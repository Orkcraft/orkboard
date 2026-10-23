"""Spec 52 §2.1 (docs/specs/52-goal-types.md): the goal types a party's leader deals, the agent who does a kind of work, whether
a party does it, and what a party misses for a type or a plan. Code, no model, no face."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from orkboard.realm import goal_team, goal_types, ideas, library, roles

ROOT = Path(__file__).resolve().parent.parent
A0_SIGNS = {"feature", "bug", "tidy", "restructure", "screen", "picture", "logo", "target", "flask", "horn", "chart", "page", "abtest", "landing", "post", "tagline",
            "mechanic", "level", "balance", "character", "release", "store", "tune"}   # spec 56 §6 and spec 59 §1.1, orkUI 0.4.1: the twenty-three


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
    return list(goal_types.CATALOG)


def _offer(board, craft_or_preset):
    """What a party of the library's offers: [(name, [who is missing])], in the catalog's order."""
    root, state = board
    lead, build, check = (library.PARTIES[craft_or_preset] if craft_or_preset in library.PARTIES
                          else next((p[4], p[5], p[6]) for p in library.PRESETS if p[0] == craft_or_preset))
    ship = _party(root, state, [*build, *check], leader=lead)
    return [(t.name, [m["agent"] for m in rows]) for t, rows in goal_types.offered(state, root, ship)]


# -- the catalog ----------------------------------------------------------------------------------------------

def test_the_catalog_is_in_spec_59s_order_with_unique_ids_and_the_words_fit_their_places():
    assert [t.id for t in goal_types.CATALOG] == [
        "feature", "bug", "tidy", "shaped-feature", "restructure", "screen", "icon", "logo", "flow-feature", "pain", "experiment",
        "launch", "metric", "report", "abtest", "landing", "post", "tagline",
        "mechanic", "level", "character", "balance", "sound", "store", "release"]
    assert len({t.id for t in _all()}) == len(_all())
    for t in _all():
        assert len(t.line) <= 60 and t.lens in goal_types.LENSES and len(t.asks) <= 3 and t.needs, t
        assert len({a.id for a in t.asks}) == len(t.asks) and goal_types.REFS not in {a.id for a in t.asks}
        assert all(len(a.label) <= 24 and len(a.hint) <= 60 for a in t.asks), t
        assert t.over == "" or t.over in goal_types.BY_ID and goal_types.BY_ID[t.over].over == "", t
    assert {t.id: t.over for t in _all() if t.over} == {"shaped-feature": "feature", "flow-feature": "feature", "experiment": "abtest"}
    assert not hasattr(goal_types, "TYPES") and not hasattr(goal_types, "of") and not hasattr(goal_types, "GENERAL")


def test_the_types_of_spec_52_keep_their_words_and_the_new_ones_are_spec_59s():
    bug = goal_types.get("bug")
    assert [(a.label, a.hint) for a in bug.asks] == [("What you did", "the steps, in order"), ("What happened", "what you saw"),
                                                     ("What should have", "what you expected")] and bug.lens == "text"
    logo = goal_types.get("logo")
    assert (logo.sign, logo.needs, logo.lens, logo.refs) == ("logo", ("art",), "text", True)
    assert goal_types.get("landing").needs == ("text", "seo") and goal_types.get("tagline").sign == "tagline"
    assert (goal_types.get("shaped-feature").name, goal_types.get("shaped-feature").lens) == ("New feature", "code")
    assert goal_types.get("experiment").needs == ("research", "experiment")
    mechanic, sound, release = goal_types.get("mechanic"), goal_types.get("sound"), goal_types.get("release")
    assert (mechanic.name, mechanic.sign, mechanic.needs, mechanic.refs) == ("New mechanic", "mechanic", ("gamedesign",), False)
    assert [(a.label, a.hint) for a in mechanic.asks] == [("What the player does", "the verb, in one line"), ("Why it is fun", "what they get from it")]
    assert (sound.name, sound.sign, sound.needs, sound.refs) == ("New sound", "tune", ("sound",), True)       # never the media's `sound`
    assert (release.needs, release.refs, release.sign) == (("aso", "code"), False, "release")
    assert [(a.label, a.hint) for a in goal_types.get("store").asks] == [("Who it is for", ""), ("The stores", "App Store, Google Play")]
    assert {t.id: t.sign for t in _all() if t.id in ("level", "character", "balance", "store")} == {
        "level": "level", "character": "character", "balance": "balance", "store": "store"}


def test_a_type_is_read_by_its_id_and_an_old_key_by_the_one_it_was_and_anything_else_reads_none():
    assert goal_types.get("icon").name == "New icon" and goal_types.get("product-designer/icon").id == "icon"
    old = {"taskmaster/feature": "feature", "taskmaster/bug": "bug", "architect/bug": "bug", "taskmaster/tidy": "tidy",
           "architect/feature": "shaped-feature", "architect/restructure": "restructure", "product-designer/screen": "screen",
           "product-designer/icon": "icon", "product-designer/logo": "logo", "product-designer/feature": "flow-feature",
           "product-manager/pain": "pain", "product-manager/experiment": "experiment", "product-manager/launch": "launch",
           "analyst/metric": "metric", "analyst/report": "report", "analyst/abtest": "abtest", "growth/landing": "landing",
           "growth/post": "post", "growth/tagline": "tagline"}
    for key, new in old.items():
        assert goal_types.get(key).id == new, key
    for bad in ("", None, "taskmaster/logo", "nobody/bug", "grunt/bug", "taskmaster", "/bug", "architect/tidy"):
        assert goal_types.get(bad) is None, bad


def test_every_sign_is_one_of_orkuis_and_a_type_shares_its_sign_only_with_the_same_thing():
    have = {p.stem for p in (ROOT / "design-system" / "orkui" / "signs").glob("*.svg")}
    assert A0_SIGNS <= have and len(A0_SIGNS) == 23                                       # the twenty-three come with orkUI 0.4.1 (specs 56, 59)
    assert set(goal_types.SIGNS) == A0_SIGNS | {"text"}                                   # `text` stays spec 51's media tile
    assert set(goal_types.SIGNS) <= have
    for t in _all():
        assert t.sign in goal_types.SIGNS and t.sign != "text", t
    by_sign: dict[str, list[str]] = {}
    for t in _all():
        by_sign.setdefault(t.sign, []).append(t.id)
    assert {s: ids for s, ids in by_sign.items() if len(ids) > 1} == {"feature": ["feature", "shaped-feature", "flow-feature"]}
    assert set(by_sign) == A0_SIGNS                                           # every sign drawn by a type (spec 56 §1.6)


def test_every_need_is_a_known_kind_and_the_ones_with_a_taker_have_one():
    for t in _all():
        for kind in t.needs:
            assert kind in roles.TASK_KINDS, (t, kind)
    leaders = {k for a in library.LIBRARY if a.band == "lead" for k in a.takes}
    for t in _all():
        for kind in t.needs:
            assert goal_types.taker(kind, roles.DEFAULT_CRAFT) or kind in leaders, (t, kind)    # a kind only a leader takes has no one to join
    assert {k: goal_types.taker(k, "design") for k in ("art", "uikit", "text", "seo", "experiment", "query", "data", "sound", "level", "aso", "playtest")} == {
        "art": "artist", "uikit": "ui-kit", "text": "copywriter", "seo": "seo", "experiment": "experimenter",
        "query": "sql", "data": "data-engineer", "sound": "sound-designer", "level": "level-designer", "aso": "aso", "playtest": "playtester"}


# -- what a party offers --------------------------------------------------------------------------------------

def test_the_library_parties_are_offered_spec_59s_lists_with_who_each_near_one_misses(board):
    got = {c: _offer(board, c) for c in ("game", "mobile-app", "website")}
    assert [n for n, m in got["game"]] == ["New feature", "Fix a bug", "Clean up", "New icon", "New logo", "New mechanic", "New level",
                                           "New character", "Balance pass", "New sound"]
    assert all(not m for _n, m in got["game"])
    assert [n for n, m in got["mobile-app"] if not m] == ["New feature", "Fix a bug", "Clean up", "New icon", "New logo", "Solve a pain",
                                                         "New character", "Store listing", "A release"]
    assert [(n, m) for n, m in got["mobile-app"] if m] == [("New screen", ["ui-kit"]), ("Try an experiment", ["experimenter"]),
                                                           ("Write the launch", ["copywriter"])]
    assert [n for n, m in got["website"]] == ["New feature", "Fix a bug", "Clean up", "A landing page", "A launch post", "A tagline"]
    assert all(not m for _n, m in got["website"])


def test_the_parties_of_one_craft_are_offered_theirs_not_their_neighbours(board, tmp_path_factory):
    names = lambda c: [(n, m) for n, m in _offer((tmp_path_factory.mktemp(c) / "wiki", tmp_path_factory.mktemp(c) / ".orkcraft"), c)]
    assert sorted(n for n, _m in names("engineering")) == sorted(["New feature", "Fix a bug", "Clean up", "Restructure"])   # the Architect's New feature, once
    design = names("design")
    assert sorted(n for n, _m in design) == sorted(["New screen", "New icon", "New logo", "New feature", "New character"]) and not any(m for _n, m in design)
    assert names("data") == [("A new metric", []), ("A report", []), ("An A/B test", ["experimenter"])]
    assert [n for n, _m in names("marketing")] == ["A landing page", "A launch post", "A tagline"]
    product = names("product")
    assert [n for n, m in product if not m] == ["New feature", "Fix a bug", "Clean up", "Solve a pain", "Write the launch", "A tagline"]
    assert [(n, m) for n, m in product if m] == [("New screen", ["ui-kit"]), ("Try an experiment", ["experimenter"])]
    assert names("mixed") == [("New feature", []), ("Fix a bug", []), ("Clean up", [])]                 # the Taskmaster alone


def test_code_is_someones_a_type_that_needs_it_is_offered_only_when_a_member_takes_it_itself(board, monkeypatch):
    root, state = board
    names = lambda slug: {t.id for t, _r in goal_types.offered(state, root, slug)}
    no_code = _party(root, state, ["artist"], leader="product-designer")
    assert not names(no_code) & {"feature", "bug", "tidy", "release"}                        # no one of it writes code: not even with the Grunt to fill in
    tester = _party(root, state, ["tester"], leader="product-manager", title="Tester")
    assert not names(tester) & {"feature", "bug", "tidy"}                                    # the Tester takes tests, not code
    grunt = _party(root, state, ["grunt"], leader="product-designer", title="Grunt")
    assert {"feature", "bug", "tidy"} <= names(grunt)
    alone = _party(root, state, [], title="Alone")
    assert {"feature", "bug", "tidy"} <= names(alone)                                        # the Taskmaster leading takes code
    monkeypatch.setattr(goal_types, "CATALOG", (*goal_types.CATALOG, goal_types.GoalType("proof", "Prove it", "bug", "x", ("tests",))))
    assert "proof" in names(tester) and "proof" not in names(no_code)                        # tests: the Tester, not the Grunt filling in
    scribe = roles.save(state, "Coder", "", 1, "Write code.", None, ["code"])
    own = _party(root, state, [scribe], leader="product-manager", title="Own")
    assert "bug" in names(own)                                                               # an agent of the person's own that takes it


def test_a_type_missing_one_agent_is_offered_only_when_the_leader_does_another_part_of_it(board):
    root, state = board
    pm = _party(root, state, ["grunt"], leader="product-manager")
    rows = {t.id: r for t, r in goal_types.offered(state, root, pm)}
    assert [m["agent"] for m in rows["screen"]] == ["ui-kit"] and [m["agent"] for m in rows["experiment"]] == ["experimenter"]
    assert set(rows["screen"][0]) == {"kind", "words", "agent", "name", "band", "free", "out"} and rows["screen"][0]["free"] is True
    assert rows["pain"] == []                                                                 # the leader's own work: nothing missing
    assert "tagline" not in rows and "icon" not in rows and "store" not in rows               # one agent missing, but beside the leader's own work
    assert "landing" not in rows and "abtest" not in rows                                     # two missing
    assert "launch" in rows and [m["agent"] for m in rows["launch"]] == ["copywriter"]
    designer = _party(root, state, ["grunt"], leader="game-designer", title="Game")
    assert not {t.id for t, r in goal_types.offered(state, root, designer) if r}               # a Game designer's goals need no one else's craft
    assert "mechanic" in {t.id for t, _r in goal_types.offered(state, root, designer)}
    # a kind with no one to join (`research` is a leader's) leaves the type out, whoever else is missing
    taskless = _party(root, state, ["grunt"], leader="growth", title="Growth")
    assert "launch" not in {t.id for t, _r in goal_types.offered(state, root, taskless)}


def test_a_type_that_stands_in_for_another_hides_it_when_it_is_met_and_is_not_offered_when_it_misses_someone(board):
    root, state = board
    eng = _party(root, state, ["grunt"], leader="architect")
    ids = [t.id for t, _r in goal_types.offered(state, root, eng)]
    assert "shaped-feature" in ids and "feature" not in ids                                    # one New feature, the Architect's
    lone = _party(root, state, ["grunt"], leader="product-designer", title="Lone")
    assert "feature" in [t.id for t, _r in goal_types.offered(state, root, lone)] and "flow-feature" not in [t.id for t, _r in goal_types.offered(state, root, lone)]
    kit = _party(root, state, ["grunt", "ui-kit"], leader="product-designer", title="Kit")
    ids = [t.id for t, _r in goal_types.offered(state, root, kit)]
    assert "flow-feature" in ids and "feature" not in ids
    data = _party(root, state, ["data-engineer"], leader="analyst", title="Data")
    assert {t.id: [m["agent"] for m in r] for t, r in goal_types.offered(state, root, data)}["abtest"] == ["experimenter"]
    pm = _party(root, state, ["grunt", "experimenter"], leader="product-manager", title="Lab")
    ids = [t.id for t, _r in goal_types.offered(state, root, pm)]
    assert "experiment" in ids and "abtest" not in ids                                         # the same name once
    # the general type met hides nothing the other way: the shaped one missing someone does not hide, nor is hidden by, the plain one
    assert "feature" in ids


def test_the_free_seat_of_a_missing_row_reads_the_leaders_seats(board):
    root, state = board
    three = _party(root, state, ["grunt", "ui-kit", "level-designer"], leader="product-designer", title="Three")
    (row,) = goal_types.missing(state, root, three, ("art",))
    assert row["free"] is False and len(row["out"]) == 3                                       # the default's three builders
    four = _party(root, state, ["grunt", "level-designer", "sound-designer"], leader="game-designer", title="Four")
    (row,) = goal_types.missing(state, root, four, ("art",))
    assert row["free"] is True                                                                  # a Game designer's four
    full = _party(root, state, ["grunt", "level-designer", "sound-designer", "artist"], leader="game-designer", title="Full")
    assert goal_types.missing(state, root, full, ("aso",))[0]["free"] is False


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
    ideas.save_state(state, slug, type="bug")
    assert goal_types.prompt_line(state, slug) == f"Its type: Fix a bug. {goal_types.get('bug').plan}\n"
    ideas.save_state(state, slug, type="taskmaster/bug")                                # a key kept before is read as its id
    assert goal_types.prompt_line(state, slug) == f"Its type: Fix a bug. {goal_types.get('bug').plan}\n"
    ideas.save_state(state, slug, type="feature")
    assert goal_types.prompt_line(state, slug) == "Its type: New feature.\n"            # no plan line: the name alone
    ideas.save_state(state, slug, type="nobody/bug")
    assert goal_types.prompt_line(state, slug) == ""
    assert json.loads((ideas.state_folder(state, slug) / "state.json").read_text())["type"] == "nobody/bug"   # kept as it was written
