"""Spec 47 §1, §6 on the system's hold (gui/awake.py): each system's command and its end with this process, on and let
go, a refused hold, the old setting's `true` / `false`, and the power per system. No process is started."""
from __future__ import annotations

import os

import pytest

from orkboard import settings
from orkboard.gui import awake
from orkboard.gui.awake import Awake, on_power


class Proc:
    def __init__(self, dead: bool = False) -> None:
        self.dead, self.ended = dead, False

    def poll(self):
        return 1 if self.dead or self.ended else None

    def terminate(self) -> None:
        self.ended = True

    def wait(self, timeout=None) -> int:
        return 0

    def kill(self) -> None:
        self.ended = True


class Popen:
    def __init__(self, dead: bool = False) -> None:
        self.calls, self.dead, self.procs = [], dead, []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        self.procs.append(Proc(self.dead))
        return self.procs[-1]


def make(platform, tools=("caffeinate", "systemd-inhibit", "tail"), dead=False, windows=None):
    popen = Popen(dead)
    a = Awake(popen=popen, which=lambda t: f"/bin/{t}" if t in tools else None, platform=platform, settle=0,
              windows=windows or (lambda flags: 1))
    a.running = True
    return a, popen


def test_a_mac_holds_with_caffeinate_against_idle_sleep_for_this_process():
    a, popen = make("darwin")
    a.apply(True)
    assert a.how == "caffeinate" and popen.calls == [["caffeinate", "-i", "-w", str(os.getpid())]]
    a.apply(True)
    assert len(popen.calls) == 1                                       # one hold, however often it is asked
    a.apply(False)
    assert a.how == "" and popen.procs[0].ended


def test_linux_holds_with_systemd_inhibit_around_tail_on_this_process():
    a, popen = make("linux")
    a.apply(True)
    (cmd,) = popen.calls
    assert a.how == "systemd-inhibit" and cmd[:3] == ["systemd-inhibit", "--what=sleep", "--mode=block"]
    assert "--who=Orkline" in cmd and f"--why={awake.WHY}" in cmd and f"--pid={os.getpid()}" in cmd
    assert "tail" in cmd
    a.stop()
    assert a.how == "" and popen.procs[0].ended


def test_windows_holds_the_system_required_state_on_a_thread_of_its_own_and_lets_go():
    seen = []
    a, popen = make("win32", windows=lambda flags: seen.append(flags) or 1)
    a.apply(True)
    assert a.how == "windows" and seen == [awake.ES_CONTINUOUS | awake.ES_SYSTEM_REQUIRED] and not popen.calls
    a.apply(False)
    assert a.how == "" and seen[-1] == awake.ES_CONTINUOUS


def test_a_host_never_run_holds_nothing_and_starts_no_process():
    a, popen = make("darwin")
    a.running = False
    a.apply(True)
    assert a.how == "" and not popen.calls


def test_a_refused_hold_says_nothing_holds_and_is_not_tried_again():
    a, popen = make("linux", dead=True)
    a.apply(True)
    assert a.how == "" and not a.can() and len(popen.calls) == 1
    a.apply(True)
    assert len(popen.calls) == 1
    none, _ = make("linux", tools=())
    none.apply(True)
    assert none.how == "" and not none.can()


def test_a_windows_refusal_holds_nothing():
    a, _ = make("win32", windows=lambda flags: 0)
    a.apply(True)
    assert a.how == "" and not a.can()


def test_the_old_true_and_false_read_as_carts_and_off():
    assert settings.awake_mode(True) == "carts" and settings.awake_mode(False) == "off"
    assert settings.awake_mode("phone") == "phone" and settings.awake_mode("nonsense") == "carts"


def test_a_mac_is_on_battery_when_pmset_says_battery_power():
    def pmset(text):
        return lambda *a, **k: type("R", (), {"stdout": text})()
    assert on_power("darwin", pmset("Now drawing from 'AC Power'\n -InternalBattery-0 100%; charged")) is True
    assert on_power("darwin", pmset("Now drawing from 'Battery Power'\n -InternalBattery-0 80%; discharging")) is False

    def broken(*a, **k):
        raise FileNotFoundError("pmset")
    assert on_power("darwin", broken) is True                          # unknown counts as on power


def _supply(root, name, **files):
    d = root / name
    d.mkdir()
    for k, v in files.items():
        (d / k).write_text(v + "\n")


def test_linux_power_reads_the_power_supply(tmp_path):
    assert on_power("linux", root=tmp_path / "missing") is True        # nothing to read
    assert on_power("linux", root=tmp_path) is True                    # a desktop: no battery
    _supply(tmp_path, "BAT0", type="Battery", status="Discharging")
    _supply(tmp_path, "AC", type="Mains", online="0")
    assert on_power("linux", root=tmp_path) is False
    (tmp_path / "AC" / "online").write_text("1\n")
    assert on_power("linux", root=tmp_path) is True


def test_windows_power_reads_the_system_power_status(monkeypatch):
    monkeypatch.setattr(awake, "_windows_power", lambda: False)
    assert on_power("win32") is False
    monkeypatch.setattr(awake, "_windows_power", lambda: True)
    assert on_power("win32") is True
