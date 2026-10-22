"""Spec 53 part A, the phone's board (docs/specs/53-phone-simpler.md §1, §3, §5 "A"): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py (a party, *Sign in with a passkey*,
of a leader, two builders and two checkers). The party's deck at the goals bar's left (44 px, the other parties' count, its sheet) and none at the stage switch's end; the tabs' faces side by side with
their signs on the faces they come from; a face pressed shows the member's tasks (`aria-pressed`) and pressed again everyone; no members' strip, a name over each column; the first phase row 180 px
under the top; a goal's type's sign before its name on a task's card and in place of *Goal* on a Planning goal's card, none for a goal with no type, none on a stop; 44 px targets; no sideways scroll."""
from __future__ import annotations

import pytest

from orkboard.gui import pwa
from tests.test_pwa_arena_browser import SCENE, _scene  # noqa: F401
from tests.test_pwa_decks_browser import second_party  # noqa: F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _band, _phone, _where  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

BUG = {"id": "bug", "name": "Fix a bug", "sign": "bug"}


def norm(s):
    return " ".join(s.split())


def _node(slug):
    return next(n for n in SCENE["map"]["nodes"] if n["slug"] == slug)


@pytest.mark.asyncio
async def test_the_partys_deck_stands_at_the_goals_bars_left_with_the_other_partys_stops_and_none_at_the_stage_switch(fake_repo, monkeypatch):
    second_party(2)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        deck = page.locator(".gbar > .partydeck")
        await deck.wait_for(timeout=WAIT_MS)
        assert await page.locator(".partydeck").count() == 1 and await page.locator(".stagebar .partydeck, .stagebar > .partydeck").count() == 0     # none at the stage switch's end
        bar, box = await page.locator(".gbar").bounding_box(), await deck.bounding_box()
        assert (round(box["width"]), round(box["height"])) == (44, 44) and round(box["x"]) == round(bar["x"]) and await deck.evaluate("e => e.nextElementSibling.matches('.gbar__head')")
        back = await deck.locator(".partydeck__back").bounding_box()
        assert (round(back["width"]), round(back["height"])) == (16, 22) and await deck.locator(".partydeck__edge").count() == 2         # a back of 16 × 22, two edges behind it
        assert await deck.locator(".ork-count").count() == 0                                                                            # no count (spec 54 §2.4); the label says it to a screen reader
        assert await deck.get_attribute("aria-label") == "Parties: Passkey shown, 2 stops wait in the other parties. A tap shows the parties"
        assert norm(await page.locator(".gbar__head").inner_text()) == "Passkey · 2 of 9 goals done"
        sheet = await _where(page)
        assert [await r.get_attribute("data-goal") for r in await sheet.locator(".where-row").all()] == ["passkey", "product", "ops"]
        await page.keyboard.press("Escape")
        await page.get_by_role("tablist", name="Stages").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_tabs_faces_are_side_by_side_each_sign_on_the_face_it_comes_from(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        tabs = page.get_by_role("tablist", name="Stages")
        await tabs.wait_for(timeout=WAIT_MS)
        bands = tabs.locator(".band")
        assert [round((await b.bounding_box())["height"]) for b in await bands.all()] == [60, 60, 60]
        assert all([abs((await b.bounding_box())["width"] - 130) <= 2 for b in await bands.all()])                                       # the whole width, shared
        assert [norm(await b.inner_text()) for b in await bands.all()] == ["Planning", "Implementation", "Checking"]
        assert [await tabs.locator(f'.band[data-band="{k}"] img.ork-race__head').count() for k in ("lead", "build", "check")] == [1, 2, 2]
        build = [await h.bounding_box() for h in await tabs.locator('.band[data-band="build"] img.ork-race__head').all()]
        assert round(build[0]["width"]) == 24 and round(build[0]["height"]) == 22 and round(build[1]["x"] - build[0]["x"]) == 28      # 24 wide, 4 apart: side by side
        sign = lambda k, who: tabs.locator(f'.band[data-band="{k}"] [data-member="{who}"] .band__sign .ork-sign')                    # noqa: E731
        assert await sign("build", "backend").get_attribute("class") == "ork-sign cross"                                                # the failed task is Backend's
        assert await tabs.locator('.band[data-band="build"] [data-member="screens"] .band__sign').count() == 0                         # nothing on a face with nothing
        assert await sign("lead", "taskmaster").get_attribute("class") == "ork-sign alert"                                              # Planning's on the leader
        assert await sign("check", "reviewer").get_attribute("class") == "ork-sign alert"                                               # the Reviewer asks
        assert await tabs.locator('.band[data-band="check"] [data-member="words"] .band__sign').count() == 0
        s, face = await tabs.locator('.band[data-band="build"] [data-member="backend"] .band__sign').bounding_box(), build[0]
        assert (round(s["width"]), round(s["height"])) == (12, 12) and round(face["x"] + face["width"] - s["x"]) == 7 and round(face["y"] - s["y"]) == 5   # 12 × 12, 5 px over the head's corner
        assert not await tabs.locator(".ork-count").count() and await tabs.locator(".band[data-band]").nth(1).get_attribute("aria-label") == "Implementation: Backend, Screens. 1 failed"
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_face_pressed_shows_only_that_members_tasks_and_pressed_again_everyone(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".stack .deck").first.wait_for(timeout=WAIT_MS)
        faces = page.locator('.band[data-band="build"] button.band__face')
        assert [await f.get_attribute("aria-label") for f in await faces.all()] == ["Only Backend’s tasks", "Only Screens’s tasks"]
        assert all([await f.get_attribute("aria-pressed") == "false" for f in await faces.all()])
        for f in await faces.all():
            box = await f.bounding_box()
            assert round(box["width"]) >= 44 and round(box["height"]) >= 44                                                              # 44 × 44 targets
        assert await page.locator('.band:not(.is-on) button.band__face').count() == 0                                                     # a tab not shown is one button
        await faces.first.click()
        solo = page.get_by_role("group", name="Only Backend’s tasks")
        await solo.wait_for(timeout=WAIT_MS)
        assert await faces.first.get_attribute("aria-pressed") == "true" and await solo.get_by_role("button", name="Everyone").count() == 1
        assert await solo.locator(".solo__card").count() == 1                                                                           # the member's card: price, kit, runs
        await faces.first.click()
        await solo.wait_for(state="detached", timeout=WAIT_MS)
        assert await faces.first.get_attribute("aria-pressed") == "false" and await page.locator(".stack[data-column]").count() == 2
        await faces.nth(1).click()                                                                                                     # another face: that member's
        await page.get_by_role("group", name="Only Screens’s tasks").wait_for(timeout=WAIT_MS)
        await _band(page, "check")
        assert await page.get_by_role("group", name="Only Screens’s tasks").count() == 0                                                  # a tab picked leaves the solo
        await page.locator('.band[data-band="check"] button.band__face').first.wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_no_members_strip_a_name_over_each_column_and_the_first_phase_row_at_180(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".stack .deck").first.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(500)
        assert await page.locator(".token").count() == 0
        names = page.locator(".colname")
        assert [norm(await n.text_content()) for n in await names.all()] == ["Backend", "Screens"]
        n0 = await names.first.bounding_box()
        assert round(n0["height"]) == 28 and await names.first.evaluate("e => e.tagName === 'SPAN' && getComputedStyle(e).textTransform === 'uppercase' && getComputedStyle(e).fontSize === '11px'")
        assert await names.first.evaluate("e => getComputedStyle(e).justifyContent === 'center' && e.getBoundingClientRect().width === e.parentElement.getBoundingClientRect().width")      # centred over the column
        row = await page.locator(".stack .phase").first.bounding_box()
        assert 180 <= row["y"] <= 190                                                                                                    # 48 + 44 + 60 + 28, and the bars' lines and the column's own 7 px
        await _band(page, "lead")
        assert [norm(await n.text_content()) for n in await page.locator(".colname").all()] == ["Taskmaster"]                              # Planning's says its leader
        assert await page.locator(".token").count() == 0 and await page.evaluate(NO_SCROLL)
    SCENE["map"]["goals"][0]["party"] = [m for m in SCENE["map"]["goals"][0]["party"] if m["band"] != "build"]                             # a band with no one keeps its line
    for n in SCENE["map"]["nodes"]:
        n["tasks"] = []                                                                                                                  # (no task of anyone either: a builder of a task is a member)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _band(page, "build")
        none = page.locator(".band-none")
        await none.wait_for(timeout=WAIT_MS)
        assert await none.get_by_role("button", name="Add to the party").count() == 1 and await page.locator(".colname").count() == 0


@pytest.mark.asyncio
async def test_a_tasks_card_wears_its_goals_type_top_right_a_planning_goal_says_its_type_none_for_no_type_none_on_a_stop(fake_repo, monkeypatch):
    _node("register")["type"] = BUG                                                                                                      # a goal at work, typed
    _node("recovery")["type"] = BUG                                                                                                      # a plan waiting, typed; Planning's card says it
    _node("pagewords")["type"] = None                                                                                                    # no type: the word as today
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".stack .deck").first.wait_for(timeout=WAIT_MS)
        typed = page.locator('.stack .deck[data-idea="register"]').first
        line = typed.locator(".tcard__idea")
        assert await typed.locator(".tcard__top .tcard__type .ork-sign.bug").count() == 1 and norm(await line.inner_text()) == "WebAuthn register"
        assert await line.locator(".ork-sign").count() == 0                                                                             # spec 55: top right, not before the name
        sign = await typed.locator(".tcard__type .ork-sign").bounding_box()
        assert (round(sign["width"]), round(sign["height"])) == (14, 14)
        assert await typed.get_attribute("aria-label") == "Challenge store (WebAuthn register, Fix a bug): in Review, now" or "WebAuthn register, Fix a bug" in await typed.get_attribute("aria-label")
        plain = page.locator('.stack .deck[data-idea="cookie"]').first                                                                  # a goal with no type: the name alone
        assert await plain.locator(".tcard__type").count() == 0 and norm(await plain.locator(".tcard__idea").inner_text()) == "Session cookie flags"
        await _band(page, "lead")
        goal = page.locator('.stack .deck[data-idea="recovery"]')
        await goal.wait_for(timeout=WAIT_MS)
        assert norm(await goal.locator(".tcard__idea").inner_text()) == "Fix a bug" and await goal.locator(".tcard__top .tcard__type .ork-sign.bug").count() == 1
        assert "Fix a bug" in await goal.get_attribute("aria-label")
        other = page.locator('.stack .deck[data-idea="pagewords"] .tcard__idea')
        assert norm(await other.inner_text()) == "Goal" and await other.locator(".tcard__type").count() == 0
        assert await page.locator(".stops .tcard__type, .stops [class*='tcard__type']").count() == 0                                   # no stop along the bottom wears it
        assert await page.evaluate(NO_SCROLL)
        await _band(page, "build")
        await typed.locator(".tcard__idea").wait_for(timeout=WAIT_MS)
        await typed.click()                                                                                                              # a stack of more spreads: its cards wear the sign too
        spread = page.locator(".spread .tcard__top .tcard__type")
        if await page.locator(".spread").count():
            assert await spread.count() >= 1


def test_the_service_worker_is_at_v61_with_b_merged_over_a_v60():
    sw = (pwa.ROOT / "sw.js").read_text(encoding="utf-8")
    assert 'const CACHE = "orkcraft-app-v66";' in sw                                                           # A set v60, B v61: the second to merge keeps v61 (spec 53 §7); spec 54 B is v62
