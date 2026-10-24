"""Spec 55, the phone (docs/specs/55-type-top-right.md §1–§4): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py with a few goals given a type. A card's top
row holds its goal's element left and its goal's type's sign right (14 × 14, the element's colour, faint while the element is drawn dim); no card has a state sign in its top row, a
failure keeps its danger edge and its danger foot; the goal line is gone and a Planning card says no type word (spec 67 §2.2); a goal with no type has no type node; no stop along the
bottom wears a type; the Goals sheet's type sign has its goal's colour; 44 px targets and no sideways scroll."""
from __future__ import annotations

import pytest

from tests.test_pwa_arena_browser import SCENE, _scene  # noqa: F401
from tests.test_pwa_decks_browser import second_party  # noqa: F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _band, _phone  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

BUG = {"id": "bug", "name": "Fix a bug", "sign": "bug"}
BG = "e => getComputedStyle(e).backgroundColor"
PROBE = "(v) => { const i = document.createElement('i'); i.style.backgroundColor = `var(${v})`; document.body.append(i); const c = getComputedStyle(i).backgroundColor; i.remove(); return c; }"


def norm(s):
    return " ".join(s.split())


def _node(slug):
    return next(n for n in SCENE["map"]["nodes"] if n["slug"] == slug)


def _typed():
    for slug in ("register", "cookie", "recovery", "magic"):                                                                             # at work, a failure, a plan, a goal not read yet
        _node(slug)["type"] = BUG
    _node("pagewords")["type"] = None                                                                                                    # no type


async def _top(card):
    """The element's and the type's boxes of a card's top row."""
    return await card.locator(".tcard__top .ork-elem").bounding_box(), await card.locator(".tcard__top .tcard__type .ork-sign").bounding_box()


@pytest.mark.asyncio
async def test_a_typed_goals_card_has_its_type_top_right_in_its_elements_colour_the_state_sign_gone_the_failure_kept_by_its_edge_and_foot(fake_repo, monkeypatch):
    _typed()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _band(page, "build")
        card = page.locator('.stack .deck[data-idea="register"]').first
        await card.locator(".tcard__type").wait_for(timeout=WAIT_MS)
        elem, sign = await _top(card)
        assert (round(sign["width"]), round(sign["height"])) == (14, 14) and sign["x"] > elem["x"] + elem["width"] - 1                    # 14 × 14, right of the element
        assert abs(sign["y"] - elem["y"]) <= 3                                                                                          # on its row
        assert await card.locator(".tcard__type .ork-sign").evaluate(BG) == await card.locator(".tcard__top .ork-elem").evaluate(BG)     # its goal's colour
        assert await card.locator(".tcard__type .ork-sign").evaluate(BG) == await page.evaluate(PROBE, "--ork-elem-meadow")
        assert await card.locator(".tcard__type").get_attribute("data-type") == "bug" and await card.locator(".tcard__type .ork-sign").get_attribute("aria-hidden") == "true"
        assert await card.locator(".tcard__type .ork-sign").get_attribute("title") == "Fix a bug"
        assert await card.locator(".tcard__idea").count() == 0                                                                          # the goal's line is gone from the field's tokens (spec 67 §2.2)
        assert await page.locator(".tcard__mark, .tcard__top .ork-sign:not(.tcard__type .ork-sign)").count() == 0                       # no state sign on any card's top
        failed = page.locator('.deck[data-state="failed"]').first
        await failed.wait_for(timeout=WAIT_MS)
        danger = await page.evaluate("() => { const e = document.createElement('i'); e.style.color = 'var(--ork-danger)'; document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; }")
        face = failed.locator(".tcard")
        assert await face.evaluate("e => getComputedStyle(e).borderTopColor") == danger and "is-fail" in await face.get_attribute("class")   # the danger edge
        assert await face.locator(".tcard__foot").count() == 0 and "failed" in await failed.get_attribute("aria-label")                 # no value at its foot (spec 67 §2.4); its edge says it, its label says it
        assert await face.locator(".tcard__type .ork-sign").evaluate(BG) == await page.evaluate(PROBE, "--ork-elem-dust")               # a failed card's type is still its goal's colour
        assert await face.locator(".tcard__top .ork-sign").count() == 1                                                                 # the type's, nothing else
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_planning_card_says_its_type_or_goal_a_dim_goals_type_is_faint_a_goal_with_no_type_has_none_and_no_stop_wears_one(fake_repo, monkeypatch):
    _typed()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _band(page, "lead")
        plan = page.locator('.stack .deck[data-idea="recovery"]')
        await plan.locator(".tcard__type").wait_for(timeout=WAIT_MS)
        assert await plan.locator(".tcard__idea").count() == 0 and "Fix a bug" in await plan.get_attribute("aria-label")                   # the type's sign says it (spec 67 §2.2); its name stays in the label
        elem, sign = await _top(plan)
        assert sign["x"] > elem["x"] and (round(sign["width"]), round(sign["height"])) == (14, 14)
        assert await plan.locator(".tcard__type .ork-sign").evaluate(BG) == await plan.locator(".tcard__top .ork-elem").evaluate(BG) == await page.evaluate(PROBE, "--ork-elem-void")
        raw = page.locator('.stack .deck[data-idea="magic"]')
        await raw.locator(".tcard__type").wait_for(timeout=WAIT_MS)
        assert await raw.locator(".tcard__top .ork-elem.dim").count() == 1                                                              # a goal not read yet: its element is dim …
        assert await raw.locator(".tcard__type .ork-sign").evaluate(BG) == await page.evaluate(PROBE, "--ork-ink-faint")                 # … and so is its type
        assert await raw.locator(".tcard__type .ork-sign").evaluate(BG) == await raw.locator(".tcard__top .ork-elem").evaluate(BG)
        other = page.locator('.stack .deck[data-idea="pagewords"]')
        await other.wait_for(timeout=WAIT_MS)
        assert await other.locator(".tcard__idea").count() == 0 and await other.locator(".tcard__type").count() == 0                     # no type: the element alone (and no "Goal" word: spec 67 §2.2)
        assert await page.locator(".tcard__mark").count() == 0
        assert await page.locator(".stops .tcard__type, .stops [class*='tcard__type']").count() == 0                                   # no stop along the bottom wears one
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_spreads_cards_keep_the_phase_word_between_the_element_and_the_type_and_the_goals_sheet_draws_the_type_in_its_goals_colour(fake_repo, monkeypatch):
    _typed()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _band(page, "build")
        stack = page.locator('.stack .deck[data-idea="register"][data-n]:not([data-n="1"])').first
        await stack.wait_for(timeout=WAIT_MS)
        await stack.click()
        cards = page.locator(".spread .tcard")
        await cards.first.wait_for(timeout=WAIT_MS)
        assert await cards.count() >= 2
        for i in range(await cards.count()):
            card = cards.nth(i)
            elem, sign = await _top(card)
            phase = await card.locator(".tcard__phase").bounding_box()
            assert elem["x"] < phase["x"] < sign["x"] and await card.locator(".tcard__mark").count() == 0                                 # the element, the phase word, the type
            assert await card.locator(".tcard__idea .ork-sign").count() == 0
        await page.keyboard.press("Escape")
        await page.locator(".spread").wait_for(state="detached", timeout=WAIT_MS)
        await page.locator(".gbar__head").click()
        sheet = page.get_by_role("dialog", name="Goals")
        row = sheet.locator('.dk[data-idea="register"]')
        await row.locator(".dk__type").wait_for(timeout=WAIT_MS)
        assert await row.locator(".dk__type .ork-sign").evaluate(BG) == await row.locator(".pile__back .ork-elem").evaluate(BG) == await page.evaluate(PROBE, "--ork-elem-meadow")
        assert await row.locator(".dk__type").evaluate("e => e.nextSibling.textContent") == "WebAuthn register"                          # the list keeps its place: before the title
        plain = sheet.locator('.dk[data-idea="pagewords"]')
        assert await plain.locator(".dk__type").count() == 0
        for r in await sheet.locator(".dk__main").all():
            assert (await r.bounding_box())["height"] >= 44                                                                             # 44 px targets
        assert await page.evaluate(NO_SCROLL)
