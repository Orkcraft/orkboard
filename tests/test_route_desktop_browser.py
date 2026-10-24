"""Spec 68 part B on the desktop, a goal's route (docs/specs/68-release-and-route.md §2, §7.1, §7.2, §7.7–§7.9, §8 "B"): Chromium at 1 440 × 900 against the one window's stub host with an Ideation party,
a Website party and a Release party (its leader the Release manager, a skeleton) beside the Passkey party. A goal sent from Ideation shows its route at the top of its screen in the drawer, each step a
button that opens what it names (the pitch's screen, the party with the goal picked into the filter, the release goal's screen); a goal with only its party step shows none; a sent pitch's screen and
Ideation's list say its goal (*At work in Passkey · 3 of 7*, *In main*, *In Release 1.4*, *Out in 1.4*, *Dropped*); a party switch says `ideas.shown`, fire and forget; the skeleton's head is drawn from the
host's `race`; an older host (no `route`, `goal_state`, `race`) draws as before. The Release party's goals, flags and forms are tests/test_release_desktop_browser.py's. Screenshots to the scratchpad
directory when ORKCRAFT_SHOTS_DIR is set."""
from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import ArenaHost, ELEMENT, member, pip  # noqa: E402
from tests.test_ideation_desktop_browser import CASE, INVEST, VIEWS, VIEW_SAYS, who  # noqa: E402
from tests.test_map_desktop_browser import node  # noqa: E402
from tests.test_shell_browser import _calls, _open, _parties, _show_goal  # noqa: E402

pytestmark = pytest.mark.browser

SKELETON = {"craft": "product", "race": "skeleton", "tier": "warrior"}
RELEASE_MANAGER = {"slug": "release-manager", "name": "Release manager", "head": SKELETON}
RELEASE_TYPE = {"id": "release", "name": "A release", "sign": "release", "line": "A version out: what is new, the build, the stores' list", "lens": "text", "refs": False, "used": 0, "missing": [],
                "asks": [{"id": "version", "label": "Version", "hint": "1.4"}, {"id": "new", "label": "What is new", "hint": "in the person's words"}]}
OUT = "2026-10-26T12:00:00"
SHOTS = os.environ.get("ORKCRAFT_SHOTS_DIR", "")
SHORT = {"passkey": "Passkey", "ideas": "Ideation", "release": "Release", "website": "Website"}

PITCH_STEP = {"step": "pitch", "party": "ideas", "goal": "dark", "at": "2026-10-22T09:00:00", "answer": "invest", "word": "Invest", "title": "Dark mode"}
MOVED_STEP = {"step": "moved", "party": "website", "from": "website", "to": "passkey", "goal": "register", "at": "2026-10-23T09:00:00"}
PARTY_STEP = {"step": "party", "party": "passkey", "goal": "register", "at": "2026-10-23T09:00:00", "state": "working", "done": 3, "total": 7}
MAIN_STEP = {"step": "main", "party": "passkey", "goal": "register", "at": "2026-10-24T09:00:00", "by": "gate"}
RELEASE_STEP = {"step": "release", "goal": "r14", "party": "release", "version": "1.4", "out": "", "at": "2026-10-24T10:00:00"}
FULL_ROUTE = [PITCH_STEP, MOVED_STEP, PARTY_STEP, MAIN_STEP, RELEASE_STEP]
WORDS = ["From Ideation: Invest, 22 Oct", "Moved from Website", "At work in Passkey · 3 of 7", "In main", "In Release 1.4"]


def shot(pg, name):
    if SHOTS:
        Path(SHOTS).mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(Path(SHOTS) / name))


class RouteHost(ArenaHost):
    """The arena's Passkey party with Ideation (four pitches sent to goals of Passkey, in each state a sent goal can be in), Website and — with `release` — a Release party whose goals r14 (in main, to go out)
    and r13 (out) hold the flags of `button` (in 1.4) and `creds` (in 1.3); `badge` and `dark-ui` have raised their flag and wait. `old`: a host from before spec 68 (no route, no goal_state, no race)."""

    def __init__(self, release=True, old=False):
        super().__init__()
        self.has_release, self.old, self.refuse = release, old, ""
        self.releases_from, self.offers = {}, set()                  # a party's `releases_from` as saved; the parties (besides the Release party) that offer *A release*
        self.since, self.candidates = {"version": "1.3", "out": "2026-10-10T10:00:00"}, []
        self.goals["ideas"] = self.goal("ideas", "Ideas lab", "normal", "ready", order=4)
        self.goals["website"] = self.goal("website", "Website", "normal", "ready", order=5)
        if release:
            self.goals["release"] = self.goal("release", "Release", "normal", "ready", order=6)
        self.rel = {"r14": {"version": "1.4", "goals": ["button"], "out": ""}, "r13": {"version": "1.3", "goals": ["creds"], "out": "2026-10-10T10:00:00"}} if release else {}
        self.routes = {"register": copy.deepcopy(FULL_ROUTE)}
        self.states = {}
        flagged = [("badge", "passkey", "A badge on the icon", "2026-10-20T09:00:00"), ("dark-ui", "passkey", "Dark sign-in page", "2026-10-21T09:00:00")]
        for slug, party, title, at in flagged:
            self.add(node(slug, party, title, "done", 1, stage="done", progress={"done": 2, "total": 2}, folded=True), "ice")
            self.flag(self.node_of(slug), at=at, tasks=2, first_time=2, usd=0.8)
        self.flag(self.node_of("creds"), at="2026-10-09T09:00:00", tasks=2, first_time=2, usd=0.9)
        for slug, title, at in (("r14", "Release 1.4", "2026-10-24T11:00:00"), ("r13", "Release 1.3", "2026-10-10T10:00:00")) if release else ():
            self.add(node(slug, "release", title, "done", 1, stage="done", progress={"done": 2, "total": 2}, folded=True,
                          type={"id": "release", "name": "A release", "sign": "release"}), "meadow")
            self.flag(self.node_of(slug), at=at, tasks=2, first_time=2, usd=0.5)
        for slug, title, goal, state in (("dark", "Dark mode", "register", {"goal": "register", "party": "passkey", "state": "working", "done": 3, "total": 7, "flag": "", "release": None}),
                                         ("pbadge", "Badge on the icon", "badge", {"goal": "badge", "party": "passkey", "state": "done", "done": 2, "total": 2, "flag": "2026-10-20T09:00:00", "release": None}),
                                         ("pbutton", "A button for the passkey", "button", {"goal": "button", "party": "passkey", "state": "done", "done": 3, "total": 3, "flag": "2026-10-14T10:00:00",
                                                                                           "release": {"goal": "r14", "party": "release", "version": "1.4", "out": ""}}),
                                         ("pcreds", "Keep the credentials", "creds", {"goal": "creds", "party": "passkey", "state": "done", "done": 2, "total": 2, "flag": "2026-10-09T09:00:00",
                                                                                      "release": {"goal": "r13", "party": "release", "version": "1.3", "out": "2026-10-10T10:00:00"}}),
                                         ("pgone", "A goal dropped", "gone", {"goal": "gone", "party": "", "state": "dropped", "done": 0, "total": 0, "flag": "", "release": None})):
            self.add(node(slug, "ideas", title, "sent", 1, stage="checking", folded=False), "meadow")
            self.states[slug] = state

    def add(self, n, element):
        n["element"], n["flag"] = element, None
        self.nodes.append(n)
        self.ideas[n["slug"]] = self.idea(n["slug"], n["title"], n["state"], len(self.ideas), track=n["goal"])

    def face(self, slug):
        gs = self.states[slug]
        views = [who(v) | {"answered": True, **dict(zip(("for", "against", "question", "size"), VIEW_SAYS[v]))} for v in VIEWS]
        sent = {"party": "passkey", "type": "feature", "goal": gs["goal"], "as_decided": True, "at": "2026-10-23T10:00:00", "name": "Passkey", "title": "WebAuthn register"}
        out = {"state": "sent", "views": views, "skeptic": who("skeptic"), "investor": who("investor"), "case": CASE, "decision": copy.deepcopy(INVEST), "sent": sent, "passed": None, "before": []}
        return out if self.old else out | {"goal_state": copy.deepcopy(gs)}

    def page(self, slug):
        got = super().page(slug)
        if "error" in got:
            return got
        if slug in self.states:
            got.update(track="ideas", plan=None, checks=[], sections=[{"name": "Gist", "thesis": "x", "text": self.ideas[slug]["title"]}], pitch=self.face(slug))
        else:
            got["pitch"] = None
        if not self.old:
            got["route"] = copy.deepcopy(self.routes.get(slug, []))
        return got

    def map_doc(self):
        doc = super().map_doc()
        doc["nodes"] = nodes = [copy.deepcopy(n) for n in doc["nodes"]]
        held = {g: r for r, v in self.rel.items() for g in v["goals"]}
        for n in nodes:
            n["element"] = n["element"] or ELEMENT.get(n["slug"], "meadow")
            n["pitch"] = self.face(n["slug"]) if n["slug"] in self.states else None
            if n["slug"] in self.states and not self.old:
                n["goal_state"] = copy.deepcopy(self.states[n["slug"]])
            if self.old:
                continue
            n["route"] = copy.deepcopy(self.routes.get(n["slug"], []))
            if n["slug"] in self.rel:
                n["release"] = {**self.rel[n["slug"]]}
            if n.get("flag"):
                r = held.get(n["slug"])
                n["flag"]["release"] = {"goal": r, "party": "release", "version": self.rel[r]["version"], "out": self.rel[r]["out"]} if r else None
        for g in doc["goals"]:
            g["short"] = SHORT.get(g["slug"], g["title"])
            g["ideation"] = g["slug"] == "ideas"
            g["types"] = [RELEASE_TYPE] if g["slug"] in self.offers else g.get("types", [])
            if g["slug"] in self.offers and not self.old:
                g.update(releases_from=list(self.releases_from.get(g["slug"], [])), wait_release=sum(1 for n in nodes if n["goal"] == g["slug"] and n.get("flag") and not n["flag"].get("release")))
            if g["slug"] == "ideas":
                g.update(leader=who("investor"), passed=0, stages={"lead": {"word": "Pitch"}, "build": {"word": "Views", "seats": 4}, "check": {"word": "Decision", "seats": 1}},
                         party=[who("investor") | {"band": "lead", "state": "free", "why": ""}] + [who(s) | {"band": "check" if s == "skeptic" else "build", "state": "free", "why": ""}
                                                                                                    for s in (*VIEWS, "skeptic")])
            if g["slug"] == "release":
                g.update(leader=RELEASE_MANAGER, types=[RELEASE_TYPE], team=[],
                         party=[member("release-manager", "Release manager", SKELETON, "lead"), member("release-engineer", "Release engineer", HEAD_OWN, "build"),
                                member("release-checker", "Release checker", SKELETON, "check")])
                if not self.old:
                    g.update(releases_from=list(self.releases_from.get("release", [])), wait_release=sum(1 for n in nodes if n.get("flag") and n["goal"] != "release" and not n["flag"].get("release")))
        return doc

    def handle(self, name, a):
        if name == "ideas.release_candidates":
            self.log.append((name, a))
            return {"since": self.since, "releases_from": [], "candidates": copy.deepcopy(self.candidates)}
        if name == "ideas.release_out":
            self.log.append((name, a))
            if self.refuse:
                return {"error": self.refuse}
            self.rel[a["slug"]]["out"] = OUT
            return self.bump({"ok": True, "out": OUT})
        return super().handle(name, a)


HEAD_OWN = {"craft": "engineering", "race": "peon", "tier": "laborer"}


@pytest.fixture
def routed(gui):
    pg, host, errors = _open(gui, host=RouteHost(), ready=".arena[data-goal=passkey]")
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _goal(pg, slug):
    """A goal's screen in the drawer, opened with › on its row."""
    pg.locator(f'.arena-goal[data-slug="{slug}"] .arena-goal__open').click()
    pg.locator(".board-ideaview").wait_for(timeout=WAIT_MS)
    return pg.locator(".shell-drawer")


def _steps(pg):
    return pg.locator(".arena-route .arena-route__step")


def _words(pg):
    return [s.inner_text().strip() for s in _steps(pg).all()]


def _tab(pg, slug):
    """The pitch of Ideation, opened from its row (the Sent fold opened first)."""
    _show_goal(pg, "ideas")
    if not pg.locator(f'.arena-pitchrow[data-slug="{slug}"]').count():
        pg.locator(".arena-sent").click()
    pg.locator(f'.arena-pitchrow[data-slug="{slug}"] .arena-goal__main').click()
    pg.locator(".shell-pitch").wait_for(timeout=WAIT_MS)


# -- the route's line ----------------------------------------------------------------------------------------------------------------------------------------

def test_a_goal_sent_from_ideation_shows_its_route_at_the_top_of_its_screen_one_step_a_button(routed):
    pg, host = routed
    _goal(pg, "register")
    nav = pg.get_by_role("navigation", name="Route")
    assert nav.count() == 1 and nav.locator("h3").text_content() == "Route"
    assert _words(pg) == WORDS
    steps = _steps(pg)
    assert [s.get_attribute("data-step") for s in steps.all()] == ["pitch", "moved", "party", "main", "release"]
    assert steps.last.get_attribute("aria-current") == "step" and pg.locator(".arena-route [aria-current]").count() == 1
    assert nav.locator(".ork-chev.right").count() == 4                                                    # joined by orkUI's ›, four of them
    assert nav.locator(".arena-route__step .ork-race__head.small").count() == 5                            # the head of each party's leader, small
    heads = [s.locator(".ork-race__head").get_attribute("src") for s in steps.all()]
    assert "investor" not in heads[0] and "lich-" in heads[0] and "peon-" in heads[2] and "skeleton-" in heads[4]    # Ideation's Investor (a lich), Passkey's Taskmaster (an ork), the Release manager (a skeleton)
    assert all(s.bounding_box()["height"] >= 24 for s in steps.all())
    top = pg.locator(".board-ideaview").bounding_box()["y"]
    assert nav.bounding_box()["y"] - top < 8 and nav.bounding_box()["y"] < pg.locator(".board-ideaview .board-bar").bounding_box()["y"]       # first, over the goal's state
    assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    shot(pg, "desk-route.png")


def test_each_step_opens_what_it_names(routed):
    pg, host = routed
    _goal(pg, "register")
    _steps(pg).nth(0).click()                                                                              # the pitch it was sent from: its screen
    pg.locator(".shell-pitch").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-pitch .shell-goal__head h2").inner_text() == "Dark mode"
    _open_register(pg)
    _steps(pg).nth(1).click()                                                                              # moved from Website: that party, whole
    pg.locator('.arena[data-goal="website"]').wait_for(timeout=WAIT_MS)
    assert pg.locator('.arena-phead[data-goal="website"]').get_attribute("aria-current") == "true"
    assert _steps(pg).count() == 5                                                                         # the drawer stays: the board changed behind it
    _steps(pg).nth(2).click()                                                                              # where it is: Passkey, the goal picked into the filter
    pg.locator('.arena[data-goal="passkey"]').wait_for(timeout=WAIT_MS)
    assert pg.locator('.arena-phead[data-goal="passkey"]').get_attribute("aria-current") == "true"
    pg.locator('.arena-goal[data-slug="register"].is-on').wait_for(timeout=WAIT_MS)
    assert pg.locator(".arena-goal.is-on").count() == 1 and pg.locator(".arena-left__head .arena-lbl + .ork-count + .arena-spacer + button", has_text="Show all").count() == 1
    pg.locator(".arena-left__head button", has_text="Show all").click()
    assert pg.locator(".arena-goal.is-on").count() == 0
    _steps(pg).nth(3).click()                                                                              # in main: the same party, the goal picked
    pg.locator('.arena-goal[data-slug="register"].is-on').wait_for(timeout=WAIT_MS)
    _steps(pg).nth(4).click()                                                                              # the release it is in: that goal's screen
    pg.wait_for_function("() => document.querySelectorAll('.arena-route').length === 0 && document.querySelector('.board-ideaview')", timeout=WAIT_MS)
    assert any(a.get("slug") == "r14" for a in _calls(pg, host, "ideas.page", at_least=2))


def _open_register(pg):
    """The register goal's screen again (its tab, or › on its row when the drawer shows something else)."""
    pg.locator('.arena-goal[data-slug="register"] .arena-goal__open').click()
    pg.locator(".arena-route").wait_for(timeout=WAIT_MS)


def test_a_goal_with_only_its_party_step_shows_no_route_and_a_step_not_working_says_in_the_party(routed):
    pg, host = routed
    _goal(pg, "signin")
    assert pg.locator(".arena-route").count() == 0
    host.routes["signin"] = [{**PARTY_STEP, "goal": "signin", "state": "plan", "done": 0, "total": 4}, {**MAIN_STEP, "goal": "signin"}]
    host.bump({})
    pg.locator(".arena-route").wait_for(timeout=WAIT_MS)
    assert _words(pg) == ["In Passkey", "In main"]                                                         # at work only while the goal works
    host.routes["signin"] = [{**PARTY_STEP, "goal": "signin", "done": 2, "total": 4}]
    host.bump({})
    pg.wait_for_function("() => document.querySelector('.arena-route__words')?.textContent === 'At work in Passkey · 2 of 4'", timeout=WAIT_MS)
    host.routes["signin"] = [{**RELEASE_STEP, "out": "2026-10-26T12:00:00"}]
    host.bump({})
    pg.wait_for_function("() => document.querySelector('.arena-route__words')?.textContent === 'Out in 1.4'", timeout=WAIT_MS)


# -- a sent pitch ----------------------------------------------------------------------------------------------------------------------------------------------

def test_a_sent_pitch_says_its_goal_under_its_decision_and_a_press_opens_the_goal(routed):
    pg, host = routed
    for slug, words in (("dark", "At work in Passkey · 3 of 7"), ("pbadge", "In main"), ("pbutton", "In Release 1.4"), ("pcreds", "Out in 1.3"), ("pgone", "Dropped")):
        _tab(pg, slug)
        line = pg.locator('.shell-pitch [data-after="goal"]')
        assert line.inner_text().replace("\n", " ").strip() == f"Its goal · {words}", slug
        assert pg.locator(".shell-pitch .board-bar .board-state").inner_text().strip() == words
        if slug == "pgone":
            assert line.locator("button").count() == 0                                                     # a goal dropped cannot be opened
    _tab(pg, "pbadge")
    pg.locator('.shell-pitch [data-after="goal"] button').click()
    pg.locator(".board-ideaview").wait_for(timeout=WAIT_MS)
    assert any(a.get("slug") == "badge" for a in _calls(pg, host, "ideas.page", at_least=2))


def test_ideations_list_says_a_sent_pitchs_goal_short_in_the_same_words(routed):
    pg, host = routed
    _show_goal(pg, "ideas")
    pg.locator(".arena-sent").click()
    said = {s: pg.locator(f'.arena-pitchrow[data-slug="{s}"] .arena-goal__line').inner_text() for s in ("dark", "pbadge", "pbutton", "pcreds", "pgone")}
    assert said == {"dark": "At work in Passkey · 3 of 7", "pbadge": "In main", "pbutton": "In Release 1.4", "pcreds": "Out in 1.3", "pgone": "Dropped"}
    host.states["dark"].update(state="done", flag="2026-10-25T09:00:00")                                    # the goal reached main: the row follows
    host.bump({})
    pg.wait_for_function("() => document.querySelector('.arena-pitchrow[data-slug=dark] .arena-goal__line')?.textContent === 'In main'", timeout=WAIT_MS)


def test_an_older_host_draws_as_before_no_route_and_a_sent_pitch_says_where_it_went(gui):
    pg, host, errors = _open(gui, host=RouteHost(release=False, old=True), ready=".arena[data-goal=passkey]")
    try:
        _goal(pg, "register")
        assert pg.locator(".arena-route").count() == 0
        _tab(pg, "dark")
        assert pg.locator('.shell-pitch [data-after="goal"]').count() == 0
        assert pg.locator('.shell-pitch [data-after="sent"]').inner_text().strip().startswith("sent to Passkey · WebAuthn register")
        assert pg.locator(".shell-pitch .board-state").inner_text().startswith("sent to Passkey")
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


# -- the party switch and the heads -------------------------------------------------------------------------------------------------------------------------

def test_a_party_switch_says_ideas_shown_fire_and_forget_and_only_a_switch(routed):
    pg, host = routed
    assert not _calls(pg, host, "ideas.shown", at_least=1, ms=300)                                           # not on the first read
    pg.locator('.arena-phead[data-goal="pricing"]').click()
    pg.locator('.arena[data-goal="pricing"]').wait_for(timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.shown") == [{"party": "pricing", "from": "passkey"}]
    pg.locator('.arena-phead[data-goal="pricing"]').click()                                                  # the open heading: nothing
    pg.locator('.arena-phead[data-goal="weekly"]').click()
    pg.locator('.arena[data-goal="weekly"]').wait_for(timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.shown", at_least=2) == [{"party": "pricing", "from": "passkey"}, {"party": "weekly", "from": "pricing"}]
    host.ops = True
    host.bump({})
    pg.locator('.arena-phead[data-goal="@operations"]').click()                                              # Operations is not a party: not counted
    pg.locator(".arena-ops").wait_for(timeout=WAIT_MS)
    pg.locator('.arena-phead[data-goal="passkey"]').click()
    pg.locator('.arena[data-goal="passkey"]').wait_for(timeout=WAIT_MS)
    assert len(_calls(pg, host, "ideas.shown", at_least=2)) == 2


def test_the_skeletons_head_is_drawn_from_the_hosts_race_in_the_column_and_in_new_party(routed):
    pg, host = routed
    head = pg.locator('.arena-phead[data-goal="release"] .arena-plist__head img.ork-race__head')
    assert "/races/skeleton-warrior" in head.get_attribute("src")
    assert head.evaluate("(i) => i.complete && i.naturalWidth > 0")
    _parties(pg).locator(".arena-pnew").click()
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.wait_for(timeout=WAIT_MS)
    tiles = dlg.locator(".shell-craft-tile")
    tiles.first.wait_for(timeout=WAIT_MS)
    assert [t.get_attribute("data-craft") for t in tiles.all()][:5] == ["game", "mobile-app", "website", "ideation", "release"]       # the fifth tile of the mixed group
    srcs = dlg.locator('.shell-craft-tile[data-craft="release"] img.ork-race__head').evaluate_all("(is) => is.map((i) => i.getAttribute('src'))")
    assert srcs and all("/races/skeleton-" in s for s in srcs[:1]) and "/races/skeleton-" in srcs[-1]        # the Release manager and the checker are skeletons
    dlg.locator('.shell-craft-tile[data-craft="release"]').click()
    seats = dlg.locator(".shell-team-seat .ork-race__head").evaluate_all("(is) => is.map((i) => i.getAttribute('src'))")
    assert any("/races/skeleton-" in s for s in seats)                                                       # the seats too
