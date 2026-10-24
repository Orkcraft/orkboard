"""Spec 65 part C, the phone (docs/specs/65-ideation.md §8, §9 "C"; decisions §78): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py with an Ideation party beside
the passkey one. New party offers Ideation, whose seats stay (no Change) and whose six agents no other party is offered; New goal in Ideation is one box (*What is the pitch?*) with *Hold* · *Tonight* ·
*Judge now*, no priority, no type; Ideation's field holds its pitches by its three stages (*Pitch*, *Views*, *Decision*), the views' heads lit one by one as each answers, the answer's word, the sent one
naming its goal and *Passed (n)* folded; a pitch's sheet (the pitch, four views one under another, the case against, the decision) with Send to <party>, Change and judge again, Pass, Drop, Try again,
Judge again, Judge now; a party of the library the project lacks opens New party with it; Needs you's `pitch` row opens the pitch's sheet. No horizontal scroll anywhere; `sw.js` v73."""
from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest

from orkboard.gui import pwa
from orkboard.realm import library, pitches
from tests.test_pwa_arena_browser import SCENE, STAMP, _redrawn, _scene, _shot_to, node  # noqa: F401
from tests.test_pwa_shell_browser import FAB, NO_SCROLL, WAIT_MS, Stub, _called, _new_goal, _phone, _pick_goal, _pop

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

LICH = {"craft": "product", "race": "lich", "tier": "warrior"}
INVESTOR = {"slug": "investor", "name": "Investor", "head": {"craft": "product", "race": "lich", "tier": "elder"}}
SKEPTIC = {"slug": "skeptic", "name": "Skeptic", "head": LICH}
VIEWS = [{"slug": "product-view", "name": "Product view", "head": LICH},
         {"slug": "market-view", "name": "Market view", "head": {"craft": "marketing", "race": "gnome", "tier": "warrior"}},
         {"slug": "tech-view", "name": "Engineering view", "head": {"craft": "engineering", "race": "peon", "tier": "warrior"}},
         {"slug": "design-view", "name": "Design view", "head": {"craft": "design", "race": "elf", "tier": "warrior"}}]
STAGES = {"lead": {"word": "Pitch"}, "build": {"word": "Views", "seats": 4}, "check": {"word": "Decision", "seats": 1}}
SHEET_SCROLL = "(d) => d.scrollWidth <= d.clientWidth + 1 && [...d.querySelectorAll('*')].every((e) => e.getBoundingClientRect().right <= 391)"


def decision(answer, where=None, **more):
    """The Investor's decision as `pitch.decision` says it (gui/ideas_pitch.py, realm/pitches.py `_decision`)."""
    return {"answer": answer, "word": pitches.ANSWER_WORDS[answer], "why": ["Two people asked for it this month", "It moves the sign-ins a week"],
            "where": where or {"party": "", "name": "", "preset": False, "type": "", "type_name": ""}, "first": "A dark theme toggle on the settings screen",
            "test": "Ask five people who sign in at night", "kills": [], "like": None, "reshaped": False, **more}


INVEST = decision("invest", {"party": "passkey", "name": "Passkey", "preset": False, "type": "bug", "type_name": "Fix a bug"})


def face(state, answered=0, case=False, d=None, sent=None, passed=None, before=()):
    """A pitch as the faces read it (realm/pitches.py `face`)."""
    views = [{**v, "answered": i < answered, "for": ["People who sign in at night"] if i < answered else [], "against": ["Another setting to keep"] if i < answered else [],
              "question": "Who asked for it?" if i < answered else "", "size": "M" if v["slug"] == "tech-view" and i < answered else ""} for i, v in enumerate(VIEWS)]
    return {"state": state, "views": views, "skeptic": SKEPTIC, "investor": INVESTOR,
            "case": {"case": "Nobody named wants it; it doubles the screens to test.", "kills": [{"id": "costly", "words": pitches.KILLS["costly"]}]} if case else None,
            "decision": d, "sent": sent, "passed": passed, "before": list(before)}


class Lab:
    """Ideation's pitches as the host keeps them: each `{title, state, queue, gist, pitch}`; the commands of spec 65 §11 change them."""

    def __init__(self):
        self.pitches = {
            "dark": {"title": "Dark mode", "state": "judged", "queue": "", "pitch": face("judged", 4, True, INVEST)},
            "widget": {"title": "A home screen widget", "state": "judging", "queue": "", "pitch": face("judging", 2)},
            "emoji": {"title": "Emoji reactions", "state": "judged", "queue": "", "pitch": face("judged", 4, True, decision(
                "reshape", kills=[{"id": "no_who", "words": pitches.KILLS["no_who"]}], reshaped=True))},
            "blog": {"title": "A blog for the app", "state": "judged", "queue": "", "pitch": face("judged", 4, True, decision(
                "invest", {"party": "website", "name": "Website", "preset": True, "type": "", "type_name": ""}))},
            "sounds": {"title": "Sounds on sign-in", "state": "failed", "queue": "", "pitch": face("failed", 3), "error": "Market view did not answer: try again"},
            "night": {"title": "Sign in by voice", "state": "raw", "queue": "hold", "pitch": face("raw")},
            "badge": {"title": "A badge on the icon", "state": "sent", "queue": "", "pitch": face("sent", 4, True, INVEST, sent={
                "party": "passkey", "type": "bug", "goal": "badge-goal", "as_decided": True, "at": STAMP, "name": "Passkey", "title": "Badge on the icon"})},
            "fax": {"title": "Sign in by fax", "state": "passed", "queue": "", "pitch": face("passed", 4, True, decision("pass"), passed={"why": "No one has a fax", "at": STAMP, "as_decided": True})},
        }
        self.made: list[dict] = []                         # parties made from a preset meanwhile

    def answered(self, slug, k):
        p = self.pitches[slug]
        p["pitch"] = face(p["state"], k, k >= 4 and p["pitch"]["case"] is not None)

    def nodes(self):
        out = []
        for slug, p in self.pitches.items():
            answered = sum(v["answered"] for v in p["pitch"]["views"])
            out.append(node(slug, p["title"], p["state"], pitches.stage_of(p["state"], answered), goal="ideation", queue=p["queue"], pitch=copy.deepcopy(p["pitch"]),
                            folded=p["state"] == "passed", needs_you="pitch" if p["state"] == "judged" else "",
                            waits={"kind": "you", "ref": "", "title": "", "until": ""} if p["state"] == "judged" else None))
        return out

    def goal(self):
        party = [{**INVESTOR, "band": "lead", "state": "free", "why": ""}, *({**v, "band": "build", "state": "free", "why": ""} for v in VIEWS),
                 {**SKEPTIC, "band": "check", "state": "free", "why": ""}]
        return {"slug": "ideation", "title": "Ideation", "short": "Ideation", "priority": "normal", "state": "ready", "craft": "product", "race": "lich", "done_when": [],
                "ideas": len(self.pitches), "done": 0, "usd": 0.8, "leader": INVESTOR, "party": party, "brief": "Small pitches: invest, reshape or pass, and why", "flags": 0, "waits_main": 0,
                "today": {"merged": 0, "usd": 0}, "team": [{"slug": m["slug"], "name": m["name"], "head": m["head"], "checks": m["band"] == "check", "every": False} for m in party[1:]],
                "verdict": None, "ideation": True, "passed": sum(p["state"] == "passed" for p in self.pitches.values()), "stages": copy.deepcopy(STAGES), "types": []}

    def needs(self):
        return [{"idea": slug, "goal": "ideation", "title": p["title"], "priority": "low", "blocks": False, "at": STAMP, "kind": "pitch",
                 "text": f"Judged: {p['pitch']['decision']['word']}", "answer": p["pitch"]["decision"]["answer"]}
                for slug, p in self.pitches.items() if p["state"] == "judged"]


LAB: dict = {}


def hosted(monkeypatch):
    """The host of spec 65 A over the arena's scene: the library's presets and stages, the Ideation party and its pitches on the Map, Needs you's `pitch` rows, and the pitch's commands."""
    lab = LAB["lab"] = Lab()
    real = Stub.commands

    def commands(self):
        got = real(self)

        def serve(name, answer):
            """A command of spec 65's own: recorded as the stub records one (no `link`, no `device`)."""
            def call(a):
                a = {k: v for k, v in a.items() if k != "link" and (k != "device" or name == "ideas.log")}
                self.calls.append((name, dict(a)))
                return answer(a)
            return call

        def over(name, answer):
            """A command the stub (or the arena's scene) answers and records, changed after: its words as the listener sends them."""
            return lambda a: answer(a, got[name](a))

        def roles(a, out):
            return {**out, "presets": library.presets(), "stages": library.stages()}

        def the_map(a, m):
            m["goals"] = [*m["goals"], lab.goal(), *copy.deepcopy(lab.made)]
            m["nodes"] = [*m["nodes"], *lab.nodes()]
            return m

        def board(a, b):
            b["tracks"] = [*b["tracks"], Stub.goal("ideation", "Ideation", "normal", "ready")]
            b["needs_you"] = [*b["needs_you"], *lab.needs()]
            b["ideas"] = [{"slug": s, "title": p["title"], "state": p["state"], "state_error": p.get("error", ""), "track": "ideation"} for s, p in lab.pitches.items()]
            return b

        def page(a):
            """A pitch's page (`pitch` on it); any other goal's, the stub's."""
            if a.get("slug") not in lab.pitches:
                return got["ideas.page"](a)
            self.calls.append(("ideas.page", {"slug": a["slug"]}))
            p = lab.pitches[a["slug"]]
            return {"slug": a["slug"], "title": p["title"], "track": "ideation", "state": p["state"], "size": "M", "talk": [], "plan": None, "busy": False, "checks": [], "lens": [],
                    "sections": [{"name": "Gist", "thesis": p["title"], "text": f"{p['title']}: a small idea, in the person's words."}], "state_error": p.get("error", ""),
                    "pitch": copy.deepcopy(p["pitch"])}

        def add(a):
            slug = a["text"].lower().replace(" ", "-")[:20]
            queue = "hold" if a.get("hold") else "night" if a.get("night") else "now"
            lab.pitches[slug] = {"title": a["text"], "state": "raw" if queue != "now" else "judging", "queue": queue, "pitch": face("raw" if queue != "now" else "judging")}
            return self.bump({"slug": slug, "queue": queue, "element": "", "type": "", "joined": None})

        def judge(a):
            p = lab.pitches[a["slug"]]
            p.update(state="judging", queue="", pitch=face("judging"))
            p.pop("error", None)
            return self.bump({"ok": True})

        def send(a):
            p = lab.pitches[a["slug"]]
            name = {"passkey": "Passkey"}.get(a["party"], a["party"])
            p.update(state="sent", pitch={**p["pitch"], "state": "sent", "sent": {"party": a["party"], "type": "bug", "goal": "dark-goal", "as_decided": True, "at": STAMP,
                                                                                    "name": name, "title": "A dark theme toggle"}})
            return self.bump({"slug": "dark-goal", "party": a["party"], "type": "bug", "queue": "now"})

        def again(a):
            p = lab.pitches[a["slug"]]
            p.update(state="judging", pitch={**face("judging"), "before": [p["pitch"]["decision"]]})
            if a.get("text"):
                p["title"] = a["text"].split("\n")[0]
            return self.bump({"ok": True})

        def pass_(a):
            p = lab.pitches[a["slug"]]
            p.update(state="passed", pitch={**p["pitch"], "state": "passed", "passed": {"why": a.get("why", ""), "at": STAMP, "as_decided": False}})
            return self.bump({"ok": True, "dropped": []})

        def drop(a):
            lab.pitches.pop(a["slug"], None)
            return self.bump({"ok": True})

        def price(a, out):
            if a.get("leader") == "investor":
                return {"low": 0.29, "high": 0.58, "learned": False, "ideas": 0, "checks": [], "pitch": True, "hints": [], "types": []}
            return out

        def goal_save(a, out):
            if a.get("preset") == "website":
                lab.made.append({**lab.goal(), "slug": out["slug"], "title": "Website", "short": "Website", "ideation": False, "passed": 0, "ideas": 0, "stages": None,
                                 "leader": Stub.LEADER, "party": [{**Stub.LEADER, "band": "lead", "state": "free", "why": ""}], "team": []})
            return out

        return {**got, "ideas.roles": over("ideas.roles", roles), "ideas.map": over("ideas.map", the_map), "ideas.board": over("ideas.board", board), "ideas.page": page,
                "ideas.add": serve("ideas.add", add), "ideas.judge": serve("ideas.judge", judge),
                "ideas.pitch_send": serve("ideas.pitch_send", send), "ideas.pitch_again": serve("ideas.pitch_again", again), "ideas.pitch_pass": serve("ideas.pitch_pass", pass_),
                "ideas.drop": serve("ideas.drop", drop), "ideas.party_price": over("ideas.party_price", price), "ideas.goal_save": over("ideas.goal_save", goal_save)}
    monkeypatch.setattr(Stub, "commands", commands)
    return lab


def _strip(calls, name):
    return [c[1] for c in calls if c[0] == name]


async def _ideation(page):
    """Ideation shown: picked in the parties' sheet; its field drawn."""
    await _pick_goal(page, "ideation")
    await page.locator(".pitchfield").wait_for(timeout=WAIT_MS)


async def _open(page, slug):
    """A pitch's sheet, from its row on Ideation's field."""
    row = page.locator(f'.pitchrow[data-idea="{slug}"]')
    if not await row.is_visible():
        await page.locator(".pitch-passed > summary").click()
    await row.click()
    sheet = page.locator("dialog.pitch-sheet[open]")
    await sheet.locator(".pitchview").first.wait_for(timeout=WAIT_MS)
    return sheet


@pytest.mark.asyncio
async def test_new_party_offers_ideation_whose_seats_stay_and_whose_agents_no_other_party_is_offered(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New party")
        await sheet.locator('.preset-tile[data-preset="ideation"]').click()
        assert await sheet.locator(".party-line").first.inner_text() == \
            "Leads: Investor · Builds: Product view, Market view, Engineering view, Design view · Checks: Skeptic"
        assert await sheet.locator('.party [data-change="team"]').count() == 0 and await sheet.locator('.party-checks [data-change="checks"]').count() == 0
        assert "its views and the skeptic stay" in await sheet.locator('.party [data-sec="ideation"]').inner_text()
        await sheet.locator(".party-price").filter(has_text="a pitch").wait_for(timeout=WAIT_MS)
        assert await sheet.locator(".party-takes").count() == 0                                    # a pitch has no goal type
        assert "Skeptic makes the case against every pitch; Investor decides." in await sheet.locator(".party-checks").inner_text()
        await _shot_to(page, "ideation-new-party")
        assert await page.evaluate(NO_SCROLL)
        await sheet.get_by_label("What it is for").fill("Small ideas for the app.")
        await sheet.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save", {"about": "Small ideas for the app.", "craft": "product", "leader": "investor", "priority": "normal", "preset": "ideation",
                                                       "team": ["product-view", "market-view", "tech-view", "design-view", "skeptic"], "every": []})


@pytest.mark.asyncio
async def test_no_other_party_is_offered_the_pitch_agents(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New party")
        await sheet.locator('.preset-tile[data-preset="game"]').click()
        await sheet.locator('.party [data-change="team"]').click()
        for band in ("Leads", "Builds", "Checks"):
            fold = sheet.get_by_role("region", name=band)
            if await fold.get_attribute("class") and "is-open" not in await fold.get_attribute("class"):
                await fold.locator(".fold-head").click()
            await fold.locator(".team-row").first.wait_for(timeout=WAIT_MS)
            listed = [await r.get_attribute("data-agent") for r in await fold.locator(".team-row").all()]
            assert listed and not {"investor", "product-view", "market-view", "tech-view", "design-view", "skeptic"} & set(listed), (band, listed)


@pytest.mark.asyncio
async def test_new_goal_in_ideation_is_one_box_held_kept_for_tonight_or_judged_now(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ideation(page)
        await page.locator(FAB).click()
        form = page.locator("dialog.newgoal[open]")
        await form.wait_for(timeout=WAIT_MS)
        assert "is-pitch" in await form.get_attribute("class")
        box = form.get_by_label("What is the pitch?")
        await box.wait_for(timeout=WAIT_MS)
        assert await box.get_attribute("maxlength") == "2000"
        assert not await form.locator(".newgoal__type").is_visible() and not await form.get_by_role("radiogroup", name="Priority").is_visible()
        assert not await form.get_by_role("button", name="Add the goal").is_visible() and not await form.get_by_role("button", name="Put it back").is_visible()
        for name in ("Hold", "Tonight", "Judge now"):
            assert await form.get_by_role("button", name=name, exact=True).is_disabled()
        await box.fill("Share a goal by link")
        await _shot_to(page, "ideation-new-goal")
        assert await page.evaluate(NO_SCROLL)
        await form.get_by_role("button", name="Hold", exact=True).click()
        assert await _called(stub, "ideas.add", {"text": "Share a goal by link", "track": "ideation", "hold": True})
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        await page.locator('.pitchrow[data-idea="share-a-goal-by-link"]').filter(has_text="held: Judge now").wait_for(timeout=WAIT_MS)
        await page.locator(FAB).click()
        await form.wait_for(timeout=WAIT_MS)
        await form.get_by_label("What is the pitch?").fill("Pin a party")
        await form.get_by_role("button", name="Judge now").click()
        assert await _called(stub, "ideas.add", {"text": "Pin a party", "track": "ideation"})
        await page.locator(FAB).click()
        await form.wait_for(timeout=WAIT_MS)
        await form.get_by_label("What is the pitch?").fill("Undo a merge")
        await form.get_by_role("button", name="Tonight").click()
        assert await _called(stub, "ideas.add", {"text": "Undo a merge", "track": "ideation", "night": True})


@pytest.mark.asyncio
async def test_new_goal_in_another_party_keeps_its_type_and_priority(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(FAB).click()
        form = page.locator("dialog.newgoal[open]")
        await form.wait_for(timeout=WAIT_MS)
        assert "is-pitch" not in await form.get_attribute("class")
        assert await form.get_by_role("button", name="Add the goal").is_visible() and not await form.get_by_role("button", name="Judge now").is_visible()
        assert await form.get_by_role("radiogroup", name="Priority").is_visible() and await form.locator('textarea[aria-label="The goal"]').count() == 1


@pytest.mark.asyncio
async def test_ideation_s_field_holds_its_pitches_by_its_three_stages_the_views_lit_one_by_one(fake_repo, monkeypatch):
    lab = hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ideation(page)
        sections = page.locator(".pitchsec")
        assert [await s.get_attribute("aria-label") for s in await sections.all()] == ["Pitch", "Views", "Decision"]
        assert await page.locator('.pitchsec[data-stage="implementation"] .pitchsec__heads img').count() == 4
        widget = page.locator('.pitchrow[data-idea="widget"]')
        assert await widget.locator(".pitchrow__view").count() == 4
        assert await widget.locator(".pitchrow__view.is-lit").count() == 2 and "2 of 4 views" in await widget.inner_text()
        lab.answered("widget", 3)
        await _redrawn(stub, page)
        assert await widget.locator(".pitchrow__view.is-lit").count() == 3
        assert await widget.locator('.pitchrow__view.is-lit[data-view="tech-view"]').count() == 1 and await widget.locator('.pitchrow__view:not(.is-lit)[data-view="design-view"]').count() == 1
        decision_ = page.locator('.pitchsec[data-stage="checking"]')
        assert await decision_.locator('.pitchrow[data-idea="dark"] .pitchrow__answer').inner_text() in ("Invest", "INVEST")
        assert (await decision_.locator('.pitchrow[data-idea="emoji"] .pitchrow__answer').get_attribute("data-answer")) == "reshape"
        assert "sent to Passkey: Badge on the icon" in await decision_.locator('.pitchrow[data-idea="badge"]').inner_text()
        assert "held: Judge now" in await page.locator('.pitchsec[data-stage="planning"] .pitchrow[data-idea="night"]').inner_text()
        assert "Market view did not answer" in await page.locator('.pitchrow[data-idea="sounds"]').inner_text()
        fold = page.locator(".pitch-passed")
        assert (await fold.locator("summary").inner_text()).lower() == "passed (1)" and await fold.get_attribute("open") is None
        assert not await page.locator('.pitchrow[data-idea="fax"]').is_visible()
        await fold.locator("summary").click()
        assert "passed: No one has a fax" in await page.locator('.pitchrow[data-idea="fax"]').inner_text()
        assert "8 pitches · 1 passed" in await page.locator(".gbar__head").inner_text()
        for row in await page.locator(".pitchrow").all():
            assert (await row.bounding_box())["height"] >= 44
        await _shot_to(page, "ideation-field")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_pitch_s_sheet_reads_the_views_the_case_and_the_decision_and_sends_it_to_the_party_named(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ideation(page)
        sheet = await _open(page, "dark")
        assert await sheet.get_attribute("aria-label") == "Dark mode"
        assert "a small idea, in the person's words" in await sheet.locator('[data-sec="The pitch"]').inner_text()
        views = sheet.locator(".pitchview")
        assert [await v.get_attribute("data-view") for v in await views.all()] == ["product-view", "market-view", "tech-view", "design-view"]
        xs = {round((await v.bounding_box())["x"]) for v in await views.all()}
        assert len(xs) == 1                                                                         # one under another
        tech = sheet.locator('.pitchview[data-view="tech-view"]')
        said = await tech.inner_text()
        assert "People who sign in at night" in said and "Another setting to keep" in said and "Who asked for it?" in said and "Size M" in said
        assert await tech.locator(".ork-race__head").count() == 1
        case = sheet.locator('[data-sec="The case against"]')
        assert "Nobody named wants it" in await case.inner_text() and pitches.KILLS["costly"] in await case.inner_text()
        dec = sheet.locator('[data-sec="Decision"]')
        assert (await dec.locator(".pitch__answer").inner_text()).strip().lower() == "invest"
        text = await dec.inner_text()
        for words in ("Two people asked for it this month", "Where: Passkey, as Fix a bug", "First step: A dark theme toggle", "Cheapest test: Ask five people"):
            assert words in text, words
        await _shot_to(page, "ideation-pitch-sheet")
        assert await sheet.evaluate(SHEET_SCROLL)
        pick = sheet.get_by_label("The party to send it to")
        assert await pick.input_value() == "passkey"
        assert [o.strip() for o in await pick.locator("option").all_inner_texts()] == ["Passkey · as decided"]          # no Ideation, no General
        await sheet.get_by_role("button", name="Send to Passkey").click()
        assert await _called(stub, "ideas.pitch_send", {"slug": "dark", "party": "passkey"})
        await sheet.locator('.pitch__state[data-state="sent"]').wait_for(timeout=WAIT_MS)
        assert "To Passkey" in await sheet.locator('[data-sec="Sent"]').inner_text()
        assert await sheet.get_by_role("button", name="Open the goal").is_visible()


@pytest.mark.asyncio
async def test_a_reshape_is_changed_and_judged_again_and_a_pass_folds_it_under_passed(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ideation(page)
        sheet = await _open(page, "emoji")
        dec = sheet.locator('[data-sec="Decision"]')
        assert (await dec.locator(".pitch__answer").inner_text()).strip().lower() == "reshape"
        assert pitches.KILLS["no_who"] in await dec.inner_text() and "made the invest a reshape" in await dec.inner_text()
        await sheet.get_by_role("button", name="Change and judge again").click()
        box = sheet.get_by_label("The pitch, changed")
        assert "a small idea" in await box.input_value()
        await box.fill("Emoji reactions for the people who review")
        await sheet.get_by_role("button", name="Judge again").click()
        assert await _called(stub, "ideas.pitch_again", {"slug": "emoji", "text": "Emoji reactions for the people who review"})
        await sheet.locator('.pitch__state[data-state="judging"]').wait_for(timeout=WAIT_MS)
        assert "Before: Reshape" in await sheet.locator('[data-sec="Decision"]').inner_text()
        await page.keyboard.press("Escape")
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        sheet = await _open(page, "dark")
        await sheet.get_by_role("button", name="Pass", exact=True).click()
        await sheet.get_by_label("Why you pass (optional)").fill("Not this season")
        await sheet.locator('.pitch__acts [data-act="pass-it"]').click()
        assert await _called(stub, "ideas.pitch_pass", {"slug": "dark", "why": "Not this season"})
        await page.keyboard.press("Escape")
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        await page.locator(".pitch-passed > summary").filter(has_text=re.compile("Passed \\(2\\)", re.I)).wait_for(timeout=WAIT_MS)
        assert await page.locator('.pitch-passed .pitchrow[data-idea="dark"]').count() == 1
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_try_again_judge_again_judge_now_and_drop(fake_repo, monkeypatch):
    lab = hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ideation(page)
        sheet = await _open(page, "sounds")
        assert "Market view did not answer" in await sheet.locator(".pitch__state").inner_text()
        await sheet.get_by_role("button", name="Try again").click()
        assert await _called(stub, "ideas.judge", {"slug": "sounds"})
        await page.keyboard.press("Escape")
        sheet = await _open(page, "fax")
        assert "No one has a fax" in await sheet.locator('[data-sec="Passed"]').inner_text()
        await sheet.get_by_role("button", name="Judge again").click()
        assert await _called(stub, "ideas.pitch_again", {"slug": "fax"})
        await page.keyboard.press("Escape")
        sheet = await _open(page, "night")
        await sheet.get_by_role("button", name="Judge now").click()
        assert await _called(stub, "ideas.judge", {"slug": "night"})
        await page.keyboard.press("Escape")
        sheet = await _open(page, "blog")
        await sheet.get_by_role("button", name="Drop", exact=True).click()
        assert "Pass keeps it" in await sheet.locator(".pitch__ask").inner_text()
        await sheet.get_by_role("button", name="Drop it").click()
        assert await _called(stub, "ideas.drop", {"slug": "blog"})
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        assert "blog" not in lab.pitches


@pytest.mark.asyncio
async def test_a_party_of_the_library_the_project_lacks_opens_new_party_with_it_then_the_pitch_again(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ideation(page)
        sheet = await _open(page, "blog")
        pick = sheet.get_by_label("The party to send it to")
        assert await pick.input_value() == "website"
        assert "Website (a new party) · as decided" in await pick.locator("option:checked").inner_text()
        await sheet.get_by_role("button", name="Send to Website").click()
        party = page.get_by_role("dialog", name="New party")
        await party.wait_for(timeout=WAIT_MS)
        assert await party.locator('.preset-tile[data-preset="website"]').get_attribute("aria-pressed") == "true"
        assert not _strip(stub.calls, "ideas.pitch_send")
        await party.get_by_label("What it is for").fill("The app's website.")
        await party.get_by_role("button", name="Save party").click()
        assert await _called(stub, "ideas.goal_save")
        assert _strip(stub.calls, "ideas.goal_save")[-1]["preset"] == "website"
        again = page.locator("dialog.pitch-sheet[open]")
        await again.wait_for(timeout=WAIT_MS)
        assert await again.get_attribute("aria-label") == "A blog for the app"


@pytest.mark.asyncio
async def test_needs_you_s_pitch_row_opens_the_pitch_s_sheet(fake_repo, monkeypatch):
    hosted(monkeypatch)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _pop(page, "Judged: Dark mode")
        assert "Judged: Invest" in await raised.inner_text()
        await raised.get_by_role("button", name="Open the pitch").click()
        sheet = page.locator("dialog.pitch-sheet[open]")
        await sheet.locator(".pitchview").first.wait_for(timeout=WAIT_MS)
        assert await sheet.get_attribute("aria-label") == "Dark mode"
        await sheet.locator(".pitch__more").scroll_into_view_if_needed()
        await _shot_to(page, "ideation-pitch-sheet-end")
        assert await sheet.evaluate(SHEET_SCROLL)


def test_the_service_worker_is_one_version_up_and_caches_the_pitch_s_module():
    sw = (Path(pwa.__file__).parent / "static" / "pwa" / "sw.js").read_text(encoding="utf-8")
    assert 'const CACHE = "orkcraft-app-v76";' in sw and '"shell-pitch.js"' in sw[sw.index("const SHELL"):sw.index("];", sw.index("const SHELL"))]
