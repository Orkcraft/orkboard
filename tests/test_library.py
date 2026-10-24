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
        assert s.build_seats + s.check_seats == (goal_team.SEATS - 1 if leader == "release-manager" else goal_team.SEATS), leader     # spec 68 §1.2: the Release manager's 3 and 1
        assert 2 <= s.build_seats <= 4 and 1 <= s.check_seats <= 3, leader
    assert library.STAGES.keys() == {"game-designer", "investor", "release-manager"}      # the Investor's: spec 65 §1; the Release manager's: spec 68 §1
    game = library.stages_of("game-designer")
    assert (game.lead, game.build, game.check, game.build_seats, game.check_seats) == ("Concept", "Build", "Playtest", 4, 1)
    for other in ("architect", "taskmaster", "product-manager", "a-persons-own", ""):
        s = library.stages_of(other)
        assert (s.lead, s.build, s.check, s.build_seats, s.check_seats) == ("Planning", "Implementation", "Checking", 3, 2), other
    assert library.seats_of("game-designer") == {"lead": 1, "build": 4, "check": 1} and library.seats_of("growth") == {"lead": 1, "build": 3, "check": 2}
    assert library.SEATS == {"lead": 1, "build": 3, "check": 2}                              # the default's, for older faces


def test_the_librarys_parties_have_known_members_that_fit_their_leaders_seats_and_bands():
    assert [p[0] for p in library.PRESETS] == ["game", "mobile-app", "website", "ideation", "release"]    # Ideation after Website (spec 65 §1), Release after Ideation (spec 68 §1)
    for pid, name, line, craft, lead, build, check in library.PRESETS:
        assert library.get(lead).band == "lead" and craft in roles.CRAFTS and name and line, pid
        assert all(library.get(s).band == "build" for s in build) and all(library.get(s).band == "check" for s in check), pid
        assert not goal_team.seats([*build, *check], lead), pid
        assert len(build) <= library.seats_of(lead)["build"] and len(check) <= library.seats_of(lead)["check"], pid
    game, app, site, _ideation, _release = library.PRESETS
    assert (game[4], game[5], game[6]) == ("game-designer", ("grunt", "artist", "level-designer", "sound-designer"), ("playtester",))
    assert (app[4], app[5], app[6]) == ("product-manager", ("grunt", "artist", "aso"), ("reviewer", "accessibility-reviewer"))
    assert (site[4], site[5], site[6]) == ("growth", ("grunt", "copywriter", "seo"), ("reviewer", "editor"))


def test_presets_answer_the_mixed_first_then_each_craft_then_the_taskmaster_alone():
    got = library.presets()
    assert [p["id"] for p in got] == ["game", "mobile-app", "website", "ideation", "release", "engineering", "design", "data", "marketing", "product", "mixed"]
    assert [p["mixed"] for p in got] == [True] * 5 + [False] * 6
    game, eng, alone = got[0], got[5], got[-1]
    assert game == {"id": "game", "name": "Game", "line": "Rules, levels, art and sound, played through", "craft": "design", "race": "elf",
                    "mixed": True, "lead": "game-designer", "build": ["grunt", "artist", "level-designer", "sound-designer"], "check": ["playtester"]}
    assert (eng["name"], eng["line"], eng["lead"], eng["race"]) == ("Engineering", "Code, tests and the build", "architect", "peon")
    assert (alone["name"], alone["lead"], alone["build"], alone["check"]) == ("Taskmaster alone", "taskmaster", [], [])
    assert [p["name"] for p in got[5:10]] == [roles.CRAFT_LABELS[c] for c in ("engineering", "design", "data", "marketing", "product")]


def test_parties_keeps_every_craft_and_adds_the_three_mixed_ones_by_their_ids():
    got = library.parties()
    for craft, (lead, build, check) in library.PARTIES.items():
        assert got[craft] == {"lead": lead, "build": list(build), "check": list(check)}      # a face that reads parties[<craft>] is unchanged
    assert {"game", "mobile-app", "website", "ideation", "release"} <= got.keys() and len(got) == len(library.PARTIES) + 5
    assert got["game"] == {"lead": "game-designer", "build": ["grunt", "artist", "level-designer", "sound-designer"], "check": ["playtester"]}


def test_listed_and_stages_answer_the_new_agents_and_every_leader():
    listed = {a["id"]: a for a in library.listed()}
    assert listed["playtester"]["band"] == "check" and listed["playtester"]["check"]["applies"].startswith("when the idea changes what a player")
    stages = library.stages()
    assert stages["game-designer"] == {"lead": "Concept", "build": "Build", "check": "Playtest", "seats": {"lead": 1, "build": 4, "check": 1}}
    assert stages["architect"] == stages["default"] == {"lead": "Planning", "build": "Implementation", "check": "Checking",
                                                       "seats": {"lead": 1, "build": 3, "check": 2}}
    assert set(stages) == {a.id for a in library.LIBRARY if a.band == "lead"} | {"default"}


# -- spec 68 §1: the Release manager and its hands, the preset, an agent's own race ---------------------------------------

def _skeletons(tmp_path, monkeypatch, tiers=roles.TIERS):
    """orkUI's copy with the skeleton drawn at `tiers` (A0's files), else as it is."""
    folder = tmp_path / "races"
    folder.mkdir()
    for t in tiers:
        (folder / f"skeleton-{t}.png").write_bytes(b"png")
    monkeypatch.setattr(roles, "RACE_FILES", folder)


def test_the_four_release_agents_follow_ideation_with_their_craft_tier_kind_band_race_and_line():
    ids = [a.id for a in library.LIBRARY]
    assert ids[ids.index("skeptic") + 1:] == ["release-manager", "release-engineer", "release-notes", "release-checker"]
    rows = {i: (a.name, a.craft, a.tier, a.band, a.takes, a.race, a.line) for i in ids[-4:] for a in [library.get(i)]}
    assert rows == {
        "release-manager": ("Release manager", "product", "warrior", "lead", ("research",), "skeleton",
                            "Gathers what goes into a version and gets it out, step by step"),
        "release-engineer": ("Release engineer", "engineering", "laborer", "build", ("code",), "",
                             "Bumps the version, the changelog and the build's config"),
        "release-notes": ("Release notes", "marketing", "laborer", "build", ("text",), "", "Writes what is new, for the stores and the changelog"),
        "release-checker": ("Release checker", "product", "warrior", "check", ("review",), "skeleton",
                            "Checks that the version, its notes and the list agree")}
    assert library.RELEASE_MANAGER == "release-manager" and not any(library.get(i).pitch for i in ids[-4:])
    for i in ids[-4:]:
        told = library.get(i).instruction
        assert 0 < len(told) <= roles.INSTRUCTION_CHARS and not re.search(r"\borcs?\b|orchestrat", told, re.I), i
    assert "never new work" in library.get("release-manager").instruction
    assert "step for the person" in library.get("release-manager").instruction and "never a feature" in library.get("release-engineer").instruction
    assert "one line a goal" in library.get("release-notes").instruction and "did not go in" in library.get("release-notes").instruction
    check = library.get("release-checker").check
    assert check.applies == "when the goal is a release" and check.fits == ("product", "engineering", "marketing")
    assert check.done == "Its version, what is new and the stores' list name exactly the goals that go in, and nothing was submitted"
    assert check.task == ("Check that the version, what is new and the stores' list name exactly the goals that go in, that the build's config "
                          "carries the version, and that nothing was submitted.")


def test_the_release_preset_follows_ideation_and_the_release_managers_stages_are_gather_prepare_check():
    got = library.presets()
    i = [p["id"] for p in got].index("release")
    assert got[i - 1]["id"] == "ideation" and got[i] == {
        "id": "release", "name": "Release", "line": "A version out: what goes in, its notes, the stores' list", "craft": "product", "race": "lich",
        "mixed": True, "lead": "release-manager", "build": ["release-engineer", "release-notes", "aso"], "check": ["release-checker"]}
    assert library.stages()["release-manager"] == {"lead": "Gather", "build": "Prepare", "check": "Check", "seats": {"lead": 1, "build": 3, "check": 1}}
    assert not goal_team.seats(["release-engineer", "release-notes", "aso", "release-checker"], "release-manager")
    assert library.parties()["release"] == {"lead": "release-manager", "build": ["release-engineer", "release-notes", "aso"], "check": ["release-checker"]}


def test_listed_says_an_agents_own_race_only_once_orkui_has_its_head(tmp_path, monkeypatch):
    listed = {a["id"]: a for a in library.listed()}
    assert listed["release-manager"]["race"] == "lich" and listed["release-checker"]["race"] == "lich"          # before A0's copy: the craft's
    assert listed["release-engineer"]["race"] == "peon" and listed["release-notes"]["race"] == "gnome" and listed["investor"]["race"] == "lich"
    _skeletons(tmp_path, monkeypatch)
    listed = {a["id"]: a for a in library.listed()}
    assert listed["release-manager"]["race"] == "skeleton" and listed["release-checker"]["race"] == "skeleton"
    assert listed["release-engineer"]["race"] == "peon" and listed["grunt"]["race"] == "peon"
    assert [p["race"] for p in library.presets() if p["id"] == "release"] == ["skeleton"]
    monkeypatch.setattr(roles, "RACE_FILES", tmp_path / "nowhere")
    assert {a["id"]: a["race"] for a in library.listed()}["release-manager"] == "lich"


def test_a_role_wears_its_own_race_when_its_file_is_in_orkuis_copy_else_its_crafts(tmp_path, monkeypatch):
    state = tmp_path / ".orkcraft"
    library.install(state, ["release-manager", "release-engineer"])
    manager, engineer = roles.role(state, "release-manager"), roles.role(state, "release-engineer")
    assert manager["race"] == "skeleton" and engineer["race"] == "" and "race: skeleton" in (state / "roles" / "release-manager.md").read_text()
    assert roles.head(manager, "balance") == {"craft": "product", "race": "lich", "tier": "warrior"}              # the file is missing: the craft's
    assert roles.head(engineer, "balance")["race"] == "peon"
    _skeletons(tmp_path, monkeypatch)
    assert roles.head(manager, "balance") == {"craft": "product", "race": "skeleton", "tier": "warrior"}
    assert roles.head({**manager, "race": "dragon"}, "balance")["race"] == "lich" and roles.head({**manager, "race": "../x"}, "balance")["race"] == "lich"


def test_a_head_needs_the_race_at_the_tier_it_is_drawn_at(tmp_path, monkeypatch):
    state = tmp_path / ".orkcraft"
    library.install(state, ["release-manager"])
    _skeletons(tmp_path, monkeypatch, tiers=("warrior",))
    manager = roles.role(state, "release-manager")
    by_target = {**manager, "model": ""}                       # By Target: the task's tier shifted by the Target
    assert roles.head(by_target, "balance") == {"craft": "product", "race": "skeleton", "tier": "warrior"}
    assert roles.head(by_target, "quality") == {"craft": "product", "race": "lich", "tier": "elder"}      # no elder gear yet: the lich's


def test_saving_a_role_keeps_its_race_and_a_role_without_one_reads_empty(tmp_path):
    state = tmp_path / ".orkcraft"
    library.install(state, ["release-manager"])
    roles.save(state, "Release manager", "warrior", 2, "Gather what goes in.", slug="release-manager")
    assert roles.role(state, "release-manager")["race"] == "skeleton" and "race: skeleton" in (state / "roles" / "release-manager.md").read_text()
    roles.save(state, "Docs scribe", "warrior", 2, "Write plainly.")
    assert roles.role(state, "docs-scribe")["race"] == "" and "race:" not in (state / "roles" / "docs-scribe.md").read_text()
    assert roles.role(state, "grunt")["craft"] == "engineering" and roles.head(roles.role(state, "grunt"), "balance")["race"] == "peon"
