"""New goal in three steps on the phone (shell-goal-new.js): its craft, its team from the library (the host's, realm/library.py),
what it is for. The Board is the stub's (tests/test_pwa_shell_browser.py)."""
from __future__ import annotations

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _new_goal, _phone, _pick_goal, _shot  # noqa: F401

pytestmark = pytest.mark.browser


@pytest.mark.asyncio
async def test_new_goal_picks_a_craft_then_its_party_in_three_bands_then_what_it_is_for(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        tiles = sheet.locator(".craft-tile")
        assert await tiles.count() == 6                                                                  # five crafts and Mixed
        await _shot(page, "phone-goal-1-craft-390x844")
        await sheet.locator('.craft-tile[data-craft="design"]').click()                                  # 2. the party: the craft's in its bands
        leads, builds, checks = (sheet.get_by_role("region", name=n) for n in ("Leads", "Builds", "Checks"))
        await leads.locator(".team-row").first.wait_for(timeout=WAIT_MS)
        assert await leads.locator('.team-row[aria-pressed="true"]').get_attribute("data-agent") == "product-designer"
        assert [await r.get_attribute("data-agent") for r in await builds.locator('.team-row[aria-pressed="true"]').all()] == ["ui-kit", "artist"]
        assert await checks.locator(".team-seat:not(.is-empty)").count() == 1 and await checks.locator(".team-seat").count() == 2
        await sheet.get_by_role("button", name="Take in: Copywriter").click()                           # the third builder
        await sheet.get_by_role("button", name="Take in: Grunt").click()                                # a fourth: no seat
        assert await builds.locator(".team-seat:not(.is-empty)").count() == 3
        assert "Builds has 3 seats" in await page.locator(".flash").last.inner_text()
        await sheet.get_by_role("button", name="Take out: Artist").click()
        await sheet.get_by_role("button", name="Take in: Analyst").click()                              # the leader changes
        assert await leads.locator('.team-row[aria-pressed="true"]').get_attribute("data-agent") == "analyst"
        await _shot(page, "phone-goal-2-team-390x844")
        await sheet.get_by_role("button", name="Next").click()                                           # 3. what it is for
        assert "led by Analyst" in await sheet.inner_text()
        await sheet.get_by_label("Description").fill("A landing page that says what Orkline does in one screen.")
        await _shot(page, "phone-goal-3-what-390x844")
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save", {"about": "A landing page that says what Orkline does in one screen.", "craft": "design",
                                                       "leader": "analyst", "team": ["ui-kit", "accessibility-reviewer", "copywriter"],
                                                       "every": [], "priority": "normal"})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_mixed_goal_starts_with_the_taskmaster_alone_and_is_its_party_s_most(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        await sheet.locator('.craft-tile[data-craft="mixed"]').click()
        leads = sheet.get_by_role("region", name="Leads")
        await leads.locator(".team-row").first.wait_for(timeout=WAIT_MS)
        assert await leads.locator('.team-row[aria-pressed="true"]').get_attribute("data-agent") == "taskmaster"
        assert await sheet.locator('.team-row[aria-pressed="true"]').count() == 1                       # the Taskmaster alone
        for name in ("Grunt", "Copywriter", "SEO"):
            await sheet.get_by_role("button", name=f"Take in: {name}").click()
        await _shot(page, "phone-goal-2-mixed-390x844")
        await sheet.get_by_role("button", name="Next").click()
        assert "Mixed, mostly Marketing" in await sheet.inner_text()
        await sheet.get_by_label("Description").fill("Launch the beta: the build and its page.")
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save", {"about": "Launch the beta: the build and its page.", "craft": "marketing",
                                                       "leader": "taskmaster", "team": ["grunt", "copywriter", "seo"], "every": [], "priority": "normal"})


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
        chip, card = page.locator(".board-bar .goal-chip"), page.locator('.map-goal[data-goal="land"]')
        await card.locator(".map-team .team-mark-heads img").nth(2).wait_for(timeout=WAIT_MS)
        assert [await i.get_attribute("src") for i in await card.locator(".map-team .team-mark-heads img").all()] == [
            "races/elf-elder.png", "races/elf-warrior.png", "races/goblin-warrior.png"]
        assert await chip.locator("img").get_attribute("src") == "races/elf-laborer.png"                # the bar: the craft's one head
        assert "Team: Product designer, Accessibility reviewer, Analyst" in await card.locator(".map-team").inner_text()
        await _shot(page, "phone-goal-team-board-390x844")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_team_s_checkers_say_what_they_add_every_idea_is_kept_and_the_spec_says_each_check(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        await sheet.locator('.craft-tile[data-craft="design"]').click()
        await sheet.get_by_role("button", name="Take in: Reviewer").click()                             # the second checker
        await sheet.get_by_role("button", name="Next").click()
        block = sheet.get_by_role("group", name="Checks")
        text = await block.inner_text()
        assert "Accessibility reviewer" in text and "Reviewer" in text and "Product designer" not in text   # checkers only
        assert "applies when the idea changes what people see or use" in text and "≈ $1.30 an idea they all apply to" in text   # a seasoned and a veteran check
        await block.get_by_label("Every idea: Reviewer").check()
        await sheet.get_by_label("Description").fill("A settings screen.")
        await _shot(page, "phone-goal-3-checks-390x844")
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save", {"about": "A settings screen.", "craft": "design", "leader": "product-designer",
                                                       "team": ["ui-kit", "artist", "accessibility-reviewer", "reviewer"],
                                                       "every": ["reviewer"], "priority": "normal"})
        stub.checks = [{"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": True, "why": "", "state": "passed"},
                       {"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "review"},
                       {"by": "seo", "name": "SEO", "applies": False, "why": "It adds no public page", "state": ""}]
        await page.locator(".screen-head").get_by_role("button", name="Back").click()                  # from the new goal's screen
        await _pick_goal(page, "general")
        await page.locator(".map-row", has_text="Sync ideas").locator(".map-open").click()
        line = page.locator(".screen").get_by_role("list", name="Checks")
        await line.wait_for(timeout=WAIT_MS)
        chips = [" ".join(t.split()) for t in await line.get_by_role("listitem").all_inner_texts()]
        assert chips == ["Accessibility reviewer passed", "Reviewer at Review", "SEO not needed: It adds no public page"]
        await _shot(page, "phone-spec-checks-390x844")


@pytest.mark.asyncio
async def test_a_goal_whose_ideas_are_done_is_accepted_by_its_leader_against_its_metrics(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="marketing", race="gnome", team=["copywriter"],
                                       leader=stub.leader("growth"), metrics=[{"name": "weekly installs", "target": "50", "how": "npm"}])
        stub.ideas["page"] = stub.idea("page", "The landing page", "done", 2, track="land")
        stub.bump({})
        await _pick_goal(page, "land")
        assert await page.locator(".board-bar .goal-chip img").get_attribute("src") == "races/gnome-elder.png"   # the goal's head: its leader's
        await page.locator('.map-goal[data-goal="land"]').get_by_role("button", name="Open goal Landing page").click()
        verdict = page.locator(".screen").get_by_role("region", name="Verdict")
        await verdict.get_by_role("button", name="Ask Growth to accept").click()
        assert await _called(stub, "ideas.goal_accept", {"slug": "land"})
        stub.goals["land"].update(busy=False, verdict={"met": False, "by": "Growth", "verdict": "Installs are at 30 a week, not 50.",
                                                        "metrics": [{"name": "weekly installs", "status": "not met", "why": "30 a week on npm"}],
                                                        "next": ["A post on the forum"]})
        stub.bump({})
        await verdict.get_by_text("Not met yet").wait_for(timeout=WAIT_MS)
        text = await verdict.inner_text()
        assert "by Growth" in text and "30 a week on npm" in text and "weekly installs · not met" in text
        await _shot(page, "phone-goal-verdict-390x844")
        await verdict.get_by_role("button", name="Add as idea: A post on the forum").click()
        assert await _called(stub, "ideas.add", {"text": "A post on the forum", "track": "land", "priority": "normal"})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_check_that_has_not_run_is_skipped_from_the_spec_to_spare_its_run(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.checks = [{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "waiting", "task": "k5", "skipped": False, "tier": "elder"},
                       {"by": "editor", "name": "Editor", "applies": True, "why": "", "state": "passed", "task": "k6", "skipped": False, "tier": "laborer"}]
        stub.bump({})
        await page.locator(".map-row", has_text="Sync ideas").locator(".map-open").click()
        line = page.locator(".screen").get_by_role("list", name="Checks")
        await line.wait_for(timeout=WAIT_MS)
        assert await line.get_by_role("button", name="Skip the check: Editor").count() == 0           # passed: nothing to spare
        skip = line.get_by_role("button", name="Skip the check: Reviewer")
        assert "spares ≈ $" in await skip.inner_text()                                                 # what it spares, in dollars
        await _shot(page, "phone-check-skip-390x844")
        await skip.click()
        assert await _called(stub, "ideas.check_skip", {"slug": "sync", "by": "reviewer"})
        await line.get_by_text("skipped by you").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)
