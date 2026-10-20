"""A goal's party measured (docs/specs/43-party-measured.md) as `gui/ideas.py`'s `Ideas` has it: `ideas.party`, what the party did
(realm/party_work.py) and `ideas.party_price`, about what a party costs before it starts (realm/party_price.py). They read and change nothing;
D to F add their commands here. Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _opt, _text
from orkboard.realm import goal_team, ideas, library, party_price, party_work, roles


class PartyMixin:
    def party(self, args: dict) -> dict:
        """`{"goal"}`: what the goal's party did, member by member and check by check (spec 43 §2.1)."""
        goal = _text(args, "goal", 100)
        if ideas.track_page(self.root(False), goal) is None:
            raise IdeasError("That goal is gone")
        return party_work.work(self.root(False), self.state_dir, goal, self._target())

    def party_price(self, args: dict) -> dict:
        """`{"leader", "team", "every"}`: about what an idea costs with this party, before it starts (spec 43 §3.1). Nothing is saved."""
        leader = _opt(args, "leader") or roles.TASKMASTER
        if leader != roles.TASKMASTER and library.get(leader) is None:
            raise IdeasError(f"No agent {leader!r}")
        try:
            team = goal_team.clean(args.get("team") if args.get("team") is not None else [])
        except ValueError as e:
            raise IdeasError(str(e)) from None
        every = [s for s in args.get("every") or [] if isinstance(s, str)] if isinstance(args.get("every"), list) else []
        if why := goal_team.seats(team, "" if leader == roles.TASKMASTER else leader):
            raise IdeasError(why)
        return party_price.price(self.root(False), self.state_dir, self.board_settings(), leader, team, [s for s in every if s in team])
