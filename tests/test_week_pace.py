"""Spec 44 A (docs/specs/44-week-pace.md, Tests → A): the Claude week's pace, the reserve per window, who put work off
to the night, when the Board's Low work goes (by day when the week is ahead, held at night when it is behind), the
`week_reset` event and the Map's data. Code, a fake clock and fake limits, no model."""
from __future__ import annotations

import datetime as dt
import json
import threading
import time
from types import SimpleNamespace

import pytest

from orkboard.core import idea_night
from orkboard.core.board_limits import BoardLimits
from orkboard.gui.board_host import Orkboard
from orkboard.realm import board_map, event_log, idea_target, ideas
from orkboard.sources.limits import Limit

from tests.test_idea_night import _goal, keeper  # noqa: F401  (the keeper on a fixture repository)
from tests.test_idea_runner import plan_of, town  # noqa: F401  (the fixture repository with a stub claude)
from tests.test_runner_35 import _now_in, _pass, _runner

NOON = dt.datetime(2026, 10, 20, 12, 0).timestamp()
NIGHT = dt.datetime(2026, 10, 21, 3, 0).timestamp()
DAY = 24 * 3600


def at(ts: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(ts)


def wk(left, days, now=NOON, **more):
    """The Claude week: `left` of it, `days` to go."""
    return Limit("claude", "", "weekly", left, at(now + days * DAY), **more)


def five(left, minutes, now=NOON):
    return Limit("claude", "", "session", left, at(now + minutes * 60))


# -- §1 the pace --------------------------------------------------------------------------------------------------

def test_week_reads_the_weekly_limit_and_the_share_of_the_week_still_to_come():
    got = idea_target.week([five(0.9, 30), wk(0.6, 3.5)], NOON)
    assert got["left"] == 0.6 and got["rest"] == pytest.approx(0.5) and got["reset"] == pytest.approx(NOON + 3.5 * DAY)
    assert idea_target.week([wk(0.5, 8)], NOON)["rest"] == 1.0                    # more than a week away: the whole week
    assert idea_target.week([wk(0.5, -1)], NOON)["rest"] == 0.0                   # a reset that has passed: none to come
    assert idea_target.week([wk(0.5, 7)], NOON)["rest"] == pytest.approx(1.0)


@pytest.mark.parametrize("limits", [
    [], [five(0.5, 30)], [wk(None, 3)], [Limit("claude", "", "weekly", 0.5, None)],            # not read · no reset
    [wk(0.5, 3, error="Not logged in")], [Limit("codex", "", "weekly", 0.5, at(NOON + DAY))],   # an error · another tool
    [Limit("claude", "API key", "weekly", None, None, "an API key has no limits")]])
def test_no_weekly_limit_read_is_no_week_and_no_pace(limits):
    assert idea_target.week(limits, NOON) is None and idea_target.pace(limits, NOON) is None


@pytest.mark.parametrize("left,want", [(0.61, "ahead"), (0.60, "ahead"), (0.59, "even"), (0.50, "even"),
                                       (0.49, "behind"), (0.0, "behind")])
def test_the_pace_is_ahead_at_ten_points_above_the_share_to_come_and_behind_below_it(left, want):
    assert idea_target.pace([wk(left, 3.5)], NOON) == want                       # 3.5 days to go: 0.50 of the week to come


def test_the_pace_at_the_ends_of_the_week():
    assert idea_target.pace([wk(1.0, 7)], NOON) == "even"                          # the week has just come back: all of it left
    assert idea_target.pace([wk(1.0, 6)], NOON) == "ahead" and idea_target.pace([wk(0.85, 6)], NOON) == "behind"
    assert idea_target.pace([wk(0.1, 0)], NOON) == "ahead" and idea_target.pace([wk(0.05, 0)], NOON) == "even"
    assert idea_target.pace([wk(0.1, -1)], NOON) == "ahead"                        # a reset that has passed: nothing to come


# -- §1 the reserve, per window -----------------------------------------------------------------------------------

S = {"night": "01:00-07:00", "reserve_day": 0.3, "reserve_night": 0.1}


def test_the_reserve_equals_todays_rule_with_no_window_near_its_reset():
    far = [five(0.25, 120), wk(0.9, 3)]
    assert idea_target.reserve_held(far, S, NOON) == pytest.approx(NOON + 120 * 60)       # day: 0.25 ≤ 0.30
    assert idea_target.reserve_held([five(0.35, 120), wk(0.9, 3)], S, NOON) is None
    assert idea_target.reserve_held([five(0.25, 120), wk(0.9, 3)], S, NIGHT) is None      # night: 0.25 > 0.10
    assert idea_target.reserve_held([five(0.08, 120), wk(0.9, 3)], S, NIGHT) is not None
    assert idea_target.reserve_held([five(0.9, 120), wk(0.25, 3)], S, NOON) == pytest.approx(NOON + 3 * DAY)
    assert idea_target.reserve_held([], S, NOON) is None


def test_by_day_within_an_hour_of_the_five_hour_reset_its_reserve_is_the_nights_unless_the_week_is_behind():
    soon = [five(0.2, 30), wk(0.9, 3.5)]                                                 # the week is ahead
    assert idea_target.reserve_held(soon, S, NOON) is None                               # 0.2 > the night's 0.1
    assert idea_target.reserve_held([five(0.08, 30), wk(0.9, 3.5)], S, NOON) == pytest.approx(NOON + 30 * 60)
    assert idea_target.reserve_held([five(0.2, 30), wk(0.52, 3.5)], S, NOON) is None     # even: not behind
    assert idea_target.reserve_held([five(0.2, 30)], S, NOON) is None                    # no week read: not behind
    assert idea_target.reserve_held([five(0.2, 30), wk(0.35, 3.5)], S, NOON) == pytest.approx(NOON + 30 * 60)   # behind
    assert idea_target.reserve_held([five(0.2, 61), wk(0.9, 3.5)], S, NOON) is not None                        # not soon
    assert idea_target.reserve_held([five(0.2, 60), wk(0.9, 3.5)], S, NOON) is None                            # SOON_S
    # only the five-hour window is eased: the week's own share is held as today
    assert idea_target.reserve_held([five(0.9, 30), wk(0.2, 0.1)], S, NOON) is not None


# -- §2 who put it off --------------------------------------------------------------------------------------------

@pytest.fixture
def host(fake_repo):
    import sys
    h = Orkboard(fake_repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


def _goal_of(host):
    root = host.ideas.root()
    return next((t["slug"] for t in ideas.tracks(root, make=False) if t["slug"] != "general"), None) or ideas.add_track(root, "First goal")


def test_an_idea_keeps_who_put_it_off_to_the_night_and_a_state_of_before_reads_the_person(host):
    g = _goal_of(host)
    low = host.command("ideas.add", {"text": "a low one", "track": g, "priority": "low"})["slug"]
    tonight = host.command("ideas.add", {"text": "tonight by the person", "track": g, "priority": "low", "night": True})["slug"]
    high = host.command("ideas.add", {"text": "a high one tonight", "track": g, "priority": "high", "night": True})["slug"]
    state = host.ideas.state_dir
    assert ideas.state(state, low)["night_by"] == "board" and ideas.state(state, tonight)["night_by"] == "person"
    assert ideas.state(state, high)["night_by"] == "person"
    ideas.save_state(state, low, night_by="")                                         # a state of before
    assert ideas.night_by_of(ideas.state(state, low)) == "person" and ideas.night_by_of({"state": "raw"}) == "person"
    host.command("ideas.queue", {"slug": low, "queue": "night"})                       # Tonight is the person's
    assert ideas.state(state, low)["night_by"] == "person"
    assert {i["slug"]: i["night_by"] for i in host.command("ideas.board")["ideas"]}[tonight] == "person"


def _ready_plan(host, slug, risk="low", priority="low"):
    root = host.ideas.root()
    ideas.set_meta(root, slug, risk=risk, priority=priority)
    ideas.save_plan(host.ideas.state_dir, slug, {"idea": slug, "made_at": "2026-10-20T09:00:00", "todos": [],
                                                  "tasks": [{"id": "k1", "title": "Do it", "tier": "warrior", "after": [],
                                                             "state": "ready"}]})
    ideas.save_state(host.ideas.state_dir, slug, state="plan")


def test_a_plan_keeps_who_put_its_start_off_to_the_night(host):
    g = _goal_of(host)
    started = []
    host.ideas._runner = SimpleNamespace(start=started.append, tick=lambda: None)
    host.limits.rows = []                                                              # no week read: today's rule
    auto = host.command("ideas.add", {"text": "low, by itself", "track": g, "priority": "low"})["slug"]
    _ready_plan(host, auto)
    assert host.ideas.autostart(auto) == "night"
    plan = ideas.plan(host.ideas.state_dir, auto)
    assert plan["start_at"] == "night" and plan["start_at_by"] == "board" and not plan.get("by_pace") and started == []
    (passed,) = [e for e in event_log.read(host.repo_root) if e["event"] == "plan_passed"]
    assert passed["by"] == "auto" and passed["pace"] is False
    legacy = {"start_at": "night"}                                                      # a plan of before
    assert idea_target.board_low(legacy) is False and idea_target.board_low({**legacy, "start_at_by": "person"}) is False


def test_a_low_plan_the_board_passes_starts_by_day_at_once_when_the_week_is_ahead_one_at_a_time(host):
    g = _goal_of(host)
    started = []
    host.ideas._runner = SimpleNamespace(start=started.append, tick=lambda: None)
    now = time.time()
    day = dt.datetime.fromtimestamp(now)
    host.board_settings = lambda: {"target": "balance", "autostart": True, "night": _now_in(False),
                                   "reserve_day": 0.3, "reserve_night": 0.1}
    host.limits.rows = [wk(0.9, 3.5, now)]
    first = host.command("ideas.add", {"text": "low one", "track": g, "priority": "low"})["slug"]
    second = host.command("ideas.add", {"text": "low two", "track": g, "priority": "low"})["slug"]
    for s in (first, second):
        _ready_plan(host, s)
    assert host.ideas.autostart(first) == "night"
    plan = ideas.plan(host.ideas.state_dir, first)
    assert started == [first] and plan["by_pace"] is True and plan["start_at_by"] == "board"
    assert ideas.state(host.ideas.state_dir, first)["state"] == "working"
    assert host.ideas.autostart(second) == "night" and started == [first]                # a second waits for the night
    assert not ideas.plan(host.ideas.state_dir, second).get("by_pace")
    events = {e["idea"]: e for e in event_log.read(host.repo_root) if e["event"] == "plan_passed"}
    assert events[first]["pace"] is True and events[second]["pace"] is False
    assert day.year >= 2026


# -- §3 when it goes: pace_tick -----------------------------------------------------------------------------------

def _board_low(k, g, text, by="board", priority="low"):
    return ideas.add_idea(k.root, text, g, k.state, priority=priority, queue="night", night_by=by)


@pytest.fixture
def paced(keeper):
    """A keeper whose draft is a recording stub, in a project with a goal; the week is ahead at noon."""
    keeper.drafted, keeper.release = [], threading.Event()
    keeper.release.set()

    def draft(slug):
        keeper.drafted.append(slug)
        assert keeper.release.wait(10)
    keeper.draft_one = draft
    keeper.limits_now = [wk(0.9, 3.5)]
    keeper.goal = _goal(keeper, "Table")
    return keeper


def _quiet(k):
    for _ in range(300):
        if not k._pace_busy:
            return
        time.sleep(0.01)
    raise AssertionError("the pace's draft never finished")


def test_by_day_and_ahead_the_clock_drafts_the_oldest_board_low_idea_once_and_one_at_a_time(paced):
    k = paced
    first, second = _board_low(k, k.goal, "first low"), _board_low(k, k.goal, "second low")
    k.release.clear()
    assert k.pace_tick(NOON) is True
    for _ in range(300):
        if k.drafted:
            break
        time.sleep(0.01)
    assert k.drafted == [first] and k._pace_busy                                       # it is running now
    assert k.pace_tick(NOON + idea_night.PACE_S) is False and k.drafted == [first]     # one at a time
    k.release.set()
    _quiet(k)
    assert k.pace_tick(NOON + 10) is False                                             # not before PACE_S
    ideas.save_state(k.state, first, state="plan", queue="")                           # the first is drafted
    assert k.pace_tick(NOON + 2 * idea_night.PACE_S) is True
    _quiet(k)
    assert k.drafted == [first, second]


def test_the_clock_leaves_alone_what_the_pace_does_not_move(paced):
    k = paced
    mine, theirs = _board_low(k, k.goal, "the person put it off", by="person"), None
    board = _board_low(k, k.goal, "the board put it off")
    assert theirs is None
    t = NOON
    steps = [("even", [wk(0.52, 3.5)]), ("behind", [wk(0.35, 3.5)]), ("no week", []), ("the reserve holds", [wk(0.9, 3.5), five(0.2, 200)])]
    for name, limits in steps:
        k.limits_now, t = limits, t + idea_night.PACE_S
        assert k.pace_tick(t) is False, name
    k.limits_now = [wk(0.9, 3.5)]
    k.settings_now["autostart"] = False
    assert k.pace_tick(t + idea_night.PACE_S) is False                                 # autostart off: never moved
    k.settings_now["autostart"] = True
    assert k.pace_tick(NIGHT) is False                                                 # never inside the night window
    assert k.drafted == [] and ideas.state(k.state, mine)["state"] == "raw" and board
    later = NOON + 2 * DAY
    k.limits_now = [wk(0.9, 3.5, later)]
    assert k.pace_tick(later) is True
    _quiet(k)
    assert k.drafted == [board]                                                        # only the Board's, never the person's


def test_the_clock_starts_a_waiting_board_low_plan_by_day_when_ahead_one_at_a_time(paced):
    k = paced

    def waiting(text, by="board"):
        slug = ideas.add_idea(k.root, text, k.goal, k.state, priority="low")
        ideas.save_plan(k.state, slug, {"idea": slug, "passed_at": "x", "start_at": "night", "start_at_by": by, "tasks": [], "todos": []})
        ideas.save_state(k.state, slug, state="plan")
        return slug
    theirs, one, two = waiting("the person's", "person"), waiting("one"), waiting("two")
    assert k.pace_tick(NOON) is True and k.started == [one]
    assert ideas.plan(k.state, one)["by_pace"] is True and not ideas.plan(k.state, theirs).get("by_pace")
    ideas.save_state(k.state, one, state="working")
    assert k.pace_tick(NOON + idea_night.PACE_S) is False and k.started == [one]       # one at a time
    ideas.save_state(k.state, one, state="done")
    assert k.pace_tick(NOON + 2 * idea_night.PACE_S) is True and k.started == [one, two]
    assert two and theirs


def test_the_keepers_clock_reaches_pace_tick(paced):
    k = paced
    seen = []
    k.pace_tick = lambda now: seen.append(now) or False
    k.tick(NOON)
    assert seen == [NOON]


def test_the_night_leaves_the_boards_low_ideas_queued_when_the_week_is_behind_and_drafts_the_persons(paced):
    k = paced
    mine, board = _board_low(k, k.goal, "the person's", by="person"), _board_low(k, k.goal, "the board's")
    k.limits_now = [wk(0.35, 3.5, time.time())]
    k.call = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("no model"))
    counts = k.run_night("2026-10-20T01:00")
    assert k.drafted == [mine] and counts["paced"] == 1
    assert ideas.state(k.state, board)["state"] == "raw" and ideas.queue_of(ideas.state(k.state, board)) == "night"
    (run,) = [r for r in event_log.read(k.repo_root) if r["event"] == "night_run"]
    assert run["paced"] == 1
    k.drafted.clear()
    ideas.save_state(k.state, mine, state="plan", queue="")                           # the person's is drafted
    k.limits_now = [wk(0.52, 3.5, time.time())]                                        # even: the night drafts it as today
    assert k.run_night("2026-10-21T01:00")["paced"] == 0 and k.drafted == [board]
    k.drafted.clear()
    ideas.save_state(k.state, board, state="raw", queue="night")
    k.limits_now, k.settings_now["autostart"] = [wk(0.35, 3.5, time.time())], False      # autostart off: never moved
    assert k.run_night("2026-10-22T01:00")["paced"] == 0 and k.drafted == [board]


# -- §3 the gate and the runner -----------------------------------------------------------------------------------

def _gate_board(night):
    return {"night": _now_in(night), "reserve_day": 0.3, "reserve_night": 0.1, "autostart": True}


LOW = {"start_at": "night", "start_at_by": "board", "passed_by": "auto"}


def test_the_gate_lets_the_boards_low_plan_start_by_day_only_when_ahead_and_free():
    now = time.time()
    day = _gate_board(False)
    assert idea_target.gate(LOW, [wk(0.9, 3.5, now)], day, now) is None
    assert idea_target.gate(LOW, [wk(0.9, 3.5, now)], day, now, day_free=False) == "night"
    assert idea_target.gate(LOW, [wk(0.52, 3.5, now)], day, now) == "night"            # even
    assert idea_target.gate(LOW, [wk(0.2, 3.5, now)], day, now) == "night"             # behind
    assert idea_target.gate(LOW, [], day, now) == "night"                              # no week read
    assert idea_target.gate({**LOW, "start_at_by": "person"}, [wk(0.9, 3.5, now)], day, now) == "night"
    assert idea_target.gate({"start_at": "night", "passed_by": "auto"}, [wk(0.9, 3.5, now)], day, now) == "night"
    assert idea_target.gate(LOW, [wk(0.9, 3.5, now)], {**day, "autostart": False}, now) == "night"
    held = idea_target.gate(LOW, [wk(0.9, 3.5, now), five(0.2, 200, now)], day, now)    # the reserve, as for any autostart
    assert held == pytest.approx(now + 200 * 60)


def test_the_gate_holds_the_boards_low_plan_at_night_with_the_week_behind_until_the_weeks_reset():
    now = time.time()
    night = _gate_board(True)
    assert idea_target.gate(LOW, [wk(0.2, 3.5, now)], night, now) == pytest.approx(now + 3.5 * DAY)
    assert idea_target.week_hold(LOW, [wk(0.2, 3.5, now)], night, now) == pytest.approx(now + 3.5 * DAY)
    assert idea_target.gate(LOW, [wk(0.52, 3.5, now)], night, now) is None             # even: starts as today
    assert idea_target.gate(LOW, [wk(0.9, 3.5, now)], night, now) is None
    assert idea_target.gate(LOW, [], night, now) is None
    assert idea_target.gate({**LOW, "start_at_by": "person"}, [wk(0.2, 3.5, now)], night, now) is None
    assert idea_target.gate(LOW, [wk(0.2, 3.5, now)], {**night, "autostart": False}, now) is None
    assert idea_target.gate({"passed_by": "auto"}, [wk(0.2, 3.5, now)], night, now) is None   # High, Normal: today's


def test_the_runner_starts_the_boards_low_plan_by_day_only_when_ahead_and_marks_it(town):
    now = time.time()
    for limits, starts in (([wk(0.9, 3.5, now)], True), ([wk(0.52, 3.5, now)], False), ([wk(0.35, 3.5, now)], False), ([], False)):
        plan_of(town, [{"id": "k1"}])
        _pass(town, start_at="night", start_at_by="board", passed_by="auto")
        r, launched = _runner(town, limits=lambda l=limits: l, night=_now_in(False))
        r.start("demo")
        plan = r.plan("demo")
        assert (launched == [("demo", "k1")]) is starts and bool(plan.get("by_pace")) is starts
        assert plan["tasks"][0]["state"] == ("running" if starts else "ready")


def test_a_second_board_low_plan_waits_while_the_first_runs_by_day(town):
    now = time.time()
    for slug in ("one", "two"):
        plan_of(town, [{"id": "k1"}], slug=slug)
        _pass(town, slug, start_at="night", start_at_by="board", passed_by="auto")
    r, launched = _runner(town, limits=lambda: [wk(0.9, 3.5, now)], night=_now_in(False), max_parallel=3)
    r._spawn = lambda slug, tid, cancel, again: (launched.append((slug, tid)),
                                                 r._runs.__setitem__((slug, tid), SimpleNamespace(role="", why="", cancel=threading.Event())))
    r.start("one")
    r.start("two")
    assert launched == [("one", "k1")] and r.plan("one")["by_pace"] and not r.plan("two").get("by_pace")
    assert r.plan("two")["tasks"][0]["state"] == "ready"                               # waits, unheld, for the night or the first


def test_at_night_with_the_week_behind_the_boards_low_plan_is_held_with_kind_week_until_the_reset(town):
    now = time.time()
    plan_of(town, [{"id": "k1"}])
    _pass(town, start_at="night", start_at_by="board", passed_by="auto")
    r, launched = _runner(town, limits=lambda: [wk(0.2, 3.5, now)], night=_now_in(True))
    r.start("demo")
    (task,) = r.plan("demo")["tasks"]
    assert launched == [] and task["state"] == "held" and task["note"].startswith("week · after ")
    assert r._until[("demo", "k1")] == pytest.approx(now + 3.5 * DAY)
    plan_of(town, [{"id": "k1"}])                                                      # the person's: starts as today
    _pass(town, start_at="night", start_at_by="person", passed_by="auto")
    r, launched = _runner(town, limits=lambda: [wk(0.2, 3.5, now)], night=_now_in(True))
    r.start("demo")
    assert launched == [("demo", "k1")]


# -- §4 events, payloads ------------------------------------------------------------------------------------------

def _read_rows(lim, rows):
    lim._read(rows)


def test_week_reset_is_written_once_when_the_weekly_reset_moves_later_to_the_project_shown(tmp_path):
    lim = BoardLimits(tmp_path, lambda fn, *a: fn(*a), fetch=lambda root: [])
    now = time.time()
    _read_rows(lim, [wk(0.3, 1, now)])
    _read_rows(lim, [wk(0.25, 1, now)])                                                # the same reset: nothing
    assert [e for e in event_log.read(tmp_path) if e["event"] == "week_reset"] == []
    _read_rows(lim, [wk(0.95, 7, now)])                                                # the week came back
    _read_rows(lim, [wk(0.9, 7, now)])
    (got,) = [e for e in event_log.read(tmp_path) if e["event"] == "week_reset"]
    assert got["left"] == 0.25 and got["provider"] == "claude"                          # the last share left before it
    _read_rows(lim, [Limit("claude", "", "weekly", None, None, "unreadable")])         # a failed read changes nothing
    _read_rows(lim, [wk(0.8, 7, now)])
    assert len([e for e in event_log.read(tmp_path) if e["event"] == "week_reset"]) == 1


def test_week_reset_is_not_written_with_no_project_open_or_in_the_demo(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    lim = BoardLimits(tmp_path, lambda fn, *a: fn(*a), fetch=lambda root: [])         # no project: the host points at home
    now = time.time()
    _read_rows(lim, [wk(0.3, 1, now)])
    _read_rows(lim, [wk(0.95, 7, now)])
    assert event_log.read(tmp_path) == []


# -- §4 the Map ---------------------------------------------------------------------------------------------------

def _map_of(host):
    return host.ideas.root(), host.ideas.state_dir


def test_the_map_says_who_put_work_off_what_the_week_holds_and_what_started_by_the_pace(host):
    root, state = _map_of(host)
    g = _goal_of(host)
    now = dt.datetime(2026, 10, 21, 3, 0).timestamp()
    behind = [wk(0.2, 3.5, now)]
    settings = {"night": "01:00-07:00", "autostart": True}
    mine = ideas.add_idea(root, "the person's", g, state, queue="night", night_by="person")
    board = ideas.add_idea(root, "the board's", g, state, queue="night", night_by="board")
    plan_board = ideas.add_idea(root, "plan of the board", g, state)
    plan_person = ideas.add_idea(root, "plan of the person", g, state)
    paced = ideas.add_idea(root, "started by day", g, state)
    for slug, by, st in ((plan_board, "board", "plan"), (plan_person, "person", "plan")):
        ideas.save_plan(state, slug, {"idea": slug, "passed_at": "x", "start_at": "night", "start_at_by": by, "tasks": [], "todos": []})
        ideas.save_state(state, slug, state=st)
    ideas.save_plan(state, paced, {"idea": paced, "passed_at": "x", "start_at": "night", "start_at_by": "board", "by_pace": True,
                                   "tasks": [{"id": "k1", "title": "T", "state": "running", "after": []}], "todos": []})
    ideas.save_state(state, paced, state="working")

    def nodes(limits, when=now, s=settings):
        return {n["slug"]: n for n in board_map.build(root, state, s, limits, when)["nodes"]}
    got = nodes(behind)
    reset = at(now + 3.5 * DAY).isoformat(timespec="seconds")
    assert got[mine]["night_by"] == "person" and got[mine]["waits"]["kind"] == "night"
    assert got[board]["night_by"] == "board" and got[board]["waits"] == {"kind": "week", "ref": "", "title": "", "until": reset}
    assert got[plan_board]["night_by"] == "board" and got[plan_board]["waits"]["kind"] == "week"
    assert got[plan_person]["night_by"] == "person" and got[plan_person]["waits"]["kind"] == "night"
    assert got[paced]["by_pace"] is True and got[paced]["waits"] is None and got[mine]["by_pace"] is False
    # not at night, not behind, no week read, autostart off: waits for the night, as today
    day = dt.datetime(2026, 10, 21, 12, 0).timestamp()
    assert nodes([wk(0.2, 3.5, day)], day)[board]["waits"]["kind"] == "night"
    assert nodes([wk(0.52, 3.5, now)])[board]["waits"]["kind"] == "night"
    assert nodes([])[board]["waits"]["kind"] == "night"
    assert nodes(behind, s={**settings, "autostart": False})[board]["waits"]["kind"] == "night"
    json.dumps(got)
    # a task held by the week at night
    ideas.edit_plan(state, plan_board, lambda p: p.update(tasks=[{"id": "k1", "title": "T", "state": "held", "after": [],
                                                                  "note": "week · after 09:00"}]))
    ideas.save_state(state, plan_board, state="working")
    assert nodes(behind)[plan_board]["waits"] == {"kind": "week", "ref": "", "title": "", "until": reset}
    assert nodes([])[plan_board]["waits"] == {"kind": "week", "ref": "", "title": "", "until": "09:00"}


def test_the_board_rows_carry_night_by_beside_queue_and_start_at(host):
    g = _goal_of(host)
    low = host.command("ideas.add", {"text": "low", "track": g, "priority": "low"})["slug"]
    rows = {i["slug"]: i for i in host.command("ideas.board")["ideas"]}
    assert rows[low]["queue"] == "night" and rows[low]["night_by"] == "board"
    state = host.ideas.state_dir
    ideas.save_plan(state, low, {"idea": low, "passed_at": "x", "start_at": "night", "start_at_by": "board", "tasks": [], "todos": []})
    ideas.save_state(state, low, state="plan")
    row = {i["slug"]: i for i in host.command("ideas.board")["ideas"]}[low]
    assert row["start_at"] == "night" and row["night_by"] == "board"


def test_an_agents_chip_says_when_its_task_started_by_the_pace(host):
    g = _goal_of(host)
    slug = host.command("ideas.add", {"text": "low", "track": g, "priority": "low"})["slug"]
    state = host.ideas.state_dir
    task = {"id": "k1", "title": "T", "state": "running", "after": [], "role": "grunt"}
    ideas.save_plan(state, slug, {"idea": slug, "passed_at": "x", "passed_by": "auto", "start_at": "night", "start_at_by": "board",
                                  "by_pace": True, "tasks": [task], "todos": []})
    ideas.save_state(state, slug, state="working")
    chips = [c for block in host.command("ideas.agents")["roles"] for c in block["chips"] if c.get("task") == "k1"]
    assert chips and all(c["pace"] is True for c in chips)
    ideas.edit_plan(state, slug, lambda p: p.pop("by_pace"))
    chips = [c for block in host.command("ideas.agents")["roles"] for c in block["chips"] if c.get("task") == "k1"]
    assert chips and all(c["pace"] is False for c in chips)
