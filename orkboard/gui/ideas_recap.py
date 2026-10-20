"""Coming back (docs/specs/42-coming-back.md) as `gui/ideas.py`'s `Ideas` has it: `ideas.recap`, what the Board did since a
device's last look (realm/board_recap.py). It reads and changes nothing; B, F, G and H add their readers here. Split from
ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from orkboard.gui.ideas_args import IdeasError
from orkboard.realm import board_recap, goal_flags

RECAP_DAYS = 30                          # a last look older than this is taken as this many days ago


class RecapMixin:
    def recap(self, args: dict) -> dict:
        """`{"since": <ms since the epoch>}`: §1.1's object for this project, `waits` filled from the snapshot."""
        ms = args.get("since")
        if not isinstance(ms, (int, float)) or isinstance(ms, bool):
            raise IdeasError("`since` is the last look, in milliseconds")
        now = dt.datetime.now().astimezone()
        try:
            since = dt.datetime.fromtimestamp(ms / 1000).astimezone()
        except (OverflowError, OSError, ValueError):
            raise IdeasError("`since` is the last look, in milliseconds") from None
        if since > now:
            raise IdeasError("`since` is ahead of now")
        since = max(since, now - dt.timedelta(days=RECAP_DAYS))
        got = board_recap.build(Path(self.host.repo_root), self.state_dir, since, now, self.board(make=False), into=self._into())
        snap = self.snapshot()
        got["waits"] = {"you": int(snap.get("needs_you") or 0), "review": int(snap.get("review_count") or 0)}
        return got

    def flags(self, args: dict) -> dict:
        """`{}`: the project's flags, goals accepted by their leader against their metrics, newest first (spec 42 §2)."""
        return {"flags": goal_flags.flags(self.root(False), self.state_dir)}
