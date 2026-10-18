"""Spec 36 part C on the phone (docs/specs/36-agents-spend.md §5, "Tests → C"): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py. Agents as a monitor (no Task types, a role's week once it has three merged results, the chips with what needs
you first), the agent's dialog as a sheet (By Target, the 600-character counter, Takes), and the result's idea line; no horizontal scroll
of the page. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _phone, _shot  # noqa: F401

pytest.importorskip("playwright.async_api")
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
    return agents.locator(".role[data-role='grunt'] .role-facts")


@pytest.mark.asyncio
async def test_agents_is_a_monitor_a_role_says_its_week_after_three_merged_and_the_chips_put_needs_you_first(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.chip_extra = {"k4": {"state": "failed", "note": "tests stayed red"}, "k2": {"state": "held", "note": "after 18:00"}}
        stub.week = {"grunt": WEEK | {"merged": 2}}                                                       # two merged: too few to say
        stub.bump({})
        agents = await _agents(page)
        assert "Task types" not in await agents.inner_text() and await agents.get_by_label("Agent for Code").count() == 0
        facts = _grunt_head(agents)
        assert await facts.inner_text() == "By Target · up to 8 · ≈$1.25 today"                         # no week under three merged
        assert await facts.locator(".priced").first.get_attribute("title") == "At API prices, not your bill"
        assert "Takes: code, tests, docs, text for people, research" in await agents.locator(".role[data-role='grunt']").inner_text()
        # needs you first, then working, then the rest; spec 35's held words stay
        states = await agents.locator(".role[data-role='grunt'] .chip[data-state]").evaluate_all("els => els.map((e) => e.querySelector('.chip-state').textContent)")
        assert states[0].startswith("needs you") and states[1].startswith("working")
        assert [s.split(" ")[0] for s in states] == ["needs", "working", "waits"]
        stub.week = {"grunt": WEEK, "taskmaster": {"spent": 1.0, "plans": 3, "merged": 0, "first_time": 8, "finished": 10, "usd_per_merged": None}}
        stub.bump({})
        await expect(facts).to_contain_text("a result", timeout=WAIT_MS)
        assert await facts.inner_text() == "By Target · up to 8 · ≈$1.25 today · ≈$0.90 a result · 8/10 the first time"
        assert await agents.locator(".role[data-role='taskmaster'] .role-facts").inner_text() == "Elder · opus · 8/10 tasks the first time"
        await _shot(page, "phone-agents-monitor-390x844")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_dialog_is_a_sheet_with_by_target_a_counter_and_takes_that_moves_a_type_from_grunt(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        agents = await _agents(page)
        await agents.get_by_role("button", name="+ Add agent").click()
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
        assert await _called(stub, "ideas.role_save", {"name": "Docs scribe", "model": "", "max_parallel": 2, "instruction": "Write plainly.", "kinds": ["docs"]})
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
        await page.get_by_role("tab", name="Review").click()
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
