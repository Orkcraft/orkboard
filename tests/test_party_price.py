"""Spec 43 C (docs/specs/43-party-measured.md §3, Tests → C): what a party costs before it starts — a first guess with no basis, learned from
`TOO_FEW` priced ideas, `every` giving a share of 1, a check's learned share, a party with no builder taking the Grunt's cost — and
`ideas.party_price`. Code, no model."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import goal_types, idea_spend, ideas, library, party_price, plans, roles


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def task(tid, kind, role, state="merged", cost=None, **more):
    return {"id": tid, "title": tid, "brief": "b", "tier": "warrior", "kind": kind, "role": role, "after": [], "state": state, "round": 1, "note": "",
            "branch": "", "commit": "", "cost": cost, "ran_tier": "warrior", "finished": dt.datetime.now().isoformat(timespec="seconds"), **more}


def add(host, text, tasks, checks, made=0):
    root, state = host.ideas.root(), host.ideas.state_dir
    goal = next((t["slug"] for t in ideas.tracks(root, make=False) if t["slug"] != "general"), None) or ideas.add_track(root, "Billing")
    s = ideas.add_idea(root, text, goal, state)
    made_at = (dt.datetime(2026, 10, 1) + dt.timedelta(hours=made)).isoformat(timespec="seconds")
    ideas.save_plan(state, s, {"idea": s, "made_at": made_at, "passed_at": None, "todos": [], "tasks": tasks})
    ideas.set_meta(root, s, checks=json.dumps(checks))
    return s


def line(host, idea, step, role, cost, tid="", rnd=1):
    idea_spend.append(host.ideas.state_dir, idea_spend.line(step, role, "claude", "m", "warrior", "", None, cost, tid, rnd), idea=idea)


def price(host, leader="architect", team=("grunt", "tester", "reviewer"), every=(), target="balance"):
    return party_price.price(host.ideas.root(), host.ideas.state_dir, {"target": target}, leader, list(team), list(every))


def test_a_first_guess_with_no_basis_takes_the_defaults_at_the_tiers_the_target_gives(host):
    got = price(host)
    # architect (a leader of the library: elder) 1.00 × 2; 3 tasks at the Grunt's warrior 0.30 and the Tester's laborer 0.05; the Reviewer's elder 1.00 × ½
    base = 2.0 + 3 * (0.30 + 0.05) / 2 + 1.0 * 0.5
    assert got["learned"] is False and got["ideas"] == 0
    assert got["low"] == pytest.approx(base * 0.5, abs=0.006) and got["high"] == pytest.approx(base * 1.5, abs=0.006)
    assert got["checks"] == [{"by": "reviewer", "name": "Reviewer", "usd": 1.0, "share": 0.5, "every": False}]
    thrift = price(host, target="thrift")                                       # the Target shifts the tiers: the architect a warrior, the Reviewer too
    assert thrift["checks"][0]["usd"] == 0.3 and thrift["high"] < got["high"]
    json.dumps(got)


def test_every_idea_gives_a_share_of_one_and_a_party_with_no_builder_takes_the_grunt_s_cost(host):
    every = price(host, every=["reviewer"])
    assert every["checks"][0]["share"] == 1.0 and every["checks"][0]["every"] is True
    assert every["high"] - price(host)["high"] == pytest.approx(1.0 * 0.5 * 1.5, abs=0.011)           # the other half of the Reviewer's task
    no_builder = price(host, leader="product-manager", team=["reviewer"])
    assert no_builder["checks"][0]["by"] == "reviewer"
    base = 2.0 + 3 * 0.30 + 0.5                                                                       # the Grunt's warrior task
    assert no_builder["low"] == pytest.approx(base * 0.5, abs=0.006)
    alone = price(host, leader="taskmaster", team=[])
    assert alone["checks"] == [] and alone["low"] == pytest.approx((2.0 + 3 * 0.30) * 0.5, abs=0.006)


def test_learned_from_three_priced_ideas_the_steps_the_tasks_and_a_check_s_share(host):
    for n in range(3):                                                                                # 3 ideas: draft 0.4 + plan 0.6, 3 tasks at 0.5, a review at 0.2
        tasks = [task(f"k{i}", "code", "grunt", cost=0.5) for i in (1, 2, 3)] + [task("k4", "review", "reviewer", cost=0.2)]
        s = add(host, f"Idea {n}", tasks, [{"by": "reviewer", "applies": True, "why": "", **({"skipped": True} if n == 2 else {})}], made=n)
        line(host, s, "draft", "architect", 0.4)
        line(host, s, "plan", "architect", 0.6)
        for i in (1, 2, 3):
            line(host, s, "task", "grunt", 0.5, f"k{i}")
        line(host, s, "task", "reviewer", 0.2, "k4")
    got = price(host, team=("grunt", "reviewer"))
    assert got["learned"] is True and got["ideas"] == 3
    assert got["checks"] == [{"by": "reviewer", "name": "Reviewer", "usd": 0.2, "share": 0.67, "every": False}]        # 2 of 3 applied, one skipped
    base = 1.0 + 3 * 0.5 + 0.2 * (2 / 3)
    assert got["low"] == pytest.approx(base * 0.5, abs=0.006) and got["high"] == pytest.approx(base * 1.5, abs=0.006)
    every = price(host, team=("grunt", "reviewer"), every=["reviewer"])
    assert every["checks"][0]["share"] == 1.0 and every["high"] == pytest.approx((1.0 + 1.5 + 0.2) * 1.5, abs=0.006)


def test_fewer_than_three_priced_ideas_is_a_first_guess_and_an_unpriced_idea_does_not_count(host):
    guess = price(host)
    for n in range(2):
        s = add(host, f"Priced {n}", [task("k1", "code", "grunt")], [], made=n)
        line(host, s, "plan", "architect", 0.6)
    unpriced = add(host, "Unpriced", [task("k1", "code", "grunt")], [], made=5)
    line(host, unpriced, "plan", "architect", None)
    got = price(host)
    assert got["learned"] is False and got["ideas"] == 3
    assert got["low"] == guess["low"] and got["high"] == guess["high"] and got["checks"] == guess["checks"]       # the same guess, with the tasks that ended unpriced


def test_the_basis_is_the_project_s_newest_twenty_ideas_with_a_plan(host):
    for n in range(22):
        add(host, f"Idea number {n}", [task("k1", "code", "grunt")], [], made=n)
    ideas.add_idea(host.ideas.root(), "No plan", next(t["slug"] for t in ideas.tracks(host.ideas.root(), make=False) if t["slug"] != "general"), host.ideas.state_dir)
    assert price(host)["ideas"] == 20
    rows = party_price.basis(host.ideas.root(), host.ideas.state_dir)
    assert len(rows) == 20 and not any(s.endswith("-0") or s == "idea-number-0" for s, _p in rows)


def test_ideas_party_price_is_the_hosts_and_a_phones_and_checks_the_party(host):
    assert BoardPhone.allowed(host, "ideas.party_price", {})
    got = host.command("ideas.party_price", {"leader": "architect", "team": ["grunt", "tester", "reviewer"], "every": ["reviewer", "not-in-the-team"]})
    json.dumps(got)
    assert got["checks"][0]["every"] is True and got["checks"][0]["share"] == 1.0 and set(got) == {"low", "high", "learned", "ideas", "checks", "hints", "types"}
    assert host.command("ideas.party_price", {})["checks"] == []                                      # the Taskmaster alone
    for bad, why in (({"leader": "nobody"}, "No agent"), ({"team": "grunt"}, "list of agents"),
                     ({"leader": "architect", "team": ["grunt", "tester", "ui-kit", "artist"]}, "at most 3 builders"),
                     ({"leader": "grunt"}, "does not lead")):
        with pytest.raises(CommandError, match=why):
            host.command("ideas.party_price", bad)


# -- the goal types the party would be offered (spec 63 §1) --------------------------------------------------------------

def types(host, leader="", team=()):
    """`ideas.party_price`'s `types` as `[(name, missing)]`."""
    got = host.command("ideas.party_price", {"leader": leader, "team": list(team)})["types"]
    return [(t["name"], t["missing"]) for t in got]


def preset(i):
    p = next(p for p in library.PRESETS if p[0] == i)
    return p[4], [*p[5], *p[6]]


def test_the_game_party_is_offered_spec_59s_game_list_each_with_its_sign_and_nothing_missing(host):
    leader, team = preset("game")
    got = host.command("ideas.party_price", {"leader": leader, "team": team})["types"]
    json.dumps(got)
    assert [t["name"] for t in got] == ["New feature", "Fix a bug", "Clean up", "New icon", "New logo", "New mechanic", "New level", "New character", "Balance pass", "New sound"]
    assert all(set(t) == {"id", "name", "sign", "missing"} and t["missing"] == "" for t in got)
    assert got[5] == {"id": "mechanic", "name": "New mechanic", "sign": "mechanic", "missing": ""}
    assert got[-1] == {"id": "sound", "name": "New sound", "sign": "tune", "missing": ""}                  # a sign is the type's, not its id
    assert [t["id"] for t in got] == [t.id for t in goal_types.CATALOG if t.id in {g["id"] for g in got}]    # in the catalog's order


def test_the_taskmaster_alone_is_offered_new_feature_fix_a_bug_and_clean_up(host):
    assert types(host) == types(host, "taskmaster") == types(host, "taskmaster", []) == [("New feature", ""), ("Fix a bug", ""), ("Clean up", "")]
    assert host.command("ideas.party_price", {})["types"][0] == {"id": "feature", "name": "New feature", "sign": "feature", "missing": ""}


def test_a_mobile_app_team_without_the_design_system_designer_is_offered_new_screen_with_the_agent_it_needs(host):
    got = types(host, *preset("mobile-app"))
    assert [n for n, m in got if not m] == ["New feature", "Fix a bug", "Clean up", "New icon", "New logo", "Solve a pain", "New character", "Store listing", "A release"]
    assert [(n, m) for n, m in got if m] == [("New screen", "Design system designer"), ("Try an experiment", "Experimenter"), ("Write the launch", "Copywriter")]
    assert [n for n, _m in got].index("New screen") == 3                                                    # where the catalog puts it, not at the end


def test_an_agent_added_to_the_team_that_opens_a_type_adds_it_and_one_that_was_missing_stops_missing(host):
    base = types(host, "game-designer", ["grunt"])
    assert base == [("New feature", ""), ("Fix a bug", ""), ("Clean up", ""), ("New mechanic", ""), ("Balance pass", "")]
    assert types(host, "game-designer", ["grunt", "level-designer"]) == [*base[:4], ("New level", ""), base[4]]       # in the catalog's order
    lone = types(host, "product-manager", ["grunt"])
    assert ("New screen", "Design system designer") in lone and ("Try an experiment", "Experimenter") in lone
    kit = types(host, "product-manager", ["grunt", "ui-kit"])
    assert ("New screen", "") in kit and ("New screen", "Design system designer") not in kit and ("Try an experiment", "Experimenter") in kit
    lab = types(host, "product-manager", ["grunt", "ui-kit", "experimenter"])
    assert ("Try an experiment", "") in lab and ("Try an experiment", "Experimenter") not in lab and ("Write the launch", "Copywriter") in lab


def test_the_types_are_read_from_the_call_s_seats_and_nothing_is_saved_or_installed(host):
    root, state = host.ideas.root(), host.ideas.state_dir
    before = (ideas.tracks(root, make=False), roles.role(state, "level-designer"), roles.role(state, "game-designer"))
    assert [n for n, _m in types(host, *preset("game"))][5:8] == ["New mechanic", "New level", "New character"]
    assert (ideas.tracks(root, make=False), roles.role(state, "level-designer"), roles.role(state, "game-designer")) == before and before[1:] == (None, None)
    library.install(state, ["level-designer", "game-designer", "grunt", "artist", "sound-designer", "playtester"])
    assert [n for n, _m in types(host, *preset("game"))][5:8] == ["New mechanic", "New level", "New character"]       # the same once they are the project's


def test_a_refused_party_is_refused_as_before_and_its_types_are_not_asked(host, monkeypatch):
    def asked(*a, **k):
        raise AssertionError("the types of a refused party were asked")
    monkeypatch.setattr(goal_types.Party, "of", asked)
    monkeypatch.setattr(goal_types, "offered", asked)
    for bad, why in (({"leader": "nobody"}, "No agent"), ({"team": "grunt"}, "list of agents"),
                     ({"leader": "architect", "team": ["grunt", "tester", "ui-kit", "artist"]}, "at most 3 builders"),
                     ({"leader": "grunt"}, "does not lead"), ({"leader": "architect", "team": ["grunt", "product-manager"]}, "A leader leads")):
        with pytest.raises(CommandError, match=why):
            host.command("ideas.party_price", bad)


