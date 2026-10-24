"""Spec 55, the desktop (docs/specs/55-type-top-right.md §1–§4): Chromium at 1 440 × 900 against the one window's stub host with a party whose goals are given a type (the way of
tests/test_goal_types_desktop_browser.py). A card's top row holds its goal's element left and its goal's type's sign right (14 × 14, the element's colour, faint while the element is drawn
dim); no card has a state sign in its top row, a failure keeps its danger edge and its danger foot; the goal line is the name alone; a Planning card says its type's name or *Planning*;
a goal with no type has no type node; no stop along the bottom wears a type; the goals' list wears the type's sign in its goal's colour."""
from __future__ import annotations

import re

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_goal_types_desktop_browser import typed  # noqa: E402,F401  (fixture)

pytestmark = pytest.mark.browser

BUG = {"id": "bug", "name": "Fix a bug", "sign": "bug"}
BG = "e => getComputedStyle(e).backgroundColor"
PROBE = "(v) => { const i = document.createElement('i'); i.style.backgroundColor = `var(${v})`; document.body.append(i); const c = getComputedStyle(i).backgroundColor; i.remove(); return c; }"


def _give(host):
    for slug in ("register", "cookie", "recovery", "magic"):                                    # at work, a failure, a plan, a goal not read yet
        host.node_of(slug)["type"] = BUG
    host.node_of("pagewords")["type"] = None
    host.bump({})


def test_a_task_card_has_its_goals_type_top_right_in_its_elements_colour_no_state_sign_and_a_failure_keeps_its_edge_and_foot(typed):
    pg, host = typed
    _give(host)
    card = pg.locator(".arena-task[data-key='register/k3']")
    card.locator(".arena-task__type").wait_for(timeout=WAIT_MS)
    elem, sign = card.locator(".arena-task__top .ork-elem").bounding_box(), card.locator(".arena-task__top .arena-task__type .ork-sign").bounding_box()
    assert (round(sign["width"]), round(sign["height"])) == (14, 14) and sign["x"] > elem["x"] + elem["width"] - 1 and abs(sign["y"] - elem["y"]) <= 3
    sig = card.locator(".arena-task__type .ork-sign")
    assert sig.evaluate(BG) == card.locator(".arena-task__top .ork-elem").evaluate(BG) == pg.evaluate(PROBE, "--ork-elem-meadow")        # its goal's colour
    assert card.locator(".arena-task__type").get_attribute("title") == "Fix a bug" and sig.get_attribute("aria-hidden") == "true"
    goal = card.locator(".arena-task__goal")
    assert goal.inner_text() == "WebAuthn register" and goal.locator(".ork-sign, .arena-task__type").count() == 0                       # the name alone
    assert pg.locator(".arena-task__mark").count() == 0                                                                                   # no state sign on any card
    failed = pg.locator(".arena-task[data-task=f1]")
    danger = pg.evaluate("() => { const e = document.createElement('i'); e.style.color = 'var(--ork-danger)'; document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; }")
    assert failed.evaluate("e => getComputedStyle(e).borderTopColor") == danger and failed.locator(".arena-task__foot").inner_text() == "failed"   # the danger edge and foot
    assert failed.locator(".arena-task__foot").evaluate("e => getComputedStyle(e).color") == danger
    assert failed.locator(".arena-task__type .ork-sign").evaluate(BG) == pg.evaluate(PROBE, "--ork-elem-dust")                           # still its goal's colour
    assert failed.locator(".arena-task__top .ork-sign").count() == 1                                                                      # the type's, nothing else
    assert pg.locator(".arena-hand .arena-task__type, .arena-hc .arena-task__type, .arena-stops .arena-task__type").count() == 0          # no stop along the bottom wears one
    assert pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_a_planning_card_says_its_type_or_planning_a_dim_goals_type_is_faint_and_a_goal_with_no_type_has_none(typed):
    pg, host = typed
    _give(host)
    pg.locator(".arena-lead .arena-member").click()                                                                                       # the leader's solo: its Planning goals
    lead = pg.locator(".arena-solo[data-agent=product-designer]")
    plan = lead.locator(".arena-task[data-slug=recovery]")
    plan.locator(".arena-task__top .arena-task__type .ork-sign.bug").wait_for(timeout=WAIT_MS)
    assert plan.locator(".arena-task__goal").inner_text() == "Fix a bug" and plan.locator(".arena-task__goal .ork-sign").count() == 0
    elem, sign = plan.locator(".arena-task__top .ork-elem").bounding_box(), plan.locator(".arena-task__type .ork-sign").bounding_box()
    assert sign["x"] > elem["x"] and (round(sign["width"]), round(sign["height"])) == (14, 14)
    assert plan.locator(".arena-task__type .ork-sign").evaluate(BG) == plan.locator(".arena-task__top .ork-elem").evaluate(BG) == pg.evaluate(PROBE, "--ork-elem-void")
    raw = lead.locator(".arena-task[data-slug=magic]")
    raw.locator(".arena-task__type").wait_for(timeout=WAIT_MS)
    assert raw.locator(".arena-task__top .ork-elem.dim").count() == 1                                                                     # not read yet: its element is dim …
    assert raw.locator(".arena-task__type .ork-sign").evaluate(BG) == pg.evaluate(PROBE, "--ork-ink-faint")                             # … and so is its type
    assert raw.locator(".arena-task__type .ork-sign").evaluate(BG) == raw.locator(".arena-task__top .ork-elem").evaluate(BG)
    none = lead.locator(".arena-task[data-slug=pagewords]")
    assert none.locator(".arena-task__goal").inner_text() == "Planning" and none.locator(".arena-task__type").count() == 0               # no type: the element alone
    assert lead.locator(".arena-task__mark").count() == 0
    pg.keyboard.press("Escape")


def test_a_spreads_cards_keep_the_type_top_right_and_the_goals_list_draws_the_type_in_its_goals_colour(typed):
    pg, host = typed
    _give(host)
    pg.locator(".arena-stack[data-agent=backend] .arena-phase[data-row=now] .arena-stk[data-goal=register] .arena-task").click()
    spread = pg.get_by_role("group", name=re.compile("tasks of Backend at this phase"))
    spread.wait_for(timeout=WAIT_MS)
    cards = spread.locator(".arena-spread__card")
    assert cards.count() == 2
    for c in cards.all():
        elem, sign = c.locator(".arena-task__top .ork-elem").bounding_box(), c.locator(".arena-task__top .arena-task__type .ork-sign").bounding_box()
        phase = c.locator(".arena-task__phase").bounding_box()
        assert elem["x"] < phase["x"] < sign["x"] and c.locator(".arena-task__mark").count() == 0 and c.locator(".arena-task__goal .ork-sign").count() == 0
    pg.keyboard.press("Escape")
    spread.wait_for(state="hidden", timeout=WAIT_MS)
    row = pg.locator(".arena-goal[data-slug=register]")
    row.locator(".arena-goal__type .ork-sign.bug").wait_for(timeout=WAIT_MS)
    assert row.locator(".arena-goal__type .ork-sign").evaluate(BG) == row.locator(".arena-goal__back .ork-elem").evaluate(BG) == pg.evaluate(PROBE, "--ork-elem-meadow")
    assert row.locator(".arena-goal__title").evaluate("e => e.firstElementChild.classList.contains('arena-goal__type')")                  # the list keeps its place: before the title
    assert pg.locator(".arena-goal[data-slug=pagewords] .arena-goal__type").count() == 0
