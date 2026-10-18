"""The board's keeper (spec 29a §4, decisions §43, §47; docs/specs/35-goals-window.md): it reads goals, drafts each
idea straight into its spec, talks a spec through with the person, turns a spec into a plan, and works at night.

    keeper = IdeaKeeper(repo_root, state_dir, wiki_root=lambda: root, settings=lambda: machine.ideas,
                        publish=lambda slug: ..., limits=lambda: town.limits, on_plan=autostart)
    keeper.draft(slug)                # an idea → its spec (core/idea_draft.py), then its plan when it asks nothing
    keeper.say(slug, "Why not a toggle?", "Risks")    # the keeper answers in the background
    keeper.plan(slug)                 # Re-plan: the page → plan.json, with its estimate
    keeper.read_stop(slug)            # this idea's run stops (its own cancel); its queue is `hold`
    keeper.tick()                     # the host's clock: what the limits held runs again, and the night (core/idea_night.py)

- **The Target** (realm/idea_target.py) picks each step's tier and effort: goal, draft, talk, plan, refresh, propose. The
  Taskmaster's own model, when it is not its default `elder`, replaces the tier; the Target still gives the effort.
- **Goal** (read-only, core/idea_goals.py): a goal saved is read at once: its title, Summary, Metrics, links, questions.
- **Draft** (read-only): it starts the idea's session; the talk and the plan resume it. One Claude session per idea
  (`--resume`); a new one when the last turn is older than `idle_hours` or its context passed 60 % of the window. The
  talk is archived in `talk.jsonl` and never read back into a model.
- **Plan**: the page → `plan.json` (at most 8 tasks), its Stages and its risk written by code, the estimate from the
  tiers the tasks will run on; then `on_plan(slug)` (the face decides whether it starts by itself, spec 35 §5).
- **The window** (spec 35 §6): in a spent window a call is not made; what runs by itself waits with `held_until`, a
  call the person asks for is refused in plain words.

Every model call goes through `realm/jobs.py` on the `claude` harness; its answer is untrusted: it is parsed
strictly and only known sections are written. Each change is published (`publish(slug)`: the face puts
`ideas.changed` on the bus). The keeper never commits: the pages stay in the working tree. No face.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

from orkcraft.core.idea_draft import DraftMixin
from orkcraft.core.idea_goals import GoalMixin
from orkcraft.core.idea_night import NightMixin
from orkcraft.realm import event_log, idea_target, ideas, plans, roles, status

CHANGED = "ideas.changed"          # the bus's topic: slug
HARNESS = "claude"
WINDOW = 200_000                   # Claude's context window, tokens
COMPACT_SHARE = 0.6                # a talk's session past this share of the window is compacted
MAX_TASKS, MAX_TODOS, MAX_QUESTIONS = 8, 5, 3
INDEX_CHARS, PAGE_CHARS, REPLY_CHARS = 6000, 30_000, 4000
TIERS = ("elder", "warrior", "laborer")
KINDS = ("secret", "choice", "confirm", "instructions", "file")
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
TICK_S = 20.0                      # how often the clock looks for what the limits held

Call = Callable[[str, str, str, str], tuple[str, Any, Any, str]]   # (tier, prompt, resume, effort) → (text, cost, tokens, session)


class KeeperError(Exception):
    """What the keeper refuses, in plain words."""


def first_json(text: str) -> dict | None:
    """The first JSON object in a model's answer (it may wrap it in prose or a code fence); None when there is none."""
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text or ""):
        try:
            value, _end = decoder.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _words(value: object, limit: int) -> str:
    return str(value).strip()[:limit] if isinstance(value, (str, int, float)) and not isinstance(value, bool) else ""


def _strings(value: object, limit: int, each: int = 500) -> list[str]:
    if not isinstance(value, list):
        return []
    return [s for s in (_words(v, each) for v in value) if s][:limit]


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {' '.join(q.split())}" for q in lines)


def _iso(at: float) -> str:
    return dt.datetime.fromtimestamp(at).isoformat(timespec="seconds")


class IdeaKeeper(DraftMixin, GoalMixin, NightMixin):
    def __init__(self, repo_root: Path, state_dir: Path, wiki_root: Callable[[], Path],
                 settings: Callable[[], dict], publish: Callable[[str], None] = lambda slug: None,
                 demo: bool = False, budget_ok: Callable[[], bool] = lambda: True,
                 taskmaster: Callable[[], str] | None = None, limits: Callable[[], list] | None = None,
                 on_plan: Callable[[str], None] | None = None, start_night: Callable[[str], bool] | None = None,
                 events: bool = True) -> None:
        """`limits`: the quota readers' last read (spent windows hold the keeper); `on_plan(slug)`: a plan was made
        or its risk changed (the face's autostart); `start_night(slug)`: a plan passed to start at night is started
        (the night's step 2); `events`: the keeper's own events go to the local event log (spec 35 §12)."""
        self.repo_root, self.state_dir = Path(repo_root), Path(state_dir)
        self.taskmaster = taskmaster or (lambda: (roles.role(self.state_dir, roles.TASKMASTER) or {}).get("model") or "elder")
        self._again: set[str] = set()                # a busy key asked again while it ran
        self.wiki_root, self.settings, self.publish = wiki_root, settings, publish
        self.demo, self.budget_ok, self.events = demo, budget_ok, events
        self.limits = limits or (lambda: [])
        self.on_plan = on_plan or (lambda slug: None)
        self.start_night = start_night or (lambda slug: False)
        self.call: Call = self._claude                # tests swap the model call here
        self.cancel = threading.Event()
        self._tls = threading.local()               # the idea a model call is for (its record in realm/call_log.py names it)
        self._lock = threading.Lock()
        self._busy: dict[str, str] = {}             # key → drafting | talking | planning | goal
        self._cancels: dict[str, threading.Event] = {}   # key → its run's own cancel (read_stop)
        self._tick_at = float("-inf")
        self._night_busy, self._night_tried = False, float("-inf")

    # -- the model call -------------------------------------------------------------------------------------

    def _claude(self, tier: str, prompt: str, resume: str = "", effort: str = "") -> tuple[str, Any, Any, str]:
        from orkcraft.realm import harnesses, jobs
        from orkcraft.sources import telemetry
        h = harnesses.get(HARNESS)
        purpose = {"laborer": "sort", "elder": "plan"}.get(tier, "plan")      # the Taskmaster's own model is a plan
        cancel = getattr(self._tls, "cancel", None) or self.cancel
        with telemetry.tagged(purpose, "board"):
            return jobs.run_read(HARNESS, prompt, self.repo_root, cancel, h.pick(tier) if h else tier,
                                 env={"ORKCRAFT_ORC": "board/keeper", "ORKCRAFT_IDEA": getattr(self._tls, "slug", "")},
                                 resume=resume, effort=effort)

    def target(self) -> str:
        return idea_target.target_of(self.settings())

    def pick(self, step: str) -> tuple[str, str] | None:
        """The (model or tier, effort) a keeper step runs on: by the Target, the Taskmaster's own model winning."""
        return idea_target.keeper_pick(step, self.target(), self.taskmaster())

    def ask(self, step: str, prompt: str, resume: str = "") -> tuple[str, Any, Any, str]:
        """One model call on a step; a run stopped meanwhile (its own cancel or Stop all) raises InterruptedError."""
        got = self.pick(step)
        if got is None:
            raise KeeperError(f"The Target {self.target()} makes no {step} call")
        self._tls.picked = got
        out = self.call(got[0], prompt, resume, got[1])
        cancel = getattr(self._tls, "cancel", None)
        if (cancel is not None and cancel.is_set()) or self.cancel.is_set():
            raise InterruptedError("stopped")
        return out

    def picked(self) -> tuple[str, str]:
        return getattr(self._tls, "picked", ("", ""))

    def _context(self, session: str, tokens) -> int:
        from orkcraft.realm import jobs
        try:
            read = jobs.context_of(HARNESS, session, self.repo_root)
        except Exception:                            # a transcript we cannot read: the run's own count
            read = 0
        return int(read or tokens or 0)

    def _ev(self, event: str, **fields: Any) -> None:
        if self.events and not self.demo:
            event_log.record(self.repo_root, event, **fields)

    # -- what the host asks ------------------------------------------------------------------------------

    def busy(self, slug: str) -> str:
        """What the keeper does on this idea now ("" nothing)."""
        return self._busy.get(slug, "")

    def busy_goal(self, slug: str) -> str:
        return self._busy.get(f"goal:{slug}", "")

    def stop_all(self) -> None:
        """Stop all: every run is stopped (its call raises), the next calls run again."""
        stopping, self.cancel = self.cancel, threading.Event()
        stopping.set()
        with self._lock:
            runs = list(self._cancels.values())
        for ev in runs:
            ev.set()

    def read_stop(self, slug: str) -> bool:
        """The person stops the keeper's run on this idea (its own cancel, not Stop all's); its queue is `hold`, so
        nothing drafts it by itself again. True when a run was going."""
        with self._lock:
            ev = self._cancels.get(slug)
        if ev is not None:
            ev.set()
        ideas.save_state(self.state_dir, slug, queue="hold", held_until="")
        self._ev(event_log.KEEPER_STOPPED, idea=slug)
        self.publish(slug)
        return ev is not None

    def _may_run(self) -> str:
        if self.demo:
            return "The demo runs no model: the keeper only reads ideas in a real town"
        if not self.budget_ok():
            return "Today's spend limit is reached: the keeper waits"
        return ""

    def window_until(self) -> float | None:
        """When the Claude window comes back, while it is (nearly) spent: as the runner reads it."""
        try:
            limits = list(self.limits() or [])
        except Exception:                            # a quota never stops the board
            limits = []
        return status.reset_of(limits, HARNESS, time.time(), status.NEARLY)

    def refuse_spent(self) -> None:
        """A call the person asks for (a talk, Process now, Re-plan) in a spent window: refused in plain words."""
        until = self.window_until()
        if until is not None:
            raise KeeperError(f"Claude's window is spent: try again after {dt.datetime.fromtimestamp(until):%H:%M}")

    def hold(self, slug: str) -> bool:
        """What runs by itself, in a spent window: not made; the idea waits with `held_until` (the reset)."""
        until = self.window_until()
        if until is None:
            return False
        ideas.save_state(self.state_dir, slug, held_until=_iso(until))
        self.publish(slug)
        return True

    def tick(self, now: float | None = None) -> bool:
        """The host's clock: an idea the limits held (or whose run the host lost) runs again once the window is
        back, and the night runs at its start. True when something started."""
        now = time.time() if now is None else now
        if now - self._tick_at < TICK_S or self._may_run():
            return False
        self._tick_at = now
        started = False
        if self.window_until() is None:
            for i in ideas.ideas(self.wiki_root()):
                slug = i["slug"]
                st = ideas.state(self.state_dir, slug)
                if self.busy(slug) or (not st["held_until"] and (st["error"] or st["state"] != "raw")):
                    continue
                if st["state"] == "raw" and ideas.queue_of(st) == "now":
                    started |= self._quiet(lambda: self.draft(slug))
                elif st["state"] == "ready" and st["held_until"] and ideas.plan(self.state_dir, slug) is None:
                    started |= self._quiet(lambda: self.plan(slug, auto=True))
        return self.night_tick(now) or started

    def _quiet(self, fn: Callable[[], Any]) -> bool:
        try:
            return fn() is not False
        except KeeperError:
            return False

    def _run(self, key: str, what: str, fn: Callable[[], None], slug: str = "") -> None:
        """Run `fn` as the keeper's run on `key` (a goal's is `goal:<slug>`), with its own cancel, on this thread."""
        cancel = threading.Event()
        with self._lock:
            self._cancels[key] = cancel
        self._tls.cancel, self._tls.slug = cancel, slug or key
        try:
            fn()
        finally:
            with self._lock:
                self._busy.pop(key, None)
                if self._cancels.get(key) is cancel:
                    self._cancels.pop(key)
            self._tls.cancel = None
            self.publish(key)

    def _claim(self, key: str, what: str) -> None:
        with self._lock:
            if self._busy.get(key):
                raise KeeperError("The keeper is busy with this idea: a moment")
            self._busy[key] = what

    def _start(self, slug: str, what: str, fn: Callable[[], None], key: str = "") -> None:
        """`key`: the busy key (a goal's is `goal:<slug>`); what is published is the key, or the idea's slug."""
        key = key or slug
        self._claim(key, what)
        threading.Thread(target=self._run, args=(key, what, fn, slug if key == slug else f"goal-{slug}"),
                         daemon=True, name=f"idea-{what}").start()

    def _sync(self, slug: str, what: str, fn: Callable[[], None], key: str = "") -> bool:
        """The night's way: the same run, on this thread; False when the key is busy."""
        key = key or slug
        try:
            self._claim(key, what)
        except KeeperError:
            return False
        self._run(key, what, fn, slug if key == slug else f"goal-{slug}")
        return True

    def _place(self, root: Path, slug: str, before: str) -> None:
        """The keeper's proposal of an idea's place among its goal's ideas; the person's own drag is never undone."""
        page = ideas.idea_page(root, slug)
        if not before or page is None or page.get("placed") == "person":
            return
        target = ideas.idea_page(root, before)
        if target is None or before == slug or target.get("track") != page.get("track"):
            return
        ideas.move(root, slug, before=before)

    def read_now(self, slug: str) -> None:
        """Process now: a `raw` idea drafted at once, in the background (`ideas.read_now`, `ideas.queue` now)."""
        if ideas.idea_page(self.wiki_root(), slug) is None:
            raise KeeperError("That idea is gone")
        if ideas.state(self.state_dir, slug)["state"] != "raw":
            raise KeeperError("The keeper has read this idea already")
        self.draft(slug, person=True)

    # -- the talk: one session per idea, the draft's -----------------------------------------------------

    def say(self, slug: str, text: str, section: str = "") -> None:
        root = self.wiki_root()
        text = str(text or "").strip()[:ideas.SECTION_CHARS]
        if ideas.idea_page(root, slug) is None:
            raise KeeperError("That idea is gone")
        if not text:
            raise KeeperError("Say something to the keeper")
        if section and section not in ideas.SECTIONS:
            raise KeeperError(f"An idea has no section {section!r}")
        if why := self._may_run():
            raise KeeperError(why)
        if self.busy(slug):
            raise KeeperError("The keeper is busy with this idea: a moment")
        self.refuse_spent()
        ideas.add_turn(self.state_dir, slug, "you", text, section)
        self._start(slug, "talking", lambda: self.talk_one(slug, text, section))

    def fresh(self, st: dict, now: dt.datetime | None = None) -> bool:
        """Whether the talk's next turn needs a new session (compaction): none yet, its last turn older than
        `idle_hours`, or its context past 60 % of the window."""
        if not st.get("session"):
            return True
        now = now or dt.datetime.now()
        hours = int((self.settings() or {}).get("idle_hours") or 24)
        try:
            at = dt.datetime.fromisoformat(str(st.get("session_at") or ""))
        except ValueError:
            return True
        return now - at > dt.timedelta(hours=hours) or int(st.get("context") or 0) > COMPACT_SHARE * WINDOW

    def talk_prompt(self, root: Path, slug: str, text: str, section: str, fresh: bool) -> str:
        page = ideas.idea_page(root, slug)
        about = f" (about {section})" if section else ""
        ask = f"""The person says{about}:
{text}

Answer with one JSON object and nothing else:
{{"reply": "your answer to the person, short and plain",
 "sections": {{"<a section's name>": "its whole new text"}},
 "decisions": ["one line for each thing decided in this turn, and why"],
 "questions": ["the open questions that remain (all of them; [] when none)"]}}
Put in `sections` only the sections this turn is about; leave the others out. Section names: {", ".join(n for n in ideas.SECTIONS if n != "Decisions")}."""
        if not fresh:
            now = page.section(section) if section else ""
            return ask + (f"\n\nThe section {section} reads now:\n{now[:PAGE_CHARS]}" if section else "")
        return f"""You are the keeper of one idea on this project's Task board: you talk its spec through with the
person, and keep its page. You may read the repository (read only). Edit only the sections a turn is about, never
rewrite the page; each decision goes to Decisions (you name it, the board writes the line).

The idea's page now:
{page.text()[:PAGE_CHARS]}

{ask}"""

    def talk_one(self, slug: str, text: str, section: str = "") -> None:
        root = self.wiki_root()
        st = ideas.state(self.state_dir, slug)
        fresh = self.fresh(st)
        before = ideas.idea_page(root, slug)
        asked = bool(before and ideas.items(before.section("Open questions")))
        try:
            out, _cost, tokens, session = self.ask("talk", self.talk_prompt(root, slug, text, section, fresh),
                                                   "" if fresh else st["session"])
        except Exception as e:
            ideas.add_turn(self.state_dir, slug, "keeper", f"I could not answer: {_why(e)}", section)
            ideas.save_state(self.state_dir, slug, error=_why(e))
            return
        answer = first_json(out)
        if answer is None:                           # plain words: kept as the reply, nothing written
            answer = {"reply": out}
        sections = answer.get("sections") if isinstance(answer.get("sections"), dict) else {}
        written = {n: _words(v, ideas.SECTION_CHARS) for n, v in sections.items()
                   if n in ideas.SECTIONS and n not in ("Decisions", "Stages") and isinstance(v, str)}
        if isinstance(answer.get("questions"), list):
            written["Open questions"] = _bullets(_strings(answer["questions"], 10))
        decisions = _strings(answer.get("decisions"), 10)
        if written or decisions:
            ideas.update(root, slug, written, decisions)
        reply = _words(answer.get("reply"), REPLY_CHARS) or "(the keeper wrote the page and said nothing)"
        ideas.add_turn(self.state_dir, slug, "keeper", reply, section)
        changes: dict[str, Any] = {"session": session or ("" if fresh else st["session"]),
                                   "session_at": dt.datetime.now().isoformat(timespec="seconds"),
                                   "context": self._context(session or st["session"], tokens), "error": ""}
        state = ideas.state(self.state_dir, slug)["state"]
        page = ideas.idea_page(root, slug)
        open_now = bool(page and ideas.items(page.section("Open questions")))
        if state in ("raw", "asks", "ready"):
            changes["state"] = "asks" if open_now else "ready"
        ideas.save_state(self.state_dir, slug, **changes)
        plan = ideas.plan(self.state_dir, slug)
        if written and plan is not None and not plan.get("passed_at"):
            was = self.assess(slug)
            if was is not None:                      # the risk changed: whether it starts is decided again
                self.on_plan(slug)
        if asked and not open_now and plan is None and changes.get("state") == "ready" and not self.hold(slug):
            self._busy[slug] = "planning"            # the person answered the last question: the plan follows at once
            ideas.save_state(self.state_dir, slug, state="planning", error="")
            self.plan_one(slug, "ready")

    # -- the plan: the spec → plan.json -------------------------------------------------------------------

    def plan(self, slug: str, auto: bool = False) -> bool:
        """Re-plan (the person's: refused in a spent window), or a plan that follows by itself (`auto`: it waits
        with `held_until`). False when it was held."""
        root = self.wiki_root()
        if ideas.idea_page(root, slug) is None:
            raise KeeperError("That idea is gone")
        old = ideas.plan(self.state_dir, slug)
        if old and old.get("passed_at"):
            raise KeeperError("Its plan is passed already: the tasks are in work")
        if why := self._may_run():
            raise KeeperError(why)
        if self.busy(slug):
            raise KeeperError("The keeper is busy with this idea: a moment")
        if not auto:
            self.refuse_spent()
        elif self.hold(slug):
            return False
        was = ideas.state(self.state_dir, slug)["state"]
        ideas.save_state(self.state_dir, slug, state="planning", error="", held_until="")
        try:
            self._start(slug, "planning", lambda: self.plan_one(slug, was))
        except KeeperError:
            ideas.save_state(self.state_dir, slug, state=was)
            raise
        return True

    def plan_prompt(self, root: Path, slug: str) -> str:
        page = ideas.idea_page(root, slug)
        return f"""You are the keeper of this project's Task board. This spec goes to work: turn it into a plan. You may
read the repository (read only) to see what the work touches.

The spec:
{page.text()[:PAGE_CHARS]}

Rules:
- At most {MAX_TASKS} tasks. Each is a brief another Claude session can do alone, in a worktree of the repository:
  what to change, where, and how it is tested; it names the Done when lines it proves. `after` only where a task
  needs another's result.
- Each task's type (`kind`): "code", "tests", "docs", "text" (text for people), or "research"; ordinary work is "code".
- Each task's tier, its complexity: "elder" (hard design or a wide change), "warrior" (ordinary code), "laborer"
  (small, mechanical).
- To-dos only for what a task cannot start without: a key ("secret": its title is the environment variable's name,
  e.g. API_KEY), a decision ("choice", with its choices), a yes ("confirm"), steps a person does ("instructions"), a
  file the person gives ("file": its title says what the file is, e.g. the Firebase config, google-services.json;
  `accept` the extensions it may have). Any kind may carry `steps` when the person has to do something first. Most
  plans need none. `for`: the tasks that wait for it.

Answer with one JSON object and nothing else:
{{"tasks": [{{"id": "k1", "title": "…", "brief": "…", "kind": "code", "tier": "warrior", "after": []}}],
 "todos": [{{"id": "t1", "title": "…", "kind": "confirm", "why": "…", "choices": [], "steps": [], "accept": [], "for": ["k1"]}}]}}
"""

    def plan_one(self, slug: str, was: str = "ready") -> None:
        """The plan, resuming the idea's session; its Stages and risk written, its estimate by the tiers the tasks will
        run on; then whether it starts by itself is the face's (`on_plan`)."""
        root = self.wiki_root()
        back = was if was in ("raw", "asks", "ready", "plan", "failed") else "ready"
        st = ideas.state(self.state_dir, slug)
        fresh = self.fresh(st)
        try:
            text, _cost, tokens, session = self.ask("plan", self.plan_prompt(root, slug), "" if fresh else st["session"])
            data = make_plan(slug, first_json(text))
            target = self.target()
            runs = [idea_target.tier_of(idea_target.task_pick(t["tier"], target, str(roles.role_for(self.state_dir, t["kind"]).get("model") or ""))[0])
                    for t in data["tasks"]]
            data["estimate"] = estimate(data["tasks"], runs)
            ideas.save_plan(self.state_dir, slug, data)
        except Exception as e:
            ideas.save_state(self.state_dir, slug, state=back, error="" if isinstance(e, InterruptedError) else f"No plan: {_why(e)}",
                             **({"queue": "hold"} if isinstance(e, InterruptedError) else {}))
            return
        self.write_stages(slug, data)
        self.assess(slug)
        if session:
            ideas.save_state(self.state_dir, slug, session=session, session_at=dt.datetime.now().isoformat(timespec="seconds"),
                             context=self._context(session, tokens))
        ideas.save_state(self.state_dir, slug, state="plan", error="", held_until="")
        self.publish(slug)
        self.on_plan(slug)


def make_plan(slug: str, answer: dict | None, made_at: str = "") -> dict:
    """plan.json from the model's answer, strictly: at most 8 tasks with their ids renamed k1…, `after` only to an
    earlier task, known tiers and kinds; the estimate from the tiers' default cost, ±50 %."""
    if not isinstance(answer, dict) or not isinstance(answer.get("tasks"), list):
        raise KeeperError("the keeper's answer was not a plan")
    names: dict[str, str] = {}
    tasks: list[dict] = []
    for raw in answer["tasks"]:
        if not isinstance(raw, dict) or len(tasks) >= MAX_TASKS:
            continue
        title, brief = _words(raw.get("title"), 200), _words(raw.get("brief"), 6000)
        if not title or not brief:
            continue
        tid = f"k{len(tasks) + 1}"
        after = [names[a] for a in _strings(raw.get("after"), MAX_TASKS, 20) if a in names]
        names[_words(raw.get("id"), 20) or tid] = tid
        tier = raw.get("tier") if raw.get("tier") in TIERS else "warrior"
        kind = raw.get("kind") if raw.get("kind") in roles.TASK_KINDS else roles.DEFAULT_KIND
        tasks.append({"id": tid, "title": title, "brief": brief, "kind": kind, "tier": tier, "after": list(dict.fromkeys(after)),
                      "state": "waiting", "branch": "", "commit": "", "session": "", "cost": None, "tokens": None,
                      "started": "", "finished": "", "error": "", "note": ""})
    if not tasks:
        raise KeeperError("the plan had no task")
    todos: list[dict] = []
    for raw in answer.get("todos") if isinstance(answer.get("todos"), list) else []:
        if not isinstance(raw, dict) or len(todos) >= MAX_TODOS or raw.get("kind") not in KINDS:
            continue
        title = _words(raw.get("title"), 200)
        if raw["kind"] == "secret":
            title = re.sub(r"[^A-Z0-9_]+", "_", title.upper()).strip("_")
            if not ENV_NAME.match(title):
                continue
        if not title:
            continue
        for_ = [names[f] for f in _strings(raw.get("for"), MAX_TASKS, 20) if f in names]
        todo = {"id": f"t{len(todos) + 1}", "title": title, "kind": raw["kind"],
                "why": _words(raw.get("why"), 500),
                "choices": _strings(raw.get("choices"), 8, 200) if raw["kind"] == "choice" else [],
                "steps": _strings(raw.get("steps"), 12, 500),         # steps on any kind (spec 35 §9)
                "for": list(dict.fromkeys(for_)), "done": False, "value": None}
        if raw["kind"] == "file":
            todo["accept"] = [re.sub(r"[^a-z0-9]", "", a.lower())[:10] for a in _strings(raw.get("accept"), 8, 20)
                              if re.sub(r"[^a-z0-9]", "", a.lower())]
        todos.append(todo)
    data = {"idea": slug, "made_at": made_at or dt.datetime.now().isoformat(timespec="seconds"), "passed_at": None,
            "estimate": estimate(tasks), "todos": todos, "tasks": tasks}
    readiness(data)
    return data


def estimate(tasks: list[dict], tiers: list[str] | None = None) -> dict:
    """The price range of the tasks, counted on the tiers they will run on (`tiers`, else their planned ones)."""
    tiers = tiers if tiers is not None else [t.get("tier", "warrior") for t in tasks]
    base = sum(plans.DEFAULT_COST.get(tier, plans.DEFAULT_COST["warrior"]) for tier in tiers)
    return {"tasks": len(tasks), "usd_low": round(base * 0.5, 2), "usd_high": round(base * 1.5, 2)}


def readiness(data: dict) -> None:
    """A task not started yet is `ready` when what it waits for is done (its `after`, its to-dos), else `waiting`."""
    merged = {t["id"] for t in data.get("tasks") or [] if t.get("state") == "merged"}
    blocked = {f for td in data.get("todos") or [] if not td.get("done") for f in td.get("for") or []}
    for t in data.get("tasks") or []:
        if t.get("state") in ("waiting", "ready"):
            t["state"] = "ready" if set(t.get("after") or []) <= merged and t["id"] not in blocked else "waiting"


def _why(e: Exception) -> str:
    if isinstance(e, InterruptedError):
        return "stopped"
    return (str(e) or type(e).__name__).strip()[:300]
