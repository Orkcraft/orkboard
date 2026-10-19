"""The v1 shell on the desktop (docs/specs/33-v1-shell.md §6–§7), in a real browser at 1 440 × 900 against a stub host that
answers the §5 commands: Board on the left, Review on the right, the preview in the centre and Agents under it as VS Code's
terminal. A click on an idea, a to-do, a chip and a result opens the right preview; Merge is off on red with its reason; Send
back needs its line; no camp. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)

_TODAY = dt.date.today().isoformat()                 # a reset today reads "resets at 18:00", whatever the day
_IN_TWO_DAYS = (dt.date.today() + dt.timedelta(days=2)).isoformat()

pytestmark = pytest.mark.browser

QR = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

SHOTS = Path(__file__).resolve().parent.parent / "docs" / "design" / "img" / "v1"
SECTIONS = ["Gist", "Why", "Done when", "Out", "Risks", "Depends on", "Stages", "Open questions", "Decisions"]      # spec 35 §3
STAGES = "1. k1 Read the sync code (S)\n2. k2 Add the queue (M) ∥ k3 Retry on a lost signal (M)\n3. k4 Test it offline (L), after k3"
GREEN = {"passed": 20, "failed": 0, "failing": [], "tail": "20 passed in 1.1s", "green": True}
RED = {"passed": 10, "failed": 10, "failing": ["tests/test_sync.py::test_retry", "tests/test_sync.py::test_queue", "t3"],
       "tail": "10 failed, 10 passed in 2.0s", "green": False}
PATCH = "diff --git a/sync.py b/sync.py\n--- a/sync.py\n+++ b/sync.py\n@@ -1,2 +1,3 @@\n keep = 1\n-old = 2\n+new = 3\n+more = 4\n"


def task(tid, title, state, after=(), **more):
    return {"id": tid, "title": title, "brief": f"Brief of {title}", "tier": "warrior", "after": list(after), "state": state,
            "branch": f"idea/sync/{tid}", "commit": "", "session": "s", "cost": 0.42, "tokens": 10, "started": "", "finished": "2026-10-17T10:00:00",
            "error": "", "note": "", "round": 1, "tests": None, "diff": None, "conflict": "", "why": "", **more}


def make_plan():
    return {"idea": "sync", "made_at": "2026-10-17T10:00:00", "passed_at": "2026-10-17T10:05:00",
            "estimate": {"tasks": 5, "usd_low": 1.2, "usd_high": 3.5},
            "todos": [{"id": "t1", "title": "API_KEY", "kind": "secret", "why": "The sync service needs it", "choices": [], "steps": [],
                       "for": ["k2", "k3"], "done": False, "value": None}],
            "tasks": [task("k1", "Read the sync code", "merged"), task("k2", "Add the queue", "review", ["k1"], tests=GREEN,
                      diff={"files": 14, "added": 320, "removed": 41}),
                      task("k3", "Retry on a lost signal", "running", ["k2"]),
                      task("k4", "Test it offline", "review", ["k3"], tests=RED, round=2, diff={"files": 3, "added": 12, "removed": 0},
                           conflict="conflicts with dev in a.py, b.py"),
                      task("k5", "Write the notes", "waiting", ["k4"])]}


class StubHost:
    """What part A's commands answer, in the shapes of §5; every change bumps `ideas_rev` and pushes a snapshot."""

    def __init__(self, look="camp", onboarding=None):
        self.look, self.onboarding, self.rev, self.log, self.ws = look, onboarding, 1, [], None
        self.plan = make_plan()
        self.into, self.push = "dev", False
        self.paired = [{"id": "p1", "name": "Pixel 8", "seen": "2026-10-17T09:30:00"}]
        self.target, self.autostart, self.night = "balance", True, "01:00-07:00"
        self.goals = {"general": self.goal("general", "General", "normal", "ready", order=0),
                      "ship-sync": self.goal("ship-sync", "Ship sync", "normal", "ready", summary="Sync is the first thing a second device needs.\nIt touches sync.py.")}
        self.roles = {"taskmaster": {"slug": "taskmaster", "name": "Taskmaster", "model": "elder", "max_parallel": 1, "instruction": "", "builtin": True},
                      "grunt": {"slug": "grunt", "name": "Grunt", "model": "", "max_parallel": 8, "instruction": "", "builtin": True}}
        self.kinds = {k: "grunt" for k in ("code", "tests", "docs", "text", "research")}
        self.limits = [{"provider": "claude", "name": "Claude", "left": 0.62,
                        "rows": [{"window": "5h", "left": 0.62, "reset": f"{_TODAY}T18:00"}, {"window": "week", "left": 0.8, "reset": f"{_IN_TWO_DAYS}T09:00"}]},
                       {"provider": "agy", "name": "Antigravity", "left": 0.15, "rows": [{"window": "daily", "left": 0.15, "reset": ""}]}]
        self.ideas = {"sync": self.idea("sync", "Sync ideas between the phone and the town", "working", 0),
                      "dark": self.idea("dark", "Dark mode", "plan", 1, start_at="night"),
                      "offline": self.idea("offline", "Offline mode", "raw", 2, queue="night"),
                      "export": self.idea("export", "Export notes", "plan", 3, in_needs_you=True),
                      "search": self.idea("search", "Search the notes", "asks", 4, in_needs_you=True),
                      "tags": self.idea("tags", "Tag the notes", "proposed", 5, in_needs_you=True, track="grow")}
        self.goals["grow"] = self.goal("grow", "Grow installs", "high", "ready", order=2, summary="More people try Orkline.", questions=["Which channel first?"])
        self.proposals, self.asked, self.todo_log = [], [], []

    def idea(self, slug, title, state, order, **more):
        return {"slug": slug, "title": title, "track": "ship-sync", "order": order, "state": state, "size": "M", "asks": 0, "updated": "x", "talk": [],
                "priority": "normal", "queue": "", "held_until": "", "risk": "low", "risk_triggers": [], "depends_on": [], "waits_on": [],
                "start_at": "", "in_needs_you": False, **more}

    def needs_you(self):
        todo = {"id": "t1", "title": "API_KEY", "kind": "secret", "why": "The sync service needs it", "choices": [], "steps": ["Open the console", "Copy the key"],
                "accept": [], "done": False}
        base = {"goal": "ship-sync", "priority": "normal", "blocks": False, "at": "2026-10-18T09:00:00"}
        out = [base | {"kind": "todo", "idea": "sync", "title": "Sync ideas between the phone and the town", "text": "API_KEY", "blocks": True, "todo": todo},
               base | {"kind": "plan", "idea": "export", "title": "Export notes", "text": "Plan ready · 3 tasks"},
               base | {"kind": "asks", "idea": "search", "title": "Search the notes", "text": "Which fields count?"},
               base | {"kind": "goal", "idea": "", "goal": "grow", "title": "Grow installs", "text": "Which channel first?", "priority": "high"},
               base | {"kind": "proposal", "idea": "tags", "goal": "grow", "title": "Tag the notes", "text": "Tags make a long list findable."}]
        gone = set(self.proposals) | set(self.asked)            # answered: out of the list
        return [n for n in out if (n["idea"] or n["goal"]) not in gone]

    def goal(self, slug, title, priority, state, order=1, **more):
        return {"slug": slug, "title": title, "about": "", "criteria": [], "deadline": "", "order": order, "count": 0, "priority": priority,
                "metrics": [], "links": [], "summary": "", "questions": [], "state": state, "error": "", **more}

    def kind_list(self):
        names = {"code": "Code", "tests": "Tests", "docs": "Docs", "text": "Text for people", "research": "Research"}
        return [{"kind": k, "label": names[k], "role": r} for k, r in self.kinds.items()]

    def results(self):
        return [{"idea": "sync", "idea_title": "Sync ideas between the phone and the town", "task": t["id"], "title": t["title"], "round": t["round"],
                 "tests": t["tests"], "diff": t["diff"], "cost": t["cost"], "conflict": t["conflict"], "finished": t["finished"]}
                for t in self.plan["tasks"] if t["state"] == "review"]

    def snapshot(self):
        return {"t": "state", "state": {
            "focus": "board", "ideas_rev": self.rev, "look": self.look, "project": "orkline", "demo": False, "onboarding": self.onboarding or False,
            "words": [], "resources": {}, "orkspaces": [], "buildings": [], "roads": [], "alerts": [], "score": {},
            "limits": self.limits, "review_count": len(self.results()), "needs_you": 1,
            "hud": {"gold": "$2.40", "show_gold": True, "lumber": "120k"}}}

    def page(self, slug):
        i = self.ideas[slug]
        secs = [{"name": n, "thesis": f"{n} in one line", "text": f"{n}: the longer text of this section."} for n in SECTIONS]
        if slug == "sync":
            next(x for x in secs if x["name"] == "Stages")["text"] = STAGES
        if slug == "search":
            next(x for x in secs if x["name"] == "Open questions")["text"] = "- Which fields count?\n- Do tags count?"
        return {"slug": slug, "title": i["title"], "track": "general", "state": i["state"], "size": "M", "sections": secs, "talk": i["talk"],
                "plan": self.plan if slug == "sync" else None, "busy": False}

    def find(self, a):
        return next(t for t in self.plan["tasks"] if t["id"] == a["task"])

    def handle(self, name, a):
        self.log.append((name, a))
        if name == "ideas.board":
            ideas = [i | {"thesis": "Gist in one line", "progress": {"done": 1, "total": 5} if i["slug"] == "sync" else {"done": 0, "total": 0}}
                     for i in self.ideas.values()]
            return {"tracks": [g | {"count": sum(1 for i in ideas if i["track"] == g["slug"])} for g in self.goals.values()],
                    "ideas": ideas, "needs_you": self.needs_you(), "target": self.target, "autostart": self.autostart, "night": self.night,
                    "rev": self.rev}
        if name == "ideas.page":
            return self.page(a["slug"])
        if name == "ideas.review_list":
            return {"into": self.into, "push": self.push, "branches": ["dev", "main"], "results": self.results()}
        if name == "ideas.agents":
            chips = [dict(idea="sync", idea_title="Sync ideas between the phone and the town", task=t["id"], title=t["title"],
                          state=t["state"], tier=t["tier"], note="", by="auto" if t["id"] == "k3" else "person", night=False)
                     for t in self.plan["tasks"] if t["state"] in ("running", "review")]
            chips += [dict(idea="sync", idea_title="Sync ideas between the phone and the town", task="k5", title="Write the notes", state="held",
                           tier="warrior", note="reserve · after 18:00", by="person", night=False),
                      dict(idea="dark", idea_title="Dark mode", task="d1", title="Dark palette", state="ready", tier="warrior", note="", by="auto", night=True),
                      dict(idea="export", idea_title="Export notes", task="e1", title="Write the export", state="held", tier="warrior", note="files · sync",
                           waits_title="Sync ideas between the phone and the town", by="auto", night=False)]
            blocks = [{"role": "taskmaster", "name": "Taskmaster", "model": "elder", "max_parallel": 1, "builtin": True, "spend_today": 0,
                       "state": "waiting", "waits_on": {"idea": "dark", "text": "waiting for your answers on “Dark mode”"}, "chips": []},
                      {"role": "grunt", "name": "Grunts", "model": "", "max_parallel": 8, "builtin": True, "spend_today": 1.25, "chips": chips,
                       "kinds": [k for k, r in self.kinds.items() if r == "grunt"]}]
            blocks += [{"role": r["slug"], "name": r["name"], "model": r["model"], "max_parallel": r["max_parallel"], "builtin": False, "spend_today": 0,
                        "chips": [], "kinds": [k for k, x in self.kinds.items() if x == r["slug"]]} for r in self.roles.values() if not r["builtin"]]
            return {"roles": blocks, "done_today": [{"idea": "sync", "task": "k1", "title": "Read the sync code", "role": "grunt"}]}
        if name == "ideas.roles":
            return {"roles": [r | {"spend_today": 0} for r in self.roles.values()], "kinds": self.kind_list(),
                    "models": [{"id": "", "label": "The task's own tier"}, {"id": "elder", "label": "Elder tier (opus)"},
                               {"id": "warrior", "label": "Warrior tier (sonnet)"}, {"id": "laborer", "label": "Laborer tier (haiku)"}]}
        if name == "ideas.role_save":
            slug = a.get("slug") or a["name"].lower().replace(" ", "-")
            self.roles[slug] = {"slug": slug, "name": a["name"], "model": a["model"], "max_parallel": a["max_parallel"],
                                "instruction": a.get("instruction", ""), "builtin": slug in ("taskmaster", "grunt")}
            for k in a.get("kinds", []):                                                              # spec 36 §3: the types this agent takes
                self.kinds[k] = slug
            return self.bump({"slug": slug})
        if name == "ideas.role_drop":
            self.roles.pop(a["slug"])
            self.kinds = {k: ("grunt" if r == a["slug"] else r) for k, r in self.kinds.items()}
            return self.bump({"ok": True})
        if name == "ideas.kind_set":
            self.kinds[a["kind"]] = a["role"]
            return self.bump({"ok": True})
        if name == "ideas.goal_save":
            slug = a.get("slug") or "-".join(a["about"].lower().replace(".", "").split()[:2])
            old = self.goals.get(slug, {})
            title = a.get("title") or old.get("title") or a["about"][:30]
            self.goals[slug] = self.goal(slug, title, a["priority"], "reading", about=a["about"], summary=old.get("summary", ""),
                                         title_by="person" if a.get("title") else old.get("title_by", "keeper"))
            return self.bump({"slug": slug})
        if name == "ideas.goal":
            g = self.goals[a["slug"]]
            return g | {"description": g["about"], "talk": [], "busy": g["state"] == "reading", "sections": []}
        if name == "ideas.queue":
            self.ideas[a["slug"]].update(queue=a["queue"], state="reading" if a["queue"] == "now" else "raw")
            return self.bump({"ok": True})
        if name == "ideas.read_stop":
            self.ideas[a["slug"]].update(queue="hold", state="raw")
            return self.bump({"ok": True})
        if name == "ideas.start_now":
            self.ideas[a["slug"]].update(start_at="", state="working")
            return self.bump({"ok": True})
        if name == "ideas.drop":
            self.ideas.pop(a["slug"], None)
            return self.bump({"ok": True})
        if name == "ideas.proposal":
            self.proposals.append(a["slug"])
            return self.bump({"ok": True})
        if name == "ideas.answer":
            self.asked.append(a["slug"])
            return self.bump({"ok": True})
        if name == "ideas.board_set":
            self.target, self.autostart, self.night = a.get("target", self.target), a.get("autostart", self.autostart), a.get("night", self.night)
            return self.bump({"target": self.target, "autostart": self.autostart, "night": self.night})
        if name == "ideas.todo":
            return self.bump({"ok": True})
        if name == "ideas.doc":
            return {"path": a["path"], "text": f"The text of {a['path']}", "truncated": False}
        if name == "phones.pair":
            return {"phones": list(self.paired), "listening": True, "address": "https://192.168.1.20:8443", "tail_address": "https://studio.tail1234.ts.net:8443",
                    "tail_trusted": True, "tailscale": True, "fingerprint": "AB:CD", "open": [], "pairing": 120, "awake_offer": "",
                    "link": "orkcraft://x", "qr": QR, "code": "123456", "app_link": "https://studio.tail1234.ts.net:8443/app", "app_qr": QR}
        if name == "phones.tailnet":
            return {"running": True, "installed": True, "phones": [{"name": "Pixel 8", "os": "Android", "online": True}], "install_qr": QR,
                    "dns_qr": QR, "install": "https://tailscale.com/download", "dns": "https://login.tailscale.com/admin/dns", "account": "me@example.com"}
        if name == "phones.list":
            return {"phones": self.paired, "listening": True, "address": "https://192.168.1.20:8443", "tail_address": "https://studio.tail1234.ts.net:8443",
                    "tail_trusted": True, "tailscale": True, "fingerprint": "AB:CD", "open": [], "pairing": 100, "awake_offer": ""}
        if name == "phones.forget":
            self.paired = [d for d in self.paired if d["id"] != a["id"]]
            return {"phones": self.paired, "listening": True, "address": "", "tail_address": "", "open": [], "pairing": 0}
        if name == "phones.pair_stop":
            return {"phones": self.paired, "pairing": 0}
        if name == "ideas.task":
            return self.find(a) | {"idea": a["slug"], "idea_title": "Sync ideas between the phone and the town", "log": "== round 1\nreading sync.py\n"}
        if name == "ideas.diff":
            return {"base": self.into, "branch": f"idea/sync/{a['task']}", "commits": [{"sha": "9f2c41d7e0", "subject": "k2: add the queue"}],
                    "files": [{"path": "sync.py", "added": 2, "removed": 1, "patch": PATCH}, {"path": "huge.json", "added": 9000, "removed": 0, "patch": None}],
                    "truncated": True}
        if name == "ideas.merge":
            self.find(a)["state"] = "merged"
            return self.bump({"ok": True, "commit": "abc"})
        if name == "ideas.back":
            self.find(a).update(state="running", round=self.find(a)["round"] + 1, why=a["why"])
            return self.bump({"ok": True})
        if name == "ideas.drop_task":
            self.find(a).update(state="failed", error="dropped by you")
            return self.bump({"ok": True})
        if name == "ideas.stop_task":
            self.find(a).update(state="ready", note="stopped by you")
            return self.bump({"ok": True})
        if name == "ideas.into":
            self.into, self.push = a.get("branch", self.into), a.get("push", self.push)
            return self.bump({"ok": True})
        if name == "ideas.add":
            if not a.get("track") or a["track"] == "general":
                return {"error": "An idea needs a goal"}
            slug = a["text"].lower().replace(" ", "-")
            now = a["priority"] != "low" and not a.get("night")
            self.ideas[slug] = self.idea(slug, a["text"], "reading" if now else "raw", 9, track=a["track"], priority=a["priority"], queue="now" if now else "night")
            return self.bump({"slug": slug, "queue": "now" if now else "night"})
        if name == "onboarding.skip":
            self.onboarding = {"step": "raising", "steps": ["tools"], "n": 0, "raising": {"title": "x", "phase": "done", "steps": [], "buildings": [], "error": ""}}
            return self.bump({})
        if name == "onboarding.close":
            self.onboarding = None
            return self.bump({})
        return {"ok": True}

    def bump(self, result):
        self.rev += 1
        if self.ws:
            self.ws.send(json.dumps(self.snapshot()))
        return result

    def on_socket(self, ws):
        self.ws = ws
        ws.send(json.dumps(self.snapshot()))

        def on_message(raw):
            m = json.loads(raw)
            ws.send(json.dumps({"t": "reply", "id": m["id"], "ok": True, "result": self.handle(m["name"], m["args"])}))
        ws.on_message(on_message)


def _sent(pg, host, entry, ms=WAIT_MS) -> bool:
    """The stub got `entry`. A command goes over the page's socket to the stub, whose handler runs only while Playwright
    is called (the sync API): the page is given a moment, up to `ms`, until it has (on a busy machine one call was not
    enough)."""
    for _ in range(ms // 50):
        if entry in host.log:
            return True
        pg.wait_for_timeout(50)
    return entry in host.log


def _calls(pg, host, name, at_least=1, ms=WAIT_MS) -> list[dict]:
    """The arguments of every `name` the stub got, once it got at least `at_least` of them (as `_sent`)."""
    for _ in range(ms // 50):
        got = [a for n, a in host.log if n == name]
        if len(got) >= at_least:
            return got
        pg.wait_for_timeout(50)
    return [a for n, a in host.log if n == name]


def _open(gui, viewport=None, host=None, ready=".shell-card"):
    server, browser = gui
    host = host or StubHost()
    pg = browser.new_page(viewport=viewport or {"width": 1440, "height": 900})
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    if ready:
        pg.wait_for_selector(ready, timeout=WAIT_MS)
    return pg, host, errors


@pytest.fixture
def shell(gui):
    pg, host, errors = _open(gui)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def box(pg, selector):
    return pg.locator(selector).first.bounding_box()


def test_three_columns_agents_under_the_preview_and_no_camp(shell):
    pg, host = shell
    board, preview, review, agents = box(pg, ".shell-board"), box(pg, ".shell-preview"), box(pg, ".shell-review"), box(pg, ".shell-agents")
    assert board["x"] < preview["x"] < review["x"] and 280 <= board["width"] <= 320 and 320 <= review["width"] <= 360
    assert board["height"] > 500 and review["height"] > 500                                   # both full height
    assert agents["y"] > preview["y"] + preview["height"] - 2 and abs(agents["x"] - preview["x"]) < 2   # Agents under the preview
    assert 0.25 < agents["height"] / (agents["y"] + agents["height"] - preview["y"]) < 0.42   # about a third of the centre
    assert pg.evaluate("document.documentElement.dataset.look") == "office"                   # the person's look is camp: not here
    for gone in (".gui-hud", ".gui-camp", ".gui-town", ".gui-foot", ".gui-warchief__face", "[data-look=camp]"):
        assert pg.locator(gone).count() == 0, gone
    assert pg.get_by_role("tab", name="Map").get_attribute("aria-selected") == "true"        # the Map takes the place of the empty text (spec 39 §3.1)
    assert "Open an idea, a task or a result" not in pg.locator(".shell-preview").inner_text()
    assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.locator(".shell-card").nth(0).click()
        pg.locator(".shell-file").first.wait_for(timeout=WAIT_MS)
        pg.locator(".shell-file").first.locator("summary").click()
        pg.screenshot(path=str(SHOTS / "desktop-1440x900.png"))


def test_the_top_bar_limits_spend_stop_all_and_the_push_switch(shell):
    pg, host = shell
    top = pg.locator(".shell-top")
    assert "62 %" in top.locator(".shell-limit").nth(0).inner_text() and top.locator(".shell-limit").nth(0).get_attribute("data-provider") == "claude"
    assert "is-warn" in top.locator(".shell-limit").nth(1).get_attribute("class") and "15 %" in top.locator(".shell-limit").nth(1).inner_text()
    pop = top.locator(".shell-limit").nth(0).locator(".shell-pop")
    assert not pop.is_visible()
    top.locator(".shell-limit").nth(0).hover()
    assert pop.is_visible() and "week" in pop.inner_text() and "resets at 18:00" in pop.inner_text()
    assert "$2.40" in top.inner_text()
    top.get_by_role("button", name="Stop all").click()
    assert _sent(pg, host, ("halt", {}))
    top.get_by_role("button", name="Settings").click()
    assert pg.get_by_role("dialog", name="Settings").is_visible()
    label = pg.get_by_text("Push after merging (sends your code to origin)")
    assert label.is_visible() and not pg.get_by_role("checkbox", name="Push after merging").is_checked()
    pg.get_by_text("Push after merging (sends your code to origin)").click()
    assert _sent(pg, host, ("ideas.into", {"push": True}))
    links = pg.locator(".shell-modal a[download]")                              # the day's logs, today and the last 7 days
    assert links.all_inner_texts() == ["Today", "The last 7 days"]
    assert "/api/analytics?days=1" in links.nth(0).get_attribute("href") and "days=7" in links.nth(1).get_attribute("href")


def test_agents_resize_hide_and_remember(shell, gui):
    pg, host = shell
    h0 = box(pg, ".shell-agents")["height"]
    handle = box(pg, ".shell-split")
    pg.mouse.move(handle["x"] + 40, handle["y"] + 2)
    pg.mouse.down()
    pg.mouse.move(handle["x"] + 40, handle["y"] - 150, steps=5)
    pg.mouse.up()
    assert box(pg, ".shell-agents")["height"] > h0 + 120
    pg.keyboard.press("Control+j")                                       # hides it, as VS Code's panel
    assert pg.locator(".shell-agents__body").count() == 0 and box(pg, ".shell-agents")["height"] < 60
    assert pg.locator(".shell-split").count() == 0
    pg.reload()
    pg.wait_for_selector(".shell-card", timeout=WAIT_MS)
    assert pg.locator(".shell-agents__body").count() == 0               # kept in localStorage
    pg.get_by_role("button", name="Show Agents (Ctrl+J)").click()
    assert pg.locator(".shell-agents__body").is_visible() and box(pg, ".shell-agents")["height"] > h0 + 120   # and its height


def test_a_click_on_an_idea_a_todo_a_chip_and_a_result_opens_the_right_preview(shell):
    pg, host = shell
    pg.locator(".board-card", has_text="Sync ideas").click()                      # an idea → its spec: the nine sections
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "idea", "ref": "sync", "device": "desktop", "via": "board"}))
    pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-preview .board-sec").count() == len(SECTIONS)
    assert "Spec" in pg.locator(".shell-preview > header").inner_text()

    pg.locator(".board-need[data-kind=todo]").click()                              # a to-do → its dialog; from it the plan, scrolled to it
    pg.get_by_role("dialog", name="API_KEY").get_by_role("button", name="What waits for it").click()
    target = pg.locator(".shell-preview .board-plan__todo.is-target")
    target.wait_for(timeout=WAIT_MS)
    assert "tasks k2 and k3 wait for it" in target.inner_text()
    assert "Plan" in pg.locator(".shell-preview > header").inner_text() and pg.get_by_role("tab", name="Plan", exact=False).count() == 1
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "todo", "ref": "sync/t1", "device": "desktop"}))

    pg.locator(".shell-chip", has_text="Retry on a lost signal").click()          # a chip → the task: brief, log, Stop
    pg.locator(".shell-task").wait_for(timeout=WAIT_MS)
    text = pg.locator(".shell-task").inner_text()
    assert "Brief of Retry on a lost signal" in text and "reading sync.py" in text and "idea/sync/k3" in text and "working" in text
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "task", "ref": "sync/k3", "device": "desktop", "via": "agents"}))
    pg.get_by_role("button", name="Stop", exact=True).click()
    assert _sent(pg, host, ("ideas.stop_task", {"slug": "sync", "task": "k3"}))

    pg.locator(".shell-card", has_text="Add the queue").click()                   # a result → its code
    pg.locator(".shell-result .shell-commits").wait_for(timeout=WAIT_MS)
    assert "k2: add the queue" in pg.locator(".shell-commits").inner_text()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "result", "ref": "sync/k2", "device": "desktop", "via": "review"}))
    pg.locator(".shell-file", has_text="sync.py").locator("summary").click()
    pg.locator(".shell-patch__line.is-add").first.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-patch__line.is-add").count() == 2 and pg.locator(".shell-patch__line.is-del").count() == 1
    pg.locator(".shell-file", has_text="huge.json").locator("summary").click()
    pg.get_by_text("Too large to show.", exact=True).wait_for(timeout=WAIT_MS)    # not "Some files are too large…"
    colors = pg.evaluate("""() => { const cs = (q) => getComputedStyle(document.querySelector(q)).color;
      return [cs('.shell-patch__line.is-add'), cs('.shell-patch__line.is-del'), getComputedStyle(document.documentElement).getPropertyValue('--success').trim()]; }""")
    assert colors[0] != colors[1]
    assert pg.get_by_role("button", name="Merge into dev").last.is_visible()      # its actions stay pinned at the foot
    foot, body = box(pg, ".shell-result__foot"), box(pg, ".shell-result__body")
    assert foot["y"] >= body["y"] + body["height"] - 2


def test_merge_is_off_on_red_with_its_reason_and_send_back_needs_a_line(shell):
    pg, host = shell
    green, red = pg.locator(".shell-card", has_text="Add the queue"), pg.locator(".shell-card", has_text="Test it offline")
    assert "20 / 20 passed" in green.inner_text() and "14 files, +320 −41" in green.inner_text() and "$0.42" in green.inner_text()
    assert "10 / 20 failed" in red.inner_text() and "test_retry" in red.inner_text() and "round 2" in red.inner_text()
    assert "conflicts with dev in a.py, b.py" in red.inner_text()
    merge = red.get_by_role("button", name="Merge into dev")
    assert merge.is_disabled() and "red" in red.locator(".shell-actions__why").inner_text()
    assert green.get_by_role("button", name="Merge into dev").is_enabled()
    # the quiet Drop is apart from Merge
    drop, mergeb = red.get_by_role("button", name="Drop…").bounding_box(), merge.bounding_box()
    assert drop["x"] > mergeb["x"] + mergeb["width"] + 10

    fix = red.get_by_role("button", name="Fix", exact=True)                       # red / conflict: Fix, the line prefilled
    fix.click()
    line = red.get_by_label("What to fix, in one line")
    assert line.input_value().startswith("Resolve the conflict with dev")
    line.fill("")
    assert red.locator(".shell-actions__line .ork-btn.primary").is_disabled()      # the line is required
    line.fill("Rebase and keep both queues")
    red.locator(".shell-actions__line .ork-btn.primary").click()
    assert _sent(pg, host, ("ideas.back", {"slug": "sync", "task": "k4", "why": "Rebase and keep both queues"}))

    green.get_by_role("button", name="Send back").click()
    assert green.locator(".shell-actions__line .ork-btn.primary").is_disabled()
    green.get_by_role("button", name="Merge into dev").click()
    assert _sent(pg, host, ("ideas.merge", {"slug": "sync", "task": "k2"}))
    pg.locator(".shell-card").first.wait_for(state="detached", timeout=WAIT_MS) if pg.locator(".shell-card").count() else None
    assert pg.locator(".shell-card", has_text="Add the queue").count() == 0


def test_drop_asks_first_and_merge_into_changes_the_branch(shell):
    pg, host = shell
    card = pg.locator(".shell-card", has_text="Add the queue")
    card.get_by_role("button", name="Drop…").click()
    assert pg.get_by_role("dialog", name="Drop this result?").is_visible()
    pg.get_by_role("dialog").get_by_role("button", name="Keep it").click()
    assert pg.get_by_role("dialog").count() == 0 and ("ideas.drop_task", {"slug": "sync", "task": "k2"}) not in host.log
    assert card.get_by_role("button", name="Drop…").evaluate("e => e === document.activeElement")     # the focus went back
    pg.locator(".shell-into").get_by_role("button", name="Merge into dev").click()
    assert pg.get_by_role("menuitemradio").count() == 2
    pg.get_by_role("menuitem", name="New branch…").click()
    pg.get_by_label("Name of the new branch").fill("next")
    pg.get_by_role("button", name="Make it").click()
    assert _sent(pg, host, ("ideas.into", {"branch": "next"}))
    pg.locator(".shell-into").get_by_role("button", name="Merge into next").wait_for(timeout=WAIT_MS)


def test_esc_closes_the_preview_and_arrows_move_through_the_review_cards(shell):
    pg, host = shell
    pg.locator(".board-card", has_text="Dark mode").click()
    pg.locator(".shell-preview .board-sec").first.wait_for(timeout=WAIT_MS)
    pg.keyboard.press("Escape")
    pg.locator(".shell-preview .board-sec").first.wait_for(state="detached", timeout=WAIT_MS)      # the tab closes: the Map is shown
    assert pg.get_by_role("tab", name="Map").get_attribute("aria-selected") == "true"
    first = pg.locator(".shell-card").nth(0)
    first.focus()
    pg.keyboard.press("ArrowDown")
    pg.locator(".shell-card.is-on", has_text="Test it offline").wait_for(timeout=WAIT_MS)
    assert "Test it offline" in pg.locator(".shell-preview > header").inner_text()
    pg.keyboard.press("ArrowUp")
    pg.locator(".shell-card.is-on", has_text="Add the queue").wait_for(timeout=WAIT_MS)
    assert not [c for c in host.log if c[0] in ("ideas.merge", "ideas.back", "ideas.drop_task")]     # no shortcut merges


def test_the_board_drops_an_idea_and_lists_it_with_its_state_in_words(shell):
    pg, host = shell
    assert "working 1/5" in pg.locator(".board-card", has_text="Sync ideas").inner_text()
    assert "starts tonight" in pg.locator(".board-card", has_text="Dark mode").inner_text()
    pg.get_by_role("button", name="New idea").click()
    pg.get_by_label("Your idea").fill("Offline sync")
    pg.get_by_role("button", name="Add", exact=True).click()
    pg.locator(".board-card", has_text="Offline sync").wait_for(timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.add", {"text": "Offline sync", "track": "grow", "priority": "high"}))      # the first goal by priority


def test_below_1024_the_phones_layout_three_tabs_and_the_preview_on_its_own_screen(gui):
    pg, host, errors = _open(gui, {"width": 900, "height": 800}, ready=".shell-tabs")
    try:
        tabs = pg.locator(".shell-tabs")
        assert tabs.get_by_role("tab", name="Review").text_content().replace("\n", "").strip() == "Review2"
        assert pg.locator(".shell-review").is_hidden() and pg.locator(".shell-board").is_visible()
        tabs.get_by_role("tab", name="Review").click()
        assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "tab", "ref": "review", "device": "desktop"}))
        pg.locator(".shell-card", has_text="Add the queue").click()
        pg.locator(".shell-preview.is-open").wait_for(timeout=WAIT_MS)
        box_ = box(pg, ".shell-preview")
        assert box_["x"] == 0 and box_["width"] == 900
        pg.get_by_role("button", name="Back", exact=True).click()
        assert pg.locator(".shell-card").first.is_visible()
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_the_first_start_shows_the_first_screen_then_opens_the_shell(gui):
    onboarding = {"step": "tools", "steps": ["tools", "who", "town"], "n": 0, "again": False, "raising": None, "classes": [], "only_kin": "",
                  "tools": {"ready": True, "warder": True, "warder_agy": "", "cli": [], "others": [], "missing": [], "recommended": [],
                            "rows": [{"id": "claude", "title": "Claude Code", "mark": "✱", "enabled": True, "billing": "subscription", "version": "2.0",
                                      "logged_in": True, "login": "", "check": None, "risk": ""}]}}
    pg, host, errors = _open(gui, host=StubHost(onboarding=onboarding), ready=".gui-onb__card")
    try:
        card = pg.locator(".gui-onb__card").text_content()                          # its title is in capitals on the page
        assert "Your AI tools" in card and "Claude Code" in card
        for gone in ("Who are you", "Mission", "Skip: empty town", "Security reviewer"):
            assert gone not in pg.locator(".gui-onb").inner_text()
        pg.get_by_role("button", name="Open the board", exact=True).click()
        pg.locator(".shell-card").first.wait_for(timeout=WAIT_MS)
        assert _sent(pg, host, ("onboarding.skip", {})) and _sent(pg, host, ("onboarding.close", {}))
    finally:
        pg.close()
    assert not errors, "\n".join(errors)



# -- spec 34 round 2: dialogs, agents by task type, the phone from the shell -----------------------------------------

def adds(host):
    return [a for n, a in host.log if n == "ideas.add"]


def test_new_goal_is_a_description_and_a_priority_then_reading_then_its_title_and_summary(shell):
    pg, host = shell
    pg.get_by_role("button", name="New goal").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    assert dlg.is_visible() and dlg.get_by_role("button", name="Save goal").is_disabled()           # a description is required
    assert dlg.get_by_label("Title").count() == 0 and dlg.get_by_label("Deadline").count() == 0     # nothing else is asked
    assert dlg.get_by_label("Metric 1: what is measured").count() == 0 and dlg.get_by_label("Link 1", exact=True).count() == 0
    dlg.get_by_label("Description").fill("More people try Orkline.")
    dlg.get_by_text("High", exact=True).click()
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-new-goal-1440x900.png"))
    dlg.get_by_role("button", name="Save goal").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.goal_save")[0] == {"about": "More people try Orkline.", "priority": "high"}
    pg.locator(".shell-goal").wait_for(timeout=WAIT_MS)                                             # the goal opens in the preview
    assert "drafting" in pg.locator(".board-state", has_text="reading").first.inner_text() or "reading" in pg.locator(".shell-goal").inner_text()
    assert "reading" in pg.locator(".board-goals__select option:checked").inner_text()
    g = host.goals["more-people"]
    g.update(title="Grow installs", state="asks", summary="Installs are the first step.", questions=["Which channel first?"], title_by="keeper",
             metrics=[{"name": "weekly installs", "target": "50", "how": "npm downloads, per week"}])
    host.bump({})
    pg.locator(".shell-goal").get_by_text("Installs are the first step.").wait_for(timeout=WAIT_MS)
    text = pg.locator(".shell-goal").inner_text()
    assert "npm downloads, per week" in text and "weekly installs" in text and "Which channel first?" in text
    assert "Grow installs · High · asks you" in pg.locator(".board-goals__select option:checked").inner_text()
    pg.get_by_label("Answer 1: Which channel first?").fill("npm first")                              # §0: one round, one Send
    pg.locator(".shell-goal").get_by_role("button", name="Send").click()
    assert _sent(pg, host, ("ideas.answer", {"slug": "more-people", "answers": ["npm first"], "goal": True}))
    pg.get_by_role("button", name="Edit goal Grow installs").click()                                # Edit: description, priority and Title
    dlg = pg.get_by_role("dialog", name="Edit goal")
    assert dlg.get_by_label("Title").input_value() == "Grow installs" and dlg.get_by_label("Description").input_value() == "More people try Orkline."
    dlg.get_by_label("Description").fill("More people try Orkline, and stay.")
    dlg.get_by_role("button", name="Save goal").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.goal_save", 2)[-1] == {"slug": "more-people", "about": "More people try Orkline, and stay.", "priority": "high"}
    pg.get_by_role("button", name="Edit goal Grow installs").click()                                # a corrected title is sent, and only then
    pg.get_by_role("dialog", name="Edit goal").get_by_label("Title").fill("Grow weekly installs")
    pg.get_by_role("dialog", name="Edit goal").get_by_role("button", name="Save goal").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.goal_save", 3)[-1]["title"] == "Grow weekly installs"


def test_new_idea_needs_a_goal_a_priority_and_one_button_and_a_closed_dialog_goes_to_the_night(shell):
    pg, host = shell
    pg.get_by_role("button", name="New idea").click()
    dlg = pg.get_by_role("dialog", name="New idea")
    assert dlg.get_by_role("button", name="Add", exact=True).is_disabled() and dlg.get_by_role("button", name="Later").count() == 0
    assert dlg.get_by_label("Goal", exact=True).locator("option").all_inner_texts() == ["Grow installs", "Ship sync"]     # by priority; no General
    assert dlg.get_by_label("Priority", exact=True).input_value() == "high"                          # the first goal's priority
    dlg.get_by_label("Goal", exact=True).select_option("ship-sync")
    assert dlg.get_by_label("Priority", exact=True).input_value() == "normal"                        # follows the goal until the person picks one
    dlg.get_by_label("Your idea").fill("Dark mode please")
    dlg.get_by_label("Priority", exact=True).select_option("high")
    dlg.get_by_role("button", name="Add", exact=True).click()
    pg.locator(".board-card", has_text="Dark mode please").wait_for(timeout=WAIT_MS)
    assert adds(host) == [{"text": "Dark mode please", "track": "ship-sync", "priority": "high"}]
    pg.get_by_role("button", name="New idea").click()                                               # closed with text: tonight's queue
    pg.get_by_label("Your idea").fill("Later idea")
    pg.get_by_role("button", name="Close", exact=True).click()
    pg.locator(".board-card", has_text="Later idea").wait_for(timeout=WAIT_MS)
    assert adds(host)[-1] == {"text": "Later idea", "track": "grow", "priority": "high", "night": True}
    pg.get_by_role("button", name="New idea").click()                                               # closed empty: nothing
    pg.get_by_role("dialog", name="New idea").wait_for(timeout=WAIT_MS)
    before = len(adds(host))
    pg.keyboard.press("Escape")
    pg.wait_for_function("() => !document.querySelector('[role=dialog]')", timeout=WAIT_MS)
    pg.wait_for_timeout(200)
    assert len(adds(host)) == before
    pg.get_by_role("button", name="New idea").click()                                               # Esc with text in it too
    pg.get_by_label("Your idea").fill("Saved by Esc")
    pg.keyboard.press("Escape")
    pg.locator(".board-card", has_text="Saved by Esc").wait_for(timeout=WAIT_MS)
    assert adds(host)[-1]["night"] is True and adds(host)[-1]["text"] == "Saved by Esc"


def test_with_no_goal_yet_new_idea_opens_new_goal_first_and_then_itself_with_that_goal(shell):
    pg, host = shell
    host.goals.pop("grow"), host.goals.pop("ship-sync")
    host.bump({})
    pg.wait_for_function("() => document.querySelectorAll('.board-goals__select option').length === 1", timeout=WAIT_MS)
    pg.get_by_role("button", name="New idea").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    dlg.get_by_label("Description").fill("Make notes searchable.")
    dlg.get_by_role("button", name="Save goal").click()
    idea = pg.get_by_role("dialog", name="New idea")
    idea.wait_for(timeout=WAIT_MS)
    assert idea.get_by_label("Goal", exact=True).input_value() == "make-notes"


def test_the_goal_select_filters_needs_you_and_the_ideas_and_shows_the_summary_open_and_edit(shell):
    pg, host = shell
    assert pg.locator(".board-need:not(.board-proposal)").count() == 4 and pg.locator(".board-proposal").count() == 1      # all goals: one list
    assert pg.locator(".board-goals__select option").all_inner_texts()[0] == "All goals"
    assert pg.locator(".board-card", has_text="Dark mode").count() == 1
    pg.get_by_label("Goal", exact=True).select_option("grow")
    assert pg.locator(".board-need:not(.board-proposal)").count() == 1 and "Grow installs" in pg.locator(".board-need").first.inner_text()
    assert pg.locator(".board-proposal").count() == 1
    assert pg.locator(".board-card").count() == 0                                                    # the ideas of the other goal are filtered out
    assert "More people try Orkline." in pg.locator(".board-goals__one").inner_text()                # the Summary's first line
    pg.get_by_label("Goal", exact=True).select_option("ship-sync")
    assert pg.locator(".board-goals__line").inner_text() == "Sync is the first thing a second device needs."
    assert pg.locator(".board-card", has_text="Dark mode").count() == 1 and pg.locator(".board-proposal").count() == 0
    pg.get_by_role("button", name="Open goal Ship sync").click()
    pg.locator(".shell-goal").wait_for(timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.goal", {"slug": "ship-sync"}))
    pg.get_by_role("button", name="Edit goal Ship sync").click()
    assert pg.get_by_role("dialog", name="Edit goal").is_visible()
    pg.keyboard.press("Escape")


def test_the_target_chip_shows_and_sets_the_boards_one_target(shell):
    pg, host = shell
    chip = pg.get_by_role("button", name="Target: Balance")
    assert chip.is_visible()
    chip.click()
    menu = pg.get_by_role("menu", name="Target")
    assert menu.get_by_role("menuitemradio").count() == 3
    assert "lighter models, less reasoning, no proposals at night" in menu.inner_text()
    assert "heavier models, more reasoning, three proposals a night" in menu.inner_text()
    assert menu.get_by_role("menuitemradio", name="Balance").get_attribute("aria-checked") == "true"
    menu.get_by_role("menuitemradio", name="Thrift").click()
    pg.get_by_role("button", name="Target: Thrift").wait_for(timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.board_set", {"target": "thrift"})) and pg.get_by_role("menu").count() == 0
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.get_by_role("button", name="Target: Thrift").click()
        pg.screenshot(path=str(SHOTS / "desktop-board-target-1440x900.png"))


def test_a_high_idea_shows_a_spinner_and_stop_leaves_it_stopped_a_low_one_waits_for_tonight(shell):
    pg, host = shell
    pg.get_by_role("button", name="New idea").click()
    pg.get_by_label("Your idea").fill("Fast one")
    pg.get_by_role("dialog").get_by_label("Priority", exact=True).select_option("high")
    pg.get_by_role("button", name="Add", exact=True).click()
    row = pg.locator(".board-card-row", has_text="Fast one")
    row.wait_for(timeout=WAIT_MS)
    assert "drafting" in row.inner_text() and row.locator(".shell-spin").count() == 1 and "High" in row.inner_text()
    row.get_by_role("button", name="Stop: Fast one").click()
    pg.wait_for_function("() => document.querySelector('.board-card-row .board-state')?.innerText.includes('stopped') || true")
    row.get_by_text("stopped").wait_for(timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.read_stop", {"slug": "fast-one"})) and row.locator(".shell-spin").count() == 0
    assert row.get_by_role("button", name="Process now: Fast one").is_visible() and row.get_by_role("button", name="Tonight: Fast one").is_visible()
    row.get_by_role("button", name="Tonight: Fast one").click()                                    # Tonight puts a stopped one back
    row.get_by_text("tonight").wait_for(timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.queue", {"slug": "fast-one", "queue": "night"}))
    low = pg.locator(".board-card-row", has_text="Offline mode")                                    # a Low one: tonight, Process now and Delete
    assert "tonight" in low.inner_text()
    assert [b.inner_text() for b in low.locator(".board-card__acts .ork-btn").all()] == ["Process now", "Delete"]
    low.get_by_role("button", name="Process now: Offline mode").click()
    assert _sent(pg, host, ("ideas.queue", {"slug": "offline", "queue": "now"}))
    row.get_by_role("button", name="Delete: Fast one").click()                                      # Delete asks first
    row.get_by_role("button", name="Keep it").click()
    assert ("ideas.drop", {"slug": "fast-one"}) not in host.log
    row.get_by_role("button", name="Delete: Fast one").click()
    row.get_by_role("button", name="Delete it: Fast one").click()
    row.wait_for(state="detached", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.drop", {"slug": "fast-one"}))
    start = pg.locator(".board-card-row", has_text="Dark mode")                                     # a plan that starts at night: Start now
    start.get_by_role("button", name="Start now: Dark mode").click()
    assert _sent(pg, host, ("ideas.start_now", {"slug": "dark"}))
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.screenshot(path=str(SHOTS / "desktop-board-rows-1440x900.png"))


def test_needs_you_is_one_list_the_questions_one_form_and_a_proposal_is_answered_in_its_row(shell):
    pg, host = shell
    kinds = pg.locator(".board-need, .board-proposal").evaluate_all("els => els.map(e => e.dataset.kind)")
    assert kinds == ["todo", "plan", "asks", "goal", "proposal"]                                    # the host's order; proposals last
    assert "Sync ideas between the phone and the town" in pg.locator(".board-need").first.inner_text() and "API_KEY" in pg.locator(".board-need").first.inner_text()
    assert "export" not in pg.locator(".board-ideas").inner_text().lower() and "Search the notes" not in pg.locator(".board-ideas").inner_text()    # each idea in one place
    pg.locator(".board-need[data-kind=asks]").click()                                              # the spec's questions: a box each, one Send
    dlg = pg.get_by_role("dialog", name="Questions: Search the notes")
    dlg.get_by_label("Answer 2: Do tags count?").wait_for(timeout=WAIT_MS)
    assert dlg.get_by_role("button", name="Send").count() == 1
    dlg.get_by_label("Answer 1: Which fields count?").fill("title and text")
    dlg.get_by_label("Answer 2: Do tags count?").fill("yes")
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.screenshot(path=str(SHOTS / "desktop-questions-1440x900.png"))
    dlg.get_by_role("button", name="Send").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.answer", {"slug": "search", "answers": ["title and text", "yes"]}))
    pg.wait_for_function("() => document.querySelectorAll('.board-need[data-kind=asks]').length === 0", timeout=WAIT_MS)
    pg.locator(".board-need[data-kind=goal]").click()                                              # a goal that asks
    pg.get_by_role("dialog", name="Questions: Grow installs").get_by_label("Answer 1: Which channel first?").fill("npm")
    pg.get_by_role("dialog").get_by_role("button", name="Send").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.answer", {"slug": "grow", "answers": ["npm"], "goal": True}))
    prop = pg.locator(".board-proposal")                                                           # a proposal: Take with a priority, or No with a reason
    assert prop.get_by_label("Priority of Tag the notes").input_value() == "high"                    # the goal's
    prop.get_by_label("Priority of Tag the notes").select_option("low")
    prop.get_by_role("button", name="Take: Tag the notes").click()
    pg.wait_for_function("() => document.querySelectorAll('.board-proposal').length === 0", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.proposal", {"slug": "tags", "take": True, "priority": "low"}))


def test_a_proposal_declined_with_a_reason_or_without(shell):
    pg, host = shell
    prop = pg.locator(".board-proposal")
    prop.get_by_role("button", name="No: Tag the notes").click()
    prop.get_by_label("Why not: Tag the notes").fill("not now")
    prop.get_by_role("button", name="Decline: Tag the notes").click()
    pg.wait_for_function("() => document.querySelectorAll('.board-proposal').length === 0", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.proposal", {"slug": "tags", "take": False, "reason": "not now"}))


def test_the_spec_shows_its_sections_and_stages_with_each_tasks_live_state(shell):
    pg, host = shell
    pg.locator(".board-card", has_text="Sync ideas").click()
    stages = pg.locator(".shell-preview .board-sec[data-name=Stages]")
    stages.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-preview .board-sec").evaluate_all("els => els.map(e => e.dataset.name)") == SECTIONS
    stages.locator("summary").click()
    waves = stages.locator(".board-stages__wave")
    assert waves.count() == 3 and waves.nth(1).locator(".board-stages__task").count() == 2           # k2 ∥ k3
    state = lambda k: stages.locator(f".board-stages__task[data-task={k}] .board-stages__state").inner_text()
    assert "merged" in state("k1") and "at Review" in state("k2") and "working" in state("k3") and "at Review" in state("k4")
    host.plan["tasks"][2]["state"] = "held"
    host.plan["tasks"][4]["state"] = "failed"
    host.bump({})
    pg.wait_for_function("() => document.querySelector('[data-task=k3] .board-stages__state')?.innerText.includes('held')", timeout=WAIT_MS)
    assert "held" in state("k3")
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.screenshot(path=str(SHOTS / "desktop-spec-stages-1440x900.png"))


def test_a_file_todo_shows_its_steps_and_uploads_the_file_and_a_secret_shows_its_steps_too(shell, tmp_path):
    pg, host = shell
    pg.locator(".board-need[data-kind=todo]").click()                                               # steps on any kind: a secret has them too
    dlg = pg.get_by_role("dialog", name="API_KEY")
    assert "The sync service needs it" in dlg.inner_text() and dlg.locator("ol li").all_inner_texts() == ["Open the console", "Copy the key"]
    dlg.get_by_label("Value of API_KEY").fill("sk-1")
    dlg.get_by_role("button", name="Keep it").click()
    assert _sent(pg, host, ("ideas.todo", {"idea": "sync", "id": "t1", "done": True, "value": "sk-1"}))
    host.needs = None
    todo = {"id": "t2", "title": "The Firebase config, google-services.json", "kind": "file", "why": "The app signs in with it",
            "steps": ["Open the Firebase console", "Download google-services.json"], "accept": ["json"], "choices": [], "done": False}
    original = host.needs_you
    host.needs_you = lambda: [{"kind": "todo", "idea": "sync", "goal": "ship-sync", "title": "Sync ideas", "text": todo["title"], "priority": "normal",
                               "blocks": True, "at": "2026-10-18T09:00:00", "todo": todo}] + original()[1:]
    host.bump({})
    pg.locator(".board-need[data-kind=todo]").wait_for(timeout=WAIT_MS)
    pg.locator(".board-need[data-kind=todo]").first.click()
    dlg = pg.get_by_role("dialog", name="The Firebase config, google-services.json")
    assert dlg.locator("ol li").all_inner_texts() == ["Open the Firebase console", "Download google-services.json"]
    assert dlg.get_by_role("button", name="Send the file").is_disabled()
    assert dlg.get_by_label("File: The Firebase config, google-services.json").get_attribute("accept") == ".json"
    f = tmp_path / "google-services.json"
    f.write_text('{"project": "x"}')
    dlg.get_by_label("File: The Firebase config, google-services.json").set_input_files(str(f))
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.screenshot(path=str(SHOTS / "desktop-file-todo-1440x900.png"))
    dlg.get_by_role("button", name="Send the file").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    sent = _calls(pg, host, "ideas.todo", 2)[-1]                                                     # the secret's, then the file's
    import base64
    assert sent["id"] == "t2" and sent["done"] is True and sent["file"]["name"] == "google-services.json"
    assert base64.b64decode(sent["file"]["data"]) == b'{"project": "x"}' and "value" not in sent
    pg.locator(".board-need[data-kind=todo]").first.click()                                         # a file over 5 MB is refused in the dialog
    big = tmp_path / "big.json"
    big.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    dlg = pg.get_by_role("dialog", name="The Firebase config, google-services.json")
    dlg.get_by_label("File: The Firebase config, google-services.json").set_input_files(str(big))
    assert "larger than 5 MB" in dlg.inner_text() and dlg.get_by_role("button", name="Send the file").is_disabled()


def test_the_gear_holds_start_plans_by_themselves_and_the_night(shell):
    pg, host = shell
    pg.get_by_role("button", name="Settings").click()
    dlg = pg.get_by_role("dialog", name="Settings")
    box_ = dlg.get_by_role("checkbox", name="Start plans by themselves")
    assert box_.is_checked() and dlg.get_by_label("Night from").input_value() == "01:00" and dlg.get_by_label("Night to").input_value() == "07:00"
    dlg.get_by_text("Start plans by themselves").click()
    assert _sent(pg, host, ("ideas.board_set", {"autostart": False}))
    dlg.get_by_label("Night from").fill("23:30")
    dlg.get_by_label("Night from").blur()
    assert _sent(pg, host, ("ideas.board_set", {"night": "23:30-07:00"}))


def test_agents_chips_say_by_itself_tonight_and_why_a_task_is_held(shell):
    pg, host = shell
    chips = pg.locator(".shell-agents .shell-chip")
    k3 = chips.filter(has_text="Retry on a lost signal")
    assert "by itself" in k3.inner_text() and "working" in k3.inner_text().lower()
    assert "by itself" not in chips.filter(has_text="Add the queue").inner_text()
    night = chips.filter(has_text="Dark palette")
    assert "tonight" in night.inner_text().lower()
    held = chips.filter(has_text="Write the notes")
    assert "keeps your reserve · after 18:00" in held.inner_text().lower()
    files = chips.filter(has_text="Write the export")
    assert "waits for sync ideas between the phone and the town · same files" in files.inner_text().lower()
    host_chip = next(c for c in [files])                                                             # after the wait: beside
    assert host_chip.count() == 1
    if os.environ.get("ORKCRAFT_SHOTS"):
        handle = box(pg, ".shell-split")                                    # Agents taller, so its held chips show
        pg.mouse.move(handle["x"] + 40, handle["y"] + 2)
        pg.mouse.down()
        pg.mouse.move(handle["x"] + 40, handle["y"] - 200, steps=5)
        pg.mouse.up()
        pg.screenshot(path=str(SHOTS / "desktop-agents-chips-1440x900.png"))


def test_agents_add_an_agent_edit_it_and_give_it_a_task_type(shell):
    pg, host = shell
    agents = pg.locator(".shell-agents")
    assert "taskmaster" in agents.inner_text().lower() and "task types" not in agents.inner_text().lower()      # spec 36 §5: a monitor
    agents.get_by_role("button", name="+ Add agent").click()
    dlg = pg.get_by_role("dialog", name="Add agent")
    dlg.get_by_label("Name").fill("Docs scribe")
    dlg.get_by_label("Model").select_option("laborer")
    dlg.get_by_label("At most at once").select_option("3")
    dlg.get_by_label("Instruction").fill("Write plainly.")
    dlg.get_by_role("button", name="Save agent").click()
    pg.locator(".shell-role[data-slug='docs-scribe']").wait_for(timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.role_save", {"name": "Docs scribe", "model": "laborer", "max_parallel": 3, "instruction": "Write plainly.", "kinds": [], "craft": "engineering"}))
    pg.get_by_role("button", name="Edit Docs scribe").click()                                       # a type given in its dialog (Takes)
    pg.get_by_role("dialog", name="Edit agent").get_by_label("Docs").check()
    pg.get_by_role("button", name="Save agent").click()
    pg.get_by_role("dialog").wait_for(state="detached", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.role_save", {"slug": "docs-scribe", "name": "Docs scribe", "model": "laborer", "max_parallel": 3, "instruction": "Write plainly.", "kinds": ["docs"], "craft": "engineering"}))
    pg.get_by_role("button", name="Edit Docs scribe").click()                                        # Edit, then Delete says what moves back
    dlg = pg.get_by_role("dialog", name="Edit agent")
    assert dlg.get_by_label("Instruction").input_value() == "Write plainly."
    dlg.get_by_role("button", name="Delete…").click()
    assert "back to Grunt" in dlg.inner_text() and "docs" in dlg.inner_text().lower()
    dlg.get_by_role("button", name="Delete agent").click()
    pg.locator(".shell-role[data-slug='docs-scribe']").wait_for(state="detached", timeout=WAIT_MS)
    pg.get_by_role("button", name="Edit Taskmaster").click()                                         # the built-ins: edit, never delete
    builtin = pg.get_by_role("dialog", name="Edit agent")
    builtin.get_by_label("Name").wait_for(timeout=WAIT_MS)
    assert builtin.get_by_label("Name").input_value() == "Taskmaster" and builtin.get_by_role("button", name="Delete…").count() == 0
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.keyboard.press("Escape")
        pg.wait_for_function("() => !document.querySelector('[role=dialog]')", timeout=WAIT_MS)
        handle = box(pg, ".shell-split")                                    # Agents taller, so its task types show
        pg.mouse.move(handle["x"] + 40, handle["y"] + 2)
        pg.mouse.down()
        pg.mouse.move(handle["x"] + 40, handle["y"] - 300, steps=5)
        pg.mouse.up()
        pg.screenshot(path=str(SHOTS / "desktop-agents-1440x900.png"))


def test_every_dialog_has_a_dimmed_backdrop_an_opaque_panel_and_closes_on_esc(shell):
    pg, host = shell
    opens = [("New goal", lambda: pg.get_by_role("button", name="New goal").click()),
             ("New idea", lambda: pg.get_by_role("button", name="New idea").click()),
             ("Add agent", lambda: pg.get_by_role("button", name="+ Add agent").click()),
             ("Settings", lambda: pg.get_by_role("button", name="Settings").click()),
             ("Merge into", lambda: pg.locator(".shell-into").get_by_role("button", name="Merge into dev").click()),
             ("Drop this result?", lambda: pg.locator(".shell-card", has_text="Add the queue").get_by_role("button", name="Drop…").click())]
    for name, opener in opens:
        opener()
        dlg = pg.get_by_role("dialog", name=name)
        dlg.wait_for(timeout=WAIT_MS)
        back = pg.locator(".shell-backdrop")
        shade = back.evaluate("e => getComputedStyle(e).backgroundColor")
        alpha = float(shade.split(",")[3].strip(" )")) if shade.startswith("rgba") else (1.0 if shade.startswith("rgb(") else 0.0)
        assert 0.2 < alpha < 0.9, (name, shade)                                                       # dimmed, not transparent, not black
        panel = dlg.evaluate("e => getComputedStyle(e).backgroundColor")
        assert panel.startswith("rgb(") or panel.endswith(", 1)"), (name, panel)                      # opaque
        bb, db = back.bounding_box(), dlg.bounding_box()
        assert bb["width"] == 1440 and bb["height"] == 900 and db["x"] > 0 and db["x"] + db["width"] < 1440
        assert dlg.get_by_role("button", name="Close", exact=True).is_visible()
        for _ in range(12):                                                                           # Tab keeps the focus inside
            pg.keyboard.press("Tab")
        assert dlg.evaluate("e => e.contains(document.activeElement)"), name
        pg.keyboard.press("Escape")
        pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)


def test_pair_a_phone_from_the_gear_shows_the_qr_the_time_left_how_it_reaches_and_forget(shell):
    pg, host = shell
    pg.get_by_role("button", name="Settings").click()
    pg.get_by_role("button", name="Pair a phone").click()
    dlg = pg.get_by_role("dialog", name="Pair a phone")
    dlg.locator("img.gui-phones__qr").wait_for(timeout=WAIT_MS)
    assert dlg.locator("img.gui-phones__qr").is_visible() and _sent(pg, host, ("phones.pair", {}))
    text = dlg.inner_text()
    assert "good for" in text and "On this Wi-Fi" in text and "Anywhere on your tailnet: studio.tail1234.ts.net" in text
    assert "Pixel 8" in text                                                                          # the paired phones, with Forget
    dlg.get_by_role("button", name="Forget").click()
    dlg.get_by_text("No phone is paired yet.").wait_for(timeout=WAIT_MS)
    assert _sent(pg, host, ("phones.forget", {"id": "p1"}))
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.screenshot(path=str(SHOTS / "desktop-pair-1440x900.png"))
    pg.keyboard.press("Escape")
    for _ in range(20):
        if ("phones.pair_stop", {}) in host.log:
            break
        pg.wait_for_timeout(100)
    assert _sent(pg, host, ("phones.pair_stop", {}))                                                       # closing voids a code not used
    assert pg.get_by_role("button", name="Settings").evaluate("e => e === document.activeElement")    # the focus is back on the gear
