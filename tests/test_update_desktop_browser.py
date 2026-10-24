"""A newer version in Orkboard's window (js/shell/update.js, docs/updates.md), in a real browser: a major update is
offered in a dialog with Update and restart, Later hides it until the next version, and Settings → Updates shows it
again with what installs by itself."""
from __future__ import annotations

import pytest

playwright = pytest.importorskip("playwright.sync_api")

from orkboard.core import updates  # noqa: E402
from orkboard.gui.server import Server  # noqa: E402
from tests.browser_kit import WAIT_MS, launch  # noqa: E402
from tests.test_board_browser import board  # noqa: E402,F401  (the fixture)

pytestmark = pytest.mark.browser


def test_a_major_update_is_offered_later_hides_it_and_settings_shows_it(board):   # noqa: F811
    board.updates._method = lambda: updates.Method("uv", (("uv", "tool", "upgrade", "orkboard"),))
    board.updates._read(updates.State(manifest={"releases": [
        {"version": "9.0.0", "notes": "Parties work across projects."}]}))
    server = Server(board)
    thread = server.start_thread()
    with playwright.sync_playwright() as p:
        browser = launch(p)
        try:
            pg = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
            errors: list[str] = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(server.url)
            ask = pg.get_by_role("dialog", name="New version: Orkline 9.0.0")
            ask.wait_for(timeout=WAIT_MS)
            assert "A major update" in ask.inner_text() and "9.0.0: Parties work across projects." in ask.inner_text()
            assert ask.get_by_role("button", name="Update and restart").is_visible()
            ask.get_by_role("button", name="Later").click()
            ask.wait_for(state="detached", timeout=WAIT_MS)
            pg.get_by_role("button", name="Settings").click()
            field = pg.locator('[data-settings="updates"]')
            field.wait_for(timeout=WAIT_MS)
            assert "New version: Orkline 9.0.0" in field.inner_text()
            assert field.get_by_label("Updates that install by themselves").input_value() == "critical"
            field.get_by_label("Updates that install by themselves").select_option("ask")
            field.get_by_role("button", name="Update…").click()
            pg.get_by_role("dialog", name="New version: Orkline 9.0.0").wait_for(timeout=WAIT_MS)
            assert board.machine.updates == "ask"
            assert not errors, errors
        finally:
            browser.close()
            server.stop()
            thread.join(10)
