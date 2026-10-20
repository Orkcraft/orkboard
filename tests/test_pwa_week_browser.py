"""Spec 42 F on the phone (docs/specs/42-coming-back.md §6, Tests → F): the drawer's *Spend today* row opens the This week sheet with its
lines in order; *Nothing waits for tonight* and New idea."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _menu, _phone  # noqa: E402,F401

WEEK = {"usd": 46.1, "ops_usd": 3.2, "merged": 12, "first_time": 10, "usd_per_merged": 3.84, "nights": {"worked": 4, "idle": 2, "off": 1},
        "tonight": 0, "night_on": True, "into": "dev"}
ANSWER: dict = {}


@pytest.fixture(autouse=True)
def _week(monkeypatch):
    ANSWER.clear()
    ANSWER.update(WEEK)
    real = Stub.commands

    def commands(self):
        def fake(a):
            self.calls.append(("ideas.week_work", {}))
            return dict(ANSWER)
        return {**real(self), "ideas.week_work": fake}
    monkeypatch.setattr(Stub, "commands", commands)


async def _sheet(page):
    drawer = await _menu(page)
    row = drawer.locator(".board-spend__open")
    assert (await row.get_attribute("aria-label")).startswith("Spend today: $") and (await row.get_attribute("aria-label")).endswith(". This week’s work")
    await row.click()
    sheet = page.get_by_role("dialog", name="This week")
    await sheet.locator(".week p").first.wait_for(timeout=WAIT_MS)
    return sheet


@pytest.mark.asyncio
async def test_the_spend_row_opens_this_week_with_its_lines_in_order_and_new_idea(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["ship"] = stub.goal("ship", "Ship v1", "normal", "ready")                       # New idea needs a goal (spec 35 §3)
        reads = len([c for c in stub.calls if c[0] == "ideas.board"])
        stub.bump({})
        for _ in range(100):                                                                         # the Board reads its goals again
            if len([c for c in stub.calls if c[0] == "ideas.board"]) > reads:
                break
            await page.wait_for_timeout(100)
        await page.wait_for_timeout(600)
        sheet = await _sheet(page)
        lines = [" ".join(t.split()) for t in await sheet.locator(".week p").all_text_contents()]
        assert lines == ["≈$46 of work at API prices in this project, ≈$3 in Operations: not your bill",
                         "12 results in dev, 10 the first time · ≈$3.84 a result",
                         "The last 7 nights: 4 with work done, 2 with none, 1 Orkline was not running", "Nothing waits for tonight · New idea"]
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "week", "ref": "this", "device": "phone"})
        assert await page.evaluate(NO_SCROLL)
        await sheet.get_by_role("button", name="New idea").click()
        await page.get_by_role("dialog", name="New idea").wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_tonight_says_how_many_wait(fake_repo, monkeypatch):
    ANSWER.update(tonight=3, ops_usd=None)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _sheet(page)
        lines = [" ".join(t.split()) for t in await sheet.locator(".week p").all_text_contents()]
        assert lines[0] == "≈$46 of work at API prices in this project: not your bill" and lines[-1] == "Tonight: 3 wait"


# -- spec 42 G: Last week ----------------------------------------------------------------------------------------------

import datetime as dt  # noqa: E402
import json  # noqa: E402

from tests.test_pwa_recap_browser import RECAP  # noqa: E402

LAST = {"week": "2026-W42", "from": "2026-10-12", "to": "2026-10-18", "into": "dev", "merged": 23, "first_time": 19, "usd": 61.2, "usd_per_merged": 2.66,
        "before": {"merged": 14, "first_time": 10, "usd_per_merged": 3.1},
        "goals": [{"goal": "general", "short": "Offline mode", "title": "Offline mode", "done": 3}, {"goal": "ship", "short": "Billing", "title": "Billing", "done": 1}],
        "flags": [{"goal": "general", "short": "Offline mode", "title": "Offline mode", "met": True, "by": "Product manager"}],
        "dearest": {"slug": "sync", "short": "Offline mode", "title": "Offline mode", "usd": 12.0},
        "fastest": {"slug": "dark", "short": "Export CSV", "title": "Export CSV", "minutes": 42},
        "answers": {"answers": 12, "recommended": 9, "decided": 2}, "nights": {"worked": 5, "idle": 2, "off": 0}, "streak": 0, "empty": False}
LASTS: dict = {}


@pytest.fixture(autouse=True)
def _last(monkeypatch):
    LASTS.clear()
    LASTS.update(LAST)
    real = Stub.commands

    def commands(self):
        def week(a):
            self.calls.append(("ideas.week", {}))
            return dict(LASTS)

        def recap(a):
            self.calls.append(("ideas.recap", {}))
            return dict(RECAP)
        return {**real(self), "ideas.week": week, "ideas.recap": recap}
    monkeypatch.setattr(Stub, "commands", commands)


def _iso(days_ago):
    year, week, _d = (dt.date.today() - dt.timedelta(days=days_ago)).isocalendar()
    return f"{year}-W{week:02d}"


def _seed(repo, week=None, look_hours=None):
    out = ""
    if week:
        key = json.dumps(f"orkboard.week.{repo.name}")
        out += f"if (!localStorage.getItem({key})) localStorage.setItem({key}, {json.dumps(week)});"
    if look_hours is not None:
        key = json.dumps(f"orkboard.look.{repo.name}")
        out += f"if (!localStorage.getItem({key})) localStorage.setItem({key}, String(Date.now() - {look_hours} * 3600 * 1000));"
    return out


@pytest.mark.asyncio
async def test_the_first_look_of_a_new_week_shows_last_weeks_card_then_the_recap(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=_seed(fake_repo, _iso(14), 9)) as (stub, page):
        card = page.get_by_label("Last week")
        await card.wait_for(timeout=WAIT_MS)
        assert " ".join((await card.locator(".away-head h3").text_content()).split()) == "Last week · 12–18 October"
        assert [" ".join(t.split()) for t in await card.locator(".away-lines p").all_text_contents()] == [
            "23 results in dev, 19 the first time (83 %; the week before 71 %)", "≈$2.66 a result (the week before ≈$3.10)",
            "Goals: Offline mode, 3 ideas done · Billing, 1", "Flags: Offline mode, met",
            "Cost the most: Offline mode, ≈$12 · Fastest from idea to dev: Export CSV, 42 min",
            "Questions: 9 of 12 answers were the recommended one; 2 cards left to the Taskmaster", "Nights: 5 with work done, 2 with none"]
        assert await page.get_by_label("While you were away").count() == 0                          # the week's card first
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "week", "ref": "2026-W42", "device": "phone"})
        assert await page.evaluate(NO_SCROLL)
        await card.get_by_role("button", name="Close").click()
        await page.get_by_label("While you were away").wait_for(timeout=WAIT_MS)                    # then the recap's
        assert json.loads(await page.evaluate(f"JSON.stringify(localStorage.getItem({json.dumps('orkboard.week.' + fake_repo.name)}))")) == _iso(7)
        await page.get_by_label("While you were away").get_by_role("button", name="Close").click()


@pytest.mark.asyncio
async def test_no_key_writes_it_and_the_drawers_row_shows_the_card_any_time(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        for _ in range(50):
            if await page.evaluate(f"localStorage.getItem({json.dumps('orkboard.week.' + fake_repo.name)})") is not None:
                break
            await page.wait_for_timeout(100)
        assert await page.get_by_label("Last week").count() == 0 and not any(c[0] == "ideas.week" for c in stub.calls)
        drawer = await _menu(page)
        await drawer.get_by_role("button", name="Last week", exact=True).click()
        card = page.get_by_label("Last week")
        await card.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "week", "ref": "2026-W42", "device": "phone", "via": "map"})
        await card.get_by_role("button", name="Close").click()
        assert await card.count() == 0
