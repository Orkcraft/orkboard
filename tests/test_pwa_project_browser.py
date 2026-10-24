"""Spec 70 part C, the phone: the Orkmaster and the project's level (docs/specs/70-orkmaster-and-the-project.md §2.1, §2.4, §3, §4, §5 "C"): Chromium at 390 × 844 against the world of tests/test_pwa_route_browser.py
(the Passkey, Ideation, Website and Release parties) with the stub host of spec 70 §1: `ideas.map`'s `project` block (the Orkmaster and the deal), `ideas.party_for` and `ideas.shown`. *The project* stands at the top of the
parties' sheet; its sheet has a section for each party (*Open <party>* switches), its goals as rows (Planning and At work, Waits for main and Flags folded), a row opens the goal's screen, `ideas.shown` says `@project`;
*New party* deals the library's parties as a strip in the deal's order with their why, a tile opens New party with that preset picked, and New party's own tiles follow the deal; *New goal* from the sheet has no party yet:
*Its party* from `ideas.party_for` (*Orkmaster suggests Website · takes it whole*, the others to pick), `ideas.add` with the party picked; an older host (no `project`) has none of it; no sideways scroll; the worker's version."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from orkboard.gui import pwa
from orkboard.realm import library
from tests.test_pwa_arena_browser import SCENE, _redrawn, _scene, _shot_to, node  # noqa: F401
from tests.test_pwa_goal_types_browser import TYPES
from tests.test_pwa_route_browser import WORLD, norm, world  # noqa: F401
from tests.test_pwa_shell_browser import FAB, NO_SCROLL, WAIT_MS, Stub, _called, _phone, _pick_goal, _where

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

ORKMASTER = {"id": "orkmaster", "name": "Orkmaster", "race": "peon", "tier": "elder"}
LOGO = next(t for t in TYPES if t["id"] == "logo")                      # needs an Artist (free)
LOGO_WHOLE = {**LOGO, "missing": []}
BUG = next(t for t in TYPES if t["id"] == "bug")
PRESET_IDS = [p["id"] for p in library.presets()]
GAME = "game"

STATE: dict = {}


def deal_of(kind):
    """The deal of spec 70 §1.1: `flags` — no Release party, flags wait (Release first, then Ideation, the library's order); `have` — the project has both (the library's order, then Release and Ideation last)."""
    rest = [i for i in PRESET_IDS if i not in ("release", "ideation")]
    if kind == "flags":
        return [{"id": "release", "why": "flags_wait", "n": 3}, {"id": "ideation", "why": "no_pitches", "n": 0}, *({"id": i, "why": "", "n": 0} for i in rest)]
    return [*({"id": i, "why": "", "n": 0} for i in rest), {"id": "release", "why": "have", "n": 0}, {"id": "ideation", "why": "have", "n": 0}]


def hosted(monkeypatch, deal="flags", project=True):
    """The world of the route tests with spec 70's host: `project` on the Map, the parties' types, `ideas.party_for` (spec 70 §1.2) and `ideas.shown`."""
    world(monkeypatch)
    goals = {g["slug"]: g for g in SCENE["map"]["goals"]}
    goals["passkey"]["types"] = [copy.deepcopy(BUG), copy.deepcopy(LOGO)]                  # Passkey misses an Artist for a logo
    goals["website"]["types"] = [copy.deepcopy(LOGO_WHOLE)]                                 # Website takes it whole
    SCENE["map"]["nodes"].append(node("tidy", "Tidy the cookies", "done", "done", element="dust", folded=True))                  # done, not flagged, in dev: it waits for main
    SCENE["gate"]["ideas"].append({"slug": "tidy", "title": "Tidy the cookies", "goal": "passkey", "tasks": 1})
    if project:
        SCENE["map"]["project"] = {"orkmaster": copy.deepcopy(ORKMASTER), "deal": deal_of(deal)}
    STATE.clear()
    real = Stub.commands

    def commands(self):
        got = real(self)

        def serve(name, answer):
            def call(a):
                a = {k: v for k, v in a.items() if k != "link" and (k != "device" or name == "ideas.log")}
                self.calls.append((name, dict(a)))
                return answer(a)
            return call

        def party_for(a):
            t = a.get("type", "")
            rows, ideation = [], None
            for g in SCENE["map"]["goals"]:
                if g["slug"] == "general":
                    continue
                offered = {x["id"]: x for x in g.get("types") or []}
                if g.get("ideation"):
                    ideation = {"party": g["slug"], "name": g["title"], "fits": "none" if t else "pitch", "missing": []}
                elif not t:
                    rows.append({"party": g["slug"], "name": g["title"], "fits": "", "missing": []})
                elif t in offered:
                    miss = [{"agent": m["agent"], "name": m["name"]} for m in offered[t]["missing"]]
                    rows.append({"party": g["slug"], "name": g["title"], "fits": "missing" if miss else "whole", "missing": miss})
                else:
                    rows.append({"party": g["slug"], "name": g["title"], "fits": "none", "missing": []})
            if t:
                rows.sort(key=lambda r: {"whole": 0, "missing": 1, "none": 2}[r["fits"]])
            out = [*rows, *([ideation] if ideation else [])]
            STATE["asked"] = STATE.get("asked", 0) + 1
            return {"parties": out, "suggested": out[0]["party"] if out else ""}

        return {**got, "ideas.party_for": serve("ideas.party_for", party_for), "ideas.shown": serve("ideas.shown", lambda a: {"ok": True})}
    monkeypatch.setattr(Stub, "commands", commands)


def calls(stub, name):
    return [c[1] for c in stub.calls if c[0] == name]


async def _project(page):
    """The project's sheet, opened from the parties' sheet's first row."""
    sheet = await _where(page)
    await sheet.locator('.where-row[data-act="the-project"]').click()
    project = page.get_by_role("dialog", name="The project")
    await project.wait_for(timeout=WAIT_MS)
    await project.locator(".pj-party").first.wait_for(timeout=WAIT_MS)
    return project


# -- The Orkmaster at the parties' sheet's top ---------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_project_is_the_first_row_of_the_parties_sheet_with_the_orkmasters_head(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _where(page)
        rows = sheet.locator(".where-parties > *")
        first = rows.first
        assert await first.get_attribute("data-act") == "the-project"
        assert norm(await first.inner_text()) == "The project The parties, their goals"
        assert await first.locator("img.ork-race__head").get_attribute("src") == "races/peon-elder.png"             # the Orkmaster's head: an ork, the elder tier
        assert await first.locator("img.ork-race__head").evaluate("(i) => i.complete && i.naturalWidth > 0")
        assert (await first.bounding_box())["height"] >= 44
        assert [await r.get_attribute("data-goal") for r in await sheet.locator(".where-row[data-goal]").all()][:2] == ["passkey", "ideation"]      # the parties follow it
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_host_with_no_project_keeps_todays_phone(fake_repo, monkeypatch):
    hosted(monkeypatch, project=False)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _where(page)
        assert await sheet.locator('[data-act="the-project"]').count() == 0
        assert "The project" not in await sheet.inner_text()
        await page.keyboard.press("Escape")
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        await _pick_goal(page, "passkey")
        await page.locator(FAB).click()                                                                                 # New goal is the party's own, with its party button
        form = page.get_by_role("dialog", name="New goal")
        await form.wait_for(timeout=WAIT_MS)
        assert await form.locator(".newgoal__party").is_visible() and await form.locator(".itsparty").is_hidden()
        assert calls(stub, "ideas.party_for") == []


# -- The project's sheet -------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_projects_sheet_has_a_section_for_each_party_with_its_goals_and_folds(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        project = await _project(page)
        assert await project.locator(".sheet-head h2").text_content() == "The project"
        sections = project.locator(".pj-party")
        assert [await s.get_attribute("data-goal") for s in await sections.all()] == ["passkey", "ideation", "website", "release"]      # the parties' order
        passkey = sections.nth(0)
        await _shot_to(page, "phone-project")
        head = passkey.locator(".pj-party__head")
        assert "Passkey" in await head.inner_text() and "2/9" in await head.inner_text()                               # k/n
        assert await head.locator("img.ork-race__head").count() == 1                                                    # its leader's head
        open_btn = passkey.get_by_role("button", name="Open Passkey")
        assert norm(await open_btn.inner_text()) == "Open Passkey" and (await open_btn.bounding_box())["height"] >= 44
        assert [norm(await g.inner_text()) for g in await passkey.locator(".pj-group").all()] == ["Planning", "At work"]
        assert await passkey.locator('.pj-row[data-idea="register"]').count() == 1                                      # a goal at work: its element, its words
        row = passkey.locator('.pj-row[data-idea="register"]')
        assert await row.locator(".ork-elem").count() == 1
        assert "WebAuthn register" in await row.inner_text() and "in dev" in await row.inner_text()
        assert (await row.bounding_box())["height"] >= 44
        flags = passkey.locator('.pj-fold[data-fold="flags"]')                                                          # folded: Flags (n)
        assert norm(await flags.locator(".pj-fold__head").inner_text()).startswith("Flags (3)")
        assert await flags.locator(".pj-fold__head").get_attribute("aria-expanded") == "false" and await flags.locator(".pj-row").count() == 0
        await flags.locator(".pj-fold__head").click()
        assert await flags.locator(".pj-row").count() == 3 and await flags.locator(".pj-fold__head").get_attribute("aria-expanded") == "true"
        waits = passkey.locator('.pj-fold[data-fold="waits"]')
        assert norm(await waits.locator(".pj-fold__head").inner_text()).startswith("Waits for main") and await waits.locator(".pj-row").count() == 0
        await waits.locator(".pj-fold__head").click()
        assert await waits.locator('.pj-row[data-idea="tidy"]').count() == 1
        assert "Nothing in Website yet" in await sections.nth(2).inner_text()
        assert "null" not in await project.inner_text() and "undefined" not in await project.inner_text()
        await sections.nth(1).scroll_into_view_if_needed()
        await project.evaluate("(d) => { d.scrollTop = d.scrollHeight; }")
        await _shot_to(page, "phone-project-more")
        assert await sections.nth(1).locator('.pj-row[data-idea="dark"]').count() == 1                                  # Ideation's pitch, under Planning
        assert await page.evaluate(NO_SCROLL) and await project.evaluate("(d) => d.scrollWidth <= d.clientWidth")


@pytest.mark.asyncio
async def test_the_project_says_ideas_shown_at_project_and_a_row_opens_the_goals_screen(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        project = await _project(page)
        assert await _called(stub, "ideas.shown", {"party": "@project", "from": "passkey"})                              # fire and forget, once, from the party shown
        assert len(calls(stub, "ideas.shown")) == 1
        await project.locator('.pj-row[data-idea="register"]').click()
        await project.wait_for(state="hidden", timeout=WAIT_MS)
        screen = page.locator("section.screen:not([hidden])")
        await screen.locator(".screen-body > *").first.wait_for(timeout=WAIT_MS)
        assert "WebAuthn register" in await screen.inner_text()                                                         # the goal's screen
        assert await screen.locator("nav[aria-label=Route]").count() == 1                                              # with its route line (spec 68)


@pytest.mark.asyncio
async def test_open_party_switches_the_board_and_closes_the_sheet(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        project = await _project(page)
        await project.get_by_role("button", name="Open Website").click()
        await project.wait_for(state="hidden", timeout=WAIT_MS)
        await page.locator('.partydeck[data-goal="website"]').wait_for(timeout=WAIT_MS)                                 # the board shows Website
        assert await _called(stub, "ideas.shown", {"party": "website", "from": "@project"})
        sheet = await _where(page)
        assert await sheet.locator('.where-row[data-goal="website"]').get_attribute("aria-current") == "true"


# -- The deal ------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_party_deals_the_presets_as_a_strip_in_the_deals_order_with_their_why(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        project = await _project(page)
        button = project.locator('[data-act="project-new-party"]')
        assert norm(await button.inner_text()) == "New party" and await button.get_attribute("aria-expanded") == "false"
        assert await project.locator(".pj-deal").count() == 0
        await button.click()
        strip = project.locator(".pj-deal")
        await strip.wait_for(timeout=WAIT_MS)
        tiles = strip.locator(".pj-tile")
        assert [await t.get_attribute("data-preset") for t in await tiles.all()] == [d["id"] for d in deal_of("flags")]  # Release first, Ideation, then the library's order
        assert "3 flags wait and no party releases them" in await tiles.nth(0).inner_text()
        assert "No party judges small ideas yet" in await tiles.nth(1).inner_text()
        assert await tiles.nth(2).locator(".pj-tile__why").count() == 0                                                  # the others say no why
        assert "Your own goal" not in await strip.inner_text() and min([(await t.bounding_box())["height"] for t in await tiles.all()]) >= 44
        assert await tiles.nth(0).locator("img.ork-race__head").count() >= 2                                             # its heads
        assert await strip.evaluate("(e) => e.scrollWidth > e.clientWidth")                                              # a strip: it scrolls along itself
        assert await page.evaluate(NO_SCROLL)
        await _shot_to(page, "phone-deal")
        await tiles.nth(0).click()
        form = page.get_by_role("dialog", name="New party")
        await form.wait_for(timeout=WAIT_MS)
        assert await form.locator('.preset-tile[data-preset="release"]').get_attribute("aria-pressed") == "true"       # New party with Release picked


@pytest.mark.asyncio
async def test_the_parties_you_have_come_last_in_the_deal_muted(fake_repo, monkeypatch):
    hosted(monkeypatch, deal="have")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        project = await _project(page)
        await project.locator('[data-act="project-new-party"]').click()
        tiles = project.locator(".pj-deal .pj-tile")
        await tiles.first.wait_for(timeout=WAIT_MS)
        ids = [await t.get_attribute("data-preset") for t in await tiles.all()]
        assert ids[-2:] == ["release", "ideation"] and "You have one" in await tiles.nth(len(ids) - 1).inner_text()
        assert await tiles.last.get_attribute("class") and "is-have" in await tiles.last.get_attribute("class")


@pytest.mark.asyncio
async def test_new_partys_tiles_follow_the_deal_with_the_why_under_the_line(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await (await _where(page)).get_by_role("button", name="+ New party").click()                                     # the sheet's own *+ New party* stays
        sheet = page.get_by_role("dialog", name="New party")
        await sheet.locator(".preset-tile").first.wait_for(timeout=WAIT_MS)
        mixed = [await t.get_attribute("data-preset") for t in await sheet.locator('.preset-group[aria-label="Mixed"] .preset-tile').all()]
        assert mixed == ["release", "ideation", "game", "mobile-app", "website"]                                          # inside the group, the deal's order
        one = [await t.get_attribute("data-preset") for t in await sheet.locator('.preset-group[aria-label="One craft"] .preset-tile').all()]
        assert one == ["engineering", "design", "data", "marketing", "product"]                                           # the craft group keeps its headings and order
        assert [norm(await h.inner_text()) for h in await sheet.locator(".preset-group h4").all()][:2] == ["Mixed", "One craft"]
        release = sheet.locator('.preset-tile[data-preset="release"]')
        assert await release.locator(".preset-why").inner_text() == "3 flags wait and no party releases them"
        assert await sheet.locator('.preset-tile[data-preset="game"] .preset-why').count() == 0
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_an_older_host_keeps_new_partys_tiles_as_they_were(fake_repo, monkeypatch):
    hosted(monkeypatch, project=False)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await (await _where(page)).get_by_role("button", name="+ New party").click()
        sheet = page.get_by_role("dialog", name="New party")
        await sheet.locator(".preset-tile").first.wait_for(timeout=WAIT_MS)
        ids = [await t.get_attribute("data-preset") for t in await sheet.locator(".preset-tile").all()]
        assert ids[:5] == ["game", "mobile-app", "website", "ideation", "release"] and await sheet.locator(".preset-why").count() == 0


# -- New goal from the project -------------------------------------------------------------------------------------------------------------------------

async def _new_goal_from_project(page):
    project = await _project(page)
    await project.locator('[data-act="project-new-goal"]').click()
    form = page.get_by_role("dialog", name="New goal")
    await form.wait_for(timeout=WAIT_MS)
    await page.wait_for_function("() => !document.getAnimations().some((a) => a.playState === 'running')", timeout=WAIT_MS)
    await form.locator(".itsparty__chip").first.wait_for(timeout=WAIT_MS)
    return form


@pytest.mark.asyncio
async def test_new_goal_from_the_project_has_no_party_yet_and_its_party_from_the_orkmaster(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _new_goal_from_project(page)
        assert await form.locator(".newgoal__party").is_hidden()                                                        # no party button: the party is asked of the Orkmaster
        its = form.locator(".itsparty")
        assert await its.locator(".field-label").text_content() == "Its party" and norm(await its.locator(".itsparty__line").inner_text()) == "Any party"
        assert calls(stub, "ideas.party_for") == [{}]                                                                   # without a type
        chips = its.locator(".itsparty__chip")
        assert [await c.get_attribute("data-goal") for c in await chips.all()] == ["passkey", "website", "release", "ideation"]      # Ideation last
        assert "a pitch there" in await chips.last.inner_text()
        assert await chips.first.get_attribute("aria-checked") == "true"
        types = [await c.get_attribute("data-type") for c in await form.locator(".newgoal__chip").all()]
        assert types == ["", "bug", "logo", "release"]                                                                  # Your own goal first, then the union of the parties' types, once each
        # a type: asked again, the party that takes it whole is suggested
        await form.locator('.newgoal__chip[data-type="logo"]').click()
        await its.locator(".itsparty__line", has_text="Orkmaster suggests").wait_for(timeout=WAIT_MS)
        assert calls(stub, "ideas.party_for")[-1] == {"type": "logo"}
        assert norm(await its.locator(".itsparty__line").inner_text()) == "Orkmaster suggests Website · takes it whole"
        chips = its.locator(".itsparty__chip")
        assert [await c.get_attribute("data-goal") for c in await chips.all()] == ["website", "passkey", "release", "ideation"]
        assert await chips.nth(0).get_attribute("aria-checked") == "true"
        assert "takes it whole" in await chips.nth(0).inner_text() and "needs Artist" in await chips.nth(1).inner_text()
        assert "no one there does it" in await chips.nth(2).inner_text() and "no one there does it" in await chips.nth(3).inner_text()
        assert min([(await c.bounding_box())["height"] for c in await chips.all()]) >= 44
        assert await form.locator(".joins").is_hidden()                                                                 # Website misses no one
        # another party picked: its fit says who joins
        await chips.nth(1).click()
        assert await chips.nth(1).get_attribute("aria-checked") == "true" and await chips.nth(0).get_attribute("aria-checked") == "false"
        await form.locator(".joinline").first.wait_for(timeout=WAIT_MS)                                                 # the join line of spec 52, as today
        assert "Artist joins the party" in await form.locator(".joinline").first.inner_text()
        await form.get_by_role("textbox", name="The goal").fill("A mark for the passkey")
        assert await page.evaluate(NO_SCROLL)
        await _shot_to(page, "phone-goal-party")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add")
        sent = calls(stub, "ideas.add")[-1]
        assert sent["track"] == "passkey" and sent["type"] == "logo" and sent["text"] == "A mark for the passkey" and sent["join"] == {"add": "artist"}


@pytest.mark.asyncio
async def test_the_suggested_party_is_the_one_the_goal_is_added_to(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        form = await _new_goal_from_project(page)
        await form.locator('.newgoal__chip[data-type="logo"]').click()
        await form.locator(".itsparty__line", has_text="Orkmaster suggests Website").wait_for(timeout=WAIT_MS)
        await form.get_by_role("textbox", name="The goal").fill("A logo for the website")
        await form.get_by_role("button", name="Add the goal").click()
        assert await _called(stub, "ideas.add")
        sent = calls(stub, "ideas.add")[-1]
        assert sent["track"] == "website" and sent["type"] == "logo" and "join" not in sent                              # it takes it whole: nothing joins
        await page.locator('.partydeck[data-goal="website"]').wait_for(timeout=WAIT_MS)                                  # the board shows the party the goal went to


@pytest.mark.asyncio
async def test_a_partys_own_new_goal_is_unchanged(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _pick_goal(page, "passkey")
        await page.locator(FAB).click()
        form = page.get_by_role("dialog", name="New goal")
        await form.wait_for(timeout=WAIT_MS)
        assert await form.locator(".newgoal__party").is_visible() and await form.locator(".itsparty").is_hidden()
        assert [await c.get_attribute("data-type") for c in await form.locator(".newgoal__chip").all()] == ["", "bug", "logo"]
        assert calls(stub, "ideas.party_for") == []


# -- The service worker --------------------------------------------------------------------------------------------------------------------------------

def test_the_service_worker_is_one_up_and_keeps_the_projects_module():
    sw = (Path(pwa.__file__).parent / "static" / "pwa" / "sw.js").read_text(encoding="utf-8")
    shell = sw[sw.index("const SHELL"):sw.index("];", sw.index("const SHELL"))]
    assert 'const CACHE = "orkcraft-app-v78";' in sw and '"shell-project.js"' in shell
