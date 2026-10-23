"""The spec after the start (docs/specs/62-spec-after-start.md) as `gui/ideas.py`'s `Ideas` has it: `ideas.revise`, the person's press on
*Re-plan what is left* (the goal's leader proposes a plan change for the tasks not started: core/idea_revise.py) and `ideas.revise_answer`,
*Take the new plan* or *Keep the plan* (the runner applies it: core/idea_review.py `revise_tasks`). The plan change waits beside the plan
(realm/idea_change.py) and comes to the hand as one stop (realm/board_map.py). Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _str, _text, _via
from orkboard.realm import event_log, idea_change, ideas


class ReviseMixin:
    def revise(self, args: dict) -> dict:
        """`{"slug"}`: Re-plan what is left, in the background (the keeper's refusals are in words: no plan, not started, done, busy, the demo,
        the budget, a spent window). The goal's state does not change; the plan change comes to the hand as a stop."""
        slug = _text(args, "slug", 100)
        self.keeper.revise(slug)
        self.changed(slug)
        return {"ok": True}

    def revise_answer(self, args: dict) -> dict:
        """`{"slug", "take", "via"?}`: Take the new plan (the runner applies the plan change under its lock; the goal's Stages are written again)
        or Keep the plan (the plan as it was). Either way the plan change is dropped and `changed` cleared. Answers `{ok, added, changed, dropped,
        left}`: counts, and the titles of the tasks the change named that had started meanwhile (zeros when kept)."""
        slug = _text(args, "slug", 100)
        take = args.get("take")
        if not isinstance(take, bool):
            raise IdeasError("take is true or false")
        with ideas.LOCK:                             # claimed: a second press finds none waiting
            plan = ideas.plan(self.state_dir, slug)
            change = idea_change.live(self.state_dir, slug, plan, self._state(slug)["state"])
            if change is None:
                raise IdeasError("No plan change waits for this goal")
            if self.keeper.busy(slug):
                raise IdeasError("The keeper is busy with this goal: a moment")
            runner = self.runner(need=True) if take else None
            idea_change.drop(self.state_dir, slug)
        proposed = idea_change.summary(change, plan)
        got = {"added": 0, "changed": 0, "dropped": 0, "left": []}
        if take:
            try:
                got = runner.revise_tasks(slug, change)
            except Exception:
                idea_change.write(self.state_dir, slug, change)       # it did not apply: it waits as it did
                raise
            now = ideas.plan(self.state_dir, slug) or {}
            self.keeper.write_stages(slug, {**now, "tasks": idea_change.in_order(now.get("tasks") or [])})
        idea_change.clear(self.state_dir, slug)
        said = got if take else proposed
        self._ev(event_log.PLAN_CHANGE_ANSWERED, args, idea=slug, take=take, added=said["added"], changed_n=said["changed"],
                 dropped=said["dropped"], left=len(got["left"]), via=_via(args))
        self.changed(slug)
        return {"ok": True, **got}

    def after_start(self, slug: str, plan: dict | None, st: dict) -> dict:
        """What the page adds for the spec after the start: `changed` (the plan-making sections written since the plan, `[]` when none),
        `passed` (the plan is passed) and `change` (the plan change that waits, as its summary, else `null`)."""
        return {"changed": idea_change.changed_of(st), "passed": bool((plan or {}).get("passed_at")),
                "change": idea_change.shown(self.state_dir, slug, plan, st["state"])}

    def edited(self, args: dict, slug: str) -> None:
        """A section written by hand (`ideas.edit`): its text set, `changed` kept when it makes a plan and its text differs, and `idea_edited`."""
        section, text = _text(args, "section", 60), _str(args, "text", ideas.SECTION_CHARS)
        idea_change.set_section(self.root(), self.state_dir, slug, section, text)
        plan = ideas.plan(self.state_dir, slug)
        self._ev(event_log.IDEA_EDITED, args, idea=slug, section=section, chars=len(text), passed=bool(plan and plan.get("passed_at")))

    def settle_change(self, slug: str) -> None:
        """From the bus, whenever a goal changed: a plan change that cannot be taken any more (the goal is done, its plan was made again,
        every task it names has started and it adds nothing) is dropped by itself (spec 62 §3.3)."""
        idea_change.settle(self.state_dir, slug)
