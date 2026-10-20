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
                      {"slug": "z", "state": "working", "queue": "", "start_at": ""}, {"slug": "d", "state": "done", "queue": "night", "start_at": ""},
                      {"slug": "p", "state": "plan", "queue": "night", "start_at": ""},          # drafted: its queue is still `night`
                      {"slug": "w", "state": "working", "queue": "", "start_at": "night"}]}     # started: its plan still says `night`
    got = board_week.this_week(root, state, SETTINGS, NOW, rows, ops_base=ops)
    assert got["usd"] == 40.0 and got["ops_usd"] == 3.2 and (got["merged"], got["first_time"]) == (4, 3)
    assert got["usd_per_merged"] == 10.0 and got["tonight"] == 2 and got["night_on"] is True and got["into"] == "dev"
    assert sum(got["nights"].values()) == 7 and set(got["nights"]) == {"worked", "idle", "off"}
    assert set(got) == {"usd", "ops_usd", "merged", "first_time", "usd_per_merged", "nights", "tonight", "night_on", "into", "streak", "week", "last_unused"}


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


# -- last week (spec 42 §7) ---------------------------------------------------------------------------------------

def _rows():
    return {"ideas": [{"slug": s, "short": s.title(), "title": f"The {s}", "track": g, "state": "done"}
                      for s, g in (("export", "offline"), ("table", "offline"), ("queue", "offline"), ("bill", "billing"), ("loose", "general"))],
            "tracks": [{"slug": g, "short": g.title(), "title": f"{g.title()} goal"} for g in ("offline", "billing", "general")]}


def test_last_week_defaults_to_the_last_full_week_and_counts_results_and_the_week_before(root, tmp_path):
    state = tmp_path / "state"
    for n, (day, rnd) in enumerate(((13, 1), (14, 1), (15, 2), (16, 1))):                            # 4 results last week, 3 the first time
        log(root, "task_state", at(day, 10), idea="export", task=f"k{n}", state="merged", was="review", round=rnd)
    log(root, "task_state", at(20, 9), idea="export", task="now", state="merged", was="review", round=1)      # this week: not counted
    for n, rnd in enumerate((1, 1, 2)):                                                                # the week before: 3 results, 2 first time
        log(root, "task_state", at(7, 10 + n), idea="export", task=f"p{n}", state="merged", was="review", round=rnd)
    _ledger(state, "export", at(14, 11), 8.0)
    _ledger(state, "export", at(5, 11), 9.0)
    got = board_week.last_week(root, state, SETTINGS, NOW, _rows())
    assert (got["week"], got["from"], got["to"]) == ("2026-W42", "2026-10-12", "2026-10-18")
    assert (got["merged"], got["first_time"], got["usd"], got["usd_per_merged"]) == (4, 3, 8.0, 2.0)
    assert got["before"] == {"merged": 3, "first_time": 2, "usd_per_merged": 3.0} and got["into"] == "dev" and got["streak"] == 0
    other = board_week.last_week(root, state, SETTINGS, NOW, _rows(), week="2026-W41")
    assert (other["from"], other["merged"], other["before"], other["usd_per_merged"]) == ("2026-10-05", 3, None, 3.0)


def test_last_week_goals_flags_dearest_fastest_answers_and_nights(root, tmp_path):
    state = tmp_path / "state"
    for slug, day in (("export", 13), ("table", 14), ("queue", 15), ("bill", 16), ("loose", 16)):
        log(root, "keeper_state", at(day, 12), idea=slug, state="done", was="working")
    log(root, "keeper_state", at(8, 12), idea="bill", state="done", was="working")                   # the week before: not counted
    log(root, "goal_accepted", at(16, 9), goal="billing", met=False, by="Growth")
    log(root, "goal_accepted", at(17, 9), goal="billing", met=True, by="Growth")
    log(root, "goal_accepted", at(17, 9), goal="gone", met=True, by="Growth")
    _ledger(state, "table", at(14, 9), 12.0)
    _ledger(state, "export", at(14, 9), 3.0)
    _ledger(state, "bill", at(14, 9), 0.004)
    log(root, "idea_added", at(14, 8), idea="export", track="offline")
    log(root, "idea_added", at(14, 9, 18), idea="table", track="offline")
    log(root, "task_state", at(14, 10), idea="export", task="k1", state="merged", was="review", round=1)         # 2 h after it was added
    log(root, "task_state", at(14, 10), idea="table", task="k1", state="merged", was="review", round=1)          # 42 min
    log(root, "task_state", at(15, 10), idea="table", task="k2", state="merged", was="review", round=1)
    log(root, "idea_answered", at(14, 12), idea="export", answers=5, picked=5, recommended=4, typed=0, decided=True)
    log(root, "goal_answered", at(15, 12), goal="offline", answers=7, picked=7, recommended=5, typed=0, decided=False)
    run(root, at(15, 2), drafted=1)
    got = board_week.last_week(root, state, SETTINGS, NOW, _rows())
    assert got["goals"] == [{"goal": "offline", "short": "Offline", "title": "Offline goal", "done": 3},
                            {"goal": "billing", "short": "Billing", "title": "Billing goal", "done": 1}]       # General's idea is not a goal's
    assert got["flags"] == [{"goal": "billing", "short": "Billing", "title": "Billing goal", "met": True, "by": "Growth"}]
    assert got["dearest"] == {"slug": "table", "short": "Table", "title": "The table", "usd": 12.0}               # under a cent is no cost
    assert got["fastest"] == {"slug": "table", "short": "Table", "title": "The table", "minutes": 42}
    assert got["answers"] == {"answers": 12, "recommended": 9, "decided": 1}
    assert got["nights"] == {"worked": 1, "idle": 0, "off": 6} and got["empty"] is False


def test_a_week_that_has_not_ended_counts_only_its_own_nights_that_have(root, tmp_path):
    run(root, at(18, 2), drafted=1)                                                  # the night of Sunday 18th: last week's
    run(root, at(20, 2), drafted=1)                                                  # Tuesday's night, ended at 07:00
    got = board_week.last_week(root, tmp_path / "state", SETTINGS, NOW, _rows(), week="2026-W43")
    assert got["nights"] == {"worked": 1, "idle": 0, "off": 1}                       # Monday's night is off; none from before its Monday


def test_a_quiet_week_is_empty_with_null_answers_and_a_deleted_idea_is_left_out(root, tmp_path):
    state = tmp_path / "state"
    got = board_week.last_week(root, state, SETTINGS, NOW, _rows())
    assert got["empty"] is True and got["answers"] is None and got["dearest"] is None and got["fastest"] is None and got["before"] is None
    log(root, "keeper_state", at(14, 12), idea="deleted", state="done", was="working")
    _ledger(state, "deleted", at(14, 9), 5.0)
    again = board_week.last_week(root, state, SETTINGS, NOW, _rows())
    assert again["goals"] == [] and again["dearest"] is None and again["empty"] is True
    log(root, "goal_accepted", at(14, 12), goal="offline", met=True, by="PM")
    assert board_week.last_week(root, state, SETTINGS, NOW, _rows())["empty"] is False                          # a flag alone makes it


def test_ideas_week_is_the_hosts_and_a_phones_and_checks_its_week(fake_repo):
    with pytest.raises(CommandError, match="Open a folder first"):
        Orkboard().command("ideas.week", {})
    host = Orkboard(fake_repo)
    assert BoardPhone.allowed(host, "ideas.week", {})
    got = host.command("ideas.week", {})
    json.dumps(got)
    assert got["empty"] is True and got["week"] and host.command("ideas.week", {"week": "2026-W42"})["from"] == "2026-10-12"
    for bad in ("last", 5, "2026-W99"):
        with pytest.raises(CommandError, match="ISO week"):
            host.command("ideas.week", {"week": bad})


# -- nights in a row (spec 42 §8) ---------------------------------------------------------------------------------

def _worked(root, days):
    for d in days:
        run(root, at(d, 1, 30), drafted=1)


def test_a_run_of_worked_nights_counts_up_to_the_last_that_ended_and_an_idle_or_off_night_ends_it(root):
    _worked(root, (20, 19, 18, 16))                                          # the 17th is off: it ends the run
    assert board_week.streak(root, SETTINGS, NOW) == 3
    run(root, at(17, 1, 30))                                                  # idle: still ends it
    assert board_week.streak(root, SETTINGS, NOW) == 3
    _worked(root, (17,))
    assert board_week.streak(root, SETTINGS, NOW) == 5                        # 16, 17, 18, 19, 20 … and the 15th is off
    assert board_week.streak(root, {"night": ""}, NOW) == 0


def test_todays_night_is_not_counted_until_it_has_ended_and_a_long_run_is_counted_through_the_parts(root):
    _worked(root, range(20, 0, -1))
    assert board_week.streak(root, SETTINGS, at(20, 3, 0)) == 19              # the night of the 20th is still going on
    assert board_week.streak(root, SETTINGS, at(20, 8, 0)) == 20
    assert board_week.streak(root, SETTINGS, NOW) == 20                       # 1 October is the first with a log; the 30th of September is off


def test_the_streak_is_in_this_week_and_last_week(root, tmp_path):
    _worked(root, (19, 18))
    assert board_week.this_week(root, tmp_path / "s", SETTINGS, NOW, {})["streak"] == 0          # the night of the 20th was off
    _worked(root, (20,))
    assert board_week.this_week(root, tmp_path / "s", SETTINGS, NOW, {})["streak"] == 3
    assert board_week.last_week(root, tmp_path / "s", SETTINGS, NOW, {})["streak"] == 1           # the run as the week ended: the 18th, and the 17th is off
    assert board_week.last_week(root, tmp_path / "s", SETTINGS, NOW, {}, week="2026-W43")["streak"] == 3


def test_the_recap_carries_the_streak(fake_repo):
    host = Orkboard(fake_repo)
    today = dt.date.today()
    ended = dt.datetime.now().time() >= dt.time(7, 0)                       # tonight's window (01:00–07:00) counts once it has ended
    for back in (0, 1, 2) if ended else (1, 2):
        when = dt.datetime.combine(today - dt.timedelta(days=back), dt.time(1, 30)).astimezone()
        log(Path(host.ideas.host.repo_root), "night_run", when, drafted=1, started=0, refreshed=0, proposed=0)
    assert host.command("ideas.recap", {"since": int((dt.datetime.now().timestamp() - 3600) * 1000)})["nights"] == (3 if ended else 2)


def test_a_check_that_found_nothing_is_no_result_in_the_week_or_in_last_week(root, tmp_path):
    """Spec 43 A: a clean check is not counted in `merged` or `first_time`, nor is it the fastest from idea to dev."""
    log(root, "task_state", NOW - dt.timedelta(days=1), idea="a", task="k1", state="merged", was="review", round=1)
    log(root, "task_state", NOW - dt.timedelta(days=1, hours=1), idea="a", task="k2", state="merged", was="running", round=1, check=True, clean=True)
    got = board_week.this_week(root, tmp_path / "state", SETTINGS, NOW, {"ideas": []})
    assert (got["merged"], got["first_time"]) == (1, 1)
    log(root, "idea_added", at(14, 8), idea="export", track="offline")
    log(root, "task_state", at(14, 8, 5), idea="export", task="k1", state="merged", was="running", round=1, check=True, clean=True)
    log(root, "task_state", at(14, 10), idea="export", task="k2", state="merged", was="review", round=1)
    last = board_week.last_week(root, tmp_path / "state", SETTINGS, NOW, _rows())
    assert (last["merged"], last["first_time"]) == (1, 1) and last["fastest"]["minutes"] == 120


def test_a_night_where_only_a_clean_check_merged_is_not_worked(root):
    log(root, "task_state", at(19, 3), idea="a", task="k1", state="merged", was="running", round=1, check=True, clean=True)
    run(root, at(19, 1, 5))
    log(root, "task_state", at(18, 3), idea="a", task="k2", state="merged", was="review", round=1)
    got = board_week.nights(root, SETTINGS, NOW, n=3)
    assert [(n["date"], n["kind"]) for n in got] == [("2026-10-20", "off"), ("2026-10-19", "idle"), ("2026-10-18", "worked")]
