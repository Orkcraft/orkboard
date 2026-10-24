"""Spec 43 D on the desktop (docs/specs/43-party-measured.md §4, Tests → D): Needs you's party row with *Take it out* and *Keep it*, never
counted; a checker's muted line (*its check: 6 goals, caught 2*) and the dialog's *Its check* line."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_36_browser import Stub36  # noqa: E402
from tests.test_shell_browser import _agents, _calls, _open, _sent, _show_goal, _stop  # noqa: E402

pytestmark = pytest.mark.browser

ROW = {"idea": "", "goal": "ship-sync", "kind": "party", "by": "reviewer", "title": "Take Reviewer out of Ship sync's party?",
       "text": "It found nothing in the last 8 goals; a check costs about $0.35.", "priority": "normal", "blocks": False, "at": "2026-10-20T03:00:00"}
HEAD = {"craft": "engineering", "race": "peon", "tier": "elder"}


@pytest.fixture
def shell(gui):
    host = Stub36()
    host.party_rows = [dict(ROW)]
    host.roles["reviewer"] = {"slug": "reviewer", "name": "Reviewer", "model": "elder", "max_parallel": 1, "instruction": "", "builtin": False, "head": HEAD}
    host.check_week = {"reviewer": {"checks": 6, "clean": 4, "caught": 2, "left": 1, "usd_per_check": None}}
    host.record = {"reviewer": {"days": 30, "finished": 14, "merged": 14, "first_time": 14, "usd_per_merged": None,
                                "check": {"checks": 14, "clean": 11, "caught": 3, "left": 1, "usd_per_check": 0.35}}}
    pg, host, errors = _open(gui, host=host)
    _show_goal(pg)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _needs(pg):
    pg.locator(".arena-hc").first.wait_for(timeout=WAIT_MS)
    return _stop(pg, "party")


def test_the_party_row_is_a_proposal_s_with_take_it_out_and_keep_it_and_is_never_counted(shell):
    pg, host = shell
    row = _needs(pg)
    assert "Take Reviewer out of Ship sync's party?" in row.inner_text() and "It found nothing in the last 8 goals; a check costs about $0.35." in row.inner_text()
    assert "proposed" in row.inner_text().lower()
    assert row.get_by_role("button", name="Take it out: Take Reviewer out of Ship sync's party?").is_visible()
    rows = pg.locator(".arena-hc").evaluate_all("els => els.map(e => e.dataset.kind)")
    assert rows[-1] == "party" or rows[-2:] == ["proposal", "party"]                                    # last, with the proposals
    row.get_by_role("button", name="Keep it: Take Reviewer out of Ship sync's party?").click()
    why = row.get_by_label("Why not: Take Reviewer out of Ship sync's party?")
    assert why.get_attribute("placeholder") == "Why not? (optional, one line)"
    why.fill("the public page needs it")
    row.get_by_role("button", name="Keep: Take Reviewer out of Ship sync's party?").click()
    assert _sent(pg, host, ("ideas.party_answer", {"goal": "ship-sync", "take": False, "reason": "the public page needs it"}))
    pg.wait_for_function("() => document.querySelectorAll('.arena-hc[data-kind=party]').length === 0", timeout=WAIT_MS)


def test_take_it_out_answers_at_once_and_a_keep_with_no_reason_sends_none(shell):
    pg, host = shell
    _needs(pg).get_by_role("button", name="Take it out: Take Reviewer out of Ship sync's party?").click()
    assert _sent(pg, host, ("ideas.party_answer", {"goal": "ship-sync", "take": True}))
    pg.mouse.move(5, 5)                                                                                 # nothing shifts under the pointer: it is away
    host.party_rows = [dict(ROW)]
    host.bump({})
    pg.locator(".arena-hc[data-kind=party]").wait_for(timeout=WAIT_MS)
    _stop(pg, "party").get_by_role("button", name="Keep it: Take Reviewer out of Ship sync's party?").click()
    pg.get_by_role("button", name="Keep: Take Reviewer out of Ship sync's party?").click()
    assert _calls(pg, host, "ideas.party_answer", 2)[-1] == {"goal": "ship-sync", "take": False}


def test_the_row_is_one_of_the_party_s_stops_along_the_bottom(shell):
    pg, host = shell
    host.party_rows = [dict(ROW)]
    host.bump({})
    pg.locator(".arena-hc[data-kind=party]").wait_for(timeout=WAIT_MS)
    assert pg.locator(".arena-hand .arena-hc[data-kind=party]").count() == 1                             # the stops along the bottom (their count), the row among them
    assert pg.locator('.arena-phead[aria-current=true]').get_attribute("data-goal") == "ship-sync" and pg.locator('.arena-phead[aria-current=true] .arena-phead__stop').count() == 0      # the shown party's stops are not counted on its heading (spec 52 §4.5)


def test_a_checker_s_muted_line_ends_with_its_check_and_its_dialog_says_it_over_30_days(shell):
    pg, host = shell
    _agents(pg)
    week = pg.locator(".shell-role[data-slug='reviewer'] .shell-role__week")
    week.wait_for(timeout=WAIT_MS)
    assert week.inner_text() == "its check: 6 goals, caught 2"
    host.check_week = {"reviewer": {"checks": 1, "clean": 1, "caught": 0, "left": 0, "usd_per_check": None}}
    host.bump({})
    pg.wait_for_function("() => document.querySelector(\".shell-role[data-slug='reviewer'] .shell-role__week\")?.innerText === 'its check: 1 goal, caught 0'", timeout=WAIT_MS)
    host.check_week = {}
    host.bump({})
    pg.wait_for_function("() => !document.querySelector(\".shell-role[data-slug='reviewer'] .shell-role__week\")", timeout=WAIT_MS)
    pg.get_by_role("button", name="Edit Reviewer").click()
    dlg = pg.get_by_role("dialog", name="Edit agent")
    check = dlg.get_by_label("Its check", exact=True)
    assert " ".join(check.text_content().split()) == "Its check, the last 30 days: 14 goals: 11 clean, caught 3 · ≈$0.35 a check"
    assert dlg.get_by_label("The last 30 days").text_content().startswith("The last 30 days: 14 tasks")
    dlg.get_by_role("button", name="Cancel").click()
    host.record = {"reviewer": {"days": 30, "finished": 2, "merged": 2, "first_time": 2, "usd_per_merged": None,
                                "check": {"checks": 2, "clean": 2, "caught": 0, "left": 0, "usd_per_check": None}}}
    host.bump({})
    pg.wait_for_timeout(300)
    pg.get_by_role("button", name="Edit Reviewer").click()
    assert " ".join(dlg.get_by_label("Its check", exact=True).text_content().split()) == "Its check, the last 30 days: 2 goals: too few to say more"
    dlg.get_by_role("button", name="Cancel").click()
    pg.get_by_role("button", name="Edit Grunts").click()
    assert dlg.get_by_label("Its check", exact=True).count() == 0                                   # an agent that checks nothing
