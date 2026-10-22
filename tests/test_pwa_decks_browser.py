"""Spec 50 part C, the phone (docs/specs/50-parties-and-goals.md §6, §7 "C"): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py (a party, *Sign in with a
passkey*, of a leader, two builders and two checkers; goals in each stage, a goal's tasks in one phase after another, goals done and flagged). No lost tap (a redraw waits while a
pointer is down; the holds redraw only what they held back); the party's deck and its sheet, the project's button and its sheet, the menu without the projects, Today in the menu; no chips row; the goals bar with the gate and About this
party; the goals sheet with the filter; the rows by phase and the stacks of cards; a spread's strip; the members' strip; the create button's deck and New goal's turn; the flag line; 44 px targets;
the service worker."""
from __future__ import annotations

import copy
import json
import re

import pytest

from tests.test_pwa_arena_browser import FLAG, SCENE, _about, _redrawn, _scene, member, node, task, BACKEND, OWN  # noqa: F401
from tests.test_pwa_shell_browser import FAB, NO_SCROLL, WAIT_MS, Stub, _band, _called, _menu, _new_goal, _phone, _pop, _today, _where  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

TOP_POINT = """(b) => { const r = b.getBoundingClientRect();         // a point of the card's top that is its own (its neighbours in the fan lie over its sides)
  for (let y = r.top + 6; y < r.top + 40; y += 3) for (let x = r.left + 3; x < r.right - 2; x += 3) { const e = document.elementFromPoint(x, y); if (e && e.closest(".hc") === b) return { x, y }; }
  return null; }"""


async def _reopen(page):
    """The page opened again, as a reload does: the app's own address, the pairing kept in the browser's storage (the old page's socket is let go first)."""
    url, ctx = page.url, page.context
    await page.close()
    fresh = await ctx.new_page()
    await fresh.goto(url)
    return fresh


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
        card = page.locator('.stack[data-column="backend"] .deck').first
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


# -- the parties' sheet from the party's deck, the projects' from the top bar (spec 50 §6.1, spec 52 §5.1, §5.3) -------------------------------------------------------------------------------------------------

@pytest.fixture
def projects(monkeypatch):
    state = {"current": "/work/alpha"}
    rows = [{"path": "/work/alpha", "name": "alpha", "working": 2, "needs_you": 1, "review": 0}, {"path": "/work/beta", "name": "beta", "working": 0, "needs_you": 0, "review": 3},
            {"path": "/work/gamma", "name": "gamma", "working": 0, "needs_you": 0, "review": 0}]
    real = Stub.commands

    def commands(self):
        def use(a):
            state["current"] = a["path"]
            self.calls.append(("projects.use", {"path": a["path"]}))
            return self.bump({"ok": True})

        def lst(a):
            self.calls.append(("projects.list", {}))
            return {"current": state["current"], "open": rows, "recent": [{"path": "/work/old", "name": "old"}]}
        return {**real(self), "projects.list": lst, "projects.use": use}
    monkeypatch.setattr(Stub, "commands", commands)


def second_party(stops=2):
    """A second party, *Product*, in the project, with `stops` questions waiting in it (the party's deck counts them)."""
    goal = copy.deepcopy(SCENE["map"]["goals"][0])
    goal.update(slug="product", title="Product", short="Product", ideas=4, done=1, usd=1.0, flags=0, waits_main=0, state="ready")
    SCENE["map"]["goals"].append(goal)
    for i in range(stops):
        SCENE["needs"].append({"kind": "asks", "idea": f"p{i}", "goal": "product", "title": f"A question {i}", "text": "Which one?", "questions": ["Which one?"], "priority": "normal", "blocks": False,
                               "at": "2026-10-21T10:00:00", "asked": []})


@pytest.mark.asyncio
async def test_the_partys_deck_opens_one_sheet_from_the_top_with_the_parties_and_new_party_and_the_project_button_the_projects(fake_repo, monkeypatch, projects):
    second_party()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        bar = page.locator(".board-bar")
        where = page.locator(".partydeck")
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        assert await where.evaluate("e => e.tagName") == "BUTTON" and await where.get_attribute("aria-haspopup") == "dialog"
        assert await where.locator(".ork-count.warning").inner_text() == "2"                                                          # the other parties' stops: this one's are the bottom row's
        assert "2 stops wait in the other parties" in await where.get_attribute("aria-label")                                          # a question elsewhere is never hidden
        menu = bar.get_by_role("button", name="Menu")
        assert await menu.get_attribute("aria-label") == "Menu: Stop all, Spend, Agents, Today and settings" and await bar.locator(".today").count() == 0
        await where.click()
        sheet = page.get_by_role("dialog", name="Parties")
        await sheet.locator(".where-row").first.wait_for(timeout=WAIT_MS)
        box = await sheet.bounding_box()
        assert box["x"] == 0 and box["y"] == 0 and box["width"] == 390 and box["height"] < 760                                          # one sheet from the top
        rows = sheet.locator(".where-row")
        assert [norm(await r.inner_text()) for r in await rows.all()] == ["Sign in with a passkey 2/9 done 4", "Product 1/4 done 2", "Operations"]      # the parties, then Operations
        assert [round((await r.bounding_box())["height"]) >= 52 for r in await rows.all()] == [True, True, True]                       # rows of 52 px at least
        first = rows.first
        assert await first.get_attribute("aria-current") == "true" and await rows.nth(1).get_attribute("aria-current") is None           # the picked one marked
        assert await first.locator("img.ork-race__head").get_attribute("src") == "races/peon-elder.png" and await first.locator(".ork-sign.work").count() == 1      # its leader's head, the work sign
        assert await first.locator(".ork-count.warning").inner_text() == "4" and await rows.nth(1).locator(".ork-sign.work").count() == 0
        new = sheet.get_by_role("button", name="+ New party")
        assert norm(await new.inner_text()) == "+ New party one of yours, or from the library" and (await new.bounding_box())["height"] >= 52
        assert await sheet.locator(".project-row, .projects-block").count() == 0                                                      # the projects are the project button's
        await rows.nth(1).click()                                                                                                      # a pick: kept and the sheet is put away
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        await page.locator('.partydeck[data-goal="product"]').wait_for(timeout=WAIT_MS)
        assert await where.locator(".ork-count.warning").inner_text() == "4" and norm(await page.locator(".gbar__head").inner_text()).startswith("Product ·")
        assert json.loads(await page.evaluate("() => localStorage.getItem('orkcraft.goal')")) == {"project": "product"}                 # `orkcraft.goal`, as today
        await where.click()
        await sheet.locator(".where-new").click()                                                                                      # + New party: its sheet
        await page.get_by_role("dialog", name="New party").wait_for(timeout=WAIT_MS)
        await page.keyboard.press("Escape")
        await bar.locator(".projbtn").click()                                                                                          # the project's button: the projects
        projects_ = page.get_by_role("dialog", name="Projects")
        await projects_.get_by_role("button", name=re.compile("^beta")).click()                                                       # a tap on another project switches this phone to it
        assert await _called(stub, "projects.use", {"path": "/work/beta"})
        await projects_.wait_for(state="hidden", timeout=WAIT_MS)
        drawer = await _menu(page)                                                                                                     # the menu: Stop all, Spend, Agents, Today and the settings
        text = await drawer.inner_text()
        assert await drawer.locator(".project-row").count() == 0 and "Other projects" not in text and "opened and closed at the computer" not in text
        assert "Stop all" in text and "Agents" in text and "this project" in text.lower() and "this phone" in text.lower() and await drawer.get_by_role("button", name=re.compile("^Flags")).count() == 0
        assert await page.evaluate(NO_SCROLL)


# -- the goals bar, its sheet and the filter (spec 50 §6.4) ----------------------------------------------------------------------------------------------

def norm(text):
    return " ".join(text.split())


@pytest.mark.asyncio
async def test_the_goals_bar_is_one_quiet_line_and_its_sheet_lists_what_is_at_work_in_planning_waiting_for_main_and_flagged(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        bar = page.locator(".gbar__head")
        await bar.wait_for(timeout=WAIT_MS)
        assert norm(await bar.inner_text()) == "Passkey · 2 of 9 goals done" and await bar.locator(".ork-chev").count() == 1          # ⌄ the party · k of n goals done
        box = await bar.bounding_box()
        assert round(box["height"]) == 44 and await bar.evaluate("e => getComputedStyle(e).fontSize") == "12px"                    # one quiet line, 44 px
        await bar.click()
        sheet = page.get_by_role("dialog", name="Goals")
        await sheet.wait_for(timeout=WAIT_MS)
        sb = await sheet.bounding_box()
        assert sb["x"] == 0 and sb["width"] == 390 and sb["y"] + sb["height"] == 844                                                   # from the bottom
        assert await sheet.locator(".sheet-head .ork-count").inner_text() == "9" and await sheet.locator('[data-act="show-all"]').is_hidden()      # Goals 9; no *Show all* while nothing is picked
        text = norm(await sheet.inner_text())
        assert "A tap shows only that goal’s tasks; tap more to add them. opens one." in text and await sheet.locator(".goals__how .ork-chev.right").count() == 1
        about = sheet.get_by_role("button", name=re.compile("^About "))                                                                # the head's *About Passkey ›*: it opens About this party
        assert norm(await about.inner_text()) == "About Passkey" and await about.locator(".ork-chev.right").count() == 1 and (await about.bounding_box())["height"] >= 44
        assert (await about.bounding_box())["y"] < (await sheet.locator(".goals__how").bounding_box())["y"]
        assert [await h.text_content() for h in await sheet.locator("h3").all()] == ["At work", "Planning", "Waits for main · 1", "Flags · 1"]       # (drawn in capitals)
        rows = sheet.locator(".dk")
        assert [await r.get_attribute("data-idea") for r in await rows.all()] == ["register", "signin", "cookie", "recovery", "second", "pagewords", "ratelimit", "magic", "log"]
        lines = {await r.get_attribute("data-idea"): norm(await r.locator(".dk__line").inner_text()) for r in await rows.all()}
        assert lines["register"] == "0/6 in dev · implementation" and lines["signin"] == "3/5 in dev · checking" and lines["cookie"] == "0/2 in dev · implementation"
        assert lines["recovery"] == "plan ready · $1–2" and lines["second"] == "asks you · Reviewer" and lines["pagewords"] == "proposed" and lines["ratelimit"] == "Taskmaster is reading"
        assert lines["magic"] == "new · tonight" and lines["log"] == "new · Taskmaster reads it later"
        marks = {await r.get_attribute("data-idea"): await r.locator(".dk__mark .ork-sign").get_attribute("class") if await r.locator(".dk__mark .ork-sign").count() else "" for r in await rows.all()}
        assert marks["register"] == "ork-sign work" and marks["cookie"] == "ork-sign cross" and marks["recovery"] == "ork-sign alert" and marks["ratelimit"] == "ork-sign work" and marks["magic"] == ""
        assert "asks" not in await rows.nth(3).get_attribute("class") and await rows.nth(3).locator(".dk__mark .ork-sign.alert").count() == 1     # a goal that asks you: its sign, no alert edge (spec 52 §5.8)
        for r in await rows.all():
            assert (await r.locator(".dk__main").bounding_box())["height"] >= 52 and (await r.locator(".dk__open").bounding_box())["width"] == 44       # 52 px rows, › 44 px wide
        pile = rows.nth(0).locator(".pile")                                                                                           # its pile: a back with its element, edges behind it for its open tasks
        assert await pile.locator(".pile__back .ork-elem.meadow").count() == 1 and await pile.locator(".pile__edge").count() == 3
        assert await rows.nth(7).locator(".ork-elem.lava.dim").count() == 1 and await rows.nth(7).locator(".pile__edge").count() == 0          # a goal not read yet: its element dim
        waits = sheet.locator(".goals__line").filter(has=page.locator(".ork-sign.check"))
        assert [norm(await w.inner_text()) for w in await waits.all()] == ["Where the credentials are kept · in dev"]                 # ✓ done, in dev, waiting for main
        flags = sheet.locator(".goals__flag")
        assert [norm(await f.inner_text()) for f in await flags.all()] == ["Passkey button on the sign-in page · 14 Oct · ≈$2.10 · 4 of 4 first time"]
        assert await flags.locator(".ork-sign.flag").count() == 1
        await rows.nth(0).locator(".dk__open").click()                                                                                # › opens one, on its own screen
        await page.locator(".screen").wait_for(state="visible", timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "idea", "ref": "register", "device": "phone", "via": "map"})
        await page.get_by_role("button", name="Back", exact=True).click()
        assert await sheet.is_hidden()                                                                                                # the sheet was put away


@pytest.mark.asyncio
async def test_a_tap_picks_a_goal_more_add_and_the_filter_leaves_only_their_cards_results_and_stops(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".gbar__head").wait_for(timeout=WAIT_MS)
        backend, screens, fan = '.stack[data-column="backend"] .deck:not(.is-leaving)', '.stack[data-column="screens"] .deck:not(.is-leaving)', ".hc"

        async def keys(selector):
            return [await d.get_attribute("data-key") for d in await page.locator(selector).all()]
        assert await keys(backend) == ["register|now", "cookie|now", "register|next"] and await page.locator(fan).count() == 6
        await page.locator(".gbar__head").click()
        sheet = page.get_by_role("dialog", name="Goals")
        register = sheet.locator('.dk__main[data-idea="register"]')
        await register.click()                                                                                                        # a tap picks it
        await sheet.locator('.dk__main[data-idea="register"][aria-pressed="true"]').wait_for(timeout=WAIT_MS)                        # (the sheet is drawn again just after the tap)
        assert await register.locator(".dk__check .ork-sign.check").count() == 1
        assert await sheet.locator('[data-act="show-all"]').is_visible()                                                              # *Show all* appears
        await page.wait_for_function("() => document.querySelectorAll('.stack[data-column=\"backend\"] .deck:not(.is-leaving)').length === 2", timeout=WAIT_MS)
        assert await keys(backend) == ["register|now", "register|next"] and await keys(screens) == ["register|now", "register|later"]      # the columns: only its stacks
        assert [await b.get_attribute("data-kind") for b in await page.locator(fan).all()] == ["look"]                                 # the bottom row: only its results (and stops: it has none)
        assert await page.locator(".board-bar .ork-count, .partydeck .ork-count").count() == 0                                         # no count of the party shown's stops: the bottom row is it
        await sheet.locator('.dk__main[data-idea="cookie"]').click()                                                                  # more add to it
        await page.wait_for_function("() => document.querySelectorAll('.hc').length === 2", timeout=WAIT_MS)
        await page.wait_for_function("() => document.querySelectorAll('.stack[data-column=\"backend\"] .deck:not(.is-leaving)').length === 3", timeout=WAIT_MS)
        assert await keys(backend) == ["register|now", "cookie|now", "register|next"] and [await b.get_attribute("data-kind") for b in await page.locator(fan).all()] == ["failed", "look"]
        await page.keyboard.press("Escape")
        bar = page.locator(".gbar")
        assert norm(await bar.locator(".gbar__head").inner_text()) == "Passkey 2 of 9 goals" and norm(await bar.locator(".gbar__all").inner_text()) == "Show all"
        assert await bar.locator(".ork-elem.meadow").count() == 1 and await bar.locator(".ork-elem.dust").count() == 1 and await bar.locator(".gbar__gate").is_visible()   # the picked goals' elements, *k of n goals*, *Show all*, the gate
        assert (await bar.bounding_box())["height"] == 44 and (await bar.locator('[data-act="show-all"]').bounding_box())["height"] >= 44
        await _band(page, "lead")                                                                                                     # Planning: only the picked goals' cards (none of these is in Planning)
        assert await page.locator(".stack[data-column=\"taskmaster\"] .deck").count() == 0 and "Nothing of these goals" in await page.locator(".stack[data-column=\"taskmaster\"]").inner_text()
        await _band(page, "build")
        await page.locator(".gbar__all").click()                                                                                      # Show all clears the filter
        await page.wait_for_function("() => document.querySelectorAll('.hc').length === 6", timeout=WAIT_MS)
        await page.locator(".gbar:not(.is-on)").wait_for(timeout=WAIT_MS)                                                             # (the bar is drawn again with the field)
        assert norm(await page.locator(".gbar__head").inner_text()) == "Passkey · 2 of 9 goals done" and await keys(backend) == ["register|now", "cookie|now", "register|next"]
        await page.locator(".gbar__head").click()                                                                                     # a goal of Planning: a member with none of its work says so
        await sheet.locator('.dk__main[data-idea="recovery"]').click()
        await page.keyboard.press("Escape")
        await page.wait_for_function("() => document.querySelectorAll('.stack[data-column=\"backend\"] .stack__empty').length === 1", timeout=WAIT_MS)
        assert await page.locator('.stack[data-column="backend"] .stack__empty').inner_text() == "Nothing of these goals"
        assert [await b.get_attribute("data-kind") for b in await page.locator(fan).all()] == ["plan"]
        page = await _reopen(page)                                                                                                    # the picks are the session's: not kept across a reload
        await page.locator(".gbar__head").wait_for(timeout=WAIT_MS)
        assert norm(await page.locator(".gbar__head").inner_text()) == "Passkey · 2 of 9 goals done"


# -- rows by phase and the stacks (spec 50 §3.4, §6.5) ----------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_card_is_132_by_185_wears_its_goals_element_and_a_raw_goal_is_dashed_with_its_element_dim(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        failed = page.locator('.stack[data-column="backend"] .deck[data-key="cookie|now"]')
        await failed.wait_for(timeout=WAIT_MS)
        box = await failed.locator(".tcard").bounding_box()
        assert abs(box["width"] - 132) <= 1 and abs(box["height"] - 185) <= 1 and abs(box["height"] / box["width"] - 7 / 5) < 0.02          # 132 × 185, 5:7, two columns at 390
        cols = [await c.bounding_box() for c in await page.locator(".stack[data-column]").all()]
        assert len(cols) == 2 and abs(cols[0]["width"] - cols[1]["width"]) <= 1 and cols[1]["x"] > cols[0]["x"] + cols[0]["width"] - 1
        assert await failed.locator(".tcard__top .ork-elem.dust").count() == 1 and await failed.locator(".tcard__mark .ork-sign.cross").count() == 1    # the element top left, the mark top right
        assert await failed.locator(".tcard__idea").inner_text() == "Session cookie flags" and await failed.locator(".tcard__name").inner_text() == "Secure cookie flags"
        assert await failed.locator(".tcard__foot").inner_text() == "failed" and "is-fail" in await failed.get_attribute("class")
        assert await failed.locator(".tcard").evaluate("e => getComputedStyle(e).borderColor") == await page.evaluate(
            "(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-danger)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")   # a failure has the danger edge
        every = await page.locator(".deck:not(.is-leaving)").count()
        assert every == 6 and await page.locator(".deck .tcard__top .ork-elem").count() == every                                      # an element on every card
        stack = page.locator('.stack[data-column="backend"] .deck[data-key="register|now"]')
        assert await stack.locator(".deck__edge").count() == 1 and await stack.locator(".deck__n").inner_text() == "×2"             # a stack of two: an edge behind it, ×2 on its corner
        edge = await stack.locator(".deck__edge").bounding_box()
        front = await stack.locator(".tcard").bounding_box()
        assert round(edge["x"] - front["x"]) == 4 and round(front["y"] - edge["y"]) == 4                                               # offset 4 px up and to the right
        await _band(page, "lead")                                                                                                     # Planning: a goal a card, two to a row, centred, 16 px apart
        cards = [await c.bounding_box() for c in await page.locator('.stack[data-column="taskmaster"] .deck').all()]
        assert len(cards) == 6 and len({round(b["y"]) for b in cards[:2]}) == 1 and round(cards[1]["x"] - (cards[0]["x"] + cards[0]["width"])) == 16
        assert abs((cards[0]["x"] + cards[1]["x"] + cards[1]["width"]) / 2 - 195) <= 1 and all(abs(b["width"] - 132) <= 1 and abs(b["height"] - 185) <= 1 for b in cards)
        raw = page.locator('.deck[data-idea="magic"] .tcard')
        assert "is-raw" in await raw.get_attribute("class") and await raw.evaluate("e => getComputedStyle(e).borderStyle") == "dashed" and await raw.locator(".ork-elem.lava.dim").count() == 1
        stop = page.locator('.deck[data-idea="recovery"] .tcard')
        assert await stop.locator(".ork-elem.void:not(.dim)").count() == 1 and await stop.locator(".tcard__mark .ork-sign.alert").count() == 1 and await stop.locator(".tcard__idea").inner_text() == "Goal"
        assert await stop.locator(".tcard__foot").inner_text() == "plan ready · $1–2"                                                  # its words at the foot
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_phase_of_a_task_is_its_wave_against_its_goals_lowest_open_wave_in_every_stage(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        phases = """(c) => [...document.querySelectorAll(`.stack[data-column="${c}"] .phase`)].map((p) => [p.dataset.phase, [...p.querySelectorAll('.deck')].map((d) => d.dataset.key.split('|')[0] + (d.dataset.n === '1' ? '' : '×' + d.dataset.n))])"""
        await page.locator(".deck").first.wait_for(timeout=WAIT_MS)
        assert await page.evaluate(phases, "backend") == [["now", ["register×2", "cookie"]], ["next", ["register"]]]                   # wave 1, 1 and 2 of the register goal; 1 of the cookie goal
        assert await page.evaluate(phases, "screens") == [["now", ["register", "cookie"]], ["later", ["register"]]]                   # its wave 3 is two after the goal's current one
        await _band(page, "check")                                                                                                    # the checkers' columns the same: a check's phase is its wave against its goal's
        await page.locator('.stack[data-column="reviewer"]').wait_for(timeout=WAIT_MS)
        assert await page.evaluate(phases, "reviewer") == [["now", ["signin"]], ["later", ["register"]]]
        assert await page.evaluate(phases, "words") == [["now", ["signin"]]]
        for t in SCENE["map"]["nodes"][6]["tasks"]:
            if t["id"] in ("k1", "k2", "k3"):
                t["state"] = "merged"                                                                                                  # the goal's wave 1 is done: what was next is now
        await _redrawn(stub, page)
        await _band(page, "build")
        assert await page.evaluate(phases, "backend") == [["now", ["register", "cookie"]]]
        assert await page.evaluate(phases, "screens") == [["now", ["cookie"]], ["next", ["register"]]]                               # wave 3 is one after wave 2 now
        assert await page.locator(".phase__lbl").evaluate_all("els => els.map((e) => e.textContent)") == ["now", "now", "next"]


# -- a spread (spec 50 §3.6, §6.6) ---------------------------------------------------------------------------------------------------------------------

RECORD_DEAL = """
(() => {
  window.__deal = [];
  const animate = Element.prototype.animate;
  Element.prototype.animate = function (frames, options) {
    if (this.classList && (this.classList.contains('spread__card') || this.classList.contains('drawcard'))) window.__deal.push({ el: this.classList[0], key: this.dataset.key || '', ms: options && options.duration, delay: options && options.delay, easing: options && options.easing, from: frames[0] && frames[0].transform, to: frames[frames.length - 1] && frames[frames.length - 1].transform, n: frames.length });
    return animate.call(this, frames, options);
  };
})();
"""


def dependent_wave():
    """The register goal's *Register endpoint* is in the first wave too, after the other two: a stack of three at *now*, one of them waiting for two and one waiting for it."""
    for t in SCENE["map"]["nodes"][6]["tasks"]:
        if t["id"] == "k5":
            t["wave"] = 1


@pytest.mark.asyncio
async def test_a_press_on_a_stack_of_more_spreads_its_cards_in_a_strip_with_their_dependency_lines_and_a_press_on_one_opens_it(fake_repo, monkeypatch):
    dependent_wave()
    async with _phone(fake_repo, monkeypatch, init=RECORD_DEAL) as (stub, page):
        stack = page.locator('.stack[data-column="backend"] .deck[data-key="register|now"]')
        await stack.wait_for(timeout=WAIT_MS)
        assert await stack.get_attribute("data-n") == "3" and await stack.locator(".deck__edge").count() == 2 and await stack.locator(".deck__n").inner_text() == "×3"     # two edges behind, ×3
        await page.locator('.stack[data-column="backend"] .deck[data-key="cookie|now"]').click()                                      # a stack of one opens its task
        await page.locator(".screen").wait_for(state="visible", timeout=WAIT_MS)
        assert await _called(stub, "ideas.task", {"slug": "cookie", "task": "q1"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await stack.click()                                                                                                           # a stack of more spreads
        spread = page.locator(".spread")
        await spread.wait_for(timeout=WAIT_MS)
        assert await spread.get_attribute("aria-label") == "WebAuthn register · 3 tasks of Backend at this phase" and norm(await spread.locator(".spread__cap").inner_text()) == "WebAuthn register · 3 tasks of Backend at this phase"
        cards = spread.locator(".spread__card")
        assert await cards.count() == 3
        await page.wait_for_timeout(600)                                                                                              # the deal is over
        boxes = [await c.bounding_box() for c in await cards.all()]
        assert all(round(b["width"]) == 172 and round(b["height"]) == 240 for b in boxes)                                            # 172 × 240
        row = spread.locator(".spread__row")
        style = await row.evaluate("e => [getComputedStyle(e).scrollSnapType, getComputedStyle(e).overflowX, e.scrollWidth > e.clientWidth]")
        assert style[0].startswith("x mandatory") and style[1] == "auto" and style[2] is True                                        # in a row that scrolls sideways, snapping to a card
        assert await cards.first.evaluate("e => getComputedStyle(e).scrollSnapAlign") == "center start center" or "center" in await cards.first.evaluate("e => getComputedStyle(e).scrollSnapAlign")
        sb, wrap = await spread.bounding_box(), await page.locator(".boardwrap").bounding_box()
        assert round(sb["x"]) == round(wrap["x"]) and round(sb["height"]) == round(wrap["height"])                                    # over the field
        assert await spread.evaluate("e => getComputedStyle(e).backgroundColor") != "rgba(0, 0, 0, 0)"                               # … which it dims
        first = cards.nth(0)
        assert await first.locator(".tcard__name").inner_text() == "Credential table and migration" and await first.locator(".tcard__phase").inner_text() == "now"
        assert await first.locator(".tcard__top .ork-elem.meadow").count() == 1 and await first.locator(".tcard__mark .ork-sign.work").count() == 1
        assert norm(await first.locator(".spread__dep").inner_text()) == "1 waits for it" and await first.locator(".spread__dep .ork-sign.after").count() == 1      # no arrows on the phone: a line
        last = cards.nth(2)
        deps = [norm(await d.inner_text()) for d in await last.locator(".spread__dep").all()]
        assert deps == ["waits for Challenge store and Credential table and migration", "1 waits for it"]
        assert await last.locator(".spread__dep .ork-sign.before").count() == 1 and await last.locator(".tcard__foot").inner_text() == "after k1, k2"
        deal = [d for d in await page.evaluate("() => window.__deal") if d["el"] == "spread__card"]
        assert len(deal) == 3 and {d["ms"] for d in deal} == {300} and [d["delay"] for d in deal] == [0, 35, 70] and {d["easing"] for d in deal} == {"steps(6)"}    # dealt: ≈ 0.3 s, 35 ms apart, in steps
        await cards.nth(2).click()                                                                                                    # a press on one opens it
        await page.locator(".screen").wait_for(state="visible", timeout=WAIT_MS)
        assert await _called(stub, "ideas.task", {"slug": "register", "task": "k5"})
        await page.get_by_role("button", name="Back", exact=True).click()
        assert await spread.is_visible()                                                                                              # the spread stays under that screen
        await spread.get_by_role("button", name="Put them back").click()                                                              # Put them back gathers them
        await spread.wait_for(state="detached", timeout=WAIT_MS)
        await stack.click()
        await spread.wait_for(timeout=WAIT_MS)
        await page.keyboard.press("Escape")                                                                                           # Esc too
        await spread.wait_for(state="detached", timeout=WAIT_MS)
        await stack.click()
        await spread.wait_for(timeout=WAIT_MS)
        await spread.click(position={"x": 4, "y": 4})                                                                                 # and a tap on the dimmed field
        await spread.wait_for(state="detached", timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_spread_holds_its_cards_while_it_is_open_closes_itself_when_its_stack_is_gone_and_none_is_dealt_under_reduced_motion(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD_DEAL) as (stub, page):
        await page.emulate_media(reduced_motion="reduce")
        stack = page.locator('.stack[data-column="backend"] .deck[data-key="register|now"]')
        await stack.wait_for(timeout=WAIT_MS)
        await stack.click()
        spread = page.locator(".spread")
        await spread.wait_for(timeout=WAIT_MS)
        assert await page.evaluate("() => window.__deal") == [] and await spread.evaluate("e => e.getAnimations({ subtree: true }).length") == 0      # none dealt under reduced motion
        SCENE["map"]["nodes"][6]["tasks"][1]["title"] = SCENE["map"]["nodes"][6]["tasks"][1]["short"] = "Renamed while it is open"            # the Board moves on
        await _redrawn(stub, page)
        assert await spread.locator(".spread__card").count() == 2 and await spread.locator(".tcard__name").first.inner_text() == "Credential table and migration"      # it holds its cards
        for t in SCENE["map"]["nodes"][6]["tasks"]:
            if t["id"] in ("k1", "k2"):
                t["state"] = "merged"                                                                                                  # its stack is gone
        await _redrawn(stub, page)
        await spread.wait_for(state="detached", timeout=WAIT_MS)                                                                      # it closes itself
        await stack.wait_for(state="detached", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_the_cards_of_a_spread_are_gathered_by_the_deal_backwards_under_motion(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD_DEAL) as (stub, page):
        stack = page.locator('.stack[data-column="backend"] .deck[data-key="register|now"]')
        await stack.wait_for(timeout=WAIT_MS)
        await stack.click()
        spread = page.locator(".spread")
        await spread.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(500)
        await spread.get_by_role("button", name="Put them back").click()
        assert "is-gathering" in await spread.get_attribute("class")                                                                 # not gone at once: the cards go back to the stack
        deal = [d for d in await page.evaluate("() => window.__deal") if d["el"] == "spread__card"]
        gather = deal[2:]                                                                                                              # the deal's two, then the gathering's two
        assert len(gather) == 2 and {d["ms"] for d in gather} == {300} and [d["delay"] for d in gather] == [35, 0] and gather[0]["to"].startswith("translate(") and gather[0]["from"] == "none"
        await spread.wait_for(state="detached", timeout=WAIT_MS)


# -- the members and their columns: one sideways strip (spec 50 §6.5) ---------------------------------------------------------------------------------------

GOBLIN = {"craft": "data", "race": "goblin", "tier": "warrior"}
DATA = {"slug": "data", "name": "Data"}
POINTERS = "(() => { window.__pointers = []; for (const t of ['pointerdown', 'pointerup', 'pointercancel']) window.addEventListener(t, () => window.__pointers.push(t), true); })();"


def three_builders():
    """A third builder, *Data*, with a task of its own: the Implementation stage has three members."""
    goal = SCENE["map"]["goals"][0]
    goal["party"].insert(3, member(DATA, "build", GOBLIN, "work"))
    goal["team"].insert(2, {"slug": "data", "name": "Data", "head": GOBLIN, "checks": False, "every": False})
    for n in SCENE["map"]["nodes"]:
        if n["slug"] == "register":
            t = task("d1", "Numbers of the sign-in", "running", {"slug": "screens", "name": "Screens"}, 1)
            t["by"], t["head"] = DATA, GOBLIN
            n["tasks"].append(t)


async def _swipe(page, x, y, dx):
    """A finger drags sideways on the strip: a touch scroll (the browser ends the pointer with `pointercancel`)."""
    cdp = await page.context.new_cdp_session(page)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    steps = 12
    for i in range(1, steps + 1):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x + dx * i / steps, "y": y}]})
        await page.wait_for_timeout(16)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    await page.wait_for_timeout(700)


@pytest.mark.asyncio
async def test_three_members_are_one_sideways_strip_of_148_px_columns_snapped_with_the_third_peeking_and_the_cards_keep_their_size(fake_repo, monkeypatch):
    three_builders()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _band(page, "build")
        scroller = page.locator(".arena-scroll")
        await page.locator(".pair").nth(2).wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(500)
        pairs = [await p.bounding_box() for p in await page.locator(".pair").all()]
        assert [round(b["width"]) for b in pairs] == [148, 148, 148]                                                                  # a fixed width: 148 px
        assert round(pairs[0]["x"]) == 12 and round(pairs[1]["x"]) == 166 and round(pairs[2]["x"]) == 320                              # two whole, the third peeking …
        assert round(390 - pairs[2]["x"]) == 70                                                                                       # … about 70 px of it
        css = await scroller.evaluate("e => ({ snap: getComputedStyle(e).scrollSnapType, bar: getComputedStyle(e).scrollbarWidth, x: getComputedStyle(e).overflowX, w: e.scrollWidth, c: e.clientWidth })")
        assert css["snap"] == "x mandatory" and css["bar"] == "none" and css["x"] == "auto" and css["w"] > css["c"]                    # snapping, no scrollbar drawn, scrolling
        assert await page.locator(".pair").first.evaluate("e => getComputedStyle(e).scrollSnapAlign") == "start"                      # to a column's start
        for pair in await page.locator(".pair").all():                                                                                # the member never separates from its tasks
            token, column = await pair.locator(".token").bounding_box(), await pair.locator(".stack").bounding_box()
            box = await pair.bounding_box()
            assert abs(token["x"] + token["width"] / 2 - (column["x"] + column["width"] / 2)) <= 1 and token["y"] < column["y"] and abs(box["x"] - column["x"]) <= 1
        sizes = {(round(b["width"]), round(b["height"])) for b in [await c.locator(".tcard").bounding_box() for c in await page.locator(".pair .deck:not(.is-leaving)").all()]}
        assert sizes == {(132, 185)}                                                                                                  # the cards stay 132 × 185
        assert await page.evaluate(NO_SCROLL) and await page.evaluate("() => document.scrollingElement.scrollLeft") == 0              # the strip scrolls, the page does not
        await _swipe(page, 250, 500, -120)                                                                                            # a swipe scrolls it and snaps
        left = await scroller.evaluate("e => e.scrollLeft")
        assert round(left) in (90, 154), left                                                                                         # the last column cannot reach the edge: it rests at the end, whole
        last = await page.locator(".pair").nth(2).bounding_box()
        assert 390 - 12 - 1 <= last["x"] + last["width"] <= 390 - 12 + 1                                                              # the third whole, with the gutter after it
        await _swipe(page, 250, 500, 200)
        assert round(await scroller.evaluate("e => e.scrollLeft")) == 0                                                               # and back to the first
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_two_members_or_fewer_share_the_width_with_no_scroll_and_the_cards_stay_132_by_185_centred(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _band(page, "build")
        await page.locator(".pair").nth(1).wait_for(timeout=WAIT_MS)
        scroller = page.locator(".arena-scroll")
        css = await scroller.evaluate("e => ({ w: e.scrollWidth, c: e.clientWidth })")
        assert css["w"] <= css["c"] and await page.locator(".strip.is-few").count() == 1                                              # nothing to scroll
        pairs = [await p.bounding_box() for p in await page.locator(".pair").all()]
        assert len(pairs) == 2 and abs(pairs[0]["width"] - pairs[1]["width"]) <= 1 and pairs[0]["width"] > 148 and round(pairs[0]["x"]) == 12     # the columns share the width
        assert round(pairs[1]["x"] + pairs[1]["width"]) == 378
        for pair in await page.locator(".pair").all():
            box = await pair.bounding_box()
            for deck in await pair.locator(".deck:not(.is-leaving) .tcard").all():
                d = await deck.bounding_box()
                assert (round(d["width"]), round(d["height"])) == (132, 185) and abs(d["x"] + d["width"] / 2 - (box["x"] + box["width"] / 2)) <= 8           # 132 × 185, centred in its column
        await _band(page, "lead")                                                                                                     # one member (the leader): one column across the width
        await page.locator(".pair").first.wait_for(timeout=WAIT_MS)
        assert await page.locator(".pair").count() == 1 and await page.locator(".strip.is-few").count() == 1
        css = await scroller.evaluate("e => ({ w: e.scrollWidth, c: e.clientWidth })")
        assert css["w"] <= css["c"]


@pytest.mark.asyncio
async def test_a_swipe_on_the_strip_is_a_scroll_not_a_tap_and_it_never_holds_a_redraw_back(fake_repo, monkeypatch):
    three_builders()
    async with _phone(fake_repo, monkeypatch, init=POINTERS) as (stub, page):
        await _band(page, "build")
        await page.locator(".pair").nth(2).wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(400)
        await page.evaluate("() => { window.__pointers = []; }")
        await _swipe(page, 250, 500, -150)                                                                                            # a pointer goes down on a card and turns into a scroll
        got = await page.evaluate("() => window.__pointers")
        assert got[0] == "pointerdown" and "pointercancel" in got and await page.locator(".screen").count() == 0 or not await page.locator(".screen").is_visible()    # (the browser cancels the pointer; no tap opened a task)
        for n in SCENE["map"]["nodes"]:                                                                                               # the Board changes: it is drawn at once, nothing waits for a pointer that is gone
            if n["slug"] == "register":
                n["tasks"].append(task("d2", "A later task of Data", "waiting", {"slug": "screens", "name": "Screens"}, 3))
                n["tasks"][-1]["by"], n["tasks"][-1]["head"] = DATA, GOBLIN
        stub.bump({})
        await page.locator('.stack[data-column="data"] .deck[data-key="register|next"], .stack[data-column="data"] .deck[data-key="register|later"]').first.wait_for(timeout=WAIT_MS * 2)
        assert await page.evaluate("() => document.getAnimations().filter((a) => a.playState === 'running').length") >= 0
        assert await page.locator(".arena-scroll").evaluate("e => e.scrollLeft") > 0                                                  # the strip stayed where it was scrolled


# -- the create button, a face-down deck, and New goal's card (spec 50 §6.7, §4.2) ------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_goal_turns_a_blank_card_over_from_the_button_to_the_middle_then_the_full_screen_form_opens(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD_DEAL) as (stub, page):
        fab = page.locator(FAB)
        await fab.wait_for(timeout=WAIT_MS)
        fb = await fab.bounding_box()
        await fab.click()                                                                                                             # one tap: the top card lifts, turns over and grows
        layer = page.locator(".drawlayer")
        await layer.wait_for(timeout=WAIT_MS)                                                                                         # the blank card turns …
        assert await page.locator("dialog.full[open]").count() == 0                                                                   # … and the form is not open yet
        turn = [d for d in await page.evaluate("() => window.__deal") if d["el"] == "drawcard"]
        assert len(turn) == 1 and turn[0]["ms"] == 500 and turn[0]["easing"] == "steps(8)" and "rotateY(0deg)" in turn[0]["from"] and "rotateY(180deg)" in turn[0]["to"]     # ≈ 0.5 s, in steps, turned over
        assert turn[0]["n"] == 3                                                                                                      # lifted off the deck first, then turned and grown
        m = re.search(r"translate\((-?\d+)px, (-?\d+)px\)", turn[0]["from"])
        assert abs(fb["x"] + fb["width"] / 2 - 195 - int(m.group(1))) <= 2 and abs(fb["y"] + fb["height"] / 2 - 422 - int(m.group(2))) <= 2                       # it starts at the button, ends in the middle
        assert await layer.locator(".drawcard__back .ork-icon").count() == 1                                                          # a back with orkUI's plus
        form = page.get_by_role("dialog", name="New goal")
        await form.wait_for(timeout=WAIT_MS)                                                                                          # then the form
        await layer.wait_for(state="detached", timeout=WAIT_MS)
        box = await form.bounding_box()
        assert box["x"] == 0 and box["y"] == 0 and box["width"] == 390 and box["height"] == 844                                      # full-screen
        assert norm(await form.locator(".newgoal__head").inner_text()) == "A blank goal for Sign in with a passkey · the Taskmaster reads it next"
        assert await form.locator(".newgoal__el .ork-elem.big.lava").count() == 1 and "Its element marks every task of it." in await form.inner_text()      # the element it will get, shown, never named
        assert not re.search(r"lava|meadow|dust|void|ice\b", await form.inner_text())
        add = form.get_by_role("button", name="Add the goal")
        assert await add.is_disabled() and await form.get_by_role("button", name="Put it back").is_visible()
        assert await form.get_by_label("Its title").is_visible() and await form.get_by_label("What it is for").is_visible() and await form.get_by_label("Party").input_value() == "passkey"
        await form.get_by_label("Its title").fill("Let people sign in on a phone")
        await form.get_by_label("What it is for").fill("No password: the phone's own unlock.")
        await add.click()
        assert await _called(stub, "ideas.add", {"text": "Let people sign in on a phone\n\nNo password: the phone's own unlock.", "track": "passkey", "priority": "high"})
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        await fab.click()                                                                                                             # Put it back with words in it keeps the goal for tonight
        await form.wait_for(timeout=WAIT_MS)
        await form.get_by_label("Its title").fill("Only a title")
        await form.get_by_role("button", name="Put it back").click()
        assert await _called(stub, "ideas.add", {"text": "Only a title", "track": "passkey", "priority": "high", "night": True})


@pytest.mark.asyncio
async def test_under_reduced_motion_the_form_opens_at_once_with_no_card_turned(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD_DEAL + "(() => { window.__layers = 0; document.addEventListener('DOMContentLoaded', () => new MutationObserver((ms) => { for (const m of ms) for (const n of m.addedNodes) if (n.classList && n.classList.contains('drawlayer')) window.__layers += 1; }).observe(document.body, { childList: true })); })();") as (stub, page):
        await page.emulate_media(reduced_motion="reduce")
        fab = page.locator(FAB)
        await fab.wait_for(timeout=WAIT_MS)
        await fab.click()
        await page.get_by_role("dialog", name="New goal").wait_for(timeout=WAIT_MS)
        assert await page.evaluate("() => window.__layers") == 0 and await page.evaluate("() => window.__deal") == [] and await page.locator(".drawlayer").count() == 0


@pytest.mark.asyncio
async def test_new_party_is_the_where_sheets_and_opens_the_new_party_sheet(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(FAB).wait_for(timeout=WAIT_MS)
        await _new_goal(page)                                                                                                         # one of yours, or from the library: the New party sheet
        sheet = page.get_by_role("dialog", name="New party")
        await sheet.wait_for(timeout=WAIT_MS)
        assert await sheet.get_by_role("button", name="Save party").is_disabled() and await sheet.get_by_label("What it is for").is_visible()
        assert await sheet.get_by_role("heading", name="The party").count() == 1 and await sheet.get_by_role("heading", name="Checks on every goal").count() == 1
        text = await sheet.inner_text()
        assert not re.search(r"\b[Ii]deas?\b", text) and "Description" not in text
        await sheet.get_by_label("What it is for").fill("A team for the sign-in.")
        await sheet.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save")
        sent = [a for n, a in stub.calls if n == "ideas.goal_save"][0]
        assert sent["about"] == "A team for the sign-in." and sent["craft"] == "engineering" and sent["priority"] == "normal" and "title" not in sent


# -- the flag line (spec 50 §6.8, §3.8) ---------------------------------------------------------------------------------------------------------------

def flagged(slug="kept", at="2026-10-21T11:00:00"):
    for n in SCENE["map"]["nodes"]:
        if n["slug"] == slug:
            n["flag"] = {**FLAG, "at": at, "tasks": 2, "first_time": 1, "usd": 0.8}
    SCENE["map"]["goals"][0]["flags"] = len([n for n in SCENE["map"]["nodes"] if n["flag"]])


@pytest.mark.asyncio
async def test_the_flag_line_is_said_once_after_a_gate_merge_that_raised_flags_and_its_press_opens_its_flags(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(500)
        assert await page.locator(".flagline").count() == 0                                                                           # the first start keeps the flags of before and says none
        key = json.loads(await page.evaluate("() => localStorage.getItem('orkcraft.flags.goals')"))
        assert len(key) == 1 and list(key.values())[0] > 0                                                                           # the newest seen, per project
        flagged()                                                                                                                      # the gate took a goal into main
        await _redrawn(stub, page)
        line = page.locator(".flagline")
        await line.wait_for(timeout=WAIT_MS)
        assert norm(await line.inner_text()) == "1 flag raised · Where the credentials are kept is in main"
        assert await line.locator(".ork-sign.flag").count() == 1 and await line.locator(".ork-sign.flag").evaluate("e => getComputedStyle(e).color") == await page.evaluate(
            "(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-success)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")      # ⚑ in the success colour
        goals, flag, bands = await page.locator(".gbar").bounding_box(), await line.bounding_box(), await page.locator(".bands").bounding_box()
        assert round(flag["y"]) == round(goals["y"] + goals["height"]) and round(bands["y"]) == round(flag["y"] + flag["height"]) and flag["height"] >= 44      # under the goals bar, over nothing of the work
        close = line.get_by_role("button", name="Close")
        cb = await close.bounding_box()
        assert round(cb["width"]) >= 44 and round(cb["height"]) >= 44 and await close.locator(".ork-icon").count() == 1                # its × 44 px, orkUI's icon
        await page.locator(".gbar__head").click()                                                                                     # its goal's row in *Flags* is lit once
        sheet = page.get_by_role("dialog", name="Goals")
        row = sheet.locator('.goals__flag[data-idea="kept"]')
        await row.wait_for(timeout=WAIT_MS)
        assert "is-reward" in await row.get_attribute("class") and "is-reward" not in await sheet.locator('.goals__flag[data-idea="button"]').get_attribute("class")
        await page.wait_for_function("() => !document.querySelector('.goals__flag.is-reward')", timeout=3000)
        await page.keyboard.press("Escape")
        await line.locator(".flagline__body").click()                                                                                 # its press opens About this party at *Its flags*
        about = page.get_by_role("dialog", name="About this party")
        await about.wait_for(timeout=WAIT_MS)
        flags = about.locator('[data-sec="Its flags"]')
        assert norm(await flags.inner_text()).lower().startswith("its flags") and await flags.locator(".party-about__flag").count() == 2
        fb, ab = await flags.bounding_box(), await about.bounding_box()
        assert fb["y"] >= ab["y"] and fb["y"] + fb["height"] <= ab["y"] + ab["height"]                                                # in view: it is scrolled to (a short sheet has nothing to scroll)
        await page.keyboard.press("Escape")
        await close.click()                                                                                                           # × puts it away
        await line.wait_for(state="detached", timeout=WAIT_MS)
        await _redrawn(stub, page)
        assert await page.locator(".flagline").count() == 0                                                                           # and it is not said again
        page = await _reopen(page)
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(800)
        assert await page.locator(".flagline").count() == 0                                                                           # not after a reload either: said once per device


@pytest.mark.asyncio
async def test_the_flag_lines_words_for_one_two_and_more_goals(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        got = await page.evaluate("""async () => {
          const { flagLine, freshFlags, flagTally } = await import('./shell-goals-words.js');
          const f = (short) => ({ short });
          return [flagLine([f('A')]), flagLine([f('A'), f('B')]), flagLine([f('A'), f('B'), f('C'), f('D')]),
            freshFlags([{ slug: 'a', flag: { at: '2026-10-14T10:00:00' } }, { slug: 'b', flag: { at: '2026-10-21T10:00:00' } }, { slug: 'c', flag: null }], Date.parse('2026-10-15T00:00:00')).fresh.map((x) => x.slug),
            flagTally({ at: '2026-10-14T16:20:00', tasks: 4, first_time: 3, usd: 2.1 }), flagTally({ at: 'x', tasks: 0, usd: null })]; }""")
        assert got[0] == {"head": "1 flag raised", "tail": "A is in main"} and got[1] == {"head": "2 flags raised", "tail": "A and B are in main"}
        assert got[2] == {"head": "4 flags raised", "tail": "A, B and 2 more are in main"} and got[3] == ["b"]
        assert got[4] == "14 Oct · ≈$2.10 · 3 of 4 first time" and got[5] == ""


# -- the look: orkUI's own symbols, 44 px targets, the words (spec 50 §0, §6.8) ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_typed_symbol_stands_in_for_an_orkui_sign_and_no_old_word_is_on_the_page(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".deck").first.wait_for(timeout=WAIT_MS)
        glyphs = re.compile("[✓✗↻☾⚑←→]")                                                                                              # in what is drawn (an aria-label is words for a reader)
        old = re.compile(r"\b[Ii]deas?\b|\bIn play\b|\b[Dd]ecks?\b|\b[Hh]and\b|\b[Ss]tacks?\b|\b[Ss]pread\b|\b[Ee]lements?\b|\b[Cc]ards?\b")
        async def texts():
            return await page.evaluate("() => document.body.innerText + ' ' + [...document.querySelectorAll('[aria-label], [title]')].map((e) => (e.getAttribute('aria-label') || '') + ' ' + (e.getAttribute('title') || '')).join(' ')")
        for opener in (None, ".gbar__head", ".partydeck", ".board-bar .projbtn", "about", "today", "menu"):
            if opener == "about":
                await _about(page)
            elif opener == "today":
                await _today(page)
            elif opener == "menu":
                await _menu(page)
            elif opener:
                await page.locator(opener).click()
            if opener:
                await page.wait_for_timeout(400)
            text = await texts()
            seen = await page.evaluate("() => document.body.innerText")
            assert not glyphs.findall(seen), (opener, glyphs.findall(seen))
            assert not old.findall(text), (opener, old.findall(text))
            if opener:
                await page.keyboard.press("Escape")
        raised = await _pop(page, "To look at: Challenge store")
        assert not glyphs.findall(await raised.inner_text()) and await raised.locator(".raised__text .ork-sign.check").count() == 1       # a result's tests: orkUI's check
        await page.keyboard.press("Escape")
        await _band(page, "build")
        await page.locator(".deck.is-many").first.click()
        await page.locator(".spread").wait_for(timeout=WAIT_MS)
        assert not glyphs.findall(await page.evaluate("() => document.body.innerText")) and not old.findall(await texts())


@pytest.mark.asyncio
async def test_every_new_target_is_a_finger_wide(fake_repo, monkeypatch):
    flagged()
    async with _phone(fake_repo, monkeypatch, init="localStorage.setItem('orkcraft.flags.goals', '{\"project\": 1}');") as (stub, page):
        await page.locator(".deck").first.wait_for(timeout=WAIT_MS)
        small = []
        for selector in (".board-name", ".gbar__gate", ".gbar__head", ".band", ".token", ".deck", ".flagline__body", ".flagline__close", FAB):
            for e in await page.locator(selector).all():
                b = await e.bounding_box()
                if b and (b["height"] < 44 or (selector in (FAB, ".flagline__close") and b["width"] < 44)):
                    small.append((selector, b["width"], b["height"]))
        assert not small, small
        await page.locator(".gbar__head").click()
        sheet = page.get_by_role("dialog", name="Goals")
        for selector in (".dk__main", ".dk__open"):
            for e in await sheet.locator(selector).all():
                b = await e.bounding_box()
                assert b["height"] >= 44 and (selector != ".dk__open" or b["width"] >= 44), (selector, b)
        await page.keyboard.press("Escape")
        await page.locator(".deck.is-many").first.click()
        spread = page.locator(".spread")
        await spread.wait_for(timeout=WAIT_MS)
        assert [(await b.bounding_box())["height"] >= 44 for b in await spread.get_by_role("button").all()] == [True, True, True]      # the two cards and *Put them back*
