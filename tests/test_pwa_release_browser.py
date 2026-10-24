"""Spec 68 part C, the phone: a Release party (docs/specs/68-release-and-route.md §3, §7.3–§7.6, §7.9, §8 "C"): Chromium at 390 × 844 against the world of tests/test_pwa_route_browser.py (the Passkey party, Ideation,
Website and a Release party whose leader is the Release manager, a skeleton). Release is the library's fifth mixed tile in New party and shows *Releases from* ticked (*Every party but Ideation*); Edit the party shows it
for a party that offers *A release*; New goal of *A release* asks **What goes in** after *Version* (a held flag greyed *In 1.4 already*, the empty line, *Add the goal* still adds); the Release party's Goals say *k flags wait
for a release* (a press opens New goal of *A release*), its Flags a release's version and *k goals*, **Mark it out** (asking first) and then *Out in 1.4*; another party's flags say *In Release 1.4*, *Out in 1.3* or *Waits for
a release* (only with a Release party); a party switch says `ideas.shown`, fire and forget. No horizontal scroll anywhere."""
from __future__ import annotations

import pytest

from tests.test_pwa_arena_browser import SCENE, _redrawn, _scene, _shot_to  # noqa: F401
from tests.test_pwa_route_browser import WORLD, norm, world  # noqa: F401
from tests.test_pwa_shell_browser import FAB, NO_SCROLL, WAIT_MS, _called, _new_goal, _phone, _pick_goal, _where

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

CANDIDATES = [
    {"goal": "button", "title": "Passkey button on the sign-in page", "party": "passkey", "party_name": "Passkey", "element": "ice", "at": "2026-10-14T16:20:00", "commit": "abc1234", "held": ""},
    {"goal": "badge", "title": "A badge on the icon", "party": "passkey", "party_name": "Passkey", "element": "ice", "at": "2026-10-20T09:00:00", "commit": "def5678", "held": ""},
    {"goal": "kept", "title": "Where the credentials are kept", "party": "passkey", "party_name": "Passkey", "element": "meadow", "at": "2026-10-10T09:00:00", "commit": "0a1b2c3", "held": "1.4"},
]
ASK = "Is 1.4 out in the stores? Orkboard submits nothing: say so once you have."


def calls(stub, name):
    return [c[1] for c in stub.calls if c[0] == name]


async def _goals(page):
    """The Goals sheet of the party shown."""
    await page.locator(".gbar__head").click()
    sheet = page.get_by_role("dialog", name="Goals")
    await sheet.wait_for(timeout=WAIT_MS)
    return sheet


async def _release_form(page, type_id="release"):
    """New goal in the Release party, A release picked."""
    await _pick_goal(page, "release")
    await page.locator(FAB).click()
    form = page.get_by_role("dialog", name="New goal")
    await form.wait_for(timeout=WAIT_MS)
    await page.wait_for_function("() => !document.getAnimations().some((a) => a.playState === 'running')", timeout=WAIT_MS)
    if type_id:
        await form.locator(f'.newgoal__chip[data-type="{type_id}"]').click()
    return form


# -- New party: Release is the fifth mixed tile --------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_release_is_the_fifth_mixed_tile_its_heads_are_the_hosts_races_and_it_shows_releases_from_ticked(fake_repo, monkeypatch):
    world(monkeypatch, release=False)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New party")
        tiles = sheet.locator(".preset-tile")
        await tiles.first.wait_for(timeout=WAIT_MS)
        ids = [await t.get_attribute("data-preset") for t in await tiles.all()]
        assert ids[:5] == ["game", "mobile-app", "website", "ideation", "release"] and ids.index("release") == 4        # the fifth tile of the mixed group
        tile = sheet.locator('.preset-tile[data-preset="release"]')
        assert "A version out: what goes in, its notes, the stores' list" in await tile.inner_text()
        heads = await tile.locator("img.ork-race__head").evaluate_all("(is) => is.map((i) => i.getAttribute('src'))")
        assert heads[0].startswith("races/skeleton-") and heads[-1].startswith("races/skeleton-")                        # the Release manager and the checker are skeletons
        assert await tile.locator('img[data-agent="release-manager"]').evaluate("(i) => i.complete && i.naturalWidth > 0")
        assert await sheet.locator(".releasesfrom").is_hidden()                                                         # only a Release party takes goals from the others
        await tile.click()
        box = sheet.locator(".releasesfrom")
        await box.wait_for(timeout=WAIT_MS)
        assert [norm(await r.inner_text()) for r in await box.locator(".releasesfrom__row").all()] == ["Passkey", "Website"]        # not Ideation, not General
        assert await box.locator("input:checked").count() == 2
        assert "Every party but Ideation" in await box.inner_text()
        await sheet.locator('.preset-tile[data-preset="game"]').click()
        await box.wait_for(state="hidden", timeout=WAIT_MS)
        await tile.click()
        await box.wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)
        await sheet.get_by_label("What it is for").fill("Our versions out.")
        await sheet.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save")
        assert "releases_from" not in calls(stub, "ideas.goal_save")[-1] and calls(stub, "ideas.goal_save")[-1]["preset"] == "release"      # nothing changed: the default


@pytest.mark.asyncio
async def test_unticking_a_party_in_new_party_sends_the_parties_left_and_one_always_stays(fake_repo, monkeypatch):
    world(monkeypatch, release=False)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New party")
        await sheet.locator('.preset-tile[data-preset="release"]').click()
        box = sheet.locator(".releasesfrom")
        await box.locator('input[data-goal="website"]').click()
        assert "Only the ticked parties" in await box.inner_text()
        await box.locator('input[data-goal="passkey"]').click()                                                         # the last one stays: none would mean every party
        assert await box.locator('input[data-goal="passkey"]').is_checked()
        await sheet.get_by_label("What it is for").fill("Our versions out.")
        await sheet.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save")
        assert calls(stub, "ideas.goal_save")[-1]["releases_from"] == ["passkey"]


# -- Edit the party -------------------------------------------------------------------------------------------------------------------------------------

async def _edit(page, party):
    await _pick_goal(page, party)
    sheet = await _goals(page)
    await sheet.get_by_role("button", name="About ").click()
    about = page.get_by_role("dialog", name="About this party")
    await about.get_by_role("button", name="Edit the party").click()
    form = page.get_by_role("dialog", name="Edit the party")
    await form.wait_for(timeout=WAIT_MS)
    return form


@pytest.mark.asyncio
async def test_edit_the_party_of_a_release_party_shows_releases_from_and_saves_what_changed(fake_repo, monkeypatch):
    world(monkeypatch)
    release = next(g for g in SCENE["map"]["goals"] if g["slug"] == "release")
    release["releases_from"] = ["passkey"]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _edit(page, "release")
        box = form.locator(".releasesfrom")
        await box.wait_for(timeout=WAIT_MS)
        assert [await r.locator("input").is_checked() for r in await box.locator(".releasesfrom__row").all()] == [True, False]      # as saved
        assert "Only the ticked parties" in await box.inner_text()
        assert await page.evaluate(NO_SCROLL)
        await form.get_by_label("What it is for").fill("Our versions out.")
        await form.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save")
        assert "releases_from" not in calls(stub, "ideas.goal_save")[-1]                                                  # unchanged: not sent
        await page.locator(".screen .back").click()                                                                     # the party's screen it opens after a save
        await page.locator("section.screen:not([hidden])").wait_for(state="detached", timeout=WAIT_MS)
        form = await _edit(page, "release")
        await form.locator('.releasesfrom input[data-goal="website"]').check()
        assert "Every party but Ideation" in await form.locator(".releasesfrom").inner_text()
        await form.get_by_label("What it is for").fill("Our versions out.")
        await form.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save") and len(calls(stub, "ideas.goal_save")) == 2
        assert calls(stub, "ideas.goal_save")[-1]["releases_from"] == [] and calls(stub, "ideas.goal_save")[-1]["slug"] == "release"      # all ticked is the default: []


@pytest.mark.asyncio
async def test_a_party_that_does_not_offer_a_release_has_no_releases_from(fake_repo, monkeypatch):
    world(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _edit(page, "passkey")
        assert await form.locator(".releasesfrom").is_hidden()


# -- New goal of A release ------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_goal_of_a_release_asks_what_goes_in_after_version_with_a_held_flag_greyed(fake_repo, monkeypatch):
    world(monkeypatch)
    WORLD["candidates"] = CANDIDATES
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _release_form(page)
        goes = form.locator(".goesin")
        await goes.locator(".goesin__row").first.wait_for(timeout=WAIT_MS)
        assert calls(stub, "ideas.release_candidates") == [{"party": "release"}]
        order = await form.locator(".newgoal__asks > *").evaluate_all("(es) => es.map((e) => e.classList.contains('goesin') ? 'goes' : e.textContent.trim())")
        assert order == ["Version", "goes", "What is new"]                                                               # What goes in comes after Version
        rows = goes.locator(".goesin__row")
        assert [await r.get_attribute("data-goal") for r in await rows.all()] == ["button", "badge", "kept"]
        assert [await r.locator("input").is_checked() for r in await rows.all()] == [True, True, False]                  # the free ones are ticked
        assert await rows.nth(2).locator("input").is_disabled()
        text = [norm(await r.inner_text()) for r in await rows.all()]
        assert text[0] == "Passkey button on the sign-in page Passkey · 14 Oct" and text[2] == "Where the credentials are kept Passkey · 10 Oct · In 1.4 already"
        assert await rows.nth(0).locator(".ork-elem").count() == 1                                                       # its goal's element
        assert min([(await r.bounding_box())["height"] for r in await rows.all()]) >= 44
        await goes.locator('input[data-goal="badge"]').uncheck()
        await form.get_by_label("Version").fill("1.5")
        await form.get_by_role("textbox", name="The goal").fill("Version 1.5 out")
        assert await page.evaluate(NO_SCROLL)
        await _shot_to(page, "phone-release-new-goal")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add")
        sent = calls(stub, "ideas.add")[-1]
        assert sent["type"] == "release" and sent["track"] == "release" and sent["asks"] == {"version": "1.5"} and sent["goes_in"] == ["button"]


@pytest.mark.asyncio
async def test_with_nothing_flagged_it_says_so_and_the_goal_is_still_added(fake_repo, monkeypatch):
    world(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _release_form(page)
        empty = form.locator(".goesin__empty")
        await empty.wait_for(timeout=WAIT_MS)
        assert norm(await empty.inner_text()) == "Nothing has raised its flag since 1.3."
        await form.get_by_role("textbox", name="The goal").fill("Fixes not yet flagged")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add")
        assert calls(stub, "ideas.add")[-1]["goes_in"] == []
        WORLD["since"] = None                                                                                           # before the first release
        form = await _release_form(page)
        await form.locator(".goesin__empty", has_text="since the start").wait_for(timeout=WAIT_MS)
        assert norm(await form.locator(".goesin__empty").inner_text()) == "Nothing has raised its flag since the start."


@pytest.mark.asyncio
async def test_another_type_has_no_what_goes_in_and_sends_no_goes_in(fake_repo, monkeypatch):
    world(monkeypatch)
    release = next(g for g in SCENE["map"]["goals"] if g["slug"] == "release")
    release["types"] = [*release["types"], {"id": "bug", "name": "Fix a bug", "sign": "bug", "line": "Something that goes wrong, made right", "lens": "text", "refs": False, "used": 0, "missing": [],
                                            "asks": []}]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _release_form(page, "bug")
        assert await form.locator(".goesin").is_hidden()
        await form.get_by_role("textbox", name="The goal").fill("A bug")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add")
        assert "goes_in" not in calls(stub, "ideas.add")[-1]


# -- The Release party's Goals ---------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_k_flags_wait_for_a_release_opens_new_goal_on_a_release(fake_repo, monkeypatch):
    world(monkeypatch)
    WORLD["candidates"] = CANDIDATES
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _pick_goal(page, "release")
        sheet = await _goals(page)
        wait = sheet.locator('[data-act="wait-release"]')
        assert norm(await wait.inner_text()) == "2 flags wait for a release" and (await wait.bounding_box())["height"] >= 44
        assert await wait.locator(".ork-sign.flag").count() == 1                                                        # orkUI's flag, no Unicode sign
        await wait.click()
        form = page.get_by_role("dialog", name="New goal")
        await form.wait_for(timeout=WAIT_MS)
        await form.locator('.goesin__row[data-goal="button"]').wait_for(timeout=WAIT_MS)
        assert await form.locator('.newgoal__chip[data-type="release"]').get_attribute("aria-checked") == "true"
        assert await form.locator('.newgoal__party').get_attribute("data-goal") == "release"
        SCENE["map"]["goals"][-1]["wait_release"] = 1
        await page.keyboard.press("Escape")
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        await _redrawn(stub, page)
        sheet = await _goals(page)
        assert norm(await sheet.locator('[data-act="wait-release"]').inner_text()) == "1 flag waits for a release"
        SCENE["map"]["goals"][-1]["wait_release"] = 0
        await _redrawn(stub, page)
        assert await sheet.locator('[data-act="wait-release"]').count() == 0                                            # none waits: the line goes
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_releases_row_says_its_version_and_goals_and_mark_it_out_asks_first_then_it_is_out(fake_repo, monkeypatch):
    world(monkeypatch)
    for n in SCENE["map"]["nodes"]:                                                                                     # the titles a person writes, not the version
        n["title"] = n["short"] = {"r14": "Sign-in fixes", "r13": "Dark sign-in"}.get(n["slug"], n["title"])
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _pick_goal(page, "release")
        sheet = await _goals(page)
        r14, r13 = sheet.locator('.goals__release[data-idea="r14"]'), sheet.locator('.goals__release[data-idea="r13"]')
        assert norm(await r14.locator("p").inner_text()) == "Sign-in fixes · 1.4 · 2 goals"
        assert norm(await r13.locator("p").inner_text()) == "Dark sign-in · Out in 1.3" and await r13.locator("button").count() == 0       # out already: no press
        out = r14.get_by_role("button", name="Mark it out")
        assert (await out.bounding_box())["height"] >= 44
        await _shot_to(page, "phone-release")
        await out.click()
        ask = r14.locator(".goals__ask")
        assert norm(await ask.locator("p").first.inner_text()) == ASK                                                   # it asks first
        assert not calls(stub, "ideas.release_out")
        await ask.get_by_role("button", name="Not yet").click()
        assert await r14.locator(".goals__ask").count() == 0 and not calls(stub, "ideas.release_out")
        await r14.get_by_role("button", name="Mark it out").click()
        await _shot_to(page, "phone-release-ask")
        assert await page.evaluate(NO_SCROLL)
        await r14.get_by_role("button", name="Out", exact=True).click()
        assert await _called(stub, "ideas.release_out", {"slug": "r14"})
        await r14.locator("p", has_text="Out in 1.4").wait_for(timeout=WAIT_MS)
        assert norm(await r14.locator("p").inner_text()) == "Sign-in fixes · Out in 1.4" and await r14.locator("button").count() == 0
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_refused_mark_it_out_says_the_hosts_words_and_asks_again(fake_repo, monkeypatch):
    world(monkeypatch)
    WORLD["refuse"] = "Its flag is not raised yet: a release goes out once it is in main"
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _pick_goal(page, "release")
        sheet = await _goals(page)
        r14 = sheet.locator('.goals__release[data-idea="r14"]')
        await r14.get_by_role("button", name="Mark it out").click()
        await r14.get_by_role("button", name="Out", exact=True).click()
        warn = r14.locator(".goals__ask .warn")
        await warn.wait_for(timeout=WAIT_MS)
        assert await warn.inner_text() == WORLD["refuse"] and await r14.locator(".goals__ask").count() == 1
        assert "Out in 1.4" not in await sheet.inner_text()                                                             # it stays as it was


# -- Another party's flags -------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_another_partys_flags_say_in_release_out_in_or_waits_for_a_release(fake_repo, monkeypatch):
    world(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _goals(page)
        flags = {await p.get_attribute("data-idea"): norm(await p.inner_text()) for p in await sheet.locator("p.goals__flag").all()}
        assert flags["button"].endswith("In Release 1.4") and flags["kept"].endswith("Out in 1.3") and flags["badge"].endswith("Waits for a release")
        assert await page.evaluate(NO_SCROLL)
        await page.keyboard.press("Escape")
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        await page.locator(".gbar__head").click()
        await sheet.get_by_role("button", name="About ").click()
        about = page.get_by_role("dialog", name="About this party")
        lines = norm(await about.locator('[data-sec="Its flags"]').inner_text())
        assert "In Release 1.4" in lines and "Out in 1.3" in lines and "Waits for a release" in lines


@pytest.mark.asyncio
async def test_without_a_release_party_no_flag_waits_for_one(fake_repo, monkeypatch):
    world(monkeypatch, release=False)
    for n in SCENE["map"]["nodes"]:
        if n.get("flag"):
            n["flag"] = {**n["flag"], "release": None}
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _goals(page)
        flags = norm(await sheet.locator("p.goals__flag").first.locator("xpath=..").inner_text())
        assert "flags · 3" in flags.lower() and "release" not in flags.lower().replace("releases", "")
        assert await sheet.locator('[data-act="wait-release"]').count() == 0


# -- A party switch says ideas.shown ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_party_switch_says_ideas_shown_once_fire_and_forget(fake_repo, monkeypatch):
    world(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.wait_for_timeout(500)
        assert not calls(stub, "ideas.shown")                                                                           # not on the first read, not on a redraw
        await _redrawn(stub, page)
        assert not calls(stub, "ideas.shown")
        sheet = await _where(page)
        assert await sheet.locator('.where-row[data-goal="release"] img').get_attribute("src") == "races/skeleton-warrior.png"      # the leader's head, from the host's race
        await sheet.locator('.where-row[data-goal="website"]').click()
        await page.locator('.partydeck[data-goal="website"]').wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.shown", {"party": "website", "from": "passkey"})
        sheet = await _where(page)                                                                                      # the one shown again: nothing said
        await sheet.locator('.where-row[data-goal="website"]').click()
        await page.wait_for_timeout(300)
        assert calls(stub, "ideas.shown") == [{"party": "website", "from": "passkey"}]
        sheet = await _where(page)
        await sheet.locator('.where-row[data-goal="release"]').click()
        assert await _called(stub, "ideas.shown", {"party": "release", "from": "website"})
        assert await page.locator("p.flash").count() == 0                                                               # never a toast
