"""Spec 68 part C, the phone: a goal's route (docs/specs/68-release-and-route.md §2, §7.1, §7.2, §7.8, §8 "C"): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py (the Passkey party)
with an Ideation party, a Website party and a Release party beside it (its leader the Release manager, a skeleton). A goal sent from Ideation shows its route under its title, each step a 44 px button that opens what it
names (the pitch's sheet, the party with the goal picked into the filter, the release goal's screen), the line wrapping at 390 with no sideways scroll; a goal with only its party step shows none; a sent pitch's sheet
and Ideation's list say its goal (*At work in Passkey · 3 of 7*, *In main*, *In Release 1.4*, *Out in 1.4*, *Dropped*); the skeleton's head is drawn from the host's `race`; an older host (no `route`, `goal_state`, `race`)
draws as before; the service worker's version. The Release party's goals, flags and forms are tests/test_pwa_release_browser.py's."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from orkboard.gui import pwa
from orkboard.realm import library
from tests.test_pwa_arena_browser import ELEMENT, FLAG, OWN, SCENE, STAMP, _redrawn, _scene, _shot_to, member, node  # noqa: F401
from tests.test_pwa_ideation_browser import INVEST, Lab, face
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _phone, _pick_goal

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

SKELETON = {"craft": "product", "race": "skeleton", "tier": "warrior"}
RELEASE_MANAGER = {"slug": "release-manager", "name": "Release manager", "head": SKELETON}
RELEASE_TYPE = {"id": "release", "name": "A release", "sign": "release", "line": "A version out: what is new, the build, the stores' list", "lens": "text", "refs": False, "used": 0, "missing": [],
                "asks": [{"id": "version", "label": "Version", "hint": "1.4"}, {"id": "new", "label": "What is new", "hint": "in the person's words"}]}
OUT = "2026-10-26T12:00:00"
IN_14 = {"goal": "r14", "party": "release", "version": "1.4", "out": ""}
OUT_13 = {"goal": "r13", "party": "release", "version": "1.3", "out": "2026-10-10T10:00:00"}

PITCH_STEP = {"step": "pitch", "party": "ideation", "goal": "dark", "at": "2026-10-22T09:00:00", "answer": "invest", "word": "Invest", "title": "Dark mode"}
MOVED_STEP = {"step": "moved", "party": "website", "from": "website", "to": "passkey", "goal": "register", "at": "2026-10-23T09:00:00"}
PARTY_STEP = {"step": "party", "party": "passkey", "goal": "register", "at": "2026-10-23T09:00:00", "state": "working", "done": 3, "total": 7}
MAIN_STEP = {"step": "main", "party": "passkey", "goal": "register", "at": "2026-10-24T09:00:00", "by": "gate"}
RELEASE_STEP = {"step": "release", "goal": "r14", "party": "release", "version": "1.4", "out": "", "at": "2026-10-24T10:00:00"}
FULL_ROUTE = [PITCH_STEP, MOVED_STEP, PARTY_STEP, MAIN_STEP, RELEASE_STEP]

WORLD: dict = {}


def a_party(slug, title, leader, members, **more):
    """A party of the Map as the scene's Passkey party is, with another leader and members (`members`: [(agent dict, band, head)])."""
    g = copy.deepcopy(SCENE["map"]["goals"][0])
    party = [member(m, band, head) for m, band, head in members]
    g.update(slug=slug, title=title, short=title, leader={"slug": members[0][0]["slug"], "name": members[0][0]["name"], "head": members[0][2]}, party=party,
             team=[{"slug": m["slug"], "name": m["name"], "head": head, "checks": band == "check", "every": False} for m, band, head in members[1:]],
             ideas=0, done=0, flags=0, waits_main=0, usd=None, **more)
    return g


def world(monkeypatch, release=True):
    """The Passkey scene with Ideation (one pitch sent to Passkey), Website and, with `release`, the Release party: its goals r14 (in main, to go out) and r13 (out), the Passkey flags in a release or waiting."""
    goals = SCENE["map"]["goals"]
    lab = Lab()
    ideation = {**lab.goal(), "ideas": 1, "passed": 0}
    goals.extend([ideation, a_party("website", "Website", {"slug": "web-lead", "name": "Web lead"}, [({"slug": "web-lead", "name": "Web lead"}, "lead", OWN)], types=[])])
    SCENE["map"]["nodes"].append(node("dark", "Dark mode", "sent", "checking", goal="ideation", element="meadow", folded=False, queue="",
                                      pitch=face("sent", 4, True, INVEST, sent={"party": "passkey", "type": "bug", "goal": "register", "as_decided": True, "at": STAMP, "name": "Passkey",
                                                                                 "title": "WebAuthn register"}),
                                      goal_state={"goal": "register", "party": "passkey", "state": "working", "done": 3, "total": 7, "flag": "", "release": None}))
    for n in SCENE["map"]["nodes"]:
        n.setdefault("route", [])
        if n["slug"] == "register":
            n["route"] = copy.deepcopy(FULL_ROUTE)
        if n["slug"] == "button":
            n["flag"] = {**FLAG, "release": IN_14}
        if n["slug"] == "kept":
            n["flag"] = {**FLAG, "at": "2026-10-10T09:00:00", "release": OUT_13}
    SCENE["map"]["nodes"].append(node("badge", "A badge on the icon", "done", "done", element="ice", folded=True, flag={**FLAG, "at": "2026-10-20T09:00:00", "release": None}, route=[]))
    if release:
        rel = a_party("release", "Release", RELEASE_MANAGER, [(RELEASE_MANAGER, "lead", SKELETON), ({"slug": "release-engineer", "name": "Release engineer"}, "build", OWN),
                                                               ({"slug": "release-checker", "name": "Release checker"}, "check", SKELETON)],
                      types=[RELEASE_TYPE], releases_from=[], wait_release=2)
        rel["ideas"], rel["done"] = 2, 2
        goals.append(rel)
        SCENE["map"]["nodes"].extend([
            node("r14", "Release 1.4", "done", "done", goal="release", element="meadow", folded=True, flag={**FLAG, "at": "2026-10-24T11:00:00", "release": None}, route=[],
                 type={"id": "release", "name": "A release", "sign": "release"}, release={"version": "1.4", "goals": ["button", "kept"], "out": ""}),
            node("r13", "Release 1.3", "done", "done", goal="release", element="dust", folded=True, flag={**FLAG, "at": "2026-10-10T10:00:00", "release": None}, route=[],
                 type={"id": "release", "name": "A release", "sign": "release"}, release={"version": "1.3", "goals": ["kept"], "out": "2026-10-10T10:00:00"})])
    WORLD.clear()
    WORLD.update(lab=lab, since={"version": "1.3", "out": "2026-10-10T10:00:00"}, candidates=[], refuse="")
    real = Stub.commands

    def commands(self):
        got = real(self)

        def serve(name, answer):
            def call(a):
                a = {k: v for k, v in a.items() if k != "link" and (k != "device" or name == "ideas.log")}
                self.calls.append((name, dict(a)))
                return answer(a)
            return call

        def over(name, answer):
            return lambda a: answer(a, got[name](a))

        def roles(a, out):
            return {**out, "presets": library.presets(), "stages": library.stages()}

        def board(a, b):
            b["tracks"] = [*b["tracks"], *(Stub.goal(g["slug"], g["title"], "normal", "ready") for g in goals if g["slug"] != "passkey")]
            return b

        def page(a):
            """Any goal of the Map (a pitch has its `pitch`, with its goal's state), with its route."""
            n = next(x for x in SCENE["map"]["nodes"] if x["slug"] == a["slug"])
            self.calls.append(("ideas.page", {"slug": a["slug"]}))
            out = {"slug": n["slug"], "title": n["title"], "track": n["goal"], "state": n["state"], "size": "M", "talk": [], "plan": None, "busy": False, "checks": [], "lens": [],
                   "sections": [{"name": "Gist", "thesis": n["title"], "text": f"{n['title']}: in the person's words."}], "state_error": "", "route": copy.deepcopy(n.get("route") or [])}
            if n.get("pitch"):
                out["pitch"] = {**copy.deepcopy(n["pitch"]), "goal_state": copy.deepcopy(n.get("goal_state"))}
            return out

        def out(a):
            if WORLD["refuse"]:
                return {"error": WORLD["refuse"]}
            n = next(x for x in SCENE["map"]["nodes"] if x["slug"] == a["slug"])
            n["release"] = {**n["release"], "out": OUT}
            return self.bump({"ok": True, "out": OUT})

        return {**got, "ideas.roles": over("ideas.roles", roles), "ideas.board": over("ideas.board", board), "ideas.page": page,
                "ideas.release_candidates": serve("ideas.release_candidates", lambda a: {"since": WORLD["since"], "releases_from": [], "candidates": copy.deepcopy(WORLD["candidates"])}),
                "ideas.release_out": serve("ideas.release_out", out), "ideas.shown": serve("ideas.shown", lambda a: {"ok": True})}
    monkeypatch.setattr(Stub, "commands", commands)
    return WORLD


def norm(s):
    return " ".join(s.split())


async def _goal_screen(page, slug="register"):
    """A goal's own screen, opened with the › of its row in the Goals sheet."""
    await page.locator(".gbar__head").click()
    sheet = page.get_by_role("dialog", name="Goals")
    await sheet.locator(f'.dk[data-idea="{slug}"] .dk__open').click()
    screen = page.locator("section.screen:not([hidden])")
    await screen.locator(".screen-body > *").first.wait_for(timeout=WAIT_MS)
    return screen


SCREEN_FITS = "(e) => e.scrollWidth <= e.clientWidth + 1 && [...e.querySelectorAll('*')].every((x) => x.getBoundingClientRect().right <= 391)"


@pytest.mark.asyncio
async def test_a_goal_sent_from_ideation_shows_its_route_under_its_title_wrapping_with_no_sideways_scroll(fake_repo, monkeypatch):
    world(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        screen = await _goal_screen(page)
        route = screen.locator("nav.route")
        await route.wait_for(timeout=WAIT_MS)
        steps = route.locator(".route__step")
        assert [norm(await s.inner_text()) for s in await steps.all()] == [
            "From Ideation: Invest, 22 Oct", "Moved from Website", "At work in Passkey · 3 of 7", "In main", "In Release 1.4"]
        assert [await s.get_attribute("data-step") for s in await steps.all()] == ["pitch", "moved", "party", "main", "release"]
        assert min([(await s.bounding_box())["height"] for s in await steps.all()]) >= 44                     # 44 px buttons
        assert await route.locator(".route__sep.ork-chev").count() == 4                                       # joined by orkUI's ›, no Unicode sign
        assert "›" not in await route.inner_text()
        assert await route.locator(".ork-race__head").count() == 5                                            # the party's leader's head leads each step
        tops = {round((await s.bounding_box())["y"]) for s in await steps.all()}                              # (a set of the rows the steps lie on)
        assert len(tops) >= 2                                                                                 # it wraps at 390
        title = await screen.locator(".screen-title").bounding_box()
        first = await route.bounding_box()
        assert first["y"] >= title["y"] + title["height"] - 1                                                 # under the title
        assert await screen.locator(".screen-body").evaluate(SCREEN_FITS) and await page.evaluate(NO_SCROLL)
        await _shot_to(page, "phone-route")


@pytest.mark.asyncio
async def test_each_step_opens_what_it_names(fake_repo, monkeypatch):
    world(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        screen = await _goal_screen(page)
        await screen.locator('.route__step[data-step="pitch"]').click()                                       # the pitch's sheet
        sheet = page.locator("dialog.pitch-sheet[open]")
        await sheet.locator(".pitchview").first.wait_for(timeout=WAIT_MS)
        assert await sheet.get_attribute("aria-label") == "Dark mode"
        await page.keyboard.press("Escape")
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        await screen.locator('.route__step[data-step="release"]').click()                                    # the release goal's own screen
        await page.locator(".screen-title", has_text="Release 1.4").wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.page", {"slug": "r14"})
        await page.locator(".screen .back").click()
        await page.locator("section.screen:not([hidden])").wait_for(state="detached", timeout=WAIT_MS)
        screen = await _goal_screen(page)
        await screen.locator('.route__step[data-step="party"]').click()                                       # that party, the goal picked into the filter
        await page.locator("section.screen:not([hidden])").wait_for(state="detached", timeout=WAIT_MS)
        bar = page.locator(".gbar.is-on")
        await bar.wait_for(timeout=WAIT_MS)
        assert "Passkey" in await bar.inner_text() and "1 of" in await bar.locator(".gbar__words").inner_text()
        assert await bar.locator(".ork-elem").count() == 1
        await page.locator(".gbar__all").click()
        await page.locator(".gbar.is-on").wait_for(state="detached", timeout=WAIT_MS)
        screen = await _goal_screen(page)                                                                     # moved: the party it came from, shown whole
        await screen.locator('.route__step[data-step="moved"]').click()
        await page.locator(f'.partydeck[data-goal="website"]').wait_for(timeout=WAIT_MS)
        assert await page.locator(".gbar.is-on").count() == 0
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_goal_with_only_its_party_step_has_no_route_and_an_older_host_draws_as_before(fake_repo, monkeypatch):
    world(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        screen = await _goal_screen(page, "cookie")
        assert await screen.locator("nav.route").count() == 0
        await page.locator(".screen .back").click()
        await page.locator("section.screen:not([hidden])").wait_for(state="detached", timeout=WAIT_MS)
        SCENE["map"]["nodes"] = [{k: v for k, v in n.items() if k not in ("route", "goal_state", "release")} for n in SCENE["map"]["nodes"]]
        stub.bump({})
        screen = await _goal_screen(page, "register")
        assert await screen.locator("nav.route").count() == 0 and await screen.locator(".muted").count() >= 1


@pytest.mark.asyncio
async def test_the_skeletons_head_is_drawn_from_the_hosts_race(fake_repo, monkeypatch):
    world(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        screen = await _goal_screen(page)
        step = screen.locator('.route__step[data-step="release"] img.ork-race__head')
        src = await step.get_attribute("src")
        assert src == "races/skeleton-warrior.png"
        assert await step.evaluate("(i) => i.complete && i.naturalWidth > 0")                                 # the file is served: orkUI's 0.5.0 copy
        assert "Seasoned skeleton" in await step.get_attribute("title")                                       # its words: the race in today's word
        await page.keyboard.press("Escape")


@pytest.mark.asyncio
async def test_a_sent_pitch_says_its_goal_on_its_sheet_and_in_ideations_list(fake_repo, monkeypatch):
    world(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _pick_goal(page, "ideation")
        row = page.locator('.pitchrow[data-idea="dark"]')
        await row.wait_for(timeout=WAIT_MS)
        for state, release, flag, words in [
            ("working", None, "", "At work in Passkey · 3 of 7"), ("planned", None, "", "In Passkey"), ("done", None, "2026-10-24T09:00:00", "In main"), ("done", IN_14, "2026-10-24T09:00:00", "In Release 1.4"),
            ("done", {**IN_14, "out": OUT}, "2026-10-24T09:00:00", "Out in 1.4"), ("dropped", None, "", "Dropped")]:
            gs = {"goal": "register", "party": "passkey" if state != "dropped" else "", "state": state, "done": 3 if state == "working" else 7, "total": 7 if state == "working" else 7,
                  "flag": flag, "release": release}
            if state == "dropped":
                gs.update(done=0, total=0)
            next(n for n in SCENE["map"]["nodes"] if n["slug"] == "dark")["goal_state"] = gs
            await _redrawn(stub, page)
            assert await row.locator(".pitchrow__line").inner_text() == words
            await row.click()
            sheet = page.locator("dialog.pitch-sheet[open]")
            await sheet.locator(".pitchview").first.wait_for(timeout=WAIT_MS)
            goal = sheet.locator('[data-sec="Decision"] .pitch__goal')
            assert norm(await goal.inner_text()) == f"Its goal {words}"
            assert (await goal.bounding_box())["height"] >= 44 and await sheet.evaluate("(d) => d.scrollWidth <= d.clientWidth + 1")
            if state == "working":
                await goal.click()                                                                            # a press opens the goal
                await page.locator(".screen-title", has_text="WebAuthn register").wait_for(timeout=WAIT_MS)
                await page.locator(".screen .back").click()
                await page.locator("section.screen:not([hidden])").wait_for(state="detached", timeout=WAIT_MS)
            else:
                assert await goal.is_disabled() == (state == "dropped")
                await page.keyboard.press("Escape")
            await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


def test_the_service_worker_is_one_version_up_and_caches_the_route_s_module():
    sw = (Path(pwa.__file__).parent / "static" / "pwa" / "sw.js").read_text(encoding="utf-8")
    shell = sw[sw.index("const SHELL"):sw.index("];", sw.index("const SHELL"))]
    assert 'const CACHE = "orkcraft-app-v76";' in sw and '"shell-route.js"' in shell and '"shell-release.js"' in shell
