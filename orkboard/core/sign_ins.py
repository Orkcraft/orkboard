"""Sign-ins (docs/specs/45-sign-in.md §4): the host's service that keeps, for each AI tool, whether it needs its own
sign-in, starts it, and tells the work that waits for it when it is done. No face: every change is published on the bus.

    signins = SignIns(bus, env, state_dir)       # watches `tool_errors`: a login failure that a sign-in helps begins an episode
    signins.start("claude", auto=True)           # the tool's own sign-in, one run per tool (realm/sign_in.py)
    signins.cancel("claude") / signins.done("pi") / signins.stop_all()
    signins.blocked("claude")                    # the tool needs its sign-in: what runs by itself waits (spec 45 §6)
    signins.holds(err)                           # a failure that a sign-in helps: the work is held for it
    signins.snapshot()                           # the snapshot's `sign_in`: the tools not done, in the registry's order
    signins.tick()                               # the host's clock: its open runs are polled (at most every POLL_S)

An **episode** begins with a failure that a sign-in helps while the tool has none going, and ends at `done` (by its run, by
a run of the tool that ended well, or because the tool says it is signed in: `by` `browser` | `terminal` | `elsewhere`).
`auto` is true from its start until the first `start(auto=True)`: a second page, a reload or a second failure open nothing
more by themselves. Each change publishes `bus.SIGN_IN`; `done` also `bus.SIGNED_IN`. Never a toast or a dialog.
"""
from __future__ import annotations

import os
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

from orkboard import tools
from orkboard.core import bus as b
from orkboard.realm import event_log, harnesses, sign_in, tool_errors
from orkboard.realm.sign_in import POLL_S, WAIT_S, SignInError  # noqa: F401  (SignInError: the commands' refusal)

HOLD_H = 24                      # what waits for a sign-in waits at most this long, then it fails as it did
PROBE_S = 30                     # how often a tool that needs its sign-in is asked whether it was signed in elsewhere
GRACE_S = 60                     # a failure this soon after a sign-in, of a tool that says it is signed in, begins nothing
NEEDED, OPEN, DONE, FAILED, NONE = "needed", "open", "done", "failed", "none"
KNOWN_WHY = ("timeout", "cancelled", "refused", "no_browser")      # the event log keeps only these, else "check"


class SignIns:
    def __init__(self, bus: Any, env: dict | None = None, state_dir: Path | None = None,
                 clock: Callable[[], float] = time.time, *,
                 start: Callable[..., sign_in.Run] = sign_in.start,
                 signed_in: Callable[..., bool | None] = tools.signed_in,
                 helps: Callable[[tool_errors.ToolError], bool] | None = None,
                 which: Callable[[str], str | None] = shutil.which, platform: str = sys.platform,
                 port_busy: Callable[[], bool] = sign_in.port_busy,
                 waiting: Callable[[str], int] | None = None, root: Callable[[], Path | None] | None = None,
                 threaded: bool = True) -> None:
        """`env`: the environment the tools run in (None: this process's); `waiting(harness)`: how much is held for the
        tool now; `root()`: the shown project's folder, whose event log gets the three events (None: none written);
        `threaded` False: polls and a person's *Done* run on the caller's thread (tests)."""
        self.bus, self._env, self.state_dir, self.clock = bus, env, Path(state_dir or "."), clock
        self._start, self._signed_in, self._which, self._platform = start, signed_in, which, platform
        self._helps = helps or (lambda err: tool_errors.helps(err, self.env))
        self._port_busy, self._waiting, self._root, self._threaded = port_busy, waiting, root, threaded
        self._lock = threading.RLock()
        self._entries: dict[str, dict] = {}
        self._runs: dict[str, sign_in.Run] = {}
        self._pending: dict[str, float] = {}          # a Codex sign-in waiting for the first one's port: until when
        self._probe: dict[str, list] = {}             # harness → [next ask, whether the tool was ever told not signed in]
        self._telling: set[str] = set()               # tools whose Check runs now: its good answer is not "elsewhere"
        self._done_at: dict[str, float] = {}
        self._forced: dict[str, str] = {}             # harness → the way a person chose for the run ("terminal")
        self._ticked = float("-inf")
        self._polling = False
        self._off: list[Callable[[], None]] = []

    @property
    def env(self) -> dict:
        return dict(os.environ) if self._env is None else dict(self._env)

    # -- watching ---------------------------------------------------------------------------------

    def watch(self) -> "SignIns":
        """Hear every login failure and every run that ended well. Nothing is watched until a host does."""
        self._off = [tool_errors.watch(self._failed), tool_errors.watch_ok(self._ran)]
        return self

    def close(self) -> None:
        """Quitting Orkline: the runs stop, nothing is watched."""
        for off in self._off:
            off()
        self._off = []
        self.stop_all()

    def _failed(self, err: tool_errors.ToolError) -> None:
        """A tool's login failure was made (any thread): an episode begins when a sign-in helps."""
        err.helped = bool(self._helps(err))
        if not err.helped or harnesses.get(err.harness) is None:
            return                                      # its line says its step, as today
        with self._lock:
            e = self._entries.get(err.harness)
            if e is not None and e["state"] != DONE:
                return                                  # the episode goes on: nothing more opens by itself
            if e is not None and self.clock() - self._done_at.get(err.harness, float("-inf")) < GRACE_S \
                    and self._signed_in(err.harness, self.env) is True:
                return                                  # a run that began before the sign-in: it is held, then goes on
            e = self._begin(err.harness, tool_errors.where_now())
        self._publish(e)

    def _begin(self, harness: str, where: str) -> dict:
        h = harnesses.need(harness)
        e = {"harness": h.id, "tool": h.title, "mark": h.mark, "state": NEEDED, "by": h.sign_in_by, "auto": True,
             "type": h.sign_in_type, "since": self.clock(), "where": where, "why": "", "command": ""}
        self._entries[h.id] = e
        self._probe[h.id] = [self.clock() + PROBE_S, False]
        self._pending.pop(h.id, None)
        self._event(event_log.SIGN_IN_NEEDED, harness=h.id, where=where)
        return e

    def _ran(self, harness: str) -> None:
        """A run of the tool ended well: the person signed in elsewhere."""
        with self._lock:
            e = self._entries.get(harness)
            if e is None or e["state"] == DONE or harness in self._telling:
                return
            self._finish(harness, "elsewhere")

    # -- what the work asks ------------------------------------------------------------------------

    def blocked(self, harness: str) -> bool:
        """The tool needs its sign-in (an episode not done): what runs by itself waits (spec 45 §6)."""
        with self._lock:
            e = self._entries.get(harness)
            return e is not None and e["state"] != DONE

    def holds(self, err: Exception) -> bool:
        """A failure that a sign-in helps: the work that hit it is held for the sign-in instead of failed."""
        if not isinstance(err, tool_errors.ToolError):
            return False
        if err.helped is None:
            err.helped = bool(self._helps(err))
        return err.helped

    def snapshot(self) -> list[dict]:
        """The snapshot's `sign_in`: the tools not done, in the registry's order."""
        with self._lock:
            return [self._public(self._entries[h]) for h in harnesses.ids() if h in self._entries
                    and self._entries[h]["state"] != DONE]

    def entry(self, harness: str) -> dict | None:
        with self._lock:
            e = self._entries.get(harness)
            return self._public(e) if e is not None else None

    def _public(self, e: dict) -> dict:
        try:
            waiting = int(self._waiting(e["harness"])) if self._waiting else 0
        except Exception:                               # a count never stops the page
            waiting = 0
        return {**e, "waiting": waiting}

    # -- the commands -----------------------------------------------------------------------------

    def start(self, harness: str, auto: bool = False, by: str | None = None) -> dict:
        """The tool's own sign-in; one run per tool (an open one is returned, never a second). `auto` is taken once per
        episode, by the first page that asks. `by` \"terminal\": a terminal window opens with the tool, not its browser way
        (after a browser that did not open); None | \"browser\": the tool's own way."""
        if by not in (None, "browser", "terminal"):
            raise SignInError('by is "terminal" or "browser"')
        h = harnesses.get(harness)
        if h is None:
            raise SignInError(f"{harness} is not one of the AI tools")
        if not self._which(h.bin):
            raise SignInError(f"{h.title} is not found on this computer")
        with self._lock:
            e = self._entries.get(harness)
            if e is None or e["state"] == DONE:
                e = self._begin(harness, "ask")
            if e["state"] == OPEN or (auto and not (e["auto"] and e["state"] == NEEDED)):
                return self._public(e)
            e["auto"] = False
            e.update(why="", command="")
            if by == "terminal":
                self._forced[h.id] = by
            else:
                self._forced.pop(h.id, None)
            if h.id == "codex" and self._port_busy():   # one Codex sign-in at a time on the computer: it waits for the port
                self._pending[h.id] = self.clock() + WAIT_S
                e.update(state=OPEN, by=self._forced.get(h.id, h.sign_in_by))
            else:
                self._open(h.id, e)
            out = self._public(e)
        self._publish(e)
        return out

    def _open(self, harness: str, e: dict) -> None:
        way = {"by": self._forced[harness]} if harness in self._forced else {}      # only a chosen way is passed on
        run = self._start(harness, self.env, self.state_dir, platform=self._platform, which=self._which, **way)
        self._runs[harness] = run
        e.update(state=OPEN, by=run.by)
        if run.outcome is not None:                      # none: this computer has no terminal to open
            self._ended(harness, run.outcome)

    def cancel(self, harness: str) -> dict | None:
        with self._lock:
            run = self._runs.get(harness)
            e = self._entries.get(harness)
            if e is None or e["state"] != OPEN:
                return self._public(e) if e is not None else None
            if run is not None:
                self._ended(harness, run.cancel())
            else:
                self._pending.pop(harness, None)
                self._ended(harness, sign_in.Outcome("failed", "cancelled"))
            return self._public(e)

    def done(self, harness: str) -> dict | None:
        """*Done*: the person says a terminal sign-in is done (a tool that cannot be told): it is told, as `signed_in`
        or the Check says."""
        with self._lock:
            run, e = self._runs.get(harness), self._entries.get(harness)
            if e is None or run is None or e["state"] != OPEN:
                raise SignInError("No sign-in of this tool is open")
            self._telling.add(harness)

        def tell() -> None:
            try:
                out = run.told()
            finally:
                with self._lock:
                    self._telling.discard(harness)
            with self._lock:
                if self._runs.get(harness) is run:
                    self._ended(harness, out)

        self._thread(tell, f"sign-in-told-{harness}")
        return self.entry(harness)

    def stop_all(self) -> None:
        """Stop all: every open run is cancelled."""
        for harness in list(self._runs) + [h for h in self._pending if h not in self._runs]:
            self.cancel(harness)

    # -- the clock --------------------------------------------------------------------------------

    def tick(self, now: float | None = None) -> None:
        """The host's clock: the open runs are polled, a Codex sign-in waiting for its port tried, and a tool that needs
        its sign-in asked now and then whether it was signed in elsewhere; at most every `POLL_S`."""
        t = self.clock()
        if t - self._ticked < POLL_S or self._polling:
            return
        self._ticked = t
        if not (self._runs or self._pending or any(e["state"] != DONE for e in self._entries.values())):
            return
        self._polling = True
        self._thread(self.poll, "sign-in-poll")

    def poll(self) -> None:
        try:
            with self._lock:
                runs = list(self._runs.items())
            for harness, run in runs:                   # its end may ask the tool (a Check): not under the lock
                with self._lock:
                    self._telling.add(harness)
                try:
                    out = run.poll()
                finally:
                    with self._lock:
                        self._telling.discard(harness)
                if out is not None:
                    with self._lock:
                        if self._runs.get(harness) is run:
                            self._ended(harness, out)
            with self._lock:
                for harness, until in list(self._pending.items()):
                    if self.clock() > until:
                        self._pending.pop(harness)
                        self._ended(harness, sign_in.Outcome("failed", "timeout"))
                    elif not self._port_busy():
                        self._pending.pop(harness)
                        self._open(harness, self._entries[harness])
                        self._publish(self._entries[harness])
            self._probe_all()
        finally:
            self._polling = False

    def _probe_all(self) -> None:
        """A tool that needs its sign-in and has none going: signed in elsewhere? (nothing runs to tell, while it is held)"""
        t = self.clock()
        for harness in list(self._entries):
            with self._lock:
                e, probe = self._entries.get(harness), self._probe.get(harness)
                if e is None or probe is None or e["state"] in (DONE, OPEN) or t < probe[0]:
                    continue
                probe[0] = t + PROBE_S
            got = self._signed_in(harness, self.env)
            with self._lock:
                e = self._entries.get(harness)
                if e is None or e["state"] in (DONE, OPEN):
                    continue
                if got is False:
                    probe[1] = True
                elif got is True and probe[1]:        # told not signed in before, signed in now
                    self._finish(harness, "elsewhere")

    def _thread(self, fn: Callable[[], None], name: str) -> None:
        if self._threaded:
            threading.Thread(target=fn, daemon=True, name=name).start()
        else:
            fn()

    # -- ending -----------------------------------------------------------------------------------

    def _ended(self, harness: str, out: sign_in.Outcome) -> None:
        """A run ended (lock held)."""
        run = self._runs.pop(harness, None)
        e = self._entries[harness]
        if out.state == "done":
            self._finish(harness, run.by if run is not None else e["by"])
            return
        if out.state == "none":
            e.update(state=NONE, why="", command=out.command)
        else:
            e.update(state=FAILED, why=out.why, command="")
            self._event(event_log.SIGN_IN_FAILED, harness=harness, why=out.why if out.why in KNOWN_WHY else "check")
        self._publish(e)

    def _finish(self, harness: str, by: str) -> None:
        """The episode ends: the tool is signed in (lock held)."""
        run = self._runs.pop(harness, None)
        if run is not None and run.outcome is None:
            run.cancel()
        self._pending.pop(harness, None)
        e = self._entries[harness]
        e.update(state=DONE, why="", command="")
        self._done_at[harness] = self.clock()
        self._event(event_log.SIGNED_IN, harness=harness, by=by, s=round(self.clock() - e["since"], 1))
        self._publish(e)
        self.bus.publish(b.SIGNED_IN, harness=harness)

    def _publish(self, e: dict) -> None:
        p = self._public(e)
        self.bus.publish(b.SIGN_IN, **{k: p[k] for k in ("harness", "tool", "state", "by", "auto", "why", "command",
                                                          "waiting")})

    def _event(self, name: str, **fields: Any) -> None:
        root = self._root() if self._root else None
        if root is not None:
            event_log.record(root, name, **fields)
