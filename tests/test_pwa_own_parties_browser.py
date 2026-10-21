"""Spec 43 F on the phone (docs/specs/43-party-measured.md §6.3, Tests → F): *Save this party* on a goal's screen (the name, the replace);
*Your parties* in New goal and a goal's Team fill the seats and the craft; a seat changed afterwards drops the id; Remove asks first."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from tests.test_pwa_goal_team_browser import _pick_goal  # noqa: E402,F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _new_goal, _phone  # noqa: E402,F401

LEAN = {"id": "p-1a2b3c4d", "name": "Lean web", "craft": "engineering", "leader": "architect", "team": ["grunt", "tester", "reviewer"], "every": ["reviewer"],
        "own": [], "goals": 3, "projects": 2, "met": 2, "saved": "2026-10-20T10:00:00"}
FRESH = {**LEAN, "id": "p-5e6f7a8b", "name": "Fresh", "craft": "design", "leader": "product-designer", "team": ["ui-kit"], "every": [], "goals": 0, "projects": 0, "met": 0}


@pytest.mark.asyncio
async def test_your_parties_fill_the_seats_and_the_craft_and_a_seat_changed_afterwards_drops_the_id(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.own = [dict(LEAN), dict(FRESH)]
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        row = sheet.get_by_role("region", name="Your parties")
        chip = row.locator("[data-party=p-1a2b3c4d]")
        await chip.wait_for(timeout=WAIT_MS)
        assert " ".join((await chip.inner_text()).split()) == "Lean web 3 goals in 2 projects · 2 met" and await chip.locator("img").count() == 4
        assert " ".join((await row.locator("[data-party=p-5e6f7a8b]").inner_text()).split()) == "Fresh"              # not used yet: nothing muted
        await chip.get_by_role("button", name="Pick your party “Lean web”").click()
        assert await sheet.locator(".craft-tile[aria-pressed='true']").get_attribute("data-craft") == "engineering"
        assert await sheet.locator(".party-line").first.inner_text() == "Leads: Architect · Builds: Grunt, Tester · Checks: Reviewer"
        await sheet.get_by_label("Description").fill("A goal from your party.")
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save", {"about": "A goal from your party.", "craft": "engineering", "leader": "architect", "team": ["grunt", "tester", "reviewer"],
                                                       "every": ["reviewer"], "priority": "normal", "party": "p-1a2b3c4d"})
        stub.own = [dict(LEAN)]
        await page.locator(".screen-head").get_by_role("button", name="Back").click()                                    # from the new goal's screen
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        await sheet.get_by_role("region", name="Your parties").get_by_role("button", name="Pick your party “Lean web”").click()
        await sheet.locator('.party [data-change="team"]').click()
        await sheet.get_by_role("region", name="Builds").get_by_role("button").first.click()
        await sheet.get_by_role("button", name="Take out: Tester").click()                                              # a seat changed afterwards
        await sheet.get_by_label("Description").fill("A changed party.")
        await sheet.get_by_role("button", name="Save goal").click()
        saves = [c[1] for c in stub.calls if c[0] == "ideas.goal_save"]
        for _ in range(100):
            if len(saves) > 1:
                break
            await page.wait_for_timeout(100)
            saves = [c[1] for c in stub.calls if c[0] == "ideas.goal_save"]
        assert "party" not in saves[1] and "tester" not in saves[1]["team"]
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_remove_asks_first_and_the_goals_that_use_it_keep_their_agents(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.own = [dict(LEAN)]
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        row = sheet.get_by_role("region", name="Your parties")
        await row.get_by_role("button", name="Remove your party “Lean web”").click()
        await row.get_by_text("Remove your party “Lean web”? Goals that use it keep their agents.").wait_for(timeout=WAIT_MS)
        assert not any(c[0] == "ideas.party_drop" for c in stub.calls)                                                  # asked, not dropped
        await row.get_by_role("button", name="Keep it").click()
        assert await row.locator("[data-party=p-1a2b3c4d]").count() == 1
        await row.get_by_role("button", name="Remove your party “Lean web”").click()
        await row.get_by_role("button", name="Remove it").click()
        assert await _called(stub, "ideas.party_drop", {"id": "p-1a2b3c4d"})
        await row.wait_for(state="detached", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_save_this_party_on_a_goal_s_screen_asks_a_name_and_asks_again_before_it_replaces(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.own = [dict(LEAN)]
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="design", race="elf", team=["ui-kit"], leader=stub.leader("product-designer"), metrics=[])
        stub.ideas["page"] = stub.idea("page", "The landing page", "plan", 2, track="land")
        stub.bump({})
        await _pick_goal(page, "land")
        await page.locator(".ghead").get_by_role("button", name="Open goal Landing page").click()
        team = page.locator(".screen").get_by_role("region", name="Team")
        await team.get_by_role("button", name="Save this party").click()
        name = team.get_by_label("Name of your party")
        assert await name.input_value() == "Design party"
        await name.fill("Brand new")
        await team.get_by_role("button", name="Save", exact=True).click()
        assert await _called(stub, "ideas.party_save", {"goal": "land", "name": "Brand new"})
        await page.get_by_text("Saved: pick it for a goal in any project.").wait_for(timeout=WAIT_MS)
        await team.get_by_role("button", name="Save this party").click()
        await team.get_by_label("Name of your party").fill("lean  WEB")
        await team.get_by_role("button", name="Save", exact=True).click()
        await team.get_by_text("Replace your party “Lean web”?").wait_for(timeout=WAIT_MS)
        assert not any(c[0] == "ideas.party_save" and c[1].get("name") == "lean WEB" for c in stub.calls)             # asked first
        await team.get_by_role("button", name="Replace it").click()
        assert await _called(stub, "ideas.party_save", {"goal": "land", "name": "lean WEB", "replace": True})


@pytest.mark.asyncio
async def test_a_goal_s_team_picks_a_party_and_says_what_it_kept(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.own = [dict(LEAN)]
        stub.goal_notes = ["Docs scribe is this project's already: kept as it is"]
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="design", race="elf", team=["ui-kit"], leader=stub.leader("product-designer"), metrics=[])
        stub.ideas["page"] = stub.idea("page", "The landing page", "plan", 2, track="land")
        stub.bump({})
        await _pick_goal(page, "land")
        await page.locator(".ghead").get_by_role("button", name="Open goal Landing page").click()
        await page.locator(".screen").get_by_role("button", name="Change the team").click()
        sheet = page.get_by_role("dialog", name="Team")
        await sheet.get_by_role("region", name="Your parties").get_by_role("button", name="Pick your party “Lean web”").click()
        await sheet.get_by_role("button", name="Save team").click()
        assert await _called(stub, "ideas.goal_save", {"slug": "land", "team": ["grunt", "tester", "reviewer"], "every": ["reviewer"], "leader": "architect", "party": "p-1a2b3c4d"})
        await page.get_by_text("Docs scribe is this project's already: kept as it is").wait_for(timeout=WAIT_MS)
