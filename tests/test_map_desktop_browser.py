"""The Map and the preview's tabs on the desktop (docs/specs/39-map.md §3–§4, Tests → B), in a real browser at 1 440 × 900 and
at 1 000 px against a stub host that answers `ideas.map` in §1's shape: the Map is the first tab, pinned, shown at start; goals
as sections, an idea under the ideas it depends on with a line between, each waiting node saying why; Tasks in waves; *new*;
a click opens a passing tab, a double-click or an edit keeps it; Esc closes the active tab; at most 12 tabs; tabs per project
kept after a reload; below 1 024 px no strip, Back and the Board's Map button."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import _show_goal, SHOTS, StubHost, _calls, _sent, box  # noqa: E402

pytestmark = pytest.mark.browser

NOW = dt.datetime.now().replace(microsecond=0)
ago = lambda hours: (NOW - dt.timedelta(hours=hours)).isoformat()      # noqa: E731  (naive local, as `ideas.touched_at`)
SHOP, BLOG = "/work/shop", "/work/blog"
FILES = {"README.md": "# Shop\n\nSells things.\n", "notes.txt": "one\ntwo\n"}


def key(path: str) -> str:
    """The tabs' storage key of a project (spec 39 §3.7)."""
    return "orkboard.tabs." + hashlib.sha1(path.encode()).hexdigest()[:12]


def pip(tid, title, state, after=()):
    return {"id": tid, "title": title, "state": state, "after": list(after), "tier": "warrior"}


def node(slug, goal, title, state, tier, **more):
    base = {"slug": slug, "goal": goal, "title": title, "state": state, "queue": "", "held_until": "", "start_at": "", "priority": "normal",
            "size": "M", "risk": "low", "tier": tier, "depends_on": [], "waits_on": [], "waits": None, "needs_you": "",
            "progress": {"done": 0, "total": 0}, "tasks": [], "estimate": None, "by_itself": False, "folded": False, "updated": ago(30)}
    return base | more


class MapHost(StubHost):
    """The shell's stub plus the Map (§1), a project switcher and a Files tree."""

    def __init__(self):
        super().__init__()
        self.current = SHOP
        self.files = dict(FILES)
        self.ideas["growth"] = self.idea("growth", "Grow the list", "ready", 6, track="grow")
        for n in range(1, 14):
            self.ideas[f"i{n}"] = self.idea(f"i{n}", f"Idea {n}", "plan", 20 + n)
        self.tasks = [pip("k1", "Read the sync code", "merged"), pip("k2", "Add the queue", "running", ["k1"]),
                      pip("k3", "Retry on a lost signal", "ready", ["k1"]), pip("k4", "Test it offline", "waiting", ["k2", "k3"])]
        self.nodes = [
            node("sync", "ship-sync", "Sync ideas between the phone and the town", "working", 1, progress={"done": 1, "total": 4},
                 tasks=self.tasks, by_itself=True, updated=ago(1)),
            node("offline", "ship-sync", "Offline mode", "raw", 1, queue="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}),
            node("dark", "ship-sync", "Dark mode", "plan", 2, depends_on=["sync"], waits_on=["sync"], needs_you="plan",
                 waits={"kind": "you", "ref": "", "title": "", "until": ""}, estimate={"usd_low": 0.4, "usd_high": 1.2}),
            node("export", "ship-sync", "Export notes", "done", 1, folded=True, progress={"done": 3, "total": 3}),
            node("tags", "grow", "Tag the notes", "proposed", 1, needs_you="proposal", waits={"kind": "you", "ref": "", "title": "", "until": ""}),
            node("growth", "grow", "Grow the list", "ready", 2, depends_on=["tags"], waits_on=["tags"],
                 waits={"kind": "idea", "ref": "tags", "title": "Tag the notes", "until": ""}, checks=[{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "passed"},
                            {"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": True, "why": "", "state": "running"}]),
        ]
        self.edges = [{"from": "sync", "to": "dark"}, {"from": "tags", "to": "growth"}]

    def snapshot(self):
        snap = super().snapshot()
        snap["state"]["projects"] = {"current": self.current, "recent": [], "open": [
            {"path": p, "name": p.rsplit("/", 1)[1], "working": 0, "needs_you": 0, "review": 0} for p in (SHOP, BLOG)]}
        return snap

    def map_doc(self):
        goals = [{"slug": "grow", "title": "Grow installs", "priority": "high", "state": "ready", "done_when": ["weekly installs", "stars"],
                  "ideas": 2, "done": 0, "usd": None, "team": [{"slug": "product-designer", "name": "Product designer", "head": {"craft": "design", "race": "elf", "tier": "elder"}, "checks": False, "every": False},
                           {"slug": "reviewer", "name": "Reviewer", "head": {"craft": "engineering", "race": "peon", "tier": "elder"}, "checks": True, "every": True}]},
                 {"slug": "ship-sync", "title": "Ship sync", "priority": "normal", "state": "ready", "done_when": ["sync works offline"],
                  "ideas": 4, "done": 1, "usd": 12.4}]
        return {"goals": goals, "nodes": sorted(self.nodes, key=lambda n: (n["goal"] != "grow", n["tier"])), "edges": self.edges, "rev": self.rev}

    def handle(self, name, a):
        if name == "ideas.map":
            self.log.append((name, a))
            return self.map_doc()
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


def _open(gui, host=None, viewport=None, init="", ready=".map-card"):
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
    _show_goal(pg)                                    # the Board shows one goal: most of the stub's ideas are Ship sync's
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
    return pg.locator(".map-card", has_text=title)


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


def test_two_goals_a_tier_below_its_dependency_with_a_line_and_each_waiting_node_says_why(mapped):
    pg, host = mapped
    sections = pg.locator(".map-goal")
    assert sections.count() == 2 and [s.get_attribute("data-goal") for s in sections.all()] == ["grow", "ship-sync"]   # the Board's order
    head = pg.locator(".map-goal[data-goal=ship-sync] .map-goal__head").inner_text()
    assert "Ship sync" in head and "Normal" in head and "1 of 4 done" in head and "≈$12 so far" in head
    assert "—" in pg.locator(".map-goal[data-goal=grow] .map-goal__head").inner_text()              # nothing priced
    when = pg.locator(".map-goal[data-goal=grow] .map-goal__when")
    assert "done when weekly installs" in when.inner_text() and "stars" not in when.inner_text()    # folded to the first
    when.get_by_role("button", name="and 1 more").click()
    assert "done when stars" in when.inner_text()

    upper, lower = box(pg, ".map-card[data-slug=sync]"), box(pg, ".map-card[data-slug=dark]")
    assert lower["y"] >= upper["y"] + upper["height"] + 12                                          # a tier below
    assert 215 <= upper["width"] <= 225 and 68 <= upper["height"] <= 76                              # about 220 × 72
    line = pg.locator(".map-lines path[data-from=sync][data-to=dark]")
    assert line.count() == 1
    ends = pg.evaluate("""() => { const d = document.querySelector('.map-lines path[data-from=sync][data-to=dark]').getAttribute('d').match(/-?[\\d.]+/g).map(Number);
      const r = document.querySelector('.map-goal[data-goal=ship-sync] .map-lines').getBoundingClientRect(); return [d[0] + r.left, d[1] + r.top, d[d.length - 2] + r.left, d[d.length - 1] + r.top]; }""")
    assert upper["x"] <= ends[0] <= upper["x"] + upper["width"] and abs(ends[1] - (upper["y"] + upper["height"])) < 3      # from the upper's foot
    assert lower["x"] <= ends[2] <= lower["x"] + lower["width"] and abs(ends[3] - lower["y"]) < 3                         # to the lower's top
    assert pg.locator(".map-lines path[data-from=tags][data-to=growth]").count() == 1

    assert "tonight" in card(pg, "Offline mode").inner_text()
    assert "waits for Tag the notes" in card(pg, "Grow the list").inner_text()
    assert card(pg, "Grow the list").evaluate("e => getComputedStyle(e).borderStyle") == "dashed"
    assert pg.locator(".map-card[data-slug=tags]").evaluate("e => getComputedStyle(e).borderStyle") == "dotted"   # proposed
    need = card(pg, "Dark mode")
    assert need.get_attribute("data-needs") == "plan" and "plan ready" in need.inner_text() and "●" in need.inner_text()
    assert need.evaluate("e => getComputedStyle(e).boxShadow") != "none"                            # the frame heavier
    assert "≈$0.40–1.20" in need.inner_text()
    assert "by itself" in card(pg, "Sync ideas").inner_text() and "working 1/4" in card(pg, "Sync ideas").inner_text()
    assert card(pg, "Sync ideas").locator(".shell-spin").count() == 1                               # working: a spinner
    assert pg.locator(".map-card", has_text="Export notes").count() == 0                            # a done idea nothing depends on
    pg.get_by_role("button", name="Done (1)").click()
    assert card(pg, "Export notes").is_visible() and "done" in card(pg, "Export notes").inner_text()
    assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")


def test_a_goal_folds_and_stays_folded_after_a_reload(mapped):
    pg, host = mapped
    pg.get_by_role("button", name="Fold Ship sync").click()
    assert pg.locator(".map-card[data-slug=sync]").count() == 0 and "Ship sync" in pg.locator(".map-goal[data-goal=ship-sync]").inner_text()
    pg.reload()
    pg.locator(".map-card").first.wait_for(timeout=WAIT_MS)
    assert pg.locator(".map-card[data-slug=sync]").count() == 0
    pg.get_by_role("button", name="Unfold Ship sync").click()
    pg.locator(".map-card[data-slug=sync]").wait_for(timeout=WAIT_MS)


def test_the_map_shows_every_goal_whatever_goal_the_board_shows(mapped):
    pg, host = mapped
    pg.get_by_label("Goal", exact=True).select_option("grow")
    assert pg.locator(".map-goal").count() == 2                                       # the Map is the view of them all (the Board shows one)


def test_tasks_unfold_in_waves_and_the_map_asks_again_when_the_board_moves(mapped):
    pg, host = mapped
    assert pg.locator(".map-tasks").count() == 0
    pips = pg.get_by_role("button", name="Tasks of Sync ideas between the phone and the town")
    assert pips.locator(".map-pip").count() == 4 and pips.locator("[data-pip=done]").count() == 1 and pips.locator("[data-pip=working]").count() == 1
    pips.click()
    waves = pg.locator(".map-tasks .map-wave")
    assert waves.count() == 3 and waves.nth(0).inner_text() == "k1 Read the sync code · merged"
    assert "k2 Add the queue · working" in waves.nth(1).inner_text() and "k3 Retry on a lost signal · queued" in waves.nth(1).inner_text()
    assert waves.nth(2).inner_text() == "k4 Test it offline · waiting"
    # the lower tier moved down
    assert box(pg, ".map-card[data-slug=dark]")["y"] > box(pg, ".map-card[data-slug=sync]")["y"] + 72 + 60
    before = len(_calls(pg, host, "ideas.map"))
    host.nodes[0]["tasks"] = [pip("k1", "Read the sync code", "merged"), pip("k2", "Add the queue", "merged", ["k1"]),
                              pip("k3", "Retry on a lost signal", "ready", ["k1"]), pip("k4", "Test it offline", "waiting", ["k2", "k3"])]
    host.bump({})
    pg.locator(".map-tasks .map-task", has_text="k2 Add the queue · merged").wait_for(timeout=WAIT_MS)     # read again with the rev
    assert len(_calls(pg, host, "ideas.map")) > before


def test_new_marks_what_moved_since_the_map_was_last_looked_at_and_is_gone_after(gui):
    seen = seed(SHOP, tabs=[], active="map", seen=ago(2), folded=[])
    pg, host, errors = _open(gui, init=seen)
    try:
        assert "new" in card(pg, "Sync ideas").inner_text()                                        # updated an hour ago, looked at two hours ago
        assert pg.locator(".map-card__new").count() == 1 and "new" not in card(pg, "Dark mode").inner_text()
        pg.locator(".board-card", has_text="Dark mode").click()
        pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
        tab(pg, "Map").click()                                                                     # looked at again: the time moved
        pg.locator(".map-card").first.wait_for(timeout=WAIT_MS)
        assert pg.locator(".map-card__new").count() == 0
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
    assert pg.locator(".map-card[data-slug=sync]").is_visible()
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
    pg.locator(".map-card[data-slug=tags]").click()
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
        pg.locator(".map-card").first.wait_for(timeout=WAIT_MS)
        assert box(pg, ".shell-preview")["width"] == 1000 and pg.locator(".map-card[data-slug=dark]").is_visible()
        assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        card(pg, "Offline mode").click()                                                            # a node opens its idea on the full screen
        pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
        pg.get_by_role("button", name="Back", exact=True).click()
        assert pg.locator(".map-card[data-slug=dark]").is_visible()                                 # Back from an idea returns to the Map
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


def test_a_goal_says_its_team_and_an_idea_how_many_of_its_checks_passed(mapped):
    pg, host = mapped
    goal = pg.locator('.map-goal[data-goal="grow"]')
    team = goal.locator(".map-goal__team")
    team.wait_for(timeout=WAIT_MS)
    assert "Team: Product designer, Reviewer (checks every idea)" in team.inner_text()
    assert team.locator("img.ork-race__head").count() == 2
    mark = goal.locator('.map-card[data-slug="growth"] .map-card__checks')
    assert mark.inner_text() == "checks 1/2" and "Accessibility reviewer: working" in mark.get_attribute("title")
    assert pg.locator('.map-goal[data-goal="ship-sync"] .map-goal__team').count() == 0               # no team, no line
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-map-team-1440x900.png"))
