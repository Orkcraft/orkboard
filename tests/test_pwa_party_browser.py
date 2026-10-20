"""Spec 43 B on the phone (docs/specs/43-party-measured.md §2.3, Tests → B): a goal's screen has *What the party did* under its Team, closed at
first and read when opened. (The same fold under a flag's row is in tests/test_pwa_map39_browser.py.)"""
from __future__ import annotations

import copy

import pytest

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from tests.test_pwa_goal_team_browser import _pick_goal  # noqa: E402,F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _phone  # noqa: E402,F401
from tests.test_shell_browser import PARTY, PARTY_LINES  # noqa: E402


@pytest.mark.asyncio
async def test_the_goal_s_screen_has_what_the_party_did_closed_at_first_and_read_when_opened(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.party = copy.deepcopy(PARTY)
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="marketing", race="gnome", team=["copywriter"],
                                       leader=stub.leader("growth"), metrics=[])
        stub.bump({})
        await _pick_goal(page, "land")
        await page.locator('.map-goal[data-goal="land"]').get_by_role("button", name="Open goal Landing page").click()
        fold = page.locator(".screen").get_by_role("region", name="What the party did").locator("details")
        await fold.wait_for(timeout=WAIT_MS)
        assert await fold.get_attribute("open") is None and not any(c[0] == "ideas.party" for c in stub.calls)     # closed at first: not asked for
        await fold.locator("summary").click()
        await page.wait_for_function("() => document.querySelectorAll('.screen .party-work li').length === 4", timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in await fold.locator("li").all_inner_texts()] == PARTY_LINES
        assert await _called(stub, "ideas.party", {"goal": "land"})
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "party", "ref": "land", "device": "phone"})
        assert await page.evaluate(NO_SCROLL)
        stub.party = {"ideas": 0, "leader": PARTY["leader"], "members": [], "checks": []}
        await fold.locator("summary").click()
        await fold.locator("summary").click()
        await page.get_by_text("No work yet", exact=True).wait_for(timeout=WAIT_MS)
