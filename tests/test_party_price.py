"""Spec 43 C (docs/specs/43-party-measured.md §3, Tests → C): about what an idea costs with a party, on a fixture project. Code, no model."""
from __future__ import annotations

import json

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import idea_spend, ideas, library, party_price, plans


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def _goal(host):
    root, state = host.ideas.root(), host.ideas.state_dir
    return root, state, ideas.save_goal(root, None, "Billing", "About billing", None, "normal")[0]


def _idea(root, state, goal, text, tasks, checks=None, lines=()):
    slug = ideas.add_idea(root, text, goal, state)
    page = ideas.idea_page(root, slug)
    if checks is not None:
        page.set("checks", json.dumps(checks))
        ideas._write(root / ideas.IDEAS / f"{slug}.md", page.text())
    folder = state / "ideas" / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(json.dumps({"idea": slug, "tasks": tasks}))
    for step, cost, task in lines:
        idea_spend.append(state, idea_spend.line(step, "grunt", "t", "m", "warrior", "", None, cost, task, 1), idea=slug)
    return slug


def _t(tid, kind="code"):
    return {"id": tid, "title": tid, "state": "merged", "kind": kind, "round": 1}


def _learned(root, state, goal, n=3, applies=(True, True, False)):
    for i in range(n):
        _idea(root, state, goal, f"Idea {i}", [_t("k1"), _t("k2"), _t("k3", "review")],
              [{"by": "reviewer", "applies": True, "why": "", "skipped": not applies[i % len(applies)]}],
              lines=[("draft", 1.0, ""), ("plan", 0.5, ""), ("task", 0.1, "k1")])


def test_with_no_basis_it_is_a_first_guess_at_the_tiers_the_target_gives(host):
    root, state, _goal_ = _goal(host)
    got = party_price.price(root, state, {}, "product-manager", ["tester", "reviewer"], [])
    base = plans.DEFAULT_COST["elder"] * 2 + 3 * plans.DEFAULT_COST["laborer"] + plans.DEFAULT_COST["elder"] * 0.5
    assert got["learned"] is False and got["ideas"] == 0
    assert got["low"] == pytest.approx(base * 0.5, abs=0.01) and got["high"] == pytest.approx(base * 1.5, abs=0.01)
    assert got["checks"] == [{"by": "reviewer", "name": "Reviewer", "usd": 1.0, "share": 0.5, "every": False}]


def test_the_targets_tier_moves_the_leaders_steps(host):
    root, state, _g = _goal(host)
    thrift = party_price.price(root, state, {"target": "thrift"}, "taskmaster", [], [])
    quality = party_price.price(root, state, {"target": "quality"}, "taskmaster", [], [])
    assert thrift["high"] < quality["high"]


def test_every_gives_a_share_of_one_and_a_party_with_no_builder_takes_the_grunts_cost(host):
    root, state, _g = _goal(host)
    some = party_price.price(root, state, {}, "taskmaster", ["reviewer"], [])
    every = party_price.price(root, state, {}, "taskmaster", ["reviewer"], ["reviewer"])
    assert every["checks"][0]["share"] == 1.0 and every["checks"][0]["every"] is True and some["checks"][0]["share"] == 0.5
    assert every["high"] - some["high"] == pytest.approx(1.0 * 0.5 * 1.5, abs=0.02)             # half a check more, ×1.5
    base = plans.DEFAULT_COST["elder"] * 2 + 3 * plans.DEFAULT_COST["warrior"]                 # the Grunt's task: a seasoned one
    assert party_price.price(root, state, {}, "taskmaster", [], [])["high"] == pytest.approx(base * 1.5, abs=0.01)


def test_a_party_below_a_dollar_keeps_cents_and_low_is_half_high_is_one_and_a_half(host):
    root, state, _g = _goal(host)
    got = party_price.price(root, state, {"target": "thrift"}, "taskmaster", ["tester"], [])
    assert got["high"] == pytest.approx(got["low"] * 3, abs=0.02)


def test_too_few_priced_ideas_is_still_a_first_guess(host):
    root, state, goal = _goal(host)
    _learned(root, state, goal, n=2)
    got = party_price.price(root, state, {}, "product-manager", ["tester"], [])
    assert got["learned"] is False and got["ideas"] == 2


def test_it_learns_from_the_last_priced_ideas(host):
    root, state, goal = _goal(host)
    _learned(root, state, goal)
    got = party_price.price(root, state, {}, "product-manager", ["tester", "reviewer"], [])
    assert got["learned"] is True and got["ideas"] == 3
    share = round(2 / 3, 2)                                                                     # applied and not skipped in 2 of 3
    base = 1.5 + 2 * 0.05 + 1.0 * share                                                         # steps (draft + plan), 2 tasks that are no check, the check
    assert got["checks"][0]["share"] == share and got["checks"][0]["usd"] == 1.0
    assert got["low"] == pytest.approx(base * 0.5, abs=0.02) and got["high"] == pytest.approx(base * 1.5, abs=0.02)


def test_a_checks_share_is_learned_from_at_least_three_ideas_drafted_with_it(host):
    root, state, goal = _goal(host)
    _learned(root, state, goal, n=2, applies=(True, False))
    assert party_price.price(root, state, {}, "taskmaster", ["reviewer"], [])["checks"][0]["share"] == 0.5
    _learned(root, state, goal, n=1, applies=(True,))
    assert party_price.price(root, state, {}, "taskmaster", ["reviewer"], [])["checks"][0]["share"] == round(2 / 3, 2)


def test_only_the_newest_twenty_ideas_are_the_basis(host):
    root, state, goal = _goal(host)
    _learned(root, state, goal, n=22)
    assert party_price.price(root, state, {}, "taskmaster", [], [])["ideas"] == party_price.BASIS


def test_an_agent_not_installed_yet_is_priced_at_its_library_tier(host):
    root, state, _g = _goal(host)
    tier = library.get("copywriter").tier
    got = party_price.price(root, state, {}, "taskmaster", ["copywriter"], [])
    base = plans.DEFAULT_COST["elder"] * 2 + 3 * plans.DEFAULT_COST[tier]
    assert got["checks"] == [] and got["high"] == pytest.approx(base * 1.5, abs=0.01)


def test_the_command_is_the_hosts_and_a_phones_and_needs_a_project(host):
    assert BoardPhone.allowed(Orkboard(), "ideas.party_price", {})
    with pytest.raises(CommandError, match="Open a folder first"):
        Orkboard().command("ideas.party_price", {"leader": "taskmaster", "team": [], "every": []})
    got = host.command("ideas.party_price", {"leader": "product-manager", "team": ["tester", "reviewer"], "every": ["reviewer", "seo"]})
    json.dumps(got)
    assert set(got) == {"low", "high", "learned", "ideas", "checks"} and got["checks"][0]["every"] is True       # `every` outside the team is dropped


def test_the_command_refuses_a_party_that_does_not_fit_its_seats(host):
    with pytest.raises(CommandError, match="at most"):
        host.command("ideas.party_price", {"leader": "taskmaster", "team": ["reviewer", "editor", "security-reviewer"], "every": []})
    with pytest.raises(CommandError, match="does not lead"):
        host.command("ideas.party_price", {"leader": "tester", "team": [], "every": []})
