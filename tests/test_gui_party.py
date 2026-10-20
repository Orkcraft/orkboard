"""Spec 43 B (docs/specs/43-party-measured.md §2.2, Tests → B): `ideas.party` on the host and the phone, and `opened`'s `party`."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, ideas


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def test_the_party_is_the_hosts_and_a_phones_and_needs_a_project():
    assert BoardPhone.allowed(Orkboard(), "ideas.party", {})
    with pytest.raises(CommandError, match="Open a folder first"):
        Orkboard().command("ideas.party", {"goal": "x"})


def test_the_answer_is_the_goals_work(host):
    root, state = host.ideas.root(), host.ideas.state_dir
    goal = ideas.save_goal(root, None, "Billing", "About billing", None, "normal")[0]
    slug = ideas.add_idea(root, "Invoices", goal, state)
    (state / "ideas" / slug).mkdir(parents=True, exist_ok=True)
    (state / "ideas" / slug / "plan.json").write_text(json.dumps({"idea": slug, "tasks": [{"id": "k1", "title": "T", "state": "merged", "round": 1}]}))
    got = host.command("ideas.party", {"goal": goal})
    json.dumps(got)
    assert got["ideas"] == 1 and got["leader"]["slug"] == "taskmaster"
    assert [(m["slug"], m["tasks"], m["merged"], m["first_time"]) for m in got["members"]] == [("grunt", 1, 1, 1)]


def test_a_missing_or_gone_goal_is_refused(host):
    with pytest.raises(CommandError):
        host.command("ideas.party", {})
    with pytest.raises(CommandError, match="That goal is gone"):
        host.command("ideas.party", {"goal": "nope"})


def test_opened_takes_party(host):
    host.command("ideas.log", {"event": "opened", "what": "party", "ref": "billing"})
    rows = [r for r in event_log.read(Path(host.town.repo_root)) if r["event"] == "opened"]
    assert rows[-1]["what"] == "party" and rows[-1]["ref"] == "billing"


def test_party_price_is_the_hosts_and_a_phones_and_the_answer_is_a_price(host):
    assert BoardPhone.allowed(Orkboard(), "ideas.party_price", {})
    got = host.command("ideas.party_price", {"leader": "taskmaster", "team": ["tester", "reviewer"], "every": []})
    json.dumps(got)
    assert got["learned"] is False and 0 < got["low"] < got["high"] and [c["by"] for c in got["checks"]] == ["reviewer"]


def test_party_price_writes_nothing(host):
    root, state = host.ideas.root(), host.ideas.state_dir
    before = sorted(p.name for p in state.rglob("*") if p.is_file())
    thrift = host.command("ideas.party_price", {"leader": "taskmaster", "team": ["reviewer"], "every": []})
    assert thrift["checks"][0]["usd"] > 0 and sorted(p.name for p in state.rglob("*") if p.is_file()) == before


def test_party_price_with_no_arguments_is_the_taskmaster_alone_and_a_bad_team_is_refused(host):
    assert host.command("ideas.party_price", {})["checks"] == []
    with pytest.raises(CommandError, match="at most"):
        host.command("ideas.party_price", {"team": ["reviewer", "editor", "security-reviewer"]})
    with pytest.raises(CommandError, match="A team is a list"):
        host.command("ideas.party_price", {"team": "reviewer"})
