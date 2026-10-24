"""A subscription's spend as a share of Claude's five-hour window (decisions §82), on the desktop (the phone's:
tests/test_pwa_spend_share_browser.py): with the snapshot's `rate` (what 1 % of the window has cost at API prices) Agents
says a task's cost as *≈ 18 % of 5h a task*, with its hint; without one it says the $ as before
(tests/test_shell_36_browser.py, tests/test_pwa_agents36_browser.py)."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_36_browser import Stub36  # noqa: E402
from tests.test_shell_browser import _agents, _open  # noqa: E402

pytestmark = pytest.mark.browser

RATE = {"tool": "claude", "window": "5h", "usd_per_pct": 0.05, "windows": 3}
TIP = "An estimate: its cost at API prices over what 1 % of Claude's five-hour window has cost on this machine"


def test_the_desktop_says_a_tasks_cost_as_a_share_of_the_five_hour_window(gui):
    pg, host, errors = _open(gui, host=Stub36())
    _agents(pg)
    host.usd_task, host.rate = {"grunt": 0.9}, RATE
    host.bump({})
    pg.wait_for_function("() => document.querySelector(\".shell-role[data-slug='grunt'] .shell-role__head\")?.getAttribute('aria-label')?.includes('18 % of 5h')", timeout=WAIT_MS)
    line = pg.locator(".shell-role[data-slug='grunt'] .shell-role__head")
    assert " ".join(line.inner_text().split()).startswith("Grunts ×8 ≈ 18 % of 5h a task Edit")              # $0.90 at $0.05 a percent
    assert line.locator(".shell-role__week").inner_text() == "≈25 % of 5h today · ≈18 % of 5h a result · 6/10 the first time"
    assert line.locator(f"[title=\"{TIP}\"]").count() == 2 and "$" not in line.inner_text()
    pg.close()
    assert not errors, "\n".join(errors)

