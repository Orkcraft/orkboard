"""Spec 49 part C, the phone (docs/specs/49-one-window.md §10, §11, "Tests → C"; spec 50 §6): Chromium at 390 × 844 against the stub of test_pwa_shell_browser.py with
a Board of one party, *Sign in with a passkey*, as the mockup draws it: a leader, two builders and two checkers, goals in each stage, a plan, a
question, a proposal and a failure waiting, two results to look at, two goals done and one of them flagged. No tab bar; the top bar's project button and the limits' sheet, Today in the menu; the goals bar with the gate at its right
(two rows under the top bar: it and the stage switch); the stage switch; the members' cards and their marks; a member's solo; the stops along the bottom, popped out with their quick answers; `#needs`;
44 px targets. The members stand under the stage switch and their tasks run down toward the bottom row in rows by phase (the top row lit); the fan lies across the width; the create
button floats over the field. The parties' sheet, the goals bar's sheet, the stacks, the spread, the create button's deck and the flag line are tests/test_pwa_decks_browser.py's."""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path

import pytest

from tests.test_pwa_shell_browser import FAB, NO_SCROLL, WAIT_MS, Stub, _band, _called, _menu, _phone, _pop, _shot, _today, _where  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

SHOTS = os.environ.get("ARENA_SHOTS", "")                 # a folder: screenshots of the window are kept there

OWN = {"craft": "engineering", "race": "peon", "tier": "warrior"}
ELDER = {"craft": "engineering", "race": "peon", "tier": "elder"}
ELF = {"craft": "design", "race": "elf", "tier": "warrior"}
GNOME = {"craft": "marketing", "race": "gnome", "tier": "laborer"}
TASKMASTER = {"slug": "taskmaster", "name": "Taskmaster", "head": ELDER}
BACKEND = {"slug": "backend", "name": "Backend"}
SCREENS = {"slug": "screens", "name": "Screens"}
REVIEWER = {"slug": "reviewer", "name": "Reviewer"}
WORDS = {"slug": "words", "name": "Words"}
STAMP = "2026-10-21T10:00:00"


ELEMENT = {"register": "meadow", "signin": "ice", "cookie": "dust", "recovery": "void", "second": "dust", "ratelimit": "meadow", "pagewords": "ice", "magic": "lava", "log": "void",
           "button": "ice", "kept": "meadow"}                                      # a goal's element (spec 50 §2.3): given once, the least used among its party's open goals
FLAG = {"at": "2026-10-14T16:20:00", "by": "gate", "commit": "abc1234", "tasks": 4, "first_time": 4, "usd": 2.1, "days": 3}


def node(slug, title, state, stage, **more):
    return {"slug": slug, "goal": "passkey", "title": title, "short": title, "state": state, "element": ELEMENT.get(slug, ""), "flag": None, "queue": "", "held_until": "", "start_at": "", "priority": "normal", "size": "M",
            "risk": "", "tier": 1, "depends_on": [], "waits_on": [], "waits": None, "needs_you": "", "progress": {"done": 0, "total": 0}, "tasks": [], "estimate": None,
            "by_itself": False, "folded": False, "updated": STAMP, "stage": stage, "round": 1, "usd": None, "plan_estimate": None, "asked": [], "results": [], "checks": [], **more}


def task(tid, title, state, by, wave=1, band="build", after=(), **more):
    head = {"backend": OWN, "screens": ELF, "reviewer": ELDER, "words": GNOME}[by["slug"]]
    return {"id": tid, "title": title, "short": title, "state": state, "after": list(after), "tier": "warrior", "head": head, "by": by, "band": band, "wave": wave,
            "error": "", "note": "", "round": 1, "cost": None, "started": "", "tag": "Code", **more}


def result(idea, idea_title, tid, title, **more):
    return {"idea": idea, "idea_title": idea_title, "task": tid, "title": title, "round": 1, "tests": {"passed": 14, "failed": 0, "failing": [], "tail": "14 passed", "green": True},
            "diff": {"files": 3, "added": 146, "removed": 0}, "cost": 0.42, "conflict": "", "finished": STAMP, "estimate": None, "over": False, **more}


def member(m, band, head, state="free", why=""):
    return {**m, "head": head, "band": band, "state": state, "why": why}


def scene():
    """What the host answers for the goal, in a dict a test changes before the page reads it."""
    k1 = task("k1", "Challenge store", "review", BACKEND, 1, tests=None)
    nodes = [
        node("recovery", "Recovery codes", "plan", "planning", needs_you="plan", plan_estimate={"usd_low": 1.0, "usd_high": 2.0}, estimate={"usd_low": 1.0, "usd_high": 2.0},
             tasks=[task("p1", "Codes table", "waiting", BACKEND), task("p2", "Show the codes once", "waiting", SCREENS, 2, after=["p1"]),
                    task("p3", "Code review", "waiting", REVIEWER, 3, "check")]),
        node("second", "Passkey on a second device", "asks", "planning", needs_you="asks",
             asked=[{"ask": "Should a lost phone sign out every passkey of that person?", "choices": ["Yes, every passkey of that person", "Only the lost phone’s passkey",
                                                                                                 "Ask the person when they report it"], "pick": 1, "why": "The least surprise",
                     "by": {**REVIEWER, "head": ELDER}}]),
        node("ratelimit", "Rate-limit the sign-in", "reading", "planning"),
        node("pagewords", "Words of the sign-in page", "proposed", "planning", needs_you="proposal"),
        node("magic", "Magic link if the passkey fails", "raw", "planning", queue="night"),
        node("log", "A log of every sign-in", "raw", "planning", queue="hold"),
        node("register", "WebAuthn register", "working", "implementation", progress={"done": 0, "total": 6}, usd=1.8, plan_estimate={"usd_low": 2.0, "usd_high": 3.0},
             tasks=[k1, task("k2", "Credential table and migration", "running", BACKEND, 1, started="2026-10-21T09:40:00"),
                    task("k3", "Register screen", "running", SCREENS, 1, started="2026-10-21T09:50:00"),
                    task("k5", "Register endpoint", "waiting", BACKEND, 2, after=["k1", "k2"]),
                    task("k4", "Wire the screen to the endpoint", "waiting", SCREENS, 3, after=["k3", "k5"]),
                    task("c1", "Code review", "waiting", REVIEWER, 4, "check")],
             results=[result("register", "WebAuthn register", "k1", "Challenge store")]),
        node("signin", "Sign in with the passkey", "working", "checking", progress={"done": 3, "total": 5}, usd=2.9,
             tasks=[task("s1", "Sign-in endpoint", "merged", BACKEND), task("s2", "Sign-in screen", "merged", SCREENS), task("s3", "Remember this device", "merged", BACKEND, 2),
                    task("c1", "Code review", "running", REVIEWER, 3, "check", started="2026-10-21T09:53:00"),
                    task("c2", "Words on the screens", "review", WORDS, 3, "check")],
             results=[result("signin", "Sign in with the passkey", "c2", "Words on the screens", check="Words", tests={"passed": None, "failed": None, "tail": "", "ran": False},
                             findings=[{"where": "signin.html", "what": "Not allowed does not say what next", "fixed": False}])]),
        node("cookie", "Session cookie flags", "working", "implementation", progress={"done": 0, "total": 2}, usd=0.35,
             tasks=[task("q1", "Secure cookie flags", "failed", BACKEND, 1, error="The session ended without a change: “You changed no file.”"),
                    task("q2", "Sign out everywhere, in Settings", "held", SCREENS, 1, note="reserve · after 18:00")]),
        node("button", "Passkey button on the sign-in page", "done", "done", folded=True, tasks=[task("b1", "The button", "merged", SCREENS)], flag=FLAG),
        node("kept", "Where the credentials are kept", "done", "done", folded=True),
    ]
    party = [member(TASKMASTER, "lead", ELDER, "needs", "plan"), member(BACKEND, "build", OWN, "needs", "failed"), member(SCREENS, "build", ELF, "work"),
             member(REVIEWER, "check", ELDER, "work"), member(WORDS, "check", GNOME, "needs", "plan")]
    goal = {"slug": "passkey", "title": "Sign in with a passkey", "short": "Passkey", "priority": "high", "state": "ready", "craft": "engineering", "race": "peon",
            "done_when": ["a person signs in on a phone without a password"], "ideas": 9, "done": 2, "usd": 6.4, "leader": TASKMASTER, "party": party,
            "brief": "Builds the app: the API, the database and the screens of the sign-in", "flags": 1, "waits_main": 1,
            "today": {"merged": 3, "usd": 1.1}, "team": [{"slug": m["slug"], "name": m["name"], "head": m["head"], "checks": m["band"] == "check", "every": False} for m in party[1:]],
            "verdict": None}
    needs = [
        {"kind": "plan", "idea": "recovery", "goal": "passkey", "title": "Recovery codes", "text": "Plan ready · 3 tasks", "priority": "high", "blocks": False, "at": STAMP},
        {"kind": "asks", "idea": "second", "goal": "passkey", "title": "Passkey on a second device", "text": "Should a lost phone sign out every passkey of that person?",
         "questions": ["Should a lost phone sign out every passkey of that person?"], "priority": "high", "blocks": False, "at": STAMP,
         "asked": nodes[1]["asked"]},
        {"kind": "failed", "idea": "cookie", "goal": "passkey", "title": "Session cookie flags", "text": "Secure cookie flags: failed", "priority": "high", "blocks": True, "at": STAMP},
        {"kind": "proposal", "idea": "pagewords", "goal": "passkey", "title": "Words of the sign-in page", "text": "The screens merged so far say passkey three ways", "priority": "high",
         "blocks": False, "at": STAMP},
    ]
    roles = [
        {"role": "taskmaster", "name": "Taskmaster", "model": "elder", "max_parallel": 1, "builtin": True, "spend_today": 0.6, "state": "waiting", "waits_on": None, "chips": [],
         "week": {"plans": 6, "finished": 6, "first_time": 5, "merged": 5, "spent": 0.72}, "usd_task": None, "head": ELDER, "harness": {"id": "claude", "name": "Claude"}},
        {"role": "backend", "name": "Backend", "model": "warrior", "max_parallel": 2, "builtin": False, "spend_today": 1.2, "chips": [], "kinds": ["code", "tests"],
         "week": {"finished": 5, "merged": 4, "first_time": 4, "spent": 1.9, "usd_per_merged": 0.475}, "usd_task": 0.38, "head": OWN, "harness": {"id": "claude", "name": "Claude"}},
        {"role": "screens", "name": "Screens", "model": "warrior", "max_parallel": 2, "builtin": False, "spend_today": 0.3, "chips": [], "kinds": ["docs"],
         "week": {"finished": 2, "merged": 2, "first_time": 2, "spent": 0.5, "usd_per_merged": None}, "usd_task": 0.3, "head": ELF, "harness": {"id": "codex", "name": "Codex"}},
        {"role": "reviewer", "name": "Reviewer", "model": "elder", "max_parallel": 1, "builtin": False, "spend_today": 0.2, "chips": [], "kinds": [],
         "week": {"finished": 6, "merged": 6, "first_time": 6, "spent": 1.5, "usd_per_merged": 0.25}, "check_week": {"checks": 6, "clean": 4, "caught": 2, "left": 1, "usd_per_check": 0.25},
         "usd_task": 0.25, "head": ELDER, "harness": {"id": "claude", "name": "Claude"}},
        {"role": "words", "name": "Words", "model": "laborer", "max_parallel": 1, "builtin": False, "spend_today": 0.04, "chips": [], "kinds": [],
         "week": {"finished": 1, "merged": 1, "first_time": 1, "spent": 0.04, "usd_per_merged": None}, "check_week": {"checks": 4, "clean": 1, "caught": 3, "left": 0, "usd_per_check": None},
         "usd_task": 0.05, "head": GNOME, "harness": {"id": "claude", "name": "Claude"}},
    ]
    return {"map": {"goals": [goal], "nodes": nodes, "edges": [], "rev": "1"}, "needs": needs, "agents": {"roles": roles, "done_today": []},
            "results": [result("register", "WebAuthn register", "k1", "Challenge store"),
                        result("signin", "Sign in with the passkey", "c2", "Words on the screens", check="Words", tests={"passed": None, "failed": None, "tail": "", "ran": False},
                               findings=[{"where": "signin.html", "what": "Not allowed does not say what next", "fixed": False}], cost=0.04)],
            "events": [{"at": "12:40", "mark": "✓", "tone": "ok", "words": "merged into dev", "title": "Remember this device", "goal": "passkey", "idea": "signin", "task": "s3",
                        "open": {"kind": "result", "slug": "signin", "task": "s3"}},
                       {"at": "12:10", "mark": "↺", "tone": "muted", "words": "sent back", "title": "Sign-in screen", "goal": "passkey", "idea": "signin", "task": "s2",
                        "open": {"kind": "result", "slug": "signin", "task": "s2"}},
                       {"at": "11:55", "mark": "✗", "tone": "danger", "words": "failed", "title": "Secure cookie flags", "goal": "passkey", "idea": "cookie", "task": "q1",
                        "open": {"kind": "task", "slug": "cookie", "task": "q1"}},
                       {"at": "10:30", "mark": "▸", "tone": "ink", "words": "the work started", "title": "WebAuthn register", "goal": "passkey", "idea": "register", "task": "",
                        "open": {"kind": "idea", "slug": "register"}},
                       {"at": "09:00", "mark": "✓", "tone": "ok", "words": "dev merged into main", "title": "dev → main", "goal": "", "idea": "", "task": "", "open": {"kind": "gate", "slug": ""}}],
            "gate": {"main": "main", "same": False, "commits": 4, "files": 9,
                     "ideas": [{"slug": "button", "title": "Passkey button on the sign-in page", "goal": "passkey", "tasks": 1},
                               {"slug": "kept", "title": "Where the credentials are kept", "goal": "passkey", "tasks": 2}]}}


SCENE: dict = {}


@pytest.fixture(autouse=True)
def _scene(monkeypatch):
    """The Board the stub answers with: the goal of `scene()`, the Needs you rows and the results at Review, the agents and the day's events."""
    SCENE.clear()
    SCENE.update(scene())
    real, init = Stub.commands, Stub.__init__

    def commands(self):
        def serve(name, answer):
            def call(a):
                a = {k: v for k, v in a.items() if k != "link" and (k != "device" or name == "ideas.log")}
                self.calls.append((name, dict(a)))
                return answer(a)
            return call

        def ideas_board(a):
            return {"tracks": [Stub.goal("passkey", "Sign in with a passkey", "high", "ready")], "ideas": [], "needs_you": copy.deepcopy(SCENE["needs"]), "target": self.target,
                    "autostart": self.autostart, "night": self.night, "rev": self.rev, "demo": False}

        def review(a):
            return {"into": self.into, "push": self.push, "branches": ["dev", "main"], "results": copy.deepcopy(SCENE["results"])}
        return {**real(self), "ideas.map": serve("ideas.map", lambda a: copy.deepcopy(SCENE["map"])), "ideas.board": serve("ideas.board", ideas_board),
                "ideas.agents": serve("ideas.agents", lambda a: copy.deepcopy(SCENE["agents"])), "ideas.review_list": serve("ideas.review_list", review),
                "ideas.today": serve("ideas.today", lambda a: {"events": copy.deepcopy(SCENE["events"])}),
                "ideas.gate": serve("ideas.gate", lambda a: {"into": self.into, **copy.deepcopy(SCENE["gate"])})}

    def new_init(self):
        init(self)
        self.goals = {"passkey": Stub.goal("passkey", "Sign in with a passkey", "high", "ready")}
    monkeypatch.setattr(Stub, "commands", commands)
    monkeypatch.setattr(Stub, "__init__", new_init)


async def _redrawn(stub, page, ms=700):
    """The Board changed and was read again (`ideas.map` asked once more), and the page had the time to draw it."""
    before = len([c for c in stub.calls if c[0] == "ideas.map"])
    stub.bump({})
    for _ in range(100):
        if len([c for c in stub.calls if c[0] == "ideas.map"]) > before:
            break
        await page.wait_for_timeout(50)
    await page.wait_for_timeout(ms)


async def _redrawn(stub, page, ms=700):
    """The Board changed and was read again (`ideas.map` asked once more), and the page had the time to draw it."""
    before = len([c for c in stub.calls if c[0] == "ideas.map"])
    stub.bump({})
    for _ in range(100):
        if len([c for c in stub.calls if c[0] == "ideas.map"]) > before:
            break
        await page.wait_for_timeout(50)
    await page.wait_for_timeout(ms)


async def _shot_to(page, name: str) -> None:
    """A screenshot of the window into the folder named by ARENA_SHOTS (a test of the window's look, kept by hand)."""
    if SHOTS:
        Path(SHOTS).mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(Path(SHOTS) / f"{name}.png"))


async def _about(page):
    """About this party: the Goals sheet's head says *About Passkey ›* and opens it (spec 50 §6.2)."""
    await page.locator(".gbar__head").click()
    await page.get_by_role("dialog", name="Goals").get_by_role("button", name=re.compile("^About ")).click()
    sheet = page.get_by_role("dialog", name="About this party")
    await sheet.wait_for(timeout=WAIT_MS)
    return sheet


@pytest.mark.asyncio
async def test_the_window_is_one_screen_with_no_tab_bar(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        assert await page.get_by_role("tab", name=re.compile("Board|Agents|Needs you")).count() == 0        # Board, Agents and Needs you are no tabs
        assert await page.locator(".tabs, .tab-bar, nav.tabs").count() == 0
        assert [await t.get_attribute("aria-label") for t in await page.get_by_role("tab").all()][0].startswith("Planning")      # the only tabs are the stage switch's
        bar = page.locator(".board-bar")
        assert await bar.get_by_role("button", name="Menu").is_visible() and await bar.locator(".projbtn").is_visible() and await bar.locator(".limit-chip").is_visible()
        assert await bar.locator(".today, .bar-btn.today").count() == 0                                          # Today is the menu's
        assert (await bar.bounding_box())["height"] <= 50 and await page.evaluate(NO_SCROLL)                  # one line, no band above it
        await page.wait_for_timeout(600)
        await _shot_to(page, "board-implementation")
        await _band(page, "lead")
        await _shot_to(page, "board-planning")
        await _band(page, "build")
        await page.locator('button.band__face[data-member="backend"]').click()
        await _shot_to(page, "member-solo")
        await page.locator('[data-act="everyone"]').click()
        await _pop(page, "Plan ready: Recovery codes")
        await _shot_to(page, "stop-popped-plan")
        await page.keyboard.press("Escape")
        await _pop(page, "To look at: Challenge store")
        await _shot_to(page, "stop-popped-look")
        await page.keyboard.press("Escape")


@pytest.mark.asyncio
async def test_today_is_the_menus_item_with_its_count_and_lists_the_partys_day_newest_first_a_tap_opens_it_and_done_follows(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(500)
        today = (await _menu(page)).locator('[data-act="today"]')
        assert await today.locator(".ork-count").inner_text() == "5" and "5 events" in await today.get_attribute("aria-label")      # the menu's item: a clock, Today, its count
        assert (await today.inner_text()).split() == ["Today", "5"] and await today.locator(".ork-icon").count() == 1
        await today.click()
        await page.locator("dialog.drawer").wait_for(state="hidden", timeout=WAIT_MS)                          # the menu is put away; Today's sheet is over the board
        sheet = page.get_by_role("dialog", name="Today")
        await sheet.wait_for(timeout=WAIT_MS)
        rows = sheet.locator(".today-list .hrow")
        assert [" ".join((await r.inner_text()).split()) for r in await rows.all()][:3] == [
            "Remember this device 12:40 · merged into dev", "↺ Sign-in screen 12:10 · sent back", "Secure cookie flags 11:55 · failed"]       # newest first, a mark and a time each
        assert [await r.locator(".hrow__mark .ork-sign").get_attribute("class") for r in (rows.nth(0), rows.nth(2))] == ["ork-sign check", "ork-sign cross"]     # the marks are orkUI's signs
        assert [await r.get_attribute("data-open") for r in await rows.all()] == ["result", "result", "task", "idea", "gate"]
        assert "Done · 2" in await sheet.locator("h3").text_content()
        assert await sheet.locator(".done-row").count() == 2
        for r in await rows.all():
            assert (await r.bounding_box())["height"] >= 44
        await rows.nth(2).click()                                                                    # a tap opens it on its own screen
        await page.locator(".screen").wait_for(state="visible", timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "today", "ref": "", "device": "phone"})              # the sheet opened …
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "task", "ref": "cookie/q1", "device": "phone", "via": "today"})  # … and the row's open, said where it came from
        await page.get_by_role("button", name="Back", exact=True).click()
        await _today(page)
        await rows.nth(4).click()                                                                    # the gate's event opens the gate
        await page.locator(".screen").get_by_text("dev", exact=False).first.wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_the_project_button_says_the_project_the_goals_bar_the_party_and_has_the_gate_and_the_header_is_two_rows(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        where = page.locator(".board-bar .projbtn")
        await where.wait_for(timeout=WAIT_MS)
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        assert await page.locator(".partydeck").get_attribute("data-goal") == "passkey" and await page.locator(".board-bar .ork-count").count() == 0      # no count in the top bar (spec 52 §5.8)
        label = await where.get_attribute("aria-label")
        assert label == "Project project. A tap shows your projects" and "%" not in label + await where.inner_text()      # a party has no end: no %
        assert await where.inner_text() == "project" and await where.locator(".projbtn__name").evaluate("e => getComputedStyle(e).fontSize") == "12px"
        assert await where.locator(".ork-chev").count() == 1 and (await where.bounding_box())["height"] >= 44                       # harbor ⌄
        bar, menu, limits = [await page.locator(s).bounding_box() for s in (".board-bar", ".board-bar .menu", ".board-bar .limit-chip")]
        wb = await where.bounding_box()
        assert wb["x"] >= menu["x"] + menu["width"] and wb["x"] + wb["width"] <= limits["x"] + 1 and await page.evaluate(NO_SCROLL)       # it fits beside the menu and the limits
        assert await page.locator(".gchips, .gchip, .ghead, .ibar, .pbar").count() == 0                # no chips row, no header, no party bar: the goals bar says the party
        line = page.locator(".gbar")
        assert " ".join((await line.locator(".gbar__head").inner_text()).split()) == "Passkey · 2 of 9 goals done" and "%" not in await line.inner_text()    # the party and its done goals
        assert (await line.bounding_box())["height"] == 44 and await line.locator(".gbar__quiet").evaluate("e => getComputedStyle(e).fontSize") == "12px"       # one quiet line, 44 px
        first, second = await line.bounding_box(), await page.locator(".stagebar").bounding_box()
        assert round(first["y"]) == round(bar["y"] + bar["height"]) and round(second["y"]) == round(first["y"] + first["height"])           # two rows: the goals bar, the stage switch
        assert "k at work" not in await line.inner_text() and "ask you" not in await line.inner_text()    # the stage switch's counts say it
        gate = line.locator(".gbar__gate")
        assert (await gate.bounding_box())["x"] > (await line.locator(".gbar__head").bounding_box())["x"] + 100                              # the gate at its right
        assert " ".join((await gate.inner_text()).split()) == "dev main 2" and await gate.locator(".ork-sign.after").count() == 1 and await gate.is_enabled()      # dev → main and its count
        assert "2 goals in dev wait for main" in await gate.get_attribute("title") and (await gate.get_attribute("aria-label")).startswith("dev → main: 2 goals in dev wait for main")
        assert await gate.evaluate("e => getComputedStyle(e).backgroundColor") == "rgba(0, 0, 0, 0)" and "primary" not in await gate.get_attribute("class")   # quiet: no green
        await gate.click()                                                                           # its screen, full over the board
        screen = page.locator(".screen")
        await screen.get_by_role("button", name="Merge dev into main").wait_for(timeout=WAIT_MS)
        text = await screen.inner_text()
        assert " ".join((await screen.locator(".screen-title").inner_text()).split()) == "The gate dev main" and await screen.locator(".screen-title .ork-sign.after").count() == 1
        assert "2 goals in dev wait for main" in text and "Passkey button on the sign-in page" in text and "Nothing reaches main without you." in text
        await screen.get_by_role("button", name="Merge dev into main").click()
        assert await _called(stub, "ideas.gate_merge")
        await page.get_by_role("button", name="Back", exact=True).click()
        SCENE["gate"] = {"main": "main", "same": False, "commits": 0, "files": 0, "ideas": []}      # main has every goal of dev: the button is off
        stub.bump({})
        await page.locator(".gbar__gate:disabled").wait_for(timeout=WAIT_MS * 2)
        assert " ".join((await page.locator(".gbar__gate").inner_text()).split()) == "main" and await page.locator(".gbar__gate .ork-sign.check").count() == 1       # main ✓
        SCENE["gate"] = {"main": "main", "same": True, "commits": 0, "files": 0, "ideas": []}        # one branch: there is no gate
        stub.bump({})
        await page.locator(".gbar__gate").wait_for(state="detached", timeout=WAIT_MS * 2)


@pytest.mark.asyncio
async def test_about_this_party_is_a_sheet_of_blocks_with_its_flags_and_only_a_verdict_of_before_says_before(fake_repo, monkeypatch):
    SCENE["map"]["goals"][0]["verdict"] = {"met": True, "by": "Growth", "at": "2026-10-18T10:00:00"}      # a party's old flag: history
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _about(page)
        assert (await sheet.locator(".party-about__sec").evaluate_all("els => els.map((e) => e.dataset.sec)")) == ["What it is for", "The party", "Checks on every goal", "What it costs", "Its flags"]
        assert "led by Taskmaster" in await sheet.locator(".party-about__who").inner_text()
        assert "Builds the app: the API, the database and the screens of the sign-in" in await sheet.locator('[data-sec="What it is for"]').inner_text()
        party = " ".join((await sheet.locator('[data-sec="The party"]').inner_text()).split())
        assert "Taskmaster · leads · $0.12 a plan" in party and "Backend · builds · $0.38 a result" in party and "Reviewer · checks · $0.25 a goal" in party
        checks = " ".join((await sheet.locator('[data-sec="Checks on every goal"]').inner_text()).split())
        assert "Reviewer checks" in checks and "caught 2/6 lately" in checks and "Words checks" in checks and "idea" not in checks     # the library's words said as the goal's
        cost = " ".join((await sheet.locator('[data-sec="What it costs"]').inner_text()).split())
        assert "≈$6.40 so far · today 3 merged · ≈$1.10" in cost and "about $2–6 a goal with this party" in cost
        flags = sheet.locator('[data-sec="Its flags"]')
        assert await flags.locator(".ork-sign.flag").count() == 1 and "14 Oct · ≈$2.10 · 4 of 4 first time" in await flags.inner_text()
        assert "Before: met, says Growth · 18 October" in await sheet.inner_text()                      # only a party with a verdict of before
        assert await sheet.get_by_role("button", name="Edit the party").is_visible() and await sheet.get_by_role("button", name="Save it to your parties").is_visible()
        assert await sheet.get_by_role("button", name="Add to the party").is_visible() and "free seat" in await sheet.locator(".party-about__seats").inner_text()   # Add to the party: beside Edit the party
        assert not re.search(r"Metrics|Verdict|accept", await sheet.inner_text())                       # no metrics, no verdict, no *Ask … to accept*
        await sheet.get_by_role("button", name="Edit the party").click()                                # Edit the party: its sheet
        edit = page.get_by_role("dialog", name="Edit the party")
        await edit.wait_for(timeout=WAIT_MS)
        await page.keyboard.press("Escape")
        SCENE["map"]["goals"][0].pop("verdict")
        await _redrawn(stub, page)
        sheet = await _about(page)
        assert "Before:" not in await sheet.inner_text()
        await sheet.get_by_role("button", name="Save it to your parties").click()                       # the party saved as one of yours
        await sheet.get_by_label("Name of your party").fill("Tech")
        await sheet.get_by_role("button", name="Save", exact=True).click()
        assert await _called(stub, "ideas.party_save", {"goal": "passkey", "name": "Tech"})


@pytest.mark.asyncio
async def test_the_stage_switch_starts_on_the_first_stage_with_work_counts_the_stops_and_shows_only_its_columns(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        bands = page.locator(".band")
        await bands.first.wait_for(timeout=WAIT_MS)
        assert [await b.get_attribute("role") for b in await bands.all()] == ["tab", "tab", "tab"] and await page.get_by_role("tablist").count() == 1
        assert await page.locator('.band[data-band="build"]').get_attribute("aria-selected") == "true"     # a builder has an open task: Implementation first
        labels = [await b.get_attribute("aria-label") for b in await bands.all()]
        assert labels[0].startswith("Planning: ") and labels[1].startswith("Implementation: ") and labels[2].startswith("Checking: ")
        assert await page.locator('.band[data-band="build"] .band__sign .ork-sign.cross').count() == 1         # the failure sits in Implementation (spec 52 §5.3: a sign, no number)
        assert await page.locator('.band[data-band="lead"] .band__sign .ork-sign.alert').count() == 1          # the plan and the proposal in Planning
        assert await page.locator(".band .ork-count").count() == 0
        assert [await t.get_attribute("data-member") for t in await page.locator(".colname").all()] == ["backend", "screens"]     # only the builders' columns
        for b in await bands.all():
            assert (await b.bounding_box())["height"] >= 44
        await _band(page, "lead")                                                                    # a press shows another stage's columns
        assert [await t.get_attribute("data-member") for t in await page.locator(".colname").all()] == ["taskmaster"]
        await _band(page, "check")
        assert [await t.get_attribute("data-member") for t in await page.locator(".colname").all()] == ["reviewer", "words"]
        assert await page.evaluate(NO_SCROLL)
        for band in ("lead", "build", "check"):                                                      # up to three columns share the width: no sideways scroll
            await _band(page, band)
            assert await page.locator(".arena-scroll").evaluate("e => e.scrollWidth <= e.clientWidth + 1")
        SCENE["map"]["goals"][0]["party"].append(member({"slug": "extra", "name": "Extra"}, "build", OWN))          # three builders still fit
        SCENE["map"]["goals"][0]["party"].append(member({"slug": "more", "name": "More"}, "build", OWN))           # four fit too (spec 67 §1.1, the most of a stage): the columns share the width, nothing scrolls
        stub.bump({})
        await _band(page, "build")
        await page.locator(".colname").nth(3).wait_for(timeout=WAIT_MS * 2)
        assert await page.locator(".arena-scroll").evaluate("e => e.scrollWidth <= e.clientWidth") and await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_member_is_a_face_on_the_stage_switch_its_runs_and_price_are_in_its_solo_and_the_marks_are_served(fake_repo, monkeypatch):
    SCENE["map"]["goals"][0]["party"][2]["state"] = "tonight"                                        # Screens keeps its work for tonight
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".band__face").first.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(300)
        assert await page.locator(".token").count() == 0                                             # no framed row: the face is the member (spec 53 §1.3)
        backend, screens = page.locator('button.band__face[data-member="backend"]'), page.locator('button.band__face[data-member="screens"]')
        assert await backend.locator("img.ork-race__head").get_attribute("src") == "races/peon-warrior.png"
        assert await backend.locator(".band__sign .ork-sign.cross").count() == 1 and await screens.locator(".band__sign").count() == 0     # a failure: ✗ on its face; at work or tonight: no sign
        await _band(page, "lead")
        assert await page.locator('button.band__face[data-member="taskmaster"] .band__sign .ork-sign.alert').count() == 1                # any other stop: ! on the leader's face
        await _band(page, "build")
        await backend.click()                                                                         # its runs, redos and price are in its solo
        solo = page.locator(".solo")
        await solo.wait_for(timeout=WAIT_MS)
        card = " ".join((await solo.locator(".solo__card").inner_text()).split())
        assert "$0.38 a run" in card and "Backend · Seasoned ork · Engineering" in card and "Takes: code, tests" in card and "5/1 runs/sent back" in card      # its head's words, its kit, its runs and redos, its price
        for src in ("marks/harness-claude.png", "marks/harness-codex.png", "marks/rank-2.png", "marks/rank-2@2x.png", "marks/rank-3.png"):                    # the phone serves orkUI's marks
            got = await page.evaluate("async (u) => { const r = await fetch(u); return [r.status, r.headers.get('content-type'), (await r.arrayBuffer()).byteLength]; }", src)
            assert got[0] == 200 and got[1] == "image/png" and got[2] > 50, (src, got)
        for src in ("elements/meadow.svg", "elements/lava.svg", "signs/check.svg", "signs/after.svg"):                                          # … its elements and its signs too, from the page's own origin
            got = await page.evaluate("async (u) => { const r = await fetch(u); return [r.status, r.headers.get('content-type')]; }", src)
            assert got == [200, "image/svg+xml"], (src, got)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_member_names_stand_under_the_stage_switch_and_their_tasks_run_down_in_rows_by_phase_the_top_one_lit(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".colname").first.wait_for(timeout=WAIT_MS)
        bands = await page.locator(".bands").bounding_box()
        tokens = await page.locator(".colname").first.bounding_box()
        assert 0 <= tokens["y"] - (bands["y"] + bands["height"]) <= 14                                  # the names are the first thing under the stage switch
        column = page.locator('.stack[data-column="backend"]')
        rows = column.locator(".phase")
        assert [await r.get_attribute("data-phase") for r in await rows.all()] == ["now", "next"]         # a row that has nothing is not drawn (no *later* here)
        assert [await r.locator(".phase__lbl").text_content() for r in await rows.all()] == ["now", "next"]          # (drawn in capitals, 10 px, faint)
        assert await page.locator('.stack[data-column="screens"] .phase').evaluate_all("els => els.map((e) => e.dataset.phase)") == ["now", "later"]
        decks = column.locator(".deck")
        ys = [(await d.bounding_box())["y"] for d in await decks.all()]
        assert len(ys) == 3 and abs(ys[0] - ys[1]) <= 8 and ys[2] > max(ys[:2]) and min(ys) > tokens["y"] + tokens["height"]      # running down from the member's name: the two of *now* on a row (the stack of two 8 px lower for its edges), then *next* under them
        assert [await d.get_attribute("data-key") for d in await decks.all()] == ["register|now", "cookie|now", "register|next"]      # one stack a goal, in the Board's order; then the next row
        assert [await d.get_attribute("data-n") for d in await decks.all()] == ["2", "1", "1"]
        first = decks.first
        assert await first.locator(".tcard__name").inner_text() == "Credential table and migration"       # the one at work in front: the one in Review behind it
        assert await first.locator(".deck__n").inner_text() == "×2" and await first.locator(".deck__edge").count() == 1
        assert await decks.nth(1).locator(".deck__n").count() == 0 and await decks.nth(1).locator(".deck__edge").count() == 0
        later = [await r.get_attribute("class") for r in await rows.all()]
        assert "is-now" in later[0] and "is-next" in later[1]                                              # the top row is lit, the rows after it muted
        now_bg, next_bg = [await r.locator(".tcard").first.evaluate("e => getComputedStyle(e).backgroundColor") for r in await rows.all()]
        assert now_bg != next_bg
        done = column.locator(".stack__done")
        assert " ".join((await done.inner_text()).split()) == "2 in dev" and await done.locator(".ork-sign.check").count() == 1
        await column.evaluate("e => { e.scrollTop = e.scrollHeight; }")
        db, cb = await done.bounding_box(), await decks.last.bounding_box()
        assert db["y"] >= cb["y"] + cb["height"] - 1                                                    # *✓ k in dev* at the far end, under the queue
        assert await page.locator('.stack[data-column="screens"] .stack__empty').count() == 0
        assert await page.evaluate(NO_SCROLL)
        await _band(page, "lead")                                                                    # the leader's column: Process now nearest it, then the stops first
        lead = page.locator('.stack[data-column="taskmaster"]')
        first = await lead.locator(".pwr").bounding_box()
        assert first["y"] <= (await lead.locator(".deck").first.bounding_box())["y"]
        assert [await c.get_attribute("data-state") for c in await lead.locator(".deck").all()][:3] == ["stop", "stop", "stop"]


@pytest.mark.asyncio
async def test_a_members_solo_keeps_its_columns_order_two_to_a_row_centred_from_the_top_under_the_stage_switch(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".colname").first.wait_for(timeout=WAIT_MS)
        order = [await c.get_attribute("data-key") for c in await page.locator('.stack[data-column="backend"] .deck').all()]
        await page.locator('button.band__face[data-member="backend"]').click()
        solo = page.locator(".solo")
        await solo.wait_for(timeout=WAIT_MS)
        assert await solo.get_attribute("aria-label") == "Only Backend’s tasks" and await solo.locator(".solo__head .ork-count").inner_text() == "4"      # its tasks: a stack of two, two more
        assert [await c.get_attribute("data-key") for c in await solo.locator(".deck").all()] == order                      # nothing reordered
        assert await page.locator('button.band__face[data-member="backend"]').get_attribute("aria-pressed") == "true" and await page.locator('button.band__face[data-member="screens"]').get_attribute("aria-pressed") == "false"      # the face pressed
        rows = solo.locator(".phase")
        assert [await r.get_attribute("data-phase") for r in await rows.all()] == ["now", "next"]
        assert ["is-wrap" in await r.get_attribute("class") for r in await rows.all()] == [True, True]
        first_row = [await c.bounding_box() for c in await rows.first.locator(".deck").all()]
        assert len(first_row) == 2 and abs(first_row[0]["y"] - first_row[1]["y"]) <= 12 and first_row[0]["x"] < first_row[1]["x"]      # two to a row …
        gap = round(first_row[1]["x"] - (first_row[0]["x"] + 74))
        assert 6 <= gap <= 16                                                                          # … 6 px apart (the stack of two keeps room for its edges)
        mid = (first_row[0]["x"] + first_row[1]["x"] + first_row[1]["width"]) / 2
        assert abs(mid - 195) <= 14                                                                    # … centred
        single = await rows.nth(1).locator(".deck").first.bounding_box()
        assert abs(single["x"] + single["width"] / 2 - 195) <= 14                                      # a lone card is centred
        card = await solo.bounding_box()
        bands = await page.locator(".stagebar").bounding_box()
        assert round(card["y"]) >= round(bands["y"] + bands["height"]) - 1 and first_row[0]["y"] > card["y"]                  # in the field under the stage switch, from the top
        assert "is-now" in await rows.first.get_attribute("class") and "is-next" in await rows.nth(1).get_attribute("class")
        assert "$0.38 a run" in await solo.locator(".solo__card").inner_text() and "Takes:" in await solo.locator(".solo__card").inner_text()
        await page.locator('button.band__face[data-member="backend"]').click()                           # a second tap shows everyone again
        await solo.wait_for(state="detached", timeout=WAIT_MS)
        await page.locator('button.band__face[data-member="screens"]').click()
        await solo.wait_for(timeout=WAIT_MS)
        await solo.get_by_role("button", name="Everyone").click()
        await solo.wait_for(state="detached", timeout=WAIT_MS)
        await _band(page, "lead")                                                                    # the leader's solo lays Planning's goals out the same way: four to a row, centred, 6 px apart (spec 67 §1.2)
        await page.locator('button.band__face[data-member="taskmaster"]').click()
        lead = page.locator(".solo")
        await lead.wait_for(timeout=WAIT_MS)
        cards = [await c.bounding_box() for c in await lead.locator(".deck").all()]
        assert len(cards) == 6 and len({round(b["y"]) for b in cards[:4]}) == 1 and cards[4]["y"] > cards[0]["y"] and round(cards[1]["x"] - (cards[0]["x"] + cards[0]["width"])) == 6
        assert abs((cards[0]["x"] + cards[3]["x"] + cards[3]["width"]) / 2 - 195) <= 1 and await page.evaluate(NO_SCROLL)
