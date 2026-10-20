"""Spec 43 D (docs/specs/43-party-measured.md §4.2, Tests → D): the night proposes taking a checker out of a goal's party when
its newest eight checks all ended clean in round 1; `ideas.party_answer`; Needs you's `party` row. Code, no model."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, goal_team, goal_verdict, ideas, party_proposals
from tests.test_idea_night import keeper  # noqa: F401  (the keeper fixture)
from tests.test_party_work import _check, _idea, _party


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def _quiet(root, state, goal, n=8, by="reviewer", start=0, round=1, price=0.4):
    base = dt.datetime.now() - dt.timedelta(hours=2)
    for k in range(start, start + n):
        at = (base + dt.timedelta(minutes=k)).isoformat(timespec="seconds")
        _idea(root, state, goal, f"Idea {by} {k}", [_check(f"{by[:3]}{k}", [], round, by, finished=at)], lines=[(f"{by[:3]}{k}", price)])


def _keeper(host):
    return host.ideas.keeper


def _row(host):
    return next((n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "party"), None)


def test_eight_clean_checks_propose_taking_the_checker_out(host):
    root, state, goal = _party(host, every=("reviewer",))
    _quiet(root, state, goal)
    assert party_proposals.night(root, state) == [(goal, "reviewer", 8)]
    got = party_proposals.proposal(state, goal)
    assert got["by"] == "reviewer" and got["runs"] == 8 and got["usd"] == 0.4 and got["at"]
    assert (state / "goals" / goal / "party-proposal.json").is_file()
    assert party_proposals.night(root, state) == []                                                  # one waiting per goal


def test_a_catch_a_send_back_seven_or_a_met_goal_do_not_propose(host):
    root, state, goal = _party(host)
    _quiet(root, state, goal, 7)
    assert party_proposals.night(root, state) == []                                                  # seven
    _quiet(root, state, goal, 1, start=7, round=2)                                                    # the eighth was sent back once
    assert party_proposals.night(root, state) == []
    other = ideas.save_goal(root, None, "Search", "About search", None, "normal")[0]
    goal_team.set_team(root, other, ["reviewer"], [], "taskmaster")
    base = dt.datetime.now() - dt.timedelta(hours=2)
    for k in range(8):
        at = (base + dt.timedelta(minutes=k)).isoformat(timespec="seconds")
        found = [{"where": "a:1", "what": "x", "fixed": True}] if k == 3 else []
        _idea(root, state, other, f"Search {k}", [_check(f"s{k}", found, 1, finished=at)])
    assert party_proposals.night(root, state) == []                                                  # one caught
    third = ideas.save_goal(root, None, "Mail", "About mail", None, "normal")[0]
    goal_team.set_team(root, third, ["reviewer"], [], "taskmaster")
    _quiet(root, state, third)
    goal_verdict.save(state, third, {"met": True, "verdict": "ok"}, by="x")
    assert party_proposals.night(root, state) == []                                                  # a met goal


def test_a_decline_holds_until_a_newer_run_of_eight(host):
    root, state, goal = _party(host)
    _quiet(root, state, goal)
    party_proposals.night(root, state)
    party_proposals.decline(state, goal, "reviewer", "keep it")
    party_proposals.remove(state, goal)
    assert party_proposals.declines(state, goal)[0]["reason"] == "keep it"
    assert party_proposals.night(root, state) == []
    base = dt.datetime.now() + dt.timedelta(minutes=5)
    for k in range(8):
        at = (base + dt.timedelta(minutes=k)).isoformat(timespec="seconds")
        _idea(root, state, goal, f"Later {k}", [_check(f"l{k}", [], 1, finished=at)])
    assert party_proposals.night(root, state) == [(goal, "reviewer", 8)]


def test_the_night_has_the_step_and_logs_it(keeper):  # noqa: F811
    root, state = keeper.root, keeper.state
    goal = ideas.save_goal(root, None, "Billing", "About billing", None, "normal")[0]
    from orkboard.realm import library
    library.install(state, ["reviewer"])
    goal_team.set_team(root, goal, ["reviewer"], [], "taskmaster")
    _quiet(root, state, goal)
    keeper.run_night()
    (ev,) = [r for r in event_log.read(keeper.repo_root) if r["event"] == "party_proposed"]
    assert (ev["goal"], ev["by"], ev["runs"]) == (goal, "reviewer", 8)
    assert party_proposals.proposal(state, goal)["by"] == "reviewer"
    assert keeper.run_night() is not None and len([r for r in event_log.read(keeper.repo_root) if r["event"] == "party_proposed"]) == 1


def test_needs_you_has_a_party_row_sorted_last_and_not_counted(host):
    root, state, goal = _party(host)
    _quiet(root, state, goal)
    party_proposals.night(root, state)
    board = host.command("ideas.board")
    row = _row(host)
    assert row["title"] == "Take Reviewer out of Billing's party?" and row["by"] == "reviewer" and row["goal"] == goal
    assert row["text"] == "It found nothing in the last 8 ideas; a check costs about $0.40." and row["blocks"] is False
    assert board["needs_you"][-1]["kind"] == "party"
    assert host.ideas.snapshot()["needs_you"] == 0                                                   # never counted in the signal


def test_a_party_changed_since_drops_its_proposal(host):
    root, state, goal = _party(host)
    _quiet(root, state, goal)
    party_proposals.night(root, state)
    goal_team.set_team(root, goal, ["tester"], [], "product-manager")
    assert _row(host) is None and party_proposals.proposal(state, goal) is None


def test_taking_it_out_saves_the_party_without_the_checker_and_reads_nothing(host):
    root, state, goal = _party(host, every=("reviewer", "tester"))
    _quiet(root, state, goal)
    party_proposals.night(root, state)
    read = []
    host.ideas.keeper.read_goal = lambda *a, **k: read.append(a)
    assert BoardPhone.allowed(host, "ideas.party_answer", {})
    assert host.command("ideas.party_answer", {"goal": goal, "take": True}) == {"ok": True}
    assert goal_team.team_of(root, goal) == ["tester", "accessibility-reviewer"]
    assert goal_team.every_of(root, goal) == ["tester"] and goal_team.leader_of(root, goal) == "product-manager"
    assert read == [] and party_proposals.proposal(state, goal) is None and party_proposals.declines(state, goal) == []
    (ev,) = [r for r in event_log.read(host.ideas.host.repo_root) if r["event"] == "party_answered"]
    assert (ev["goal"], ev["by"], ev["take"], ev["has_reason"]) == (goal, "reviewer", True, False)
    with pytest.raises(CommandError, match="That proposal is gone"):
        host.command("ideas.party_answer", {"goal": goal, "take": True})


def test_keeping_it_is_a_decline_with_its_reason(host):
    root, state, goal = _party(host)
    _quiet(root, state, goal)
    party_proposals.night(root, state)
    host.command("ideas.party_answer", {"goal": goal, "take": False, "reason": " we need it "})
    assert "reviewer" in goal_team.team_of(root, goal)
    (d,) = party_proposals.declines(state, goal)
    assert d["by"] == "reviewer" and d["reason"] == "we need it" and party_proposals.proposal(state, goal) is None
    (ev,) = [r for r in event_log.read(host.ideas.host.repo_root) if r["event"] == "party_answered"]
    assert ev["take"] is False and ev["has_reason"] is True
    json.dumps(host.command("ideas.board"))


def test_roles_and_agents_carry_a_checkers_check(host):
    root, state, goal = _party(host)
    _quiet(root, state, goal, 4)
    got = host.command("ideas.roles")
    rev = next(r for r in got["roles"] if r["slug"] == "reviewer")
    assert rev["check_week"]["checks"] == 4 and rev["check_week"]["clean"] == 4 and rev["check_week"]["usd_per_check"] == 0.4
    assert next(r for r in got["roles"] if r["slug"] == "grunt")["check_week"] is None
    agents = host.command("ideas.agents")
    assert next(b for b in agents["roles"] if b["role"] == "reviewer")["check_week"]["checks"] == 4
    assert next(b for b in agents["roles"] if b["role"] == "grunt")["check_week"] is None
