"""Spec 42 A on the phone (docs/specs/42-coming-back.md §1.3–§1.4, Tests → A): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py with a fake `ideas.recap`. A last look 9 hours old gets the card at the top of the Board tab with its
lines in order; 2 hours old, none; no last look, none and the key written; Close removes it; a tap on an idea opens its screen,
logged `via: "recap"`; *Waits for you* opens Needs you; no horizontal scroll."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _phone  # noqa: E402,F401

RECAP = {"since": "2026-10-20T03:00:00+00:00", "hours": 9, "into": "dev",
         "merged": {"tasks": 5, "first_time": 4, "ideas": [
             {"slug": "sync", "short": "Sync ideas", "title": "Sync ideas between the phone and the town", "goal": "general", "done": True},
             {"slug": "dark", "short": "Dark mode", "title": "Dark mode", "goal": "general", "done": False}]},
         "flags": [{"goal": "general", "short": "General", "title": "General", "met": True, "by": "Product manager"}],
         "night": {"drafted": 2, "started": 1, "refreshed": 0, "proposed": 2},
         "proposed": [{"slug": "dark", "short": "Dark mode", "title": "Dark mode", "goal": "general"}],
         "failed": [{"slug": "sync", "short": "Sync ideas", "title": "Sync ideas between the phone and the town", "task": "The table"}],
         "usd": 4.2, "nights": 0, "waits": {"you": 1, "review": 3}, "empty": False}
ANSWER: dict = {}


@pytest.fixture(autouse=True)
def _recap(monkeypatch):
    ANSWER.clear()
    ANSWER.update(RECAP)
    real = Stub.commands

    def commands(self):
        def fake(a):
            self.calls.append(("ideas.recap", {"since": a.get("since")}))
            return dict(ANSWER)
        return {**real(self), "ideas.recap": fake}
    monkeypatch.setattr(Stub, "commands", commands)


def seed(repo, hours_ago):
    """The last look this phone kept, written once (a reload keeps what the page wrote)."""
    if hours_ago is None:
        return ""
    key = json.dumps(f"orkboard.look.{repo.name}")
    return f"if (!localStorage.getItem({key})) localStorage.setItem({key}, String(Date.now() - {hours_ago} * 3600 * 1000));"


def _lines(card):
    return card.locator(".away-lines p")


@pytest.mark.asyncio
async def test_a_last_look_nine_hours_old_shows_the_card_at_the_top_of_the_board_tab(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=seed(fake_repo, 9)) as (stub, page):
        card = page.get_by_label("While you were away")
        await card.wait_for(timeout=WAIT_MS)
        assert " ".join((await card.locator(".away-head h3").text_content()).split()) == "While you were away · 9 h"
        assert [" ".join(t.split()) for t in await _lines(card).all_text_contents()] == [
            "5 results in dev, 4 the first time", "Sync ideas · done, Dark mode", "Flag raised: General, met, says Product manager",
            "The night: drafted 2 ideas, started 1 plan, proposed 2 ideas", "Proposed for you: Dark mode", "Failed: Sync ideas · The table",
            "≈$4.20 of work at API prices, not your bill.", "Waits for you: 1 answer, 3 results to check"]
        assert await page.locator(".board-tab-pane > *").first.get_attribute("aria-label") == "While you were away"      # above the Map
        assert await card.get_by_role("button", name="Close").get_attribute("class") == "ork-btn quiet"
        assert await _called(stub, "ideas.recap")
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "recap", "ref": "9h", "device": "phone"})
        assert await page.evaluate(NO_SCROLL)
        assert (await card.bounding_box())["width"] <= 390


@pytest.mark.asyncio
async def test_two_hours_is_not_away_and_no_last_look_is_written_and_shows_nothing(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=seed(fake_repo, 2)) as (stub, page):
        await page.wait_for_timeout(500)
        assert await page.get_by_label("While you were away").count() == 0
        assert not any(c[0] == "ideas.recap" for c in stub.calls)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.wait_for_function(f"localStorage.getItem({json.dumps('orkboard.look.' + fake_repo.name)}) !== null", timeout=WAIT_MS)
        assert await page.get_by_label("While you were away").count() == 0
        assert not any(c[0] == "ideas.recap" for c in stub.calls)


@pytest.mark.asyncio
async def test_close_removes_the_card_and_it_is_not_shown_again(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=seed(fake_repo, 9)) as (stub, page):
        card = page.get_by_label("While you were away")
        await card.wait_for(timeout=WAIT_MS)
        await card.get_by_role("button", name="Close").click()
        assert await card.count() == 0
        await page.reload()
        await page.locator(".board-tab-pane").wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(500)
        assert await card.count() == 0 and len([c for c in stub.calls if c[0] == "ideas.recap"]) == 1


@pytest.mark.asyncio
async def test_a_tap_on_an_idea_opens_it_and_waits_for_you_opens_needs_you(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=seed(fake_repo, 9)) as (stub, page):
        card = page.get_by_label("While you were away")
        await card.wait_for(timeout=WAIT_MS)
        await card.get_by_role("button", name="Dark mode").first.click()
        await page.locator(".screen .sec").first.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "idea", "ref": "dark", "device": "phone", "via": "recap"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await card.get_by_role("button", name="Waits for you: 1 answer, 3 results to check").click()
        assert await page.locator(".needs-pane").is_visible() and not await page.locator(".board-tab-pane").is_visible()
