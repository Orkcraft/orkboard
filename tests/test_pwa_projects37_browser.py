"""Spec 37 part D3 on the phone (docs/specs/37-board-and-line.md §8, "Tests → D3"): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py with fake `projects.*` and `files.read` commands. The switcher as a sheet with the open projects and
their counts, a tap shows another one; a spec a goal links opens read-only, rendered, with no edit or git control; no
horizontal scroll of the page. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _phone, _pick_goal, _shot  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

SPEC = "docs/specs/37-board-and-line.md"
HTML = "<h1>Board and line</h1><p>The <strong>phone</strong> reads this.</p><table><tr><td>" + "wide " * 40 + "</td></tr></table>"


@pytest.fixture(autouse=True)
def _projects(monkeypatch):
    state = {"current": "/work/alpha"}
    rows = [{"path": "/work/alpha", "name": "alpha", "working": 2, "needs_you": 1, "review": 0},
            {"path": "/work/beta", "name": "beta", "working": 0, "needs_you": 0, "review": 3}]
    real = Stub.commands

    def commands(self):
        def use(a):
            assert a.get("device") == "phone"
            state["current"] = a["path"]
            self.calls.append(("projects.use", {"path": a["path"]}))
            return self.bump({"ok": True})

        def lst(a):
            self.calls.append(("projects.list", {}))
            return {"current": state["current"], "open": rows, "recent": [{"path": "/work/old", "name": "old"}]}

        def doc(a):
            self.calls.append(("ideas.doc", {"path": a["path"]}))
            return {"path": a["path"], "text": "# Board and line", "html": HTML, "truncated": False}
        return {**real(self), "projects.list": lst, "projects.use": use, "ideas.doc": doc}
    monkeypatch.setattr(Stub, "commands", commands)
    return state


@pytest.mark.asyncio
async def test_the_switcher_is_a_drawer_with_the_open_projects_and_a_tap_shows_another(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        chip = page.locator(".project-chip")
        await chip.wait_for(timeout=WAIT_MS)
        await chip.click()
        sheet = page.get_by_role("dialog", name="Projects")
        await sheet.wait_for(timeout=WAIT_MS)
        await sheet.get_by_text("2 working · 1 needs you").wait_for(timeout=WAIT_MS)
        text = await sheet.inner_text()
        assert "3 to review" in text and "old" in text and "Open a folder" not in text
        assert "opened and closed at the computer" in text
        box = await sheet.bounding_box()
        assert box["x"] == 0 and box["y"] == 0 and box["height"] == 844 and box["width"] < 390       # a drawer from the left
        assert "Shown now" in await sheet.locator('[aria-current="true"]').inner_text()
        assert await sheet.get_by_role("button", name="old").count() == 0                   # a recent one is not opened from the phone
        await _shot(page, "phone-projects-390x844")
        await sheet.get_by_role("button", name="beta").click()
        assert await _called(stub, "projects.use", {"path": "/work/beta"})
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_linked_spec_opens_read_only_rendered_with_no_edit_or_git_control(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["ship"] = stub.goal("ship", "Ship v1", "high", "ready", links=[SPEC])
        stub.bump({})
        await page.locator(".map-goal, .goal-pick").first.wait_for(timeout=WAIT_MS)
        await _pick_goal(page, "ship")
        await page.locator('.map-goal[data-goal="ship"]').get_by_role("button", name="Open goal Ship v1").click()
        await page.locator(".screen").get_by_role("button", name=SPEC).click()
        doc = page.locator(".screen .md.doc")
        await doc.wait_for(timeout=WAIT_MS)
        assert await doc.locator("h1").inner_text() == "Board and line" and await doc.locator("strong").inner_text() == "phone"
        screen = page.locator(".screen")
        assert await screen.locator("textarea, input, [contenteditable]").count() == 0
        names = [(await b.inner_text()).lower() for b in await screen.get_by_role("button").all()]
        assert not [n for n in names if any(w in n for w in ("edit", "save", "commit", "push", "pull", "switch"))]
        await _shot(page, "phone-spec-390x844")
        assert await page.evaluate(NO_SCROLL)
