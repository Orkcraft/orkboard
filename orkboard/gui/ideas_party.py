"""A goal's party measured (docs/specs/43-party-measured.md) as `gui/ideas.py`'s `Ideas` has it: `ideas.party`, what the
party did (realm/party_work.py), and `ideas.party_price`, about what a party costs an idea (realm/party_price.py). They read and
change nothing; D and F add their commands here. Split from ideas.py to
keep it under ~600 lines.
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _text
from orkboard.realm import goal_team, ideas, party_price, party_work, roles


class PartyMixin:
    def party(self, args: dict) -> dict:
        """`{"goal"}`: §2.1's object, what the goal's party did."""
        goal = _text(args, "goal", 100)
        if ideas.track_page(self.root(False), goal) is None:
            raise IdeasError("That goal is gone")
        return party_work.work(self.root(False), self.state_dir, goal, self._target())

    def party_price(self, args: dict) -> dict:
        """`{"leader", "team", "every"}`: §3.1's object, about what an idea costs with that party, before it starts."""
        leader = _text(args, "leader", 60) if args.get("leader") else roles.TASKMASTER
        try:
            team = goal_team.clean(args.get("team") if args.get("team") is not None else [])
            every = goal_team.clean(args.get("every") if args.get("every") is not None else [])
        except ValueError as e:
            raise IdeasError(str(e)) from None
        if why := goal_team.seats(team, "" if leader == roles.TASKMASTER else leader):
            raise IdeasError(why)
        return party_price.price(self.root(False), self.state_dir, self.board_settings(), leader, team, [s for s in every if s in team])
