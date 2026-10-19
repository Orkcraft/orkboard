"""Spec 35 part C on the phone (docs/specs/35-goals-window.md §11, "Tests → C"): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py. The Target chip, the goal select, Needs you as one list with a proposal answered in its row and the
questions as one form, the ideas' rows by state, the spec's Stages, a file to-do's sheet, the Agents chips' words; no horizontal
scroll of the page. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import asyncio
import base64

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _needs, _phone, _pick_goal, _shot  # noqa: F401

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
async def test_the_target_chip_sets_and_shows_and_the_gear_has_autostart_and_the_night(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        chip = page.locator(".pane-head .target-chip")
        assert (await chip.inner_text()).replace("\n", " ") == "Target: Balance"
        assert (await page.locator(".board-tab-pane .pane-head").bounding_box())["y"] < 200                              # in the Board's header
        await chip.click()
        sheet = page.get_by_role("dialog", name="Target")
        await sheet.wait_for(timeout=WAIT_MS)
        text = await sheet.inner_text()
        assert "lighter models, less reasoning, no proposals at night" in text and "heavier models, more reasoning, three proposals a night" in text
        assert await sheet.get_by_role("radio", name="Balance").is_checked()
        box = await sheet.bounding_box()
        assert box["x"] == 0 and box["width"] == 390 and box["y"] + box["height"] == 844                 # a bottom sheet
        await _shot(page, "phone-target-390x844")
        await sheet.get_by_role("radio", name="Quality").click()
        assert await _called(stub, "ideas.board_set", {"target": "quality"})
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        await page.locator(".target-chip", has_text="Quality").wait_for(timeout=WAIT_MS)
        await page.get_by_role("button", name="Settings").click()
        gear = page.get_by_role("dialog", name="Settings")
        box_ = gear.get_by_label("Start plans by themselves")
        assert await box_.is_checked() and await gear.get_by_label("Night from").input_value() == "01:00"
        await box_.uncheck()
        assert await _called(stub, "ideas.board_set", {"autostart": False})
        await gear.get_by_label("Night to").fill("06:30")
        assert await _called(stub, "ideas.board_set", {"night": "01:00-06:30"})
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
        assert await page.locator(".idea-card", has_text="Write the guide").count() == 0 and await page.locator(".idea-card", has_text="Offline mode").count() == 1
        now = page.locator(".goal-now")
        assert "Ship the first release." in await now.inner_text() and "More." not in await now.inner_text()      # the summary's first line
        assert "1 of 2 ideas done" in await now.locator(".goal-progress").inner_text()                   # how far, in words
        assert await page.locator(".needs-pane").is_hidden()                                             # Needs you: its own screen
        await _needs(page)
        await page.locator(".need-proposal").wait_for(timeout=WAIT_MS)                                   # a docs proposal, though Ship v1 is shown
        await page.get_by_role("tab", name="Board").click()
        await now.get_by_role("button", name="Edit goal Ship v1").click()
        assert await page.get_by_role("dialog", name="Edit goal").get_by_label("Title").input_value() == "Ship v1"
        await page.keyboard.press("Escape")
        await now.get_by_role("button", name="Open", exact=True).click()
        await page.locator(".screen").get_by_text("Ship v1").first.wait_for(timeout=WAIT_MS)
        await page.get_by_role("button", name="Back", exact=True).click()
        await _pick_goal(page, "docs")
        await page.locator(".idea-card", has_text="Write the guide").wait_for(timeout=WAIT_MS)
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
        hi = page.locator(".idea-card[data-slug=hi]")
        await hi.wait_for(timeout=WAIT_MS)
        assert await hi.locator(".spin").count() == 1 and "drafting" in await hi.inner_text()
        await hi.scroll_into_view_if_needed()
        await _shot(page, "phone-ideas-390x844")
        await hi.get_by_role("button", name="Stop: Fast sync").click()                                   # Stop → stopped
        assert await _called(stub, "ideas.read_stop", {"slug": "hi"})
        await hi.locator(".state-word", has_text="stopped").wait_for(timeout=WAIT_MS)
        assert await hi.locator(".spin").count() == 0
        for name in ("Process now: Fast sync", "Tonight: Fast sync", "Delete: Fast sync"):
            assert await hi.get_by_role("button", name=name).is_visible()
        await hi.get_by_role("button", name="Tonight: Fast sync").click()
        assert await _called(stub, "ideas.queue", {"slug": "hi", "queue": "night"})
        lim = page.locator(".idea-card", has_text="Wait for limits")
        assert "waits for limits · after 18:00" in await lim.inner_text() and await lim.get_by_role("button").count() == 2   # the open area and Delete
        nt = page.locator(".idea-card", has_text="Starts tonight")
        assert "starts tonight" in await nt.inner_text()
        await nt.get_by_role("button", name="Start now: Starts tonight").click()
        assert await _called(stub, "ideas.start_now", {"slug": "nt"})
        assert "waits for Fast sync" in await page.locator(".idea-card", has_text="Needs the sync").inner_text()
        done = page.locator("details.done-ideas")                                                       # done ideas folded at the end
        assert "Done (1)" in await done.inner_text() and not await done.evaluate("e => e.open")
        await page.locator(".idea-card", has_text="Offline mode").get_by_role("button", name="Delete: Offline mode").click()   # Delete asks first, on a sheet
        sheet = page.get_by_role("dialog", name="Delete this idea?")
        await sheet.get_by_role("button", name="Keep it").click()
        assert not any(c[0] == "ideas.drop" for c in stub.calls)
        await page.locator(".idea-card", has_text="Offline mode").get_by_role("button", name="Delete: Offline mode").click()
        await sheet.get_by_role("button", name="Delete", exact=True).click()
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
        await page.locator(".idea-card", has_text="Sync ideas").click()
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
async def test_the_top_bar_names_the_project_and_the_goal_with_its_craft_s_head_and_slides_away_scrolling_down(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        stub.goals["ship"].update(craft="design", race="elf")
        for n in range(14):
            stub.ideas[f"i{n}"] = stub.idea(f"i{n}", f"Idea number {n}", "raw", 10 + n, track="ship", queue="night")
        stub.bump({})
        bar = page.locator(".board-bar")
        await bar.locator(".goal-chip").click()
        rows = page.get_by_role("dialog", name="Goals").locator(".goal-row")
        await rows.nth(4).wait_for(timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in await rows.all_inner_texts()] == [
            "General Engineering · Normal · ready", "Ship v1 Design · High · ready", "Docs Engineering · Low · ready", "Operations",
            "Map Every goal, its ideas and tasks on one screen"]
        await _shot(page, "phone-goals-390x844")
        await page.keyboard.press("Escape")
        await _pick_goal(page, "ship")
        await page.locator(".idea-card", has_text="Idea number 13").wait_for(timeout=WAIT_MS)
        chip = bar.locator(".goal-chip")
        assert "Ship v1" in await chip.inner_text() and await chip.get_attribute("aria-label") == "Goal: Ship v1. Choose another"
        assert await chip.locator("img").get_attribute("src") == "races/elf-laborer.png"                 # the goal's craft, its race's head
        assert await chip.locator("img").get_attribute("title") == "Design"
        assert await bar.locator(".project-chip").is_visible() and "project" in await chip.locator(".goal-chip__project").inner_text()   # the project over the goal
        assert (await bar.bounding_box())["height"] < 80
        assert "Design" in await page.locator(".goal-now").inner_text()
        away = "(() => { const b = document.querySelector('.board-bar'); return [b.classList.contains('is-away'), b.getBoundingClientRect().bottom]; })()"
        await page.mouse.wheel(0, 600)
        assert await _until(page, away, lambda v: v[0] and v[1] <= 1)                                  # scrolling down: it slides away
        await page.mouse.wheel(0, -200)
        assert await _until(page, away, lambda v: not v[0] and v[1] > 40)                              # scrolling up brings it back
        await _shot(page, "phone-top-bar-goal-390x844")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_question_is_answered_in_its_card_with_a_likely_answer_and_later_puts_a_row_away(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        base = {"priority": "normal", "blocks": False, "at": ""}
        stub.extra_needs = [
            {**base, "kind": "goal", "idea": "", "goal": "ship", "title": "Ship v1", "text": "Which store first? (App Store / Google Play)",
             "questions": ["Which store first? (App Store / Google Play)"]},
            {**base, "kind": "asks", "idea": "sync", "goal": "general", "title": "Sync ideas", "text": "Keep the edits offline? (yes / no)",
             "questions": ["Keep the edits offline? (yes / no)", "Which server?"]}]
        stub.bump({})
        assert await _until(page, "document.querySelector('.needs-chip').getAttribute('aria-label')", lambda v: v == "Needs you, 4")
        await _needs(page)
        goal = page.locator(".need-goal")
        await goal.wait_for(timeout=WAIT_MS)
        assert "Which store first?" in await goal.inner_text() and "(App Store" not in await goal.inner_text()   # the question, its answers as buttons
        send = goal.get_by_role("button", name="Send")
        assert await send.is_disabled()
        await goal.get_by_role("button", name="App Store").click()
        assert await goal.get_by_role("button", name="App Store").get_attribute("aria-pressed") == "true"
        await _shot(page, "phone-quick-answers-390x844")
        await send.click()
        assert await _called(stub, "ideas.answer", {"slug": "ship", "answers": ["App Store"], "goal": True})
        asks = page.locator(".need-asks")
        assert "Which server?" in await asks.inner_text() and "the Taskmaster decides" in await asks.inner_text()
        assert await asks.get_by_role("button", name="yes", exact=True).count() == 1
        await asks.get_by_role("button", name="Later: Sync ideas").click()                              # put away on this phone
        await asks.wait_for(state="detached", timeout=WAIT_MS)
        assert await page.locator(".board-bar .needs-chip").get_attribute("aria-label") == "Needs you, 2"   # answered, and one put away
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
async def test_new_idea_is_the_button_at_the_bottom_right_and_limits_are_said_where_a_choice_spends_them(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _two_goals(stub)
        await _pick_goal(page, "ship")
        fab = page.get_by_role("button", name="New idea", exact=True)
        box = await fab.bounding_box()
        assert box["x"] + box["width"] > 330 and box["y"] > 600 and box["width"] >= 44                 # under the thumb
        assert await page.locator(".section-head").get_by_role("button", name="New idea").count() == 0
        await fab.click()
        await page.get_by_role("dialog", name="New idea").wait_for(timeout=WAIT_MS)
        await page.keyboard.press("Escape")
        await page.get_by_role("tab", name="Review").click()
        assert await fab.is_hidden()                                                                    # the Board's own
        await page.get_by_role("tab", name="Board").click()
        await page.locator(".board-bar .goal-chip").click()
        await page.get_by_role("dialog", name="Goals").get_by_role("button", name="New goal").click()
        sheet = page.get_by_role("dialog", name="New goal")
        await sheet.locator('.craft-tile[data-craft="data"]').click()
        await sheet.get_by_role("button", name="Next").click()
        assert "What is left: Claude 62 % · Antigravity 15 %" in await sheet.locator(".limits-note").inner_text()
        await page.keyboard.press("Escape")
        await page.locator(".idea-card", has_text="Offline mode").locator(".idea-open").click()
        await page.locator(".screen .limits-note").wait_for(timeout=WAIT_MS) if await page.locator(".screen .action-bar, .screen-foot").count() else None
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_folder_opens_the_drawer_of_projects_with_the_goal_s_documents(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["ship"] = stub.goal("ship", "Ship v1", "high", "ready", links=["docs/plan.md", "https://example.com/post"])
        stub.bump({})
        await _pick_goal(page, "ship")
        await page.locator(".board-bar .project-chip").click()
        drawer = page.get_by_role("dialog", name="Projects")
        await drawer.wait_for(timeout=WAIT_MS)
        box = await drawer.bounding_box()
        assert box["x"] == 0 and box["y"] == 0 and box["height"] == 844 and box["width"] < 390        # from the left, the whole height
        assert "ship v1: its documents" in (await drawer.inner_text()).lower() and "example.com" not in await drawer.inner_text()
        await _shot(page, "phone-projects-390x844")
        await drawer.get_by_role("button", name="docs/plan.md").click()
        await page.locator(".screen").get_by_text("The text of docs/plan.md").wait_for(timeout=WAIT_MS)
