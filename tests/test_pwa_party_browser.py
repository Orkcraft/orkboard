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
        await page.locator(".ghead").get_by_role("button", name="Open goal Landing page").click()
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


@pytest.mark.asyncio
async def test_new_goal_says_the_price_asks_again_300_ms_after_a_seat_and_each_check_says_what_it_adds(fake_repo, monkeypatch):
    from tests.test_pwa_shell_browser import _new_goal
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        asked = lambda: [c[1] for c in stub.calls if c[0] == "ideas.party_price"]      # noqa: E731
        price = sheet.locator(".party-price")
        await price.wait_for(timeout=WAIT_MS)
        assert " ".join((await price.inner_text()).split()) == "This party: about $2–6 an idea from this project's last 12 ideas"
        stub.learned = False
        before = len(asked())
        await sheet.locator('.craft-tile[data-craft="design"]').click()                      # the craft's party: changes in the seats
        await sheet.locator('.party [data-change="team"]').click()
        await sheet.get_by_role("button", name="Take in: Analyst").click()
        await sheet.get_by_role("button", name="Take in: Copywriter").click()
        for _ in range(100):                                                                 # the last change is asked 300 ms after it
            if asked()[-1]["leader"] == "analyst" and len(asked()) > before:
                break
            await page.wait_for_timeout(100)
        await page.wait_for_function("() => document.querySelector('.party-price')?.innerText.includes('a first guess')", timeout=WAIT_MS)
        assert len(asked()) - before <= 3                                                     # the changes of 300 ms are a call each at most (and the picker's own)
        assert asked()[-1]["leader"] == "analyst"
        assert " ".join((await price.inner_text()).split()) == "This party: about $2–6 an idea a first guess: it learns from this project's ideas"
        await sheet.get_by_role("region", name="Checks").get_by_role("button").first.click()
        mark = sheet.get_by_role("button", name="Take out: Accessibility reviewer").locator(".check-badge")
        assert await mark.text_content() == "checks"                                            # a checker's mark, as the desktop's
        assert await sheet.get_by_role("button", name="Take in: Reviewer").locator(".check-badge").text_content() == "checks"
        await sheet.get_by_role("region", name="Checks").get_by_role("button", name="Done").click()
        await sheet.locator('.party-checks [data-change="checks"]').click()
        block = sheet.get_by_role("group", name="Checks")
        text = " ".join((await block.inner_text()).split())
        assert "adds about $0.35 to an idea it checks · about half of them" in text and "an idea they all apply to" not in text
        await block.get_by_label("Every idea: Accessibility reviewer").check()
        await page.wait_for_function("() => document.querySelector('.checks-block')?.innerText.includes('· every idea')", timeout=WAIT_MS)
        assert asked()[-1]["every"] == ["accessibility-reviewer"]
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_hints_are_quiet_lines_under_the_price_and_never_block_save(fake_repo, monkeypatch):
    """Spec 43 E: muted, one line each, no button; the goal's craft is sent with the party."""
    from tests.test_pwa_shell_browser import _new_goal
    hints = ["Reviewer found nothing in its last 12 checks.", "No one in the party writes code: code tasks go to this project's agent for code (the Grunt when none)."]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.hints = list(hints)
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        await sheet.locator(".party-hint").first.wait_for(timeout=WAIT_MS)
        assert await sheet.locator(".party-hint").all_inner_texts() == hints
        assert await sheet.locator(".party-hint button, .party-hint a").count() == 0
        asked = [c[1] for c in stub.calls if c[0] == "ideas.party_price"]
        assert asked[0].get("craft") == "engineering"
        await sheet.get_by_label("Description").fill("A goal that saves with its hints.")
        assert await sheet.get_by_role("button", name="Save goal").is_enabled()                  # a hint never blocks Save
        assert await page.evaluate(NO_SCROLL)
