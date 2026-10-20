"""Spec 42 F (docs/specs/42-coming-back.md §6, Tests → F): the Board's nights and the work of the last seven days on a fixture
log and ledgers, and `ideas.week_work`. Code, no model."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import board_week, event_log, idea_spend, ideas, op_runs

SETTINGS = {"night": "01:00-07:00"}
NOW = dt.datetime(2026, 10, 20, 12, 0).astimezone()


def at(day, hour, minute=0):
    return dt.datetime.combine(dt.date(2026, 10, day), dt.time(hour, minute)).astimezone()


def log(root: Path, event: str, when: dt.datetime, **fields):
    target = event_log.path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event_log.line(event, at=when, **fields)) + "\n")


def run(root, when, **counts):
    log(root, "night_run", when, **{"drafted": 0, "started": 0, "refreshed": 0, "proposed": 0, **counts})


@pytest.fixture
def root(tmp_path):
    return tmp_path


def test_a_night_is_worked_by_a_task_or_a_night_run_idle_with_a_run_and_nothing_and_off_without_one(root):
    run(root, at(19, 1, 5), drafted=2)                                        # night of the 19th: worked by the run
    run(root, at(18, 1, 5))                                                   # the 18th: a run, nothing worked → idle
    log(root, "task_state", at(17, 3), idea="a", task="k1", state="merged", was="review", round=1)       # the 17th: a task, no run → worked
    log(root, "task_state", at(16, 3), idea="a", task="k1", state="running", was="ready", round=1)       # the 16th: nothing reached Review → off
    log(root, "task_state", at(15, 5), idea="a", task="k2", state="review", was="running", round=1)
    run(root, at(15, 1, 30))
    got = board_week.nights(root, SETTINGS, NOW, n=6)
    assert [(n["date"], n["kind"]) for n in got] == [("2026-10-20", "off"), ("2026-10-19", "worked"), ("2026-10-18", "idle"),
                                                    ("2026-10-17", "worked"), ("2026-10-16", "off"), ("2026-10-15", "worked")]


def test_today_s_night_counts_only_once_it_has_ended(root):
    run(root, at(20, 1, 5), drafted=1)
    assert board_week.nights(root, SETTINGS, at(20, 6, 0), n=1)[0]["date"] == "2026-10-19"       # still the night: yesterday's is the last that ended
    assert board_week.nights(root, SETTINGS, at(20, 7, 0), n=1) == [{"date": "2026-10-20", "kind": "worked"}]


def test_a_window_across_midnight_starts_the_evening_before_its_date(root):
    run(root, at(19, 23, 30), proposed=1)                                       # inside the night that ends on the 20th
    log(root, "task_state", at(19, 22, 59), idea="a", task="k1", state="merged", was="review", round=1)      # before it began: not in it
    got = board_week.nights(root, {"night": "23:00-07:00"}, NOW, n=2)
    assert got == [{"date": "2026-10-20", "kind": "worked"}, {"date": "2026-10-19", "kind": "off"}]
    assert board_week.nights(root, {"night": ""}, NOW) == [] and board_week.window("02:00-02:00") is None


def _ledger(state: Path, slug: str, when: dt.datetime, cost):
    folder = state / "ideas" / slug
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / idea_spend.FILE).open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": when.replace(tzinfo=None).isoformat(), "step": "task", "task": "k1", "round": 1, "role": "grunt", "cost": cost}) + "\n")


def test_this_week_sums_the_seven_days_the_ops_ledger_and_what_waits_for_tonight(root, tmp_path):
    state = tmp_path / "state"
    ops = tmp_path / "ops"
    ops.mkdir()
    _ledger(state, "a", NOW - dt.timedelta(days=3), 40.0)
    _ledger(state, "a", NOW - dt.timedelta(days=9), 99.0)                         # older than a week
    (ops / "spend.jsonl").write_text(json.dumps({"at": (NOW - dt.timedelta(days=1)).replace(tzinfo=None).isoformat(), "cost": 3.2}) + "\n")
    for n, rnd in enumerate((1, 1, 2, 1)):
        log(root, "task_state", NOW - dt.timedelta(days=2, hours=n), idea="a", task=f"k{n}", state="merged", was="review", round=rnd)
    log(root, "task_state", NOW - dt.timedelta(days=8), idea="a", task="old", state="merged", was="review", round=1)
    rows = {"ideas": [{"slug": "x", "state": "raw", "queue": "night", "start_at": ""}, {"slug": "y", "state": "plan", "queue": "", "start_at": "night"},
                      {"slug": "z", "state": "working", "queue": "", "start_at": ""}, {"slug": "d", "state": "done", "queue": "night", "start_at": ""}]}
    got = board_week.this_week(root, state, SETTINGS, NOW, rows, ops_base=ops)
    assert got["usd"] == 40.0 and got["ops_usd"] == 3.2 and (got["merged"], got["first_time"]) == (4, 3)
    assert got["usd_per_merged"] == 10.0 and got["tonight"] == 2 and got["night_on"] is True and got["into"] == "dev"
    assert sum(got["nights"].values()) == 7 and set(got["nights"]) == {"worked", "idle", "off"}
    assert set(got) == {"usd", "ops_usd", "merged", "first_time", "usd_per_merged", "nights", "tonight", "night_on", "into"}


def test_the_price_of_a_result_is_said_from_three_merged_on_and_null_when_unpriced(root, tmp_path):
    state = tmp_path / "state"
    _ledger(state, "a", NOW - dt.timedelta(days=1), 6.0)
    for n in range(2):
        log(root, "task_state", NOW - dt.timedelta(hours=n + 1), idea="a", task=f"k{n}", state="merged", was="review", round=1)
    assert board_week.this_week(root, state, SETTINGS, NOW, {})["usd_per_merged"] is None             # 2 merged: too few
    log(root, "task_state", NOW - dt.timedelta(hours=5), idea="a", task="k9", state="merged", was="review", round=1)
    assert board_week.this_week(root, state, SETTINGS, NOW, {})["usd_per_merged"] == 2.0
    _ledger(state, "b", NOW - dt.timedelta(hours=2), None)
    state2 = tmp_path / "state2"
    _ledger(state2, "b", NOW - dt.timedelta(hours=2), None)
    assert board_week.this_week(root, state2, SETTINGS, NOW, {})["usd"] is None and board_week.this_week(root, state2, SETTINGS, NOW, {})["usd_per_merged"] is None
    assert board_week.this_week(root, tmp_path / "none", {"night": ""}, NOW, {})["night_on"] is False
    assert board_week.this_week(root, tmp_path / "none", {"night": ""}, NOW, {})["usd"] == 0.0


def test_ideas_week_work_is_the_hosts_and_a_phones_and_needs_a_project(fake_repo):
    with pytest.raises(CommandError, match="Open a folder first"):
        Orkboard().command("ideas.week_work", {})
    host = Orkboard(fake_repo)
    assert BoardPhone.allowed(host, "ideas.week_work", {})
    got = host.command("ideas.week_work", {})
    json.dumps(got)
    assert got["merged"] == 0 and got["night_on"] is True and got["tonight"] == 0 and got["into"] == "dev"
    goal = ideas.save_goal(host.ideas.root(), None, "Offline", "About", None, "low")[0]
    host.command("ideas.add", {"text": "Wait for the night", "track": goal, "night": True})
    assert host.command("ideas.week_work", {})["tonight"] == 1
