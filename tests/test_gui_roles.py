"""Spec 59 §2.4 (gui/ideas_roles.py): `ideas.roles` answers the library's parties (`presets`) and every leader's stages (`stages`), and
the five new kinds. Code, no model."""
from __future__ import annotations

import pytest

from orkboard.gui.board_host import Orkboard
from orkboard.realm import library, roles


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def test_ideas_roles_answers_the_presets_the_mixed_first_and_the_old_parties_as_before(host):
    got = host.command("ideas.roles")
    assert [p["id"] for p in got["presets"]] == ["game", "mobile-app", "website", "ideation", "release", "engineering", "design", "data", "marketing",
                                                 "product", "mixed"]          # Ideation after Website (spec 65 §1)
    game = got["presets"][0]
    assert (game["name"], game["craft"], game["race"], game["mixed"], game["lead"]) == ("Game", "design", "elf", True, "game-designer")
    assert game["build"] == ["grunt", "artist", "level-designer", "sound-designer"] and game["check"] == ["playtester"]
    assert set(game) == {"id", "name", "line", "craft", "race", "mixed", "lead", "build", "check"}
    assert got["parties"]["engineering"] == {"lead": "architect", "build": ["grunt", "tester"], "check": ["reviewer"]}      # by craft, as before
    assert got["parties"]["game"]["lead"] == "game-designer" and got["seats"] == {"lead": 1, "build": 3, "check": 2}


def test_ideas_roles_answers_every_leaders_stages_and_the_default(host):
    stages = host.command("ideas.roles")["stages"]
    assert stages["game-designer"] == {"lead": "Concept", "build": "Build", "check": "Playtest", "seats": {"lead": 1, "build": 4, "check": 1}}
    assert stages["default"]["build"] == "Implementation" and stages["default"]["seats"] == {"lead": 1, "build": 3, "check": 2}
    assert set(stages) == {a.id for a in library.LIBRARY if a.band == "lead"} | {"default"}


def test_ideas_roles_lists_the_five_new_kinds_and_agents(host):
    got = host.command("ideas.roles")
    labels = {k["kind"]: k["label"] for k in got["kinds"]}
    assert [labels[k] for k in ("gamedesign", "level", "sound", "playtest", "aso")] == ["Game design", "Levels", "Sound", "Playtest", "Store pages (ASO)"]
    assert len(got["kinds"]) == len(roles.TASK_KINDS) and all(k["role"] == "grunt" for k in got["kinds"])
    assert {"game-designer", "level-designer", "sound-designer", "playtester", "aso"} <= {a["id"] for a in got["library"]}
