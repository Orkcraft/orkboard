"""The one window's motion on the desktop (docs/specs/49-one-window.md §11, docs/specs/50-parties-and-goals.md §4; Tests → B), in a real browser at
1 440 × 900 against the one window's stub host (tests/test_arena_desktop_browser.py): a task that appears rises, a merged one fades where it stands
with its check and the column settles, nothing moves under the pointer, a task that changes its place slides there, a merge lights the first number
once, a member whose sign turns ✗ is struck and one whose sign turns ! calls (decisions §80, §11.7), and none of it plays under reduced motion. A spread's deal, New goal's turn and the filter's leave are tests/test_arena_decks_desktop_browser.py's."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import ArenaHost, _settle, arena, pip  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import _open  # noqa: E402

pytestmark = pytest.mark.browser


# -- motion (§11): what changed, in steps, never on the first read, never under reduced motion ---------------------------------------

def test_a_task_that_appears_rises_a_merged_one_fades_with_its_check_and_the_column_settles(arena):
    pg, host = arena
    assert pg.locator(".is-drawn, .is-leaving").count() == 0                                                      # none on the first read
    host.nodes[0]["tasks"] = [*host.nodes[0]["tasks"], pip("k6", "Revoke a credential", "ready", wave=4, by="backend")]
    host.bump({})
    pg.locator(".arena-task[data-task=k6].is-drawn").wait_for(timeout=WAIT_MS)                                    # a new one rises in, in a row of its own (later)
    assert pg.locator(".arena-task[data-task=k6]").evaluate("e => getComputedStyle(e).animationName") == "arena-rise"
    _settle(pg)
    tasks = host.nodes[0]["tasks"]
    assert pg.locator(".arena-stk[data-goal=register] .arena-stk__n").first.inner_text() == "×2"                  # the register stack of Backend: k2 in front, k1 behind
    behind = pg.locator(".arena-task[data-task=k5]").bounding_box()["y"]                                          # the row behind the one that goes
    pg.locator(".arena-task[data-task=k5]").hover()                                                               # the pointer is in the column: the ghost stays to be looked at
    tasks[1]["state"] = "merged"                                                                                  # k2 merges
    host.bump({})
    leaving = pg.locator(".arena-task[data-task=k2].is-leaving")
    leaving.wait_for(timeout=WAIT_MS)
    assert leaving.get_attribute("data-sign") == "check" and leaving.evaluate("e => getComputedStyle(e).animationName") == "arena-leave"          # fades where it stands, with a check
    assert leaving.locator(".arena-task__flash .ork-sign.check").count() == 1                                    # the check is orkUI's sign
    pg.mouse.move(5, 5)
    pg.locator(".arena-task[data-task=k2]").wait_for(state="detached", timeout=WAIT_MS)                            # then the column settles
    _settle(pg)
    pg.wait_for_function("() => document.getAnimations().length === 0", timeout=WAIT_MS)
    assert pg.locator(".arena-stk[data-goal=register] .arena-stk__n").count() == 0 and pg.locator(".arena-task[data-task=k1]").count() == 1           # the stack is one card now: k1
    assert pg.locator(".arena-task[data-task=k5]").bounding_box()["y"] < behind                                   # and the row behind it stepped up toward the member
    assert "2 in dev" in pg.locator(".arena-stack[data-agent=backend] .arena-stack__done").inner_text()           # and the count of what merged goes up


def test_nothing_moves_under_the_pointer_a_column_waits_until_it_leaves(arena):
    pg, host = arena
    column = pg.locator(".arena-stack[data-agent=backend]")
    pg.locator(".arena-task[data-task=k5]").hover()                                                               # the pointer is over the column
    before = [t.get_attribute("data-task") for t in column.locator(".arena-task").all()]
    assert before == ["k2", "f1", "k5"]
    host.nodes[0]["tasks"][1]["state"] = "merged"
    host.bump({})
    pg.locator(".arena-task[data-task=k2].is-leaving").wait_for(timeout=WAIT_MS)
    pg.wait_for_timeout(900)                                                                                      # past the fade: the gap stays empty
    assert [t.get_attribute("data-task") for t in column.locator(".arena-task").all()] == before and pg.locator(".arena-task[data-task=k2]").count() == 1
    assert pg.locator(".arena-task[data-task=k2]").evaluate("e => getComputedStyle(e).opacity") == "0"
    pg.mouse.move(5, 5)                                                                                           # the pointer leaves: it settles
    pg.locator(".arena-task[data-task=k2]").wait_for(state="detached", timeout=WAIT_MS)
    assert [t.get_attribute("data-task") for t in column.locator(".arena-task").all()] == ["k1", "f1", "k5"]       # the stack's next card is the front now


def test_a_task_that_changes_its_place_slides_there_and_a_merge_lights_the_first_number_once(arena):
    pg, host = arena
    pg.evaluate("""() => { window.__anims = []; const orig = Element.prototype.animate;
      Element.prototype.animate = function (...a) { window.__anims.push([this.className, JSON.stringify(a[0]).slice(0, 120)]); return orig.apply(this, a); }; }""")
    for i in (0, 1, 2):                                                                                           # k1, k2 and k3 merge: the goal's next wave is its current one,
        host.nodes[0]["tasks"][i]["state"] = "merged"                                                             # so k5 moves up from the next row to the first
    host.bump({})
    pg.wait_for_function("() => window.__anims.some((a) => a[1].includes('translate'))", timeout=WAIT_MS)
    moved = pg.evaluate("window.__anims.filter((a) => a[1].includes('translate')).map((a) => a[0])")
    assert any("arena-task" in c for c in moved)
    assert pg.locator(".arena-stack[data-agent=backend] .arena-phase").first.locator(".arena-task[data-task=k5]").count() == 1
    host.week["backend"] = {**host.week["backend"], "finished": 6, "merged": 6, "first_time": 5}                    # a merge: 5/1 → 6/1
    host.bump({})
    pg.wait_for_function("() => window.__anims.some((a) => a[1].includes('background'))", timeout=WAIT_MS)
    pg.wait_for_function("() => document.querySelector('.arena-member[data-agent=backend] .arena-num')?.innerText === '6/1'", timeout=WAIT_MS)


def test_under_reduced_motion_none_of_it_plays(gui):
    server, browser = gui
    host = ArenaHost()
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    host.nodes[0]["tasks"] = [*host.nodes[0]["tasks"], pip("k6", "Revoke a credential", "ready", wave=4, by="backend")]
    host.bump({})
    pg.locator(".arena-task[data-task=k6]").wait_for(timeout=WAIT_MS)
    assert pg.locator(".is-drawn, .is-leaving").count() == 0
    host.nodes[0]["tasks"][1]["state"] = "merged"
    host.bump({})
    pg.locator(".arena-task[data-task=k2]").wait_for(state="detached", timeout=WAIT_MS)                            # it just goes
    assert pg.evaluate("document.getAnimations().filter((a) => a.animationName !== undefined).length") == 0
    hc = pg.locator(".arena-hc").first
    assert hc.evaluate("e => getComputedStyle(e).transitionDuration") in ("0s", "0s, 0s")                          # a stop rises with no motion
    pg.close()


# -- a member struck, a member calling (decisions §80, spec 49 §11.7) ------------------------------------------------------------

# The heads that were given `is-struck` or `is-calling`, as they were given (the class stays ≈ 0.35 s): [member, class].
RECORD = """
(() => {
  window.__moments = [];
  new MutationObserver((ms) => { for (const m of ms) { const t = m.target; if (!t.classList || !t.classList.contains("arena-tport")) continue;
    for (const c of ["is-struck", "is-calling"]) if (t.classList.contains(c)) window.__moments.push([t.closest("[data-agent]").dataset.agent, c]); } })
    .observe(document, { subtree: true, attributes: true, attributeFilter: ["class"] });
})();
"""
MOMENTS = "() => [...new Set(window.__moments.map((x) => x.join(' ')))].sort()"


def _party(gui, reduced=False):
    """The one window with the recorder in, its party read (the first read: nothing is struck, nothing calls)."""
    server, browser = gui
    host = ArenaHost()
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, **({"reduced_motion": "reduce"} if reduced else {}))
    pg.add_init_script(RECORD)
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    pg.locator(".arena-member[data-agent=words]").wait_for(timeout=WAIT_MS)
    return pg, host


def _turn(host, slug, state, why=""):
    member = next(m for m in host.party["passkey"] if m["slug"] == slug)
    member.update(state=state, why=why)
    host.bump({})


def _sign(pg, slug):
    return pg.locator(f".arena-member[data-agent={slug}] .arena-sign").get_attribute("data-sign")


def test_a_member_whose_sign_turns_a_cross_is_struck_and_one_whose_sign_turns_an_alert_calls_each_once(gui):
    pg, host = _party(gui)
    pg.wait_for_timeout(700)
    assert pg.evaluate(MOMENTS) == [] and pg.locator(".arena-tport.is-struck, .arena-tport.is-calling").count() == 0       # the first read: the signs stand (Backend's ✗ among them)
    assert _sign(pg, "backend") == "cross" and _sign(pg, "taskmaster") == "alert"
    _turn(host, "screens", "needs", "failed")                                                                              # work → ✗
    port = pg.locator(".arena-member[data-agent=screens] .arena-tport")
    port.evaluate("e => e")
    pg.wait_for_function("() => window.__moments.length > 0", timeout=WAIT_MS)
    assert _sign(pg, "screens") == "cross" and pg.evaluate(MOMENTS) == ["screens is-struck"]
    assert port.evaluate("e => getComputedStyle(e).animationName") in ("arena-jolt", "none")                               # the jolt (or already over)
    assert port.locator(".ork-race__head").evaluate("e => getComputedStyle(e).animationName") in ("arena-struck", "none")   # the head lit once
    pg.wait_for_function("() => !document.querySelector('.arena-tport.is-struck')", timeout=WAIT_MS)                       # it is over: the class is gone, the sign stays
    _turn(host, "words", "needs", "pick")                                                                                  # next → !
    pg.wait_for_function("() => window.__moments.some((x) => x[0] === 'words')", timeout=WAIT_MS)
    assert pg.evaluate(MOMENTS) == ["screens is-struck", "words is-calling"] and _sign(pg, "words") == "alert"
    assert pg.locator(".arena-member[data-agent=words] .arena-tport .arena-sign").evaluate("e => getComputedStyle(e).animationName") in ("arena-call", "none")
    pg.wait_for_function("() => !document.querySelector('.arena-tport.is-calling')", timeout=WAIT_MS)
    host.bump({})                                                                                                          # the same signs read again: nothing plays again
    pg.wait_for_timeout(500)
    assert pg.evaluate(MOMENTS) == ["screens is-struck", "words is-calling"]
    _turn(host, "screens", "work")                                                                                         # a sign that goes away, or turns ↻, does not play
    pg.wait_for_timeout(500)
    assert pg.evaluate(MOMENTS) == ["screens is-struck", "words is-calling"] and _sign(pg, "screens") == "work"
    pg.close()


def test_the_jolt_and_the_hop_move_two_pixels_in_steps_and_nothing_travels(gui):
    pg, host = _party(gui)
    rules = pg.evaluate("""() => { const all = [...document.styleSheets].flatMap((s) => [...s.cssRules]), by = (n) => all.find((r) => r.name === n).cssText;
      return { jolt: by("arena-jolt"), hop: by("arena-hop"), call: by("arena-call"), lit: by("arena-struck") }; }""")
    assert rules["jolt"].count("translateX(2px)") == 3 and rules["jolt"].count("translateX(-2px)") == 3 and "translateX(3px)" not in rules["jolt"]       # 2 px, three times
    assert "translateY(-2px)" in rules["hop"] and "translateY(-3px)" in rules["call"] and "var(--ork-ink)" in rules["lit"]                              # a hop of 2 px, the sign from above, the head lit with ink
    given = pg.evaluate("""() => { const port = document.querySelector('.arena-member[data-agent=screens] .arena-tport'), out = {}, of = (e) => { const c = getComputedStyle(e);
        return [c.animationName, c.animationDuration, c.animationTimingFunction]; };
      port.classList.add('is-struck'); out.struck = [of(port), of(port.querySelector('.ork-race__head'))];
      port.classList.replace('is-struck', 'is-calling'); out.calling = [of(port), of(port.querySelector('.arena-sign'))];
      port.classList.remove('is-calling'); return out; }""")
    assert given["struck"] == [["arena-jolt", "0.3s", "steps(1)"], ["arena-struck", "0.3s", "steps(1)"]]                                      # in steps, ≈ 0.3 s: lit once and jolting
    assert given["calling"] == [["arena-hop", "0.25s", "steps(1)"], ["arena-call", "0.25s", "steps(3)"]]                                    # in steps, ≈ 0.25 s: the head hops, the sign drops
    pg.close()


def test_at_most_three_heads_play_in_one_refresh_the_rest_simply_wear_the_sign(gui):
    pg, host = _party(gui)
    for slug, state, why in (("screens", "needs", "failed"), ("reviewer", "needs", "failed"), ("words", "needs", "pick")):
        next(m for m in host.party["passkey"] if m["slug"] == slug).update(state=state, why=why)
    next(m for m in host.party["passkey"] if m["slug"] == "taskmaster").update(state="needs", why="failed")                # four change at once: ! → ✗ is a change too
    host.bump({})
    pg.wait_for_function("() => window.__moments.length >= 3", timeout=WAIT_MS)
    pg.wait_for_timeout(500)
    assert len(pg.evaluate(MOMENTS)) == 3
    assert [_sign(pg, s) for s in ("taskmaster", "screens", "reviewer", "words")] == ["cross", "cross", "cross", "alert"]   # all four wear theirs
    pg.close()


def test_a_head_under_the_pointer_is_not_struck_and_neither_is_a_change_while_the_page_is_hidden(gui):
    pg, host = _party(gui)
    pg.locator(".arena-member[data-agent=screens]").hover()                                                                # the pointer is on Screens
    _turn(host, "screens", "needs", "failed")
    _turn(host, "words", "needs", "pick")
    pg.wait_for_function("() => window.__moments.some((x) => x[0] === 'words')", timeout=WAIT_MS)
    pg.wait_for_timeout(500)
    assert pg.evaluate(MOMENTS) == ["words is-calling"] and _sign(pg, "screens") == "cross"                                # the sign stands, nothing plays on that head
    pg.mouse.move(5, 5)
    pg.evaluate("() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); }")           # the page is hidden
    _turn(host, "reviewer", "needs", "failed")
    pg.wait_for_function("() => document.querySelector('.arena-member[data-agent=reviewer] .arena-sign')", timeout=WAIT_MS)
    pg.wait_for_timeout(300)                                                                                               # its effects run while it is hidden
    pg.evaluate("() => { delete document.hidden; }")
    host.bump({})
    pg.wait_for_timeout(500)
    assert pg.evaluate(MOMENTS) == ["words is-calling"] and _sign(pg, "reviewer") == "cross"                               # what changed while hidden just stands
    pg.close()


def test_under_reduced_motion_no_head_is_struck_and_none_calls(gui):
    pg, host = _party(gui, reduced=True)
    _turn(host, "screens", "needs", "failed")
    _turn(host, "words", "needs", "pick")
    pg.wait_for_function("() => document.querySelector('.arena-member[data-agent=words] .arena-sign')", timeout=WAIT_MS)
    pg.wait_for_timeout(500)
    assert pg.evaluate(MOMENTS) == [] and _sign(pg, "screens") == "cross" and _sign(pg, "words") == "alert"                # the signs are there, nothing plays
    assert pg.evaluate("document.getAnimations().length") == 0
    pg.close()
