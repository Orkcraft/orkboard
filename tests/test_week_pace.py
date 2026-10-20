"""Spec 44 A (docs/specs/44-week-pace.md §1–§4, Tests → A): the week's pace, the reserve per window, who put work off to the night, `pace_tick`,
the gate and the runner, the night when the week is behind, `week_reset`, the Map's waits and This week. Code, no model."""
from __future__ import annotations

import datetime as dt
import json
import threading
import time
from types import SimpleNamespace

import pytest

from orkboard.core.board_limits import BoardLimits
from orkboard.core.idea_runner import IdeaRunner
from orkboard.gui.board_host import Orkboard
from orkboard.realm import board_map, event_log, idea_target, ideas
from orkboard.sources.limits import Limit
from tests.test_idea_draft import DRAFT, PLAN, Model
from tests.test_idea_night import _events, _goal, keeper  # noqa: F401  (a fixture)
from tests.test_idea_runner import plan_of, tasks_of, town, wait_idle  # noqa: F401  (a fixture)

WEEK = 7 * 24 * 3600


def at(now: float, days: float = 0, hours: float = 0) -> dt.datetime:
    return dt.datetime.fromtimestamp(now + days * 86400 + hours * 3600)


def weekly(left: float, days: float, now: float | None = None) -> Limit:
    now = time.time() if now is None else now
    return Limit("claude", "", "weekly", left, at(now, days))


def session(left: float, hours: float, now: float | None = None) -> Limit:
    now = time.time() if now is None else now
    return Limit("claude", "", "session", left, at(now, hours=hours))


def night_around_now() -> str:
    """A night window the clock is inside, and one it is not (the Board reads the machine's time)."""
    n = dt.datetime.now()
    return f"{(n - dt.timedelta(hours=1)):%H:%M}-{(n + dt.timedelta(hours=1)):%H:%M}"


def day_around_now() -> str:
    n = dt.datetime.now()
    return f"{(n + dt.timedelta(hours=5)):%H:%M}-{(n + dt.timedelta(hours=6)):%H:%M}"


# -- §1: the week, its pace and the reserve per window ---------------------------------------------------------------

def test_the_week_is_its_share_left_the_share_to_come_and_its_reset_and_none_without_one():
    now = 1_800_000_000.0
    got = idea_target.week([weekly(0.55, 2, now)], now)
    assert got["left"] == 0.55 and got["rest"] == pytest.approx(2 / 7) and got["reset"] == pytest.approx(now + 2 * 86400)
    assert idea_target.week([weekly(0.5, 7.5, now)], now)["rest"] == 1.0                       # a week and more away: the whole week to come
    assert idea_target.week([weekly(0.5, -1, now)], now)["rest"] == 0.0                         # a reset passed: nothing to come
    assert idea_target.week([weekly(0.5, 3, now), weekly(0.2, 3, now)], now)["left"] == 0.2    # the tightest, when a tool has several
    assert idea_target.week([], now) is None and idea_target.week(None, now) is None
    assert idea_target.week([session(0.5, 2, now)], now) is None                                # not a weekly window
    assert idea_target.week([Limit("claude", "", "weekly", None, at(now, 2), "Not logged in")], now) is None          # an error
    assert idea_target.week([Limit("claude", "", "weekly", 0.5, None)], now) is None                                  # no reset read
    assert idea_target.week([Limit("codex", "", "weekly", 0.5, at(now, 2))], now) is None                             # another tool
    assert idea_target.week([Limit("codex", "", "weekly", 0.5, at(now, 2))], now, "codex")["left"] == 0.5
    assert idea_target.pace([], now) is None


@pytest.mark.parametrize("left,expected", [(0.2857 + 0.10 + 0.001, "ahead"), (2 / 7 + 0.10, "ahead"), (2 / 7 + 0.0999, "even"), (2 / 7, "even"),
                                           (2 / 7 - 0.0001, "behind"), (0.0, "behind"), (1.0, "ahead")])
def test_the_pace_is_ahead_from_ten_points_above_the_share_to_come_behind_below_it_else_even(left, expected):
    now = 1_800_000_000.0
    assert idea_target.pace([weekly(left, 2, now)], now) == expected


def _old_reserve(limits, settings, now, provider="claude"):
    """The rule before spec 44 (`reserve_held`): the smallest window against one share."""
    from orkboard.realm import status
    left = idea_target.left_of(limits, provider)
    if left is None:
        return None
    night = idea_target.in_night(str((settings or {}).get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now))
    share = idea_target.reserve(settings, night)
    if left > share:
        return None
    return status.reset_of(limits, provider, now, share) or now + status.UNKNOWN_RESET_S


def test_the_reserve_per_window_is_todays_rule_when_no_window_is_near_its_reset():
    now = time.time()
    for night in (night_around_now(), day_around_now()):
        settings = {"night": night, "reserve_day": 0.3, "reserve_night": 0.1}
        for s in (0.05, 0.1, 0.25, 0.3, 0.31, 0.9):
            for w in (0.05, 0.12, 0.3, 0.5, 0.9):
                for hours in (2, 5, 40):                                                    # no session reset within the hour
                    rows = [session(s, hours, now), weekly(w, 3, now)]
                    assert idea_target.reserve_held(rows, settings, now) == _old_reserve(rows, settings, now), (night, s, w, hours)
    assert idea_target.reserve_held([], {}, now) is None
    assert idea_target.reserve_held([Limit("claude", "", "session", None, None, "error")], {}, now) is None


def test_the_hour_before_the_five_hours_come_back_eases_their_reserve_by_day_while_the_week_is_not_behind():
    now = time.time()
    day = {"night": day_around_now(), "reserve_day": 0.3, "reserve_night": 0.1}
    ahead = [weekly(0.9, 2, now)]                                       # the week is ahead of its pace
    rows = lambda hours: [session(0.2, hours, now), *ahead]             # noqa: E731
    assert idea_target.reserve_held(rows(3), day, now) is not None                                     # 0.2 ≤ the day's 0.3: held
    assert idea_target.reserve_held(rows(0.9), day, now) is None                                      # within the hour: the night's 0.1 is the share
    assert idea_target.reserve_held(rows(1.1), day, now) is not None                                  # a little more than an hour away: not yet
    assert idea_target.reserve_held([session(0.08, 0.5, now), *ahead], day, now) is not None          # still under the night's share
    even = [weekly(0.4, 2, now)]                                                                       # even: eased too
    assert idea_target.reserve_held([session(0.2, 0.5, now), *even], day, now) is None
    behind = [weekly(0.5, 6, now)]                                                                     # behind (0.5 < 6/7), above the reserve itself
    assert idea_target.pace(behind, now) == "behind"
    assert idea_target.reserve_held([session(0.2, 0.5, now), *behind], day, now) == pytest.approx(now + 0.5 * 3600, abs=1)       # not eased
    assert idea_target.reserve_held([session(0.2, 0.5, now)], day, now) is not None                    # no week read: today's rule
    night = {**day, "night": night_around_now()}
    assert idea_target.reserve_held([session(0.2, 0.5, now), *ahead], night, now) is None              # at night the share is the night's anyway
    assert idea_target.reserve_held([session(0.2, 3, now), weekly(0.9, 2, now)], {**night, "reserve_night": 0.25}, now) is not None


# -- §2: who put it off -----------------------------------------------------------------------------------------------

@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def _add(host, text, **more):
    root = host.ideas.root()
    goal = next((t["slug"] for t in ideas.tracks(root, make=False) if t["slug"] != "general"), None) or ideas.add_track(root, "First goal")
    return host.command("ideas.add", {"text": text, "track": goal, **more})["slug"]


def test_a_low_idea_is_put_off_by_the_board_the_persons_own_night_and_tonight_by_them_and_before_reads_person(host):
    state = host.ideas.state_dir
    low = _add(host, "a low idea", priority="low")
    mine = _add(host, "my night idea", priority="high", night=True)
    both = _add(host, "low, and mine too", priority="low", night=True)
    now = _add(host, "an idea for now", priority="high")
    assert [ideas.state(state, s)["night_by"] for s in (low, mine, both, now)] == ["board", "person", "person", ""]
    assert [ideas.night_by_of(ideas.state(state, s)) for s in (low, mine, both)] == ["board", "person", "person"]
    ideas.save_state(state, now, state="raw", queue="")
    host.command("ideas.queue", {"slug": low, "queue": "night"})                                   # Tonight, on the Board's own: now the person's
    assert ideas.state(state, low)["night_by"] == "person"
    old = ideas.add_idea(host.ideas.root(), "an idea from before", "first-goal", state, queue="night")
    (state / "ideas" / old / "state.json").write_text(json.dumps({"state": "raw", "queue": "night"}))
    assert ideas.state(state, old)["night_by"] == "" and ideas.night_by_of(ideas.state(state, old)) == "person"       # nothing before was moved


def _plan(host, slug, state="plan"):
    ideas.save_plan(host.ideas.state_dir, slug, {"idea": slug, "made_at": "2026-10-20T09:00:00", "passed_at": None, "todos": [],
                                                 "tasks": [{"id": "k1", "title": "Do it", "brief": "b", "tier": "warrior", "after": [], "state": "ready"}]})
    ideas.save_state(host.ideas.state_dir, slug, state=state)


def test_a_plan_put_off_to_the_night_says_who_did_it_and_a_plan_of_before_reads_person(host):
    a, b, c = (_add(host, f"idea {n}", priority="low") for n in range(3))
    for s in (a, b, c):
        _plan(host, s)
    host.ideas.pass_plan(a, "auto", night=True)                                                     # autostart's Low
    host.ideas.pass_plan(b, "person", night=True)                                                   # the person's Start tonight
    assert ideas.plan(host.ideas.state_dir, a)["start_at_by"] == "board" and ideas.plan(host.ideas.state_dir, b)["start_at_by"] == "person"
    host.ideas.pass_plan(c, "person", night=False)
    assert "start_at_by" not in ideas.plan(host.ideas.state_dir, c)
    assert ideas.night_by_of({}) == "person"
    plan = {"start_at": "night", "passed_at": "x"}                                                   # a plan of before
    assert not idea_target.board_low(plan, {}) and idea_target.board_low({**plan, "start_at_by": "board"}, {}) and \
        not idea_target.board_low({**plan, "start_at_by": "board"}, {"autostart": False})
    logs = [r for r in event_log.read(host.repo_root) if r["event"] == "plan_passed"]
    assert all("pace" not in r for r in logs)                                                         # the pass says nothing of the pace: the tasks that run do (by_pace)


# -- §3: pace_tick ----------------------------------------------------------------------------------------------------

def _ready(keeper, *texts, by="board", priority="low"):
    g = _goal(keeper, "Table")
    slugs = [ideas.add_idea(keeper.root, t, g, keeper.state, priority=priority, queue="night", night_by=by) for t in texts]
    return g, slugs


def _pace(keeper):
    keeper._pace_at = float("-inf")
    got = keeper.pace_tick(time.time())
    for _ in range(300):
        if not keeper._pace_busy:
            break
        time.sleep(0.01)
    return got


def _drafting(keeper):
    keeper.call = model = Model(draft=lambda p: {**DRAFT, "questions": []}, plan=PLAN)
    return model


def test_by_day_with_the_week_ahead_the_oldest_boards_low_idea_is_drafted_one_a_time(keeper):
    _g, (first, second) = _ready(keeper, "first low idea", "second low idea")
    keeper.settings_now["night"] = day_around_now()
    keeper.limits_now = [weekly(0.9, 2)]
    model = _drafting(keeper)
    assert _pace(keeper) is True
    assert ideas.state(keeper.state, first)["state"] != "raw" and ideas.state(keeper.state, second)["state"] == "raw"
    assert [a["step"] for a in model.asked if a["step"] == "draft"] == ["draft"] and "first low idea" in model.asked[0]["prompt"]
    assert _pace(keeper) is True                                                                   # the next tick, the next idea
    assert ideas.state(keeper.state, second)["state"] != "raw"
    goal = ideas.tracks(keeper.root, make=False)[0]["slug"]
    running = ideas.add_idea(keeper.root, "a low idea being drafted", goal, keeper.state, priority="low", queue="night", night_by="board")
    waiting = ideas.add_idea(keeper.root, "a low idea that waits", goal, keeper.state, priority="low", queue="night", night_by="board")
    keeper._claim(running, "drafting")                                                             # a draft of the Board's Low is running here: no other
    keeper.run_pace()
    assert ideas.state(keeper.state, waiting)["state"] == "raw"
    keeper._busy.pop(running)
    keeper.run_pace()
    assert ideas.state(keeper.state, running)["state"] != "raw"                                    # the oldest, once nothing runs


def test_pace_tick_waits_every_ten_minutes_not_in_the_night_and_not_when_the_week_is_not_ahead(keeper):
    _ready(keeper, "a low idea")
    model = _drafting(keeper)
    keeper.limits_now = [weekly(0.9, 2)]
    keeper.settings_now["night"] = night_around_now()                                               # the night window: the night's own
    assert _pace(keeper) is False and model.asked == []
    keeper.settings_now["night"] = day_around_now()
    keeper.limits_now = [weekly(0.3, 2)]                                                            # even
    assert _pace(keeper) is False
    keeper.limits_now = [weekly(0.1, 2)]                                                            # behind
    assert _pace(keeper) is False
    keeper.limits_now = []                                                                          # no week read
    assert _pace(keeper) is False and model.asked == []
    keeper.limits_now = [weekly(0.9, 2)]
    keeper._pace_at = float("-inf")
    assert keeper.pace_tick(time.time()) is True                                                    # ahead
    for _ in range(300):
        if not keeper._pace_busy:
            break
        time.sleep(0.01)
    asked = len(model.asked)
    assert keeper.pace_tick(time.time() + 30) is False and len(model.asked) == asked               # asked again within PACE_S: not read again


def test_pace_tick_does_nothing_while_the_reserve_holds_with_autostart_off_or_for_the_persons_own(keeper):
    _g, (mine,) = _ready(keeper, "the person's own", by="person")
    keeper.settings_now["night"] = day_around_now()
    model = _drafting(keeper)
    keeper.limits_now = [weekly(0.9, 2)]
    assert _pace(keeper) is True and model.asked == [] and ideas.state(keeper.state, mine)["state"] == "raw"      # Tonight is not the Board's to move
    ideas.add_idea(keeper.root, "the board's own", ideas.tracks(keeper.root, make=False)[0]["slug"], keeper.state, priority="low", queue="night", night_by="board")
    keeper.limits_now = [weekly(0.9, 2), session(0.2, 3)]                                           # the day's reserve holds
    assert _pace(keeper) is False and model.asked == []
    keeper.limits_now = [weekly(0.9, 2)]
    keeper.settings_now["autostart"] = False
    assert _pace(keeper) is False and model.asked == []
    keeper.settings_now["autostart"] = True
    assert _pace(keeper) is True and [a["step"] for a in model.asked][0] == "draft"


def test_pace_tick_starts_the_boards_low_plan_waiting_for_the_night_and_not_the_persons(keeper):
    g, (a, b) = _ready(keeper, "board plan", "person plan")
    for s, by in ((a, "board"), (b, "person")):
        ideas.save_plan(keeper.state, s, {"idea": s, "made_at": "x", "passed_at": "x", "start_at": "night", "start_at_by": by, "tasks": [], "todos": []})
        ideas.save_state(keeper.state, s, state="plan", queue="")
    keeper.settings_now["night"] = day_around_now()
    keeper.limits_now = [weekly(0.9, 2)]
    _drafting(keeper)
    assert _pace(keeper) is True
    assert keeper.started == [a]


# -- §3: the night when the week is behind ------------------------------------------------------------------------------

def test_the_night_leaves_the_boards_low_ideas_when_the_week_is_behind_and_drafts_the_persons_own(keeper):
    g, (boards, mine) = _ready(keeper, "the board's low", "the person's own", by="board")
    ideas.save_state(keeper.state, mine, night_by="person")
    keeper.limits_now = [weekly(0.35, 6)]                                                          # behind, above the reserve
    model = _drafting(keeper)
    keeper.call = model = Model(draft=lambda p: {**DRAFT, "questions": []}, plan=PLAN, propose={"proposals": []})
    counts = keeper.run_night("2026-10-20T01:00")
    assert counts["drafted"] == 1 and ideas.state(keeper.state, boards)["state"] == "raw" and ideas.state(keeper.state, mine)["state"] != "raw"
    assert "paced" not in counts
    (run,) = _events(keeper, "night_run")
    assert run["paced"] == 1 and run["drafted"] == 1
    keeper.limits_now = [weekly(0.9, 2)]                                                           # ahead: the night drafts it, as today
    keeper.call = Model(draft=lambda p: {**DRAFT, "questions": []}, plan=PLAN, propose={"proposals": []})
    keeper.run_night("2026-10-21T01:00")
    assert ideas.state(keeper.state, boards)["state"] != "raw" and _events(keeper, "night_run")[-1]["paced"] == 0
    keeper.settings_now["autostart"] = False                                                       # autostart off: nothing is moved
    again = ideas.add_idea(keeper.root, "another low", g, keeper.state, priority="low", queue="night", night_by="board")
    keeper.limits_now = [weekly(0.35, 6)]
    keeper.call = Model(draft=lambda p: {**DRAFT, "questions": []}, plan=PLAN, propose={"proposals": []})
    keeper.run_night("2026-10-22T01:00")
    assert ideas.state(keeper.state, again)["state"] != "raw"


# -- §3: the gate and the runner ------------------------------------------------------------------------------------------

def test_the_gate_lets_the_boards_low_plan_start_by_day_only_ahead_and_holds_it_at_night_when_behind():
    now = time.time()
    day, night = {"night": day_around_now(), "autostart": True}, {"night": night_around_now(), "autostart": True}
    low = {"start_at": "night", "start_at_by": "board", "passed_by": "auto"}
    person = {"start_at": "night", "start_at_by": "person", "passed_by": "person"}
    ahead, even, behind = [weekly(0.9, 2, now)], [weekly(0.3, 2, now)], [weekly(0.35, 6, now)]
    assert idea_target.gate(low, ahead, day, now) is None and idea_target.by_pace(low, ahead, day, now) is True
    assert idea_target.gate(low, even, day, now) == "night" and idea_target.gate(low, behind, day, now) == "night" and idea_target.gate(low, [], day, now) == "night"
    assert idea_target.gate(person, ahead, day, now) == "night" and not idea_target.by_pace(person, ahead, day, now)
    assert idea_target.gate(low, ahead, {**day, "autostart": False}, now) == "night"
    assert idea_target.gate(low, ahead, night, now) is None and idea_target.gate(low, even, night, now) is None and idea_target.gate(low, [], night, now) is None
    held = idea_target.gate(low, behind, night, now)
    assert isinstance(held, idea_target.WeekHold) and held == pytest.approx(now + 6 * 86400)          # the week's reset
    assert idea_target.gate(person, behind, night, now) is None                                       # the person's night stays theirs
    assert idea_target.gate({**low, "start_at_by": "person"}, behind, night, now) is None
    assert idea_target.gate({"passed_by": "auto"}, behind, day, now) is None                          # High and Normal: as today
    assert idea_target.gate(low, ahead + [session(0.2, 3, now)], day, now) == pytest.approx(now + 3 * 3600, abs=1)          # the reserve, as for any autostart


def _board_low(town, slug="demo", tasks=None, by="board"):
    plan_of(town, tasks or [{"id": "k1"}], slug=slug)
    p = json.loads((town.state / "ideas" / slug / "plan.json").read_text())
    p.update(passed_by="auto" if by == "board" else "person", start_at="night", start_at_by=by)
    (town.state / "ideas" / slug / "plan.json").write_text(json.dumps(p))


def _runner(town, limits, night, max_parallel=1):
    settings = SimpleNamespace(ideas={"max_parallel": max_parallel, "merge_into": "main", "push": True, "review": False, "night": night, "autostart": True})
    return IdeaRunner(town.repo, town.state, settings, SimpleNamespace(publish=lambda *a, **k: None), limits=lambda: limits)


def test_by_day_with_the_week_ahead_the_boards_low_plan_starts_and_says_it_went_by_the_pace(town):
    _board_low(town)
    runner = _runner(town, [weekly(0.9, 2)], day_around_now())
    runner.start("demo")
    assert wait_idle(runner)["state"] == "done"
    assert json.loads((town.state / "ideas" / "demo" / "plan.json").read_text())["by_pace"] is True and tasks_of(town)["k1"]["state"] == "merged"


def test_by_day_when_the_week_is_not_ahead_it_waits_for_the_night_unheld_and_the_persons_own_always_does(town):
    for limits in ([weekly(0.3, 2)], [weekly(0.1, 2)], []):
        _board_low(town)
        runner = _runner(town, limits, day_around_now())
        runner.start("demo")
        time.sleep(0.6)
        runner.tick()
        assert tasks_of(town)["k1"]["state"] == "ready" and not runner.busy()
        assert "by_pace" not in json.loads((town.state / "ideas" / "demo" / "plan.json").read_text())
        runner.stop("demo")
    _board_low(town, by="person")
    runner = _runner(town, [weekly(0.9, 2)], day_around_now())
    runner.start("demo")
    time.sleep(0.6)
    runner.tick()
    assert tasks_of(town)["k1"]["state"] == "ready"                                                 # by day, whatever the week: the person's night is theirs


def test_only_one_boards_low_plan_runs_by_day_in_a_project_a_second_waits(town, monkeypatch):
    monkeypatch.setenv("STUB_SLEEP", "1.5")
    _board_low(town, "demo")
    _board_low(town, "second", [{"id": "k2"}])                                                       # (another file than the first's)
    (town.state / "ideas" / "second" / "state.json").write_text(json.dumps({"state": "plan"}))
    runner = _runner(town, [weekly(0.9, 2)], day_around_now(), max_parallel=2)
    runner.start("demo")
    runner.start("second")
    time.sleep(0.5)
    runner.tick()
    states = {s: next(iter(tasks_of(town, s).values()))["state"] for s in ("demo", "second")}
    assert sorted(states.values()) in (["ready", "running"], ["ready", "testing"]), states               # one runs by day, the other waits
    end = time.time() + 60
    while time.time() < end and not (json.loads((town.state / "ideas" / "second" / "state.json").read_text())["state"] == "done"
                                     and json.loads((town.state / "ideas" / "demo" / "state.json").read_text())["state"] == "done"):
        runner.tick()
        time.sleep(0.2)
    assert tasks_of(town, "demo")["k1"]["state"] == "merged" and tasks_of(town, "second")["k2"]["state"] == "merged"      # the second went on after the first


def test_at_night_with_the_week_behind_the_boards_low_plan_is_held_until_the_reset_and_let_go_when_it_is_not_behind(town):
    _board_low(town)
    limits = [weekly(0.1, 2)]
    runner = _runner(town, limits, night_around_now())
    runner.start("demo")
    time.sleep(0.6)
    runner.tick()
    task = tasks_of(town)["k1"]
    assert task["state"] == "held" and task["note"].startswith("week · after ") and not runner.busy()
    assert runner._until[("demo", "k1")] == pytest.approx(time.time() + 2 * 86400, abs=60)
    limits[:] = [weekly(0.9, 2)]                                                                    # the week is not behind any more
    assert wait_idle(runner)["state"] == "done" and tasks_of(town)["k1"]["state"] == "merged"


# -- §4: week_reset, the Map, This week ---------------------------------------------------------------------------------------

def test_week_reset_is_written_once_when_the_weekly_reset_moves_later_to_the_project_shown(tmp_path):
    shown = tmp_path / "shop"
    shown.mkdir()
    now = time.time()
    limits = BoardLimits(shown, lambda fn, *a: fn(*a), fetch=lambda p: [])
    log = lambda: [r for r in event_log.read(shown) if r["event"] == "week_reset"]           # noqa: E731
    limits._read([weekly(0.42, 1, now)])                                                       # the first read: nothing before it
    limits._read([weekly(0.40, 1, now + 120)])                                                  # a few minutes of jitter in the reset: not a new week
    assert log() == []
    limits._read([weekly(0.18, 1, now + 600)])
    limits._read([weekly(0.95, 8, now + 700)])                                                  # a week later: it came back
    assert [(r["left"], r["provider"]) for r in log()] == [(0.18, "claude")]                   # the last share left read before it
    limits._read([weekly(0.9, 8, now + 800)])
    limits._read([session(0.5, 2, now)])                                                        # no week read: nothing
    assert len(log()) == 1
    home = BoardLimits(__import__("pathlib").Path.home(), lambda fn, *a: fn(*a), fetch=lambda p: [])
    home._read([weekly(0.4, 1, now)])
    home._read([weekly(0.9, 8, now)])                                                           # no project open: not written
    assert not event_log.path(__import__("pathlib").Path.home()).exists() or not [r for r in event_log.read(__import__("pathlib").Path.home()) if r["event"] == "week_reset"]


def test_the_map_says_week_for_the_boards_low_work_held_at_night_and_night_by_and_by_pace(host):
    state = host.ideas.state_dir
    low = _add(host, "a low idea", priority="low")
    mine = _add(host, "my own night idea", priority="high", night=True)
    plan_idea = _add(host, "a low plan", priority="low")
    _plan(host, plan_idea)
    host.ideas.pass_plan(plan_idea, "auto", night=True)
    by_day = _add(host, "went by day", priority="low")
    _plan(host, by_day, "working")
    ideas.edit_plan(state, by_day, lambda p: p.update(by_pace=True, passed_at="x", tasks=[{**p["tasks"][0], "state": "running"}]))
    ideas.save_state(state, by_day, state="working")

    def nodes(**settings):
        host.ideas.save_settings({**host.ideas.settings_now(), **settings})
        return {n["slug"]: n for n in host.command("ideas.map")["nodes"]}

    host.limits.rows = [weekly(0.1, 2)]                                                             # behind
    got = nodes(night=night_around_now())
    reset = at(time.time(), 2).strftime("%Y-%m-%dT%H:%M")
    assert got[low]["waits"]["kind"] == "week" and got[low]["waits"]["until"] == reset and got[plan_idea]["waits"]["kind"] == "week"
    assert got[mine]["waits"]["kind"] == "night" and got[low]["night_by"] == "board" and got[mine]["night_by"] == "person" and got[plan_idea]["night_by"] == "board"
    assert got[by_day]["by_pace"] is True and got[low]["by_pace"] is False and got[by_day]["night_by"] == ""
    assert nodes(night=day_around_now())[low]["waits"]["kind"] == "night"                          # by day it waits for the night, as it did
    host.limits.rows = [weekly(0.9, 2)]
    assert nodes(night=night_around_now())[low]["waits"]["kind"] == "night"                        # not behind: only the night
    host.limits.rows = [weekly(0.1, 2)]
    assert nodes(night=night_around_now(), autostart=False)[low]["waits"]["kind"] == "night"      # autostart off: nothing is moved


def test_this_week_carries_the_week_and_what_the_last_one_left_unused(host):
    now = time.time()
    assert host.command("ideas.week_work")["week"] is None and host.command("ideas.week_work")["last_unused"] is None
    host.limits.rows = [weekly(0.55, 2, now)]
    got = host.command("ideas.week_work")
    assert got["week"]["left"] == 0.55 and got["week"]["pace"] == "ahead" and got["week"]["rest"] == pytest.approx(2 / 7, abs=0.01)
    assert got["week"]["reset"] == pytest.approx(now + 2 * 86400, abs=5)
    event_log.record(host.repo_root, event_log.WEEK_RESET, left=0.5, provider="claude")
    event_log.record(host.repo_root, event_log.WEEK_RESET, left=0.3, provider="claude")
    assert host.command("ideas.week_work")["last_unused"] == 0.3                                    # the newest
    json.dumps(got)


def test_a_chip_of_a_task_of_a_plan_that_went_by_day_says_pace(host):
    state = host.ideas.state_dir
    s = _add(host, "went by day", priority="low")
    _plan(host, s, "working")
    ideas.edit_plan(state, s, lambda p: p.update(by_pace=True, passed_at="x", tasks=[{**p["tasks"][0], "state": "running"}]))
    other = _add(host, "went at once", priority="high")
    _plan(host, other, "working")
    ideas.edit_plan(state, other, lambda p: p.update(passed_at="x", tasks=[{**p["tasks"][0], "state": "running"}]))
    chips = [c for b in host.command("ideas.agents")["roles"] for c in b["chips"] if c.get("task")]
    assert {c["idea"]: c.get("pace") for c in chips} == {s: True, other: None}


# -- fixes after review ---------------------------------------------------------------------------------------------------

def test_a_board_low_draft_that_failed_is_not_retried_by_the_pace_and_the_next_idea_is_drafted(keeper):
    _g, (broken, next_one) = _ready(keeper, "first low idea", "second low idea")
    ideas.save_state(keeper.state, broken, state="raw", error="The tool failed")
    keeper.settings_now["night"] = day_around_now()
    keeper.limits_now = [weekly(0.9, 2)]
    model = _drafting(keeper)
    assert _pace(keeper) is True
    assert ideas.state(keeper.state, broken)["state"] == "raw" and ideas.state(keeper.state, next_one)["state"] != "raw"
    drafts = [a["prompt"] for a in model.asked if a["step"] == "draft"]
    assert len(drafts) == 1 and "second low idea" in drafts[0]


def _passed_low(keeper, slug, **plan):
    ideas.save_plan(keeper.state, slug, {"idea": slug, "made_at": "x", "passed_at": "x", "start_at": "night", "start_at_by": "board",
                                         "tasks": [{"id": "k1", "state": "ready"}], "todos": [], **plan})
    ideas.save_state(keeper.state, slug, state="plan", queue="")


def test_the_pace_starts_one_boards_low_plan_a_second_waits_until_the_first_has_ended_and_the_started_one_is_not_waiting_for_the_night(keeper):
    _g, (a, b) = _ready(keeper, "first plan", "second plan")
    for s in (a, b):
        _passed_low(keeper, s)
    keeper.settings_now["night"] = day_around_now()
    keeper.limits_now = [weekly(0.9, 2)]
    _drafting(keeper)
    keeper.run_pace()
    assert keeper.started == [a]
    got = ideas.plan(keeper.state, a)
    assert got["by_pace"] is True and got["start_at"] is None                                       # running by day: not waiting for the night
    ideas.save_state(keeper.state, a, state="working")
    keeper.run_pace()
    assert keeper.started == [a]                                                                      # the first is not finished: the second is not started
    ideas.edit_plan(keeper.state, a, lambda p: p.update(tasks=[{"id": "k1", "state": "merged"}]))
    keeper.run_pace()
    assert keeper.started == [a, b]


def test_a_low_plan_the_pace_runs_by_day_is_no_longer_waiting_for_the_night_on_the_map(town):
    _board_low(town)
    runner = _runner(town, [weekly(0.9, 2)], day_around_now())
    runner.start("demo")
    wait_idle(runner)
    plan = json.loads((town.state / "ideas" / "demo" / "plan.json").read_text())
    assert plan["by_pace"] is True and plan["start_at"] is None


def test_the_tasks_of_a_plan_the_pace_started_say_so_and_the_plan_passed_does_not(town):
    _board_low(town)
    runner = _runner(town, [weekly(0.9, 2)], day_around_now())
    runner.events = True
    runner.start("demo")
    wait_idle(runner)
    running = [r for r in event_log.read(town.repo) if r["event"] == "task_state" and r["state"] == "running"]
    assert running and all(r.get("by_pace") is True for r in running)
    _board_low(town, "second", [{"id": "k2"}], by="person")
    other = _runner(town, [weekly(0.9, 2)], night_around_now())
    other.events = True
    other.start("second")
    wait_idle(other)
    mine = [r for r in event_log.read(town.repo) if r["event"] == "task_state" and r["state"] == "running" and r["idea"] == "second"]
    assert mine and all("by_pace" not in r for r in mine)


def test_a_low_idea_or_plan_raised_to_high_is_no_longer_the_boards_to_hold(keeper, town):
    now = time.time()
    day, night = {"night": day_around_now(), "autostart": True}, {"night": night_around_now(), "autostart": True}
    low = {"start_at": "night", "start_at_by": "board", "passed_by": "auto"}
    assert idea_target.gate(low, [weekly(0.9, 2, now)], day, now, low=False) == "night" and not idea_target.by_pace(low, [weekly(0.9, 2, now)], day, now, low=False)
    assert idea_target.gate(low, [weekly(0.35, 6, now)], night, now, low=False) is None             # not held by the week at night
    assert not idea_target.board_low(low, {}, low=False)
    # the night's queue: raised, it is drafted though the week is behind; the pace leaves it alone
    _g, (raised, still) = _ready(keeper, "raised", "still low")
    ideas.set_meta(keeper.root, raised, priority="high")
    keeper.limits_now = [weekly(0.35, 6)]
    keeper.call = Model(draft=lambda p: {**DRAFT, "questions": []}, plan=PLAN, propose={"proposals": []})
    keeper.run_night("2026-10-20T01:00")
    assert ideas.state(keeper.state, raised)["state"] != "raw" and ideas.state(keeper.state, still)["state"] == "raw"
    assert _events(keeper, "night_run")[-1]["paced"] == 1
    # the pace: a raised plan is not started by it
    _g2, (plan_raised,) = _ready(keeper, "plan raised")
    ideas.set_meta(keeper.root, plan_raised, priority="normal")
    _passed_low(keeper, plan_raised)
    keeper.settings_now["night"] = day_around_now()
    keeper.limits_now = [weekly(0.9, 2)]
    keeper.run_pace()
    assert plan_raised not in keeper.started
    # the runner: the raised plan waits for the night by day as the person's does
    _board_low(town)
    runner = IdeaRunner(town.repo, town.state, SimpleNamespace(ideas={"max_parallel": 1, "merge_into": "main", "push": True, "review": False,
                                                                       "night": day_around_now(), "autostart": True}),
                        SimpleNamespace(publish=lambda *a, **k: None), limits=lambda: [weekly(0.9, 2)], rank=lambda s: (0, 0, 0))
    runner.start("demo")
    time.sleep(0.6)
    runner.tick()
    assert tasks_of(town)["k1"]["state"] == "ready" and not runner.busy()


def test_the_map_calls_a_raised_idea_the_persons_not_the_boards(host):
    low = _add(host, "stays low", priority="low")
    raised = _add(host, "raised later", priority="low")
    ideas.set_meta(host.ideas.root(), raised, priority="high")
    plan_idea = _add(host, "a plan, raised", priority="low")
    _plan(host, plan_idea)
    host.ideas.pass_plan(plan_idea, "auto", night=True)
    ideas.set_meta(host.ideas.root(), plan_idea, priority="normal")
    got = {n["slug"]: n for n in host.command("ideas.map")["nodes"]}
    assert (got[low]["night_by"], got[raised]["night_by"], got[plan_idea]["night_by"]) == ("board", "person", "person")


def test_a_night_proposal_taken_as_low_is_queued_for_the_night_by_the_board(host):
    root = host.ideas.root()
    goal = next((t["slug"] for t in ideas.tracks(root, make=False) if t["slug"] != "general"), None) or ideas.add_track(root, "First goal")
    s = ideas.add_idea(root, "a proposal", goal, host.ideas.state_dir)                                  # (no draft thread to race the state)
    ideas.save_state(host.ideas.state_dir, s, state="proposed", queue="")
    host.command("ideas.proposal", {"slug": s, "take": True, "priority": "low"})
    st = ideas.state(host.ideas.state_dir, s)
    assert st["queue"] == "night" and st["night_by"] == "board"


def test_a_night_that_left_the_boards_low_ideas_for_the_week_is_tried_again_when_the_week_comes_back(keeper):
    _ready(keeper, "the board's low")
    keeper.limits_now = [weekly(0.35, 6)]                                                          # behind
    keeper.call = Model(draft=lambda p: {**DRAFT, "questions": []}, plan=PLAN, propose={"proposals": []})
    keeper.run_night("2026-10-20T01:00")
    assert keeper.night_state()["held"] is True                                                    # night_tick tries again after RETRY_S


def test_a_week_hold_without_a_week_read_says_no_time():
    node = {"needs_you": False, "held_until": "", "queue": "", "start_at": "night", "night_by": "board"}
    held = [{"state": "held", "note": "week · after 09:00"}]
    assert board_map._waits(node, held, {}, [], None) == {"kind": "week", "ref": "", "title": "", "until": ""}
    got = board_map._waits(node, held, {}, [], {"until": "2026-10-22T09:00", "held": True})
    assert got["until"] == "2026-10-22T09:00"
