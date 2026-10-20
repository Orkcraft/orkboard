"""Spec 35 part C on the phone (docs/specs/35-goals-window.md §11, "Tests → C"): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py. The Target chip, the goal select, Needs you as one list with a proposal answered in its row and the
questions as one form, the ideas' rows by state, the spec's Stages, a file to-do's sheet, the Agents chips' words; no horizontal
scroll of the page. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import asyncio
import base64

import pytest

from tests.test_pwa_shell_browser import _menu, _said, _stop, NO_SCROLL, WAIT_MS, Stub, _called, _needs, _phone, _pick_goal, _shot  # noqa: F401

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
        pane = page.locator(".board-tab-pane")
        assert await pane.locator("h2").count() == 0 and await page.locator(".target-chip").count() == 0       # spec 41 §2: the tab says Board, the drawer the Target
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
async def test_the_board_shows_one_goal_s_ideas_its_card_and_how_far_it_is_and_needs_you_holds_every_goal_s(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        stub.extra_needs = [{"kind": "proposal", "idea": "p1", "goal": "docs", "title": "A docs page", "text": "Why: it helps", "priority": "low", "blocks": False, "at": ""}]
        stub.ideas["p1"] = stub.idea("p1", "A docs page", "proposed", 7, track="docs", in_needs_you=True)
        stub.ideas["shipped"] = stub.idea("shipped", "Shipped one", "done", 8, track="ship")
        stub.bump({})
        await _pick_goal(page, "ship")
        await _stop(page, "Offline mode").wait_for(timeout=WAIT_MS)
        assert await _stop(page, "Write the guide").count() == 0
        now = page.locator('.map-goal[data-goal="ship"]')
        assert "Ship the first release." in await now.locator(".goal-line").inner_text() and "More." not in await now.inner_text()   # the summary's first line
        assert "1 of 2 ideas" in await now.locator(".trail-start").inner_text()                          # how far
        assert await page.locator(".needs-pane").is_hidden()                                             # Needs you: its own screen
        await _needs(page)
        await page.locator(".need-proposal").wait_for(timeout=WAIT_MS)                                   # a docs proposal, though Ship v1 is shown
        await page.get_by_role("tab", name="Board").click()
        await now.get_by_role("button", name="Edit goal Ship v1").click()
        assert await page.get_by_role("dialog", name="Edit goal").get_by_label("Title").input_value() == "Ship v1"
        await page.keyboard.press("Escape")
        await now.get_by_role("button", name="Open goal Ship v1").click()
        await page.locator(".screen").get_by_text("Ship v1").first.wait_for(timeout=WAIT_MS)
        await page.get_by_role("button", name="Back", exact=True).click()
        await _pick_goal(page, "docs")
        await _stop(page, "Write the guide").wait_for(timeout=WAIT_MS)
        assert "docs" in await page.evaluate("localStorage.getItem('orkcraft.goal')")                    # the goal shown last, kept on this phone
        assert "Docs" in await page.locator(".board-bar .goal-chip").inner_text()
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_drafting_idea_stops_and_is_stopped_a_low_one_waits_for_tonight_and_limits_and_the_night_show(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        stub.ideas["hi"] = stub.idea("hi", "Fast sync", "reading", 8, track="ship", priority="high", queue="now")
        stub.ideas["lim"] = stub.idea("lim", "Wait for limits", "ready", 9, track="ship", held_until="2026-10-18T18:00:00")
        stub.ideas["nt"] = stub.idea("nt", "Starts tonight", "plan", 10, track="ship", start_at="night")
        stub.ideas["dep"] = stub.idea("dep", "Needs the sync", "working", 11, track="ship", waits_on=["hi"])
        stub.ideas["fin"] = stub.idea("fin", "Finished one", "done", 12, track="ship")
        stub.bump({})
        await _pick_goal(page, "ship")
        hi = page.locator(".map-row[data-slug=hi]")
        await hi.wait_for(timeout=WAIT_MS)
        assert await hi.locator(".spin").count() == 1 and "drafting" in await _said(page, "Fast sync")
        await hi.scroll_into_view_if_needed()
        await _shot(page, "phone-ideas-390x844")
        screen = page.locator(".screen")
        await hi.locator(".map-open").click()                                                            # its screen holds what its row held
        await screen.get_by_role("button", name="Stop").click()                                         # Stop → stopped
        assert await _called(stub, "ideas.read_stop", {"slug": "hi"})
        await page.get_by_role("button", name="Back", exact=True).click()
        stub.ideas["hi"].update(state="raw", queue="hold")
        stub.bump({})
        await _until(page, "document.querySelector('.map-row[data-slug=hi] .map-open')?.getAttribute('aria-label') || ''", lambda v: "stopped" in v)
        assert await hi.locator(".spin").count() == 0
        await hi.locator(".map-open").click()
        for name in ("Process now", "Tonight"):
            await screen.get_by_role("button", name=name, exact=True).wait_for(timeout=WAIT_MS)
        await screen.get_by_role("button", name="Tonight", exact=True).click()
        assert await _called(stub, "ideas.queue", {"slug": "hi", "queue": "night"})
        await page.get_by_role("button", name="Back", exact=True).click()
        lim = _stop(page, "Wait for limits")
        assert "waits for limits · after 18:00" in await _said(page, "Wait for limits") and await lim.locator(".trail-mark use[href$='#clock']").count() == 1
        assert "starts tonight" in await _said(page, "Starts tonight")
        await _stop(page, "Starts tonight").locator(".map-open").click()
        await screen.get_by_role("button", name="Start now").click()
        assert await _called(stub, "ideas.start_now", {"slug": "nt"})
        await page.get_by_role("button", name="Back", exact=True).click()
        assert "waits for Fast sync" in await _said(page, "Needs the sync")
        done = page.locator("details.done-ideas")                                                       # done ideas folded at the end
        assert "Done (1)" in await done.inner_text() and not await done.evaluate("e => e.open")
        page.once("dialog", lambda d: d.accept())                                                       # Delete asks first
        await _stop(page, "Offline mode").locator(".map-open").click()
        await screen.get_by_role("button", name="Delete this idea…").click()
        assert await _called(stub, "ideas.drop", {"slug": "offline"})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_needs_you_is_one_list_questions_are_one_form_and_a_proposal_is_answered_in_its_row(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        base = {"priority": "normal", "blocks": False, "at": ""}
        stub.extra_needs = [
            {**base, "kind": "goal", "idea": "", "goal": "ship", "title": "Ship v1", "text": "Which store first?"},
            {**base, "kind": "asks", "idea": "sync", "goal": "general", "title": "Sync ideas", "text": "Open questions in one line"},
            {**base, "kind": "proposal", "idea": "p1", "goal": "docs", "title": "A docs page", "text": "Why: it helps"},
            {**base, "kind": "proposal", "idea": "p2", "goal": "docs", "title": "A tour", "text": "Why: onboarding"}]
        stub.bump({})
        await _needs(page)
        await page.locator(".need-proposal").first.wait_for(timeout=WAIT_MS)
        kinds = await page.locator(".need").evaluate_all("els => els.map((e) => e.dataset.kind)")
        assert kinds == ["plan", "todo", "goal", "asks", "proposal", "proposal"] and await page.get_by_role("heading", name="Needs you").count() == 1
        await page.locator(".need-goal").get_by_role("button", name="More").click()                     # a goal's questions: a box each, one Send
        sheet = page.get_by_role("dialog", name="Questions")
        await sheet.get_by_label("Answer 1: Which store first?").fill("The App Store")
        await sheet.get_by_role("button", name="Send").click()
        assert await _called(stub, "ideas.answer", {"slug": "ship", "answers": ["The App Store"], "goal": True})
        await page.locator(".need-goal").wait_for(state="detached", timeout=WAIT_MS)
        await page.locator(".need-asks").get_by_role("button", name="More").click()                     # a spec's questions: its Open questions section
        await sheet.wait_for(timeout=WAIT_MS)
        boxes = sheet.locator("textarea")
        assert await boxes.count() == 2
        await boxes.nth(0).fill("first")
        await boxes.nth(1).fill("second")
        await _shot(page, "phone-questions-390x844")
        await sheet.get_by_role("button", name="Send").click()
        assert await _called(stub, "ideas.answer", {"slug": "sync", "answers": ["first", "second"]})
        await page.locator(".need-asks").wait_for(state="detached", timeout=WAIT_MS)                    # the list is drawn again before the row is used
        one, two = page.locator(".need-proposal", has_text="A docs page"), page.locator(".need-proposal", has_text="A tour")
        assert await one.get_by_role("radio", name="Normal").is_checked()                                  # the proposal's priority
        await one.get_by_role("radio", name="High").click()
        await one.get_by_role("button", name="Take").click()
        assert await _called(stub, "ideas.proposal", {"slug": "p1", "take": True, "priority": "high"}), [c for c in stub.calls if "proposal" in c[0]]
        await two.get_by_label("Why not: A tour").fill("Not now")
        await two.get_by_role("button", name="No").click()
        assert await _called(stub, "ideas.proposal", {"slug": "p2", "take": False, "reason": "Not now"})
        await one.wait_for(state="detached", timeout=WAIT_MS)
        await two.wait_for(state="detached", timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_specs_stages_say_each_tasks_state_and_a_file_todo_has_its_steps_and_an_upload(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.plan["tasks"][4].update(state="held", note="reserve · after 18:00")
        stub.plan["tasks"][3].update(state="failed", error="tests red")
        stub.todos.append({"idea": "sync", "id": "t2", "title": "The Firebase config, google-services.json", "kind": "file", "why": "The app needs it to start",
                           "choices": [], "steps": ["Open the Firebase console", "Download google-services.json"], "accept": [".json"], "done": False})
        stub.bump({})
        await _stop(page, "Sync ideas").locator(".map-open").click()
        screen = page.locator(".screen")
        await screen.locator(".plan").wait_for(timeout=WAIT_MS)
        stages = await screen.locator(".tasks").inner_text()
        for word in ("merged", "working", "at Review", "keeps your reserve · after 18:00", "needs you"):
            assert word in stages, (word, stages)
        await _shot(page, "phone-stages-390x844")
        assert await page.evaluate(NO_SCROLL)
        await page.get_by_role("button", name="Back", exact=True).click()
        await _needs(page)
        await page.locator(".need-todo", has_text="google-services").click()
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
        await page.get_by_role("tab", name="Agents").click()
        agents = page.locator(".agents")
        await agents.locator(".chip-why").first.wait_for(timeout=WAIT_MS)
        assert "by itself" in await agents.locator(".chip", has_text="Retry on a lost signal").inner_text()
        assert "tonight" in await agents.locator(".chip", has_text="Add the queue").inner_text()
        assert "keeps your reserve · after 18:00" in (await agents.locator(".chip", has_text="Write the notes").inner_text()).lower()
        assert "waits for dark mode · same files" in (await agents.locator(".chip", has_text="Test it offline").inner_text()).lower()
        assert "by itself" not in await agents.locator(".chip", has_text="Add the queue").inner_text()
        await _shot(page, "phone-agents-chips-390x844")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_top_bar_has_the_menu_and_the_goal_with_its_craft_s_head_and_short_name_and_slides_away_scrolling_down(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        stub.goals["ship"].update(craft="design", race="elf", short="Ship")
        for n in range(14):
            stub.ideas[f"i{n}"] = stub.idea(f"i{n}", f"Idea number {n}", "raw", 10 + n, track="ship", queue="night")
        stub.bump({})
        bar = page.locator(".board-bar")
        await bar.locator(".goal-chip").click()
        rows = page.get_by_role("dialog", name="Goals").locator(".goal-row")
        await rows.nth(3).wait_for(timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in await rows.all_inner_texts()] == [
            "General Engineering · Normal · ready", "Ship v1 Design · High · ready", "Docs Engineering · Low · ready", "Operations"]   # the Map is the Board
        await _shot(page, "phone-goals-390x844")
        await page.keyboard.press("Escape")
        await _pick_goal(page, "ship")
        await _stop(page, "Idea number 13").wait_for(timeout=WAIT_MS)
        chip = bar.locator(".goal-chip")
        assert (await chip.inner_text()).strip().startswith("Ship") and "Ship v1" not in await chip.inner_text()           # its short name, on one line
        assert await chip.get_attribute("aria-label") == "Goal: Ship v1. Choose another" and await chip.get_attribute("title") == "Ship v1"
        assert await chip.locator("img").get_attribute("src") == "races/elf-laborer.png"                 # the goal's craft, its race's head
        assert await chip.locator("img").get_attribute("title") == "Design"
        assert await bar.get_by_role("button", name="Menu").is_visible() and await bar.locator(".goal-chip__project, .project-chip, .needs-chip, .gear").count() == 0
        assert (await bar.bounding_box())["height"] < 80
        away = "(() => { const b = document.querySelector('.board-bar'); return [b.classList.contains('is-away'), b.getBoundingClientRect().bottom]; })()"
        await page.mouse.wheel(0, 600)
        assert await _until(page, away, lambda v: v[0] and v[1] <= 1)                                  # scrolling down: it slides away
        await page.mouse.wheel(0, -200)
        assert await _until(page, away, lambda v: not v[0] and v[1] > 40)                              # scrolling up brings it back
        await _shot(page, "phone-top-bar-goal-390x844")
        assert await page.evaluate(NO_SCROLL)


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
async def test_a_question_comes_with_its_answer_picked_one_send_takes_it_and_later_puts_a_row_away(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        _asked_needs(stub)
        tab = "document.querySelector('.board-tabs .board-tab:nth-child(3)').getAttribute('aria-label')"
        want = f"Needs you: 4 wait for your answer, {len(stub.results())} results to check"
        assert await _until(page, tab, lambda v: v == want)
        await _needs(page)
        goal = page.locator(".need-goal")
        await goal.wait_for(timeout=WAIT_MS)
        assert "Which store first?" in await goal.inner_text() and "(App Store" not in await goal.inner_text()   # the question, its answers as buttons
        store = goal.get_by_role("button", name="App Store")
        assert await store.get_attribute("aria-pressed") == "true" and "Recommended" in await store.inner_text()   # the pick is pressed, and said in words
        assert await goal.get_by_role("button", name="Google Play").get_attribute("aria-pressed") == "false"
        assert "most of its users are on iPhone" in await goal.inner_text()                              # its why, under the question
        send = goal.get_by_role("button", name="Send")
        assert await send.is_enabled()                                                                  # one tap takes every recommendation
        await _shot(page, "phone-quick-answers-390x844")
        await send.click()
        assert await _called(stub, "ideas.answer", {"slug": "ship", "answers": ["App Store"], "goal": True})
        asks = page.locator(".need-asks")
        assert "Which server?" in await asks.inner_text()
        assert await asks.get_by_role("button", name="yes", exact=False).get_attribute("aria-pressed") == "true"
        await asks.get_by_role("button", name="Later: Sync ideas").click()                              # put away on this phone
        await asks.wait_for(state="detached", timeout=WAIT_MS)
        want = f"Needs you: 2 wait for your answer, {len(stub.results())} results to check"            # answered and one put away
        assert await _until(page, tab, lambda v: v == want)
        await page.get_by_role("button", name="Put away for later (1): show").click()
        await page.locator(".need-asks").wait_for(timeout=WAIT_MS)
        plan = page.locator(".need-plan")                                                              # a swipe to the left: Later too
        box = await plan.bounding_box()
        y = box["y"] + box["height"] / 2
        await plan.dispatch_event("pointerdown", {"pointerType": "touch", "clientX": box["x"] + 300, "clientY": y, "isPrimary": True})
        await plan.dispatch_event("pointermove", {"pointerType": "touch", "clientX": box["x"] + 150, "clientY": y, "isPrimary": True})
        await plan.dispatch_event("pointerup", {"pointerType": "touch", "clientX": box["x"] + 150, "clientY": y, "isPrimary": True})
        assert "Hide the 2 put away" in await page.locator(".needs-pane").inner_text()
        assert not any(c[0] in ("ideas.plan", "ideas.start") for c in stub.calls)                       # a swipe never starts work
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_choice_can_be_changed_more_fills_the_picks_and_let_the_taskmaster_decide_answers_with_them(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        _asked_needs(stub)
        await _needs(page)
        asks = page.locator(".need-asks")
        await asks.wait_for(timeout=WAIT_MS)
        await asks.get_by_role("button", name="no", exact=True).click()                                 # another choice replaces the pick
        assert await asks.get_by_role("button", name="no", exact=True).get_attribute("aria-pressed") == "true"
        assert await asks.get_by_role("button", name="yes").get_attribute("aria-pressed") == "false"
        await asks.get_by_role("button", name="More").click()                                           # the form, the picks filled in
        form = page.get_by_role("dialog", name="Questions")
        await form.wait_for(timeout=WAIT_MS)
        assert await form.get_by_label("Answer 1: Keep the edits offline?").input_value() == "no"
        assert await form.get_by_label("Answer 2: Which server?").input_value() == ""
        await form.get_by_label("Answer 2: Which server?").fill("the office one")
        await form.get_by_role("button", name="Send").click()
        assert await _called(stub, "ideas.answer", {"slug": "sync", "answers": ["no", "the office one"]})
        goal = page.locator(".need-goal")
        await goal.get_by_role("button", name="Let the Taskmaster decide").click()
        assert await _called(stub, "ideas.answer", {"slug": "ship", "decide": True, "goal": True})
        await page.locator(".need-goal").wait_for(state="detached", timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_new_idea_is_the_button_at_the_bottom_right_and_limits_are_said_where_a_choice_spends_them(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        await _pick_goal(page, "ship")
        fab = page.get_by_role("button", name="New idea", exact=True)
        box = await fab.bounding_box()
        assert box["x"] + box["width"] > 330 and box["y"] > 600 and box["width"] >= 44                 # under the thumb
        assert await page.locator(".section-head").get_by_role("button", name="New idea").count() == 0
        assert await page.locator(".fab").count() == 1 and await page.get_by_role("button", name="Speak a new idea").count() == 0   # one button; Speak is in the sheet (spec 41 §5)
        await fab.click()
        await page.get_by_role("dialog", name="New idea").wait_for(timeout=WAIT_MS)
        await page.keyboard.press("Escape")
        await page.get_by_role("tab", name="Needs you").click()
        assert await fab.is_hidden()                                                                    # the Board's own
        await page.get_by_role("tab", name="Board").click()
        await page.locator(".board-bar .goal-chip").click()
        await page.get_by_role("dialog", name="Goals").get_by_role("button", name="New goal").click()
        sheet = page.get_by_role("dialog", name="New goal")
        await sheet.locator('.craft-tile[data-craft="data"]').click()
        assert "What is left: Claude 62 % · Antigravity 15 %" in await sheet.locator(".limits-note").inner_text()
        await page.keyboard.press("Escape")
        await _stop(page, "Offline mode").locator(".map-open").click()
        await page.locator(".screen .limits-note").wait_for(timeout=WAIT_MS) if await page.locator(".screen .action-bar, .screen-foot").count() else None
        assert await page.evaluate(NO_SCROLL)


PARTY_ROW = {"kind": "party", "idea": "", "goal": "docs", "by": "reviewer", "title": "Take Reviewer out of Docs' party?",
             "text": "It found nothing in the last 8 ideas; a check costs about $0.35.", "priority": "low", "blocks": False, "at": ""}


@pytest.mark.asyncio
async def test_a_party_proposal_is_answered_in_its_row_taken_out_or_kept_with_a_reason(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.extra_needs = [dict(PARTY_ROW)]
        stub.bump({})
        await _needs(page)
        row = page.locator(".need-party")
        await row.wait_for(timeout=WAIT_MS)
        text = await row.inner_text()
        assert "Take Reviewer out of Docs' party?" in text and "It found nothing in the last 8 ideas; a check costs about $0.35." in text
        assert await row.get_by_label("Why not: " + PARTY_ROW["title"]).get_attribute("placeholder") == "Why not? (optional, one line)"
        await row.get_by_label("Why not: " + PARTY_ROW["title"]).fill("it guards the docs")
        await row.get_by_role("button", name="Keep it: " + PARTY_ROW["title"]).click()
        assert await _called(stub, "ideas.party_answer", {"goal": "docs", "take": False, "reason": "it guards the docs"})
        await page.wait_for_function("() => document.querySelectorAll('.need-party').length === 0", timeout=WAIT_MS * 2)
        stub.extra_needs = [dict(PARTY_ROW)]
        stub.bump({})
        await page.locator(".need-party").wait_for(timeout=WAIT_MS)
        await page.get_by_role("button", name="Take it out: " + PARTY_ROW["title"]).click()
        assert await _called(stub, "ideas.party_answer", {"goal": "docs", "take": True})
        assert await page.evaluate(NO_SCROLL)
