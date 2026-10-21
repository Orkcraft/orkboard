"""Today's events (docs/specs/49-one-window.md §2.2): `board_today.rows` on fixture log lines, and `ideas.today` on the log."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, Orkboard
from orkboard.realm import board_today, event_log, ideas

NOW = dt.datetime(2026, 10, 21, 15, 30).astimezone()
TITLES = {"ideas": {"sync": {"title": "Sync the queue", "goal": "offline"}, "csv": {"title": "CSV export", "goal": "reports"}},
          "goals": {"offline": "Work offline"},
          "tasks": {"sync": {"k1": "Queue writes", "k2": "Retry"}}}


def line(event: str, hours_ago: float = 1, **fields) -> dict:
    return event_log.line(event, at=NOW - dt.timedelta(hours=hours_ago), **fields)


def one(event: str, **fields) -> dict:
    (got,) = board_today.rows([line(event, 1, **fields)], TITLES)
    return got


def test_each_event_is_one_row_with_its_mark_tone_words_and_what_a_click_opens():
    k1 = {"idea": "sync", "task": "k1"}
    assert one("task_state", **k1, state="merged", was="review") == {
        "at": "14:30", "mark": "✓", "tone": "ok", "words": "merged into dev", "title": "Queue writes", "goal": "offline",
        "idea": "sync", "task": "k1", "open": {"kind": "result", "slug": "sync", "task": "k1"}}
    assert one("task_state", **k1, state="failed", was="running") == {
        "at": "14:30", "mark": "✗", "tone": "danger", "words": "failed", "title": "Queue writes", "goal": "offline",
        "idea": "sync", "task": "k1", "open": {"kind": "task", "slug": "sync", "task": "k1"}}
    for decision in ("back", "fix"):
        got = one("result_decided", **k1, decision=decision)
        assert (got["mark"], got["tone"], got["words"], got["title"]) == ("↺", "muted", "sent back", "Queue writes")
        assert got["open"] == {"kind": "result", "slug": "sync", "task": "k1"}
    got = one("result_decided", **k1, decision="drop")
    assert (got["mark"], got["tone"], got["words"], got["open"]["kind"]) == ("✗", "muted", "dropped", "task")
    assert one("plan_passed", idea="sync", tasks=2) == {
        "at": "14:30", "mark": "▸", "tone": "ink", "words": "the work started", "title": "Sync the queue", "goal": "offline",
        "idea": "sync", "task": "", "open": {"kind": "idea", "slug": "sync"}}
    got = one("idea_answered", idea="csv", answers=1)
    assert (got["mark"], got["tone"], got["words"], got["title"], got["goal"]) == ("·", "muted", "you answered", "CSV export", "reports")
    got = one("goal_answered", goal="offline", answers=2)
    assert (got["mark"], got["tone"], got["words"], got["title"], got["goal"], got["idea"]) == (
        "·", "muted", "you answered", "Work offline", "offline", "")
    assert got["open"] == {"kind": "goal", "slug": "offline"}
    taken, left = one("proposal_answered", idea="csv", take=True), one("proposal_answered", idea="csv", take=False)
    assert (taken["mark"], taken["words"], left["mark"], left["words"]) == ("+", "taken", "·", "left out")
    assert taken["tone"] == left["tone"] == "muted" and taken["open"] == {"kind": "idea", "slug": "csv"}
    assert one("gate_merged", commits=3, ideas=2, files=5, how="merge") == {
        "at": "14:30", "mark": "✓", "tone": "ok", "words": "dev merged into main", "title": "dev → main", "goal": "", "idea": "",
        "task": "", "open": {"kind": "gate", "slug": ""}}


def test_the_gates_row_says_the_branches_it_merged_and_a_merge_says_where_it_went():
    got = one("gate_merged", commits=1, ideas=1, files=1, how="fast-forward", into="next", main="trunk")
    assert (got["words"], got["title"]) == ("next merged into trunk", "next → trunk")
    (row,) = board_today.rows([line("task_state", idea="sync", task="k1", state="merged")], TITLES, into="next")
    assert row["words"] == "merged into next"


def test_a_check_that_found_nothing_landed_nothing_and_has_no_row():
    clean = line("task_state", idea="sync", task="k2", state="merged", was="review", check=True, clean=True)
    fixed = line("task_state", idea="sync", task="k2", state="merged", was="review", check=True)
    assert board_today.rows([clean], TITLES) == []
    assert [r["words"] for r in board_today.rows([fixed], TITLES)] == ["merged into dev"]


def test_other_events_and_lines_without_what_they_need_are_skipped():
    skipped = [line("keeper_state", idea="sync", state="plan", was="planning"), line("opened", what="idea", ref="sync"),
               line("task_state", idea="sync", task="k1", state="running", was="ready"),
               line("result_decided", idea="sync", task="k1", decision="merge"),
               line("task_state", idea="sync", state="merged"),                       # no task
               line("plan_passed", tasks=1), line("goal_answered", answers=1),        # no idea, no goal
               {"event": "plan_passed", "idea": "sync", "at": "nonsense"},
               line("idea_added", idea="sync", track="offline")]
    assert board_today.rows(skipped, TITLES) == []


def test_the_newest_is_first_and_a_later_line_wins_a_tie():
    lines = [line("plan_passed", 5, idea="sync"), line("idea_answered", 2, idea="csv"),
             line("task_state", 0.5, idea="sync", task="k2", state="failed"),
             line("proposal_answered", 2, idea="csv", take=True)]                      # the same second as the answer, written later
    got = board_today.rows(lines, TITLES)
    assert [(r["at"], r["words"]) for r in got] == [("15:00", "failed"), ("13:30", "taken"), ("13:30", "you answered"), ("10:30", "the work started")]


def test_at_most_forty_rows():
    lines = [event_log.line("plan_passed", at=NOW - dt.timedelta(minutes=n), idea="sync") for n in range(1, 61)]   # one a minute
    got = board_today.rows(lines, TITLES)
    assert len(got) == board_today.LIMIT == 40
    assert got[0]["at"] == "15:29" and got[-1]["at"] == "14:50"                          # the newest forty
    assert len(board_today.rows(lines, TITLES, limit=3)) == 3


def test_a_title_the_board_no_longer_has_reads_as_the_slug():
    gone = board_today.rows([line("plan_passed", idea="gone"), line("goal_answered", goal="lost")], TITLES)
    assert [(r["title"], r["goal"]) for r in gone] == [("lost", "lost"), ("gone", "")]
    task = board_today.rows([line("task_state", idea="sync", task="k9", state="failed")], TITLES)[0]
    assert (task["title"], task["task"]) == ("Sync the queue", "k9")                    # a lost task reads as its idea
    task = board_today.rows([line("task_state", idea="gone", task="k9", state="failed")], TITLES)[0]
    assert (task["title"], task["goal"]) == ("gone", "")
    assert board_today.rows([line("plan_passed", idea="gone")], {})[0]["title"] == "gone"


def test_midnight_cuts_the_day_by_the_instants_of_the_lines():
    midnight = board_today.midnight(NOW)
    assert midnight == dt.datetime(2026, 10, 21, 0, 0).astimezone() and midnight.utcoffset() is not None
    before = event_log.line("plan_passed", at=midnight - dt.timedelta(seconds=1), idea="sync")
    after = event_log.line("plan_passed", at=midnight, idea="csv")
    far = dt.timezone(dt.timedelta(hours=-11))                                          # written in another offset: placed by its instant
    elsewhere = event_log.line("plan_passed", at=(midnight + dt.timedelta(minutes=5)).astimezone(far), idea="csv")
    got = board_today.rows([before, after, elsewhere], TITLES, since=midnight)
    assert [r["at"] for r in got] == [(midnight + dt.timedelta(minutes=5)).strftime("%H:%M"), "00:00"]
    assert len(board_today.rows([before, after], TITLES)) == 2                          # without a cut, all of them


# -- ideas.today ----------------------------------------------------------------------------------------------------

@pytest.fixture
def host(fake_repo):
    h = Orkboard(fake_repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


def test_ideas_today_reads_the_log_since_midnight_and_joins_the_titles_from_the_board(host):
    root = host.ideas.root()
    goal = ideas.add_track(root, "Work offline")
    slug = host.command("ideas.add", {"text": "Sync the queue\nwith the server", "track": goal, "night": True})["slug"]
    ideas.save_plan(host.ideas.state_dir, slug, {"idea": slug, "tasks": [{"id": "k1", "title": "Queue writes", "state": "failed"}]})
    repo = Path(host.repo_root)
    now = dt.datetime.now().astimezone()
    old = event_log.line("task_state", at=board_today.midnight(now) - dt.timedelta(minutes=1), idea=slug, task="k1", state="failed")
    with event_log.path(repo).open("a", encoding="utf-8") as f:
        f.write(json.dumps(old) + "\n")
    event_log.record(repo, event_log.PLAN_PASSED, idea=slug, tasks=1)
    event_log.record(repo, event_log.TASK_STATE, idea=slug, task="k1", state="failed", was="running")
    event_log.record(repo, event_log.GOAL_ANSWERED, goal=goal, answers=1)
    event_log.record(repo, event_log.KEEPER_STATE, idea=slug, state="plan", was="planning")      # not a row
    event_log.record(repo, event_log.PLAN_PASSED, idea="gone", tasks=1)
    got = host.command("ideas.today")
    assert list(got) == ["events"]
    assert [(r["words"], r["title"], r["goal"]) for r in got["events"]] == [
        ("the work started", "gone", ""), ("you answered", "Work offline", goal), ("failed", "Queue writes", goal),
        ("the work started", "Sync the queue", goal)]                                  # newest first; yesterday's failure is not here
    assert all(len(r["at"]) == 5 and r["at"][2] == ":" for r in got["events"]) and BoardPhone.allowed(host, "ideas.today", {})


def test_ideas_today_of_a_quiet_day_is_empty(host):
    assert host.command("ideas.today") == {"events": []}
