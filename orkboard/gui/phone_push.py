"""Notifications to a paired phone (docs/specs/42-coming-back.md §3): the Board reaches a phone whose page is not open, for the
two things worth it — an answer that waits, and the morning's summary — and for nothing else.

    pusher = Pusher(host)            # the Orkboard host's, ticked by its clock; `host.attach_phones(listener)` gives it the devices
    pusher.tick(now)                 # at most every TICK_S: what goes, to whom, off the loop (a worker thread for a send)
    pusher.on / off / quiet / key    # the `mobile.push_*` commands of a phone (gui/board_host.py)

Never: in the quiet hours, under Do not disturb, for a proposal, a result to check, a merge, a spend or a limit, to a device whose
socket is open, or more than one push of a tag to a device every PUSH_GAP_S. The words are the Board's own (a kind, a short name,
a count): never a question's text, a spec's, a mail's or a template's field.
"""
from __future__ import annotations

import datetime as dt
import threading
from typing import Any, Callable

from orkboard import schedule, settings
from orkboard.gui import web_push
from orkboard.gui.ideas_recap import RECAP_DAYS
from orkboard.realm import board_recap, event_log
from orkboard.realm.idea_words import short_of

TICK_S = 30.0
PUSH_GAP_S = 900.0
MORNING_H = 3                                   # the morning is the first tick within this many hours after the quiet hours end
KIND_WORDS = {"goal": "A party asks", "asks": "A spec asks", "plan": "A plan waits for you", "change": "A plan change waits for you", "todo": "A to-do", "failed": "Failed",
              "op": "At your check", "op_failed": "Failed"}      # js/board/today.js KIND_WORDS, the kinds that wait for an answer


PICK_WORDS = "{member} asks you to pick one"      # a task that made variants waits for the person's pick (spec 51 §2.4): a pick that waits is an answer that waits


class PushRefused(Exception):
    """A `mobile.push_*` the computer refuses, in plain words."""


def _thread(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, daemon=True, name="phone-push").start()


def span_label(span: schedule.Span | None) -> str:
    return f"{schedule.fmt(span.start)}-{schedule.fmt(span.end)}" if span is not None else ""


def dnd_on(machine, now: dt.datetime) -> bool:
    d = machine.dnd_until
    if d == "on":
        return True
    when = board_recap.when(d) if d else None
    return when is not None and when > now.astimezone()


class Pusher:
    def __init__(self, host: Any) -> None:
        self.host = host
        self.listener: Any = None                              # gui/phones.py `Listener`: `pairing`, `open_ids()`
        self.send: Callable[[dict, dict], int] = web_push.send
        self.spawn: Callable[[Callable[[], None]], None] = _thread
        self.machine: Callable[[], Any] = settings.load
        self._at: dt.datetime | None = None
        self._told: dict[str, int] = {}                        # device → how many waiting it was last told (or saw itself)
        self._sent: dict[tuple[str, str], dt.datetime] = {}    # (device, tag) → when

    # -- what the Board holds ----------------------------------------------------------------------------------

    def _waiting(self) -> int:
        n = 0
        for p in self.host.projects.open_ones:
            try:
                n += int(p.ideas.snapshot().get("needs_you") or 0)
            except Exception:                                  # a broken Board never stops the clock
                pass
        try:
            return n + self.host.ops.count()                   # Operations are the person's: counted once
        except Exception:
            return n

    def _first(self) -> tuple[str, str] | None:
        """(kind's words, short name) of the first row of the shown project's Needs you that waits for an answer."""
        ideas = self.host.ideas
        rows: list[dict] = []
        try:
            rows += ideas.board(make=False)["needs_you"] if ideas is not None else []
            rows += self.host.ops.needs()
        except Exception:
            pass
        row = next((n for n in rows if n.get("kind") in KIND_WORDS or n.get("kind") == "pick"), None)
        if row and row["kind"] == "pick":                           # said by who asks: the member the task ran as, no title
            return PICK_WORDS.format(member=str((row.get("by") or {}).get("name") or "A member")), ""
        return (KIND_WORDS[row["kind"]], short_of(str(row.get("title") or ""))) if row else None

    def words_needs(self, waiting: int) -> str:
        first = self._first()
        row = f"{first[0]} · {first[1]}" if first and first[1] else (first[0] if first else "")
        if waiting > 1:
            return " · ".join(x for x in (f"{waiting} wait for your answer", row) if x)
        return row or "1 waits for your answer"

    def morning(self, since: dt.datetime, now: dt.datetime, waiting: int) -> str:
        """§3.1's morning line, summed over the open projects; "" when there is nothing to say."""
        results = flags = proposed = failed = 0
        into, empty = "dev", True
        for p in self.host.projects.open_ones:
            try:
                got = board_recap.build(p.root, p.ideas.state_dir, since, now, p.ideas.board(make=False), into=p.ideas._into())
            except Exception:
                continue
            empty = empty and got["empty"]
            results += got["merged"]["tasks"]
            flags += sum(1 for f in got["flags"] if f["met"])
            proposed += len(got["proposed"])
            failed += len(got["failed"])
            into = got["into"] if p is self.host.project else into
        if empty:
            return ""
        parts = [results and f"{results} {'result' if results == 1 else 'results'} in {into}",
                 flags and f"{flags} {'flag' if flags == 1 else 'flags'} raised",
                 proposed and f"{proposed} {'goal' if proposed == 1 else 'goals'} proposed",
                 failed and f"{failed} failed"]
        said = ", ".join(str(x) for x in parts if x) or "the night's work"
        return f"While you were away: {said} · {waiting} {'waits' if waiting == 1 else 'wait'} for your answer" if waiting \
            else f"While you were away: {said} and nothing waits for you"

    # -- the clock ------------------------------------------------------------------------------------------------

    def tick(self, now: dt.datetime | None = None) -> None:
        now = (now or dt.datetime.now()).astimezone()
        if self.listener is None or (self._at is not None and (now - self._at).total_seconds() < TICK_S):
            return
        self._at = now
        try:
            self._run(now)
        except Exception:                                      # a push never troubles the Board
            pass

    def _run(self, now: dt.datetime) -> None:
        pairing, machine = self.listener.pairing, self.machine()
        devices = [d for d in pairing.devices() if d.get("push")]
        if not devices:
            return
        opened, waiting = self.listener.open_ids(), self._waiting()
        quiet = schedule.quiet_now(machine, now.replace(tzinfo=None)) or dnd_on(machine, now)
        out: dict[str, list[tuple[dict, dict]]] = {}
        for d in devices:
            did = d["id"]
            if did in opened:                                  # an open page says it itself
                self._told[did] = waiting
                continue
            told = self._told.setdefault(did, waiting)
            self._told[did] = min(told, waiting)               # answered since: a new one is news again
            if quiet:
                continue
            if waiting > self._told[did] and self._free(did, "needs", now):
                self._told[did] = waiting
                out.setdefault("needs", []).append((d, {"title": "Orkline", "body": self.words_needs(waiting), "tag": "needs",
                                                         "badge": waiting, "url": "./#needs"}))
            elif self._morning_due(d, machine, now):
                since = max(board_recap.when(d.get("seen")) or now, now - dt.timedelta(days=RECAP_DAYS))      # as `ideas.recap` caps it
                body = self.morning(since, now, waiting)
                if not body:                                   # nothing to say: the day is checked, not asked again every tick
                    pairing.set_push(did, {**d["push"], "morning": now.date().isoformat()})
                elif self._free(did, "recap", now):
                    out.setdefault("recap", []).append((d, {"title": "Orkline", "body": body, "tag": "recap", "badge": waiting, "url": "./"}))
                    pairing.set_push(did, {**d["push"], "morning": now.date().isoformat()})
        for tag, sends in out.items():
            for d, _m in sends:
                self._sent[(d["id"], tag)] = now
            self._go(tag, sends)

    def _free(self, device: str, tag: str, now: dt.datetime) -> bool:
        last = self._sent.get((device, tag))
        return last is None or (now - last).total_seconds() >= PUSH_GAP_S

    def _morning_due(self, d: dict, machine, now: dt.datetime) -> bool:
        """The quiet hours ended less than MORNING_H hours ago, today's morning is not sent, and the device was not seen since the quiet
        hours began."""
        q = machine.quiet
        if q is None or d["push"].get("morning") == now.date().isoformat():
            return False
        local = now.replace(tzinfo=None)
        back_end = (local.hour * 60 + local.minute - q.end) % schedule.DAY
        if back_end >= MORNING_H * 60:
            return False
        began = local.replace(hour=q.start // 60, minute=q.start % 60, second=0, microsecond=0)
        if began > local:
            began -= dt.timedelta(days=1)
        seen = board_recap.when(d.get("seen"))
        return seen is not None and seen.replace(tzinfo=None) < began

    def _go(self, tag: str, sends: list[tuple[dict, dict]]) -> None:
        """The pushes of one tag, sent off the loop; a subscription the push service no longer knows (404, 410) is dropped."""
        pairing, project = self.listener.pairing, self.host.repo_root

        def run() -> None:
            gone = [d["id"] for d, m in sends if self.send(d["push"], m) in (404, 410)]

            def after() -> None:
                for did in gone:
                    pairing.set_push(did, None)
                if project is not None:
                    event_log.record(project, event_log.PUSH_SENT, tag=tag, devices=len(sends), gone=len(gone))
            self.host.call(after)
        self.spawn(run)

    # -- the phone's commands ----------------------------------------------------------------------------------

    def _device(self, args: dict) -> str:
        did = args.get("device_id")
        if self.listener is None or not isinstance(did, str) or not self.listener.pairing.known(did):
            raise PushRefused("Only a paired phone can do this")
        try:
            web_push._crypto()                                 # every push command needs it, not only the key
        except web_push.PushError as e:
            raise PushRefused(str(e)) from None
        return did

    def _log_set(self, on: bool) -> None:
        if self.host.repo_root is not None:
            event_log.record(self.host.repo_root, event_log.PUSH_SET, on=on, device="phone")

    def _machine_quiet(self, span: schedule.Span) -> None:
        m = settings.load()
        m.quiet = span
        settings.save(m)
        self.host.machine.quiet = span

    def key(self, args: dict) -> dict:
        self._device(args)
        try:
            return {"key": web_push.public_key(), "quiet": span_label(self.machine().quiet)}
        except web_push.PushError as e:
            raise PushRefused(str(e)) from None

    def on(self, args: dict) -> dict:
        did = self._device(args)
        sub = {k: args.get(k) for k in ("endpoint", "p256dh", "auth")}
        kept = (self.listener.pairing.get(did) or {}).get("push") or {}
        got = settings.clean_push({**sub, "at": dt.datetime.now().isoformat(timespec="seconds"), "morning": kept.get("morning") or ""})
        if got is None or not self.listener.pairing.set_push(did, got):
            raise PushRefused("That subscription is not one a phone gives")
        if self.machine().quiet is None:
            self._machine_quiet(schedule.DEFAULT_QUIET)
        if not kept:
            self._log_set(True)
        return {"ok": True, "quiet": span_label(self.machine().quiet)}

    def off(self, args: dict) -> dict:
        did = self._device(args)
        if (self.listener.pairing.get(did) or {}).get("push"):
            self.listener.pairing.set_push(did, None)
            self._log_set(False)
        return {"ok": True}

    def quiet(self, args: dict) -> dict:
        self._device(args)
        text = args.get("quiet")
        a, _dash, b = (text if isinstance(text, str) else "").partition("-")
        span = schedule.Span.parse(a, b)
        if span is None:
            raise PushRefused("The quiet hours are HH:MM-HH:MM")
        self._machine_quiet(span)
        return {"ok": True}

    def commands(self) -> dict[str, Callable[[dict], Any]]:
        return {"mobile.push_key": self.key, "mobile.push_on": self.on, "mobile.push_off": self.off, "mobile.push_quiet": self.quiet}
