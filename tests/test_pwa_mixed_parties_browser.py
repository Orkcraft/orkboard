"""Spec 59 part C, the phone (docs/specs/59-mixed-parties.md §7, §8 "C"): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py. New party's library in one column, the mixed
first (*Mixed*, *One craft*, *Taskmaster alone*): a pick fills the seats and sends `preset`, a seat changed clears it; the Game's four builders' seats and *Concept* / *Build* / *Playtest*; a leader with
fewer seats (the alert line, *Save party* off); the stage switch's four heads (66 px) and its words whole at 390, a Game party's words and today's for another; an older host with no `stages` or
`presets` (the row of crafts as before); the service worker's version."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from orkboard.gui import pwa
from orkboard.realm import library
from tests.test_pwa_arena_browser import ELF, OWN, SCENE, _scene, member  # noqa: F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _band, _called, _new_goal, _phone  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

GAME = {"lead": {"word": "Concept"}, "build": {"word": "Build", "seats": 4}, "check": {"word": "Playtest", "seats": 1}}


def hosted(monkeypatch, *, newer=True):
    """The host of spec 59 A answers `presets` and `stages` with the roles (`newer`), or an older one does not."""
    real = Stub.commands

    def commands(self):
        got = real(self)
        roles = got["ideas.roles"]

        def serve(a):
            out = roles(a)
            return {**out, "presets": library.presets(), "stages": library.stages()} if newer else out
        return {**got, "ideas.roles": serve}
    monkeypatch.setattr(Stub, "commands", commands)


async def _sheet(page):
    await _new_goal(page)
    sheet = page.get_by_role("dialog", name="New party")
    await sheet.wait_for(timeout=WAIT_MS)
    return sheet


@pytest.mark.asyncio
async def test_the_library_gives_the_mixed_parties_first_in_one_column(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _sheet(page)
        tiles = sheet.locator(".preset-tile")
        await tiles.first.wait_for(timeout=WAIT_MS)
        assert [await t.get_attribute("data-preset") for t in await tiles.all()] == ["game", "mobile-app", "website", "engineering", "design", "data", "marketing", "product", "mixed"]
        assert [await g.get_attribute("aria-label") for g in await sheet.locator(".preset-group").all()] == ["Mixed", "One craft", "Taskmaster alone"]
        xs = {round((await t.bounding_box())["x"]) for t in await tiles.all()}
        assert len(xs) == 1                                                                     # one column
        for t in await tiles.all():
            assert (await t.bounding_box())["height"] >= 44
        game = sheet.locator('.preset-tile[data-preset="game"]')
        assert "Rules, levels, art and sound, played through" in await game.inner_text() and await game.locator("img").count() == 6
        await game.click()
        assert await sheet.locator(".party-line").first.inner_text() == \
            "Leads: Game designer · Builds: Grunt, Artist, Level designer, Sound designer · Checks: Playtester"
        await sheet.get_by_label("What it is for").fill("A tower game.")
        await sheet.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save", {"about": "A tower game.", "craft": "design", "leader": "game-designer", "priority": "normal", "preset": "game",
                                                       "team": ["grunt", "artist", "level-designer", "sound-designer", "playtester"], "every": []})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_seat_changed_clears_the_preset_and_the_game_has_four_builders_seats(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _sheet(page)
        await sheet.locator('.preset-tile[data-preset="game"]').click()
        await sheet.locator('.party [data-change="team"]').click()
        builds = sheet.get_by_role("region", name="Builds")
        await builds.get_by_role("button").first.click()
        assert await builds.get_attribute("data-stage") == "Build"
        assert await builds.locator(".team-seat").count() == 4 and await builds.locator(".team-seat:not(.is-empty)").count() == 4
        assert "4 of 4" in await builds.inner_text() and "Build · 4 seats" in await builds.inner_text()
        assert await sheet.get_by_role("region", name="Leads").get_attribute("data-stage") == "Concept"
        assert await sheet.get_by_role("region", name="Checks").get_attribute("data-stage") == "Playtest"
        await sheet.get_by_role("button", name="Take out: Sound designer").click()
        await builds.get_by_role("button", name="Done").click()
        await sheet.get_by_label("What it is for").fill("A tower game, quiet.")
        await sheet.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save", {"about": "A tower game, quiet.", "craft": "design", "leader": "game-designer", "priority": "normal",
                                                       "team": ["grunt", "artist", "level-designer", "playtester"], "every": []})
        sent = [c[1] for c in stub.calls if c[0] == "ideas.goal_save"][-1]
        assert "preset" not in sent


@pytest.mark.asyncio
async def test_a_leader_with_fewer_seats_says_so_and_save_stays_off_until_it_fits(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _sheet(page)
        await sheet.locator('.preset-tile[data-preset="game"]').click()
        await sheet.get_by_label("What it is for").fill("A tower game.")
        save = sheet.get_by_role("button", name="Save party")
        assert await save.is_enabled()
        await sheet.locator('.party [data-change="team"]').click()
        await sheet.get_by_role("region", name="Leads").get_by_role("button", name="Take in: Architect").click()      # the Architect leads three builders: the Game's four do not fit
        line = "Implementation has 3 seats with Architect: take one out first."
        builds = sheet.get_by_role("region", name="Builds")
        assert await builds.locator(".party-over").inner_text() == line
        assert await builds.locator(".team-seat.is-over").count() == 1
        assert await save.is_disabled()
        await builds.get_by_role("button", name="Take out: Sound designer").click()
        assert await builds.locator(".party-over").count() == 0 and await save.is_enabled()


@pytest.mark.asyncio
async def test_the_stage_switch_shows_four_heads_in_66_px_and_the_party_s_words(fake_repo, monkeypatch):
    hosted(monkeypatch)
    goal = SCENE["map"]["goals"][0]
    goal["stages"] = copy.deepcopy(GAME)
    goal["party"] += [member({"slug": "levels", "name": "Levels"}, "build", ELF), member({"slug": "sound", "name": "Sound"}, "build", OWN)]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        names = [await page.locator(f'.band[data-band="{k}"] .band__name').inner_text() for k in ("lead", "build", "check")]
        assert [n.lower() for n in names] == ["concept", "build", "playtest"]
        await _band(page, "build")
        faces = page.locator('.band[data-band="build"] .band__face')
        assert await faces.count() == 4
        boxes = [await f.locator(".ork-race__head").bounding_box() for f in await faces.all()]
        assert round(boxes[-1]["x"] + boxes[-1]["width"] - boxes[0]["x"]) == 66
        assert [round(b["x"] - boxes[0]["x"]) for b in boxes] == [0, 14, 28, 42]
        for key in ("lead", "build", "check"):                                               # the words whole, none cut
            word = page.locator(f'.band[data-band="{key}"] .band__name')
            assert await word.evaluate("e => e.scrollWidth <= e.clientWidth + 1 && e.getBoundingClientRect().right <= 390")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_an_older_host_says_today_s_words_and_keeps_the_row_of_crafts(fake_repo, monkeypatch):
    hosted(monkeypatch, newer=False)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        names = [await page.locator(f'.band[data-band="{k}"] .band__name').inner_text() for k in ("lead", "build", "check")]
        assert [n.lower() for n in names] == ["planning", "implementation", "checking"]
        sheet = await _sheet(page)
        assert await sheet.locator(".craft-tile").count() == 6 and await sheet.locator(".preset-tile").count() == 0
        await sheet.locator('.craft-tile[data-craft="design"]').click()
        await sheet.get_by_label("What it is for").fill("A design party.")
        await sheet.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save")
        assert "preset" not in [c[1] for c in stub.calls if c[0] == "ideas.goal_save"][-1]


def test_the_service_worker_is_one_version_up():
    sw = (Path(pwa.__file__).parent / "static" / "pwa" / "sw.js").read_text(encoding="utf-8")
    assert 'const CACHE = "orkcraft-app-v72";' in sw
