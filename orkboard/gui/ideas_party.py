"""A goal's party measured (docs/specs/43-party-measured.md) as `gui/ideas.py`'s `Ideas` has it: `ideas.party`, what the
party did (realm/party_work.py), and `ideas.party_price`, about what a party costs an idea (realm/party_price.py). `ideas.party_answer`
takes or keeps the night's proposal to take a checker out of a party (realm/party_proposals.py); `ideas.parties`, `ideas.party_save` and
`ideas.party_drop` are the person's own parties (F: realm/own_parties.py). Split from ideas.py to
keep it under ~600 lines.
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _text
from orkboard.realm import event_log, goal_team, ideas, own_parties, party_hints, party_price, party_proposals, party_work, roles


class PartyMixin:
    def party(self, args: dict) -> dict:
        """`{"goal"}`: §2.1's object, what the goal's party did."""
        goal = _text(args, "goal", 100)
        if ideas.track_page(self.root(False), goal) is None:
            raise IdeasError("That goal is gone")
        return party_work.work(self.root(False), self.state_dir, goal, self._target())

    def party_price(self, args: dict) -> dict:
        """`{"leader", "team", "every", "craft"?}`: §3.1's object, about what an idea costs with that party, before it starts, and
        `hints` (spec 43 §5): at most two lines about the party for the goal's `craft`."""
        leader = _text(args, "leader", 60) if args.get("leader") else roles.TASKMASTER
        try:
            team = goal_team.clean(args.get("team") if args.get("team") is not None else [])
            every = goal_team.clean(args.get("every") if args.get("every") is not None else [])
        except ValueError as e:
            raise IdeasError(str(e)) from None
        if why := goal_team.seats(team, "" if leader == roles.TASKMASTER else leader):
            raise IdeasError(why)
        every = [s for s in every if s in team]
        craft = args.get("craft") if args.get("craft") in roles.CRAFTS else ""
        got = party_price.price(self.root(False), self.state_dir, self.board_settings(), leader, team, every)
        return {**got, "hints": party_hints.hints(self.root(False), self.state_dir, craft, leader, team, every)}

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

    def parties(self, args: dict) -> dict:
        """`{}`: the person's parties (spec 43 §6.2), for the pickers: each with its seats, the names of its own agents and its
        record (`goals`, `projects`, `met`)."""
        return {"parties": [{"id": p["id"], "name": p["name"], "craft": p["craft"], "leader": p["leader"], "team": p["team"],
                             "every": p["every"], "own": [o["name"] for o in p["own"]], **own_parties.counts(p), "saved": p["saved"]}
                            for p in own_parties.list()]}

    def party_save(self, args: dict) -> dict:
        """`{"goal", "name", "replace"?}`: the goal's party as it is now, kept among the person's (a taken name is refused unless
        `replace`); the agents of its own that are not the library's go with it."""
        goal = _text(args, "goal", 100)
        root = self.root(False)
        g = next((t for t in ideas.tracks(root, make=False) if t["slug"] == goal), None)
        if g is None:
            raise IdeasError("That goal is gone")
        leader = g["leader"] or roles.TASKMASTER
        own = own_parties.carry(self.state_dir, leader, g["team"])
        replace = args.get("replace") is True
        before = {p["name"].lower() for p in own_parties.list()}
        name = _text(args, "name", 200)
        try:
            pid = own_parties.save(name, g["craft"], leader, g["team"], g["every"], own, replace)
        except ValueError as e:
            raise IdeasError(str(e)) from None
        self._ev(event_log.PARTY_SAVED, args, party=pid, members=len(g["team"]) + (leader != roles.TASKMASTER), own=len(own),
                 replaced=" ".join(name.split()).lower() in before)
        return {"id": pid}

    def party_drop(self, args: dict) -> dict:
        """`{"id"}`: a party of the person's removed; the goals that used it keep their agents."""
        pid = _text(args, "id", 60)
        try:
            own_parties.drop(pid)
        except ValueError as e:
            raise IdeasError(str(e)) from None
        self._ev(event_log.PARTY_DROPPED, args, party=pid)
        return {"ok": True}
