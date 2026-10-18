"""Spec 37 C on the phone's Review card (390 × 844): the same lines as the desktop's (test_gate_browser.py). Screenshot to the
folder named by GATE_SHOTS when it is set."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from tests.test_gate_browser import LINES, tasks  # noqa: E402
from tests.browser_kit import WAIT_MS  # noqa: E402
from tests.test_pwa_shell_browser import _phone  # noqa: E402

@pytest.mark.asyncio
async def test_phone_review_card_reads_ran_then_the_exit_code_then_the_counts(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.plan["tasks"] = tasks()
        stub.bump(None)
        await page.get_by_role("tab", name="Review").click()
        await page.locator(".result", has_text="Pytest counts").wait_for(timeout=WAIT_MS)
        for title, line in LINES.items():
            facts = page.locator(".result", has_text=title).locator(".facts dd").first
            assert " ".join((await facts.inner_text()).split()) == line, title
        red = page.locator(".result", has_text="Exit one")
        assert await red.get_by_role("button", name="Fix", exact=True).is_visible()
        assert await red.get_by_role("button", name="Merge into dev").is_disabled()
        assert await page.locator(".result", has_text="Nothing ran").get_by_role("button", name="Merge into dev").is_enabled()
        folder = os.environ.get("GATE_SHOTS")
        if folder:
            Path(folder).mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(Path(folder) / "review-phone-390x844.png"))
