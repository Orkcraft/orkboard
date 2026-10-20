"""Spec 47 §2–§4, §6 on when the computer is kept awake (gui/keep_awake.py): a fake `Awake`, a fake clock, fake power."""
from __future__ import annotations

import pytest

from orkboard import settings
from orkboard.gui import board_host, keep_awake
from orkboard.gui.keep_awake import LINGER_S, POWER_S, TICK_S, TONIGHT_S
from orkboard.gui.board_host import Orkboard
from tests.conftest import FakeAwake


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def go(self, s: float) -> float:
        self.now += s
        return self.now


class Power:
    on = True

    def __call__(self):
        return self.on


@pytest.fixture
def awake(fake_repo):
    """A host that is running (its Awake fake), a clock, the power, and what the Board and Operations are doing."""
    host = Orkboard(fake_repo)
    clock, power = Clock(), Power()
    keep = host.keep_awake
    keep.clock, keep.power = clock, power
    keep.paired = lambda: keep.phones
    keep.phones = False
    box = type("Box", (), {})()
    box.host, box.keep, box.clock, box.power, box.fake = host, keep, clock, power, host.awake
    box.working, box.tonight, box.ops = False, 0, False
    (project,) = host.projects.open_ones
    project.ideas.working = lambda: box.working
    project.ideas.tonight = lambda: box.tonight
    host.ops.runner.busy = lambda: box.ops
    keep.start()
    return box


def test_a_host_never_run_holds_nothing_and_reads_nothing(fake_repo):
    host = Orkboard(fake_repo)
    host.keep_awake.power = lambda: pytest.fail("the power is read")
    host.ideas.working = lambda: True
    host.keep_awake.tick(1e6)
    host.keep_awake.apply(1e6)
    assert host.awake.how == "" and host.awake.applied == [] and host.keep_awake.state()["holding"] is False


def test_off_never_holds(awake):
    awake.working = True
    awake.host.machine.keep_awake = "off"
    assert awake.keep.reason() == "" and awake.keep.state()["holding"] is False


def test_on_battery_nothing_holds_in_any_mode(awake):
    awake.power.on, awake.working, awake.keep.phones = False, True, True
    for mode in ("carts", "phone"):
        awake.host.machine.keep_awake = mode
        awake.clock.go(POWER_S)
        assert awake.keep.reason() == ""
    assert awake.keep.state()["battery"] is True


def test_the_power_is_read_at_most_every_minute_and_none_counts_as_on_power(awake):
    reads = []
    awake.keep.power = lambda: reads.append(1) or None
    awake.clock.go(POWER_S)
    awake.working = True
    for _ in range(3):
        assert awake.keep.reason() == "work"
    assert len(reads) == 1 and awake.keep.state()["battery"] is False


def test_carts_holds_while_the_keeper_a_task_or_an_operation_is_at_work(awake):
    assert awake.keep.reason() == ""
    awake.working = True                                   # a draft, a plan, a read, a check, the night, a task
    assert awake.keep.reason() == "work"
    awake.working, awake.ops = False, True                 # an operation running or waiting
    assert awake.keep.reason() == "work"
    awake.ops = False
    assert awake.keep.reason() == ""                       # a task at Review, a held plan, a question: none of them


def test_tonight_holds_for_work_waiting_for_the_night_and_not_for_its_proposals(awake):
    awake.tonight = 2
    awake.clock.go(TONIGHT_S)                              # the cached read of nothing is a minute old
    assert awake.keep.reason() == "tonight"
    awake.working = True
    assert awake.keep.reason() == "work"                   # inside the window the night runs it
    awake.working, awake.tonight = False, 0               # drafted and started
    awake.clock.go(TONIGHT_S)
    assert awake.keep.reason() == ""


def test_tonight_is_read_at_most_every_minute_per_project(awake):
    reads = []
    (project,) = awake.host.projects.open_ones
    project.ideas.tonight = lambda: reads.append(1) or 1
    awake.clock.go(TONIGHT_S)
    for _ in range(3):
        assert awake.keep.reason() == "tonight"
    assert len(reads) == 1
    awake.clock.go(TONIGHT_S)
    awake.keep.reason()
    assert len(reads) == 2


def test_phone_holds_with_a_phone_paired_and_falls_back_to_carts_without(awake):
    awake.host.machine.keep_awake = "phone"
    assert awake.keep.reason() == ""
    awake.working = True
    assert awake.keep.reason() == "work"
    awake.keep.phones, awake.working = True, False
    assert awake.keep.reason() == "phone"
    awake.working = True
    assert awake.keep.reason() == "phone"                  # the phone's reason comes first


def test_it_lets_go_only_after_the_linger_and_a_reason_coming_back_keeps_one_hold(awake):
    awake.fake.applied.clear()
    awake.working = True
    awake.keep.apply()
    assert awake.fake.how and awake.keep.state()["why"] == "work" and awake.fake.applied == [True]
    awake.working = False
    awake.keep.apply(awake.clock.go(10))
    assert awake.fake.how and awake.keep.state()["why"] == "" and awake.keep.state()["holding"]
    awake.working = True                                   # the next task starts inside the linger
    awake.keep.apply(awake.clock.go(LINGER_S - 20))
    assert awake.keep.state()["why"] == "work" and awake.fake.applied.count(False) == 0
    awake.working = False
    awake.keep.apply(awake.clock.go(1))
    awake.keep.apply(awake.clock.go(LINGER_S - 1))
    assert awake.fake.how
    awake.keep.apply(awake.clock.go(1))
    assert awake.fake.how == "" and awake.keep.state()["holding"] is False


def test_tick_asks_at_most_every_thirty_seconds(awake):
    awake.working = True
    awake.keep.tick(awake.clock.go(0))
    first = len(awake.fake.applied)
    awake.keep.tick(awake.clock.go(TICK_S - 1))
    assert len(awake.fake.applied) == first
    awake.keep.tick(awake.clock.go(1))
    assert len(awake.fake.applied) == first + 1


def test_set_saves_and_applies_at_once_and_off_lets_go_with_no_linger(awake):
    awake.working = True
    awake.keep.apply()
    assert awake.fake.how
    state = awake.host.command("awake.set", {"mode": "off"})
    assert state["mode"] == "off" and state["holding"] is False and awake.fake.how == ""
    assert settings.load().keep_awake == "off"
    assert awake.host.command("awake.set", {"mode": "nonsense"})["mode"] == "carts"       # an unknown value reads carts
    assert awake.fake.how and settings.load().keep_awake == "carts"
    assert awake.host.command("awake.state") == awake.keep.state()


def test_state_has_the_keys_the_page_reads(awake):
    s = awake.keep.state()
    assert set(s) == {"mode", "why", "holding", "battery", "can", "how", "machine", "paired"}
    assert s["machine"] == "computer" and s["can"] is True
    awake.fake.platform = "darwin"
    assert awake.keep.state()["machine"] == "Mac"


def test_offer_once_and_yes_makes_the_mode_phone(awake):
    assert awake.keep.offer() == ""                         # no phone
    awake.keep.phones = True
    assert awake.keep.offer() == "computer"
    awake.fake.platform = "darwin"
    assert awake.keep.offer() == "Mac"
    state = awake.host.command("awake.offer", {"yes": True})
    assert state["mode"] == "phone" and awake.keep.offer() == "" and settings.load().awake_offered is True
    assert settings.load().keep_awake == "phone"


def test_not_now_answers_it_and_keeps_the_mode(awake):
    awake.keep.phones = True
    awake.host.command("awake.offer", {"yes": False})
    assert awake.keep.offer() == "" and awake.host.machine.keep_awake == "carts"


def test_no_offer_in_the_mode_phone_when_it_cannot_or_in_the_demo(awake):
    awake.keep.phones = True
    awake.host.machine.keep_awake = "phone"
    assert awake.keep.offer() == ""
    awake.host.machine.keep_awake = "carts"
    awake.fake.can = lambda: False
    assert awake.keep.offer() == ""
    awake.fake.can = lambda: True
    awake.host.demo = True
    assert awake.keep.offer() == ""


def test_the_phone_says_battery_and_off(awake):
    assert awake.keep.phone_line() == ""
    awake.host.machine.keep_awake = "off"
    assert awake.keep.phone_line() == "Your computer may sleep: keeping it awake is off in its Settings."
    awake.host.machine.keep_awake = "carts"
    awake.power.on = False
    awake.clock.go(POWER_S)
    awake.keep.reason()
    assert awake.keep.phone_line() == "Your computer is on battery and may sleep."
    awake.fake.platform = "darwin"
    assert awake.keep.phone_line() == "Your Mac is on battery and may sleep."


def test_run_hands_stop_to_show_and_it_lets_go_when_the_window_closes(fake_repo, monkeypatch):
    shown = {}

    def show(host, server, thread, browser, **kw):
        host.ideas.working = lambda: True
        host.keep_awake.apply()
        shown["held"], shown["stop"] = host.awake.how, kw.get("stop")
        kw["stop"]()
        shown["after"] = host.awake.how

    class Server:
        url = "http://x"

        def __init__(self, host, port=0) -> None:
            pass

        def start_thread(self):
            return None

    monkeypatch.setattr(board_host, "show", show)
    monkeypatch.setattr("orkboard.gui.server.Server", Server)
    monkeypatch.setattr(keep_awake.KeepAwake, "start", lambda self: setattr(self.awake, "running", True))
    assert board_host.run(fake_repo, browser=True) == 0
    assert shown["held"] == "systemd-inhibit" and shown["after"] == "" and shown["stop"] is not None
