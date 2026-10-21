"""Spec 49 part C, the phone (docs/specs/49-one-window.md §10, §11, "Tests → C"): Chromium at 390 × 844 against the stub of test_pwa_shell_browser.py with
a Board of one goal, *Sign in with a passkey*, as the mockup draws it: a party of a leader, two builders and two checkers, ideas in each stage, a plan, a
question, a proposal and a failure waiting, two results to look at. No tab bar; the top bar's Today and limits sheets; the goal chips and header; the stage
switch; the members' cards and their marks; a member's solo; the stops along the bottom, popped out with their quick answers; `#needs`; 44 px targets."""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _phone, _shot  # noqa: F401

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


def node(slug, title, state, stage, **more):
    return {"slug": slug, "goal": "passkey", "title": title, "short": title, "state": state, "queue": "", "held_until": "", "start_at": "", "priority": "normal", "size": "M",
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
        node("button", "Passkey button on the sign-in page", "done", "done", folded=True, tasks=[task("b1", "The button", "merged", SCREENS)]),
        node("kept", "Where the credentials are kept", "done", "done", folded=True),
    ]
    party = [member(TASKMASTER, "lead", ELDER, "needs", "plan"), member(BACKEND, "build", OWN, "needs", "failed"), member(SCREENS, "build", ELF, "work"),
             member(REVIEWER, "check", ELDER, "work"), member(WORDS, "check", GNOME, "needs", "plan")]
    goal = {"slug": "passkey", "title": "Sign in with a passkey", "short": "Passkey", "priority": "high", "state": "ready", "craft": "engineering", "race": "peon",
            "done_when": ["a person signs in on a phone without a password"], "ideas": 9, "done": 2, "usd": 6.4, "leader": TASKMASTER, "party": party,
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


async def _shot_to(page, name: str) -> None:
    """A screenshot of the window into the folder named by ARENA_SHOTS (a test of the window's look, kept by hand)."""
    if SHOTS:
        Path(SHOTS).mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(Path(SHOTS) / f"{name}.png"))


@pytest.mark.asyncio
async def test_the_window_is_one_screen_with_no_tab_bar(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".ghead").wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(600)
        await _shot_to(page, "board-implementation")
        await page.locator('.band[data-band="lead"]').click()
        await page.wait_for_timeout(300)
        await _shot_to(page, "board-planning")
        await page.locator('.band[data-band="build"]').click()
        await page.locator('.token[data-member="backend"]').click()
        await page.wait_for_timeout(300)
        await _shot_to(page, "member-solo")
        await page.locator('[data-act="everyone"]').click()
        await page.locator('.hc[data-kind="plan"]').click(position={"x": 14, "y": 12})
        await page.wait_for_timeout(600)
        await _shot_to(page, "stop-popped-plan")
        await page.keyboard.press("Escape")
        await page.locator('.hc[data-kind="look"]').first.click(position={"x": 14, "y": 12})
        await page.wait_for_timeout(600)
        await _shot_to(page, "stop-popped-look")
        await page.keyboard.press("Escape")
        await page.locator(".bar-btn.today").click()
        await page.wait_for_timeout(300)
        await _shot_to(page, "sheet-today")
        await page.keyboard.press("Escape")
        await page.locator(".limit-chip").click()
        await page.wait_for_timeout(300)
        await _shot_to(page, "sheet-tools")
