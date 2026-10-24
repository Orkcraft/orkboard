"""Spec 67 A (docs/specs/67-release-and-route.md §3–§6, Tests → A): what goes in a release (since the last one out, Releases from, held
flags), a release's file, `goes_in`, the prompt's lines cut at 3 000, Mark it out, the events, the party switch, the Map's answers. Code, no model."""
from __future__ import annotations

import json

import pytest

from orkboard.gui.board_host import CommandError
from orkboard.realm import board_map, event_log, goal_types, idea_flag, ideas, library, releases
from tests.test_idea_route import events, flag, goal, host, party, wait, wait_party  # noqa: F401  (`host`: the fixture of spec 67's route tests)

A1, W1, A2 = "2026-10-20T09:00:00", "2026-10-21T09:00:00", "2026-10-22T09:00:00"


@pytest.fixture
def board(host):  # noqa: F811
    """The Mobile app, Website and Ideation parties of the route's fixture, and a Release party; three flagged goals, one not, one of Ideation's."""
    h = host
    h.rel = party(h, "Release", "release")
    h.a1, h.w1, h.a2 = goal(h, h.app, "Cache the table"), goal(h, h.web, "Faster pages"), goal(h, h.app, "Dark mode")
    for slug, at in ((h.a1, A1), (h.w1, W1), (h.a2, A2)):
        ideas.save_state(h.state, slug, state="done")
        flag(h, slug, at)
    h.open = goal(h, h.app, "Not flagged yet", state="working")
    h.pitch = goal(h, h.talk, "A pitch with a flag")
    flag(h, h.pitch, "2026-10-23T09:00:00")
    return h


def release(h, version="1.3", goals=(), out="", at="2026-10-21T08:00:00", party_slug=None):
    slug = goal(h, party_slug or h.rel, f"Release {version}")
    ideas.save_state(h.state, slug, type="release")
    ideas._write_json(releases._path(h.state, slug), {"version": version, "goals": list(goals), "out": out, "at": at})
    return slug


def ids(rows):
    return [c["goal"] for c in rows]


# -- §3.2: what goes in ---------------------------------------------------------------------------------------------------

def test_a_release_party_releases_from_every_party_but_ideation_and_itself_newest_flag_first(board):
    h = board
    assert releases.releases_from(h.root, h.rel) == [] and releases.sources(h.root, h.rel) == [h.app, h.web]
    got = releases.candidates(h.root, h.state, h.rel)
    assert ids(got) == [h.a2, h.w1, h.a1]                                              # the pitch's flag, an unflagged goal: not listed
    assert got[0] == {"goal": h.a2, "title": "Dark mode", "party": h.app, "party_name": "Mobile app", "element": "", "at": A2, "commit": "c" * 40, "held": ""}
    assert releases.since(h.root, h.state, h.rel) is None                              # before the first release: all of them
    assert releases.sources(h.root, h.app) == [h.app] and releases.sources(h.root, h.talk) == [h.talk]      # any other party: itself


def test_candidates_are_the_flags_raised_after_the_last_release_that_is_out(board):
    h = board
    r1 = release(h, "1.3", [h.a1], out="")                                              # open: it holds a1, no "last release" yet
    assert releases.since(h.root, h.state, h.rel) is None
    assert [(c["goal"], c["held"]) for c in releases.candidates(h.root, h.state, h.rel)] == [(h.a2, ""), (h.w1, ""), (h.a1, "1.3")]
    ideas._write_json(releases._path(h.state, r1), {"version": "1.3", "goals": [h.a1], "out": "2026-10-21T12:00:00", "at": "2026-10-21T08:00:00"})
    assert releases.since(h.root, h.state, h.rel) == {"version": "1.3", "out": "2026-10-21T12:00:00"}
    assert ids(releases.candidates(h.root, h.state, h.rel)) == [h.a2]                   # a1 and w1 were raised before it went out
    late = goal(h, h.app, "Raised after")
    flag(h, late, "2026-10-23T09:00:00")
    assert ids(releases.candidates(h.root, h.state, h.rel)) == [late, h.a2]
    r2 = release(h, "1.4", [], out="2026-10-24T09:00:00", at="2026-10-24T08:00:00")
    assert releases.since(h.root, h.state, h.rel)["version"] == "1.4" and releases.candidates(h.root, h.state, h.rel) == []
    assert r2 not in ids(releases.candidates(h.root, h.state, h.rel))
    assert releases.since(h.root, h.state, h.app) is None                              # another party's releases are its own


def test_a_release_goals_own_flag_is_never_listed_and_a_flag_in_an_open_release_is_held_by_it(board):
    h = board
    r = release(h, "1.4", [h.a2])
    flag(h, r, "2026-10-25T09:00:00")
    got = releases.candidates(h.root, h.state, h.rel)
    assert r not in ids(got) and {c["goal"]: c["held"] for c in got} == {h.a2: "1.4", h.w1: "", h.a1: ""}
    assert releases.wait(h.root, h.state, h.rel) == 2                                   # not the held one


def test_releases_from_set_on_the_party_is_kept_on_its_page_and_narrows_what_is_listed(board):
    h = board
    assert releases.set_releases_from(h.root, h.rel, [h.web]) == [h.web]
    assert "releases_from" in (h.root / ideas.TRACKS / f"{h.rel}.md").read_text() and releases.releases_from(h.root, h.rel) == [h.web]
    assert releases.sources(h.root, h.rel) == [h.web] and ids(releases.candidates(h.root, h.state, h.rel)) == [h.w1]
    assert releases.set_releases_from(h.root, h.rel, []) == [] and releases.sources(h.root, h.rel) == [h.app, h.web]        # [] is the default
    assert releases.releases_from(h.root, h.rel) == []
    for bad, why in (([h.talk], "to release from"), ([h.rel], "to release from"), (["nowhere"], "to release from"), ("web", "list"), ([1], "list")):
        with pytest.raises(ValueError, match=why):
            releases.set_releases_from(h.root, h.rel, bad)
    assert releases.set_releases_from(h.root, h.rel, [h.web, h.web, h.app]) == [h.web, h.app]
    h.gone = party(h, "Gone", "website")
    releases.set_releases_from(h.root, h.rel, [h.gone])
    (h.root / ideas.TRACKS / f"{h.gone}.md").unlink()
    assert releases.sources(h.root, h.rel) == [h.app, h.web]                            # a party since gone: the default again


def test_a_party_that_offers_a_release_without_a_release_party_releases_its_own_flags(board):
    h = board
    (h.root / ideas.TRACKS / f"{h.rel}.md").unlink()
    assert goal_types.release_party(h.root) == "" and releases.offers(h.state, h.root, h.app) and not releases.offers(h.state, h.root, h.talk)
    assert ids(releases.candidates(h.root, h.state, h.app)) == [h.a2, h.a1] and releases.wait(h.root, h.state, h.app) == 2
    assert releases.wait(h.root, h.state, h.talk) == 0


def test_a_dropped_release_frees_its_goals_and_a_dropped_one_that_was_out_does_not_move_the_last_release(board):
    h = board
    r = release(h, "1.4", [h.a1, h.a2])
    assert {c["goal"]: c["held"] for c in releases.candidates(h.root, h.state, h.rel)}[h.a1] == "1.4"
    ideas.drop(h.root, r, h.state)
    assert {c["goal"]: c["held"] for c in releases.candidates(h.root, h.state, h.rel)} == {h.a2: "", h.w1: "", h.a1: ""}
    assert releases.holding(h.root, h.state) == {} and releases.index(h.root, h.state) == []


# -- §3.3: ideas.add of A release takes goes_in ----------------------------------------------------------------------------

def add_release(h, goes_in=None, version="1.4", party_slug=None, **more):
    args = {"text": "Ship the next version", "track": party_slug or h.rel, "type": "release", "asks": {"version": version}, **more}
    if goes_in is not None:
        args["goes_in"] = goes_in
    return h.command("ideas.add", args)


def test_a_release_goal_keeps_its_version_and_the_goals_that_go_in_in_its_file_and_writes_nothing_on_them(board):
    h = board
    got = add_release(h, [h.a2, h.w1])
    wait(h, got["slug"])
    file = json.loads(releases._path(h.state, got["slug"]).read_text())
    assert set(file) == {"version", "goals", "out", "at"} and file["version"] == "1.4" and file["goals"] == [h.a2, h.w1] and file["out"] == ""
    assert releases.read(h.state, got["slug"])["at"] and got["type"] == "release"
    assert not (h.state / "ideas" / h.a2 / "release.json").exists() and not (h.state / "ideas" / h.a2 / "route.json").exists()
    assert ideas.state(h.state, got["slug"])["type"] == "release"
    (ev,) = events(h, event_log.RELEASE_MADE)
    assert (ev["goal"], ev["party"], ev["goals"], ev["parties"], ev["device"]) == (got["slug"], h.rel, 2, 2, "desktop")
    assert {c["goal"]: c["held"] for c in releases.candidates(h.root, h.state, h.rel)} == {h.a2: "1.4", h.w1: "1.4", h.a1: ""}
    with pytest.raises(CommandError, match="“Dark mode” is in 1.4 already"):                 # held by the open release
        add_release(h, [h.a2], "1.5")
    again = add_release(h, [h.a1], "1.5")
    wait(h, again["slug"])
    assert releases.read(h.state, again["slug"])["goals"] == [h.a1]


def test_a_release_with_nothing_that_goes_in_is_added_all_the_same_and_goes_in_is_refused_for_what_is_not_listed(board):
    h = board
    bare = add_release(h)
    wait(h, bare["slug"])
    assert releases.read(h.state, bare["slug"]) == {"version": "1.4", "goals": [], "out": "", "at": releases.read(h.state, bare["slug"])["at"]}
    for bad in ([h.open], [h.pitch], ["nowhere"], [h.rel]):
        with pytest.raises(CommandError, match="has not raised its flag in a party this release takes from"):
            add_release(h, bad)
    for bad in ("a", [1], {"a": 1}):
        with pytest.raises(CommandError, match="goes_in is a list of goals"):
            add_release(h, bad)
    with pytest.raises(CommandError, match="Only a release takes goals to go in"):
        h.command("ideas.add", {"text": "A plain goal", "track": h.app, "goes_in": [h.a1]})
    assert h.command("ideas.add", {"text": "A plain goal", "track": h.app, "goes_in": []})["type"] == ""
    releases.set_releases_from(h.root, h.rel, [h.web])
    with pytest.raises(CommandError, match="has not raised its flag"):                      # a party it was not set to release from
        add_release(h, [h.a1])
    assert not [i for i in ideas.ideas(h.root, h.rel) if i["title"] == "Ship the next version" and releases.read(h.state, i["slug"]) is None]


def test_a_release_of_a_party_without_a_release_party_takes_its_own_flags_and_the_version_is_cut(board):
    h = board
    (h.root / ideas.TRACKS / f"{h.rel}.md").unlink()
    got = add_release(h, [h.a1], "  1.4   beta " + "x" * 80, party_slug=h.app)
    wait(h, got["slug"])
    assert releases.read(h.state, got["slug"])["version"].startswith("1.4 beta xxx") and len(releases.read(h.state, got["slug"])["version"]) == releases.VERSION_CHARS
    with pytest.raises(CommandError, match="has not raised its flag"):
        add_release(h, [h.w1], party_slug=h.app)                                            # Website's flag: not this party's to release


def test_release_candidates_answers_what_goes_in_for_the_dialog(board):
    h = board
    r = release(h, "1.3", [h.a1], out="2026-10-21T12:00:00")
    open_ = release(h, "1.4", [h.a2])
    got = h.command("ideas.release_candidates", {"party": h.rel})
    assert set(got) == {"since", "releases_from", "candidates"} and got["since"] == {"version": "1.3", "out": "2026-10-21T12:00:00"}
    assert got["releases_from"] == [] and [(c["goal"], c["held"]) for c in got["candidates"]] == [(h.a2, "1.4")]
    assert set(got["candidates"][0]) == {"goal", "title", "party", "party_name", "element", "at", "commit", "held"}
    assert h.command("ideas.release_candidates", {"party": h.app})["since"] is None and r and open_
    with pytest.raises(CommandError, match="That party is gone"):
        h.command("ideas.release_candidates", {"party": "nowhere"})


# -- §3.4: the prompt's lines ----------------------------------------------------------------------------------------------

def test_the_prompts_lines_name_the_version_and_each_goal_that_goes_in_and_are_empty_for_any_other_goal(board):
    h = board
    ideas.set_section(h.root, h.a2, "Done when", "- Dark theme follows the system\n- Toggle in settings")
    r = release(h, "1.4", [h.a2, h.w1])
    text = releases.prompt_lines(h.root, h.state, r)
    assert text.startswith("This goal is a release. Its version: 1.4.\n") and text.endswith("\n")
    assert "- Dark mode — Done when: Dark theme follows the system; Toggle in settings — flag: commit " + "c" * 40 in text
    assert "- Faster pages — flag: commit" in text and "more" not in text
    assert releases.prompt_lines(h.root, h.state, h.a1) == "" and releases.prompt_lines(h.root, h.state, "gone") == ""
    bare = release(h, "", [])
    assert "Its version is not set yet." in releases.prompt_lines(h.root, h.state, bare) and "No goal goes in yet" in releases.prompt_lines(h.root, h.state, bare)


def test_the_prompts_lines_are_cut_at_three_thousand_the_last_goals_first_with_and_k_more(board):
    h = board
    many = []
    for n in range(40):
        slug = goal(h, h.app, f"Goal number {n:02d} " + "w" * 60)
        ideas.set_section(h.root, slug, "Done when", "- " + "d" * 150 + f" {n}")
        flag(h, slug, f"2026-10-23T09:{n:02d}:00")
        many.append(slug)
    r = release(h, "2.0", many)
    text = releases.prompt_lines(h.root, h.state, r)
    assert len(text) <= releases.PROMPT_CHARS == 3000
    kept = [ln for ln in text.splitlines() if ln.startswith("- Goal number")]
    assert 5 < len(kept) < 40 and kept[0].startswith("- Goal number 00") and kept[-1].startswith(f"- Goal number {len(kept) - 1:02d}")      # the first stay, the last go
    assert text.splitlines()[-1] == f"- and {40 - len(kept)} more"
    short = release(h, "2.1", many[:3])
    assert "more" not in releases.prompt_lines(h.root, h.state, short)


def test_the_draft_and_the_plan_prompts_hold_the_releases_lines_and_a_goal_that_is_not_a_release_holds_none(board):
    h = board
    prompts = []

    def spy(tier, prompt, effort="", budget=None):
        prompts.append(prompt)
        return json.dumps({"summary": "", "questions": [], "title": "A goal"}), 0.01, 10, ""

    h.ideas.keeper.call = spy
    got = add_release(h, [h.a2])                                                          # Now: drafted at once
    wait(h, got["slug"])
    draft = next(p for p in prompts if "write its spec straight away" in p)
    assert "Its type: A release." in draft and "This goal is a release. Its version: 1.4." in draft and "- Dark mode — flag: commit" in draft
    assert draft.index("Its type: A release.") < draft.index("This goal is a release.")
    prompts.clear()
    plain = h.command("ideas.add", {"text": "A plain goal", "track": h.app})
    wait(h, plain["slug"])
    assert prompts and not any("This goal is a release" in p for p in prompts)
    from orkboard.core import idea_keeper, idea_revise
    assert "releases" in vars(idea_keeper) and "releases" in vars(idea_revise)


# -- §3.5: Out ----------------------------------------------------------------------------------------------------------------

def test_mark_it_out_is_refused_before_the_releases_own_flag_for_a_goal_that_is_not_a_release_and_the_second_time(board):
    h = board
    r = release(h, "1.4", [h.a1, h.a2])
    with pytest.raises(CommandError, match="Its flag is not raised yet: a release goes out once it is in main"):
        h.command("ideas.release_out", {"slug": r})
    with pytest.raises(CommandError, match="That goal is not a release"):
        h.command("ideas.release_out", {"slug": h.a1})
    flag(h, r, "2026-10-25T09:00:00")
    got = h.command("ideas.release_out", {"slug": r})
    assert got["ok"] is True and got["out"] == releases.read(h.state, r)["out"] != ""
    assert releases.read(h.state, r)["goals"] == [h.a1, h.a2] and releases.read(h.state, r)["version"] == "1.4"
    with pytest.raises(CommandError, match="1.4 is out already"):
        h.command("ideas.release_out", {"slug": r})
    (ev,) = events(h, event_log.RELEASE_OUT)
    assert (ev["goal"], ev["goals"], ev["device"]) == (r, 2, "desktop") and isinstance(ev["days"], int) and ev["days"] >= 3      # a1's flag was 20 October
    nodes = {n["slug"]: n for n in board_map.build(h.root, h.state, {}, [], 0.0)["nodes"]}
    assert nodes[h.a1]["flag"]["release"] == {"goal": r, "party": h.rel, "version": "1.4", "out": got["out"]}
    assert nodes[r]["release"] == {"version": "1.4", "goals": [h.a1, h.a2], "out": got["out"]}
    assert nodes[h.a1]["route"][-1]["step"] == "release" and nodes[h.a1]["route"][-1]["out"] == got["out"]
    assert nodes[h.w1]["flag"]["release"] is None and nodes[h.w1]["release"] is None
    assert releases.since(h.root, h.state, h.rel)["version"] == "1.4"                           # a1, a2 and w1 were raised before it went out


def test_a_release_with_no_goal_that_has_a_flag_says_no_days(board):
    h = board
    r = release(h, "1.4", ["gone"])
    flag(h, r)
    assert h.command("ideas.release_out", {"slug": r})["ok"] is True
    (ev,) = events(h, event_log.RELEASE_OUT)
    assert ev["days"] is None and ev["goals"] == 1


def test_the_events_hold_no_goals_words_and_party_shown_comes_from_ideas_shown(board):
    h = board
    secret = goal(h, h.app, "SECRET-WORDS in a title")
    ideas.save_state(h.state, secret, state="done")
    flag(h, secret, "2026-10-23T11:00:00")
    got = add_release(h, [secret])
    wait(h, got["slug"])
    flag(h, got["slug"])
    h.command("ideas.release_out", {"slug": got["slug"]})
    h.command("ideas.move", {"slug": goal(h, h.app, "SECRET-WORDS again"), "track": h.web})
    assert h.command("ideas.shown", {"party": h.web, "from": h.app}) == {"ok": True}
    h.command("ideas.shown", {"party": h.web, "from": h.web})                            # the same party: nothing
    h.command("ideas.shown", {"party": h.web})                                           # a first read: nothing
    h.command("ideas.shown", {"party": h.app, "from": "nowhere"})                        # from a party that is gone: nothing
    with pytest.raises(CommandError, match="That party is gone"):
        h.command("ideas.shown", {"party": "nowhere", "from": h.app})
    rows = [r for r in event_log.read(h.ideas.host.repo_root) if r["event"] in ("idea_moved", "release_made", "release_out", "party_shown")]
    assert [r["event"] for r in rows] == ["release_made", "release_out", "idea_moved", "party_shown"]
    assert "SECRET-WORDS" not in json.dumps(rows) and "Ship the next version" not in json.dumps(rows)
    shown = rows[-1]
    assert (shown["from"], shown["to"], shown["face"]) == (h.app, h.web, "desktop") and "goal" not in shown
    assert {"idea_moved", "release_made", "release_out", "party_shown"} <= set(event_log.EVENTS)
    assert (event_log.IDEA_MOVED, event_log.RELEASE_MADE, event_log.RELEASE_OUT, event_log.PARTY_SHOWN) == ("idea_moved", "release_made", "release_out", "party_shown")
    assert event_log.counts(h.ideas.host.repo_root)["party_shown"] == 1


# -- §6: the host's answers --------------------------------------------------------------------------------------------------

def test_the_map_says_a_partys_releases_from_and_what_waits_for_a_release(board):
    h = board
    parties = {p["slug"]: p for p in board_map.build(h.root, h.state, {}, [], 0.0)["goals"]}
    assert parties[h.rel]["releases_from"] == [] and parties[h.rel]["wait_release"] == 3
    assert parties[h.app]["wait_release"] == 0 and parties[h.talk]["wait_release"] == 0           # the Release party takes the flags: Mobile app offers none now
    release(h, "1.4", [h.a2])
    assert {p["slug"]: p["wait_release"] for p in board_map.build(h.root, h.state, {}, [], 0.0)["goals"]}[h.rel] == 2
    releases.set_releases_from(h.root, h.rel, [h.web])
    parties = {p["slug"]: p for p in h.command("ideas.map", {})["goals"]}
    assert parties[h.rel]["releases_from"] == [h.web] and parties[h.rel]["wait_release"] == 1
    json.dumps(h.command("ideas.map", {}))
    (h.root / ideas.TRACKS / f"{h.rel}.md").unlink()
    parties = {p["slug"]: p for p in board_map.build(h.root, h.state, {}, [], 0.0)["goals"]}
    assert parties[h.app]["wait_release"] == 1 and parties[h.web]["wait_release"] == 0           # Mobile app: a2 is held by 1.4; a1 waits (Website offers none)


def test_ideas_flags_say_the_release_of_a_flag_and_goal_save_keeps_releases_from_with_the_party(board):
    h = board
    r = release(h, "1.4", [h.a2], out="2026-10-26T09:00:00")
    rows = {g["slug"]: g for g in h.command("ideas.flags")["goals"]}
    assert rows[h.a2]["release"] == {"goal": r, "party": h.rel, "version": "1.4", "out": "2026-10-26T09:00:00"} and rows[h.a1]["release"] is None
    lead, build, check = next((p[4], p[5], p[6]) for p in library.PRESETS if p[0] == "release")
    save = {"slug": h.rel, "leader": lead, "team": [*build, *check], "craft": "product"}
    h.command("ideas.goal_save", {**save, "releases_from": [h.app]})
    wait_party(h, h.rel)
    assert releases.releases_from(h.root, h.rel) == [h.app]
    h.command("ideas.goal_save", save)                                                       # not sent: kept as it was
    assert releases.releases_from(h.root, h.rel) == [h.app]
    h.command("ideas.goal_save", {**save, "releases_from": []})
    assert releases.releases_from(h.root, h.rel) == []
    with pytest.raises(CommandError, match="to release from"):
        h.command("ideas.goal_save", {**save, "releases_from": [h.talk]})
    with pytest.raises(CommandError, match="Releases from is a list of parties"):
        h.command("ideas.goal_save", {**save, "releases_from": "all"})
    made = h.command("ideas.goal_save", {"title": "Store releases", "about": "Out.", "craft": "product", "leader": lead, "team": [*build, *check],
                                         "preset": "release", "releases_from": [h.web]})["slug"]
    assert releases.releases_from(h.root, made) == [h.web]


def test_the_release_party_is_priced_and_listed_as_any_preset(board):
    h = board
    lead, build, check = next((p[4], p[5], p[6]) for p in library.PRESETS if p[0] == "release")
    price = h.command("ideas.party_price", {"leader": lead, "team": [*build, *check], "craft": "product"})
    assert price["types"] and "release" in [t["id"] for t in price["types"]] and price["low"] <= price["high"]
    assert {t["id"] for t in h.command("ideas.party_price", {"leader": "product-manager", "team": ["grunt", "artist", "aso"], "craft": "product"})["types"]}.isdisjoint({"release"})                                                          # beside a Release party: not offered elsewhere
    roles = h.command("ideas.roles")
    release_preset = next(p for p in roles["presets"] if p["id"] == "release")
    assert release_preset["lead"] == "release-manager" and release_preset["race"] == "lich" and roles["stages"]["release-manager"]["lead"] == "Gather"
    assert {a["id"]: a["race"] for a in roles["library"]}["release-checker"] == "lich"
    assert idea_flag.flag_of(h.state, h.a1)["at"] == A1


def test_the_release_partys_work_says_releases_out_goals_a_release_and_the_days_from_a_flag_to_out(board):
    h = board
    from orkboard.realm import party_work
    party_work.forget()
    assert h.command("ideas.party", {"goal": h.rel})["releases"] == {"made": 0, "out": 0, "goals": None, "days": None}
    release(h, "1.3", [h.a1, h.w1], out="2026-10-24T09:00:00")                              # a1's flag was 20 October: 4 days
    release(h, "1.4", [h.a2])
    party_work.forget()
    got = h.command("ideas.party", {"goal": h.rel})["releases"]
    assert got == {"made": 2, "out": 1, "goals": 1.5, "days": 4.0}
    party_work.forget()
    assert "releases" not in h.command("ideas.party", {"goal": h.app}) and "pitches" not in h.command("ideas.party", {"goal": h.rel})
