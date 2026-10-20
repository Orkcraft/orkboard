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
