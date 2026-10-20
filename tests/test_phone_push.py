"""Spec 42 C (docs/specs/42-coming-back.md §3.1, §3.3, Tests → C): the pusher with a fake clock — an answer that waits, the morning,
and every case that sends nothing — and the four `mobile.push_*` commands."""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from orkboard import schedule, settings
from orkboard.gui import phone_push
from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.gui.pairing import Pairing
from orkboard.realm import event_log, ideas

SUB = {"endpoint": "https://push.example.com/send/abc", "p256dh": "BCVxsr7N_eNgVRqvHtD0", "auth": "BTBZMqHH6r4T", "at": "2026-10-01T10:00:00", "morning": ""}
DAY = dt.date(2026, 10, 20)


def at(hour, minute=0, day=DAY):
    return dt.datetime.combine(day, dt.time(hour, minute)).astimezone()


class Rig:
    def __init__(self, repo):
        self.host = Orkboard(repo)
        self.pairing = Pairing()
        self.opened: set[str] = set()
        self.sent: list[tuple[dict, dict]] = []
        self.status = 201
        self.machine = settings.MachineSettings()
        self.machine.quiet = schedule.DEFAULT_QUIET
        pusher = self.host.pusher
        pusher.listener = SimpleNamespace(pairing=self.pairing, open_ids=lambda: set(self.opened))
        pusher.send = lambda sub, message: (self.sent.append((sub, message)), self.status)[1]
        pusher.spawn = lambda fn: fn()
        pusher.machine = lambda: self.machine
        self.device, _token, _name = self.pairing.add("Pixel 8")
        self.pairing.set_push(self.device, SUB)
        self.set_seen("2026-10-19T08:00:00")
        self.root, self.state = self.host.ideas.root(), self.host.ideas.state_dir
        self.goal = ideas.save_goal(self.root, None, "Offline mode", "About it", None, "normal")[0]

    def set_seen(self, iso):
        devices = self.pairing.devices()
        for d in devices:
            d["seen"] = iso
        self.pairing._save(devices)

    def ask(self, title, state="asks"):
        slug = ideas.add_idea(self.root, title, self.goal, self.state)
        ideas.save_state(self.state, slug, state=state)
        self.host.ideas.rev += 1
        return slug

    def tick(self, when):
        self.host.pusher.tick(when)
        return [m for _s, m in self.sent]


@pytest.fixture
def rig(fake_repo) -> Rig:
    return Rig(fake_repo)


def test_a_new_answer_that_waits_sends_once_to_a_device_without_a_socket(rig):
    assert rig.tick(at(12, 0)) == []                                    # nothing waits: the device is told 0
    rig.ask("Offline mode retry queue")
    assert rig.tick(at(12, 0, DAY)) == []                               # the clock: not twice inside TICK_S
    (msg,) = rig.tick(at(12, 1))
    assert msg == {"title": "Orkline", "body": "A spec asks · Offline mode retry queue", "tag": "needs", "badge": 1, "url": "./#needs"}
    assert rig.tick(at(12, 2)) == [msg]                                  # told: no second push for the same one


def test_within_the_gap_nothing_more_goes_and_then_the_count_and_the_row_are_said(rig):
    rig.tick(at(12, 0))
    rig.ask("First question")
    rig.tick(at(12, 1))
    rig.ask("Second question")
    assert len(rig.tick(at(12, 5))) == 1                                 # inside PUSH_GAP_S (900 s)
    (_first, second) = rig.tick(at(12, 17))
    assert second["body"].startswith("2 wait for your answer · A spec asks · ") and second["badge"] == 2 and second["tag"] == "needs"


def test_an_answer_since_makes_the_next_question_news_again(rig):
    rig.tick(at(12, 0))
    first = rig.ask("First question")
    rig.tick(at(12, 1))
    ideas.save_state(rig.state, first, state="ready")                    # answered
    rig.host.ideas.rev += 1
    rig.tick(at(13, 0))
    rig.ask("Another question")
    assert len(rig.tick(at(13, 2))) == 2


def test_none_to_a_device_with_a_socket_open_and_what_it_saw_is_not_news_later(rig):
    rig.tick(at(12, 0))
    rig.opened.add(rig.device)
    rig.ask("A question")
    assert rig.tick(at(12, 1)) == []                                     # the page says it itself; its told number is the current one
    rig.opened.clear()
    assert rig.tick(at(12, 2)) == []


def test_none_in_the_quiet_hours_or_under_do_not_disturb(rig):
    rig.tick(at(12, 0))
    rig.ask("A question")
    assert rig.tick(at(23, 30)) == [] and rig.tick(at(2, 0, DAY + dt.timedelta(days=1))) == []
    rig.machine.dnd_until = "on"
    assert rig.tick(at(12, 0, DAY + dt.timedelta(days=1))) == []
    rig.machine.dnd_until = (at(18, 0, DAY + dt.timedelta(days=1))).replace(tzinfo=None).isoformat(timespec="minutes")
    assert rig.tick(at(13, 0, DAY + dt.timedelta(days=1))) == []
    rig.machine.dnd_until = "2020-01-01T10:00"                           # long over
    assert len(rig.tick(at(14, 0, DAY + dt.timedelta(days=1)))) == 1


def test_a_proposal_a_result_to_check_and_a_phone_without_a_subscription_send_nothing(rig):
    rig.tick(at(12, 0))
    rig.ask("A proposal", state="proposed")
    assert rig.tick(at(12, 1)) == []
    rig.pairing.set_push(rig.device, None)
    rig.ask("A question")
    assert rig.tick(at(12, 40)) == []


def _log(rig, event, when, **fields):
    row = event_log.line(event, at=when, **fields)
    target = event_log.path(Path(rig.host.repo_root))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def test_the_morning_is_sent_once_a_day_when_the_device_was_not_seen_since_the_quiet_hours_began(rig):
    slug = ideas.add_idea(rig.root, "Export notes", rig.goal, rig.state)
    ideas.save_state(rig.state, slug, state="done")
    for n in range(3):
        _log(rig, "task_state", at(3, n), idea=slug, task=f"k{n}", state="merged", was="review", round=1)
    _log(rig, "goal_accepted", at(4), goal=rig.goal, met=True, by="Product manager")
    rig.set_seen("2026-10-19T20:00:00")
    assert rig.tick(at(7, 0)) == []                                      # still the quiet hours
    (msg,) = rig.tick(at(8, 30))
    assert msg == {"title": "Orkline", "body": "While you were away: 3 results in dev, 1 flag raised and nothing waits for you",
                   "tag": "recap", "badge": 0, "url": "./"}
    assert rig.pairing.get(rig.device)["push"]["morning"] == "2026-10-20"
    assert len(rig.tick(at(8, 31))) == 1 and len(rig.tick(at(9, 0))) == 1          # a restart or a later tick: not twice


def test_the_morning_says_what_waits_and_is_not_sent_to_a_device_seen_in_the_night_or_for_nothing(rig):
    slug = ideas.add_idea(rig.root, "Export notes", rig.goal, rig.state)
    _log(rig, "task_state", at(3), idea=slug, task="k1", state="merged", was="review", round=1)
    rig.ask("A question")
    rig.set_seen("2026-10-19T23:30:00")                                  # after the quiet hours began
    assert rig.tick(at(8, 30)) == []
    rig.set_seen("2026-10-19T20:00:00")
    rig.host.pusher._told[rig.device] = 1                                # the answer was told already
    (msg,) = rig.tick(at(8, 45))
    assert msg["body"] == "While you were away: 1 result in dev · 1 waits for your answer"


def test_nothing_to_say_is_no_morning(rig):
    rig.set_seen("2026-10-19T20:00:00")
    assert rig.tick(at(8, 30)) == []


def test_a_gone_subscription_is_dropped_and_the_send_is_logged(rig):
    rig.tick(at(12, 0))
    rig.ask("A question")
    rig.status = 410
    rig.tick(at(12, 1))
    assert "push" not in rig.pairing.get(rig.device)
    (line,) = [r for r in event_log.read(Path(rig.host.repo_root)) if r["event"] == "push_sent"]
    assert (line["tag"], line["devices"], line["gone"]) == ("needs", 1, 1)


def test_the_words_never_hold_a_questions_text(rig):
    slug = rig.ask("Dark mode")
    ideas.set_section(rig.root, slug, "Open questions", "- Which secret token does the vault use?")
    rig.host.ideas.rev += 1
    rig.pairing.set_push(rig.device, SUB)
    rig.host.pusher._told[rig.device] = 0
    (msg,) = rig.tick(at(12, 0))
    assert "secret token" not in json.dumps(msg) and msg["body"] == "A spec asks · Dark mode"


def test_the_kinds_are_the_pages_words():
    page = Path(phone_push.__file__).parent / "static" / "js" / "board" / "today.js"
    table = dict(re.findall(r'(\w+): "([^"]+)"', re.search(r"const KIND_WORDS = \{(.*?)\};", page.read_text(encoding="utf-8")).group(1)))
    assert {k: table[k] for k in phone_push.KIND_WORDS} == phone_push.KIND_WORDS


# -- the commands -----------------------------------------------------------------------------------------------

def _as_phone(host, name, args, device):
    return host.command(name, BoardPhone.guard(name, args, {"id": device} if device else None))


def test_the_four_commands_are_a_phones_only(rig):
    host = rig.host
    for name in ("mobile.push_key", "mobile.push_on", "mobile.push_off", "mobile.push_quiet"):
        assert BoardPhone.allowed(host, name, {})
        with pytest.raises(CommandError, match="Only a paired phone"):
            host.command(name, {})                                       # the page has no device
        with pytest.raises(CommandError, match="Only a paired phone"):
            _as_phone(host, name, {"device_id": rig.device}, None)       # a made-up id is not taken from the args


def test_push_key_gives_the_key_and_the_quiet_hours(rig):
    rig.machine.quiet = None
    got = _as_phone(rig.host, "mobile.push_key", {}, rig.device)
    assert len(got["key"]) == 87 and got["quiet"] == ""
    rig.machine.quiet = schedule.DEFAULT_QUIET
    assert _as_phone(rig.host, "mobile.push_key", {}, rig.device)["quiet"] == "23:00-08:00"


def test_push_on_keeps_the_subscription_sets_the_quiet_hours_when_none_and_logs(rig):
    rig.pairing.set_push(rig.device, None)
    rig.machine = settings.MachineSettings()                              # the file's own settings decide: quiet is off there
    args = {"endpoint": SUB["endpoint"], "p256dh": SUB["p256dh"], "auth": SUB["auth"]}
    rig.host.pusher.machine = settings.load
    got = _as_phone(rig.host, "mobile.push_on", args, rig.device)
    assert got == {"ok": True, "quiet": "23:00-08:00"} and settings.load().quiet == schedule.DEFAULT_QUIET
    kept = rig.pairing.get(rig.device)["push"]
    assert kept["endpoint"] == SUB["endpoint"] and kept["morning"] == "" and kept["at"]
    _as_phone(rig.host, "mobile.push_on", {**args, "endpoint": "https://other.example.com/x"}, rig.device)     # a renewed endpoint
    assert rig.pairing.get(rig.device)["push"]["endpoint"] == "https://other.example.com/x"
    with pytest.raises(CommandError, match="not one a phone gives"):
        _as_phone(rig.host, "mobile.push_on", {**args, "endpoint": "http://insecure"}, rig.device)
    lines = [r for r in event_log.read(Path(rig.host.repo_root)) if r["event"] == "push_set"]
    assert [(r["on"], r["device"]) for r in lines] == [(True, "phone")]


def test_push_off_and_push_quiet(rig):
    rig.host.pusher.machine = settings.load
    assert _as_phone(rig.host, "mobile.push_quiet", {"quiet": "22:00-07:30"}, rig.device) == {"ok": True}
    assert settings.load().quiet == schedule.Span.parse("22:00", "07:30")
    with pytest.raises(CommandError, match="HH:MM-HH:MM"):
        _as_phone(rig.host, "mobile.push_quiet", {"quiet": "late"}, rig.device)
    assert _as_phone(rig.host, "mobile.push_off", {}, rig.device) == {"ok": True}
    assert "push" not in rig.pairing.get(rig.device)
    lines = [r for r in event_log.read(Path(rig.host.repo_root)) if r["event"] == "push_set"]
    assert [r["on"] for r in lines] == [False]
