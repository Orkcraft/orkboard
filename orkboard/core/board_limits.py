"""What is left of each AI tool, for the Board on its own (spec 37 §4): the quota readers (`sources/limits.py`) on a
thread, on the Town Hall's clock (every LIMITS_REFRESH_S), the rows kept for the top bar and the runner's reserve.

    limits = BoardLimits(repo_root, call)   # call: runs a function on the host's thread
    limits.tick(now)                         # from the host's clock: reads again when due
    limits()                                 # the last rows read ([] until the first read is in)
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from orkboard.realm import event_log, idea_target
from orkboard.sources.limits import Limit, fetch_limits

LIMITS_REFRESH_S = 10 * 60      # as the Town Hall's worker (core/workers/town_hall.py)
WEEK_MOVED_S = 3600             # a weekly reset this much later than the one read before: the week came back


class BoardLimits:
    def __init__(self, repo_root: Path, call: Callable[..., None], demo: bool = False,
                 fetch: Callable[[Path], list[Limit]] = fetch_limits) -> None:
        self.repo_root = Path(repo_root)
        self.call = call                    # the host's thread: the rows change only there
        self.demo = demo
        self.fetch = fetch
        self.rows: list[Limit] = []
        self.reading = False
        self._at = float("-inf")
        self._week: dict | None = None      # the weekly window as last read: {"left", "reset"} (spec 44 §4)

    def __call__(self) -> list[Limit]:
        return list(self.rows)

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        if self.demo or self.reading or now - self._at < LIMITS_REFRESH_S:
            return
        self._at, self.reading = now, True

        def work() -> None:
            try:
                found = self.fetch(self.repo_root)
            except Exception as e:              # a quota never stops the Board
                found = [Limit("limits", "—", "—", None, None, str(e))]
            self.call(self._read, found)

        threading.Thread(target=work, daemon=True, name="board-limits").start()

    def _read(self, found: list[Limit]) -> None:
        self.rows, self.reading = list(found), False
        self._note_week(found)

    def _note_week(self, found: list[Limit]) -> None:
        """`week_reset` (spec 44 §4): the weekly reset moved later than the one read before, so the week came back; the
        share left before it is written once to the log of the project shown (none open: not written)."""
        got = idea_target.week(found, time.time())
        if got is None:
            return
        before, self._week = self._week, {"left": got["left"], "reset": got["reset"]}
        if before is None or got["reset"] <= before["reset"] + WEEK_MOVED_S or self.demo or self.repo_root == Path.home():
            return
        event_log.record(self.repo_root, event_log.WEEK_RESET, left=round(before["left"], 4), provider="claude")
