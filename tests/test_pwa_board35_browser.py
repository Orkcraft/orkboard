"""Spec 35 part C on the phone (docs/specs/35-goals-window.md §11, "Tests → C"), through the one window of spec 49 and spec 50's words: Chromium at 390 × 844 against the
stub of test_pwa_shell_browser.py. The Target in the drawer, the parties in the where button's sheet, what waits for you as stops along the bottom (a proposal answered on its raised
one, the questions as one form), the goals in Planning by state, the spec's Stages, a file to-do's sheet, the Agents chips' words, the create button; no
horizontal scroll of the page. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import asyncio
import base64

import pytest

from tests.test_pwa_shell_browser import FAB, _agents, _band, _item, _menu, _new_goal, _new_idea, _open_idea, _open_party, _open_task, _pop, _said, _today, _where, NO_SCROLL, WAIT_MS, Stub, _called, _phone, _pick_goal, _shot  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser


async def _until(page, expr, ok, timeout=5.0):
    """`expr` read on the page until `ok` says so (the page's CSP refuses wait_for_function's eval)."""
    for _ in range(int(timeout * 20)):
        if ok(await page.evaluate(expr)):
            return True
        await asyncio.sleep(0.05)
    return False


def _two_goals(stub: Stub) -> None:
    stub.goals["ship"] = stub.goal("ship", "Ship v1", "high", "ready", summary="Ship the first release.\nMore.", questions=["Which store first?"])
    stub.goals["docs"] = stub.goal("docs", "Docs", "low", "ready")
    stub.ideas["offline"] = stub.idea("offline", "Offline mode", "raw", 5, track="ship", queue="night")
    stub.ideas["guide"] = stub.idea("guide", "Write the guide", "raw", 6, track="docs", queue="night")
    stub.bump({})


@pytest.mark.asyncio
async def test_the_drawer_sets_the_target_autostart_and_the_night_and_the_board_has_no_heading_or_target(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        pane = page.locator(".arena")
        assert await pane.locator("h2").count() == 0 and await page.locator(".target-chip").count() == 0       # spec 41 §2: no heading on the Board, the drawer has the Target
        drawer = await _menu(page)
        text = await drawer.inner_text()
        assert "lighter models, less reasoning, no proposals at night" in text and "heavier models, more reasoning, three proposals a night" in text
        assert await drawer.get_by_role("radio", name="Balance").is_checked()
        await _shot(page, "phone-drawer-390x844")
        await drawer.get_by_role("radio", name="Quality").click()
        assert await _called(stub, "ideas.board_set", {"target": "quality"})
        box_ = drawer.get_by_label("Start plans by themselves")
        assert await box_.is_checked() and await drawer.get_by_label("Night from").input_value() == "01:00"
        await box_.uncheck()
        assert await _called(stub, "ideas.board_set", {"autostart": False})
        await drawer.get_by_label("Night to").fill("06:30")
        assert await _called(stub, "ideas.board_set", {"night": "01:00-06:30"})
        await drawer.get_by_label("Push after merging (sends your code to origin)").check()
        assert await _called(stub, "ideas.into", {"push": True})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_board_shows_one_party_s_goals_its_goals_bar_and_the_parties_sheet_counts_every_party_s_stops(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        stub.extra_needs = [{"kind": "proposal", "idea": "p1", "goal": "docs", "title": "A docs page", "text": "Why: it helps", "priority": "low", "blocks": False, "at": ""}]
        stub.ideas["p1"] = stub.idea("p1", "A docs page", "proposed", 7, track="docs", in_needs_you=True)
        stub.ideas["shipped"] = stub.idea("shipped", "Shipped one", "done", 8, track="ship")
        stub.bump({})
        await _pick_goal(page, "ship")
        await _band(page, "lead")
        await _item(page, "Offline mode").wait_for(timeout=WAIT_MS)
        assert await page.locator(".stack .deck", has_text="Write the guide").count() == 0              # another party's goal is not here
        where = page.locator(".partydeck")
        assert " ".join((await page.locator(".gbar__head").inner_text()).split()) == "Ship v1 · 1 of 2 goals done"       # the party, how far: its done goals of all its goals, no %
        sheet = await _where(page)                                                                       # a docs proposal, though Ship v1 is shown: its row counts it
        assert await sheet.locator('.where-row[data-goal="docs"] .ork-count.warning').inner_text() == "1"
        await page.keyboard.press("Escape")
        await _open_party(page, "Ship v1")                                                               # the party's screen: its edit button pinned
        screen = page.locator(".screen")
        await screen.get_by_text("Ship v1").first.wait_for(timeout=WAIT_MS)
        await screen.get_by_role("button", name="Edit the party", exact=True).click()
        assert await page.get_by_role("dialog", name="Edit the party").get_by_label("Name").input_value() == "Ship v1"
        await page.keyboard.press("Escape")
        await page.get_by_role("button", name="Back", exact=True).click()
        await _pick_goal(page, "docs")
        await _band(page, "lead")
        await _item(page, "Write the guide").wait_for(timeout=WAIT_MS)
        assert "docs" in await page.evaluate("localStorage.getItem('orkcraft.goal')")                    # the party shown last, kept on this phone
        assert await where.get_attribute("data-goal") == "docs"
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_drafting_goal_stops_and_is_stopped_a_low_one_waits_for_tonight_and_limits_and_the_night_show(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        stub.ideas["hi"] = stub.idea("hi", "Fast sync", "reading", 8, track="ship", priority="high", queue="now")
        stub.ideas["lim"] = stub.idea("lim", "Wait for limits", "ready", 9, track="ship", held_until="2026-10-18T18:00:00")
        stub.ideas["nt"] = stub.idea("nt", "Starts tonight", "plan", 10, track="ship", start_at="night")
        stub.ideas["dep"] = stub.idea("dep", "Needs the sync", "working", 11, track="ship", waits_on=["hi"])
        stub.ideas["fin"] = stub.idea("fin", "Finished one", "done", 12, track="ship")
        stub.gate.update(commits=1, files=1, ideas=[{"slug": "fin", "title": "Finished one", "goal": "ship", "tasks": 1}])          # in dev, not in main yet
        stub.bump({})
        await _pick_goal(page, "ship")
        await _band(page, "lead")
        hi = _item(page, "Fast sync")
        await hi.wait_for(timeout=WAIT_MS)
        assert "Taskmaster is reading" in await _said(page, "Fast sync") and await hi.locator(".tcard__mark .ork-sign.work").count() == 1      # the leader reads it: orkUI's work sign
        await _shot(page, "phone-ideas-390x844")
        screen = page.locator(".screen")
        await _open_idea(page, hi)                                                            # its screen holds what its row held
        await screen.get_by_role("button", name="Stop").click()                                         # Stop → stopped
        assert await _called(stub, "ideas.read_stop", {"slug": "hi"})
        await page.get_by_role("button", name="Back", exact=True).click()
        stub.ideas["hi"].update(state="raw", queue="hold")
        stub.bump({})
        await _until(page, "document.querySelector('.stack .deck[data-idea=hi]')?.getAttribute('aria-label') || ''", lambda v: "reads it later" in v)
        assert await hi.locator(".tcard__mark .ork-sign.work").count() == 0
        await _open_idea(page, hi)
        for name in ("Process now", "Tonight"):
            await screen.get_by_role("button", name=name, exact=True).wait_for(timeout=WAIT_MS)
        await screen.get_by_role("button", name="Tonight", exact=True).click()
        assert await _called(stub, "ideas.queue", {"slug": "hi", "queue": "night"})
        await page.get_by_role("button", name="Back", exact=True).click()
        assert "waits for limits · after 18:00" in await _said(page, "Wait for limits")
        assert "starts tonight" in await _said(page, "Starts tonight")
        await _open_idea(page, "Starts tonight")
        await screen.get_by_role("button", name="Start now").click()
        assert await _called(stub, "ideas.start_now", {"slug": "nt"})
        await page.get_by_role("button", name="Back", exact=True).click()
        assert "waits for Fast sync" in await _said(page, "Needs the sync")
        await _today(page)                                                                              # done goals: Today's sheet lists them, Done · n
        done = page.get_by_role("dialog", name="Today")
        text = await done.text_content()                                                                # (the label is in capitals on the page)
        assert "Done · 1" in text and "Finished one" in text and "in dev · waits for main" in text
        await page.keyboard.press("Escape")
        page.once("dialog", lambda d: d.accept())                                                       # Delete asks first
        await _open_idea(page, "Offline mode")
        await screen.get_by_role("button", name="Delete this goal…").click()
        assert await _called(stub, "ideas.drop", {"slug": "offline"})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_goal_s_questions_are_one_form_and_a_proposal_is_answered_on_its_raised_stop(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        base = {"priority": "normal", "blocks": False, "at": ""}
        stub.extra_needs = [
            {**base, "kind": "goal", "idea": "", "goal": "ship", "title": "Ship v1", "text": "Which store first?"},
            {**base, "kind": "asks", "idea": "sync", "goal": "general", "title": "Sync ideas", "text": "Open questions in one line"},
            {**base, "kind": "proposal", "idea": "p1", "goal": "docs", "title": "A docs page", "text": "Why: it helps", "priority": "low"},
            {**base, "kind": "proposal", "idea": "p2", "goal": "docs", "title": "A tour", "text": "Why: onboarding", "priority": "low"}]
        stub.bump({})
        await _pick_goal(page, "ship")
        raised = await _pop(page, "Asks you: Ship v1")                                                  # a goal's questions, with no choices: Open… only
        assert [await b.inner_text() for b in await raised.locator(".raised__quick button").all()] == ["Open…"]
        await raised.get_by_role("button", name="Open…").click()                                        # a box each, one Send
        sheet = page.get_by_role("dialog", name="Questions")
        await sheet.get_by_label("Answer 1: Which store first?").fill("The App Store")
        await sheet.get_by_role("button", name="Send").click()
        assert await _called(stub, "ideas.answer", {"slug": "ship", "answers": ["The App Store"], "goal": True})
        await page.locator('.hc[data-kind="goal"]').wait_for(state="detached", timeout=WAIT_MS)
        await _pick_goal(page, "general")
        raised = await _pop(page, "Asks you: Sync ideas")                                               # a spec's questions: its Open questions section
        await raised.get_by_role("button", name="Open…").click()
        await sheet.wait_for(timeout=WAIT_MS)
        boxes = sheet.locator("textarea")
        assert await boxes.count() == 2
        await boxes.nth(0).fill("first")
        await boxes.nth(1).fill("second")
        await _shot(page, "phone-questions-390x844")
        await sheet.get_by_role("button", name="Send").click()
        assert await _called(stub, "ideas.answer", {"slug": "sync", "answers": ["first", "second"]})
        await page.locator('.hc[data-kind="asks"]').wait_for(state="detached", timeout=WAIT_MS)         # the row is drawn again before it is used
        await _pick_goal(page, "docs")
        one = await _pop(page, "Proposed: A docs page")                                                 # a proposal is answered on its raised stop: Take at the goal's priority
        assert [await b.inner_text() for b in await one.locator(".raised__quick button").all()] == ["Take", "No"]
        await one.get_by_role("button", name="Take").click()
        assert await _called(stub, "ideas.proposal", {"slug": "p1", "take": True, "priority": "low"}), [c for c in stub.calls if "proposal" in c[0]]
        await one.wait_for(state="hidden", timeout=WAIT_MS)
        two = await _pop(page, "Proposed: A tour")
        await two.get_by_label("Why not: A tour").fill("Not now")
        await two.get_by_role("button", name="No").click()
        assert await _called(stub, "ideas.proposal", {"slug": "p2", "take": False, "reason": "Not now"})
        await page.locator(".hc").first.wait_for(state="detached", timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_specs_stages_say_each_tasks_state_and_a_file_todo_has_its_steps_and_an_upload(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.plan["tasks"][4].update(state="held", note="reserve · after 18:00")
        stub.plan["tasks"][3].update(state="failed", error="tests red")
        stub.todos.append({"idea": "sync", "id": "t2", "title": "The Firebase config, google-services.json", "kind": "file", "why": "The app needs it to start",
                           "choices": [], "steps": ["Open the Firebase console", "Download google-services.json"], "accept": [".json"], "done": False})
        stub.bump({})
        await _band(page, "build")
        await _open_task(page, "Retry on a lost signal")                                                 # a task's screen → its goal's screen, with the plan
        await page.locator(".screen .facts").get_by_role("button", name="Sync ideas between the phone and the town").click()
        screen = page.locator(".screen")
        await screen.locator(".plan").wait_for(timeout=WAIT_MS)
        stages = await screen.locator(".tasks").inner_text()
        for word in ("merged", "working", "at Review", "keeps your reserve · after 18:00", "needs you"):
            assert word in stages, (word, stages)
        await _shot(page, "phone-stages-390x844")
        assert await page.evaluate(NO_SCROLL)
        await page.go_back()                                                                             # one step back to the window: the idea's screen replaced the task's
        await screen.wait_for(state="hidden", timeout=WAIT_MS)
        raised = await _pop(page, "A to-do: The Firebase config")
        await raised.get_by_role("button", name="Open…").click()
        sheet = page.get_by_role("dialog", name="To-do")
        await sheet.wait_for(timeout=WAIT_MS)
        text = await sheet.inner_text()
        assert "The app needs it to start" in text and "Open the Firebase console" in text and "Download google-services.json" in text
        assert await sheet.locator("input[type=file]").get_attribute("accept") == ".json"
        send = sheet.get_by_role("button", name="Send the file")
        assert await send.is_disabled()
        await sheet.locator("input[type=file]").set_input_files({"name": "google-services.json", "mimeType": "application/json", "buffer": b'{"a": 1}'})
        await _shot(page, "phone-file-todo-390x844")
        await send.click()
        data = base64.b64encode(b'{"a": 1}').decode()
        assert await _called(stub, "ideas.todo", {"idea": "sync", "id": "t2", "done": True, "file": {"name": "google-services.json", "data": data}})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_agents_chips_say_by_itself_tonight_and_why_a_task_is_held(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.plan["tasks"][4].update(state="held", note="reserve · after 18:00")
        stub.plan["tasks"][3].update(state="held", note="files · dark")
        stub.chip_extra = {"k3": {"by": "auto"}, "k2": {"night": True}, "k4": {"waits_title": "Dark mode", "note": "files · dark"},
                           "k5": {"note": "reserve · after 18:00"}}
        stub.bump({})
        agents = await _agents(page)
        await agents.locator(".chip-why").first.wait_for(timeout=WAIT_MS)
        assert "by itself" in await agents.locator(".chip", has_text="Retry on a lost signal").inner_text()
        assert "tonight" in await agents.locator(".chip", has_text="Add the queue").inner_text()
        assert "keeps your reserve · after 18:00" in (await agents.locator(".chip", has_text="Write the notes").inner_text()).lower()
        assert "waits for dark mode · same files" in (await agents.locator(".chip", has_text="Test it offline").inner_text()).lower()
        assert "by itself" not in await agents.locator(".chip", has_text="Add the queue").inner_text()
        await _shot(page, "phone-agents-chips-390x844")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_top_bar_has_the_menu_and_the_project_button_and_slides_away_as_the_page_scrolls_and_its_sheet_says_each_party(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        stub.goals["ship"].update(craft="design", race="elf", short="Ship")
        for n in range(14):
            stub.ideas[f"i{n}"] = stub.idea(f"i{n}", f"Idea number {n}", "raw", 10 + n, track="ship", queue="night")
        stub.bump({})
        bar = page.locator(".board-bar")
        sheet = await _where(page)
        await sheet.locator('.where-row[data-goal="docs"]').wait_for(timeout=WAIT_MS)
        assert [await r.get_attribute("data-goal") for r in await sheet.locator(".where-row").all()] == ["general", "ship", "docs", "ops"]       # the parties, then Operations; no New party row among them
        await _shot(page, "phone-goals-390x844")
        await page.keyboard.press("Escape")
        await _pick_goal(page, "ship")
        await _band(page, "lead")
        assert " ".join((await page.locator(".gbar__head").inner_text()).split()).startswith("Ship ·") and "Ship v1" not in await page.locator(".gbar__head").inner_text()   # its short name
        assert "Ship v1" in await (await _where(page)).locator('.where-row[data-goal="ship"]').get_attribute("aria-label")                                # the sheet says its name
        await page.keyboard.press("Escape")
        assert await bar.get_by_role("button", name="Menu").is_visible() and await bar.locator(".goal-chip, .project-chip, .needs-chip, .gear").count() == 0
        assert (await bar.bounding_box())["height"] < 80
        assert await _item(page, "Idea number 13").count() == 1                                         # a column holds them all and scrolls in itself
        assert await page.evaluate("document.documentElement.scrollHeight") <= 844 + 1                  # the window is one screen: the page does not scroll
        await page.evaluate("document.querySelector('.board').style.minHeight = '2400px'")             # a page that does scroll (a short screen): the bar slides away
        away = "(() => { const b = document.querySelector('.board-bar'); return [b.classList.contains('is-away'), b.getBoundingClientRect().bottom]; })()"
        await page.mouse.wheel(0, 600)
        assert await _until(page, away, lambda v: v[0] and v[1] <= 1)                                  # scrolling down: it slides away
        await page.mouse.wheel(0, -200)
        assert await _until(page, away, lambda v: not v[0] and v[1] > 40)                              # scrolling up brings it back
        await _shot(page, "phone-top-bar-goal-390x844")


def _asked_needs(stub: Stub) -> None:
    """Two cards with questions, as the host sends them (`asked`, spec 41 §9)."""
    base = {"priority": "normal", "blocks": False, "at": ""}
    stub.extra_needs = [
        {**base, "kind": "goal", "idea": "", "goal": "ship", "title": "Ship v1", "text": "Which store first?", "questions": ["Which store first?"],
         "asked": [{"ask": "Which store first?", "choices": ["App Store", "Google Play"], "pick": 0, "why": "most of its users are on iPhone"}]},
        {**base, "kind": "asks", "idea": "sync", "goal": "general", "title": "Sync ideas", "text": "Keep the edits offline?",
         "questions": ["Keep the edits offline?", "Which server?"],
         "asked": [{"ask": "Keep the edits offline?", "choices": ["yes", "no"], "pick": 0, "why": "the phone loses signal"},
                   {"ask": "Which server?", "choices": [], "pick": None, "why": ""}]}]
    stub.bump({})


@pytest.mark.asyncio
async def test_a_question_comes_with_its_choices_as_buttons_the_recommended_one_marked_and_one_press_answers(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        _asked_needs(stub)
        count = lambda slug: f'.where-row[data-goal="{slug}"] .ork-count.warning'                          # noqa: E731
        sheet = await _where(page)
        assert await _until(page, f"document.querySelector('{count('ship')}')?.textContent || ''", lambda v: v == "1")     # the party's questions: one stop on its row
        await page.keyboard.press("Escape")
        await _pick_goal(page, "ship")
        goal = await _pop(page, "Asks you: Ship v1")
        assert "Which store first?" in await goal.inner_text()                                           # the question, its choices as buttons
        store = goal.locator('[data-choice="0"]')
        assert await store.inner_text() == "● App Store" and "primary" in await store.get_attribute("class")   # the recommended one is marked and primary
        assert "primary" not in await goal.locator('[data-choice="1"]').get_attribute("class")
        assert await store.evaluate("e => e.offsetHeight") >= 43
        await _shot(page, "phone-quick-answers-390x844")
        await store.click()                                                                              # one press answers it
        assert await _called(stub, "ideas.answer", {"slug": "ship", "answers": ["App Store"], "goal": True})
        await page.locator(".flash", has_text="Sent: the Taskmaster answers in a moment.").wait_for(timeout=WAIT_MS)
        await page.locator('.hc[data-kind="goal"]').wait_for(state="detached", timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_with_more_than_one_question_send_the_picks_answers_with_the_recommended_and_open_fills_the_form_with_them(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        _asked_needs(stub)
        await _pick_goal(page, "general")
        asks = await _pop(page, "Asks you: Sync ideas")
        assert [await b.inner_text() for b in await asks.locator(".raised__quick button").all()] == ["Send the picks", "Open…"]
        await asks.get_by_role("button", name="Open…").click()                                          # the form, the picks filled in
        form = page.get_by_role("dialog", name="Questions")
        await form.wait_for(timeout=WAIT_MS)
        assert await form.get_by_label("Answer 1: Keep the edits offline?").input_value() == "yes"
        assert await form.get_by_label("Answer 2: Which server?").input_value() == ""
        await form.get_by_label("Answer 1: Keep the edits offline?").fill("no")
        await form.get_by_label("Answer 2: Which server?").fill("the office one")
        await form.get_by_role("button", name="Send").click()
        assert await _called(stub, "ideas.answer", {"slug": "sync", "answers": ["no", "the office one"]})
        await page.locator('.hc[data-kind="asks"]').wait_for(state="detached", timeout=WAIT_MS)
        _asked_needs(stub)                                                                                 # asked again: Send the picks takes every recommendation
        asks = await _pop(page, "Asks you: Sync ideas")
        await asks.get_by_role("button", name="Send the picks").click()
        assert await _called(stub, "ideas.answer", {"slug": "sync", "answers": ["yes", ""]})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_create_button_floats_over_the_field_s_bottom_right_and_limits_are_said_where_a_choice_spends_them(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        await _pick_goal(page, "ship")
        fab = page.locator(FAB)
        box = await fab.bounding_box()
        assert box["width"] == 48 and box["height"] == 64 and round(box["x"]) == 390 - 16 - 48                  # a small face-down deck, under the thumb, 16 px from the right …
        assert round(box["y"] + box["height"]) == 844 - 56 - 10                                                  # … over the field, 10 px above the bottom row
        assert await page.locator(".section-head").get_by_role("button", name="New goal").count() == 0
        assert await page.get_by_role("button", name="Speak a new goal").count() == 0                   # one button; Speak is in the sheet (spec 41 §5)
        assert await page.locator("[role=menu], dialog.dial-dlg").count() == 0                          # no dial: one tap, New goal
        await fab.click()
        goal = page.get_by_role("dialog", name="New goal")
        await goal.wait_for(timeout=WAIT_MS)
        assert await goal.get_by_label("Party").input_value() == "ship"
        await page.keyboard.press("Escape")
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New party")
        await sheet.locator('.craft-tile[data-craft="data"]').click()
        assert "What is left: Claude 62 % · Antigravity 15 %" in await sheet.locator(".limits-note").inner_text()
        await page.keyboard.press("Escape")
        await _open_idea(page, "Offline mode")
        assert await page.locator(FAB).is_visible() is False or await page.locator(".screen").is_visible()   # a screen covers the button
        assert await page.evaluate(NO_SCROLL)
