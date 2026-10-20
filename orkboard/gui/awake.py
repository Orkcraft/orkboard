"""The system's hold (docs/specs/47-keep-awake.md §1): the computer does not go to sleep by itself while this process
lives and the hold is on. It holds against idle sleep only (never the screen, a sleep the person asks for, a closed lid),
and it ends with this process even when that is killed. *When* to hold is `gui/keep_awake.py`'s.

    awake = Awake()
    awake.running = True               # the host serves (a host never run holds nothing, starts no process)
    awake.apply(True)                  # hold; apply(False) lets go; idempotent: one process for any number of calls
    awake.how                          # "caffeinate" | "systemd-inhibit" | "windows" | "" (nothing holds)
    awake.can()                        # this computer has a way to hold
    on_power()                         # mains power, or a machine that says nothing of a battery (unknown: True)

The three ways: macOS `caffeinate -i -w <pid>`; Linux `systemd-inhibit --what=sleep --mode=block` around
`tail --pid=<pid>`; Windows `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` on a thread of its own.
A hold refused (no logind, no right to inhibit, a container) ends at once: `how` stays "".

Written from the spec's description: Orkline's `orkcraft/gui/awake.py` was not at hand, and Orkboard imports no module
of Orkline's.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

WHO = "Orkline"      # the product's name in the interface (decisions §50.1)
WHY = "Orkline: the orks keep working, and a paired phone reaches this computer, while the screen is off"
SETTLE_S = 0.25      # a hold that is refused ends within this long
ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
POWER_ROOT = Path("/sys/class/power_supply")


def _set_execution_state(flags: int) -> int:
    import ctypes
    return int(ctypes.windll.kernel32.SetThreadExecutionState(flags))      # type: ignore[attr-defined]


class Awake:
    """`apply(want)`, `stop()`, `how`, `can()`, `running`; `popen`, `which`, `platform`, `settle` and `windows` are the
    tests' to fake."""

    def __init__(self, popen: Callable[..., Any] = subprocess.Popen, which: Callable[[str], str | None] = shutil.which,
                 platform: str | None = None, settle: float = SETTLE_S,
                 windows: Callable[[int], int] = _set_execution_state) -> None:
        self.popen, self.which, self.settle, self._windows = popen, which, settle, windows
        self.platform = sys.platform if platform is None else platform
        self.running = False            # the host serves (gui/board_host.py `run`); until then nothing holds
        self.how = ""
        self._proc: Any = None
        self._thread: threading.Thread | None = None
        self._release = threading.Event()
        self._refused = False

    # -- what this computer can do ------------------------------------------------------------------------------

    def _way(self) -> str:
        if self.platform == "darwin":
            return "caffeinate" if self.which("caffeinate") else ""
        if self.platform.startswith("win"):
            return "windows"
        if self.platform.startswith("linux"):
            return "systemd-inhibit" if self.which("systemd-inhibit") and self.which("tail") else ""
        return ""

    def can(self) -> bool:
        """This computer has a way to hold (a hold once refused counts as none)."""
        return bool(self._way()) and not self._refused

    # -- holding ------------------------------------------------------------------------------------------------

    def apply(self, want: bool) -> None:
        """Hold when `want` (and the host runs), else let go; holding twice starts nothing twice."""
        if not (want and self.running):
            self.stop()
            return
        if self.how or self._refused:
            return
        way = self._way()
        if way == "caffeinate":
            self._spawn(way, ["caffeinate", "-i", "-w", str(os.getpid())])
        elif way == "systemd-inhibit":
            self._spawn(way, ["systemd-inhibit", "--what=sleep", "--mode=block", f"--who={WHO}", f"--why={WHY}",
                              "--", "tail", f"--pid={os.getpid()}", "-f", os.devnull])
        elif way == "windows":
            self._hold_windows()

    def _spawn(self, way: str, cmd: list[str]) -> None:
        try:
            proc = self.popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, ValueError):
            self._refused = True
            return
        if self.settle:
            time.sleep(self.settle)
        if proc.poll() is not None:                       # refused: it ended at once
            self._refused = True
            return
        self._proc, self.how = proc, way

    def _hold_windows(self) -> None:
        self._release = release = threading.Event()
        started = threading.Event()
        ok: list[bool] = []

        def hold() -> None:
            try:
                ok.append(bool(self._windows(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)))
            except Exception:
                ok.append(False)
            started.set()
            if ok[0]:
                release.wait()
                try:
                    self._windows(ES_CONTINUOUS)
                except Exception:
                    pass

        thread = threading.Thread(target=hold, daemon=True, name="awake")
        thread.start()
        started.wait(5)
        if ok and ok[0]:
            self._thread, self.how = thread, "windows"
        else:
            release.set()
            self._refused = True

    def stop(self) -> None:
        """Let go, and kill the process that holds."""
        proc, self._proc = self._proc, None
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        if self._thread is not None:
            self._release.set()
            self._thread.join(2)
            self._thread = None
        self.how = ""


# -- power ------------------------------------------------------------------------------------------------------

def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _linux_power(root: Path) -> bool:
    try:
        entries = sorted(root.iterdir())
    except OSError:
        return True
    batteries, mains_online = [], False
    for e in entries:
        kind = _read(e / "type").lower()
        if kind == "battery" and _read(e / "scope").lower() != "device":
            batteries.append(e)
        elif kind in ("mains", "usb", "ups") and _read(e / "online") == "1":
            mains_online = True
    if not batteries or mains_online:
        return True
    return not any(_read(b / "status").lower() == "discharging" for b in batteries)


def _windows_power() -> bool:
    import ctypes

    class Status(ctypes.Structure):
        _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte), ("BatteryLifePercent", ctypes.c_ubyte),
                    ("SystemStatusFlag", ctypes.c_ubyte), ("BatteryLifeTime", ctypes.c_ulong),
                    ("BatteryFullLifeTime", ctypes.c_ulong)]

    status = Status()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):    # type: ignore[attr-defined]
        return True
    return status.ACLineStatus != 0


def on_power(platform: str | None = None, run: Callable[..., Any] = subprocess.run, root: Path = POWER_ROOT) -> bool:
    """On mains power, or a machine that says nothing of a battery (a desktop); unknown counts as on power."""
    platform = sys.platform if platform is None else platform
    try:
        if platform == "darwin":
            out = run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5).stdout or ""
            return "battery power" not in out.lower()
        if platform.startswith("linux"):
            return _linux_power(Path(root))
        if platform.startswith("win"):
            return _windows_power()
    except Exception:
        return True
    return True
