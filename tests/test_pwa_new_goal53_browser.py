"""Spec 53 part B, the phone's New goal (docs/specs/53-phone-simpler.md §2, §4, §5 "B"): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py (a party, *Sign in
with a passkey*) and a second one, *Product*, each with its leader's goal types. The create button opens the form at once, sliding up in 180 ms (none of the lift, the deal or the turn; none
under reduced motion); the party first (the leader's head, *<leader> leads · k of n goals done*, the list of the parties with ✓ and *+ New party*, no Operations, a pick that deals that
party's types); the priority (*Low*'s line and *Keep for tonight*); the types' row (*Your own goal* first and picked when the form opens, then the most used first, its line; spec 61 C); one field, *The goal*; the asks, Refs and the join
line; a typed goal with no lens switch; what *Add the goal* sends; and *Fix a bug* in one screen."""
from __future__ import annotations

import copy

import pytest

from tests.test_pwa_arena_browser import SCENE, _scene  # noqa: F401
from tests.test_pwa_decks_browser import second_party
from tests.test_pwa_goal_types_browser import TYPES, _form, norm, typed
from tests.test_pwa_shell_browser import FAB, NO_SCROLL, WAIT_MS, Stub, _called, _phone

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

RECORD = """
window.__slides = [];
const _anim = Element.prototype.animate;
Element.prototype.animate = function (frames, options) {
  window.__slides.push({ el: this.tagName.toLowerCase() + '.' + (this.classList[0] || ''), ms: options && options.duration, easing: options && options.easing, frames: JSON.stringify(frames) });
  return _anim.call(this, frames, options);
};
"""


def two_parties(monkeypatch):
    """*Product* beside the party (the Board's and the map's), with its own types (the logo type only)."""
    typed(monkeypatch)
    real = Stub.commands

    def commands(self):
        got = real(self)

        def board(a):
            out = got["ideas.board"](a)
            return {**out, "tracks": [*out["tracks"], Stub.goal("product", "Product", "normal", "ready")]}
        return {**got, "ideas.board": board}
    monkeypatch.setattr(Stub, "commands", commands)
    second_party(stops=0)
    SCENE["map"]["goals"][1]["types"] = [copy.deepcopy(TYPES[1])]
    SCENE["map"]["goals"][1]["leader"] = {**SCENE["map"]["goals"][0]["leader"], "name": "Elder"}


@pytest.fixture(autouse=True)
def _fresh_scene(monkeypatch):
    saved = copy.deepcopy(SCENE)
    yield
    SCENE.clear()
    SCENE.update(saved)


@pytest.mark.asyncio
async def test_the_create_button_slides_the_form_up_in_one_animation_of_180_ms_and_down_again(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        fab = page.locator(FAB)
        await fab.wait_for(timeout=WAIT_MS)
        assert await fab.get_attribute("aria-label") == "New goal"
        before = len(await page.evaluate("() => window.__slides"))
        await fab.click()
        form = page.get_by_role("dialog", name="New goal")
        await form.wait_for(timeout=WAIT_MS)
        await page.wait_for_function("() => !document.getAnimations().some((a) => a.playState === 'running')", timeout=WAIT_MS)
        slides = (await page.evaluate("() => window.__slides"))[before:]
        assert len(slides) == 1 and slides[0]["el"] == "dialog.sheet" and slides[0]["ms"] == 180 and slides[0]["easing"] == "ease-out"       # one slide, a transform
        assert "translateY(100%)" in slides[0]["frames"] and "transform" in slides[0]["frames"] and "rotateY" not in slides[0]["frames"]
        assert await page.locator(".drawlayer, .typedeal, .typecard").count() == 0                                                         # no lift, no deal, no turn
        await form.get_by_role("button", name="Put it back").click()
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        slides = (await page.evaluate("() => window.__slides"))[before:]
        assert [s["ms"] for s in slides] == [180, 180] and "translateY(100%)" in slides[1]["frames"]                                       # and down again
        await fab.click()
        await form.wait_for(timeout=WAIT_MS)
        await page.keyboard.press("Escape")                                                                                                # Esc slides it down
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        await fab.click()
        await form.wait_for(timeout=WAIT_MS)
        await form.get_by_role("button", name="Close").click()
        await form.wait_for(state="hidden", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_under_reduced_motion_the_form_shows_and_goes_at_once(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await page.emulate_media(reduced_motion="reduce")
        await page.locator(FAB).wait_for(timeout=WAIT_MS)
        before = len(await page.evaluate("() => window.__slides"))
        form = await _form(page)
        await form.get_by_role("button", name="Put it back").click()
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        assert len((await page.evaluate("() => window.__slides"))[before:]) == 0


@pytest.mark.asyncio
async def test_the_party_comes_first_with_its_leaders_head_its_list_and_a_pick_that_deals_its_types(fake_repo, monkeypatch):
    two_parties(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page)
        order = await form.evaluate("e => [...e.querySelectorAll('.newgoal__party, .newgoal__goal, .newgoal__type, [aria-label=Priority]')].map((n) => n.className || n.getAttribute('aria-label'))")
        assert order[0].startswith("newgoal__party") and order.index("pills") < order.index("field newgoal__type") < order.index("field newgoal__goal")       # the party, the priority, the type, the goal
        btn = form.locator(".newgoal__party")
        box = await btn.bounding_box()
        assert round(box["height"]) == 52 and await btn.locator("img.ork-race__head").count() == 1
        head = await btn.locator("img.ork-race__head").bounding_box()
        assert (round(head["width"]), round(head["height"])) == (24, 22)
        assert norm(await btn.locator(".newgoal__name").inner_text()) == "Sign in with a passkey" and await btn.locator(".newgoal__name").evaluate("e => getComputedStyle(e).fontWeight") == "600"
        assert norm(await btn.locator(".newgoal__line").inner_text()) == "Taskmaster leads · 2 of 9 goals done" and await btn.locator(".ork-chev").count() == 1
        assert await form.get_by_role("listbox", name="Parties").is_hidden()
        await btn.click()
        listbox = form.get_by_role("listbox", name="Parties")
        opts = listbox.get_by_role("option")
        assert await opts.evaluate_all("els => els.map((e) => [e.dataset.goal, e.getAttribute('aria-selected')])") == [["passkey", "true"], ["product", "false"]]
        assert norm(await opts.first.inner_text()) == "Sign in with a passkey Taskmaster · 2 of 9 goals done" and await opts.first.locator(".ork-sign.check").count() == 1       # ✓ on the one picked
        assert norm(await opts.nth(1).inner_text()) == "Product Elder · 1 of 4 goals done" and await opts.nth(1).locator("img.ork-race__head").count() == 1
        assert "Operations" not in await form.inner_text()
        new = form.get_by_role("button", name="+ New party")
        assert "one of yours, or from the library" in await new.inner_text() and (await new.bounding_box())["height"] >= 44
        assert all([(await o.bounding_box())["height"] >= 44 for o in await opts.all()])
        await opts.nth(1).click()                                                                                                           # a pick closes the list and deals that party's types
        await listbox.wait_for(state="hidden", timeout=WAIT_MS)
        assert norm(await btn.locator(".newgoal__name").inner_text()) == "Product" and await btn.get_attribute("data-goal") == "product"
        assert await form.locator(".newgoal__chip").evaluate_all("els => els.map((e) => [e.dataset.type, e.getAttribute('aria-checked')])") == [["", "true"], ["logo", "false"]]     # one's own first, picked
        await form.locator('.newgoal__chip[data-type="logo"]').click()
        await form.get_by_label("The goal", exact=True).fill("A mark for Product")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add")
        sent = [a for n, a in stub.calls if n == "ideas.add"][-1]
        assert sent["track"] == "product" and sent["type"] == "logo" and sent["text"] == "A mark for Product"
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        form = await _form(page)                                                                                                            # the party shown is the one picked first
        assert await form.locator(".newgoal__party").get_attribute("data-goal") == "product"


@pytest.mark.asyncio
async def test_new_party_in_the_list_opens_new_party_and_esc_puts_the_list_away_first(fake_repo, monkeypatch):
    two_parties(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page)
        await form.locator(".newgoal__party").click()
        await page.keyboard.press("Escape")
        assert await form.get_by_role("listbox", name="Parties").is_hidden() and await form.is_visible()
        await form.locator(".newgoal__party").click()
        await form.get_by_role("button", name="+ New party").click()
        await page.get_by_role("dialog", name="New party").wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_the_priority_is_the_partys_and_low_says_it_waits_for_the_night_and_keeps_for_tonight(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page)
        assert await form.get_by_role("radio", name="High").is_checked()                                                                    # the party's own
        low = "Waits for the night: the leader reads it then."
        assert low not in await form.inner_text() and await form.get_by_role("button", name="Add the goal").is_visible()
        assert await form.get_by_role("radio", name="Normal").evaluate("e => e.parentElement.getBoundingClientRect().height") >= 44
        assert "High and Normal are drafted at once" not in await form.inner_text()                                                         # spec 50's hint is gone
        await form.get_by_role("radio", name="Low").click()
        assert low in await form.inner_text() and await form.get_by_role("button", name="Add the goal").count() == 0
        keep = form.get_by_role("button", name="Keep for tonight")
        await form.get_by_label("The goal", exact=True).fill("Someday")
        await keep.click()
        assert await _called(stub, "ideas.add", {"text": "Someday", "track": "passkey", "priority": "low"})                                 # one's own goal: no type
        await form.wait_for(state="hidden", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_the_types_row_deals_your_own_goal_first_and_picked_then_the_types_in_order_and_the_line_under_it(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page)
        row = form.get_by_role("radiogroup", name="Goal type")
        chips = row.get_by_role("radio")
        assert await chips.evaluate_all("els => els.map((e) => [e.dataset.type, e.getAttribute('aria-checked')])") == [["", "true"], ["bug", "false"], ["logo", "false"], ["screen", "false"], ["experiment", "false"]]
        assert [norm(t) for t in await chips.all_inner_texts()] == ["Your own goal", "Fix a bug", "New logo", "New screen", "Try an experiment"]       # one's own first, the types after it in their order
        assert all([(await c.bounding_box())["height"] >= 44 for c in await chips.all()])
        assert await chips.first.evaluate("e => getComputedStyle(e).borderStyle") == "dashed" and await chips.first.locator(".ork-sign").count() == 0 and await chips.first.get_attribute("class") == "newgoal__chip is-blank"
        assert await chips.nth(1).locator(".ork-sign.bug").count() == 1 and (await chips.nth(1).locator(".ork-sign").bounding_box())["width"] == 14
        assert await row.evaluate("e => getComputedStyle(e).overflowX") == "auto"                                                           # scrolls sideways when wider
        line, field = form.locator(".newgoal__typeline"), form.get_by_label("The goal", exact=True)
        assert norm(await line.inner_text()) == "In your words: the leader plans it like any other." and await line.evaluate("e => getComputedStyle(e).fontSize") == "11px"       # picked when the form opens
        assert await field.get_attribute("placeholder") == "What should become possible" and await form.locator(".newgoal__asks").is_hidden()
        await chips.nth(1).click()
        assert norm(await line.inner_text()) == "Something that goes wrong, made right" and await chips.nth(1).get_attribute("aria-checked") == "true" and await chips.first.get_attribute("aria-checked") == "false"
        assert await field.get_attribute("placeholder") == "In a line or a few"
        await chips.nth(2).click()
        assert norm(await line.inner_text()) == "A mark for the product, picked from a few" and await chips.nth(2).get_attribute("aria-checked") == "true" and await chips.nth(1).get_attribute("aria-checked") == "false"
        await chips.first.click()
        assert norm(await line.inner_text()) == "In your words: the leader plans it like any other." and await chips.first.get_attribute("aria-checked") == "true"
        assert await field.get_attribute("placeholder") == "What should become possible"
        for gone in ("No type", "A blank goal"):
            assert gone not in await form.inner_text()


@pytest.mark.asyncio
async def test_add_the_goal_with_your_own_goal_sends_no_type_and_a_tapped_type_is_sent(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page)
        await form.get_by_label("The goal", exact=True).fill("Make sign-in kinder")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add", {"text": "Make sign-in kinder", "track": "passkey", "priority": "high"})                     # picked at open: no `type`
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        form = await _form(page, "experiment")
        await form.get_by_label("The goal", exact=True).fill("Try a shorter sign-in")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add", {"text": "Try a shorter sign-in", "track": "passkey", "priority": "high", "type": "experiment"})
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        form = await _form(page, "bug")
        await form.locator('.newgoal__chip[data-type=""]').click()                                                                          # back to one's own: the type's ask is not sent
        await form.get_by_label("The goal", exact=True).fill("Again in my words")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add", {"text": "Again in my words", "track": "passkey", "priority": "high"})


@pytest.mark.asyncio
async def test_the_goal_is_one_field_and_the_old_lines_are_gone(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page, "bug")
        field = form.get_by_label("The goal", exact=True)
        assert await field.evaluate("e => e.tagName") == "TEXTAREA" and await field.get_attribute("rows") == "3"
        label = form.locator(".newgoal__goallabel")
        assert norm(await label.text_content()) == "The goalits first line is its title" and await label.locator("small").inner_text() == "its first line is its title"
        assert await form.get_by_role("button", name="Photo").is_visible()
        for gone in ("Its title", "What it is for"):
            assert await form.get_by_label(gone).count() == 0
        text = await form.inner_text()
        for gone in ("Its element marks every task of it.", "reads it next", "A blank goal for", "Priority High and Normal"):
            assert gone not in text
        assert await form.locator(".ork-elem").count() == 0
        await field.fill("Make sign-in kinder\n\nNo password: the phone's own unlock.")
        await form.get_by_label("What you did").fill("Tapped Sign in")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add", {"text": "Make sign-in kinder\n\nNo password: the phone's own unlock.", "track": "passkey", "priority": "high", "type": "bug", "asks": {"did": "Tapped Sign in"}})


@pytest.mark.asyncio
async def test_a_typed_goal_has_no_lens_switch_its_types_lens_is_open_and_your_own_goal_keeps_the_switch(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page)
        bar = form.get_by_role("radiogroup", name="Lens")
        await bar.get_by_role("radio", name="Text", exact=True).wait_for(timeout=WAIT_MS)                                                   # one's own goal, picked at open, keeps today's switch
        assert await bar.is_visible() and len(await bar.get_by_role("radio").all()) == 2
        await form.locator('.newgoal__chip[data-type="bug"]').click()
        await page.wait_for_timeout(300)
        assert await form.locator(".lens").is_hidden()                                                                                      # *Fix a bug*: a text lens shows nothing
        await form.locator('.newgoal__chip[data-type="logo"]').click()
        await form.get_by_role("group", name="The project's screens").wait_for(timeout=WAIT_MS)                                            # a screen lens: its own fields …
        assert await bar.is_hidden() and await form.locator(".lens .field-label", has_text="Lens").is_hidden()                              # … and no switch
        await form.locator('.newgoal__chip[data-type=""]').click()
        await bar.get_by_role("radio", name="Text", exact=True).wait_for(timeout=WAIT_MS)                                                   # one's own goal again: the switch
        assert await bar.is_visible() and len(await bar.get_by_role("radio").all()) == 2


@pytest.mark.asyncio
async def test_put_it_back_with_words_keeps_the_goal_for_tonight_and_never_sends_join(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page, "logo")
        join = form.locator('.joinline[data-agent="artist"]')
        assert await join.get_by_role("checkbox").is_checked() and "Artist joins the party" in await join.inner_text()
        assert await form.locator(".newgoal__refs").is_visible() and await form.get_by_label("What it should say").is_visible()
        await form.get_by_label("The goal", exact=True).fill("Kept for tonight")
        await form.get_by_role("button", name="Put it back").click()
        assert await _called(stub, "ideas.add", {"text": "Kept for tonight", "track": "passkey", "priority": "high", "night": True, "type": "logo"})


@pytest.mark.asyncio
async def test_fix_a_bug_fits_one_screen(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page, "bug")
        assert await form.evaluate("e => e.scrollHeight <= e.clientHeight") and await page.evaluate(NO_SCROLL)                              # three asks, no Refs: no scroll
        foot = await form.locator(".sheet-foot").bounding_box()
        assert foot["y"] + foot["height"] >= 844 - 2 and await form.get_by_label("What should have").is_visible()


@pytest.mark.asyncio
async def test_a_map_with_no_types_opens_the_form_with_no_goal_type_row(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page)
        assert await form.get_by_role("radiogroup", name="Goal type").count() == 0 and await form.get_by_label("The goal", exact=True).is_visible()
        await form.get_by_label("The goal", exact=True).fill("A plain goal")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add", {"text": "A plain goal", "track": "passkey", "priority": "high"})
