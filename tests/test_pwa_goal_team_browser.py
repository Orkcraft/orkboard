"""New goal in three steps on the phone (shell-goal-new.js, a mock of the team's flow): its craft, its team from the library,
what it is for. The Board is the stub's (tests/test_pwa_shell_browser.py)."""
from __future__ import annotations

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _new_goal, _phone, _shot  # noqa: F401

pytestmark = pytest.mark.browser


@pytest.mark.asyncio
async def test_new_goal_picks_a_craft_then_its_team_from_the_library_then_what_it_is_for(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        tiles = sheet.locator(".craft-tile")
        assert await tiles.count() == 5                                                                  # four crafts and Mixed
        await _shot(page, "phone-goal-1-craft-390x844")
        await sheet.locator('.craft-tile[data-craft="design"]').click()                                  # 2. the team: the craft's agents in it
        rows = sheet.locator(".team-row")
        await rows.first.wait_for(timeout=WAIT_MS)
        assert [await r.get_attribute("aria-pressed") for r in await rows.all()] == ["true", "true"]
        assert await sheet.locator(".team-seat:not(.is-empty):not(.is-keeper)").count() == 2
        await sheet.get_by_role("button", name="+ From the library: the other crafts' agents").click()
        await sheet.get_by_role("button", name="Take in: Analyst").click()
        await sheet.get_by_role("button", name="Take out: UX writer").click()
        assert await sheet.locator(".team-seat:not(.is-empty):not(.is-keeper)").count() == 2
        await _shot(page, "phone-goal-2-team-390x844")
        await sheet.get_by_role("button", name="Next").click()                                           # 3. what it is for
        await sheet.get_by_label("Description").fill("A landing page that says what Orkline does in one screen.")
        await _shot(page, "phone-goal-3-what-390x844")
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save", {"about": "A landing page that says what Orkline does in one screen.", "craft": "design",
                                                       "team": ["ui-designer", "analyst"], "priority": "normal"})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_mixed_goal_starts_empty_with_the_whole_library_by_craft_and_is_its_team_s_most(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        await sheet.locator('.craft-tile[data-craft="mixed"]').click()
        await sheet.locator(".team-craft").first.wait_for(timeout=WAIT_MS)
        assert [t.lower() for t in await sheet.locator(".team-craft").all_inner_texts()] == ["engineering", "design", "data", "marketing"]
        assert await sheet.locator('.team-row[aria-pressed="true"]').count() == 0                       # none taken: each is picked
        assert await sheet.get_by_role("button", name="Next").is_disabled()
        for name in ("Grunt", "Copywriter", "SEO"):
            await sheet.get_by_role("button", name=f"Take in: {name}").click()
        await _shot(page, "phone-goal-2-mixed-390x844")
        await sheet.get_by_role("button", name="Next").click()
        assert "Mixed, mostly Marketing" in await sheet.inner_text()
        await sheet.get_by_label("Description").fill("Launch the beta: the build and its page.")
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save", {"about": "Launch the beta: the build and its page.", "craft": "marketing",
                                                       "team": ["grunt", "copywriter", "seo"], "priority": "normal"})
