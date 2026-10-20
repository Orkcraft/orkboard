"""Agents: the roles and the task type of each (spec 34 §3, §4), as `gui/ideas.py`'s `Ideas` has them:
`ideas.agents`, `ideas.roles`, `ideas.role_save`, `ideas.role_add` (one of the library's), `ideas.role_drop`,
`ideas.kind_set`; what each costs and how often it gets it right (spec 36 §2: each role's `week`; spec 41 §8: about what a
task of it costs, `usd_task`), what the built-in two are told already (`told`), and `ideas.spend`, an idea's or a goal's
money by stage.

A role is a small file in the repository's `.orkcraft/roles/` (realm/roles.py); the runner runs a task as its type's
role (core/idea_runner.py). Each role, each chip, carries the head the page draws for it (`head`: its craft's race at the
tier it runs at, realm/roles.py `head`; decisions §53). Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

import datetime as dt

from orkboard.gui.ideas_args import IdeasError, _device, _opt, _text
from orkboard.realm import board_map, event_log, idea_spend, idea_target, ideas, library, party_work, roles
from orkboard.realm.idea_words import short_of


RECORD_DAYS = 30                   # an agent's record: the last 30 days (spec 42 §4)
CHECK_WEEK = 7                     # a checker's check, the muted line under its name: the last 7 days (spec 43 §4.1)


class RolesMixin:
    def _target(self) -> str:
        return idea_target.target_of(self.board_settings())

    def _with_heads(self, plan: dict | None) -> dict | None:
        """A plan as the page reads it: each task with the head of who does it (`head`: race and tier, realm/roles.py) and
        its tag in words (`tag`: the kind of work it is)."""
        if not plan:
            return plan
        target, read = self._target(), roles.known(self.state_dir)
        return {**plan, "tasks": [{**t, "head": roles.task_head(self.state_dir, t, target, read),
                                   "tag": roles.KIND_LABELS.get(str(t.get("kind") or ""), roles.KIND_LABELS[roles.DEFAULT_KIND])}
                                  for t in plan.get("tasks") or []]}

    def _role_spend(self) -> dict[str, float]:
        """Today's cost of each role: the tasks it ran today, summed."""
        pairs = [(str(t.get("role") or roles.GRUNT), t) for _s, _title, plan in self._plans() for t in plan.get("tasks") or []]
        return roles.spend_today(pairs)

    def _usd_task(self, r: dict, week: dict, costs: dict, target: str) -> float | None:
        """About what a task of this agent costs (spec 41 §8): its week's spend by its tasks that ended, from
        `idea_spend.TOO_FEW` of them on; else a task's at its head's tier. None for the Taskmaster (its cost is its
        steps) and while nothing is priced."""
        if r["slug"] == roles.TASKMASTER:
            return None
        mine = week.get(r["slug"]) or {}
        if mine.get("spent") is not None and int(mine.get("finished") or 0) >= idea_spend.TOO_FEW:
            return round(float(mine["spent"]) / int(mine["finished"]), 2)
        usd = costs.get(roles.head(r, target)["tier"])
        return round(float(usd), 2) if usd is not None else None

    @staticmethod
    def _record(row: dict | None, slug: str) -> dict | None:
        """What an agent did in the last 30 days (spec 42 §4): its row of `idea_spend.by_role`, in the shape the dialog reads; the
        Taskmaster's counts its plans and the tasks of them."""
        if row is None:
            return None
        if slug == roles.TASKMASTER:
            return {"days": RECORD_DAYS, **{k: row.get(k, 0) for k in ("plans", "finished", "first_time")}}
        return {"days": RECORD_DAYS, **{k: row.get(k) for k in ("finished", "merged", "first_time", "usd_per_merged")}}

    def _checker_record(self, slug: str, days: int) -> dict | None:
        """A checker's check over the last `days` (realm/party_work.py `check_record`); None for an agent that brings no check."""
        a = library.get(slug)
        return party_work.check_record(self.root(False), self.state_dir, slug, days) if a is not None and a.check is not None else None

    def _with_check(self, record: dict | None, slug: str) -> dict | None:
        """An agent's record with its check of the last 30 days when it is a checker (spec 43 §4.1); a checker with no task has the record
        of its check alone."""
        check = self._checker_record(slug, RECORD_DAYS)
        if check is None:
            return record
        return {**(record or {"days": RECORD_DAYS}), "check": check}

    def roles(self, args: dict) -> dict:
        spent, week, kinds = self._role_spend(), idea_spend.by_role(self.state_dir), roles.kinds(self.state_dir)
        record = idea_spend.by_role(self.state_dir, days=RECORD_DAYS)
        target, costs = self._target(), idea_spend.tier_costs(self.state_dir)
        mine = [{**r, "spend_today": spent.get(r["slug"], 0.0), "week": week.get(r["slug"]),
                 "kinds": [k for k, v in kinds.items() if v == r["slug"]], "hand_model": roles.hand_set(r),
                 "head": roles.head(r, target), "record": self._with_check(self._record(record.get(r["slug"]), r["slug"]), r["slug"]),
                 "usd_task": self._usd_task(r, week, costs, target),
                 **({"check_week": c} if (c := self._checker_record(r["slug"], CHECK_WEEK)) is not None else {}),
                 **({"told": roles.TOLD[r["slug"]]} if r["slug"] in roles.TOLD else {})}
                for r in roles.roles(self.state_dir)]
        have = {r["slug"] for r in mine}
        return {"roles": mine, "kinds": [{"kind": k, "label": roles.KIND_LABELS[k], "role": kinds[k]} for k in roles.TASK_KINDS],
                "models": roles.models(), "target": target,
                "crafts": [{"craft": c, "label": roles.CRAFT_LABELS[c], "race": roles.RACES[c],
                            "heads": {m["id"]: roles.head_tier(m["id"], target) for m in roles.models()}} for c in roles.CRAFTS],
                "library": [{**a, "installed": a["id"] in have} for a in library.listed()],
                "suggested": library.SUGGESTED, "seats": library.SEATS,
                "parties": library.parties(),
                "tier_costs": costs}                     # $ a task per tier: what a check adds to an idea

    def role_save(self, args: dict) -> dict:
        slug = _opt(args, "slug") or None
        instruction = args.get("instruction", "")
        if not isinstance(instruction, str):
            raise IdeasError("instruction is not text")
        kinds = args.get("kinds")
        if kinds is not None and (not isinstance(kinds, list) or not all(isinstance(k, str) for k in kinds)):
            raise IdeasError("kinds is a list of task types")
        craft = args.get("craft")
        if craft is not None and not isinstance(craft, str):
            raise IdeasError("craft is engineering, design, data or marketing")
        got = roles.save(self.state_dir, _text(args, "name", roles.NAME_CHARS), args.get("model", ""),
                         args.get("max_parallel"), instruction, slug, kinds, craft)
        r = roles.role(self.state_dir, got)
        idea_spend.forget()
        self._ev(event_log.ROLE_SAVED, args, role=got, model=r["model"], max_parallel=r["max_parallel"], new=slug is None, craft=r["craft"],
                 kinds=[k for k, v in roles.kinds(self.state_dir).items() if v == got], instruction_chars=len(instruction.strip()))
        self.changed("")
        return {"slug": got}

    def role_add(self, args: dict) -> dict:
        """An agent of the library made a role of this project (spec 41 §8, Add agent → From the library)."""
        agent = _text(args, "id", 100)
        if library.get(agent) is None:
            raise IdeasError(f"No agent {agent!r} in the library")
        if roles.role(self.state_dir, agent) is not None:
            raise IdeasError(f"{library.get(agent).name} is already this project's")
        (got,) = library.install(self.state_dir, [agent])
        r = roles.role(self.state_dir, got)
        self._ev(event_log.ROLE_SAVED, args, role=got, model=r["model"], max_parallel=r["max_parallel"], new=True, craft=r["craft"],
                 kinds=[k for k, v in roles.kinds(self.state_dir).items() if v == got], instruction_chars=len(r["instruction"]),
                 library=True)
        self.changed("")
        return {"slug": got}

    def role_drop(self, args: dict) -> dict:
        slug = _text(args, "slug", 100)
        back = roles.drop(self.state_dir, slug)
        self._ev(event_log.ROLE_DROPPED, args, role=slug, kinds=back)
        self.changed("")
        return {"ok": True}

    def kind_set(self, args: dict) -> dict:
        kind, role = _text(args, "kind", 40), _text(args, "role", 100)
        roles.set_kind(self.state_dir, kind, role)
        self._ev(event_log.KIND_SET, args, kind=kind, role=role)
        self.changed("")
        return {"ok": True}

    def spend(self, args: dict) -> dict:
        """`ideas.spend` (spec 36 §4): an idea's money by stage (`{"idea"}`), or a goal's with its ideas' (`{"goal"}`)."""
        if idea := _opt(args, "idea"):
            if ideas.idea_page(self.root(), idea) is None and not (self.state_dir / "ideas" / idea).is_dir():
                raise IdeasError("That idea is gone")
            return idea_spend.of_idea(self.state_dir, idea)
        goal = _text(args, "goal", 100)
        if ideas.track_page(self.root(), goal) is None:
            raise IdeasError("That goal is gone")
        return idea_spend.of_goal(self.state_dir, goal, [i["slug"] for i in ideas.ideas(self.root(), goal)])

    def agents(self, args: dict) -> dict:
        """The Agents window: a block per role — the Taskmaster (the keeper, with what it does now), the Grunt and the
        person's own — each with a chip per live task of the types it has."""
        board = self.board(make=False)
        titles = {i["slug"]: i["title"] for i in board["ideas"]}
        shorts = {i["slug"]: i["short"] for i in board["ideas"]}
        chips, waits, mode = [], None, "waiting"
        for i in board["ideas"]:
            busy = self.keeper.busy(i["slug"])
            if i["state"] in ("reading", "planning") or busy:
                state = "planning" if i["state"] == "planning" else ("reading" if i["state"] == "reading" else "talking")
                chips.append({"idea": i["slug"], "title": i["title"], "short": i["short"], "state": state})
            elif i["state"] == "asks":
                chips.append({"idea": i["slug"], "title": i["title"], "short": i["short"], "state": "waiting"})
                waits = waits or {"idea": i["slug"], "text": f"waiting for your answers on “{i['title']}”"}
        for g in board["tracks"]:
            if self.keeper.busy_goal(g["slug"]):
                chips.append({"idea": "", "goal": g["slug"], "title": g["title"], "short": g["short"], "state": "reading"})
        for rank in ("planning", "reading", "talking"):
            if any(c["state"] == rank for c in chips):
                mode = rank
                break
        by_role: dict[str, list] = {}
        done, today = [], dt.date.today().isoformat()
        target, read = board.get("target") or self._target(), roles.known(self.state_dir)
        for slug, title, plan in self._plans():
            for t in plan.get("tasks") or []:
                state, role = t.get("state"), str(t.get("role") or roles.GRUNT)
                if state == "merged" and str(t.get("finished") or "").startswith(today):
                    done.append({"idea": slug, "task": t.get("id"), "title": t.get("title", ""), "role": role})
                elif state in ("running", "testing", "review", "ready", "held", "failed"):
                    by_role.setdefault(role, []).append(
                        {"idea": slug, "idea_title": titles.get(slug, title),
                         "idea_short": shorts.get(slug) or short_of(title), "task": t.get("id"),
                         "title": t.get("title", ""), "short": board_map.task_short(t), "state": state, "tier": t.get("tier", ""), "role": role,
                         "kind": t.get("kind") or roles.DEFAULT_KIND, "head": roles.task_head(self.state_dir, t, target, read),
                         "tag": roles.KIND_LABELS.get(str(t.get("kind") or ""), roles.KIND_LABELS[roles.DEFAULT_KIND]),
                         "note": t.get("note") or (t.get("error") if state == "failed" else "") or "",
                         # spec 35 §11.5: who started it, and whether it waits for the night
                         "by": "auto" if plan.get("passed_by") == "auto" else "person",
                         "night": plan.get("start_at") == "night" and not t.get("started")})
        spent, week, out = self._role_spend(), idea_spend.by_role(self.state_dir), []
        costs = idea_spend.tier_costs(self.state_dir)
        for r in roles.roles(self.state_dir):
            block = {"role": r["slug"], "name": "Grunts" if r["slug"] == roles.GRUNT and r["name"] == "Grunt" else r["name"],
                     "model": r["model"], "max_parallel": r["max_parallel"], "builtin": r["builtin"],
                     "spend_today": spent.get(r["slug"], 0.0), "week": week.get(r["slug"]), "head": roles.head(r, target),
                     "usd_task": self._usd_task(r, week, costs, target),
                     **({"check_week": c} if (c := self._checker_record(r["slug"], CHECK_WEEK)) is not None else {})}
            if r["slug"] == roles.TASKMASTER:
                out.append({**block, "state": mode, "waits_on": waits, "chips": chips})
            else:
                out.append({**block, "chips": by_role.pop(r["slug"], []),
                            "kinds": [k for k, v in roles.kinds(self.state_dir).items() if v == r["slug"]]})
        if by_role and out:                              # tasks of a role that was dropped since: Grunt's
            grunt = next(b for b in out if b["role"] == roles.GRUNT)
            grunt["chips"] += [c for cs in by_role.values() for c in cs]
        return {"roles": out, "done_today": done}
