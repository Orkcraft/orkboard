"""The Board's Target (docs/specs/35-goals-window.md §1): thrift · balance · quality picks the tier and the reasoning
(effort) of every step of the Board, the keeper's and the orks'; and the clock the Board's night and reserve read.

    pick("draft", "balance")                       # ("elder", "medium")
    pick("refresh", "thrift")                      # None: thrift reads no goal again at night
    pick("op_act", "balance")                      # ("laborer", ""): an operation's action (spec 38 §4)
    keeper_pick("talk", "quality", "haiku")        # ("haiku", "high"): the Taskmaster's own model wins
    task_pick("warrior", "thrift", "")             # ("laborer", "low"): Grunt runs on the shifted tier
    in_night("01:00-07:00", now)                   # inside the night window (the machine's local time)
    reserve_held(limits, settings, now)            # the reserve left for the person: None, or until when
    week(limits, now), pace(limits, now)           # the Claude week's share left against the share of it still to come (spec 44 §1)

One Target per Board, for the whole route board → pool → gate (decisions §44.3, §47.6). A role with a model set
(spec 34 §3) runs on it; the Target still gives the effort. No face, no model.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from orkboard.realm import plans

TARGETS = ("thrift", "balance", "quality")
DEFAULT = "balance"
EFFORTS = ("low", "medium", "high", "xhigh", "max")      # the Claude CLI's `--effort` levels
STEPS = ("goal", "draft", "answer", "talk", "plan", "refresh", "propose", "task")
PROPOSALS = {"thrift": 0, "balance": 2, "quality": 3}  # the night's proposals by the Target (§8)
MAX_WAITING = 3                                          # never more proposals than this waiting in all
TIER_ROLE = "elder"                                      # the Taskmaster's default: its model is not the person's pick

# step → target → (tier, effort); a task's tier is relative: -1 one lighter, 0 its own, +1 one heavier.
MATRIX: dict[str, dict[str, tuple[Any, str] | None]] = {
    "goal": {"thrift": ("elder", "medium"), "balance": ("elder", "high"), "quality": ("elder", "xhigh")},
    "draft": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    # the answer to a spec's questions (§0) is not in the spec's table: it finishes the draft, so it runs as the draft
    "answer": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "talk": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "plan": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "refresh": {"thrift": None, "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "propose": {"thrift": None, "balance": ("elder", "low"), "quality": ("elder", "medium")},
    # a goal's leader accepts the goal against its metrics once its ideas are done (core/idea_lead.py)
    "accept": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "task": {"thrift": (-1, "low"), "balance": (0, "medium"), "quality": (1, "high")},
    # Operations' calls (docs/specs/38-operations.md §4), under Operations' own Target: no effort on the laborer tier
    "op_prepare": {"thrift": ("warrior", "low"), "balance": ("warrior", "medium"), "quality": ("elder", "medium")},
    "op_act": {"thrift": ("laborer", ""), "balance": ("laborer", ""), "quality": ("warrior", "low")},
    "op_learn": {"thrift": ("laborer", ""), "balance": ("warrior", "low"), "quality": ("warrior", "medium")},
}
OP_STEPS = ("op_prepare", "op_act", "op_learn")


# §0: one call, one job. What a keeper call is given is built by code and cut to a cap (characters of the prompt, the
# call's own instructions not counted); how many files it may read; its budget in USD (`--max-budget-usd`) in balance,
# half in thrift, double in quality.
CONTEXT = {"goal": 12_000, "draft": 8_000, "answer": 8_000, "talk": 6_000, "plan": 10_000, "refresh": 12_000, "accept": 10_000,
           "propose": 10_000, "op_prepare": 12_000, "op_act": 6_000, "op_learn": 6_000}
READS = {"goal": 8, "draft": 6, "plan": 6, "refresh": 6, "talk": 2, "answer": 2, "propose": 0, "accept": 4}
CAPS = {"goal": 1.00, "draft": 0.60, "answer": 0.40, "talk": 0.20, "plan": 0.60, "refresh": 0.50, "propose": 0.30, "accept": 0.60,
        "op_prepare": 0.30, "op_act": 0.10, "op_learn": 0.10}
BUDGET_SHARE = {"thrift": 0.5, "balance": 1.0, "quality": 2.0}


def budget(step: str, target: str) -> float | None:
    """A keeper call's budget in USD under the Target; None for a step with no cap."""
    if step not in CAPS:
        return None
    return round(CAPS[step] * BUDGET_SHARE.get(target if target in TARGETS else DEFAULT, 1.0), 2)


def cut(parts: list[tuple[str, str]], cap: int) -> str:
    """A call's context from its parts ((heading, text), in the order they matter), cut so the whole stays within
    `cap` characters: a part that does not fit is cut, the ones after it are left out."""
    out, left = [], cap
    for head, text in parts:
        block = f"{head}:\n{(text or '').strip() or '(none)'}\n\n"
        if len(block) <= left:
            out.append(block)
            left -= len(block)
            continue
        if left > len(head) + 40:
            out.append(block[:left - 2].rstrip() + "…\n")
        break
    return "".join(out)


def target_of(settings: dict | None) -> str:
    value = (settings or {}).get("target")
    return value if value in TARGETS else DEFAULT


def pick(step: str, target: str, tier: str = "warrior") -> tuple[str, str] | None:
    """(tier, effort) of a step under a target; None when the target skips the step. `tier`: a task's planned tier."""
    row = MATRIX[step].get(target if target in TARGETS else DEFAULT)
    if row is None:
        return None
    what, effort = row
    return (plans.shift(tier, what) if step == "task" else what), effort


def keeper_pick(step: str, target: str, taskmaster: str = TIER_ROLE) -> tuple[str, str] | None:
    """A keeper step's (model or tier, effort): the Taskmaster's model, when it is not its default elder, replaces
    the tier; the Target still gives the effort."""
    got = pick(step, target)
    if got is None:
        return None
    tier, effort = got
    return (taskmaster if taskmaster and taskmaster != TIER_ROLE else tier), effort


def task_pick(tier: str, target: str, role_model: str = "") -> tuple[str, str]:
    """A task's (model or tier it runs on, effort): a role with a model keeps it; Grunt ("") the shifted tier."""
    shifted, effort = pick("task", target, tier or "warrior")
    return (role_model or shifted), effort


def tier_of(model: str) -> str:
    """The tier a model or tier counts as in an estimate (a model the tables do not know: warrior)."""
    if model in plans.tiers.TIERS:
        return model
    from orkboard.realm import harnesses
    return harnesses.tier_of_model(model) or "warrior"


# -- the night and the reserve (§6, §7) -------------------------------------------------------------------------

def _minutes(text: str) -> int:
    hh, mm = text.split(":")
    return int(hh) * 60 + int(mm)


def night_start(spec: str, now: dt.datetime) -> dt.datetime | None:
    """When the night window `now` is in began ("01:00-07:00", local time; it may cross midnight); None outside it."""
    try:
        a, b = (_minutes(x) for x in str(spec).split("-"))
    except ValueError:
        return None
    m = now.hour * 60 + now.minute
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if a < b:
        return day + dt.timedelta(minutes=a) if a <= m < b else None
    if m >= a:
        return day + dt.timedelta(minutes=a)
    if m < b:
        return day - dt.timedelta(days=1) + dt.timedelta(minutes=a)
    return None


def in_night(spec: str, now: dt.datetime | None = None) -> bool:
    return night_start(spec, now or dt.datetime.now()) is not None


def left_of(limits, provider: str = "claude") -> float | None:
    """The smallest share left among the tool's windows, None when none was read."""
    left = [lim.remaining for lim in limits or () if getattr(lim, "provider", "") == provider
            and getattr(lim, "remaining", None) is not None]
    return min(left) if left else None


def reserve(settings: dict | None, night: bool) -> float:
    s = settings or {}
    key, default = ("reserve_night", 0.1) if night else ("reserve_day", 0.3)
    value = s.get(key, default)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default


MARGIN = 0.10                                            # the week is ahead of its pace by at least this much (spec 44 §1)
SOON_S = 3600                                            # within this long of the five-hour window's reset, its reserve is the night's
WEEK_S = 7 * 24 * 3600


def week(limits, now: float, provider: str = "claude") -> dict | None:
    """The tool's weekly window as {"left", "rest", "reset"}: its share left, the share of the week still to come
    ((reset − now) / 7 days, between 0 and 1) and its reset in epoch seconds. None when no weekly limit has a share
    and a reset read (not read, an error, another tool, an API key): every rule that reads the pace is then today's."""
    from orkboard.realm import status
    rows = [(lim.remaining, r) for lim in limits or () if getattr(lim, "provider", "") == provider and getattr(lim, "window", "") == "weekly"
            and getattr(lim, "remaining", None) is not None and (r := status._reset_s(lim)) is not None]
    if not rows:
        return None
    left, reset = min(rows)                               # the tightest, when a tool has several
    return {"left": left, "rest": min(1.0, max(0.0, (reset - now) / WEEK_S)), "reset": reset}


def pace(limits, now: float, provider: str = "claude") -> str | None:
    """The week's pace: "ahead" (its share left at least MARGIN above the share to come), "behind" (below it), else
    "even"; None with no week."""
    got = week(limits, now, provider)
    if got is None:
        return None
    if got["left"] - got["rest"] >= MARGIN - 1e-9:
        return "ahead"
    return "behind" if got["left"] < got["rest"] else "even"


def reserve_held(limits, settings: dict | None, now: float, provider: str = "claude") -> float | None:
    """What starts by itself waits while any of the tool's windows has its share or less left (by day the day's reserve, inside
    the night window the night's): until when (epoch seconds), else None. By day, within SOON_S of the five-hour window's
    (`session`) reset and while the week is not behind, that window's share is the night's. With no limits read for the
    tool, no reserve applies; with no window near its reset this is the smallest window against one share."""
    rows = [lim for lim in limits or () if getattr(lim, "provider", "") == provider and getattr(lim, "remaining", None) is not None]
    if not rows:
        return None
    from orkboard.realm import status
    night = in_night(str((settings or {}).get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now))
    eased = not night and pace(limits, now, provider) in ("ahead", "even")
    spent = []
    for lim in rows:
        share = reserve(settings, night)
        reset = status._reset_s(lim)
        if eased and getattr(lim, "window", "") == "session" and reset is not None and 0 < reset - now <= SOON_S:
            share = reserve(settings, True)               # the hour before the five hours come back: they ease the reserve
        if lim.remaining <= share:
            spent.append(lim)
    if not spent:
        return None
    resets = [r for lim in spent if (r := status._reset_s(lim)) is not None and r > now]
    return max(resets) if resets else now + status.UNKNOWN_RESET_S


class WeekHold(float):
    """What `gate` answers when the week holds a Board's Low plan's tasks at night: the week's reset (a hold of kind `week`)."""


def board_low(plan: dict, board: dict) -> bool:
    """A plan the Board itself put off to the night (a Low plan's start) while it may still decide: autostart is on."""
    return plan.get("start_at") == "night" and plan.get("start_at_by") == "board" and bool(board.get("autostart", True))


def by_pace(plan: dict, limits, board: dict, now: float) -> bool:
    """The Board's Low plan may start by day: the week is ahead of its pace (spec 44 §3)."""
    night = in_night(str(board.get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now))
    return board_low(plan, board) and not night and pace(limits, now) == "ahead"


def gate(plan: dict, limits, board: dict, now: float) -> str | float | None:
    """What holds a passed plan's tasks besides the spent window: "night" (it starts at night and the window is not
    open: its tasks wait, unheld), the reserve's reset (it started by itself), the week's reset (`WeekHold`: the Board's
    Low plan at night while the week is behind), else None (spec 35 §5, §6; spec 44 §3). The Board's Low plan is the one
    exception to "night": by day, with the week ahead of its pace, it starts, the reserve as for any autostart."""
    night = in_night(str(board.get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now))
    if plan.get("start_at") == "night":
        low = board_low(plan, board)
        if not night and not (low and pace(limits, now) == "ahead"):
            return "night"
        if night and low and pace(limits, now) == "behind":
            got = week(limits, now)
            return WeekHold(got["reset"])
    if plan.get("passed_by") == "auto" or plan.get("start_at") == "night":
        return reserve_held(limits, board, now)
    return None
