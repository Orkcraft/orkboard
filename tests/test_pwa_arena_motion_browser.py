"""Spec 49 part C, motion on the phone (docs/specs/49-one-window.md §11, §13 "C"; spec 50 §4): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py. Motion says what
changed and never decorates: a stack that appears rises into its column; one that leaves (a merge, a drop) fades where it stands with a one-frame orkUI sign and its column settles up toward
the member; one that moves slides, with the stacks it passes; a merge lights the member's first number and its column's count once. None under reduced motion, on the first read of a goal or
while the page is hidden; nothing moves under a finger or the focus; the bottom row does not shift while a stop is popped. The filter, the spread and New goal's card move in
tests/test_pwa_decks_browser.py."""
from __future__ import annotations

import copy

import pytest

from tests.test_pwa_arena_browser import SCENE, _scene, member, node, OWN, result, task, BACKEND  # noqa: F401
from tests.test_pwa_shell_browser import WAIT_MS, _band, _phone, _pop  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

# What the page does is recorded as it happens (a fade lasts 0.3 s: it is not waited for): the animations the field plays and the classes it gives.
RECORD = """
(() => {
  window.__anims = []; window.__seen = [];
  const animate = Element.prototype.animate;
  Element.prototype.animate = function (frames, options) { window.__anims.push({ key: this.dataset ? this.dataset.key || this.dataset.ghost || this.className : "", from: frames[0] && frames[0].transform, ms: options && options.duration }); return animate.call(this, frames, options); };
  const note = (e) => {
    if (!e.classList) return;
    if (e.classList.contains("is-leaving")) window.__seen.push({ t: Math.round(performance.now()), kind: "leave", sign: e.dataset.sign, key: e.dataset.ghost, index: [...e.parentElement.children].filter((c) => c.classList.contains("deck")).indexOf(e) });
    if (e.classList.contains("is-drawn")) window.__seen.push({ t: Math.round(performance.now()), kind: "rise", key: e.dataset.key, name: getComputedStyle(e).animationName });
    if (e.classList.contains("is-reward")) window.__seen.push({ t: Math.round(performance.now()), kind: "reward", cls: e.className, text: e.textContent });
  };
  document.addEventListener("DOMContentLoaded", () => new MutationObserver((ms) => { for (const m of ms) { if (m.type === "attributes") note(m.target); for (const n of m.addedNodes) if (n.nodeType === 1) { note(n); n.querySelectorAll && n.querySelectorAll("*").forEach(note); } } })
    .observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] }));
})();
"""
SEEN = "() => window.__seen"
BACKEND_COLUMN = '.stack[data-column="backend"]'


def register():
    return SCENE["map"]["nodes"][6]


def tasks_of(node_):
    return {t["id"]: t for t in node_["tasks"]}


async def _ready(page):
    """The window read, its Implementation stage shown, and a moment kept for the second read (the first read of a goal is not a change)."""
    await page.locator(f"{BACKEND_COLUMN} .deck").first.wait_for(timeout=WAIT_MS)
    await page.wait_for_timeout(2300)


async def _keys(page, column="backend"):
    """The stacks of a column, in the order they lie (the rows by phase, top down): `<goal>|<phase>`."""
    return [await c.get_attribute("data-key") for c in await page.locator(f'.stack[data-column="{column}"] .deck:not(.is-leaving)').all()]


@pytest.mark.asyncio
async def test_nothing_moves_on_the_first_read_of_a_goal(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        assert await page.evaluate(SEEN) == [] and await page.evaluate("() => window.__anims") == []        # the cards were there when the page first drew them: no rise, no fade, no slide
        assert await page.evaluate("() => document.getAnimations().filter((a) => ['rise', 'leave', 'flash', 'reward'].includes(a.animationName)).length") == 0
        await _band(page, "lead")                                                                      # another stage of the same goal is not a change either
        await _band(page, "build")
        assert await page.evaluate(SEEN) == []


@pytest.mark.asyncio
async def test_a_stack_that_appears_rises_into_its_place_from_below_once(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        node_ = register()
        node_["tasks"].append(task("n1", "A new task", "waiting", BACKEND, 3))                           # two waves after the goal's current one: *later*, a stack of its own
        stub.bump({})
        await page.wait_for_function("() => window.__seen.some((s) => s.kind === 'rise')", timeout=WAIT_MS * 2)
        rises = [s for s in await page.evaluate(SEEN) if s["kind"] == "rise"]
        assert {r["key"] for r in rises} == {"register|later"} and {r["name"] for r in rises} == {"rise"}   # the one that was not there, and only it
        assert await page.evaluate("() => getComputedStyle(document.querySelector('.deck.is-drawn') || document.body).animationDuration") in ("0.36s", "0s")
        await page.wait_for_timeout(1500)                                                              # it is drawn again with the next read: it does not rise twice
        later = [s["t"] for s in await page.evaluate(SEEN) if s["kind"] == "rise"]
        assert max(later) - min(later) < 300


@pytest.mark.asyncio
async def test_a_stack_that_leaves_fades_where_it_stands_with_its_sign_then_what_lies_behind_it_steps_up_toward_the_member(fake_repo, monkeypatch):
    SCENE["map"]["nodes"].append(node("x1", "An extra goal", "working", "implementation", tasks=[task("x1t", "An extra task", "ready", BACKEND, 1)]))      # a third stack of the first row: with two tokens to a row (spec 65 §1.2) it lies in a row of its own, behind
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        assert await _keys(page) == ["register|now", "cookie|now", "x1|now", "register|next"]
        tasks_of(SCENE["map"]["nodes"][8])["q1"]["state"] = "merged"                                     # the failed one, alone in its stack, merges
        stub.bump({})
        await page.wait_for_function("() => window.__seen.some((s) => s.kind === 'leave')", timeout=WAIT_MS * 2)
        leave = [s for s in await page.evaluate(SEEN) if s["kind"] == "leave"]
        assert {(s["key"], s["sign"], s["index"]) for s in leave} == {("cookie|now", "check", 1)}        # where it stood: second in its row, the one-frame ✓ (orkUI's sign, not a typed one)
        await page.wait_for_function("() => window.__anims.length > 0", timeout=WAIT_MS)                # then the gap closes
        anims = await page.evaluate("() => window.__anims")
        assert sorted(a["key"] for a in anims if "|" in a["key"]) == ["register|next", "x1|now"]        # what was behind it (the stack that wraps into its row, the rows after it) …
        assert any(a["key"].startswith("stack__done") for a in anims)                                    # … and the count at the column's far end
        assert all(a["from"].startswith("translateY(") and float(a["from"][11:-3]) > 0 and a["ms"] == 250 for a in anims)       # … starts lower and steps up (≈ 0.25 s), no bounce
        await page.wait_for_function("() => document.querySelectorAll('.deck.is-leaving').length === 0", timeout=WAIT_MS)
        assert await _keys(page) == ["register|now", "x1|now", "register|next"]
        await page.wait_for_timeout(1000)
        assert {s["key"] for s in await page.evaluate(SEEN) if s["kind"] == "leave"} == {"cookie|now"}      # once: no other stack fades, and it does not fade again


@pytest.mark.asyncio
async def test_several_that_leave_in_one_refresh_move_together_the_first_three_fade_and_the_rest_simply_go(fake_repo, monkeypatch):
    for i in range(5):                                                                                   # five goals of their own, each a task of Backend's, in the first row
        SCENE["map"]["nodes"].append(node(f"x{i}", f"Extra {i}", "working", "implementation", tasks=[task("t", f"Waiting {i}", "waiting", BACKEND, 1)]))
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        for n in SCENE["map"]["nodes"][-5:]:
            n["tasks"][0]["state"] = "dropped"                                                           # five dropped at once
        stub.bump({})
        await page.wait_for_function("() => window.__seen.some((s) => s.kind === 'leave')", timeout=WAIT_MS * 2)
        await page.wait_for_function("() => document.querySelectorAll('.deck.is-leaving').length === 0", timeout=WAIT_MS)
        leave = [s for s in await page.evaluate(SEEN) if s["kind"] == "leave"]
        assert {s["key"] for s in leave} == {"x0|now", "x1|now", "x2|now"} and {s["sign"] for s in leave} == {"cross"}      # three fade (a drop shows ✗), the others are simply gone
        assert not [k for k in await _keys(page) if k.startswith("x")]


@pytest.mark.asyncio
async def test_a_stack_that_moves_slides_with_the_stacks_it_passes_and_nothing_else_moves(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        SCENE["map"]["nodes"].append(node("x0", "Extra 0", "working", "implementation", tasks=[task("t", "A task of a goal of its own", "waiting", BACKEND, 1)]))      # a stack comes into the first row …
        stub.bump({})
        await page.wait_for_function("() => window.__anims.length > 0", timeout=WAIT_MS * 2)
        await page.wait_for_timeout(500)
        assert await _keys(page) == ["register|now", "cookie|now", "x0|now", "register|next"]
        anims = await page.evaluate("() => window.__anims")
        moved = {a["key"]: float(a["from"][11:-3]) for a in anims}
        assert moved["register|next"] < 0                                                                # … and what lay below it slid down
        assert "register|now" not in moved and "cookie|now" not in moved and all(a["ms"] == 250 for a in anims)   # what lay above did not move: nothing else does
        seen = await page.evaluate(SEEN)
        assert {s["key"] for s in seen if s["kind"] == "rise"} == {"x0|now"} and not [s for s in seen if s["kind"] == "leave"]


@pytest.mark.asyncio
async def test_a_merge_lights_its_columns_count_once(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        assert " ".join((await page.locator(f"{BACKEND_COLUMN} .stack__done").inner_text()).split()) == "2 in dev"
        tasks_of(register())["k1"]["state"] = "merged"                                                   # its result in Review is merged
        SCENE["agents"]["roles"][1]["week"].update(finished=6, first_time=5, merged=5)                  # … and the week says one run more: 5/1 → 6/1
        stub.bump({})
        await page.wait_for_function("() => window.__seen.some((s) => s.kind === 'reward')", timeout=WAIT_MS * 2)
        await page.wait_for_timeout(300)
        rewards = [s for s in await page.evaluate(SEEN) if s["kind"] == "reward"]
        assert {(s["cls"].split()[0], s["text"].strip()) for s in rewards} == {("stack__done", "3 in dev")}        # its new value, highlighted (a member's runs are in its solo, not on the board: spec 53 §1.4)
        await page.wait_for_function("() => document.querySelectorAll('.is-reward').length === 0", timeout=3000)                                      # about 0.6 s, then it is plain
        assert " ".join((await page.locator(f"{BACKEND_COLUMN} .stack__done").inner_text()).split()) == "3 in dev"
        await page.wait_for_timeout(1200)
        times = [s["t"] for s in await page.evaluate(SEEN) if s["kind"] == "reward"]
        assert max(times) - min(times) < 400                                                              # once: lit together, not again


@pytest.mark.asyncio
async def test_under_reduced_motion_nothing_rises_fades_slides_or_is_lit(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await page.emulate_media(reduced_motion="reduce")
        await _ready(page)
        node_ = register()
        node_["tasks"].append(task("n1", "A new task", "waiting", BACKEND, 3))                           # one appears, one leaves, one moves, one merges
        tasks_of(node_)["k3"]["state"] = "merged"
        tasks_of(node_)["k2"]["state"] = "review"
        tasks_of(SCENE["map"]["nodes"][8])["q1"]["state"] = "merged"
        SCENE["agents"]["roles"][1]["week"].update(finished=6, first_time=5)
        stub.bump({})
        await page.locator(f'{BACKEND_COLUMN} .deck[data-key="register|later"]').wait_for(timeout=WAIT_MS * 2)           # the change is drawn …
        await page.wait_for_timeout(1000)
        assert await page.evaluate(SEEN) == [] and await page.evaluate("() => window.__anims") == []   # … with nothing moving
        assert await page.evaluate("() => document.getAnimations().length") == 0
        assert await page.locator(f'{BACKEND_COLUMN} .deck[data-key="cookie|now"]').count() == 0
        raised = await _pop(page, "Plan ready: Recovery codes")
        assert "is-pop" not in await raised.get_attribute("class")


@pytest.mark.asyncio
async def test_nothing_moves_for_what_changed_while_the_page_was_hidden(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        await page.evaluate("() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); }")
        node_ = register()
        node_["tasks"].append(task("n1", "A new task", "waiting", BACKEND, 3))
        tasks_of(SCENE["map"]["nodes"][8])["q1"]["state"] = "merged"
        stub.bump({})
        await page.locator(f'{BACKEND_COLUMN} .deck[data-key="register|later"]').wait_for(timeout=WAIT_MS * 2)
        await page.wait_for_timeout(800)
        assert await page.evaluate(SEEN) == [] and await page.evaluate("() => window.__anims") == []
        assert await page.locator(f'{BACKEND_COLUMN} .deck[data-key="cookie|now"]').count() == 0        # the change is simply there


@pytest.mark.asyncio
async def test_a_column_under_a_finger_or_the_focus_waits_and_settles_when_it_is_let_go(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        stack = page.locator(f'{BACKEND_COLUMN} .deck[data-key="register|now"]')
        await stack.dispatch_event("touchstart")                                                         # a finger is down in Backend's column
        tasks_of(SCENE["map"]["nodes"][8])["q1"]["state"] = "merged"
        stub.bump({})
        await page.wait_for_timeout(2600)                                                                # the Board was read again: the column waits, the gap stays
        assert "cookie|now" in await _keys(page) and not [s for s in await page.evaluate(SEEN) if s["kind"] in ("leave", "rise")]
        assert await page.locator('.stack[data-column="screens"] .deck').count() >= 1                    # another column is not held
        await page.locator(f'{BACKEND_COLUMN} .deck').first.dispatch_event("touchend")
        await page.wait_for_function("() => !document.querySelector('.stack[data-column=\"backend\"] .deck[data-key=\"cookie|now\"]')", timeout=WAIT_MS)
        assert "cookie|now" not in await _keys(page)                                                    # let go: it settles
        # the keyboard's focus holds a column too
        await page.keyboard.press("Tab")                                                                 # the keyboard is in use: the focus ring shows
        await page.locator(f'{BACKEND_COLUMN} .deck').last.focus()
        assert await page.evaluate("() => document.activeElement.matches(':focus-visible') && !!document.activeElement.closest('.stack[data-column=\"backend\"]')")
        tasks_of(register())["k5"]["state"] = "merged"
        stub.bump({})
        await page.wait_for_timeout(2600)
        assert "register|next" in await _keys(page)
        await page.evaluate("() => document.activeElement.blur()")
        await page.wait_for_function("() => !document.querySelector('.deck[data-key=\"register|next\"]')", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_the_bottom_row_does_not_shift_while_a_stop_is_popped(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        raised = await _pop(page, "Plan ready: Recovery codes")                                         # it came to the front first (spec 65 §4.4)
        before = await page.evaluate("() => [...document.querySelectorAll('.hand .hc')].map((b) => b.dataset.stop)")
        SCENE["needs"] = [n for n in SCENE["needs"] if n["kind"] != "proposal"]                        # a stop is answered elsewhere meanwhile
        stub.bump({})
        await page.wait_for_timeout(2600)
        assert await page.evaluate("() => [...document.querySelectorAll('.hand .hc')].map((b) => b.dataset.stop)") == before        # the fan stands still under the raised one
        await page.keyboard.press("Escape")
        await raised.wait_for(state="hidden", timeout=WAIT_MS)
        await page.wait_for_function("(n) => document.querySelectorAll('.hand .hc').length === n", arg=len(before) - 1, timeout=WAIT_MS)    # and shows what changed once it is put back
