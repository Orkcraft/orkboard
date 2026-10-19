"""New goal in three steps on the phone (shell-goal-new.js): its craft, its team from the library (the host's, realm/library.py),
what it is for. The Board is the stub's (tests/test_pwa_shell_browser.py)."""
from __future__ import annotations

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _new_goal, _phone, _pick_goal, _shot  # noqa: F401

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
        assert [await r.get_attribute("aria-pressed") for r in await rows.all()] == ["true", "true", "false", "false"]   # four of the craft, two in
        assert await sheet.locator(".team-seat:not(.is-empty):not(.is-keeper)").count() == 2
        await sheet.get_by_role("button", name="+ From the library: the other crafts' agents").click()
        await sheet.get_by_role("button", name="Take in: Analyst").click()
        await sheet.get_by_role("button", name="Take out: Design system designer").click()
        await sheet.get_by_role("button", name="Take in: Accessibility reviewer").click()
        assert await sheet.locator(".team-seat:not(.is-empty):not(.is-keeper)").count() == 3
        await sheet.locator(".team-seats").scroll_into_view_if_needed()
        await _shot(page, "phone-goal-2-team-390x844")
        await sheet.get_by_role("button", name="Next").click()                                           # 3. what it is for
        await sheet.get_by_label("Description").fill("A landing page that says what Orkline does in one screen.")
        await _shot(page, "phone-goal-3-what-390x844")
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save", {"about": "A landing page that says what Orkline does in one screen.", "craft": "design",
                                                       "team": ["product-designer", "analyst", "accessibility-reviewer"], "every": [], "priority": "normal"})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_mixed_goal_starts_empty_with_the_whole_library_by_craft_and_is_its_team_s_most(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        await sheet.locator('.craft-tile[data-craft="mixed"]').click()
        await sheet.locator(".team-craft").first.wait_for(timeout=WAIT_MS)
        assert [t.lower() for t in await sheet.locator(".team-craft").all_inner_texts()] == ["engineering", "design", "data", "marketing"]
        assert await sheet.locator(".team-row").count() == 19                                            # the whole library
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
                                                       "team": ["grunt", "copywriter", "seo"], "every": [], "priority": "normal"})


@pytest.mark.asyncio
async def test_the_goal_s_card_wears_its_team_s_heads_and_names_them_and_the_top_bar_its_craft_s_head(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        from orkboard.realm import library
        for a in (library.get("product-designer"), library.get("accessibility-reviewer"), library.get("analyst")):
            race = {"design": "elf", "data": "goblin"}[a.craft]
            stub.roles[a.id] = {"slug": a.id, "name": a.name, "model": a.tier, "max_parallel": 2, "instruction": a.instruction,
                                "builtin": False, "craft": a.craft, "head": {"craft": a.craft, "race": race, "tier": a.tier}}
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="design", race="elf",
                                       team=["product-designer", "accessibility-reviewer", "analyst"])
        stub.bump({})
        await page.locator(".board-bar .goal-chip").click()
        await page.get_by_role("dialog", name="Goals").locator('.goal-row[data-goal="land"]').click()
        chip, card = page.locator(".board-bar .goal-chip"), page.locator(".goal-now")
        await card.locator(".team-mark-heads img").nth(2).wait_for(timeout=WAIT_MS)
        assert [await i.get_attribute("src") for i in await card.locator(".team-mark-heads img").all()] == [
            "races/elf-elder.png", "races/elf-warrior.png", "races/goblin-warrior.png"]
        assert await chip.locator("img").get_attribute("src") == "races/elf-laborer.png"                # the bar: the craft's one head
        assert "Team: Product designer, Accessibility reviewer, Analyst" in await page.locator(".goal-now").inner_text()
        await _shot(page, "phone-goal-team-board-390x844")
        await page.locator(".idea-card").first.wait_for(state="attached", timeout=WAIT_MS) if await page.locator(".idea-card").count() else None
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_team_s_checkers_say_what_they_add_every_idea_is_kept_and_the_spec_says_each_check(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        await sheet.locator('.craft-tile[data-craft="design"]').click()
        assert "checks" in (await sheet.get_by_role("button", name="Take in: Accessibility reviewer").inner_text()).lower()   # a checker says so
        await sheet.get_by_role("button", name="Take out: Design system designer").click()
        await sheet.get_by_role("button", name="Take in: Accessibility reviewer").click()
        await sheet.get_by_role("button", name="+ From the library: the other crafts' agents").click()
        await sheet.get_by_role("button", name="Take in: Reviewer").click()
        await sheet.get_by_role("button", name="Next").click()
        block = sheet.get_by_role("group", name="Checks")
        text = await block.inner_text()
        assert "Accessibility reviewer" in text and "Reviewer" in text and "Product designer" not in text   # checkers only
        assert "applies when the idea changes what people see or use" in text and "≈ $1.30 an idea they all apply to" in text   # a seasoned and a veteran check
        await block.get_by_label("Every idea: Reviewer").check()
        await sheet.get_by_label("Description").fill("A settings screen.")
        await _shot(page, "phone-goal-3-checks-390x844")
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save", {"about": "A settings screen.", "craft": "design",
                                                       "team": ["product-designer", "accessibility-reviewer", "reviewer"],
                                                       "every": ["reviewer"], "priority": "normal"})
        stub.checks = [{"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": True, "why": "", "state": "passed"},
                       {"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "review"},
                       {"by": "seo", "name": "SEO", "applies": False, "why": "It adds no public page", "state": ""}]
        await page.locator(".screen-head").get_by_role("button", name="Back").click()                  # from the new goal's screen
        await _pick_goal(page, "general")
        await page.locator(".idea-card", has_text="Sync ideas").locator(".idea-open").click()
        line = page.locator(".screen").get_by_role("list", name="Checks")
        await line.wait_for(timeout=WAIT_MS)
        chips = [" ".join(t.split()) for t in await line.get_by_role("listitem").all_inner_texts()]
        assert chips == ["Accessibility reviewer passed", "Reviewer at Review", "SEO not needed: It adds no public page"]
        await _shot(page, "phone-spec-checks-390x844")
