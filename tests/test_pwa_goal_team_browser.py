"""New party on one sheet on the phone (shell-goal-new.js, spec 41 §6, spec 50 §0): what it is for, its craft in one row of heads, its members from the
library (the host's, realm/library.py) in three folds, its checks; a party's members changed from its own screen (§7), which About this party opens. The Board is the stub's
(tests/test_pwa_shell_browser.py)."""
from __future__ import annotations

import pytest

from orkboard.realm import library  # noqa: E402
from tests.test_pwa_shell_browser import _band, _item, _open_idea_of, _open_party, NO_SCROLL, WAIT_MS, _called, _new_goal, _phone, _pick_goal, _pop, _shot  # noqa: F401
from playwright.async_api import expect  # noqa: E402  (the shell tests above skip the file when playwright is not there)

pytestmark = pytest.mark.browser


@pytest.mark.asyncio
async def test_new_goal_is_one_sheet_a_craft_in_one_row_its_team_in_three_folds_and_save_in_sight(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New party")
        tiles = sheet.locator(".craft-tile")
        assert await tiles.count() == 6                                                                  # five crafts and Mixed, one row
        ys = {round((await t.bounding_box())["y"]) for t in await tiles.all()}
        assert len(ys) == 1 and await sheet.get_by_label("What it is for").evaluate("e => document.activeElement === e")   # one row; the description focused
        assert [await t.get_attribute("aria-label") for t in await tiles.all()] == ["Engineering", "Design", "Data", "Marketing", "Product", "Mixed"]
        save = sheet.get_by_role("button", name="Save party")
        assert await save.is_disabled()                                                                  # enabled once the description has words
        foot = await sheet.locator(".sheet-foot").bounding_box()
        assert foot["y"] + foot["height"] >= 844 - 2 and await sheet.get_by_role("button", name="Next").count() == 0   # pinned at the foot, no steps
        await sheet.locator('.craft-tile[data-craft="product"]').click()
        assert "Product: who it is for, what it moves, what it leaves out" in await sheet.locator(".craft-line").inner_text()
        await sheet.locator('.craft-tile[data-craft="design"]').click()
        line = sheet.locator(".party-line").first
        assert await line.inner_text() == "Leads: Product designer · Builds: Design system designer, Artist · Checks: Accessibility reviewer"   # folded to one line
        assert "null" not in await sheet.inner_text()                                                    # no saved party of yours: no row, and no word in its place
        await _shot(page, "phone-goal-new-390x844")
        await sheet.locator('.party [data-change="team"]').click()                                      # Change: the folds, Leads open
        leads, builds, checks = (sheet.get_by_role("region", name=n) for n in ("Leads", "Builds", "Checks"))
        await leads.locator(".team-row").first.wait_for(timeout=WAIT_MS)
        assert await builds.locator(".team-row").count() == 0 and await checks.locator(".team-row").count() == 0      # one open at a time
        assert await leads.locator('.team-row[aria-pressed="true"]').get_attribute("data-agent") == "product-designer"
        await sheet.get_by_role("button", name="Take in: Analyst").click()                              # a lead's pick folds Leads and opens Builds
        await builds.locator(".team-row").first.wait_for(timeout=WAIT_MS)
        assert await leads.locator(".team-row").count() == 0 and "Analyst" in await leads.inner_text()
        assert [await r.get_attribute("data-agent") for r in await builds.locator('.team-row[aria-pressed="true"]').all()] == ["ui-kit", "artist"]
        await sheet.get_by_role("button", name="Take in: Copywriter").click()                           # the third builder
        await sheet.get_by_role("button", name="Take in: Grunt").click()                                # a fourth: no seat
        assert await builds.locator(".team-seat:not(.is-empty)").count() == 3
        assert "Builds has 3 seats" in await page.locator(".flash").last.inner_text()
        await sheet.get_by_role("button", name="Take out: Artist").click()
        await _shot(page, "phone-goal-team-folds-390x844")
        await builds.get_by_role("button", name="Done").click()                                         # Done: every fold closed, back to the line
        assert await line.inner_text() == "Leads: Analyst · Builds: Design system designer, Copywriter · Checks: Accessibility reviewer"
        await sheet.get_by_label("What it is for").fill("A landing page that says what Orkline does in one screen.")
        await save.click()
        assert await _called(stub, "ideas.goal_save", {"about": "A landing page that says what Orkline does in one screen.", "craft": "design",
                                                       "leader": "analyst", "team": ["ui-kit", "accessibility-reviewer", "copywriter"],
                                                       "every": [], "priority": "normal"})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_mixed_goal_starts_with_the_taskmaster_alone_and_is_its_party_s_most(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New party")
        await sheet.locator('.craft-tile[data-craft="mixed"]').click()
        assert await sheet.locator(".party-line").first.inner_text() == "Leads: Taskmaster · Builds: none · Checks: none"
        await sheet.locator('.party [data-change="team"]').click()
        builds = sheet.get_by_role("region", name="Builds")
        await sheet.get_by_role("region", name="Builds").get_by_role("button").first.click()            # open Builds
        for name in ("Grunt", "Copywriter", "SEO"):
            await sheet.get_by_role("button", name=f"Take in: {name}").click()
        assert await builds.locator(".team-seat:not(.is-empty)").count() == 3
        await builds.get_by_role("button", name="Done").click()
        await sheet.get_by_label("What it is for").fill("Launch the beta: the build and its page.")
        await sheet.get_by_role("button", name="Save party").click()
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
        await _pick_goal(page, "land")
        await _band(page, "build")                                                                      # its party's members: a column each, a head each
        tokens = page.locator(".token")
        await tokens.nth(2).wait_for(timeout=WAIT_MS)
        assert [await t.locator("img.ork-race__head").get_attribute("src") for t in await tokens.all()] == [
            "races/elf-elder@2x.png", "races/elf-warrior@2x.png", "races/goblin-warrior@2x.png"]
        assert [(await t.get_attribute("aria-label")).split(", ")[:2] for t in await tokens.all()] == [
            ["Product designer", "Veteran elf · Design"], ["Accessibility reviewer", "Seasoned elf · Design"], ["Analyst", "Seasoned goblin · Data"]]   # each named, with its head in words
        assert [await t.locator(".token__name").inner_text() for t in await tokens.all()] == ["Product designer", "Accessibility reviewer", "Analyst"]
        await _band(page, "lead")                                                                       # the leader's head leads the Planning column
        assert await page.locator(".token img.ork-race__head").get_attribute("src") == "races/peon-elder@2x.png"
        await _shot(page, "phone-goal-team-board-390x844")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_team_s_checkers_say_what_they_add_every_idea_is_kept_and_the_spec_says_each_check(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New party")
        await sheet.locator('.craft-tile[data-craft="design"]').click()
        await sheet.locator('.party [data-change="team"]').click()
        await sheet.get_by_role("region", name="Checks").get_by_role("button").first.click()            # open Checks
        await sheet.get_by_role("button", name="Take in: Reviewer").click()                             # the second checker
        await sheet.get_by_role("region", name="Checks").get_by_role("button", name="Done").click()
        assert await sheet.locator(".party-checks .party-line").inner_text() == "2 checks, where each applies"      # folded to one line
        await sheet.locator('.party-checks [data-change="checks"]').click()
        block = sheet.get_by_role("group", name="Checks")
        await expect(block).to_contain_text("adds about $0.35 to a goal it checks", timeout=WAIT_MS)      # the price comes back from the host a moment after the pick
        text = await block.inner_text()
        assert "Accessibility reviewer" in text and "Reviewer" in text and "Product designer" not in text   # checkers only
        assert "applies when the goal changes what people see or use" in text and "≈ $1.30 a goal they all apply to" not in text   # the sum goes: each check says what it adds (spec 43 C)
        assert "adds about $0.35 to a goal it checks · about half of them" in text
        await block.get_by_label("Every goal: Reviewer").check()
        await block.get_by_role("button", name="Done").click()
        assert await sheet.locator(".party-checks .party-line").inner_text() == "2 checks, 1 on every goal"
        await sheet.get_by_label("What it is for").fill("A settings screen.")
        await _shot(page, "phone-goal-3-checks-390x844")
        await sheet.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save", {"about": "A settings screen.", "craft": "design", "leader": "product-designer",
                                                       "team": ["ui-kit", "artist", "accessibility-reviewer", "reviewer"],
                                                       "every": ["reviewer"], "priority": "normal"})
        stub.checks = [{"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": True, "why": "", "state": "passed"},
                       {"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "review"},
                       {"by": "seo", "name": "SEO", "applies": False, "why": "It adds no public page", "state": ""}]
        await page.locator(".screen-head").get_by_role("button", name="Back").click()                  # from the new goal's screen
        await _pick_goal(page, "general")
        await _open_idea_of(page, "Retry on a lost signal", "Sync ideas")
        line = page.locator(".screen").get_by_role("list", name="Checks")
        await line.wait_for(timeout=WAIT_MS)
        chips = [" ".join(t.split()) for t in await line.get_by_role("listitem").all_inner_texts()]
        assert chips == ["Accessibility reviewer passed", "Reviewer at Review", "SEO not needed: It adds no public page"]
        await _shot(page, "phone-spec-checks-390x844")


@pytest.mark.asyncio
async def test_a_party_whose_goals_are_done_has_no_verdict_to_ask_for_and_its_screen_says_what_it_did(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="marketing", race="gnome", team=["copywriter"],
                                       leader=stub.leader("growth"), metrics=[{"name": "weekly installs", "target": "50", "how": "npm"}])
        stub.ideas["page"] = stub.idea("page", "The landing page", "done", 2, track="land")
        stub.bump({})
        await _pick_goal(page, "land")
        await _band(page, "lead")
        assert await page.locator(".token img.ork-race__head").get_attribute("src") == "races/gnome-elder@2x.png"   # the party's head: its leader's, in Planning
        await _open_party(page, "Landing page")
        screen = page.locator(".screen")
        await screen.get_by_text("Landing page").first.wait_for(timeout=WAIT_MS)
        text = await screen.inner_text()
        assert "Verdict" not in text and "accept" not in text.lower() and "Metrics" not in text and "weekly installs" not in text     # a party has no end: no verdict, no metrics
        assert await screen.get_by_role("button", name="Edit the party", exact=True).is_visible()
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_check_that_has_not_run_is_skipped_from_the_spec_to_spare_its_run(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.checks = [{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "waiting", "task": "k5", "skipped": False, "tier": "elder"},
                       {"by": "editor", "name": "Editor", "applies": True, "why": "", "state": "passed", "task": "k6", "skipped": False, "tier": "laborer"}]
        stub.bump({})
        await _open_idea_of(page, "Retry on a lost signal", "Sync ideas")
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


@pytest.mark.asyncio
async def test_a_check_is_skipped_from_the_checking_stage_before_its_task_runs(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.checks = [{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "waiting", "task": "k5", "skipped": False, "tier": "elder"}]
        for t in stub.plan["tasks"]:                                                                   # only the check is left: the idea is in Checking
            if t["id"] != "k5":
                t["state"] = "merged"
        stub.bump({})
        await _band(page, "check")                                                                      # the check's task waits in Checking, not run yet: its screen, then its idea's
        await _item(page, "Write the notes").click()
        await page.locator(".screen .facts").get_by_role("button", name="Sync ideas between the phone and the town").click()
        skip = page.locator(".screen").get_by_role("list", name="Checks").get_by_role("button", name="Skip the check: Reviewer")
        await skip.wait_for(timeout=WAIT_MS)
        assert (await skip.bounding_box())["height"] >= 43                                             # a finger's size
        assert "spares ≈ $" in await skip.inner_text()
        await _shot(page, "phone-trail-check-skip-390x844")
        await skip.click()
        assert await _called(stub, "ideas.check_skip", {"slug": "sync", "by": "reviewer"})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_goal_s_team_is_changed_from_its_screen_and_saved_alone(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        for a in (library.get("product-designer"), library.get("ui-kit"), library.get("accessibility-reviewer")):
            stub.roles[a.id] = {"slug": a.id, "name": a.name, "model": a.tier, "max_parallel": 2, "instruction": a.instruction, "builtin": False,
                                "craft": a.craft, "head": {"craft": a.craft, "race": "elf", "tier": a.tier}}
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="design", race="elf", about="A landing page.",
                                       team=["ui-kit", "accessibility-reviewer"], every=[], leader=stub.leader("product-designer"))
        stub.bump({})
        await _pick_goal(page, "land")
        await _open_party(page, "Landing page")
        team = page.locator(".screen").get_by_role("region", name="The party", exact=True)
        await team.wait_for(timeout=WAIT_MS)
        assert await team.locator("img").count() == 3 and "Product designer" in await team.inner_text() and "Design system designer" in await team.inner_text()   # its heads and names
        await team.get_by_role("button", name="Change the party").click()
        sheet = page.get_by_role("dialog", name="The party")
        await sheet.wait_for(timeout=WAIT_MS)
        assert await sheet.locator(".party-line").first.inner_text() == "Leads: Product designer · Builds: Design system designer · Checks: Accessibility reviewer"
        await sheet.locator('.party [data-change="team"]').click()
        await sheet.get_by_role("button", name="Take in: Analyst").click()                              # the leader changes; Builds opens
        await sheet.get_by_role("button", name="Take in: Artist").click()
        await sheet.get_by_role("region", name="Builds").get_by_role("button", name="Done").click()
        await sheet.get_by_role("button", name="Save the party").click()
        assert await _called(stub, "ideas.goal_save", {"slug": "land", "team": ["ui-kit", "accessibility-reviewer", "artist"], "every": [], "leader": "analyst"})
        assert not any(c[0] == "ideas.goal_save" and "about" in c[1] and c[1].get("slug") == "land" for c in stub.calls)   # the party alone: no words sent
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)
