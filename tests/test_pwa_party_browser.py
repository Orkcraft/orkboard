"""Spec 43 B on the phone (docs/specs/43-party-measured.md §2.3, Tests → B), in spec 50's words: a party's screen has *What the party did* under its members,
closed at first and read when opened. (The same fold under a flag's row is in tests/test_pwa_map39_browser.py.) Spec 63 C (docs/specs/63-party-gathered.md §2, §5 "C"), 390 × 844:
under the price of New party's sheet, and of The party's, *It can take:* the goal types the seats would be offered (each its sign and name, *with one more:* those that need someone,
three lines at most then *and k more*), a type the last change opened lit once, nothing lit by the first answers, none under reduced motion, no line from an older host."""
from __future__ import annotations

import copy

import pytest

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from orkboard.realm import goal_types, library  # noqa: E402
from tests.test_pwa_goal_team_browser import _pick_goal  # noqa: E402,F401
from tests.test_pwa_mixed_parties_browser import _sheet, hosted  # noqa: E402
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _open_party, _phone  # noqa: E402,F401
from tests.test_shell_browser import PARTY, PARTY_LINES  # noqa: E402


def fixed(line):
    """The desktop's lines say *the party* and *goals* too (spec 50 §0); a copy of them from before is said the same."""
    return line.replace("for the goal, the drafts", "for the party, the drafts").replace("checked 6 ideas", "checked 6 goals").replace("checked 1 idea:", "checked 1 goal:")


@pytest.mark.asyncio
async def test_the_party_s_screen_has_what_the_party_did_closed_at_first_and_read_when_opened(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.party = copy.deepcopy(PARTY)
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="marketing", race="gnome", team=["copywriter"],
                                       leader=stub.leader("growth"), metrics=[])
        stub.bump({})
        await _pick_goal(page, "land")
        await _open_party(page, "Landing page")
        fold = page.locator(".screen").get_by_role("region", name="What the party did").locator("details")
        await fold.wait_for(timeout=WAIT_MS)
        assert await fold.get_attribute("open") is None and not any(c[0] == "ideas.party" for c in stub.calls)     # closed at first: not asked for
        await fold.locator("summary").click()
        await page.wait_for_function("() => document.querySelectorAll('.screen .party-work li').length === 4", timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in await fold.locator("li").all_inner_texts()] == [fixed(l) for l in PARTY_LINES]
        assert await _called(stub, "ideas.party", {"goal": "land"})
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "party", "ref": "land", "device": "phone"})
        assert await page.evaluate(NO_SCROLL)
        stub.party = {"ideas": 0, "leader": PARTY["leader"], "members": [], "checks": []}
        await fold.locator("summary").click()
        await fold.locator("summary").click()
        await page.get_by_text("No work yet", exact=True).wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_new_party_says_the_price_asks_again_300_ms_after_a_seat_and_each_check_says_what_it_adds(fake_repo, monkeypatch):
    from tests.test_pwa_shell_browser import _new_goal
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New party")
        asked = lambda: [c[1] for c in stub.calls if c[0] == "ideas.party_price"]      # noqa: E731
        price = sheet.locator(".party-price")
        await price.wait_for(timeout=WAIT_MS)
        assert " ".join((await price.inner_text()).split()) == "This party: about $2–6 a goal from this project's last 12 goals"
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
        assert " ".join((await price.inner_text()).split()) == "This party: about $2–6 a goal a first guess: it learns from this project's goals"
        await sheet.get_by_role("region", name="Checks").get_by_role("button").first.click()
        mark = sheet.get_by_role("button", name="Take out: Accessibility reviewer").locator(".check-badge")
        assert await mark.text_content() == "checks"                                            # a checker's mark, as the desktop's
        assert await sheet.get_by_role("button", name="Take in: Reviewer").locator(".check-badge").text_content() == "checks"
        await sheet.get_by_role("region", name="Checks").get_by_role("button", name="Done").click()
        await sheet.locator('.party-checks [data-change="checks"]').click()
        block = sheet.get_by_role("group", name="Checks")
        text = " ".join((await block.inner_text()).split())
        assert "adds about $0.35 to a goal it checks · about half of them" in text and "a goal they all apply to" not in text
        await block.get_by_label("Every goal: Accessibility reviewer").check()
        await page.wait_for_function("() => document.querySelector('.checks-block')?.innerText.includes('· every goal')", timeout=WAIT_MS)
        assert asked()[-1]["every"] == ["accessibility-reviewer"]
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_hints_are_quiet_lines_under_the_price_and_never_block_save(fake_repo, monkeypatch):
    """Spec 43 E: muted, one line each, no button; the party's craft is sent with it."""
    from tests.test_pwa_shell_browser import _new_goal
    hints = ["Reviewer found nothing in its last 12 checks.", "No one in the party writes code: code tasks go to this project's agent for code (the Grunt when none)."]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.hints = list(hints)
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New party")
        await sheet.locator(".party-hint").first.wait_for(timeout=WAIT_MS)
        assert await sheet.locator(".party-hint").all_inner_texts() == hints
        assert await sheet.locator(".party-hint button, .party-hint a").count() == 0
        asked = [c[1] for c in stub.calls if c[0] == "ideas.party_price"]
        assert asked[0].get("craft") == "engineering"
        await sheet.get_by_label("What it is for").fill("A party that saves with its hints.")
        assert await sheet.get_by_role("button", name="Save party").is_enabled()                  # a hint never blocks Save
        assert await page.evaluate(NO_SCROLL)


# -- spec 63 C: what the party can take -----------------------------------------------------------------------------------------------------------------

LIT = """
(() => {
  window.__lit = [];                              // the goal types that were lit, as the page lit them (a light lasts 0.6 s)
  const done = new WeakSet();                     // a node is told once (it is seen added and changed in one batch)
  const note = (e) => {
    if (!e.classList || done.has(e) || !e.isConnected || !e.classList.contains("take") || !e.classList.contains("is-reward")) return;
    done.add(e);
    const cs = getComputedStyle(e);
    window.__lit.push({ at: Math.round(performance.now()), type: e.dataset.type, name: cs.animationName, duration: cs.animationDuration, timing: cs.animationTimingFunction });
  };
  document.addEventListener("DOMContentLoaded", () => new MutationObserver((ms) => { for (const m of ms) { if (m.type === "attributes") note(m.target); for (const n of m.addedNodes) if (n.nodeType === 1) { note(n); n.querySelectorAll && n.querySelectorAll("*").forEach(note); } } })
    .observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] }));
})();
"""
GAME = ["New feature", "Fix a bug", "Clean up", "New icon", "New logo", "New mechanic", "New level", "New character", "Balance pass", "New sound"]
BEFORE_PRICE = "e => { const l = e.querySelector('.party-takes'), p = e.querySelector('.party-price-box'); return Boolean(p.compareDocumentPosition(l) & Node.DOCUMENT_POSITION_FOLLOWING) && l.parentElement === p.parentElement; }"


def said(text):
    return " ".join(text.split())


def typed(monkeypatch, repo, types=None):
    """The host of spec 63 A: `ideas.party_price` answers `types` too, read from the call's seats by the realm as `gui/ideas_party.py` does (the stub's price is its own); `types`: what a test has it answer instead."""
    state, root = repo / ".orkcraft", repo / "board"
    real = Stub.commands

    def commands(self):
        got = real(self)
        price = got["ideas.party_price"]

        def serve(a):
            party = goal_types.Party.of(state, root, a.get("leader") or "", list(a.get("team") or []))
            read = [{"id": t.id, "name": t.name, "sign": t.sign, "missing": rows[0]["name"] if rows else ""} for t, rows in goal_types.offered(state, root, "", read=party)]
            return {**price(a), "types": read if types is None else types}
        return {**got, "ideas.party_price": serve}
    monkeypatch.setattr(Stub, "commands", commands)


async def _takes(sheet, last):
    """The line, once it is drawn for a party that has the type `last`."""
    await sheet.locator(f'.party-takes .take[data-type="{last}"]').wait_for(timeout=WAIT_MS)
    return sheet.locator(".party-takes")


@pytest.mark.asyncio
async def test_new_party_says_what_it_can_take_under_the_price_three_lines_at_most_and_k_more(fake_repo, monkeypatch):
    hosted(monkeypatch)
    typed(monkeypatch, fake_repo)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _sheet(page)
        await sheet.locator('.preset-tile[data-preset="game"]').click()
        line = await _takes(sheet, "mechanic")
        assert said(await line.inner_text()).startswith("It can take: New feature · Fix a bug · Clean up · New icon · New logo · New mechanic")
        shown = await line.locator(".take").count()
        more = line.locator(".take-more")
        assert 3 <= shown < len(GAME) and said(await more.inner_text()) == f"and {len(GAME) - shown} more"          # what does not fit ends with *and k more*
        assert await more.get_attribute("title") == ", ".join(GAME)                                                   # its title lists all
        assert await line.locator(".take-with").count() == 0 and await line.locator(".is-missing").count() == 0       # the Game's types miss no one
        assert await line.evaluate("e => e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)") <= 3.05
        assert await sheet.evaluate(BEFORE_PRICE)                                                                     # under the price
        first = line.locator(".take").first
        assert await first.locator(".ork-sign.feature").count() == 1                                                  # a type's sign, as New goal's chips draw it
        assert await line.locator('.take[data-type="mechanic"] .ork-sign.mechanic').count() == 1
        box = await first.locator(".ork-sign").bounding_box()
        assert (round(box["width"]), round(box["height"])) == (12, 12)
        assert await first.locator(".ork-sign").evaluate("e => getComputedStyle(e).color") == await sheet.locator(".party-hint, .muted").first.evaluate("e => getComputedStyle(e).color")      # small, in the muted ink
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_type_that_needs_someone_follows_with_one_more_and_says_who(fake_repo, monkeypatch):
    hosted(monkeypatch)
    typed(monkeypatch, fake_repo)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _sheet(page)
        await sheet.locator('.preset-tile[data-preset="data"]').click()
        line = await _takes(sheet, "abtest")
        assert said(await line.inner_text()) == "It can take: A new metric · A report, with one more: An A/B test (needs Experimenter)"
        assert await line.locator(".take-with").inner_text() == "with one more:" and await line.locator(".take.is-missing").count() == 1
        assert await line.locator(".take-more").count() == 0                                                          # it fits: no *and k more*
        await sheet.locator('.preset-tile[data-preset="mobile-app"]').click()                                         # a long list: the types that miss someone fall in *and k more*, titled whole
        await _takes(sheet, "character")
        title = await sheet.locator(".party-takes .take-more").get_attribute("title")
        assert "New screen (needs Design system designer)" in title and "Try an experiment (needs Experimenter)" in title
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_taskmaster_alone_is_offered_the_three_of_the_code(fake_repo, monkeypatch):
    hosted(monkeypatch)
    typed(monkeypatch, fake_repo)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _sheet(page)
        await sheet.locator('.preset-tile[data-preset="mixed"]').click()
        line = await _takes(sheet, "feature")                                                                  # (the engineering party has no *feature*, its own is the shaped one)
        assert said(await line.inner_text()) == "It can take: New feature · Fix a bug · Clean up"


@pytest.mark.asyncio
async def test_a_party_that_is_offered_no_type_says_to_add_a_builder(fake_repo, monkeypatch):
    typed(monkeypatch, fake_repo, types=[])
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _sheet(page)
        await sheet.locator(".party-takes").wait_for(timeout=WAIT_MS)
        assert said(await sheet.locator(".party-takes").inner_text()) == "It can take: nothing of its own yet: add a builder."


@pytest.mark.asyncio
async def test_an_older_host_sends_no_types_the_price_stands_and_no_line_is_drawn(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _sheet(page)
        await sheet.locator(".party-price").wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(500)
        assert await sheet.locator(".party-takes").count() == 0 and "It can take" not in await sheet.inner_text()


@pytest.mark.asyncio
@pytest.mark.parametrize("reduced", [False, True])
async def test_a_seat_that_opens_a_type_lights_it_once_the_first_answers_light_nothing_and_none_under_reduced_motion(fake_repo, monkeypatch, reduced):
    hosted(monkeypatch)
    typed(monkeypatch, fake_repo)
    async with _phone(fake_repo, monkeypatch, init=LIT) as (stub, page):
        if reduced:
            await page.emulate_media(reduced_motion="reduce")
        sheet = await _sheet(page)
        asked = lambda: [c[1] for c in stub.calls if c[0] == "ideas.party_price"]      # noqa: E731
        await sheet.locator(".party-takes").wait_for(timeout=WAIT_MS)
        for _ in range(60):                                                                 # the sheet's own two answers (the Taskmaster alone, then the craft's party)
            if len(asked()) >= 2:
                break
            await page.wait_for_timeout(100)
        await page.wait_for_timeout(700)
        assert await page.evaluate("window.__lit") == []                                    # nothing is lit by the first answers
        await sheet.locator('.preset-tile[data-preset="game"]').click()
        await _takes(sheet, "level")
        await page.wait_for_timeout(300)
        await page.evaluate("window.__lit.length = 0")
        await sheet.locator('.party [data-change="team"]').click()
        builds = sheet.get_by_role("region", name="Builds")
        await builds.get_by_role("button").first.click()
        await sheet.get_by_role("button", name="Take out: Level designer").click()
        await sheet.locator('.party-takes .take[data-type="level"]').wait_for(state="detached", timeout=WAIT_MS)       # a type that went is simply not drawn
        assert await page.evaluate("window.__lit") == []
        await sheet.get_by_role("button", name="Take in: Level designer").click()
        await _takes(sheet, "level")
        if reduced:
            await page.wait_for_timeout(500)
            assert await page.evaluate("window.__lit") == [] and await sheet.locator(".party-takes .is-reward").count() == 0
            return
        await page.wait_for_function("() => window.__lit.length > 0", timeout=WAIT_MS)
        await builds.get_by_role("button", name="Done").click()                             # a redraw for another reason does not light it again
        await page.wait_for_timeout(900)
        lit = await page.evaluate("window.__lit")
        assert [(l["type"], l["name"], l["duration"], l["timing"]) for l in lit] == [("level", "reward", "0.6s", "steps(4)")]      # the one the seat opened, once, the quiet reward's look
        assert await sheet.locator(".party-takes .is-reward").count() == 0                  # and it is over (0.6 s)


@pytest.mark.asyncio
async def test_the_party_sheet_of_a_goal_s_own_screen_says_what_it_can_take_too(fake_repo, monkeypatch):
    typed(monkeypatch, fake_repo)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        for a in (library.get("product-designer"), library.get("ui-kit"), library.get("accessibility-reviewer")):
            stub.roles[a.id] = {"slug": a.id, "name": a.name, "model": a.tier, "max_parallel": 2, "instruction": a.instruction, "builtin": False,
                                "craft": a.craft, "head": {"craft": a.craft, "race": "elf", "tier": a.tier}}
        stub.goals["land"] = stub.goal("land", "Landing page", "high", "ready", craft="design", race="elf", about="A landing page.",
                                       team=["ui-kit", "accessibility-reviewer"], every=[], leader=stub.leader("product-designer"))
        stub.bump({})
        await _pick_goal(page, "land")
        await _open_party(page, "Landing page")
        await page.locator(".screen").get_by_role("region", name="The party", exact=True).get_by_role("button", name="Change the party").click()
        sheet = page.get_by_role("dialog", name="The party")
        line = await _takes(sheet, "screen")
        assert said(await line.inner_text()).startswith("It can take: New screen · New feature") and await line.locator(".ork-sign.screen").count() == 1
        assert await sheet.evaluate(BEFORE_PRICE)
        await sheet.locator('.party [data-change="team"]').click()
        await sheet.get_by_role("button", name="Take in: Analyst").click()                  # a seat changed: asked again, the line drawn again
        for _ in range(100):
            if [c[1]["leader"] for c in stub.calls if c[0] == "ideas.party_price"][-1] == "analyst":
                break
            await page.wait_for_timeout(100)
        await sheet.locator(".party-takes").wait_for(timeout=WAIT_MS)
        assert said(await sheet.locator(".party-takes").inner_text()).startswith("It can take:")
        assert await page.evaluate(NO_SCROLL)
