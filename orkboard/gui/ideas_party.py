"""A goal's party measured (docs/specs/43-party-measured.md) as `gui/ideas.py`'s `Ideas` has it: `ideas.party`, what the party did
(realm/party_work.py). It reads and changes nothing; C to F add their commands here. Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _text
from orkboard.realm import ideas, party_work


class PartyMixin:
    def party(self, args: dict) -> dict:
        """`{"goal"}`: what the goal's party did, member by member and check by check (spec 43 §2.1)."""
        goal = _text(args, "goal", 100)
        if ideas.track_page(self.root(False), goal) is None:
            raise IdeasError("That goal is gone")
        return party_work.work(self.root(False), self.state_dir, goal, self._target())
