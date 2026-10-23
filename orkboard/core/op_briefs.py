"""Briefs on Operations' runner (docs/specs/66-team-briefs.md §1–§4): a template that reads and writes a page for the
person, and does nothing outside. A mixin of `OpRunner` (core/op_runner.py), beside the person's commands
(core/op_commands.py).

    runner.keep(op_id, fields, draft)           # Keep: the brief saved as corrected; a correction teaches (§1)
    runner.forget_value("one-on-one", "Ana")    # Forget: every operation of that value, its calls, its standing briefs
    runner.standing_add("daily-brief", fields, days=[0, 1, 2, 3, 4], at="09:30", before=30)
    runner.standing_change(st_id, at="10:00") · runner.standing_stop(st_id)

- **About people** (`people = true`, §2): the prepare's and the learn call's prompts carry `PEOPLE_RULE`; a proposed
  rule holding one of `PEOPLE_WORDS` is dropped; a bound read (`[[prepare.bound]]`) called with a value the person did
  not name fails the brief before its answer is read, and its calls' prompts and outputs are removed.
- **Follow** (§4): the prepare gets the last kept brief of the same value (*Last time*); one is kept per value, until
  `ops.follow_days`.
- **Standing briefs** (§3, realm/op_standing.py): added on Operations' tick at their time, once a day; not the person's
  own press, so they keep the reserve (spec 35 §6) and are held as any operation is; a meeting passed is skipped, once.
No face: what changed is published.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from typing import Any

from orkboard.core.op_commands import OpsError
from orkboard.realm import event_log, idea_target, op_runs, op_standing, op_templates
from orkboard.realm.op_templates import Template, same_value

PEOPLE_RULE = ("Write about the work and the meeting, never about a person: no strengths or weaknesses, no score, no "
               "ranking, no comparison of people, no reading of a person's tone or mood, no counts of commits, messages "
               "or time as a measure of anyone. Name people only as the owner or the author of an item, with its link. "
               "When the person's notes judge someone, keep them as written and add nothing.")
# A rule the learn call proposes for a template about people is dropped when it holds one of these (a word's start:
# "weak" drops "weakness", "rank" drops "ranking"). Short on purpose: its tests are the guard.
PEOPLE_WORDS = ("weak", "strong side", "strength", "rating", "rate them", "score", "rank", "performance",
                "performer", "productive", "productivity", "lazy", "underperform", "mood", "attitude", "personality",
                "compare people", "comparison of people")
_PEOPLE = re.compile(r"\b(" + "|".join(re.escape(w) for w in PEOPLE_WORDS) + ")", re.IGNORECASE)
BOUND_WORDS = "it read a channel you did not name: nothing was kept"
STANDING_WAITS = "waits for limits: prepared when the window allows"
LAST_CHARS = 3000
LOOKUP_CHARS = 200_000                     # a bound brief reads its lookup's whole answer (spec 66 §2)
_PAIR = (re.compile(r'"id"\s*:\s*"([^"]{1,200})"[^{}]*?"name"\s*:\s*"([^"]{1,200})"'),
         re.compile(r'"name"\s*:\s*"([^"]{1,200})"[^{}]*?"id"\s*:\s*"([^"]{1,200})"'))


def about_people(line: str) -> bool:
    """A rule that judges a person (spec 66 §2): it holds one of PEOPLE_WORDS."""
    return bool(_PEOPLE.search(line or ""))


# -- bound reads (§2) ---------------------------------------------------------------------------------------------

def _norm(value: object) -> str:
    return str(value or "").strip().lstrip("#@").strip().casefold()


def named(value: object) -> set[str]:
    """The values a field names: split on commas, spaces and lines; `#` and `@` left off; case ignored."""
    return {n for n in (_norm(x) for x in re.split(r"[,;\s]+", str(value or ""))) if n}


def pairs(text: str) -> list[tuple[str, str]]:
    """The (id, name) pairs a lookup tool answered: every object with both, in its JSON, else as the text spells them
    (an answer cut short)."""
    out: list[tuple[str, str]] = []

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            if isinstance(x.get("id"), str) and isinstance(x.get("name"), str):
                out.append((x["id"], x["name"]))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    try:
        walk(json.loads(text))
    except ValueError:
        out += [m.groups() for m in _PAIR[0].finditer(text or "")]
        out += [(i, n) for n, i in (m.groups() for m in _PAIR[1].finditer(text or ""))]
    return out


def breach(bounds: list[dict], events: list[dict], fields: dict) -> str:
    """The first bound tool called with a value its field does not name, by name or by the id its lookup answered for
    such a name (a call without the argument counts as one); "" when every call kept to them."""
    uses = {e["id"]: e for e in events if e.get("type") == "tool_use"}
    for b in bounds:
        allowed = named(fields.get(b["field"], ""))
        names = set(allowed)
        for e in events:
            use = uses.get(e.get("id", "")) if e.get("type") == "tool_result" else None
            if use is None or use["name"] == b["tool"] or (b.get("lookup") and use["name"] != b["lookup"]):
                continue
            allowed |= {_norm(i) for i, n in pairs(e.get("text") or "") if _norm(n) in names}
        for use in uses.values():
            if use["name"] != b["tool"]:
                continue
            given = use["input"].get(b["arg"]) if isinstance(use.get("input"), dict) else None
            values = given if isinstance(given, list) else [given]
            if not values or any(not isinstance(v, str) or _norm(v) not in allowed for v in values):
                return b["tool"]
    return ""


def last_time(t: Template, last: dict | None) -> str:
    """The last kept brief, as the prepare reads it under *Last time* (at most LAST_CHARS)."""
    if last is None:
        return ""
    labels = {p["name"]: p["label"] for p in t.draft}
    body = "\n\n".join(f"{labels.get(k, k)}:\n{v}" for k, v in (last.get("draft") or {}).items() if v)
    return f"Kept {str(last.get('done_at') or '')[:10]}.\n{body}"[:LAST_CHARS]


class BriefsMixin:
    """Needs the runner's `template`, `trust`, `_set_trust`, `_run`, `_save`, `_ev`, `learn`, `ops`, `limits`,
    `reserve`, `clock`, `add`, its queue and `publish` (core/op_runner.py, core/op_commands.py)."""

    # -- Keep (§1) -------------------------------------------------------------------------------------------------

    def keep(self, op_id: object, fields: object = None, draft: object = None, device: str = "desktop") -> None:
        """The brief saved as corrected: a clean keep counts towards by itself, a corrected one asks the learn call; a
        changed field means Prepare again."""
        run, t = self._at_check(op_id)
        if not t.brief:
            raise OpsError(f"{t.title} acts: its check's button is {t.act_label}")
        values, parts = self._form(t, run, fields, draft)
        changes = self._changes(t, run, values, parts)
        needs = next((c for c in changes if not c["at"]), None)
        if needs is not None:
            raise OpsError(f"{needs['label']} changed: Prepare again first")
        edited = sorted({*run.get("edited", []), *(c["name"] for c in changes)})
        run.update(state="done", fields=values, draft=parts, edited=edited, alone=False, why="", acted=False,
                   done_at=op_runs.now_iso(), changes=[*(run.get("changes") or []), *changes], held="", held_until="")
        self._save(run)
        self._ev(event_log.OP_CHECKED, op=run["id"], edited=edited, again=bool(run.get("again")), device=device)
        self._kept(t, run, device)
        self._set_trust(t, op_runs.after_check(self.trust(t), bool(edited), self.ops()["trust_after"]))
        if edited:
            self.learn(t.name, run["id"], changes=run.get("changes") or [])

    def _kept_alone(self, t: Template, run: dict) -> None:
        """A brief of a template that goes by itself, kept with no check (§1)."""
        run.update(state="done", alone=True, why="", edited=[], acted=False, done_at=op_runs.now_iso())
        self._save(run)
        self._kept(t, run, "alone")
        op_runs.save_trust(self.base, t.name, op_runs.after_alone(self.trust(t), dt.date.today().isoformat()))

    def _kept(self, t: Template, run: dict, device: str) -> None:
        """Kept: one per value of a follow brief, the older ones of that value cut now (§2, §4)."""
        self._ev(event_log.OP_KEPT, op=run["id"], alone=bool(run.get("alone")), edited=len(run.get("edited") or []),
                 device=device)
        if t.follow:
            value = (run.get("fields") or {}).get(t.follow)
            older = [r["id"] for r in op_runs.kept_briefs(op_runs.runs(self.base), t.name, t.follow)
                     if r["id"] != run["id"] and same_value(r["fields"].get(t.follow), value)]
            if older:
                op_runs.cut(self.base, older)

    def follows(self, t: Template, run: dict) -> dict | None:
        """The last kept brief of the same value of the template's follow field (§4), within `ops.follow_days`."""
        if not t.follow:
            return None
        last = op_runs.last_kept(self.base, t.name, t.follow, (run.get("fields") or {}).get(t.follow), but=run["id"])
        since = (dt.datetime.now() - dt.timedelta(days=self.ops()["follow_days"])).isoformat(timespec="seconds")
        return last if last is not None and str(last.get("done_at") or "") >= since else None

    # -- Forget (§2) -------------------------------------------------------------------------------------------------

    def forget_value(self, template: object, value: object) -> int:
        """Every operation of the template with that value of its follow field, kept or not, removed now with its
        calls' prompts and outputs; its standing briefs stopped; the value no longer remembered. How many."""
        t = self.template(template)
        if not t.follow:
            raise OpsError(f"{t.title} follows no one: nothing is kept by name")
        value = str(value or "").strip()
        if not value:
            raise OpsError(f"Say whose: {t.field_of(t.follow)['label']}")
        ids = [r["id"] for r in op_runs.runs(self.base) if r.get("template") == t.name
               and same_value((r.get("fields") or {}).get(t.follow), value)]
        with self._lock:
            busy = [i for i in ids if i in self._running or any(k == i for k, _ in self._queue)]
        if busy:
            raise OpsError("A brief of theirs is being prepared: stop it, then Forget")
        n = op_runs.remove(self.base, ids)
        items = op_standing.load(self.base)
        left = [i for i in items if not (i["template"] == t.name and same_value(i["fields"].get(t.follow), value))]
        if len(left) != len(items):
            op_standing.save(self.base, left)
        op_runs.forget_value(self.base, t.name, t.follow, value)
        pending = self._learn.get(t.name) or op_runs.pending_learns(self.base).get(t.name)
        if pending and pending.get("op") in ids:
            self._learn.pop(t.name, None)
            op_runs.drop_learn(self.base, t.name)
        got = op_runs.proposal(self.base, t.name)
        if got and got.get("op") in ids:
            op_runs.drop_proposal(self.base, t.name)
        self._ev(event_log.OP_FORGOT, template=t.name, runs=n, standing=len(items) - len(left))
        self.publish(template=t.name)
        return n

    # -- standing briefs (§3) ----------------------------------------------------------------------------------------

    def _standing_item(self, t: Template, given: dict, fields: object) -> dict:
        if not t.brief:
            raise OpsError(f"{t.title} acts: only a brief is prepared before a meeting")
        why = op_templates.unusable(t, self.ops()["servers"], self.claude())
        if why:
            raise OpsError(why)
        try:
            values = op_templates.clean_fields(t, fields, op_runs.last_values(self.base, t.name))
            return op_standing.clean(given, values)
        except ValueError as e:
            raise OpsError(str(e)) from None

    def standing_add(self, template: object, fields: object, days: object, at: object, before: object = None,
                     device: str = "desktop") -> str:
        t = self.template(template)
        item = self._standing_item(t, {"days": days, "at": at, "before": op_standing.BEFORE if before is None
                                       else before}, fields)
        items = op_standing.load(self.base)
        if len(items) >= op_standing.MAX:
            raise OpsError(f"At most {op_standing.MAX} standing briefs: stop one first")
        item.update(id=op_standing.new_id(), template=t.name, last="", skipped="")
        item["last"] = op_standing.first_last(item, self.clock())
        op_standing.save(self.base, [*items, item])
        self._ev(event_log.OP_STANDING, standing=item["id"], template=t.name, what="set", device=device)
        self.publish(template=t.name)
        return item["id"]

    def standing_change(self, st_id: object, changes: dict, device: str = "desktop") -> None:
        items = op_standing.load(self.base)
        was = next((i for i in items if i["id"] == st_id), None)
        if was is None:
            raise OpsError("That standing brief is gone")
        t = self.template(was["template"])
        given = {k: changes.get(k, was[k]) for k in ("days", "at", "before")}
        item = {**was, **self._standing_item(t, given, {**was["fields"], **(changes.get("fields") or {})}),
                "skipped": ""}
        item["last"] = op_standing.first_last(item, self.clock())
        op_standing.save(self.base, [item if i["id"] == st_id else i for i in items])
        self._ev(event_log.OP_STANDING, standing=item["id"], template=t.name, what="changed", device=device)
        self.publish(template=t.name)

    def standing_stop(self, st_id: object, device: str = "desktop") -> None:
        items = op_standing.load(self.base)
        was = next((i for i in items if i["id"] == st_id), None)
        if was is None:
            raise OpsError("That standing brief is gone")
        op_standing.save(self.base, [i for i in items if i["id"] != st_id])
        self._ev(event_log.OP_STANDING, standing=was["id"], template=was["template"], what="stopped", device=device)
        self.publish(template=was["template"])

    def standing(self, now: dt.datetime | None = None) -> None:
        """Operations' tick: each standing brief due today added as `ops.add` adds one (not the person's press: it
        keeps the reserve), once a day; one whose meeting passed is skipped, once (§3)."""
        now = now or self.clock()
        items = op_standing.load(self.base)
        moved = False
        for item in items:
            what = op_standing.due(item, now)
            if not what:
                continue
            item["last"], moved = now.date().isoformat(), True
            if what == "skip":
                item["skipped"] = op_standing.OFF
            else:
                try:
                    self.add(item["template"], item["fields"], device="standing", standing=item["id"])
                    item["skipped"] = ""
                except OpsError as e:
                    item["skipped"], what = f"skipped: {e}", "skip"
            self._ev(event_log.OP_STANDING, standing=item["id"], template=item["template"],
                     what="added" if what == "add" else "skipped", device="standing")
        if moved:
            op_standing.save(self.base, items)
            self.publish()

    def reserve_until(self) -> float | None:
        """When the reserve is back, while it holds what starts by itself (realm/idea_target.py `reserve_held`, the
        machine's Board settings' reserves); None when it does not hold."""
        try:
            limits = list(self.limits() or [])
        except Exception:
            limits = []
        return idea_target.reserve_held(limits, self.reserve(), time.time())
