"""A goal's party measured (docs/specs/43-party-measured.md) as `gui/ideas.py`'s `Ideas` has it: `ideas.party`, what the
party did (realm/party_work.py), and `ideas.party_price`, about what a party costs an idea (realm/party_price.py). `ideas.party_answer`
takes or keeps the night's proposal to take a checker out of a party (realm/party_proposals.py); F adds its commands here. Split from ideas.py to
keep it under ~600 lines.
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _text
from orkboard.realm import event_log, goal_team, ideas, party_price, party_proposals, party_work, roles


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

    def party_answer(self, args: dict) -> dict:
        """`{"goal", "take", "reason"?}`: the person's answer to the night's proposal to take a checker out of a goal's
        party (spec 43 §4.2). Take: the party without that checker (and its Every idea); the goal is not read again. Keep: a
        decline, held until a newer run of eight."""
        goal = _text(args, "goal", 100)
        root = self.root()
        got = party_proposals.proposal(self.state_dir, goal)
        if ideas.track_page(root, goal) is None or got is None:
            raise IdeasError("That proposal is gone")
        by, take = got["by"], args.get("take") is True
        reason = args.get("reason") if isinstance(args.get("reason"), str) else ""
        if take:
            goal_team.set_team(root, goal, [s for s in goal_team.team_of(root, goal) if s != by],
                               [s for s in goal_team.every_of(root, goal) if s != by])
        else:
            party_proposals.decline(self.state_dir, goal, by, reason)
        party_proposals.remove(self.state_dir, goal)
        self._ev(event_log.PARTY_ANSWERED, args, goal=goal, by=by, take=take, has_reason=bool(reason.strip()))
        self.changed(f"goal:{goal}")
        return {"ok": True}
