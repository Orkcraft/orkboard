"""Spec 37 C on the phone's results (390 × 844; each a stop along the bottom, spec 49 §6): the same lines as the desktop's (test_gate_browser.py). Screenshot to the
folder named by GATE_SHOTS when it is set."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from tests.test_gate_browser import LINES, tasks  # noqa: E402
from tests.browser_kit import WAIT_MS  # noqa: E402
from tests.test_pwa_shell_browser import _phone, _pop  # noqa: E402


def plain(line):
    """The desktop's line starts with a typed ✓ or ✗; the phone draws orkUI's sign there (spec 50 §0): the words after it are the same."""
    return re.sub(r"^[✓✗] ", "", line)


@pytest.mark.asyncio
async def test_phone_review_card_reads_ran_then_the_exit_code_then_the_counts(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.plan["tasks"] = tasks()
        stub.bump(None)
        await page.locator('.hc[aria-label*="Pytest counts"]').wait_for(timeout=WAIT_MS)
        for title, line in LINES.items():                                                              # a result stop says its tests' line, then its changes
            raised = await _pop(page, f"To look at: {title}")
            assert plain(line) in " ".join((await raised.locator(".raised__text").inner_text()).split()), title
            if title == "Exit one":
                assert await raised.get_by_role("button", name="Fix", exact=True).is_visible()
                assert await raised.get_by_role("button", name="Merge into dev").is_disabled()
            if title == "Nothing ran":
                assert await raised.get_by_role("button", name="Merge into dev").is_enabled()
            await raised.get_by_role("button", name="Put it back").click()
            await raised.wait_for(state="hidden", timeout=WAIT_MS)
        raised = await _pop(page, "To look at: Pytest counts")                                         # its own screen has the facts, the same line
        await raised.get_by_role("button", name="Open it on its own screen").click()
        facts = page.locator(".screen .facts dd").first
        await facts.wait_for(timeout=WAIT_MS)
        assert " ".join((await facts.inner_text()).split()) == plain(LINES["Pytest counts"])
        await page.get_by_role("button", name="Back", exact=True).click()
        folder = os.environ.get("GATE_SHOTS")
        if folder:
            Path(folder).mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(Path(folder) / "review-phone-390x844.png"))
