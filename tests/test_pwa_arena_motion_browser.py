"""Spec 49 part C, motion on the phone (docs/specs/49-one-window.md §11, §13 "C"; spec 50 §4): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py. Motion says what
changed and never decorates: a stack that appears rises into its column; one that leaves (a merge, a drop) fades where it stands with a one-frame orkUI sign and its column settles up toward
the member; one that moves slides, with the stacks it passes; a merge lights the member's first number and its column's count once. None under reduced motion, on the first read of a goal or
while the page is hidden; nothing moves under a finger or the focus; the bottom row does not shift while a stop is popped. The filter, the spread and New goal's card move in
tests/test_pwa_decks_browser.py. A member's face whose sign turns ✗ is struck and one whose sign turns ! calls (decisions §80), once, on the change only."""
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
    SCENE["map"]["nodes"].append(node("x1", "An extra goal", "working", "implementation", tasks=[task("x1t", "An extra task", "ready", BACKEND, 1)]))      # a third stack of the first row: with two tokens to a row (spec 67 §1.2) it lies in a row of its own, behind
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
        raised = await _pop(page, "Plan ready: Recovery codes")                                         # it came to the front first (spec 67 §4.4)
        before = await page.evaluate("() => [...document.querySelectorAll('.hand .hc')].map((b) => b.dataset.stop)")
        SCENE["needs"] = [n for n in SCENE["needs"] if n["kind"] != "proposal"]                        # a stop is answered elsewhere meanwhile
        stub.bump({})
        await page.wait_for_timeout(2600)
        assert await page.evaluate("() => [...document.querySelectorAll('.hand .hc')].map((b) => b.dataset.stop)") == before        # the fan stands still under the raised one
        await page.keyboard.press("Escape")
        await raised.wait_for(state="hidden", timeout=WAIT_MS)
        await page.wait_for_function("(n) => document.querySelectorAll('.hand .hc').length === n", arg=len(before) - 1, timeout=WAIT_MS)    # and shows what changed once it is put back


# -- a face struck, a face calling (decisions §80, spec 49 §11.7) -------------------------------------------------------------------

# The faces drawn with `is-struck` or `is-calling` (the draw makes a face anew: the class is on it as it is added), in the order drawn: [member, class].
FACES = """
(() => {
  window.__moments = [];
  const note = (e) => { if (e.classList && e.classList.contains("band__face")) for (const c of ["is-struck", "is-calling"]) if (e.classList.contains(c)) window.__moments.push([e.dataset.member, c]); };
  document.addEventListener("DOMContentLoaded", () => new MutationObserver((ms) => { for (const m of ms) for (const n of m.addedNodes) if (n.nodeType === 1) { note(n); n.querySelectorAll && n.querySelectorAll(".band__face").forEach(note); } })
    .observe(document.body, { childList: true, subtree: true }));
})();
"""
MOMENTS = "() => window.__moments.map((x) => x.join(' ')).sort()"


def screens_task():
    return tasks_of(register())["k3"]                                       # Screens' Register screen, running


def words_task():
    return tasks_of(SCENE["map"]["nodes"][7])["c2"]                         # Words' check, in review


def reviewer_task():
    return tasks_of(SCENE["map"]["nodes"][7])["c1"]                         # Reviewer's check, running (it asks a question too: its face wears ! already)


def backend_task():
    return tasks_of(SCENE["map"]["nodes"][8])["q1"]                         # Backend's failed task: its face wears ✗ already


async def _sign(page, slug):
    return await page.evaluate("(m) => document.querySelector(`.band__face[data-member=\"${m}\"] .band__sign`)?.dataset.sign ?? null", slug)


@pytest.mark.asyncio
async def test_a_face_whose_sign_turns_a_cross_is_struck_and_one_whose_sign_turns_an_alert_calls_once(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=FACES) as (stub, page):
        await _ready(page)
        assert await page.evaluate(MOMENTS) == [] and await page.locator(".band__face.is-struck, .band__face.is-calling").count() == 0       # the first read: the signs stand
        assert await _sign(page, "backend") == "cross" and await _sign(page, "reviewer") == "alert" and await _sign(page, "screens") is None
        screens_task()["state"] = "failed"                                                              # work → ✗
        stub.bump({})
        await page.wait_for_function("() => window.__moments.length > 0", timeout=WAIT_MS * 2)
        assert await page.evaluate(MOMENTS) == ["screens is-struck"] and await _sign(page, "screens") == "cross"
        words_task()["state"] = "picking"                                                               # nothing → !
        stub.bump({})
        await page.wait_for_function("() => window.__moments.some((x) => x[0] === 'words')", timeout=WAIT_MS * 2)
        assert await page.evaluate(MOMENTS) == ["screens is-struck", "words is-calling"] and await _sign(page, "words") == "alert"
        node_ = register()
        node_["tasks"].append(task("n1", "A new task", "waiting", BACKEND, 3))                           # the face is drawn again by another change: it does not play again
        stub.bump({})
        await page.locator(f'{BACKEND_COLUMN} .deck[data-key="register|later"]').wait_for(timeout=WAIT_MS * 2)
        await page.wait_for_timeout(500)
        assert await page.evaluate(MOMENTS) == ["screens is-struck", "words is-calling"]
        screens_task()["state"] = "running"                                                             # a sign that goes away does not play
        stub.bump({})
        await page.wait_for_function("() => !document.querySelector('.band__face[data-member=\"screens\"] .band__sign')", timeout=WAIT_MS * 2)
        assert await page.evaluate(MOMENTS) == ["screens is-struck", "words is-calling"]


@pytest.mark.asyncio
async def test_a_struck_face_is_lit_and_jolts_two_pixels_and_a_calling_one_drops_its_sign_and_hops_in_steps(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=FACES) as (stub, page):
        await _ready(page)
        given = await page.evaluate("""() => { const face = document.querySelector('.band__face[data-member="screens"]'), out = {}, of = (e) => { const c = getComputedStyle(e);
            return [c.animationName, c.animationDuration, c.animationTimingFunction]; };
          face.classList.add('is-struck'); out.struck = [of(face), of(face.querySelector('.ork-race__head'))];
          face.classList.replace('is-struck', 'is-calling'); out.calling = [of(face), of(face.querySelector('.band__sign') || face)];
          face.classList.remove('is-calling'); return out; }""")
        assert given["struck"] == [["jolt", "0.3s", "steps(1)"], ["struck", "0.3s", "steps(1)"]]        # lit once, jolting in steps, ≈ 0.3 s
        assert given["calling"][0] == ["hop", "0.25s", "steps(1)"]                                      # the face hops in steps, ≈ 0.25 s (its sign drops: the next face has one)
        css = await page.evaluate("[...document.styleSheets].flatMap((s) => [...s.cssRules]).filter((r) => ['jolt', 'hop', 'call'].includes(r.name)).map((r) => r.cssText).join(' ')")
        assert css.count("translateX(2px)") == 3 and css.count("translateX(-2px)") == 3 and "translateY(-2px)" in css and "translateX(3px)" not in css       # 2 px, three times; once


@pytest.mark.asyncio
async def test_at_most_three_faces_play_in_one_refresh_the_rest_wear_the_sign(fake_repo, monkeypatch):
    backend_task()["state"] = "held"                                                                    # Backend wears no sign at first: four faces change at once below
    async with _phone(fake_repo, monkeypatch, init=FACES) as (stub, page):
        await _ready(page)
        assert await _sign(page, "backend") is None
        backend_task()["state"] = "failed"
        screens_task()["state"] = "failed"
        reviewer_task()["state"] = "failed"                                                             # ! → ✗ is a change too
        words_task()["state"] = "picking"
        stub.bump({})
        await page.wait_for_function("() => window.__moments.length >= 3", timeout=WAIT_MS * 2)
        await page.wait_for_timeout(500)
        assert len(await page.evaluate(MOMENTS)) == 3
        assert [await _sign(page, m) for m in ("backend", "screens", "reviewer", "words")] == ["cross", "cross", "cross", "alert"]       # all four wear theirs


@pytest.mark.asyncio
async def test_a_face_under_the_pointer_is_not_struck_and_neither_is_a_change_while_the_page_is_hidden(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=FACES) as (stub, page):
        await _ready(page)
        await page.locator('.band__face[data-member="screens"]').hover()
        screens_task()["state"] = "failed"
        words_task()["state"] = "picking"
        stub.bump({})
        await page.wait_for_function("() => window.__moments.some((x) => x[0] === 'words')", timeout=WAIT_MS * 2)
        await page.wait_for_timeout(500)
        assert await page.evaluate(MOMENTS) == ["words is-calling"] and await _sign(page, "screens") == "cross"        # the sign stands, nothing plays on that face
        await page.mouse.move(5, 300)
        await page.evaluate("() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); }")
        reviewer_task()["state"] = "failed"
        stub.bump({})
        await page.wait_for_function("() => document.querySelector('.band__face[data-member=\"reviewer\"] .band__sign')?.dataset.sign === 'cross'", timeout=WAIT_MS * 2)
        await page.evaluate("() => { delete document.hidden; }")
        node_ = register()
        node_["tasks"].append(task("n1", "A new task", "waiting", BACKEND, 3))
        stub.bump({})
        await page.locator(f'{BACKEND_COLUMN} .deck[data-key="register|later"]').wait_for(timeout=WAIT_MS * 2)
        await page.wait_for_timeout(500)
        assert await page.evaluate(MOMENTS) == ["words is-calling"]                                     # what changed while hidden just stands


@pytest.mark.asyncio
async def test_under_reduced_motion_no_face_is_struck_and_none_calls(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=FACES) as (stub, page):
        await page.emulate_media(reduced_motion="reduce")
        await _ready(page)
        screens_task()["state"] = "failed"
        words_task()["state"] = "picking"
        stub.bump({})
        await page.wait_for_function("() => document.querySelector('.band__face[data-member=\"words\"] .band__sign')", timeout=WAIT_MS * 2)
        await page.wait_for_timeout(500)
        assert await page.evaluate(MOMENTS) == [] and await _sign(page, "screens") == "cross" and await _sign(page, "words") == "alert"        # the signs are there, nothing plays
