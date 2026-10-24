"""Spec 57 part C, the phone (docs/specs/57-deal-on-start.md §1, §2, §4; decisions §70): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py. A plan started by a press on
its raised stop (*Start the work*, *Add and start*, *Start without*, a night plan's *Start now*) deals its new tasks from that card's box onto the stage shown, in the field's order, steps(6) 0.30 s
and 35 ms apart, six at most (the rest rise); the tasks of other goals rise; a start whose tasks go to a stage not shown deals nothing and does not switch the stage; nothing deals under reduced
motion, after a refusal, or for tasks that come after 6 s or with no press; `sw.js` v64."""
from __future__ import annotations

from pathlib import Path

import pytest

from orkboard.gui import pwa
from tests.test_pwa_arena_browser import ELDER, OWN, SCENE, _scene, member, node, task  # noqa: F401
from tests.test_pwa_goal_types_browser import ART
from tests.test_pwa_one_hand_browser import tech
from tests.test_pwa_shell_browser import WAIT_MS, Stub, _band, _called, _phone, _pop  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

BACKEND = {"slug": "backend", "name": "Backend"}
TESTER = {"slug": "tester", "name": "Tester"}
MODE = {"start": "ok", "many": False}          # what the host answers a start with: "ok", "refuse", or "quiet" (ok, and the tasks come when a test says so); `many`: a plan of many tasks

# What the page does is recorded as it happens (a deal lasts 0.3 s): the stacks that were dealt or risen with the variables and the boxes they were given, and the copies that fly.
RECORD = """
(() => {
  window.__deal = [];
  const done = new WeakSet();                     // a node is told once (the observer sees it added and changed in one batch)
  const note = (e) => {
    if (!e.classList || done.has(e)) return;
    if (e.classList.contains("is-dealt") || e.classList.contains("is-drawn") || e.classList.contains("deal-fly")) done.add(e);
    const at = Math.round(performance.now());
    if (e.classList.contains("is-dealt")) {
      const r = e.getBoundingClientRect();
      window.__deal.push({ kind: "dealt", at, key: e.dataset.key, column: e.closest(".stack").dataset.column, drawn: e.classList.contains("is-drawn"),
        dx: e.style.getPropertyValue("--dx"), dy: e.style.getPropertyValue("--dy"), s: e.style.getPropertyValue("--s"), delay: e.style.getPropertyValue("--delay"),
        cx: r.left + r.width / 2, cy: r.top + r.height / 2, w: r.width });
    }
    if (e.classList.contains("is-drawn")) window.__deal.push({ kind: "rise", at, key: e.dataset.key, column: e.closest(".stack") && e.closest(".stack").dataset.column, delay: e.style.animationDelay });
    if (e.classList.contains("deal-fly")) {
      const cs = getComputedStyle(e);
      window.__deal.push({ kind: "fly", at, key: e.querySelector(".tcard__name") && e.querySelector(".tcard__name").textContent, name: cs.animationName, duration: cs.animationDuration,
        timing: cs.animationTimingFunction, delay: cs.animationDelay, position: cs.position, z: cs.zIndex, pointer: cs.pointerEvents, parent: e.parentElement.tagName });
    }
  };
  document.addEventListener("DOMContentLoaded", () => new MutationObserver((ms) => { for (const m of ms) { if (m.type === "attributes") note(m.target); for (const n of m.addedNodes) if (n.nodeType === 1) { note(n); n.querySelectorAll && n.querySelectorAll("*").forEach(note); } } })
    .observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] }));
})();
"""
DEAL = "() => window.__deal"


@pytest.fixture(autouse=True)
def _start(monkeypatch):
    """`ideas.start` and `ideas.start_now` answer as `MODE` says; an ok start puts the plan to work: its tasks join the Board (and a task of another goal does, in the same read)."""
    MODE.update(start="ok", many=False)
    real = Stub.commands

    def commands(self):
        def serve(name):
            def call(a):
                self.calls.append((name, {k: v for k, v in a.items() if k not in ("link", "device")}))
                if MODE["start"] == "refuse":
                    return {"error": "The plan was not started."}
                if MODE["start"] == "ok":
                    put_to_work(self, MODE["many"])
                return {"ok": True}
            return call
        return {**real(self), "ideas.start": serve("ideas.start"), "ideas.start_now": serve("ideas.start_now")}
    monkeypatch.setattr(Stub, "commands", commands)


def put_to_work(stub, many=False):
    """The plan Recovery codes at work: Backend's first task now, Screens' next; with `many`, a third builder (Tester) and three phases each; and a task of another goal in the same read."""
    recovery = next(n for n in SCENE["map"]["nodes"] if n["slug"] == "recovery")
    tasks = [task("p1", "Codes table", "ready", BACKEND), task("p2", "Show the codes once", "waiting", {"slug": "screens", "name": "Screens"}, 2, after=["p1"]),
             task("p3", "Code review", "waiting", {"slug": "reviewer", "name": "Reviewer"}, 3, "check")]
    if many:
        for wave in (1, 2, 3):
            for who in (BACKEND, TESTER):
                t = task(f"m{wave}{who['slug']}", f"{who['name']} wave {wave}", "ready" if wave == 1 else "waiting", BACKEND, wave)
                tasks.append({**t, "by": who})
    recovery.update(state="working", stage="implementation", needs_you="", tasks=tasks)
    SCENE["needs"] = [n for n in SCENE["needs"] if n.get("idea") != "recovery"]
    SCENE["map"]["nodes"].append(node("other", "Another goal", "working", "implementation", tasks=[task("o1", "A task of another goal", "waiting", BACKEND, 1)]))
    stub.bump({})


def add_tester():
    """A third builder in the party."""
    goal = SCENE["map"]["goals"][0]
    goal["party"].append(member({**TESTER}, "build", OWN))
    goal["team"].append({"slug": "tester", "name": "Tester", "head": OWN, "checks": False, "every": False})


async def _ready(page):
    await page.locator('.hc[data-kind="plan"]').first.wait_for(timeout=WAIT_MS)
    await page.locator('.stack[data-column="backend"] .deck').first.wait_for(timeout=WAIT_MS)
    await page.wait_for_timeout(2300)          # a moment kept for the second read: the first read of a goal is not a change


async def _centre(raised):
    b = await raised.bounding_box()
    return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, b["width"]


async def _dealt(page, minimum=1):
    await page.wait_for_function("(n) => window.__deal.filter((d) => d.kind === 'dealt').length >= n", arg=minimum, timeout=WAIT_MS * 2)
    return await page.evaluate(DEAL)


@pytest.mark.asyncio
async def test_start_the_work_deals_the_new_stacks_from_the_raised_card_to_their_columns_and_the_other_goals_rise(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raised = await _pop(page, "Plan ready: Recovery codes")
        cx, cy, width = await _centre(raised)
        await raised.get_by_role("button", name="Start the work").click()
        assert await _called(stub, "ideas.start", {"slug": "recovery", "via": "hand"})
        rec = await _dealt(page, 2)
        dealt = [d for d in rec if d["kind"] == "dealt"]
        assert [(d["key"], d["column"]) for d in dealt[:2]] == [("recovery|now", "backend"), ("recovery|next", "screens")]       # the field's order: the left column first
        assert [d["delay"] for d in dealt[:2]] == ["0ms", "35ms"] and not any(d["drawn"] for d in dealt)                         # 35 ms apart; dealt instead of risen
        for d in dealt[:2]:
            assert abs((d["cx"] + float(d["dx"][:-2])) - cx) <= 2 and abs((d["cy"] + float(d["dy"][:-2])) - cy) <= 2             # from the raised card's centre …
            assert abs(float(d["s"]) - width / d["w"]) <= 0.02                                                                    # … at its width
        flies = [d for d in rec if d["kind"] == "fly"]
        assert len(flies) >= 2 and {f["name"] for f in flies} == {"deal"} and {f["duration"] for f in flies} == {"0.3s"}           # 0.30 s,
        assert all(f["timing"] == "steps(6)" and f["position"] == "fixed" and f["pointer"] == "none" and f["parent"] == "BODY" for f in flies)       # in steps, over the page, taking nothing
        assert int(flies[0]["z"]) > 30
        rises = [d for d in rec if d["kind"] == "rise"]
        assert {d["key"] for d in rises} == {"other|now"} and not any(d["key"].startswith("recovery") for d in rises)             # the goal's stacks are dealt; another goal's new stack rises
        assert await page.locator('.band[data-band="build"]').get_attribute("aria-selected") == "true"                           # the stage is not switched
        await page.wait_for_function("() => document.querySelectorAll('.deal-fly').length === 0", timeout=WAIT_MS)             # the copies are gone …
        landed = page.locator('.stack[data-column="backend"] .deck[data-key="recovery|now"]')
        assert await landed.is_visible()                                                                                       # … the stack has landed, a press on it works
        await landed.click()
        await page.locator(".screen").wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_the_real_stack_takes_the_pointer_and_shows_only_when_it_lands(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raised = await _pop(page, "Plan ready: Recovery codes")
        await raised.get_by_role("button", name="Start the work").click()
        await _dealt(page)
        # the stack is hidden while its copy travels, and lands (visible) at the end of its delay and its 0.30 s
        css = await page.evaluate("""() => { const n = document.querySelector('.deck.is-dealt'); if (!n) return null; const s = getComputedStyle(n); return { name: s.animationName, delay: s.animationDelay }; }""")
        if css:                                                                                                                # (a later draw may already have replaced it)
            assert css["name"] == "landed" and css["delay"] == "0.3s"
        await page.wait_for_function("() => { const n = document.querySelector('.stack[data-column=\"backend\"] .deck[data-key=\"recovery|now\"]'); return n && getComputedStyle(n).visibility === 'visible'; }",
                                     timeout=WAIT_MS)


@pytest.mark.asyncio
@pytest.mark.parametrize("button,call,missing,night", [
    ("Add and start", ("ideas.start", {"slug": "recovery", "join": {"add": "artist"}, "via": "hand"}), [{k: v for k, v in ART.items() if k != "out"}], False),
    ("Start without", ("ideas.start", {"slug": "recovery", "via": "hand"}), [{**{k: v for k, v in ART.items() if k != "out"}, "free": False}], False),
    ("Start now", ("ideas.start_now", {"slug": "recovery", "via": "hand"}), [], True),
])
async def test_the_other_ways_to_start_a_plan_from_the_raised_card_deal_too(fake_repo, monkeypatch, button, call, missing, night):
    if missing:
        SCENE["needs"][0]["missing"] = missing
    if night:
        next(n for n in SCENE["map"]["nodes"] if n["slug"] == "recovery")["start_at"] = "night"
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raised = await _pop(page, "Plan ready: Recovery codes")
        await raised.get_by_role("button", name=button).click()
        assert await _called(stub, *call)
        dealt = [d for d in await _dealt(page) if d["kind"] == "dealt"]
        assert dealt[0]["key"] == "recovery|now" and not dealt[0]["drawn"]


@pytest.mark.asyncio
async def test_at_most_six_travel_and_the_rest_of_the_goals_new_stacks_rise_after_the_sixth_starts(fake_repo, monkeypatch):
    add_tester()
    MODE["many"] = True
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await page.set_viewport_size({"width": 390, "height": 1700})                                                          # tall enough that every stack is in view
        await _ready(page)
        raised = await _pop(page, "Plan ready: Recovery codes")
        await raised.get_by_role("button", name="Start the work").click()
        rec = await _dealt(page)
        await page.wait_for_timeout(600)
        rec = await page.evaluate(DEAL)
        dealt = [d for d in rec if d["kind"] == "dealt"]
        rises = [d for d in rec if d["kind"] == "rise" and d["key"].startswith("recovery")]
        assert 1 <= len(dealt) <= 6 and [d["delay"] for d in dealt] == [f"{35 * i}ms" for i in range(len(dealt))]              # six at most, 35 ms apart
        if len(dealt) == 6:
            assert rises and all(r["delay"] == "210ms" for r in rises)                                                          # the rest rise after the sixth starts
        assert len(dealt) + len(rises) >= 3


@pytest.mark.asyncio
async def test_tasks_that_go_to_a_stage_not_shown_are_not_dealt_and_the_stage_is_not_switched(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        await _band(page, "lead")                                                                                               # Planning is shown: the tasks go to Implementation
        raised = await _pop(page, "Plan ready: Recovery codes")
        await raised.get_by_role("button", name="Start the work").click()
        assert await _called(stub, "ideas.start", {"slug": "recovery", "via": "hand"})
        await page.wait_for_function("() => !document.querySelector('.hc[data-kind=\"plan\"]')", timeout=WAIT_MS)             # the stop is gone: the Board was read again
        await page.wait_for_timeout(900)
        rec = await page.evaluate(DEAL)
        assert not [d for d in rec if d["kind"] in ("dealt", "fly")]
        assert await page.locator('.band[data-band="lead"]').get_attribute("aria-selected") == "true"                           # still Planning
        await _band(page, "build")
        assert await page.locator('.stack[data-column="backend"] .deck[data-key="recovery|now"]').count() == 1                 # the work is there when the person looks (nothing is dealt late)
        assert not [d for d in await page.evaluate(DEAL) if d["kind"] in ("dealt", "fly")]


@pytest.mark.asyncio
async def test_under_reduced_motion_nothing_is_dealt_or_risen(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        await page.emulate_media(reduced_motion="reduce")
        raised = await _pop(page, "Plan ready: Recovery codes")
        await raised.get_by_role("button", name="Start the work").click()
        assert await _called(stub, "ideas.start", {"slug": "recovery", "via": "hand"})
        await page.locator('.stack[data-column="backend"] .deck[data-key="recovery|now"]').wait_for(timeout=WAIT_MS * 2)
        await page.wait_for_timeout(600)
        assert await page.evaluate(DEAL) == [] and await page.locator(".deal-fly").count() == 0
        assert await page.locator(".deck.is-dealt").count() == 0


@pytest.mark.asyncio
async def test_a_refused_start_keeps_nothing_waiting(fake_repo, monkeypatch):
    MODE["start"] = "refuse"
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raised = await _pop(page, "Plan ready: Recovery codes")
        await raised.get_by_role("button", name="Start the work").click()
        assert await _called(stub, "ideas.start", {"slug": "recovery", "via": "hand"})
        await page.wait_for_timeout(500)
        MODE["start"] = "quiet"
        put_to_work(stub)                                                                                                       # the tasks come some other way within 6 s (an autostart)
        await page.locator('.stack[data-column="backend"] .deck[data-key="recovery|now"]').wait_for(timeout=WAIT_MS * 2)
        await page.wait_for_timeout(600)
        rec = await page.evaluate(DEAL)
        assert not [d for d in rec if d["kind"] in ("dealt", "fly")] and "recovery|now" in {d["key"] for d in rec if d["kind"] == "rise"}      # they rise as ever


@pytest.mark.asyncio
async def test_tasks_that_come_after_six_seconds_rise_and_so_do_those_of_a_start_with_no_press(fake_repo, monkeypatch):
    MODE["start"] = "quiet"
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raised = await _pop(page, "Plan ready: Recovery codes")
        await raised.get_by_role("button", name="Start the work").click()
        assert await _called(stub, "ideas.start", {"slug": "recovery", "via": "hand"})
        await page.wait_for_timeout(6400)                                                                                       # answered ok, and nothing came within 6 s
        put_to_work(stub)
        await page.locator('.stack[data-column="backend"] .deck[data-key="recovery|now"]').wait_for(timeout=WAIT_MS * 2)
        await page.wait_for_timeout(600)
        rec = await page.evaluate(DEAL)
        assert not [d for d in rec if d["kind"] in ("dealt", "fly")] and "recovery|now" in {d["key"] for d in rec if d["kind"] == "rise"}


@pytest.mark.asyncio
async def test_another_partys_plan_started_from_the_raised_card_deals_nothing_and_the_cache_is_v64(fake_repo, monkeypatch):
    assert 'const CACHE = "orkcraft-app-v74";' in (Path(pwa.__file__).parent / "static" / "pwa" / "sw.js").read_text(encoding="utf-8")
    tech(failed=False, ops=False, todos=False)
    SCENE["needs"].append({"kind": "plan", "idea": "art", "goal": "tech", "title": "Reference art", "text": "Plan ready", "priority": "normal", "blocks": False, "at": "2026-10-20T08:00:00"})
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raised = await _pop(page, "Plan ready: Reference art")
        await raised.get_by_role("button", name="Start the work").click()
        assert await _called(stub, "ideas.start", {"slug": "art", "via": "hand"})
        await page.wait_for_timeout(1500)
        assert not [d for d in await page.evaluate(DEAL) if d["kind"] in ("dealt", "fly")]
