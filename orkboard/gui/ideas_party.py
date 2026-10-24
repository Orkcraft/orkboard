"""A goal's party measured (docs/specs/43-party-measured.md) as `gui/ideas.py`'s `Ideas` has it: `ideas.party`, what the party did
(realm/party_work.py) and `ideas.party_price`, about what a party costs before it starts (realm/party_price.py). They read and change nothing;
`ideas.party_answer`, the person's answer to the night's proposal about a party (realm/party_proposals.py). `ideas.parties`, `ideas.party_save` and `ideas.party_drop`, the person's own parties (realm/own_parties.py). Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _device, _opt, _text
from orkboard.realm import event_log, goal_team, goal_types, ideas, library, own_parties, party_hints, party_price, party_proposals, party_work, releases, roles


class PartyMixin:
    def party(self, args: dict) -> dict:
        """`{"goal"}`: what the goal's party did, member by member and check by check (spec 43 §2.1)."""
        goal = _text(args, "goal", 100)
        if ideas.track_page(self.root(False), goal) is None:
            raise IdeasError("That party is gone")
        return party_work.work(self.root(False), self.state_dir, goal, self._target())

    def party_price(self, args: dict) -> dict:
        """`{"leader", "team", "every", "craft"?}`: about what an idea costs with this party, before it starts (spec 43 §3.1), `hints`, at
        most two quiet lines about it (§5; `craft` is the goal's, left out for a Mixed goal), and `types`, the goal types it would be offered
        (spec 63 §1: `[{id, name, sign, missing}]` in the catalog's order, `missing` the name of the agent a type needs, "" with none).
        Nothing is saved. Led by the Investor (Ideation): a pitch's price (`pitch: true`), no hints, no types (spec 65 §1, §3)."""
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
        party = goal_types.Party.of(self.state_dir, self.root(False), leader, team)
        types = [{"id": t.id, "name": t.name, "sign": t.sign, "missing": rows[0]["name"] if rows else ""}
                 for t, rows in goal_types.offered(self.state_dir, self.root(False), "", read=party)]
        ideation = leader == library.INVESTOR                # a pitch's price, no hint about code or checks (spec 65 §3)
        return {**party_price.price(self.root(False), self.state_dir, self.board_settings(), leader, team, every),
                "hints": [] if ideation else party_hints.hints(self.root(False), self.state_dir, craft, leader, team, every), "types": types}

    def save_releases_from(self, party: str, value: object) -> None:
        """`releases_from` of `ideas.goal_save`: the parties a Release party takes its flags from, kept with the party ([] is every party but
        Ideation; spec 67 §3.2). Refused when it is not a list of the project's parties."""
        try:
            releases.set_releases_from(self.root(), party, value)
        except ValueError as e:
            raise IdeasError(str(e)) from None

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

    # -- your parties (spec 43 §6) -------------------------------------------------------------------------------------------

    def parties(self, args: dict) -> dict:
        """`{}`: the person's saved parties, for every project, with how many goals and projects used each and how many were met."""
        return {"parties": [{"id": p["id"], "name": p["name"], "craft": p.get("craft") or "", "leader": p.get("leader") or roles.TASKMASTER,
                             "team": p.get("team") or [], "every": p.get("every") or [], "own": [o.get("name") or o.get("slug") for o in p.get("own") or []],
                             "goals": len(p.get("uses") or []), "projects": len({u.get("project") for u in p.get("uses") or []}),
                             "met": sum(1 for u in p.get("uses") or [] if u.get("met") is True), "saved": p.get("saved") or ""}
                            for p in own_parties.list()]}

    def party_save(self, args: dict) -> dict:
        """`{"goal", "name", "replace"?}`: the goal's party as it is now, kept for any project. A taken name is refused (*You have a party named
        “Lean web”*) unless `replace`; a thirteenth is refused. An agent of the person's own travels in it (its role as it is now)."""
        goal = _text(args, "goal", 100)
        g = next((t for t in ideas.tracks(self.root(False), make=False) if t["slug"] == goal), None)
        if g is None:
            raise IdeasError("That party is gone")
        name = _text(args, "name", own_parties.NAME_CHARS + 20)
        replace = args.get("replace") is True
        leader, team, every = goal_team.leader_of(self.root(False), goal), goal_team.team_of(self.root(False), goal), goal_team.every_of(self.root(False), goal)
        carried = [r for s in dict.fromkeys([leader, *team]) if s not in roles.BUILTIN and library.get(s) is None and (r := roles.role(self.state_dir, s)) is not None]
        own = [{k: r.get(k) for k in own_parties.OWN_KEYS} for r in carried]
        existing = {p["name"].lower() for p in own_parties.list()}
        try:
            got = own_parties.save(name, g["craft"], leader, team, every, own, replace)
        except own_parties.OwnPartyError as e:
            raise IdeasError(str(e)) from None
        self._ev(event_log.PARTY_SAVED, args, party=got, members=len(team) + (1 if leader != roles.TASKMASTER else 0), own=len(own),
                 replaced=" ".join(name.split()).lower() in existing)
        self.changed("")
        return {"id": got}

    def party_drop(self, args: dict) -> dict:
        """`{"id"}`: a party of the person's removed; the goals that used it keep their agents."""
        party = _text(args, "id", 40)
        try:
            own_parties.drop(party)
        except own_parties.OwnPartyError as e:
            raise IdeasError(str(e)) from None
        self._ev(event_log.PARTY_DROPPED, args, party=party)
        return {"ok": True}
