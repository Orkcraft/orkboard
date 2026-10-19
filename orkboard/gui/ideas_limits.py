"""The top bar's limits (docs/specs/33-v1-shell.md §5) and their `limits_read` events (§9), as `gui/ideas.py`'s `Ideas` has them.

What is left of each installed AI tool: `[{"provider","name","left","rows":[{"window","left","reset"}]}]`, `left` the smallest
`remaining` of the tool's rows (decisions §45.3). A tool turned on in Settings whose limits could not be read stays, with
`left` None and `error` its reader's words, so it is never missing without a word. The Town Hall's last read when it has
one, else read in a thread every LIMITS_S. Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

import datetime as dt
import threading
import time
from pathlib import Path

from orkboard.realm import event_log, harnesses

LIMITS_S = 300.0                  # how often the AI tools' limits are read for the top bar
LIMITS_LOG_S = 3600.0             # limits_read at most once an hour (and whenever a task is held)
WINDOWS = {"session": "5h", "weekly": "week"}      # the quota readers' window names → the top bar's
UNREAD_CHARS = 160                # of a reader's words when a tool's limits could not be read


def _window(lim, grouped: bool) -> str:
    """A row's name in the top bar: its window ("5h", "week"), after its group when the tool has several."""
    window = WINDOWS.get(lim.window, lim.window) or lim.group or "limit"
    return f"{lim.group} · {window}" if grouped and lim.group and lim.group != window else window


class LimitsMixin:
    def limits(self) -> list[dict]:
        """What is left of each installed AI tool, for the top bar: `[{"provider","name","left","rows":[{"window",
        "left","reset"}]}]`, `left` the smallest `remaining` of the tool's rows (decisions §45.3). The Town Hall's
        last read when it has one, else read here in a thread every LIMITS_S."""
        rows = list(self.host.limits() or [])
        if rows:
            self.log_limits()
        if not rows:
            now = time.monotonic()
            if now - self._limits_at >= LIMITS_S and not self._limits_busy:
                self._limits_busy, self._limits_at = True, now
                threading.Thread(target=self._read_limits, daemon=True, name="ideas-limits").start()
            return self._limits
        return self._limits_of(rows)

    def log_limits(self, force: bool = False) -> None:
        """`limits_read` for each tool: once an hour at most, and whenever a task is held (`force`)."""
        now = time.monotonic()
        if not force and now - self._limits_logged < LIMITS_LOG_S:
            return
        rows = list(self.host.limits() or [])
        found = self._limits_of(rows) if rows else self._limits
        if not found:
            return
        self._limits_logged = now
        for l in found:
            if l["left"] is None:
                continue
            low = min(l["rows"], key=lambda r: r["left"]) if l.get("rows") else {}
            self._ev(event_log.LIMITS_READ, provider=l["provider"], left=l["left"], window=low.get("window", ""))

    def _read_limits(self) -> None:
        try:
            from orkboard.sources.limits import fetch_limits
            self._limits = self._limits_of(fetch_limits(Path(self.host.repo_root)))
            self.log_limits()
        except Exception:                       # a quota never breaks the top bar
            pass
        finally:
            self._limits_busy = False

    def _limits_of(self, rows: list) -> list[dict]:
        by: dict[str, list] = {}
        unread: dict[str, str] = {}             # a tool turned on whose rows all failed: its reader's first words
        tools = getattr(getattr(self.host, "machine", None), "tools", None) or {}
        for lim in rows:
            provider = getattr(lim, "provider", "")
            if not harnesses.get(provider):
                continue
            if getattr(lim, "remaining", None) is not None:
                by.setdefault(provider, []).append(lim)
            elif getattr(lim, "error", None) and getattr(tools.get(provider), "enabled", False):
                unread.setdefault(provider, str(lim.error).strip()[:UNREAD_CHARS])
        out = []
        for provider, mine in by.items():
            grouped = len({x.group for x in mine}) > 1      # agy's Gemini and its Claude and GPT models: each row says whose
            out.append({"provider": provider, "name": harnesses.title(provider).split()[0],
                        "left": round(min(x.remaining for x in mine), 4),
                        "rows": [{"window": _window(x, grouped),
                                  "left": round(x.remaining, 4),
                                  "reset": x.reset.isoformat(timespec="minutes") if isinstance(x.reset, dt.datetime)
                                  else ""} for x in mine]})
        out += [{"provider": p, "name": harnesses.title(p).split()[0], "left": None, "error": why, "rows": []}
                for p, why in unread.items() if p not in by]
        order = harnesses.ids()
        return sorted(out, key=lambda l: order.index(l["provider"]))
