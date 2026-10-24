"""A subscription's spend as a share of Claude's five-hour window (decisions §82), on the phone: with the snapshot's `rate`
Agents says a task's cost as *≈ 8 % of 5h a task*, with its hint (the desktop's: tests/test_spend_share_browser.py)."""
from __future__ import annotations

import pytest

from tests.test_pwa_shell_browser import WAIT_MS, _agents, _phone  # noqa: F401
from tests.test_spend_share_browser import RATE, TIP

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser
from playwright.async_api import expect  # noqa: E402


@pytest.mark.asyncio
async def test_the_phone_says_a_tasks_cost_as_a_share_of_the_five_hour_window(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.usd_task, stub.rate = {"grunt": 0.4}, RATE
        stub.bump({})
        agents = await _agents(page)
        line = agents.locator(".role[data-role='grunt'] .role-head")
        await expect(line).to_have_attribute("aria-label", "Grunts: an ork, Engineering, Seasoned; up to 8 at once; about 8 % of 5h a task", timeout=WAIT_MS)
        assert " ".join((await line.inner_text()).split()).startswith("Grunts ×8 ≈ 8 % of 5h a task Edit")
        assert await line.locator(".role-facts").inner_text() == "≈25 % of 5h today"
        assert await line.locator(".role-usd").get_attribute("title") == TIP
