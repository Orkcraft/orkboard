"""A goal's party measured (docs/specs/43-party-measured.md) as `gui/ideas.py`'s `Ideas` has it: `ideas.party`, what the party did
(realm/party_work.py) and `ideas.party_price`, about what a party costs before it starts (realm/party_price.py). They read and change nothing;
`ideas.party_answer`, the person's answer to the night's proposal about a party (realm/party_proposals.py). E and F add their commands here. Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _device, _opt, _text
from orkboard.realm import event_log, goal_team, ideas, library, party_hints, party_price, party_proposals, party_work, roles


class PartyMixin:
    def party(self, args: dict) -> dict:
        """`{"goal"}`: what the goal's party did, member by member and check by check (spec 43 §2.1)."""
        goal = _text(args, "goal", 100)
        if ideas.track_page(self.root(False), goal) is None:
            raise IdeasError("That goal is gone")
        return party_work.work(self.root(False), self.state_dir, goal, self._target())

    def party_price(self, args: dict) -> dict:
        """`{"leader", "team", "every", "craft"?}`: about what an idea costs with this party, before it starts (spec 43 §3.1), and `hints`, at
        most two quiet lines about it (§5; `craft` is the goal's, left out for a Mixed goal). Nothing is saved."""
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
        every = [s for s in every if s in team]
        craft = _opt(args, "craft")
        return {**party_price.price(self.root(False), self.state_dir, self.board_settings(), leader, team, every),
                "hints": party_hints.hints(self.root(False), self.state_dir, craft, leader, team, every)}

    def party_answer(self, args: dict) -> dict:
        """`{"goal", "take", "reason"?}`: take the checker the night proposed out of the goal's party (the goal is not read again), or keep it
        (a decline, which holds until a newer run of eight). Spec 43 §4.2."""
        goal = _text(args, "goal", 100)
        if not isinstance(args.get("take"), bool):
            raise IdeasError("take is true or false")
        reason = args.get("reason") if isinstance(args.get("reason"), str) else ""
        try:
            by = party_proposals.answer(self.root(), self.state_dir, goal, args["take"], reason)
        except ValueError as e:
            raise IdeasError(str(e)) from None
        self._ev(event_log.PARTY_ANSWERED, args, goal=goal, by=by, take=args["take"], has_reason=bool(reason.strip()))
        self.changed(f"goal:{goal}")
        return {"ok": True}
