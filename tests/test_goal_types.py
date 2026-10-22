"""Spec 52 §2.1 (docs/specs/52-goal-types.md): the goal types a party's leader deals, the agent who does a kind of work, whether
a party does it, and what a party misses for a type or a plan. Code, no model, no face."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from orkboard.realm import goal_team, goal_types, ideas, library, roles

ROOT = Path(__file__).resolve().parent.parent
A0_SIGNS = {"feature", "bug", "tidy", "screen", "picture", "logo", "target", "flask", "horn", "chart", "page"}   # spec 52 §1, orkUI 0.3.3


@pytest.fixture
def board(tmp_path):
    return tmp_path / "wiki", tmp_path / ".orkcraft"


def _party(root, state, team=(), leader="taskmaster", title="Ship"):
    slug, _new = ideas.save_goal(root, None, title, "About " + title, None, "normal")
    library.install(state, [s for s in (*team, leader) if library.get(s) is not None])
    goal_team.set_team(root, slug, list(team), leader=leader)
    return slug


def _goal(root, state, party, tasks, state_="working"):
    slug = ideas.add_idea(root, f"goal {len(ideas.ideas(root))}", party, state)
    ideas.save_state(state, slug, state=state_)
    ideas.save_plan(state, slug, {"idea": slug, "tasks": tasks, "todos": []})
    return slug


def _all():
    return [t for set_ in goal_types.TYPES.values() for t in set_]


# -- the types ------------------------------------------------------------------------------------------------

def test_every_leader_of_the_library_has_a_set_and_the_taskmasters_is_the_general_one():
    leads = [a.id for a in library.LIBRARY if a.band == "lead"]
    assert set(goal_types.TYPES) == set(leads)
    assert [t.name for t in goal_types.of("taskmaster")] == ["New feature", "Fix a bug", "Clean up"]
    assert [t.name for t in goal_types.of("product-designer")] == ["New screen", "New icon", "New logo", "New feature"]
    assert [t.name for t in goal_types.of("architect")] == ["New feature", "Fix a bug", "Restructure"]
    assert goal_types.of("someone-new") is goal_types.TYPES["taskmaster"]               # a leader with no set deals the general one


def test_ids_are_unique_in_a_set_and_the_words_fit_their_places():
    for leader, set_ in goal_types.TYPES.items():
        assert len({t.id for t in set_}) == len(set_), leader
        for t in set_:
            assert len(t.line) <= 60 and t.lens in goal_types.LENSES and len(t.asks) <= 3, t
            assert len({a.id for a in t.asks}) == len(t.asks) and goal_types.REFS not in {a.id for a in t.asks}
            assert all(len(a.label) <= 24 and len(a.hint) <= 60 for a in t.asks), t
    bug = goal_types.get("taskmaster/bug")
    assert [(a.label, a.hint) for a in bug.asks] == [("What you did", "the steps, in order"), ("What happened", "what you saw"),
                                                     ("What should have", "what you expected")]
    assert goal_types.get("architect/bug").asks == bug.asks and goal_types.get("architect/bug").plan == bug.plan     # as the Taskmaster's
    logo = goal_types.get("product-designer/logo")
    assert (logo.sign, logo.needs, logo.lens, logo.refs) == ("logo", ("art",), "text", True)
    assert goal_types.get("growth/landing").needs == ("text", "seo") and goal_types.get("growth/tagline").sign == "text"


def test_a_type_is_read_by_its_key_and_an_unknown_key_reads_none():
    assert goal_types.get("product-designer/icon").name == "New icon"
    assert goal_types.key("growth", "post") == "growth/post" and goal_types.get("growth/post").name == "A launch post"
    for bad in ("", None, "taskmaster/logo", "nobody/bug", "grunt/bug", "taskmaster", "/bug"):
        assert goal_types.get(bad) is None, bad


def test_every_sign_is_one_of_orkuis():
    have = {p.stem for p in (ROOT / "design-system" / "orkui" / "signs").glob("*.svg")}
    assert "text" in have                                                                 # spec 51's, for the tagline
    for t in _all():
        assert t.sign in have | A0_SIGNS and t.sign in goal_types.SIGNS, t                 # the eleven come with orkUI 0.3.3 (A0)


def test_every_need_is_a_known_kind_with_a_taker():
    for t in _all():
        for kind in t.needs:
            assert kind in roles.TASK_KINDS and goal_types.taker(kind, roles.DEFAULT_CRAFT), (t, kind)
    assert {k: goal_types.taker(k, "design") for k in ("art", "uikit", "text", "seo", "experiment", "query", "data")} == {
        "art": "artist", "uikit": "ui-kit", "text": "copywriter", "seo": "seo", "experiment": "experimenter",
        "query": "sql", "data": "data-engineer"}


def test_the_taker_is_of_the_leaders_craft_first_and_never_a_leader(monkeypatch):
    scribe = library.Agent("scribe", "Scribe", "design", "warrior", ("text",), "Writes a screen's words", "")
    monkeypatch.setattr(library, "LIBRARY", (*library.LIBRARY, scribe))
    assert goal_types.taker("text", "design") == "scribe" and goal_types.taker("text", "marketing") == "copywriter"
    assert goal_types.taker("text", "data") == "copywriter"                                # no one of its craft: the library's order
    assert goal_types.taker("design", "design") == goal_types.taker("metrics", "data") == ""      # a leader's kind: no one is offered


def test_a_kind_in_a_sentence():
    assert [goal_types.words(k) for k in ("art", "uikit", "text", "experiment", "seo")] == [
        "pixel art", "UI kit", "text for people", "experiments", "search (SEO)"]


# -- whether a party does it ---------------------------------------------------------------------------------

def test_met_by_a_member_the_leader_the_projects_role_or_the_grunts_own_kinds_never_by_the_grunt_filling_in(board):
    root, state = board
    library.install(state, ["artist", "product-designer"])
    assert goal_types.met(state, "art", ["artist", "taskmaster"])                        # a member who takes it
    assert goal_types.met(state, "design", ["product-designer"])                         # the leader
    assert goal_types.met(state, "code", []) and goal_types.met(state, "tests", ["taskmaster"])   # the Grunt's own
    assert not goal_types.met(state, "art", ["taskmaster"]) and not goal_types.met(state, "uikit", ["product-designer"])   # the Grunt filling in
    pixel = roles.save(state, "Pixel smith", "", 1)
    roles.set_kind(state, "art", pixel)
    assert goal_types.met(state, "art", ["taskmaster"])                                  # the project's role for it


# -- what a party misses -----------------------------------------------------------------------------------------

def test_missing_says_who_would_join_once_each_and_whether_a_seat_is_free(board):
    root, state = board
    ship = _party(root, state, ["grunt"], leader="product-designer")
    got = goal_types.missing(state, root, ship, ("uikit", "art", "uikit", "design", "code"))
    assert [(m["kind"], m["agent"], m["name"], m["band"], m["free"]) for m in got] == [
        ("uikit", "ui-kit", "Design system designer", "build", True), ("art", "artist", "Artist", "build", True)]
    assert got[0]["words"] == "UI kit" and got[1]["words"] == "pixel art" and got[1]["out"] == [{"slug": "grunt", "name": "Grunt", "runs": 0}]
    full = _party(root, state, ["grunt", "tester", "ui-kit"], leader="product-designer", title="Full")
    (art,) = goal_types.missing(state, root, full, ("art", "uikit"))
    assert art["free"] is False and [o["slug"] for o in art["out"]] == ["ui-kit", "tester", "grunt"]       # no runs: the later first
    assert goal_types.missing(state, root, full, ()) == [] and goal_types.missing(state, root, full, ("bogus",)) == []


def test_out_leaves_the_members_with_open_work_out_and_puts_the_fewest_runs_first(board, monkeypatch):
    root, state = board
    full = _party(root, state, ["grunt", "tester", "ui-kit"], leader="product-designer")
    monkeypatch.setattr(goal_types.idea_spend, "by_role", lambda state_dir, days=7: {"grunt": {"finished": 1}, "tester": {"finished": 4}, "ui-kit": {"finished": 1}})
    open_ = {"id": "k1", "title": "t", "kind": "uikit", "role": "ui-kit", "state": "running"}
    _goal(root, state, full, [open_])
    (art,) = goal_types.missing(state, root, full, ("art",))
    assert art["out"] == [{"slug": "grunt", "name": "Grunt", "runs": 1}, {"slug": "tester", "name": "Tester", "runs": 4}]
    for gone in ({"state": "merged"}, {"state": "dropped"}, {"state": "failed", "error": "dropped by you"}):
        other = _party(root, state, ["grunt", "tester", "ui-kit"], leader="product-designer", title=f"Other {len(ideas.tracks(root))}")
        _goal(root, state, other, [{**open_, **gone}])
        assert "ui-kit" in [o["slug"] for o in goal_types.missing(state, root, other, ("art",))[0]["out"]], gone
    done = _party(root, state, ["grunt", "tester", "ui-kit"], leader="product-designer", title="Done")
    _goal(root, state, done, [open_], state_="done")                                     # a goal done holds no one
    assert "ui-kit" in [o["slug"] for o in goal_types.missing(state, root, done, ("art",))[0]["out"]]
    failed = _party(root, state, ["grunt", "tester", "ui-kit"], leader="product-designer", title="Failed")
    _goal(root, state, failed, [{**open_, "state": "failed", "error": "tests failed"}])   # a failure waits: its member stays
    assert "ui-kit" not in [o["slug"] for o in goal_types.missing(state, root, failed, ("art",))[0]["out"]]


# -- a plan's missing ------------------------------------------------------------------------------------------

def test_a_plans_missing_is_the_kinds_no_one_of_the_party_does_once_each_in_its_order(board):
    root, state = board
    library.install(state, ["grunt", "product-designer"])
    tasks = [{"kind": "code"}, {"kind": "art"}, {"kind": "uikit"}, {"kind": "art"}, {"kind": "design"}, {"kind": "community"}]
    got = goal_types.of_plan(state, tasks, ["grunt", "product-designer"], "product-designer")
    assert got == [{"kind": "art", "agent": "artist"}, {"kind": "uikit", "agent": "ui-kit"}, {"kind": "community", "agent": "community"}]


def test_a_plans_missing_read_now_drops_what_a_member_added_since_does_and_a_party_with_no_team_has_none(board):
    root, state = board
    ship = _party(root, state, ["grunt"], leader="product-designer")
    missed = [{"kind": "art", "agent": "artist"}, {"kind": "uikit", "agent": "ui-kit"}, {"kind": "nope", "agent": "x"}]
    assert [(m["kind"], m["name"], m["free"]) for m in goal_types.still_missing(state, root, ship, missed)] == [
        ("art", "Artist", True), ("uikit", "Design system designer", True)]
    library.install(state, ["artist"])
    goal_team.set_team(root, ship, ["grunt", "artist"])
    assert [m["kind"] for m in goal_types.still_missing(state, root, ship, missed)] == ["uikit"]
    assert set(goal_types.still_missing(state, root, ship, missed)[0]) == {"kind", "words", "agent", "name", "band", "free"}
    alone = _party(root, state, [], leader="product-designer", title="Alone")
    assert goal_types.still_missing(state, root, alone, missed) == [] and goal_types.still_missing(state, root, ship, None) == []


def test_the_prompts_line_says_the_type_and_its_plan(board):
    root, state = board
    ship = _party(root, state)
    slug = ideas.add_idea(root, "the login breaks", ship, state)
    assert goal_types.prompt_line(state, slug) == ""
    ideas.save_state(state, slug, type="taskmaster/bug")
    assert goal_types.prompt_line(state, slug) == f"Its type: Fix a bug. {goal_types.get('taskmaster/bug').plan}\n"
    ideas.save_state(state, slug, type="taskmaster/feature")
    assert goal_types.prompt_line(state, slug) == "Its type: New feature.\n"            # no plan line: the name alone
    ideas.save_state(state, slug, type="nobody/bug")
    assert goal_types.prompt_line(state, slug) == ""
    assert json.loads((ideas.state_folder(state, slug) / "state.json").read_text())["type"] == "nobody/bug"   # kept as it was written
