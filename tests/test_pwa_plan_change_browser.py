"""Spec 62 part C, the phone (docs/specs/62-spec-after-start.md §0, §5, §7; decisions §75): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py. A goal's
preview names the party's leader in its talk (*Ask or answer Game designer…*, *Sent: Game designer answers in a moment.*; *the Taskmaster* for a Taskmaster party); it has the changed line
(*Re-plan* before the start, *Re-plan what is left* after it, while the leader works, while a change waits; the press 44 px); the hand has the stop *Plan change* (its gem, text and why,
*Take the new plan*, *Keep the plan*, the raised card's other ways) and a taken change deals its added tasks only into the stage shown; the plan's screen shows *The change*; `sw.js` v69."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from orkboard.gui import pwa
from tests.test_pwa_arena_browser import ELF, SCENE, STAMP, SCREENS, _scene, node, task  # noqa: F401
from tests.test_pwa_deal_start_browser import DEAL, RECORD, _centre, _dealt, _ready  # noqa: F401
from tests.test_pwa_shell_browser import NO_SCROLL, SECTIONS, WAIT_MS, Stub, _band, _called, _phone, _pop, _today
from tests.test_pwa_shell_browser import task as plan_task

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

GAME = {"slug": "game-designer", "name": "Game designer", "head": ELF}
PAGE: dict = {}                      # what `ideas.page` answers: a test changes it
ANSWER: dict = {}                    # what `ideas.revise_answer` answers a Take with (or an error)
CHANGE = {"made_at": STAMP, "why": "The sign-in is a passkey only.", "added": 1, "changed": 1, "dropped": 1, "usd_low": 0.4, "usd_high": 1.2,
          "rows": [{"op": "add", "id": "", "title": "Screen for the codes"}, {"op": "change", "id": "k5", "title": "Register endpoint, passkey only"},
                   {"op": "drop", "id": "k4", "title": "Wire the screen to the endpoint"}]}
LABELS = "() => [...document.querySelectorAll('.hand .hc')].map((b) => b.getAttribute('aria-label'))"


def page_doc(**more):
    """`ideas.page` of the goal *WebAuthn register* (it has a passed plan, a talk of nothing yet, and nothing changed)."""
    plan = {"idea": "register", "estimate": {"tasks": 2, "usd_low": 1.2, "usd_high": 3.5}, "passed_at": "x", "todos": [],
            "tasks": [plan_task("k1", "Challenge store", "merged"), plan_task("k2", "Credential table", "running", ["k1"])]}
    return {"slug": "register", "title": "WebAuthn register", "track": "passkey", "state": "working", "size": "M", "talk": [], "busy": False, "checks": [], "lens": [], "plan": plan,
            "sections": [{"name": n, "thesis": f"{n} in one line", "text": f"{n} in one line\nAnd the {n} at length."} for n in SECTIONS],
            "changed": [], "passed": True, "change": None, "revising": False, **more}


def stop(**more):
    """The plan change as `ideas.board` serves it in `needs_you`."""
    return {"kind": "change", "idea": "register", "goal": "passkey", "title": "WebAuthn register", "priority": "high", "blocks": False, "at": STAMP,
            "text": "The plan changes · +1 · 1 changed · −1", "why": "The sign-in is a passkey only.", "added": 1, "changed": 1, "dropped": 1, "usd_low": 0.4, "usd_high": 1.2, **more}


def wait_for_change(**more):
    """A plan change waits: its stop in the hand, its summary on the goal's page, its node's mark."""
    SCENE["needs"].append(stop(**more))
    next(n for n in SCENE["map"]["nodes"] if n["slug"] == "register")["needs_you"] = "change"
    PAGE.update(change=CHANGE, changed=["Gist", "Out"])


def add_tasks():
    """What a taken change adds: a task of Screens in the next wave (a stack the field does not have yet)."""
    register = next(n for n in SCENE["map"]["nodes"] if n["slug"] == "register")
    register["tasks"].append(task("k7", "Screen for the codes", "waiting", SCREENS, 2, after=["k3"]))
    register["needs_you"] = ""


@pytest.fixture(autouse=True)
def _wires(monkeypatch):
    """`ideas.page`, `ideas.revise` and `ideas.revise_answer` as the host answers them (a Take puts the added task on the field and takes the stop away)."""
    PAGE.clear()
    PAGE.update(page_doc())
    ANSWER.clear()
    ANSWER.update(added=2, changed=0, dropped=1, left=[], tasks=True)
    real = Stub.commands

    def commands(self):
        def serve(name, answer):
            def call(a):
                self.calls.append((name, {k: v for k, v in a.items() if k not in ("link", "device")}))
                return answer(a)
            return call

        def revise(a):
            PAGE.update(busy=True, revising=True)
            return {"ok": True}

        def revise_answer(a):
            if ANSWER.get("error"):
                return {"error": ANSWER["error"]}
            SCENE["needs"] = [n for n in SCENE["needs"] if n["kind"] != "change"]
            PAGE.update(change=None, changed=[])
            if a["take"] and ANSWER["tasks"]:
                add_tasks()
            self.bump({})
            counts = {k: ANSWER[k] for k in ("added", "changed", "dropped", "left")} if a["take"] else {"added": 0, "changed": 0, "dropped": 0, "left": []}
            return {"ok": True, **counts}
        return {**real(self), "ideas.page": serve("ideas.page", lambda a: {**copy.deepcopy(PAGE), "slug": a["slug"]}), "ideas.revise": serve("ideas.revise", revise),
                "ideas.revise_answer": serve("ideas.revise_answer", revise_answer)}
    monkeypatch.setattr(Stub, "commands", commands)


async def _open_spec(page):
    """The goal's spec on its own screen, from Today's row of the work started (it opens the goal, `kind: idea`)."""
    await _today(page)
    sheet = page.get_by_role("dialog", name="Today")
    await sheet.wait_for(timeout=WAIT_MS)
    await sheet.locator(".today-list .hrow", has_text="WebAuthn register").click()
    await page.locator(".screen .ask").wait_for(timeout=WAIT_MS)


async def _flash(page, text):
    await page.locator(".flash", has_text=text).first.wait_for(timeout=WAIT_MS)
    return True


# -- the talk names the party's leader (§5) -----------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_talk_names_the_partys_leader_in_its_speaker_its_placeholder_and_its_toast(fake_repo, monkeypatch):
    SCENE["map"]["goals"][0]["leader"] = GAME
    PAGE.update(talk=[{"who": "you", "text": "Passkeys only", "section": "Gist", "at": ""}, {"who": "taskmaster", "text": "Done: the Gist says passkeys only.", "section": "Gist", "at": ""}])
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_spec(page)
        field = page.locator("#ask-field")
        assert await field.get_attribute("placeholder") == "Ask or answer Game designer…" and await field.get_attribute("aria-label") == "Ask or answer Game designer"
        assert [" ".join((await w.inner_text()).split()) for w in await page.locator(".turn .who").all()] == ["You · Gist", "Game designer · Gist"]
        await field.fill("Only passkeys")
        await page.locator(".ask").get_by_role("button", name="Send").click()
        assert await _called(stub, "ideas.say", {"slug": "register", "text": "Only passkeys"})
        assert await _flash(page, "Sent: Game designer answers in a moment.")
        assert "Taskmaster" not in await page.locator(".screen-body").inner_text()


@pytest.mark.asyncio
async def test_a_taskmaster_party_keeps_the_taskmaster_with_its_article(fake_repo, monkeypatch):
    PAGE.update(talk=[{"who": "taskmaster", "text": "Done.", "section": "", "at": ""}])
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_spec(page)
        field = page.locator("#ask-field")
        assert await field.get_attribute("placeholder") == "Ask or answer the Taskmaster…" and await field.get_attribute("aria-label") == "Ask or answer the Taskmaster"
        assert (await page.locator(".turn .who").inner_text()).strip() == "The Taskmaster"                                  # at a sentence's start
        await field.fill("Go on")
        await page.locator(".ask").get_by_role("button", name="Send").click()
        assert await _flash(page, "Sent: the Taskmaster answers in a moment.")


@pytest.mark.asyncio
async def test_the_ask_box_says_who_is_answering_during_a_talk_and_not_while_the_leader_re_plans(fake_repo, monkeypatch):
    SCENE["map"]["goals"][0]["leader"] = GAME
    PAGE.update(busy=True)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_spec(page)
        assert await page.locator(".ask").get_by_text("Game designer is answering…").count() == 1
        PAGE.update(revising=True)
        stub.bump({})
        await page.locator(".ask", has_text="is answering").wait_for(state="detached", timeout=WAIT_MS)


# -- the changed line (§6.1, §7.1) --------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_before_the_start_the_changed_line_names_the_sections_and_re_plans(fake_repo, monkeypatch):
    PAGE.update(state="plan", passed=False, changed=["Gist", "Done when"])
    PAGE["plan"]["passed_at"] = ""
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_spec(page)
        line = page.locator(".changed-line")
        assert (await line.locator("p").inner_text()).strip() == "Gist and Done when changed since the plan."
        press = line.get_by_role("button")
        assert (await press.inner_text()).strip() == "Re-plan" and (await press.bounding_box())["height"] >= 44 and await press.is_enabled()
        sections = await page.locator(".sec").last.bounding_box()
        assert (await line.bounding_box())["y"] >= sections["y"] + sections["height"] - 1                                # under the sections
        await press.click()
        assert await _called(stub, "ideas.plan", {"slug": "register"})
        assert await _flash(page, "The Taskmaster is planning.")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_after_the_start_the_line_re_plans_what_is_left_then_waits_for_the_leader_then_for_the_person(fake_repo, monkeypatch):
    SCENE["map"]["goals"][0]["leader"] = GAME
    PAGE.update(changed=["Gist", "Done when", "Out"])
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_spec(page)
        line = page.locator(".changed-line")
        assert (await line.locator("p").inner_text()).strip() == "Gist, Done when and Out changed since the work started: the tasks not started may change."
        press = line.get_by_role("button")
        assert (await press.inner_text()).strip() == "Re-plan what is left" and (await press.bounding_box())["height"] >= 44
        await press.click()
        assert await _called(stub, "ideas.revise", {"slug": "register"})
        assert await _flash(page, "Game designer re-plans what is left.")
        await line.get_by_text("Game designer re-plans what is left…").wait_for(timeout=WAIT_MS)                       # the leader works: the press is off
        assert await press.is_disabled() and await line.get_attribute("data-state") == "revising"
        PAGE.update(busy=False, revising=False, change=CHANGE)                                                           # the leader proposed a change
        stub.bump({})
        await line.get_by_text("Game designer proposed a plan change: it waits for you.").wait_for(timeout=WAIT_MS)
        assert (await press.inner_text()).strip() == "Re-plan what is left again" and await press.is_enabled() and (await press.bounding_box())["height"] >= 44
        await press.click()                                                                                               # a newer one is asked for
        assert len([c for c in stub.calls if c[0] == "ideas.revise"]) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("more", [{"changed": []}, {"changed": ["Gist"], "state": "done"}])
async def test_a_goal_with_nothing_changed_and_a_goal_done_say_nothing(fake_repo, monkeypatch, more):
    PAGE.update(more)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_spec(page)
        await page.wait_for_timeout(300)
        assert await page.locator(".changed-line").count() == 0


# -- the stop in the hand (§7.2, §7.3) ------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_stop_says_its_kind_its_price_its_text_and_why_and_has_the_two_answers_and_the_screen(fake_repo, monkeypatch):
    wait_for_change()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _pop(page, "Plan change: WebAuthn register")
        assert (await raised.locator(".raised__kind").text_content()).strip() == "Plan change" and "alert" in await raised.get_attribute("class")
        assert (await raised.locator(".ork-gem").first.inner_text()).strip() == "+$0.40–1.20"
        assert (await raised.locator(".raised__text").inner_text()).strip() == "The plan changes · +1 · 1 changed · −1"
        assert (await raised.locator(".raised__why").inner_text()).strip() == "The sign-in is a passkey only."
        buttons = raised.locator(".raised__quick button")
        assert [(await b.inner_text()).strip() for b in await buttons.all()] == ["Take the new plan", "Keep the plan"]
        assert "primary" in await buttons.nth(0).get_attribute("class") and "primary" not in await buttons.nth(1).get_attribute("class")
        assert all([(await b.bounding_box())["height"] >= 43 for b in await buttons.all()])
        assert await raised.get_by_role("button", name="Put it back").is_visible() and await raised.get_by_role("button", name="Open it on its own screen").is_visible()
        await page.keyboard.press("Escape")                                                                               # the raised card's way out
        await page.locator("dialog.raised-dlg[open]").wait_for(state="detached", timeout=WAIT_MS)
        assert await page.locator('.hc[data-kind="change"]').count() == 1


@pytest.mark.asyncio
async def test_a_saving_has_a_minus_and_a_change_of_nothing_has_no_gem(fake_repo, monkeypatch):
    wait_for_change(usd_low=-0.13, usd_high=-0.38)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _pop(page, "Plan change: WebAuthn register")
        assert (await raised.locator(".ork-gem").first.inner_text()).strip() == "−$0.13–0.38"                              # a real minus sign


@pytest.mark.asyncio
async def test_a_change_of_nothing_says_so_and_has_no_gem(fake_repo, monkeypatch):
    wait_for_change(text="The plan stays as it is", added=0, changed=0, dropped=0, usd_low=0, usd_high=0)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _pop(page, "Plan change: WebAuthn register")
        assert (await raised.locator(".raised__text").inner_text()).strip() == "The plan stays as it is" and await raised.locator(".ork-gem").count() == 0
        assert await page.locator('.hc[data-kind="change"] .ork-gem').count() == 0


@pytest.mark.asyncio
async def test_it_lies_among_the_stops_that_hold_work_back_after_a_failure_and_before_a_proposal(fake_repo, monkeypatch):
    wait_for_change()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator('.hc[data-kind="change"]').wait_for(timeout=WAIT_MS)
        labels = await page.evaluate(LABELS)                                                                              # the page keeps the urgency's order
        at = {kind: next(i for i, label in enumerate(labels) if label.startswith(kind)) for kind in ("Failed", "Plan ready", "Plan change", "Proposed", "To look at")}
        assert at["Failed"] < at["Plan ready"] < at["Plan change"] < at["Proposed"] < at["To look at"]


@pytest.mark.asyncio
async def test_keep_the_plan_sends_the_answer_from_the_hand_and_says_the_plan_stays(fake_repo, monkeypatch):
    wait_for_change()
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raised = await _pop(page, "Plan change: WebAuthn register")
        await raised.get_by_role("button", name="Keep the plan").click()
        assert await _called(stub, "ideas.revise_answer", {"slug": "register", "take": False, "via": "hand"})
        assert await _flash(page, "The plan stays as it was.")
        await page.locator('.hc[data-kind="change"]').wait_for(state="detached", timeout=WAIT_MS)
        await page.wait_for_timeout(500)
        assert not [d for d in await page.evaluate(DEAL) if d["kind"] in ("dealt", "fly")]


@pytest.mark.asyncio
async def test_take_the_new_plan_says_what_changed_and_deals_the_added_tasks_from_the_raised_card_into_the_stage_shown(fake_repo, monkeypatch):
    wait_for_change()
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raised = await _pop(page, "Plan change: WebAuthn register")
        cx, cy, width = await _centre(raised)
        await raised.get_by_role("button", name="Take the new plan").click()
        assert await _called(stub, "ideas.revise_answer", {"slug": "register", "take": True, "via": "hand"})
        assert await _flash(page, "The plan changed: 2 added, 1 dropped.")                                                # what the host applied, the non-zero parts
        rec = await _dealt(page)
        dealt = [d for d in rec if d["kind"] == "dealt"]
        assert [(d["key"], d["column"], d["drawn"]) for d in dealt] == [("register|next", "screens", False)]              # dealt, not risen
        for d in dealt:
            assert abs((d["cx"] + float(d["dx"][:-2])) - cx) <= 2 and abs((d["cy"] + float(d["dy"][:-2])) - cy) <= 2     # from the raised card's centre …
            assert abs(float(d["s"]) - width / d["w"]) <= 0.02                                                             # … at its width
        flies = [d for d in rec if d["kind"] == "fly"]
        assert flies and {f["name"] for f in flies} == {"deal"} and {f["duration"] for f in flies} == {"0.3s"} and all(f["timing"] == "steps(6)" for f in flies)
        assert await page.locator('.band[data-band="build"]').get_attribute("aria-selected") == "true"                  # the stage is not switched
        await page.wait_for_function("() => document.querySelectorAll('.deal-fly').length === 0", timeout=WAIT_MS)
        assert await page.locator('.stack[data-column="screens"] .deck[data-key="register|next"]').is_visible()          # it has landed
        await page.locator('.hc[data-kind="change"]').wait_for(state="detached", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_what_was_left_is_said_after_the_changes_and_a_change_of_nothing_taken_says_the_plan_stays(fake_repo, monkeypatch):
    wait_for_change()
    ANSWER.update(added=0, changed=1, dropped=0, left=["Task k2", "Task k3"], tasks=False)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _pop(page, "Plan change: WebAuthn register")
        await raised.get_by_role("button", name="Take the new plan").click()
        assert await _flash(page, "The plan changed: 1 changed. 2 left as they were: they started.")
        ANSWER.update(added=0, changed=0, dropped=0, left=["Task k2"], tasks=False)
        wait_for_change()
        stub.bump({})
        raised = await _pop(page, "Plan change: WebAuthn register")
        await raised.get_by_role("button", name="Take the new plan").click()
        assert await _flash(page, "The plan stays as it was. 1 left as it was: it started.")


@pytest.mark.asyncio
async def test_the_tasks_a_change_adds_to_a_stage_not_shown_are_not_dealt_and_the_stage_is_not_switched(fake_repo, monkeypatch):
    wait_for_change()
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        await _band(page, "lead")                                                                                         # Planning is shown: the added task goes to Implementation
        raised = await _pop(page, "Plan change: WebAuthn register")
        await raised.get_by_role("button", name="Take the new plan").click()
        assert await _called(stub, "ideas.revise_answer", {"slug": "register", "take": True, "via": "hand"})
        await page.locator('.hc[data-kind="change"]').wait_for(state="detached", timeout=WAIT_MS)
        await page.wait_for_timeout(900)
        assert not [d for d in await page.evaluate(DEAL) if d["kind"] in ("dealt", "fly")]
        assert await page.locator('.band[data-band="lead"]').get_attribute("aria-selected") == "true"                      # still Planning
        await _band(page, "build")
        assert await page.locator('.stack[data-column="screens"] .deck[data-key="register|next"]').count() == 1           # it is there when the person looks
        assert not [d for d in await page.evaluate(DEAL) if d["kind"] in ("dealt", "fly")]


@pytest.mark.asyncio
async def test_a_change_that_adds_nothing_leaves_no_deal_waiting_and_reduced_motion_deals_nothing(fake_repo, monkeypatch):
    wait_for_change(added=0, text="The plan changes · 1 changed · −1", usd_low=-0.1, usd_high=-0.2)
    ANSWER.update(added=0, changed=1, dropped=1, left=[], tasks=False)
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raised = await _pop(page, "Plan change: WebAuthn register")
        await raised.get_by_role("button", name="Take the new plan").click()
        assert await _flash(page, "The plan changed: 1 changed, 1 dropped.")
        await page.locator('.hc[data-kind="change"]').wait_for(state="detached", timeout=WAIT_MS)
        add_tasks()                                                                                                       # a task comes within 6 s some other way: it rises as ever
        stub.bump({})
        await page.locator('.stack[data-column="screens"] .deck[data-key="register|next"]').wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(600)
        rec = await page.evaluate(DEAL)
        assert not [d for d in rec if d["kind"] in ("dealt", "fly")] and "register|next" in {d["key"] for d in rec if d["kind"] == "rise"}


@pytest.mark.asyncio
async def test_under_reduced_motion_a_taken_change_deals_nothing(fake_repo, monkeypatch):
    wait_for_change()
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        await page.emulate_media(reduced_motion="reduce")
        raised = await _pop(page, "Plan change: WebAuthn register")
        await raised.get_by_role("button", name="Take the new plan").click()
        assert await _called(stub, "ideas.revise_answer", {"slug": "register", "take": True, "via": "hand"})
        await page.locator('.stack[data-column="screens"] .deck[data-key="register|next"]').wait_for(timeout=WAIT_MS * 2)
        await page.wait_for_timeout(600)
        assert await page.evaluate(DEAL) == [] and await page.locator(".deal-fly").count() == 0 and await page.locator(".deck.is-dealt").count() == 0


@pytest.mark.asyncio
async def test_a_refused_answer_keeps_the_stop_and_says_why(fake_repo, monkeypatch):
    wait_for_change()
    ANSWER.update(error="No plan change waits for this goal")
    async with _phone(fake_repo, monkeypatch, init=RECORD) as (stub, page):
        await _ready(page)
        raised = await _pop(page, "Plan change: WebAuthn register")
        await raised.get_by_role("button", name="Take the new plan").click()
        assert await _flash(page, "No plan change waits for this goal")
        assert await page.locator("dialog.raised-dlg[open]").count() == 1                                                  # the card stays up
        assert not [d for d in await page.evaluate(DEAL) if d["kind"] in ("dealt", "fly")]


# -- the plan's screen (§7.4) ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_plan_screen_shows_the_change_with_its_rows_its_cost_and_the_two_presses(fake_repo, monkeypatch):
    wait_for_change()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _pop(page, "Plan change: WebAuthn register")
        await raised.get_by_role("button", name="Open it on its own screen").click()                                      # a press elsewhere on the stop opens the plan screen
        block = page.locator(".screen .plan-change")
        await block.wait_for(timeout=WAIT_MS)
        assert (await block.locator("h3").text_content()).strip() == "The change" and (await block.locator(".change-why").inner_text()).strip() == "The sign-in is a passkey only."
        rows = block.locator(".change-row")
        assert [(await r.get_attribute("data-op"), (await r.locator(".change-mark").inner_text()).strip(), (await r.locator(".change-title").inner_text()).strip()) for r in await rows.all()] == [
            ("add", "+", "Screen for the codes"), ("change", "~", "Register endpoint, passkey only"), ("drop", "−", "Wire the screen to the endpoint")]
        assert [await r.locator(".change-mark").get_attribute("aria-label") for r in await rows.all()] == ["added", "changed", "dropped"]
        drop = rows.nth(2)
        assert "line-through" in await drop.evaluate("e => getComputedStyle(e).textDecorationLine") and "line-through" not in await rows.nth(0).evaluate("e => getComputedStyle(e).textDecorationLine")
        assert await drop.evaluate("e => getComputedStyle(e).color") != await rows.nth(0).evaluate("e => getComputedStyle(e).color")           # muted
        assert (await block.locator(".change-cost").inner_text()).strip() == "+$0.40–1.20"
        assert await block.bounding_box() and (await block.bounding_box())["y"] < (await page.locator(".screen .plan").bounding_box())["y"]                # over the plan
        bar = page.locator(".screen-bar")
        buttons = bar.locator("button")
        assert [(await b.inner_text()).strip() for b in await buttons.all()] == ["Take the new plan", "Keep the plan"] and "primary" in await buttons.nth(0).get_attribute("class")
        assert all([(await b.bounding_box())["height"] >= 44 for b in await buttons.all()]) and await page.evaluate(NO_SCROLL)
        await buttons.nth(1).click()                                                                                      # Keep the plan, from the screen
        assert await _called(stub, "ideas.revise_answer", {"slug": "register", "take": False})
        assert await _flash(page, "The plan stays as it was.")
        await page.locator(".screen .plan-change").wait_for(state="detached", timeout=WAIT_MS)
        assert await page.locator(".screen .plan").is_visible()


@pytest.mark.asyncio
async def test_take_the_new_plan_from_the_plan_screen_says_what_changed_and_the_screen_has_no_change_after_it(fake_repo, monkeypatch):
    wait_for_change()
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _pop(page, "Plan change: WebAuthn register")
        await raised.get_by_role("button", name="Open it on its own screen").click()
        await page.locator(".screen .plan-change").wait_for(timeout=WAIT_MS)
        await page.locator(".screen-bar").get_by_role("button", name="Take the new plan").click()
        assert await _called(stub, "ideas.revise_answer", {"slug": "register", "take": True})
        assert await _flash(page, "The plan changed: 2 added, 1 dropped.")
        await page.locator(".screen .plan-change").wait_for(state="detached", timeout=WAIT_MS)
        assert await page.locator(".screen-bar button").count() == 0


@pytest.mark.asyncio
async def test_a_plan_screen_with_no_change_waiting_shows_none_and_the_cache_is_v69(fake_repo, monkeypatch):
    assert 'const CACHE = "orkcraft-app-v77";' in (Path(pwa.__file__).parent / "static" / "pwa" / "sw.js").read_text(encoding="utf-8")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _pop(page, "Plan ready: Recovery codes")
        await raised.get_by_role("button", name="Open the plan").click()
        await page.locator(".screen .plan").wait_for(timeout=WAIT_MS)
        assert await page.locator(".screen .plan-change").count() == 0
