"""The board's host commands (spec 29a §6): tracks and ideas from the Wiki, the keeper, the runner.

    ideas = Ideas(host)
    host.commands.update(ideas.commands())     # ideas.board, ideas.page, ideas.add, … (the phone may call them all)
    ideas.tick(now)                            # the host's clock: the keeper's batch, the runner's tick
    ideas.snapshot()                           # focus, ideas_rev, needs_you, review_count, limits, reserve: in the snapshot
    ideas.stop_all()                           # Stop all

The pages live in the Wiki joined to the board (`realm/ideas.py`), what runs on them in `.orkcraft/ideas/`. The
keeper (`core/idea_keeper.py`) reads, talks and plans in the background; the runner (`core/idea_runner.py`, spec 29a
part B) carries a passed plan's tasks to `main`. Every change bumps `ideas_rev`, so the board and the phone know to
look again.

Spec 33 adds Review: the results waiting for the person (`ideas.review_list`, `ideas.diff`), their three answers
(`ideas.merge`, `ideas.back`, `ideas.drop_task`), `ideas.stop_task`, the Agents window (`ideas.agents`), one task
with its log (`ideas.task`) and the branch results merge into (`ideas.into`).

Spec 35: an idea needs a goal and is drafted at once (High, Normal) or at night (Low); the board, Needs you, autostart
and the Board's own commands are in gui/ideas_board.py; a file to-do's file is kept beside the secrets.

Spec 49: the gate, dev → main (`ideas.gate`, `ideas.gate_merge`: gui/ideas_gate.py), today's events (`ideas.today`:
gui/ideas_recap.py) and the reserve in the snapshot.

Spec 37 §8: the Board's settings are the project's (`BoardHost.board_settings`: `<repo>/.orkcraft/board.json` over the
machine's `ideas`), read through `settings_now()` and written with `save_settings()`.
"""
from __future__ import annotations

import base64
import datetime as dt
import os
import time
from pathlib import Path
from typing import Any, Callable

from orkboard import settings
from orkboard.core import idea_keeper
from orkboard.realm import event_log, idea_checks, idea_element, idea_lens, idea_photos, idea_secrets, idea_target, ideas, wiki
from orkboard.gui.ideas_args import VIA, IdeasError, _device, _opt, _str, _text
from orkboard.gui.ideas_board import BoardMixin
from orkboard.gui.ideas_gate import GateMixin
from orkboard.gui.ideas_goals import GoalsMixin
from orkboard.gui.ideas_map import MapMixin
from orkboard.gui.ideas_party import PartyMixin
from orkboard.gui.ideas_recap import RecapMixin
from orkboard.gui.ideas_review import ReviewMixin
from orkboard.gui.ideas_lens import LensMixin
from orkboard.gui.ideas_limits import LimitsMixin
from orkboard.gui.ideas_roles import RolesMixin

RUNNER_TICK_S = 3.0               # how often the runner looks at its tasks
SNAPSHOT_S = 10.0                 # the most a cached Needs you count is kept without a change
PHONE_ZIP_MAX = 8 * 1024 * 1024   # a zip the phone is handed in a message: larger waits for the computer
OPENED = ("idea", "plan", "todo", "task", "result", "tab", "map", "recap", "flag", "week", "push", "party", "gate", "today")


def focus_of(machine) -> str:
    """The focus the window and the phone show: `ORKCRAFT_FOCUS` when set ("" the whole town, "board"), else the
    machine's setting. Tests set it to "" (tests/conftest.py), so the town's own suites see the town."""
    env = os.environ.get("ORKCRAFT_FOCUS")
    return env if env in settings.FOCUSES else machine.focus


class _Settings:
    """The settings as the runner reads them (`ideas.<key>`): the project's Board settings, read when asked."""

    def __init__(self, host) -> None:
        self.host = host

    @property
    def ideas(self) -> dict:
        return self.host.board_settings()


class _Hop:
    """The bus as the runner gets it: a publish from its thread is made on the host's (`BoardHost.call`)."""

    def __init__(self, host) -> None:
        self.host = host

    def publish(self, topic: str, **data: Any) -> None:
        self.host.call(lambda: self.host.publish(topic, **data))


class Ideas(LensMixin, LimitsMixin, GateMixin, GoalsMixin, MapMixin, PartyMixin, RecapMixin, RolesMixin, ReviewMixin, BoardMixin):
    def __init__(self, host) -> None:
        """`host`: what the Board needs of whoever runs it, a `gui/board_host.py` `BoardHost` (spec 37 §4): Orkline's
        host makes one from its town, Orkboard its own."""
        self.host = host
        self.state_dir = Path(self.host.repo_root) / ".orkcraft"
        self.rev = 0
        self._cache: tuple[int, float, dict] | None = None
        self._runner: Any = None
        self._runner_error = ""
        self._runner_at = 0.0
        self._limits: list[dict] = []
        self._limits_at = float("-inf")
        self._limits_busy = False
        self._seen: dict[str, tuple[str, float]] = {}     # slug → (state, when it began): keeper_state
        self._what: dict[str, str] = {}                   # slug → what its next Board commit says (spec 35 §13)
        self._limits_logged = float("-inf")
        self.keeper = idea_keeper.IdeaKeeper(
            self.host.repo_root, self.state_dir, self.keeper_root, self.settings_now, self._publish,
            demo=bool(self.host.demo), budget_ok=lambda: self.host.budget_ok(), limits=lambda: list(self.host.limits() or []),
            on_plan=self._on_plan, start_night=self.start_night, events=not self.host.demo)
        self.keeper.index_root = self.wiki
        self.host.bus.subscribe(idea_keeper.CHANGED, self._changed)

    # -- the project's Board settings (spec 37 §8) --------------------------------------------------------------

    def settings_now(self) -> dict:
        """The Board's settings of this project: its `board.json` over the machine's `ideas`."""
        return self.host.board_settings()

    def save_settings(self, values: dict) -> dict:
        """The Board's settings written for this project (never the machine's); what is kept."""
        return self.host.save_board_settings(values)

    # -- where the pages are --------------------------------------------------------------------------------

    def root(self, make: bool = True) -> Path:
        """Where the Board's pages are: its own tree on the work branch (spec 35 §13, gui/ideas_board.py), else the Wiki
        joined to the board. `make`: the tree is made (and the pages moved into it) when missing; the snapshot only reads."""
        return self.tree_root(self.wiki(), make)

    def keeper_root(self) -> Path:
        """The keeper's (its clock, the night): the Board's tree is made only for a Board that has pages already."""
        wiki = self.wiki()
        used = any((wiki / f).is_dir() and any((wiki / f).glob("*.md")) for f in (ideas.TRACKS, ideas.IDEAS))
        return self.tree_root(wiki, make=used)

    def wiki(self) -> Path:
        """The Wiki joined to the board: `ideas.wiki` (a folder in the repository) when it is set, else the one the
        host finds (Orkline's: the Task board's `wiki`, else the camp's first Wiki, `BoardHost.wiki_of`), else
        `llm-wiki/general/` in the repository (spec 37 §3.5). The keeper reads its index here."""
        repo = Path(self.host.repo_root)
        own = str(self.settings_now().get("wiki") or "")
        if own:
            return repo / own
        found = self.host.wiki_of() if self.host.wiki_of is not None else None
        return Path(found) if found is not None else wiki.root_of(repo, None, "general")

    # -- the bus, the clock, the snapshot ------------------------------------------------------------------

    def _publish(self, slug: str) -> None:
        """From the keeper's thread: `ideas.changed` on the host's."""
        self.host.call(lambda: self.host.publish(idea_keeper.CHANGED, slug=slug))

    def _changed(self, event) -> None:
        self.rev += 1
        slug = str((getattr(event, "data", None) or {}).get("slug") or "")
        if slug:
            try:
                if slug.startswith("goal:"):
                    self.goal_event(slug[5:])
                else:
                    self._state_event(slug)
            except Exception:                   # a log never stops the board
                pass
        self.tree_note(slug)

    # -- the event log (spec 33 §9): every action of the shell, for the day's analysis ------------------------

    def _ev(self, event: str, args: dict | None = None, **fields: Any) -> None:
        """One line of `.orkcraft/usage/events.jsonl`; none in the demo. `device`: "phone" (put there by the listener) or "desktop"."""
        if not self.host.demo:
            if args is not None:
                fields["device"] = _device(args)
            event_log.record(Path(self.host.repo_root), event, **fields)

    def _state_event(self, slug: str) -> None:
        """`keeper_state` when an idea's state changed, and `plan_made` when it reaches `plan`."""
        state = str(ideas.state(self.state_dir, slug).get("state") or "")
        now = time.monotonic()
        was, since = self._seen.get(slug, ("", None))
        if state == was:
            return
        self._seen[slug] = (state, now)
        what = {"plan": "planned", "proposed": "proposed"}.get(state) or ("drafted" if was == "reading" and state in ("asks", "ready") else "")
        if what:
            self._what.setdefault(slug, what)
        self._ev(event_log.KEEPER_STATE, idea=slug, state=state, was=was, seconds=round(now - since, 1) if since else None)
        if state == "done" and was and was != "done":
            self._flag_when_done(slug)             # a goal done where there is no gate, or with its commits in main already (spec 50 §2.2)
        if state == "plan":
            plan = ideas.plan(self.state_dir, slug) or {}
            est = plan.get("estimate") or {}
            m = ideas.state(self.state_dir, slug).get("measure") or {}
            self._ev(event_log.PLAN_MADE, idea=slug, tasks=len(plan.get("tasks") or []), todos=len(plan.get("todos") or []),
                     usd_low=est.get("usd_low"), usd_high=est.get("usd_high"),
                     **{k: m.get(k) for k in ("step", "prompt_chars", "tokens", "cost")} if m.get("step") == "plan" else
                     {"step": "plan", "prompt_chars": None, "tokens": None, "cost": None})

    def _since(self, iso: object) -> float | None:
        try:
            return round(max(0.0, time.time() - dt.datetime.fromisoformat(str(iso)).timestamp()), 1)
        except ValueError:
            return None

    def changed(self, slug: str) -> None:
        self.host.publish(idea_keeper.CHANGED, slug=slug)

    def runner(self, need: bool = False):
        """The runner (spec 29a part B), made once; None while this build has none (`need`: say so instead)."""
        if self._runner is None and not self._runner_error:
            try:
                from orkboard.core.idea_runner import IdeaRunner
                self._runner = IdeaRunner(self.host.repo_root, self.state_dir, _Settings(self.host), _Hop(self.host),
                                          events=not self.host.demo, on_held=lambda: self.log_limits(force=True),
                                          rank=self.rank)
            except ImportError:
                self._runner_error = "The runner is not in this build yet: plans cannot start"
            except Exception as e:              # a runner that cannot start never stops the board
                self._runner_error = f"The runner could not start: {e}"
        if self._runner is None and need:
            raise IdeasError(self._runner_error)
        return self._runner

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.tree_flush()
        try:
            self.keeper.tick()
        except Exception as e:                  # the keeper's batch never stops the clock
            self.host.toast(f"{type(e).__name__}: {e}", title="The keeper", severity="error")
        if now - self._runner_at >= RUNNER_TICK_S:
            self._runner_at = now
            runner = self.runner() if self._ever_passed() else self._runner
            if runner is not None:
                try:
                    runner.tick()
                except Exception as e:
                    self.host.toast(f"{type(e).__name__}: {e}", title="The runner", severity="error")

    def _ever_passed(self) -> bool:
        folder = self.state_dir / "ideas"
        return folder.is_dir() and any((p / "plan.json").exists() for p in folder.iterdir() if p.is_dir())

    def running(self) -> int:
        """How many of the project's tasks are running now (Close project asks first when some are)."""
        return len(getattr(self._runner, "_runs", {}) or {})

    def stop_all(self, device: str = "desktop") -> None:
        self._ev(event_log.STOP_ALL, count=self.running(), device=device or "desktop")
        self.keeper.stop_all()
        if self._runner is not None:
            try:
                self._runner.stop_all()
            except Exception:
                pass

    def snapshot(self) -> dict[str, Any]:
        """What the page's snapshot carries of the board: the focus, the rev, how many ideas need the person, and
        each idea's state (what a push says when it changes: gui/mobile.py `news`)."""
        now = time.monotonic()
        if self._cache is None or self._cache[0] != self.rev or now - self._cache[1] > SNAPSHOT_S:
            try:
                b = self.board(make=False)       # reads only: no tree is made for a snapshot
                waiting = self.results()
                data = {"needs_you": sum(1 for n in b["needs_you"] if n["kind"] not in ("proposal", "party")),
                        "idea_states": [{"slug": i["slug"], "title": i["title"], "state": i["state"]} for i in b["ideas"]],
                        "review_count": len(waiting),
                        "review_results": [{k: r[k] for k in ("idea", "task", "title")} for r in waiting]}
            except Exception:                   # a broken page never breaks the town's snapshot
                data = {"needs_you": 0, "idea_states": [], "review_count": 0, "review_results": []}
            self._cache = (self.rev, now, data)
        return {"focus": focus_of(self.host.machine), "ideas_rev": self.rev, **self._cache[2],
                "limits": self.limits(), "reserve": self.reserve()}

    def reserve(self) -> dict[str, Any]:
        """`{share, night}` (spec 49 §2.3): the part of the AI tool's window the Board keeps from work that starts by
        itself right now (the day's, inside the night window the night's), and whether the night window holds now. It is
        read at each snapshot: the clock moves it, not a change."""
        s = self.settings_now()
        night = idea_target.in_night(str(s.get("night") or settings.IDEAS["night"]))
        return {"share": idea_target.reserve(s, night), "night": night}

    # -- reading -------------------------------------------------------------------------------------------

    def _state(self, slug: str) -> dict:
        st = ideas.state(self.state_dir, slug)
        if st["state"] in ("reading", "planning") and not self.keeper.busy(slug):
            st["state"] = "raw" if st["state"] == "reading" else "ready"     # a run the host lost (it closed)
        return st

    def page(self, slug: str) -> dict[str, Any]:
        root = self.root()
        page = ideas.idea_page(root, slug)
        if page is None:
            raise IdeasError("That idea is gone")
        names = list(ideas.SECTIONS) + [n for n, _t in page.sections if n not in ideas.SECTIONS]
        st = self._state(slug)
        plan = ideas.plan(self.state_dir, slug)
        checks = idea_checks.status(self.keeper.idea_checks(root, slug), self.keeper.team_checks(root, slug),
                                    (plan or {}).get("tasks") or [])
        return {"slug": slug, "title": page.title or slug, "track": page.get("track") or ideas.GENERAL, "checks": checks,
                "state": st["state"], "size": page.get("size") if page.get("size") in ideas.SIZES else "",
                "sections": [{"name": n, "thesis": ideas.thesis(page.section(n)), "text": page.section(n)}
                             for n in names],
                "talk": ideas.talk(self.state_dir, slug), "plan": self._with_heads(plan),
                "busy": bool(self.keeper.busy(slug)) or st["state"] in ("reading", "planning"),
                "state_error": st.get("error", ""), "proposed_track": page.get("proposed_track"),
                "lens": idea_lens.read(self.state_dir, slug)}

    # -- writing -------------------------------------------------------------------------------------------

    def add(self, args: dict) -> dict:
        """An idea: a text, its goal (never General: that is the system's) and a priority (default the goal's). High
        and Normal are drafted at once, Low and a closed dialog's (`night`) wait for the night (spec 35 §3). `photos`
        (the phone's, base64) are kept beside it for the Taskmaster to read (realm/idea_photos.py), and `lens`, what the
        person pointed at with the lens of the goal's party (realm/idea_lens.py)."""
        text = _text(args, "text", ideas.SECTION_CHARS)
        track = _opt(args, "track")
        goals = {t["slug"]: t for t in ideas.tracks(self.root(), make=False)}
        if not track or track == ideas.GENERAL:
            raise IdeasError("An idea needs a goal")
        if track not in goals:
            raise IdeasError("That goal is gone")
        priority = _opt(args, "priority").lower() or goals[track]["priority"]
        if priority not in ideas.PRIORITIES:
            raise IdeasError("Priority is High, Normal or Low")
        try:
            photos = idea_photos.decode(args.get("photos"))
        except ValueError as e:
            raise IdeasError(str(e)) from None
        pointed = self._lens_args(args)
        queue = "night" if priority == "low" or args.get("night") is True else "now"
        slug = ideas.add_idea(self.root(), text, track, self.state_dir, priority, queue,
                              night_by="person" if args.get("night") is True else "board")      # a Low idea the Board puts off itself; the person's own night is theirs (spec 44 §2)
        for raw in photos:
            idea_photos.put(self.state_dir, slug, raw)
        idea_lens.save(self.state_dir, slug, pointed)
        element = idea_element.give(self.root(), self.state_dir, slug)    # the mark of every card of it (spec 50 §2.3)
        ideas.add_turn(self.state_dir, slug, "you", text, "Gist")     # the person's own words, kept
        self._ev(event_log.IDEA_ADDED, args, idea=slug, track=track, chars=len(text), now=queue == "now",
                 priority=priority, queue=queue, photos=len(photos), lens=[a["kind"] for a in pointed])
        out = {"slug": slug, "queue": queue, "element": element}
        if queue == "now":                      # drafted at once, in the background (held in a spent window)
            try:
                self.keeper.draft(slug)
            except idea_keeper.KeeperError as e:
                ideas.save_state(self.state_dir, slug, error=str(e))
                out["error"] = str(e)
        self.changed(slug)
        return out

    def say(self, args: dict) -> dict:
        slug = _text(args, "slug", 100)
        text = _text(args, "text", ideas.SECTION_CHARS)
        if args.get("goal") is True or (ideas.idea_page(self.root(), slug) is None and ideas.track_page(self.root(), slug)):
            self._read_goal(slug, text)         # the answer to a goal's questions: the same talk, on the goal
            self._ev(event_log.IDEA_SAID, args, idea=f"goal:{slug}", section="", chars=len(text), text=text)
            self.changed(f"goal:{slug}")
            return {"ok": True}
        self.keeper.say(slug, text, _opt(args, "section"), _device(args))     # its `idea_said` is the keeper's, measured
        self.changed(slug)
        return {"ok": True}

    def plan(self, args: dict) -> dict:
        slug = _text(args, "slug", 100)
        self.keeper.plan(slug)
        self.changed(slug)
        return {"ok": True}

    def start(self, args: dict) -> dict:
        """The person passes the plan (`passed_by: "person"`): it is the runner's from now on, and it starts."""
        slug = _text(args, "slug", 100)
        if ideas.plan(self.state_dir, slug) is None:
            raise IdeasError("This idea has no plan yet: Take it to work first")
        st = self._state(slug)["state"]
        if st not in ("plan", "failed", "working"):
            raise IdeasError("Its plan is not ready")
        self.pass_plan(slug, "person", args=args)
        self.changed(slug)
        return {"ok": True}

    def stop(self, args: dict) -> dict:
        """The person stops a plan's work: from then on it waits for them (autostart never starts it again)."""
        slug = _text(args, "slug", 100)
        self.runner(need=True).stop(slug)
        if ideas.plan(self.state_dir, slug) is not None:
            ideas.edit_plan(self.state_dir, slug, lambda p: p.update(stopped=True))
        self.changed(slug)
        return {"ok": True}

    def move(self, args: dict) -> dict:
        slug = _text(args, "slug", 100)
        ideas.move(self.root(), slug, _opt(args, "track") or None, _opt(args, "before") or None, by="person")
        self._what[slug] = "moved"
        self.changed(slug)
        return {"ok": True}

    def edit(self, args: dict) -> dict:
        """A section written by hand, or (`priority` without a section) the idea's priority: a plan waiting is then
        decided again (spec 35 §5)."""
        slug = _text(args, "slug", 100)
        if "priority" in args and "section" not in args:
            priority = _opt(args, "priority").lower()
            if priority not in ideas.PRIORITIES or ideas.idea_page(self.root(), slug) is None:
                raise IdeasError("Priority is High, Normal or Low")
            ideas.set_meta(self.root(), slug, priority=priority)
            self.autostart(slug)
            self.changed(slug)
            return {"ok": True}
        if self.keeper.busy(slug):
            raise IdeasError("The keeper is writing this idea: a moment")
        ideas.set_section(self.root(), slug, _text(args, "section", 60), _str(args, "text", ideas.SECTION_CHARS))
        self.changed(slug)
        return {"ok": True}

    def track_add(self, args: dict) -> dict:
        slug = ideas.add_track(self.root(), _text(args, "title", ideas.TITLE_CHARS))
        self.changed("")
        return {"slug": slug}

    def track_set(self, args: dict) -> dict:
        criteria = args.get("criteria")
        if criteria is not None and not isinstance(criteria, list):
            raise IdeasError("Success criteria are a list")
        about, deadline = args.get("about"), args.get("deadline")
        ideas.set_track(self.root(), _text(args, "slug", 100),
                        about=str(about)[:ideas.SECTION_CHARS] if isinstance(about, str) else None,
                        criteria=criteria, deadline=str(deadline) if isinstance(deadline, str) else None)
        self.changed("")
        return {"ok": True}

    def todo(self, args: dict) -> dict:
        """A to-do of a plan ticked (or unticked). A secret's value goes to the machine's secret store; the plan
        says only "stored". This is the one write to a passed plan: the runner reads the to-do as done."""
        slug, tid = _text(args, "idea", 100), _text(args, "id", 20)
        plan = ideas.plan(self.state_dir, slug)
        todo = next((t for t in (plan or {}).get("todos") or [] if t.get("id") == tid), None)
        if todo is None:
            raise IdeasError("That to-do is gone")
        done, value = bool(args.get("done")), args.get("value")
        kept: Any = todo.get("value")
        if done and todo.get("kind") == "file":
            kept = self._todo_file(args, slug, todo)
        elif done and todo.get("kind") == "secret":
            if not isinstance(value, str) or not value.strip():
                if todo.get("value") != "stored":
                    raise IdeasError("A secret needs its value")
            else:
                idea_secrets.put(self.state_dir, slug, tid, value.strip())
                kept = "stored"
        elif done and todo.get("kind") == "choice":
            if value not in (todo.get("choices") or []):
                raise IdeasError("Pick one of its choices")
            kept = value
        elif isinstance(value, str) and value.strip():
            kept = value.strip()[:500]

        def tick(p: dict) -> None:
            for t in p.get("todos") or []:
                if t.get("id") == tid:
                    t["done"], t["value"] = done, kept
            if not p.get("passed_at"):
                idea_keeper.readiness(p)

        ideas.edit_plan(self.state_dir, slug, tick)
        if done:                                # a secret's value (or a file) is never logged: only that it was done
            self._ev(event_log.TODO_DONE, args, idea=slug, todo=tid, kind=todo.get("kind"), seconds=self._since(plan.get("made_at")))
        self.changed(slug)
        return {"ok": True}

    def drop(self, args: dict) -> dict:
        slug = _text(args, "slug", 100)
        if self.keeper.busy(slug):
            raise IdeasError("The keeper is busy with this idea: a moment")
        plan = ideas.plan(self.state_dir, slug) or {}
        if self._runner is not None and plan.get("passed_at"):
            self._runner.stop(slug)
        secrets = [t["id"] for t in plan.get("todos") or [] if t.get("kind") == "secret" and t.get("id")]
        ideas.drop(self.root(), slug, self.state_dir)
        idea_secrets.forget(self.state_dir, slug, secrets)
        idea_secrets.forget_files(self.state_dir, slug)
        self.changed(slug)
        return {"ok": True}

    def log(self, args: dict) -> dict:
        """`ideas.log`: the shell's one event, `opened` — a preview or a tab the person opened. Any other event is refused."""
        if args.get("event") != event_log.OPENED:
            raise IdeasError("Only `opened` can be logged from here")
        what, ref = _opt(args, "what"), _opt(args, "ref")
        if what not in OPENED:
            raise IdeasError(f"`what` is one of {', '.join(OPENED)}")
        via = _opt(args, "via")
        if via and via not in VIA:
            raise IdeasError(f"`via` is one of {', '.join(VIA)}")
        self._ev(event_log.OPENED, args, what=what, ref=ref, via=via)
        return {"ok": True}

    def logs(self, args: dict) -> dict:
        """The day's logs (or the last `days`) as the analytics zip, for a phone: {"name", "data": base64}. The computer's
        gear downloads the same zip from `/api/analytics`."""
        days = args.get("days")
        got = self.host.day_logs.pack_period(days if isinstance(days, int) and not isinstance(days, bool) and days > 0 else 1)
        if got is None:
            raise IdeasError("No logs yet")
        name, data = got
        if len(data) > PHONE_ZIP_MAX:
            raise IdeasError("The logs are too large for the phone: download them on the computer")
        return {"name": name, "data": base64.b64encode(data).decode("ascii")}

    def commands(self) -> dict[str, Callable[[dict], Any]]:
        def guarded(fn):
            def run(args: dict) -> Any:
                try:
                    return fn(args)
                except (ValueError, idea_keeper.KeeperError) as e:
                    raise IdeasError(str(e)) from None
                except Exception as e:
                    if type(e).__name__ != "RunnerError":      # the runner is loaded on demand: no import here
                        raise
                    raise IdeasError(str(e)) from None
            return run

        table = {"ideas.board": lambda a: self.board(), "ideas.map": self.map, "ideas.recap": self.recap, "ideas.flags": self.flags, "ideas.week_work": self.week_work, "ideas.week": self.week, "ideas.party": self.party, "ideas.party_price": self.party_price, "ideas.party_answer": self.party_answer, "ideas.parties": self.parties, "ideas.party_save": self.party_save, "ideas.party_drop": self.party_drop, "ideas.page": lambda a: self.page(_text(a, "slug", 100)),
                 "ideas.add": self.add, "ideas.say": self.say, "ideas.plan": self.plan, "ideas.start": self.start,
                 "ideas.move": self.move, "ideas.edit": self.edit, "ideas.track_add": self.track_add,
                 "ideas.track_set": self.track_set, "ideas.todo": self.todo, "ideas.drop": self.drop,
                 "ideas.stop": self.stop, "ideas.review_list": self.review_list, "ideas.diff": self.diff,
                 "ideas.merge": self.merge, "ideas.back": self.back, "ideas.drop_task": self.drop_task,
                 "ideas.stop_task": self.stop_task, "ideas.agents": self.agents, "ideas.task": self.task,
                 "ideas.into": self.into, "ideas.log": self.log, "ideas.logs": self.logs, "ideas.goal_save": self.goal_save,
                 "ideas.words": self.words, "ideas.goal_accept": self.goal_accept,
                 "ideas.goal": self.goal, "ideas.read_now": self.read_now, "ideas.doc": self.doc, "ideas.roles": self.roles,
                 "ideas.role_save": self.role_save, "ideas.role_add": self.role_add, "ideas.role_drop": self.role_drop,
                 "ideas.kind_set": self.kind_set,
                 "ideas.queue": self.queue, "ideas.read_stop": self.read_stop, "ideas.start_now": self.start_now,
                 "ideas.proposal": self.proposal, "ideas.board_set": self.board_set, "ideas.answer": self.answer,
                 "ideas.spend": self.spend, "ideas.lens": self.lens, "ideas.lens_code": self.lens_code,
                 "ideas.lens_screen": self.lens_screen, "ideas.check_skip": self.check_skip,
                 "ideas.gate": self.gate, "ideas.gate_merge": self.gate_merge, "ideas.today": self.today}
        return {name: guarded(fn) for name, fn in table.items()}

