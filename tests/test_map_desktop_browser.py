"""The Map and the preview's tabs on the desktop (docs/specs/39-map.md §3–§4, Tests → B), in a real browser at 1 440 × 900 and
at 1 000 px against a stub host that answers `ideas.map` in §1's shape: the Map is the first tab, pinned, shown at start; goals
as sections, an idea under the ideas it depends on with a line between, each waiting node saying why; Tasks in waves; *new*;
a click opens a passing tab, a double-click or an edit keeps it; Esc closes the active tab; at most 12 tabs; tabs per project
kept after a reload; below 1 024 px no strip, Back and the Board's Map button."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os

import pytest

pytest.importorskip("playwright.sync_api")

from orkboard.realm.idea_words import short_of  # noqa: E402
from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import _show_goal, PARTY, PARTY_LINES, SHOTS, StubHost, _calls, _sent, box  # noqa: E402

pytestmark = pytest.mark.browser

NOW = dt.datetime.now().replace(microsecond=0)
ago = lambda hours: (NOW - dt.timedelta(hours=hours)).isoformat()      # noqa: E731  (naive local, as `ideas.touched_at`)
SHOP, BLOG = "/work/shop", "/work/blog"
FILES = {"README.md": "# Shop\n\nSells things.\n", "notes.txt": "one\ntwo\n"}


def key(path: str) -> str:
    """The tabs' storage key of a project (spec 39 §3.7)."""
    return "orkboard.tabs." + hashlib.sha1(path.encode()).hexdigest()[:12]


def pip(tid, title, state, after=(), wave=1, by="grunt", band="build"):
    return {"id": tid, "title": title, "state": state, "after": list(after), "tier": "warrior", "head": {"craft": "engineering", "race": "peon", "tier": "warrior"},
            "by": {"slug": by, "name": {"grunt": "Grunts", "reviewer": "Reviewer"}.get(by, by)}, "band": band, "wave": wave, "tag": "Code"}


def node(slug, goal, title, state, tier, **more):
    base = {"slug": slug, "goal": goal, "title": title, "short": short_of(title), "state": state, "queue": "", "held_until": "", "start_at": "", "priority": "normal",
            "size": "M", "risk": "low", "tier": tier, "depends_on": [], "waits_on": [], "waits": None, "needs_you": "",
            "progress": {"done": 0, "total": 0}, "tasks": [], "estimate": None, "by_itself": False, "folded": False, "updated": ago(30),
            "stage": "planning", "round": 1, "usd": None, "plan_estimate": None, "asked": [], "results": []}
    return base | more


LEAD = {"slug": "taskmaster", "name": "Taskmaster", "head": {"craft": "engineering", "race": "peon", "tier": "elder"}}
GRUNT_HEAD = {"craft": "engineering", "race": "peon", "tier": "warrior"}
RESULT = {"idea": "sync", "idea_title": "Sync ideas between the phone and the town", "task": "k3", "title": "Retry on a lost signal", "round": 1,
          "tests": {"passed": 20, "failed": 0, "failing": [], "tail": ""}, "diff": {"files": 14, "added": 30, "removed": 4}, "cost": 0.42, "conflict": "",
          "finished": "2026-10-20T10:00:00", "estimate": None, "over": None}


class MapHost(StubHost):
    """The shell's stub plus the Map (spec 48 §1), a project switcher and a Files tree."""

    def __init__(self):
        super().__init__()
        self.current = SHOP
        self.files = dict(FILES)
        self.ideas["growth"] = self.idea("growth", "Grow the list", "ready", 6, track="grow")
        for n in range(1, 14):
            self.ideas[f"i{n}"] = self.idea(f"i{n}", f"Idea {n}", "plan", 20 + n)
        self.tasks = [pip("k1", "Read the sync code", "merged"), pip("k2", "Add the queue", "running", ["k1"], 2),
                      pip("k3", "Retry on a lost signal", "review", ["k1"], 2), pip("k4", "Test it offline", "waiting", ["k2", "k3"], 3, "reviewer", "check")]
        self.nodes = [
            node("sync", "ship-sync", "Sync ideas between the phone and the town", "working", 1, progress={"done": 1, "total": 4}, stage="implementation",
                 tasks=self.tasks, by_itself=True, updated=ago(1), usd=0.84, plan_estimate={"usd_low": 1.0, "usd_high": 2.0}, results=[dict(RESULT)],
                 checks=[{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "waiting", "task": "k4", "skipped": False, "tier": "elder"}]),
            node("offline", "ship-sync", "Offline mode", "asks", 1, needs_you="asks", waits={"kind": "you", "ref": "", "title": "", "until": ""},
                 asked=[{"ask": "Which store first?", "choices": ["App Store", "Google Play"], "by": {**LEAD, "slug": "reviewer", "name": "Reviewer"}}],
                 checks=[{"by": "editor", "name": "Editor", "applies": True, "why": "", "state": "", "task": "", "skipped": False, "tier": "laborer"},
                         {"by": "seo", "name": "SEO", "applies": True, "why": "", "state": "", "task": "", "skipped": True, "tier": "laborer"}]),
            node("dark", "ship-sync", "Dark mode", "plan", 2, depends_on=["sync"], waits_on=["sync"], needs_you="plan", progress={"done": 0, "total": 3},
                 tasks=[pip("d1", "Dark palette", "waiting"), pip("d2", "Dark icons", "waiting", wave=1), pip("d3", "Check it", "waiting", ["d1"], 2, "reviewer", "check")],
                 waits={"kind": "you", "ref": "", "title": "", "until": ""}, estimate={"usd_low": 0.4, "usd_high": 1.2}, plan_estimate={"usd_low": 0.4, "usd_high": 1.2}),
            node("later", "ship-sync", "Cache the table", "ready", 2, updated=ago(1)),
            node("export", "ship-sync", "Export notes", "done", 1, folded=True, progress={"done": 3, "total": 3}, stage="done"),
            node("tags", "grow", "Tag the notes", "proposed", 1, needs_you="proposal", waits={"kind": "you", "ref": "", "title": "", "until": ""}),
            node("growth", "grow", "Grow the list", "ready", 2, depends_on=["tags"], waits_on=["tags"],
                 waits={"kind": "idea", "ref": "tags", "title": "Tag the notes", "until": ""}, checks=[{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "passed"},
                            {"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": True, "why": "", "state": "running"}]),
        ]
        self.edges = [{"from": "sync", "to": "dark"}, {"from": "tags", "to": "growth"}]
        self.extra_goal: dict = {}                    # more of the first goal's fields (its verdict)
        self.results_list = [dict(RESULT)]

    def results(self):
        return self.results_list

    def snapshot(self):
        snap = super().snapshot()
        snap["state"]["projects"] = {"current": self.current, "recent": [], "open": [
            {"path": p, "name": p.rsplit("/", 1)[1], "working": 0, "needs_you": 0, "review": 0} for p in (SHOP, BLOG)]}
        return snap

    def map_doc(self):
        mate = lambda slug, name, state, why="", band="build", head=GRUNT_HEAD: {"slug": slug, "name": name, "head": head, "band": band, "state": state, "why": why}      # noqa: E731
        goals = [{"slug": "grow", "title": "Grow installs", "priority": "high", "state": "ready", "done_when": ["weekly installs", "stars"],
                  "ideas": 2, "done": 0, "usd": None, "leader": LEAD, "today": {"merged": 0, "usd": 0.0},
                  "party": [{**LEAD, "band": "lead", "state": "needs", "why": "proposal"}, mate("product-designer", "Product designer", "next"),
                            mate("reviewer", "Reviewer", "free", band="check")],
                  "team": [{"slug": "product-designer", "name": "Product designer", "head": {"craft": "design", "race": "elf", "tier": "elder"}, "checks": False, "every": False},
                           {"slug": "reviewer", "name": "Reviewer", "head": {"craft": "engineering", "race": "peon", "tier": "elder"}, "checks": True, "every": True}]},
                 {"slug": "ship-sync", "title": "Ship sync", "priority": "normal", "state": "ready", "done_when": ["sync works offline"],
                  "ideas": 4, "done": 1, "usd": 12.4, "leader": LEAD, "today": {"merged": 2, "usd": 1.15}, "team": [],
                  "party": [{**LEAD, "band": "lead", "state": "needs", "why": "plan"}, mate("grunt", "Grunts", "work"), mate("reviewer", "Reviewer", "next", band="check"),
                            mate("editor", "Editor", "tonight", band="check"), mate("seo", "SEO", "free", band="check")]}]
        goals[0].update(self.extra_goal)
        return {"goals": goals, "nodes": sorted(self.nodes, key=lambda n: (n["goal"] != "grow", n["tier"])), "edges": self.edges, "rev": self.rev}

    def handle(self, name, a):
        if name == "ideas.map":
            self.log.append((name, a))
            return self.map_doc()
        if name == "ideas.flags":
            self.log.append((name, a))
            return {"flags": [{"goal": g["slug"], "title": g["title"], "short": g["title"], "by": g["verdict"]["by"], "at": g["verdict"]["at"],
                               "tally": g["verdict"].get("tally")} for g in self.map_doc()["goals"] if (g.get("verdict") or {}).get("met")]}
        if name == "ideas.party":
            self.log.append((name, a))
            return copy.deepcopy(PARTY)
        if name == "files.tree":
            self.log.append((name, a))
            return {"entries": [{"name": n, "path": n, "dir": False, "secret": False, "ignored": False} for n in self.files]}
        if name == "files.read":
            self.log.append((name, a))
            text = self.files[a["path"]]
            return {"path": a["path"], "kind": "markdown" if a["path"].endswith(".md") else "text", "text": text, "html": f"<p>{text}</p>",
                    "size": len(text), "mtime": 1.0}
        if name == "files.write":
            self.log.append((name, a))
            self.files[a["path"]] = a["text"]
            return {"mtime": 2.0}
        if name == "projects.use":
            self.log.append((name, a))
            self.current = a["path"]
            return self.bump({"ok": True})
        return super().handle(name, a)


def _open(gui, host=None, viewport=None, init="", ready=".map-goal", goal="ship-sync"):
    server, browser = gui
    host = host or MapHost()
    pg = browser.new_page(viewport=viewport or {"width": 1440, "height": 900})
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
    if init:
        pg.add_init_script(init)
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.wait_for_selector(ready, timeout=WAIT_MS)
    _show_goal(pg, goal)                              # the Board shows one goal, and so does the Map: most of the stub's ideas are Ship sync's
    return pg, host, errors


def seed(path, **state):
    """Storage the page starts with, written once (a reload keeps what the page wrote)."""
    return f"if (!localStorage.getItem({json.dumps(key(path))})) localStorage.setItem({json.dumps(key(path))}, {json.dumps(json.dumps(state))});"


@pytest.fixture
def mapped(gui):
    pg, host, errors = _open(gui)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def tab(pg, name):
    return pg.locator(".shell-tabstrip").get_by_role("tab", name=name)


def active_tab(pg):
    return pg.locator(".shell-ptab.is-on [role=tab]")


def card(pg, title):
    """An expanded idea's Open: the idea in the passing tab (a row expands first)."""
    return pg.locator(".map-idea", has_text=title).get_by_role("button", name="Open", exact=True)


def passing(pg):
    return pg.locator(".shell-ptab.is-passing")


def kept(pg):
    return pg.locator(".shell-ptab:not(.is-passing):not(.is-pinned)")


def test_the_map_is_the_first_tab_pinned_shown_at_start_and_esc_does_not_close_it(mapped):
    pg, host = mapped
    tabs = pg.locator(".shell-tabstrip [role=tab]")
    assert tabs.count() == 1 and tabs.first.inner_text() == "Map" and tabs.first.get_attribute("aria-selected") == "true"
    assert pg.locator(".shell-tabstrip button[aria-label^=Close]").count() == 0                   # no ×
    assert "Open an idea, a task or a result" not in pg.locator(".shell-preview").inner_text()
    assert pg.locator(".shell-preview .map").is_visible()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "map", "ref": "", "device": "desktop"}))
    pg.keyboard.press("Escape")
    assert pg.locator(".shell-preview .map").is_visible() and active_tab(pg).inner_text() == "Map"
    pg.locator(".board-card", has_text="Dark mode").click()                                       # a tab opens, then Esc closes it, not the Map
    pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
    assert tabs.count() == 2
    pg.keyboard.press("Escape")
    pg.locator(".shell-preview .map").wait_for(timeout=WAIT_MS)
    assert tabs.count() == 1


def test_the_map_shows_one_goal_its_header_its_party_and_its_ideas_by_stage(mapped):
    pg, host = mapped
    assert pg.locator(".map-goal").count() == 1 and pg.locator(".map-goal").get_attribute("data-goal") == "ship-sync"         # one goal
    head = pg.locator(".map-goal__head").inner_text()
    for words in ("Ship sync", "Normal", "25 %", "1 of 5 ideas done", "≈$12 so far", "today 2 merged · ≈$1.15", "done when sync works offline"):
        assert words in head, words
    party = pg.locator(".map-party__member")                                                         # the whole party, each with its state
    assert [" ".join(m.inner_text().split()) for m in party.all()] == [
        "Taskmaster plan ready", "Grunts at work ↻", "Reviewer next", "Editor tonight", "SEO free"]
    assert [m.get_attribute("class") for m in party.all()].count("map-party__member is-needs") == 1       # only the one the work stopped on
    assert party.first.get_attribute("data-state") == "needs"
    assert [li.get_attribute("data-slug") for li in pg.locator(".map-ideas > li").all()] == ["sync", "offline", "dark", "later"]   # trail order
    assert [s for s in ("sync", "offline", "dark") if pg.locator(f".map-idea[data-slug={s}]").count()] == ["sync", "offline", "dark"]   # at work or waiting: expanded
    row = pg.locator(".map-row[data-slug=later]")
    assert row.count() == 1 and "Planning · ready" in row.inner_text() and "new" not in row.inner_text()                 # the rest: one line each
    assert pg.locator(".map-row[data-slug=export]").count() == 0                                          # done: folded
    pg.get_by_role("button", name="Done (1)").click()
    assert "in dev · waits for main" in pg.locator(".map-row[data-slug=export]").inner_text()
    assert "3 of 3 tasks in dev" in pg.locator(".map-row[data-slug=export]").inner_text()
    row.click()                                                                                          # a row expands in place
    pg.locator(".map-idea[data-slug=later]").wait_for(timeout=WAIT_MS)
    assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")


def test_a_goal_s_flag_is_in_its_header_when_its_leader_accepts_it(gui):
    host = MapHost()
    host.extra_goal = {"verdict": {"met": True, "by": "Growth"}}
    pg, host, errors = _open(gui, host, goal="grow")
    grow = pg.locator(".map-goal[data-goal=grow]")
    grow.locator(".trail-end.is-met").wait_for(timeout=WAIT_MS)
    assert "accepted by Growth" in grow.locator(".map-goal__head").inner_text()
    pg.close()
    assert not errors, "\n".join(errors)


def test_the_goal_picker_switches_the_goal_and_the_device_keeps_it(mapped):
    pg, host = mapped
    pick = pg.get_by_label("Show another goal")
    assert pick.input_value() == "ship-sync" and pick.locator("option").count() == 2
    pick.select_option("grow")
    pg.locator(".map-goal[data-goal=grow]").wait_for(timeout=WAIT_MS)
    assert pg.locator(".map-goal").count() == 1 and pg.locator(".map-idea[data-slug=tags]").count() == 1      # a proposal waits for the person: expanded
    assert pg.get_by_label("Goal", exact=True).input_value() == "grow"                                         # the Board shows the same goal
    pg.reload()
    pg.locator(".map-goal[data-goal=grow]").wait_for(timeout=WAIT_MS)
    assert pg.locator(".map-goal").count() == 1


def test_an_expanded_idea_has_its_stage_track_lanes_waves_stacks_and_questions(mapped):
    pg, host = mapped
    sync = pg.locator(".map-idea[data-slug=sync]")
    now = sync.locator(".map-track__stage.is-now")                                                      # the stage track
    track = sync.locator(".map-track").text_content()
    assert now.text_content() == "Implementation" and "✓" in track and "Checking" in track
    lanes = sync.locator(".map-lane")                                                                    # only the builders with tasks in the plan
    assert lanes.count() == 1 and "Grunts" in lanes.first.inner_text() and "at work" in lanes.first.inner_text()
    assert lanes.first.locator(".map-lane__head.is-needs").count() == 0                                  # nobody stopped here: no alert
    assert [c.text_content() for c in sync.locator(".map-field__col").all()] == ["Wave 2"]                  # k1 merged: gone; the check is Checking's
    stack = sync.locator(".map-stack")
    assert stack.count() == 1 and stack.locator(".map-stack__count").inner_text() == "2"                 # two tasks of one agent in one wave
    stack.hover()
    items = sync.locator(".map-stack__item")
    items.first.wait_for(timeout=WAIT_MS)
    assert [" ".join(i.inner_text().split()) for i in items.all()] == ["Add the queue working", "Retry on a lost signal in Review"]
    pg.keyboard.press("Escape")
    items.first.wait_for(state="detached", timeout=WAIT_MS)
    assert pg.locator(".shell-preview .map").is_visible()                                                # Esc closed the list, not the Map
    stack.locator("button").first.focus()                                                                # focus opens it too
    sync.locator(".map-stack__item", has_text="Retry on a lost signal").click()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "result", "ref": "sync/k3", "device": "desktop", "via": "map"}))
    tab(pg, "Map").click()
    stack = pg.locator(".map-idea[data-slug=sync] .map-stack")
    stack.locator("button").first.focus()                                                                # focus opens it as well
    pg.locator(".map-stack__item").first.wait_for(timeout=WAIT_MS)
    pg.keyboard.press("Escape")
    # a checker's task not run yet: its × spares the run; the checks a plan will hold before it is made
    pending = pg.get_by_label("Checks of Offline mode")
    pending.get_by_role("button", name="Skip the check: Editor").click()
    assert _sent(pg, host, ("ideas.check_skip", {"slug": "offline", "by": "editor"}))
    pending.get_by_role("button", name="Take the check again: SEO").click()
    assert _sent(pg, host, ("ideas.check_skip", {"slug": "offline", "by": "seo", "skip": False}))
    # Planning: the leader's lane holds the plan and the members' questions, each wearing the head of who asks
    ask = pg.locator(".map-idea[data-slug=offline] .map-ask")
    assert ask.count() == 1 and ask.get_attribute("aria-label") == "Reviewer asks: Which store first?" and ask.locator("img.ork-race__head").count() == 1
    assert pg.locator(".map-idea[data-slug=offline] .map-field--plan .map-lane").count() == 1
    dark = pg.locator(".map-idea[data-slug=dark]")
    lead = dark.locator(".map-lane__head")
    assert "Taskmaster" in lead.inner_text() and lead.get_attribute("class").endswith("is-needs")         # the alert: the leader, for a plan
    assert "2 tasks, 1 check" in dark.locator(".map-plan").inner_text() and "plan ready" in dark.locator(".map-plan").inner_text()
    # the Map asks again when the board moves, and a merged task leaves the field
    before = len(_calls(pg, host, "ideas.map"))
    host.nodes[0]["tasks"] = [pip("k1", "Read the sync code", "merged"), pip("k2", "Add the queue", "running", ["k1"], 2),
                              pip("k3", "Retry on a lost signal", "merged", ["k1"], 2), pip("k4", "Test it offline", "waiting", ["k2", "k3"], 3, "reviewer", "check")]
    host.nodes[0]["progress"] = {"done": 2, "total": 4}
    host.nodes[0]["results"] = []
    host.bump({})
    leaving = pg.locator(".map-idea[data-slug=sync] .map-taskcard-pair.map-leaving")
    leaving.wait_for(timeout=WAIT_MS)                                                                  # it moves up once and fades
    assert "in dev" in leaving.inner_text()
    pg.wait_for_function("() => !document.querySelector('.map-leaving')", timeout=WAIT_MS)
    assert pg.locator(".map-idea[data-slug=sync] .map-stack").count() == 0 and "2 of 4 tasks in dev" in pg.locator(".map-idea[data-slug=sync] .map-card-frame").inner_text()
    assert len(_calls(pg, host, "ideas.map")) > before


def test_new_marks_what_moved_since_the_map_was_last_looked_at_and_is_gone_after(gui):
    seen = seed(SHOP, tabs=[], active="map", seen=ago(2), folded=[])
    pg, host, errors = _open(gui, init=seen)
    try:
        assert "new" in pg.locator(".map-row[data-slug=later]").inner_text()                           # updated an hour ago, looked at two hours ago
        pg.locator(".board-card", has_text="Dark mode").click()
        pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
        tab(pg, "Map").click()                                                                     # looked at again: the time moved
        pg.locator(".map-row[data-slug=later]").wait_for(timeout=WAIT_MS)
        assert "new" not in pg.locator(".map-row[data-slug=later]").inner_text()
        assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "map", "ref": "", "device": "desktop"}))
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_a_click_on_a_node_opens_a_passing_tab_another_replaces_it_and_a_double_click_keeps_it(mapped):
    pg, host = mapped
    card(pg, "Dark mode").click()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "idea", "ref": "dark", "device": "desktop", "via": "map"}))
    pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
    assert passing(pg).count() == 1 and "Dark mode" in passing(pg).inner_text()
    assert passing(pg).locator("[role=tab]").evaluate("e => getComputedStyle(e).fontStyle") == "italic"
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 2
    tab(pg, "Map").click()
    assert pg.locator(".map-idea[data-slug=sync]").is_visible()
    card(pg, "Offline mode").click()                                                               # replaces the passing tab
    pg.locator(".shell-ptab.is-passing", has_text="Offline mode").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 2 and "Dark mode" not in pg.locator(".shell-tabstrip").inner_text()
    passing(pg).locator("[role=tab]").dblclick()                                                   # kept: upright, stays
    assert passing(pg).count() == 0 and kept(pg).count() == 1
    assert kept(pg).locator("[role=tab]").evaluate("e => getComputedStyle(e).fontStyle") == "normal"
    tab(pg, "Map").click()
    card(pg, "Dark mode").click()
    pg.locator(".shell-ptab.is-passing", has_text="Dark mode").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 3                                   # Offline stays beside the new passing one
    pg.get_by_role("button", name="Keep Dark mode").click()                                        # Keep, as the button
    assert passing(pg).count() == 0 and kept(pg).count() == 2


def test_editing_a_file_keeps_its_tab_and_unsaved_changes_ask_before_esc_closes_it(mapped):
    pg, host = mapped
    pg.get_by_role("tab", name="Files").click()
    pg.locator(".shell-tree__row", has_text="notes.txt").click()
    pg.locator(".shell-code").wait_for(timeout=WAIT_MS)
    assert passing(pg).count() == 1
    pg.get_by_role("button", name="Edit", exact=True).click()
    pg.get_by_label("Editor").fill("one\ntwo\nthree\n")
    pg.wait_for_selector(".shell-ptab:not(.is-passing):not(.is-pinned)", timeout=WAIT_MS)          # an edit keeps the passing tab
    assert passing(pg).count() == 0 and "notes.txt" in kept(pg).inner_text()
    active_tab(pg).focus()
    pg.keyboard.press("Escape")
    dlg = pg.get_by_role("dialog", name="Unsaved changes")                                         # asks first
    dlg.wait_for(timeout=WAIT_MS)
    dlg.get_by_role("button", name="Keep editing").click()
    assert kept(pg).count() == 1
    pg.keyboard.press("Escape")
    pg.get_by_role("dialog", name="Unsaved changes").get_by_role("button", name="Discard changes").click()
    pg.locator(".shell-preview .map").wait_for(timeout=WAIT_MS)
    assert kept(pg).count() == 0 and host.files["notes.txt"] == "one\ntwo\n"


def test_a_file_saved_from_its_tab_and_opening_what_has_a_tab_shows_that_tab(mapped):
    pg, host = mapped
    pg.get_by_role("tab", name="Files").click()
    pg.locator(".shell-tree__row", has_text="README.md").click()
    pg.locator(".shell-md").wait_for(timeout=WAIT_MS)
    pg.locator(".shell-ptab.is-on [role=tab]").dblclick()
    tab(pg, "Map").click()
    card(pg, "Dark mode").click()
    pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 3
    pg.locator(".shell-tree__row", has_text="README.md").click()                                   # already has a tab: shown, not added
    pg.locator(".shell-md").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 3 and "README.md" in active_tab(pg).inner_text()
    assert passing(pg).count() == 1                                                                # the passing one is still Dark mode's


def test_esc_the_cross_and_a_middle_click_close_tabs_and_the_tab_to_the_left_is_shown(mapped):
    pg, host = mapped
    for title in ("Dark mode", "Offline mode", "Sync ideas"):
        tab(pg, "Map").click()
        card(pg, title).click()
        pg.locator(".shell-ptab.is-passing", has_text=title).wait_for(timeout=WAIT_MS)
        passing(pg).locator("[role=tab]").dblclick()
    assert kept(pg).count() == 3 and "Sync ideas" in active_tab(pg).inner_text()
    pg.get_by_role("button", name="Close Offline mode").click()                                    # a tab that is not shown goes, the shown one stays
    assert kept(pg).count() == 2 and "Sync ideas" in active_tab(pg).inner_text()
    pg.keyboard.press("Escape")                                                                    # the shown one goes: the tab to its left
    pg.wait_for_function("() => !document.querySelector('.shell-ptab[data-tab^=\"idea:sync\"]')")
    assert "Dark mode" in active_tab(pg).inner_text()
    tab(pg, "Dark mode").click(button="middle")
    pg.wait_for_function("() => document.querySelectorAll('.shell-tabstrip [role=tab]').length === 1")
    assert active_tab(pg).inner_text() == "Map"


def test_the_arrow_keys_move_between_tabs_and_enter_shows_one(mapped):
    pg, host = mapped
    card(pg, "Dark mode").click()
    pg.locator(".shell-ptab.is-passing", has_text="Dark mode").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip").get_attribute("role") == "tablist"
    active_tab(pg).focus()
    pg.keyboard.press("ArrowLeft")
    assert pg.evaluate("document.activeElement.textContent.trim()") == "Map"
    pg.keyboard.press("Enter")
    pg.locator(".shell-preview .map").wait_for(timeout=WAIT_MS)
    assert active_tab(pg).inner_text() == "Map"
    pg.keyboard.press("ArrowRight")
    assert "Dark mode" in pg.evaluate("document.activeElement.textContent")
    pg.keyboard.press("End")
    pg.keyboard.press("Enter")
    pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)


def test_a_13th_tab_closes_the_oldest_kept_one_and_says_so(mapped):
    pg, host = mapped
    for n in range(1, 14):
        pg.evaluate("""async (slug) => { const m = await import(document.querySelector('link[href$="shell.css"]').href.replace('shell.css', 'store.js'));
          m.showIdea(slug, { keep: true }); }""", f"i{n}")
        pg.locator(".shell-ptab.is-on", has_text=f"Idea {n}").wait_for(timeout=WAIT_MS)
    tabs = pg.locator(".shell-tabstrip [role=tab]")
    assert tabs.count() == 13                                                                      # the Map and 12 others
    assert "closed the oldest tab: Idea 1" in pg.locator("body").inner_text()
    names = [t.get_attribute("title") for t in tabs.all()][1:]
    assert names == [f"Spec: Idea {n}" for n in range(2, 14)]                                      # Idea 1 went, the others stay in order


def test_tabs_come_back_after_a_reload_and_each_project_has_its_own(mapped):
    pg, host = mapped
    card(pg, "Offline mode").click()
    pg.locator(".shell-ptab.is-passing", has_text="Offline mode").wait_for(timeout=WAIT_MS)
    passing(pg).locator("[role=tab]").dblclick()
    tab(pg, "Map").click()
    card(pg, "Dark mode").click()
    pg.locator(".shell-ptab.is-passing", has_text="Dark mode").wait_for(timeout=WAIT_MS)
    pg.reload()
    pg.locator(".shell-ptab.is-on", has_text="Dark mode").wait_for(timeout=WAIT_MS)                # which tabs, which is active, which is passing
    assert kept(pg).count() == 1 and "Offline mode" in kept(pg).inner_text() and passing(pg).count() == 1
    pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
    stored = json.loads(pg.evaluate(f"localStorage.getItem({json.dumps(key(SHOP))})"))
    assert [t["p"]["slug"] for t in stored["tabs"]] == ["offline", "dark"] and stored["active"] == "idea:dark::"

    pg.locator(".shell-proj__btn").click()                                                         # another project: its own tabs, the Map stays
    pg.locator(f".shell-proj__one[data-path='{BLOG}']").click()
    pg.wait_for_function("() => document.querySelectorAll('.shell-tabstrip [role=tab]').length === 1")
    pg.locator(".shell-preview .map").wait_for(timeout=WAIT_MS)
    assert active_tab(pg).inner_text() == "Map"
    pg.get_by_label("Show another goal").select_option("grow")
    card(pg, "Tag the notes").click()
    pg.locator(".shell-ptab.is-passing", has_text="Tag the notes").wait_for(timeout=WAIT_MS)
    pg.locator(".shell-proj__btn").click()
    pg.locator(f".shell-proj__one[data-path='{SHOP}']").click()
    pg.locator(".shell-ptab.is-on", has_text="Dark mode").wait_for(timeout=WAIT_MS)
    assert kept(pg).count() == 1 and "Tag the notes" not in pg.locator(".shell-tabstrip").inner_text()


def test_a_tab_whose_idea_is_gone_says_so_with_close(gui):
    ghost = {"kind": "idea", "slug": "ghost"}
    pg, host, errors = _open(gui, init=seed(SHOP, tabs=[{"p": ghost, "kept": True, "title": "Ghost idea"}], active="idea:ghost::", seen="", folded=[]), ready=".shell-ptab")
    try:
        pg.get_by_text("This idea is gone").wait_for(timeout=WAIT_MS)
        assert not [a for n, a in host.log if n == "ideas.page" and a.get("slug") == "ghost"]       # not asked for
        pg.get_by_role("button", name="Close", exact=True).click()
        pg.locator(".shell-preview .map").wait_for(timeout=WAIT_MS)
        assert active_tab(pg).inner_text() == "Map" and pg.locator(".shell-ptab:not(.is-pinned)").count() == 0
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_no_goal_says_so_with_new_goal(gui):
    host = MapHost()
    host.nodes, host.edges = [], []
    host.map_doc = lambda: {"goals": [], "nodes": [], "edges": [], "rev": host.rev}
    server, browser = gui
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    try:
        pg.get_by_text("No goals yet").wait_for(timeout=WAIT_MS)
        pg.locator(".shell-preview").get_by_role("button", name="New goal").click()
        assert pg.get_by_role("dialog", name="New goal").is_visible()
    finally:
        pg.close()


def test_at_1000_px_no_strip_the_preview_full_screen_back_closes_it_and_the_map_has_a_button(gui):
    errors: list[str] = []
    server, browser = gui
    host = MapHost()
    pg = browser.new_page(viewport={"width": 1000, "height": 800})
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    try:
        _show_goal(pg)
        pg.wait_for_selector(".board-card", timeout=WAIT_MS)
        assert pg.locator(".shell-tabstrip").is_hidden() and pg.locator(".shell-preview").is_hidden()
        pg.locator(".board-card", has_text="Dark mode").click()
        pg.locator(".shell-preview.is-open").wait_for(timeout=WAIT_MS)
        shown = box(pg, ".shell-preview")
        assert shown["x"] == 0 and shown["width"] == 1000 and pg.locator(".shell-tabstrip").is_hidden()
        pg.get_by_role("button", name="Back", exact=True).click()
        assert pg.locator(".board-card").first.is_visible() and pg.locator(".shell-preview").is_hidden()
        pg.get_by_role("button", name="Map", exact=True).click()                                    # the Board's Map button
        pg.locator(".map-goal").first.wait_for(timeout=WAIT_MS)
        assert box(pg, ".shell-preview")["width"] == 1000 and pg.locator(".map-idea[data-slug=dark]").is_visible()
        assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        card(pg, "Offline mode").click()                                                            # a node opens its idea on the full screen
        pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
        pg.get_by_role("button", name="Back", exact=True).click()
        assert pg.locator(".map-idea[data-slug=dark]").is_visible()                                 # Back from an idea returns to the Map
        pg.get_by_role("button", name="Back", exact=True).click()
        assert pg.locator(".shell-preview").is_hidden() and pg.locator(".board-card").first.is_visible()
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_an_idea_opened_from_the_board_or_needs_you_says_where_it_was_opened_from(mapped):
    """Spec 39 §6: an open is logged with `via`, so the Map's share can be told from the Board's and Needs you's."""
    pg, host = mapped

    def opened_via(via):
        for _ in range(WAIT_MS // 50):
            if any(name == "ideas.log" and a.get("what") == "idea" and a.get("via") == via for name, a in host.log):
                return True
            pg.wait_for_timeout(50)
        return False
    board_card = pg.locator(".board-card").first
    board_card.wait_for(timeout=WAIT_MS)
    board_card.click()
    assert opened_via("board")
    need = pg.locator(".board-need").filter(has_not=pg.locator("[data-kind^=op]")).first
    if need.count() and need.get_attribute("data-kind") in ("plan", "failed", "proposal", None):
        need.click()
        assert opened_via("needs")


def test_the_party_line_says_each_members_state_and_a_member_opens_its_agent(mapped):
    pg, host = mapped
    pg.get_by_label("Show another goal").select_option("grow")
    party = pg.locator(".map-party")
    party.wait_for(timeout=WAIT_MS)
    assert [" ".join(m.inner_text().split()) for m in party.locator(".map-party__member").all()] == ["Taskmaster proposed", "Product designer next", "Reviewer free"]
    assert party.locator("img.ork-race__head").count() == 3
    assert pg.locator(".map-party__member.is-needs").count() == 1
    party.get_by_role("button", name="Product designer").click()
    assert pg.get_by_role("dialog").is_visible()
    pg.keyboard.press("Escape")
    row = pg.locator(".map-row[data-slug=growth] .map-row__btn")
    assert "checks 1/2 passed" in row.get_attribute("title")                                            # a row says its checks on hover
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-map-team-1440x900.png"))


def test_a_row_and_a_task_show_their_short_names_on_two_lines_with_the_title_in_their_label(gui):
    host = MapHost()
    host.nodes[3] = {**host.nodes[3], "short": "Cache"}
    host.nodes[0] = {**host.nodes[0], "short": "Sync", "tasks": [{**t, "short": f"T{t['id']}"} for t in host.nodes[0]["tasks"]]}
    pg, host, errors = _open(gui, host)
    row = pg.locator(".map-row[data-slug=later] .map-row__btn")
    assert row.locator(".map-row__title").inner_text() == "Cache" and "Cache the table" in row.get_attribute("aria-label")
    task = pg.locator(".map-stack .map-taskcard").first
    assert task.get_attribute("title").startswith("2 tasks") and task.locator(".map-taskcard__title").inner_text() == "Tk2"
    assert task.locator(".map-taskcard__title").evaluate("e => getComputedStyle(e).webkitLineClamp") == "2"
    assert pg.get_by_label("Goal", exact=True).locator("option").first.get_attribute("title")           # the goal select keeps the title on its options
    pg.close()
    assert not errors, "\n".join(errors)


def test_the_idea_s_card_starts_the_work_and_merges_sends_back_and_drops_results_but_never_into_main(mapped):
    pg, host = mapped
    card = pg.locator(".map-idea[data-slug=sync] .map-card-frame")                                      # Implementation: Waits for your look
    assert "Implementation" in card.inner_text() and "1 of 4 tasks in dev" in card.inner_text()
    assert "≈$0.84 so far · plan ≈$1–2" in " ".join(card.inner_text().split())
    assert "waits for your look" in card.inner_text().lower() and "20 / 20 passed" in card.inner_text() and "14 files" in card.inner_text()
    assert "main" not in card.get_by_role("button").all_inner_texts() and card.get_by_role("button", name="Merge into dev").is_visible()
    assert card.evaluate("e => getComputedStyle(e).borderTopStyle") == "double"                           # orkUI's double frame
    card.get_by_role("button", name="Send back").first.click()
    card.get_by_label("Why you send it back, in one line").fill("Retry less often")
    card.locator(".shell-actions__line button").click()
    assert _sent(pg, host, ("ideas.back", {"slug": "sync", "task": "k3", "why": "Retry less often"}))
    card.get_by_role("button", name="Drop…").click()
    pg.get_by_role("dialog").get_by_role("button", name="Drop it").click()
    assert _sent(pg, host, ("ideas.drop_task", {"slug": "sync", "task": "k3"}))
    card.get_by_role("button", name="Merge into dev").click()
    assert _sent(pg, host, ("ideas.merge", {"slug": "sync", "task": "k3"}))
    # Planning with a plan waiting: Start the work and Open the plan
    dark = pg.locator(".map-idea[data-slug=dark] .map-card-frame")
    assert "Planning" in dark.inner_text() and dark.get_by_role("button", name="Merge into dev").count() == 0
    dark.get_by_role("button", name="Open the plan").click()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "plan", "ref": "dark", "device": "desktop", "via": "map"}))
    tab(pg, "Map").click()
    pg.locator(".map-idea[data-slug=dark] .map-card-frame").get_by_role("button", name="Start the work").click()
    assert _sent(pg, host, ("ideas.start", {"slug": "dark", "via": "map"}))


def test_no_review_column_the_gate_stays_in_needs_you_and_the_alert_is_only_where_the_work_stopped(mapped):
    pg, host = mapped
    assert pg.locator(".shell-review").count() == 0 and pg.locator("[aria-label=Review]").count() == 0
    task = pg.locator(".map-idea[data-slug=sync] .map-stack .map-taskcard")
    pg.locator(".map-idea[data-slug=sync] .map-stack").hover()
    review_item = pg.locator(".map-idea[data-slug=sync] .map-stack__item", has_text="in Review")
    assert review_item.count() == 1 and review_item.evaluate("e => getComputedStyle(e).color") == pg.locator(".map-idea[data-slug=sync] .map-stack__item", has_text="working").evaluate("e => getComputedStyle(e).color")
    sync_alerts = pg.locator(".map-idea[data-slug=sync] .is-needs, .map-idea[data-slug=sync] .is-failed")
    assert sync_alerts.count() == 0                                                                    # a result waiting is no signal
    host.nodes[0]["tasks"][1]["state"] = "failed"
    host.bump({})
    pg.locator(".map-idea[data-slug=sync] .map-stack .map-taskcard.is-failed").wait_for(timeout=WAIT_MS)   # a failed task: its card in danger
    assert task.count() == 1


def test_under_reduced_motion_a_merged_task_leaves_without_moving(gui):
    server, browser = gui
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    host = MapHost()
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    _show_goal(pg)
    pg.locator(".map-idea[data-slug=sync] .map-stack").wait_for(timeout=WAIT_MS)
    host.nodes[0]["tasks"][2]["state"] = "merged"
    host.nodes[0]["results"] = []
    host.bump({})
    pg.locator(".map-idea[data-slug=sync] .map-stack").wait_for(state="detached", timeout=WAIT_MS)
    assert pg.locator(".map-leaving").count() == 0
    pg.close()


# -- spec 42 B: the flag raised once, its tally and Flags -------------------------------------------------------------

TALLY = {"ideas": 7, "results": 23, "first_time": 19, "usd": 38.4, "days": 9}
MET = {"met": True, "by": "Product manager", "at": "2026-10-18T10:00:00", "tally": TALLY}


def flags_key(path: str) -> str:
    return key(path).replace("orkboard.tabs.", "orkboard.flags.")


def with_list(slugs, path=SHOP):
    """The flags this device raised, written once (a reload keeps what the page wrote)."""
    k = json.dumps(flags_key(path))
    return f"if (!localStorage.getItem({k})) localStorage.setItem({k}, {json.dumps(json.dumps(slugs))});"


def met_host():
    host = MapHost()
    host.extra_goal = {"verdict": MET}
    return host


def test_a_met_goal_not_in_the_list_is_raised_once_and_its_slug_kept(gui):
    pg, host, errors = _open(gui, met_host(), goal="grow", init=with_list([]), ready=".trail-end.is-met")
    flag = pg.locator(".map-goal[data-goal=grow] .trail-end__flag")
    flag.wait_for(timeout=WAIT_MS)
    assert pg.locator(".is-raising").count() == 1 and flag.evaluate("e => getComputedStyle(e).animationName") == "map-flag-raise"
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "flag", "ref": "grow", "device": "desktop"}))
    assert json.loads(pg.evaluate(f"localStorage.getItem({json.dumps(flags_key(SHOP))})")) == ["grow"]
    pg.wait_for_function("document.querySelectorAll('.is-raising').length === 0", timeout=WAIT_MS)       # it moved once
    pg.reload()
    pg.locator(".trail-end.is-met").wait_for(timeout=WAIT_MS)
    pg.wait_for_timeout(300)
    assert pg.locator(".is-raising").count() == 0 and len(_calls(pg, host, "ideas.log", at_least=1)) and \
        [a for n, a in host.log if n == "ideas.log" and a.get("what") == "flag"] == [{"event": "opened", "what": "flag", "ref": "grow", "device": "desktop"}]
    pg.close()
    assert not errors, "\n".join(errors)


FAR = "{ const sheet = new CSSStyleSheet(); sheet.replaceSync('.trail-end { margin-top: 3000px }'); document.adoptedStyleSheets = [sheet]; }"      # a constructed sheet: the phone's CSP has no inline style
FLAG_LOGS = lambda host: [a for n, a in host.log if n == "ideas.log" and a.get("what") == "flag"]    # noqa: E731


def test_a_flag_whose_trail_is_out_of_sight_waits_for_it_and_is_raised_once_when_it_comes_into_view(gui):
    pg, host, errors = _open(gui, met_host(), goal="grow", init=with_list([]) + FAR, ready=".trail-end.is-met")
    flag = pg.locator(".map-goal[data-goal=grow] .trail-end__flag")
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")                   # the page is visible, the trail is not
    pg.wait_for_timeout(400)
    assert pg.locator(".is-raising").count() == 0 and not FLAG_LOGS(host)
    assert json.loads(pg.evaluate(f"localStorage.getItem({json.dumps(flags_key(SHOP))})")) == []
    flag.scroll_into_view_if_needed()
    pg.wait_for_function("document.querySelectorAll('.is-raising').length === 1", timeout=WAIT_MS)
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    pg.wait_for_timeout(300)
    assert FLAG_LOGS(host) == [{"event": "opened", "what": "flag", "ref": "grow", "device": "desktop"}]            # one `opened`, not more
    pg.close()
    assert not errors, "\n".join(errors)


def test_under_reduced_motion_nothing_moves_and_the_slug_is_kept_all_the_same(gui):
    server, browser = gui
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    pg.add_init_script(with_list([]))
    host = met_host()
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.wait_for_selector(".trail-end.is-met", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "flag", "ref": "grow", "device": "desktop"}))
    assert pg.locator(".is-raising").count() == 0
    assert pg.locator(".map-goal[data-goal=grow] .trail-end__flag").evaluate("e => getComputedStyle(e).animationName") == "none"
    assert json.loads(pg.evaluate(f"localStorage.getItem({json.dumps(flags_key(SHOP))})")) == ["grow"]
    pg.close()


def test_a_device_with_no_list_raises_nothing_and_adds_every_met_goal(gui):
    pg, host, errors = _open(gui, met_host(), goal="grow", ready=".trail-end.is-met")
    pg.wait_for_timeout(500)
    assert pg.locator(".is-raising").count() == 0
    assert json.loads(pg.evaluate(f"localStorage.getItem({json.dumps(flags_key(SHOP))})")) == ["grow"]
    assert not [a for n, a in host.log if n == "ideas.log" and a.get("what") == "flag"]
    pg.close()
    assert not errors, "\n".join(errors)


def test_the_tally_stays_under_a_met_flag_and_a_goal_not_met_has_none(gui):
    host = met_host()
    pg, host, errors = _open(gui, host, goal="grow", init=with_list(["grow"]), ready=".trail-end.is-met")
    tally = pg.locator(".map-goal[data-goal=grow] .trail-end__tally")
    assert " ".join(tally.inner_text().split()) == "7 ideas · 23 results · 19 the first time · ≈$38 · 9 days"
    assert pg.locator(".map-goal[data-goal=ship-sync] .trail-end__tally").count() == 0
    host.extra_goal = {"verdict": {**MET, "tally": {**TALLY, "usd": None, "days": None}}}
    host.bump({})
    pg.wait_for_function("document.querySelector('.trail-end__tally').textContent === '7 ideas · 23 results · 19 the first time'", timeout=WAIT_MS)
    pg.close()
    assert not errors, "\n".join(errors)


def test_flags_opens_with_its_rows_and_a_row_opens_the_goal(gui):
    pg, host, errors = _open(gui, met_host(), goal="grow", init=with_list(["grow"]), ready=".trail-end.is-met")
    fold = pg.get_by_role("button", name="Flags (1)")
    assert fold.get_attribute("aria-expanded") == "false" and not [1 for n, _a in host.log if n == "ideas.flags"]     # closed at first: not asked for
    fold.click()
    row = pg.locator(".map-flag")
    row.wait_for(timeout=WAIT_MS)
    assert " ".join(row.inner_text().split()) == "Grow installs met, says Product manager · 18 October 7 ideas · 23 results · 19 the first time · ≈$38 · 9 days"
    row.click()
    pg.locator(".shell-ptab.is-on[data-tab='goal:grow::']").wait_for(timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "idea", "ref": "goal:grow", "device": "desktop", "via": "flags"}))
    pg.locator(".shell-tabstrip").get_by_role("tab", name="Map").click()
    assert pg.get_by_role("button", name="Flags (1)").get_attribute("aria-expanded") == "true"        # remembered with the folds
    pg.reload()
    pg.locator(".trail-end.is-met").wait_for(timeout=WAIT_MS)
    assert pg.get_by_role("button", name="Flags (1)").get_attribute("aria-expanded") == "true"
    pg.close()
    assert not errors, "\n".join(errors)


def test_a_met_goal_s_row_in_flags_has_what_the_party_did_closed_at_first(gui):
    """Spec 43 B: the same fold under a flag's row."""
    pg, host, errors = _open(gui, met_host(), goal="grow", init=with_list(["grow"]), ready=".trail-end.is-met")
    pg.get_by_role("button", name="Flags (1)").click()
    pg.locator(".map-flag").wait_for(timeout=WAIT_MS)
    fold = pg.locator(".map-flags__list .shell-party")
    assert fold.get_attribute("open") is None and not [1 for n, _a in host.log if n == "ideas.party"]
    fold.locator("summary").click()
    pg.wait_for_function("() => document.querySelectorAll('.map-flags__list .shell-party li').length === 4", timeout=WAIT_MS)
    assert [" ".join(t.split()) for t in fold.locator("li").all_inner_texts()] == PARTY_LINES
    assert _sent(pg, host, ("ideas.party", {"goal": "grow"}))
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "party", "ref": "grow", "device": "desktop"}))
    pg.close()
    assert not errors, "\n".join(errors)
