"""Spec 43 B (docs/specs/43-party-measured.md §2, Tests → B): what a goal's party did, on a fixture goal. Code, no model."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from orkboard.gui.board_host import Orkboard
from orkboard.realm import goal_team, idea_spend, ideas, library, party_work


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def _party(host, leader="product-manager", team=("tester", "reviewer", "accessibility-reviewer"), every=()):
    root, state = host.ideas.root(), host.ideas.state_dir
    goal = ideas.save_goal(root, None, "Billing", "About billing", None, "normal")[0]
    library.install(state, [leader, *team])
    goal_team.set_team(root, goal, list(team), list(every), leader)
    return root, state, goal


def _idea(root, state, goal, text, tasks, checks=None, lines=()):
    slug = ideas.add_idea(root, text, goal, state)
    page = ideas.idea_page(root, slug)
    if checks is not None:
        page.set("checks", json.dumps(checks))
        ideas._write(root / ideas.IDEAS / f"{slug}.md", page.text())
    folder = state / "ideas" / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(json.dumps({"idea": slug, "tasks": tasks}))
    for task, cost in lines:
        idea_spend.append(state, idea_spend.line("task", "grunt", "t", "m", "warrior", "", None, cost, task, 1), idea=slug)
    return slug


def _t(tid, state, kind="code", role="", round=1, **more):
    return {"id": tid, "title": tid, "state": state, "kind": kind, "round": round, **({"role": role} if role else {}), **more}


def test_a_goal_with_no_plan_has_no_work(host):
    root, state, goal = _party(host)
    ideas.add_idea(root, "Not planned", goal, state)
    got = party_work.work(root, state, goal)
    assert got["ideas"] == 0 and got["members"] == []
    assert got["leader"]["slug"] == "product-manager" and got["leader"]["usd"] is None
    assert [c["by"] for c in got["checks"]] == ["reviewer", "accessibility-reviewer"]
    assert all(c["applied"] == 0 and c["usd"] is None for c in got["checks"])


def test_members_come_in_the_partys_order_then_the_others(host):
    root, state, goal = _party(host)
    _idea(root, state, goal, "One", [_t("k1", "merged", role="grunt"), _t("k2", "merged", "tests", "tester", 2),
                                     _t("k3", "failed", "tests", "tester"), _t("k4", "running", role="grunt")],
          lines=[("k1", 1.5), ("k2", 0.25), ("k3", 0.25)])
    got = party_work.work(root, state, goal)
    assert got["ideas"] == 1
    assert [m["slug"] for m in got["members"]] == ["tester", "grunt"]                  # the goal's builder first, then the others
    tester, grunt = got["members"]
    assert (tester["tasks"], tester["merged"], tester["first_time"], tester["usd"]) == (2, 1, 0, 0.5)
    assert (grunt["tasks"], grunt["merged"], grunt["first_time"], grunt["usd"]) == (1, 1, 1, 1.5)       # a running task is not counted
    assert tester["name"] == "Tester" and set(tester["head"]) == {"craft", "race", "tier"}


def test_a_task_with_no_role_goes_to_the_role_of_its_type_and_an_unpriced_task_has_no_usd(host):
    root, state, goal = _party(host)
    _idea(root, state, goal, "One", [_t("k1", "merged")])
    (member,) = party_work.work(root, state, goal)["members"]
    assert member["slug"] == "grunt" and member["usd"] is None


def test_the_leaders_dollars_are_the_goal_spec_and_plan_stages(host):
    root, state, goal = _party(host)
    slug = _idea(root, state, goal, "One", [_t("k1", "merged", role="grunt")], lines=[("k1", 9)])
    idea_spend.append(state, idea_spend.line("goal", "product-manager", "t", "m", "elder", "", None, 1.0), goal=goal)
    idea_spend.append(state, idea_spend.line("draft", "product-manager", "t", "m", "elder", "", None, 2.0), idea=slug)
    idea_spend.append(state, idea_spend.line("plan", "product-manager", "t", "m", "elder", "", None, 1.1), idea=slug)
    assert party_work.work(root, state, goal)["leader"]["usd"] == 4.1                  # the work's $9 is not the leader's


def test_a_check_counts_applied_skipped_clean_caught_left_and_before(host):
    root, state, goal = _party(host)
    both = [{"by": "reviewer", "applies": True, "why": ""}, {"by": "accessibility-reviewer", "applies": False, "why": "No screen"}]
    skipped = [{"by": "reviewer", "applies": True, "why": "", "skipped": True}, {"by": "accessibility-reviewer", "applies": True, "why": ""}]
    _idea(root, state, goal, "Clean", [_t("k1", "merged", "review", findings=[], note="clean")], both, lines=[("k1", 0.5)])
    _idea(root, state, goal, "Found", [_t("k1", "merged", "review", findings=[{"where": "a", "what": "b", "fixed": True}])], both, lines=[("k1", 0.5)])
    _idea(root, state, goal, "Sent back", [_t("k1", "merged", "review", round=2, findings=[])], both)
    _idea(root, state, goal, "Left", [_t("k1", "review", "review", findings=[{"where": "a", "what": "b", "fixed": False},
                                                                          {"where": "c", "what": "d", "fixed": True}]),
                                      _t("k2", "merged", "a11y", findings=[], note="clean")], skipped)
    _idea(root, state, goal, "Before", [_t("k1", "merged", "review")], both)
    reviewer, a11y = party_work.work(root, state, goal)["checks"]
    assert reviewer["by"] == "reviewer" and reviewer["name"] == "Reviewer"
    assert (reviewer["applied"], reviewer["skipped"]) == (4, 1)
    assert (reviewer["clean"], reviewer["caught"], reviewer["left"], reviewer["before"]) == (1, 3, 1, 1)
    assert reviewer["usd"] == 1.0
    assert (a11y["applied"], a11y["skipped"], a11y["clean"], a11y["caught"], a11y["usd"]) == (1, 0, 1, 0, None)


def test_a_checker_outside_the_party_whose_check_ran_is_listed_after_it(host):
    root, state, goal = _party(host)
    _idea(root, state, goal, "One", [_t("k1", "merged", "security", findings=[], note="clean")])
    assert [c["by"] for c in party_work.work(root, state, goal)["checks"]] == ["reviewer", "accessibility-reviewer", "security-reviewer"]


def test_a_goal_with_no_party_is_led_by_the_taskmaster(host):
    root, state = host.ideas.root(), host.ideas.state_dir
    goal = ideas.save_goal(root, None, "Plain", "About", None, "normal")[0]
    got = party_work.work(root, state, goal)
    assert got["leader"]["slug"] == "taskmaster" and got["checks"] == [] and got["members"] == []


# -- what a check is worth (spec 43 §4.1) ---------------------------------------------------------------------------

def _check(tid, findings, round=1, by="reviewer", state="merged", finished=None):
    import datetime as dt
    when = finished or dt.datetime.now().isoformat(timespec="seconds")
    return _t(tid, state, "review", by, round, findings=findings, finished=when)


def test_a_checkers_record_is_its_checks_that_ended_with_findings_read_in_the_window(host):
    import datetime as dt
    root, state, goal = _party(host)
    other = ideas.save_goal(root, None, "Search", "About search", None, "normal")[0]
    old = (dt.datetime.now() - dt.timedelta(days=10)).isoformat(timespec="seconds")
    miss = [{"where": "a.py:1", "what": "x", "fixed": False}]
    _idea(root, state, goal, "One", [_check("c1", []), _check("c2", miss, 2, state="review"), _check("c3", [], finished=old),
                                     _t("c4", "merged", "review", "reviewer", findings=None), _check("c5", [], by="accessibility-reviewer", finished=old)],
          lines=[("c1", 0.3), ("c2", 0.3)])
    _idea(root, state, other, "Two", [_check("d1", [])], lines=[("d1", 0.6)])
    week = party_work.check_record(root, state, "reviewer", 7)
    assert week == {"checks": 3, "clean": 2, "caught": 1, "left": 1, "usd_per_check": 0.4}            # across goals, c3 and c4 left out
    assert party_work.check_record(root, state, "reviewer", 30)["checks"] == 4
    assert party_work.check_record(root, state, "accessibility-reviewer", 7)["checks"] == 0
    assert party_work.check_record(root, state, "accessibility-reviewer", 30) == {"checks": 1, "clean": 1, "caught": 0, "left": 0, "usd_per_check": None}


def test_the_price_of_a_check_is_said_from_too_few_checks_on(host):
    root, state, goal = _party(host)
    _idea(root, state, goal, "One", [_check("c1", []), _check("c2", [])], lines=[("c1", 0.2), ("c2", 0.4)])
    assert party_work.check_record(root, state, "reviewer", 30)["usd_per_check"] is None             # two checks: too few
    _idea(root, state, goal, "Two", [_check("c3", [])], lines=[("c3", 0.3)])
    assert party_work.check_record(root, state, "reviewer", 30)["usd_per_check"] == 0.3


def test_a_quiet_run_is_eight_checks_in_a_row_that_ended_clean_in_round_one(host):
    import datetime as dt
    root, state, goal = _party(host)
    base = dt.datetime.now() - dt.timedelta(hours=1)
    at = lambda n: (base + dt.timedelta(minutes=n)).isoformat(timespec="seconds")                    # noqa: E731
    for n in range(7):
        _idea(root, state, goal, f"Idea {n}", [_check(f"c{n}", [], finished=at(n))], lines=[(f"c{n}", 0.3)])
    assert party_work.quiet_run(root, state, goal, "reviewer") is None                               # seven
    _idea(root, state, goal, "Idea 7", [_check("c7", [], finished=at(7))], lines=[("c7", 0.5)])
    assert party_work.quiet_run(root, state, goal, "reviewer") == {"at": at(7), "usd": 0.33}
    assert party_work.quiet_run(root, state, goal, "accessibility-reviewer") is None
    _idea(root, state, goal, "Idea 8", [_check("c8", [], 2, finished=at(8))])                        # sent back once: not quiet
    assert party_work.quiet_run(root, state, goal, "reviewer") is None
    for n in range(9, 17):
        _idea(root, state, goal, f"Idea {n}", [_check(f"c{n}", [], finished=at(n))])
    assert party_work.quiet_run(root, state, goal, "reviewer")["at"] == at(16)                       # the newest eight again
