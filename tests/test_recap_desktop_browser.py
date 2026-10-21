"""Spec 42 A on the desktop (docs/specs/42-coming-back.md §1.3–§1.4, Tests → A): Chromium at 1 440 × 900 against the Map's stub host
with a fake `ideas.recap`. A last look 9 hours old gets the card at the top of the Map with its lines in order; 2 hours old, none;
no last look, none and the key written; Close and Esc remove it; a click on an idea opens it `via: "recap"`; *Waits for you* opens
Needs you; no horizontal scroll at 390 px."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_map_desktop_browser import SHOP, MapHost, _open, key  # noqa: E402
from tests.test_shell_browser import _calls, _sent  # noqa: E402

pytestmark = pytest.mark.browser

LOOK = key(SHOP).replace("orkboard.tabs.", "orkboard.look.")

RECAP = {"since": "2026-10-20T03:00:00+00:00", "hours": 9, "into": "dev",
         "merged": {"tasks": 5, "first_time": 4, "ideas": [
             {"slug": "export", "short": "Export notes", "title": "Export notes", "goal": "ship-sync", "done": True},
             {"slug": "dark", "short": "Dark mode", "title": "Dark mode", "goal": "ship-sync", "done": False}]},
         "flags": [{"goal": "ship-sync", "short": "Ship sync", "title": "Ship sync", "met": True, "by": "Product manager"}],
         "night": {"drafted": 2, "started": 1, "refreshed": 0, "proposed": 2},
         "proposed": [{"slug": "tags", "short": "Tag the notes", "title": "Tag the notes", "goal": "grow"}],
         "failed": [{"slug": "sync", "short": "Sync ideas", "title": "Sync ideas between the phone and the town", "task": "The table"}],
         "usd": 4.2, "nights": 0, "waits": {"you": 1, "review": 3}, "empty": False}


class RecapHost(MapHost):
    def __init__(self):
        super().__init__()
        self.recap = dict(RECAP)

    def handle(self, name, a):
        if name == "ideas.recap":
            self.log.append((name, a))
            return dict(self.recap)
        return super().handle(name, a)


def seed(hours_ago=None):
    """The last look this device kept, written once (a reload keeps what the page wrote)."""
    if hours_ago is None:
        return ""
    return f"if (!localStorage.getItem({json.dumps(LOOK)})) localStorage.setItem({json.dumps(LOOK)}, String(Date.now() - {hours_ago} * 3600 * 1000));"


def _page(gui, hours_ago, host=None, viewport=None, ready=".map-goal"):
    pg, host, errors = _open(gui, host or RecapHost(), viewport=viewport, init=seed(hours_ago), ready=ready)
    return pg, host, errors


def _text(loc):
    return " ".join(loc.text_content().split())


def test_a_last_look_nine_hours_old_shows_the_card_at_the_top_of_the_map_with_its_lines_in_order(gui):
    pg, host, errors = _page(gui, 9)
    card = pg.get_by_label("While you were away")
    card.wait_for(timeout=WAIT_MS)
    assert _text(card.locator(".away__title")) == "While you were away · 9 h"
    assert [_text(p) for p in card.locator(".away__lines p").all()] == [
        "5 results in dev, 4 the first time", "Export notes · done, Dark mode", "Flag raised: Ship sync, met, says Product manager",
        "The night: drafted 2 ideas, started 1 plan, proposed 2 ideas", "Proposed for you: Tag the notes", "Failed: Sync ideas · The table",
        "≈$4.20 of work at API prices, not your bill.", "Waits for you: 1 answer, 3 results to check"]
    assert pg.locator(".map > *").first.get_attribute("aria-label") == "While you were away"     # at the top, above the goals
    assert pg.locator(".away__failed.ok-tone-error").count() == 1
    assert pg.locator("[data-modal-backdrop]").count() == 0 and card.get_by_role("button", name="Close").get_attribute("class") == "ork-btn quiet"
    since = _calls(pg, host, "ideas.recap")[0]["since"]
    assert 8.9 * 3600e3 < pg.evaluate("Date.now()") - since < 9.1 * 3600e3
    assert int(pg.evaluate(f"localStorage.getItem({json.dumps(LOOK)})")) > since                  # the last look moved
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "recap", "ref": "9h", "device": "desktop"}))
    pg.close()
    assert not errors, "\n".join(errors)


def test_two_hours_is_not_away_and_no_last_look_writes_it_and_shows_nothing(gui):
    pg, host, errors = _page(gui, 2)
    pg.wait_for_timeout(400)
    assert pg.get_by_label("While you were away").count() == 0 and not [n for n, _a in host.log if n == "ideas.recap"]
    pg.close()
    pg, host, errors2 = _page(gui, None)
    pg.wait_for_function(f"localStorage.getItem({json.dumps(LOOK)}) !== null", timeout=WAIT_MS)
    assert pg.get_by_label("While you were away").count() == 0 and not [n for n, _a in host.log if n == "ideas.recap"]
    pg.close()
    assert not errors and not errors2


def test_an_empty_answer_shows_nothing_and_the_look_still_moves(gui):
    host = RecapHost()
    host.recap = {"empty": True, "hours": 9, "merged": {"tasks": 0, "first_time": 0, "ideas": []}, "waits": {"you": 2, "review": 0}}
    pg, host, errors = _page(gui, 9, host)
    assert _calls(pg, host, "ideas.recap")
    pg.wait_for_function(f"Date.now() - Number(localStorage.getItem({json.dumps(LOOK)})) < 60000", timeout=WAIT_MS)
    assert pg.get_by_label("While you were away").count() == 0
    pg.close()
    assert not errors


def test_close_and_esc_remove_the_card_and_it_is_not_shown_again(gui):
    pg, host, errors = _page(gui, 9)
    card = pg.get_by_label("While you were away")
    card.wait_for(timeout=WAIT_MS)
    card.get_by_role("button", name="Close").click()
    assert card.count() == 0
    pg.reload()
    pg.wait_for_selector(".map-goal", timeout=WAIT_MS)
    pg.wait_for_timeout(300)
    assert pg.get_by_label("While you were away").count() == 0 and len([n for n, _a in host.log if n == "ideas.recap"]) == 1
    pg.close()
    pg, host, errors2 = _page(gui, 9)
    pg.get_by_label("While you were away").wait_for(timeout=WAIT_MS)
    pg.get_by_label("While you were away").get_by_role("button", name="Close").focus()
    pg.keyboard.press("Escape")
    assert pg.get_by_label("While you were away").count() == 0 and pg.locator(".shell-preview .map").is_visible()   # Esc closed the card, not the Map
    pg.close()
    assert not errors and not errors2


def test_a_click_on_an_idea_opens_it_and_waits_for_you_opens_needs_you(gui):
    pg, host, errors = _page(gui, 9)
    card = pg.get_by_label("While you were away")
    card.wait_for(timeout=WAIT_MS)
    card.get_by_role("button", name="Dark mode").click()
    pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "idea", "ref": "dark", "device": "desktop", "via": "recap"}))
    pg.locator(".shell-tabstrip").get_by_role("tab", name="Map").click()
    pg.get_by_label("While you were away").get_by_role("button", name="Waits for you: 1 answer, 3 results to check").click()
    pg.locator(".board-today").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-board").get_by_role("tab", name="Needs you").get_attribute("aria-selected") == "true"
    pg.close()
    assert not errors, "\n".join(errors)


def test_the_card_does_not_scroll_the_page_sideways_at_390_px(gui):
    pg, host, errors = _page(gui, 9, viewport={"width": 390, "height": 844}, ready=".shell")
    pg.get_by_role("button", name="Map").click()
    pg.get_by_label("While you were away").wait_for(timeout=WAIT_MS)
    assert pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    assert pg.get_by_label("While you were away").bounding_box()["width"] <= 390
    pg.close()
    assert not errors, "\n".join(errors)


def test_nights_in_a_row_is_line_seven_from_two_and_not_at_one_spec_42_h(gui):
    for nights, said in ((5, True), (2, True), (1, False), (0, False)):
        host = RecapHost()
        host.recap = {**RECAP, "nights": nights}
        pg, host, errors = _page(gui, 9, host)
        card = pg.get_by_label("While you were away")
        card.wait_for(timeout=WAIT_MS)
        lines = [_text(p) for p in card.locator(".away__lines p").all()]
        if said:
            assert lines[-3:] == ["≈$4.20 of work at API prices, not your bill.", f"{nights} nights in a row with work done.", "Waits for you: 1 answer, 3 results to check"]
        else:
            assert not [x for x in lines if "in a row" in x]
        pg.close()
        assert not errors, "\n".join(errors)
