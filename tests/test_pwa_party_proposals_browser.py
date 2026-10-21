"""Spec 43 D on the phone (docs/specs/43-party-measured.md §4, Tests → D): the party's proposal, a stop along the bottom (spec 49 §6) with *Take it out* and
*Keep it* and a line for why not; a checker's muted line and its sheet's *Its check* line."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _agents, _called, _phone, _pop  # noqa: E402,F401

ROW = {"idea": "", "goal": "general", "kind": "party", "by": "reviewer", "title": "Take Reviewer out of Billing's party?",
       "text": "It found nothing in the last 8 ideas; a check costs about $0.35.", "priority": "normal", "blocks": False, "at": "2026-10-20T03:00:00"}
HEAD = {"craft": "engineering", "race": "peon", "tier": "elder"}


@pytest.mark.asyncio
async def test_the_party_proposal_is_a_stop_answered_where_it_is_and_the_row_counts_it(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        hand = page.locator(".hc")
        before = await hand.count()
        stub.extra_needs.append(dict(ROW))
        stub.bump({})
        row = await _pop(page, "Proposed: Take Reviewer out of Billing's party?")
        text = await row.inner_text()
        assert "Take Reviewer out of Billing's party?" in text and "It found nothing in the last 8 ideas; a check costs about $0.35." in text
        await row.get_by_role("button", name="Put it back").click()
        await row.wait_for(state="hidden", timeout=WAIT_MS)
        assert await hand.count() == before + 1                                                             # it waits for the person like the others: one more along the bottom
        assert await page.evaluate(NO_SCROLL)
        row = await _pop(page, "Proposed: Take Reviewer out of Billing's party?")
        await row.get_by_label("Why not: Take Reviewer out of Billing's party?").fill("the public page needs it")
        await row.get_by_role("button", name="Keep it").click()
        assert await _called(stub, "ideas.party_answer", {"goal": "general", "take": False, "reason": "the public page needs it"})
        await page.locator('.hc[data-kind="party"]').wait_for(state="detached", timeout=WAIT_MS)
        stub.extra_needs.append(dict(ROW))
        stub.bump({})
        row = await _pop(page, "Proposed: Take Reviewer out of Billing's party?")
        await row.get_by_role("button", name="Take it out").click()
        assert await _called(stub, "ideas.party_answer", {"goal": "general", "take": True})


@pytest.mark.asyncio
async def test_a_checker_s_line_and_sheet_say_its_check(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.roles["reviewer"] = {"slug": "reviewer", "name": "Reviewer", "model": "elder", "max_parallel": 1, "instruction": "", "builtin": False, "head": HEAD}
        stub.check_week = {"reviewer": {"checks": 6, "clean": 4, "caught": 2, "left": 1, "usd_per_check": None}}
        stub.record = {"reviewer": {"days": 30, "finished": 14, "merged": 14, "first_time": 14, "usd_per_merged": None,
                                    "check": {"checks": 14, "clean": 11, "caught": 3, "left": 1, "usd_per_check": 0.35}}}
        stub.bump({})
        await page.wait_for_timeout(800)
        agents = await _agents(page)
        facts = agents.locator(".role[data-slug='reviewer'] .role-facts")
        await facts.wait_for(timeout=WAIT_MS)
        assert await facts.inner_text() == "its check: 6 goals, caught 2"
        await agents.get_by_role("button", name="Edit Reviewer").click()
        sheet = page.get_by_role("dialog", name="Edit agent")
        assert " ".join((await sheet.get_by_label("Its check", exact=True).text_content()).split()) == "Its check, the last 30 days: 14 goals: 11 clean, caught 3 · ≈$0.35 a check"
        await sheet.get_by_role("button", name="Cancel").click()
        stub.record["reviewer"]["check"] = {"checks": 2, "clean": 2, "caught": 0, "left": 0, "usd_per_check": None}
        read = len([c for c in stub.calls if c[0] == "ideas.roles"])
        stub.bump({})
        for _ in range(100):                                                                         # the phone reads the Board again on the next snapshot
            if len([c for c in stub.calls if c[0] == "ideas.roles"]) > read:
                break
            await page.wait_for_timeout(100)
        await page.wait_for_timeout(200)
        await agents.get_by_role("button", name="Edit Reviewer").click()
        assert " ".join((await sheet.get_by_label("Its check", exact=True).text_content()).split()) == "Its check, the last 30 days: 2 goals: too few to say more"
        await sheet.get_by_role("button", name="Cancel").click()
        await agents.get_by_role("button", name="Edit Grunts").click()
        assert await sheet.get_by_label("Its check", exact=True).is_hidden()
