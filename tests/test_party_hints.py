"""Spec 43 E (docs/specs/43-party-measured.md §5, Tests → E): `hints` — each of the four, their order, at most two, none for a party that fits —
`Check.fits`, and `ideas.party_price`'s `hints`. Code, no model."""
from __future__ import annotations

import json

import pytest

from orkboard.realm import library, party_hints
from tests.test_party_proposals import add, check, goal, host, quiet  # noqa: F401  (fixtures and helpers)

NO_CODE = "No one in the party writes code: code tasks go to this project's agent for code (the Grunt when none)."
NO_BUILDERS = "No builders: each task goes to this project's agent for its type (the Grunt when none)."


def test_the_library_says_the_crafts_a_check_usually_applies_to():
    fits = {a.id: a.check.fits for a in library.LIBRARY if a.check}
    assert fits == {"security-reviewer": ("engineering", "product", "data"), "reviewer": ("engineering", "product", "data"),
                    "accessibility-reviewer": ("design", "product", "engineering"), "data-reviewer": ("data", "engineering", "product"),
                    "editor": ("marketing", "product", "design")}


def hints(host, craft, leader, team, every=()):
    party_hints.party_work.forget()                                                                  # a record is kept for 30 s: these tests change the plans
    return party_hints.hints(host.ideas.root(), host.ideas.state_dir, craft, leader, list(team), list(every))


def test_a_party_that_fits_has_no_hint(host):
    for craft, (lead, builds, checks) in library.PARTIES.items():                      # each craft's own party
        assert hints(host, craft, lead, [*builds, *checks]) == [], craft
    assert hints(host, "", "taskmaster", []) == []                                  # the Taskmaster alone, no craft (Mixed)


def test_a_check_that_found_nothing_in_its_last_checks_is_said_from_eight_with_none_caught(host, goal):
    quiet(host, goal, 7)
    assert hints(host, "engineering", "architect", ["grunt", "reviewer"]) == []
    add(host, goal, "The eighth", [check("k1", finished=party_hints.party_work.dt.datetime.now().isoformat(timespec="seconds"))])
    assert hints(host, "engineering", "architect", ["grunt", "reviewer"]) == ["Reviewer found nothing in its last 8 checks."]
    quiet(host, goal, 4, by="reviewer")
    assert hints(host, "engineering", "architect", ["grunt", "reviewer"]) == ["Reviewer found nothing in its last 12 checks."]
    add(host, goal, "A catch", [check("k1", findings=[{"where": "x", "what": "y", "fixed": True}])])
    assert hints(host, "engineering", "architect", ["grunt", "reviewer"]) == []                       # it caught one


def test_a_check_that_seldom_applies_to_the_craft_says_when_it_checks(host):
    assert hints(host, "data", "analyst", ["data-engineer", "accessibility-reviewer"]) == [
        "Accessibility reviewer seldom checks a Data party: it checks when the idea changes what people see or use."]
    assert hints(host, "engineering", "architect", ["grunt", "editor"]) == [
        "Editor seldom checks an Engineering party: it checks when the idea adds or changes text people read."]               # an, before a vowel
    assert hints(host, "", "architect", ["grunt", "editor"]) == []                                  # a Mixed goal has no craft to leave out


def test_no_one_who_writes_code_in_an_engineering_or_product_party_and_no_builders_under_a_leader(host):
    assert hints(host, "engineering", "architect", ["tester", "reviewer"]) == [NO_CODE]               # the Tester takes tests, not code
    assert hints(host, "engineering", "architect", ["ui-kit", "reviewer"]) == [NO_CODE]
    assert hints(host, "product", "product-manager", ["copywriter", "reviewer"]) == [NO_CODE]
    assert hints(host, "design", "product-designer", ["ui-kit"]) == []                                 # a design goal needs no code
    assert hints(host, "engineering", "taskmaster", ["ui-kit"]) == [NO_CODE]                          # the Taskmaster alone does not write it
    assert hints(host, "engineering", "taskmaster", []) == [NO_CODE]
    assert hints(host, "design", "product-designer", []) == [NO_BUILDERS]
    assert hints(host, "design", "taskmaster", []) == []                                              # the Taskmaster leads with Grunts by default


def test_their_order_and_at_most_two(host):
    got = hints(host, "data", "analyst", ["accessibility-reviewer", "editor"])                       # two checks that seldom apply, and no builder
    assert len(got) == 2 and got[0].startswith("Accessibility reviewer seldom") and got[1].startswith("Editor seldom")
    got = hints(host, "engineering", "architect", ["editor"])                                         # a check that seldom applies, no code, no builder
    assert got == ["Editor seldom checks an Engineering party: it checks when the idea adds or changes text people read.", NO_CODE]


def test_a_person_s_own_agent_that_takes_code_counts(host):
    from orkboard.realm import roles
    roles.save(host.ideas.state_dir, "Scripter", "", 1, "You write scripts.", None, ["code"], "engineering")
    got = hints(host, "engineering", "architect", ["scripter", "reviewer"])
    assert got == []


def test_ideas_party_price_answers_the_hints_with_the_craft(host):
    got = host.command("ideas.party_price", {"leader": "analyst", "team": ["accessibility-reviewer"], "craft": "data"})
    json.dumps(got)
    assert got["hints"] == ["Accessibility reviewer seldom checks a Data party: it checks when the idea changes what people see or use.", NO_BUILDERS]
    assert host.command("ideas.party_price", {"leader": "analyst", "team": ["accessibility-reviewer"]})["hints"] == [NO_BUILDERS]       # no craft: no craft hint
    assert host.command("ideas.party_price", {"leader": "architect", "team": ["grunt", "tester", "reviewer"], "craft": "engineering"})["hints"] == []
    assert host.command("ideas.party_price", {"craft": "nonsense", "leader": "taskmaster", "team": ["grunt"]})["hints"] == []
