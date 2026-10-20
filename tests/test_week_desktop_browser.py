"""Spec 42 F on the desktop (docs/specs/42-coming-back.md §6, Tests → F): today's spend in the top bar is a button that opens This week
with its lines in order; *Nothing waits for tonight* and New idea; no night, no tonight line."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import StubHost, _open, _sent  # noqa: E402

pytestmark = pytest.mark.browser

WEEK = {"usd": 46.1, "ops_usd": 3.2, "merged": 12, "first_time": 10, "usd_per_merged": 3.84, "nights": {"worked": 4, "idle": 2, "off": 1},
        "tonight": 0, "night_on": True, "into": "dev"}


class WeekHost(StubHost):
    def __init__(self):
        super().__init__()
        self.week = dict(WEEK)

    def handle(self, name, a):
        if name == "ideas.week_work":
            self.log.append((name, a))
            return dict(self.week)
        return super().handle(name, a)


def _lines(pg):
    return [" ".join(p.text_content().split()) for p in pg.get_by_role("dialog", name="This week").locator(".week p").all()]


def _show(gui, host):
    pg, host, errors = _open(gui, host=host)
    pg.get_by_role("button", name="Spend today: $2.40. This week's work").click()
    pg.get_by_role("dialog", name="This week").locator(".week").wait_for(timeout=WAIT_MS)
    return pg, host, errors


def test_todays_spend_opens_this_week_with_its_lines_in_order(gui):
    pg, host, errors = _show(gui, WeekHost())
    assert _lines(pg) == ["≈$46 of work at API prices in this project, ≈$3 in Operations: not your bill",
                          "12 results in dev, 10 the first time · ≈$3.84 a result",
                          "The last 7 nights: 4 with work done, 2 with none, 1 Orkline was not running",
                          "Nothing waits for tonight · New idea"]
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "week", "ref": "this", "device": "desktop"}))
    pg.get_by_role("dialog", name="This week").get_by_role("button", name="New idea").click()
    pg.get_by_role("dialog", name="New idea").wait_for(timeout=WAIT_MS)                              # it opens New idea
    pg.close()
    assert not errors, "\n".join(errors)


def test_tonight_says_how_many_wait_and_a_null_part_a_missing_price_and_no_night_are_left_out(gui):
    host = WeekHost()
    host.week.update(tonight=2, ops_usd=None, usd_per_merged=None, nights={"worked": 0, "idle": 7, "off": 0})
    pg, host, errors = _show(gui, host)
    assert _lines(pg) == ["≈$46 of work at API prices in this project: not your bill", "12 results in dev, 10 the first time",
                          "The last 7 nights: 7 with none", "Tonight: 2 wait"]
    pg.keyboard.press("Escape")
    host.week.update(night_on=False, usd=None, ops_usd=None, merged=0, first_time=0, nights={"worked": 0, "idle": 0, "off": 0})
    pg.get_by_role("button", name="Spend today: $2.40. This week's work").click()
    pg.get_by_role("dialog", name="This week").locator(".week").wait_for(timeout=WAIT_MS)
    assert _lines(pg) == ["No results in dev in the last 7 days"]
    pg.close()
    assert not errors, "\n".join(errors)


# -- spec 44 B: the week's pace ---------------------------------------------------------------------------------------

def test_the_week_line_says_what_low_work_does_and_last_weeks_unused_share(gui):
    host = WeekHost()
    host.week.update(week={"left": 0.55, "rest": 2 / 7, "pace": "ahead", "reset": 0}, last_unused=0.3)
    pg, host, errors = _show(gui, host)
    lines = _lines(pg)
    assert lines[-3:-1] == ["The week: 55 % left with 2 days to go: Low work starts by day", "Last week ended with 30 % unused"]
    pg.keyboard.press("Escape")
    for pace, words in (("even", "Low work waits for the night"), ("behind", "Low work waits until the week comes back")):
        host.week.update(week={"left": 0.2, "rest": 1 / 7, "pace": pace, "reset": 0}, last_unused=None)
        pg.get_by_role("button", name="Spend today: $2.40. This week's work").click()
        pg.get_by_role("dialog", name="This week").locator(".week").wait_for(timeout=WAIT_MS)
        got = _lines(pg)
        assert f"The week: 20 % left with 1 day to go: {words}" in got and not [x for x in got if x.startswith("Last week ended")]
        pg.keyboard.press("Escape")
    host.week.update(week=None)
    pg.get_by_role("button", name="Spend today: $2.40. This week's work").click()
    pg.get_by_role("dialog", name="This week").locator(".week").wait_for(timeout=WAIT_MS)
    assert not [x for x in _lines(pg) if x.startswith("The week")]                                     # no week read: no line
    pg.close()
    assert not errors, "\n".join(errors)


def test_a_boards_own_night_work_reads_or_sooner_and_a_held_wait_says_until_when(gui):
    pg, host, errors = _open(gui, host=StubHost())
    got = pg.evaluate("""async () => {
      const base = document.querySelector('link[href$="shell.css"]').href.replace('shell/shell.css', 'board/');
      const t = await import(base + 'tracks.js'), m = await import(base + 'maplayout.js');
      return [t.rowOf({ state: "raw", queue: "night", night_by: "board" }, {})[0], t.rowOf({ state: "raw", queue: "night", night_by: "person" }, {})[0],
        t.rowOf({ state: "plan", start_at: "night", night_by: "board" }, {})[0], t.rowOf({ state: "plan", start_at: "night" }, {})[0],
        m.waitsWords({ kind: "week", until: "2026-10-26T09:00" })]; }""")
    assert got[:4] == ["tonight, or sooner if the week has room", "tonight", "starts tonight, or sooner if the week has room", "starts tonight"]
    assert got[4] == "waits: the week is behind · until Mon 09:00"
    pg.close()
    assert not errors, "\n".join(errors)


# -- spec 42 G: Last week ----------------------------------------------------------------------------------------------

import datetime as dt  # noqa: E402
import json  # noqa: E402

from tests.test_map_desktop_browser import SHOP, MapHost, _open as _open_map, key  # noqa: E402
from tests.test_recap_desktop_browser import LOOK, RECAP  # noqa: E402

WEEK_KEY = key(SHOP).replace("orkboard.tabs.", "orkboard.week.")
LAST = {"week": "2026-W42", "from": "2026-10-12", "to": "2026-10-18", "into": "dev", "merged": 23, "first_time": 19, "usd": 61.2, "usd_per_merged": 2.66,
        "before": {"merged": 14, "first_time": 10, "usd_per_merged": 3.1},
        "goals": [{"goal": "ship-sync", "short": "Offline mode", "title": "Offline mode", "done": 3}, {"goal": "grow", "short": "Billing", "title": "Billing", "done": 1}],
        "flags": [{"goal": "ship-sync", "short": "Offline mode", "title": "Offline mode", "met": True, "by": "Product manager"}],
        "dearest": {"slug": "sync", "short": "Offline mode", "title": "Offline mode", "usd": 12.0},
        "fastest": {"slug": "dark", "short": "Export CSV", "title": "Export CSV", "minutes": 42},
        "answers": {"answers": 12, "recommended": 9, "decided": 2}, "nights": {"worked": 5, "idle": 2, "off": 0}, "streak": 0, "empty": False}


class LastHost(MapHost):
    def __init__(self):
        super().__init__()
        self.last = dict(LAST)
        self.recap = dict(RECAP)

    def handle(self, name, a):
        if name in ("ideas.week", "ideas.recap"):
            self.log.append((name, a))
            return dict(self.last if name == "ideas.week" else self.recap)
        return super().handle(name, a)


def _iso(days_ago):
    year, week, _d = (dt.date.today() - dt.timedelta(days=days_ago)).isocalendar()
    return f"{year}-W{week:02d}"


def _seed(week=None, look_hours=None):
    out = ""
    if week:
        out += f"if (!localStorage.getItem({json.dumps(WEEK_KEY)})) localStorage.setItem({json.dumps(WEEK_KEY)}, {json.dumps(week)});"
    if look_hours is not None:
        out += f"if (!localStorage.getItem({json.dumps(LOOK)})) localStorage.setItem({json.dumps(LOOK)}, String(Date.now() - {look_hours} * 3600 * 1000));"
    return out


def test_the_first_look_of_a_new_week_shows_last_weeks_card_with_its_lines_then_the_recap_and_not_twice(gui):
    pg, host, errors = _open_map(gui, LastHost(), init=_seed(_iso(14), 9), ready=".map-card")
    card = pg.get_by_label("Last week")
    card.wait_for(timeout=WAIT_MS)
    assert " ".join(card.locator(".away__title").text_content().split()) == "Last week · 12–18 October"
    assert [" ".join(p.text_content().split()) for p in card.locator(".away__lines p").all()] == [
        "23 results in dev, 19 the first time (83 %; the week before 71 %)", "≈$2.66 a result (the week before ≈$3.10)",
        "Goals: Offline mode, 3 ideas done · Billing, 1", "Flags: Offline mode, met",
        "Cost the most: Offline mode, ≈$12 · Fastest from idea to dev: Export CSV, 42 min",
        "Questions: 9 of 12 answers were the recommended one; 2 cards left to the Taskmaster",
        "Nights: 5 with work done, 2 with none"]
    assert pg.get_by_label("While you were away").count() == 0                                         # the week's card comes first
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "week", "ref": "2026-W42", "device": "desktop"}))
    assert json.loads(pg.evaluate(f"JSON.stringify(localStorage.getItem({json.dumps(WEEK_KEY)}))")) == _iso(7)
    recap_logs = lambda: [a for n, a in host.log if n == "ideas.log" and a.get("what") == "recap"]   # noqa: E731
    assert recap_logs() == []                                                                          # it waits behind Last week's card: not opened yet
    card.get_by_role("button", name="Close").click()
    pg.get_by_label("While you were away").wait_for(timeout=WAIT_MS)                                   # then the recap's
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "recap", "ref": "9h", "device": "desktop"})) and len(recap_logs()) == 1
    pg.get_by_label("While you were away").get_by_role("button", name="Close").click()
    pg.reload()
    pg.locator(".map-card").first.wait_for(timeout=WAIT_MS)
    pg.wait_for_timeout(400)
    assert pg.get_by_label("Last week").count() == 0 and len([n for n, _a in host.log if n == "ideas.week"]) == 1
    pg.close()
    assert not errors, "\n".join(errors)


def test_the_week_ideas_week_answered_is_the_one_kept_so_its_card_shows_once(gui):
    host = LastHost()
    host.last = {**LAST, "week": "2026-W41"}                          # the host's idea of last week is not this device's
    pg, host, errors = _open_map(gui, host, init=_seed("2026-W41"), ready=".map-card")
    pg.wait_for_function(f"localStorage.getItem({json.dumps(WEEK_KEY)}) === '2026-W41'", timeout=WAIT_MS)
    pg.wait_for_timeout(400)
    assert [n for n, _a in host.log if n == "ideas.week"] == ["ideas.week"] and pg.get_by_label("Last week").count() == 0     # asked, kept, not shown
    pg.close()
    assert not errors, "\n".join(errors)


def test_a_device_with_no_week_key_writes_it_and_shows_nothing_and_an_empty_week_shows_nothing(gui):
    pg, host, errors = _open_map(gui, LastHost(), ready=".map-card")
    pg.wait_for_function(f"localStorage.getItem({json.dumps(WEEK_KEY)}) !== null", timeout=WAIT_MS)
    assert pg.get_by_label("Last week").count() == 0 and not [n for n, _a in host.log if n == "ideas.week"]
    pg.close()
    host = LastHost()
    host.last = {**LAST, "empty": True}
    pg, host, errors2 = _open_map(gui, host, init=_seed(_iso(14)), ready=".map-card")
    pg.wait_for_function(f"localStorage.getItem({json.dumps(WEEK_KEY)}) === {json.dumps(_iso(7))}", timeout=WAIT_MS)
    assert pg.get_by_label("Last week").count() == 0
    pg.close()
    assert not errors and not errors2


def test_the_maps_last_week_link_shows_the_card_any_time_and_logs_via_map(gui):
    host = LastHost()
    host.last = {**LAST, "goals": [], "flags": [], "dearest": None, "fastest": None, "answers": None, "before": None, "usd_per_merged": None}
    pg, host, errors = _open_map(gui, host, ready=".map-card")
    pg.get_by_role("button", name="Last week", exact=True).click()
    card = pg.get_by_label("Last week")
    card.wait_for(timeout=WAIT_MS)
    assert [" ".join(p.text_content().split()) for p in card.locator(".away__lines p").all()] == ["23 results in dev, 19 the first time (83 %)",
                                                                                                    "Nights: 5 with work done, 2 with none"]
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "week", "ref": "2026-W42", "device": "desktop", "via": "map"}))
    card.get_by_role("button", name="Close").click()
    host.last = {**host.last, "empty": True, "merged": 0, "first_time": 0, "nights": {"worked": 0, "idle": 0, "off": 0}}
    pg.get_by_role("button", name="Last week", exact=True).click()
    pg.get_by_label("Last week").get_by_text("Nothing was merged or finished.").wait_for(timeout=WAIT_MS)
    pg.close()
    assert not errors, "\n".join(errors)


def test_nights_in_a_row_is_line_four_of_this_week_from_two_and_after_the_nights_of_last_week_spec_42_h(gui):
    host = WeekHost()
    host.week.update(streak=5)
    pg, host, errors = _show(gui, host)
    assert _lines(pg)[2:4] == ["The last 7 nights: 4 with work done, 2 with none, 1 Orkline was not running", "5 nights in a row"]
    pg.keyboard.press("Escape")
    host.week.update(streak=1)
    pg.get_by_role("button", name="Spend today: $2.40. This week's work").click()
    pg.get_by_role("dialog", name="This week").locator(".week").wait_for(timeout=WAIT_MS)
    assert not [x for x in _lines(pg) if "in a row" in x]
    pg.close()
    host = LastHost()
    host.last = {**LAST, "streak": 5}
    pg, host, errors2 = _open_map(gui, host, init=_seed(_iso(14)), ready=".map-card")
    card = pg.get_by_label("Last week")
    card.wait_for(timeout=WAIT_MS)
    assert [" ".join(p.text_content().split()) for p in card.locator(".away__lines p").all()][-1] == "Nights: 5 with work done, 2 with none · 5 in a row"
    pg.close()
    assert not errors and not errors2
