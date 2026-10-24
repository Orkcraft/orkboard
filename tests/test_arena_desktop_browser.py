"""The one window on the desktop (docs/specs/49-one-window.md §3–§9, §11, docs/specs/50-parties-and-goals.md §3–§5; Tests → B), in a real browser at
1 440 × 900 against a stub host that answers `ideas.map`, `ideas.agents`, `ideas.board`, `ideas.gate`, `ideas.today` and `ideas.flags` in their shapes:
the regions and their sizes, the party tabs, the leader over the party's goals, the party line, a member's numbers, marks and peek, solo, the rows by
phase, the results, the gate, the stops in the fan, the strip, the limits, the drawer, the narrow layout. The goals list, the filter, the stacks, a
spread, the arrows, New goal's pile and the flag line are tests/test_arena_decks_desktop_browser.py's. Screenshots to docs/design/img/v1/ when
ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import datetime as dt
import os
import re

import pytest

pytest.importorskip("playwright.sync_api")

from orkboard.realm import idea_element  # noqa: E402
from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_map_desktop_browser import node, pip as _pip  # noqa: E402
from tests.test_shell_browser import LEAD, _parties, SHOTS, StubHost, _calls, _drawer, _open, _sent, _show_goal, _stop, box  # noqa: E402

pytestmark = pytest.mark.browser

HEAD = {"craft": "engineering", "race": "peon", "tier": "warrior"}
ELF = {"craft": "design", "race": "elf", "tier": "warrior"}
ELDER = {"craft": "engineering", "race": "peon", "tier": "elder"}
GNOME = {"craft": "marketing", "race": "gnome", "tier": "laborer"}
NAMES = {"backend": "Backend", "screens": "Screens", "reviewer": "Reviewer", "words": "Words"}
HEADS = {"backend": HEAD, "screens": ELF, "reviewer": ELDER, "words": GNOME}


def pip(tid, title, state, after=(), wave=1, by="backend", band="build"):
    """A task of the party's member `by`, with its name and its head."""
    return {"round": 1, "error": "", "note": "", "cost": None, "started": ""} | _pip(tid, title, state, after, wave, by, band) | {
        "by": {"slug": by, "name": NAMES.get(by, by)}, "head": HEADS.get(by, HEAD)}


IN_MIN = lambda n: (dt.datetime.now() - dt.timedelta(minutes=n)).isoformat(timespec="seconds")      # noqa: E731
RESULT = {"idea": "register", "idea_title": "WebAuthn register", "task": "k1", "title": "Challenge store", "round": 1,
          "tests": {"passed": 14, "failed": 0, "failing": [], "tail": "", "green": True}, "diff": {"files": 14, "added": 146, "removed": 0}, "cost": 0.42,
          "conflict": "", "finished": "2026-10-20T10:00:00", "estimate": None, "over": None}
CHECK = {"idea": "signin", "idea_title": "Sign in with the passkey", "task": "c2", "title": "Words on the screens", "round": 1, "check": "Words",
         "tests": {"passed": 0, "failed": 0, "failing": [], "tail": "", "green": True, "ran": False}, "diff": {"files": 2, "added": 9, "removed": 9}, "cost": 0.04,
         "conflict": "", "finished": "2026-10-20T11:00:00", "estimate": None, "over": None,
         "findings": [{"where": "the sign-in screen", "what": "an error that says nothing", "fixed": False}, {"where": "settings", "what": "one word", "fixed": True}]}


ELEMENT = {"register": "meadow", "signin": "ice", "cookie": "dust", "recovery": "void", "second": "lava", "ratelimit": "meadow", "pagewords": "ice",
           "magic": "dust", "log": "void", "button": "meadow", "creds": "ice", "prices": "meadow"}


def member(slug, name, head, band, state="free", why=""):
    return {"slug": slug, "name": name, "head": head, "band": band, "state": state, "why": why}


class ArenaHost(StubHost):
    """The passkey goal of the mockup: a leader, two builders, two checkers; ideas in every stage; stops of every kind."""

    def __init__(self):
        super().__init__()
        self.ideas, self.goals = {}, {}
        for slug, title, prio, order in (("passkey", "Sign in with a passkey", "high", 1), ("pricing", "Pricing page", "normal", 2), ("weekly", "Weekly report email", "low", 3)):
            self.goals[slug] = self.goal(slug, title, prio, "ready", order=order)
        self.goals["general"] = self.goal("general", "General", "normal", "ready", order=0)
        self.ops = False
        self.limits = [{"provider": "claude", "name": "Claude", "left": 0.62, "rows": [{"window": "5h", "left": 0.62, "reset": "2099-01-01T18:00"}]},
                       {"provider": "codex", "name": "Codex", "left": 0.4, "rows": [{"window": "week", "left": 0.4, "reset": "2099-01-05T09:00"}]}]
        self.week = {"backend": {"spent": 1.9, "merged": 5, "first_time": 4, "finished": 5, "usd_per_merged": 0.38},
                     "screens": {"spent": 0.6, "merged": 2, "first_time": 2, "finished": 2, "usd_per_merged": None},
                     "taskmaster": {"spent": 0.72, "plans": 6, "first_time": 5, "finished": 6}}
        self.check_week = {"reviewer": {"checks": 6, "clean": 4, "caught": 2, "left": 0, "usd_per_check": None}}
        self.usd_task = {"backend": 0.38, "screens": 0.30, "reviewer": 0.25, "words": 0.05}
        self.harness = {"screens": {"id": "codex", "name": "Codex"}}
        self.tasks = [pip("k1", "Challenge store", "review", wave=1, by="backend"), pip("k2", "Credential table", "running", wave=1, by="backend"),
                      pip("k3", "Register screen", "running", wave=1, by="screens"), pip("k5", "Register endpoint", "waiting", ["k1", "k2"], 2, "backend"),
                      pip("k4", "Wire the screen", "waiting", ["k3", "k5"], 3, "screens"), pip("c1", "Code review", "waiting", ["k4"], 4, "reviewer", "check")]
        self.tasks[1]["started"] = IN_MIN(12)
        self.tasks[2]["started"] = IN_MIN(4)
        self.signin = [pip("s1", "Sign-in endpoint", "merged", by="backend"), pip("s2", "Sign-in screen", "merged", by="screens"),
                       pip("v1", "Code review", "running", ["s1", "s2"], 2, "reviewer", "check"), pip("c2", "Words on the screens", "review", ["s1", "s2"], 2, "words", "check")]
        self.signin[2]["started"] = IN_MIN(7)
        self.cookie = [pip("f1", "Secure cookie flags", "failed", by="backend"), pip("f2", "Sign out everywhere", "held", by="screens")]
        self.cookie[0]["error"] = "The session ended without a change: “You changed no file.”"
        self.cookie[1]["note"] = "reserve · after 18:00"
        self.nodes = [
            node("register", "passkey", "WebAuthn register", "working", 1, stage="implementation", tasks=self.tasks, progress={"done": 0, "total": 6}, usd=1.8,
                 plan_estimate={"usd_low": 2.0, "usd_high": 3.0}, results=[dict(RESULT)]),
            node("signin", "passkey", "Sign in with the passkey", "working", 1, stage="checking", tasks=self.signin, progress={"done": 2, "total": 4}, usd=2.9,
                 plan_estimate={"usd_low": 2.0, "usd_high": 4.0}, results=[dict(CHECK)], round=2),
            node("cookie", "passkey", "Session cookie flags", "working", 1, stage="implementation", tasks=self.cookie, progress={"done": 0, "total": 2}, usd=0.35,
                 waits={"kind": "night", "ref": "", "title": "", "until": "2099-01-01T01:00"}),
            node("recovery", "passkey", "Recovery codes", "plan", 2, needs_you="plan", plan_estimate={"usd_low": 1.0, "usd_high": 2.0},
                 tasks=[pip("r1", "Codes table", "ready"), pip("r2", "Show the codes once", "waiting", ["r1"], 2, "screens"), pip("r3", "Code review", "waiting", ["r2"], 3, "reviewer", "check")]),
            node("second", "passkey", "Passkey on a second device", "asks", 2, needs_you="asks",
                 asked=[{"ask": "Should a lost phone sign out every passkey?", "choices": ["Yes, every passkey", "Only the lost phone’s", "Ask the person"], "pick": 1, "why": "less to undo",
                         "by": member("reviewer", "Reviewer", ELDER, "check")}]),
            node("ratelimit", "passkey", "Rate-limit the sign-in", "reading", 2),
            node("pagewords", "passkey", "Words of the sign-in page", "proposed", 2, needs_you="proposal"),
            node("magic", "passkey", "Magic link if the passkey fails", "raw", 3, queue="night"),
            node("log", "passkey", "A log of every sign-in", "raw", 3),
            node("button", "passkey", "Passkey button on the page", "done", 1, stage="done", progress={"done": 3, "total": 3}, folded=True),
            node("creds", "passkey", "Where the credentials are kept", "done", 1, stage="done", progress={"done": 2, "total": 2}, folded=True),
            node("prices", "pricing", "Prices from the billing settings", "done", 1, stage="done", folded=True)]
        for n in self.nodes:                                                        # a goal's element and flag (spec 50 §2.3, §2.4)
            n["element"] = ELEMENT.get(n["slug"], "")
            n["flag"] = None
        self.flag(self.node_of("button"), at="2026-10-14T10:00:00", tasks=4, first_time=4, usd=2.1)
        for at, n in enumerate(self.nodes):                                        # the Board's goals: what a press on a row or a stop answers about
            self.ideas[n["slug"]] = self.idea(n["slug"], n["title"], n["state"], at, track=n["goal"], queue=n["queue"], start_at=n["start_at"])
        self.party = {"passkey": [member("taskmaster", "Taskmaster", ELDER, "lead", "needs", "plan"), member("backend", "Backend", HEAD, "build", "needs", "failed"),
                                  member("screens", "Screens", ELF, "build", "work"), member("reviewer", "Reviewer", ELDER, "check", "work"),
                                  member("words", "Words", GNOME, "check", "next")],
                      "pricing": [member("taskmaster", "Taskmaster", ELDER, "lead")], "weekly": [member("taskmaster", "Taskmaster", ELDER, "lead")]}
        self.gate_doc = {"into": "dev", "main": "main", "same": False, "commits": 5, "files": 12,
                         "ideas": [{"slug": "button", "title": "Passkey button on the page", "goal": "passkey", "tasks": 3},
                                   {"slug": "creds", "title": "Where the credentials are kept", "goal": "passkey", "tasks": 2}]}
        self.extra_needs: list[dict] = []

    def node_of(self, slug):
        return next(n for n in self.nodes if n["slug"] == slug)

    def flag(self, n, at, tasks=3, first_time=3, usd=1.0, by="gate"):
        """A goal's flag, as `ideas.map` carries it (spec 50 §2.4): raised when the gate took it into main."""
        n["flag"] = {"at": at, "by": by, "commit": "abc", "tasks": tasks, "first_time": first_time, "usd": usd, "days": 3}

    def find(self, a):
        return next(t for n in self.nodes if n["slug"] == a["slug"] for t in n["tasks"] if t["id"] == a["task"])

    def leave(self, name, a):
        """A merge, a send back and a drop take the result off the list and move its task, as the host does."""
        n = next(n for n in self.nodes if n["slug"] == a["slug"])
        n["results"] = [r for r in n["results"] if r["task"] != a["task"]]
        self.find(a)["state"] = {"ideas.merge": "merged", "ideas.back": "running", "ideas.drop_task": "dropped"}[name]
        return self.bump({"ok": True})

    def needs_you(self):
        base = {"goal": "passkey", "priority": "high", "blocks": False, "at": "2026-10-18T09:00:00"}
        return [base | {"kind": "failed", "idea": "cookie", "title": "Session cookie flags", "text": "Secure cookie flags: The session ended", "blocks": True},
                base | {"kind": "plan", "idea": "recovery", "title": "Recovery codes", "text": "Plan ready · 3 tasks"},
                base | {"kind": "asks", "idea": "second", "title": "Passkey on a second device", "text": "Should a lost phone sign out every passkey?",
                        "questions": ["Should a lost phone sign out every passkey?"]},
                base | {"kind": "proposal", "idea": "pagewords", "title": "Words of the sign-in page", "text": "One page of words would settle it."},
                *self.extra_needs]

    def map_doc(self):
        goals = [{"slug": g["slug"], "title": g["title"], "short": g["title"], "priority": g["priority"], "state": g["state"], "done_when": ["a person signs in without a password"],
                  "ideas": sum(1 for n in self.nodes if n["goal"] == g["slug"]), "done": sum(1 for n in self.nodes if n["goal"] == g["slug"] and n["state"] == "done"),
                  "usd": 6.4 if g["slug"] == "passkey" else None, "leader": LEAD, "team": [], "party": self.party.get(g["slug"], []),
                  "today": {"merged": 3, "usd": 1.1}, "brief": "Builds the sign-in: the API, the database and the screens" if g["slug"] == "passkey" else "",
                  "flags": sum(1 for n in self.nodes if n["goal"] == g["slug"] and n["flag"]),
                  "waits_main": sum(1 for n in self.nodes if n["goal"] == g["slug"] and n["state"] == "done" and not n["flag"])}
                 for g in self.goals.values() if g["slug"] != "general"]
        return {"goals": goals, "nodes": self.nodes, "edges": [], "rev": self.rev}

    def snapshot(self):
        snap = super().snapshot()
        if self.ops:
            snap["state"]["ops_rev"] = 1
        return snap

    def handle(self, name, a):
        if name in ("ideas.merge", "ideas.back", "ideas.drop_task"):
            self.log.append((name, a))
            return self.leave(name, a)
        if name == "ideas.agents":
            got = super().handle(name, a)
            by = {r["role"]: r for r in got["roles"]}
            for slug, nm, head in (("backend", "Backend", HEAD), ("screens", "Screens", ELF), ("reviewer", "Reviewer", ELDER), ("words", "Words", GNOME)):
                by[slug] = {"role": slug, "name": nm, "model": "warrior", "max_parallel": 2, "builtin": False, "spend_today": 0, "chips": [], "kinds": ["code"] if slug != "reviewer" else [],
                            "usd_task": self.usd_task.get(slug), "head": head, "harness": self.harness.get(slug, {"id": "claude", "name": "Claude"}), "week": self.week.get(slug),
                            **({"check_week": self.check_week[slug]} if slug in self.check_week else {})}
            return {**got, "roles": list(by.values())}
        if name == "ops.list":
            return {"templates": [], "runs": []}
        if name == "ideas.add":                                  # a new goal gets its party's least used element (spec 50 §2.3)
            got = super().handle(name, a)
            used = [n["element"] for n in self.nodes if n["goal"] == a["track"] and n["state"] != "done" and n["element"]]
            return {**got, "element": idea_element.pick(used)}
        if name == "ideas.flags":
            self.log.append((name, a))
            return {"flags": [], "goals": sorted([{"slug": n["slug"], "title": n["title"], "short": n["short"], "goal": n["goal"], "element": n["element"], **n["flag"]}
                                                    for n in self.nodes if n["flag"]], key=lambda f: f["at"], reverse=True)}
        return super().handle(name, a)


def _settle(pg):
    pg.wait_for_function("() => !document.querySelector('.is-leaving') && !document.querySelector('.is-drawn')", timeout=WAIT_MS)


@pytest.fixture
def arena(gui):
    pg, host, errors = _open(gui, host=ArenaHost(), ready=".arena-ptop")
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def test_the_regions_in_their_order_and_sizes_at_1440_by_900_with_no_page_scroll(arena):
    pg, host = arena
    sizes = {"top bar": (".shell-top", 32), "party's top line": (".arena-ptop", 32), "Parties": (".arena-ptop__deck", 28), "party line": (".arena-ibar__bar", 36),
             "party row": (".arena-team", 64), "bottom row": (".arena-stops", 64)}
    for name, (css, h) in sizes.items():
        assert box(pg, css)["height"] == h, name
    assert pg.locator(".arena-tabs").count() == 0 and pg.locator(".shell-top [role=tablist], .shell-top .arena-ptop").count() == 0      # no parties in the top bar (spec 52 §3.1)
    assert all(box(pg, css)["y"] == 32 for css in (".shell-main", ".arena-today", ".arena-left", ".arena-field"))      # the main row starts right under the top bar
    wide = {"strip": (".arena-today", 40), "left column": (".arena-left", 248), "results": (".arena-look", 312), "gate": (".arena-gatebox", 312), "limits": (".arena-limits", 312)}
    for name, (css, w) in wide.items():
        assert box(pg, css)["width"] == w, name
    assert box(pg, ".arena-goal__main")["height"] == 42 and box(pg, ".arena-new")["height"] == 72                 # a goal's row 42; the New goal pile 60 + 12 of padding
    assert box(pg, ".arena-new__pile")["width"] == 44 and box(pg, ".arena-new__pile")["height"] == 60
    landmarks = [("navigation", "Today"), ("region", "Leader"), ("region", "Goals"), ("region", "Party"), ("region", "The party at work"),
                 ("complementary", "Waits for your look"), ("region", "Waits for you"), ("region", "What is left of your AI tools")]
    seen = [pg.get_by_role(role, name=name, exact=True) for role, name in landmarks]
    assert [s.count() for s in seen] == [1] * len(landmarks)                                              # each one, in the order of the page
    handles = [s.element_handle() for s in seen]
    assert all(pg.evaluate("([a, b]) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING)", [a, b]) for a, b in zip(handles, handles[1:]))
    by = {name: s.bounding_box() for (_r, name), s in zip(landmarks, seen)}
    assert by["Today"]["x"] < by["Leader"]["x"] and box(pg, ".arena-ptop")["y"] + 32 <= by["Leader"]["y"]          # the party's top line over the leader
    assert by["Leader"]["y"] < by["Goals"]["y"] and by["Leader"]["x"] == by["Goals"]["x"]                  # the leader over its goals, in the left column
    ibar, party, cols, look, gate = box(pg, ".arena-ibar__bar"), by["Party"], by["The party at work"], by["Waits for your look"], box(pg, ".arena-gatebox")
    assert ibar["y"] + ibar["height"] <= party["y"] and party["y"] + party["height"] <= cols["y"]           # the party line, the party row, the columns under it
    assert party["x"] == cols["x"] and party["y"] == gate["y"] and gate["x"] == look["x"] and gate["y"] + gate["height"] <= look["y"]            # the gate at the row's right end, over the results
    assert look["y"] == cols["y"] and look["x"] > cols["x"] + cols["width"] - 1                              # the results beside the columns
    stops, limits = by["Waits for you"], by["What is left of your AI tools"]
    assert abs(stops["y"] - limits["y"]) <= 1 and stops["y"] >= cols["y"] + cols["height"] and limits["x"] > stops["x"]       # the bottom row: the stops, the limits at its right
    assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    assert not pg.evaluate("document.documentElement.scrollHeight > document.documentElement.clientHeight")
    assert box(pg, ".arena-left")["x"] == 40 and box(pg, ".arena-field")["x"] == 288                      # strip 40, left 248
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.locator(".arena-member[data-agent=backend]").hover()
        pg.screenshot(path=str(SHOTS / "desktop-one-window-1440x900.png"))


def test_the_partys_deck_its_cards_the_count_of_the_others_operations_and_the_pick_kept(gui):
    host = ArenaHost()
    host.ops = True
    host.extra_needs = [{"kind": "op", "op": "r1", "title": "Weekly report", "text": "Waits at your check", "goal": "", "idea": "", "priority": "normal", "blocks": False, "at": "x"}]
    pg, host, errors = _open(gui, host=host, ready=".arena-ptop")
    try:
        line = pg.locator(".arena-ptop")
        assert line.locator(".arena-ptop__name").inner_text() == "Sign in with a passkey"
        count = line.locator(".arena-ptop__count")
        assert count.inner_text() == "2/11" and count.get_attribute("title") == "2 of 11 goals done"             # its done goals of all its goals
        assert line.locator(".ork-meter").count() == 0 and "%" not in line.inner_text()                        # a party has no end: no meter, no %
        assert line.locator(".arena-ptop__work .ork-sign.work").count() == 1                                   # at work: orkUI's sign
        deck = line.locator(".arena-ptop__deck")
        assert deck.locator(".ork-count").count() == 0                                                         # no count of stops anywhere (spec 54 §2.4); the label says it for a screen reader
        assert deck.get_attribute("aria-label") == "Parties: Sign in with a passkey shown, 1 stop waits in the other parties"
        cards = _parties(pg).locator(".arena-spread__card")
        assert [c.get_attribute("data-goal") for c in cards.all()] == ["passkey", "pricing", "weekly", "@operations", ""]      # the Board's order: priority, then the person's
        first = cards.first
        assert first.get_attribute("aria-label") == "Sign in with a passkey, 2 of 11 goals done, at work, shown"
        assert "Builds the sign-in" in first.get_attribute("title")                                            # what it is for, in its tooltip
        assert first.locator(".ork-flag, .arena-flag").count() == 0 and first.locator(".ork-count").count() == 0      # no verdict's flag; the shown party's stops not counted
        assert cards.nth(1).locator(".arena-deck__dot").count() == 0 and "1/1 done" in cards.nth(1).inner_text()      # no stop: no dot
        assert cards.nth(3).locator(".arena-deck__dot").count() == 1 and cards.locator(".ork-count").count() == 0      # Operations' row: a dot where its count was
        cards.nth(3).click()
        pg.locator(".arena-ops").wait_for(timeout=WAIT_MS)                                                    # Operations: its view in the field, its rows below
        assert pg.locator(".arena-hc[data-kind=op]").count() == 1 and pg.locator(".arena-hc").count() == 5 and pg.locator(".arena-ptop__deck .ork-count").count() == 0   # the passkey party's lie in the hand too
        _show_goal(pg, "passkey")
        pg.reload()                                                                                         # the pick is kept per device
        pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
        _show_goal(pg, "pricing")
        pg.reload()
        pg.locator(".arena[data-goal=pricing]").wait_for(timeout=WAIT_MS)
        into = pg.get_by_role("button", name=re.compile("results go into"))                                    # the results' branch: a quiet line under the gate's button
        assert into.is_visible() and into.inner_text().strip() == "results go into dev" and into.evaluate("e => e.closest('.arena-gatebox') !== null")
        assert box(pg, ".arena-into")["y"] > box(pg, ".arena-gate__btn")["y"] + box(pg, ".arena-gate__btn")["height"] - 1
        into.click()                                                                                          # the same dialog as the results' own Merge into
        assert pg.get_by_role("dialog", name=re.compile("Merge into")).is_visible()
        pg.keyboard.press("Escape")
        plus = _parties(pg).get_by_role("button", name="New party", exact=True)                               # the last card, after Operations: its dialog (spec 50 §3.7)
        assert plus.get_attribute("title").startswith("One of yours") and plus.locator(".ork-icon").count() == 1
        plus.click()
        pg.get_by_role("dialog", name="New party").wait_for(timeout=WAIT_MS)
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_member_two_numbers_marks_signs_and_peek(arena):
    pg, host = arena
    team = pg.get_by_role("region", name="Party")
    assert [m.get_attribute("data-agent") for m in team.locator(".arena-member").all()] == ["backend", "screens", "reviewer", "words"]      # builders, then checkers
    assert team.locator(".arena-seat").count() == 0                                                         # a party's free seats are not drawn
    backend = team.locator(".arena-member[data-agent=backend]")
    nums = backend.locator(".arena-num")
    assert nums.nth(0).inner_text() == "5/1" and nums.nth(1).inner_text() == "$0.38"                          # runs, sent back; the week's average once 5 finished
    assert nums.nth(0).get_attribute("title") == "5 runs this week, 1 sent back to redo"
    assert nums.nth(1).get_attribute("title") == "The average of its 5 runs this week, at API prices, not your bill"
    screens = team.locator(".arena-member[data-agent=screens]")
    assert screens.locator(".arena-num").nth(1).inner_text() == "≈$0.30"                                        # 2 finished: its level's price, with ≈
    assert screens.locator(".arena-num").nth(1).get_attribute("title") == "About: too few runs yet, the price of its level, at API prices, not your bill"
    reviewer = team.locator(".arena-member[data-agent=reviewer]")
    assert reviewer.locator(".arena-num").nth(0).inner_text() == "6/2" and reviewer.locator(".arena-num").nth(0).get_attribute("title") == "6 checks this week, 2 caught something"
    lead = pg.locator(".arena-hero .arena-member")
    assert lead.locator(".arena-num").nth(0).inner_text() == "6/1" and lead.locator(".arena-num").nth(0).get_attribute("title") == "6 plans this week, 1 made again"
    assert lead.locator(".arena-num").nth(1).inner_text() == "$0.12" and lead.locator("img.ork-race__head").evaluate("e => e.getBoundingClientRect().width") == 36   # the leader's head is a member's
    marks = backend.locator("img.ork-mark")                                                                   # the tool's mark and the level's chevrons, with their tooltips
    assert [m.get_attribute("src") for m in marks.all()] == ["/ds/orkui/marks/rank-2.png", "/ds/orkui/marks/harness-claude.png"]
    assert backend.locator("img.arena-mark--h").get_attribute("title") == "Runs on Claude" and backend.locator("img.arena-mark--r").get_attribute("title") == "Seasoned: its level"
    assert screens.locator("img.arena-mark--h").get_attribute("src") == "/ds/orkui/marks/harness-codex.png" and screens.locator("img.arena-mark--h").get_attribute("title") == "Runs on Codex"
    assert reviewer.locator("img.arena-mark--r").get_attribute("src") == "/ds/orkui/marks/rank-3.png" and team.locator(".arena-member[data-agent=words] img.arena-mark--r").get_attribute("src").endswith("rank-1.png")
    assert all(pg.evaluate("(src) => fetch(src).then((r) => r.ok)", m.get_attribute("src")) for m in marks.all())      # the marks are served
    assert backend.locator(".arena-sign .ork-sign.cross").count() == 1 and "danger" in backend.locator(".arena-sign").get_attribute("class")       # a failure: the cross on the danger ground
    assert backend.locator(".arena-sign").get_attribute("title") == "failed" and backend.locator(".arena-sign").inner_text() == ""            # the sign is drawn, never typed
    assert lead.locator(".arena-sign .ork-sign.alert").count() == 1 and "alert" in lead.locator(".arena-sign").get_attribute("class")          # plan ready: the alert sign on the alert ground
    assert screens.locator(".arena-sign .ork-sign.work").count() == 1 and team.locator(".arena-member[data-agent=words] .arena-sign").count() == 0   # at work: the work sign; next: none
    label = backend.get_attribute("aria-label")
    assert label.startswith("Backend, ork, Claude, Seasoned, failed, 5 runs this week") and "A click shows its work." in label
    assert box(pg, ".arena-member[data-agent=backend]")["height"] < 60 and box(pg, ".arena-member[data-agent=backend]")["width"] <= 200          # a small row
    peek = backend.locator("xpath=..").locator(".arena-peek")
    assert not peek.is_visible()
    backend.hover()                                                                                           # the peek: the whole face beside it
    assert peek.is_visible() and peek.get_attribute("aria-hidden") == "true" and peek.locator("button, a, input").count() == 0
    member_box, peek_box = backend.bounding_box(), peek.bounding_box()
    assert peek_box["y"] >= member_box["y"] + member_box["height"]                                            # it opens below the member: above it, the page would clip it
    pg.locator(".arena-hero .arena-member").hover()
    side, leader = pg.locator(".arena-hero .arena-peek").bounding_box(), pg.locator(".arena-hero .arena-member").bounding_box()
    assert side["x"] >= leader["x"] + leader["width"] and side["y"] >= 0                                       # the leader's opens beside it, into the field
    backend.hover()
    text = " ".join(peek.inner_text().split())
    assert "$0.38 a run" in text and "BUILDS" in text.upper() and "Backend" in text and "ork · Claude · Seasoned" in text and "0 of 2 at once" in text and "Takes: code" in text
    assert peek.locator(".ork-stat").count() == 2 and peek.locator(".ork-gem").count() == 1 and "runs/sent back" in text
    pg.mouse.move(5, 5)
    reviewer.focus()                                                                                           # focus shows it too
    assert reviewer.locator("xpath=..").locator(".arena-peek").is_visible() and "Checks:" in reviewer.locator("xpath=..").locator(".arena-peek").inner_text()


def _keys(pg, agent):
    """The cards of a member's column, in the order they lie: [<goal>/<task>]."""
    return pg.locator(f".arena-stack[data-agent={agent}] .arena-task").evaluate_all("els => els.map((e) => e.dataset.key)")


def test_solo_one_member_s_rows_across_the_field_in_the_same_order_and_back(arena):
    pg, host = arena
    before = _keys(pg, "backend")
    assert before == ["register/k2", "cookie/f1", "register/k5"]                                              # now: the register stack (k2 in front), cookie; next: k5
    pg.locator(".arena-member[data-agent=backend]").click()
    solo = pg.get_by_role("group", name="Only Backend’s tasks")
    solo.wait_for(timeout=WAIT_MS)
    assert solo.locator(".arena-task").evaluate_all("els => els.map((e) => e.dataset.key)") == before         # nothing is reordered
    assert pg.locator(".arena-stack[data-agent]").count() == 0                                                 # the others are gone
    first = solo.locator(".arena-task").first.bounding_box()
    member_box = pg.locator(".arena-member[data-agent=backend]").bounding_box()
    assert first["y"] >= member_box["y"] + member_box["height"]                                                # it starts under the party row, at the top
    assert first["width"] <= 104 and solo.locator(".arena-phase").first.bounding_box()["width"] > 600           # its rows lie across the field's whole width
    assert [r.get_attribute("data-row") for r in solo.locator(".arena-phase").all()] == ["now", "next"]
    row = solo.locator(".arena-phase").first
    assert len(row.locator(".arena-task").all()) == 2 and row.locator(".arena-task").nth(1).bounding_box()["x"] > row.locator(".arena-task").nth(0).bounding_box()["x"] + 100   # side by side
    assert "only Backend’s" in pg.locator(".arena-look__head").inner_text() and pg.locator(".arena-result[data-task=k1]").count() == 1       # the right column: only its results
    assert pg.locator('.arena-result[data-task="c2"]').count() == 0
    assert pg.locator(".arena-member[data-agent=backend]").get_attribute("aria-pressed") == "true"
    pg.get_by_role("button", name="Show everyone’s work").click()
    assert pg.locator(".arena-stack[data-agent]").count() == 4 and pg.locator(".arena-result").count() == 2
    pg.locator(".arena-member[data-agent=backend]").click()
    pg.keyboard.press("Escape")                                                                                # Esc shows all again
    pg.locator(".arena-stack[data-agent]").first.wait_for(timeout=WAIT_MS)
    pg.locator(".arena-hero .arena-member").click()                                                            # the leader's solo: its goals in Planning the same way
    lead = pg.get_by_role("group", name="Only Taskmaster’s work")
    assert [t.get_attribute("data-slug") for t in lead.locator(".arena-task").all()] == ["recovery", "second", "pagewords", "ratelimit", "magic", "log"]
    assert lead.locator(".arena-task").first.locator(".ork-elem").count() == 1                                  # a goal per card, its element top left
    pg.keyboard.press("Escape")


def test_the_columns_hold_rows_by_phase_the_merged_count_and_what_waits_for_a_task(arena):
    pg, host = arena
    assert _keys(pg, "screens") == ["register/k3", "cookie/f2", "register/k4"] and _keys(pg, "reviewer") == ["signin/v1", "register/c1"]     # now, now, later; now, later
    assert _keys(pg, "words") == ["signin/c2"]
    rows = lambda agent: pg.locator(f".arena-stack[data-agent={agent}] .arena-phase").evaluate_all("els => els.map((e) => e.dataset.row)")      # noqa: E731
    assert rows("backend") == ["now", "next"] and rows("screens") == ["now", "later"] and rows("words") == ["now"]                # a row with nothing is not drawn
    labels = pg.locator(".arena-stack[data-agent=screens] .arena-phase__lbl")
    assert [l.text_content() for l in labels.all()] == ["now", "later"] and labels.first.evaluate("e => getComputedStyle(e).fontSize") == "10px"
    now, later = pg.locator(".arena-stack[data-agent=screens] .arena-phase.is-later"), pg.locator(".arena-stack[data-agent=screens] .arena-phase").first
    assert now.count() == 1 and "is-later" not in later.get_attribute("class")                                  # the rows after now are muted
    ys = [p.bounding_box()["y"] for p in pg.locator(".arena-stack[data-agent=screens] .arena-phase").all()]
    assert ys == sorted(ys) and len(set(ys)) == 2                                                              # top-down: now nearest the member
    member_box = pg.locator(".arena-member[data-agent=screens]").bounding_box()
    assert ys[0] > member_box["y"] + member_box["height"]                                                      # the party row is above the columns
    lit, muted = pg.locator(".arena-task[data-key='register/k3']"), pg.locator(".arena-task[data-key='register/k4']")
    assert lit.evaluate("e => getComputedStyle(e).backgroundColor") != muted.evaluate("e => getComputedStyle(e).backgroundColor")
    for t in pg.locator(".arena-stack .arena-task").all():                                                   # a name never runs into its state line
        name, foot = t.locator(".arena-task__name").bounding_box(), t.locator(".arena-task__foot").bounding_box()
        assert name["y"] + name["height"] <= foot["y"] + 0.5, t.inner_text()
        assert round(name["height"]) % 15 == 0, t.inner_text()                                                # whole lines only, none cut in half
    column = pg.locator(".arena-stack[data-agent=backend]")
    assert "1 in dev" in column.locator(".arena-stack__done").inner_text() and column.locator(".arena-stack__done .ork-sign.check").count() == 1       # what merged stays a count
    assert "1 in dev" in pg.locator(".arena-stack[data-agent=screens] .arena-stack__done").inner_text()
    assert [h.text_content() for h in pg.locator(".arena-cols__head .arena-lbl:not(.is-blank)").all()] == ["Implementation", "Checking"]            # over the first builder, the first checker
    running = pg.locator(".arena-task[data-key='register/k3']")
    assert "working 4 min" in running.inner_text() and running.locator(".ork-sign.work").count() == 0 and running.locator(".ork-elem.meadow").count() == 1
    assert "WebAuthn register" in running.locator(".arena-task__goal").inner_text() and "Register screen" in running.locator(".arena-task__name").inner_text()
    failed = column.locator(".arena-task[data-state=failed]")
    assert "failed" in failed.inner_text() and "You changed no file" in failed.get_attribute("title") and failed.locator(".ork-sign.cross").count() == 0   # the error in its tooltip
    assert "is-fail" in failed.locator("xpath=..").get_attribute("class")                                      # a failed stack has the danger edge
    held = pg.locator(".arena-stack[data-agent=screens] .arena-task[data-state=held]")
    assert "tonight · after 01:00" in held.inner_text() and held.locator(".ork-sign.night").count() == 0       # a hold for tonight: said by the foot, no clock on the card (spec 55 §2)
    assert column.locator(".arena-stk[data-goal=register] .arena-stk__n").inner_text() == "×2"                  # a stack of two: ×n on its corner
    pg.locator(".arena-task[data-key='register/k5']").hover()                                                  # hovering a card says what waits for it and what it waits for
    assert "1 waits for it" in pg.locator(".arena-task[data-key='register/k5']").inner_text()                   # k4 waits for k5
    k4, k2 = pg.locator(".arena-task[data-key='register/k4']"), pg.locator(".arena-task[data-key='register/k2']")
    assert "waits for Register endpoint" in k4.inner_text() and "is-after" in k4.get_attribute("class") and k4.locator(".ork-sign.before").count() == 1
    assert "is-before" in k2.get_attribute("class") and "1 waits for it" in k2.inner_text()                     # what k5 waits for: k2 shows; k1 lies under it
    pg.mouse.move(5, 5)
    assert "waits for it" not in pg.locator(".arena-task[data-key='register/k5']").inner_text()
    pg.locator(".arena-task[data-key='register/k5']").click()                                                  # a stack of one: a click opens the task in the drawer
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "task", "ref": "register/k5", "device": "desktop", "via": "map"}))
    pg.get_by_role("button", name="Close the drawer").click()                                                  # the drawer covers the right of the field: it goes, its tab stays
    pg.locator(".arena-task[data-key='signin/c2']").click()                                                    # in Review: its result
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "result", "ref": "signin/c2", "device": "desktop", "via": "map"}))


def test_waits_for_your_look_its_results_buttons_and_commands_and_no_alert_colour(arena):
    pg, host = arena
    look = pg.get_by_role("complementary", name="Waits for your look")
    assert look.locator(".ork-count").inner_text() == "2"
    results = look.locator(".arena-result")
    assert [r.get_attribute("data-task") for r in results.all()] == ["k1", "c2"]                                 # oldest first
    first, check = results.nth(0), results.nth(1)
    text = " ".join(first.inner_text().split())
    assert text.startswith("WebAuthn register Challenge store Backend 14 / 14 passed 14 files · $0.42") and first.locator(".arena-result__tests .ork-sign.check").count() == 1
    assert first.locator(".arena-result__idea .ork-elem.meadow").count() == 1                                    # its goal's element, before its name
    assert "Words" in check.inner_text() and "its check" in check.inner_text() and "Found 2: 1 fixed, 1 left" in check.inner_text()          # a check: its findings
    assert first.locator(".arena-link").inner_text() == "Challenge store"
    assert first.get_by_role("button", name="Merge into dev").is_enabled() and first.get_by_role("button", name="Send back").is_visible() and first.get_by_role("button", name="Drop…").is_visible()
    alert = pg.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-alert)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
    assert alert not in look.locator("*").evaluate_all("els => els.map((e) => getComputedStyle(e).color)")        # a result is not a signal
    assert pg.get_by_role("button", name="Last week").is_visible()                                                # the foot
    def again():                                                                                              # the host took the result off the list; the next one comes
        pg.mouse.move(5, 5)
        pg.locator(".arena-result[data-task=k1]").wait_for(state="detached", timeout=WAIT_MS)
        host.nodes[0]["results"] = [dict(RESULT)]
        host.nodes[0]["tasks"][0]["state"] = "review"
        host.bump({})
        pg.locator(".arena-result[data-task=k1]").wait_for(timeout=WAIT_MS)
        _settle(pg)
        return pg.locator(".arena-result[data-task=k1]")
    first.locator(".arena-link").click()                                                                       # its code, in the drawer
    _drawer(pg).locator(".shell-result").wait_for(timeout=WAIT_MS)
    pg.get_by_role("button", name="Close the drawer").click()
    first.get_by_role("button", name="Send back").click()
    first.get_by_label("Why you send it back, in one line").fill("Name it better")
    first.locator(".shell-actions__line button").click()
    assert _sent(pg, host, ("ideas.back", {"slug": "register", "task": "k1", "why": "Name it better"}))
    first = again()
    first.get_by_role("button", name="Drop…").click()
    pg.get_by_role("dialog", name="Drop this result?").get_by_role("button", name="Drop it").click()
    assert _sent(pg, host, ("ideas.drop_task", {"slug": "register", "task": "k1"}))
    first = again()
    first.get_by_role("button", name="Merge into dev").click()
    assert _sent(pg, host, ("ideas.merge", {"slug": "register", "task": "k1"}))
    check.get_by_role("button", name="Fix them").click()
    assert _calls(pg, host, "ideas.back", 2)[-1]["task"] == "c2"
    pg.mouse.move(5, 5)
    pg.get_by_text("Nothing waits for your look. Results come here as their tasks finish.").wait_for(timeout=WAIT_MS)       # empty


def test_the_gate_button_its_screen_and_the_one_press_that_merges_dev_into_main(arena):
    pg, host = arena
    gate = pg.locator(".arena-gate")
    button = gate.get_by_role("button", name="Merge dev into main")
    assert button.is_enabled() and "primary" in button.get_attribute("class") and "2 goals in dev wait for main" in gate.inner_text()
    button.click()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "gate", "ref": "", "device": "desktop", "via": "gate"}))
    view = _drawer(pg).locator(".arena-gateview")
    view.wait_for(timeout=WAIT_MS)
    assert "dev → main" in view.inner_text() and "2 goals in dev wait for main" in view.inner_text() and "In dev, not in main" in view.text_content()
    assert "Passkey button on the page" in view.inner_text() and "Sign in with a passkey" in view.inner_text()      # the goals, with their parties
    assert "5 commits" in view.inner_text() and "12 files" in view.inner_text() and "Nothing reaches main without you." in view.inner_text()
    assert "gate" in _drawer(pg).get_by_role("tab").first.inner_text().lower()
    view.get_by_role("button", name="Merge dev into main").click()
    assert _sent(pg, host, ("ideas.gate_merge", {}))
    pg.get_by_text("main has every goal of dev").wait_for(timeout=WAIT_MS)                                      # after: the drawer says so, the button is off
    assert view.get_by_role("button", name="Merge dev into main").is_disabled()
    assert gate.get_by_role("button", name="Merge dev into main").is_disabled() and "main is up to date" in gate.inner_text()
    host.gate_doc.update(same=True)                                                                           # one branch: no gate to draw
    host.bump({})
    pg.wait_for_function("() => !document.querySelector('.arena-gate__btn')", timeout=WAIT_MS)


def test_what_waits_for_you_a_fan_raised_on_hover_and_focus_each_kind_and_its_quick_answers(arena):
    pg, host = arena
    hand = pg.get_by_role("region", name="Waits for you")
    kinds = pg.locator(".arena-hc").evaluate_all("els => els.map((e) => e.dataset.kind)")
    assert kinds == ["failed", "plan", "asks", "proposal"]                                                      # urgency's order (spec 54 §2.3), a failed task in its row's place
    items = pg.locator(".arena-hc")
    assert items.nth(0).get_attribute("class").count("danger") == 1 and items.nth(1).get_attribute("class").count("alert") == 1             # the edge: danger, alert
    tops = {i.get_attribute("data-kind"): i.bounding_box() for i in items.all()}
    assert [k for k, _ in sorted(tops.items(), key=lambda kv: kv[1]["x"])] == ["asks", "failed", "plan", "proposal"]                    # the most urgent in the middle, the next to its right, then to its left
    assert tops["failed"]["y"] < tops["asks"]["y"] and tops["plan"]["y"] < tops["proposal"]["y"]                 # the middle ones higher
    rot = items.nth(0).evaluate("e => getComputedStyle(e).transform")
    assert rot != "none" and items.nth(1).evaluate("e => getComputedStyle(e).transform") != items.nth(0).evaluate("e => getComputedStyle(e).transform")        # each turned a little
    assert items.nth(0).bounding_box()["y"] + items.nth(0).bounding_box()["height"] > 900 and box(pg, ".arena-stops")["height"] == 64        # only the tops show
    plan = items.nth(1)
    top = plan.bounding_box()
    pg.mouse.move(top["x"] + top["width"] / 2, 880)                                                              # hover raises it whole, above the others
    pg.wait_for_function("(el) => el.getBoundingClientRect().height >= 240 && el.getBoundingClientRect().bottom < 900", arg=plan.element_handle(), timeout=WAIT_MS)
    assert plan.bounding_box()["width"] >= 156 and plan.evaluate("e => getComputedStyle(e).zIndex") == "50"
    assert plan.get_by_role("button", name="Start the work").is_visible() and plan.get_by_role("button", name="Open the plan").is_visible()
    assert "$1–2" in plan.locator(".ork-gem").inner_text() and "plan ready" in plan.inner_text().lower() and "2 tasks, 1 check" in plan.inner_text()
    pg.mouse.move(5, 5)
    pg.wait_for_function("(el) => el.getBoundingClientRect().bottom > 900", arg=plan.element_handle(), timeout=WAIT_MS)
    asks = items.nth(2)
    asks.locator(".arena-hc__open").focus()                                                                      # focus raises it too
    assert pg.evaluate("document.querySelector('.shell').scrollTop") == 0 and box(pg, ".shell-top")["y"] == 0     # and the window does not move to show it
    pg.wait_for_function("(el) => el.getBoundingClientRect().bottom < 900", arg=asks.element_handle(), timeout=WAIT_MS)
    assert "?" == asks.locator(".ork-gem").inner_text() and "“Should a lost phone sign out every passkey?”" in asks.inner_text() and asks.locator(".arena-hc__who img").count() == 1
    only = asks.get_by_role("button", name=re.compile("Only the lost phone"))
    assert "●" in only.inner_text() and "primary" in only.get_attribute("class") and asks.get_by_role("button", name="Yes, every passkey").get_attribute("class").count("primary") == 0
    only.click()
    assert _sent(pg, host, ("ideas.answer", {"slug": "second", "answers": ["Only the lost phone’s"]}))
    pg.locator(".ok-toast", has_text="Sent: the Taskmaster answers in a moment.").wait_for(timeout=WAIT_MS)
    pg.mouse.move(5, 5)
    _stop(pg, "plan").get_by_role("button", name="Start the work").click()
    assert _sent(pg, host, ("ideas.start", {"slug": "recovery", "via": "hand"}))
    _stop(pg, "failed").get_by_role("button", name="Start again").click()
    assert _sent(pg, host, ("ideas.start", {"slug": "cookie", "via": "hand"}))
    assert "Its goal’s tasks that are not merged or at Review run again" == _stop(pg, "failed").get_by_role("button", name="Start again").get_attribute("title")
    failed = _stop(pg, "failed")
    assert failed.locator(".ork-gem .ork-sign.cross").count() == 1 and "You changed no file" in failed.inner_text() and failed.locator(".arena-hc__who img").count() == 1
    failed.get_by_role("button", name="Open…").click()                                                          # the task's screen, with Drop and its confirmation
    _drawer(pg).get_by_role("button", name="Drop…").click()
    assert "Drop this task?" in pg.locator(".shell-task").inner_text()
    _drawer(pg).get_by_role("button", name="Drop it").click()
    assert _sent(pg, host, ("ideas.drop_task", {"slug": "cookie", "task": "f1"}))
    pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)                                  # a drop ends the thing: its tab goes, and the drawer with it
    _stop(pg, "proposal").get_by_role("button", name="Take: Words of the sign-in page").click()
    assert _sent(pg, host, ("ideas.proposal", {"slug": "pagewords", "take": True, "priority": "high"}))
    assert hand.get_by_role("button", name="Plan ready: Recovery codes").count() == 1


def test_a_plan_held_for_the_night_starts_now_and_a_to_do_opens_its_dialog(gui):
    host = ArenaHost()
    host.nodes[3]["start_at"] = "night"
    host.extra_needs = [{"kind": "todo", "idea": "recovery", "goal": "passkey", "title": "Recovery codes", "text": "SMTP_KEY", "priority": "high", "blocks": False, "at": "x",
                         "todo": {"id": "t1", "title": "SMTP_KEY", "kind": "secret", "why": "to send the codes", "choices": [], "steps": [], "accept": [], "done": False}}]
    pg, host, errors = _open(gui, host=host, ready=".arena-ptop")
    try:
        pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
        _stop(pg, "plan").get_by_role("button", name="Start now").click()
        assert _sent(pg, host, ("ideas.start_now", {"slug": "recovery", "via": "hand"}))
        todo = _stop(pg, "todo")
        assert todo.locator(".ork-gem").inner_text() == "·" and "SMTP_KEY" in todo.inner_text()
        todo.get_by_role("button", name="Open…").click()
        pg.get_by_role("dialog", name="SMTP_KEY").wait_for(timeout=WAIT_MS)
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_the_strip_marks_the_day_of_the_goal_and_a_click_opens_what_it_says(gui):
    host = ArenaHost()
    host.today_events = [
        {"at": "12:40", "mark": "✓", "tone": "ok", "words": "merged into dev", "title": "Sign-in screen", "goal": "passkey", "idea": "signin", "task": "s2", "open": {"kind": "result", "slug": "signin", "task": "s2"}},
        {"at": "12:10", "mark": "↺", "tone": "muted", "words": "sent back", "title": "Sign-in screen", "goal": "passkey", "idea": "signin", "task": "s2", "open": {"kind": "result", "slug": "signin", "task": "s2"}},
        {"at": "11:55", "mark": "✗", "tone": "danger", "words": "failed", "title": "Secure cookie flags", "goal": "passkey", "idea": "cookie", "task": "f1", "open": {"kind": "task", "slug": "cookie", "task": "f1"}},
        {"at": "11:00", "mark": "·", "tone": "muted", "words": "you answered", "title": "Prices", "goal": "pricing", "idea": "prices", "task": "", "open": {"kind": "idea", "slug": "prices"}},
        {"at": "10:30", "mark": "▸", "tone": "ink", "words": "the work started", "title": "WebAuthn register", "goal": "passkey", "idea": "register", "task": "", "open": {"kind": "idea", "slug": "register"}},
        {"at": "09:00", "mark": "✓", "tone": "ok", "words": "dev merged into main", "title": "dev → main", "goal": "", "idea": "", "task": "", "open": {"kind": "gate", "slug": ""}}]
    pg, host, errors = _open(gui, host=host, ready=".arena-ptop")
    try:
        pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
        strip = pg.get_by_role("navigation", name="Today")
        marks = strip.locator(".arena-hitem")
        what = lambda m: m.locator(".ork-sign").get_attribute("class").replace("ork-sign ", "") if m.locator(".ork-sign").count() else m.inner_text()      # noqa: E731
        assert [what(m) for m in marks.all()] == ["check", "↺", "cross", "▸", "check"]                         # this party's day and the gate's; newest at the top; orkUI's signs
        assert strip.locator(".ork-icon").count() == 1                                                          # a clock over them
        assert marks.nth(0).get_attribute("aria-label") == "12:40 · Sign-in screen · merged into dev"
        colours = marks.evaluate_all("els => els.map((e) => getComputedStyle(e).color)")
        assert colours[0] == colours[4] != colours[2] and colours[1] != colours[0]                               # ✓ success, ✗ danger, ↺ muted
        marks.nth(0).click()
        assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "result", "ref": "signin/s2", "device": "desktop", "via": "today"}))
        _drawer(pg).locator(".shell-result").wait_for(timeout=WAIT_MS)
        pg.get_by_role("button", name="Close the drawer").click()
        marks.nth(4).click()
        pg.locator(".arena-gateview").wait_for(timeout=WAIT_MS)
        pg.get_by_role("button", name="Close the drawer").click()
        _show_goal(pg, "pricing")
        assert [what(m) for m in strip.locator(".arena-hitem").all()] == ["·", "check"]                         # another party's day, and the gate's on every party
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_the_limits_inside_the_night_window_say_the_morning(gui):
    host = ArenaHost()
    host.reserve = {"share": 0.2, "night": True}
    pg, host, errors = _open(gui, host=host, ready=".arena-ptop")
    try:
        limits = pg.get_by_role("region", name="What is left of your AI tools")
        claude = limits.locator(".arena-limit[data-provider=claude]")
        assert claude.locator(".ork-crystals i.kept").count() == 2 and claude.locator(".ork-crystals i.on").count() == 4
        assert "hatched: kept for the morning" in limits.inner_text() and "kept for the morning" in claude.get_attribute("title")
        assert limits.locator(".arena-limit[data-provider=codex] .ork-crystals i.kept").count() == 0                # the reserve is Claude's only
        assert pg.evaluate("getComputedStyle(document.querySelector('.ork-crystals i.kept')).backgroundImage").startswith("repeating-linear-gradient")
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_the_drawer_opens_on_a_click_keeps_its_tabs_on_esc_and_holds_agents_and_files(gui):
    from tests.test_map_desktop_browser import MapHost
    pg, host, errors = _open(gui, host=MapHost(), ready=".arena-ptop")
    try:
        _show_goal(pg)
        assert pg.locator(".shell-drawer").count() == 0
        pg.locator(".arena-task[data-task=k4]").click()
        drawer = _drawer(pg)
        bb = drawer.bounding_box()
        assert abs(bb["width"] - 0.62 * 1440) < 3 and bb["x"] + bb["width"] == 1440 and bb["height"] > 800                 # 62 % of the window, from the right
        assert drawer.evaluate("e => getComputedStyle(e).borderLeftStyle") == "double"
        assert pg.locator(".arena-ptop").is_visible() and pg.locator(".arena-left").is_visible()                       # the window is still there, behind it
        pg.locator(".shell-top").get_by_role("button", name="Agents").click()
        assert "Add agent" in drawer.inner_text() and drawer.get_by_role("tab").count() == 2                        # Agents: today's pane, in a tab of the drawer
        pg.locator(".shell-top").get_by_role("button", name="Files").click()
        pg.locator(".shell-tree__row", has_text="notes.txt").wait_for(timeout=WAIT_MS)
        assert drawer.get_by_role("tab").count() == 3
        pg.keyboard.press("Escape")
        pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)
        pg.locator(".shell-top").get_by_role("button", name="Agents").click()
        assert _drawer(pg).get_by_role("tab").count() == 3                                                         # its tabs are kept
        pg.get_by_role("button", name="Close the drawer").click()
        pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_below_1024_the_columns_scroll_sideways_and_the_drawer_takes_the_window(gui):
    pg, host, errors = _open(gui, host=ArenaHost(), viewport={"width": 900, "height": 800}, ready=".arena-ptop")
    try:
        pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
        assert pg.locator(".arena-today").count() == 0 and box(pg, ".arena-left")["width"] == 200 and pg.locator(".arena-look").count() == 0
        play = pg.locator(".arena-play")
        assert play.evaluate("e => e.scrollWidth > e.clientWidth && getComputedStyle(e).overflowX") in (True, "auto")
        assert pg.locator(".arena-hc[data-kind=result]").count() == 2                                              # the results join the bottom row, after the stops
        assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        pg.locator(".arena-task[data-task=k3]").first.click()
        assert box(pg, ".shell-drawer")["width"] == 900
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_waiting_card_says_waits_for_n_with_the_before_sign_its_tooltip_names_the_tasks_and_no_card_or_tooltip_says_an_id(arena):
    """Spec 67 §3: *waits for 2* (one: *waits for <name>*) at the foot, the names in the tooltip, never an id."""
    pg, host = arena
    k5 = pg.locator(".arena-task[data-key='register/k5']")
    foot = k5.locator(".arena-task__foot")
    assert foot.inner_text().strip() == "waits for 2" and foot.locator(".ork-sign.before").count() == 1
    assert re.search(r"after [A-Z][^·]*, [A-Z]", k5.get_attribute("title")) and not re.search(r"\bk\d\b", k5.get_attribute("title"))        # its tooltip names the tasks
    assert not re.search(r"\bk\d\b", k5.get_attribute("aria-label"))
    for t in pg.locator(".arena-stack .arena-task").all():                                                    # no card, tooltip or label says an id
        said = " ".join([t.inner_text(), t.get_attribute("title") or "", t.get_attribute("aria-label") or ""])
        assert not re.search(r"\b(?:after|waits for) [a-z]\d\b", said), said
    assert pg.locator(".arena-task[data-key='register/k4'] .arena-task__foot").inner_text().strip() == "waits for 2"                          # k3 and k5
    assert pg.locator(".arena-task[data-key='register/c1'] .arena-task__foot").inner_text().strip() == "waits for Wire the screen"              # one: its name
