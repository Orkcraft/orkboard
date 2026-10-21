"""The one window's motion on the desktop (docs/specs/49-one-window.md §11, docs/specs/50-parties-and-goals.md §4; Tests → B), in a real browser at
1 440 × 900 against the one window's stub host (tests/test_arena_desktop_browser.py): a task that appears rises, a merged one fades where it stands
with its check and the column settles, nothing moves under the pointer, a task that changes its place slides there, a merge lights the first number
once, and none of it plays under reduced motion. A spread's deal, New goal's turn and the filter's leave are tests/test_arena_decks_desktop_browser.py's."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import ArenaHost, _settle, arena, pip  # noqa: E402,F401  (fixture)

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
    assert pg.locator(".arena-member[data-agent=backend] .arena-num").first.inner_text() == "6/1"


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
