"""New goal by its type (docs/specs/52-goal-types.md §2.3, §2.6), as `gui/ideas.py`'s `Ideas` has it: `ideas.add`'s `type`,
`asks` and `join`, `ideas.start`'s `join`, and what spec 52 §2.7 adds to the events.

A type is one the party is offered (realm/goal_types.py `offered`, spec 59 §4); its asks are written after the goal's text, a line each. Who
joins changes the party the way *Edit the party* does (`ideas.goal_save`): the agent installed from the library, a member
who leaves taken out, the seats checked, the team kept, `goal_saved` logged (with `joined`, `out`, `via`). A goal kept for
tonight never changes the party; a member with work open never leaves this way. Split from ideas.py to keep it under ~600
lines.
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _opt
from orkboard.realm import event_log, goal_team, goal_types, ideas, library, party_proposals, roles

NOT_STARTED = ("waiting", "ready", "held")      # a task that has not run: given its role again when someone joins
BANDS = {"build": "builders", "check": "checkers"}


def _name(slug: str) -> str:
    a = library.get(slug)
    return a.name if a is not None else slug


class TypesMixin:
    # -- New goal by its type (§2.3) ------------------------------------------------------------------------

    def typed(self, args: dict, track: str, title: str) -> dict:
        """The type, its asks and who joins as `ideas.add` is sent them: `{key, type, lines, answered, join, rows}`.
        `type`: an id of the types the party is offered (`rows`: what that one misses; how many were offered, and how many of
        them with someone missing, wait for `idea_added`: `type_fields`); `asks`: `{ask id: text}` of that type's (`refs`: Refs' links, when it has them), each one
        line of at most 300 characters, an empty one left out; `join`: `{add, out?}`, checked against the party when the goal
        is added (`join_goal`)."""
        type_id, t, rows = _opt(args, "type"), None, []
        p = goal_types.Party(self.state_dir, self.root(), track)
        got = goal_types.offered(self.state_dir, self.root(), track, read=p)
        if type_id:
            known = goal_types.BY_ID.get(type_id)
            if known is None:
                raise IdeasError(f"No goal type “{type_id}”")
            t, rows = next(((x, r) for x, r in got if x.id == type_id), (None, []))
            if t is None:
                raise IdeasError(f"{title} cannot take “{known.name}”: no one of it does "
                                 f"{goal_types.words(goal_types.lacking(self.state_dir, p, known))}")
        asks = args.get("asks") if args.get("asks") is not None else {}
        if not isinstance(asks, dict):
            raise IdeasError("asks are the goal type's fields, by their ids")
        known = {a.id: a for a in (t.asks if t else ())}
        said: dict[str, str] = {}
        for ask_id, text in asks.items():
            if ask_id not in known and not (t and t.refs and ask_id == goal_types.REFS):
                raise IdeasError(f"{t.name} has no field “{ask_id}”" if t else "A goal with no type has no fields of its own")
            if not isinstance(text, str):
                raise IdeasError(f"“{ask_id}” is not text")
            if line := " ".join(text.split())[:goal_types.ASK_CHARS]:
                said[ask_id] = line
        lines = [f"{a.label}: {said[a.id]}" for a in (t.asks if t else ()) if a.id in said]
        if goal_types.REFS in said:
            lines.append(f"Refs: {said[goal_types.REFS]}")
        join = args.get("join")
        if join is not None and (not isinstance(join, dict) or not isinstance(join.get("add"), str)
                                 or not isinstance(join.get("out") or "", str)):
            raise IdeasError("join names the agent who joins, and who leaves")
        self.__dict__.setdefault("_offers", {})[track] = (len(got), sum(1 for _t, r in got if r))
        return {"key": t.id if t else "", "type": t, "lines": lines, "rows": rows, "join": join,
                "answered": sum(1 for a in (t.asks if t else ()) if a.id in said)}

    @staticmethod
    def with_asks(text: str, typed: dict) -> str:
        """The goal's words: its text, then each answered ask as a line `<label>: <text>` in the type's order."""
        return text + ("\n\n" + "\n".join(typed["lines"]) if typed["lines"] else "")

    def join_goal(self, track: str, typed: dict, args: dict) -> dict | None:
        """Who joins for a new goal of a type (§2.3), under `ideas.LOCK` with the goal's add: `add` one of the type's `missing`
        for this party, `out` one of its `out` (required when its band is full); the party changed. `{add, out}`, or None."""
        join, t = typed["join"], typed["type"]
        if not join:
            return None
        root = self.root()
        p = goal_types.Party(self.state_dir, root, track)
        add, out = join["add"].strip(), (join.get("out") or "").strip()
        row = next((r for r in typed["rows"] if r["agent"] == add), None)
        if row is None:
            raise IdeasError(f"{_name(add)} is not what this goal misses")
        if out and out not in p.band(row["band"]):
            raise IdeasError(f"{_name(out)} is not one of the party's {BANDS[row['band']]}")
        if out and out not in {o["slug"] for o in row["out"]}:
            raise IdeasError(f"{_name(out)} has work open: it cannot leave")
        if not out and not row["free"]:
            raise IdeasError("The party is full: pick who leaves")
        self._join(p, add, out, "type", args)
        return {"add": add, "out": out}

    def _join(self, p: goal_types.Party, add: str, out: str, via: str, args: dict) -> None:
        """The party changed as Edit the party changes it: `add` in `out`'s seat (else last), `out` out of the team and its
        every, the seats checked, the agent installed, the team kept; `goal_saved` with who joined, who left and `via`. The
        caller says the party changed (`changed("goal:<slug>")`) once out of the lock."""
        root = self.root()
        team = [add if s == out else s for s in p.team] if out else [*p.team, add]
        if why := goal_team.seats(team, p.leader):
            raise IdeasError(why)
        library.install(self.state_dir, [add])
        goal_team.set_team(root, p.slug, team, [s for s in goal_team.every_of(root, p.slug) if s != out])
        party_proposals.drop_left(root, self.state_dir, p.slug)
        g = next(x for x in ideas.tracks(root, make=False) if x["slug"] == p.slug)
        self._ev(event_log.GOAL_SAVED, args, goal=p.slug, new=False, metrics=[m["name"] for m in g["metrics"]], links=g["links"],
                 priority=g["priority"], craft=g["craft"], team=g["team"], every=g["every"], leader=g["leader"] or roles.TASKMASTER,
                 party=goal_team.party_of(root, p.slug), joined=add, out=out, via=via)

    # -- a plan that gives work to no one of the party (§2.6) -------------------------------------------------

    def plan_missing(self, slug: str, plan: dict | None) -> list[dict]:
        """A plan's `missing` read against its party now (the stop's line, the drawer's plan)."""
        root = self.root(False)
        page = ideas.idea_page(root, slug)
        if not plan or page is None:
            return []
        return goal_types.still_missing(self.state_dir, root, page.get("track") or ideas.GENERAL, plan.get("missing"))

    def start_join(self, slug: str, args: dict) -> dict:
        """`ideas.start`'s `join: {add}` (Add and start): `add` one of the plan's `missing` with a free seat; the party changed
        (`via: "plan"`), then the plan's tasks that have not run given their role again. What its `plan_passed` says: `{joined,
        missing}`, who joined and how many kinds the plan missed at the press (before the join)."""
        join = args.get("join")
        if join is not None and (not isinstance(join, dict) or not isinstance(join.get("add"), str)):
            raise IdeasError("join names the agent who joins")
        root = self.root()
        track = (ideas.idea_page(root, slug) or ideas.Page()).get("track") or ideas.GENERAL
        with ideas.LOCK:
            p = goal_types.Party(self.state_dir, root, track)
            rows = goal_types.still_missing(self.state_dir, root, track, (ideas.plan(self.state_dir, slug) or {}).get("missing"), read=p)
            if join is None:
                return {"joined": "", "missing": len(rows)}
            add = join["add"].strip()
            row = next((r for r in rows if r["agent"] == add), None)
            if row is None:
                raise IdeasError(f"{_name(add)} is not what this plan misses")
            if not row["free"]:
                raise IdeasError("The party is full: change a member in Edit the party")
            self._join(p, add, "", "plan", args)
            party = [*goal_team.team_of(root, track), p.leader]

            def again(plan: dict) -> None:
                for t in plan.get("tasks") or []:
                    if (t.get("state") or "waiting") in NOT_STARTED:
                        t["role"] = roles.role_for(self.state_dir, str(t.get("kind") or ""), party)["slug"]
            ideas.edit_plan(self.state_dir, slug, again)
        self.changed(f"goal:{track}")
        return {"joined": add, "missing": len(rows)}

    # -- the events (§2.7) ----------------------------------------------------------------------------------

    def type_fields(self, event: str, fields: dict) -> dict:
        """What specs 52 §2.7 and 59 §5 add to events written elsewhere: `idea_added` says how many types the party offered and how
        many of them with someone missing (`typed`), Edit the party's `goal_saved` says no one joined (`via` ""), the seats of its
        leader (`stages`) and the library's party it started from (`preset`), and every `plan_passed` says who joined at its press and how many kinds the plan missed (its `missing` read against
        the party then: before a join). `_passing`: what `ideas.start` read for its pass (`start_join`)."""
        if event == event_log.IDEA_ADDED:
            offered, near = self.__dict__.get("_offers", {}).pop(fields.get("track"), (0, 0))
            return {"offered": offered, "near": near}
        if event == event_log.GOAL_SAVED:
            seats = library.seats_of(fields.get("leader") or roles.TASKMASTER)
            return {"joined": fields.get("joined", ""), "out": fields.get("out", ""), "via": fields.get("via", ""),
                    "stages": f"{seats['build']}/{seats['check']}", "preset": fields.get("preset", "")}
        if event == event_log.PLAN_PASSED:
            slug = str(fields.get("idea") or "")
            got = self._passing.pop(slug, None)
            if got is None:
                try:
                    got = {"joined": "", "missing": len(self.plan_missing(slug, ideas.plan(self.state_dir, slug)))}
                except (OSError, ValueError):
                    got = {"joined": "", "missing": None}
            return got
        return {}
