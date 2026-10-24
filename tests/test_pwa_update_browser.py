"""A newer Orkline installed from the phone (pwa/shell-update.js, gui/board_host.py `BoardPhone`), in Chromium at
390 × 844: the bar says a major update is out, its sheet installs it on the computer with Update and restart, and when
the computer comes back on that version the phone says so; Later hides it, Check for updates in the menu shows it again."""
from __future__ import annotations

import pytest

pw = pytest.importorskip("playwright.async_api")

from orkboard.gui import board_host, updates as gui_updates  # noqa: E402
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _phone  # noqa: E402

pytestmark = pytest.mark.browser

OFFER = {"version": "9.0.0", "critical": False, "major": True, "notes": ["9.0.0: Parties work across projects."],
         "critical_notes": [], "current": board_host.__version__, "state": "idle", "error": "", "installed": "",
         "can": True, "how": "uv tool upgrade orkboard", "policy": "critical"}


@pytest.mark.asyncio
async def test_the_phone_installs_a_major_update_and_says_when_the_computer_runs_it(fake_repo, monkeypatch):
    shown = {"update": dict(OFFER)}
    installs = []
    monkeypatch.setattr(gui_updates.Updates, "snapshot", lambda self: shown["update"])

    def install(self, args):
        installs.append(args)
        shown["update"] = {**OFFER, "state": "installing"}
        self.host.on_change()
        return shown["update"]
    monkeypatch.setattr(gui_updates.Updates, "install", install)
    monkeypatch.setattr(gui_updates.Updates, "check", lambda self, args: shown["update"])
    async with _phone(fake_repo, monkeypatch) as (_stub, page):
        bar = page.locator('[data-update="bar"]')
        await bar.wait_for(timeout=WAIT_MS)
        assert await bar.inner_text() == "New version: Orkline 9.0.0"
        assert await page.evaluate(NO_SCROLL)
        await bar.click()
        ask = page.get_by_role("dialog", name="New version: Orkline 9.0.0")
        await ask.wait_for(timeout=WAIT_MS)
        said = await ask.inner_text()
        assert "A major update" in said and "9.0.0: Parties work across projects." in said and "comes back on its own" in said
        await ask.get_by_role("button", name="Later").click()
        await bar.wait_for(state="hidden", timeout=WAIT_MS)
        await page.get_by_role("button", name="Menu: Stop all, Spend, Agents, Today and settings").click()
        await page.locator('[data-act="update-check"]').click()
        await bar.wait_for(timeout=WAIT_MS)                          # asked for: shown again, whatever Later said
        await bar.click()
        await ask.get_by_role("button", name="Update and restart").click()
        await page.get_by_text("Installing Orkline 9.0.0 on the computer.", exact=False).first.wait_for(timeout=WAIT_MS)
        assert len(installs) == 1
        await page.locator('[data-update="bar"]', has_text="Installing Orkline 9.0.0 on the computer").wait_for(timeout=WAIT_MS)
        monkeypatch.setattr(board_host, "__version__", "9.0.0")       # the computer came back on 9.0.0
        shown["update"] = None
        await page.get_by_text("Updated: the computer runs Orkline 9.0.0.").wait_for(timeout=WAIT_MS * 2)
        await bar.wait_for(state="hidden", timeout=WAIT_MS)
