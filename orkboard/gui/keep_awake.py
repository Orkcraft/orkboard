"""When the computer is kept awake (docs/specs/47-keep-awake.md §2, §3): the host's `keep_awake`.

    host.keep_awake = KeepAwake(host)      # gui/board_host.py, beside `host.awake = awake.Awake()`
    host.keep_awake.start()                # `run`: the server is up; holds at once if a reason holds
    host.keep_awake.tick(now)              # from the host's clock, at most every TICK_S
    host.keep_awake.stop()                 # the window closed, Ctrl+C, an update's restart: let go for good
    host.commands: awake.state · awake.set {mode} · awake.offer {yes}      (desktop only)

The setting is Orkline's (`keep_awake` off | carts | phone, `awake_offered`): switching between the two loses nothing.
The hold itself is `gui/awake.py`; here is only *why* and *for how long*. The hold's reason, in this order: the mode
is `off` or the computer is on battery: none; a phone is paired and the mode says so: `phone`; an ork or an operation
is at work: `work`; the Board has work waiting for tonight: `tonight`. It lets go only after LINGER_S with no reason.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from orkboard import settings
from orkboard.gui import awake as awake_
from orkboard.gui.pairing import Pairing

TICK_S = 30.0        # the host's clock asks this often
POWER_S = 60.0       # the power is read again after this
TONIGHT_S = 60.0     # a project's work for tonight is read again after this
LINGER_S = 300.0     # the hold stays this long after the last reason: a task ending and the next starting leave no gap


class KeepAwake:
    def __init__(self, host: Any, power: Callable[[], bool | None] = awake_.on_power,
                 clock: Callable[[], float] = time.monotonic, pairing: Pairing | None = None) -> None:
        self.host, self.power, self.clock = host, power, clock
        self.pairing = pairing or Pairing()
        self.why = ""                                   # what holds now ("" while it lingers or nothing holds)
        self._free_at: float | None = None              # when the last reason went
        self._tick_at = float("-inf")
        self._on_power: bool | None = None              # the last read; None: not read or unknown
        self._power_at = float("-inf")
        self._tonight_read: dict[str, tuple[float, int]] = {}    # project → (read at, rows)

    @property
    def awake(self):
        return self.host.awake

    @property
    def mode(self) -> str:
        return settings.awake_mode(self.host.machine.keep_awake)

    # -- reading -----------------------------------------------------------------------------------------------

    def _battery(self, now: float) -> bool:
        if now - self._power_at >= POWER_S:
            self._power_at = now
            try:
                self._on_power = self.power()
            except Exception:
                self._on_power = None
        return self._on_power is False

    def paired(self) -> bool:
        try:
            return bool(self.pairing.devices())
        except Exception:
            return False

    def _working(self) -> bool:
        for p in self.host.projects.open_ones:
            try:
                if p.ideas.working():
                    return True
            except Exception:
                continue
        try:
            return bool(self.host.ops.runner.busy())
        except Exception:
            return False

    def _tonight(self, now: float) -> bool:
        for p in self.host.projects.open_ones:
            read = self._tonight_read.get(p.path)
            if read is None or now - read[0] >= TONIGHT_S:
                try:
                    read = (now, int(p.ideas.tonight()))
                except Exception:
                    read = (now, 0)
                self._tonight_read[p.path] = read
            if read[1] > 0:
                return True
        return False

    def reason(self, now: float | None = None) -> str:
        """"work" | "tonight" | "phone" | "" (spec 47 §2)."""
        now = self.clock() if now is None else now
        mode = self.mode
        if mode == "off" or self._battery(now):
            return ""
        if mode == "phone" and self.paired():
            return "phone"
        if self._working():
            return "work"
        if self._tonight(now):
            return "tonight"
        return ""

    # -- holding -----------------------------------------------------------------------------------------------

    def start(self) -> None:
        """The server is up: the hold may begin (`run`)."""
        self.awake.running = True
        self.apply()

    def stop(self) -> None:
        """Let go for good: the window closed, Ctrl+C, an update's restart."""
        self.awake.running = False
        self.awake.stop()
        self.why, self._free_at = "", None

    def tick(self, now: float | None = None) -> None:
        now = self.clock() if now is None else now
        if not self.awake.running or now - self._tick_at < TICK_S:
            return
        self._tick_at = now
        self.apply(now)

    def apply(self, now: float | None = None) -> None:
        """Hold when a reason holds; let go after LINGER_S without one; at once when the mode is `off`."""
        now = self.clock() if now is None else now
        if not self.awake.running:
            return
        why = self.reason(now)
        if why:
            self.why, self._free_at = why, None
            self.awake.apply(True)
            return
        self.why = ""
        if self.mode == "off" or not self.awake.how:
            self._free_at = None
            self.awake.apply(False)
            return
        if self._free_at is None:
            self._free_at = now
        if now - self._free_at >= LINGER_S:
            self._free_at = None
            self.awake.apply(False)

    # -- what the page and the phone read ----------------------------------------------------------------------

    def machine(self) -> str:
        return "Mac" if self.awake.platform == "darwin" else "computer"

    def state(self) -> dict:
        mode = self.mode
        return {"mode": mode, "why": self.why, "holding": bool(self.awake.how),
                "battery": mode != "off" and self._on_power is False, "can": bool(self.awake.can()),
                "how": self.awake.how, "machine": self.machine(), "paired": self.paired()}

    def offer(self) -> str:
        """The machine's word while "keep it awake for the phone" is to be asked, else ""."""
        if self.host.demo or self.mode == "phone" or self.host.machine.awake_offered or not self.paired():
            return ""
        return self.machine() if self.awake.can() else ""

    def phone_line(self) -> str:
        """What the phone says of this computer's sleep (one line or "")."""
        machine = self.machine()
        if self.state()["battery"]:
            return f"Your {machine} is on battery and may sleep."
        if self.mode == "off":
            return f"Your {machine} may sleep: keeping it awake is off in its Settings."
        return ""

    # -- the page's commands (desktop only) ----------------------------------------------------------------------

    def commands(self) -> dict[str, Callable[[dict], Any]]:
        return {"awake.state": lambda a: self.state(), "awake.set": self._set, "awake.offer": self._offer}

    def _save(self) -> None:
        settings.save(self.host.machine)
        self.apply()

    def _set(self, args: dict) -> dict:
        self.host.machine.keep_awake = settings.awake_mode(args.get("mode"))
        self._save()
        return self.state()

    def _offer(self, args: dict) -> dict:
        self.host.machine.awake_offered = True
        if args.get("yes") is True:
            self.host.machine.keep_awake = "phone"
        self._save()
        return self.state()
