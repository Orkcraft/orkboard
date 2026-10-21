"""Spec 42 D on the desktop (docs/specs/42-coming-back.md §4, Tests → D): an agent's dialog says its record of the last 30 days in
the four wordings, read only; the agent's line on Agents is as it was."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_36_browser import Stub36  # noqa: E402
from tests.test_shell_browser import _agents, _open  # noqa: E402

pytestmark = pytest.mark.browser

RECORDS = {"grunt": {"days": 30, "finished": 41, "merged": 38, "first_time": 36, "usd_per_merged": 0.6},
           "scribe": {"days": 30, "finished": 2, "merged": 2, "first_time": 2, "usd_per_merged": None},
           "taskmaster": {"days": 30, "plans": 12, "finished": 41, "first_time": 36}}


@pytest.fixture
def recorded(gui):
    host = Stub36()
    host.record = dict(RECORDS)
    pg, host, errors = _open(gui, host=host)
    _agents(pg)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _record(pg, button):
    pg.get_by_role("button", name=button).click()
    dlg = pg.get_by_role("dialog", name="Edit agent")
    dlg.get_by_label("Name").wait_for(timeout=WAIT_MS)
    text = " ".join(dlg.get_by_label("The last 30 days").text_content().split())
    assert dlg.get_by_label("The last 30 days").locator("input, textarea, button").count() == 0          # read only
    dlg.get_by_role("button", name="Cancel").click()
    return text


def test_each_wording_in_the_dialog_and_the_agents_line_unchanged(recorded):
    pg, host = recorded
    line = pg.locator(".shell-role[data-slug='grunt']").inner_text()
    assert _record(pg, "Edit Grunts") == "The last 30 days: 41 tasks, 36 merged the first time · ≈$0.60 a merged result"
    assert _record(pg, "Edit Scribe") == "The last 30 days: 2 tasks: too few to say more"
    assert _record(pg, "Edit Taskmaster") == "The last 30 days: 12 plans; of their 41 tasks, 36 merged the first time"
    assert pg.locator(".shell-role[data-slug='grunt']").inner_text() == line and "36 merged" not in line      # §54.6: the line stays its own
    host.record = {"grunt": {"days": 30, "finished": 5, "merged": 4, "first_time": 3, "usd_per_merged": None}}
    host.bump({})
    pg.wait_for_timeout(200)
    assert _record(pg, "Edit Grunts") == "The last 30 days: 5 tasks, 3 merged the first time"                  # no price: none said
    assert _record(pg, "Edit Scribe") == "No tasks in the last 30 days"                                         # null
    assert _record(pg, "Edit Taskmaster") == "No tasks in the last 30 days"


def test_a_new_agent_has_no_record(recorded):
    pg, _host = recorded
    pg.get_by_role("button", name="+ Add agent").click()
    pg.get_by_role("dialog", name="Add an agent").get_by_role("button", name="Your own").click()
    assert pg.get_by_role("dialog", name="Add agent").get_by_label("The last 30 days").count() == 0
