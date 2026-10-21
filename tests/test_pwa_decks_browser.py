"""Spec 50 part C, the phone (docs/specs/50-parties-and-goals.md §6, §7 "C"): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py (a party, *Sign in with a
passkey*, of a leader, two builders and two checkers; goals in each stage, a goal's tasks in one phase after another, goals done and flagged). No lost tap (a redraw waits while a
pointer is down; the holds redraw only what they held back); the Projects sheet from the top bar and the menu without the projects; the party chips; the party bar and About this
party; the goals bar and its sheet with the filter; the rows by phase and the stacks of cards; a spread's strip; the create dial and New goal's turn; the flag line; 44 px targets;
the service worker."""
from __future__ import annotations

import pytest

from tests.test_pwa_arena_browser import SCENE, _scene  # noqa: F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _band, _called, _phone, _pop  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

TOP_POINT = """(b) => { const r = b.getBoundingClientRect();         // a point of the card's top that is its own (its neighbours in the fan lie over its sides)
  for (let y = r.top + 6; y < r.top + 40; y += 3) for (let x = r.left + 3; x < r.right - 2; x += 3) { const e = document.elementFromPoint(x, y); if (e && e.closest(".hc") === b) return { x, y }; }
  return null; }"""


async def _redrawn(stub, page, ms=700):
    """The Board changed and was read again (`ideas.map` asked once more), and the page had the time to draw it."""
    before = len([c for c in stub.calls if c[0] == "ideas.map"])
    stub.bump({})
    for _ in range(100):
        if len([c for c in stub.calls if c[0] == "ideas.map"]) > before:
            break
        await page.wait_for_timeout(50)
    await page.wait_for_timeout(ms)


# -- no lost tap (spec 50 §6.9) ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_tap_is_not_lost_to_a_redraw_between_its_down_and_its_up(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        band = page.locator('.band[data-band="lead"]')
        await band.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(300)
        box = await band.bounding_box()
        await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        await page.mouse.down()
        await band.evaluate("e => { window.__pressed = e; }")
        SCENE["map"]["nodes"][6]["tasks"][1]["state"] = "review"                       # the Board changes under the finger: the field would be drawn again
        await _redrawn(stub, page)
        assert await page.evaluate("() => window.__pressed.isConnected")                # … and is not, while the pointer is down
        await page.mouse.up()
        await page.locator('.band[data-band="lead"][aria-selected="true"]').wait_for(timeout=WAIT_MS)       # the click landed: one tap did it
        await page.wait_for_function("() => !window.__pressed.isConnected", timeout=WAIT_MS)                # and the postponed draw ran after it


@pytest.mark.asyncio
async def test_a_tap_on_a_stop_or_the_raised_one_is_not_lost_either(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        card = page.locator('.hc[data-kind="plan"]')
        await card.wait_for(timeout=WAIT_MS)
        at = await card.evaluate(TOP_POINT)
        await page.mouse.move(at["x"], at["y"])
        await page.mouse.down()
        await card.evaluate("e => { window.__pressed = e; }")
        SCENE["needs"] = [n for n in SCENE["needs"] if n["kind"] != "proposal"]        # a stop is answered elsewhere meanwhile: the fan would be laid again
        await _redrawn(stub, page)
        assert await page.evaluate("() => window.__pressed.isConnected")
        await page.mouse.up()
        raised = page.locator(".raised")
        await raised.wait_for(timeout=WAIT_MS)
        assert await raised.get_attribute("data-kind") == "plan"                       # the tap popped the stop it was on
        await page.keyboard.press("Escape")
        await page.wait_for_function("() => !window.__pressed.isConnected", timeout=WAIT_MS)
        assert await page.locator(".hc").count() == 5                                  # the postponed draw laid the fan again


@pytest.mark.asyncio
async def test_the_holds_redraw_the_field_only_when_they_held_a_redraw_back(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        card = page.locator('.stack[data-column="backend"] .tcard').first
        await card.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(2400)
        await page.evaluate("() => { window.__col = document.querySelector('.stack[data-column=\"backend\"]'); }")
        await card.focus()                                                             # the focus comes and goes: nothing was held back, so nothing is drawn again for it
        await page.evaluate("() => document.activeElement.blur()")
        await page.wait_for_timeout(500)
        assert await page.evaluate("() => window.__col.isConnected")
        await page.keyboard.press("Tab")                                               # the keyboard is in use: the focus ring shows, and holds the column
        await card.focus()
        SCENE["map"]["nodes"][6]["tasks"][1]["state"] = "review"                       # a change arrives while it is held
        await _redrawn(stub, page, 300)
        assert await page.evaluate("() => window.__col.isConnected")
        await page.evaluate("() => document.activeElement.blur()")                     # let go: what was held back is drawn now
        await page.wait_for_function("() => !window.__col.isConnected", timeout=WAIT_MS)
