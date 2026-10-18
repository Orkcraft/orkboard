"""Review, Agents and one task (spec 33 §5), as `gui/ideas.py`'s `Ideas` has them: the results waiting for the person
(`ideas.review_list`, `ideas.diff`), their three answers (`ideas.merge`, `ideas.back`, `ideas.drop_task`),
`ideas.stop_task`, one task with its log (`ideas.task`) and the branch results merge into (`ideas.into`, the project's
own setting: spec 37 §8). Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

from pathlib import Path

from orkboard import settings
from orkboard.gui.ideas_args import IdeasError, _device, _text
from orkboard.realm import event_log, idea_spend, ideas
from orkboard.realm.idea_git import IdeaGit

_NO_TESTS = {"passed": 0, "failed": 0, "failing": [], "tail": ""}


class ReviewMixin:

    def _into(self) -> str:
        return str(self.settings_now().get("merge_into") or settings.IDEAS["merge_into"])

    def _plans(self) -> list[tuple[str, str, dict]]:
        """(slug, title, plan) of every idea that has a plan, in the board's order."""
        out = []
        for i in ideas.ideas(self.root()):
            plan = ideas.plan(self.state_dir, i["slug"])
            if plan:
                out.append((i["slug"], i["title"], plan))
        return out

    def results(self) -> list[dict]:
        """The results waiting at Review, oldest first; each with its cost split (work, rework) and against its
        planned share (`estimate`, `over`: spec 36 §4)."""
        out, costs = [], idea_spend.tier_costs(self.state_dir)
        for slug, title, plan in self._plans():
            split = None
            for t in plan.get("tasks") or []:
                if t.get("state") == "review":
                    split = split or idea_spend.of_idea(self.state_dir, slug)["tasks"]
                    est = idea_spend.estimate_of(t, costs)
                    out.append({"idea": slug, "idea_title": title, "task": t.get("id"), "title": t.get("title", ""),
                                "round": int(t.get("round") or 1), "tests": t.get("tests") or _NO_TESTS,
                                "diff": t.get("diff") or {"files": 0, "added": 0, "removed": 0},
                                "cost": t.get("cost"), "conflict": t.get("conflict") or "",
                                "finished": t.get("finished") or "",
                                "work": (split.get(t.get("id")) or {}).get("work"),
                                "rework": (split.get(t.get("id")) or {}).get("rework"),
                                "estimate": est, "over": idea_spend.over(t.get("cost"), est)})
        return sorted(out, key=lambda r: r["finished"])

    def review_list(self, args: dict) -> dict:
        m = self.settings_now()
        try:
            branches = IdeaGit(Path(self.host.repo_root)).branches()
        except Exception:                       # not a git folder yet: the picker offers only the current branch
            branches = []
        into = self._into()
        return {"into": into, "push": bool(m.get("push", settings.IDEAS["push"])),
                "branches": branches if into in branches else [into, *branches], "results": self.results()}

    def _task(self, args: dict) -> tuple[str, str, dict, dict]:
        slug, tid = _text(args, "slug", 100), _text(args, "task", 40)
        plan = ideas.plan(self.state_dir, slug)
        task = next((t for t in (plan or {}).get("tasks") or [] if t.get("id") == tid), None)
        if task is None:
            raise IdeasError("That task is gone")
        return slug, tid, task, plan

    def diff(self, args: dict) -> dict:
        _slug, _tid, task, _plan = self._task(args)
        branch = str(task.get("branch") or "")
        if not branch:
            raise IdeasError("That task has no code yet")
        git = IdeaGit(Path(self.host.repo_root))
        try:
            got = git.diff(branch, str(task.get("base") or self._into()))
        except Exception as e:
            raise IdeasError("Its code cannot be read: " + " ".join(str(e).split())[:200]) from None
        return {**got, "base": self._into()}

    def merge(self, args: dict) -> dict:
        slug, tid, _task, _plan = self._task(args)
        dear = args.get("dear", False)
        if not isinstance(dear, bool):
            raise IdeasError("dear is true or false")
        commit = self.runner(need=True).merge(slug, tid, device=_device(args), **({"dear": True} if dear else {}))
        self.changed(slug)
        return {"ok": True, "commit": commit}

    def back(self, args: dict) -> dict:
        slug, tid, _task, _plan = self._task(args)
        self.runner(need=True).back(slug, tid, _text(args, "why", 1000), device=_device(args))
        self.changed(slug)
        return {"ok": True}

    def drop_task(self, args: dict) -> dict:
        slug, tid, _task, _plan = self._task(args)
        self.runner(need=True).drop_task(slug, tid, device=_device(args))
        self.changed(slug)
        return {"ok": True}

    def stop_task(self, args: dict) -> dict:
        slug, tid, _task, _plan = self._task(args)
        self.runner(need=True).stop_task(slug, tid, device=_device(args))
        self.changed(slug)
        return {"ok": True}

    def task(self, args: dict) -> dict:
        slug, tid, task, plan = self._task(args)
        page = ideas.idea_page(self.root(), slug)
        runner = self._runner
        return {**task, "idea": slug, "idea_title": (page.title if page else "") or slug,
                "log": runner.log(slug, tid) if runner is not None else "",
                "after": task.get("after") or [], "round": int(task.get("round") or 1)}

    def into(self, args: dict) -> dict:
        """The branch results merge into (made from the default branch when missing) and whether it is pushed."""
        branch, push = args.get("branch"), args.get("push")
        if branch is None and not isinstance(push, bool):
            raise IdeasError("branch is missing")
        mine = dict(self.settings_now())
        if branch is not None:
            name = _text(args, "branch", 100)
            if settings.clean_ideas({"merge_into": name})["merge_into"] != name:
                raise IdeasError(f"{name!r} is not a branch name")
            try:
                IdeaGit(Path(self.host.repo_root)).ensure_branch(name)
            except RuntimeError as e:
                raise IdeasError(str(e)) from None
            mine["merge_into"] = name
        if isinstance(push, bool):
            mine["push"] = push
        kept = self.save_settings(mine)
        self._ev(event_log.INTO_CHANGED, args, branch=kept["merge_into"], push=kept["push"])
        self.changed("")
        return {"ok": True}
