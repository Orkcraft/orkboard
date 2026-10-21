"""What the Map was and the drawer's tabs on the desktop (docs/specs/39-map.md §3–§4, spec 49 §4–§5, §9, spec 50 §3, Tests → B), in a real browser at
1 440 × 900 against a stub host that answers `ideas.map` in §1's shape: the parties are the top bar's switch, the party's goals are the left column's rows, its
tasks the party's columns, its results a column; a click opens a passing tab in the drawer, a double-click or an edit keeps it; Esc puts the drawer away and
keeps its tabs; at most 12 tabs; tabs per project kept after a reload. (A party has no flag of its own now: the goals' flags are tests/test_arena_decks_desktop_browser.py's.)"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json

import pytest

pytest.importorskip("playwright.sync_api")

from orkboard.realm.idea_words import short_of  # noqa: E402
from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import _show_goal, PARTY, StubHost, _calls, _sent  # noqa: E402

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
        self.ideas["later"] = self.idea("later", "Cache the table", "ready", 7)
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


def _open(gui, host=None, viewport=None, init="", ready=".arena-gtab", goal="ship-sync"):
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
    if goal:
        _show_goal(pg, goal)                          # the window shows one goal: most of the stub's ideas are Ship sync's
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


def row(pg, title):
    """A goal of the party shown, by its title: its row in the goals list."""
    return pg.locator(".arena-goal", has_text=title)


def opener(pg, title):
    """› on the goal's row (a goal not yet read: its row): a click opens it in the drawer."""
    return row(pg, title).locator(":scope > button:last-child")


def passing(pg):
    return pg.locator(".shell-ptab.is-passing")


def kept(pg):
    return pg.locator(".shell-ptab:not(.is-passing)")


def show(pg, kind, **args):
    """What the window opens, by its own store (a thing with no row to click)."""
    pg.evaluate("""async ([kind, args]) => { const m = await import(document.querySelector('link[href$="shell.css"]').href.replace('shell.css', 'store.js'));
      m.show({ kind, ...args }, args.opts || {}); }""", [kind, args])


def test_nothing_is_open_at_start_no_pinned_tab_and_esc_puts_the_drawer_away_and_keeps_its_tabs(mapped):
    pg, host = mapped
    assert pg.locator(".shell-drawer").count() == 0 and pg.locator(".shell-tabstrip").count() == 0          # no pinned Map tab: nothing opened, no drawer
    assert pg.locator(".arena").is_visible() and pg.locator(".arena-look").is_visible()                       # the field is never behind a tab
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "map", "ref": "", "device": "desktop"}))
    assert len(_calls(pg, host, "ideas.map")) >= 1
    pg.keyboard.press("Escape")                                                                               # nothing to close
    assert pg.locator(".arena").is_visible()
    opener(pg, "Cache the table").click()
    pg.locator(".shell-drawer .board-sec").first.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 1
    pg.keyboard.press("Escape")                                                                               # the drawer goes ...
    pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)
    assert json.loads(pg.evaluate(f"localStorage.getItem({json.dumps(key(SHOP))})"))["open"] is False         # ... and its tabs stay
    opener(pg, "Offline mode").click()                                                                           # opening anything brings it back
    pg.locator(".shell-ptab.is-on", has_text="Offline mode").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 1                                              # Cache the table's tab was the passing one: replaced


def test_the_party_switch_changes_the_party_and_the_device_keeps_it(mapped):
    pg, host = mapped
    tabs = pg.locator(".arena-gtab")
    assert tabs.count() == 2 and pg.locator(".arena-gtab.is-on").get_attribute("data-goal") == "ship-sync"
    pg.locator(".arena-gtab[data-goal=grow]").click()
    pg.locator(".arena[data-goal=grow]").wait_for(timeout=WAIT_MS)
    assert row(pg, "Tag the notes").count() == 1 and row(pg, "Dark mode").count() == 0                       # a proposal waits: its row
    pg.reload()
    pg.locator(".arena[data-goal=grow]").wait_for(timeout=WAIT_MS)
    assert pg.locator(".arena-gtab.is-on").get_attribute("data-goal") == "grow"


def test_a_goal_at_work_has_its_row_its_tasks_in_the_party_s_columns_and_its_results_beside_them(mapped):
    pg, host = mapped
    work = row(pg, "Sync ideas between")                                                                   # At work: a goal's row says how far it is
    assert work.get_attribute("data-state") == "work" and work.locator(".arena-goal__line").inner_text() == "1/4 in dev · implementation"
    assert work.locator(".arena-goal__mark .ork-sign.work").count() == 1                                  # at work: orkUI's sign
    columns = pg.locator(".arena-stack[data-agent]")                                                      # a column per member of the party row
    assert [c.get_attribute("data-agent") for c in columns.all()] == ["grunt", "reviewer", "editor", "seo"]
    grunt = columns.first
    stack = grunt.locator(".arena-stk")
    assert stack.count() == 1 and stack.get_attribute("data-n") == "2"                                    # k2 and k3 are one goal's: one stack, the one at work in front
    assert [t.get_attribute("data-task") for t in grunt.locator(".arena-task").all()] == ["k2"]
    assert grunt.locator(".arena-task.is-fail, .arena-task.is-stop").count() == 0                          # nobody stopped here: no alert
    assert "1 in dev" in grunt.inner_text() and grunt.locator(".ork-sign.check").count() == 1
    assert pg.locator(".arena-result[data-task=k3]").count() == 1                                         # its result waits on the right
    ask = row(pg, "Offline mode")                                                                         # Planning: a member's question and a plan
    assert "asks you · Reviewer" in ask.inner_text() and ask.locator(".arena-goal__mark .ork-sign.alert").count() == 1
    dark = row(pg, "Dark mode")
    assert "plan ready" in dark.inner_text() and "is-stop" in dark.get_attribute("class")
    assert "ready · Taskmaster plans it next" in row(pg, "Cache the table").inner_text()
    # the window asks again when the board moves, and a merged task leaves its stack
    before = len(_calls(pg, host, "ideas.map"))
    host.nodes[0]["tasks"] = [pip("k1", "Read the sync code", "merged"), pip("k2", "Add the queue", "running", ["k1"], 2),
                              pip("k3", "Retry on a lost signal", "merged", ["k1"], 2), pip("k4", "Test it offline", "waiting", ["k2", "k3"], 3, "reviewer", "check")]
    host.nodes[0]["progress"] = {"done": 2, "total": 4}
    host.nodes[0]["results"] = []
    host.bump({})
    pg.wait_for_function("() => document.querySelector('.arena-stack[data-agent=grunt] .arena-stk')?.dataset.n === '1'", timeout=WAIT_MS)
    assert [t.get_attribute("data-task") for t in grunt.locator(".arena-task").all()] == ["k2"] and "2 in dev" in grunt.inner_text()
    assert len(_calls(pg, host, "ideas.map")) > before


def test_a_click_on_a_row_opens_a_passing_tab_another_replaces_it_and_a_double_click_keeps_it(mapped):
    pg, host = mapped
    opener(pg, "Cache the table").click()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "idea", "ref": "later", "device": "desktop", "via": "map"}))
    pg.locator(".shell-drawer .board-sec").first.wait_for(timeout=WAIT_MS)
    assert passing(pg).count() == 1 and "Cache the table" in passing(pg).inner_text()
    assert passing(pg).locator("[role=tab]").evaluate("e => getComputedStyle(e).fontStyle") == "italic"
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 1                                          # no pinned Map: the one tab
    pg.get_by_role("button", name="Close the drawer").click()
    opener(pg, "Offline mode").click()                                                                       # replaces the passing tab
    pg.locator(".shell-ptab.is-passing", has_text="Offline mode").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 1 and "Cache the table" not in pg.locator(".shell-tabstrip").inner_text()
    passing(pg).locator("[role=tab]").dblclick()                                                          # kept: upright, stays
    assert passing(pg).count() == 0 and kept(pg).count() == 1
    assert kept(pg).locator("[role=tab]").evaluate("e => getComputedStyle(e).fontStyle") == "normal"
    pg.get_by_role("button", name="Close the drawer").click()
    opener(pg, "Cache the table").click()
    pg.locator(".shell-ptab.is-passing", has_text="Cache the table").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 2                                          # Offline stays beside the new passing one
    pg.get_by_role("button", name="Keep Cache the table").click()                                               # Keep, as the button
    assert passing(pg).count() == 0 and kept(pg).count() == 2


def test_editing_a_file_keeps_its_tab_and_unsaved_changes_ask_before_esc_closes_it(mapped):
    pg, host = mapped
    pg.locator(".shell-top").get_by_role("button", name="Files").click()                                  # Files: a tab of the drawer
    pg.locator(".shell-tree__row", has_text="notes.txt").click()
    pg.locator(".shell-code").wait_for(timeout=WAIT_MS)
    assert passing(pg).count() == 1 and kept(pg).count() == 1                                             # Files is kept, the file is the passing one
    pg.get_by_role("button", name="Edit", exact=True).click()
    pg.locator("textarea.shell-edit__text").fill("one\ntwo\nthree\n")
    pg.wait_for_selector(".shell-ptab.is-on:not(.is-passing)", timeout=WAIT_MS)                            # an edit keeps the passing tab
    assert passing(pg).count() == 0 and "notes.txt" in kept(pg).last.inner_text()
    active_tab(pg).focus()
    pg.keyboard.press("Escape")
    dlg = pg.get_by_role("dialog", name="Unsaved changes")                                                # asks first
    dlg.wait_for(timeout=WAIT_MS)
    dlg.get_by_role("button", name="Keep editing").click()
    assert pg.locator(".shell-drawer").is_visible()
    pg.keyboard.press("Escape")
    pg.get_by_role("dialog", name="Unsaved changes").get_by_role("button", name="Discard changes").click()
    pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)
    assert host.files["notes.txt"] == "one\ntwo\n"


def test_a_file_saved_from_its_tab_and_opening_what_has_a_tab_shows_that_tab(mapped):
    pg, host = mapped
    pg.locator(".shell-top").get_by_role("button", name="Files").click()
    pg.locator(".shell-tree__row", has_text="README.md").click()
    pg.locator(".shell-md").wait_for(timeout=WAIT_MS)
    pg.locator(".shell-ptab.is-on [role=tab]").dblclick()
    tab(pg, "Files").click()
    pg.locator(".shell-tree__row", has_text="README.md").wait_for(timeout=WAIT_MS)
    show(pg, "idea", slug="dark")
    pg.locator(".shell-drawer .board-sec").first.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 3                                          # Files, README.md, the idea
    tab(pg, "Files").click()
    pg.locator(".shell-tree__row", has_text="README.md").click()                                          # already has a tab: shown, not added
    pg.locator(".shell-md").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tab]").count() == 3 and "README.md" in active_tab(pg).inner_text()
    assert passing(pg).count() == 1                                                                       # the passing one is still Dark mode's


def test_esc_the_cross_and_a_middle_click_close_tabs_and_the_tab_to_the_left_is_shown(mapped):
    pg, host = mapped
    for title in ("Cache the table", "Offline mode"):
        pg.keyboard.press("Escape")
        opener(pg, title).click()
        pg.locator(".shell-ptab.is-passing", has_text=title).wait_for(timeout=WAIT_MS)
        passing(pg).locator("[role=tab]").dblclick()
    show(pg, "idea", slug="dark", opts={"keep": True})
    pg.locator(".shell-ptab.is-on", has_text="Dark mode").wait_for(timeout=WAIT_MS)
    assert kept(pg).count() == 3 and "Dark mode" in active_tab(pg).inner_text()
    pg.get_by_role("button", name="Close Offline mode").click()                                           # a tab that is not shown goes, the shown one stays
    assert kept(pg).count() == 2 and "Dark mode" in active_tab(pg).inner_text()
    pg.get_by_role("button", name="Close Dark mode").click()                                              # the shown one goes: the tab to its left
    pg.wait_for_function("() => !document.querySelector('.shell-ptab[data-tab^=\"idea:dark\"]')")
    assert "Cache the table" in active_tab(pg).inner_text()
    tab(pg, "Cache the table").click(button="middle")
    pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)                                # none left: the drawer goes


def test_the_arrow_keys_move_between_tabs_and_enter_shows_one(mapped):
    pg, host = mapped
    opener(pg, "Cache the table").click()
    pg.locator(".shell-ptab.is-passing", has_text="Cache the table").wait_for(timeout=WAIT_MS)
    passing(pg).locator("[role=tab]").dblclick()
    pg.keyboard.press("Escape")
    opener(pg, "Offline mode").click()
    pg.locator(".shell-ptab.is-passing", has_text="Offline mode").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-tabstrip [role=tablist]").count() == 1
    active_tab(pg).focus()
    pg.keyboard.press("ArrowLeft")
    assert "Cache the table" in pg.evaluate("document.activeElement.textContent")
    pg.keyboard.press("Enter")
    pg.locator(".shell-ptab.is-on", has_text="Cache the table").wait_for(timeout=WAIT_MS)
    pg.keyboard.press("ArrowRight")
    assert "Offline mode" in pg.evaluate("document.activeElement.textContent")
    pg.keyboard.press("Home")
    assert "Cache the table" in pg.evaluate("document.activeElement.textContent")
    pg.keyboard.press("End")
    pg.keyboard.press("Enter")
    pg.locator(".shell-ptab.is-on", has_text="Offline mode").wait_for(timeout=WAIT_MS)


def test_a_13th_tab_closes_the_oldest_kept_one_and_says_so(mapped):
    pg, host = mapped
    for n in range(1, 14):
        show(pg, "idea", slug=f"i{n}", opts={"keep": True})
        pg.locator(".shell-ptab.is-on", has_text=f"Idea {n}").wait_for(timeout=WAIT_MS)
    tabs = pg.locator(".shell-tabstrip [role=tab]")
    assert tabs.count() == 12                                                                             # at most 12: no pinned one
    assert "closed the oldest tab: Idea 1" in pg.locator("body").inner_text()
    names = [t.get_attribute("title") for t in tabs.all()]
    assert names == [f"Goal: Idea {n}" for n in range(2, 14)]                                             # Idea 1 went, the others stay in order


def test_tabs_come_back_after_a_reload_and_each_project_has_its_own(mapped):
    pg, host = mapped
    opener(pg, "Offline mode").click()
    pg.locator(".shell-ptab.is-passing", has_text="Offline mode").wait_for(timeout=WAIT_MS)
    passing(pg).locator("[role=tab]").dblclick()
    pg.get_by_role("button", name="Close the drawer").click()
    opener(pg, "Cache the table").click()
    pg.locator(".shell-ptab.is-passing", has_text="Cache the table").wait_for(timeout=WAIT_MS)
    pg.reload()
    pg.locator(".shell-ptab.is-on", has_text="Cache the table").wait_for(timeout=WAIT_MS)                       # which tabs, which is active, which is passing
    assert kept(pg).count() == 1 and "Offline mode" in kept(pg).inner_text() and passing(pg).count() == 1
    pg.locator(".shell-drawer .board-sec").first.wait_for(timeout=WAIT_MS)
    stored = json.loads(pg.evaluate(f"localStorage.getItem({json.dumps(key(SHOP))})"))
    assert [t["p"]["slug"] for t in stored["tabs"]] == ["offline", "later"] and stored["active"] == "idea:later::"

    pg.locator(".shell-proj__btn").click()                                                                # another project: its own tabs
    pg.locator(f".shell-proj__one[data-path='{BLOG}']").click()
    pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)
    _show_goal(pg, "grow")
    opener(pg, "Tag the notes").click()
    pg.locator(".shell-ptab.is-passing", has_text="Tag the notes").wait_for(timeout=WAIT_MS)
    pg.locator(".shell-proj__btn").click()
    pg.locator(f".shell-proj__one[data-path='{SHOP}']").click()
    pg.locator(".shell-ptab.is-on", has_text="Cache the table").wait_for(timeout=WAIT_MS)
    assert kept(pg).count() == 1 and "Tag the notes" not in pg.locator(".shell-tabstrip").inner_text()


def test_a_tab_whose_idea_is_gone_says_so_with_close(gui):
    ghost = {"kind": "idea", "slug": "ghost"}
    pg, host, errors = _open(gui, init=seed(SHOP, tabs=[{"p": ghost, "kept": True, "title": "Ghost idea"}], active="idea:ghost::", open=True, folded=[]), ready=".shell-ptab", goal="")
    try:
        pg.get_by_text("This goal is gone").wait_for(timeout=WAIT_MS)
        assert not [a for n, a in host.log if n == "ideas.page" and a.get("slug") == "ghost"]            # not asked for
        pg.get_by_role("button", name="Close", exact=True).click()
        pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)
        assert pg.locator(".shell-ptab").count() == 0
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_no_party_says_so_with_new_party_and_new_goal(gui):
    host = MapHost()
    host.nodes, host.edges = [], []
    host.map_doc = lambda: {"goals": [], "nodes": [], "edges": [], "rev": host.rev}
    server, browser = gui
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    try:
        pg.get_by_text("No parties yet").wait_for(timeout=WAIT_MS)
        pg.locator(".arena-note").get_by_role("button", name="New goal").click()                               # a goal needs a party: this makes one first
        assert pg.get_by_role("dialog", name="New party").is_visible()
        pg.keyboard.press("Escape")
        pg.locator(".arena-note").get_by_role("button", name="New party").click()
        assert pg.get_by_role("dialog", name="New party").is_visible()
    finally:
        pg.close()


def test_an_idea_opened_says_where_it_was_opened_from(mapped):
    """Spec 39 §6, spec 49 §2.6: an open is logged with `via`: the window's own (`map`), a stop's (`hand`), the strip's (`today`)."""
    pg, host = mapped

    def opened_via(what, via):
        for _ in range(WAIT_MS // 50):
            if any(name == "ideas.log" and a.get("what") == what and a.get("via") == via for name, a in host.log):
                return True
            pg.wait_for_timeout(50)
        return False
    opener(pg, "Cache the table").click()
    assert opened_via("idea", "map")
    pg.get_by_role("button", name="Close the drawer").click()                                             # the drawer covers the middle of the fan
    item = pg.locator(".arena-hc[data-kind=plan]")
    item.locator(".arena-hc__open").focus()
    item.get_by_role("button", name="Open the plan").click()
    assert opened_via("plan", "hand")
    pg.locator(".arena-hitem").first.click()
    assert opened_via("result", "today") or opened_via("task", "today") or opened_via("idea", "today")


def test_a_row_and_a_task_show_their_short_names_with_the_title_in_their_label(gui):
    host = MapHost()
    host.nodes[3] = {**host.nodes[3], "short": "Cache"}
    host.nodes[0] = {**host.nodes[0], "short": "Sync", "tasks": [{**t, "short": f"T{t['id']}"} for t in host.nodes[0]["tasks"]]}
    pg, host, errors = _open(gui, host)
    prow = row(pg, "Cache")
    assert prow.locator(".arena-goal__title").inner_text() == "Cache" and "Cache the table" in prow.locator(".arena-goal__main").get_attribute("title")
    task = pg.locator(".arena-task[data-task=k2]")
    assert task.get_attribute("title").startswith("Add the queue") and task.locator(".arena-task__name").inner_text() == "Tk2"
    assert "Add the queue" in task.get_attribute("aria-label") and task.locator(".arena-task__goal").inner_text() == "Sync"
    assert task.locator(".arena-task__name").evaluate("e => getComputedStyle(e).webkitLineClamp") == "2"
    assert pg.locator(".arena-gtab").first.get_attribute("title").startswith("Grow installs")             # a tab keeps the title
    pg.close()
    assert not errors, "\n".join(errors)


def test_the_results_column_merges_sends_back_and_drops_but_never_into_main_and_a_plan_starts_from_its_stop(mapped):
    pg, host = mapped
    look = pg.get_by_role("complementary", name="Waits for your look")
    result = look.locator(".arena-result[data-task=k3]")
    assert "20 / 20 passed" in result.inner_text() and "14 files · $0.42" in result.inner_text() and "Retry on a lost signal" in result.inner_text()
    assert "main" not in result.get_by_role("button").all_inner_texts() and result.get_by_role("button", name="Merge into dev").is_visible()
    assert result.evaluate("e => getComputedStyle(e).borderTopStyle") == "double"                         # orkUI's double frame
    result.get_by_role("button", name="Send back").first.click()
    result.get_by_label("Why you send it back, in one line").fill("Retry less often")
    result.locator(".shell-actions__line button").click()
    assert _sent(pg, host, ("ideas.back", {"slug": "sync", "task": "k3", "why": "Retry less often"}))
    result.get_by_role("button", name="Drop…").click()
    pg.get_by_role("dialog").get_by_role("button", name="Drop it").click()
    assert _sent(pg, host, ("ideas.drop_task", {"slug": "sync", "task": "k3"}))
    result.get_by_role("button", name="Merge into dev").click()
    assert _sent(pg, host, ("ideas.merge", {"slug": "sync", "task": "k3"}))
    # Planning with a plan waiting: its stop starts the work (the plan's pass), or opens the plan
    item = pg.locator(".arena-hc[data-kind=plan]")
    item.locator(".arena-hc__open").focus()
    item.get_by_role("button", name="Start the work").click()
    assert _sent(pg, host, ("ideas.start", {"slug": "export", "via": "hand"}))


def test_no_review_column_and_the_alert_is_only_where_the_work_stopped(mapped):
    pg, host = mapped
    assert pg.locator(".shell-review").count() == 0 and pg.locator("[aria-label=Review]").count() == 0
    assert pg.locator(".arena-result .ork-count.warning, .arena-result .is-alert, .arena-look .ork-count.warning").count() == 0     # a result is not a signal
    alert = pg.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-alert)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
    colours = pg.locator(".arena-look *").evaluate_all("els => els.map(e => getComputedStyle(e).color)")
    assert alert not in colours                                                                           # no alert colour anywhere in the results' column
    assert pg.locator(".arena-member[data-agent=grunt] .arena-sign.alert, .arena-member[data-agent=grunt] .arena-sign.danger").count() == 0
    host.nodes[0]["tasks"][1]["state"] = "failed"
    host.bump({})
    pg.locator(".arena-stack[data-agent=grunt] .arena-task.is-fail").wait_for(timeout=WAIT_MS)             # a failed task: its item in danger
    failed = pg.locator(".arena-hc[data-kind=failed]")
    failed.wait_for(timeout=WAIT_MS)                                                                      # and a stop along the bottom, in danger
    assert "danger" in failed.get_attribute("class") and "Add the queue" in failed.inner_text()


def test_under_reduced_motion_a_merged_task_leaves_without_moving(gui):
    server, browser = gui
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    host = MapHost()
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    _show_goal(pg)
    pg.locator(".arena-task[data-task=k2]").wait_for(timeout=WAIT_MS)                                    # the front of Grunts' stack
    host.nodes[0]["tasks"][1]["state"] = "merged"
    host.bump({})
    pg.locator(".arena-task[data-task=k2]").wait_for(state="detached", timeout=WAIT_MS)                  # gone at once; k3 is the front now
    pg.locator(".arena-task[data-task=k3]").wait_for(timeout=WAIT_MS)
    assert pg.locator(".is-leaving, .is-drawn").count() == 0
    pg.close()
