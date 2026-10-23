"""Spec 64 part C, the phone (docs/specs/64-flags-raised.md §1, §2, §4; decisions §77): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py. When the flag line first stands, up to
six of its goals' elements travel from the gate (the box of the merge's press, kept 10 s, else the goals bar's gate button when it is in view and under nothing) to a row after its flag, steps(6) 0.30 s and 35 ms
apart, scaled from the source's height to their own; then the flag is raised (6 px, steps(3), 0.18 s) and the line lit once (0.6 s, steps(4)). The line is waited for while the gate's screen or a sheet lies over it
(10 s at most). Nothing under reduced motion; no second time at a later draw or after a reload; `sw.js` v68."""
from __future__ import annotations

import pytest

from tests.test_pwa_arena_browser import FLAG, SCENE, _scene, _redrawn, node  # noqa: F401
from tests.test_pwa_decks_browser import _reopen, norm
from tests.test_pwa_shell_browser import WAIT_MS, Stub, _called, _phone

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

ELEMENTS = ["meadow", "ice", "dust", "void", "lava"]
MODE = {"flags": ["kept", "g2"], "merge": "ok"}          # the goals a merge raises the flags of, the newest first; what the host answers the merge with: "ok" or "refuse"

# What the page does is recorded as it happens (a raise lasts 1 s): the copies that fly with the variables and the boxes they were given, and the line when its flag is raised and it is lit.
RECORD = """
(() => {
  window.__raise = [];
  const done = new WeakSet();                     // a node is told once (the observer sees it added and changed in one batch)
  const anim = (e) => { const s = getComputedStyle(e); return { name: s.animationName, duration: s.animationDuration, timing: s.animationTimingFunction, delay: s.animationDelay }; };
  const note = (e) => {
    if (!e.classList || done.has(e)) return;
    const at = Math.round(performance.now());
    if (e.classList.contains("flag-fly")) {
      done.add(e);
      const cs = getComputedStyle(e), st = e.style;
      window.__raise.push({ kind: "fly", at, element: ["meadow", "ice", "dust", "void", "lava"].find((n) => e.classList.contains(n)), left: parseFloat(st.left), top: parseFloat(st.top),
        width: parseFloat(st.width), height: parseFloat(st.height), dx: parseFloat(st.getPropertyValue("--dx")), dy: parseFloat(st.getPropertyValue("--dy")), s: parseFloat(st.getPropertyValue("--s")),
        ...anim(e), position: cs.position, pointer: cs.pointerEvents, z: cs.zIndex, parent: e.parentElement.tagName });
    }
    if (e.classList.contains("flagline") && e.classList.contains("is-raised")) {
      done.add(e);
      const slots = [...e.querySelectorAll(".flagline__row .ork-elem")].map((s) => { const c = getComputedStyle(s); return { hidden: c.visibility === "hidden", name: c.animationName, delay: c.animationDelay }; });
      window.__raise.push({ kind: "raised", at, line: anim(e), sign: anim(e.querySelector(".ork-sign.flag")), words: anim(e.querySelector(".flagline__words")), slots });
    }
  };
  document.addEventListener("DOMContentLoaded", () => new MutationObserver((ms) => { for (const m of ms) { if (m.type === "attributes") note(m.target); for (const n of m.addedNodes) if (n.nodeType === 1) { note(n); n.querySelectorAll && n.querySelectorAll("*").forEach(note); } } })
    .observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] }));
})();
"""
REC = "() => window.__raise"


def ms(seconds):
    """A computed time, "0.335s", in milliseconds."""
    return round(float(seconds[:-1]) * 1000)


@pytest.fixture(autouse=True)
def _merge(monkeypatch, _scene):
    """`ideas.gate_merge` answers as `MODE` says; an ok merge takes the goals of `MODE["flags"]` into main: they have their flags, the gate holds nothing."""
    MODE.update(flags=["kept", "g2"], merge="ok")
    for i in range(2, 9):                                                                                   # done goals that wait in dev, each with an element
        SCENE["map"]["nodes"].append(node(f"g{i}", f"Goal {i}", "done", "done", folded=True, element=ELEMENTS[i % 5]))
    real = Stub.commands

    def commands(self):
        def merge(a):
            self.calls.append(("ideas.gate_merge", {k: v for k, v in a.items() if k not in ("link", "device")}))
            if MODE["merge"] == "refuse":
                return {"error": "Nothing was merged."}
            raise_flags(MODE["flags"])
            return self.bump({"ok": True, "commit": "abc", "note": ""})
        return {**real(self), "ideas.gate_merge": merge}
    monkeypatch.setattr(Stub, "commands", commands)


def raise_flags(slugs):
    """The gate took these goals into main, the first the newest (an hour apart, all newer than the flag of before)."""
    for i, slug in enumerate(slugs):
        next(n for n in SCENE["map"]["nodes"] if n["slug"] == slug)["flag"] = {**FLAG, "at": f"2026-10-21T{12 - i:02d}:00:00", "tasks": 2, "first_time": 1, "usd": 0.8}
    SCENE["map"]["goals"][0]["flags"] = len([n for n in SCENE["map"]["nodes"] if n["flag"]])
    SCENE["map"]["rev"] = str(int(SCENE["map"]["rev"]) + 1)
    SCENE["gate"] = {**SCENE["gate"], "commits": 0, "files": 0, "ideas": []}


def element_of(slug):
    return next(n for n in SCENE["map"]["nodes"] if n["slug"] == slug)["element"]


async def _ready(page):
    """The party read, and the flags of before kept: the first start says none."""
    await page.locator(".gbar").wait_for(timeout=WAIT_MS)
    await page.wait_for_function("() => localStorage.getItem('orkcraft.flags.goals')", timeout=WAIT_MS)


async def _merged(page, stub):
    """The gate's screen opened and *Merge dev into main* pressed: the button's box at the press. The screen stays (it says *main has every goal of dev*), the flag line stands under it."""
    await page.locator(".gbar__gate").click()
    merge = page.locator(".screen").get_by_role("button", name="Merge dev into main")
    await merge.wait_for(timeout=WAIT_MS)
    box = await merge.bounding_box()
    await merge.click()
    assert await _called(stub, "ideas.gate_merge")
    return box


async def _flown(page, minimum):
    await page.wait_for_function("(n) => window.__raise.filter((r) => r.kind === 'fly').length >= n", arg=minimum, timeout=WAIT_MS * 2)
    return [r for r in await page.evaluate(REC) if r["kind"] == "fly"]


async def _raised(page):
    await page.wait_for_function("() => window.__raise.some((r) => r.kind === 'raised')", timeout=WAIT_MS * 2)
    return next(r for r in await page.evaluate(REC) if r["kind"] == "raised")


async def _nothing_moved(page):
    """No copy flew and no line was raised (after a moment: a motion would have begun)."""
    await page.wait_for_timeout(700)
    assert await page.evaluate(REC) == [] and await page.locator(".flag-fly").count() == 0 and await page.locator(".flagline.is-raised").count() == 0


async def _row(page):
    """The element classes of the line's row, in order."""
    return await page.locator(".flagline__row .ork-elem").evaluate_all("els => els.map((e) => ['meadow', 'ice', 'dust', 'void', 'lava'].find((n) => e.classList.contains(n)))")


def centre(fly):
    """Where a copy starts: its own centre moved by the variables."""
    return fly["left"] + fly["width"] / 2 + fly["dx"], fly["top"] + fly["height"] / 2 + fly["dy"]


@pytest.mark.asyncio
async def test_a_merge_from_the_gate_raises_two_flags_their_elements_travel_from_the_merge_to_the_line_and_its_flag_is_raised_and_the_line_lit(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        press = await _merged(page, stub)
        await page.locator(".flagline").wait_for(state="attached", timeout=WAIT_MS * 2)                   # the line stands, under the gate's screen
        await page.wait_for_timeout(700)
        assert await page.evaluate(REC) == []                                                               # nothing moves where nobody looks: it waits for the screen to go
        await page.get_by_role("button", name="Back", exact=True).click()
        flies = await _flown(page, 2)
        assert len(flies) == 2 and [f["element"] for f in flies] == [element_of("kept"), element_of("g2")]  # the line's goals, newest first
        for f in flies:
            x, y = centre(f)
            assert abs(x - (press["x"] + press["width"] / 2)) <= 2 and abs(y - (press["y"] + press["height"] / 2)) <= 2       # from the merge's press (the screen is gone: its box was kept)
            assert abs(f["s"] - press["height"] / f["height"]) <= 0.02                                                       # scaled from its height to the element's own
        assert [ms(f["delay"]) for f in flies] == [0, 35] and {f["name"] for f in flies} == {"deal"}                         # 35 ms apart, the deal's
        assert {f["duration"] for f in flies} == {"0.3s"} and {f["timing"] for f in flies} == {"steps(6)"}                  # 0.30 s in steps
        assert all(f["position"] == "fixed" and f["pointer"] == "none" and f["parent"] == "BODY" and int(f["z"]) > 30 for f in flies)       # over the page, taking nothing
        raised = await _raised(page)
        assert (raised["line"]["name"], raised["line"]["duration"], raised["line"]["timing"], ms(raised["line"]["delay"])) == ("lit", "0.6s", "steps(4)", 335)         # lit once, when the last lands (35 ms + 0.30 s)
        assert (raised["sign"]["name"], raised["sign"]["duration"], raised["sign"]["timing"], ms(raised["sign"]["delay"])) == ("raise", "0.18s", "steps(3)", 335)     # the flag steps up
        assert [s["hidden"] for s in raised["slots"]] == [True, True] and {s["name"] for s in raised["slots"]} == {"landed"}      # the row's elements show as their copies land
        row = page.locator(".flagline__row .ork-elem")
        line = await page.locator(".flagline").bounding_box()
        for f, slot in zip(flies, [await row.nth(0).bounding_box(), await row.nth(1).bounding_box()]):
            assert abs(f["left"] - slot["x"]) <= 1 and abs(f["top"] - slot["y"]) <= 1                                            # they land in the row …
            assert line["y"] <= slot["y"] and slot["y"] + slot["height"] <= line["y"] + line["height"]                          # … which is in the line
        flag = (await page.locator(".flagline .ork-sign.flag").bounding_box())["x"]
        assert (await row.nth(0).bounding_box())["x"] > flag and (await row.nth(1).bounding_box())["x"] < (await page.locator(".flagline__words").bounding_box())["x"]     # after the flag, before the words
        await page.wait_for_function("() => document.querySelectorAll('.flag-fly').length === 0", timeout=WAIT_MS)         # the copies are gone …
        assert await _row(page) == [element_of("kept"), element_of("g2")]                                                  # … the row has the two elements
        await page.wait_for_function("() => [...document.querySelectorAll('.flagline__row .ork-elem')].every((e) => getComputedStyle(e).visibility === 'visible')", timeout=WAIT_MS)
        assert norm(await page.locator(".flagline").inner_text()) == "2 flags raised · Where the credentials are kept and Goal 2 are in main"
        SCENE["map"]["rev"] = "9"                                                                                          # the Board changes: the line is drawn again …
        await _redrawn(stub, page)
        assert await _row(page) == [element_of("kept"), element_of("g2")] and await page.locator(".flagline.is-raised, .flagline__row .is-dealt").count() == 0       # … its row still, nothing flies again
        assert len(await _flown(page, 2)) == 2 and len([r for r in await page.evaluate(REC) if r["kind"] == "raised"]) == 1
        page = await _reopen(page)                                                                                         # a reload: the line does not stand again
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(800)
        assert await page.locator(".flagline").count() == 0 and await page.evaluate(REC) == []


@pytest.mark.asyncio
async def test_eight_flags_put_six_elements_in_the_row_and_the_words_name_the_rest(fake_repo, monkeypatch):
    MODE["flags"] = ["kept", "g2", "g3", "g4", "g5", "g6", "g7", "g8"]
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        await _merged(page, stub)
        await page.locator(".flagline").wait_for(state="attached", timeout=WAIT_MS * 2)
        await page.get_by_role("button", name="Back", exact=True).click()
        flies = await _flown(page, 6)
        await page.wait_for_timeout(700)
        flies = [r for r in await page.evaluate(REC) if r["kind"] == "fly"]
        assert [f["element"] for f in flies] == [element_of(s) for s in MODE["flags"][:6]]                                  # six travel, the newest first
        assert [ms(f["delay"]) for f in flies] == [35 * i for i in range(6)]
        raised = await _raised(page)
        assert ms(raised["line"]["delay"]) == 475 and len(raised["slots"]) == 6                                              # the last lands after 5 × 35 ms + 0.30 s
        await page.wait_for_function("() => document.querySelectorAll('.flag-fly').length === 0", timeout=WAIT_MS)
        assert await _row(page) == [element_of(s) for s in MODE["flags"][:6]]
        words = norm(await page.locator(".flagline__words").inner_text())
        assert words == "8 flags raised · Where the credentials are kept, Goal 2 and 6 more are in main"                  # the seventh and the eighth have no element: the words say them


@pytest.mark.asyncio
async def test_flags_raised_elsewhere_travel_from_the_gates_button(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raise_flags(["kept", "g2"])                                                                                         # a merge on the desktop: no press on this phone
        await _redrawn(stub, page, 100)
        flies = await _flown(page, 2)
        gate = await page.locator(".gbar__gate").bounding_box()
        for f in flies:
            x, y = centre(f)
            assert abs(x - (gate["x"] + gate["width"] / 2)) <= 2 and abs(y - (gate["y"] + gate["height"] / 2)) <= 2         # from the gate's button
            assert abs(f["s"] - gate["height"] / f["height"]) <= 0.02
        await _raised(page)


@pytest.mark.asyncio
async def test_with_no_gate_on_screen_nothing_travels_and_the_flag_is_still_raised(fake_repo, monkeypatch):
    SCENE["gate"]["same"] = True                                                                                            # dev and main are one branch: no gate on screen
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        assert await page.locator(".gbar__gate").count() == 0
        raise_flags(["kept", "g2"])
        await _redrawn(stub, page, 100)
        raised = await _raised(page)
        assert (raised["line"]["name"], ms(raised["line"]["delay"])) == ("lit", 0) and (raised["sign"]["name"], ms(raised["sign"]["delay"])) == ("raise", 0)       # the flag is raised and the line lit at once
        assert await page.locator(".flag-fly").count() == 0 and not [r for r in await page.evaluate(REC) if r["kind"] == "fly"]       # no copy
        assert await _row(page) == [element_of("kept"), element_of("g2")] and await page.locator(".flagline__row .is-dealt").count() == 0   # the row is there, drawn at once


@pytest.mark.asyncio
async def test_a_refused_merge_keeps_no_box_and_a_sheet_over_the_line_is_waited_for(fake_repo, monkeypatch):
    MODE["merge"] = "refuse"
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        await _merged(page, stub)                                                                                           # refused: the press's box is not kept
        raise_flags(["kept", "g2"])                                                                                         # the flags come some other way (the desktop) …
        await page.locator(".screen").get_by_role("button", name="Back", exact=True).click()
        await page.locator(".gbar__head").click()                                                                           # … while a sheet lies over the line
        sheet = page.get_by_role("dialog", name="Goals")
        await sheet.wait_for(timeout=WAIT_MS)
        await _redrawn(stub, page, 100)
        await page.locator(".flagline").wait_for(state="attached", timeout=WAIT_MS * 2)
        await _nothing_moved(page)                                                                                          # it waits: nobody sees the line
        await page.keyboard.press("Escape")
        flies = await _flown(page, 2)
        gate = await page.locator(".gbar__gate").bounding_box()
        x, y = centre(flies[0])
        assert abs(x - (gate["x"] + gate["width"] / 2)) <= 2 and abs(y - (gate["y"] + gate["height"] / 2)) <= 2             # from the gate's button, not from a press that was refused
        await _raised(page)


@pytest.mark.asyncio
async def test_a_line_first_in_view_after_ten_seconds_stands_still(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        await page.locator(".gbar__head").click()
        await page.get_by_role("dialog", name="Goals").wait_for(timeout=WAIT_MS)
        raise_flags(["kept", "g2"])
        await _redrawn(stub, page, 100)
        await page.locator(".flagline").wait_for(state="attached", timeout=WAIT_MS * 2)
        await page.wait_for_timeout(10500)                                                                                  # nobody looked for 10 s: the raise is dropped
        await page.keyboard.press("Escape")
        await page.get_by_role("dialog", name="Goals").wait_for(state="hidden", timeout=WAIT_MS)
        await _nothing_moved(page)
        assert await _row(page) == [element_of("kept"), element_of("g2")]                                                   # the row is drawn still


@pytest.mark.asyncio
async def test_under_reduced_motion_nothing_flies_and_the_row_is_drawn(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        await page.emulate_media(reduced_motion="reduce")
        await _merged(page, stub)
        await page.locator(".flagline").wait_for(state="attached", timeout=WAIT_MS * 2)
        await page.get_by_role("button", name="Back", exact=True).click()
        await page.locator(".flagline").wait_for(timeout=WAIT_MS)
        await _nothing_moved(page)
        assert await _row(page) == [element_of("kept"), element_of("g2")] and await page.locator(".flagline__row .is-dealt").count() == 0       # the row stands with its elements
        assert await page.locator(".flagline__row .ork-elem").evaluate_all("els => els.every((e) => getComputedStyle(e).visibility === 'visible')")
        assert await page.locator(".flagline .ork-sign.flag").evaluate("e => getComputedStyle(e).animationName") == "none"
