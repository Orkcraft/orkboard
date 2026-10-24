"""Spec 65 B on the desktop (docs/specs/65-ideation.md §8, §9 → B), in a real browser at 1 440 × 900 against the one window's stub host with an Ideation
party: New party offers Ideation and no seat change in it (the pitch agents never offered to another party); New goal in Ideation is one box, its lens,
Judge now · Tonight · Hold; its line on the field and in the left column (judging with the views' heads lit one by one, judged with the answer's word, sent
naming its goal, Passed (n) folded; Pitch, Views, Decision); a pitch's screen (the four views, the case against, the decision) with Send to <party>,
Change and judge again, Pass and Drop; Needs you's pitch opens it. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import copy
import os

import pytest

pytest.importorskip("playwright.sync_api")

from orkboard.realm import library, roles  # noqa: E402
from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import SHOTS, StubHost, _calls, _new_party, _open, _show_goal, _stop  # noqa: E402

pytestmark = pytest.mark.browser

PARTY = "ideas"
VIEWS = ["product-view", "market-view", "tech-view", "design-view"]
TEAM = [*VIEWS, "skeptic"]


def head(slug):
    a = library.get(slug)
    return {"craft": a.craft, "race": roles.RACES[a.craft], "tier": a.tier}


def who(slug):
    return {"slug": slug, "name": library.get(slug).name, "head": head(slug)}


VIEW_SAYS = {"product-view": (["People who keep notes on two devices"], ["Nobody asked for it yet"], "Who loses notes today?", ""),
             "market-view": (["A line for the store page"], ["Every notes app has it"], "Would anyone pay for it?", ""),
             "tech-view": (["The sync queue is there"], ["Conflicts on two devices"], "Which device wins a conflict?", "M"),
             "design-view": (["One switch in Settings"], ["A conflict screen is a new screen"], "Where does a conflict show?", "")}
INVEST = {"answer": "invest", "word": "Invest", "why": ["Two-device users lose notes today", "The sync queue makes it small"],
          "where": {"party": "ship-sync", "name": "Ship sync", "preset": False, "type": "feature", "type_name": "New feature"},
          "first": "Sync notes offline and settle conflicts by the newest edit", "test": "Ask five two-device users whether they lost a note this month",
          "kills": [], "like": None, "reshaped": False}
RESHAPE = {"answer": "reshape", "word": "Reshape", "why": ["No one it is for is named"], "where": {"party": "", "name": "", "preset": False, "type": "", "type_name": ""},
           "first": "Name who it is for first", "test": "", "kills": [{"id": "no_who", "words": "No one it is for is named"}], "like": None, "reshaped": True}
CASE = {"case": "A conflict screen is a whole new flow, and two-device users are few.", "kills": [{"id": "costly", "words": "It costs more than it is likely to bring"}]}


class IdeationHost(StubHost):
    """The shell's stub with an Ideation party (`ideas`, led by the Investor, its four views and the Skeptic) and its pitches, each judged as the host would:
    `answer(slug, k)` lets k views answer, `decide(slug, d)` makes the case against and the decision."""

    def __init__(self):
        super().__init__()
        self.goals[PARTY] = self.goal(PARTY, "Ideas lab", "normal", "ready", order=3, leader=self.leader("investor"), team=list(TEAM), craft="product")
        self.judge: dict[str, dict] = {}                   # slug → {views: {id: answered?}, case, decision, sent, passed, before}
        self.pitch("dark-sync", "Sync in the dark", "judged", views=4, decision=copy.deepcopy(INVEST), case=copy.deepcopy(CASE))

    # -- the pitches ---------------------------------------------------------------------------------------------------------------
    def pitch(self, slug, title, state, views=0, decision=None, case=None, queue=""):
        self.ideas[slug] = self.idea(slug, title, state, 9, track=PARTY, queue=queue)
        self.judge[slug] = {"views": views, "case": case, "decision": decision, "sent": None, "passed": None, "before": []}

    def face(self, slug):
        j, st = self.judge[slug], self.ideas[slug]["state"]
        views = [who(v) | {"answered": i < j["views"], **dict(zip(("for", "against", "question", "size"), VIEW_SAYS[v] if i < j["views"] else ([], [], "", "")))}
                 for i, v in enumerate(VIEWS)]
        return {"state": st, "views": views, "skeptic": who("skeptic"), "investor": who("investor"), "case": j["case"], "decision": j["decision"],
                "sent": j["sent"], "passed": j["passed"], "before": j["before"]}

    def answer(self, slug, k):
        self.judge[slug]["views"] = k
        self.bump({})

    def decide(self, slug, decision, case=CASE):
        self.judge[slug].update(case=copy.deepcopy(case), decision=copy.deepcopy(decision))
        self.ideas[slug]["state"] = "judged"
        self.bump({})

    def is_pitch(self, slug):
        return slug in self.judge

    # -- what the host answers -------------------------------------------------------------------------------------------------------
    def needs_you(self):
        rows = super().needs_you()
        return rows + [{"kind": "pitch", "idea": s, "goal": PARTY, "title": self.ideas[s]["title"], "priority": "low", "blocks": False, "at": "2026-10-23T09:00:00",
                        "text": f"Judged: {j['decision']['word']}", "answer": j["decision"]["answer"]}
                       for s, j in self.judge.items() if s in self.ideas and self.ideas[s]["state"] == "judged" and j["decision"]]

    def page(self, slug):
        got = super().page(slug)
        if slug in self.judge and "error" not in got:
            got.update(track=PARTY, plan=None, checks=[], sections=[{"name": "Gist", "thesis": self.ideas[slug]["title"], "text": self.ideas[slug].get("text", self.ideas[slug]["title"])}],
                       pitch=self.face(slug))
        elif "error" not in got:
            got["pitch"] = None
        return got

    def map_doc(self):
        doc = super().map_doc()
        for g in doc["goals"]:
            if g["slug"] == PARTY:
                waiting = any(self.ideas[s]["state"] == "judged" for s in self.judge if s in self.ideas)
                g.update(ideation=True, types=[], leader=who("investor"), passed=sum(1 for s in self.judge if s in self.ideas and self.ideas[s]["state"] == "passed"),
                         stages={"lead": {"word": "Pitch"}, "build": {"word": "Views", "seats": 4}, "check": {"word": "Decision", "seats": 1}},
                         party=[who("investor") | {"band": "lead", "state": "needs" if waiting else "free", "why": "pitch" if waiting else ""}]
                         + [who(s) | {"band": "check" if s == "skeptic" else "build", "state": "free", "why": ""} for s in TEAM])
            else:
                g.update(ideation=False, passed=0)
        for n in doc["nodes"]:
            if n["slug"] in self.judge:
                st, face = n["state"], self.face(n["slug"])
                done = sum(v["answered"] for v in face["views"])
                n.update(pitch=face, folded=st == "passed", needs_you="pitch" if st == "judged" else "", tasks=[], progress={"done": 0, "total": 0},
                         stage="planning" if st in ("raw", "failed") else "implementation" if st == "judging" and done < 4 else "checking")
            else:
                n["pitch"] = None
        return doc

    def handle(self, name, a):
        if name == "ideas.party_price" and a.get("leader") == "investor":
            self.log.append((name, a))
            return {"low": 0.29, "high": 0.58, "learned": False, "ideas": 0, "checks": [], "pitch": True, "hints": [], "types": []}
        if name == "ideas.add" and a.get("track") == PARTY:
            self.log.append((name, a))
            slug = "-".join(a["text"].lower().split()[:3])
            queue = "hold" if a.get("hold") else "night" if a.get("night") else "now"
            self.pitch(slug, a["text"].split("\n")[0][:60], "judging" if queue == "now" else "raw", queue="" if queue == "now" else queue)
            self.ideas[slug]["text"] = a["text"]
            return self.bump({"slug": slug, "queue": queue, "element": "meadow", "type": "", "joined": None})
        if name == "ideas.judge":
            self.log.append((name, a))
            self.ideas[a["slug"]].update(state="judging", queue="")
            self.judge[a["slug"]].update(views=0, case=None, decision=None)
            return self.bump({"ok": True})
        if name == "ideas.pitch_send":
            self.log.append((name, a))
            j = self.judge[a["slug"]]
            if a["party"] not in self.goals:
                return {"error": "Make the Mobile app party first"}
            new = f"{a['slug']}-goal"
            self.ideas[new] = self.idea(new, j["decision"]["first"][:40], "reading", 10, track=a["party"])
            self.ideas[a["slug"]]["state"] = "sent"
            j["sent"] = {"party": a["party"], "type": "feature", "goal": new, "as_decided": True, "at": "2026-10-23T10:00:00", "name": self.goals[a["party"]]["title"],
                         "title": self.ideas[new]["title"]}
            return self.bump({"slug": new, "party": a["party"], "type": "feature", "queue": "now"})
        if name == "ideas.pitch_again":
            self.log.append((name, a))
            j = self.judge[a["slug"]]
            if a.get("text"):
                self.ideas[a["slug"]]["text"] = a["text"]
            j["before"] = ([dict(j["decision"], at="2026-10-23T09:00:00")] if j["decision"] else []) + j["before"][:1]
            j.update(views=0, case=None, decision=None, passed=None)
            self.ideas[a["slug"]]["state"] = "judging"
            return self.bump({"ok": True})
        if name == "ideas.pitch_pass":
            self.log.append((name, a))
            self.judge[a["slug"]]["passed"] = {"why": a.get("why", ""), "at": "2026-10-23T10:00:00", "as_decided": False}
            self.ideas[a["slug"]]["state"] = "passed"
            return self.bump({"ok": True, "dropped": []})
        if name == "ideas.drop" and a.get("slug") in self.judge:
            self.judge.pop(a["slug"])
        return super().handle(name, a)


@pytest.fixture
def lab(gui):
    pg, host, errors = _open(gui, host=IdeationHost(), ready=".arena-ptop")
    _show_goal(pg, PARTY)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _shot(pg, name):
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / name))


def _pitch_screen(pg, slug):
    pg.locator(f'.arena-pitchrow[data-slug="{slug}"] .arena-goal__main').click()
    pg.locator(".shell-pitch").wait_for(timeout=WAIT_MS)
    return pg.locator(".shell-drawer")


# -- New party (§1, §8) ----------------------------------------------------------------------------------------------------------------

def test_new_party_offers_ideation_with_its_seats_fixed_and_no_pitch_agent_elsewhere(gui):
    pg, host, errors = _open(gui, host=IdeationHost())
    try:
        _new_party(pg)
        dlg = pg.get_by_role("dialog", name="New party")
        everyone = dlg.locator(".shell-team-row")
        assert everyone.count() > 0 and not any(everyone.nth(i).get_attribute("data-agent") in ["investor", *TEAM] for i in range(everyone.count()))   # never offered elsewhere
        dlg.locator('.shell-craft-tile[data-craft="ideation"]').click()
        builds = dlg.get_by_role("region", name="Builds")
        assert [b.locator("h3").text_content() for b in (dlg.get_by_role("region", name=n) for n in ("Leads", "Builds", "Checks"))] == ["Pitch", "Views", "Decision"]
        assert builds.locator(".shell-team-seat:not(.is-empty)").count() == 4 and dlg.locator(".shell-team-row").count() == 0      # no seat change in Ideation
        assert "its views and the Skeptic stay" in dlg.inner_text()
        pg.get_by_text("This party: about $0.29–0.58 a pitch").wait_for(timeout=WAIT_MS)
        assert dlg.locator(".shell-cantake").count() == 0 and dlg.locator(".shell-checks").count() == 0
        _shot(pg, "ideation-new-party.png")
        dlg.get_by_label("Name", exact=True).fill("Ideas lab")
        dlg.get_by_role("button", name="Save party").click()
        got = _calls(pg, host, "ideas.goal_save")[0]
        assert got["preset"] == "ideation" and got["leader"] == "investor" and got["team"] == TEAM
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_edit_the_party_of_ideation_offers_no_seat_change(lab):
    pg, host = lab
    pg.get_by_role("button", name="Edit the party").click()
    dlg = pg.get_by_role("dialog", name="Edit the party")
    dlg.wait_for(timeout=WAIT_MS)
    assert dlg.get_by_role("button", name="Change the party").count() == 0 and "its views and the Skeptic stay" in dlg.inner_text()


# -- New goal in Ideation (§8)--------------------------------------------------------------------------------------------------------

def test_new_goal_in_ideation_is_one_box_and_judge_now_tonight_or_hold(lab):
    pg, host = lab
    assert "a pitch to judge" in pg.locator(".arena-new__words").inner_text()
    pg.get_by_role("button", name="New goal: a pitch to judge").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    dlg.wait_for(timeout=WAIT_MS)
    assert dlg.get_by_label("What is the pitch?").count() == 1 and dlg.locator("textarea").count() == 1
    assert dlg.get_by_label("Priority").count() == 0 and dlg.locator("[data-ask]").count() == 0 and dlg.locator(".arena-type__head, .arena-typed").count() == 0
    assert [b.inner_text() for b in dlg.locator(".shell-modal__foot button").all()] == ["Hold", "Tonight", "Judge now"]
    dlg.get_by_label("What is the pitch?").fill("Offline notes for travellers")
    _shot(pg, "ideation-new-goal.png")
    dlg.get_by_role("button", name="Hold").click()
    got = _calls(pg, host, "ideas.add")[-1]
    assert got["hold"] is True and got["track"] == PARTY and "type" not in got and "night" not in got
    _new_and_judge(pg, "Share a note by link")
    got = _calls(pg, host, "ideas.add", at_least=2)[-1]
    assert got["text"] == "Share a note by link" and "hold" not in got and "night" not in got and got["priority"] != "low"


def _new_and_judge(pg, text):
    pg.get_by_role("button", name="New goal: a pitch to judge").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    dlg.wait_for(timeout=WAIT_MS)
    dlg.get_by_label("What is the pitch?").fill(text)
    dlg.get_by_role("button", name="Judge now").click()
    dlg.wait_for(state="detached", timeout=WAIT_MS)


# -- the line on the field (§8) ------------------------------------------------------------------------------------------------------

def test_a_pitch_judging_lights_the_views_one_by_one_then_says_its_answer(lab):
    pg, host = lab
    assert [h.text_content() for h in pg.locator(".arena-pitches .arena-cols__head .arena-lbl:not(.is-blank)").all()] == ["Views", "Decision"]
    assert pg.locator(".arena-ptop__count").count() == 1 and "Judge now" in pg.locator(".arena-power").inner_text()
    _new_and_judge(pg, "Share a note by link")
    line = pg.locator('.arena-pitch[data-slug="share-a-note"]')
    line.wait_for(timeout=WAIT_MS)
    assert line.get_attribute("data-state") == "judging" and "judging · 0 of 4 views" in line.inner_text()
    lit = lambda: [c.get_attribute("data-view") for c in line.locator('.arena-pitch__view[data-on="true"]').all()]     # noqa: E731
    assert lit() == []
    for k in range(1, 5):
        host.answer("share-a-note", k)
        pg.wait_for_function(f"() => document.querySelectorAll('.arena-pitch[data-slug=\"share-a-note\"] .arena-pitch__view[data-on=true]').length === {k}", timeout=WAIT_MS)
        assert lit() == VIEWS[:k]                                                                 # one by one, in the views' order
    assert "the case against" in line.inner_text()
    _shot(pg, "ideation-judging.png")
    host.decide("share-a-note", INVEST)
    pg.locator('.arena-pitch[data-slug="share-a-note"][data-state="judged"]').wait_for(timeout=WAIT_MS)
    assert line.locator(".arena-pitch__answer").text_content() == "Invest"
    row = pg.locator('.arena-pitchrow[data-slug="share-a-note"]')
    assert "judged: Invest" in row.inner_text() and row.locator(".arena-goal__mark.is-alert").count() == 1
    assert pg.locator('.arena-hc[data-kind="pitch"]').count() == 2                                 # Needs you's pitch rows, in the one hand


def test_a_pitchs_screen_has_the_four_views_the_case_against_and_the_decision_and_send_sends_it(lab):
    pg, host = lab
    drawer = _pitch_screen(pg, "dark-sync")
    views = drawer.locator(".shell-pitch__view")
    assert views.count() == 4 and [v.get_attribute("data-view") for v in views.all()] == VIEWS
    tops = {round(v.bounding_box()["y"]) for v in views.all()}
    assert len(tops) == 1                                                                         # side by side
    tech = drawer.locator('.shell-pitch__view[data-view="tech-view"]')
    assert "The sync queue is there" in tech.inner_text() and "Conflicts on two devices" in tech.inner_text() and "Which device wins a conflict?" in tech.inner_text()
    assert tech.locator(".ork-race__head").count() == 1 and tech.locator(".board-size").inner_text() == "M"
    case = drawer.get_by_role("region", name="The case against")
    assert "A conflict screen is a whole new flow" in case.inner_text() and "It costs more than it is likely to bring" in case.inner_text()
    dec = drawer.get_by_role("region", name="Decision")
    assert dec.locator(".shell-pitch__answer").text_content() == "Invest"
    assert "Two-device users lose notes today" in dec.inner_text() and "the Ship sync party, as New feature" in dec.inner_text()
    assert "Sync notes offline" in dec.inner_text() and "Ask five two-device users" in dec.inner_text()
    words = drawer.locator(".shell-pitch__list").first.evaluate("e => getComputedStyle(e).fontFamily")
    title = dec.locator(".shell-pitch__answer").evaluate("e => getComputedStyle(e).fontFamily")
    assert words != title                                                                          # the views' words in the text face, the answer in the pixel face
    _shot(pg, "ideation-pitch.png")
    send = drawer.get_by_label("Send to party")
    assert send.input_value() == "ship-sync" and PARTY not in [o.get_attribute("value") for o in send.locator("option").all()]
    drawer.get_by_role("button", name="Send to Ship sync").click()
    got = _calls(pg, host, "ideas.pitch_send")[0]
    assert got["slug"] == "dark-sync" and got["party"] == "ship-sync" and "type" not in got
    pg.get_by_text("Sent: a new goal in Ship sync, drafted now.").wait_for(timeout=WAIT_MS)
    drawer.locator('.shell-pitch[data-state="sent"]').wait_for(timeout=WAIT_MS)
    assert "sent to Ship sync" in drawer.locator(".shell-pitch__after").inner_text()
    pg.keyboard.press("Escape")
    pg.locator(".arena-sent").click()
    assert "sent to Ship sync · Sync notes offline" in pg.locator('.arena-pitchrow[data-slug="dark-sync"]').inner_text()


def test_a_preset_the_project_lacks_opens_new_party_with_it(lab):
    pg, host = lab
    host.judge["dark-sync"]["decision"]["where"] = {"party": "mobile-app", "name": "Mobile app", "preset": True, "type": "", "type_name": ""}
    drawer = _pitch_screen(pg, "dark-sync")
    assert drawer.get_by_label("Send to party").input_value() == "mobile-app"
    drawer.get_by_role("button", name="Send to Mobile app").click()
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.wait_for(timeout=WAIT_MS)
    assert dlg.locator('.shell-craft-tile[data-craft="mobile-app"]').get_attribute("aria-pressed") == "true"
    assert not [a for n, a in host.log if n == "ideas.pitch_send"]


def test_a_reshape_changed_and_judged_again(lab):
    pg, host = lab
    host.decide("dark-sync", RESHAPE)
    drawer = _pitch_screen(pg, "dark-sync")
    dec = drawer.get_by_role("region", name="Decision")
    dec.locator('.shell-pitch__answer[data-answer="reshape"]').wait_for(timeout=WAIT_MS)
    assert "No one it is for is named" in dec.inner_text() and "made it a reshape" in dec.inner_text()
    drawer.get_by_role("button", name="Change and judge again").click()
    box = drawer.get_by_label("The pitch, changed")
    box.fill("Sync in the dark, for people who write on the train")
    drawer.get_by_role("button", name="Judge it again").click()
    got = _calls(pg, host, "ideas.pitch_again")[0]
    assert got == {"slug": "dark-sync", "text": "Sync in the dark, for people who write on the train", "via": "pitch"}
    drawer.locator('.shell-pitch[data-state="judging"]').wait_for(timeout=WAIT_MS)
    assert drawer.locator(".shell-pitch__view.is-off").count() == 4 and "Before (1)" in drawer.inner_text()
    host.answer("dark-sync", 2)
    pg.wait_for_function("() => document.querySelectorAll('.shell-pitch__view:not(.is-off)').length === 2", timeout=WAIT_MS)


def test_pass_folds_it_under_passed_and_it_can_be_judged_again(lab):
    pg, host = lab
    drawer = _pitch_screen(pg, "dark-sync")
    drawer.get_by_role("button", name="Pass", exact=True).click()
    drawer.get_by_label("Why you pass").fill("Not this quarter")
    drawer.get_by_role("button", name="Pass it").click()
    assert _calls(pg, host, "ideas.pitch_pass")[0] == {"slug": "dark-sync", "why": "Not this quarter", "via": "pitch"}
    fold = pg.locator(".arena-passed")
    fold.wait_for(timeout=WAIT_MS)
    assert fold.inner_text() == "Passed (1)" and fold.get_attribute("aria-expanded") == "false"
    assert pg.locator('.arena-pitch[data-slug="dark-sync"]').count() == 0 and pg.locator('.arena-pitchrow[data-slug="dark-sync"]').count() == 0
    drawer.locator('.shell-pitch[data-state="passed"]').wait_for(timeout=WAIT_MS)
    assert "Not this quarter" in drawer.locator('[data-after="passed"]').inner_text()
    _shot(pg, "ideation-passed.png")
    drawer.get_by_role("button", name="Judge again").click()
    assert _calls(pg, host, "ideas.pitch_again")[0] == {"slug": "dark-sync", "via": "pitch"}


def test_needs_you_pitch_opens_the_pitchs_screen(lab):
    pg, host = lab
    _show_goal(pg)                                                                                  # another party shown: the stop says its party
    stop = _stop(pg, "pitch")
    assert "Pitch judged" in stop.text_content() and "Judged: Invest" in stop.inner_text()
    stop.get_by_role("button", name="Open the pitch").click()
    pg.locator('.shell-pitch[data-state="judged"]').wait_for(timeout=WAIT_MS)
    assert pg.locator(".arena[data-goal=ideas]").count() == 1


def test_a_failed_pitch_says_why_and_tries_again(lab):
    pg, host = lab
    host.pitch("lost-views", "Lost views", "failed", views=2)
    host.ideas["lost-views"]["state_error"] = "Market view did not answer: try again"
    host.bump({})
    row = pg.locator('.arena-pitchrow[data-slug="lost-views"]')
    row.wait_for(timeout=WAIT_MS)
    assert "failed · Market view did not answer: try again" in row.inner_text() and row.locator(".arena-goal__mark.is-danger").count() == 1
    drawer = _pitch_screen(pg, "lost-views")
    assert "Market view did not answer" in drawer.locator(".shell-error").inner_text()
    drawer.get_by_role("button", name="Try again").click()
    assert _calls(pg, host, "ideas.judge")[0]["slug"] == "lost-views"


def test_drop_asks_first(lab):
    pg, host = lab
    drawer = _pitch_screen(pg, "dark-sync")
    drawer.get_by_role("button", name="Drop", exact=True).click()
    drawer.get_by_role("button", name="Drop it").click()
    assert _calls(pg, host, "ideas.drop")[0]["slug"] == "dark-sync"
    pg.locator('.arena-pitchrow[data-slug="dark-sync"]').wait_for(state="detached", timeout=WAIT_MS)
