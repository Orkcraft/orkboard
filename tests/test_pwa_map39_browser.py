"""Spec 39 part C on the phone (docs/specs/39-map.md §5, "Tests → C"): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py with a fake `ideas.map`. The Board's Map button opens the Map; a goal's ideas in tier order with their
dots, words, pips and *after …*; a row that needs the person first in its tier; a tap opens the idea, logged `via: "map"`;
no horizontal scroll."""
from __future__ import annotations

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _phone, _pick_goal, _shot  # noqa: F401


async def _open_map(page):
    """The Map: it is the Board."""
    await page.locator(".board-tab-pane").wait_for(timeout=WAIT_MS)

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser


def node(slug, title, tier, state, **more):
    return {"slug": slug, "goal": "ship", "title": title, "state": state, "queue": "", "held_until": "", "start_at": "", "priority": "normal",
            "size": "M", "risk": "", "tier": tier, "depends_on": [], "waits_on": [], "waits": None, "needs_you": "",
            "progress": {"done": 0, "total": 0}, "tasks": [], "estimate": None, "by_itself": False, "folded": False,
            "updated": "2026-10-01T10:00:00", **more}


def _tasks(*states):
    return [{"id": f"k{i}", "title": f"Task {i}", "state": s, "after": [], "tier": "warrior",
             "head": {"craft": "engineering", "race": "peon", "tier": "warrior"}} for i, s in enumerate(states, 1)]


# Ordered as the backend gives them: by goal, then tier, then the ones that need the person first.
NODES = [
    node("plan-me", "Draft the pricing page", 1, "plan", needs_you="plan", waits={"kind": "you", "ref": "plan-me", "title": "", "until": ""}),
    node("tables", "Build the tables", 1, "done", progress={"done": 2, "total": 2}, tasks=_tasks("merged", "merged")),
    node("night", "Write the changelog", 1, "raw", queue="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}),
    node("sync", "Sync between phone and town", 2, "working", depends_on=["tables"], checks=[{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "passed"},
                            {"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": True, "why": "", "state": "running"}], progress={"done": 1, "total": 3},
         tasks=_tasks("merged", "running", "waiting")),
    node("old", "Old cleanup", 1, "done", folded=True),
]
MAP = {"goals": [{"slug": "ship", "title": "Ship v1", "priority": "high", "state": "ready", "done_when": ["Tests pass", "Docs read"],
                  "ideas": 5, "done": 2, "usd": 12.4, "team": [{"slug": "product-designer", "name": "Product designer", "head": {"craft": "design", "race": "elf", "tier": "elder"}, "checks": False, "every": False},
                  {"slug": "reviewer", "name": "Reviewer", "head": {"craft": "engineering", "race": "peon", "tier": "elder"}, "checks": True, "every": True}]},
                 {"slug": "docs", "title": "Docs", "priority": "normal", "state": "ready", "done_when": [], "ideas": 0, "done": 0, "usd": None,
                  "verdict": {"met": True, "by": "Growth"}}],
       "nodes": NODES, "edges": [{"from": "tables", "to": "sync"}], "rev": "1"}


ANSWER: dict = {}                                    # what `ideas.map` answers in a test; the full Map by default


@pytest.fixture(autouse=True)
def _map(monkeypatch):
    ANSWER.clear()
    ANSWER.update(MAP)
    real = Stub.commands

    def commands(self):
        def fake(a):
            self.calls.append(("ideas.map", {}))
            return dict(ANSWER)
        return {**real(self), "ideas.map": fake}
    monkeypatch.setattr(Stub, "commands", commands)


@pytest.mark.asyncio
async def test_the_goals_are_tabs_with_how_far_each_is_and_a_goal_is_a_trail_down_to_its_flag(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        goal = page.locator(".map-goal")
        await goal.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "map", "device": "phone"})
        tabs = page.get_by_role("tablist", name="Goals")
        assert [" ".join(t.split()) for t in await tabs.get_by_role("tab").all_inner_texts()] == ["Ship v1 47 %", "Docs met"]   # 2 done of 5 and a third of sync; Docs accepted
        assert await tabs.get_by_role("tab", name="Ship v1").get_attribute("aria-selected") == "true"
        assert await goal.get_attribute("aria-label") == "Ship v1" and "≈$12 so far" in await goal.locator(".map-goal-meta").inner_text()
        start = goal.locator(".trail-start")
        assert "47 %" in await start.inner_text() and "2 of 5 ideas" in await start.inner_text()
        steps = goal.locator(".trail-step")
        assert await steps.count() == 2
        first = [await t.inner_text() for t in await steps.nth(0).locator(".idea-title").all()]
        assert first == ["Draft the pricing page", "Write the changelog"]                      # side by side; the hand first; done not on the trail
        gate = steps.nth(0).locator(".map-row").first
        assert await gate.locator(".trail-mark.is-gate").count() == 1 and "plan ready" in await gate.locator(".map-open").get_attribute("aria-label")   # a gate: ! on its chip
        sync = steps.nth(1).locator('.map-row[data-slug="sync"]')
        assert "working 1/3" in await sync.locator(".map-open").get_attribute("aria-label")
        assert (await sync.locator(".map-open").bounding_box())["height"] <= 48                        # a chip: one line
        tasks = sync.get_by_label("Tasks of Sync between phone and town")
        assert [await t.locator(".map-task-title").inner_text() for t in await tasks.locator(".map-task").all()] == ["Task 2", "Task 3"]
        assert await tasks.locator(".map-task").first.locator("img").count() == 1                      # the head of who does it
        assert "1 done" in await tasks.inner_text()
        assert "The goal" in await goal.locator(".trail-end").inner_text()
        for row in await goal.locator(".trail-step .map-open").all():                         # tap targets of at least 44 px
            assert (await row.bounding_box())["height"] >= 44
        await goal.get_by_text("Done (2)").click()
        await goal.get_by_text("Old cleanup").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)
        await _shot(page, "phone-map-390x844")
        await tabs.get_by_role("tab", name="Docs").click()                                    # another goal: its trail, and the Board's goal
        await page.locator('.map-goal[data-goal="docs"]').wait_for(timeout=WAIT_MS)
        assert "Met · Growth" in await page.locator(".trail-end").inner_text()
        await tabs.get_by_role("tab", name="Ship v1").click()
        await page.locator('.map-goal[data-goal="ship"] .map-row[data-slug="sync"] .map-open').click()
        await page.locator(".screen .sec").first.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "idea", "ref": "sync", "device": "phone", "via": "map"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await page.locator(".map-goal").wait_for(timeout=WAIT_MS)                            # back on the Board: its trails
        assert await page.locator(".pane-head h2", has_text="Board").count() == 1


@pytest.mark.asyncio
async def test_no_project_open_says_open_a_folder_first(fake_repo, monkeypatch):
    ANSWER.clear()
    ANSWER["error"] = "Open a folder first"
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.get_by_text("Open a folder first").wait_for(timeout=WAIT_MS)
        assert await page.locator(".map-goal").count() == 0
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_project_with_no_goal_says_no_goals_yet_with_new_goal(fake_repo, monkeypatch):
    ANSWER.update(goals=[], nodes=[], edges=[])
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.get_by_text("No goals yet.").wait_for(timeout=WAIT_MS)
        await page.locator(".pane").get_by_role("button", name="New goal").last.click()
        await page.get_by_role("dialog", name="New goal").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_phone_map_says_a_goal_s_team_and_an_idea_s_checks(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        team = page.locator('.map-goal[data-goal="ship"] .map-team')
        await team.wait_for(timeout=WAIT_MS)
        assert "Team: Product designer, Reviewer (checks every idea)" in await team.inner_text()
        said = await page.locator('.map-row[data-slug="sync"] .map-open').get_attribute("aria-label")
        assert "checks 1/2" in said
        await _shot(page, "phone-map-team-390x844")
        assert await page.evaluate(NO_SCROLL)
