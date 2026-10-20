"""Spec 43 E (docs/specs/43-party-measured.md §5, Tests → E): the hints while a party is picked, and `ideas.party_price`'s `hints`. Code, no model."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from orkboard.gui.board_host import Orkboard
from orkboard.realm import ideas, library, party_hints, roles


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def _checks(host, by, n, caught=0, kind=None):
    """`n` check tasks of `by` that ended (merged) in the last days, `caught` of them with a finding."""
    root, state = host.ideas.root(), host.ideas.state_dir
    goal = ideas.save_goal(root, None, "Billing", "About billing", None, "normal")[0]
    kind = kind or library.get(by).takes[0]
    now = dt.datetime.now().isoformat(timespec="seconds")
    for i in range(n):
        slug = ideas.add_idea(root, f"Idea {i}", goal, state)
        (state / "ideas" / slug).mkdir(parents=True, exist_ok=True)
        found = [{"where": "a.py", "what": "x", "fixed": True}] if i < caught else []
        task = {"id": "k1", "title": "Check", "state": "merged", "kind": kind, "role": by, "round": 1, "finished": now, "findings": found}
        (state / "ideas" / slug / "plan.json").write_text(json.dumps({"idea": slug, "tasks": [task]}))


def _hints(host, craft, leader, team, every=()):
    return party_hints.hints(host.ideas.root(), host.ideas.state_dir, craft, leader, list(team), list(every))


def test_every_check_says_the_crafts_it_fits():
    fits = {a.id: a.check.fits for a in library.LIBRARY if a.check}
    assert fits == {"security-reviewer": ("engineering", "product", "data"), "reviewer": ("engineering", "product", "data"),
                    "accessibility-reviewer": ("design", "product", "engineering"), "data-reviewer": ("data", "engineering", "product"),
                    "editor": ("marketing", "product", "design")}


def test_a_party_that_fits_has_no_hint(host):
    assert _hints(host, "engineering", "architect", ["grunt", "tester", "reviewer"]) == []
    assert _hints(host, "design", "product-designer", ["ui-kit", "accessibility-reviewer"]) == []
    assert _hints(host, "marketing", "growth", ["copywriter", "seo", "editor"]) == []


def test_a_checker_that_found_nothing_in_eight_checks_or_more_is_said(host):
    _checks(host, "reviewer", 12)
    assert _hints(host, "engineering", "architect", ["grunt", "reviewer"]) == ["Reviewer found nothing in its last 12 checks."]
    assert _hints(host, "engineering", "architect", ["grunt"]) == []                                  # not in the party: not said


def test_a_checker_that_caught_something_or_has_under_eight_checks_is_not_said(host):
    _checks(host, "reviewer", 12, caught=1)
    assert _hints(host, "engineering", "architect", ["grunt", "reviewer"]) == []


def test_seven_checks_are_too_few(host):
    _checks(host, "reviewer", 7)
    assert _hints(host, "engineering", "architect", ["grunt", "reviewer"]) == []


def test_a_checker_whose_fits_leave_out_the_crafts_goal_is_said(host):
    assert _hints(host, "data", "analyst", ["data-engineer", "accessibility-reviewer"]) == [
        "Accessibility reviewer seldom checks a Data goal: it checks when the idea changes what people see or use."]
    assert _hints(host, "engineering", "architect", ["grunt", "editor"]) == [
        "Editor seldom checks an Engineering goal: it checks when the idea adds or changes text people read."]
    assert _hints(host, "", "architect", ["grunt", "editor"]) == []                                   # no craft known: nothing to say


def test_an_engineering_or_product_goal_with_no_one_who_writes_code_is_said(host):
    line = "No one in the party writes code: code tasks go to this project's agent for code (the Grunt when none)."
    assert _hints(host, "engineering", "architect", ["tester", "reviewer"]) == [line]
    assert _hints(host, "product", "product-manager", ["copywriter"]) == [line]
    assert _hints(host, "engineering", "architect", ["grunt"]) == []
    assert _hints(host, "engineering", "taskmaster", []) == []                                        # the Taskmaster takes code
    assert _hints(host, "design", "product-designer", ["ui-kit"]) == []                               # a design goal needs no code


def test_an_agent_of_the_persons_own_that_takes_code_counts(host):
    roles.save(host.ideas.state_dir, "Coder", "warrior", 1, "Writes code.", takes=["code"])
    assert _hints(host, "engineering", "architect", ["coder"]) == []


def test_a_leader_other_than_the_taskmaster_with_no_builder_is_said(host):
    line = "No builders: each task goes to this project's agent for its type (the Grunt when none)."
    assert _hints(host, "design", "product-designer", ["accessibility-reviewer"]) == [line]
    assert _hints(host, "design", "taskmaster", ["accessibility-reviewer"]) == []
    assert _hints(host, "design", "product-designer", ["ui-kit"]) == []


def test_at_most_two_in_the_specs_order(host):
    _checks(host, "reviewer", 9)
    got = _hints(host, "data", "architect", ["editor", "reviewer", "accessibility-reviewer"])
    assert got == ["Reviewer found nothing in its last 9 checks.",
                   "Editor seldom checks a Data goal: it checks when the idea adds or changes text people read."]
    assert len(_hints(host, "data", "architect", ["editor", "accessibility-reviewer"])) == 2


def test_party_price_answers_hints_for_the_craft_it_is_asked(host):
    got = host.command("ideas.party_price", {"leader": "analyst", "team": ["accessibility-reviewer"], "every": [], "craft": "data"})
    assert got["hints"][0].startswith("Accessibility reviewer seldom checks a Data goal")
    assert "low" in got and got["checks"][0]["by"] == "accessibility-reviewer"


def test_party_price_with_no_craft_or_a_bad_one_has_no_craft_hint_and_still_answers(host):
    for craft in ({}, {"craft": "wizardry"}):
        got = host.command("ideas.party_price", {"leader": "analyst", "team": ["accessibility-reviewer"], "every": [], **craft})
        assert got["hints"] == ["No builders: each task goes to this project's agent for its type (the Grunt when none)."]
    assert host.command("ideas.party_price", {})["hints"] == []
