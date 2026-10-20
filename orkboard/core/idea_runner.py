"""The runner of a passed plan (docs/specs/29a-board-focus.md §5, 33 §2–§3): each task its own Claude session in a
worktree, tested, then judged at Review by the person, who merges it into `ideas.merge_into` (default `dev`; rebased
and fast-forwarded, pushed only when `ideas.push`), sends it back with a line, or drops it.

    runner = IdeaRunner(repo_root, state_dir, settings, bus)
    runner.start(slug)        # after `ideas.start` set the plan's `passed_at`
    runner.tick()             # every few seconds from the host: never blocks, the work runs on threads
    runner.stop(slug) / runner.stop_all()
    runner.merge(slug, tid) / runner.back(slug, tid, why) / runner.drop_task(slug, tid) / runner.stop_task(slug, tid)
    runner.log(slug, tid)     # the task's session output, last 200 lines (kept in <state_dir>/ideas/<slug>/<tid>.log)

The plan's tasks live in `<state_dir>/ideas/<slug>/plan.json` (the runner owns them once the plan is passed; it
re-reads the file before each write, so the keeper's to-dos stay as the keeper wrote them). A task waits for its
`after` tasks to be merged and for the to-dos `for` it to be done, starts when a slot is free (`ideas.max_parallel`)
and its tool's window is not nearly spent (else `held`, "after HH:MM"), works as its task type's role (that role's
model and instruction; its `max_parallel` is held besides `ideas.max_parallel`, spec 34 §3), passes the gate (once more on the
same session when red) and waits at `review`, green or red, holding its worktree and branch (`ideas.review` false:
green lands by itself, as before; a result for which no test ran waits at `review` all the same). Every task change publishes `ideas.changed`. All git: realm/idea_git.py.

Spec 35: a task runs on the Target's tier and effort (`ran_tier`, `effort`; a role's own model wins); `start_at: "night"`
starts only inside the night window; `passed_by: "auto"` leaves the person the reserve (realm/idea_target.py `gate`);
ideas go by `rank` (priority, then order); a file to-do's path reaches its task in the environment (idea_secrets).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from orkboard.core.sign_ins import HOLD_H
from orkboard.core.idea_review import BACK, STOP_ONE, STOPPED_NOTE, ReviewMixin, RunnerError  # noqa: F401
from orkboard.core.idea_task import FINDINGS_ASK, NO_CHANGE, NO_FINDINGS, TaskMixin, is_check
from orkboard.realm import call_log, event_log, halt, harnesses, idea_checks, idea_spend, idea_target, jobs, roles, status, tool_errors
from orkboard.realm.idea_git import BOARD_PAGE, CRITICAL_TESTS, Conflict, IdeaGit, env_name, has_summary, parse_tests, read_secret, spec_paths  # noqa: F401

CHANGED = "ideas.changed"          # slug: an idea's state or one of its tasks changed
HARNESS = "claude"
LIMITS_EVERY_S = 600               # how often the runner reads the quota itself, when nobody hands it one
DEFAULTS = {"max_parallel": 1, "merge_into": "dev", "push": False, "review": True}
STOPPED = "stopped"
LIVE = ("running", "testing")
PAGE_KEEP = 20000

FIX = """The gate after your work said no:

{problem}

Fix it in this same worktree. Then stop: what you leave changed is committed for you, and the gate runs again."""


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def setting(settings: Any, key: str, default: Any = None) -> Any:
    """`ideas.<key>` of the settings, however they carry it: an `ideas` dict or object, `ideas_<key>`, a dict."""
    default = DEFAULTS.get(key) if default is None else default
    ideas = settings.get("ideas") if isinstance(settings, dict) else getattr(settings, "ideas", None)
    if isinstance(ideas, dict) and key in ideas:
        return ideas[key]
    if ideas is not None and not isinstance(ideas, dict) and hasattr(ideas, key):
        return getattr(ideas, key)
    for name in (f"ideas_{key}", f"ideas.{key}"):
        if isinstance(settings, dict) and name in settings:
            return settings[name]
        if not isinstance(settings, dict) and hasattr(settings, name.replace(".", "_")):
            return getattr(settings, name.replace(".", "_"))
    return default


def _epoch(iso: object) -> float | None:
    """A task's `held_until` (local ISO time) as seconds; None when it holds none."""
    try:
        return dt.datetime.fromisoformat(str(iso)).timestamp()
    except ValueError:
        return None


def _until_of(note: str, now: float) -> float | None:
    """The time an "after HH:MM" note means: today's, else tomorrow's when it has passed by more than an hour."""
    try:
        hh, mm = note.split("after", 1)[1].strip().split()[0].split(":")[:2]
        t = dt.datetime.fromtimestamp(now).replace(hour=int(hh), minute=int(mm[:2]), second=0, microsecond=0)
    except (IndexError, ValueError):
        return None
    if t.timestamp() < now - 3600:
        t += dt.timedelta(days=1)
    return t.timestamp()


class Held(Exception):
    def __init__(self, until: float, line: str = "") -> None:
        """`line`: the tool's refused sign-in in words, when the work is held for the tool's sign-in (spec 45 §6)."""
        super().__init__("held")
        self.until, self.line = until, line


@dataclass
class Run:
    thread: threading.Thread
    cancel: threading.Event
    why: str = ""                  # set when someone stopped it
    role: str = ""                 # the role it runs as (spec 34 §3): its `max_parallel` is held


class IdeaRunner(TaskMixin, ReviewMixin):
    def __init__(self, repo_root: Path, state_dir: Path, settings: Any, bus: Any = None, *,
                 limits: Callable[[], list] | None = None, events: bool = True,
                 on_held: Callable[[], None] | None = None, rank: Callable[[str], Any] | None = None,
                 sign_ins: Any = None) -> None:
        """`limits`: the quota readers' last read (the town's `limits`); without it the runner reads it itself.
        `events`: write the task's events to the local event log (spec 33 §9); `on_held`: a task was held (the limits are read);
        `rank(slug)`: the idea's place (its priority, then the person's order): the ideas are served in that order;
        `sign_ins`: the host's sign-ins (core/sign_ins.py): a task whose tool is not signed in is held for it, not failed."""
        self.repo_root, self.state_dir = Path(repo_root), Path(state_dir)
        self.settings, self.bus = settings, bus
        self.git = IdeaGit(self.repo_root)
        self._limits_fn = limits
        self._limits: list = []
        self._limits_at = 0.0
        self._lock = threading.RLock()
        self._runs: dict[tuple[str, str], Run] = {}
        self._gate_runs: dict[str, object] = {}              # a worktree's last gate run, until the task reads it
        self._active: list[str] = []
        self._until: dict[tuple[str, str], float] = {}
        self.events, self.on_held, self.rank, self.sign_ins = events, on_held, rank, sign_ins
        self._since: dict[tuple[str, str], float] = {}     # when a task entered the state it is in (the event log)
        self._tls = threading.local()                       # Merge's `dear`, on the thread that merges
        self._resume_working()

    # -- files -----------------------------------------------------------------------------------

    def _dir(self, slug: str) -> Path:
        return self.state_dir / "ideas" / slug

    def _read(self, path: Path) -> dict | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def _write(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def plan(self, slug: str) -> dict | None:
        plan = self._read(self._dir(slug) / "plan.json")
        if plan is None or not isinstance(plan.get("tasks"), list):
            return None
        return plan

    def _save_tasks(self, slug: str, tasks: list[dict]) -> None:
        """Write the tasks into the plan as it is on disk now (the to-dos and the rest stay as they are there)."""
        plan = self.plan(slug) or {"idea": slug, "todos": []}
        was = {t.get("id"): t.get("state") for t in plan.get("tasks") or []}
        plan["tasks"] = tasks
        self._write(self._dir(slug) / "plan.json", plan)
        self._note(slug, was, tasks)

    def _emit(self, event: str, **fields: Any) -> None:
        if self.events:
            event_log.record(self.repo_root, event, **fields)

    def _note(self, slug: str, was: dict, tasks: list[dict]) -> None:
        """The event log's lines for the tasks whose state changed (spec 33 §9): `task_state`, and `result_ready` at Review."""
        now = time.time()
        for t in tasks:
            tid, new, old = t.get("id"), t.get("state"), was.get(t.get("id"))
            if new == old or old is None:
                continue
            since = self._since.get((slug, tid))
            self._since[(slug, tid)] = now
            check = ({"check": True, **({"clean": True} if new == "merged" and t.get("note") == "clean" else {})}
                     if is_check(t) else {})            # a check task's lines say so; a clean one is no result (spec 43 §1.3)
            self._emit(event_log.TASK_STATE, idea=slug, task=tid, state=new, was=old, round=int(t.get("round") or 1),
                       tier=t.get("tier") or "", role=t.get("role") or "", seconds=round(now - since, 1) if since else None, tokens=t.get("tokens"),
                       cost=t.get("cost"), ran_tier=t.get("ran_tier") or "", effort=t.get("effort") or "",
                       tool=t.get("tool") or "", model=t.get("model") or "",
                       **({"check": True, **({"clean": True} if new == "merged" and t.get("note") == "clean" else {})} if is_check(t) else {}))
            if new == "review":
                tests, diff = t.get("tests") or {}, t.get("diff") or {}
                self._emit(event_log.RESULT_READY, idea=slug, task=tid, round=int(t.get("round") or 1), passed=tests.get("passed"),
                           failed=tests.get("failed"), files=diff.get("files"), added=diff.get("added"),
                           removed=diff.get("removed"), cost=t.get("cost"), role=t.get("role") or "")
            if new == "held" and self.on_held is not None:
                try:
                    self.on_held()
                except Exception:               # a log never stops the work
                    pass

    def _set_task(self, slug: str, task_id: str, **fields: Any) -> None:
        with self._lock:
            plan = self.plan(slug)
            if plan is None:
                return
            for t in plan["tasks"]:
                if t.get("id") == task_id:
                    t.update(fields)
            self._save_tasks(slug, plan["tasks"])
        self._changed(slug)

    def _set_idea(self, slug: str, state: str, error: str = "") -> None:
        path = self._dir(slug) / "state.json"
        data = self._read(path) or {}
        data.update(state=state, error=error)
        self._write(path, data)

    def _changed(self, slug: str) -> None:
        if self.bus is not None:
            try:
                self.bus.publish(CHANGED, slug=slug)
            except Exception:              # a face's subscriber never stops the work
                pass

    def _resume_working(self) -> None:
        """After a restart: the ideas that were `working` go on; a task cut off mid-run is ready again."""
        for state_file in sorted((self.state_dir / "ideas").glob("*/state.json")):
            slug = state_file.parent.name
            if (self._read(state_file) or {}).get("state") != "working" or (plan := self.plan(slug)) is None:
                continue
            for t in plan["tasks"]:
                if t.get("state") in LIVE:       # cut off in a send back: back to Review, its work is on the branch
                    t.update(state="review", note="") if t.get("tests") else t.update(state="ready", note="")
            self._save_tasks(slug, plan["tasks"])
            self._active.append(slug)

    # -- the commands ----------------------------------------------------------------------------

    def start(self, slug: str) -> None:
        """The plan was passed (or Start again): every task not merged waits anew, the idea is `working`."""
        with self._lock:
            plan = self.plan(slug)
            if plan is None:
                raise RuntimeError(f"no plan for {slug!r}")
            for t in plan["tasks"]:
                if (slug, t.get("id")) in self._runs:
                    continue
                if t.get("state") not in ("merged", "review"):
                    t.update(state="waiting", error="", note="")
                    for key in ("held_for", "held_until", "held_line"):
                        t.pop(key, None)
                self._until.pop((slug, t.get("id")), None)
            self._save_tasks(slug, plan["tasks"])
            self._set_idea(slug, "working")
            if slug not in self._active:
                self._active.append(slug)
        self._changed(slug)
        self.tick()

    def stop(self, slug: str, why: str = "stopped by you") -> None:
        """Its running tasks stop (their worktrees stay until the next start); the idea needs you."""
        with self._lock:
            runs = [(k, r) for k, r in self._runs.items() if k[0] == slug]
            for _key, run in runs:
                run.why = why
                run.cancel.set()
            plan = self.plan(slug)
            if plan is not None:
                for t in plan["tasks"]:
                    if t.get("state") in ("ready", "held", *LIVE):
                        t.update(state="failed", error=why, finished=now_iso())
                self._save_tasks(slug, plan["tasks"])
            if slug in self._active:
                self._active.remove(slug)
                self._set_idea(slug, "failed", why)
        self._changed(slug)

    def stop_all(self) -> None:
        """Stop all (`realm/halt`): every idea's tasks stop and nothing new starts."""
        with self._lock:
            slugs = list(dict.fromkeys([*self._active, *(k[0] for k in self._runs)]))
        for slug in slugs:
            self.stop(slug, "stopped by Stop all")

    def busy(self) -> bool:
        with self._lock:
            return bool(self._runs)

    # -- the tick --------------------------------------------------------------------------------

    def tick(self) -> None:
        """Move what can move: waiting → ready, a held task whose window came back, a free slot → a task starts,
        an idea whose tasks are all merged → done, one with a failed task (and none running) → failed."""
        now = time.time()
        with self._lock:
            limits = self._read_limits(now)
            slots = max(1, int(setting(self.settings, "max_parallel") or 1)) - len(self._runs)
            for slug in sorted(self._active, key=self._rank_of):
                plan = self.plan(slug)
                if plan is None:
                    self._active.remove(slug)
                    continue
                tasks, changed = plan["tasks"], self._advance(slug, plan, now, limits)
                running = [t for t in tasks if (slug, t.get("id")) in self._runs]
                failed = next((t for t in tasks if t.get("state") == "failed"), None)
                if failed is not None or all(t.get("state") == "merged" for t in tasks):
                    if changed:
                        self._save_tasks(slug, tasks)
                    if not running:
                        self._finish(slug, failed)
                    elif changed:
                        self._changed(slug)
                    continue
                board = self.board()
                gate = idea_target.gate(plan, limits, board, now, day_free=self._pace_free(slug))
                for t in tasks:
                    if slots <= 0 or gate == "night":       # starts at night: only inside the window
                        break
                    if t.get("state") != "ready" or t.get("note") == STOPPED_NOTE:
                        continue
                    role = self._role(t)
                    if self._running_as(role["slug"]) >= role["max_parallel"]:
                        continue                     # this role's own limit (spec 34 §3): the task waits its turn
                    until = status.reset_of(limits, HARNESS, now, status.NEARLY)
                    if until is not None or gate is not None:     # the window, else the week (spec 44), else the reserve (§6)
                        week = until is None and idea_target.week_hold(plan, limits, board, now) == gate
                        self._hold(slug, t, until if until is not None else gate,
                                   "" if until is not None else ("week · " if week else "reserve · "))
                    elif self.signed_out():                       # its tool needs a sign-in: held for it (spec 45 §6)
                        self._hold_sign_in(t, "")
                    else:
                        if plan.get("start_at") == "night" and idea_target.board_low(plan, board) and not plan.get("by_pace") \
                                and not idea_target.in_night(str(board.get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now)):
                            self._mark_pace(slug)                  # it goes by day because the week is ahead (spec 44 §3)
                        self._launch(slug, t)
                        slots -= 1
                        if paced:
                            self._mark_pace(slug)
                    changed = True
                if changed:
                    self._save_tasks(slug, tasks)
                    self._changed(slug)

    def merge(self, slug: str, tid: str, device: str = "desktop", dear: bool = False) -> str:
        """Review's Merge; `dear` (spec 36 §4: it cost too much for this) only goes on its `result_decided`."""
        self._tls.dear = bool(dear)
        try:
            return super().merge(slug, tid, device)
        finally:
            self._tls.dear = False

    def _decided(self, slug: str, task: dict, decision: str, device: str, **more: Any) -> None:
        if decision == "merge":
            more["dear"] = bool(getattr(self._tls, "dear", False))
        super()._decided(slug, task, decision, device, **more)

    def _role(self, task: dict) -> dict:
        """The role it runs as: the goal's team's pick in its plan (`role`), else its tag's in the project."""
        return (roles.role(self.state_dir, str(task.get("role") or "")) if task.get("role") else None) \
            or roles.role_for(self.state_dir, str(task.get("kind") or ""))

    def _rank_of(self, slug: str) -> Any:
        try:
            return (0, self.rank(slug)) if self.rank is not None else (0, 0)
        except Exception:                      # an idea the face cannot place goes last
            return (1, 0)

    def board(self) -> dict:
        """The Board's own settings as the runner reads them (spec 35): its Target, night, reserves, and whether it
        starts plans by itself (spec 44: the week's pace moves only the Board's own work)."""
        return {k: setting(self.settings, k, d) for k, d in (("target", "balance"), ("night", "01:00-07:00"),
                                                             ("reserve_day", 0.3), ("reserve_night", 0.1),
                                                             ("autostart", True))}

    def _pace_free(self, slug: str) -> bool:
        """No other plan of this project goes by day by the week's pace (one at a time, spec 44 §3)."""
        return not any(o != slug and (self.plan(o) or {}).get("by_pace") for o in self._active)

    def _mark_pace(self, slug: str) -> None:
        plan = self.plan(slug)
        if plan is not None:
            plan["by_pace"] = True
            self._write(self._dir(slug) / "plan.json", plan)

    def ran_on(self, task: dict) -> tuple[str, str]:
        """(the model or tier a task runs on, its effort): the Target's shift of its tier, a role's own model winning."""
        return idea_target.task_pick(str(task.get("tier") or "warrior"), idea_target.target_of(self.board()),
                                     str(self._role(task).get("model") or ""))

    def _running_as(self, slug: str) -> int:
        return sum(1 for r in self._runs.values() if r.role == slug)

    def _advance(self, slug: str, plan: dict, now: float, limits: list | None = None) -> bool:
        tasks = plan["tasks"]
        merged = {t.get("id") for t in tasks if t.get("state") == "merged"}
        todos = [d for d in plan.get("todos") or [] if isinstance(d, dict)]
        changed = False
        for t in tasks:
            tid, state = t.get("id"), t.get("state")
            if state == "held" and t.get("held_for") == "sign_in":
                if self.signed_out(t.get("harness") or HARNESS):
                    if (due := _epoch(t.get("held_until"))) and now >= due:      # a day: it fails as it did, with the line
                        t.update(state="failed", error=t.get("held_line") or tool_errors.LINES[tool_errors.LOGIN].format(
                                     tool=harnesses.title(t.get("harness") or HARNESS)),
                                 finished=now_iso(), held_for="", held_until="", held_line="")
                        changed = True
                    continue
                t.update(state="waiting", note="", held_for="", held_until="", held_line="")     # signed in: it goes on
                state, changed = "waiting", True
            if state == "held":
                until = self._until.get((slug, tid)) or _until_of(t.get("note", ""), now) or now
                if until > now:
                    continue
                self._until.pop((slug, tid), None)
                t.update(state="waiting", note="")
                state, changed = "waiting", True
            if state in LIVE and (slug, tid) not in self._runs:      # its thread is gone (should not happen)
                t.update(state="ready")
                changed = True
            if state not in ("waiting", "", None):
                continue
            after_ok = all(a in merged for a in t.get("after") or [])
            todos_ok = all(d.get("done") for d in todos if tid in (d.get("for") or []))
            if after_ok and todos_ok:
                t["state"], changed = "ready", True
            elif state != "waiting":
                t["state"], changed = "waiting", True
        return changed

    def _finish(self, slug: str, failed: dict | None) -> None:
        self._active.remove(slug)
        if failed is None:
            self._set_idea(slug, "done")
        else:
            why = failed.get("error") or "it failed"
            self._set_idea(slug, "failed", f"{failed.get('title') or failed.get('id')}: {why}")
        self._changed(slug)

    def signed_out(self, harness: str = HARNESS) -> bool:
        """Whether the host says this tool needs its sign-in: what runs by itself waits for it."""
        return self.sign_ins is not None and bool(self.sign_ins.blocked(harness))

    def _hold_sign_in(self, task: dict, line: str) -> None:
        """The task waits for its tool's sign-in: at most `HOLD_H` hours, then it fails with `line`."""
        task.update(state="held", note="", held_for="sign_in", harness=HARNESS, held_line=line[:600],
                    held_until=dt.datetime.fromtimestamp(time.time() + HOLD_H * 3600).isoformat(timespec="seconds"))

    def held_for(self, harness: str) -> int:
        """How many tasks wait for this tool's sign-in now."""
        n = 0
        for state_file in (self.state_dir / "ideas").glob("*/plan.json"):
            plan = self._read(state_file) or {}
            n += sum(1 for t in plan.get("tasks") or [] if isinstance(t, dict) and t.get("state") == "held"
                     and t.get("held_for") == "sign_in" and (t.get("harness") or HARNESS) == harness)
        return n

    def _hold(self, slug: str, task: dict, until: float, why: str = "") -> None:
        self._until[(slug, task.get("id"))] = until
        task.update(state="held", note=f"{why}after {dt.datetime.fromtimestamp(until):%H:%M}")

    def _read_limits(self, now: float) -> list:
        if self._limits_fn is not None:
            try:
                return list(self._limits_fn() or [])
            except Exception:
                return []
        if now - self._limits_at > LIMITS_EVERY_S:
            self._limits_at = now

            def read() -> None:
                from orkboard.sources.limits import fetch_limits
                try:
                    self._limits = list(fetch_limits(self.repo_root))
                except Exception:          # a quota never stops the work
                    pass
            threading.Thread(target=read, daemon=True, name="ideas-limits").start()
        return self._limits

    # -- one task --------------------------------------------------------------------------------

    def _launch(self, slug: str, task: dict) -> None:
        tid = task.get("id")
        cancel = threading.Event()
        run, effort = self.ran_on(task)
        h = harnesses.get(HARNESS)
        task.update(tool=HARNESS, model=(h.pick(run) if h else run) or run)    # the model the run names (spec 35 §12)
        task.update(state="running", started=now_iso(), finished="", error="", note="",
                    branch=f"idea/{slug}/{tid}", commit="", session="", cost=None, tokens=None,
                    tests=None, diff=None, round=1, conflict="", why="", base="", findings=None, role=self._role(task)["slug"],
                    ran_tier=idea_target.tier_of(run), effort=effort)
        self._clear_log(slug, tid)
        self._spawn(slug, tid, cancel, None)

    def _spawn(self, slug: str, tid: str, cancel: threading.Event, again: dict | None) -> None:
        thread = threading.Thread(target=self._work, args=(slug, tid, cancel, again), daemon=True,
                                  name=f"idea-{slug}-{tid}")
        task = next((t for t in (self.plan(slug) or {}).get("tasks") or [] if t.get("id") == tid), {})
        self._runs[(slug, tid)] = Run(thread, cancel, role=self._role(task)["slug"])
        thread.start()

    def _work(self, slug: str, tid: str, cancel: threading.Event, again: dict | None = None) -> None:
        """One try of a task: the session, the gate (once more on the same session when red), then Review (or, with
        `ideas.review` off, the merge). `again`: a send back, {"why", "files"} (files: the conflict being fixed)."""
        path: Path | None = None
        spent = {"cost": None, "tokens": None}
        try:
            plan = self.plan(slug) or {"tasks": []}
            task = next(t for t in plan["tasks"] if t.get("id") == tid)
            base = str(setting(self.settings, "merge_into") or "dev")
            env = self._env(slug, tid, plan)
            h = harnesses.need(HARNESS)
            run, effort = self.ran_on(task)
            model = h.pick(run)                          # the role's model, else the tier the Target gives
            rnd, chk = int(task.get("round") or 1), is_check(task)
            if again is None:
                self.git.ensure_branch(base)
                path, branch = self.git.prepare(slug, tid, base)
                start_sha = self.git.head(path)
                self._set_task(slug, tid, base=start_sha)
                prompt, resume = self._prompt(slug, plan, task), ""
            else:
                path, branch = self.git.reopen(slug, tid), str(task.get("branch") or f"idea/{slug}/{tid}")
                start_sha = str(task.get("base") or "") or self.git.head(path)
                spent.update(cost=task.get("cost"), tokens=task.get("tokens"))
                extra = ""
                tests = task.get("tests") or {}
                if again["files"]:
                    extra += (f"Your branch conflicted with `{base}` in {', '.join(again['files'])}. The merge of "
                              f"`{base}` into your branch is open in this worktree: rebase onto {base} and resolve "
                              "it by editing those files until no conflict marker is left (keep what both sides "
                              "meant). Do not abort the merge.\n\n")
                if tests and not tests.get("green", not tests.get("failed")):
                    extra += f"The tests were red:\n{tests.get('tail', '')}\n\n"
                prompt, resume = BACK.format(why=again["why"], extra=extra), str(task.get("session") or "")
                if chk and resume:
                    prompt += "\n\n" + FINDINGS_ASK
                if not resume:
                    prompt = self._prompt(slug, plan, task) + "\n\n" + prompt
                elif is_check(task):
                    prompt += self._again_ask(task)
                if is_check(task):
                    self._set_task(slug, tid, findings=None)       # replaced by this round's
            self._log(slug, tid, f"== round {rnd} · {now_iso()} · {model}\n{prompt}\n", env)
            session = self._session(slug, tid, path, cancel, model, env, prompt, resume, spent, effort)
            problem, out, findings = None, "", None
            for attempt in (1, 2):
                self._set_task(slug, tid, state="testing")
                if chk:                              # spec 43 §1.3: what it found decides how it ends
                    done, findings = self._check_round(slug, tid, path, start_sha, task, spent, env, attempt > 1 and findings is not None)
                    if done:
                        return
                problem, out = self._check(path, start_sha, cancel, str(task.get("title") or ""), chk)
                self._log(slug, tid, f"== the gate, try {attempt}\n{out or problem}\n", env)
                if problem is None:
                    break
                if attempt == 2:
                    if chk and findings is None and problem.startswith(NO_CHANGE):
                        raise RuntimeError(NO_FINDINGS)
                    if out and setting(self.settings, "review"):    # red after the one fix: the person decides
                        break
                    raise RuntimeError(f"the gate is still red after one fix: {problem[-600:]}")
                self._set_task(slug, tid, state="running")
                session = self._session(slug, tid, path, cancel, model, env, FIX.format(problem=problem) + (f"\n\n{FINDINGS_ASK}" if chk else ""), session,
                                        spent, effort, "fix")
            tests = self._tests_of(path, out, problem)
            diff = self.git.stats(path, start_sha)
            left = idea_checks.counts(findings)["left"] or 0 if chk else 0      # findings left always wait at Review
            if setting(self.settings, "review") or not tests["ran"] or left:     # nothing ran: never lands by itself
                self._set_task(slug, tid, state="review", tests=tests, diff=diff, conflict="", finished=now_iso(),
                               error="" if problem is None else "the tests are red", note=f"{left} left" if left else "")
                self._log(slug, tid, f"== at Review · {now_iso()}\n", env)
                return
            commit, subjects, note = self.git.land(path, branch, base, bool(setting(self.settings, "push")))
            self._set_task(slug, tid, state="merged", commit=commit, subjects=subjects, note=note, tests=tests,
                           diff=diff, finished=now_iso(), error="")
            self.git.remove(path)
        except Held as e:
            with self._lock:
                self._until[(slug, tid)] = e.until
            if e.line:                      # held for its tool's sign-in (spec 45 §6), not for a window
                hold: dict = {}
                self._hold_sign_in(hold, e.line)
                self._set_task(slug, tid, finished="", **({**hold, "note": ""} if again is None
                                                          else {"state": "review", "note": e.line[:300]}))
            else:
                self._set_task(slug, tid, state="held" if again is None else "review",
                               note=f"after {dt.datetime.fromtimestamp(e.until):%H:%M}", finished="")
        except (InterruptedError, halt.Halted) as e:
            run = self._runs.get((slug, tid))
            why = (run.why if run else "") or (str(e) if isinstance(e, halt.Halted) else STOPPED)
            if why == STOP_ONE:
                self._set_task(slug, tid, state="review" if again is not None else "ready",
                               note="" if again is not None else STOPPED_NOTE, error="", finished="")
            else:
                self._set_task(slug, tid, state="failed", error=why, finished=now_iso())
        except Conflict as e:
            self._set_task(slug, tid, state="failed", error=str(e), finished=now_iso())
        except Exception as e:             # a task's failure is said on its card, never a crash of the host
            self._set_task(slug, tid, state="failed", error=" ".join(str(e).split())[:600] or type(e).__name__,
                           finished=now_iso())
        finally:
            with self._lock:
                self._runs.pop((slug, tid), None)
            self._changed(slug)
            try:
                self.tick()
            except Exception:
                pass

    def _session(self, slug: str, tid: str, path: Path, cancel: threading.Event, model: str, env: dict,
                 prompt: str, resume: str, spent: dict, effort: str = "", step: str = "task") -> str:
        """One turn of the task's Claude session (work mode); its cost and tokens add up on the task, and its line
        goes to the idea's ledger (spec 36 §1: `task`, or `fix` for the gate's retry)."""
        try:
            with call_log.of_project(self.repo_root), tool_errors.doing("task"):     # its log and spend: this project's
                _text, cost, tokens, session = jobs.run_work(HARNESS, prompt, path, cancel, model=model, env=env,
                                                             resume=resume, effort=effort)
        except tool_errors.ToolError as e:
            if e.kind != tool_errors.LIMIT:
                if self.sign_ins is not None and self.sign_ins.holds(e):      # its sign-in helps: the task waits for it
                    raise Held(time.time() + HOLD_H * 3600, tool_errors.plainly(e)) from e
                raise
            now = time.time()
            raise Held(status.reset_of(self._read_limits(now), HARNESS, now, 1.0)
                       or now + status.UNKNOWN_RESET_S) from e
        for key, value in (("cost", cost), ("tokens", tokens)):
            if value is not None:
                spent[key] = (spent[key] or 0) + value
        session = session or resume
        task = next((t for t in (self.plan(slug) or {}).get("tasks") or [] if t.get("id") == tid), {"id": tid})
        idea_spend.task_line(self.state_dir, slug, task, step, HARNESS, model, cost, tokens)
        self._log(slug, tid, f"== the session answered\n{_text}\n", env)
        self._set_task(slug, tid, session=session, cost=spent["cost"], tokens=spent["tokens"])
        return session
