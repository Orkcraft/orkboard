"""Spec 43 A on the phone (docs/specs/43-party-measured.md §1.4, §1.5, Tests → A): a check's result in Review says what it found, with *Fix them*
and *Leave them*; the idea's Checks say *clean* and *found 2: 1 fixed, 1 left*."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from tests.test_pwa_goal_team_browser import _pick_goal  # noqa: E402,F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _phone  # noqa: E402,F401
from tests.test_shell_browser import GREEN, task  # noqa: E402

NO_RUN = {"passed": 0, "failed": 0, "failing": [], "tail": "", "green": True, "ran": False, "command": ""}
FOUND = [{"where": "sync.py:41", "what": "a lost signal is not retried", "fixed": True},
         {"where": "queue.py:9", "what": "the queue is never emptied", "fixed": False},
         {"where": "the Sync screen", "what": "no way to cancel", "fixed": False}]


def with_checks(stub):
    stub.plan["tasks"] += [
        task("k6", "Check: Reviewer", "review", ["k5"], kind="review", tests=NO_RUN, diff={"files": 0, "added": 0, "removed": 0}, check="Reviewer",
             findings=FOUND, note="2 left"),
        task("k7", "Check: Accessibility reviewer", "review", ["k5"], kind="a11y", tests=GREEN, diff={"files": 1, "added": 3, "removed": 0},
             check="Accessibility reviewer", findings=[{"where": "a.css:3", "what": "low contrast", "fixed": True}])]


@pytest.mark.asyncio
async def test_a_check_s_card_says_what_it_found_and_fix_them_and_leave_them_answer(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, ) as (stub, page):
        with_checks(stub)
        stub.rev += 1
        await page.get_by_role("tab", name="Needs you").click()
        card = page.locator(".result", has_text="Check: Reviewer")
        await card.wait_for(timeout=WAIT_MS)
        assert await card.locator(".found-sum").inner_text() == "Found 3: 1 fixed, 2 left"
        assert [" ".join(t.split()) for t in await card.locator(".found-list li").all_inner_texts()] == [
            "queue.py:9 · the queue is never emptied", "the Sync screen · no way to cancel"]
        assert await card.get_by_role("button", name="Fix them").is_enabled() and await card.get_by_role("button", name="Leave them").is_enabled()
        assert await card.get_by_role("button", name="Drop…").count() == 1
        assert await card.get_by_role("button", name="Merge into dev").count() == 0 and await card.get_by_role("button", name="Send back").count() == 0
        other = page.locator(".result", has_text="Check: Accessibility reviewer")                    # nothing left: today's card
        assert await other.locator(".found").count() == 0 and await other.get_by_role("button", name="Merge into dev").is_enabled()
        assert await page.evaluate(NO_SCROLL)
        await card.get_by_role("button", name="Fix them").click()
        assert await _called(stub, "ideas.back", {"slug": "sync", "task": "k6",
                                                  "why": "Fix the findings left:\nqueue.py:9: the queue is never emptied\nthe Sync screen: no way to cancel"})


@pytest.mark.asyncio
async def test_leave_them_is_the_merge_and_the_result_screen_says_what_was_found(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        with_checks(stub)
        stub.rev += 1
        await page.get_by_role("tab", name="Needs you").click()
        card = page.locator(".result", has_text="Check: Reviewer")
        await card.wait_for(timeout=WAIT_MS)
        await card.locator(".result-open").click()
        screen = page.locator(".screen")
        await screen.locator(".found-sum").wait_for(timeout=WAIT_MS)
        assert await screen.locator(".found-sum").inner_text() == "Found 3: 1 fixed, 2 left"
        await screen.get_by_role("button", name="Leave them").click()
        assert await _called(stub, "ideas.merge", {"slug": "sync", "task": "k6"})


@pytest.mark.asyncio
async def test_the_idea_s_checks_say_clean_or_found_with_what_was_fixed_and_left(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.checks = [{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "passed", "found": 0, "fixed": 0, "left": 0},
                       {"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": True, "why": "", "state": "passed", "found": 2, "fixed": 1,
                        "left": 1}]
        await _pick_goal(page, "general")
        await page.locator(".map-row", has_text="Sync ideas").locator(".map-open").click()
        line = page.locator(".screen").get_by_role("list", name="Checks")
        await line.wait_for(timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in await line.get_by_role("listitem").all_inner_texts()] == [
            "Reviewer clean", "Accessibility reviewer found 2: 1 fixed, 1 left"]
