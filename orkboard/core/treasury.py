"""The treasury: 🪙 this run's spend and 🪵 each session's context against the town's limits, and
the subscription quota. It reads, warns once per limit and words what the HUD shows; the face
draws it and tells it which session is in front (`active`) and what the last quota reads were.

Orkboard's (spec 37 §4): the check of the spend against its cap (`over`) and the HUD's words (`words`) take no town,
and `budget(repo_root)` reads the cap where the town keeps it; `Treasury` keeps them for the line, on its `Town`.
"""
from __future__ import annotations

import json
from pathlib import Path

from orkboard.sources import telemetry

GOLD_LIMIT_USD = 20.0           # the Town Scroll's own defaults (scroll.py `Budget`), when it names none
LUMBER_LIMIT_TOKENS = 131072


def budget(repo_root: Path) -> tuple[float, int]:
    """(🪙 limit in USD, 🪵 limit in tokens) the repository's Town Scroll sets (`.orkcraft.json` `budget`), read as
    plain JSON: the Board on its own has no town; its defaults when there is none."""
    try:
        raw = json.loads((Path(repo_root) / ".orkcraft.json").read_text(encoding="utf-8")).get("budget") or {}
    except (OSError, ValueError, AttributeError):
        raw = {}
    gold, lumber = raw.get("gold_session_limit_usd"), raw.get("lumber_context_limit_tokens")
    ok = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0   # noqa: E731
    return (float(gold) if ok(gold) else GOLD_LIMIT_USD), (int(lumber) if ok(lumber) else LUMBER_LIMIT_TOKENS)


def over(spent: float, limit: float) -> bool:
    """Whether this run's spend reached the 🪙 limit (none when the limit is 0): no new work."""
    return limit > 0 and spent >= limit


def words(snap: telemetry.Snapshot, gold_limit_usd: float, lumber_limit_tokens: int,
          active: str | None = None) -> tuple[str, str, str, str]:
    """(gold, gold level, lumber, lumber level) for the HUD; "—" until a session reports. Lumber is
    the `active` session's context, else the fullest one's."""
    gold_limit = f"${gold_limit_usd:.2f}"
    if snap.sessions or snap.unpriced or snap.side_usd:
        # "+" marks spend that could not be priced (agy, or a model with no published price).
        gold = f"${snap.spent_usd:.2f}{'+' if snap.unpriced else ''} / {gold_limit}"
    else:
        gold = f"$— / {gold_limit}"
    gold_level = telemetry.level(snap.spent_usd, gold_limit_usd)
    ctx = snap.context_by_terminal.get(active) if active else None
    if ctx is None and snap.context_by_terminal:
        ctx = max(snap.context_by_terminal.values())
    lumber_limit = telemetry.fmt_tokens(lumber_limit_tokens)
    lumber = f"{telemetry.fmt_tokens(ctx)} / {lumber_limit}" if ctx is not None else f"— / {lumber_limit}"
    lumber_level = telemetry.level(ctx or 0, lumber_limit_tokens)
    return gold, gold_level, lumber, lumber_level


class Treasury:
    def __init__(self, town) -> None:
        self.town = town
        self.gold_warned = False
        self.lumber_warned: set[str] = set()

    def refresh(self) -> None:
        """Re-read this run's transcripts (only new bytes) and warn once when a limit is crossed."""
        town = self.town
        try:
            town.snapshot = town.telemetry.refresh()
        except OSError:
            return
        budget, snap = town.scroll.budget, town.snapshot
        if not self.gold_warned and snap.spent_usd >= budget.gold_session_limit_usd > 0:
            self.gold_warned = True
            town.toast(f"🪙 ${snap.spent_usd:.2f} spent of ${budget.gold_session_limit_usd:.2f} this run — new "
                       "sessions are held until you raise budget.gold_session_limit_usd in .orkcraft.json",
                       title="Treasury empty", severity="error", timeout=12)
        for key, ctx in snap.context_by_terminal.items():
            if ctx >= budget.lumber_context_limit_tokens > 0 and key not in self.lumber_warned:
                self.lumber_warned.add(key)
                town.toast(f"🪵 {telemetry.fmt_tokens(ctx)} of context in {key} (limit "
                           f"{telemetry.fmt_tokens(budget.lumber_context_limit_tokens)}) — /compact or start fresh",
                           title="Lumber over the limit", severity="warning", timeout=10)

    def exhausted(self, quiet: bool = False) -> bool:
        """True when this run's spend reached the 🪙 limit: no new sessions (said so unless `quiet`)."""
        limit = self.town.scroll.budget.gold_session_limit_usd
        spent = self.town.snapshot.spent_usd
        if over(spent, limit):
            if not quiet:
                self.town.toast(f"🪙 ${spent:.2f} of ${limit:.2f} spent this run — raise "
                                "budget.gold_session_limit_usd in .orkcraft.json to summon more",
                                title="Treasury empty", severity="warning")
            return True
        return False

    def resources(self, active: str | None = None) -> tuple[str, str, str, str]:
        """(gold, gold level, lumber, lumber level) for the HUD; "—" until a session reports. Lumber is
        the `active` session's context, else the fullest one's."""
        budget = self.town.scroll.budget
        return words(self.town.snapshot, budget.gold_session_limit_usd, budget.lumber_context_limit_tokens, active)


def subscriptions(machine) -> list[str]:
    """The enabled tools billed by subscription (settings.py): their quota is what runs out."""
    return [t for t, c in machine.tools.items() if c.enabled and c.billing == "subscription"]


def quota(machine, limits: list) -> tuple[str, str, bool]:
    """(quota, its level, whether 🪙 shows): the HUD corner follows each tool's billing — the used
    share still left of the tightest window for a subscription, 🪙 for an API (its level follows what is used)."""
    on = [t for t, c in machine.tools.items() if c.enabled]
    subs = subscriptions(machine)
    if not subs:
        return "", "ok", True
    parts, worst = [], 0.0
    for t in subs:
        left = [x.remaining for x in limits if x.provider == t and x.remaining is not None]
        if left:
            used = round((1 - min(left)) * 100)
            worst = max(worst, used)
            parts.append(f"{t} {100 - used}%")
        else:
            parts.append(f"{t} —")
    return " · ".join(parts), telemetry.level(worst, 100), len(subs) < len(on)
