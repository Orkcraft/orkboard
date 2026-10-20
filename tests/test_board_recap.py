"""Spec 42 A (docs/specs/42-coming-back.md §1.1, Tests → A): `board_recap.build` on a fixture log and ledgers, and
`idea_spend.between`. Code, no model."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from orkboard.realm import board_recap, event_log, idea_spend, ideas

NOW = dt.datetime(2026, 10, 20, 12, 0).astimezone()
SINCE = NOW - dt.timedelta(hours=9)


def _at(hours_ago: float) -> dt.datetime:
    return NOW - dt.timedelta(hours=hours_ago)


def _log(root: Path, event: str, hours_ago: float, **fields) -> None:
    row = event_log.line(event, at=_at(hours_ago), **fields)
    target = event_log.path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _ledger(state: Path, slug: str, hours_ago: float, cost, naive: bool = True) -> None:
    folder = state / "ideas" / slug
    folder.mkdir(parents=True, exist_ok=True)
    at = _at(hours_ago)
    row = {"at": (at.replace(tzinfo=None) if naive else at).isoformat(timespec="seconds"), "step": "task", "task": "k1", "round": 1,
           "role": "grunt", "cost": cost}
    with (folder / idea_spend.FILE).open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _rows(*items, goals=("offline",)):
    return {"ideas": [{"slug": s, "short": s.title(), "title": f"Title of {s}", "track": "offline", "state": st} for s, st in items],
            "tracks": [{"slug": g, "short": g.title(), "title": f"{g.title()} goal"} for g in goals]}


def _plan(state: Path, slug: str, *tasks) -> None:
    folder = state / "ideas" / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(json.dumps({"idea": slug, "tasks": [{"id": i, "title": t, "state": s} for i, t, s in tasks]}))


@pytest.fixture
def where(tmp_path):
    root, state = tmp_path / "wiki", tmp_path / "state"
    root.mkdir()
    state.mkdir()
    return root, state


def test_each_list_comes_from_its_events(where):
    root, state = where
    _log(root, "task_state", 8, idea="queue", task="k1", state="merged", was="review", round=1)
    _log(root, "task_state", 7, idea="queue", task="k2", state="merged", was="review", round=2)
    _log(root, "task_state", 6, idea="csv", task="k1", state="merged", was="review", round=1)
    _log(root, "task_state", 12, idea="csv", task="k2", state="merged", was="review", round=1)           # before the period
    _log(root, "task_state", 5, idea="gone", task="k1", state="merged", was="review", round=1)           # a deleted idea
    _log(root, "goal_accepted", 4, goal="offline", met=False, by="Product manager")
    _log(root, "goal_accepted", 3, goal="offline", met=True, by="Product manager")                        # the last per goal
    _log(root, "goal_accepted", 3, goal="deleted", met=True, by="Growth")
    _log(root, "night_run", 5, drafted=2, started=1, refreshed=0, proposed=1)
    _log(root, "night_run", 4, drafted=0, started=0, refreshed=0, proposed=1)
    _log(root, "proposal_made", 4, idea="retry", goal="offline")
    _log(root, "proposal_made", 4, idea="taken", goal="offline")
    _log(root, "task_state", 2, idea="table", task="k1", state="failed", was="running", round=1)
    _log(root, "task_state", 2, idea="fixed", task="k1", state="failed", was="running", round=1)
    _plan(state, "table", ("k1", "The table", "failed"))
    _plan(state, "fixed", ("k1", "Fixed since", "review"))
    rows = _rows(("queue", "working"), ("csv", "done"), ("retry", "proposed"), ("taken", "ready"), ("table", "working"), ("fixed", "working"))
    got = board_recap.build(root, state, SINCE, NOW, rows)
    assert got["hours"] == 9 and got["into"] == "dev" and got["nights"] == 0 and got["waits"] == {"you": 0, "review": 0}
    assert got["merged"]["tasks"] == 4 and got["merged"]["first_time"] == 3          # the deleted idea's merge is counted, not listed
    assert got["merged"]["ideas"] == [
        {"slug": "queue", "short": "Queue", "title": "Title of queue", "goal": "offline", "done": False},
        {"slug": "csv", "short": "Csv", "title": "Title of csv", "goal": "offline", "done": True}]
    assert got["flags"] == [{"goal": "offline", "short": "Offline", "title": "Offline goal", "met": True, "by": "Product manager"}]
    assert got["night"] == {"drafted": 2, "started": 1, "refreshed": 0, "proposed": 2}
    assert got["proposed"] == [{"slug": "retry", "short": "Retry", "title": "Title of retry", "goal": "offline"}]
    assert got["failed"] == [{"slug": "table", "short": "Table", "title": "Title of table", "task": "The table"}]
    assert got["empty"] is False


def test_a_quiet_night_a_lone_cost_and_an_empty_period(where):
    root, state = where
    _log(root, "night_run", 5, drafted=0, started=0, refreshed=0, proposed=0)
    _ledger(state, "queue", 5, 1.5)
    got = board_recap.build(root, state, SINCE, NOW, _rows(("queue", "working")))
    assert got["night"] is None and got["usd"] == 1.5 and got["empty"] is True       # a cost alone makes no card
    got = board_recap.build(root, state, SINCE, NOW, _rows(("queue", "working")), into="main")
    assert got["into"] == "main"
    _log(root, "task_state", 5, idea="queue", task="k1", state="merged", was="review", round=1)
    assert board_recap.build(root, state, SINCE, NOW, _rows(("queue", "working")))["empty"] is False


def test_usd_is_null_when_unpriced_and_zero_when_none(where):
    root, state = where
    assert board_recap.build(root, state, SINCE, NOW, _rows())["usd"] == 0.0
    _ledger(state, "queue", 3, None)
    assert board_recap.build(root, state, SINCE, NOW, _rows())["usd"] is None
    _ledger(state, "queue", 2, 0.337)
    assert board_recap.build(root, state, SINCE, NOW, _rows())["usd"] == 0.34


def test_times_with_and_without_an_offset(where):
    root, state = where
    assert board_recap.when("2026-10-20T09:00:00").utcoffset() is not None
    assert board_recap.when("2026-10-20T09:00:00+05:00") == dt.datetime(2026, 10, 20, 4, 0, tzinfo=dt.timezone.utc)
    assert board_recap.when("nonsense") is None and board_recap.when(None) is None
    far = dt.timezone(dt.timedelta(hours=-11))                                       # a line written in another offset is placed by its instant
    row = event_log.line("task_state", at=_at(3).astimezone(far), idea="queue", task="k1", state="merged", was="review", round=1)
    event_log.path(root).parent.mkdir(parents=True)
    event_log.path(root).write_text(json.dumps(row) + "\n")
    assert board_recap.build(root, state, SINCE, NOW, _rows(("queue", "working")))["merged"]["tasks"] == 1


def test_between_is_a_half_open_period_over_every_ledger(where):
    _root, state = where
    _ledger(state, "a", 10, 9.0)                                                     # before
    _ledger(state, "a", 8, 1.0)
    _ledger(state, "b", 8, 2.0, naive=False)
    _ledger(state, "a", 0, 4.0)                                                      # at `now`: not in the period
    goal = state / "goals" / "offline"
    goal.mkdir(parents=True)
    (goal / idea_spend.FILE).write_text(json.dumps({"at": _at(2).replace(tzinfo=None).isoformat(), "cost": 0.5}) + "\n")
    (state / "ideas" / idea_spend.BOARD).write_text(json.dumps({"at": _at(1).replace(tzinfo=None).isoformat(), "cost": None}) + "\n")
    assert idea_spend.between(state, SINCE, NOW) == 3.5
    assert idea_spend.between(state, NOW + dt.timedelta(hours=1), NOW + dt.timedelta(hours=2)) == 0.0
