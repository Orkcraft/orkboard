"""Spec 43 B (docs/specs/43-party-measured.md §2, Tests → B): what a goal's party did, on a fixture goal with plans, findings and ledgers;
and `ideas.party`. Code, no model."""
from __future__ import annotations

import json

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import goal_team, idea_spend, ideas, party_work


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def task(tid, kind, role, state="merged", rnd=1, **more):
    return {"id": tid, "title": tid, "brief": "b", "tier": "warrior", "kind": kind, "role": role, "after": [], "state": state, "round": rnd, "note": "",
            "branch": "", "commit": "", "cost": None, **more}


def spend(state, idea, step, role, cost, tid="", rnd=1):
    idea_spend.append(state, idea_spend.line(step, role, "claude", "m", "warrior", "", None, cost, tid, rnd), idea=idea)


def idea_with(host, goal, text, tasks, checks, slug=None):
    root, state = host.ideas.root(), host.ideas.state_dir
    s = ideas.add_idea(root, text, goal, state)
    if tasks is not None:
        ideas.save_plan(state, s, {"idea": s, "made_at": "x", "passed_at": None, "todos": [], "tasks": tasks})
    ideas.set_meta(root, s, checks=json.dumps(checks))
    return s


@pytest.fixture
def goal(host):
    root = host.ideas.root()
    g = ideas.save_goal(root, None, "Billing", "About billing", None, "normal")[0]
    goal_team.set_team(root, g, ["tester", "reviewer", "accessibility-reviewer"], every=[], leader="product-manager")
    return g


def build(host, goal):
    """Two ideas with a plan and one without; the ledgers hold the $."""
    state = host.ideas.state_dir
    both = [{"by": "reviewer", "applies": True, "why": ""}, {"by": "accessibility-reviewer", "applies": True, "why": ""}]
    one = idea_with(host, goal, "First idea", [
        task("k1", "code", "grunt"), task("k2", "tests", "tester", rnd=2),
        task("k3", "review", "reviewer", findings=[], note="clean"),
        task("k4", "a11y", "accessibility-reviewer", findings=[{"where": "a.css:3", "what": "contrast", "fixed": True},
                                                                 {"where": "b.css:1", "what": "tap size", "fixed": False}])], both)
    two = idea_with(host, goal, "Second idea", [
        task("k1", "code", "grunt", state="failed"), task("k2", "review", "reviewer", rnd=2, findings=[], note="clean"),
        task("k3", "a11y", "accessibility-reviewer")],                                                     # a11y: before findings were kept
        [{"by": "reviewer", "applies": True, "why": ""}, {"by": "accessibility-reviewer", "applies": True, "why": "", "skipped": True}])
    three = idea_with(host, goal, "Third idea", None, both)                                                 # no plan: not counted
    spend(state, one, "task", "grunt", 0.5, "k1")
    spend(state, one, "task", "tester", 0.2, "k2")
    spend(state, one, "fix", "tester", 0.1, "k2", 2)
    spend(state, one, "task", "reviewer", 0.2, "k3")
    spend(state, one, "task", "accessibility-reviewer", 0.4, "k4")
    spend(state, two, "task", "grunt", 0.25, "k1")
    spend(state, two, "task", "reviewer", 0.3, "k2")
    spend(state, one, "draft", "product-manager", 0.2)
    spend(state, one, "plan", "product-manager", 0.3)
    idea_spend.append(state, idea_spend.line("goal", "product-manager", "claude", "m", "elder", "", None, 0.1), goal=goal)
    return one, two, three


def test_the_party_s_work_member_by_member_and_check_by_check(host, goal):
    build(host, goal)
    got = party_work.work(host.ideas.root(), host.ideas.state_dir, goal)
    json.dumps(got)
    assert got["ideas"] == 2
    assert (got["leader"]["slug"], got["leader"]["name"], got["leader"]["usd"]) == ("product-manager", "Product manager", 0.6)   # the goal, spec and plan steps
    assert set(got["leader"]["head"]) == {"craft", "race", "tier"}
    assert [(m["slug"], m["tasks"], m["merged"], m["first_time"], m["usd"]) for m in got["members"]] == [
        ("tester", 1, 1, 0, 0.3),                                   # the party's builders first (round 2: not the first time) …
        ("grunt", 2, 1, 1, 0.75)]                                   # … then the project's agent for the type
    rows = {c["by"]: c for c in got["checks"]}
    assert list(rows) == ["reviewer", "accessibility-reviewer"]    # the party's checkers, in its order
    r, a = rows["reviewer"], rows["accessibility-reviewer"]
    assert (r["applied"], r["skipped"], r["clean"], r["caught"], r["left"], r["before"], r["usd"]) == (2, 0, 1, 1, 0, 0, 0.5)   # a send back catches
    assert (a["applied"], a["skipped"], a["clean"], a["caught"], a["left"], a["before"], a["usd"]) == (1, 1, 0, 1, 1, 1, 0.4)
    assert r["name"] == "Reviewer" and set(r["head"]) == {"craft", "race", "tier"} and "slug" not in r


def test_a_goal_with_no_plan_says_so_and_nothing_is_priced_that_was_not(host, goal):
    got = party_work.work(host.ideas.root(), host.ideas.state_dir, goal)
    assert got["ideas"] == 0 and got["members"] == [] and got["leader"]["usd"] is None
    assert [(c["by"], c["applied"], c["clean"], c["caught"], c["before"], c["usd"]) for c in got["checks"]] == [
        ("reviewer", 0, 0, 0, 0, None), ("accessibility-reviewer", 0, 0, 0, 0, None)]
    one, _two, _three = build(host, goal)
    state = host.ideas.state_dir                                                                  # the idea's ledger holds unpriced lines only
    (state / "ideas" / one / idea_spend.FILE).write_text("\n".join(json.dumps(idea_spend.line("task", "grunt", "claude", "m", "warrior", "", None, None, "k1")) for _ in range(2)))
    got = party_work.work(host.ideas.root(), state, goal)
    assert next(m for m in got["members"] if m["slug"] == "grunt")["usd"] == 0.25               # only the priced part of the goal's ledger sums
    assert next(m for m in got["members"] if m["slug"] == "tester")["usd"] is None                # nothing priced: null, never 0


def test_a_checker_that_ran_and_is_not_in_the_party_is_listed_after_the_party_s_and_a_leader_alone_has_no_builders(host):
    root, state = host.ideas.root(), host.ideas.state_dir
    g = ideas.save_goal(root, None, "Speed", "About speed", None, "normal")[0]
    goal_team.set_team(root, g, ["reviewer"], every=["reviewer"], leader="architect")
    idea_with(host, g, "Fast", [task("k1", "code", "grunt"), task("k2", "security", "security-reviewer", findings=[]), task("k3", "review", "reviewer", state="review",
              findings=[{"where": "x", "what": "y", "fixed": False}])], [{"by": "reviewer", "applies": True, "why": ""}])
    got = party_work.work(root, state, g)
    assert [m["slug"] for m in got["members"]] == ["grunt"] and got["leader"]["slug"] == "architect"
    rows = {c["by"]: c for c in got["checks"]}
    assert list(rows) == ["reviewer", "security-reviewer"]
    assert (rows["reviewer"]["caught"], rows["reviewer"]["left"], rows["reviewer"]["applied"]) == (1, 1, 1)           # waiting at Review: it caught
    assert (rows["security-reviewer"]["clean"], rows["security-reviewer"]["applied"]) == (1, 0)                   # ran, though it is not in the party


def test_ideas_party_is_the_hosts_and_a_phones_and_needs_a_goal(host, goal):
    assert BoardPhone.allowed(host, "ideas.party", {"goal": goal})
    build(host, goal)
    got = host.command("ideas.party", {"goal": goal})
    json.dumps(got)
    assert got["ideas"] == 2 and [m["slug"] for m in got["members"]] == ["tester", "grunt"]
    with pytest.raises(CommandError, match="That party is gone"):
        host.command("ideas.party", {"goal": "nope"})
    with pytest.raises(CommandError):
        host.command("ideas.party", {})
    host.command("ideas.log", {"event": "opened", "what": "party", "ref": goal, "device": "desktop"})
