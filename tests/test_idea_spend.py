"""The ledger and its rollup (docs/specs/36-agents-spend.md §1, §2, §4, §6): code, no model."""
from __future__ import annotations

import datetime as dt
import io
import json
import zipfile

import pytest

from orkcraft.realm import analytics, idea_spend, ideas, plans


def _line(step, cost, task="", rnd=None, role="taskmaster", at="", tier="elder", tokens=None):
    return idea_spend.line(step, role, "claude", "opus", tier, "medium",
                           tokens or idea_spend.tokens_of({"in": 100, "out": 10, "cache_read": 50}), cost, task, rnd, at)


def _plan(state, slug, tasks):
    """A passed plan as the runner keeps it (its file written as the runner writes it)."""
    folder = state / "ideas" / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(json.dumps({"idea": slug, "made_at": "2026-10-18T09:00:00", "passed_at": "x",
                                                  "todos": [], "tasks": tasks}))


def _task(tid, state, rnd=1, role="grunt", finished="", cost=None, ran_tier="warrior"):
    return {"id": tid, "title": tid, "brief": "b", "tier": "warrior", "kind": "code", "after": [], "state": state,
            "round": rnd, "role": role, "finished": finished, "cost": cost, "ran_tier": ran_tier}


def _fixture(state, slug="dark-mode"):
    """goal (on the goal), draft, answer, plan, a task in round 1 and 2 with a fix, and a dropped task."""
    for row in (_line("draft", 0.5), _line("answer", 0.25), _line("talk", None), _line("plan", 0.2),
                _line("task", 1.0, "k1", 1, "grunt"), _line("task", 0.4, "k1", 2, "grunt"), _line("fix", 0.1, "k1", 2, "grunt"),
                _line("task", 0.3, "k2", 1, "grunt")):
        assert idea_spend.append(state, row, idea=slug)
    idea_spend.append(state, _line("goal", 0.4), goal="speed")
    _plan(state, slug, [_task("k1", "review", 2), _task("k2", "failed")])


def test_a_line_has_the_specs_fields_and_an_unpriced_call_is_null_never_0(tmp_path):
    row = _line("task", None, "k1", 2, "grunt", tokens=idea_spend.tokens_of(None, 1234))
    assert set(row) == {"at", "step", "task", "round", "role", "tool", "model", "tier", "effort", "tokens", "cost"}
    assert row["cost"] is None and row["round"] == 2
    assert row["tokens"] == {"in": None, "out": None, "cache_read": None, "cache_write": None, "total": 1234}
    keeper = _line("plan", 0.12)
    assert "task" not in keeper and "round" not in keeper and keeper["role"] == "taskmaster"
    assert keeper["tokens"] == {"in": 100, "out": 10, "cache_read": 50, "cache_write": None}


def test_each_line_goes_to_its_ledger(tmp_path):
    idea_spend.append(tmp_path, _line("draft", 0.1), idea="dark-mode")
    idea_spend.append(tmp_path, _line("goal", 0.1), goal="speed")
    idea_spend.append(tmp_path, _line("propose", 0.1))
    assert len(idea_spend.read(tmp_path / "ideas" / "dark-mode" / "spend.jsonl")) == 1
    assert len(idea_spend.read(tmp_path / "goals" / "speed" / "spend.jsonl")) == 1
    assert len(idea_spend.read(tmp_path / "ideas" / "spend-board.jsonl")) == 1
    assert idea_spend.append(tmp_path, _line("draft", 0.1), idea="../x") is False


def test_a_disk_that_refuses_never_troubles_the_work(tmp_path):
    (tmp_path / "ideas").write_text("a file where the folder should be")
    assert idea_spend.append(tmp_path, _line("draft", 0.1), idea="dark-mode") is False


def test_the_rollup_gives_each_stage_its_sum(tmp_path):
    _fixture(tmp_path)
    got = idea_spend.of_idea(tmp_path, "dark-mode")
    st = got["stages"]
    assert st["spec"] == {"usd": 0.75, "tokens": 480, "calls": 3}           # draft, answer, a talk unpriced
    assert st["plan"]["usd"] == 0.2 and st["work"]["usd"] == 1.0
    assert st["rework"]["usd"] == 0.5 and st["rework"]["calls"] == 2        # round 2 and the gate's fix
    assert st["dropped"] == {"usd": 0.3, "tokens": 160, "calls": 1}         # the failed task, out of work
    assert st["goal"]["calls"] == 0 and st["goal"]["usd"] == 0
    assert got["usd"] == pytest.approx(2.75) and got["unpriced"] == 1
    assert got["tasks"]["k1"] == {"usd": 1.5, "work": 1.0, "rework": 0.5}
    assert list(st) == list(idea_spend.STAGES)


def test_only_unpriced_lines_give_null_never_0(tmp_path):
    idea_spend.append(tmp_path, _line("draft", None), idea="x")
    idea_spend.append(tmp_path, _line("task", None, "k1", 1, "grunt"), idea="x")
    got = idea_spend.of_idea(tmp_path, "x")
    assert got["usd"] is None and got["stages"]["spec"]["usd"] is None and got["stages"]["work"]["usd"] is None
    assert got["unpriced"] == 2 and got["tasks"]["k1"]["usd"] is None


def test_a_goal_sums_its_own_lines_and_its_ideas(tmp_path):
    _fixture(tmp_path)
    _plan(tmp_path, "dark-mode", [_task("k1", "merged", 2), _task("k2", "failed")])
    got = idea_spend.of_goal(tmp_path, "speed", ["dark-mode"])
    assert got["stages"]["goal"]["usd"] == 0.4 and got["stages"]["spec"]["usd"] == 0.75
    assert got["stages"]["dropped"]["usd"] == 0.3
    assert got["merged"] == 1 and got["usd"] == pytest.approx(3.15) and got["usd_per_merged"] == pytest.approx(3.15)
    assert idea_spend.of_goal(tmp_path, "speed")["usd"] == 0.4


def test_by_role_over_seven_days(tmp_path):
    idea_spend.forget()
    now = dt.datetime.now()
    recent, old = (now - dt.timedelta(days=1)).isoformat(timespec="seconds"), (now - dt.timedelta(days=9)).isoformat(timespec="seconds")
    tasks = [_task("k1", "merged", 1, finished=recent), _task("k2", "merged", 2, finished=recent),
             _task("k3", "failed", 1, finished=recent), _task("k4", "merged", 1, finished=old),
             _task("k5", "merged", 1, role="scribe", finished=recent), _task("k6", "review", 1)]
    _plan(tmp_path, "a", tasks)
    for tid, cost in (("k1", 0.3), ("k2", 0.5), ("k3", 0.2), ("k4", 9.0), ("k5", 0.1), ("k6", 1.0)):
        idea_spend.append(tmp_path, _line("task", cost, tid, 1, "grunt"), idea="a")
    idea_spend.append(tmp_path, _line("task", 0.25, "k2", 2, "grunt"), idea="a")
    idea_spend.append(tmp_path, _line("plan", 0.2, at=recent), idea="a")
    idea_spend.append(tmp_path, _line("plan", 5.0, at=old), idea="a")
    idea_spend.append(tmp_path, _line("propose", 0.05, at=recent))
    week = idea_spend.by_role(tmp_path)
    g = week["grunt"]
    assert (g["finished"], g["merged"], g["first_time"]) == (3, 2, 1) and g["spent"] == pytest.approx(1.25)
    assert g["usd_per_merged"] is None                                        # under 3 merged: too few to say
    assert week["scribe"]["merged"] == 1
    tm = week["taskmaster"]                                                   # every task of its plans, whoever did it
    assert (tm["finished"], tm["first_time"], tm["plans"]) == (4, 2, 1) and tm["spent"] == pytest.approx(0.25)
    _plan(tmp_path, "b", [_task("m1", "merged", 1, finished=recent), _task("m2", "merged", 1, finished=recent)])
    idea_spend.append(tmp_path, _line("task", 0.4, "m1", 1, "grunt"), idea="b")
    assert idea_spend.by_role(tmp_path)["grunt"]["merged"] == 2               # cached for 60 s
    idea_spend.forget()
    g = idea_spend.by_role(tmp_path)["grunt"]
    assert g["merged"] == 4 and g["usd_per_merged"] == pytest.approx(round(1.65 / 4, 4))


def test_a_deleted_ideas_lines_land_in_spend_gone_and_the_week_keeps_them(tmp_path):
    idea_spend.forget()
    root = tmp_path / "wiki"
    goal = ideas.add_track(root, "Speed")
    slug = ideas.add_idea(root, "dark mode", goal, state_dir=tmp_path)
    recent = (dt.datetime.now() - dt.timedelta(hours=1)).isoformat(timespec="seconds")
    _plan(tmp_path, slug, [_task("k1", "merged", 1, finished=recent)])
    idea_spend.append(tmp_path, _line("task", 0.7, "k1", 1, "grunt"), idea=slug)
    ideas.drop(root, slug, tmp_path)
    assert not (tmp_path / "ideas" / slug).exists()
    (gone,) = idea_spend.read(tmp_path / "ideas" / "spend-gone.jsonl")
    assert gone["idea"] == slug and gone["cost"] == 0.7 and gone["ended"] == "merged" and gone["last_round"] == 1
    g = idea_spend.by_role(tmp_path)["grunt"]
    assert g["merged"] == 1 and g["spent"] == 0.7


def test_the_analytics_zip_holds_each_ideas_ledger(tmp_path):
    state = tmp_path / ".orkcraft"
    _plan(state, "dark-mode", [_task("k1", "review")])
    idea_spend.append(state, _line("plan", 0.2), idea="dark-mode")
    data = analytics.pack(tmp_path, [], {}, lambda b, d: [], lambda b, d: [])
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert "ideas/dark-mode/spend.jsonl" in names and "ideas/dark-mode/plan.json" in names


def test_the_estimate_learns_from_the_last_20_tasks_of_a_tier(tmp_path):
    assert idea_spend.tier_costs(tmp_path) == plans.DEFAULT_COST
    tasks = [_task(f"k{i}", "merged", finished=f"2026-10-{i + 1:02d}T10:00:00", cost=0.1) for i in range(5)]
    tasks += [_task(f"m{i}", "merged", finished=f"2026-10-{i + 10:02d}T10:00:00", cost=1.0) for i in range(20)]
    tasks += [_task("e1", "failed", finished="2026-10-11T10:00:00", cost=2.0, ran_tier="elder"),
              _task("e2", "review", cost=50.0, ran_tier="elder")]                 # not finished: not counted
    _plan(tmp_path, "a", tasks)
    costs = idea_spend.tier_costs(tmp_path)
    assert costs["warrior"] == pytest.approx(1.0)                           # the 20 newest, not the 5 older at 0.1
    assert costs["elder"] == pytest.approx(2.0) and costs["laborer"] == plans.DEFAULT_COST["laborer"]
    est = idea_spend.estimate_of({"ran_tier": "warrior"}, costs)
    assert est == {"low": 0.5, "high": 1.5}
    assert idea_spend.over(3.0, est) == 2.0 and idea_spend.over(1.4, est) is None and idea_spend.over(None, est) is None


def test_the_keepers_estimate_uses_the_learned_costs():
    from orkcraft.core import idea_keeper
    tasks = [{"tier": "warrior"}, {"tier": "elder"}]
    assert idea_keeper.estimate(tasks, None, {"warrior": 2.0, "elder": 4.0, "laborer": 0.1}) == {
        "tasks": 2, "usd_low": 3.0, "usd_high": 9.0}
    assert idea_keeper.estimate(tasks)["usd_high"] == round((0.3 + 1.0) * 1.5, 2)
