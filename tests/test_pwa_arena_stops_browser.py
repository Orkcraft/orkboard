"""Spec 49 part C, the phone's bottom (docs/specs/49-one-window.md §10.6, §13 "C"): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py. What waits for you lies along
the bottom, fanned across the whole width and centred (3, 6, 8 and 10 of them), no line over it and no count beside it; a tap pops one out, its quick answers send their commands
with `via: "hand"`, *Open it on its own screen*; the create button floats over the field's bottom right and covers no task, its three ways and what each opens; a push's `#needs`
arrival; the 44 px targets."""
from __future__ import annotations

import pytest

from tests.test_pwa_arena_browser import SCENE, _scene, member, OWN, result  # noqa: F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _band, _called, _dial, _phone, _pop  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

FAB = '.fab[data-act="create"]'
MORE = [("register", "WebAuthn register", "k2", "Credential table and migration"), ("register", "WebAuthn register", "k3", "Register screen"),
        ("register", "WebAuthn register", "k4", "Wire the screen to the endpoint"), ("register", "WebAuthn register", "k5", "Register endpoint")]
EXTENT = """() => { const r = [...document.querySelectorAll('.hand .hc')].map((b) => b.getBoundingClientRect());
  return { n: r.length, left: Math.min(...r.map((x) => x.left)), right: Math.max(...r.map((x) => x.right)) }; }"""
UNDER = """(fab) => { const r = fab.getBoundingClientRect(), hit = new Set();
  for (let y = r.top + 2; y < r.bottom - 1; y += 4) for (let x = r.left + 2; x < r.right - 1; x += 4) { const e = document.elementFromPoint(x, y); hit.add(e && (e.closest('.fab') ? 'fab' : e.className || e.tagName)); }
  return [...hit]; }"""


def with_stops(n):
    """The scene with `n` things waiting: its four stops first, then results to look at; fewer than four keep the first ones."""
    stops = SCENE["needs"]
    SCENE["needs"] = stops[: min(n, len(stops))]
    want = n - len(SCENE["needs"])
    pool = SCENE["results"][:2] + [result(i, t, k, title) for i, t, k, title in MORE]
    SCENE["results"] = pool[:want]
    return n


@pytest.mark.asyncio
@pytest.mark.parametrize("n", [3, 6, 8, 10])
async def test_the_fan_lies_across_the_width_centred_inside_the_screen_and_the_create_button_covers_none_of_it(fake_repo, monkeypatch, n):
    with_stops(n)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(400)
        got = await page.evaluate(EXTENT)
        assert got["n"] == n and await page.locator(".handcount").count() == 0                       # as many as wait, and no number beside them
        assert got["left"] >= 0 and got["right"] <= 390                                              # inside the screen …
        assert abs((got["left"] + got["right"]) / 2 - 195) <= 2                                      # … centred on it
        if n >= 6:
            assert got["right"] - got["left"] > 270                                                  # across the whole width, not a part of it
        overlap = [await b.evaluate("e => getComputedStyle(e).marginLeft + ' ' + getComputedStyle(e).marginRight") for b in await page.locator(".hand .hc").all()]
        assert overlap[0].startswith("0px ") and overlap[-1].endswith(" 0px")                          # the first and the last keep no outer negative margin
        side = max(8, -(-(n * 104 - 330) // (n - 1) // 2)) if n > 1 else 0
        assert overlap[1] == f"-{side}px -{side}px" or n == 2                                        # overlapping each side so that they fit (a reset of buttons' margins does not undo it)
        fab = page.locator(FAB)
        box = await fab.bounding_box()
        assert round(box["x"]) == 330 and round(box["y"] + box["height"]) == 844 - 56 - 10 and box["width"] == 48     # over the field's bottom right, 10 px above the row
        assert await fab.evaluate(UNDER) == ["fab"]                                                  # nothing lies over it: no fan item reaches its box
        row = await page.locator(".handzone").bounding_box()
        assert box["y"] + box["height"] + 10 <= row["y"] + 1 and abs(row["height"] - 56) < 1            # the row is 56 px, the button over it


@pytest.mark.asyncio
async def test_the_create_button_covers_no_task_at_the_end_of_a_queue_nor_of_a_solo(fake_repo, monkeypatch):
    backend = SCENE["map"]["nodes"][6]                                                               # the register idea: a long queue for Backend and for Screens
    for i in range(10):
        backend["tasks"].append({**backend["tasks"][3], "id": f"x{i}", "title": f"Another task {i}", "short": f"Another task {i}", "wave": 3 + i, "after": []})
        backend["tasks"].append({**backend["tasks"][2], "id": f"y{i}", "title": f"A screen {i}", "short": f"A screen {i}", "state": "waiting", "wave": 3 + i, "after": []})
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".tcard").first.wait_for(timeout=WAIT_MS)
        fab = await page.locator(FAB).bounding_box()
        for column in ("backend", "screens"):                                                          # the queues scroll inside their columns, to their far ends
            await page.locator(f'.stack[data-column="{column}"]').evaluate("e => { e.scrollTop = e.scrollHeight; }")
        await page.wait_for_timeout(200)
        right = [await c.bounding_box() for c in await page.locator('.stack[data-column="screens"] .tcard').all()]
        assert right and all(b["y"] + b["height"] <= fab["y"] + 1 or b["y"] >= fab["y"] + fab["height"] or b["x"] + b["width"] <= fab["x"] for b in right if b["y"] < 844)   # the right-most queue ends above it
        assert max(b["y"] + b["height"] for b in right) <= fab["y"] + 1
        await page.locator('.token[data-member="screens"]').click()                                    # a solo: its body keeps the room too
        await page.locator(".solo__body").evaluate("e => { e.scrollTop = e.scrollHeight; }")
        await page.wait_for_timeout(200)
        cards = [await c.bounding_box() for c in await page.locator(".solo .tcard").all()]
        assert max(b["y"] + b["height"] for b in cards) <= fab["y"] + 1
        pad = await page.locator(".solo__body").evaluate("e => getComputedStyle(e).paddingBottom")
        assert pad == "64px"


@pytest.mark.asyncio
async def test_the_stops_lie_along_the_bottom_with_no_line_over_them_and_a_tap_pops_one_out_and_a_tap_on_the_scrim_lays_it_back(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        row = page.locator(".handzone")
        box = await row.bounding_box()
        assert round(box["height"]) == 56 and round(box["y"] + box["height"]) == 844 and await row.evaluate("e => getComputedStyle(e).borderTopWidth") == "0px"      # 56 px, no line over it
        assert [await b.get_attribute("data-kind") for b in await page.locator(".hc").all()] == ["plan", "asks", "proposal", "failed", "look", "look"]      # the stops, then the results
        assert "is-look" in await page.locator('.hc[data-kind="look"]').first.get_attribute("class")
        card = page.locator('.hc[data-kind="plan"]')
        raised = await _pop(page, "Plan ready: Recovery codes")
        assert "is-pop" in await raised.get_attribute("class")                                         # it leaps from its place (in steps)
        assert "is-up" in await card.get_attribute("class") and await card.evaluate("e => getComputedStyle(e).visibility") == "hidden"     # its place in the fan stays empty
        assert await page.locator(".hc").count() == 6
        await page.mouse.click(8, 8)                                                                   # a tap on the scrim (outside the card) lays it back
        await raised.wait_for(state="hidden", timeout=WAIT_MS)
        assert "is-up" not in await card.get_attribute("class") and await page.evaluate(NO_SCROLL)
        raised = await _pop(page, "Plan ready: Recovery codes")
        await raised.get_by_role("button", name="Put it back").click()
        await raised.wait_for(state="hidden", timeout=WAIT_MS)
        raised = await _pop(page, "Plan ready: Recovery codes")                                        # Esc too
        await page.keyboard.press("Escape")
        await raised.wait_for(state="hidden", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_under_reduced_motion_a_stop_pops_with_no_leap(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.emulate_media(reduced_motion="reduce")
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        raised = await _pop(page, "Plan ready: Recovery codes")
        assert "is-pop" not in await raised.get_attribute("class") and await raised.evaluate("e => e.getAnimations().length") == 0


@pytest.mark.asyncio
async def test_each_stop_answers_in_one_tap_with_the_commands_the_hand_sends(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        plan = await _pop(page, "Plan ready: Recovery codes")
        assert [await b.inner_text() for b in await plan.locator(".raised__quick button").all()] == ["Start the work", "Open the plan"]
        assert "$1–2" in await plan.locator(".raised__top .ork-gem").inner_text() and await plan.locator(".raised__text").inner_text() == "2 tasks, 1 check"
        await plan.get_by_role("button", name="Start the work").click()
        assert await _called(stub, "ideas.start", {"slug": "recovery", "via": "hand"})
        await plan.wait_for(state="hidden", timeout=WAIT_MS)
        ask = await _pop(page, "Asks you: Passkey on a second device")
        choices = ask.locator(".raised__quick button.answer")
        assert [await b.inner_text() for b in await choices.all()] == ["Yes, every passkey of that person", "● Only the lost phone’s passkey", "Ask the person when they report it"]   # the recommended one marked
        assert "primary" in await choices.nth(1).get_attribute("class")
        await choices.nth(1).click()
        assert await _called(stub, "ideas.answer", {"slug": "second", "answers": ["Only the lost phone’s passkey"]})
        await ask.wait_for(state="hidden", timeout=WAIT_MS)
        prop = await _pop(page, "Proposed: Words of the sign-in page")
        assert [await b.inner_text() for b in await prop.locator(".raised__quick button").all()] == ["Take", "No"]
        await prop.get_by_role("button", name="Take").click()
        assert await _called(stub, "ideas.proposal", {"slug": "pagewords", "take": True, "priority": "high"})
        await prop.wait_for(state="hidden", timeout=WAIT_MS)
        failed = await _pop(page, "Failed: Secure cookie flags")
        assert "danger" in await failed.get_attribute("class") and await failed.locator(".ork-gem").first.inner_text() == "✗"
        await failed.get_by_role("button", name="Start again").click()
        assert await _called(stub, "ideas.start", {"slug": "cookie", "via": "hand"})
        await failed.wait_for(state="hidden", timeout=WAIT_MS)
        look = await _pop(page, "To look at: Challenge store")                                         # a result: Review's answers, no alert colour
        assert "alert" not in await look.get_attribute("class")
        await look.get_by_role("button", name="Open it on its own screen").click()                     # … and its own screen, with Back
        screen = page.locator(".screen")
        await screen.wait_for(state="visible", timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "result", "ref": "register/k1", "device": "phone", "via": "hand"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await screen.wait_for(state="hidden", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_the_dial_has_three_ways_above_the_button_and_each_opens_its_sheet(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        fab = page.locator(FAB)
        await fab.wait_for(timeout=WAIT_MS)
        await fab.click()
        menu = page.get_by_role("menu", name="Create")
        items = menu.get_by_role("menuitem")
        assert [(await i.locator("b").inner_text()).lower() for i in await items.all()] == ["new idea", "new goal", "add to the party"]     # New idea nearest the thumb: the last of the column
        boxes = [await i.bounding_box() for i in await items.all()]
        close = await menu.get_by_role("button", name="Close").bounding_box()
        assert boxes[2]["y"] < boxes[1]["y"] < boxes[0]["y"] < close["y"] and all(b["height"] >= 48 for b in boxes)           # stacked above the button, which turned to ×
        subs = [await i.locator(".dial__sub").inner_text() for i in await items.all()]
        assert subs == ["for Sign in with a passkey", "its title, what done means, its party", "1 free seat in this party"]
        assert await items.nth(0).evaluate("e => getComputedStyle(e.querySelector('b')).color") == await page.evaluate(
            "(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-action)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")   # its label in the action colour
        await items.nth(0).click()
        sheet = page.get_by_role("dialog", name="New idea")
        await sheet.wait_for(timeout=WAIT_MS)
        assert await sheet.get_by_label("Goal").input_value() == "passkey"
        await page.keyboard.press("Escape")
        await _dial(page, "New goal")
        await page.get_by_role("dialog", name="New goal").wait_for(timeout=WAIT_MS)
        await page.keyboard.press("Escape")
        await _dial(page, "Add to the party")
        assert await _called(stub, "ideas.goal", {"slug": "passkey"})
        await page.get_by_role("dialog", name="Team").wait_for(timeout=WAIT_MS)                       # Edit the party
        await page.keyboard.press("Escape")
        await fab.click()                                                                              # × closes it, and so does a tap on the scrim
        await menu.get_by_role("button", name="Close").click()
        await menu.wait_for(state="hidden", timeout=WAIT_MS)
        await fab.click()
        await page.locator("dialog.dial-dlg").click(position={"x": 8, "y": 8})
        await menu.wait_for(state="hidden", timeout=WAIT_MS)
        SCENE["map"]["goals"][0]["party"].append(member({"slug": "extra", "name": "Extra"}, "build", OWN))        # three builders: the seats are full
        stub.bump({})
        await page.locator(".token").nth(2).wait_for(timeout=WAIT_MS * 2)
        await fab.click()
        assert await menu.get_by_role("menuitem").nth(2).locator(".dial__sub").inner_text() == "the party is full: change a member"


@pytest.mark.asyncio
async def test_a_pushs_needs_arrival_shows_the_goal_of_the_first_stop_and_pops_it(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, extra="&needs&from=push-needs") as (stub, page):
        raised = page.locator(".raised")
        await raised.wait_for(timeout=WAIT_MS)
        assert await page.locator('.gchip[data-goal="passkey"]').get_attribute("aria-pressed") == "true"
        assert await raised.get_attribute("data-kind") == "plan"                                       # the first stop, in the host's order
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "push", "ref": "needs", "device": "phone"})
        assert "from=push" not in page.url


@pytest.mark.asyncio
async def test_every_target_is_a_finger_wide(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        small = []
        for selector in (".gchip", ".ibar__head", ".band", ".token", ".gate__btn", ".tcard", FAB, ".board-bar .bar-btn"):
            for e in await page.locator(selector).all():
                b = await e.bounding_box()
                if b and b["height"] < 44 or (b and selector == FAB and b["width"] < 44):
                    small.append((selector, b["width"], b["height"]))
        assert not small, small
        assert round((await page.locator(FAB).bounding_box())["width"]) >= 44 and round((await page.locator(".hc").first.bounding_box())["width"]) >= 100
        raised = await _pop(page, "Plan ready: Recovery codes")
        heights = [await b.evaluate("e => e.offsetHeight") for b in await raised.locator(".raised__quick button, .raised > button").all()]       # (the card still leaps: its box is read unturned)
        assert heights and all(h >= 44 for h in heights)
        await page.keyboard.press("Escape")
        await page.locator(FAB).click()
        items = [(await i.bounding_box())["height"] for i in await page.get_by_role("menuitem").all()]
        assert len(items) == 3 and all(h >= 48 for h in items)
