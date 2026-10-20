"""Operations' runner (docs/specs/38-operations.md §1, §3–§7): an operation added from a template is prepared by one
call, checked by the person, and done by one more call allowed only the one tool that does it.

    runner = OpRunner(op_runs.root(), settings=lambda: machine.ops, limits=lambda: host.limits(),
                      publish=lambda op="", template="": ...)
    runner.start()                         # what the host lost when it closed: a prepare again, an action failed
    op_id = runner.add("jira-task", {"what": "…"}, device="desktop")
    runner.act(op_id, fields, draft)       # the check passed, as corrected
    runner.tick()                          # the host's clock: what the limits held runs again; the old texts go
    runner.stop_all()                      # Stop all: every operation's call is cancelled

- **One job per call** (§4): `op_prepare` reads with its template's tools and changes nothing; `op_act` is allowed
  only the action's tool, and code reads its events to tell what it did; `op_learn` has no tools. Each is a fresh
  `claude -p` in `ops/work/`, its tier, effort and budget from Operations' Target (realm/idea_target.py), its prompt
  and output kept under `ops/calls/` only, its telemetry line in `ops/ledger.jsonl` (`call_log.apart`, on its own
  thread: a project's call made meanwhile stays the project's), its ledger line in `ops/spend.jsonl`.
- **Nothing is done twice by Orkboard** (§3): an action that may have run (`acted` true or null) is never tried again.
- **By itself** (§6): a clean check sends the template by itself; a correction, Not right, a new version or Check
  again sends it back; a doubt, a `high` risk or the day's cap stop it at the check (realm/op_runs.py).
- **The limits** (§1): in a spent window (`status.NEARLY`) a call is not made, the operation waits with
  `held_until`; the person's own operations keep no reserve. **The person's cap**: while the day's spend across the
  open projects and Operations reached the smallest of their caps (core/treasury.py `persons_cap`), no call is made
  either: the operation waits (*waits: the day's spend cap is reached*) and the person's press is refused.
- **A learn call held** by a spent window or the cap waits in `ops/templates/<name>/learn.json` and runs after a
  restart too.
- At most MAX_PARALLEL calls at once; the rest wait in order. No face: what changed is published.

The person's commands (add, the check's action, Prepare again, Stop, Drop, …) are core/op_commands.py's.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable

from orkboard.core import treasury
from orkboard.core.idea_keeper import first_json
from orkboard.core.op_commands import CAP_WAITS, CommandsMixin, OpsError
from orkboard.core.sign_ins import HOLD_H
from orkboard.realm import (call_log, event_log, harnesses, idea_spend, idea_target, jobs, op_runs, op_templates, status,
                            tool_errors)
from orkboard.realm.op_templates import Template

HARNESS = "claude"
MAX_PARALLEL = 2
TICK_S = 20.0
SKILL_CHARS, RULES_CHARS, CHANGE_CHARS = 6000, 2000, 2000
MAX_FOUND, MAX_DOUBTS, LINE_CHARS = 6, 5, 300
PREPARE_LINE = ("You prepare one operation of the person's from the template below, in one go. Use only the tools "
                "listed; change nothing; put into doubts whatever you are not sure of: a possible duplicate, a value you "
                "could not find, a guess. Never call the action's tool: write its arguments from its schema. Answer "
                "with one JSON object and nothing else.\n\n")
LEARN_LINE = ("The person corrected an operation of the template below before it was done (or said it was not right). "
              "Propose rules for every operation of this template, made general from the correction: at most 3 lines, "
              "each at most 200 characters, never a fact of this one operation, none that repeats a rule or a declined "
              "one. Propose none when nothing is general. Answer with one JSON object: "
              '{"rules": ["…"], "why": "…"}\n\n')
SHAPE = ('{"args": {"…": "the action tool\'s arguments"}, "draft": {"<part>": "…"}, '
         '"found": [{"label": "…", "value": "…"}], "doubts": ["…"]}')


def _iso(at: float) -> str:
    return dt.datetime.fromtimestamp(at).isoformat(timespec="seconds")


def _midnight() -> str:
    """The next local midnight: when the day's spend starts again from nothing."""
    today = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return (today + dt.timedelta(days=1)).isoformat(timespec="seconds")


def _same(a: object, b: object) -> bool:
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)


def _line(value: object) -> str:
    return " ".join(str(value).split())[:LINE_CHARS] if isinstance(value, (str, int, float)) \
        and not isinstance(value, bool) else ""


def claude_here() -> bool:
    h = harnesses.get(HARNESS)
    return h is not None and shutil.which(h.bin) is not None


class OpRunner(CommandsMixin):
    def __init__(self, base: Path, settings: Callable[[], dict], limits: Callable[[], list] | None = None,
                 publish: Callable[..., None] = lambda op="", template="": None, demo: bool = False,
                 templates: Callable[[], dict[str, Template]] = op_templates.find,
                 claude: Callable[[], bool] = claude_here,
                 cap: Callable[[], tuple[float, float]] | None = None, sign_ins: Any = None) -> None:
        """`cap`: (the day's spend, the person's cap) its calls are held by (the host's, across the open projects:
        core/treasury.py `persons_cap`); without it, Operations' own spend against the default cap. `sign_ins`: the
        host's sign-ins (core/sign_ins.py): a call whose tool is not signed in is held for it (spec 45 §6)."""
        self.base = Path(base)
        self.settings, self.limits, self.publish = settings, limits or (lambda: []), publish
        self.cap = cap or (lambda: treasury.persons_cap([], op_runs.ledger(self.base)))
        self.demo, self.templates, self.claude = demo, templates, claude
        self.sign_ins = sign_ins
        self._lock = threading.Lock()
        self._queue: list[tuple[str, str]] = []           # (op id or `learn:<template>`, step), in order
        self._running: dict[str, threading.Event] = {}     # key → its call's cancel
        self._learn: dict[str, dict] = {}                  # template → what its learn call is given
        self._tick_at = float("-inf")
        self._forgot = ""

    # -- the settings, the templates, the trust ----------------------------------------------------------------

    def ops(self) -> dict:
        from orkboard import settings
        return settings.clean_ops(self.settings())

    def template(self, name: object) -> Template:
        t = self.templates().get(str(name or ""))
        if t is None:
            raise OpsError("That template is gone")
        return t

    def trust(self, t: Template) -> dict:
        """The template's trust, a new version sending it back to checks (§6)."""
        was = op_runs.trust(self.base, t.name)
        now = op_runs.after_version(was, t.version)
        if now != was:
            op_runs.save_trust(self.base, t.name, now)
            if was.get("alone") and not now["alone"]:
                self._ev(event_log.OP_TRUST, template=t.name, alone=False, why="version")
        return now

    def _set_trust(self, t: Template, new: dict) -> None:
        was = op_runs.trust(self.base, t.name)
        op_runs.save_trust(self.base, t.name, new)
        if bool(was.get("alone")) != bool(new.get("alone")) or (new.get("why") != was.get("why") and not new["alone"]):
            self._ev(event_log.OP_TRUST, template=t.name, alone=bool(new["alone"]), why=new.get("why") or "")
        self.publish(template=t.name)

    def _ev(self, name: str, **fields: Any) -> None:
        if not self.demo:
            op_runs.event(self.base, name, **fields)

    def _run(self, op_id: object) -> dict:
        run = op_runs.load(self.base, str(op_id or ""))
        if run is None:
            raise OpsError("That operation is gone")
        return run

    def _save(self, run: dict) -> None:
        op_runs.save(self.base, run)
        self.publish(op=run["id"])

    # -- the queue -----------------------------------------------------------------------------------------------

    def _enqueue(self, key: str, step: str) -> None:
        with self._lock:
            if all(k != key for k, _ in self._queue):
                self._queue.append((key, step))
        self._launch()

    def _launch(self) -> None:
        """The queue's next, in order, while fewer than MAX_PARALLEL run; a key still running waits its turn (a
        prepare queues its action before its own run has ended)."""
        with self._lock:
            started, n = [], 0
            while n < len(self._queue) and len(self._running) < MAX_PARALLEL:
                key, step = self._queue[n]
                if key in self._running:
                    n += 1
                    continue
                self._queue.pop(n)
                cancel = self._running[key] = threading.Event()
                started.append((key, step, cancel))
        for key, step, cancel in started:
            threading.Thread(target=self._job, args=(key, step, cancel), daemon=True, name=f"op-{step}").start()

    def _job(self, key: str, step: str, cancel: threading.Event) -> None:
        try:
            if step == "learn":
                self._learn_one(key.split(":", 1)[1], cancel)
            elif step == "prepare":
                self._prepare(key, cancel)
            else:
                self._act(key, cancel)
        except Exception as e:                  # an operation never breaks the host
            try:
                if step != "learn":
                    run = self._run(key)
                    self._fail(run, step, f"something failed: {str(e)[:200]}",
                               None if step == "act" else False)
            except OpsError:
                pass
        finally:
            with self._lock:
                self._running.pop(key, None)
            self._launch()

    def running(self) -> list[str]:
        with self._lock:
            return list(self._running)

    def busy(self) -> bool:
        """A call runs or waits in the queue (spec 47: the computer is kept awake meanwhile)."""
        with self._lock:
            return bool(self._queue or self._running)

    def wait_idle(self, timeout: float = 10.0) -> bool:
        """Until nothing runs or waits in the queue (tests, closing)."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            with self._lock:
                if not self._queue and not self._running:
                    return True
            time.sleep(0.02)
        return False

    def window_until(self) -> float | None:
        """When Claude's window comes back, while it is (nearly) spent; no reserve: every operation is the person's."""
        try:
            limits = list(self.limits() or [])
        except Exception:
            limits = []
        return status.reset_of(limits, HARNESS, time.time(), status.NEARLY)

    def capped(self) -> bool:
        """Whether the day's spend reached the person's cap: no call of Operations starts (§1)."""
        try:
            return treasury.over(*self.cap())
        except Exception:                      # a cap that cannot be read holds nothing
            return False

    def signed_out(self) -> bool:
        """Whether the host says Claude Code needs its sign-in: a call waits for it (spec 45 §6)."""
        return self.sign_ins is not None and bool(self.sign_ins.blocked(HARNESS))

    def held_for(self, harness: str) -> int:
        """How many operations wait for this tool's sign-in now."""
        return sum(1 for run in op_runs.runs(self.base) if run.get("state") == "held" and run.get("held_for") == "sign_in"
                   and harness == HARNESS)

    def _held(self, run: dict, step: str) -> bool:
        until = self.window_until()
        if until is not None:
            run.update(state="held", held_until=_iso(until), held=step, why="", held_for="")
        elif self.capped():
            run.update(state="held", held_until=_midnight(), held=step, why=CAP_WAITS, held_for="")
        elif self.signed_out():
            self._hold_sign_in(run, step)
        else:
            return False
        self._save(run)
        return True

    def _hold_sign_in(self, run: dict, step: str, line: str = "") -> None:
        """The run waits for Claude Code's sign-in, at most `HOLD_H` hours; then it fails with `line`."""
        run.update(state="held", held=step, why=line[:LINE_CHARS], held_for="sign_in",
                   held_until=_iso(time.time() + HOLD_H * 3600))

    def _sign_in_failure(self, run: dict, step: str, e: BaseException) -> bool:
        """A call failed for its sign-in (it helps): the run waits for it, instead of failing. False when it did not."""
        err = tool_errors.taken()
        if self.sign_ins is None or err is None or not self.sign_ins.holds(err):
            return False
        self._hold_sign_in(run, step, tool_errors.plainly(err))
        self._save(run)
        return True

    # -- the calls ------------------------------------------------------------------------------------------------

    def _call(self, step: str, prompt: str, allow: list[str], cancel: threading.Event, op_id: str,
              template: str) -> tuple[str, Any, list[dict], dict]:
        """One call on a step: (text, cost, events, its measure). Raises jobs.CallFailed, InterruptedError."""
        target = idea_target.target_of(self.ops())
        tier, effort = idea_target.pick(step, target) or ("warrior", "")
        h = harnesses.need(HARNESS)
        model = h.pick(tier)
        work = op_runs._private_dir(self.base / "work")
        env = {"ORKCRAFT_ORC": f"ops/{step}", "ORKCRAFT_TASK": op_id}
        start = time.monotonic()
        from orkboard.sources import telemetry
        cost: Any = None
        tokens: Any = None
        try:
            tool_errors.taken()                  # a failure of this call is the one `_sign_in_failure` reads
            with call_log.apart(self.base / "calls", "ops", op_runs.ledger(self.base)), telemetry.tagged("plan", "ops"), \
                    tool_errors.doing("op"):
                text, cost, tokens, events = jobs.run_call(HARNESS, prompt, work, cancel, allow, model, env=env,
                                                           effort=effort, budget=idea_target.budget(step, target))
        finally:
            usage = jobs.last_usage()
            op_runs.spend(self.base, {**idea_spend.line(step, "ops", HARNESS, model or tier, tier, effort,
                                                        idea_spend.tokens_of(usage, tokens), cost),
                                      "op": op_id, "template": template})
        measure = {"step": step, "tier": tier, "effort": effort, "prompt_chars": len(prompt),
                   "tokens": usage or ({"total": tokens} if isinstance(tokens, int) else None),
                   "cost": cost if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None,
                   "seconds": round(time.monotonic() - start, 1)}
        if cancel.is_set():
            raise InterruptedError("stopped")
        return text, cost, events, measure

    def _fail(self, run: dict, step: str, why: str, acted: bool | None) -> None:
        run.update(state="failed", why=why, acted=acted, step=step, held="", held_until="", held_for="")
        self._save(run)
        self._ev(event_log.OP_FAILED, op=run["id"], step=f"op_{step}", acted=acted)

    # -- the prepare (§4) ------------------------------------------------------------------------------------------

    def prepare_prompt(self, t: Template, run: dict, tools: list[str], act: str) -> str:
        fields = "\n".join(f"- {f['label']} ({f['name']}): {run['fields'].get(f['name'], '') or '(not given)'}"
                           for f in t.fields)
        draft = "\n".join(f"- {p['name']} — {p['label']}" + (f" (written at args.{p['at']})" if p.get("at") else "")
                          for p in t.draft)
        ats = "\n".join(f"- {f['name']} → args.{f['at']}" for f in t.fields if f.get("at"))
        parts = [("The skill", op_templates.skill_body(t)[:SKILL_CHARS]),
                 ("Its rules (the person's, from earlier corrections)", op_runs.rules(self.base, t.name)[:RULES_CHARS]),
                 ("The fields the person gave", fields),
                 ("The draft parts to write (the person checks them)", draft),
                 ("Fields that code writes into the arguments as given", ats),
                 ("The action's tool (never call it: write its arguments)", act),
                 ("The tools you may read with", ", ".join(tools)),
                 ("Today", dt.date.today().isoformat()),
                 ("The answer's shape", SHAPE)]
        return PREPARE_LINE + idea_target.cut(parts, idea_target.CONTEXT["op_prepare"])

    def _prepare(self, op_id: str, cancel: threading.Event) -> None:
        run = self._run(op_id)
        if run["state"] != "preparing":
            return
        try:
            t = self.template(run["template"])
            tools, act = op_templates.tools(t, self.ops()["servers"])
        except (OpsError, ValueError) as e:
            self._fail(run, "prepare", str(e), False)
            return
        if self._held(run, "prepare"):
            return
        try:
            text, cost, events, measure = self._call("op_prepare", self.prepare_prompt(t, run, tools, act), tools,
                                                     cancel, op_id, t.name)
        except InterruptedError:
            self._fail(self._run(op_id), "prepare", "stopped", False)
            return
        except jobs.CallFailed as e:
            run = self._run(op_id)
            if not self._sign_in_failure(run, "prepare", e):
                self._fail(run, "prepare", str(e)[:300], False)
            return
        run = self._run(op_id)
        if run["state"] != "preparing":
            return
        op_runs.add_cost(run, cost)
        init = next((e["tools"] for e in events if e["type"] == "init"), [])
        missing = next((x for x in [*tools, act] if x not in init), None)
        if missing is not None:
            what = op_templates.what_of(t, missing, self.ops()["servers"])
            self._fail(run, "prepare", f"{what}'s server has no {op_templates.short(missing)}: check the server picked "
                       "in Operations' gear", False)
            return
        answer = first_json(text)
        if answer is None:
            self._fail(run, "prepare", "the answer was not the JSON it was asked for", False)
            return
        keep = {k: v for k, v in (run.get("keep") or {}).items() if isinstance(v, str)}
        draft = {**op_templates.clean_draft(t, answer.get("draft")), **keep}
        found = [{"label": _line(r.get("label")), "value": _line(r.get("value"))}
                 for r in answer.get("found") or [] if isinstance(r, dict) and _line(r.get("label"))][:MAX_FOUND] \
            if isinstance(answer.get("found"), list) else []
        doubts = [d for d in (_line(x) for x in answer.get("doubts") or []) if d][:MAX_DOUBTS] \
            if isinstance(answer.get("doubts"), list) else []
        args = answer.get("args") if isinstance(answer.get("args"), dict) else {}
        run.update(draft=draft, found=found, doubts=doubts, args=op_templates.with_values(t, args, run["fields"], draft))
        run.pop("keep", None)
        self._ev(event_log.OP_PREPARED, op=op_id, doubts=len(doubts), **measure)
        ops = self.ops()
        tr = self.trust(t)
        stop = "checks" if run.get("again") else op_runs.stops(tr, t.risk, doubts, ops["daily_alone"],
                                                                 dt.date.today().isoformat())
        if not stop:
            run.update(state="acting", alone=True, why="", edited=[])
            self._save(run)
            self._enqueue(op_id, "act")
            return
        run.update(state="check", alone=False,
                   why=op_runs.stop_words(stop, ops["daily_alone"]) if tr.get("alone") or stop == "high" else "")
        self._save(run)

    # -- the action (§4) --------------------------------------------------------------------------------------------

    def act_prompt(self, act: str, args: dict) -> str:
        return (f"Call `{act}` once with exactly these arguments, then answer {{\"id\", \"link\"}} from what it "
                f"returns, as one JSON object. Call no other tool, and nothing a second time.\n\nArguments:\n"
                f"{json.dumps(args, ensure_ascii=False, indent=1)}\n")

    def _act(self, op_id: str, cancel: threading.Event) -> None:
        run = self._run(op_id)
        if run["state"] != "acting":
            return
        try:
            t = self.template(run["template"])
            _tools, act = op_templates.tools(t, self.ops()["servers"])
        except (OpsError, ValueError) as e:
            self._fail(run, "act", str(e), False)
            return
        what = op_templates.what_of(t, act, self.ops()["servers"])
        prompt = self.act_prompt(act, run["args"])
        if len(prompt) > idea_target.CONTEXT["op_act"]:
            self._fail(run, "act", "its arguments are too long for one call: shorten the draft and add it again", False)
            return
        if self._held(run, "act"):
            return
        text, failed = "", ""
        try:
            text, cost, events, measure = self._call("op_act", prompt, [act], cancel, op_id, t.name)
        except InterruptedError:
            self._fail(self._run(op_id), "act", f"stopped while doing it: look in {what} before you add it again", None)
            return
        except jobs.CallFailed as e:
            events, failed, cost, measure = e.events, str(e)[:300], None, {"step": "op_act", "tokens": None,
                                                                           "cost": None, "seconds": None}
        run = self._run(op_id)
        op_runs.add_cost(run, cost)
        uses = [e for e in events if e["type"] == "tool_use"]
        results = {e["id"]: e for e in events if e["type"] == "tool_result"}
        if not uses:
            if failed and self._sign_in_failure(run, "act", RuntimeError(failed)):    # nothing was done: it waits
                return
            self._fail(run, "act", failed or "nothing was done", False)
            return
        if len(uses) != 1 or uses[0]["name"] != act or not _same(uses[0]["input"], run["args"]):
            self._fail(run, "act", f"it did not do exactly what was checked: look in {what}", True)
            return
        result = results.get(uses[0]["id"])
        if result is not None and result["is_error"]:
            first = next((ln.strip() for ln in result["text"].splitlines() if ln.strip()), "")
            self._fail(run, "act", (first or f"{what} said it failed")[:LINE_CHARS], True)
            return
        if failed and result is None:
            self._fail(run, "act", f"{failed}: look in {what} before you add it again", None)
            return
        answer = first_json(text) or {}
        link = str(answer.get("link") or "")
        run.update(state="done", acted=True, why="", done_at=op_runs.now_iso(), done_id=_line(answer.get("id"))[:200],
                   link=link if link.lower().startswith(("http://", "https://")) else "", held="", held_until="")
        self._save(run)
        self._ev(event_log.OP_DONE, op=op_id, alone=bool(run.get("alone")), step="op_act",
                 tokens=measure.get("tokens"), cost=measure.get("cost"), seconds=measure.get("seconds"))
        tr, today = self.trust(t), dt.date.today().isoformat()
        if run.get("alone"):
            op_runs.save_trust(self.base, t.name, op_runs.after_alone(tr, today))
            return
        edited = bool(run.get("edited"))
        self._set_trust(t, op_runs.after_check(tr, edited, self.ops()["trust_after"]))
        if edited:
            self.learn(t.name, op_id, changes=run.get("changes") or [])

    # -- the learn call (§7) -----------------------------------------------------------------------------------------

    def learn(self, template: str, op_id: str, changes: list[dict] | None = None, not_right: str | None = None) -> None:
        self._learn[template] = {"op": op_id, "changes": list(changes or []), "not_right": not_right}
        if not self.demo:
            op_runs.save_learn(self.base, template, self._learn[template])      # a restart loses none
        self._enqueue(f"learn:{template}", "learn")

    def learn_prompt(self, t: Template, op: dict, given: dict) -> str:
        fields = "\n".join(f"- {f['label']}: {op.get('fields', {}).get(f['name'], '')}" for f in t.fields)
        if given.get("not_right") is not None:
            what = ("It went by itself, and the person says it was not right"
                    + (f": {given['not_right'][:CHANGE_CHARS]}" if given["not_right"] else " (no reason given)."))
        else:
            what = "\n".join(f"- {c.get('label') or c.get('name')}: {str(c.get('before') or '')[:CHANGE_CHARS]!r} → "
                             f"{str(c.get('after') or '')[:CHANGE_CHARS]!r}" for c in given.get("changes") or [])
        turned = "\n".join(f"- {line}" for row in op_runs.declined(self.base, t.name)
                           for line in row.get("lines") or [] if isinstance(line, str))
        parts = [("The template", t.title), ("Its rules", op_runs.rules(self.base, t.name)[:RULES_CHARS]),
                 ("The correction (before → after)", what), ("The fields of the operation", fields),
                 ("Rules the person turned down (never propose these again)", turned)]
        return LEARN_LINE + idea_target.cut(parts, idea_target.CONTEXT["op_learn"])

    def _learn_one(self, template: str, cancel: threading.Event) -> None:
        given = self._learn.get(template)
        try:
            t = self.template(template)
        except OpsError:
            self._learn.pop(template, None)
            op_runs.drop_learn(self.base, template)
            return
        if given is None or self.window_until() is not None or self.capped():
            return                              # held: the clock tries it again when the window is back
        self._learn.pop(template, None)
        op_runs.drop_learn(self.base, template)
        op = op_runs.load(self.base, given["op"]) or {}
        try:
            text, _cost, _events, measure = self._call("op_learn", self.learn_prompt(t, op, given), [], cancel,
                                                       given["op"], t.name)
        except (InterruptedError, jobs.CallFailed):
            return
        answer = first_json(text) or {}
        lines = op_runs.new_rules(answer.get("rules"), op_runs.rules(self.base, t.name),
                                  op_runs.declined(self.base, t.name, 10 ** 6))
        self._ev(event_log.OP_LEARNED, template=t.name, lines=len(lines), step="op_learn",
                 tokens=measure.get("tokens"), cost=measure.get("cost"))
        if lines:
            op_runs.propose(self.base, t.name, lines, _line(answer.get("why")), given["op"])
        self.publish(template=t.name)

    # -- the clock -------------------------------------------------------------------------------------------------

    def start(self) -> None:
        """What the host lost when it closed: a prepare runs again (it changes nothing); an action may have run, so
        it fails with `acted: null`; a learn call held waits again for the window; the old texts go."""
        for run in op_runs.runs(self.base):
            if run.get("state") == "preparing":
                self._enqueue(run["id"], "prepare")
            elif run.get("state") == "acting":
                what = run.get("template", "")
                try:
                    t = self.template(what)
                    what = op_templates.what_of(t, t.act)
                except OpsError:
                    pass
                self._fail(run, "act", f"Orkboard closed while doing it: look in {what} before you add it again", None)
        for template, given in op_runs.pending_learns(self.base).items():
            self._learn.setdefault(template, given)
            self._enqueue(f"learn:{template}", "learn")
        self.forget()

    def forget(self) -> None:
        today = dt.date.today().isoformat()
        if self._forgot != today:
            self._forgot = today
            if op_runs.forget_old(self.base, self.ops()["keep_days"]):
                self.publish()

    def _sign_in_tick(self) -> None:
        """What waits for Claude Code's sign-in goes on once it is signed in; after a day it fails with its line."""
        for run in op_runs.runs(self.base):
            if run.get("state") != "held" or run.get("held_for") != "sign_in":
                continue
            if self.signed_out():
                try:
                    due = dt.datetime.fromisoformat(str(run.get("held_until"))).timestamp()
                except ValueError:
                    due = 0.0
                if time.time() >= due:
                    why = run.get("why") or tool_errors.LINES[tool_errors.LOGIN].format(tool=harnesses.title(HARNESS))
                    self._fail(run, "act" if run.get("held") == "act" else "prepare", why, False)
                continue
            step = "act" if run.get("held") == "act" else "prepare"
            run.update(state="acting" if step == "act" else "preparing", held="", held_until="", held_for="", why="")
            self._save(run)
            self._enqueue(run["id"], step)

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        if now - self._tick_at < TICK_S:
            return
        self._tick_at = now
        self.forget()
        self._sign_in_tick()
        if self.window_until() is not None:
            return
        held = [run for run in op_runs.runs(self.base)
                if run.get("state") == "held" and run.get("held_for") != "sign_in"]
        if (held or self._learn) and self.capped():        # the ledgers are read only when something waits
            return
        for run in held:
            step = "act" if run.get("held") == "act" else "prepare"
            run.update(state="acting" if step == "act" else "preparing", held="", held_until="", why="")
            self._save(run)
            self._enqueue(run["id"], step)
        for template in list(self._learn):
            self._enqueue(f"learn:{template}", "learn")
