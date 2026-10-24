"""Spec 58, the desktop (docs/specs/58-stop-and-its-task.md §1, §2, §4; Tests → B): Chromium at 1 440 × 900 against the one window's stub host with a pick that waits
(tests/pick_desktop_host.py), a failed task, a plan, a question and a to-do of another party. While a stop is looked at (the pointer over it, the focus in it) the cards it is about
wear a ring (`is-linked`: 2 px of ink, 2 px outside, no transition) and no other; a stop of another party rings nothing; leaving the stop takes the ring away. An answered stop
fades where it stands (`is-leaving`, steps(4), 0.30 s) in the frame its task's card changes, and not at all under reduced motion."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.pick_desktop_host import PickHost, open_pick  # noqa: E402
from tests.test_one_hand_desktop_browser import row, todo  # noqa: E402
from tests.test_shell_browser import _sent, _stop  # noqa: E402

pytestmark = pytest.mark.browser

LINKED = ".arena-stk.is-linked"
FRAMES = """() => {
  window.__frames = [];
  let last = "";
  const sample = () => {
    const card = document.querySelector(".arena-task[data-key='logo/p1']"), live = document.querySelector(".arena-hc[data-kind=pick]:not(.is-leaving)");
    const ghost = document.querySelector(".arena-hc[data-kind=pick].is-leaving"), now = JSON.stringify([card?.dataset.state || "", !!live, !!ghost]);
    if (now !== last) { window.__frames.push(JSON.parse(now)); last = now; }
    requestAnimationFrame(sample);
  };
  sample();
}"""


class LinkHost(PickHost):
    """The pick of the passkey party, its failed task and plan and question (the one window's), and a to-do of another party."""

    def __init__(self):
        super().__init__()
        self.extra_needs = [row("todo", goal="pricing", idea="prices", title="Prices from the billing settings", text="Reference picture", at="2026-10-16T09:00:00",
                                todo=todo("t9", "Reference picture", "file", accept=["png"]))]


@pytest.fixture
def linking(gui):
    pg, host, errors = open_pick(gui, LinkHost())
    pg.locator(".arena-hc[data-kind=todo]").wait_for(timeout=WAIT_MS)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _linked(pg):
    """The keys of the cards (and the Planning goals) that wear the ring."""
    return pg.evaluate("""() => [...document.querySelectorAll('.arena-stk.is-linked')].map((s) => s.querySelector('.arena-task').dataset.key || s.querySelector('.arena-task').dataset.slug)""")


def _hover(pg, kind):
    """The pointer over a stop's top (the part that shows along the bottom): it rises."""
    pg.locator(f".arena-hc[data-kind={kind}] .arena-hc__top").hover()


def _wait_ring(pg, keys):
    pg.wait_for_function("(keys) => JSON.stringify([...document.querySelectorAll('.arena-stk.is-linked')].map((s) => s.querySelector('.arena-task').dataset.key || s.querySelector('.arena-task').dataset.slug)) === JSON.stringify(keys)",
                         arg=keys, timeout=WAIT_MS)


# -- the ring while a stop is looked at (§1, §2) --------------------------------------------------------------------------------------

def test_hovering_a_picks_stop_rings_its_task_and_no_other_and_leaving_takes_it_away(linking):
    pg, host = linking
    assert _linked(pg) == []                                                                             # nothing is ringed until a stop is looked at
    _hover(pg, "pick")
    _wait_ring(pg, ["logo/p1"])
    ring = pg.locator(LINKED)
    css = ring.evaluate("e => { const c = getComputedStyle(e); return [c.outlineStyle, c.outlineWidth, c.outlineOffset, c.outlineColor, c.transitionDuration, c.transitionProperty]; }")
    ink = pg.evaluate("() => { const i = document.createElement('i'); i.style.color = 'var(--ork-ink)'; document.body.append(i); const c = getComputedStyle(i).color; i.remove(); return c; }")
    assert css[:4] == ["solid", "2px", "2px", ink] and css[4] in ("0s", "0s, 0s")                       # 2 px of ink, 2 px outside, no transition
    assert ring.locator(".arena-task").get_attribute("class").count("is-linked") == 1                   # the card wears it too
    assert pg.locator(".arena-task.is-linked").count() == 1                                                # no other card
    assert ring.bounding_box()["x"] >= pg.locator(".arena-stack[data-agent=screens]").bounding_box()["x"] + 2      # its ring is not cut by the column
    pg.mouse.move(700, 300)                                                                              # the pointer leaves the stop
    pg.wait_for_function("() => !document.querySelector('.arena-stk.is-linked')", timeout=WAIT_MS)


def test_the_focus_by_keys_rings_the_same_and_leaving_takes_it_away(linking):
    pg, host = linking
    _stop(pg, "pick")                                                                                    # the focus in the stop raises it, as a hover does
    _wait_ring(pg, ["logo/p1"])
    pg.evaluate("document.activeElement.blur()")
    pg.wait_for_function("() => !document.querySelector('.arena-stk.is-linked')", timeout=WAIT_MS)
    _stop(pg, "failed")                                                                                  # a failed task's stop rings the task
    _wait_ring(pg, ["cookie/f1"])
    pg.keyboard.press("Tab")                                                                             # the focus moves on to the next button of the same stop: still looked at
    assert _linked(pg) == ["cookie/f1"]


def test_a_plans_and_a_questions_stop_ring_their_goals_planning_card_and_a_goal_at_work_rings_its_cards(linking):
    pg, host = linking
    _stop(pg, "plan")
    pg.wait_for_timeout(200)
    assert _linked(pg) == []                                                                             # Planning is not drawn on the field now: nothing to ring
    pg.evaluate("document.activeElement.blur()")
    pg.locator(".arena-lead .arena-member").click()                                                      # the leader's solo: its Planning goals
    pg.locator(".arena-solo[data-agent] .arena-task[data-slug=recovery]").wait_for(timeout=WAIT_MS)
    _stop(pg, "plan")
    _wait_ring(pg, ["recovery"])
    assert pg.locator(".arena-solo .arena-task.is-linked").count() == 1
    pg.evaluate("document.activeElement.blur()")
    _stop(pg, "asks")
    _wait_ring(pg, ["second"])
    pg.keyboard.press("Escape")


def test_a_stop_of_another_party_rings_nothing_and_says_nothing(linking):
    pg, host = linking
    other = pg.locator(".arena-hc[data-kind=todo]")
    assert "is-other" in other.get_attribute("class") and other.locator(".arena-hc__open").get_attribute("aria-describedby") is None
    _stop(pg, "todo")
    pg.wait_for_timeout(300)
    assert _linked(pg) == []                                                                             # not on this field
    pg.evaluate("document.activeElement.blur()")


def test_the_stop_says_its_task_is_ringed_in_its_description_not_drawn(linking):
    pg, host = linking
    open_ = pg.locator(".arena-hc[data-kind=pick] .arena-hc__open")
    said = open_.get_attribute("aria-describedby")
    assert said and pg.locator(f"#{said}").evaluate("e => e.hidden && e.textContent") == ", its task is ringed on the field"
    assert "ringed" not in pg.locator(".arena-hc[data-kind=pick]").inner_text()                           # nothing of it is drawn
    assert open_.get_attribute("aria-label") == "Pick one: Draw the mark"                                 # the label is as it was
    plan = pg.locator(".arena-hc[data-kind=plan] .arena-hc__open")
    assert pg.locator(f"#{plan.get_attribute('aria-describedby')}").evaluate("e => e.textContent") == ", its goal is ringed on the field"


# -- an answered stop leaves where it stands, in the frame its task changes (§4) ------------------------------------------------------

def test_an_answered_stop_fades_where_it_stands_in_the_frame_its_card_changes(linking):
    pg, host = linking
    stop = _stop(pg, "pick")
    stop.locator("[role=radio][data-variant=B]").click()
    pg.evaluate(FRAMES)
    stop.get_by_role("button", name="Take B").click()
    assert _sent(pg, host, ("ideas.pick", {"slug": "logo", "task": "p1", "key": "B", "via": "hand"}))
    ghost = pg.locator(".arena-hc[data-kind=pick].is-leaving")
    ghost.wait_for(state="attached", timeout=WAIT_MS)
    css = ghost.evaluate("e => { const c = getComputedStyle(e); return [c.animationName, c.animationDuration, c.animationTimingFunction, c.pointerEvents]; }")
    assert css == ["arena-leave", "0.3s", "steps(4)", "none"]                                         # opacity 1 → 0, steps(4), 0.30 s
    assert ghost.get_attribute("inert") is not None and ghost.get_attribute("aria-hidden") == "true" and "is-raised" in ghost.get_attribute("class")      # it fades up where it was raised
    ghost.wait_for(state="detached", timeout=WAIT_MS)                                                     # then the hand closes the gap
    assert pg.locator(".arena-hc[data-kind=pick]").count() == 0
    frames = pg.evaluate("window.__frames")
    assert ["running", False, True] in frames                                                             # the card changed with the ghost in the same frame …
    assert not any(state == "running" and live for state, live, _ in frames)                              # … never the changed card with the live stop
    assert not any(state == "picking" and ghost_ for state, _, ghost_ in frames)                          # … nor the ghost with the old card
    assert pg.locator(".arena-task[data-key='logo/p1']").get_attribute("data-state") == "running"
    assert _linked(pg) == []


def test_a_stop_that_is_withdrawn_leaves_the_same_way(linking):
    pg, host = linking
    pg.locator(".arena-hc[data-kind=proposal]").wait_for(timeout=WAIT_MS)
    pg.mouse.move(700, 300)
    host.waits = False                                                                                    # the pick is answered elsewhere
    host.bump({})
    pg.locator(".arena-hc[data-kind=pick].is-leaving").wait_for(state="attached", timeout=WAIT_MS)
    pg.locator(".arena-hc[data-kind=pick]").wait_for(state="detached", timeout=WAIT_MS)


def test_under_reduced_motion_the_ring_is_there_and_an_answered_stop_is_simply_gone(gui):
    pg, host, errors = open_pick(gui, LinkHost(), reduced=True)
    pg.locator(".arena-hc[data-kind=todo]").wait_for(timeout=WAIT_MS)
    _hover(pg, "pick")
    _wait_ring(pg, ["logo/p1"])                                                                           # a ring is no motion
    pg.mouse.move(700, 300)
    stop = _stop(pg, "pick")
    stop.locator("[role=radio][data-variant=B]").click()
    pg.evaluate("() => { window.__ghosts = 0; new MutationObserver(() => { if (document.querySelector('.arena-hc.is-leaving')) window.__ghosts += 1; }).observe(document.body, {subtree: true, childList: true, attributes: true}); }")
    stop.get_by_role("button", name="Take B").click()
    assert _sent(pg, host, ("ideas.pick", {"slug": "logo", "task": "p1", "key": "B", "via": "hand"}))
    pg.locator(".arena-hc[data-kind=pick]").wait_for(state="detached", timeout=WAIT_MS)
    assert pg.evaluate("window.__ghosts") == 0 and pg.locator(".arena-hc.is-leaving").count() == 0
    pg.close()
    assert not errors, "\n".join(errors)
