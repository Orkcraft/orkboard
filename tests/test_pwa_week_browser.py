"""Spec 42 F on the phone (docs/specs/42-coming-back.md §6, Tests → F): the drawer's *Spend today* row opens the This week sheet with its
lines in order; *Nothing waits for tonight* and New idea."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _menu, _phone  # noqa: E402,F401

WEEK = {"usd": 46.1, "ops_usd": 3.2, "merged": 12, "first_time": 10, "usd_per_merged": 3.84, "nights": {"worked": 4, "idle": 2, "off": 1},
        "tonight": 0, "night_on": True, "into": "dev"}
ANSWER: dict = {}


@pytest.fixture(autouse=True)
def _week(monkeypatch):
    ANSWER.clear()
    ANSWER.update(WEEK)
    real = Stub.commands

    def commands(self):
        def fake(a):
            self.calls.append(("ideas.week_work", {}))
            return dict(ANSWER)
        return {**real(self), "ideas.week_work": fake}
    monkeypatch.setattr(Stub, "commands", commands)


async def _sheet(page):
    drawer = await _menu(page)
    row = drawer.locator(".board-spend__open")
    assert (await row.get_attribute("aria-label")).startswith("Spend today: $") and (await row.get_attribute("aria-label")).endswith(". This week’s work")
    await row.click()
    sheet = page.get_by_role("dialog", name="This week")
    await sheet.locator(".week p").first.wait_for(timeout=WAIT_MS)
    return sheet


@pytest.mark.asyncio
async def test_the_spend_row_opens_this_week_with_its_lines_in_order_and_new_idea(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["ship"] = stub.goal("ship", "Ship v1", "normal", "ready")                       # New idea needs a goal (spec 35 §3)
        reads = len([c for c in stub.calls if c[0] == "ideas.board"])
        stub.bump({})
        for _ in range(100):                                                                         # the Board reads its goals again
            if len([c for c in stub.calls if c[0] == "ideas.board"]) > reads:
                break
            await page.wait_for_timeout(100)
        await page.wait_for_timeout(600)
        sheet = await _sheet(page)
        lines = [" ".join(t.split()) for t in await sheet.locator(".week p").all_text_contents()]
        assert lines == ["≈$46 of work at API prices in this project, ≈$3 in Operations: not your bill",
                         "12 results in dev, 10 the first time · ≈$3.84 a result",
                         "The last 7 nights: 4 with work done, 2 with none, 1 Orkline was not running", "Nothing waits for tonight · New idea"]
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "week", "ref": "this", "device": "phone"})
        assert await page.evaluate(NO_SCROLL)
        await sheet.get_by_role("button", name="New idea").click()
        await page.get_by_role("dialog", name="New idea").wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_tonight_says_how_many_wait(fake_repo, monkeypatch):
    ANSWER.update(tonight=3, ops_usd=None)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _sheet(page)
        lines = [" ".join(t.split()) for t in await sheet.locator(".week p").all_text_contents()]
        assert lines[0] == "≈$46 of work at API prices in this project: not your bill" and lines[-1] == "Tonight: 3 wait"
