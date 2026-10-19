"""Who does a task on the phone (decisions §53; the desktop's tests/test_races_browser.py): Agents at 390 × 844 with each agent's
head (its craft's race in its tier's gear) beside its name and each card's head, the agent's sheet picking the craft and showing
the head it will wear, the Agents tab an ork; every head is served beside the app's files. Against the stub of
test_pwa_shell_browser.py with the host's heads."""
from __future__ import annotations

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _phone, _shot  # noqa: F401
from tests.test_races_browser import MINE, _heads

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser


def _with_heads(stub):
    stub.roles.update({k: dict(v) for k, v in MINE.items()})
    run = stub.run
    stub.run = lambda name, a: _heads(name, run(name, a), stub.roles, a)       # the commands call stub.run when they run
    stub.bump({})


async def _drawn(page, selector):
    return await page.evaluate(f"[...document.querySelectorAll({selector!r})].every((i) => i.complete && i.naturalWidth > 0)")


@pytest.mark.asyncio
async def test_agents_wear_their_races_the_cards_their_runners_and_the_tab_is_a_robot(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _with_heads(stub)
        tab = page.get_by_role("tab", name="Agents")
        assert await tab.locator("img").count() == 0                                                      # a head says a craft: the tab is orkUI's robot
        assert (await tab.locator("svg.ork-icon use").get_attribute("href")).endswith("#robot")
        await tab.click()
        agents = page.locator(".agents")
        await agents.locator(".role[data-slug=layout]").wait_for(timeout=WAIT_MS)
        head = lambda slug: agents.locator(f".role[data-slug={slug}] .role-head > img.ork-race__head")       # noqa: E731
        assert await head("layout").get_attribute("src") == "races/elf-elder.png"
        assert await head("seer").get_attribute("src") == "races/goblin-warrior.png"
        assert await head("herald").get_attribute("src") == "races/gnome-laborer.png"
        assert await head("grunt").get_attribute("src") == "races/peon-warrior.png"
        assert (await head("layout").bounding_box())["width"] == 24
        assert (await agents.locator(".role[data-slug=seer] .role-facts").inner_text()).startswith("Data · By Target, now Seasoned")
        card = agents.locator(".role[data-role=grunt] .chip").first
        assert await card.locator("img.ork-race__head").get_attribute("src") == "races/peon-warrior.png"
        assert (await card.locator("img.ork-race__head").bounding_box())["width"] == 12              # an accent: a cell a pixel
        assert await _drawn(page, "img.ork-race__head")
        assert await page.evaluate(NO_SCROLL)
        await _shot(page, "phone-agents-races-390x844")


@pytest.mark.asyncio
async def test_the_agents_sheet_picks_the_craft_and_shows_the_head_it_will_wear(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _with_heads(stub)
        await page.get_by_role("tab", name="Agents").click()
        await page.locator(".agents .role[data-slug=layout]").wait_for(timeout=WAIT_MS)
        await page.get_by_role("button", name="+ Add agent").click()
        sheet = page.get_by_role("dialog", name="Add agent")
        await sheet.get_by_label("Name").fill("Counter")
        craft = sheet.get_by_label("Craft")
        assert [" ".join((await o.text_content()).split()) for o in await craft.locator("option").all()] == [
            "Engineering: an ork", "Design: an elf", "Data: a goblin", "Marketing: a gnome"]
        await craft.select_option("data")
        await sheet.get_by_label("Model").select_option("laborer")
        assert await sheet.locator(".craft-now img.ork-race__head").get_attribute("src") == "races/goblin-laborer.png"
        assert "Novice" in await sheet.locator(".craft-now").inner_text()
        await sheet.get_by_role("button", name="Save agent").click()
        assert await _called(stub, "ideas.role_save", {"name": "Counter", "model": "laborer", "max_parallel": 2, "instruction": "", "kinds": [],
                                                       "craft": "data"})
