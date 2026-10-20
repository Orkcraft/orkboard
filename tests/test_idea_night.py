"""Spec 35 §7, §8 on the keeper, the model call stubbed: the night's order, a refresh only for a goal whose paths
changed (a fixture repository with a commit), proposals by the Target, never more than 3 waiting, a declined one read
back the next night, the reserve, `night_run`."""
from __future__ import annotations

import datetime as dt
import json
import subprocess

import pytest

from orkboard.core import idea_night
from orkboard.core.idea_keeper import IdeaKeeper
from orkboard.realm import event_log, ideas
from orkboard.sources.limits import Limit

from tests.test_idea_draft import DRAFT, PLAN, Model


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def keeper(fake_repo, tmp_path):
    root, state = tmp_path / "wiki", fake_repo / ".orkcraft"
    settings = {"target": "balance", "autostart": True, "night": "01:00-07:00"}
    started, plans = [], []
    k = IdeaKeeper(fake_repo, state, lambda: root, lambda: settings, on_plan=plans.append,
                   start_night=lambda slug: started.append(slug) or True)
    k.root, k.state, k.settings_now, k.started, k.plans, k.limits_now = root, state, settings, started, plans, []
    k.limits = lambda: k.limits_now
    return k


def _goal(k, title, links=(), summary="", read_at=""):
    slug = ideas.add_track(k.root, title)
    ideas.write_goal_reading(k.root, slug, summary, {}, [], links=list(links))
    ideas.save_goal_state(k.state, slug, state="ready", read_at=read_at or k.head())
    return slug


def _events(k, name):
    return [r for r in event_log.read(k.repo_root) if r["event"] == name]


def test_the_night_runs_its_steps_in_order_and_says_so(keeper):
    g = _goal(keeper, "Table", links=["src/app.py"], summary="It lives in `docs/notes.md`.")
    low = ideas.add_idea(keeper.root, "a low idea", g, keeper.state, priority="low", queue="night")
    high = ideas.add_idea(keeper.root, "a high idea", g, keeper.state, priority="high", queue="night")
    old = ideas.add_idea(keeper.root, "an idea from before", g, keeper.state)            # raw, no queue: the night's
    tonight = ideas.add_idea(keeper.root, "passed for tonight", g, keeper.state)
    ideas.save_plan(keeper.state, tonight, {"idea": tonight, "passed_at": "x", "start_at": "night", "tasks": [], "todos": []})
    ideas.save_state(keeper.state, tonight, state="plan")
    (keeper.repo_root / "docs" / "notes.md").write_text("# Notes\n\n- changed\n")
    _git(keeper.repo_root, "commit", "-qam", "notes changed")
    keeper.call = model = Model(draft=lambda p: {**DRAFT, "questions": []}, plan=PLAN, goal={"summary": "Again.", "questions": []},
                                propose={"proposals": [{"goal": g, "title": "Sort the table", "why": "People sort.\nOften."},
                                                       {"goal": "general", "title": "Never here", "why": "x"},
                                                       {"goal": g, "title": "Filter it", "why": "They filter."},
                                                       {"goal": g, "title": "A third", "why": "Too many."}]})
    counts = keeper.run_night("2026-10-18T01:00")
    drafts = [a["prompt"] for a in model.asked if a["step"] == "draft"]
    assert ["a high idea" in drafts[0], "an idea from before" in drafts[1] or "a low idea" in drafts[1]] == [True, True]
    assert "a low idea" in drafts[2] or "an idea from before" in drafts[2]
    order = [s for s in model.steps() if s != "plan"]
    assert order == ["draft", "draft", "draft", "goal", "propose"]               # 1. queue 3. refresh 4. proposals
    assert keeper.started == [tonight] and set(keeper.plans) == {low, high, old}   # 2. the plans that start at night
    assert counts == {"drafted": 3, "started": 1, "refreshed": 1, "proposed": 2, "held": 0}
    proposed = [i for i in ideas.ideas(keeper.root) if ideas.state(keeper.state, i["slug"])["state"] == "proposed"]
    assert {i["title"] for i in proposed} == {"Sort the table", "Filter it"}       # balance: 2, never into General
    assert all(i["track"] == g for i in proposed)
    page = ideas.idea_page(keeper.root, proposed[0]["slug"])
    assert page.section("Done when") == "" and page.section("Gist") in ("People sort.\nOften.", "They filter.")
    assert next(a for a in model.asked if a["step"] == "goal")["prompt"].count("docs/notes.md") >= 1
    (run,) = _events(keeper, "night_run")
    assert {k: run[k] for k in ("drafted", "started", "refreshed", "proposed", "held")} == counts
    assert run["step"] == "propose" and run["seconds"] is not None and run["cost"] is None
    assert [e["goal"] for e in _events(keeper, "proposal_made")] == [g, g]
    refreshed = ideas.goal_state(keeper.state, g)
    assert refreshed["measure"]["step"] == "refresh" and refreshed["read_at"] == keeper.head()


def test_an_unchanged_goal_costs_nothing(keeper):
    _goal(keeper, "Quiet", links=["src/app.py"])
    (keeper.repo_root / "docs" / "notes.md").write_text("# other\n")
    _git(keeper.repo_root, "commit", "-qam", "elsewhere")
    keeper.call = model = Model(propose={"proposals": []})
    assert keeper.run_night()["refreshed"] == 0 and "goal" not in model.steps()


def test_proposals_by_the_target_never_more_than_three_waiting(keeper):
    g = _goal(keeper, "Table")
    many = {"proposals": [{"goal": g, "title": f"Idea {n}", "why": "why"} for n in range(5)]}
    keeper.settings_now["target"] = "thrift"
    keeper.call = model = Model(propose=many)
    assert keeper.run_night()["proposed"] == 0 and "propose" not in model.steps()
    keeper.settings_now["target"] = "quality"
    assert keeper.run_night()["proposed"] == 3
    keeper.call = model = Model(propose=many)
    assert keeper.run_night()["proposed"] == 0 and model.asked == []           # 3 wait: none more


def test_a_declined_proposal_is_read_back_the_next_night_and_never_proposed_again(keeper):
    g = _goal(keeper, "Table")
    idea_night.decline(keeper.state, "Sort the table", g, "we sort elsewhere")
    keeper.call = model = Model(propose={"proposals": [{"goal": g, "title": "Sort the table", "why": "again"}]})
    assert keeper.run_night()["proposed"] == 0
    prompt = next(a for a in model.asked if a["step"] == "propose")["prompt"]
    assert "Sort the table (goal table): we sort elsewhere" in prompt
    assert idea_night.declined(keeper.state)[-1]["reason"] == "we sort elsewhere"


def test_the_night_stops_at_its_reserve(keeper):
    g = _goal(keeper, "Table")
    for n in range(2):
        ideas.add_idea(keeper.root, f"idea {n}", g, keeper.state, queue="night")
    reset = dt.datetime.now() + dt.timedelta(hours=3)
    keeper.limits_now = [Limit("claude", "", "session", 0.05 if keeper.night_key(dt.datetime.now().timestamp()) else 0.2, reset)]
    keeper.call = model = Model(draft=DRAFT, plan=PLAN, propose={"proposals": []})
    counts = keeper.run_night()
    assert counts["drafted"] == 0 and counts["held"] >= 2 and model.asked == []
    assert keeper.night_state()["held"] is True


def test_the_proposals_call_reads_nothing_and_keeps_no_session(keeper, monkeypatch):
    from orkboard.realm import jobs
    seen = []

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        seen.append({"resume": resume, **kw})
        return json.dumps({"proposals": []}), None, 5, ""

    monkeypatch.setattr(jobs, "run_read", run_read)
    _goal(keeper, "Table")
    keeper.run_night()
    (call,) = seen
    assert call["tools"] is False and call["one_shot"] is True and call["resume"] == "" and call["budget"] == 0.3


def test_at_work_and_tonight_are_what_the_computer_is_kept_awake_for(keeper):
    """Spec 47 §3: `at_work` is a draft, a plan, a read, a check or the night's run; `tonight` the rows of the night's
    steps 1 and 2, never its proposals."""
    g = _goal(keeper, "Table")
    assert not keeper.at_work() and keeper.tonight() == 0
    ideas.add_idea(keeper.root, "for the day", g, keeper.state, queue="hold")            # held by the person: not tonight's
    ideas.add_idea(keeper.root, "from before", g, keeper.state)                          # raw, no queue: the night's
    ideas.add_idea(keeper.root, "for tonight", g, keeper.state, queue="night")
    passed = ideas.add_idea(keeper.root, "passed for tonight", g, keeper.state)
    ideas.save_plan(keeper.state, passed, {"idea": passed, "passed_at": "x", "start_at": "night", "tasks": [], "todos": []})
    ideas.save_state(keeper.state, passed, state="plan")
    soon = ideas.add_idea(keeper.root, "passed to start now", g, keeper.state)
    ideas.save_plan(keeper.state, soon, {"idea": soon, "passed_at": "x", "start_at": "now", "tasks": [], "todos": []})
    ideas.save_state(keeper.state, soon, state="plan")
    proposed = ideas.add_idea(keeper.root, "proposed", g, keeper.state)
    ideas.save_state(keeper.state, proposed, state="proposed", queue="")
    assert keeper.tonight() == 3
    keeper._busy["some-idea"] = "drafting"
    assert keeper.at_work()
    keeper._busy.clear()
    keeper._night_busy = True
    assert keeper.at_work()
