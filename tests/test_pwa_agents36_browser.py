"""Spec 36 part C on the phone (docs/specs/36-agents-spend.md §5, "Tests → C"): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py. Agents as a monitor (no Task types, a role's week once it has three merged results, the chips with what needs
you first), the agent's dialog as a sheet (By Target, the 600-character counter, Takes), and the result's idea line; no horizontal scroll
of the page. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _phone, _shot  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser
from playwright.async_api import expect  # noqa: E402

WEEK = {"spent": 4.2, "merged": 8, "first_time": 8, "finished": 10, "usd_per_merged": 0.9}
SPEND = {"usd": 3.1, "unpriced": 0, "tasks": {},
         "stages": {"goal": {"usd": 0.4}, "spec": {"usd": 0.5}, "plan": {"usd": 0.2}, "work": {"usd": 1.5}, "rework": {"usd": 0.5}, "dropped": {"usd": 0}}}


async def _agents(page):
    await page.get_by_role("tab", name="Agents").click()
    agents = page.locator(".agents")
    await agents.get_by_role("button", name="+ Add agent").wait_for(timeout=WAIT_MS)
    return agents


def _grunt_head(agents):
    return agents.locator(".role[data-role='grunt'] .role-head")


@pytest.mark.asyncio
async def test_agents_is_a_monitor_a_role_is_one_line_with_what_a_task_costs_and_the_chips_put_needs_you_first(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.chip_extra = {"k4": {"state": "failed", "note": "tests stayed red"}, "k2": {"state": "held", "note": "after 18:00"}}
        stub.usd_task = {"grunt": 0.4}                                                                    # spec 41 §8: `usd_task`
        stub.bump({})
        agents = await _agents(page)
        assert "Task types" not in await agents.inner_text() and await agents.get_by_label("Agent for Code").count() == 0
        line = _grunt_head(agents)
        await expect(line).to_have_attribute("aria-label", "Grunts: an ork, Engineering, Seasoned; up to 8 at once; about $0.40 a task", timeout=WAIT_MS)
        assert " ".join((await line.inner_text()).split()).startswith("Grunts ×8 ≈ $0.40 a task Edit")   # its head, its name, ×8, the cost of a task
        assert await line.locator(".role-facts").inner_text() == "≈$1.25 today"                          # its day, muted under the line (the owner, 20 October)
        assert await line.locator("img").count() == 1 and await line.locator(".role-usd").get_attribute("title") == "At API prices, not your bill"
        assert "up to" not in await line.inner_text() and "By Target" not in await line.inner_text()      # no model in words (spec 41 §8)
        assert "Takes: code, tests, docs, text for people, research" in await agents.locator(".role[data-role='grunt']").inner_text()
        tm = agents.locator(".role[data-role='taskmaster'] .role-head")                                  # its cost is its steps: no ×N, no cost of a task
        assert " ".join((await tm.inner_text()).split()) == "Taskmaster Edit" and "×" not in await tm.inner_text()
        # needs you first, then working, then the rest; spec 35's held words stay
        await expect(agents.locator(".role[data-role='grunt'] .chip[data-state] .chip-state").first).to_contain_text(
            "needs you", timeout=WAIT_MS)                                                               # the bump drawn
        states = await agents.locator(".role[data-role='grunt'] .chip[data-state]").evaluate_all("els => els.map((e) => e.querySelector('.chip-state').textContent)")
        assert states[0].startswith("needs you") and states[1].startswith("working")
        assert [s.split(" ")[0] for s in states] == ["needs", "working", "waits"]
        stub.week = {"taskmaster": {"spent": 1.0, "plans": 3, "merged": 0, "first_time": 8, "finished": 10, "usd_per_merged": None}}
        stub.bump({})
        await expect(tm).to_contain_text("8/10 tasks the first time", timeout=WAIT_MS)                    # the Taskmaster's week stays as it was said
        await _shot(page, "phone-agents-monitor-390x844")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_chip_shows_its_short_name_on_two_lines_with_the_title_in_its_label(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.chip_extra = {"k3": {"short": "Retry offline", "idea_short": "Sync"}}
        stub.bump({})
        agents = await _agents(page)
        chip = agents.locator(".chip", has_text="Retry offline")
        await chip.wait_for(timeout=WAIT_MS)
        assert await chip.get_attribute("title") == "Retry on a lost signal" and "Retry on a lost signal" in await chip.get_attribute("aria-label")
        assert "Sync" in await chip.locator(".chip-idea").inner_text() and "Sync ideas between" not in await chip.inner_text()
        assert await chip.locator(".chip-name").evaluate("e => getComputedStyle(e).webkitLineClamp") == "2"
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_add_agent_opens_two_ways_from_the_library_adds_the_agent_and_your_own_is_the_sheet(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        agents = await _agents(page)
        await agents.get_by_role("button", name="+ Add agent").click()
        choose = page.get_by_role("dialog", name="Add an agent")
        await choose.wait_for(timeout=WAIT_MS)
        rows = choose.locator(".team-row")
        assert await rows.count() > 5 and await choose.get_by_role("button", name="Add Taskmaster").count() == 0   # the ones the project has are not offered
        assert await choose.get_by_role("button", name="Your own").is_visible()
        row = choose.get_by_role("button", name="Add Copywriter")
        assert "Marketing" in await row.inner_text() and await row.locator("img").count() == 1                 # its head, name, craft and what it takes
        await _shot(page, "phone-add-agent-390x844")
        await row.click()
        assert await _called(stub, "ideas.role_add", {"id": "copywriter"})
        await choose.wait_for(state="hidden", timeout=WAIT_MS)
        await agents.locator(".role[data-slug='copywriter']").wait_for(timeout=WAIT_MS)
        await agents.get_by_role("button", name="+ Add agent").click()                                   # added: no longer offered
        await choose.wait_for(timeout=WAIT_MS)
        assert await choose.get_by_role("button", name="Add Copywriter").count() == 0
        await choose.get_by_role("button", name="Your own").click()
        assert await page.get_by_role("dialog", name="Add agent").get_by_label("Name").is_visible()      # today's sheet
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_built_in_two_show_what_they_are_told_already_and_the_field_adds_to_it(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        agents = await _agents(page)
        await agents.get_by_role("button", name="Edit Taskmaster").click()
        sheet = page.get_by_role("dialog", name="Edit agent")
        told = sheet.locator(".told")
        assert await told.get_attribute("open") is None and "What it is told already" in await told.inner_text()      # folded
        await told.locator("summary").click()
        assert "The Taskmaster reads each step's prompt." in await told.inner_text() and await told.locator("textarea, input").count() == 0   # read only
        assert await sheet.get_by_label("Added to what it is told").is_visible()
        await sheet.get_by_role("button", name="Cancel").click()
        await agents.get_by_role("button", name="Edit Grunts").click()
        assert "A Grunt gets the task's brief" in await page.get_by_role("dialog", name="Edit agent").locator(".told").text_content()
        await page.get_by_role("dialog", name="Edit agent").get_by_role("button", name="Cancel").click()
        await agents.get_by_role("button", name="+ Add agent").click()                                    # an agent of your own: no told, the plain field
        await page.get_by_role("dialog", name="Add an agent").get_by_role("button", name="Your own").click()
        own = page.get_by_role("dialog", name="Add agent")
        assert await own.locator(".told").is_hidden() and await own.get_by_label("Instruction").is_visible()


@pytest.mark.asyncio
async def test_the_dialog_is_a_sheet_with_by_target_a_counter_and_takes_that_moves_a_type_from_grunt(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        agents = await _agents(page)
        await agents.get_by_role("button", name="+ Add agent").click()
        await page.get_by_role("dialog", name="Add an agent").get_by_role("button", name="Your own").click()
        sheet = page.get_by_role("dialog", name="Add agent")
        box = await sheet.bounding_box()
        assert box["x"] == 0 and box["width"] == 390 and box["y"] + box["height"] == 844                # a bottom sheet
        options = await sheet.get_by_label("Model").locator("option").all_inner_texts()
        assert options == ["By Target", "Elder · opus", "Warrior · sonnet", "Laborer · haiku"]
        assert await sheet.get_by_label("Model").input_value() == ""                                    # a new agent is By Target
        assert "By Target: the task's own tier, moved by the Target" in await sheet.inner_text()
        assert await sheet.locator(".counter").inner_text() == "0 / 600"
        await sheet.get_by_label("Name").fill("Docs scribe")
        await sheet.get_by_label("Instruction").fill("Write plainly. " * 10)
        assert await sheet.locator(".counter").inner_text() == "149 / 600"
        take = sheet.locator(".take-row[data-kind='docs']")
        assert "now Grunt" in await take.inner_text()
        await take.get_by_label("Docs").check()
        await _shot(page, "phone-agent-dialog-390x844")
        await sheet.get_by_label("Instruction").fill("x" * 601)                                          # over: refused here, as on the host
        assert await sheet.locator(".counter").inner_text() == "601 / 600"
        assert await sheet.get_by_role("button", name="Save agent").is_disabled()
        await sheet.get_by_label("Instruction").fill("Write plainly.")
        await sheet.get_by_role("button", name="Save agent").click()
        assert await _called(stub, "ideas.role_save", {"name": "Docs scribe", "model": "", "max_parallel": 2, "instruction": "Write plainly.", "kinds": ["docs"], "craft": "engineering"})
        await agents.locator(".role[data-slug='docs-scribe']").wait_for(timeout=WAIT_MS)
        assert "Takes: docs" in await agents.locator(".role[data-slug='docs-scribe']").inner_text()
        assert "docs" not in (await agents.locator(".role[data-role='grunt']").inner_text()).split("Takes:")[1].split("\n")[0]   # Grunt's block no longer says it
        await agents.get_by_role("button", name="Edit Docs scribe").click()                              # unticked, it goes back to Grunt
        sheet = page.get_by_role("dialog", name="Edit agent")
        assert await sheet.get_by_label("Docs").is_checked() and "now Docs scribe" in await sheet.locator(".take-row[data-kind='docs']").inner_text()
        await sheet.get_by_label("Docs").uncheck()
        await sheet.get_by_role("button", name="Save agent").click()
        await expect(agents.locator(".role[data-slug='docs-scribe']")).not_to_contain_text("Takes:", timeout=WAIT_MS)
        assert stub.kinds["docs"] == "grunt"
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_grunts_types_are_shown_not_editable_the_taskmaster_has_no_takes_and_a_long_instruction_is_said(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.roles["scribe"] = {"slug": "scribe", "name": "Scribe", "model": "opus-9", "max_parallel": 2, "instruction": "Short.", "builtin": False,
                                "instruction_long": "Long. " * 200, "hand_model": True}
        stub.kinds["docs"] = "scribe"
        stub.bump({})
        agents = await _agents(page)
        await agents.locator(".role[data-slug='scribe']").wait_for(timeout=WAIT_MS)
        await agents.get_by_role("button", name="Edit Grunts").click()
        sheet = page.get_by_role("dialog", name="Edit agent")
        boxes = sheet.locator(".take-row input")
        assert await boxes.count() == 5 and all([await boxes.nth(i).is_disabled() for i in range(5)])
        assert "Grunt takes what no other agent takes" in await sheet.inner_text()
        assert not await sheet.get_by_label("Docs").is_checked() and await sheet.get_by_label("Code").is_checked()
        await sheet.get_by_role("button", name="Cancel").click()
        await agents.get_by_role("button", name="Edit Taskmaster").click()
        sheet = page.get_by_role("dialog", name="Edit agent")
        assert await sheet.locator(".takes").is_hidden()
        assert "By Target" not in " ".join(await sheet.get_by_label("Model").locator("option").all_inner_texts()) and "tasks" not in await sheet.locator(".takes").inner_text()
        await sheet.get_by_role("button", name="Cancel").click()
        await agents.get_by_role("button", name="Edit Scribe").click()                                   # saved before: a hand-set model, an instruction too long
        sheet = page.get_by_role("dialog", name="Edit agent")
        assert await sheet.get_by_label("Model").input_value() == "opus-9" and "opus-9 (set by hand)" in await sheet.get_by_label("Model").inner_text()
        assert "Only the first 600 characters go to the ork: shorten it" in await sheet.inner_text()
        assert await sheet.locator(".counter").inner_text() == "1199 / 600" and await sheet.get_by_role("button", name="Save agent").is_disabled()
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_result_says_what_its_idea_cost_so_far_by_stage(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.spend = SPEND
        await page.get_by_role("tab", name="Needs you").click()
        await page.get_by_role("button", name="Add the queue: open its code").click()
        line = page.locator(".screen .spend-line")
        await line.wait_for(timeout=WAIT_MS)
        assert await line.inner_text() == "This idea so far: ≈$3.10 — goal 0.40 · spec 0.50 · plan 0.20 · work 1.50 · rework 0.50"
        assert await _called(stub, "ideas.spend", {"idea": "sync"})
        assert (await line.bounding_box())["y"] < (await page.locator(".screen .code").bounding_box())["y"]      # under the title, above the code
        await _shot(page, "phone-result-idea-line-390x844")
        assert await page.evaluate(NO_SCROLL)
        await page.get_by_role("button", name="Back", exact=True).click()
        stub.spend = {"usd": None, "unpriced": 3, "tasks": {}, "stages": {"work": {"usd": None}}}          # all unpriced: a dash
        await page.get_by_role("button", name="Add the queue: open its code").click()
        await page.locator(".screen .spend-line", has_text="—").wait_for(timeout=WAIT_MS)
        assert await page.locator(".screen .spend-line").inner_text() == "This idea so far: —"
        await page.get_by_role("button", name="Back", exact=True).click()
        stub.spend = None                                                                                  # the host cannot say: no line, the result still opens
        await page.get_by_role("button", name="Add the queue: open its code").click()
        await page.locator(".screen .code").wait_for(timeout=WAIT_MS)
        assert await page.locator(".screen .spend-line").count() == 0


@pytest.mark.asyncio
async def test_an_agents_sheet_says_its_record_of_the_last_30_days_in_each_wording(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.record = {"grunt": {"days": 30, "finished": 41, "merged": 38, "first_time": 36, "usd_per_merged": 0.6},
                       "taskmaster": {"days": 30, "plans": 12, "finished": 41, "first_time": 36}}
        stub.roles["scribe"] = {"slug": "scribe", "name": "Scribe", "model": "", "max_parallel": 2, "instruction": "", "builtin": False}
        stub.record["scribe"] = {"days": 30, "finished": 2, "merged": 2, "first_time": 2, "usd_per_merged": None}
        stub.bump({})
        await page.wait_for_timeout(800)
        agents = await _agents(page)
        line = await agents.locator(".role[data-slug='grunt']").inner_text()

        async def said(button):
            await agents.get_by_role("button", name=button).click()
            sheet = page.get_by_role("dialog", name="Edit agent")
            text = " ".join((await sheet.get_by_label("The last 30 days").text_content()).split())
            await sheet.get_by_role("button", name="Cancel").click()
            return text
        assert await said("Edit Grunts") == "The last 30 days: 41 tasks, 36 merged the first time · ≈$0.60 a merged result"
        assert await said("Edit Scribe") == "The last 30 days: 2 tasks: too few to say more"
        assert await said("Edit Taskmaster") == "The last 30 days: 12 plans; of their 41 tasks, 36 merged the first time"
        stub.record = {}
        stub.bump({})
        await page.wait_for_timeout(1200)
        assert await said("Edit Grunts") == "No tasks in the last 30 days"
        assert await agents.locator(".role[data-slug='grunt']").inner_text() == line                   # the line stays its own (§54.6)
        await agents.get_by_role("button", name="+ Add agent").click()
        await page.get_by_role("dialog", name="Add an agent").get_by_role("button", name="Your own").click()
        assert await page.get_by_role("dialog", name="Add agent").get_by_label("The last 30 days").is_hidden()


@pytest.mark.asyncio
async def test_a_checkers_line_ends_with_its_check_of_the_week_and_its_sheet_has_its_check_of_30_days(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.check_week = {"grunt": {"checks": 6, "clean": 4, "caught": 2, "left": 1, "usd_per_check": None}}
        stub.roles["scribe"] = {"slug": "scribe", "name": "Scribe", "model": "", "max_parallel": 2, "instruction": "", "builtin": False}
        stub.record = {"scribe": {"days": 30, "finished": 20, "merged": 18, "first_time": 15, "usd_per_merged": 0.5,
                                  "check": {"checks": 14, "clean": 11, "caught": 3, "left": 1, "usd_per_check": 0.35}},
                       "grunt": {"days": 30, "finished": 41, "merged": 38, "first_time": 36, "usd_per_merged": 0.6}}
        stub.bump({})
        agents = await _agents(page)
        await expect(_grunt_head(agents).locator(".role-facts")).to_have_text("≈$1.25 today · its check: 6 ideas, caught 2", timeout=WAIT_MS)

        async def said(button):
            await agents.get_by_role("button", name=button).click()
            sheet = page.get_by_role("dialog", name="Edit agent")
            line = sheet.get_by_label("Its check")
            await sheet.get_by_label("Name").wait_for(timeout=WAIT_MS)
            text = " ".join((await line.text_content()).split()) if await line.is_visible() else ""
            await sheet.get_by_role("button", name="Cancel").click()
            return text
        assert await said("Edit Scribe") == "Its check, the last 30 days: 14 ideas: 11 clean, caught 3 · ≈$0.35 a check"
        assert await said("Edit Grunts") == ""
        stub.record = {"scribe": {"days": 30, "finished": 20, "merged": 18, "first_time": 15, "usd_per_merged": 0.5,
                                  "check": {"checks": 2, "clean": 2, "caught": 0, "left": 0, "usd_per_check": None}}}
        stub.bump({})
        await page.wait_for_timeout(3500)
        assert await said("Edit Scribe") == "Its check, the last 30 days: 2 ideas: too few to say more"


@pytest.mark.asyncio
async def test_a_chip_started_by_the_pace_says_the_week_has_room(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.chip_extra = {"k3": {"by": "auto", "pace": True}, "k2": {"by": "auto"}}
        stub.bump({})
        agents = await _agents(page)
        pace = agents.locator(".chip", has_text="Retry on a lost signal")
        await pace.wait_for(timeout=WAIT_MS)
        assert await pace.locator(".chip-why").inner_text() == "by itself: the week has room"
        assert await agents.locator(".chip", has_text="Add the queue").locator(".chip-why").inner_text() == "by itself"
