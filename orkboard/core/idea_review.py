"""What the person does at Review (docs/specs/33-v1-shell.md §3), and each task's log: the runner's second half.

    ReviewMixin on `IdeaRunner` (core/idea_runner.py): merge / back / drop_task / skip_task / revise_tasks / stop_task / log.

A result waits at `review` holding its worktree and branch. **Merge** lands it into `ideas.merge_into` (only when its
tests are green and it does not conflict); **Send back** resumes the task's session with one line; **Drop** fails it
("dropped by you") and keeps its branch. The log is each task's session output, shown and never fed back to a model;
a secret's value never appears in it. Split from the runner to keep both under ~600 lines.
"""
from __future__ import annotations

import datetime as dt
import re
import threading
import time
from pathlib import Path

from orkboard.core.idea_plan import _task, estimate
from orkboard.core.idea_task import is_check
from orkboard.realm import idea_change, idea_spend, idea_target

STOP_ONE = "stop-one"                # a Run's `why` when one task is stopped (stop_task)
STOPPED_NOTE = "stopped by you"      # a task stopped on its own waits as `ready` with this note until Start
LOG_KEEP = 2000
LOG_SHOWN = 200
MASK = "••••"

BACK = """The person looked at your work at Review and sends it back:

{why}

{extra}Change it in this same worktree. Then stop: what you leave changed is committed for you, and the gate runs again."""


class RunnerError(Exception):
    """A command the runner refuses, in plain words."""


def _r():
    """The runner's module (it imports this one: looked up when a command runs)."""
    from orkboard.core import idea_runner
    return idea_runner


def _Conflict():
    from orkboard.realm.idea_git import Conflict
    return Conflict


class ReviewMixin:
    """The runner's Review answers and logs; `self` is an IdeaRunner."""

    # -- the person's answers at Review (spec 33 §3) -----------------------------------------------

    def _task(self, slug: str, tid: str) -> dict:
        plan = self.plan(slug)
        task = next((t for t in (plan or {}).get("tasks") or [] if t.get("id") == tid), None)
        if task is None:
            raise RunnerError("That task is gone")
        return task

    def _decided(self, slug: str, task: dict, decision: str, device: str, **more) -> None:
        """`result_decided` (spec 33 §9): what the person decided, and how long after the result was ready."""
        try:
            seconds = round(max(0.0, time.time() - dt.datetime.fromisoformat(str(task.get("finished") or "")).timestamp()), 1)
        except ValueError:
            seconds = None
        tests = task.get("tests") or {}
        self._emit("result_decided", idea=slug, task=task.get("id"), round=int(task.get("round") or 1), decision=decision,
                   conflict=str(task.get("conflict") or ""), passed=tests.get("passed"), failed=tests.get("failed"),
                   device=device or "desktop", seconds=seconds, **more)

    def merge(self, slug: str, tid: str, device: str = "desktop") -> str:
        """Land a task that waits at Review into `ideas.merge_into`; the commit. Refused when its tests are red or
        it conflicts (RunnerError, in plain words); a conflict found now is said on the task and it stays."""
        with self._lock:
            task = self._task(slug, tid)
            if task.get("state") != "review" or (slug, tid) in self._runs:
                raise RunnerError("That result is not waiting at Review")
            tests = task.get("tests") or {}
            if not tests.get("green", not tests.get("failed")):
                raise RunnerError("Its tests are red: send it back to fix them, or drop it")
            if task.get("conflict"):
                raise RunnerError(f"{task['conflict']}: send it back to fix the conflict, or drop it")
            self._runs[(slug, tid)] = _r().Run(threading.current_thread(), threading.Event())   # held while it lands
        base = str(_r().setting(self.settings, "merge_into") or "dev")
        if is_check(task) and (task.get("diff") or {}).get("files") == 0 and not task.get("commit"):
            return self._leave(slug, tid, task, device, base)       # a check that changed no file: *Leave them* lands nothing
        try:
            self.git.ensure_branch(base)
            path = self.git.reopen(slug, tid)
            commit, subjects, note = self.git.land(path, str(task.get("branch") or f"idea/{slug}/{tid}"), base,
                                                   bool(_r().setting(self.settings, "push")))
        except _Conflict() as e:
            self._set_task(slug, tid, conflict=str(e))
            raise RunnerError(str(e)) from None
        except Exception as e:
            raise RunnerError(" ".join(str(e).split())[:300] or "The merge failed") from None
        finally:
            with self._lock:
                self._runs.pop((slug, tid), None)
        self._decided(slug, task, "merge", device, into=base, pushed=bool(_r().setting(self.settings, "push")) and not note)
        self._set_task(slug, tid, state="merged", commit=commit, subjects=subjects, note=note, finished=_r().now_iso(),
                       error="", conflict="")
        self._log(slug, tid, f"== merged into {base} · {commit[:10]}\n")
        self._remove_worktree(slug, tid)
        self._settle_idea(slug)
        self.tick()
        return commit

    def _leave(self, slug: str, tid: str, task: dict, device: str, base: str) -> str:
        """*Leave them* on a check that changed no file: the task is merged with what it left in its note, nothing lands."""
        try:
            self._decided(slug, task, "merge", device, into=base, pushed=False)
            left = sum(1 for f in task.get("findings") or [] if isinstance(f, dict) and not f.get("fixed"))
            self._set_task(slug, tid, state="merged", commit="", subjects=[], note=f"{left} left" if left else "", finished=_r().now_iso(),
                           error="", conflict="")
            self._log(slug, tid, "== left as it is: nothing to land\n")
        finally:
            with self._lock:
                self._runs.pop((slug, tid), None)
        self._remove_worktree(slug, tid)
        self._settle_idea(slug)
        self.tick()
        return ""

    def _remove_worktree(self, slug: str, tid: str) -> None:
        from orkboard.realm import worktrees
        from orkboard.realm.idea_git import _worktree_id
        try:
            self.git.remove(worktrees.worktree_path(self.repo_root, _worktree_id(slug, tid)))
        except Exception:
            pass

    def _settle_idea(self, slug: str) -> None:
        """An idea that is not being run (a restart, a stop) whose tasks are all merged is done."""
        plan = self.plan(slug)
        if plan and slug not in self._active and all(t.get("state") == "merged" for t in plan["tasks"]):
            self._set_idea(slug, "done")
            self._changed(slug)

    def back(self, slug: str, tid: str, why: str, device: str = "desktop") -> None:
        """Send a result back with one line: the same session goes on with it (and the failing tests, or the
        conflict), the round counts up, and it comes to Review again."""
        why = " ".join(str(why or "").split())[:1000]
        if not why:
            raise RunnerError("Say in one line what to change")
        with self._lock:
            task = self._task(slug, tid)
            if task.get("state") != "review" or (slug, tid) in self._runs:
                raise RunnerError("That result is not waiting at Review")
            base = str(_r().setting(self.settings, "merge_into") or "dev")
            files: list[str] = []
            if task.get("conflict"):
                try:
                    files = self.git.merge_in(self.git.reopen(slug, tid), base)
                except Exception as e:
                    raise RunnerError(" ".join(str(e).split())[:300]) from None
            tests = task.get("tests") or {}
            red = tests.get("green") is False or bool(tests.get("failed"))
            self._decided(slug, task, "fix" if red or task.get("conflict") else "back", device, why=why, into=base)
            self._set_task(slug, tid, state="running", round=int(task.get("round") or 1) + 1, why=why, conflict="",
                           error="", note="", finished="")
            if slug not in self._active:
                self._active.append(slug)
                self._set_idea(slug, "working")
            self._spawn(slug, tid, threading.Event(), {"why": why, "files": files})
        self._changed(slug)

    def drop_task(self, slug: str, tid: str, device: str = "desktop") -> None:
        """Drop a result: the task fails with "dropped by you", its worktree goes, its branch stays."""
        with self._lock:
            task = self._task(slug, tid)
            if task.get("state") not in ("review", "failed", "ready", "waiting", "held", "picking") or (slug, tid) in self._runs:
                raise RunnerError("That task cannot be dropped now")
            if task.get("state") == "review":
                self._decided(slug, task, "drop", device, into=str(_r().setting(self.settings, "merge_into") or "dev"))
            self._set_task(slug, tid, state="failed", error="dropped by you", finished=_r().now_iso(), conflict="")
            if slug not in self._active:
                self._active.append(slug)
        self._remove_worktree(slug, tid)
        self._log(slug, tid, f"== dropped by you · {_r().now_iso()}\n")
        self.tick()

    def skip_task(self, slug: str, tid: str, device: str = "desktop") -> None:
        """Skip a task before it runs (a check the person spares): it is taken out of the plan, and out of what the
        others wait for; nothing of it ran, nothing is kept. Once it runs, it is too late: Stop it, or Drop it at Review."""
        with self._lock:
            task = self._task(slug, tid)
            if task.get("state") not in ("waiting", "ready", "held") or (slug, tid) in self._runs:
                raise RunnerError("That check is under way: it can no longer be skipped")
            plan = self.plan(slug) or {"tasks": []}
            left = [t for t in plan["tasks"] if t.get("id") != tid]
            for t in left:
                if tid in (t.get("after") or []):
                    t["after"] = [a for a in t["after"] if a != tid]
            self._save_tasks(slug, left)
            self._emit("task_skipped", idea=slug, task=tid, device=device or "desktop")
        self._settle_idea(slug)
        self._changed(slug)
        self.tick()

    def _highest_id(self, slug: str, plan: dict) -> int:
        """The highest `k<n>` the goal has used: a task id names its branch and its log, so a new task takes the next, never one used
        before. Read from the plan's tasks, the to-dos' `for` and the logs beside it (a skipped task leaves none of these but its place)."""
        seen = [str(t.get("id")) for t in plan["tasks"]] + [str(f) for d in plan.get("todos") or [] if isinstance(d, dict) for f in d.get("for") or []]
        seen += [p.stem for p in self._dir(slug).glob("k*.log")]
        return max((int(m.group(1)) for s in seen if (m := re.fullmatch(r"k(\d+)", s))), default=0)

    def revise_tasks(self, slug: str, change: dict) -> dict:
        """Apply the leader's plan change (spec 62 §3.2) under the lock, the plan read fresh. Of the tasks it names, those still not
        started: a **dropped** one is taken out as `skip_task` takes one (out of the others' `after`); a **changed** one takes the new
        title, short, brief, kind, tier, after and role, its id, state and the rest kept (a `ready` one that now waits for a task not
        merged waits); an **added** one is appended `waiting` under the next free id, its `after` mapped from the keys; a check task not
        started waits for the added ones too. A task that started meanwhile is left as it is and named in `left`. The plan's estimate
        is made again, its `passed_at` and the rest are kept. Then the goal is settled and the runner ticks: the new tasks are taken up
        as any waiting task (`_advance`); a goal that is failed or stopped keeps its state, its new tasks wait for its work to start
        again. `{added, changed, dropped, left}`: counts, and the titles of the tasks left."""
        with self._lock:
            plan = self.plan(slug)
            if plan is None:
                raise RunnerError("This goal has no plan yet")
            tasks = plan["tasks"]
            was = {t.get("id"): t.get("state") for t in tasks}
            by_id = {str(t.get("id")): t for t in tasks}
            fresh = lambda tid: idea_change.open_task(by_id[tid]) and not is_check(by_id[tid]) and (slug, tid) not in self._runs    # noqa: E731
            to_drop = [i for i in dict.fromkeys(str(i) for i in change.get("drop") or []) if i in by_id]
            to_change = [c for c in change.get("change") or [] if isinstance(c, dict) and str(c.get("id")) in by_id]
            dropped = [i for i in to_drop if fresh(i)]
            changing = [c for c in to_change if fresh(str(c["id"])) and str(c["id"]) not in dropped]
            left = [str(by_id[i].get("title") or i) for i in dict.fromkeys([*to_drop, *(str(c["id"]) for c in to_change)]) if not fresh(i)]
            adding = [a for a in change.get("add") or [] if isinstance(a, dict)]
            ids, n = {}, self._highest_id(slug, plan)
            for a in adding:
                n += 1
                ids[str(a.get("key"))] = f"k{n}"
            kept = [t for t in tasks if str(t.get("id")) not in dropped]
            for t in kept:
                if dropped and set(t.get("after") or []) & set(dropped):
                    t["after"] = [a for a in t["after"] if a not in dropped]
            graph = {str(t.get("id")): [str(a) for a in t.get("after") or []] for t in kept}
            graph.update({i: [] for i in ids.values()})
            for t in kept:                               # a check task not started waits for the new tasks: no task may wait for it
                if is_check(t) and idea_change.open_task(t):
                    graph[str(t.get("id"))] += list(ids.values())
            merged = {str(t.get("id")) for t in kept if t.get("state") == "merged"}
            for c in changing:
                tid = str(c["id"])
                task = by_id[tid]
                wanted = c["after"] if isinstance(c.get("after"), list) else task.get("after") or []         # none given: it keeps what it waits for
                after = idea_change.safe_after(graph, tid, [ids.get(str(a), str(a)) for a in wanted])
                task.update(title=str(c.get("title") or task.get("title") or ""), short=str(c.get("short") or task.get("short") or ""),
                            brief=str(c.get("brief") or task.get("brief") or ""), kind=str(c.get("kind") or task.get("kind") or "code"),
                            tier=str(c.get("tier") or task.get("tier") or "warrior"), after=after,
                            role=str(c["role"] if "role" in c else task.get("role") or ""))
                if task.get("state") == "ready" and not set(after) <= merged:
                    task["state"] = "waiting"
            old, added = list(kept), []
            for a in adding:
                tid = ids[str(a.get("key"))]
                after = idea_change.safe_after(graph, tid, [ids.get(str(x), str(x)) for x in a.get("after") or []])
                task = _task(tid, str(a.get("title") or ""), str(a.get("brief") or ""), str(a.get("kind") or "code"),
                             str(a.get("tier") or "warrior"), after)
                task.update(short=str(a.get("short") or task["short"]), role=str(a.get("role") or ""))
                kept.append(task)
                added.append(tid)
            for t in old:
                if added and is_check(t) and idea_change.open_task(t):
                    t["after"] = list(dict.fromkeys([*(t.get("after") or []), *added]))
            if added or changing or dropped:
                plan["tasks"] = kept
                plan["estimate"] = estimate(kept, [idea_target.tier_of(self.ran_on(t)[0]) for t in kept], idea_spend.tier_costs(self.state_dir))
                self._write(self._dir(slug) / "plan.json", plan)
                self._note(slug, was, kept)
        self._settle_idea(slug)
        self._changed(slug)
        self.tick()
        return {"added": len(added), "changed": len(changing), "dropped": len(dropped), "left": left}

    def stop_task(self, slug: str, tid: str, device: str = "desktop") -> None:
        """Stop one running task: it goes back to `ready` ("stopped by you") and waits for Start; the idea's other
        tasks go on."""
        with self._lock:
            run = self._runs.get((slug, tid))
            if run is None or self._task(slug, tid).get("state") not in _r().LIVE:
                raise RunnerError("That task is not running")
            run.why = STOP_ONE
            run.cancel.set()
            self._emit("task_stopped", idea=slug, task=tid, device=device or "desktop")

    # -- the task's log (shown, never fed back to a model) -----------------------------------------

    def _log_path(self, slug: str, tid: str) -> Path:
        return self._dir(slug) / f"{tid}.log"

    def _clear_log(self, slug: str, tid: str) -> None:
        try:
            self._log_path(slug, tid).unlink()
        except OSError:
            pass

    def _log(self, slug: str, tid: str, text: str, env: dict | None = None) -> None:
        """Append to the task's log, a secret's value masked, cut to its last LOG_KEEP lines."""
        for key, value in (env or {}).items():
            if key not in ("ORKCRAFT_ORC", "ORKCRAFT_IDEA", "ORKCRAFT_TASK") and value:
                text = text.replace(value, MASK)
        path = self._log_path(slug, tid)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(text)
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            if len(lines) > LOG_KEEP:
                path.write_text("".join(lines[-LOG_KEEP:]), encoding="utf-8")
        except OSError:
            pass

    def log(self, slug: str, tid: str, lines: int = LOG_SHOWN) -> str:
        try:
            text = self._log_path(slug, tid).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return "".join(text.splitlines(keepends=True)[-lines:])
