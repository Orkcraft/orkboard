"""The spec after the start (docs/specs/62-spec-after-start.md): a goal's plan is passed and its work is under way, and its
spec changed. The person presses *Re-plan what is left*; the goal's leader looks at what is left and proposes a plan change: the
tasks not started changed, dropped or added, the tasks at work and the merged ones left as they are. It is saved beside the plan
(realm/idea_change.py) and comes to the hand as one stop; the runner applies it when the person takes it
(core/idea_review.py `revise_tasks`). A mixin of `IdeaKeeper`, as `idea_draft.py` is.

    keeper.revise(slug)               # in the background: refused in words, then `revise_one`
    keeper.revise_one(slug)           # the same, on this thread: one call on the `plan` step, one shot, read-only
    keeper.revise_prompt(root, slug)  # the spec, what changed, what is done, at work and not started
    clean_change(plan, answer)        # the leader's answer, strictly: only what can still change

Nothing is applied here and no task is touched: the keeper never writes a passed plan (`ideas.save_plan` refuses it). `self` has
the keeper's `ask`, `parse`, `wiki_root`, `state_dir`, `_start`, `_may_run`, `busy`, `refuse_spent`, `publish`, `_ev`, `measure`,
`reads`, `target`, `role_of`, `team_lines`, `team_checks`, `idea_checks`.
"""
from __future__ import annotations

import json
from pathlib import Path

from orkboard.core.idea_plan import _why, estimate
from orkboard.realm import event_log, goal_team, goal_types, idea_change, idea_checks, idea_lens, idea_spend, idea_target, ideas, releases, roles
from orkboard.realm.idea_words import short_of, short_said

SPEC_SHARE = 0.5                   # of the `plan` context, the most the spec takes: the tasks' part gets the rest
BRIEF_AT_WORK = 300                # of a task at work, the characters of its brief the leader reads
BRIEF_NOT_STARTED = 4000           # of the tasks not started, the characters of their briefs together (each at least 300)


def _kw():
    from orkboard.core import idea_keeper
    return idea_keeper


def is_check(task: dict) -> bool:
    """A check task: its `kind` is a checker's tag (core/idea_task.py `is_check`; the keeper imports none of the runner's modules)."""
    return str(task.get("kind") or "") in idea_checks.TAGS


def _cut(text: object, limit: int) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def clean_change(plan: dict, answer: dict | None) -> dict:
    """The leader's answer as a plan change, strictly (spec 62 §2.2): `change` and `drop` name only tasks not started (never a
    check task: the team's check stays); an unknown id, a task that started meanwhile, a `change` that changes nothing: left out.
    A changed task keeps the fields the leader did not give. `add` is at most the plan's MAX_TASKS, its `key` renamed n1, n2….
    An `after` names a task of the plan that stays (a check task excepted) or an added task by its key; one that names nothing or
    closes a cycle is left out, the rest is kept. `{why, change, drop, add}`."""
    kw = _kw()
    if not isinstance(answer, dict):
        raise kw.KeeperError("the keeper's answer was not a plan change")
    tasks = {str(t.get("id")): t for t in plan.get("tasks") or [] if isinstance(t, dict) and t.get("id")}
    free = [i for i, t in tasks.items() if idea_change.open_task(t) and not is_check(t)]
    drop = [i for i in dict.fromkeys(kw._strings(answer.get("drop"), len(tasks), 20)) if i in free]
    graph = {i: [a for a in t.get("after") or [] if a in tasks and a not in drop] for i, t in tasks.items() if i not in drop}
    raw_add = [r for r in answer.get("add") if isinstance(r, dict)] if isinstance(answer.get("add"), list) else []
    adding = [r for r in raw_add if kw._words(r.get("title"), 200) and kw._words(r.get("brief"), 6000)][:kw.MAX_TASKS]
    keys: dict[str, str] = {}
    for n, raw in enumerate(adding, start=1):
        keys.setdefault(kw._words(raw.get("key"), 20) or f"n{n}", f"n{n}")
    graph.update({key: [] for key in keys.values()})
    for tid, t in tasks.items():                      # a check task not started waits for the added tasks too (core/idea_review.py)
        if is_check(t) and idea_change.open_task(t) and tid in graph:
            graph[tid] = [*graph[tid], *keys.values()]

    def after_of(raw: dict, own: str, fallback: list[str]) -> list[str]:
        if not isinstance(raw.get("after"), list):
            return list(fallback)
        wanted = [a if a in tasks else keys.get(a, "") for a in kw._strings(raw["after"], 20, 20)]
        return idea_change.safe_after(graph, own, [a for a in wanted if a and not (a in tasks and is_check(tasks[a]))])

    def kind_of(raw: dict, old: str) -> str:
        kind = raw.get("kind")
        return kind if kind in roles.TASK_KINDS and kind not in idea_checks.TAGS else old

    changes, seen = [], set()
    for raw in answer.get("change") if isinstance(answer.get("change"), list) else []:
        tid = kw._words(raw.get("id"), 20) if isinstance(raw, dict) else ""
        if tid not in free or tid in drop or tid in seen:
            continue
        seen.add(tid)
        old = tasks[tid]
        was = {"title": str(old.get("title") or ""), "short": str(old.get("short") or short_of(str(old.get("title") or ""))),
               "brief": str(old.get("brief") or ""), "kind": str(old.get("kind") or roles.DEFAULT_KIND),
               "tier": str(old.get("tier") or "warrior"), "after": list(graph[tid])}
        title = kw._words(raw.get("title"), 200) or was["title"]
        short = short_said(raw.get("short"), title) if raw.get("short") else (was["short"] if title == was["title"] else short_of(title))
        row = {"title": title, "short": short, "brief": kw._words(raw.get("brief"), 6000) or was["brief"],
               "kind": kind_of(raw, was["kind"]), "tier": raw.get("tier") if raw.get("tier") in kw.TIERS else was["tier"],
               "after": after_of(raw, tid, was["after"])}
        if any(set(row[k]) != set(was[k]) if k == "after" else row[k] != was[k] for k in row):
            changes.append({"id": tid, **row})
    added = []
    for n, raw in enumerate(adding, start=1):
        title = kw._words(raw.get("title"), 200)
        added.append({"key": f"n{n}", "title": title, "short": short_said(raw.get("short"), title),
                      "brief": kw._words(raw.get("brief"), 6000), "kind": kind_of(raw, roles.DEFAULT_KIND),
                      "tier": raw.get("tier") if raw.get("tier") in kw.TIERS else "warrior", "after": after_of(raw, f"n{n}", [])})
    return {"why": " ".join(kw._words(answer.get("why"), 300).split()), "change": changes, "drop": drop, "add": added}


class ReviseMixin:
    def revise(self, slug: str) -> None:
        """*Re-plan what is left*, in the background (busy *planning*, as Re-plan; the goal's state does not change). Refused in
        words for a goal with no plan, one not started, one done, one the keeper is busy with, and as `plan()` refuses (the demo, the
        budget, a spent window)."""
        kw = _kw()
        if ideas.idea_page(self.wiki_root(), slug) is None:
            raise kw.KeeperError("That goal is gone")
        plan = ideas.plan(self.state_dir, slug)
        if plan is None:
            raise kw.KeeperError("This goal has no plan yet")
        if not plan.get("passed_at"):
            raise kw.KeeperError("Its plan is not started: Re-plan it")
        if ideas.state(self.state_dir, slug)["state"] == "done":
            raise kw.KeeperError("This goal is done")
        if self.busy(slug):
            raise kw.KeeperError("The keeper is busy with this goal: a moment")
        if why := self._may_run():
            raise kw.KeeperError(why)
        self.refuse_spent()
        self._start(slug, "planning", lambda: self.revise_one(slug))

    def plan_team(self, root: Path, slug: str) -> list[str]:
        """The goal's team as the plan gives its tasks their roles: the party and its leader (who does the tags no builder does)."""
        team = goal_team.for_idea(root, slug)
        if team and (lead := goal_team.leader_of(root, (ideas.idea_page(root, slug) or ideas.Page()).get("track") or "")) not in team:
            team = [*team, lead]
        return team

    def revise_prompt(self, root: Path, slug: str) -> str:
        """§0's `plan` context, and three parts more (spec 62 §2.2): what changed; what is done and at work, which stay as they are; the
        tasks not started, as the plan wrote them. The spec is cut to SPEC_SHARE of the context, the tasks' part gets the rest."""
        kw = _kw()
        page = ideas.idea_page(root, slug)
        plan = ideas.plan(self.state_dir, slug) or {}
        tasks = [t for t in plan.get("tasks") or [] if isinstance(t, dict)]
        track = page.get("track") or ideas.GENERAL
        goal = next((t for t in ideas.tracks(root, make=False) if t["slug"] == page.get("track")), None)
        changed = idea_change.changed_of(ideas.state(self.state_dir, slug))
        saying = f"These sections changed since the plan: {', '.join(changed)}." if changed else "The person asked to look again."
        decisions = "\n".join(page.section("Decisions").splitlines()[-10:])
        done = [t for t in tasks if t.get("state") == "merged"]
        failed = [t for t in tasks if t.get("state") == "failed"]
        todo = [t for t in tasks if idea_change.open_task(t)]
        at_work = [t for t in tasks if t not in done and t not in failed and t not in todo]
        each = max(300, BRIEF_NOT_STARTED // max(1, len(todo)))
        rows = [{"id": t.get("id"), "title": t.get("title"), "short": t.get("short") or short_of(str(t.get("title") or "")),
                 "brief": _cut(t.get("brief"), each), "kind": t.get("kind"), "tier": t.get("tier"), "after": t.get("after") or [],
                 **({"check": True} if is_check(t) else {})} for t in todo]
        cap = idea_target.CONTEXT["plan"]
        spec = idea_target.cut([*((n, page.section(n)) for n in idea_change.PLAN_SECTIONS),
                                ("Its goal's summary", goal["summary"] if goal else "")], int(cap * SPEC_SHARE))
        work = idea_target.cut([
            ("What changed", f"{saying}\nThe last decisions:\n{decisions or '(none)'}"),
            ("Done (these stay as they are)", "\n".join(f"{t.get('id')} {t.get('title')}" for t in done)),
            ("At work (these stay as they are)", "\n".join(f"{t.get('id')} {t.get('title')}: {_cut(t.get('brief'), BRIEF_AT_WORK)}" for t in at_work)),
            *([("Failed (these stay as they are)", "\n".join(f"{t.get('id')} {t.get('title')}" for t in failed))] if failed else []),
            ("Not started", "\n".join(json.dumps(r, ensure_ascii=False) for r in rows))], cap - len(spec))
        touches = [t for t in json.loads(page.get("touches") or "[]") if isinstance(t, str)] if page.get("touches", "").startswith("[") else []
        kinds = "; ".join(f'"{k}" ({roles.KIND_LINES[k]})' for k in roles.TASK_KINDS if k not in idea_checks.TAGS)
        party = goal_team.team_of(root, track)
        if party:
            party = [*party, goal_team.leader_of(root, track)]
        team = self.team_lines([s for s in dict.fromkeys(party) if s != roles.TASKMASTER])
        checks = idea_checks.plan_lines(self.idea_checks(root, slug), self.team_checks(root, slug))
        return f"""You are the keeper of this project's Task board. This goal's plan is passed and its work is under way, and its spec
changed. Look at what is left and propose a plan change: which tasks not started change, which are dropped, which are added. You
may read the repository (read only) to see what the work touches. {self.reads("plan", touches)}
{idea_lens.attached(self.state_dir, slug)}{goal_types.prompt_line(self.state_dir, slug)}{releases.prompt_lines(root, self.state_dir, slug)}{checks}
The spec: {page.title}
{spec}{work}
Rules:
- Done, At work and Failed stay as they are: never change, drop or redo a task there. Only a task in Not started may change or be
  dropped, by its id; a task you name in neither `change` nor `drop` stays as it is. A task marked "check" stays too: it waits
  for every other task, the new ones included.
- Change a task only when the spec's change reaches it: give its whole new brief, not a patch. Drop one only when the spec no
  longer needs it. Add a task only for work the spec now needs that no task covers (at most {kw.MAX_TASKS}); each is a brief another
  Claude session can do alone, in a worktree of the repository: what to change, where, and how it is tested.
- Each task's tag (`kind`), the kind of work it is, one of: {kinds}. Ordinary work is "code".{team}
- Each task's tier, its complexity: "elder" (hard design or a wide change), "warrior" (ordinary code), "laborer" (small, mechanical).
- `after`: the ids of the tasks a task needs the result of (any task above but a check, or an added task by its `key`); none that
  makes two tasks wait for each other.
- If nothing needs to change, answer with empty lists.

Answer with one JSON object and nothing else:
{{"why": "one line to the person: what you change and why",
 "change": [{{"id": "k4", "title": "…", "short": "two or three words, 24 characters at most", "brief": "…", "kind": "code",
             "tier": "warrior", "after": []}}],
 "drop": ["k5"],
 "add": [{{"key": "n1", "title": "…", "short": "two or three words, 24 characters at most", "brief": "…", "kind": "code",
          "tier": "warrior", "after": ["k2"]}}]}}
"""

    def change_price(self, plan: dict, got: dict) -> dict:
        """What the plan change adds to the plan's price, or, when it saves, takes from it (spec 62 §2.3): the added tasks and the changed
        ones as they will be, less the dropped ones and the changed ones as they were; priced as `plan_one` prices a plan (the tiers the tasks
        will run on, at what the board's last tasks on each cost). `{usd_low, usd_high}`, negative when it saves."""
        target, costs = self.target(), idea_spend.tier_costs(self.state_dir)
        old = {str(t.get("id")): t for t in plan.get("tasks") or [] if isinstance(t, dict)}

        def priced(tasks: list[dict]) -> dict:
            runs = [idea_target.tier_of(idea_target.task_pick(str(t.get("tier") or "warrior"), target,
                                                              str(self.role_of(t).get("model") or ""))[0]) for t in tasks]
            return estimate(tasks, runs, costs)

        plus = priced([*got["add"], *got["change"]])
        minus = priced([*(old[i] for i in got["drop"] if i in old), *(old[c["id"]] for c in got["change"] if c["id"] in old)])
        return {k: round(plus[k] - minus[k], 2) or 0.0 for k in ("usd_low", "usd_high")}

    def revise_one(self, slug: str) -> None:
        """The plan change, one shot: the leader's answer cleaned against the plan as it is now (a task that started while it thought is
        left out), the roles of its tasks given as `plan_one` gives them, its price; saved beside the plan. A failure is the goal's
        `error` (*No plan change: …*) and nothing is saved."""
        root = self.wiki_root()
        try:
            text, *_rest = self.ask("plan", self.revise_prompt(root, slug))
            plan = ideas.plan(self.state_dir, slug) or {}
            got = clean_change(plan, self.parse(text))
            team = self.plan_team(root, slug)
            for row in [*got["change"], *got["add"]]:
                row["role"] = roles.role_for(self.state_dir, row["kind"], team)["slug"] if team else ""
            got["changed"] = idea_change.changed_of(ideas.state(self.state_dir, slug))
            got["estimate"] = self.change_price(plan, got)
            with ideas.LOCK:
                if not (ideas.plan(self.state_dir, slug) or {}).get("passed_at"):
                    raise _kw().KeeperError("its plan is not started")
                saved = idea_change.write(self.state_dir, slug, got)
        except Exception as e:
            if not isinstance(e, InterruptedError):
                ideas.save_state(self.state_dir, slug, error=f"No plan change: {_why(e)}")
            self.publish(slug)
            return
        if str(ideas.state(self.state_dir, slug)["error"]).startswith("No plan change"):
            ideas.save_state(self.state_dir, slug, error="")
        shown = idea_change.summary(saved, ideas.plan(self.state_dir, slug))
        self._ev(event_log.PLAN_REVISED, idea=slug, changed=saved["changed"], added=shown["added"], changed_n=shown["changed"],
                 dropped=shown["dropped"], usd_low=shown["usd_low"], usd_high=shown["usd_high"], **self.measure())
        self.publish(slug)
