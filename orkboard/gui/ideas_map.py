"""The Map (docs/specs/39-map.md §2) as `gui/ideas.py`'s `Ideas` has it: `ideas.map`, a view of what the Board holds
(realm/board_map.py). It changes nothing, but for one thing: a goal of before has no element (spec 50 §2.3), and the first
time the Map reads it one is given and stored (once, ever; `ideas_rev` does not move). Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

import time

from orkboard.gui.ideas_args import IdeasError, _opt
from orkboard.realm import board_map, idea_element, ideas


class MapMixin:
    def map(self, args: dict) -> dict:
        """`{"goal"?}` one goal's slug (none: every goal): the Map of this project."""
        goal = _opt(args, "goal")
        root = self.root(False)
        if goal and not any(t["slug"] == goal and t["slug"] != ideas.GENERAL for t in ideas.tracks(root, make=False)):
            raise IdeasError("That party is gone")
        got = board_map.build(root, self.state_dir, self.settings_now(), list(self.host.limits() or []), time.time(), goal=goal,
                              rev=self.rev, state_of=self._state, goal_state_of=self.goal_state)
        waiting: dict[str, list[dict]] = {}
        if any(t["state"] == "review" for n in got["nodes"] for t in n["tasks"]):          # the results at Review, each on its idea (spec 48 §1)
            for r in self.results():
                waiting.setdefault(r["idea"], []).append(r)
        used: dict[str, list[str]] = {}                                  # each party's open goals' elements, as they are given
        for n in got["nodes"]:
            if n["element"] and n["state"] != "done":
                used.setdefault(n["goal"], []).append(n["element"])
        for n in got["nodes"]:
            n["results"] = waiting.get(n["slug"], [])
            if not n["element"]:                                         # a goal of before: one is given now, once
                try:
                    n["element"] = idea_element.give(root, self.state_dir, n["slug"], used.setdefault(n["goal"], []))
                except (OSError, ValueError):
                    continue                                             # a disk that refuses: the faces draw it dim, the next read tries again
                if n["state"] != "done":
                    used[n["goal"]].append(n["element"])
        return got
