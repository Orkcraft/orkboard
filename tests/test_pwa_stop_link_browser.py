"""Spec 58 part C, the phone (docs/specs/58-stop-and-its-task.md §1, §3, §4; decisions §71): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py. The raised card of a stop of
the party shown names what it is about under its banner, on one line cut with an ellipsis: *<goal> · <task> · <member>* for a failure, a Pick one and a result, *<goal>* for a plan, a question, a
proposal and a to-do; another party's stop keeps *<party> · <goal>*, Operations' says its party only. An answered stop is gone only in the render that rereads the Board (no optimistic removal),
and there its ghost fades in place in the fan (steps(4), 0.30 s) in the same frame its goal's card changes; none under reduced motion; a stop that is withdrawn leaves the same way."""
from __future__ import annotations

import pytest

from tests.test_pwa_arena_browser import ELF, SCENE, _scene, node, task  # noqa: F401
from tests.test_pwa_one_hand_browser import tech
from tests.test_pwa_shell_browser import WAIT_MS, Stub, _band, _called, _phone, _pop  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

SCREENS = {"slug": "screens", "name": "Screens"}
RECORD = """
(() => {
  window.__frame = 0; window.__leave = [];
  const tick = () => { window.__frame += 1; requestAnimationFrame(tick); };
  document.addEventListener("DOMContentLoaded", () => requestAnimationFrame(tick));
  const note = (e) => {
    if (!e.classList) return;
    if (e.classList.contains("hcg")) {
      const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
      window.__leave.push({ kind: "ghost", frame: window.__frame, key: e.dataset.ghost, place: e.dataset.place, tag: e.tagName, hidden: e.getAttribute("aria-hidden"), name: cs.animationName,
        duration: cs.animationDuration, timing: cs.animationTimingFunction, cx: r.left + r.width / 2, cy: r.top + r.height / 2, stops: document.querySelectorAll(".hand [data-stop]").length });
    }
    if (e.classList.contains("deck") && e.dataset.idea === "second" && e.dataset.state && e.dataset.state !== "stop") window.__leave.push({ kind: "card", frame: window.__frame, state: e.dataset.state });
  };
  document.addEventListener("DOMContentLoaded", () => new MutationObserver((ms) => { for (const m of ms) { for (const n of m.addedNodes) if (n.nodeType === 1) { note(n); n.querySelectorAll && n.querySelectorAll("*").forEach(note); } } })
    .observe(document.body, { childList: true, subtree: true }));
})();
"""
HOST = {"keeps": False}          # the host answers ok and has not changed the Board yet
LEAVE = "() => window.__leave"


@pytest.fixture(autouse=True)
def _answers(monkeypatch):
    """`ideas.answer` answers ok and the question is read: its stop leaves Needs you and its goal's card is no stop any more (the Board changes with the answer)."""
    HOST["keeps"] = False
    real = Stub.commands

    def commands(self):
        def answer(a):
            self.calls.append(("ideas.answer", {k: v for k, v in a.items() if k not in ("link", "device")}))
            if not HOST["keeps"]:
                withdraw("second")
            return self.bump({"ok": True})
        return {**real(self), "ideas.answer": answer}
    monkeypatch.setattr(Stub, "commands", commands)


def withdraw(slug):
    """The question of a goal is answered (or withdrawn) on the host: its row leaves Needs you and the goal is read again."""
    SCENE["needs"] = [n for n in SCENE["needs"] if n.get("idea") != slug]
    for n in SCENE["map"]["nodes"]:
        if n["slug"] == slug:
            n.update(state="reading", needs_you="", asked=[])


async def _line(raised):
    return " ".join((await raised.locator(".raised__goal").inner_text()).split())


@pytest.mark.asyncio
async def test_a_task_stop_names_its_goal_its_task_and_its_member_and_a_goal_stop_its_goal(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        raised = await _pop(page, "Failed: Secure cookie flags")
        assert await _line(raised) == "Session cookie flags · Secure cookie flags · Backend"                                    # a task's stop: <goal> · <task> · <member>
        await page.keyboard.press("Escape")
        raised = await _pop(page, "To look at: Challenge store")
        assert await _line(raised) == "WebAuthn register · Challenge store · Backend"                                          # a result: the same
        await page.keyboard.press("Escape")
        raised = await _pop(page, "To look at: Words on the screens")
        assert await _line(raised) == "Sign in with the passkey · Words on the screens · Words"                                # a check's result: its checker
        await page.keyboard.press("Escape")
        for name, goal in (("Plan ready: Recovery codes", "Recovery codes"), ("Asks you: Passkey on a second device", "Passkey on a second device"),
                           ("Proposed: Words of the sign-in page", "Words of the sign-in page")):
            raised = await _pop(page, name)
            assert await _line(raised) == goal                                                                                  # a goal's stop: <goal> alone
            assert await raised.locator(".raised__goal img, .raised__goal use").count() == 0                                   # (no party's mark: it is the party shown's)
            await page.keyboard.press("Escape")


@pytest.mark.asyncio
async def test_the_line_stands_under_the_banner_in_one_muted_line_cut_with_an_ellipsis(fake_repo, monkeypatch):
    SCENE["map"]["nodes"][[n["slug"] for n in SCENE["map"]["nodes"]].index("cookie")]["tasks"][0].update(short="Secure cookie flags on every sign-in response of the whole service", title="Secure cookie flags on every sign-in response of the whole service")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        raised = await _pop(page, "Failed: Secure cookie flags")
        order = await raised.evaluate("e => [...e.children].map((c) => c.classList.contains('banner') ? 'banner' : c.classList.contains('raised__goal') ? 'goal' : '')")
        assert order.index("goal") == order.index("banner") + 1                                                          # under the banner, where the party line stands
        goal = raised.locator(".raised__goal")
        css = await goal.locator(".raised__words").evaluate("e => { const s = getComputedStyle(e); return [s.whiteSpace, s.textOverflow, s.overflow, e.scrollWidth > e.clientWidth, e.getBoundingClientRect().height]; }")
        assert css[:3] == ["nowrap", "ellipsis", "hidden"] and css[3] and css[4] < 20                                          # one line, cut
        assert await goal.evaluate("e => getComputedStyle(e).color") == await page.evaluate("() => { const i = document.createElement('i'); i.style.color = 'var(--ork-ink-muted)'; document.body.append(i); const c = getComputedStyle(i).color; i.remove(); return c; }")


@pytest.mark.asyncio
async def test_a_pick_names_its_goal_its_task_and_its_member(fake_repo, monkeypatch):
    variants = [{"key": k, "name": k, "why": "", "url": "", "mime": "text/plain", "w": None, "h": None, "seconds": None, "text": f"Tagline {k}"} for k in ("a", "b")]
    SCENE["needs"].append({"kind": "pick", "slug": "logo", "idea": "logo", "goal": "passkey", "task": "l1", "title": "Draw the logo", "short": "Logo", "idea_title": "A mark for the sign-in button",
                           "priority": "high", "blocks": True, "by": {**SCREENS, "head": ELF}, "ask": "Which one?", "n": 2, "media": "text", "round": 1, "at": "2026-10-21T10:00:00", "variants": variants})
    SCENE["map"]["nodes"].append(node("logo", "A mark for the sign-in button", "working", "implementation", tasks=[task("l1", "Draw the logo", "picking", SCREENS, 1)]))
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        raised = await _pop(page, "Pick one: Draw the logo")
        assert await _line(raised) == "A mark for the sign-in button · Draw the logo · Screens"


@pytest.mark.asyncio
async def test_another_partys_stop_keeps_its_party_and_goal_and_operations_says_its_party_only(fake_repo, monkeypatch):
    tech()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        raised = await _pop(page, "Asks you: Log format")
        assert await _line(raised) == "Tech · Log format" and await raised.locator(".raised__goal img").count() == 1             # <party> · <goal>, not the task's line
        await page.keyboard.press("Escape")
        raised = await _pop(page, "Failed: Fix the build")
        assert await _line(raised) == "Tech · Broken build"                                                                     # (as spec 54 built it)
        await page.keyboard.press("Escape")
        raised = await _pop(page, "At your check: New Jira task")
        assert await _line(raised) == "Operations"
        await page.keyboard.press("Escape")
        raised = await _pop(page, "A to-do: Reference picture")
        assert await _line(raised) == "Tech · Reference art"


@pytest.mark.asyncio
async def test_a_to_do_of_the_party_shown_names_its_goal(fake_repo, monkeypatch):
    SCENE["needs"].append({"kind": "todo", "idea": "recovery", "goal": "passkey", "priority": "normal", "blocks": True, "at": "2026-10-19T09:00:00", "title": "The API key", "text": "The API key",
                           "todo": {"id": "t3", "title": "The API key", "kind": "secret", "why": "The plan needs it", "choices": None, "steps": [], "accept": [], "done": False}})
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        raised = await _pop(page, "A to-do: The API key")
        assert await _line(raised) == "Recovery codes"


@pytest.mark.asyncio
async def test_an_answered_stops_ghost_fades_in_place_in_the_fan_in_the_frame_its_goals_card_changes(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _band(page, "lead")                                                                                               # Planning is shown: the goal's card is on the field
        await page.locator('.hc[data-kind="asks"]').wait_for(timeout=WAIT_MS)
        before = await page.evaluate("() => [...document.querySelectorAll('.hand .hc')].map((b) => [b.dataset.stop, b.dataset.place])")
        raised = await _pop(page, "Asks you: Passkey on a second device")                                                          # it comes to the front first (spec 67 §4.4): the ghost lies where it stood then
        spot = await page.locator('.hc[data-kind="asks"]').evaluate("e => { const r = e.getBoundingClientRect(); return { cx: r.left + r.width / 2, cy: r.top + r.height / 2, place: e.dataset.place }; }")
        await raised.locator('[data-choice="1"]').click()
        assert await _called(stub, "ideas.answer", {"slug": "second", "answers": ["Only the lost phone’s passkey"]})
        await page.wait_for_function("() => window.__leave.some((x) => x.kind === 'ghost')", timeout=WAIT_MS * 2)
        await page.wait_for_function("() => window.__leave.some((x) => x.kind === 'card')", timeout=WAIT_MS * 2)
        rec = await page.evaluate(LEAVE)
        ghost = next(x for x in rec if x["kind"] == "ghost")
        card = next(x for x in rec if x["kind"] == "card")
        assert ghost["frame"] == card["frame"]                                                                                  # one change: the stop leaves in the frame its goal's card changes
        assert ghost["key"] == "asks:second:" and ghost["place"] == spot["place"] and ghost["tag"] == "SPAN" and ghost["hidden"] == "true"       # where it lay, no stop of the page
        assert abs(ghost["cx"] - spot["cx"]) <= 1.5 and abs(ghost["cy"] - spot["cy"]) <= 1.5                                    # … in place
        assert (ghost["name"], ghost["duration"], ghost["timing"]) == ("leave", "0.3s", "steps(4)")                              # opacity 1 → 0, steps(4), 0.30 s
        assert ghost["stops"] == len(before) - 1                                                                                # the stop itself is not in the page any more
        await page.wait_for_function("() => document.querySelectorAll('.hand .hcg').length === 0", timeout=WAIT_MS)       # then the hand closes the gap
        after = await page.evaluate("() => [...document.querySelectorAll('.hand .hc')].map((b) => [b.dataset.stop, b.dataset.place])")
        assert len(after) == len(before) - 1 and "asks:second:" not in [k for k, _ in after]
        assert sorted(int(p) for _, p in after) == list(range(len(after)))
        assert len([x for x in await page.evaluate(LEAVE) if x["kind"] == "ghost"]) == 1                                         # once


@pytest.mark.asyncio
async def test_nothing_is_removed_before_the_board_is_read_again(fake_repo, monkeypatch):
    HOST["keeps"] = True
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await page.locator('.hc[data-kind="asks"]').wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(2300)
        raised = await _pop(page, "Asks you: Passkey on a second device")
        await raised.locator('[data-choice="1"]').click()
        assert await _called(stub, "ideas.answer")
        await raised.wait_for(state="hidden", timeout=WAIT_MS)                                                                   # laid back at the press
        await page.wait_for_timeout(1200)                                                                                       # the Board was read again and still holds the stop
        assert await page.locator('.hc[data-kind="asks"]').is_visible() and await page.locator(".hand .hcg").count() == 0       # no optimistic removal: it lies in the fan, whole
        assert [x for x in await page.evaluate(LEAVE) if x["kind"] == "ghost"] == []
        withdraw("second")                                                                                                      # the host changes the Board: the next read
        stub.bump({})
        await page.wait_for_function("() => window.__leave.some((x) => x.kind === 'ghost')", timeout=WAIT_MS * 2)


@pytest.mark.asyncio
async def test_a_stop_withdrawn_elsewhere_leaves_the_same_way(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await page.locator('.hc[data-kind="asks"]').wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(2300)
        withdraw("second")
        stub.bump({})
        await page.wait_for_function("() => window.__leave.some((x) => x.kind === 'ghost')", timeout=WAIT_MS * 2)
        ghost = next(x for x in await page.evaluate(LEAVE) if x["kind"] == "ghost")
        assert ghost["key"] == "asks:second:" and ghost["duration"] == "0.3s"
        await page.wait_for_function("() => document.querySelectorAll('.hand .hcg').length === 0", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_under_reduced_motion_the_answered_stop_is_simply_gone(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await page.locator('.hc[data-kind="asks"]').wait_for(timeout=WAIT_MS)
        await page.emulate_media(reduced_motion="reduce")
        raised = await _pop(page, "Asks you: Passkey on a second device")
        await raised.locator('[data-choice="1"]').click()
        assert await _called(stub, "ideas.answer")
        await page.wait_for_function("() => !document.querySelector('.hc[data-kind=\"asks\"]')", timeout=WAIT_MS * 2)
        await page.wait_for_timeout(600)
        assert [x for x in await page.evaluate(LEAVE) if x["kind"] == "ghost"] == [] and await page.locator(".hand .hcg").count() == 0


@pytest.mark.asyncio
async def test_several_that_leave_at_once_fade_three_and_the_rest_simply_go(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(2300)
        count = await page.locator(".hand .hc").count()
        SCENE["needs"] = []                                                                                                     # every row of Needs you goes (a plan, a question, a failure, a proposal) …
        SCENE["results"] = []
        SCENE["map"]["nodes"][[n["slug"] for n in SCENE["map"]["nodes"]].index("cookie")]["tasks"][0]["state"] = "ready"
        stub.bump({})
        await page.wait_for_function("() => window.__leave.some((x) => x.kind === 'ghost')", timeout=WAIT_MS * 2)
        await page.wait_for_function("() => document.querySelectorAll('.hand .hc').length === 0", timeout=WAIT_MS * 2)
        assert count > 3 and len([x for x in await page.evaluate(LEAVE) if x["kind"] == "ghost"]) == 3                           # … three fade, the rest are simply gone
