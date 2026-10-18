"""The person's commands on Operations (docs/specs/38-operations.md §3, §4, §6, §7, §11), `OpRunner`'s
(core/op_runner.py): add from a template, Prepare again and the action on the check, Stop, Drop, Try again, Add again,
Not right, the rules' answer and Check again. Each refuses in words (`OpsError`); none calls a model itself: it
queues the call on the runner. A press that would start a call is refused while the day's spend is over the person's
cap (spec 38 §1), as the runner holds the calls already queued.
"""
from __future__ import annotations

from orkboard.core import treasury
from orkboard.realm import event_log, op_runs, op_templates
from orkboard.realm.op_templates import Template

CHANGE_CHARS = 2000
CAP_WAITS = "waits: the day's spend cap is reached"      # a held operation's row (`why`)


class OpsError(Exception):
    """What Operations refuses, in plain words."""


class CommandsMixin:
    """Needs the runner's `template`, `trust`, `_run`, `_save`, `_ev`, `_enqueue`, `_fail`, `learn`, `cap` and its
    queue."""

    def _may_spend(self) -> None:
        """Refused in words while the day's spend reached the person's cap: no new call starts."""
        try:
            spent, cap = self.cap()
        except Exception:
            return
        if treasury.over(spent, cap):
            raise OpsError(f"The day's spend cap is reached (${spent:.2f} of ${cap:.2f} today): no operation starts "
                           "until tomorrow, or until the cap is raised (budget.gold_session_limit_usd in the open "
                           "projects' .orkcraft.json)")

    def _may_add(self, t: Template) -> None:
        if self.demo:
            raise OpsError("The demo runs no model: Operations work in a real window")
        why = op_templates.unusable(t, self.ops()["servers"], self.claude())
        if why:
            raise OpsError(why)

    def add(self, template: object, fields: object, device: str = "desktop") -> str:
        t = self.template(template)
        self._may_add(t)
        self._may_spend()
        try:
            values = op_templates.clean_fields(t, fields, op_runs.last_values(self.base, t.name))
        except ValueError as e:
            raise OpsError(str(e)) from None
        run = op_runs.blank(op_runs.new_id(), t.name, t.version, values, device)
        self._save(run)
        op_runs.remember(self.base, t.name, {f["name"]: values[f["name"]] for f in t.fields if f.get("remember")
                                             and values.get(f["name"])})
        self._ev(event_log.OP_ADDED, op=run["id"], template=t.name, version=t.version[:12], device=device)
        self._enqueue(run["id"], "prepare")
        return run["id"]

    def _at_check(self, op_id: object) -> tuple[dict, Template]:
        run = self._run(op_id)
        if run["state"] != "check":
            raise OpsError("That operation is not at your check")
        return run, self.template(run["template"])

    def _changes(self, t: Template, run: dict, fields: dict, draft: dict) -> list[dict]:
        out = [{"name": f["name"], "label": f["label"], "before": run["fields"].get(f["name"], ""),
                "after": fields[f["name"]], "at": bool(f.get("at"))}
               for f in t.fields if fields[f["name"]] != run["fields"].get(f["name"], "")]
        out += [{"name": p["name"], "label": p["label"], "before": run["draft"].get(p["name"], ""),
                 "after": draft[p["name"]], "at": True, "draft": True}
                for p in t.draft if p["name"] in draft and draft[p["name"]] != run["draft"].get(p["name"], "")]
        return out

    def _form(self, t: Template, run: dict, fields: object, draft: object) -> tuple[dict, dict]:
        try:
            values = op_templates.clean_fields(t, {**run["fields"], **(fields if isinstance(fields, dict) else {})})
        except ValueError as e:
            raise OpsError(str(e)) from None
        given = draft if isinstance(draft, dict) else {}
        parts = op_templates.clean_draft(t, {**run["draft"], **given})
        return values, parts

    def prepare_again(self, op_id: object, fields: object = None, draft: object = None, device: str = "desktop") -> None:
        """Prepare again (§4): with the fields as the person changed them; the draft parts they corrected stay theirs."""
        run, t = self._at_check(op_id)
        self._may_spend()
        values, parts = self._form(t, run, fields, draft)
        changes = self._changes(t, run, values, parts)
        keep = {c["name"]: c["after"] for c in changes if c.get("draft")}
        run.update(state="preparing", fields=values, keep={**(run.get("keep") or {}), **keep}, again=True,
                   edited=sorted({*run.get("edited", []), *(c["name"] for c in changes)}),
                   changes=[*(run.get("changes") or []), *changes], why="")
        self._save(run)
        self._enqueue(run["id"], "prepare")

    def act(self, op_id: object, fields: object = None, draft: object = None, device: str = "desktop") -> None:
        """The check passed, as corrected: a changed field without `at` needs Prepare again first."""
        run, t = self._at_check(op_id)
        self._may_spend()
        values, parts = self._form(t, run, fields, draft)
        changes = self._changes(t, run, values, parts)
        needs = next((c for c in changes if not c["at"]), None)
        if needs is not None:
            raise OpsError(f"{needs['label']} changed: Prepare again first")
        edited = sorted({*run.get("edited", []), *(c["name"] for c in changes)})
        run.update(state="acting", fields=values, draft=parts, edited=edited, alone=False, why="",
                   changes=[*(run.get("changes") or []), *changes],
                   args=op_templates.with_values(t, run["args"], values, parts))
        self._save(run)
        self._ev(event_log.OP_CHECKED, op=run["id"], edited=edited, again=bool(run.get("again")), device=device)
        self._enqueue(run["id"], "act")

    def drop(self, op_id: object) -> None:
        run = self._run(op_id)
        if run["state"] not in ("check", "failed"):
            raise OpsError("Only an operation at your check or a failed one can be dropped")
        was = run["state"]
        run.update(state="dropped", done_at=op_runs.now_iso())
        self._save(run)
        self._ev(event_log.OP_DROPPED, op=run["id"], **{"from": was})

    def stop(self, op_id: object) -> bool:
        """Its call is cancelled; one that waits (queued or held) fails without having run."""
        run = self._run(op_id)
        with self._lock:
            cancel = self._running.get(run["id"])
            queued = next(((k, s) for k, s in self._queue if k == run["id"]), None)
            if queued:
                self._queue.remove(queued)
        if cancel is not None:
            cancel.set()
            return True
        if run["state"] in ("preparing", "acting", "held"):
            step = run.get("held") or ("act" if run["state"] == "acting" else "prepare")
            self._fail(run, step, "stopped", False)
            return True
        return False

    def stop_all(self) -> int:
        with self._lock:
            waiting = [k for k, _ in self._queue if not k.startswith("learn:")]
            self._queue.clear()
            cancels = list(self._running.values())
        for ev in cancels:
            ev.set()
        for op_id in waiting:
            try:
                run = self._run(op_id)
                self._fail(run, "act" if run["state"] == "acting" else "prepare", "stopped", False)
            except OpsError:
                pass
        return len(cancels) + len(waiting)

    def retry(self, op_id: object) -> None:
        run = self._run(op_id)
        if run["state"] != "failed" or run.get("acted") is not False:
            raise OpsError("Only an operation that failed before doing anything can be tried again: add it again")
        self._may_spend()
        step = "act" if run.get("step") == "act" else "prepare"
        run.update(state="acting" if step == "act" else "preparing", why="", step="")
        self._save(run)
        self._enqueue(run["id"], step)

    def again(self, op_id: object, device: str = "desktop") -> str:
        run = self._run(op_id)
        if not run.get("fields"):
            raise OpsError("That operation's fields are gone: add a new one")
        return self.add(run["template"], run["fields"], device)

    def not_right(self, op_id: object, why: str = "") -> None:
        run = self._run(op_id)
        if run["state"] != "done" or not run.get("alone"):
            raise OpsError("Not right is for an operation that went by itself")
        t = self.template(run["template"])
        self._set_trust(t, op_runs.after_not_right(self.trust(t)))
        self._ev(event_log.OP_NOT_RIGHT, op=run["id"], has_reason=bool(why.strip()))
        self.learn(t.name, run["id"], not_right=why.strip()[:CHANGE_CHARS])

    def rules_answer(self, template: object, take: bool, reason: str = "") -> None:
        t = self.template(template)
        got = op_runs.proposal(self.base, t.name)
        if got is None:
            raise OpsError("That proposal is gone")
        if take:
            op_runs.take_rules(self.base, t.name, got["lines"])
            self._set_trust(t, op_runs.after_rules(self.trust(t)))
        else:
            op_runs.decline(self.base, t.name, got["lines"], reason)
        op_runs.drop_proposal(self.base, t.name)
        self._ev(event_log.OP_RULES_ANSWERED, template=t.name, take=take, has_reason=bool(reason.strip()))
        self.publish(template=t.name)

    def trust_reset(self, template: object) -> None:
        t = self.template(template)
        self._set_trust(t, op_runs.after_reset(self.trust(t)))
