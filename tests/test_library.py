"""Spec 59 §2.2–§2.4 (docs/specs/59-mixed-parties.md; realm/library.py): the five agents of the mixed parties, the Product manager who takes
screens too, the leaders' stages and seats, and the library's parties (the mixed first). Code, no model."""
from __future__ import annotations

import re

from orkboard.realm import goal_team, library, roles


def test_the_five_new_agents_are_in_the_librarys_order_with_their_craft_tier_kinds_and_band():
    ids = [a.id for a in library.LIBRARY]
    assert ids.index("game-designer") == ids.index("product-designer") + 1                 # the Game designer after the Product designer
    assert ids[ids.index("artist") + 1:ids.index("artist") + 4] == ["level-designer", "sound-designer", "playtester"]     # after the Artist
    assert ids.index("aso") == ids.index("seo") + 1                                         # ASO after SEO
    rows = {a.id: (a.name, a.craft, roles.RACES[a.craft], a.tier, a.takes, a.band) for a in library.LIBRARY}
    assert rows["game-designer"] == ("Game designer", "design", "elf", "elder", ("gamedesign",), "lead")
    assert rows["level-designer"] == ("Level designer", "design", "elf", "warrior", ("level",), "build")
    assert rows["sound-designer"] == ("Sound designer", "design", "elf", "laborer", ("sound",), "build")
    assert rows["playtester"] == ("Playtester", "design", "elf", "warrior", ("playtest",), "check")
    assert rows["aso"] == ("ASO", "marketing", "gnome", "laborer", ("aso",), "build")
    assert [library.get(i).line for i in ("game-designer", "level-designer", "sound-designer", "playtester", "aso")] == [
        "Leads a game party: the rules, the loop, what makes it fun", "Lays out the levels: the path, the beats, where it gets hard",
        "Makes the sounds and the music, picked by ear", "Plays a change through and says where it breaks or bores",
        "Writes the store pages: keywords, title, texts, screenshots' words"]


def test_each_instruction_is_within_600_in_the_librarys_voice_and_holds_the_agent_to_its_points():
    for a in library.LIBRARY:
        assert len(a.instruction) <= 600, a.id
        assert not re.search(r"\borcs?\b|orchestrat", a.instruction, re.I), a.id
    told = {i: library.get(i).instruction.lower() for i in ("game-designer", "level-designer", "sound-designer", "playtester", "aso")}
    assert all(w in told["game-designer"] for w in ("what the player does, sees and gets", "why it is fun", "before the build", "one balance file", "by playing"))
    assert all(w in told["level-designer"] for w in ("on paper", "the path", "the beats", "gets hard", "how long it plays", "one new idea"))
    assert all(w in told["sound-designer"] for w in ("loopable", "one loudness", "a pick of sounds", "source beside the export"))
    assert all(w in told["playtester"] for w in ("test build", "headless run", "where", "what the player does", "what goes wrong", "fix only what is small"))
    assert all(w in told["aso"] for w in ("search for in the store first", "title and subtitle", "limits", "without the person's yes"))


def test_the_playtesters_check_applies_when_a_player_would_notice():
    check = library.get("playtester").check
    assert check.applies == "when the idea changes what a player does, sees or hears"
    assert check.done == "It was played through: the changed part works and nothing near it broke"
    assert check.task == "Play the idea's change through and write where it breaks, bores or confuses; fix what is small."
    assert check.fits == ("design", "engineering")


def test_the_product_manager_takes_screens_too_in_a_sentence_that_fits():
    pm = library.get("product-manager")
    assert pm.takes == ("research", "design") and pm.band == "lead" and len(pm.instruction) <= 600
    assert ("For a screen, write the flow step by step and what is on each screen and why, at phone width first, in the design "
            "system's words.") in pm.instruction


def test_the_stages_of_a_leader_sum_to_five_more_and_the_default_is_for_any_other():
    for leader, s in {**library.STAGES, "default": library.DEFAULT_STAGES}.items():
        assert s.build_seats + s.check_seats == goal_team.SEATS and 2 <= s.build_seats <= 4 and 1 <= s.check_seats <= 3, leader
    assert library.STAGES.keys() == {"game-designer", "investor"}                           # the Investor's: spec 65 §1
    game = library.stages_of("game-designer")
    assert (game.lead, game.build, game.check, game.build_seats, game.check_seats) == ("Concept", "Build", "Playtest", 4, 1)
    for other in ("architect", "taskmaster", "product-manager", "a-persons-own", ""):
        s = library.stages_of(other)
        assert (s.lead, s.build, s.check, s.build_seats, s.check_seats) == ("Planning", "Implementation", "Checking", 3, 2), other
    assert library.seats_of("game-designer") == {"lead": 1, "build": 4, "check": 1} and library.seats_of("growth") == {"lead": 1, "build": 3, "check": 2}
    assert library.SEATS == {"lead": 1, "build": 3, "check": 2}                              # the default's, for older faces


def test_the_librarys_parties_have_known_members_that_fit_their_leaders_seats_and_bands():
    assert [p[0] for p in library.PRESETS] == ["game", "mobile-app", "website", "ideation"]    # Ideation after Website (spec 65 §1)
    for pid, name, line, craft, lead, build, check in library.PRESETS:
        assert library.get(lead).band == "lead" and craft in roles.CRAFTS and name and line, pid
        assert all(library.get(s).band == "build" for s in build) and all(library.get(s).band == "check" for s in check), pid
        assert not goal_team.seats([*build, *check], lead), pid
        assert len(build) <= library.seats_of(lead)["build"] and len(check) <= library.seats_of(lead)["check"], pid
    game, app, site, _ideation = library.PRESETS
    assert (game[4], game[5], game[6]) == ("game-designer", ("grunt", "artist", "level-designer", "sound-designer"), ("playtester",))
    assert (app[4], app[5], app[6]) == ("product-manager", ("grunt", "artist", "aso"), ("reviewer", "accessibility-reviewer"))
    assert (site[4], site[5], site[6]) == ("growth", ("grunt", "copywriter", "seo"), ("reviewer", "editor"))


def test_presets_answer_the_mixed_first_then_each_craft_then_the_taskmaster_alone():
    got = library.presets()
    assert [p["id"] for p in got] == ["game", "mobile-app", "website", "ideation", "engineering", "design", "data", "marketing", "product", "mixed"]
    assert [p["mixed"] for p in got] == [True] * 4 + [False] * 6
    game, eng, alone = got[0], got[4], got[-1]
    assert game == {"id": "game", "name": "Game", "line": "Rules, levels, art and sound, played through", "craft": "design", "race": "elf",
                    "mixed": True, "lead": "game-designer", "build": ["grunt", "artist", "level-designer", "sound-designer"], "check": ["playtester"]}
    assert (eng["name"], eng["line"], eng["lead"], eng["race"]) == ("Engineering", "Code, tests and the build", "architect", "peon")
    assert (alone["name"], alone["lead"], alone["build"], alone["check"]) == ("Taskmaster alone", "taskmaster", [], [])
    assert [p["name"] for p in got[4:9]] == [roles.CRAFT_LABELS[c] for c in ("engineering", "design", "data", "marketing", "product")]


def test_parties_keeps_every_craft_and_adds_the_three_mixed_ones_by_their_ids():
    got = library.parties()
    for craft, (lead, build, check) in library.PARTIES.items():
        assert got[craft] == {"lead": lead, "build": list(build), "check": list(check)}      # a face that reads parties[<craft>] is unchanged
    assert {"game", "mobile-app", "website", "ideation"} <= got.keys() and len(got) == len(library.PARTIES) + 4
    assert got["game"] == {"lead": "game-designer", "build": ["grunt", "artist", "level-designer", "sound-designer"], "check": ["playtester"]}


def test_listed_and_stages_answer_the_new_agents_and_every_leader():
    listed = {a["id"]: a for a in library.listed()}
    assert listed["playtester"]["band"] == "check" and listed["playtester"]["check"]["applies"].startswith("when the idea changes what a player")
    stages = library.stages()
    assert stages["game-designer"] == {"lead": "Concept", "build": "Build", "check": "Playtest", "seats": {"lead": 1, "build": 4, "check": 1}}
    assert stages["architect"] == stages["default"] == {"lead": "Planning", "build": "Implementation", "check": "Checking",
                                                       "seats": {"lead": 1, "build": 3, "check": 2}}
    assert set(stages) == {a.id for a in library.LIBRARY if a.band == "lead"} | {"default"}
