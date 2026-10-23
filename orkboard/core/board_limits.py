"""What is left of each AI tool, for the Board on its own (spec 37 §4): the quota readers (`sources/limits.py`) on a
thread, on the Town Hall's clock (every LIMITS_REFRESH_S), the rows kept for the top bar and the runner's reserve.

    limits = BoardLimits(repo_root, call)   # call: runs a function on the host's thread
    limits.tick(now)                         # from the host's clock: reads again when due
    limits()                                 # the last rows read ([] until the first read is in)

A read that shows the Claude week's reset moved later than the one read before (the week came back) writes `week_reset` to the log of
the project shown (spec 44 §4): how much of the week was left unused. Each read also teaches the rate of Claude's
five-hour window (`sources/window_rate.py`, decisions §81), on the reader's thread: it reads the machine's transcripts.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from orkboard.realm import event_log, idea_target
from orkboard.sources import window_rate
from orkboard.sources.limits import Limit, fetch_limits

LIMITS_REFRESH_S = 10 * 60      # as the Town Hall's worker (core/workers/town_hall.py)
WEEK_BACK_S = 24 * 3600         # a weekly reset read this much later than the one before: the week came back (a few minutes' jitter is not)


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
        self._week: dict | None = None          # the week as the last read showed it: {"left", "rest", "reset"}

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
            try:
                window_rate.learn(found)
            except Exception:                   # nor does its rate
                pass
            self.call(self._read, found)

        threading.Thread(target=work, daemon=True, name="board-limits").start()

    def _read(self, found: list[Limit]) -> None:
        self.rows, self.reading = list(found), False
        self._watch_week(found)

    def shown(self) -> bool:
        """A project is shown (else the rows are read for the machine, from the home folder)."""
        return self.repo_root != Path.home()

    def _watch_week(self, found: list[Limit]) -> None:
        got, before = idea_target.week(found, time.time()), self._week
        if got is not None:
            self._week = got
        if got is not None and before is not None and got["reset"] - before["reset"] > WEEK_BACK_S and self.shown():
            event_log.record(self.repo_root, event_log.WEEK_RESET, left=before["left"], provider="claude")      # how much of the week was left
