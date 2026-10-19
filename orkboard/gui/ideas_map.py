"""The Map (docs/specs/39-map.md §2) as `gui/ideas.py`'s `Ideas` has it: `ideas.map`, a view of what the Board holds
(realm/board_map.py). It changes nothing. Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

import time

from orkboard.gui.ideas_args import IdeasError, _opt
from orkboard.realm import board_map, ideas


class MapMixin:
    def map(self, args: dict) -> dict:
        """`{"goal"?}` one goal's slug (none: every goal): the Map of this project."""
        goal = _opt(args, "goal")
        root = self.root(False)
        if goal and not any(t["slug"] == goal and t["slug"] != ideas.GENERAL for t in ideas.tracks(root, make=False)):
            raise IdeasError("That goal is gone")
        return board_map.build(root, self.state_dir, self.settings_now(), getattr(self, "_limits", None), time.time(), goal=goal,
                               rev=self.rev, state_of=self._state, goal_state_of=self.goal_state)
