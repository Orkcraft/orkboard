"""Spec 65, the phone (docs/specs/65-hand-first.md §1–§5): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py. The members share the width (four builders, no sideways scroll), a card is a
token of 74 px, 5:7, its stacks wrapping in its column; a token has no goal's line, its type's sign at the top right, one value at its foot, the state in its edge and fill, what it waits for by name in its label;
the hand's zone is 250 px while a stop waits, the most urgent stands upright in front with its quick answers (`via: "front"`), the rest fan around it, a card right of the front mirrored; a tap on a fanned
card brings it to the front, a tap on the front's body raises it. Screenshots go to the folder named by ARENA_SHOTS."""
from __future__ import annotations

import re

import pytest

from tests import test_pwa_arena_browser as A
from tests.test_pwa_arena_browser import SCENE, _scene, _shot_to  # noqa: F401
from tests.test_pwa_deal_start_browser import RECORD as RECORD_DEAL, _centre, _dealt, _ready as _ready_deal, _start  # noqa: F401  (`_start`: the fixture that puts a started plan to work)
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _band, _called, _phone  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

ARTIST = {"slug": "artist", "name": "Artist"}
SOUND = {"slug": "sound", "name": "Sound designer"}
ELF2 = {"craft": "design", "race": "elf", "tier": "laborer"}
BUG = {"id": "bug", "name": "Fix a bug", "sign": "bug"}
PROBE = "(v) => { const i = document.createElement('i'); i.style.color = `var(${v})`; i.style.backgroundColor = `var(${v})`; document.body.append(i); const c = getComputedStyle(i).color; i.remove(); return c; }"
STYLE = "(e) => { const s = getComputedStyle(e); return { color: s.color, bg: s.backgroundColor, border: s.borderTopColor, style: s.borderTopStyle, transform: s.transform, width: s.width, height: s.height }; }"


def _task(tid, title, state, by, head, wave=1, after=(), **more):
    x = A.task(tid, title, state, A.SCREENS, wave, after=after, **more)
    x["by"], x["head"] = by, head
    return x


def four():
    """The scene's Backend and Screens with an Artist and a Sound designer added, two tasks each (spec 65 §5)."""
    reg = next(n for n in SCENE["map"]["nodes"] if n["slug"] == "register")
    reg["tasks"] += [_task("a1", "Passkey icon", "running", ARTIST, A.ELF, started="2026-10-21T09:55:00"), _task("a2", "Empty state picture", "waiting", ARTIST, A.ELF, 2, after=["a1"]),
                     _task("d1", "Sign-in chime", "running", SOUND, ELF2, started="2026-10-21T09:58:00"), _task("d2", "Error sound", "waiting", SOUND, ELF2, 2, after=["d1"])]
    g = SCENE["map"]["goals"][0]
    g["party"] = g["party"][:3] + [A.member(ARTIST, "build", A.ELF, "work"), A.member(SOUND, "build", ELF2, "work")] + g["party"][3:]
    g["team"] = [{"slug": m["slug"], "name": m["name"], "head": m["head"], "checks": m["band"] == "check", "every": False} for m in g["party"][1:]]
    for slug, name, head in (("artist", "Artist", A.ELF), ("sound", "Sound designer", ELF2)):
        SCENE["agents"]["roles"].append({"role": slug, "name": name, "model": "warrior", "max_parallel": 1, "builtin": False, "spend_today": 0.1, "chips": [], "kinds": ["pictures"],
                                         "week": {"finished": 1, "merged": 1, "first_time": 1, "spent": 0.1, "usd_per_merged": None}, "usd_task": 0.2, "head": head, "harness": {"id": "claude", "name": "Claude"}})


async def _ready(page):
    await page.locator(".gbar").wait_for(timeout=WAIT_MS)
    await page.locator(".strip .deck").first.wait_for(timeout=WAIT_MS)
    await page.locator(".hc.is-front").wait_for(timeout=WAIT_MS)
    await page.wait_for_timeout(700)                                                                      # the cards rise in steps; what is measured stands


async def _color(page, var):
    return await page.evaluate(PROBE, var)


# -- §1 the field ------------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_four_builders_share_the_width_with_no_sideways_scroll_and_their_tokens_are_74_px_5_to_7_wrapping_in_their_column(fake_repo, monkeypatch):
    four()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ready(page)
        for sel in ("html", ".arena-scroll"):
            sw, cw = await page.locator(sel).evaluate("(e) => [e.scrollWidth, e.clientWidth]")
            assert sw == cw, f"{sel} scrolls sideways: {sw} > {cw}"
        pairs = await page.locator(".strip .pair").evaluate_all("(ps) => ps.map((p) => { const r = p.getBoundingClientRect(); return [r.left, r.width, r.right]; })")
        assert len(pairs) == 4 and max(p[1] for p in pairs) - min(p[1] for p in pairs) < 1.01                      # four equal columns
        assert pairs[0][0] >= 5.9 and pairs[-1][2] <= 390 - 5.9                                                     # 6 px short of each side
        sizes = await page.locator(".strip .deck .tcard").evaluate_all("(cs) => cs.map((c) => { const r = c.getBoundingClientRect(); return [r.width, r.height]; })")
        assert len(sizes) >= 8
        for w, h in sizes:
            assert round(w) == 74 and abs(h - w * 7 / 5) <= 1.5, (w, h)                                             # 74 px wide, 5:7
        for tops in await page.locator(".strip .pair").evaluate_all("(ps) => ps.map((p) => [...p.querySelectorAll('.deck')].map((d) => Math.round(d.getBoundingClientRect().top)))"):
            assert len(tops) == len(set(tops)), tops                                                                # one to a row with four members
        await _shot_to(page, "built-h")


@pytest.mark.asyncio
async def test_with_two_builders_a_members_now_tokens_lie_on_one_row_and_planning_lays_its_goals_four_to_a_row(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ready(page)
        backend = await page.locator('.stack[data-column="backend"] .phase.is-now .deck').evaluate_all("(ds) => ds.map((d) => [Math.round(d.getBoundingClientRect().top), Math.round(d.getBoundingClientRect().left)])")
        assert len(backend) == 2 and abs(backend[0][0] - backend[1][0]) <= 8 and backend[0][1] != backend[1][1]    # the register stack (its edges take 8 px above it) and the cookie goal's failure side by side
        for sel in ("html", ".arena-scroll"):
            sw, cw = await page.locator(sel).evaluate("(e) => [e.scrollWidth, e.clientWidth]")
            assert sw == cw
        await _shot_to(page, "built-h2")
        await _band(page, "lead")
        goals = await page.locator(".phase.is-planning .deck").evaluate_all("(ds) => ds.map((d) => Math.round(d.getBoundingClientRect().top))")
        assert len(goals) == 6 and len(set(goals[:4])) == 1 and goals[4] > goals[0] and goals[5] == goals[4]            # four to a row
        assert await page.locator(".phase.is-planning .tcard__idea").count() == 0


# -- §2, §3 a token ---------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_token_has_no_goal_line_its_type_top_right_one_value_and_the_state_in_its_edge_and_fill_and_its_label_names_what_it_waits_for(fake_repo, monkeypatch):
    for slug in ("register", "cookie"):
        next(n for n in SCENE["map"]["nodes"] if n["slug"] == slug)["type"] = BUG
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ready(page)
        assert await page.locator(".strip .tcard__idea").count() == 0                                               # the goal's line is gone, on every stage
        for band in ("build", "check", "lead"):
            await _band(page, band)
            assert await page.locator(".strip .tcard__idea").count() == 0
        await _band(page, "build")
        running = page.locator('.stack .deck[data-task="k3"]')
        elem, sign = await running.locator(".tcard__top .ork-elem").bounding_box(), await running.locator(".tcard__top .tcard__type .ork-sign").bounding_box()
        box = await running.locator(".tcard").bounding_box()
        assert sign["x"] > elem["x"] + elem["width"] and sign["x"] + sign["width"] >= box["x"] + box["width"] - 8     # the type's sign at the top right
        assert re.fullmatch(r"\d+ (s|min|h)", (await running.locator(".tcard__foot").inner_text()).strip())            # a running task's foot is its time
        held = page.locator('.stack .deck[data-task="q2"]')
        assert (await held.locator(".tcard__foot").inner_text()).strip() == "18:00"                                    # a held one's, its hour
        waiting = page.locator('.stack .deck[data-task="k5"]')
        assert await waiting.locator(".tcard__foot").count() == 0 or (await waiting.locator(".tcard__foot").inner_text()).strip() == ""
        label = await waiting.get_attribute("aria-label")
        assert "after Challenge store, Credential table and migration" in label and not re.search(r"\bk[1-5]\b", label)
        assert "after Challenge store, Credential table and migration" in await waiting.get_attribute("title") and not re.search(r"\bk[1-5]\b", await waiting.get_attribute("title"))
        failed = page.locator('.stack .deck[data-state="failed"] .tcard')
        style = await failed.evaluate(STYLE)
        assert style["border"] == await _color(page, "--ork-danger") and style["bg"] == await _color(page, "--ork-raised")   # the danger edge, the raised fill
        run = await running.locator(".tcard").evaluate(STYLE)
        assert run["bg"] == await _color(page, "--ork-raised") and run["border"] == await _color(page, "--ork-edge")
        assert (await waiting.locator(".tcard").evaluate(STYLE))["style"] == "dashed"                                  # waiting: dashed on the canvas
        name = await running.locator(".tcard__name").evaluate("(e) => { const s = getComputedStyle(e); return [s.fontWeight, s.fontSize, s.lineHeight]; }")
        assert name == ["600", "11px", "14px"]


@pytest.mark.asyncio
async def test_a_typed_goals_type_sign_is_in_its_elements_colour(fake_repo, monkeypatch):
    next(n for n in SCENE["map"]["nodes"] if n["slug"] == "register")["type"] = BUG
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ready(page)
        sign = page.locator('.stack .deck[data-task="k3"] .tcard__type')
        assert await sign.evaluate("(e) => getComputedStyle(e).color") == await _color(page, "--ork-elem-meadow")


# -- §4 the hand ------------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_zone_is_250_px_with_stops_and_56_without_and_the_most_urgent_stands_upright_in_front_with_its_quick_answers(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ready(page)
        assert await page.locator(".handzone").evaluate("(e) => getComputedStyle(e).height") == "250px"
        front = page.locator(".hc.is-front")
        assert await front.count() == 1 and await front.get_attribute("data-kind") == "failed"                      # the failure is the most urgent
        box = await front.bounding_box()
        assert (round(box["width"]), round(box["height"])) == (150, 236)
        matrix = (await front.evaluate(STYLE))["transform"]
        assert re.fullmatch(r"matrix\(1, 0, 0, 1, 0, -?\d+(\.\d+)?\)", matrix), matrix                              # not turned
        assert await front.locator(".hc__quick button").all_inner_texts() == ["Start again", "Open…"]
        assert await front.locator(".hc__banner").inner_text() == "Secure cookie flags"
        assert await front.locator(".hc__text").inner_text() != ""
        fab, zone = await page.locator(".fab").bounding_box(), await page.locator(".handzone").bounding_box()
        assert fab["y"] + fab["height"] <= zone["y"]                                                                # the create button stands over the zone
        others = await page.locator(".hc:not(.is-front)").evaluate_all("(cs) => cs.map((c) => { const r = c.getBoundingClientRect(); return [c.offsetWidth, c.offsetHeight, c.querySelector('.hc__kind') === null]; })")
        assert others and all(o[:2] == [104, 150] for o in others) and all(o[2] for o in others)                    # 104 × 150, no kind word
        await _shot_to(page, "built-h-hand")


@pytest.mark.asyncio
async def test_the_zone_is_56_px_with_nothing_waiting(fake_repo, monkeypatch):
    SCENE["needs"] = []
    SCENE["results"] = []
    for n in SCENE["map"]["nodes"]:
        if n["slug"] == "cookie":
            n["tasks"] = [t for t in n["tasks"] if t["state"] != "failed"]
        n["results"] = []
        n["needs_you"] = ""
        n["asked"] = []
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".handzone__empty").wait_for(timeout=WAIT_MS)
        assert await page.locator(".handzone").evaluate("(e) => getComputedStyle(e).height") == "56px"
        assert await page.locator(".hc").count() == 0


@pytest.mark.asyncio
async def test_a_question_in_front_shows_its_recommended_choice_and_more_and_a_right_hand_card_draws_its_corner_mirrored(fake_repo, monkeypatch):
    SCENE["needs"] = [n for n in SCENE["needs"] if n["kind"] in ("asks", "proposal")]
    SCENE["results"] = []
    for n in SCENE["map"]["nodes"]:
        if n["slug"] == "cookie":
            n["tasks"] = [t for t in n["tasks"] if t["state"] != "failed"]
        n["results"] = []
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ready(page)
        front = page.locator(".hc.is-front")
        assert await front.get_attribute("data-kind") == "asks"
        texts = await front.locator(".hc__quick button").all_inner_texts()
        assert texts == ["● Only the lost phone’s passkey", "More…"]                                                 # the recommended choice (pressed), and More…
        right = page.locator(".hc.is-right").first
        gem, elem = await right.locator(".ork-gem").bounding_box(), await right.locator(".ork-elem").bounding_box()
        assert gem["x"] > elem["x"]                                                                                  # its gem right of its element
        left = page.locator(".hc:not(.is-front):not(.is-right)").first
        if await left.count():
            gem, elem = await left.locator(".ork-gem").bounding_box(), await left.locator(".ork-elem").bounding_box()
            assert gem["x"] < elem["x"]
        await front.locator("button", has_text="More…").click()
        await page.locator(".raised").wait_for(timeout=WAIT_MS)                                                      # More… raises it


@pytest.mark.asyncio
async def test_a_tap_on_a_fanned_card_brings_it_to_the_front_a_tap_on_the_front_body_raises_it_and_an_answer_from_the_front_says_via_front(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ready(page)
        fanned = page.locator(".hc:not(.is-front)[data-kind='plan']")
        key = await fanned.get_attribute("data-stop")
        at = await fanned.evaluate("""(b) => { const r = b.getBoundingClientRect();
          for (let y = r.top + 6; y < r.top + 40; y += 3) for (let x = r.left + 3; x < r.right - 2; x += 3) { const e = document.elementFromPoint(x, y); if (e && e.closest('.hc') === b) return { x, y }; } return null; }""")
        assert at
        await page.mouse.click(at["x"], at["y"])
        await page.locator(f'.hc.is-front[data-stop="{key}"]').wait_for(timeout=WAIT_MS)                              # it stands in front, nothing is raised
        assert await page.locator(".raised").count() == 0 and await page.locator(".hc.is-front").count() == 1
        box = await page.locator(".hc.is-front").bounding_box()
        assert (round(box["width"]), round(box["height"])) == (150, 236)
        await page.locator(".hc.is-front .hc__body").click(position={"x": 40, "y": 60})
        raised = page.locator(".raised")
        await raised.wait_for(timeout=WAIT_MS)
        assert await raised.get_attribute("data-stop") == key                                                         # the raised sheet of the same stop
        await page.keyboard.press("Escape")
        await page.wait_for_function("() => !document.querySelector('dialog.raised-dlg[open]')", timeout=WAIT_MS)
        await page.locator(".hc.is-front").wait_for(timeout=WAIT_MS)
        await page.locator(".hc.is-front .hc__quick button", has_text="Start the work").click()
        assert await _called(stub, "ideas.start", {"slug": "recovery", "via": "front"})


@pytest.mark.asyncio
async def test_start_again_from_the_front_card_says_via_front(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ready(page)
        await page.locator(".hc.is-front .hc__quick button", has_text="Start again").click()
        assert await _called(stub, "ideas.start", {"slug": "cookie", "via": "front"})


@pytest.mark.asyncio
async def test_a_plan_started_from_the_front_card_deals_its_tasks_from_the_front_cards_place(fake_repo, monkeypatch):
    """Spec 65 §4.5 with spec 57: the deal starts from the front card, and the command says `via: "front"`."""
    async with _phone(fake_repo, monkeypatch, init=RECORD_DEAL) as (stub, page):
        await _ready_deal(page)
        fanned = page.locator(".hc:not(.is-front)[data-kind='plan']")
        at = await fanned.evaluate("""(b) => { const r = b.getBoundingClientRect(); const own = [];
          for (let y = r.top + 6; y < r.top + 40; y += 3) for (let x = r.left + 3; x < r.right - 2; x += 3) { const e = document.elementFromPoint(x, y); if (e && e.closest('.hc') === b) own.push({ x, y }); }
          const cx = own.reduce((k, p) => k + p.x, 0) / own.length, cy = own.reduce((k, p) => k + p.y, 0) / own.length;
          return own.reduce((a, p) => (Math.hypot(p.x - cx, p.y - cy) < Math.hypot(a.x - cx, a.y - cy) ? p : a)); }""")
        await page.mouse.click(at["x"], at["y"])
        front = page.locator(".hc.is-front[data-kind='plan']")
        await front.wait_for(timeout=WAIT_MS)
        await page.wait_for_function("() => document.getAnimations().filter((a) => a.effect?.target?.closest?.('.hand')).length === 0", timeout=WAIT_MS)
        cx, cy, width = await _centre(front)
        await front.locator(".hc__quick button", has_text="Start the work").click()
        assert await _called(stub, "ideas.start", {"slug": "recovery", "via": "front"})
        rec = await _dealt(page, 2)
        dealt = [d for d in rec if d["kind"] == "dealt"]
        assert [(d["key"], d["column"]) for d in dealt[:2]] == [("recovery|now", "backend"), ("recovery|next", "screens")]
        for d in dealt[:2]:
            assert abs((d["cx"] + float(d["dx"][:-2])) - cx) <= 2 and abs((d["cy"] + float(d["dy"][:-2])) - cy) <= 2     # from the front card's centre
