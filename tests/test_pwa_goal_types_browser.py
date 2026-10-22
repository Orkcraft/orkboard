"""Spec 52 part C, the phone (docs/specs/52-goal-types.md §5, §6, §7 "C"): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py (a party, *Sign in with a passkey*, of a
leader, two builders and two checkers), its map given the party's goal types. The top bar's project button and its Projects sheet (no party, no count); the goals bar that says the party; the stage
switch that wears the party's faces (side by side, the words whole at 390, the empty head, no number, the signs on the faces, the labels); the party's deck at the goals bar's left (the other parties' count, its sheet, a pick
kept); a band with no one and *Add to the party*; the form by a type (its asks, Refs, the type's lens first, the join line's three shapes and what *Add the goal* sends); a plan's missing line and its answers; the signs without the alert edges; 44 px
targets; the service worker's version."""
from __future__ import annotations

import copy
import re

import pytest

from orkboard.gui import pwa
from tests.test_pwa_arena_browser import SCENE, _scene, task, BACKEND  # noqa: F401
from tests.test_pwa_decks_browser import projects, second_party  # noqa: F401
from tests.test_pwa_shell_browser import FAB, NO_SCROLL, WAIT_MS, Stub, _band, _called, _phone, _pop, _where  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

ART = {"kind": "art", "words": "pixel art", "agent": "artist", "name": "Artist", "band": "build", "free": True, "out": []}
A11Y = {"kind": "a11y", "words": "accessibility", "agent": "accessibility-reviewer", "name": "Accessibility reviewer", "band": "check", "free": False,
        "out": [{"slug": "words", "name": "Words", "runs": 1}, {"slug": "reviewer", "name": "Reviewer", "runs": 6}]}
EXPERIMENT = {"kind": "experiment", "words": "experiments", "agent": "experimenter", "name": "Experimenter", "band": "build", "free": False, "out": []}
TYPES = [
    {"id": "bug", "name": "Fix a bug", "sign": "bug", "line": "Something that goes wrong, made right", "lens": "text", "refs": False, "used": 3, "missing": [],
     "asks": [{"id": "did", "label": "What you did", "hint": "the steps, in order"}, {"id": "happened", "label": "What happened", "hint": "what you saw"},
              {"id": "expected", "label": "What should have", "hint": "what you expected"}]},
    {"id": "logo", "name": "New logo", "sign": "logo", "line": "A mark for the product, picked from a few", "lens": "screen", "refs": True, "used": 1, "missing": [ART],
     "asks": [{"id": "says", "label": "What it should say", "hint": "three words"}]},
    {"id": "screen", "name": "New screen", "sign": "screen", "line": "A screen people get through, phone width first", "lens": "screen", "refs": True, "used": 0, "missing": [A11Y],
     "asks": [{"id": "who", "label": "Who uses it", "hint": "and what they came to do"}]},
    {"id": "experiment", "name": "Try an experiment", "sign": "flask", "line": "A change shown to some people, then measured", "lens": "text", "refs": False, "used": 0,
     "missing": [EXPERIMENT], "asks": []},
]
LENSES = {"lenses": [{"id": "text"}, {"id": "screen", "by": "a designer’s"}], "default": "text", "segments": [], "screens": []}


def norm(s):
    return " ".join(s.split())


def typed(monkeypatch):
    """The party deals its types; New goal by one answers who joined (the host's `joined`); the party offers the Screen lens."""
    SCENE["map"]["goals"][0]["types"] = copy.deepcopy(TYPES)
    real, init = Stub.commands, Stub.__init__

    def commands(self):
        got = real(self)

        def add(a):
            self.calls.append(("ideas.add", {k: v for k, v in a.items() if k not in ("link", "device")}))
            return self.bump({"slug": "new-one", "queue": "night" if a.get("night") else "now", "type": a.get("type", ""),
                              "joined": {"add": a["join"]["add"], "out": a["join"].get("out", "")} if a.get("join") else None})
        return {**got, "ideas.add": add}

    def new_init(self):
        init(self)
        self.lens = copy.deepcopy(LENSES)
    monkeypatch.setattr(Stub, "commands", commands)
    monkeypatch.setattr(Stub, "__init__", new_init)


async def _form(page, type_id=None):
    """New goal: the create button tapped, the form slid up; the type `type_id` picked ("" is *No type*; None leaves the first)."""
    await page.locator(FAB).click()
    form = page.get_by_role("dialog", name="New goal")
    await form.wait_for(timeout=WAIT_MS)
    await page.wait_for_function("() => !document.getAnimations().some((a) => a.playState === 'running')", timeout=WAIT_MS)
    if type_id is not None:
        await form.locator(f'.newgoal__chip[data-type="{type_id}"]').click()
    return form


async def _flash(page, text):
    await page.locator("p.flash", has_text=text).first.wait_for(timeout=WAIT_MS)
    return True


# -- the top bar, the goals bar (§5.1, §5.2) -----------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_top_bar_has_the_projects_button_and_its_sheet_and_no_party_and_no_count(fake_repo, monkeypatch, projects):
    second_party()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        bar = page.locator(".board-bar")
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        btn = bar.locator(".projbtn")
        assert norm(await btn.inner_text()) == "project" and await btn.get_attribute("aria-label") == "Project project. A tap shows your projects"
        assert (await btn.bounding_box())["height"] >= 44 and await btn.locator(".projbtn__name").evaluate("e => getComputedStyle(e).fontSize") == "12px"
        assert await btn.locator(".ork-chev").count() == 1
        assert await bar.locator(".ork-count, .where, img.ork-race__head").count() == 0 and "Passkey" not in await bar.inner_text()      # the party, its head and its counts left the bar
        await btn.click()
        sheet = page.get_by_role("dialog", name="Projects")
        await sheet.get_by_role("button", name=re.compile("^beta")).wait_for(timeout=WAIT_MS)
        box = await sheet.bounding_box()
        assert box["x"] == 0 and box["y"] == 0 and box["width"] == 390                                                                  # from the top
        rows = sheet.locator(".project-row")
        assert [norm(await r.inner_text()) for r in await rows.all()] == ["alpha this one", "beta 3 to review", "gamma nothing waits"]
        assert await rows.first.get_attribute("aria-current") == "true" and await rows.nth(1).get_attribute("aria-current") is None
        assert "Open on your computer: a tap switches this phone to one." in await sheet.inner_text()
        assert await sheet.locator(".where-row, .where-new").count() == 0                                                              # the parties are the deck's
        assert all([(await r.bounding_box())["height"] >= 44 for r in await rows.all()])
        await rows.nth(1).click()
        assert await _called(stub, "projects.use", {"path": "/work/beta"})
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_the_goals_bar_says_the_party_cut_at_fourteen_and_with_the_filter_the_party_and_its_picks(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        head = page.locator(".gbar__head")
        await head.wait_for(timeout=WAIT_MS)
        assert norm(await head.inner_text()) == "Passkey · 2 of 9 goals done" and await head.locator(".ork-chev").count() == 1
        await head.click()
        sheet = page.get_by_role("dialog", name="Goals")
        await sheet.locator('.dk__main[data-idea="register"]').click()
        await page.keyboard.press("Escape")
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        assert norm(await head.inner_text()) == "Passkey 1 of 9 goals" and await head.locator(".ork-elem").count() == 1          # the party, the picked goal's element, k of m
        assert await page.locator(".gbar").get_by_role("button", name="Show all").is_visible()
    SCENE["map"]["goals"][0]["short"] = "Sign in with a passkey"
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        head = page.locator(".gbar__head")
        await head.wait_for(timeout=WAIT_MS)
        assert norm(await head.inner_text()) == "Sign in with … · 2 of 9 goals done"                                                    # cut at 14 characters, with an ellipsis


# -- the stage switch and the party's deck (§5.3, §5.4) -------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_stage_switch_wears_the_partys_faces_over_its_words_with_one_sign_and_no_number(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        tabs = page.get_by_role("tablist", name="Stages")
        await tabs.wait_for(timeout=WAIT_MS)
        bands = tabs.locator(".band")
        assert [await b.get_attribute("data-band") for b in await bands.all()] == ["lead", "build", "check"]
        assert [norm(await b.inner_text()) for b in await bands.all()] == ["Planning", "Implementation", "Checking"]                    # the words, no number
        assert not re.search(r"\d", await tabs.inner_text()) and await tabs.locator(".ork-count").count() == 0
        assert [round((await b.bounding_box())["height"]) for b in await bands.all()] == [60, 60, 60]                                   # spec 53 §1.2
        assert all([abs((await b.bounding_box())["width"] - 130) <= 2 for b in await bands.all()])                                     # the whole width, shared (the deck is at the goals bar's left)
        assert all([await b.locator(".band__name").evaluate("e => e.scrollWidth <= e.clientWidth && getComputedStyle(e).fontSize === '11px'") for b in await bands.all()])
        heads = lambda key: tabs.locator(f'.band[data-band="{key}"] img.ork-race__head')                                             # noqa: E731
        assert [await heads(k).count() for k in ("lead", "build", "check")] == [1, 2, 2]
        build = [await h.bounding_box() for h in await heads("build").all()]
        assert round(build[0]["width"]) == 24 and round(build[0]["height"]) == 22 and round(build[1]["x"] - build[0]["x"]) == 28     # 24 × 22, side by side 4 px apart (spec 53 §1.2)
        assert await heads("lead").first.get_attribute("src") == "races/peon-elder.png"
        signs = {k: await tabs.locator(f'.band[data-band="{k}"] .band__sign .ork-sign').get_attribute("class") for k in ("lead", "build", "check")}
        assert signs == {"lead": "ork-sign alert", "build": "ork-sign cross", "check": "ork-sign alert"}                                 # a plan and a proposal; a failure; the Reviewer's question
        sign = await tabs.locator('.band[data-band="build"] [data-member="backend"] .band__sign').bounding_box()
        assert (round(sign["width"]), round(sign["height"])) == (12, 12) and round(build[0]["x"] + build[0]["width"] - sign["x"]) == 7    # 12 × 12 on the face it comes from, over its corner by 5 px
        assert await tabs.locator('.band[data-band="build"] .band__sign').evaluate("e => getComputedStyle(e).color") != await tabs.locator('.band[data-band="lead"] .band__sign').evaluate("e => getComputedStyle(e).color")
        labels = [await b.get_attribute("aria-label") for b in await bands.all()]
        assert labels == ["Planning: the Taskmaster. 2 wait for you", "Implementation: Backend, Screens. 1 failed", "Checking: Reviewer, Words. 1 waits for you"]
        assert await page.locator(".gbar > .partydeck").count() == 1 and await page.locator(".stagebar .partydeck").count() == 0         # the deck stands at the goals bar's left (spec 53 §1.1)
        assert await page.locator('.band[data-band="build"]').get_attribute("aria-selected") == "true"                                  # the tab picked keeps its underline
        assert "inset" in await page.locator('.band[data-band="build"]').evaluate("e => getComputedStyle(e).boxShadow")
        assert await page.evaluate(NO_SCROLL)
    SCENE["map"]["nodes"][6]["tasks"][2]["state"] = "picking"                                                                           # a pick waits in Implementation too: ✗ stays over !
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        band = page.locator('.band[data-band="build"]')
        await band.wait_for(timeout=WAIT_MS)
        assert await band.locator('[data-member="backend"] .band__sign .ork-sign').get_attribute("class") == "ork-sign cross"          # ✗ on the member whose task failed …
        assert await band.locator('[data-member="screens"] .band__sign .ork-sign').get_attribute("class") == "ork-sign alert"          # … ! on the one a pick waits on
        assert await band.get_attribute("aria-label") == "Implementation: Backend, Screens. 1 failed, 1 waits for you"


@pytest.mark.asyncio
async def test_a_band_with_no_one_shows_an_empty_head_says_what_happens_and_adds_from_the_party(fake_repo, monkeypatch):
    g = SCENE["map"]["goals"][0]
    g["party"] = [m for m in g["party"] if m["band"] != "check"]
    g["team"] = [m for m in g["team"] if not m["checks"]]
    for n in SCENE["map"]["nodes"]:
        n["tasks"] = [t for t in n["tasks"] if t.get("band") != "check"]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        check = page.locator('.band[data-band="check"]')
        await check.wait_for(timeout=WAIT_MS)
        empty = check.locator(".band__nohead.is-empty")
        assert await empty.count() == 1 and await check.locator("img.ork-race__head").count() == 0
        box = await empty.bounding_box()
        assert (round(box["width"]), round(box["height"])) == (24, 22) and await empty.evaluate("e => getComputedStyle(e).borderStyle") == "dashed"
        assert await check.get_attribute("aria-label") == "Checking: no checker"
        await _band(page, "check")
        none = page.locator('.band-none[data-band="check"]')
        assert norm(await none.inner_text()).startswith("No checker in this party: a goal is done when its own Done when lines are.")
        add = none.get_by_role("button", name="Add to the party")
        assert (await add.bounding_box())["height"] >= 44
        await add.click()
        assert await _called(stub, "ideas.goal", {"slug": "passkey"})                                                                 # Edit the party, as About this party's
        assert await page.locator(".stagebar [data-act='add-member'], .colname [data-act='add-member']").count() == 0                                # no other place adds a member on the field


@pytest.mark.asyncio
async def test_the_partys_deck_counts_the_other_parties_stops_and_its_sheet_picks_a_party(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        deck = page.locator(".partydeck")
        await deck.wait_for(timeout=WAIT_MS)
        assert await deck.locator(".ork-count").count() == 0                                                                           # none when none
        assert await deck.get_attribute("aria-label") == "Parties: Passkey shown. A tap shows the parties"
    second_party(2)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        deck = page.locator(".partydeck")
        await deck.wait_for(timeout=WAIT_MS)
        box = await deck.bounding_box()
        assert (round(box["width"]), round(box["height"])) == (44, 44) and await deck.locator(".partydeck__edge").count() == 2
        assert await deck.locator(".ork-count.warning").inner_text() == "2"                                                            # the one count of stops on the screen
        assert await deck.get_attribute("aria-label") == "Parties: Passkey shown, 2 stops wait in the other parties. A tap shows the parties"
        assert await page.locator(".ork-count.warning:visible").count() == 1
        sheet = await _where(page)
        sbox = await sheet.bounding_box()
        assert sbox["x"] == 0 and sbox["y"] == 0 and sbox["width"] == 390
        rows = sheet.locator(".where-row")
        assert [await r.get_attribute("data-goal") for r in await rows.all()] == ["passkey", "product", "ops"]
        assert await sheet.locator(".project-row").count() == 0 and await sheet.locator(".where-new").count() == 1                      # today's where sheet without its projects
        assert await rows.first.get_attribute("aria-current") == "true" and await rows.nth(1).locator(".ork-count.warning").inner_text() == "2"   # its rows keep their counts
        await rows.nth(1).click()
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        await page.locator('.partydeck[data-goal="product"]').wait_for(timeout=WAIT_MS)
        assert await page.locator(".partydeck .ork-count").inner_text() == "4" and norm(await page.locator(".gbar__head").inner_text()).startswith("Product ·")
        assert await page.evaluate("() => JSON.parse(localStorage.getItem('orkcraft.goal'))") == {"project": "product"}
        sheet = await _where(page)
        await sheet.locator('.where-row[data-goal="ops"]').click()                                                                     # Operations: the deck stands at its head
        await page.locator(".ops-view .partydeck").wait_for(timeout=WAIT_MS)
        assert await page.locator(".stagebar").count() == 0
        await _where(page)
        assert await page.evaluate(NO_SCROLL)


# -- New goal by its type (§5.6; the form is spec 53 §2's: tests/test_pwa_new_goal53_browser.py) --------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_goal_by_a_type_its_head_the_party_fixed_its_asks_sent(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page, "bug")
        assert await form.locator('.newgoal__chip[data-type="bug"]').get_attribute("aria-checked") == "true"                            # by its type: asks, no party row to change
        assert norm(await form.locator(".newgoal__typeline").inner_text()) == "Something that goes wrong, made right"
        did = form.get_by_label("What you did")
        assert await did.get_attribute("placeholder") == "the steps, in order" and await form.get_by_label("What should have").get_attribute("placeholder") == "what you expected"
        assert await form.locator(".newgoal__refs").is_hidden() and await form.locator(".joins").is_hidden()
        await form.get_by_label("The goal", exact=True).fill("The sign-in button does nothing")
        await did.fill("  Tapped   Sign in  ")
        await form.get_by_label("What happened").fill("Nothing")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add", {"text": "The sign-in button does nothing", "track": "passkey", "priority": "high", "type": "bug",
                                                 "asks": {"did": "Tapped   Sign in", "happened": "Nothing"}})
        assert await _flash(page, "Added: the Taskmaster drafts it now.")


@pytest.mark.asyncio
async def test_a_type_with_refs_and_a_free_seat_opens_its_lens_first_and_its_join_line_sends_who_joins(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page, "logo")
        await form.locator('.lens-pane[data-lens="screen"]').wait_for(timeout=WAIT_MS)                                                # the type's lens first, with no switch
        assert await form.locator(".lens-bar").is_hidden()
        refs = form.locator(".newgoal__refs")
        assert await refs.is_visible() and "Pictures you like" in await refs.inner_text() and await form.get_by_role("button", name="Photo").is_visible()
        line = form.locator('.joinline[data-agent="artist"]')
        box = line.get_by_role("checkbox")
        assert await box.is_checked() and norm(await line.locator(".joinline__words").inner_text()) == "Artist joins the party"
        price = line.locator(".joinline__price")
        assert norm(await price.inner_text()) == "≈$0.05 a run" and await price.get_attribute("title") == "at API prices, not your bill"
        assert await line.locator("img.ork-race__head").count() == 1 and await line.locator(".joinline__without").is_hidden()
        await box.uncheck()
        assert norm(await line.locator(".joinline__without").inner_text()) == "Without Artist, its pixel art goes to the Grunt."
        await box.check()
        await form.get_by_label("The goal", exact=True).fill("A new mark")
        await form.get_by_label("What it should say").fill("calm, fast, kind")
        await form.get_by_label("Links").fill("https://example.com/likes")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add")
        sent = [a for n, a in stub.calls if n == "ideas.add"][-1]
        assert sent["type"] == "logo" and sent["asks"] == {"says": "calm, fast, kind", "refs": "https://example.com/likes"} and sent["join"] == {"add": "artist"}
        assert await _flash(page, "Added: Artist joined the party; the Taskmaster drafts it now.")


@pytest.mark.asyncio
async def test_a_swap_picks_who_leaves_a_full_band_says_why_and_put_it_back_never_sends_join(fake_repo, monkeypatch):
    typed(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _form(page, "screen")
        line = form.locator('.joinline[data-agent="accessibility-reviewer"]')
        assert norm(await line.locator(".joinline__words").inner_text()) == "Swap: Words leaves, Accessibility reviewer joins"
        who = line.get_by_label("Who leaves")
        assert [norm(o) for o in await who.locator("option").all_inner_texts()] == ["Words · 1 run this week", "Reviewer · 6 runs this week"]
        assert (await who.bounding_box())["height"] >= 44 and await who.evaluate("e => e.tagName") == "SELECT"
        await who.select_option("reviewer")
        assert norm(await line.locator(".joinline__words").inner_text()) == "Swap: Reviewer leaves, Accessibility reviewer joins"
        await form.get_by_label("The goal", exact=True).fill("A settings screen")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add")
        assert [a for n, a in stub.calls if n == "ideas.add"][-1]["join"] == {"add": "accessibility-reviewer", "out": "reviewer"}
        await page.get_by_role("dialog", name="New goal").wait_for(state="hidden", timeout=WAIT_MS)
        form = await _form(page, "experiment")
        full = form.locator('.joinline.is-full[data-agent="experimenter"]')
        assert norm(await full.inner_text()) == ("The party’s builders all have work open: Experimenter can join from Edit the party when one is done. "
                                                  "Till then its experiments goes to the Grunt.")
        assert await form.locator(".joins").get_by_role("checkbox").count() == 0
        await form.get_by_label("The goal", exact=True).fill("Try a shorter sign-in")
        await form.get_by_role("button", name="Add the goal").click()
        await page.get_by_role("dialog", name="New goal").wait_for(state="hidden", timeout=WAIT_MS)
        assert "join" not in [a for n, a in stub.calls if n == "ideas.add"][-1]
        form = await _form(page, "logo")
        await form.get_by_label("The goal", exact=True).fill("Kept for tonight")
        await form.get_by_role("button", name="Put it back").click()
        assert await _called(stub, "ideas.add", {"text": "Kept for tonight", "track": "passkey", "priority": "high", "night": True, "type": "logo"})      # no join


# -- a plan's missing line (§5.7) ----------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_plans_missing_line_on_its_card_and_raised_and_add_and_start(fake_repo, monkeypatch):
    SCENE["needs"][0]["missing"] = [{k: v for k, v in ART.items() if k != "out"}, {"kind": "text", "words": "text for people", "agent": "copywriter", "name": "Copywriter",
                                                                                     "band": "build", "free": True}]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        card = page.locator('.hc[data-kind="plan"]')
        await card.wait_for(timeout=WAIT_MS)
        assert norm(await card.locator(".hc__miss").inner_text()) == "No one in the party does pixel art: Artist would, and 1 more."
        raised = await _pop(page, "Plan ready: Recovery codes")
        assert norm(await raised.locator(".raised__miss").inner_text()) == "No one in the party does pixel art: Artist would, and 1 more."
        quick = raised.locator(".raised__quick .ork-btn")
        assert [norm(t) for t in await quick.all_inner_texts()] == ["Add and start", "Start without"]
        assert all([(await b.bounding_box())["height"] >= 44 for b in await quick.all()])
        add = raised.get_by_role("button", name="Add and start")
        assert await add.get_attribute("title") == "Artist joins the party, then the work starts" and "primary" in await add.get_attribute("class")
        assert await raised.get_by_role("button", name="Open it on its own screen").is_visible()
        await add.click()
        assert await _called(stub, "ideas.start", {"slug": "recovery", "join": {"add": "artist"}, "via": "hand"})
        assert await _flash(page, "Artist joined the party; the work started.")


@pytest.mark.asyncio
async def test_a_plans_missing_line_with_no_free_seat_starts_without_or_edits_the_party(fake_repo, monkeypatch):
    SCENE["needs"][0]["missing"] = [{**{k: v for k, v in ART.items() if k != "out"}, "free": False}]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _pop(page, "Plan ready: Recovery codes")
        assert norm(await raised.locator(".raised__miss").inner_text()) == "No one in the party does pixel art: Artist would."
        assert [norm(t) for t in await raised.locator(".raised__quick .ork-btn").all_inner_texts()] == ["Start without", "Edit the party"]
        await raised.get_by_role("button", name="Edit the party").click()
        assert await _called(stub, "ideas.goal", {"slug": "passkey"})
        await page.get_by_role("dialog", name=re.compile("party", re.I)).first.wait_for(timeout=WAIT_MS)
        await page.keyboard.press("Escape")
        raised = await _pop(page, "Plan ready: Recovery codes")
        await raised.get_by_role("button", name="Start without").click()
        assert await _called(stub, "ideas.start", {"slug": "recovery", "via": "hand"})


# -- a stop marked once (§5.8) -----------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_signs_keep_their_place_without_an_alert_edge_a_failure_keeps_its_danger_edge_and_a_row_shows_its_type(fake_repo, monkeypatch):
    SCENE["map"]["nodes"][6]["tasks"][2]["state"] = "picking"                                                       # Register screen asks you to pick
    SCENE["map"]["nodes"][6]["type"] = {"id": "feature", "name": "New feature", "sign": "feature"}
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".deck").first.wait_for(timeout=WAIT_MS)
        alert = await page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--ork-alert').trim()")
        pick = page.locator('.deck[data-state="picking"]').first
        assert await pick.locator(".tcard__mark .ork-sign.alert").count() == 1                                                        # its sign stays
        colors = await pick.evaluate("""d => [d.querySelector('.tcard'), ...d.querySelectorAll('.deck__edge')].map((e) => getComputedStyle(e).borderTopColor)
          .concat([getComputedStyle(d.querySelector('.tcard__foot')).color])""")
        probe = await page.evaluate(f"() => {{ const e = document.createElement('i'); e.style.color = '{alert}'; document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; }}")
        assert probe not in colors                                                                                                       # no alert edge, no alert words
        failed = page.locator('.deck[data-state="failed"] .tcard').first
        danger = await page.evaluate("() => { const e = document.createElement('i'); e.style.color = 'var(--ork-danger)'; document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; }")
        assert await failed.evaluate("e => getComputedStyle(e).borderTopColor") == danger                                             # a failure keeps its danger edge
        assert await page.locator(".board-bar .ork-count, .stagebar .bands .ork-count").count() == 0
        await page.locator(".gbar__head").click()
        sheet = page.get_by_role("dialog", name="Goals")
        row = sheet.locator('.dk[data-idea="register"]')
        assert await row.locator(".dk__type .ork-sign.feature").count() == 1 and await row.locator(".dk__type .ork-sign").get_attribute("title") == "New feature"
        asks = sheet.locator('.dk[data-idea="second"]')
        assert await asks.locator(".dk__mark .ork-sign.alert").count() == 1
        assert await asks.locator(".dk__main").evaluate("e => getComputedStyle(e).boxShadow") == "none"
        assert await asks.locator(".dk__line").evaluate("e => getComputedStyle(e).color") != probe


def test_the_service_worker_is_one_up_and_keeps_the_types_module():
    sw = (pwa.ROOT / "sw.js").read_text(encoding="utf-8")
    assert 'const CACHE = "orkcraft-app-v61";' in sw and '"shell-types.js"' in sw[sw.index("const SHELL"):sw.index("];", sw.index("const SHELL"))]
