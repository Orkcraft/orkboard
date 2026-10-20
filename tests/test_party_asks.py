"""Spec 46 A, the party asks: a goal's read has its members' views in its context (balance, quality), in quality each member
asks first, and each question says who asks it. The model call is stubbed."""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest

from orkboard.core.idea_keeper import IdeaKeeper
from orkboard.gui.board_host import Orkboard
from orkboard.realm import event_log, goal_team, idea_target, idea_questions, ideas, jobs, library, roles


class Model:
    """The keeper's call: answers by who is asked (`ask` for a member's, the goal's read for the leader's) and remembers."""

    def __init__(self, members=None, goal=None) -> None:
        self.members, self.goal = members or {}, goal if goal is not None else {"summary": "S.", "questions": [], "metrics": []}
        self.calls, self.lock = [], threading.Lock()

    def __call__(self, tier, prompt, effort="", budget=None):
        kind = "goal" if "keeper of this project's Task board" in prompt else "ask"
        with self.lock:
            self.calls.append({"kind": kind, "tier": tier, "prompt": prompt, "effort": effort, "budget": budget})
        if kind == "goal":
            return json.dumps(self.goal), 0.01, 100, "s"
        answer = next((v for name, v in self.members.items() if f"You are {name}," in prompt), {"questions": []})
        if isinstance(answer, Exception):
            raise answer
        return (answer if isinstance(answer, str) else json.dumps(answer)), 0.02, 50, "s"

    def of(self, kind):
        return [c for c in self.calls if c["kind"] == kind]


@pytest.fixture
def keeper(tmp_path):
    root, state = tmp_path / "wiki", tmp_path / ".orkcraft"
    settings = {"target": "quality"}
    k = IdeaKeeper(tmp_path, state, lambda: root, lambda: settings)
    k.root, k.state, k.settings_now = root, state, settings
    return k


def _goal(k, team=("grunt", "tester", "reviewer", "ghost"), leader="architect"):
    """A goal with a party: the library's agents are the project's roles; `ghost` is a slug that is no role."""
    library.install(k.state, ["tester", "reviewer", "architect"])
    slug = ideas.save_goal(k.root, None, "Ship the sync", "Make the sync reliable.")[0]
    goal_team.set_team(k.root, slug, list(team), [], leader)
    return slug


def _questions(k):
    return next(t for t in ideas.tracks(k.root) if t["slug"] == "ship-the-sync")["questions"]


def _read(k, slug, **kw):
    k.read_goal(slug, **kw)
    for _ in range(500):
        if not k.busy(f"goal:{slug}"):
            return
        time.sleep(0.01)
    raise AssertionError("the keeper never finished")


def _events(k, name):
    return [r for r in event_log.read(k.repo_root) if r["event"] == name]


QS = [{"ask": "Which devices?", "choices": ["iPhone", "Android"], "pick": 0, "why": "most users", "by": "tester"},
      {"ask": "Which week?", "choices": ["this", "next"], "pick": 1, "by": ""},
      {"ask": "Whose call?", "choices": ["ours", "theirs"], "pick": 0, "by": "wizard"},
      {"ask": "Who reviews?", "choices": ["Ana", "Bo"], "pick": 0, "by": "reviewer"},
      {"ask": "How fast?", "choices": ["now", "later"], "pick": 0},
      {"ask": "Sixth?", "choices": ["a", "b"], "pick": 0}]


def test_the_ask_step_the_questions_a_goal_keeps_and_the_budget():
    assert idea_target.pick("ask", "thrift") is None and idea_target.pick("ask", "balance") is None
    assert idea_target.pick("ask", "quality") == ("warrior", "low")
    assert idea_target.budget("ask", "quality") == 0.20 and idea_target.READS["ask"] == 0 and idea_target.CONTEXT["ask"] == 4_000
    assert idea_target.GOAL_QUESTIONS == {"thrift": 3, "balance": 3, "quality": 5}


def test_a_question_says_who_it_is_for_and_a_leader_asks_what_is_nobodys():
    q = idea_questions.of({"ask": "Which?", "choices": ["a", "b"], "pick": 0, "by": " Tester "})
    assert q["by"] == "tester" and "by" not in idea_questions.of({"ask": "Which?"})
    assert idea_questions.asked_by([q, {"ask": "x"}, {"ask": "y", "by": "wizard"}], ["tester"], "architect") == ["tester", "architect", "architect"]
    assert idea_questions.line(q) == "Which? (**a** / b)"                      # the page keeps what is asked, not who asks


def test_thrift_reads_with_the_leader_alone(keeper):
    keeper.settings_now["target"] = "thrift"
    slug = _goal(keeper)
    keeper.call = model = Model(goal={"summary": "S.", "metrics": [], "questions": QS})
    _read(keeper, slug, party=True)
    assert len(model.calls) == 1 and "Your party" not in model.calls[0]["prompt"]
    assert "by" not in model.calls[0]["prompt"].split('"questions"')[1]
    st = ideas.goal_state(keeper.state, slug)
    assert st["state"] == "asks" and len(_questions(keeper)) == 3          # at most 3 in thrift
    assert json.loads((keeper.state / "goals" / slug / "state.json").read_text())["party"] == 0


def test_balance_has_each_members_view_in_the_leaders_context_and_calls_no_member(keeper):
    keeper.settings_now["target"] = "balance"
    slug = _goal(keeper)
    keeper.call = model = Model(goal={"summary": "S.", "metrics": [], "questions": QS})
    _read(keeper, slug, party=True)
    assert len(model.calls) == 1
    prompt = model.calls[0]["prompt"]
    assert "Your party:" in prompt and "What your party asks" not in prompt
    assert prompt.index("Its description") < prompt.index("Your party") < prompt.index("Its links")
    tester, reviewer = library.get("tester"), library.get("reviewer")
    assert f"- Tester (tester; engineering; builds): {tester.line}" in prompt
    assert f"- Reviewer (reviewer; engineering; checks): {reviewer.line}" in prompt
    assert f"done when: {reviewer.check.done}" in prompt and reviewer.check.applies in prompt     # a checker's check
    assert "Grunt" not in prompt.split("Your party:")[1].split("Its links")[0] and "ghost" not in prompt
    assert '"by": "the slug of the member' in prompt and "never two questions on one thing" in prompt
    assert len(_questions(keeper)) == 3                                                                          # at most 3 in balance
    raw = json.loads((keeper.state / "goals" / slug / "state.json").read_text())
    assert raw["asks_by"] == ["tester", "architect", "architect"] and raw["party"] == 2 and raw["by_party"] == 1


def test_quality_asks_each_member_once_before_the_leader_and_the_leader_keeps_five(keeper):
    slug = _goal(keeper)
    keeper.call = model = Model(
        members={"Tester": {"questions": [QS[0], {"ask": "Second?"}, {"ask": "Third, cut?"}]},
                 "Reviewer": {"questions": [{"ask": "Who reviews?", "choices": ["Ana", "Bo"], "pick": 1}]}},
        goal={"summary": "S.", "metrics": [], "questions": QS})
    _read(keeper, slug, party=True)
    kinds = [c["kind"] for c in model.calls]
    assert kinds == ["ask", "ask", "goal"] and len(model.of("ask")) == 2                         # each once, all before the leader
    members = {c["prompt"].split(",")[0].replace("You are ", "") for c in model.of("ask")}
    assert members == {"Tester", "Reviewer"}                                                     # not Grunt, the leader or a ghost
    for c in model.of("ask"):
        assert c["effort"] == "low" and c["budget"] == 0.20 and "a member of this goal's party" in c["prompt"]
        assert "Make the sync reliable." in c["prompt"] and "Architect (leads)" in c["prompt"] and "Reviewer (checks)" in c["prompt"]
    assert model.of("ask")[0]["tier"] in ("laborer", "elder", "warrior")
    lead = model.of("goal")[0]["prompt"]
    assert lead.startswith("You are Architect, the leader") and "What your party asks:" in lead
    assert "Tester:\n- Which devices?" in lead and "Second?" in lead and "Third, cut?" not in lead      # at most 2 of a member's
    assert "Reviewer:\n- Who reviews? (Ana / **Bo**)" in lead
    assert len(_questions(keeper)) == 5                                   # at most 5 in quality
    raw = json.loads((keeper.state / "goals" / slug / "state.json").read_text())
    assert raw["asks_by"] == ["tester", "architect", "architect", "reviewer", "architect"] and raw["party"] == 2
    asked = {e["by"]: e for e in _events(keeper, "party_asked")}
    assert set(asked) == {"tester", "reviewer"} and asked["tester"]["questions"] == 2 and asked["tester"]["goal"] == slug
    assert asked["tester"]["step"] == "ask" and asked["tester"]["prompt_chars"] > 0 and asked["tester"]["cost"] == 0.02


def test_a_member_that_fails_runs_out_or_says_nothing_adds_nothing_and_the_read_goes_on(keeper):
    slug = _goal(keeper)
    keeper.call = model = Model(members={"Tester": RuntimeError("boom"), "Reviewer": "not json"}, goal={"summary": "S.", "questions": []})
    _read(keeper, slug, party=True)
    assert len(model.of("goal")) == 1 and "What your party asks" not in model.of("goal")[0]["prompt"]
    assert ideas.goal_state(keeper.state, slug)["state"] == "ready"
    keeper.call = model = Model(members={"Tester": RuntimeError("the budget was spent"), "Reviewer": {"questions": []}})
    _read(keeper, slug, party=True)
    assert ideas.goal_state(keeper.state, slug)["state"] == "ready" and "What your party asks" not in model.of("goal")[0]["prompt"]


def test_stop_all_stops_the_members_calls_as_it_stops_the_read(keeper):
    slug = _goal(keeper)

    def call(tier, prompt, effort="", budget=None):
        keeper.stop_all()
        return json.dumps({"questions": [{"ask": "Too late?"}], "summary": "S."}), 0.01, 1, "s"

    keeper.call = call
    _read(keeper, slug, party=True)
    assert ideas.goal_state(keeper.state, slug)["state"] == "raw" and not _events(keeper, "party_asked")


def test_a_spent_window_asks_no_member(keeper, monkeypatch):
    slug = _goal(keeper)
    monkeypatch.setattr(keeper, "window_until", lambda: time.time() + 600)
    keeper.call = model = Model()
    _read(keeper, slug, party=True)
    assert model.of("ask") == [] and len(model.of("goal")) == 1


def test_no_member_asks_on_an_answered_read_an_edit_s_or_a_refresh(keeper):
    slug = _goal(keeper)
    keeper.call = model = Model()
    _read(keeper, slug, said="npm", answered=True, party=True)          # the answers
    _read(keeper, slug)                                                   # an Edit's (not a first read)
    keeper.read_goal_one(slug, "", "refresh", ["src/app.py"])             # the night's refresh
    assert model.of("ask") == [] and len(model.of("goal")) == 3
    assert all("Your party:" in c["prompt"] for c in model.of("goal"))   # but with the members' views (quality)


# -- the host: who asks in Needs you, the events ----------------------------------------------------------------------

@pytest.fixture
def host(fake_repo, monkeypatch):
    h = Orkboard(fake_repo)
    h.calls = []

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        h.calls.append(prompt)
        return json.dumps({"summary": "S.", "metrics": [], "questions": [QS[0], {**QS[3], "by": "reviewer"}, QS[1]]}), 0.01, 10, "s"

    monkeypatch.setattr(jobs, "run_read", run_read)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


def _wait(host, slug):
    for _ in range(500):
        if not host.ideas.keeper.busy_goal(slug):
            return
        time.sleep(0.01)
    raise AssertionError("the keeper never finished")


def _host_events(host, name):
    return [r for r in event_log.read(Path(host.town.repo_root)) if r["event"] == name]


def test_needs_you_says_who_asks_each_question_and_the_events_count_the_members(host):
    slug = host.command("ideas.goal_save", {"about": "Make the sync reliable.", "team": ["tester", "reviewer"], "leader": "architect"})["slug"]
    _wait(host, slug)
    row = next(n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "goal")
    assert [a["by"]["slug"] for a in row["asked"]] == ["tester", "reviewer", "architect"]
    assert row["asked"][0]["by"]["name"] == "Tester" and row["asked"][2]["by"]["name"] == "Architect"
    assert set(row["asked"][0]["by"]["head"]) == {"craft", "race", "tier"}
    assert row["questions"][0] == "Which devices? (**iPhone** / Android) — most users"            # the page's lines are unchanged
    read = _host_events(host, "goal_read")[0]
    assert read["party"] == 2 and read["by_party"] == 2          # two members' views, two of the three questions theirs
    host.command("ideas.answer", {"slug": slug, "answers": ["iPhone", "Bo", ""], "goal": True})
    _wait(host, slug)
    answered = _host_events(host, "goal_answered")[0]
    assert answered["by_party"] == 2 and answered["answers"] == 2 and answered["picked"] == 2
    assert "Your party:" in host.calls[-1]                                                      # the answered read has the views


def test_a_goal_with_no_member_reads_as_before(host):
    slug = host.command("ideas.goal_save", {"about": "Plain goal."})["slug"]
    _wait(host, slug)
    assert "Your party" not in host.calls[0]
    row = next(n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "goal")
    assert {a["by"]["slug"] for a in row["asked"]} == {"taskmaster"}
    assert _host_events(host, "goal_read")[0]["party"] == 0 and _host_events(host, "goal_read")[0]["by_party"] == 0
    assert roles.TASKMASTER == "taskmaster"
