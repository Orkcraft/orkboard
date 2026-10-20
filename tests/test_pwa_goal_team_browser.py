"""New goal on one sheet on the phone (shell-goal-new.js, spec 41 §6): what it is for, its craft in one row of heads, its team from the
library (the host's, realm/library.py) in three folds, its checks; a goal's team changed from its own screen (§7). The Board is the stub's
(tests/test_pwa_shell_browser.py)."""
from __future__ import annotations

import pytest

from orkboard.realm import library  # noqa: E402
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _new_goal, _phone, _pick_goal, _shot  # noqa: F401

pytestmark = pytest.mark.browser


@pytest.mark.asyncio
async def test_new_goal_is_one_sheet_a_craft_in_one_row_its_team_in_three_folds_and_save_in_sight(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        tiles = sheet.locator(".craft-tile")
        assert await tiles.count() == 6                                                                  # five crafts and Mixed, one row
        ys = {round((await t.bounding_box())["y"]) for t in await tiles.all()}
        assert len(ys) == 1 and await sheet.get_by_label("Description").evaluate("e => document.activeElement === e")   # one row; the description focused
        assert [await t.get_attribute("aria-label") for t in await tiles.all()] == ["Engineering", "Design", "Data", "Marketing", "Product", "Mixed"]
        save = sheet.get_by_role("button", name="Save goal")
        assert await save.is_disabled()                                                                  # enabled once the description has words
        foot = await sheet.locator(".sheet-foot").bounding_box()
        assert foot["y"] + foot["height"] >= 844 - 2 and await sheet.get_by_role("button", name="Next").count() == 0   # pinned at the foot, no steps
        await sheet.locator('.craft-tile[data-craft="product"]').click()
        assert "Product: who it is for, what it moves, what it leaves out" in await sheet.locator(".craft-line").inner_text()
        await sheet.locator('.craft-tile[data-craft="design"]').click()
        line = sheet.locator(".party-line").first
        assert await line.inner_text() == "Leads: Product designer · Builds: Design system designer, Artist · Checks: Accessibility reviewer"   # folded to one line
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
        await sheet.get_by_label("Description").fill("A landing page that says what Orkline does in one screen.")
        await save.click()
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
        assert await sheet.locator(".party-line").first.inner_text() == "Leads: Taskmaster · Builds: none · Checks: none"
        await sheet.locator('.party [data-change="team"]').click()
        builds = sheet.get_by_role("region", name="Builds")
        await sheet.get_by_role("region", name="Builds").get_by_role("button").first.click()            # open Builds
        for name in ("Grunt", "Copywriter", "SEO"):
            await sheet.get_by_role("button", name=f"Take in: {name}").click()
        assert await builds.locator(".team-seat:not(.is-empty)").count() == 3
        await builds.get_by_role("button", name="Done").click()
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
        await sheet.locator('.party [data-change="team"]').click()
        await sheet.get_by_role("region", name="Checks").get_by_role("button").first.click()            # open Checks
        await sheet.get_by_role("button", name="Take in: Reviewer").click()                             # the second checker
        await sheet.get_by_role("region", name="Checks").get_by_role("button", name="Done").click()
        assert await sheet.locator(".party-checks .party-line").inner_text() == "2 checks, where each applies"      # folded to one line
        await sheet.locator('.party-checks [data-change="checks"]').click()
        block = sheet.get_by_role("group", name="Checks")
        await page.wait_for_function("() => document.querySelectorAll('.checks-block [data-adds]').length === 2 && [...document.querySelectorAll('.checks-block [data-adds]')].every((e) => e.textContent.includes('adds about'))", timeout=WAIT_MS)
        text = await block.inner_text()
        assert "Accessibility reviewer" in text and "Reviewer" in text and "Product designer" not in text   # checkers only
        assert "applies when the idea changes what people see or use" in text
        assert text.count("adds about $0.35 to an idea it checks · about half of them") == 2 and "an idea they all apply to" not in text   # each check says what it adds
        await block.get_by_label("Every idea: Reviewer").check()
        await block.get_by_text("adds about $0.35 to an idea it checks · every idea").wait_for(timeout=WAIT_MS)       # the line changes in place
        await block.get_by_role("button", name="Done").click()
        assert await sheet.locator(".party-checks .party-line").inner_text() == "2 checks, 1 on every idea"
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


@pytest.mark.asyncio
async def test_a_check_is_skipped_right_on_the_trail_before_a_plan_or_before_its_task_runs(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.checks = [{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "waiting", "task": "k5", "skipped": False, "tier": "elder"}]
        stub.ideas["new"] = stub.idea("new", "A darker theme", "ready", 3, checks=[
            {"by": "editor", "name": "Editor", "applies": True, "why": "", "state": "", "task": "", "skipped": False, "tier": "laborer"},
            {"by": "seo", "name": "SEO", "applies": True, "why": "", "state": "", "task": "", "skipped": True, "tier": "laborer"}])
        stub.bump({})
        sync = page.locator(".map-row", has_text="Sync ideas")
        skip = sync.get_by_role("button", name="Skip the check: Reviewer")                            # its task, not run yet
        await skip.wait_for(timeout=WAIT_MS)
        assert (await skip.bounding_box())["height"] >= 43                                             # a finger's size
        await skip.click()
        sheet = page.get_by_role("dialog", name="Skip the check?")
        assert "taken out of the plan before it runs" in await sheet.inner_text() and "spares ≈ $" in await sheet.inner_text()
        await _shot(page, "phone-trail-check-skip-390x844")
        await sheet.get_by_role("button", name="Skip it").click()
        assert await _called(stub, "ideas.check_skip", {"slug": "sync", "by": "reviewer"})
        new = page.locator(".map-row", has_text="A darker theme")                                      # not planned: the checks its plan will hold
        await new.get_by_role("button", name="Skip the check: Editor").click()
        assert "The plan is made without it" in await page.get_by_role("dialog", name="Skip the check?").inner_text()
        await page.get_by_role("dialog", name="Skip the check?").get_by_role("button", name="Skip it").click()
        assert await _called(stub, "ideas.check_skip", {"slug": "new", "by": "editor"})
        await new.get_by_role("button", name="Take the check again: SEO").click()                      # left out: taken again with a tap
        assert await _called(stub, "ideas.check_skip", {"slug": "new", "by": "seo", "skip": False})
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
        await page.locator('.map-goal[data-goal="land"]').get_by_role("button", name="Open goal Landing page").click()
        team = page.locator(".screen").get_by_role("region", name="Team")
        await team.wait_for(timeout=WAIT_MS)
        assert await team.locator("img").count() == 3 and "Product designer" in await team.inner_text() and "Design system designer" in await team.inner_text()   # its heads and names
        await team.get_by_role("button", name="Change the team").click()
        sheet = page.get_by_role("dialog", name="Team")
        await sheet.wait_for(timeout=WAIT_MS)
        assert await sheet.locator(".party-line").first.inner_text() == "Leads: Product designer · Builds: Design system designer · Checks: Accessibility reviewer"
        await sheet.locator('.party [data-change="team"]').click()
        await sheet.get_by_role("button", name="Take in: Analyst").click()                              # the leader changes; Builds opens
        await sheet.get_by_role("button", name="Take in: Artist").click()
        await sheet.get_by_role("region", name="Builds").get_by_role("button", name="Done").click()
        await sheet.get_by_role("button", name="Save team").click()
        assert await _called(stub, "ideas.goal_save", {"slug": "land", "team": ["ui-kit", "accessibility-reviewer", "artist"], "every": [], "leader": "analyst"})
        assert not any(c[0] == "ideas.goal_save" and "about" in c[1] and c[1].get("slug") == "land" for c in stub.calls)   # the party alone: no words sent
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_party_s_price_is_said_when_the_picker_opens_and_after_a_seat_changes_and_a_checker_has_its_mark(fake_repo, monkeypatch):
    def asked(stub):
        return [c[1] for c in stub.calls if c[0] == "ideas.party_price"]

    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        line = sheet.locator(".party-price")
        await line.wait_for(timeout=WAIT_MS)
        assert " ".join((await line.inner_text()).split()) == "This party: about $2–6 an idea from this project's last 12 ideas"
        assert asked(stub) == [{"leader": "architect", "team": ["grunt", "tester", "reviewer"], "every": []}]       # when the sheet opens: one call
        await sheet.locator('.craft-tile[data-craft="design"]').click()                                # a craft, then a seat, inside 300 ms: one call
        await sheet.locator('.party [data-change="team"]').click()
        stub.price_learned, stub.price_low, stub.price_high = False, 0.4, 1.2
        await sheet.get_by_role("button", name="Take in: Analyst").click()
        await page.wait_for_function("() => document.querySelector('.party-price')?.textContent.includes('a first guess')", timeout=WAIT_MS)
        assert " ".join((await line.inner_text()).split()) == "This party: about $0.40–1.20 an idea a first guess: it learns from this project's ideas"
        assert len(asked(stub)) == 2 and asked(stub)[-1]["leader"] == "analyst"
        await sheet.get_by_role("region", name="Checks").get_by_role("button").first.click()            # open Checks
        mark = sheet.get_by_role("button", name="Take in: Reviewer").locator(".check-badge")
        assert await mark.text_content() == "checks"                                                      # a checker's mark, as on the desktop
        assert await sheet.get_by_role("button", name="Take out: Accessibility reviewer").locator(".check-badge").count() == 1
        await sheet.get_by_label("Description").fill("A settings screen.")
        assert await page.evaluate(NO_SCROLL)
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save")                                                  # the price never blocks Save


@pytest.mark.asyncio
async def test_a_goal_s_team_sheet_asks_the_price_when_it_opens(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="design", race="elf", about="A landing page.",
                                       team=["ui-kit", "accessibility-reviewer"], every=[], leader=stub.leader("product-designer"))
        stub.bump({})
        await _pick_goal(page, "land")
        await page.locator('.map-goal[data-goal="land"]').get_by_role("button", name="Open goal Landing page").click()
        await page.locator(".screen").get_by_role("region", name="Team").get_by_role("button", name="Change the team").click()
        sheet = page.get_by_role("dialog", name="Team")
        await sheet.locator(".party-price").wait_for(timeout=WAIT_MS)
        assert "This party: about $2–6 an idea" in await sheet.locator(".party-price").inner_text()
        assert await _called(stub, "ideas.party_price", {"leader": "product-designer", "team": ["ui-kit", "accessibility-reviewer"], "every": []})


PARTY = {"ideas": 9, "leader": {"slug": "product-manager", "name": "Product manager", "head": {"craft": "product", "race": "lich", "tier": "elder"}, "usd": 4.1},
         "members": [{"slug": "grunt", "name": "Grunt", "head": {"craft": "engineering", "race": "peon", "tier": "warrior"}, "tasks": 14, "merged": 13, "first_time": 12, "usd": 9.2}],
         "checks": [{"by": "accessibility-reviewer", "name": "Accessibility reviewer", "head": {"craft": "engineering", "race": "peon", "tier": "warrior"},
                     "applied": 6, "skipped": 1, "clean": 4, "caught": 2, "left": 1, "before": 2, "usd": 1.8}]}
PARTY_LINES = ['Product manager (leads): ≈$4.10 for the goal, the drafts and the plans', 'Grunt: 14 tasks, 12 merged the first time · ≈$9.20', 'Accessibility reviewer: checked 6 ideas: 4 clean, caught 2 (1 left) · ≈$1.80 · skipped 1 · 2 before findings were kept']


@pytest.mark.asyncio
async def test_the_goals_screen_has_a_fold_for_what_its_party_did_closed_at_first_and_read_when_opened(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.party = PARTY
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="marketing", race="gnome", leader=stub.leader("growth"))
        stub.ideas["page"] = stub.idea("page", "The landing page", "working", 2, track="land")
        stub.bump({})
        await _pick_goal(page, "land")
        await page.locator('.map-goal[data-goal="land"]').get_by_role("button", name="Open goal Landing page").click()
        sec = page.locator(".screen").get_by_role("region", name="What the party did")
        fold = sec.locator("details.party-work")
        await fold.wait_for(timeout=WAIT_MS)
        assert await fold.locator("summary").inner_text() == "What the party did" and await fold.get_attribute("open") is None
        assert not any(c[0] == "ideas.party" for c in stub.calls)                                  # closed at first: not asked for
        await fold.locator("summary").click()
        await sec.locator("li").first.wait_for(timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in await sec.locator("li").all_inner_texts()] == PARTY_LINES
        assert await _called(stub, "ideas.party", {"goal": "land"})
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "party", "ref": "land", "device": "phone"})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_goal_with_no_work_yet_says_so(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="marketing", race="gnome")
        stub.ideas["page"] = stub.idea("page", "The landing page", "working", 2, track="land")
        stub.bump({})
        await _pick_goal(page, "land")
        await page.locator('.map-goal[data-goal="land"]').get_by_role("button", name="Open goal Landing page").click()
        sec = page.locator(".screen").get_by_role("region", name="What the party did")
        await sec.locator("summary").click()
        await sec.get_by_text("No work yet").wait_for(timeout=WAIT_MS)
