"""Spec 60 part C, the phone's members wear their tool and level (docs/specs/60-phone-member-marks.md §1–§4): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py (a party,
*Sign in with a passkey*), its party given a leader and three builders on two tools and three levels. Over each column the member's tool mark before its name and its level's chevrons after it
(16 × 16, the name a span of its own, `aria-label` says both once, the text the name alone); a mark the phone has no picture for, or a head with no tier, is not drawn; a long name is cut and the
marks never; the leader's column too; on a member's card the tool in words after the head's; the stage switch as it was; the service worker's version."""
from __future__ import annotations

import copy

import pytest

from orkboard.gui import pwa
from tests.test_pwa_arena_browser import SCENE, _scene  # noqa: F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _band, _phone

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

CLAUDE, CODEX = {"id": "claude", "name": "Claude"}, {"id": "codex", "name": "Codex"}
TASKMASTER = {"slug": "taskmaster", "name": "Taskmaster", "head": {"craft": "engineering", "race": "peon", "tier": "elder"}}
BACKEND = {"slug": "backend", "name": "Backend", "head": {"craft": "engineering", "race": "peon", "tier": "warrior"}}                 # Seasoned, on Claude
SCREENS = {"slug": "screens", "name": "Screens", "head": {"craft": "design", "race": "elf", "tier": "laborer"}}                         # Novice, on Codex
LEVELS = {"slug": "levels", "name": "Level designer", "head": {"craft": "data", "race": "goblin", "tier": "elder"}}                    # Veteran, on Claude
CONFIRMED = {"taskmaster": CLAUDE, "backend": CLAUDE, "screens": CODEX, "levels": CLAUDE, "reviewer": CLAUDE, "words": CLAUDE}


@pytest.fixture(autouse=True)
def _fresh_scene():
    saved = copy.deepcopy(SCENE)
    yield
    SCENE.clear()
    SCENE.update(saved)


def norm(s):
    return " ".join(s.split())


def _role(slug):
    return next(r for r in SCENE["agents"]["roles"] if r["role"] == slug)


def party(*builders, tools=None):
    """The scene's party with these builders (a leader, `builders`, the checkers as they are) and each member's tool; a builder with no task stands in its column with no task."""
    goal = SCENE["map"]["goals"][0]
    made = [m for m in goal["party"] if m["band"] != "build"]
    goal["party"] = [m for m in made if m["band"] == "lead"] + [{**b, "band": "build", "state": "free", "why": ""} for b in builders] + [m for m in made if m["band"] == "check"]
    for b in builders:
        if not any(r["role"] == b["slug"] for r in SCENE["agents"]["roles"]):
            SCENE["agents"]["roles"].append({**copy.deepcopy(_role("backend")), "role": b["slug"], "name": b["name"], "head": b["head"]})
    for slug, tool in {**CONFIRMED, **(tools or {})}.items():
        for r in SCENE["agents"]["roles"]:
            if r["role"] == slug:
                r["harness"] = tool
                r["head"] = next((m["head"] for m in goal["party"] if m["slug"] == slug), r["head"])


async def row(colname):
    """What a column's head holds, in order: a mark's image (its file), a name's text."""
    return await colname.evaluate("e => [...e.children].map((c) => c.tagName === 'IMG' ? c.getAttribute('src') : c.textContent)")


@pytest.mark.asyncio
async def test_each_column_wears_its_members_tool_before_its_name_and_its_level_after_it(fake_repo, monkeypatch):
    party(BACKEND, SCREENS, LEVELS)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        names = page.locator(".colname")
        await names.nth(2).wait_for(timeout=WAIT_MS)
        assert [await row(n) for n in await names.all()] == [["marks/harness-claude.png", "Backend", "marks/rank-2.png"], ["marks/harness-codex.png", "Screens", "marks/rank-1.png"],
                                                             ["marks/harness-claude.png", "Level designer", "marks/rank-3.png"]]     # the tool, the name, the level's chevrons
        assert [norm(await n.text_content()) for n in await names.all()] == ["Backend", "Screens", "Level designer"]                  # its text is the name alone: images have none
        assert [await n.get_attribute("aria-label") for n in await names.all()] == ["Backend · runs on Claude · Seasoned", "Screens · runs on Codex · Novice",
                                                                                      "Level designer · runs on Claude · Veteran"]     # said once
        backend = names.first
        assert await backend.locator('img[src*="harness-claude"]').count() == 1 and await backend.locator('img[src*="rank-2"]').count() == 1
        tool, name, level = backend.locator("img").first, backend.locator("span"), backend.locator("img").last
        assert [await tool.get_attribute("title"), await level.get_attribute("title")] == ["Runs on Claude", "Seasoned: its level"]
        assert [await tool.get_attribute("alt"), await level.get_attribute("alt")] == ["", ""]                                         # their words are the title's, the label says them once
        assert await tool.get_attribute("srcset") == "marks/harness-claude@2x.png 2x" and await level.get_attribute("srcset") == "marks/rank-2@2x.png 2x"
        bar, t, n, lv = await backend.bounding_box(), await tool.bounding_box(), await name.bounding_box(), await level.bounding_box()
        assert round(bar["height"]) == 28 and (round(t["width"]), round(t["height"]), round(lv["width"]), round(lv["height"])) == (16, 16, 16, 16)
        assert round(n["x"] - (t["x"] + 16)) == 4 and round(lv["x"] - (n["x"] + n["width"])) == 4                                  # --ork-2 between the three
        left, right = t["x"] - bar["x"], bar["x"] + bar["width"] - (lv["x"] + 16)
        assert abs(left - right) <= 1                                                                                              # centred over the column
        assert await names.first.evaluate("e => getComputedStyle(e).display === 'flex' && getComputedStyle(e).justifyContent === 'center'")
        for img in await page.locator(".colname img").all():
            assert await img.evaluate("e => e.complete && e.naturalWidth > 0")                                                    # the phone serves them
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_leaders_column_and_the_checkers_wear_theirs_too(fake_repo, monkeypatch):
    party(BACKEND, SCREENS, LEVELS)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".colname").first.wait_for(timeout=WAIT_MS)
        await _band(page, "lead")
        lead = page.locator('.colname[data-member="taskmaster"]')
        await lead.wait_for(timeout=WAIT_MS)
        assert await row(lead) == ["marks/harness-claude.png", "Taskmaster", "marks/rank-3.png"] and await lead.get_attribute("aria-label") == "Taskmaster · runs on Claude · Veteran"
        assert await page.locator(".colname").count() == 1 and await page.evaluate(NO_SCROLL)
        await _band(page, "check")
        names = page.locator(".colname")
        await names.nth(1).wait_for(timeout=WAIT_MS)
        assert [await row(n) for n in await names.all()] == [["marks/harness-claude.png", "Reviewer", "marks/rank-3.png"], ["marks/harness-claude.png", "Words", "marks/rank-1.png"]]
        assert [await n.get_attribute("aria-label") for n in await names.all()] == ["Reviewer · runs on Claude · Veteran", "Words · runs on Claude · Novice"]


@pytest.mark.asyncio
async def test_a_tool_the_phone_has_no_mark_for_leaves_the_chevrons_only_a_head_with_no_tier_the_tool_only_and_neither_the_name(fake_repo, monkeypatch):
    nameless = {**LEVELS, "slug": "plain", "name": "Plain", "head": None}
    party(BACKEND, SCREENS, LEVELS, nameless, tools={"screens": {"id": "windsurf", "name": "Windsurf"}, "levels": CLAUDE, "plain": CLAUDE})
    SCENE["map"]["goals"][0]["party"][3]["head"] = {"craft": "data", "race": "goblin"}                                              # a head with no tier: no level
    SCENE["map"]["goals"][0]["party"][4]["head"] = None
    _role("plain")["harness"] = {"id": "", "name": ""}                                                                          # a role whose tool is not known
    _role("backend").pop("harness")                                                                                             # a role the host sent no tool for
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        names = page.locator(".colname")
        await names.nth(3).wait_for(timeout=WAIT_MS)
        assert [await row(n) for n in await names.all()] == [["Backend", "marks/rank-2.png"], ["Screens", "marks/rank-1.png"], ["marks/harness-claude.png", "Level designer"], ["Plain"]]
        assert [await n.get_attribute("aria-label") for n in await names.all()] == ["Backend · Seasoned", "Screens · runs on Windsurf · Novice", "Level designer · runs on Claude", "Plain"]
        assert [norm(await n.text_content()) for n in await names.all()] == ["Backend", "Screens", "Level designer", "Plain"]
        assert await page.locator(".colname img[src*='windsurf']").count() == 0 and await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_long_name_is_cut_and_the_marks_never_both_16_by_16_inside_the_column(fake_repo, monkeypatch):
    long = {**LEVELS, "name": "Design system designer"}
    party(BACKEND, SCREENS, long)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        names = page.locator(".colname")
        await names.nth(2).wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(300)
        pairs = page.locator(".strip:not(.is-few) .pair")
        assert await pairs.count() == 3 and abs((await pairs.first.bounding_box())["width"] - 148) <= 1                              # three columns: 148 px each, scrolled
        cut = names.nth(2)
        shown = cut.locator("span")
        assert await shown.evaluate("e => e.scrollWidth > e.clientWidth && getComputedStyle(e).textOverflow === 'ellipsis' && getComputedStyle(e).overflow === 'hidden'")      # the name is cut …
        assert norm(await cut.text_content()) == "Design system designer" and await row(cut) == ["marks/harness-claude.png", "Design system designer", "marks/rank-3.png"]
        col = await pairs.nth(2).bounding_box()
        for img in await cut.locator("img").all():                                                                                  # … the marks never
            box = await img.bounding_box()
            assert (round(box["width"]), round(box["height"])) == (16, 16) and box["x"] >= col["x"] and box["x"] + 16 <= col["x"] + col["width"]
        assert await cut.evaluate("e => e.scrollWidth <= e.clientWidth") and round((await cut.bounding_box())["height"]) == 28           # the row stays 28 px high and holds
        short = names.first                                                                                                         # a name that fits is whole
        assert await short.locator("span").evaluate("e => e.scrollWidth <= e.clientWidth")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_with_one_or_two_columns_sharing_the_width_a_long_name_is_whole(fake_repo, monkeypatch):
    party(BACKEND, {**SCREENS, "name": "Level designer"})                                                                         # (the scene's tasks are Backend's and Screens's: no third column)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        names = page.locator(".colname")
        await names.nth(1).wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(300)
        pairs = page.locator(".strip.is-few .pair")
        assert await pairs.count() == 2
        assert [await row(n) for n in await names.all()] == [["marks/harness-claude.png", "Backend", "marks/rank-2.png"], ["marks/harness-codex.png", "Level designer", "marks/rank-1.png"]]
        assert await names.nth(1).locator("span").evaluate("e => e.scrollWidth <= e.clientWidth")                                    # (about 180 px each: room for the name and both marks)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_on_a_members_card_the_tool_follows_the_heads_words_the_leaders_and_the_grunts_too(fake_repo, monkeypatch):
    party(BACKEND, SCREENS, LEVELS)
    _role("levels").pop("harness")                                                                                                 # a tool that is not known: nothing is added
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".colname").first.wait_for(timeout=WAIT_MS)
        info = page.locator(".solo .solo__info")
        for member, words in (("backend", "Backend · Seasoned ork · Engineering · Claude"), ("screens", "Screens · Novice elf · Design · Codex"), ("levels", "Level designer · Veteran goblin · Data")):
            await page.locator(f'button.band__face[data-member="{member}"]').click()
            await info.wait_for(timeout=WAIT_MS)
            assert norm(await info.locator("span").first.inner_text()) == words                                                    # the tool is the last word of the kit line
            await page.locator('.solo [data-act="everyone"]').click()
            await info.wait_for(state="detached", timeout=WAIT_MS)
        await _band(page, "lead")
        await page.locator('button.band__face[data-member="taskmaster"]').click()
        await info.wait_for(timeout=WAIT_MS)
        assert norm(await info.locator("span").first.inner_text()) == "Taskmaster · Veteran ork · Engineering · Claude"
        assert "Claude" not in norm(await page.locator(".solo .solo__title").inner_text())
        await page.locator('.solo [data-act="everyone"]').click()
        await info.wait_for(state="detached", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_the_stage_switch_wears_no_mark_and_its_faces_are_as_they_were(fake_repo, monkeypatch):
    party(BACKEND, SCREENS, LEVELS)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".colname").first.wait_for(timeout=WAIT_MS)
        assert await page.locator(".bands .ork-mark").count() == 0 and await page.locator(".bands img[src^='marks/']").count() == 0
        faces = page.locator('.band[data-band="build"] img.ork-race__head')
        assert await faces.count() == 3
        for f in await faces.all():
            box = await f.bounding_box()
            assert (round(box["width"]), round(box["height"])) == (24, 22)                                                         # the heads, 24 × 22, with no 16-px mark beside them
        assert [await f.get_attribute("aria-label") for f in await page.locator('.band[data-band="build"] button.band__face').all()] == ["Only Backend’s tasks", "Only Screens’s tasks",
                                                                                                                                       "Only Level designer’s tasks"]
        await _band(page, "lead")
        assert await page.locator(".bands .ork-mark").count() == 0


def test_the_service_worker_is_at_v68():
    sw = (pwa.ROOT / "sw.js").read_text(encoding="utf-8")
    assert 'const CACHE = "orkcraft-app-v73";' in sw                                                                              # specs 60 C and 61 C: one up from v67
