"""Spec 54 part B, the phone (docs/specs/54-one-hand.md §2–§6; decisions §67): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py with a second
party (Tech, led by Quill) and Operations. The hand holds every stop of the project: another party's stop says its party (the raised card's line *Tech · Log format*, its
label, its leader's small head; Operations' its sliders) and *Open…* shows that party first; the order is the urgency's (failed, what holds work back, what does not, the
results; the oldest first), the most urgent in the middle, the next to its right, the next to its left; the keys read the urgency's order; the deck has no count and the parties'
sheet a dot (danger with a failure); *Nothing waits for you.*; *Let … decide* sends `decide: true`; a file to-do's *Describe it instead* sends `words` and *Go without it* `skip`;
a choice's *Let … choose*; the Target is one switch (the menu's and Operations' gear); *Agents of this project* is a row of This project; *Edit* on a member's card opens its dialog;
44 px targets; `sw.js` v62."""
from __future__ import annotations

import copy

import pytest

from orkboard.gui import pwa
from tests.test_pwa_arena_browser import ELDER, ELF, GNOME, SCENE, STAMP, _scene, member, node, result, task  # noqa: F401
from tests.test_pwa_ops38_browser import _ops  # noqa: F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _band, _called, _phone, _pop, _where  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

QUILL = {"slug": "quill", "name": "Quill", "head": ELF}
BACKEND = {"slug": "backend", "name": "Backend"}
TODO = {"kind": "todo", "idea": "art", "goal": "tech", "priority": "normal", "blocks": True, "at": "2026-10-19T09:00:00"}
KINDS = """() => [...document.querySelectorAll('.hand .hc')].map((b) => b.dataset.kind)"""
LEFTS = """() => [...document.querySelectorAll('.hand .hc')].map((b) => [b.dataset.kind, b.getAttribute('aria-label'), b.getBoundingClientRect().left + b.getBoundingClientRect().width / 2])"""
MENU = "dialog.drawer"


@pytest.fixture(autouse=True)
def _answers(monkeypatch):
    """`ideas.answer` and `ideas.todo` answer ok whatever they are sent (the stub's own take `done` and a pick only)."""
    real = Stub.commands

    def commands(self):
        def serve(name):
            def call(a):
                self.calls.append((name, {k: v for k, v in a.items() if k not in ("link", "device")}))
                return {"ok": True}
            return call
        return {**real(self), "ideas.todo": serve("ideas.todo"), "ideas.answer": serve("ideas.answer")}
    monkeypatch.setattr(Stub, "commands", commands)


def tech(failed=True, ops=True, todos=True):
    """The scene with a second party, Tech (Quill leads it): a question, a failed task, three to-dos of the goal Reference art (a file, a choice, a secret); and Operations'
    stops (one at your check, one failed, a template's rules)."""
    m = SCENE["map"]
    goal = copy.deepcopy(m["goals"][0])
    goal.update(slug="tech", title="Tech", short="Tech", priority="normal", leader=QUILL, party=[member(QUILL, "lead", ELF)], team=[], ideas=3, done=0, flags=0, waits_main=0)
    m["goals"].append(goal)
    asked = [{"ask": "Which log format?", "choices": ["JSON", "Plain lines"], "pick": 0, "why": "", "by": {**QUILL, "head": ELF}}]
    m["nodes"] += [node("logq", "Log format", "asks", "planning", goal="tech", needs_you="asks", asked=asked),
                   node("art", "Reference art", "plan", "planning", goal="tech"),
                   node("brk", "Broken build", "working", "implementation", goal="tech", tasks=[task("z1", "Fix the build", "failed", BACKEND, 1, error="The build fails", finished="2026-10-20T07:00:00")] if failed else [])]
    SCENE["needs"].append({"kind": "asks", "idea": "logq", "goal": "tech", "title": "Log format", "text": "Which log format?", "questions": ["Which log format?"], "priority": "normal",
                           "blocks": False, "at": "2026-10-20T08:00:00", "asked": asked})
    if todos:
        for tid, kind, title, more in (("t1", "file", "Reference picture", {"accept": ["image/png"]}), ("t2", "choice", "Pick a palette", {"choices": ["Dusk", "Dawn"]}), ("t3", "secret", "The API key", {})):
            SCENE["needs"].append({**TODO, "title": title, "text": title, "todo": {"id": tid, "title": title, "kind": kind, "why": "The plan needs it", "choices": more.get("choices"),
                                                                                  "steps": [], "accept": more.get("accept", []), "done": False}})
    if ops:
        SCENE["needs"] += [{"kind": "op", "op": "op1", "template": "jira-task", "title": "New Jira task", "text": "Fix the lost signal", "why": "", "priority": "normal", "blocks": False,
                            "at": "2026-10-18T09:30:00"},
                           {"kind": "op_rules", "template": "jira-task", "title": "New Jira task", "op": "", "text": "Titles start with a verb.", "lines": ["Titles start with a verb."],
                            "priority": "normal", "blocks": False, "at": ""}]
        if failed:
            SCENE["needs"].append({"kind": "op_failed", "op": "op2", "template": "jira-task", "title": "New Jira task", "text": "Jira said no", "acted": False, "priority": "normal",
                                   "blocks": False, "at": "2026-10-22T01:00:00"})
    SCENE["map"]["nodes"][[n["slug"] for n in m["nodes"]].index("cookie")]["tasks"][0]["finished"] = "2026-10-21T09:00:00"


@pytest.mark.asyncio
async def test_the_hand_holds_every_stop_of_the_project_and_another_partys_says_its_party_and_wears_its_leaders_head(fake_repo, monkeypatch):
    tech()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(400)
        kinds = await page.evaluate(KINDS)
        assert len(kinds) == 14 and kinds.count("failed") == 2 and kinds.count("op_failed") == 1 and kinds.count("todo") == 3 and kinds.count("look") == 2          # the party shown's, Tech's and Operations'
        assert await page.locator(".partydeck").get_attribute("data-goal") == "passkey"
        own = page.locator('.hc[aria-label*="Plan ready: Recovery codes"]')
        assert await own.get_attribute("aria-label") == "Plan ready: Recovery codes" and await own.locator(".hc__party").count() == 0                   # the party shown's wear nothing
        other = page.locator('.hc[aria-label*="Asks you: Log format"]')
        assert await other.get_attribute("aria-label") == "Asks you: Log format (Tech)"                                                                      # its label names the party
        assert "elf-warrior" in await other.locator(".hc__party img").get_attribute("src")                                                                  # Quill's small head
        ops = page.locator('.hc[aria-label*="At your check: New Jira task"]')
        assert await ops.get_attribute("aria-label") == "At your check: New Jira task (Operations)" and await ops.locator('.hc__party use').get_attribute("href") == "icons/icons.svg#sliders"
        raised = await _pop(page, "Asks you: Log format")
        assert " ".join((await raised.locator(".raised__goal").inner_text()).split()) == "Tech · Log format"                                                 # <party> · <goal>
        assert await raised.locator(".raised__goal img").count() == 1
        await page.keyboard.press("Escape")
        raised = await _pop(page, "At your check: New Jira task")
        assert " ".join((await raised.locator(".raised__goal").inner_text()).split()) == "Operations" and await raised.locator(".raised__goal use").count() == 1
        await page.keyboard.press("Escape")
        raised = await _pop(page, "Asks you: Log format")
        await raised.locator('[data-choice="1"]').click()                                                                                                    # a quick answer acts in place: Tech is not shown for it
        assert await _called(stub, "ideas.answer", {"slug": "logq", "answers": ["Plain lines"]}) and await page.locator(".partydeck").get_attribute("data-goal") == "passkey"
        own = page.locator('.hc[aria-label*="Failed: Secure cookie flags"]')
        assert await own.count() == 1 and await own.locator(".hc__party").count() == 0


@pytest.mark.asyncio
async def test_open_on_another_partys_stop_shows_that_party_first(fake_repo, monkeypatch):
    tech()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        raised = await _pop(page, "A to-do: Reference picture")
        await raised.get_by_role("button", name="Open…").click()
        sheet = page.get_by_role("dialog", name="To-do")
        await sheet.wait_for(timeout=WAIT_MS)
        assert "reference picture" in (await sheet.inner_text()).lower()
        assert await page.locator(".partydeck").get_attribute("data-goal") == "tech"                                                                          # as a pick of it in the parties' list
        await sheet.get_by_role("button", name="Close").click()
        assert await page.locator(".gbar__lbl").inner_text() == "Tech"
        await page.locator('.hc[aria-label*="Plan ready: Recovery codes"]').wait_for(timeout=WAIT_MS)                                                         # and the whole project's hand is still there
        raised = await _pop(page, "At your check: New Jira task")
        await raised.get_by_role("button", name="Open…").click()
        await page.locator(".ops-view").wait_for(timeout=WAIT_MS)                                                                                             # Operations' stops show Operations first
        assert await page.locator(".partydeck").get_attribute("data-goal") == "ops"


@pytest.mark.asyncio
async def test_the_order_is_the_urgencys_the_most_urgent_in_the_middle_the_next_to_its_right_and_then_to_its_left_and_the_keys_read_the_urgency(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(400)
        assert await page.evaluate(KINDS) == ["failed", "plan", "asks", "proposal", "look", "look"]                                                         # the page: by urgency (a failure, a plan and a question, a proposal, the results)
        row = sorted(await page.evaluate(LEFTS), key=lambda x: x[2])
        assert [k for k, _, _ in row] == ["look", "asks", "failed", "plan", "proposal", "look"]                                                              # the row: the failure in the middle, the plan to its right, the question to its left
        assert await page.locator(".hc.is-fail").evaluate("e => e.style.order") == "2"
        middle = [abs(x - 195) for _, _, x in sorted(await page.evaluate(LEFTS), key=lambda x: x[2])]
        assert min(range(6), key=lambda i: middle[i]) in (2, 3)
        for slot, edge in ((0, "marginLeft"), (5, "marginRight")):                                                                                          # the row's own ends keep no outer overlap
            assert await page.locator(f'.hc[data-place="{slot}"]').evaluate(f"e => getComputedStyle(e).{edge}") == "0px"
        await page.locator(".hc").first.focus()
        seen = [await page.evaluate("document.activeElement.dataset.kind")]
        for _ in range(5):
            await page.keyboard.press("Tab")
            seen.append(await page.evaluate("document.activeElement.dataset.kind"))
        assert seen == ["failed", "plan", "asks", "proposal", "look", "look"]                                                                                 # Tab goes in the urgency's order
        assert await page.locator(".hc").first.evaluate("e => getComputedStyle(e).transitionDuration") == "0s"                                              # a new order is laid at once: nothing shuffles


@pytest.mark.asyncio
async def test_inside_a_group_the_oldest_comes_first_and_a_failure_of_any_party_comes_before_what_holds_work_back(fake_repo, monkeypatch):
    tech()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(400)
        labels = [x[1] for x in await page.evaluate(LEFTS)]                                                                                                  # (the page's order)
        assert labels[:3] == ["Failed: Fix the build (Tech)", "Failed: Secure cookie flags", "Failed: New Jira task (Operations)"]                           # red first, the oldest first
        assert labels[3] == "At your check: New Jira task (Operations)" and labels[4] == "A to-do: Reference picture (Tech)" and labels[-4:-2] == ["Proposed: Words of the sign-in page", "Proposed: New Jira task (Operations)"]
        assert labels[-2:] == ["To look at: Challenge store", "To look at: Words on the screens"]
        row = [x[1] for x in sorted(await page.evaluate(LEFTS), key=lambda x: x[2])]
        assert row[6] == labels[0] and row[7] == labels[1] and row[5] == labels[2]                                                                           # n = 14: places 6, 7, 5 are the first three


@pytest.mark.asyncio
async def test_the_filter_of_a_party_keeps_only_its_picked_goals_stops_and_results_and_the_other_parties_stay(fake_repo, monkeypatch):
    tech()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        await page.locator(".gbar__head").click()
        goals = page.get_by_role("dialog", name="Goals")
        await goals.locator('.dk__main[data-idea="recovery"]').click()
        await goals.get_by_role("button", name="Close").click()
        await page.wait_for_timeout(500)
        kinds = await page.evaluate(KINDS)
        assert kinds.count("plan") == 1 and kinds.count("look") == 0 and kinds.count("proposal") == 0 and kinds.count("todo") == 3                       # Passkey's only Recovery codes' stop; Tech's and Operations' as they were


@pytest.mark.asyncio
async def test_nothing_waits_for_you_says_so(fake_repo, monkeypatch):
    SCENE["needs"] = []
    SCENE["results"] = []
    SCENE["map"]["nodes"][[n["slug"] for n in SCENE["map"]["nodes"]].index("cookie")]["tasks"][0]["state"] = "ready"
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        empty = page.locator(".handzone__empty")
        await empty.wait_for(state="visible", timeout=WAIT_MS)
        assert (await empty.inner_text()) == "Nothing waits for you." and await page.locator(".hc").count() == 0


@pytest.mark.asyncio
async def test_the_deck_has_no_count_and_the_parties_sheet_wears_a_dot_where_a_stop_waits_danger_with_a_failure(fake_repo, monkeypatch, _ops):
    tech(failed=False)
    SCENE["needs"] = [n for n in SCENE["needs"] if n["kind"] != "op_rules"]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        deck = page.locator(".partydeck")
        assert await deck.locator(".ork-count").count() == 0 and await page.locator(".ork-count.warning").count() == 0                                      # no count on the screen
        assert "stops wait in the other parties" in await deck.get_attribute("aria-label")                                                                  # a screen reader is told
        sheet = await _where(page)
        await sheet.locator('.where-row[data-goal="tech"]').wait_for(timeout=WAIT_MS)
        assert await sheet.locator(".ork-count").count() == 0
        dots = {slug: await sheet.locator(f'.where-row[data-goal="{slug}"] .where-dot').get_attribute("data-dot") for slug in ("passkey", "tech", "ops")}
        assert dots == {"passkey": "danger", "tech": "alert", "ops": "alert"}                                                                                # Passkey has a failed task
        box = await sheet.locator('.where-row[data-goal="tech"] .where-dot').bounding_box()
        assert round(box["width"]) == 8 and round(box["height"]) == 8
        colour = lambda slug: sheet.locator(f'.where-row[data-goal="{slug}"] .where-dot').evaluate("e => getComputedStyle(e).backgroundColor")
        assert await colour("passkey") != await colour("tech") and await colour("tech") == await colour("ops")
        for r in await sheet.locator(".where-row").all():
            assert "stops wait" not in (await r.get_attribute("aria-label") or "") and not any(c.isdigit() for c in (await r.get_attribute("aria-label") or "").replace("/", " ").split(",")[-1])     # no count in a row's words either
        await sheet.locator(".where-row").first.evaluate("e => e.closest('dialog').close()")
        SCENE["needs"] = []
        SCENE["results"] = []
        SCENE["map"]["nodes"][[n["slug"] for n in SCENE["map"]["nodes"]].index("cookie")]["tasks"][0]["state"] = "ready"
        stub.bump({})
        await page.wait_for_function("() => document.querySelectorAll('.hc').length === 0", timeout=WAIT_MS)
        sheet = await _where(page)
        await page.wait_for_function("() => document.querySelectorAll('.where-dot').length === 0", timeout=WAIT_MS)
        assert await sheet.locator(".where-dot").count() == 0                                                                                               # nothing waits: no dot


@pytest.mark.asyncio
async def test_let_the_asker_decide_sends_decide_for_a_question_a_partys_question_and_the_sheet(fake_repo, monkeypatch):
    tech(todos=False, ops=False)
    SCENE["needs"][1]["asked"][0].pop("by", None)                                                                                                            # a question of no one's: the leader's, the Taskmaster
    SCENE["map"]["nodes"][[n["slug"] for n in SCENE["map"]["nodes"]].index("second")]["asked"][0].pop("by", None)
    goal = {"ask": "Which colours?", "choices": ["Dusk", "Dawn"], "pick": 1, "why": "", "by": {**QUILL, "head": ELF}}
    two = [{"ask": "Which colours?", "choices": ["Dusk"], "pick": 0, "why": "", "by": {**QUILL, "head": ELF}}, {"ask": "And the layout?", "choices": ["Wide"], "pick": 0, "why": "", "by": {**QUILL, "head": ELF}}]
    SCENE["map"]["nodes"].append(node("multi", "Two questions", "asks", "planning", needs_you="asks", asked=two))
    SCENE["needs"].append({"kind": "asks", "idea": "multi", "goal": "passkey", "title": "Two questions", "text": "Which colours?", "priority": "normal", "blocks": False, "at": STAMP, "asked": two})
    SCENE["needs"].append({"kind": "goal", "goal": "tech", "title": "Tech’s colours", "text": "Which colours?", "priority": "normal", "blocks": False, "at": "2026-10-20T09:00:00", "asked": [goal]})
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        ask = await _pop(page, "Asks you: Passkey on a second device")
        decide = ask.get_by_role("button", name="Let the Taskmaster decide")
        buttons = ask.locator(".raised__quick button")
        assert await buttons.last.inner_text() == "Let the Taskmaster decide" and "quiet" in await decide.get_attribute("class") and "primary" not in await decide.get_attribute("class")      # last, quiet
        await decide.click()
        assert await _called(stub, "ideas.answer", {"slug": "second", "decide": True})
        toast = page.locator("p.flash").last
        await toast.wait_for(timeout=WAIT_MS)
        assert await toast.inner_text() == "Sent: the Taskmaster decides."
        await ask.wait_for(state="hidden", timeout=WAIT_MS)
        ask = await _pop(page, "Asks you: Log format")
        assert await ask.locator(".raised__quick button").last.inner_text() == "Let Quill decide"
        await ask.get_by_role("button", name="Let Quill decide").click()
        assert await _called(stub, "ideas.answer", {"slug": "logq", "decide": True})
        await ask.wait_for(state="hidden", timeout=WAIT_MS)
        party = await _pop(page, "Asks you: Tech’s colours")                                                                                                 # a party's question
        await party.get_by_role("button", name="Let Quill decide").click()
        assert await _called(stub, "ideas.answer", {"slug": "tech", "decide": True, "goal": True})
        await party.wait_for(state="hidden", timeout=WAIT_MS)
        several = await _pop(page, "Asks you: Two questions")                                                                                               # two questions: the form
        assert [await b.inner_text() for b in await several.locator(".raised__quick button").all()] == ["Send the picks", "Open…", "Let Quill decide"]
        await several.get_by_role("button", name="Open…").click()
        form = page.get_by_role("dialog", name="Questions")
        await form.wait_for(timeout=WAIT_MS)
        await form.get_by_role("button", name="Let Quill decide").click()                                                                                    # the first question's asker
        assert await _called(stub, "ideas.answer", {"slug": "multi", "decide": True})
        await form.wait_for(state="hidden", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_a_file_todo_can_be_described_or_gone_without_a_choice_left_to_its_leader_and_any_other_gone_without(fake_repo, monkeypatch):
    tech(ops=False)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        file = await _pop(page, "A to-do: Reference picture")
        assert [await b.inner_text() for b in await file.locator(".raised__quick button").all()] == ["Open…", "Describe it instead", "Send", "Go without it"]
        for name in ("Describe it instead", "Go without it"):
            assert "quiet" in await file.get_by_role("button", name=name).get_attribute("class")                                                              # quiet, not primary
        send = file.get_by_role("button", name="Send")
        assert not await file.get_by_label("What should it look like?").is_visible()
        await file.get_by_role("button", name="Describe it instead").click()
        words = file.get_by_label("What should it look like?")
        await words.wait_for(timeout=WAIT_MS)
        assert await send.is_disabled()                                                                                                                      # nothing to send yet
        await words.fill("  A rope bridge at dawn  ")
        await send.click()
        assert await _called(stub, "ideas.todo", {"idea": "art", "id": "t1", "done": True, "words": "A rope bridge at dawn"})
        toast = page.locator("p.flash").last
        await toast.wait_for(timeout=WAIT_MS)
        assert await toast.inner_text() == "Sent: the words go to Quill."
        await file.wait_for(state="hidden", timeout=WAIT_MS)
        file = await _pop(page, "A to-do: Reference picture")
        await file.get_by_role("button", name="Go without it").click()
        assert await _called(stub, "ideas.todo", {"idea": "art", "id": "t1", "skip": True})
        await page.locator("p.flash", has_text="Done: Quill’s plan goes on without it.").wait_for(timeout=WAIT_MS)
        await file.wait_for(state="hidden", timeout=WAIT_MS)
        choice = await _pop(page, "A to-do: Pick a palette")
        assert [await b.inner_text() for b in await choice.locator(".raised__quick button").all()] == ["Open…", "Let Quill choose"]
        await choice.get_by_role("button", name="Let Quill choose").click()
        assert await _called(stub, "ideas.todo", {"idea": "art", "id": "t2", "skip": True})
        await choice.wait_for(state="hidden", timeout=WAIT_MS)
        secret = await _pop(page, "A to-do: The API key")
        assert [await b.inner_text() for b in await secret.locator(".raised__quick button").all()] == ["Open…", "Go without it"]
        assert await secret.get_by_role("button", name="Go without it").get_attribute("title") == "Its tasks run without it, and say so if they cannot"
        await secret.get_by_role("button", name="Go without it").click()
        assert await _called(stub, "ideas.todo", {"idea": "art", "id": "t3", "skip": True})


@pytest.mark.asyncio
async def test_the_todo_sheet_has_the_same_ways_out_under_its_input(fake_repo, monkeypatch):
    tech(ops=False)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        raised = await _pop(page, "A to-do: Reference picture")
        await raised.get_by_role("button", name="Open…").click()
        sheet = page.get_by_role("dialog", name="To-do")
        await sheet.wait_for(timeout=WAIT_MS)
        assert await sheet.get_by_label("Reference picture: the file").count() == 1
        await sheet.get_by_role("button", name="Describe it instead").click()
        await sheet.get_by_label("What should it look like?").fill("A rope bridge")
        await sheet.get_by_role("button", name="Send", exact=True).click()
        assert await _called(stub, "ideas.todo", {"idea": "art", "id": "t1", "done": True, "words": "A rope bridge"})
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        raised = await _pop(page, "A to-do: Pick a palette")
        await raised.get_by_role("button", name="Open…").click()
        sheet = page.get_by_role("dialog", name="To-do")
        await sheet.wait_for(timeout=WAIT_MS)
        assert [await b.inner_text() for b in await sheet.locator(".outs button").all()] == ["Let Quill choose"]
        await sheet.get_by_role("button", name="Let Quill choose").click()
        assert await _called(stub, "ideas.todo", {"idea": "art", "id": "t2", "skip": True})
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        raised = await _pop(page, "A to-do: The API key")
        await raised.get_by_role("button", name="Open…").click()
        sheet = page.get_by_role("dialog", name="To-do")
        await sheet.wait_for(timeout=WAIT_MS)
        await sheet.get_by_role("button", name="Go without it").click()
        assert await _called(stub, "ideas.todo", {"idea": "art", "id": "t3", "skip": True})


@pytest.mark.asyncio
async def test_the_target_is_one_switch_in_the_menu_and_in_operations_gear(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        await page.get_by_role("button", name="Menu").click()
        menu = page.locator(MENU)
        await menu.wait_for(timeout=WAIT_MS)
        group = menu.get_by_role("radiogroup", name="Target")
        pills = group.locator("label.pill")
        assert [await p.inner_text() for p in await pills.all()] == ["Thrift", "Balance", "Quality"]
        for p in await pills.all():
            assert (await p.bounding_box())["height"] >= 44                                                                                                  # 44 px
        assert "is-on" in await pills.nth(1).get_attribute("class") and await group.get_by_role("radio", name="Balance").is_checked()                       # the picked one raised as the priority's is
        line = menu.locator(".target-line")
        assert await line.inner_text() == "the usual models and reasoning, two proposals a night"
        await group.get_by_role("radio", name="Quality").check(force=True)
        assert await _called(stub, "ideas.board_set", {"target": "quality"})
        await page.wait_for_function("() => document.querySelector('.target-line').textContent.startsWith('heavier models')")
        assert "is-on" in await pills.nth(2).get_attribute("class") and "is-on" not in await pills.nth(1).get_attribute("class")
        await menu.get_by_role("button", name="Done").click()
        await _pick_ops(page)
        await page.get_by_role("button", name="Operations settings").click()
        gear = page.get_by_role("dialog", name="Operations settings")
        await gear.wait_for(timeout=WAIT_MS)
        ops_group = gear.get_by_role("radiogroup", name="Target")
        assert await ops_group.locator("label.pill").count() == 3 and await gear.locator(".target-pick").count() == 0
        await ops_group.get_by_role("radio", name="Thrift").check(force=True)
        assert await _called(stub, "ops.set", {"target": "thrift"})
        assert await gear.locator(".target-line").inner_text() == "lighter models, less reasoning, no proposals at night"


async def _pick_ops(page):
    sheet = await _where(page)
    await sheet.locator('.where-row[data-goal="ops"]').click()
    await page.locator(".ops-view").wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_agents_of_this_project_is_a_row_of_this_project_and_the_menus_head_keeps_stop_all_today_and_spend(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        await page.get_by_role("button", name="Menu").click()
        menu = page.locator(MENU)
        await menu.wait_for(timeout=WAIT_MS)
        order = await menu.evaluate("""(e) => [...e.querySelectorAll('h3, .board-stop, [data-act="today"], [data-act="agents"], .board-spend')].map((x) => x.matches('h3') ? 'h3:' + x.textContent : x.dataset.act || x.className)""")
        head = order[: order.index("h3:This project")]
        assert "board-stop" in head[0] and "today" in head and "agents" not in head                                                                         # Stop all, Spend today, Today at its head; no Agents
        assert "agents" in order[order.index("h3:This project"): order.index("h3:This phone")]
        row = menu.get_by_role("button", name="Agents of this project")
        assert (await row.bounding_box())["height"] >= 44 and await row.locator(".ork-chev.right").count() == 1
        await row.click()
        await menu.wait_for(state="hidden", timeout=WAIT_MS)
        await page.get_by_role("button", name="+ Add agent").wait_for(timeout=WAIT_MS)                                                                       # the same screen


@pytest.mark.asyncio
async def test_edit_on_a_members_card_opens_its_agent_dialog_the_leaders_too(fake_repo, monkeypatch):
    init = Stub.__init__

    def with_backend(self):
        init(self)
        self.roles["backend"] = {"slug": "backend", "name": "Backend", "model": "warrior", "max_parallel": 2, "instruction": "", "builtin": False}      # a role of this project, as the host lists it
    monkeypatch.setattr(Stub, "__init__", with_backend)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".deck").first.wait_for(timeout=WAIT_MS)
        await page.locator('button.band__face[data-member="backend"]').click()
        card = page.locator(".solo__card")
        await card.wait_for(timeout=WAIT_MS)
        edit = card.get_by_role("button", name="Edit Backend")
        assert (await edit.bounding_box())["height"] >= 44 and await edit.inner_text() == "Edit"
        await edit.click()
        dialog = page.get_by_role("dialog", name="Edit agent")
        await dialog.wait_for(timeout=WAIT_MS)
        assert await dialog.get_by_label("Name").input_value() == "Backend"
        assert await dialog.get_by_label("Model").count() == 1 and await dialog.get_by_label("At most at once").input_value() == "2" and await dialog.get_by_label("Instruction").count() == 1
        assert await dialog.get_by_text("Takes").count() >= 1
        await dialog.get_by_role("button", name="Cancel").click()
        await dialog.wait_for(state="hidden", timeout=WAIT_MS)
        await _band(page, "lead")
        await page.locator('button.band__face[data-member="taskmaster"]').click()
        await page.locator(".solo__card").get_by_role("button", name="Edit Taskmaster").click()
        dialog = page.get_by_role("dialog", name="Edit agent")
        await dialog.wait_for(timeout=WAIT_MS)
        assert await dialog.get_by_label("Name").input_value() == "Taskmaster"                                                                               # the leader's own
        await dialog.get_by_role("button", name="Cancel").click()


@pytest.mark.asyncio
async def test_every_target_of_a_raised_stop_is_44_px_and_the_page_does_not_scroll_sideways(fake_repo, monkeypatch):
    tech(ops=False)
    small = """(root) => [...root.querySelectorAll('button, input, textarea, select')].filter((b) => b.offsetParent && !b.closest('[hidden]')).map((b) => [b.textContent || b.getAttribute('aria-label'), b.getBoundingClientRect().height]).filter(([, h]) => h < 43)"""
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".hc").first.wait_for(timeout=WAIT_MS)
        for name, press in (("A to-do: Reference picture", "Describe it instead"), ("Asks you: Log format", None), ("A to-do: Pick a palette", None), ("A to-do: The API key", None)):
            raised = await _pop(page, name)
            if press:
                await raised.get_by_role("button", name=press).click()
            assert await raised.evaluate(small) == [], name
            assert await page.evaluate(NO_SCROLL)
            await page.keyboard.press("Escape")


def test_the_service_worker_is_at_v62():
    sw = (pwa.ROOT / "sw.js").read_text(encoding="utf-8")
    assert 'const CACHE = "orkcraft-app-v66";' in sw
