"""Spec 42 A (docs/specs/42-coming-back.md §1.2, Tests → A): `ideas.recap` on the host and the phone, and `opened`'s new
`what` and `via`."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, ideas


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def _ms(hours_ago: float) -> int:
    return int((time.time() - hours_ago * 3600) * 1000)


def _merge(host, hours_ago: float) -> str:
    root, state = host.ideas.root(), host.ideas.state_dir
    goal, _new = ideas.save_goal(root, None, "Offline mode", "About it", None, "normal")
    slug = ideas.add_idea(root, "Retry queue", goal, state)
    ideas.save_state(state, slug, state="done")
    event_log.record(Path(host.ideas.host.repo_root), "task_state", idea=slug, task="k1", state="merged", was="review", round=1)
    return slug


def test_the_recap_is_the_hosts_and_a_phones_and_needs_a_project():
    assert BoardPhone.allowed(Orkboard(), "ideas.recap", {})
    with pytest.raises(CommandError, match="Open a folder first"):
        Orkboard().command("ideas.recap", {"since": _ms(9)})


def test_the_answer_carries_the_period_and_what_waits(host):
    slug = _merge(host, 1)
    got = host.command("ideas.recap", {"since": _ms(9)})
    json.dumps(got)
    assert got["hours"] == 9 and got["into"] == "dev"
    assert [i["slug"] for i in got["merged"]["ideas"]] == [slug] and got["merged"]["ideas"][0]["done"] is True
    assert got["merged"]["tasks"] == 1 and got["empty"] is False and got["waits"] == {"you": 0, "review": 0}


def test_since_is_required_clamped_to_thirty_days_and_never_ahead(host):
    for bad in ({}, {"since": "yesterday"}, {"since": True}):
        with pytest.raises(CommandError, match="last look"):
            host.command("ideas.recap", bad)
    with pytest.raises(CommandError, match="`since` is ahead of now"):
        host.command("ideas.recap", {"since": _ms(-2)})
    assert host.command("ideas.recap", {"since": _ms(24 * 90)})["hours"] == 24 * 30


def test_opened_takes_the_new_what_and_via(host):
    for what in ("recap", "flag", "week", "push"):
        host.command("ideas.log", {"event": "opened", "what": what, "ref": "x"})
    for via in ("recap", "week", "flags", "push"):
        host.command("ideas.log", {"event": "opened", "what": "idea", "ref": "x", "via": via})
    with pytest.raises(CommandError, match="`what` is one of"):
        host.command("ideas.log", {"event": "opened", "what": "party"})
    rows = [r for r in event_log.read(Path(host.town.repo_root)) if r["event"] == "opened"]
    assert [r["what"] for r in rows] == ["recap", "flag", "week", "push", "idea", "idea", "idea", "idea"]
