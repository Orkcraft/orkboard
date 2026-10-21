"""The lens of New idea on the phone (shell-lens.js, shell-lens-screen.js; realm/idea_lens.py): the goal's party's lenses,
its leader's open first; a product manager's pain, an engineer's parts of the repository, a designer's screen with areas
marked; the text alone always enough. In Chromium at 390 x 844; the Board is the stub's (tests/test_pwa_shell_browser.py)."""
from __future__ import annotations

import base64

import pytest

from tests.test_pwa_idea_field_browser import _png
from tests.test_pwa_shell_browser import _dial, _open_idea, NO_SCROLL, WAIT_MS, _called, _phone, _pick_goal, _shot  # noqa: F401

pytestmark = pytest.mark.browser

PARTY = {"lenses": [{"id": "text"}, {"id": "code", "by": "Architect", "slug": "architect"},
                    {"id": "screen", "by": "UI kit designer", "slug": "ui-kit"}, {"id": "pain", "by": "Product manager", "slug": "product-manager"}],
         "default": "pain", "segments": [{"segment": "Shop owners", "pains": ["Orders get lost", "Refunds take a week"]}],
         "screens": [{"id": "abc123", "name": "Orders"}]}
PARTS = [{"path": "app", "files": ["main.py"], "count": 1, "uses": ["app/core"], "used_by": []},
         {"path": "app/core", "files": ["bus.py", "__init__.py"], "count": 2, "uses": [], "used_by": ["app"]},
         {"path": "web", "files": ["app.js"], "count": 1, "uses": [], "used_by": []}]


async def _new_idea(stub, page, lens=PARTY):
    stub.goals["ship"] = stub.goal("ship", "Ship v1", "normal", "ready")
    stub.lens, stub.parts = lens, PARTS
    stub.screen_png = base64.b64encode(_png(390, 300)).decode()
    stub.bump({})
    await _pick_goal(page, "ship")                                                                      # the goal is on the phone and shown
    await _dial(page, "New idea")                                                                       # the create button's first item
    sheet = page.get_by_role("dialog", name="New idea")
    await sheet.wait_for(timeout=WAIT_MS)
    assert await _called(stub, "ideas.lens", {"track": "ship"})
    return sheet


@pytest.mark.asyncio
async def test_the_leader_s_lens_is_open_first_and_each_lens_points_its_way_and_goes_with_the_idea(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _new_idea(stub, page)
        bar = sheet.get_by_role("radiogroup", name="Lens")
        await bar.get_by_role("radio", name="Pain").wait_for(timeout=WAIT_MS)
        assert await bar.get_by_role("radio", name="Pain").get_attribute("aria-checked") == "true"      # the leader's: a product manager
        assert [await r.get_attribute("aria-label") for r in await bar.get_by_role("radio").all()] == [
            "Text", "Code · Architect", "Screen · UI kit designer", "Pain · Product manager"]
        await sheet.get_by_label("The idea", exact=True).fill("Orders are never lost")
        await sheet.get_by_role("group", name="Kept segments").get_by_role("button", name="Shop owners").click()     # the project's own
        await sheet.get_by_role("group", name="Their pains").get_by_role("button", name="Orders get lost").click()
        await _shot(page, "phone-lens-pain-390x844")
        await bar.get_by_role("radio", name="Code").click()                                               # the architect's
        await sheet.get_by_role("button", name="Pick: app/core").click()
        assert "is-near" in await sheet.get_by_role("button", name="Pick: app", exact=True).get_attribute("class")   # what uses it, nearby
        await sheet.get_by_label("What to change there").fill("Keep each order until the till has it")
        await _shot(page, "phone-lens-code-390x844")
        await bar.get_by_role("radio", name="Screen").click()                                             # the designer's
        await sheet.get_by_role("group", name="The project's screens").get_by_role("button", name="Orders").click()
        assert await _called(stub, "ideas.lens_screen", {"id": "abc123"})
        stage = sheet.locator(".lens-stage")
        await stage.wait_for(timeout=WAIT_MS)
        await stage.scroll_into_view_if_needed()
        box = await sheet.locator(".lens-shot").bounding_box()
        await page.mouse.move(box["x"] + box["width"] * 0.1, box["y"] + box["height"] * 0.2)
        await page.mouse.down()
        await page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.4, steps=4)
        await page.mouse.up()
        await sheet.get_by_label("Mark 1: what to change").fill("Say which orders wait")
        await _shot(page, "phone-lens-screen-390x844")
        await sheet.get_by_role("button", name="Add", exact=True).click()
        await page.get_by_role("dialog", name="New idea").wait_for(state="hidden", timeout=WAIT_MS)
        sent = next(a for n, a in stub.calls if n == "ideas.add")
        assert [x["kind"] for x in sent["lens"]] == ["pain", "code", "screen"]
        assert sent["lens"][0] == {"kind": "pain", "segment": "Shop owners", "pain": "Orders get lost"}
        assert sent["lens"][1] == {"kind": "code", "paths": ["app/core"], "note": "Keep each order until the till has it"}
        mark = sent["lens"][2]["marks"][0]
        assert sent["lens"][2]["screen"] == "abc123" and mark["note"] == "Say which orders wait"
        assert abs(mark["x"] - 0.1) < 0.03 and abs(mark["w"] - 0.4) < 0.03 and abs(mark["y"] - 0.2) < 0.03
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_with_the_taskmaster_leading_text_is_open_first_and_the_text_alone_goes(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _new_idea(stub, page, {"lenses": [{"id": "text"}, {"id": "screen", "by": "Artist"}], "default": "text",
                                             "segments": [], "screens": []})
        bar = sheet.get_by_role("radiogroup", name="Lens")
        await bar.get_by_role("radio", name="Text", exact=True).wait_for(timeout=WAIT_MS)
        assert await bar.get_by_role("radio", name="Text", exact=True).get_attribute("aria-checked") == "true"
        await sheet.get_by_label("The idea", exact=True).fill("A darker theme")
        await sheet.get_by_role("button", name="Add", exact=True).click()
        assert await _called(stub, "ideas.add", {"text": "A darker theme", "track": "ship", "priority": "normal"})   # no lens: none sent
        stub.ideas["page"] = stub.idea("page", "The orders page", "ready", 3, track="ship",
                                       lens=[{"kind": "pain", "segment": "Shop owners", "pain": "Orders get lost"},
                                             {"kind": "code", "paths": ["app/core"], "note": "Keep each order"}])
        stub.bump({})
        await _open_idea(page, "The orders page")
        pointed = page.locator(".screen").get_by_role("list", name="Pointed at")
        await pointed.wait_for(timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in await pointed.get_by_role("listitem").all_inner_texts()] == [
            "Pain · Shop owners Orders get lost", "Code · app/core Keep each order"]
