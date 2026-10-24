"""Spec 70 A (docs/specs/70-orkmaster-and-the-project.md §1, Tests → A): the Orkmaster's deal of the parties, a goal's party by its type and the
parties' teams, `project` in `ideas.map`, `@project` in `ideas.shown`. Code, no model."""
from __future__ import annotations

import pytest

from orkboard.gui.board_host import CommandError
from orkboard.realm import event_log, library, orkmaster
from tests.test_idea_route import events, flag, goal, host, party, wait_party  # noqa: F401  (`host`: the fixture of spec 68's route tests)

PRESETS = [p["id"] for p in library.presets()]


@pytest.fixture
def bare(fake_repo):
    """A project with no party but General: the Orkmaster's first deal."""
    from orkboard.gui.board_host import Orkboard
    h = Orkboard(fake_repo)
    h.root, h.state = h.ideas.root(), h.ideas.state_dir
    return h


def rows(deal):
    return [(r["id"], r["why"], r["n"]) for r in deal]


def test_the_orkmaster_is_an_elder_ork():
    assert orkmaster.ORKMASTER == {"id": "orkmaster", "name": "Orkmaster", "race": "peon", "tier": "elder"}


def test_a_project_with_no_party_is_dealt_ideation_then_the_library_and_release_is_not_first_without_flags(bare):
    got = orkmaster.deal(bare.root, bare.state)
    assert [r["id"] for r in got] == ["ideation", *[i for i in PRESETS if i != "ideation"]] and len(got) == len(PRESETS)
    assert got[0] == {"id": "ideation", "why": "no_pitches", "n": 0}
    assert all(r["why"] == "" and r["n"] == 0 for r in got[1:])


def test_flags_and_no_release_party_deal_release_first_with_their_count(host):
    h = host
    for n, party_slug in enumerate((h.app, h.app, h.web)):
        flag(h, goal(h, party_slug, f"Goal {n}"))
    flag(h, goal(h, h.talk, "A pitch's flag"))                                         # Ideation's flags are left out
    got = orkmaster.deal(h.root, h.state)
    assert rows(got)[:2] == [("release", "flags_wait", 3), ("game", "", 0)] and got[-1] == {"id": "ideation", "why": "have", "n": 0}
    assert sorted(r["id"] for r in got) == sorted(PRESETS)                             # every preset once


def test_a_release_party_and_an_ideation_party_are_dealt_last_as_have(host):
    h = host
    party(h, "Release", "release")
    flag(h, goal(h, h.app, "Flagged"))
    got = orkmaster.deal(h.root, h.state)
    assert rows(got)[-2:] == [("release", "have", 0), ("ideation", "have", 0)]
    assert [r["id"] for r in got[:-2]] == [i for i in PRESETS if i not in ("release", "ideation")]


def test_a_goal_type_goes_to_the_party_that_takes_it_whole_then_the_party_that_misses_someone_then_none(host):
    h = host
    got = orkmaster.party_for(h.state, h.root, "logo")
    assert got[0] == {"party": h.app, "name": "Mobile app", "fits": "whole", "missing": []}
    assert [r["fits"] for r in got] == ["whole", "none", "none"] and got[-1]["party"] == h.talk      # Ideation: none, always
    design = h.command("ideas.goal_save", {"title": "Design", "about": "Screens.", "craft": "design", "leader": "product-designer",
                                           "team": ["artist", "accessibility-reviewer"]})["slug"]
    wait_party(h, design)
    got = orkmaster.party_for(h.state, h.root, "logo")
    assert [(r["party"], r["fits"]) for r in got] == [(h.app, "whole"), (design, "whole"), (h.web, "none"), (h.talk, "none")]
    got = orkmaster.party_for(h.state, h.root, "screen")                                 # the designer designs, nobody there builds the kit
    by = {r["party"]: r for r in got}
    assert by[design]["fits"] == "missing" and by[design]["missing"] == [{"agent": "ui-kit", "name": "Design system designer"}]
    assert [r["fits"] for r in got] == sorted((r["fits"] for r in got), key=("whole", "missing", "none").index) and got[-1]["party"] == h.talk
    assert h.command("ideas.party_for", {"type": "screen"}) == {"parties": got, "suggested": next(r["party"] for r in got if r["fits"] != "none")}


def test_the_first_party_that_misses_someone_is_suggested_when_none_takes_it_whole_and_the_first_when_none_does(host):
    h = host
    design = h.command("ideas.goal_save", {"title": "Design", "about": "Screens.", "craft": "design", "leader": "product-designer",
                                           "team": ["ui-kit", "accessibility-reviewer"]})["slug"]
    wait_party(h, design)
    assert orkmaster.suggested([{"party": "a", "fits": "none"}, {"party": "b", "fits": "missing"}, {"party": "c", "fits": "none"}]) == "b"
    assert orkmaster.suggested([{"party": "a", "fits": "none"}, {"party": "b", "fits": "none"}]) == "a"
    assert orkmaster.suggested([]) == ""
    assert h.command("ideas.party_for", {"type": "logo"})["parties"][0]["party"] in (h.app, design)


def test_without_a_type_every_party_fits_nothing_in_particular_and_ideation_is_last_as_a_pitch(host):
    h = host
    got = host.command("ideas.party_for", {})
    assert [(r["party"], r["fits"], r["missing"]) for r in got["parties"]] == [(h.app, "", []), (h.web, "", []), (h.talk, "pitch", [])]
    assert got["suggested"] == h.app
    assert host.command("ideas.party_for", {"type": ""}) == got


def test_party_for_leaves_general_out_and_is_refused_for_a_type_the_catalog_lacks(host):
    h = host
    assert "general" not in [r["party"] for r in h.command("ideas.party_for", {"type": "bug"})["parties"]]
    with pytest.raises(CommandError, match="No goal type 'nope'"):
        h.command("ideas.party_for", {"type": "nope"})


def test_party_for_writes_nothing(host):
    h = host
    before = sorted((p, p.stat().st_mtime_ns) for p in list(h.root.rglob("*")) + list(h.state.rglob("*")) if p.is_file())
    h.command("ideas.party_for", {"type": "logo"})
    h.command("ideas.map", {})
    assert before == sorted((p, p.stat().st_mtime_ns) for p in list(h.root.rglob("*")) + list(h.state.rglob("*")) if p.is_file())


def test_the_map_carries_the_project_counted_from_the_flags_it_read(host):
    h = host
    got = h.command("ideas.map", {})["project"]
    assert got["orkmaster"] == orkmaster.ORKMASTER and rows(got["deal"])[0] == ("game", "", 0) and got["deal"][-1]["why"] == "have"
    flag(h, goal(h, h.app, "One"))
    flag(h, goal(h, h.web, "Two"))
    got = h.command("ideas.map", {})["project"]
    assert rows(got["deal"])[0] == ("release", "flags_wait", 2)
    assert got["deal"] == orkmaster.deal(h.root, h.state)                               # as the realm counts it
    assert h.command("ideas.map", {"goal": h.app})["project"]["deal"] == got["deal"]    # the project's, whatever party the Map is of


def test_shown_takes_the_project_as_a_party_and_as_where_from(host):
    h = host
    assert h.command("ideas.shown", {"party": "@project", "from": h.app}) == {"ok": True}
    assert h.command("ideas.shown", {"party": h.web, "from": "@project", "device": "phone"}) == {"ok": True}
    h.command("ideas.shown", {"party": "@project", "from": "@project"})                  # the same: nothing
    h.command("ideas.shown", {"party": "@project"})                                      # a first read: nothing
    with pytest.raises(CommandError, match="That party is gone"):
        h.command("ideas.shown", {"party": "nowhere", "from": "@project"})
    shown = events(h, "party_shown")
    assert [(r["from"], r["to"]) for r in shown] == [(h.app, "@project"), ("@project", h.web)] and event_log.PARTY_SHOWN == "party_shown"
