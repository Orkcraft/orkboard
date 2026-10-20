"""Spec 43 D (docs/specs/43-party-measured.md §4, Tests → D): a check's record (30 and 7 days, `usd_per_check` under `TOO_FEW` is null),
`quiet_run` and the night's step (eight clean in round 1 proposes; a catch, a send back or seven do not; a met goal does not; one waiting a
goal; a decline holds until a newer run of eight), `ideas.party_answer` (take and keep), and Needs you's `party` row, sorted last and not
counted. Code, no model."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, goal_team, goal_verdict, idea_spend, ideas, party_proposals, party_work

NOW = dt.datetime.now().replace(microsecond=0)


def at(days_ago: float = 0, hours: float = 0) -> str:
    return (NOW - dt.timedelta(days=days_ago, hours=hours)).isoformat(timespec="seconds")


def check(tid, by="reviewer", kind="review", finished=None, rnd=1, findings=(), state="merged", **more):
    return {"id": tid, "title": tid, "brief": "b", "tier": "elder", "kind": kind, "role": by, "after": [], "state": state, "round": rnd, "note": "",
            "branch": "", "commit": "", "cost": None, "finished": finished or at(), "findings": None if findings is None else list(findings), **more}


@pytest.fixture
def host(fake_repo) -> Orkboard:
    party_work.forget()
    return Orkboard(fake_repo)


@pytest.fixture
def goal(host):
    root = host.ideas.root()
    g = ideas.save_goal(root, None, "Billing", "About billing", None, "normal")[0]
    goal_team.set_team(root, g, ["grunt", "reviewer", "accessibility-reviewer"], every=["reviewer"], leader="product-manager")
    return g


def add(host, goal, text, tasks):
    root, state = host.ideas.root(), host.ideas.state_dir
    s = ideas.add_idea(root, text, goal, state)
    ideas.save_plan(state, s, {"idea": s, "made_at": at(), "passed_at": None, "todos": [], "tasks": tasks})
    return s


def quiet(host, goal, n=8, by="reviewer", kind="review", base=0.5):
    """`n` clean checks of the checker, one an idea, the oldest first (a few hours apart)."""
    return [add(host, goal, f"Idea {by} {i}", [check("k1", by, kind, finished=at(base, hours=n - i))]) for i in range(n)]


def test_check_record_over_30_and_7_days_with_the_price_from_three_checks(host, goal):
    root, state = host.ideas.root(), host.ideas.state_dir
    a = add(host, goal, "One", [check("k1", finished=at(1)), check("k2", "accessibility-reviewer", "a11y", finished=at(1), findings=[{"where": "x", "what": "y", "fixed": False}])])
    b = add(host, goal, "Two", [check("k1", finished=at(2), rnd=2), check("k2", finished=at(20), findings=[{"where": "x", "what": "y", "fixed": True}, {"where": "z", "what": "w", "fixed": False}])])
    c = add(host, goal, "Three", [check("k1", finished=at(40)), check("k2", finished=at(3), state="running"), check("k3", finished=at(3), findings=None)])    # old · running · before findings
    for slug, tid, usd in ((a, "k1", 0.4), (b, "k1", 0.2), (b, "k2", 0.3)):
        idea_spend.append(state, idea_spend.line("task", "reviewer", "claude", "m", "elder", "", None, usd, tid), idea=slug)
    month = party_work.check_record(root, state, "reviewer", 30)
    assert month == {"checks": 3, "clean": 1, "caught": 2, "left": 1, "usd_per_check": 0.3}                  # a send back catches; the old, the running and the unkept are out
    week = party_work.check_record(root, state, "reviewer", 7)
    assert week == {"checks": 2, "clean": 1, "caught": 1, "left": 0, "usd_per_check": None}                  # under TOO_FEW: no price
    assert party_work.check_record(root, state, "accessibility-reviewer", 7)["caught"] == 1
    assert party_work.check_record(root, state, "security-reviewer", 30) == {"checks": 0, "clean": 0, "caught": 0, "left": 0, "usd_per_check": None}
    assert party_work.check_record(root, state, "reviewer", 30, now=NOW + dt.timedelta(days=25))["checks"] == 2                     # the clock moves the window: 2 and 1 days ago stay, 20 goes


def test_quiet_run_is_the_newest_eight_all_clean_in_round_one(host, goal):
    root, state = host.ideas.root(), host.ideas.state_dir
    quiet(host, goal, 7)
    assert party_work.quiet_run(root, state, goal, "reviewer") is None                                       # seven are not eight
    add(host, goal, "The eighth", [check("k1", finished=at(0, hours=0.5))])
    assert party_work.quiet_run(root, state, goal, "reviewer") == at(0, hours=0.5)                          # the newest's time
    add(host, goal, "A catch", [check("k1", finished=at(0, hours=0.1), findings=[{"where": "x", "what": "y", "fixed": True}])])
    assert party_work.quiet_run(root, state, goal, "reviewer") is None                                       # the newest eight now hold a catch
    for _ in range(8):
        add(host, goal, "Again", [check("k1", finished=at(0, hours=0.01))])
    assert party_work.quiet_run(root, state, goal, "reviewer") == at(0, hours=0.01)                         # eight quiet ones after it
    other = ideas.save_goal(root, None, "Speed", "About speed", None, "normal")[0]
    assert party_work.quiet_run(root, state, other, "reviewer") is None                                      # this goal's ideas only
    add(host, goal, "A send back", [check("k1", finished=at(0, hours=0.001), rnd=2)])
    assert party_work.quiet_run(root, state, goal, "reviewer") is None                                       # round 2 is a catch
    add(host, goal, "Failed", [check("k1", finished=at(0), state="failed", findings=None)])
    assert party_work.quiet_run(root, state, goal, "reviewer") is None


def test_the_night_proposes_once_a_goal_and_a_decline_holds_until_a_newer_run_of_eight(host, goal):
    root, state = host.ideas.root(), host.ideas.state_dir
    assert party_proposals.propose(root, state) == []
    quiet(host, goal, 8)
    quiet(host, goal, 8, by="accessibility-reviewer", kind="a11y")                                         # a second quiet checker: still one proposal a goal
    got = party_proposals.propose(root, state)
    assert got == [{"goal": goal, "by": "reviewer", "runs": 8}]
    saved = json.loads((state / "goals" / goal / "party-proposal.json").read_text())
    assert saved["by"] == "reviewer" and saved["runs"] == 8 and saved["usd"] is None and saved["at"]
    assert party_proposals.propose(root, state) == []                                                      # one waiting a goal
    by = party_proposals.answer(root, state, goal, False, "I like it  there")
    assert by == "reviewer" and not (state / "goals" / goal / "party-proposal.json").exists()
    (row,) = party_proposals.declines(state, goal)
    assert row["by"] == "reviewer" and row["reason"] == "I like it there" and row["at"]
    assert goal_team.team_of(root, goal) == ["grunt", "reviewer", "accessibility-reviewer"]                 # kept as it was
    assert party_proposals.propose(root, state) == [{"goal": goal, "by": "accessibility-reviewer", "runs": 8}]      # the other checker is still quiet
    party_proposals.answer(root, state, goal, False)
    assert party_proposals.propose(root, state) == []                                                      # both declined after their runs
    for i in range(8):                                                                                     # a newer run of eight
        add(host, goal, f"Newer {i}", [check("k1", finished=(dt.datetime.now() + dt.timedelta(seconds=60 + i)).isoformat(timespec="seconds"))])
    assert party_proposals.propose(root, state) == [{"goal": goal, "by": "reviewer", "runs": 8}]


def test_a_met_goal_a_goal_without_the_checker_and_the_general_goal_are_not_proposed(host, goal):
    root, state = host.ideas.root(), host.ideas.state_dir
    quiet(host, goal, 8)
    goal_verdict.save(state, goal, {"met": True, "verdict": "Done", "metrics": [], "next": []}, "Product manager")
    assert party_proposals.propose(root, state) == []
    goal_verdict.save(state, goal, {"met": False, "verdict": "Not yet", "metrics": [], "next": []}, "Product manager")
    goal_team.set_team(root, goal, ["grunt"], leader="product-manager")                                    # the checker left the party already
    assert party_proposals.propose(root, state) == []


def test_ideas_party_answer_takes_the_checker_out_or_keeps_it_and_logs(host, goal):
    root, state = host.ideas.root(), host.ideas.state_dir
    assert BoardPhone.allowed(host, "ideas.party_answer", {})
    with pytest.raises(CommandError, match="That proposal is gone"):
        host.command("ideas.party_answer", {"goal": goal, "take": True})
    quiet(host, goal, 8)
    party_proposals.propose(root, state)
    with pytest.raises(CommandError, match="true or false"):
        host.command("ideas.party_answer", {"goal": goal})
    seen = ideas.track_page(root, goal).text()
    host.command("ideas.party_answer", {"goal": goal, "take": True})
    assert goal_team.team_of(root, goal) == ["grunt", "accessibility-reviewer"] and goal_team.every_of(root, goal) == []     # `every` loses it too
    assert goal_team.leader_of(root, goal) == "product-manager"
    assert ideas.track_page(root, goal).text() != seen and not (state / "goals" / goal / "party-proposal.json").exists()
    assert not party_proposals.declines(state, goal)
    quiet(host, goal, 8, by="accessibility-reviewer", kind="a11y")
    party_proposals.propose(root, state)
    host.command("ideas.party_answer", {"goal": goal, "take": False, "reason": "needed for the public page"})
    assert goal_team.team_of(root, goal) == ["grunt", "accessibility-reviewer"]
    assert party_proposals.declines(state, goal)[0]["reason"] == "needed for the public page"
    log = [r for r in event_log.read(host.repo_root) if r["event"] == "party_answered"]
    assert [(r["goal"], r["by"], r["take"], r["has_reason"]) for r in log] == [(goal, "reviewer", True, False), (goal, "accessibility-reviewer", False, True)]


def test_the_row_is_in_needs_you_last_and_never_counted(host, goal):
    root, state = host.ideas.root(), host.ideas.state_dir
    other = ideas.save_goal(root, None, "Speed", "About speed", None, "normal")[0]
    ideas.add_idea(root, "A waiting proposal", other, state)
    slug = ideas.ideas(root, other)[0]["slug"]
    ideas.save_state(state, slug, state="proposed")
    quiet(host, goal, 8, base=0.2)
    quiet(host, goal, 1, by="grunt", kind="code")
    party_proposals.propose(root, state)
    host.ideas.changed("")
    needs = host.command("ideas.board")["needs_you"]
    party = [n for n in needs if n["kind"] == "party"]
    assert len(party) == 1 and party[0]["goal"] == goal and party[0]["by"] == "reviewer" and party[0]["blocks"] is False
    assert party[0]["title"] == "Take Reviewer out of Billing's party?" and party[0]["text"] == "It found nothing in the last 8 ideas."
    assert party[0]["priority"] == "normal" and party[0]["at"] and party[0]["idea"] == ""
    assert {n["kind"] for n in needs[-2:]} == {"proposal", "party"}                                          # sorted last, with the proposals
    assert host.ideas.snapshot()["needs_you"] == sum(1 for n in needs if n["kind"] not in ("proposal", "party"))     # never counted in the signal
    saved = json.loads((state / "goals" / goal / "party-proposal.json").read_text())
    saved["usd"] = 0.35
    (state / "goals" / goal / "party-proposal.json").write_text(json.dumps(saved))
    assert next(n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "party")["text"] == "It found nothing in the last 8 ideas; a check costs about $0.35."
    goal_team.set_team(root, goal, ["grunt"], leader="product-manager")                                       # a checker no longer in the party has no row
    assert not [n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "party"]


def test_roles_and_agents_carry_a_checker_s_check_week_and_record(host, goal):
    root, state = host.ideas.root(), host.ideas.state_dir
    for i in range(3):
        add(host, goal, f"Checked {i}", [check("k1", finished=at(1), findings=[{"where": "x", "what": "y", "fixed": True}] if i == 0 else [])])
    from orkboard.realm import library
    library.install(state, ["reviewer", "grunt"])
    party_work.forget()
    rows = {r["slug"]: r for r in host.command("ideas.roles")["roles"]}
    assert rows["reviewer"]["check_week"] == {"checks": 3, "clean": 2, "caught": 1, "left": 0, "usd_per_check": None}
    assert rows["reviewer"]["record"]["check"]["checks"] == 3 and rows["reviewer"]["record"]["days"] == 30
    assert "check_week" not in rows["grunt"] and "check" not in (rows["grunt"]["record"] or {})
    blocks = {b["role"]: b for b in host.command("ideas.agents")["roles"]}
    assert blocks["reviewer"]["check_week"]["caught"] == 1 and "check_week" not in blocks["grunt"]


def test_the_night_runs_the_party_step_after_its_proposals(host, goal):
    quiet(host, goal, 8)
    keeper = host.ideas.keeper
    counts = {"drafted": 0, "started": 0, "refreshed": 0, "proposed": 0, "held": 0}
    published = []
    keeper.publish = published.append
    keeper._night_parties(host.ideas.root(), counts)
    assert counts == {"drafted": 0, "started": 0, "refreshed": 0, "proposed": 0, "held": 0}               # not among the ideas' proposals nor limited by them
    (row,) = [r for r in event_log.read(host.repo_root) if r["event"] == "party_proposed"]
    assert (row["goal"], row["by"], row["runs"]) == (goal, "reviewer", 8) and published == [f"goal:{goal}"]
    steps = [s.__name__ for s in (keeper._night_queue, keeper._night_starts, keeper._night_refresh, keeper._night_proposals, keeper._night_parties)]
    assert steps[-1] == "_night_parties"
