"""The v1 shell on a phone (gui/static/pwa/board.js, shell-*.js; docs/specs/33-v1-shell.md §6, §8): Chromium at 390 × 844, paired
over the phone listener, against a stub that answers the §5 commands. Three tabs with their counts; the preview (an idea's spec,
a plan, a task, a result's code) on its own screen with Back and its actions pinned at the foot; no horizontal scroll of the
page. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import asyncio
import copy
import datetime as dt
import os
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

from orkboard.gui import pairing, phone_tls  # noqa: E402
from orkboard.gui.board_host import BoardPhone  # noqa: E402
from orkboard.realm import library, plans  # noqa: E402
from tests.test_phones import _listening, _serve  # noqa: E402
from tests.browser_kit import CHROMIUM, WAIT_MS, spki  # noqa: E402

_TODAY = dt.date.today().isoformat()                 # a reset today reads "resets at 18:00", whatever the day
_IN_TWO_DAYS = (dt.date.today() + dt.timedelta(days=2)).isoformat()

SHOTS = Path(__file__).resolve().parent.parent / "docs" / "design" / "img" / "v1"
SECTIONS = ["Gist", "Why", "In", "Out", "Risks", "Open questions", "Estimate", "Stages", "Decisions"]
GREEN = {"passed": 20, "failed": 0, "failing": [], "tail": "20 passed", "green": True}
RED = {"passed": 10, "failed": 10, "failing": ["tests/test_sync.py::test_retry", "tests/test_sync.py::test_queue"], "tail": "10 failed", "green": False}
LONG = "+" + "x" * 300
PATCH = f"diff --git a/sync.py b/sync.py\n@@ -1,2 +1,3 @@\n keep = 1\n-old = 2\n+new = 3\n{LONG}\n"


def task(tid, title, state, after=(), **more):
    return {"id": tid, "title": title, "brief": f"Brief of {title}", "tier": "warrior", "after": list(after), "state": state,
            "branch": f"idea/sync/{tid}", "commit": "", "session": "s", "cost": 0.42, "tokens": 10, "started": "", "finished": "2026-10-17T10:00:00",
            "error": "", "note": "", "round": 1, "tests": None, "diff": None, "conflict": "", "why": "", **more}


class Stub:
    """The host's §5 commands over a few ideas in memory."""

    def __init__(self) -> None:
        self.rev = 1
        self.calls: list[tuple[str, dict]] = []
        self.into, self.push = "dev", False
        self.target, self.autostart, self.night = "balance", True, "01:00-07:00"
        self.chip_extra: dict[str, dict] = {}              # spec 35 §11.5: a chip's by / night / state / note / waits_title, by task id
        self.checks: list[dict] = []                      # the idea's checks (realm/idea_checks.py `status`), the sync idea's
        self.extra_needs: list[dict] = []                 # spec 35: what a test adds to Needs you (a proposal, a goal's questions)
        self.todos = [{"idea": "sync", "id": "t1", "title": "API_KEY", "kind": "secret", "why": "The sync service needs it", "choices": [],
                       "steps": [], "done": False}]
        self.plan = {"idea": "sync", "estimate": {"tasks": 5, "usd_low": 1.2, "usd_high": 3.5}, "passed_at": "x",
                     "todos": [{**self.todos[0], "for": ["k2", "k3"]}],
                     "tasks": [task("k1", "Read the sync code", "merged", tag="Research"),
                               task("k2", "Add the queue", "review", ["k1"], tests=GREEN, diff={"files": 14, "added": 320, "removed": 41}, tag="Code"),
                               task("k3", "Retry on a lost signal", "running", ["k2"], tag="Code"),
                               task("k4", "Test it offline", "review", ["k3"], tests=RED, round=2, diff={"files": 3, "added": 12, "removed": 0},
                                    conflict="conflicts with dev in a.py, b.py", tag="Tests"),
                               task("k5", "Write the notes", "waiting", ["k4"], tag="Text for people")]}   # tag: ideas_roles `_with_heads`
        self.ideas = {"sync": self.idea("sync", "Sync ideas between the phone and the town", "working", 0),
                      "dark": self.idea("dark", "Dark mode", "plan", 1, in_needs_you=True)}
        self.goals = {"general": self.goal("general", "General", "normal", "ready")}
        self.roles = {"taskmaster": {"slug": "taskmaster", "name": "Taskmaster", "model": "elder", "max_parallel": 1, "instruction": "", "builtin": True},
                      "grunt": {"slug": "grunt", "name": "Grunt", "model": "", "max_parallel": 8, "instruction": "", "builtin": True}}
        self.kinds = {k: "grunt" for k in ("code", "tests", "docs", "text", "research")}
        self.week: dict[str, dict] = {}                   # spec 36 §2: a role's week by slug
        self.spend: dict | None = None                    # spec 36 §2: what ideas.spend returns (None: an error)

    @staticmethod
    def idea(slug, title, state, order, **more):
        return {"slug": slug, "title": title, "track": "general", "order": order, "state": state, "size": "M", "talk": [], "priority": "normal",
                "queue": "", "held_until": "", "risk": "", "risk_triggers": [], "depends_on": [], "waits_on": [], "start_at": "",
                "in_needs_you": False, **more}

    @staticmethod
    def goal(slug, title, priority, state, **more):
        return {"slug": slug, "title": title, "about": "", "criteria": [], "deadline": "", "order": 0, "count": 2, "priority": priority, "metrics": [],
                "links": [], "summary": "", "questions": [], "state": state, "error": "", **more}

    def commands(self) -> dict:
        names = ("board", "page", "review_list", "agents", "task", "diff", "merge", "back", "drop_task", "stop_task", "into", "todo", "say",
                 "plan", "start", "stop", "move", "add", "drop", "log", "logs", "goal_save", "goal", "read_now", "roles", "role_save", "role_drop",
                 "kind_set", "doc", "queue", "read_stop", "start_now", "proposal", "board_set", "answer", "spend", "words")
        return {f"ideas.{n}": (lambda a, n=n: self.run(f"ideas.{n}", a)) for n in names}

    def results(self):
        return [{"idea": "sync", "idea_title": self.ideas["sync"]["title"], "task": t["id"], "title": t["title"], "round": t["round"], "tests": t["tests"],
                 "diff": t["diff"], "cost": t["cost"], "conflict": t["conflict"], "finished": t["finished"]} for t in self.plan["tasks"] if t["state"] == "review"]

    def find(self, a):
        return next(t for t in self.plan["tasks"] if t["id"] == a["task"])

    def bump(self, result):
        self.rev += 1
        return result

    def run(self, name, a):
        device = a.get("device")                      # the listener adds it to every board command (BoardPhone.guard)
        assert device == "phone"
        assert a.get("link") == "paired"              # the listener adds it for a paired phone (spec 35 §9): a file to-do needs it
        a = {k: v for k, v in a.items() if k != "link" and (k != "device" or name == "ideas.log")}
        self.calls.append((name, dict(a)))
        if name == "ideas.board":
            ideas = [i | {"thesis": "Gist in one line", "asks": 0, "updated": "", "progress": {"done": 1, "total": 5} if i["slug"] == "sync" else {"done": 0, "total": 0}}
                     for i in self.ideas.values()]
            needs = [{"kind": "plan", "idea": "dark", "goal": "general", "title": "Dark mode", "text": "Plan ready · 5 tasks", "priority": "normal", "blocks": False, "at": ""}]
            for t in self.todos:
                if not t["done"]:
                    needs.append({"kind": "todo", "idea": t["idea"], "goal": "general", "title": t["title"], "text": t["title"], "priority": "normal", "blocks": True,
                                  "at": "", "todo": {k: t.get(k) for k in ("id", "title", "kind", "why", "choices", "steps", "accept", "done")}})
            return {"tracks": list(self.goals.values()), "ideas": ideas, "needs_you": needs + self.extra_needs,
                    "target": self.target, "autostart": self.autostart, "night": self.night, "rev": self.rev, "demo": False}
        if name == "ideas.page":
            i = self.ideas[a["slug"]]
            return {"slug": i["slug"], "title": i["title"], "track": "general", "state": i["state"], "size": "M",
                    "sections": [{"name": n, "thesis": f"{n} in one line", "text": f"{n} in one line\nAnd the {n} at length."} for n in SECTIONS],
                    "talk": [], "plan": copy.deepcopy(self.plan) if a["slug"] == "sync" else None, "busy": False,
                    "checks": copy.deepcopy(self.checks) if a["slug"] == "sync" else []}
        if name == "ideas.review_list":
            return {"into": self.into, "push": self.push, "branches": ["dev", "main"], "results": self.results()}
        if name == "ideas.agents":
            chips = [{"idea": "sync", "idea_title": self.ideas["sync"]["title"], "task": t["id"], "title": t["title"], "state": t["state"], "tier": "warrior", "note": "",
                      "by": "person", "night": False} | self.chip_extra.get(t["id"], {})
                     for t in self.plan["tasks"] if t["state"] in ("running", "review", "held")]
            blocks = [{"role": "taskmaster", "name": "Taskmaster", "model": "elder", "max_parallel": 1, "builtin": True, "spend_today": 0, "state": "waiting",
                       "waits_on": {"idea": "dark", "text": "waiting for your answers on “Dark mode”"}, "chips": [],
                       "week": self.week.get("taskmaster")},
                      {"role": "grunt", "name": "Grunts", "model": "", "max_parallel": 8, "builtin": True, "spend_today": 1.25, "chips": chips,
                       "kinds": [k for k, r in self.kinds.items() if r == "grunt"], "week": self.week.get("grunt")}]
            blocks += [{"role": r["slug"], "name": r["name"], "model": r["model"], "max_parallel": r["max_parallel"], "builtin": False, "spend_today": 0,
                        "chips": [], "kinds": [k for k, x in self.kinds.items() if x == r["slug"]], "week": self.week.get(r["slug"])} for r in self.roles.values() if not r["builtin"]]
            return {"roles": blocks, "done_today": [{"idea": "sync", "task": "k1", "title": "Read the sync code", "role": "grunt"}]}
        if name == "ideas.roles":
            names = {"code": "Code", "tests": "Tests", "docs": "Docs", "text": "Text for people", "research": "Research"}
            return {"roles": [{"instruction_long": "", "hand_model": False} | r | {"spend_today": 0} for r in self.roles.values()],
                    "kinds": [{"kind": k, "label": names[k], "role": r} for k, r in self.kinds.items()],
                    "models": [{"id": "", "label": "By Target"}, {"id": "elder", "label": "Elder · opus"},
                               {"id": "warrior", "label": "Warrior · sonnet"}, {"id": "laborer", "label": "Laborer · haiku"}],
                    "library": library.listed(), "suggested": library.SUGGESTED, "tier_costs": dict(plans.DEFAULT_COST)}                  # the host's own library
        if name == "ideas.role_save":
            slug = a.get("slug") or a["name"].lower().replace(" ", "-")
            self.roles[slug] = {"slug": slug, "name": a["name"], "model": a["model"], "max_parallel": a["max_parallel"],
                                "instruction": a.get("instruction", ""), "builtin": slug in ("taskmaster", "grunt")}
            if "kinds" in a:                              # spec 36 §3: a type another agent had moves here, an unticked one goes back to Grunt
                self.kinds = {k: slug if k in a["kinds"] else ("grunt" if r == slug else r) for k, r in self.kinds.items()}
            return self.bump({"slug": slug})
        if name == "ideas.role_drop":
            self.roles.pop(a["slug"])
            self.kinds = {k: ("grunt" if r == a["slug"] else r) for k, r in self.kinds.items()}
            return self.bump({"ok": True})
        if name == "ideas.kind_set":
            self.kinds[a["kind"]] = a["role"]
            return self.bump({"ok": True})
        if name == "ideas.goal_save":
            about = a["about"]
            slug = a.get("slug") or "-".join(about.lower().replace(".", "").split()[:3])
            old = self.goals.get(slug, {})
            self.goals[slug] = self.goal(slug, a.get("title") or old.get("title") or " ".join(about.split()[:3]), a["priority"], "reading", about=about,
                                         metrics=old.get("metrics", []), links=old.get("links", []), craft=a.get("craft", "engineering"),
                                         race={"design": "elf", "data": "goblin", "marketing": "gnome"}.get(a.get("craft"), "peon"),
                                         team=a.get("team", old.get("team", [])))
            return self.bump({"slug": slug})
        if name == "ideas.goal":
            g = self.goals[a["slug"]]
            return g | {"description": g["about"], "talk": [], "busy": g["state"] == "reading", "sections": []}
        if name == "ideas.read_now":
            self.ideas[a["slug"]]["state"] = "ready"
            return self.bump({"ok": True})
        if name == "ideas.doc":
            return {"path": a["path"], "text": f"The text of {a['path']}", "truncated": False}
        if name == "ideas.task":
            return self.find(a) | {"idea": a["slug"], "idea_title": self.ideas["sync"]["title"], "log": "== round 1\nreading sync.py\n"}
        if name == "ideas.diff":
            return {"base": self.into, "branch": f"idea/sync/{a['task']}", "commits": [{"sha": "9f2c41d7e0", "subject": "k2: add the queue"}],
                    "files": [{"path": "sync.py", "added": 2, "removed": 1, "patch": PATCH}, {"path": "huge.json", "added": 9000, "removed": 0, "patch": None}],
                    "truncated": True}
        if name == "ideas.merge":
            self.find(a)["state"] = "merged"
            return self.bump({"ok": True, "commit": "abc"})
        if name == "ideas.back":
            self.find(a).update(state="running", round=self.find(a)["round"] + 1)
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
        if name == "ideas.todo":
            self.todos[0]["done"] = a["done"]
            return self.bump({"ok": True})
        if name == "ideas.words":
            g = self.goals.get(a["track"], {})
            return {"track": a["track"], "words": [g.get("title", ""), "Offline mode", "offline", "SyncQueue", "sync_queue.py"]}
        if name == "ideas.add":
            assert a.get("track") and a["track"] != "general", "An idea needs a goal"
            slug = a["text"].lower().replace(" ", "-")
            queue = "night" if a["priority"] == "low" or a.get("night") else "now"
            self.ideas[slug] = self.idea(slug, a["text"], "raw", 9, queue=queue, priority=a["priority"], track=a["track"])
            return self.bump({"slug": slug, "queue": queue})
        if name == "ideas.queue":
            self.ideas[a["slug"]]["queue"] = a["queue"]
            return self.bump({"ok": True})
        if name == "ideas.read_stop":
            self.ideas[a["slug"]].update(state="raw", queue="hold")
            return self.bump({"ok": True})
        if name == "ideas.start_now":
            self.ideas[a["slug"]].update(state="working", start_at="")
            return self.bump({"ok": True})
        if name == "ideas.proposal":
            self.extra_needs = [n for n in self.extra_needs if n["idea"] != a["slug"]]
            return self.bump({"ok": True})
        if name == "ideas.answer":
            self.extra_needs = [n for n in self.extra_needs if n.get("goal") != a["slug"] and n.get("idea") != a["slug"]]
            return self.bump({"ok": True})
        if name == "ideas.board_set":
            self.target, self.autostart, self.night = a.get("target", self.target), a.get("autostart", self.autostart), a.get("night", self.night)
            return self.bump({"target": self.target, "autostart": self.autostart, "night": self.night})
        if name == "ideas.spend":
            return self.spend if self.spend is not None else {"error": "No such idea"}
        if name == "ideas.logs":
            import base64
            return {"name": "orkline-logs.zip", "data": base64.b64encode(b"PK-not-a-real-zip").decode()}
        if name == "ideas.log":
            return {"ok": True}
        return self.bump({"ok": True})


@asynccontextmanager
async def _phone(repo: Path, monkeypatch, init: str = ""):
    """The phone paired with a served Orkboard whose Board is the stub's; `init`: a script run before the app's (a browser API stood in)."""
    stub = Stub()
    real = BoardPhone.phone_snapshot

    def snap(host):
        s = real(host)
        return {**s, "rev": f"{s['rev']}-{stub.rev}", "focus": "board", "ideas_rev": stub.rev, "needs_you": 2, "look": "camp",
                "review_count": len(stub.results()),
                "limits": [{"provider": "claude", "name": "Claude", "left": 0.62,
                            "rows": [{"window": "5h", "left": 0.62, "reset": f"{_TODAY}T18:00"}, {"window": "week", "left": 0.8, "reset": f"{_IN_TWO_DAYS}T09:00"}]},
                           {"provider": "agy", "name": "Antigravity", "left": 0.15, "rows": [{"window": "daily", "left": 0.15, "reset": ""}]},
                           {"provider": "codex", "name": "Codex", "left": None, "error": "Not logged in", "rows": []}]}   # turned on, not read
    monkeypatch.setattr(BoardPhone, "phone_snapshot", staticmethod(snap))   # the stub's commands are the Board's: a phone's
    # A script taps faster than a person, and each change of the Board costs the phone four commands to draw again: the
    # limit of a few a second (gui/pairing.py, tests/test_phones.py) is not what these tests check.
    monkeypatch.setattr(pairing.Bucket, "take", lambda self, now=None: True)
    server, task_ = await _serve(repo)
    server.host.commands.update(stub.commands())
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        async with pw.async_playwright() as p:
            flags = [f"--ignore-certificate-errors-spki-list={spki(phone_tls.paths(server.phones.cert_folder)[0])}"]
            try:
                browser = await (p.chromium.launch(executable_path=CHROMIUM, args=flags) if CHROMIUM else p.chromium.launch(args=flags))
            except Exception as e:                         # noqa: BLE001 — no browser here
                pytest.skip(f"no Chromium for Playwright here: {e}")
            try:
                ctx = await browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, ignore_https_errors=True)
                if init:
                    await ctx.add_init_script(init)
                page = await ctx.new_page()
                errors: list[str] = []
                page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
                await page.goto(f"{server.phones.address}/app/#pair={offer['code']}")
                await page.locator(".board-tabs").wait_for(timeout=WAIT_MS)
                yield stub, page
                assert not errors, "\n".join(errors)
            finally:
                await browser.close()
    finally:
        server.stop()
        await asyncio.wait_for(task_, 10)


async def _shot(page, name: str) -> None:
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(SHOTS / f"{name}.png"))


async def _called(stub, name, args=None, timeout=5.0):
    """The stub got this command (a command goes over the phone's socket and the listener: it takes a moment)."""
    for _ in range(int(timeout * 20)):
        if any(c[0] == name and (args is None or c[1] == args) for c in stub.calls):
            return True
        await asyncio.sleep(0.05)
    return False


async def _pick_goal(page, slug):
    """The goal shown, picked in the top bar: its chip opens the Goals sheet, a row shows that goal ("" All goals, "ops" Operations)."""
    await page.locator(".board-bar .goal-chip").click()
    sheet = page.get_by_role("dialog", name="Goals")
    await sheet.locator(f'.goal-row[data-goal="{slug}"]').click()
    await sheet.wait_for(state="hidden", timeout=WAIT_MS)


async def _goal_row(page, slug):
    """The goal's row in the top bar's Goals sheet, read and the sheet put back (its text: craft · priority · state)."""
    await page.locator(".board-bar .goal-chip").click()
    sheet = page.get_by_role("dialog", name="Goals")
    row = sheet.locator(f'.goal-row[data-goal="{slug}"]')
    await row.wait_for(timeout=WAIT_MS)
    text = await row.inner_text()
    await page.keyboard.press("Escape")
    await sheet.wait_for(state="hidden", timeout=WAIT_MS)
    return text


async def _new_goal(page):
    """New goal: at the foot of the top bar's Goals sheet."""
    await page.locator(".board-bar .goal-chip").click()
    await page.get_by_role("dialog", name="Goals").get_by_role("button", name="New goal").click()


async def _wizard(sheet, craft="engineering"):
    """New goal's first two steps: a craft, and its team as suggested; the third, what it is for, is open after."""
    await sheet.locator(f'.craft-tile[data-craft="{craft}"]').click()
    await sheet.get_by_role("button", name="Next").click()


async def _needs(page):
    """Needs you: its screen, opened with the top bar's !."""
    await page.locator(".board-bar .needs-chip").click()
    await page.locator(".needs-pane").wait_for(timeout=WAIT_MS)


async def _stop_all(page):
    """Stop all, in the gear's sheet."""
    await page.locator(".board-bar").get_by_role("button", name="Settings").click()
    await page.get_by_role("dialog", name="Settings").get_by_role("button", name="Stop all").click()


NO_SCROLL = "document.documentElement.scrollWidth <= 390 && document.body.scrollWidth <= 390"
SMALL = """() => [...document.querySelectorAll('.board button, .board input, .board textarea, .screen button, .screen input')]
    .filter((b) => b.offsetParent && !b.closest('[hidden]') && !b.matches('.sec-head *')).map((b) => [b.textContent || b.getAttribute('aria-label'), b.getBoundingClientRect().height])
    .filter(([, h]) => h < 43)"""


@pytest.mark.asyncio
async def test_three_tabs_with_their_counts_the_top_bar_and_no_camp(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        tabs = page.locator(".board-tabs")
        assert [await b.get_attribute("aria-label") for b in await tabs.get_by_role("tab").all()] == ["Board", "Agents", "Review, 2"]
        assert await page.evaluate("document.documentElement.dataset.look") == "office"        # the phone's look is camp: not here
        assert await page.locator(".dock, .camp, .grid, .head").count() == 0
        top = page.locator(".board-bar")
        assert await top.get_by_role("button", name="Settings").is_visible() and "Stop all" not in await top.inner_text()   # one line: the gear holds it
        assert "General" in await top.locator(".goal-chip").inner_text()                                # the goal shown: General holds the ideas here
        assert await top.locator(".needs-chip").get_attribute("aria-label") == "Needs you, 2"            # ! says what waits, every goal's
        chip = top.locator(".limit-chip")
        assert "15 %" in await chip.inner_text() and "is-warn" in await chip.get_attribute("class")      # the smallest of all tools
        await chip.click()
        sheet = page.get_by_role("dialog", name="What is left")
        await sheet.wait_for(timeout=WAIT_MS)
        assert "Claude" in await sheet.inner_text() and "resets at 18:00" in await sheet.inner_text()
        assert "Codex · limits not read" in await sheet.inner_text() and "Not logged in" in await sheet.inner_text()
        await sheet.get_by_role("button", name="Close").click()
        await page.locator(".idea-card").first.wait_for(timeout=WAIT_MS)
        await _shot(page, "phone-board-390x844")
        await _needs(page)
        await page.get_by_role("heading", name="Needs you").wait_for(timeout=WAIT_MS)
        await _shot(page, "phone-needs-you-390x844")
        await tabs.get_by_role("tab").nth(1).click()
        await page.locator(".chip", has_text="Retry on a lost signal").wait_for(timeout=WAIT_MS)
        assert "waiting for your answers" in await page.locator(".agents").inner_text() and "Done today (1)" in await page.locator(".agents").inner_text()
        await _shot(page, "phone-agents-390x844")
        await tabs.get_by_role("tab").nth(2).click()
        await page.locator(".result").first.wait_for(timeout=WAIT_MS)
        await _shot(page, "phone-review-390x844")
        for tab in range(3):
            await tabs.get_by_role("tab").nth(tab).click()
            assert await page.evaluate(NO_SCROLL)
        await tabs.get_by_role("tab").nth(0).click()
        assert await page.evaluate(SMALL) == []
        await _stop_all(page)
        await page.get_by_role("button", name="Stop every ork").click()
        await page.get_by_role("dialog", name="Stop all").wait_for(state="hidden", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_an_idea_a_todo_a_chip_and_a_result_each_open_on_their_own_screen_with_back(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _needs(page)
        await page.locator(".need-plan", has_text="Dark mode").click()                                # a plan waiting (Needs you, not Ideas) → its spec
        screen = page.locator(".screen")
        await screen.locator(".sec").first.wait_for(timeout=WAIT_MS)
        box = await screen.bounding_box()
        assert box["x"] == 0 and box["y"] == 0 and box["width"] == 390 and box["height"] == 844       # its own full screen
        assert await screen.locator(".sec").count() == len(SECTIONS) and "spec" in (await screen.locator(".screen-head").inner_text()).lower()
        await _shot(page, "phone-spec-390x844")
        bar = await screen.locator(".screen-bar").bounding_box()
        assert abs(bar["y"] + bar["height"] - 844) < 2                                                 # the actions pinned at the foot
        assert "Start · 5 tasks" in await screen.locator(".screen-bar").inner_text() or "Start" in await screen.locator(".screen-bar").inner_text()
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "idea", "ref": "dark", "device": "phone"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await page.locator(".screen").wait_for(state="hidden", timeout=WAIT_MS)
        assert await page.locator(".needs-pane").is_visible()                                         # back on the screen it came from

        await page.locator(".need-todo", has_text="API_KEY").click()                                  # a to-do → its sheet → the plan, scrolled to it
        await page.get_by_role("dialog", name="To-do").get_by_role("button", name="Open the plan").click()
        target = page.locator(".screen .plan-todo.is-target")
        await target.wait_for(timeout=WAIT_MS)
        assert "tasks k2 and k3 wait for it" in await target.inner_text()
        await page.go_back()                                                                           # the system back gesture
        await page.locator(".screen").wait_for(state="hidden", timeout=WAIT_MS)

        await page.get_by_role("tab", name="Agents").click()                                           # a chip → its task, with Stop pinned
        await page.locator(".chip", has_text="Retry on a lost signal").click()
        await page.locator(".screen .log").wait_for(timeout=WAIT_MS)
        text = await page.locator(".screen-body").inner_text()
        assert "Brief of Retry on a lost signal" in text and "reading sync.py" in text and "idea/sync/k3" in text
        await _shot(page, "phone-task-390x844")
        await page.locator(".screen-bar").get_by_role("button", name="Stop").click()
        assert await _called(stub, "ideas.stop_task", {"slug": "sync", "task": "k3"})
        await page.get_by_role("button", name="Back", exact=True).click()
        assert (await page.locator(".board-tab.is-active").text_content()).startswith("Agents")


@pytest.mark.asyncio
async def test_review_merge_is_off_on_red_send_back_needs_a_line_and_a_patch_scrolls_inside_its_box(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.get_by_role("tab", name="Review").click()
        green, red = page.locator(".result", has_text="Add the queue"), page.locator(".result", has_text="Test it offline")
        assert "20 / 20 passed" in await green.inner_text() and "14 files, +320 −41" in await green.inner_text()
        assert "10 / 20 failed" in await red.inner_text() and "round 2" in await red.inner_text() and "conflicts with dev in a.py, b.py" in await red.inner_text()
        merge = red.get_by_role("button", name="Merge into dev")
        assert await merge.is_disabled() and "red" in await red.locator(".why").inner_text()
        await red.get_by_role("button", name="Fix", exact=True).click()                                # Fix: the line prefilled, required
        line = red.get_by_label("What to fix, in one line")
        assert (await line.input_value()).startswith("Resolve the conflict with dev")
        await line.fill("")
        assert await red.locator(".back-line .ork-btn.primary").is_disabled()
        await line.fill("Rebase and keep both queues")
        await red.locator(".back-line .ork-btn.primary").click()
        assert await _called(stub, "ideas.back", {"slug": "sync", "task": "k4", "why": "Rebase and keep both queues"})
        await page.locator(".result", has_text="Test it offline").wait_for(state="detached", timeout=WAIT_MS)

        await page.locator(".ork-btn.into").click()                              # Merge into ▾: the branches
        sheet = page.get_by_role("dialog", name="Merge into")
        await sheet.get_by_role("radio", name="main").click()
        assert await _called(stub, "ideas.into", {"branch": "main"})
        await green.get_by_role("button", name="Drop…").click()                                        # Drop asks first, apart from Merge
        drop = page.get_by_role("dialog", name="Drop this result?")                                    # … on a sheet (spec 34 §5)
        await drop.wait_for(timeout=WAIT_MS)
        await drop.get_by_role("button", name="Keep it").click()
        await drop.wait_for(state="hidden", timeout=WAIT_MS)
        assert ("ideas.drop_task", {"slug": "sync", "task": "k2"}) not in stub.calls

        await green.locator(".result-open").click()                                                     # the code on its own screen
        screen = page.locator(".screen")
        await screen.locator(".commits").wait_for(timeout=WAIT_MS)
        await screen.locator(".file", has_text="sync.py").locator("summary").click()
        patch = screen.locator(".patch")
        await patch.wait_for(timeout=WAIT_MS)
        assert await screen.locator(".pl.is-add").count() == 2 and await screen.locator(".pl.is-del").count() == 1
        assert await patch.evaluate("(el) => el.scrollWidth > el.clientWidth")                         # it scrolls sideways in its own box …
        assert await page.evaluate(NO_SCROLL) and await page.evaluate("document.querySelector('.screen-body').scrollWidth <= 390")   # … never the page
        await screen.locator(".file", has_text="huge.json").locator("summary").click()
        await screen.get_by_text("Too large to show.", exact=True).wait_for(timeout=WAIT_MS)
        await _shot(page, "phone-result-390x844")
        bar = screen.locator(".screen-bar")
        bb = await bar.bounding_box()
        assert abs(bb["y"] + bb["height"] - 844) < 2 and await bar.get_by_role("button", name="Merge into main").is_enabled()
        await bar.get_by_role("button", name="Merge into main").click()
        await screen.wait_for(state="hidden", timeout=WAIT_MS)
        assert ("ideas.merge", {"slug": "sync", "task": "k2"}) in stub.calls
        await page.locator(".result").first.wait_for(state="detached", timeout=WAIT_MS)                 # the list drawn again
        assert await page.get_by_role("tab", name="Review").locator(".count").count() == 1 and await page.locator(".result").count() == 0


@pytest.mark.asyncio
async def test_a_secret_todo_is_entered_over_the_paired_link_on_the_board(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _needs(page)
        await page.locator(".need-todo", has_text="API_KEY").click()                                    # a to-do's sheet (spec 35 §9)
        sheet = page.get_by_role("dialog", name="To-do")
        await sheet.wait_for(timeout=WAIT_MS)
        assert "The sync service needs it" in await sheet.inner_text()                                 # its why
        assert await sheet.locator("input").first.get_attribute("type") == "password"
        await sheet.locator("input").first.fill("s3cret")
        await sheet.get_by_role("button", name="Store it").click()
        await page.locator(".need-todo").wait_for(state="detached", timeout=WAIT_MS)
        assert ("ideas.todo", {"idea": "sync", "id": "t1", "done": True, "value": "s3cret"}) in stub.calls
        await page.get_by_role("tab", name="Board").click()
        await page.get_by_role("button", name="New idea", exact=True).click()                           # no goal yet: New goal opens first (spec 35 §3)
        goal = page.get_by_role("dialog", name="New goal")
        await _wizard(goal)
        await goal.get_by_label("Description").fill("Offline first")
        await goal.get_by_role("button", name="Save goal").click()
        idea = page.get_by_role("dialog", name="New idea")                                              # … then New idea, with that goal
        await idea.wait_for(timeout=WAIT_MS)
        assert await idea.get_by_label("Goal").input_value() == "offline-first"
        await idea.get_by_label("The idea").fill("Offline mode")
        await idea.get_by_role("button", name="Add").click()
        assert await _called(stub, "ideas.add", {"text": "Offline mode", "track": "offline-first", "priority": "normal"})


@pytest.mark.asyncio
async def test_the_gear_downloads_the_days_logs_on_the_phone_and_tabs_are_logged(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.get_by_role("tab", name="Agents").click()
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "tab", "ref": "agents", "device": "phone"})
        await page.get_by_role("button", name="Settings").click()
        sheet = page.get_by_role("dialog", name="Settings")
        await sheet.wait_for(timeout=WAIT_MS)
        assert "Download today's logs" in await sheet.text_content()                          # a heading: in capitals on the page
        async with page.expect_download() as got:
            await sheet.get_by_role("button", name="Today", exact=True).click()
        download = await got.value
        assert download.suggested_filename == "orkline-logs.zip"
        assert await _called(stub, "ideas.logs", {"days": 1})



# -- spec 34 round 2 on the phone: sheets, goals, ideas now or later, agents by task type, the top bar -------------------------

def _adds(stub):
    return [a for n, a in stub.calls if n == "ideas.add"]


@pytest.mark.asyncio
async def test_the_top_bar_is_one_line_with_no_band_above_it_and_the_gear_shows_spend_whole(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        bar = await page.locator(".board-bar").bounding_box()
        assert bar["y"] == 0 and bar["x"] == 0 and bar["width"] == 390                                  # no empty band above it
        assert bar["height"] < 80                                                                       # one line
        await page.locator(".board-bar").get_by_role("button", name="Settings").click()
        spend = page.get_by_role("dialog", name="Settings").locator(".board-spend")
        text = await spend.inner_text()
        assert "Spend today" in text and "…" not in text and "..." not in text                          # the whole of today's spend
        assert await spend.evaluate("e => e.scrollWidth <= e.clientWidth + 1 && getComputedStyle(e).textOverflow !== 'ellipsis'")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_every_sheet_is_dimmed_closes_on_esc_and_keeps_its_buttons_at_its_foot(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["ship"] = stub.goal("ship", "Ship v1", "normal", "ready")           # New idea needs a goal (spec 35 §3)
        stub.bump({})
        await page.get_by_role("button", name="New idea", exact=True).wait_for(timeout=WAIT_MS)
        await _goal_row(page, "ship")
        opens = [("New goal", lambda: _new_goal(page)),
                 ("New idea", lambda: page.get_by_role("button", name="New idea", exact=True).click()),
                 ("Settings", lambda: page.get_by_role("button", name="Settings").click()),
                 ("Goals", lambda: page.locator(".board-bar .goal-chip").click()),
                 ("Stop all", lambda: _stop_all(page))]
        for name, opener in opens:
            await opener()
            sheet = page.get_by_role("dialog", name=name)
            await sheet.wait_for(timeout=WAIT_MS)
            shade = await sheet.evaluate("e => getComputedStyle(e, '::backdrop').backgroundColor")
            assert shade.startswith("rgba(") and 0.2 < float(shade.split(",")[3].strip(" )")) < 0.9, (name, shade)          # dimmed
            assert await sheet.evaluate("e => getComputedStyle(e).backgroundColor") not in ("rgba(0, 0, 0, 0)", "transparent")  # opaque panel
            box = await sheet.bounding_box()
            assert box["x"] == 0 and box["width"] == 390 and box["y"] + box["height"] == 844                # from the bottom, full width
            assert await page.evaluate(NO_SCROLL)
            await page.keyboard.press("Escape")
            await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        await _new_goal(page)                                                                           # the buttons are pinned at the foot
        sheet = page.get_by_role("dialog", name="New goal")
        await sheet.locator('.craft-tile[data-craft="design"]').click()
        foot = await sheet.locator(".sheet-foot").bounding_box()
        assert foot["y"] + foot["height"] >= 844 - 2
        await page.keyboard.press("Escape")


@pytest.mark.asyncio
async def test_new_goal_sheet_description_and_priority_then_the_goal_reads_and_shows_its_summary(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _new_goal(page)
        sheet = page.get_by_role("dialog", name="New goal")
        await _wizard(sheet, "marketing")                                                               # its craft, its team as suggested
        assert await sheet.get_by_role("button", name="Save goal").is_disabled()                        # a description is required
        assert await sheet.get_by_label("Title").count() == 0                                            # no title to type on a new goal
        assert await sheet.get_by_label("Metric 1: what is measured").count() == 0 and await sheet.get_by_label("Deadline").count() == 0
        await sheet.get_by_label("Description").fill("More people try Orkline.")
        await sheet.get_by_role("radio", name="High").click()
        await _shot(page, "phone-new-goal-390x844")
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save", {"about": "More people try Orkline.", "craft": "marketing",
                                                       "team": ["copywriter", "growth"], "every": [], "priority": "high"})
        screen = page.locator(".screen")
        await screen.get_by_text("the Taskmaster is reading", exact=False).first.wait_for(timeout=WAIT_MS)      # the goal on its own screen: reading
        stub.goals["more-people-try"].update(title="Grow installs", state="asks", summary="Installs are the first step.\nMore lines.", questions=["Which channel first?"],
                                             links=["docs/plan.md", "https://example.com/post"],
                                             metrics=[{"name": "weekly installs", "target": "50", "how": "npm downloads, per week"}])
        stub.bump({})
        await screen.get_by_text("Installs are the first step.").first.wait_for(timeout=WAIT_MS)
        text = await screen.inner_text()
        assert "npm downloads, per week" in text and "Which channel first?" in text and "asks you" in text
        await screen.get_by_label("Answer the Taskmaster").fill("npm first")
        await screen.get_by_role("button", name="Send", exact=True).click()
        assert await _called(stub, "ideas.say", {"slug": "more-people-try", "text": "npm first", "goal": True})
        await screen.get_by_role("button", name="docs/plan.md").click()                                 # a repository path opens on a screen
        await screen.get_by_text("The text of docs/plan.md").wait_for(timeout=WAIT_MS)
        await screen.get_by_role("button", name="← Back to the goal").click()
        assert await screen.get_by_role("link", name="https://example.com/post").get_attribute("target") == "_blank"
        await screen.get_by_role("button", name="Edit goal", exact=True).click()                        # Edit: the sheet is filled, with the title to correct
        sheet = page.get_by_role("dialog", name="Edit goal")
        assert await sheet.get_by_label("Title").input_value() == "Grow installs"
        assert await sheet.get_by_label("Description").input_value() == "More people try Orkline."
        await sheet.get_by_label("Title").fill("Grow weekly installs")
        await sheet.get_by_role("button", name="Save goal").click()
        assert await _called(stub, "ideas.goal_save", {"slug": "more-people-try", "about": "More people try Orkline.", "craft": "marketing", "priority": "high",
                                                       "title": "Grow weekly installs"})
        await screen.get_by_text("Grow weekly installs").first.wait_for(timeout=WAIT_MS)                # saved: the goal's screen again
        await page.get_by_role("button", name="Back", exact=True).click()
        await screen.wait_for(state="hidden", timeout=WAIT_MS)
        text = await _goal_row(page, "more-people-try")                                                 # the top bar's goals: title, craft · priority · state
        assert "Grow weekly installs" in text and "Marketing · High · reading" in text
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_new_idea_sheet_a_goal_a_priority_one_add_closed_with_text_and_closed_empty(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["ship"] = stub.goal("ship", "Ship v1", "high", "ready")
        stub.goals["docs"] = stub.goal("docs", "Docs", "low", "ready")
        stub.bump({})
        await _goal_row(page, "docs")
        await page.get_by_role("button", name="New idea", exact=True).click()
        sheet = page.get_by_role("dialog", name="New idea")
        assert await sheet.get_by_label("Goal").input_value() == "ship"                                 # the first by priority; General is not listed
        assert "General" not in await sheet.get_by_label("Goal").inner_text()
        assert await sheet.get_by_role("radio", name="High").is_checked()                               # the goal's priority
        assert await sheet.get_by_role("button", name="Add").is_visible() and await sheet.get_by_role("button", name="Later").count() == 0
        await sheet.get_by_label("Goal").select_option("docs")
        assert await sheet.get_by_role("radio", name="Low").is_checked()
        await sheet.get_by_label("The idea", exact=True).fill("Dark mode please")
        await sheet.get_by_role("radio", name="High").click()
        await _shot(page, "phone-new-idea-390x844")
        await sheet.get_by_role("button", name="Add").click()
        card = page.locator(".idea-card", has_text="Dark mode please")
        await card.wait_for(timeout=WAIT_MS)
        assert _adds(stub) == [{"text": "Dark mode please", "track": "docs", "priority": "high"}]
        await page.get_by_role("button", name="New idea", exact=True).click()                           # Low → the night
        await page.get_by_role("dialog", name="New idea").get_by_label("Goal").select_option("docs")
        await page.get_by_label("The idea", exact=True).fill("Low idea")
        await page.get_by_role("dialog", name="New idea").get_by_role("button", name="Add").click()
        low = page.locator(".idea-card", has_text="Low idea")
        await low.wait_for(timeout=WAIT_MS)
        assert _adds(stub)[-1] == {"text": "Low idea", "track": "docs", "priority": "low"}
        assert "tonight" in await low.inner_text()
        assert await low.get_by_role("button", name="Process now: Low idea").is_visible() and await low.get_by_role("button", name="Delete: Low idea").is_visible()
        await page.get_by_role("button", name="New idea", exact=True).click()                           # closed with text: kept for tonight
        await page.get_by_label("The idea", exact=True).fill("Closed with text")
        await page.get_by_role("dialog", name="New idea").get_by_role("button", name="Close").click()
        await page.locator(".idea-card", has_text="Closed with text").wait_for(timeout=WAIT_MS)
        assert _adds(stub)[-1]["night"] is True and _adds(stub)[-1]["text"] == "Closed with text"
        await page.get_by_role("button", name="New idea", exact=True).click()                           # Esc with text: tonight too
        await page.get_by_label("The idea", exact=True).fill("Saved by Esc")
        await page.keyboard.press("Escape")
        await page.locator(".idea-card", has_text="Saved by Esc").wait_for(timeout=WAIT_MS)
        assert _adds(stub)[-1]["night"] is True
        before = len(_adds(stub))                                                                       # closed empty: nothing
        await page.get_by_role("button", name="New idea", exact=True).click()
        await page.get_by_role("dialog", name="New idea").get_by_role("button", name="Close").click()
        await page.wait_for_timeout(300)
        assert len(_adds(stub)) == before
        await low.get_by_role("button", name="Process now: Low idea").click()                           # Process now → the queue is now
        assert await _called(stub, "ideas.queue", {"slug": "low-idea", "queue": "now"})


@pytest.mark.asyncio
async def test_agents_add_an_agent_give_it_a_task_type_edit_and_delete_it(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.get_by_role("tab", name="Agents").click()
        agents = page.locator(".agents")
        await agents.get_by_role("button", name="+ Add agent").wait_for(timeout=WAIT_MS)
        assert "Task types" not in await agents.inner_text()                                            # spec 36 §5: the section is gone
        await agents.get_by_role("button", name="+ Add agent").click()
        sheet = page.get_by_role("dialog", name="Add agent")
        await sheet.get_by_label("Name").fill("Docs scribe")
        await sheet.get_by_label("Model").select_option("laborer")
        await sheet.get_by_label("At most at once").select_option("3")
        await sheet.get_by_label("Instruction").fill("Write plainly.")
        await sheet.get_by_label("Docs", exact=True).check()                                            # a type given in the dialog (spec 36 §3)
        await sheet.get_by_role("button", name="Save agent").click()
        assert await _called(stub, "ideas.role_save", {"name": "Docs scribe", "model": "laborer", "max_parallel": 3, "instruction": "Write plainly.",
                                                        "kinds": ["docs"], "craft": "engineering"})
        await agents.locator(".role[data-slug='docs-scribe']").wait_for(timeout=WAIT_MS)
        assert "Takes: docs" in await agents.locator(".role[data-slug='docs-scribe']").inner_text()
        await agents.get_by_role("button", name="Edit Docs scribe").click()
        sheet = page.get_by_role("dialog", name="Edit agent")
        assert await sheet.get_by_label("Instruction").input_value() == "Write plainly."
        await sheet.get_by_role("button", name="Delete…").click()
        assert "back to Grunt" in await sheet.inner_text()
        await sheet.get_by_role("button", name="Delete agent").click()
        await agents.locator(".role[data-slug='docs-scribe']").wait_for(state="detached", timeout=WAIT_MS)
        assert stub.kinds["docs"] == "grunt"
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_pair_a_phone_in_the_gear_says_where_it_is_done_and_how_the_phone_reaches_the_computer(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.get_by_role("button", name="Settings").click()
        await page.get_by_role("button", name="Pair a phone").click()
        sheet = page.get_by_role("dialog", name="Pair a phone")
        await sheet.wait_for(timeout=WAIT_MS)
        text = await sheet.inner_text()
        assert "On the same Wi-Fi" in text and "tailnet" in text and "Install Tailscale" in text and "from the computer" in text
        await _shot(page, "phone-pair-390x844")
        assert await page.evaluate(NO_SCROLL)
