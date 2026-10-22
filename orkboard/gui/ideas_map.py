"""The Map (docs/specs/39-map.md §2) as `gui/ideas.py`'s `Ideas` has it: `ideas.map`, a view of what the Board holds
(realm/board_map.py). It changes nothing, but for one thing: a goal of before has no element (spec 50 §2.3), and the first
time the Map reads it one is given and stored (once, ever; `ideas_rev` does not move). A party carries its goal types (spec 52
§2.4: its leader's set, the most used first, with what each misses of the party), read here with the map: the pure
`board_map.build` reads no runs. Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

import time
from collections import Counter
from pathlib import Path

from orkboard.gui.ideas_args import IdeasError, _opt
from orkboard.realm import board_map, goal_team, goal_types, idea_element, ideas, library


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
        for g in got["goals"]:
            g["types"] = self.types_of(root, g["slug"], [n["slug"] for n in got["nodes"] if n["goal"] == g["slug"]])
            g["stages"] = self.stages_of(root, g["slug"])
        return got

    @staticmethod
    def stages_of(root: Path, party: str) -> dict:
        """A party's stages (spec 59 §3): the words of its leader's three steps and the seats of its builders and checkers."""
        s = library.stages_of(goal_team.leader_of(root, party))
        return {"lead": {"word": s.lead}, "build": {"word": s.build, "seats": s.build_seats}, "check": {"word": s.check, "seats": s.check_seats}}

    def types_of(self, root: Path, party: str, goals: list[str]) -> list[dict]:
        """A party's goal types (spec 59 §4.5): what it is offered (`goal_types.offered`), each with what it misses of the party, the
        most used first (`used`: how many of its goals, of any state, have that type; an old key counts as its id), then those
        with nothing missing before those with someone missing, then the catalog's order."""
        p = goal_types.Party(self.state_dir, root, party)
        used = Counter(t.id for slug in goals if (t := goal_types.get(ideas.state(self.state_dir, slug).get("type"))) is not None)
        rows = [{"id": t.id, "name": t.name, "sign": t.sign, "line": t.line, "lens": t.lens,
                 "asks": [{"id": a.id, "label": a.label, "hint": a.hint} for a in t.asks], "refs": t.refs,
                 "used": used[t.id], "missing": missing}
                for t, missing in goal_types.offered(self.state_dir, root, party, read=p)]
        return sorted(rows, key=lambda r: (-r["used"], bool(r["missing"])))
