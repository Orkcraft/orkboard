"""Spec 39 part C on the phone (docs/specs/39-map.md §5, "Tests → C"): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py with a fake `ideas.map`. The Board's Map button opens the Map; a goal's ideas in tier order with their
dots, words, pips and *after …*; a row that needs the person first in its tier; a tap opens the idea, logged `via: "map"`;
no horizontal scroll."""
from __future__ import annotations

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _phone, _pick_goal, _shot  # noqa: F401


async def _open_map(page):
    """The Map: a row of the top bar's Goals sheet."""
    await page.locator(".board-bar .goal-chip").click()
    await page.get_by_role("dialog", name="Goals").locator('.goal-row[data-goal="map"]').click()

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser


def node(slug, title, tier, state, **more):
    return {"slug": slug, "goal": "ship", "title": title, "state": state, "queue": "", "held_until": "", "start_at": "", "priority": "normal",
            "size": "M", "risk": "", "tier": tier, "depends_on": [], "waits_on": [], "waits": None, "needs_you": "",
            "progress": {"done": 0, "total": 0}, "tasks": [], "estimate": None, "by_itself": False, "folded": False,
            "updated": "2026-10-01T10:00:00", **more}


def _tasks(*states):
    return [{"id": f"k{i}", "title": f"Task {i}", "state": s, "after": [], "tier": "warrior"} for i, s in enumerate(states, 1)]


# Ordered as the backend gives them: by goal, then tier, then the ones that need the person first.
NODES = [
    node("plan-me", "Draft the pricing page", 1, "plan", needs_you="plan", waits={"kind": "you", "ref": "plan-me", "title": "", "until": ""}),
    node("tables", "Build the tables", 1, "done", progress={"done": 2, "total": 2}, tasks=_tasks("merged", "merged")),
    node("night", "Write the changelog", 1, "raw", queue="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}),
    node("sync", "Sync between phone and town", 2, "working", depends_on=["tables"], progress={"done": 1, "total": 3},
         tasks=_tasks("merged", "running", "waiting")),
    node("old", "Old cleanup", 1, "done", folded=True),
]
MAP = {"goals": [{"slug": "ship", "title": "Ship v1", "priority": "high", "state": "ready", "done_when": ["Tests pass", "Docs read"],
                  "ideas": 5, "done": 2, "usd": 12.4}],
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
async def test_the_map_button_opens_the_map_and_a_tap_opens_the_idea(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        goal = page.locator(".map-goal")
        await goal.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "map", "device": "phone"})
        assert "Ship v1" in await goal.locator("h3").inner_text()
        head = await goal.locator(".map-goal-meta").inner_text()
        assert "2 of 5 done" in head and "≈$12 so far" in head
        rows = goal.locator(":scope > .map-ideas > .map-row")
        titles = [await r.locator(".idea-title").inner_text() for r in await rows.all()]
        assert titles == ["Draft the pricing page", "Build the tables", "Write the changelog", "Sync between phone and town"]   # tiers; the hand first
        assert "Old cleanup" not in " ".join(titles)
        first, sync = rows.nth(0), rows.nth(3)
        assert "plan ready" in await first.inner_text() and await first.locator(".map-hand").count() == 1       # needs the person's hand
        assert await first.locator(".map-dots").get_attribute("aria-label") == "Tier 1 of 2"
        assert await sync.locator(".map-dots").get_attribute("aria-label") == "Tier 2 of 2"
        assert "○●" in await sync.locator(".map-dots").inner_text()
        text = await sync.inner_text()
        assert "working 1/3" in text and "after Build the tables" in text
        assert await sync.locator(".pip").count() == 3 and await sync.locator(".pip-done").count() == 1 and await sync.locator(".pip-work").count() == 1
        assert "tonight" in await rows.nth(2).inner_text()
        css = "(el) => { const c = getComputedStyle(el); return [c.borderTopWidth, c.borderTopStyle]; }"
        assert await first.evaluate(css) == ["3px", "solid"]                      # needs your hand: the heavier frame
        assert await rows.nth(2).evaluate(css) == ["1px", "dashed"]               # waits: dashed
        for i in range(4):                                                         # tap targets of at least 44 px
            assert (await rows.nth(i).locator(".map-open").bounding_box())["height"] >= 44
        await goal.get_by_text("Done (1)").click()
        await goal.get_by_text("Old cleanup").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)
        await _shot(page, "phone-map-390x844")
        await sync.locator(".map-open").click()
        await page.locator(".screen .sec").first.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "idea", "ref": "sync", "device": "phone", "via": "map"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await page.locator(".map-goal").wait_for(timeout=WAIT_MS)                        # back on the Map
        await page.locator(".goal-pick").get_by_role("button", name="Board").click()
        await page.locator(".pane-head h2", has_text="Board").wait_for(timeout=WAIT_MS)
        assert await page.locator(".map-goal").count() == 0


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
