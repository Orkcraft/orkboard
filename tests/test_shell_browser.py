"""The v1 shell on the desktop (docs/specs/33-v1-shell.md §6–§7), in a real browser at 1 440 × 900 against a stub host that
answers the §5 commands: the Board on the left, the preview in the centre (the Map: its ideas carry their results, spec 48) and Agents under it as VS Code's
terminal. A click on an idea, a to-do, a chip and a result opens the right preview; Merge is off on red with its reason; Send
back needs its line; no camp. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import re
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from orkboard.realm import library, plans, roles  # noqa: E402

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


_HEAD = {"craft": "engineering", "race": "peon", "tier": "warrior"}
LEAD = {"slug": "taskmaster", "name": "Taskmaster", "head": {"craft": "engineering", "race": "peon", "tier": "elder"}}
PARTY = {"ideas": 9, "leader": {"slug": "product-manager", "name": "Product manager", "head": {"craft": "product", "race": "lich", "tier": "elder"}, "usd": 4.1},
         "members": [{"slug": "grunt", "name": "Grunt", "head": _HEAD, "tasks": 14, "merged": 13, "first_time": 12, "usd": 9.2}],
         "checks": [{"by": "accessibility-reviewer", "name": "Accessibility reviewer", "head": {"craft": "design", "race": "elf", "tier": "warrior"}, "applied": 6,
                     "skipped": 1, "clean": 4, "caught": 2, "left": 1, "before": 2, "usd": 1.8},
                    {"by": "reviewer", "name": "Reviewer", "head": _HEAD, "applied": 1, "skipped": 0, "clean": 1, "caught": 0, "left": 0, "before": 0, "usd": None}]}
PARTY_LINES = ["Product manager (leads): ≈$4.10 for the party, the drafts and the plans", "Grunt: 14 tasks, 12 merged the first time · ≈$9.20",
               "Accessibility reviewer: checked 6 goals: 4 clean, caught 2 (1 left) · ≈$1.80 · skipped 1 · 2 ended without findings",
               "Reviewer: checked 1 goal: 1 clean, caught 0"]
def party_price(a, learned=True, hints=()):
    """What `ideas.party_price` answers for a party (spec 43 §3): $0.35 a check, about half of the ideas, all of them with `every`."""
    from orkboard.realm import library
    checks = [{"by": s, "name": library.get(s).name, "usd": 0.35, "share": 1.0 if s in (a.get("every") or []) else 0.5, "every": s in (a.get("every") or [])}
              for s in a.get("team") or [] if library.get(s) is not None and library.get(s).check is not None]
    return {"low": 1.9, "high": 5.7, "learned": learned, "ideas": 12 if learned else 0, "checks": checks, "hints": list(hints)}


SAVED = "/home/me/Downloads/orkboard-logs-2026-10-19-120000.zip"            # what logs.save answers

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
        self.chip_extra: dict[str, dict] = {}             # spec 41 §3: a chip's short / idea_short, by task id
        self.usd_task: dict[str, float | None] = {}       # spec 41 §8: a role's cost a task by slug (`usd_task`)
        self.record: dict[str, dict | None] = {}          # spec 42 §4: a role's record of the last 30 days by slug (`record`)
        self.check_week: dict[str, dict] = {}             # spec 43 §4.1: a checker's check of the last 7 days by slug (`check_week`)
        self.party_rows: list[dict] = []                  # spec 43 §4.2: Needs you's `party` rows
        self.told = {"taskmaster": "The Taskmaster reads each step's prompt.", "grunt": "A Grunt gets the task's brief and the repository."}
        self.limits = [{"provider": "claude", "name": "Claude", "left": 0.62,
                        "rows": [{"window": "5h", "left": 0.62, "reset": f"{_TODAY}T18:00"}, {"window": "week", "left": 0.8, "reset": f"{_IN_TWO_DAYS}T09:00"}]},
                       {"provider": "agy", "name": "Antigravity", "left": 0.15, "rows": [{"window": "daily", "left": 0.15, "reset": ""}]},
                       {"provider": "codex", "name": "Codex", "left": None, "error": "Not logged in", "rows": []}]   # turned on, not read
        self.ideas = {"sync": self.idea("sync", "Sync ideas between the phone and the town", "working", 0),
                      "dark": self.idea("dark", "Dark mode", "plan", 1, start_at="night"),
                      "offline": self.idea("offline", "Offline mode", "raw", 2, queue="night"),
                      "export": self.idea("export", "Export notes", "plan", 3, in_needs_you=True),
                      "search": self.idea("search", "Search the notes", "asks", 4, in_needs_you=True),
                      "tags": self.idea("tags", "Tag the notes", "proposed", 5, in_needs_you=True, track="grow")}
        self.goals["grow"] = self.goal("grow", "Grow installs", "high", "ready", order=2, summary="More people try Orkline.", questions=["Which channel first?"])
        self.proposals, self.asked, self.todo_log = [], [], []
        self.lens = {"lenses": [{"id": "text"}], "default": "text", "segments": [], "screens": []}    # ideas.lens
        self.unplanned = False                        # sync's spec says no plan yet (its tasks stay on the Board)
        self.checks = [{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "passed", "task": "k1", "tier": "elder"},   # sync's
                       {"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": False, "why": "It changes no screen", "state": "",
                        "task": "", "tier": "warrior"}]
        self.parts: list[dict] = []                                                                  # ideas.lens_code
        self.screen_png = ""                                                                         # ideas.lens_screen
        self.party = copy.deepcopy(PARTY)                                                            # ideas.party (spec 43 B)
        self.hints: list[str] = []                                                                   # ideas.party_price's hints (spec 43 E)
        self.own: list[dict] = []                                                                    # ideas.parties (spec 43 F)
        self.goal_notes: list[str] = []                                                              # what ideas.goal_save says besides its slug
        self.learned = True                                                                          # ideas.party_price: learned from the project's ideas, or a first guess
        self.reserve = {"share": 0.1, "night": False}                                                # the snapshot's reserve (spec 49 §2.3)
        self.rate = None                                                                             # what 1 % of the five-hour window costs (decisions §82)
        self.week: dict[str, dict | None] = {}                                                       # ideas.agents: a role's week by slug (spec 49 §5.2)
        self.harness: dict[str, dict] = {}                                                           # ideas.agents: the tool a role runs on, by slug
        self.gate_doc = {"into": "dev", "main": "main", "same": False, "commits": 3, "files": 7,       # ideas.gate (spec 49 §2.1)
                         "ideas": [{"slug": "export", "title": "Export notes", "goal": "ship-sync", "tasks": 3}]}
        self.today_events: list[dict] = [                                                            # ideas.today (spec 49 §2.2)
            {"at": "12:40", "mark": "✓", "tone": "ok", "words": "merged into dev", "title": "Read the sync code", "goal": "ship-sync", "idea": "sync", "task": "k1",
             "open": {"kind": "result", "slug": "sync", "task": "k1"}},
            {"at": "12:10", "mark": "↺", "tone": "muted", "words": "sent back", "title": "Add the queue", "goal": "ship-sync", "idea": "sync", "task": "k2",
             "open": {"kind": "result", "slug": "sync", "task": "k2"}},
            {"at": "11:55", "mark": "✗", "tone": "danger", "words": "failed", "title": "Secure cookie flags", "goal": "grow", "idea": "tags", "task": "k1",
             "open": {"kind": "task", "slug": "tags", "task": "k1"}},
            {"at": "10:30", "mark": "▸", "tone": "ink", "words": "the work started", "title": "Sync ideas between the phone and the town", "goal": "ship-sync", "idea": "sync",
             "task": "", "open": {"kind": "idea", "slug": "sync"}},
            {"at": "09:00", "mark": "✓", "tone": "ok", "words": "dev merged into main", "title": "dev → main", "goal": "", "idea": "", "task": "", "open": {"kind": "gate", "slug": ""}}]

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
               base | {"kind": "goal", "idea": "", "goal": "grow", "title": "Grow installs", "text": "Which channel first?", "priority": "high",
                       "questions": self.goals.get("grow", {}).get("questions", []),
                       **({"asked": self.goals["grow"]["asked"]} if self.goals.get("grow", {}).get("asked") else {})},
               base | {"kind": "proposal", "idea": "tags", "goal": "grow", "title": "Tag the notes", "text": "Tags make a long list findable."}]
        gone = set(self.proposals) | set(self.asked)            # answered: out of the list
        return [n for n in out if (n["idea"] or n["goal"]) not in gone] + self.party_rows

    def goal(self, slug, title, priority, state, order=1, **more):
        return {"slug": slug, "title": title, "about": "", "criteria": [], "deadline": "", "order": order, "count": 0, "priority": priority,
                "metrics": [], "links": [], "summary": "", "questions": [], "state": state, "state_error": "", **more}

    @staticmethod
    def leader(slug):
        """A goal's leader as the host serves it (gui/ideas_goals.py `_goal_row`): None when not said."""
        from orkboard.realm import library, roles
        a = library.get(slug or "")
        if a is None:
            return None
        return {"slug": a.id, "name": a.name, "head": {"craft": a.craft, "race": roles.RACES[a.craft], "tier": a.tier}}

    def kind_list(self):
        names = {"code": "Code", "tests": "Tests", "docs": "Docs", "text": "Text for people", "research": "Research"}
        return [{"kind": k, "label": names[k], "role": r} for k, r in self.kinds.items()]

    def results(self):
        return [{"idea": "sync", "idea_title": "Sync ideas between the phone and the town", "task": t["id"], "title": t["title"], "round": t["round"],
                 "tests": t["tests"], "diff": t["diff"], "cost": t["cost"], "conflict": t["conflict"], "finished": t["finished"],
                 **({"check": t["check"], "findings": t["findings"]} if "check" in t else {})}       # spec 43 A: a check's result
                for t in self.plan["tasks"] if t["state"] == "review"]

    def snapshot(self):
        return {"t": "state", "state": {
            "focus": "board", "ideas_rev": self.rev, "look": self.look, "project": "orkline", "demo": False, "onboarding": self.onboarding or False,
            "words": [], "resources": {}, "orkspaces": [], "buildings": [], "roads": [], "alerts": [], "score": {},
            "limits": self.limits, "reserve": self.reserve, "rate": self.rate, "review_count": len(self.results()), "needs_you": 1,
            "hud": {"gold": "$2.40", "show_gold": True, "lumber": "120k"}}}

    def page(self, slug):
        if slug not in self.ideas:
            return {"error": "That goal is gone"}
        i = self.ideas[slug]
        secs = [{"name": n, "thesis": f"{n} in one line", "text": f"{n}: the longer text of this section."} for n in SECTIONS]
        if slug == "sync":
            next(x for x in secs if x["name"] == "Stages")["text"] = STAGES
        if slug == "search":
            next(x for x in secs if x["name"] == "Open questions")["text"] = "- Which fields count?\n- Do tags count?"
        return {"slug": slug, "title": i["title"], "track": "general", "state": i["state"], "size": "M", "sections": secs, "talk": i["talk"],
                "plan": self.plan if slug == "sync" and not self.unplanned else None, "busy": False, "state_error": i.get("state_error", ""), "lens": i.get("lens", []),
                "checks": self.checks if slug == "sync" else []}

    def find(self, a):
        return next(t for t in self.plan["tasks"] if t["id"] == a["task"])

    def map_doc(self):
        """`ideas.map` as spec 48 §1 and spec 49 §2.4 have it, for the shell's stub: the ideas of its goals; sync's tasks in waves and its
        results at Review; a party of a leader, a builder and a checker."""
        wave, tasks = {}, []
        for t in [] if self.unplanned else self.plan["tasks"]:
            wave[t["id"]] = 1 + max([wave[a] for a in t["after"] if a in wave], default=0)
            check = bool(t.get("check"))
            tasks.append({"id": t["id"], "title": t["title"], "short": t["title"], "state": t["state"], "after": t["after"], "tier": t["tier"], "head": _HEAD,
                          "by": {"slug": "reviewer" if check else "grunt", "name": "Reviewer" if check else "Grunts"}, "band": "check" if check else "build",
                          "wave": wave[t["id"]], "tag": "Code", "error": t["error"], "note": t["note"], "round": t["round"], "cost": t["cost"],
                          "started": t["started"] or (dt.datetime.now() - dt.timedelta(minutes=4)).isoformat(timespec="seconds") if t["state"] == "running" else t["started"]})
        nodes = []
        for i in self.ideas.values():
            if i["track"] == "general":
                continue
            sync = i["slug"] == "sync"
            need = {"asks": "asks", "plan": "plan", "proposed": "proposal"}.get(i["state"], "") if i["in_needs_you"] else ""
            asked = [{"ask": "Which fields count?", "choices": [], "pick": None, "why": "", "by": LEAD}] if i["state"] == "asks" else []
            nodes.append({"slug": i["slug"], "goal": i["track"], "title": i["title"], "short": i["title"], "state": i["state"], "queue": i["queue"], "held_until": "",
                          "element": "meadow", "flag": None,
                          "start_at": i["start_at"], "priority": "normal", "size": "M", "risk": "low", "tier": 1, "depends_on": [], "waits_on": [], "waits": None,
                          "needs_you": need, "progress": {"done": 1, "total": len(tasks)} if sync else {"done": 0, "total": 0}, "tasks": tasks if sync else [],
                          "estimate": None, "by_itself": False, "folded": False, "updated": "2026-10-17T10:00:00", "checks": [],
                          "stage": "implementation" if sync and not self.unplanned else "planning", "round": 1, "usd": 0.84 if sync else None,
                          "plan_estimate": {"usd_low": 1.0, "usd_high": 2.0} if i["state"] == "plan" else None, "asked": asked,
                          "results": self.results() if sync else []})
        goals = []
        for g in self.goals.values():
            if g["slug"] == "general":
                continue
            lead = g.get("leader") or LEAD
            reading = any(i["track"] == g["slug"] and i["state"] in ("reading", "planning") for i in self.ideas.values())       # spec 48 §1: the leader at work
            party = [{**lead, "band": "lead", "state": "work" if reading else "free", "why": ""}]
            if g["slug"] == "ship-sync":
                party += [{"slug": "grunt", "name": "Grunts", "head": _HEAD, "band": "build", "state": "work", "why": ""},
                          {"slug": "reviewer", "name": "Reviewer", "head": {"craft": "engineering", "race": "peon", "tier": "elder"}, "band": "check", "state": "next", "why": ""}]
            goals.append({"slug": g["slug"], "title": g["title"], "short": g["title"], "priority": g["priority"], "state": g["state"], "done_when": [], "ideas": 5, "done": 0,
                          "usd": None, "leader": lead, "team": [], "party": party, "today": {"merged": 0, "usd": 0.0}, "flags": 0, "waits_main": 0, "brief": ""})
        return {"goals": goals, "nodes": nodes, "edges": [], "rev": self.rev}

    def handle(self, name, a):
        self.log.append((name, a))
        if name == "ideas.map":
            return self.map_doc()
        if name == "ideas.gate":
            return copy.deepcopy(self.gate_doc)
        if name == "ideas.gate_merge":
            self.gate_doc.update(commits=0, files=0, ideas=[])
            return self.bump({"ok": True, "commit": "abc", "note": ""})
        if name == "ideas.today":
            return {"events": copy.deepcopy(self.today_events)}
        if name == "ideas.board":
            ideas = [i | {"thesis": "Gist in one line", "progress": {"done": 1, "total": 5} if i["slug"] == "sync" else {"done": 0, "total": 0}}
                     for i in self.ideas.values()]
            return {"tracks": [g | {"count": sum(1 for i in ideas if i["track"] == g["slug"])} for g in self.goals.values()],
                    "ideas": ideas, "needs_you": self.needs_you(), "target": self.target, "autostart": self.autostart, "night": self.night,
                    "rev": self.rev}
        if name == "ideas.page":
            return self.page(a["slug"])
        if name == "ideas.lens":                      # the goal's party's lenses (gui/ideas_lens.py)
            return dict(self.lens, track=a["track"])
        if name == "ideas.check_skip":                # a check skipped, or taken again (gui/ideas_review.py)
            for c in self.checks:
                if c["by"] == a["by"]:
                    c.update(skipped=a.get("skip", True) is not False, state="", task="")
            return self.bump({"ok": True})
        if name == "ideas.lens_code":
            return {"parts": self.parts}
        if name == "ideas.lens_screen":
            return {"id": a["id"], "name": "Orders", "type": "image/png", "data": self.screen_png}
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
            chips = [c | self.chip_extra.get(c["task"], {}) for c in chips]
            blocks = [{"role": "taskmaster", "name": "Taskmaster", "model": "elder", "max_parallel": 1, "builtin": True, "spend_today": 0, "usd_task": None,
                       "head": {"craft": "engineering", "race": "peon", "tier": "elder"}, "harness": {"id": "claude", "name": "Claude"}, "week": self.week.get("taskmaster"),
                       "state": "waiting", "waits_on": {"idea": "dark", "text": "waiting for your answers on “Dark mode”"}, "chips": []},
                      {"role": "grunt", "name": "Grunts", "model": "", "max_parallel": 8, "builtin": True, "spend_today": 1.25, "chips": chips,
                       "kinds": [k for k, r in self.kinds.items() if r == "grunt"], "usd_task": self.usd_task.get("grunt"),
                       "head": {"craft": "engineering", "race": "peon", "tier": "warrior"}, "harness": self.harness.get("grunt", {"id": "claude", "name": "Claude"}),
                       "week": self.week.get("grunt")}]
            blocks += [{"role": r["slug"], "name": r["name"], "model": r["model"], "max_parallel": r["max_parallel"], "builtin": False, "spend_today": 0,
                        "chips": [], "kinds": [k for k, x in self.kinds.items() if x == r["slug"]], "usd_task": self.usd_task.get(r["slug"]),
                        "head": r.get("head"), "harness": self.harness.get(r["slug"], {"id": "claude", "name": "Claude"}), "week": self.week.get(r["slug"]),
                        **({"check_week": self.check_week[r["slug"]]} if r["slug"] in self.check_week else {})}
                       for r in self.roles.values() if not r["builtin"]]
            return {"roles": blocks, "done_today": [{"idea": "sync", "task": "k1", "title": "Read the sync code", "role": "grunt"}]}
        if name == "ideas.roles":
            return {"roles": [r | {"spend_today": 0, "record": self.record.get(r["slug"])} | ({"check_week": self.check_week[r["slug"]]} if r["slug"] in self.check_week else {}) | ({"told": self.told[r["slug"]]} if r["slug"] in self.told else {}) for r in self.roles.values()],
                    "kinds": self.kind_list(),
                    "models": [{"id": "", "label": "The task's own tier"}, {"id": "elder", "label": "Elder tier (opus)"},
                               {"id": "warrior", "label": "Warrior tier (sonnet)"}, {"id": "laborer", "label": "Laborer tier (haiku)"}],
                    "library": [x | {"installed": x["id"] in self.roles} for x in library.listed()], "suggested": library.SUGGESTED, "seats": library.SEATS,
                    "parties": library.parties(), "presets": library.presets(), "stages": library.stages(), "tier_costs": dict(plans.DEFAULT_COST)}
        if name == "ideas.role_add":                  # an agent of the library made a role of this project (gui/ideas_roles.py)
            lib = library.get(a["id"])
            if lib is None or lib.id in self.roles:
                return {"error": "No such agent, or it is already this project's"}
            self.roles[lib.id] = {"slug": lib.id, "name": lib.name, "model": lib.tier, "max_parallel": 2, "instruction": lib.instruction, "builtin": False,
                                  "craft": lib.craft, "head": {"craft": lib.craft, "race": roles.RACES[lib.craft], "tier": lib.tier}}
            return self.bump({"slug": lib.id})
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
                                         title_by="person" if a.get("title") else old.get("title_by", "keeper"),
                                         leader=self.leader(a.get("leader")) or old.get("leader"), party=a.get("party", ""),
                                         team=a.get("team", old.get("team", [])), every=a.get("every", old.get("every", [])), craft=a.get("craft", old.get("craft", "engineering")))
            return self.bump({"slug": slug, **({"notes": self.goal_notes} if self.goal_notes else {})})
        if name == "ideas.parties":                    # spec 43 F: the person's own parties
            return {"parties": copy.deepcopy(self.own)}
        if name == "ideas.party_save":
            taken = next((p for p in self.own if p["name"].lower() == a["name"].lower()), None)
            if taken and not a.get("replace"):
                return {"error": f"You have a party named “{taken['name']}”"}
            if taken:
                taken.update(name=a["name"])
                return {"id": taken["id"]}
            self.own.append({"id": f"p-{len(self.own):08x}", "name": a["name"], "craft": "engineering", "leader": "architect", "team": [], "every": [], "own": [],
                             "goals": 0, "projects": 0, "met": 0, "saved": ""})
            return {"id": self.own[-1]["id"]}
        if name == "ideas.party_drop":
            self.own = [p for p in self.own if p["id"] != a["id"]]
            return {"ok": True}
        if name == "ideas.party_answer":               # spec 43 D: a party's proposal answered
            self.party_rows = [n for n in self.party_rows if n["goal"] != a["goal"]]
            return self.bump({"ok": True})
        if name == "ideas.party_price":                # spec 43 C: about what an idea costs with this party
            return party_price(a, self.learned, self.hints)
        if name == "ideas.party":                      # spec 43 B: what the goal's party did
            return copy.deepcopy(self.party)
        if name == "ideas.goal_accept":
            self.goals[a["slug"]]["busy"] = True
            return self.bump({"ok": True})
        if name == "ideas.goal":
            g = self.goals[a["slug"]]
            return g | {"description": g["about"], "talk": [], "busy": g.get("busy") or g["state"] == "reading", "sections": []}
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
                return {"error": "A goal needs a party"}
            slug = a["text"].lower().replace(" ", "-")
            now = a["priority"] != "low" and not a.get("night")
            self.ideas[slug] = self.idea(slug, a["text"], "reading" if now else "raw", 9, track=a["track"], priority=a["priority"], queue="now" if now else "night")
            return self.bump({"slug": slug, "queue": "now" if now else "night", "element": "meadow"})
        if name == "onboarding.skip":
            self.onboarding = {"step": "raising", "steps": ["tools"], "n": 0, "raising": {"title": "x", "phase": "done", "steps": [], "buildings": [], "error": ""}}
            return self.bump({})
        if name == "onboarding.close":
            self.onboarding = None
            return self.bump({})
        if name == "logs.save":
            return {"path": SAVED, "name": SAVED.rsplit("/", 1)[1], "folder": SAVED.rsplit("/", 1)[0]}
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


def _open(gui, viewport=None, host=None, ready=".arena-result", query=""):
    """The window against a stub host. The goals are tabs and the first by priority is shown: the stub's Ship sync (most of its ideas)
    is picked, and its results are in the column on the right (`ready`)."""
    server, browser = gui
    host = host or StubHost()
    pg = browser.new_page(viewport=viewport or {"width": 1440, "height": 900})
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url + query)
    if ready == ".arena-result":
        pg.wait_for_selector(".arena-phead", timeout=WAIT_MS)
        _show_goal(pg)
        pg.wait_for_selector(ready, timeout=WAIT_MS)
    elif ready:
        pg.wait_for_selector(ready, timeout=WAIT_MS)
    return pg, host, errors


def _parties(pg):
    """The left column's list of the parties (docs/specs/69-parties-in-the-column.md): waited for; a heading for each party."""
    col = pg.get_by_role("complementary", name="Parties")
    col.wait_for(timeout=WAIT_MS)
    return col


def _party_card(pg, slug):
    """A party's heading in the column."""
    return _parties(pg).locator(f'.arena-phead[data-goal="{slug}"]')


def _new_party(pg):
    """New party, from the column's last line (docs/specs/69-parties-in-the-column.md §1)."""
    _parties(pg).locator(".arena-pnew").click()
    pg.get_by_role("dialog", name="New party").wait_for(timeout=WAIT_MS)


def _show_goal(pg, slug="ship-sync"):
    """The window shows one party: this one, its heading pressed in the column (and kept, as the person's last)."""
    _parties(pg).locator(".arena-phead").first.wait_for(timeout=WAIT_MS)
    if not pg.locator(f'.arena[data-goal="{slug}"]').count() or slug == "@operations":
        _party_card(pg, slug).click()
    if slug == "@operations":
        pg.locator(".arena-ops").wait_for(timeout=WAIT_MS)
    else:
        pg.locator(f'.arena[data-goal="{slug}"]').wait_for(timeout=WAIT_MS)
        pg.wait_for_function("() => !document.querySelector('.is-leaving') && !document.querySelector('.is-drawn')", timeout=WAIT_MS)


def _stop(pg, kind, nth=0):
    """A stop in the fan along the bottom, raised (its quick answers are then in reach): the focus brings it up, as a hover does."""
    item = pg.locator(f".arena-hc[data-kind={kind}]").nth(nth)
    item.wait_for(timeout=WAIT_MS)
    item.locator(".arena-hc__open").focus()
    pg.wait_for_function("(el) => getComputedStyle(el).transform === 'matrix(1, 0, 0, 1, 0, -184)'", arg=item.element_handle(), timeout=WAIT_MS)   # it stands whole before a press
    return item


def _drawer(pg):
    """The drawer, once it is out."""
    pg.locator(".shell-drawer").wait_for(timeout=WAIT_MS)
    return pg.locator(".shell-drawer")


def _agents(pg):
    """Agents in the drawer (the top bar's button)."""
    pg.locator(".shell-top").get_by_role("button", name="Agents").click()
    pg.locator(".shell-agents").wait_for(timeout=WAIT_MS)
    return pg.locator(".shell-agents")


def _new_ideas(pg):
    """The goals list's New (n) fold, open: its rows (a goal is a row of the list: `.arena-goal`)."""
    fold = pg.locator(".arena-raw")
    if fold.get_attribute("aria-expanded") != "true":
        fold.click()
    return pg.locator(".arena-goal")


def _goal_row(pg, title):
    """A goal of the party shown, by its title: its row in the goals list."""
    return pg.locator(".arena-goal", has_text=title)


def _open_goal(pg, title):
    """› on a goal's row opens its screen in the drawer (its spec, its plan when the plan waits); a goal not yet read opens on a press."""
    row = _goal_row(pg, title)
    (row.locator(".arena-goal__open") if row.locator(".arena-goal__open").count() else row.locator(".arena-goal__main")).click()


def _new_goal(pg):
    """New goal: a press on the pile turns its top card over, then the dialog opens."""
    pg.locator(".arena-new__pile").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    dlg.wait_for(timeout=WAIT_MS)
    return dlg


@pytest.fixture
def shell(gui):
    pg, host, errors = _open(gui)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def box(pg, selector):
    return pg.locator(selector).first.bounding_box()


def test_one_window_the_parties_column_over_the_leader_and_no_camp(shell):
    pg, host = shell
    top, line, arena = box(pg, ".shell-top"), box(pg, ".arena-left .arena-phead[aria-current=true]"), box(pg, ".arena")
    assert top["height"] == 32 and arena["y"] == top["height"] and arena["width"] == 1440                     # the window right under the top bar
    assert pg.locator(".shell-top .arena-phead, .shell-top .shell-proj, .shell-top [role=tablist]").count() == 0   # no parties, no project switcher in the top bar (spec 52 §3.1, spec 69 §1)
    assert line["height"] >= 40 and line["y"] >= arena["y"] and line["y"] + line["height"] <= box(pg, ".arena-lead")["y"]      # the open party's heading over its leader
    assert pg.locator(".arena-tabs").count() == 0
    assert box(pg, ".arena-left")["width"] == 248 and box(pg, ".arena-field")["x"] > box(pg, ".arena-left")["x"]
    for gone in (".shell-board", ".shell-split", ".shell-agents", ".shell-tabs", ".shell-review"):             # no Board column, no split, no tab bar
        assert pg.locator(gone).count() == 0, gone
    assert pg.locator(".shell-drawer").count() == 0                                                         # nothing opened: no drawer
    assert pg.evaluate("document.documentElement.dataset.look") == "office"                                   # the person's look is camp: not here
    for gone in (".gui-hud", ".gui-camp", ".gui-town", ".gui-foot", ".gui-warchief__face", "[data-look=camp]"):
        assert pg.locator(gone).count() == 0, gone
    assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    assert not pg.evaluate("document.documentElement.scrollHeight > document.documentElement.clientHeight")
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.locator(".arena-task[data-task=k2]").click()
        pg.locator(".shell-file").first.wait_for(timeout=WAIT_MS)
        pg.locator(".shell-file").first.locator("summary").click()
        pg.screenshot(path=str(SHOTS / "desktop-1440x900.png"))


def test_the_top_bar_spend_stop_all_and_the_push_switch(shell):
    pg, host = shell
    top = pg.locator(".shell-top")
    assert top.locator(".shell-limit").count() == 0                                                         # the limits left the bar (spec 49 §3)
    assert "$2.40" in top.inner_text()
    top.get_by_role("button", name="Stop all").click()
    assert _sent(pg, host, ("halt", {}))
    top.get_by_role("button", name="Settings").click()
    assert pg.get_by_role("dialog", name="Settings").is_visible()
    label = pg.get_by_text("Push after merging (sends your code to origin)")
    assert label.is_visible() and not pg.get_by_role("checkbox", name="Push after merging").is_checked()
    pg.get_by_text("Push after merging (sends your code to origin)").click()
    assert _sent(pg, host, ("ideas.into", {"push": True}))
    logs = pg.locator(".shell-gear__logs .ork-btn")                             # the day's logs, today and the last 7 days,
    assert logs.all_inner_texts() == ["Today", "The last 7 days"]                # saved in Downloads (a window downloads nothing)
    logs.nth(1).click()
    assert _sent(pg, host, ("logs.save", {"said": "", "days": 7}))
    saved = pg.locator(".ok-toast", has_text="Logs saved: " + SAVED)
    saved.wait_for(timeout=WAIT_MS)
    saved.get_by_role("button", name="Show").click()
    assert _sent(pg, host, ("logs.show", {"path": SAVED}))


def test_the_tools_limits_are_at_the_bottom_right_with_their_diamonds_and_the_reserve_hatched(shell):
    pg, host = shell
    limits = pg.get_by_role("region", name="What is left of your AI tools")
    lines = limits.locator(".arena-limit")
    assert lines.count() == 3 and [l.get_attribute("data-provider") for l in lines.all()] == ["claude", "agy", "codex"]
    claude = lines.nth(0)
    assert "62 %" in claude.inner_text() and claude.locator(".ork-crystals i").count() == 10
    assert claude.locator(".ork-crystals i.on").count() == 5 and claude.locator(".ork-crystals i.kept").count() == 1      # 6 left, 1 kept for tonight
    assert lines.nth(1).locator(".ork-crystals i.kept").count() == 0 and lines.nth(1).locator(".ork-crystals i.on").count() == 2      # 15 %: two
    assert "not read" in lines.nth(2).inner_text() and lines.nth(2).locator(".ork-crystals i").count() == 0                       # never missing
    assert claude.get_attribute("title") == "Claude: 62 % left, 10 % of it kept for tonight · resets at 18:00"
    assert "hatched: kept for tonight" in limits.inner_text() and "Claude resets at 18:00" in limits.inner_text()
    bb = limits.bounding_box()
    assert bb["x"] + bb["width"] == 1440 and bb["width"] == 312 and bb["y"] + bb["height"] == 900                  # at the bottom right


def test_a_click_on_an_idea_a_todo_a_chip_and_a_result_opens_the_right_preview(shell):
    pg, host = shell
    _open_goal(pg, "Dark mode")                                                   # a goal in Planning → its spec in the drawer: the nine sections
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "idea", "ref": "dark", "device": "desktop", "via": "map"}))
    pg.locator(".shell-drawer .board-sec").first.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-drawer .board-sec").count() == len(SECTIONS)
    assert "goal" in pg.locator(".shell-drawer .shell-tabstrip").inner_text().lower()

    pg.get_by_role("button", name="Close the drawer").click()                     # the drawer covers the fan's middle: it goes, its tab stays
    item = _stop(pg, "todo")                                                      # a to-do → its dialog; from it the plan, scrolled to it
    item.get_by_role("button", name="Open…").click()
    pg.get_by_role("dialog", name="API_KEY").get_by_role("button", name="What waits for it").click()
    target = pg.locator(".shell-drawer .board-plan__todo.is-target")
    target.wait_for(timeout=WAIT_MS)
    assert "tasks k2 and k3 wait for it" in target.inner_text()
    assert "plan" in pg.locator(".shell-drawer .shell-tabstrip").inner_text().lower() and pg.get_by_role("tab", name="Plan", exact=False).count() == 1
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "todo", "ref": "sync/t1", "device": "desktop"}))

    _agents(pg)                                                                   # a chip in Agents → the task: brief, log, Stop
    pg.locator(".shell-chip", has_text="Retry on a lost signal").click()
    pg.locator(".shell-task").wait_for(timeout=WAIT_MS)
    text = pg.locator(".shell-task").inner_text()
    assert "Brief of Retry on a lost signal" in text and "reading sync.py" in text and "idea/sync/k3" in text and "working" in text
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "task", "ref": "sync/k3", "device": "desktop", "via": "agents"}))
    pg.get_by_role("button", name="Stop", exact=True).click()
    assert _sent(pg, host, ("ideas.stop_task", {"slug": "sync", "task": "k3"}))

    pg.locator(".arena-task[data-task=k2]").click()                               # a result → its code, from its task in the field
    pg.locator(".shell-result .shell-commits").wait_for(timeout=WAIT_MS)
    assert "k2: add the queue" in pg.locator(".shell-commits").inner_text()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "result", "ref": "sync/k2", "device": "desktop", "via": "map"}))
    pg.locator(".shell-file", has_text="sync.py").locator("summary").click()
    pg.locator(".shell-patch__line.is-add").first.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-patch__line.is-add").count() == 2 and pg.locator(".shell-patch__line.is-del").count() == 1
    pg.locator(".shell-file", has_text="huge.json").locator("summary").click()
    pg.get_by_text("Too large to show.", exact=True).wait_for(timeout=WAIT_MS)    # not "Some files are too large…"
    colors = pg.evaluate("""() => { const cs = (q) => getComputedStyle(document.querySelector(q)).color;
      return [cs('.shell-patch__line.is-add'), cs('.shell-patch__line.is-del'), getComputedStyle(document.documentElement).getPropertyValue('--success').trim()]; }""")
    assert colors[0] != colors[1]
    assert pg.locator(".shell-drawer").get_by_role("button", name="Merge into dev").is_visible()      # its actions stay pinned at the foot
    foot, body = box(pg, ".shell-result__foot"), box(pg, ".shell-result__body")
    assert foot["y"] >= body["y"] + body["height"] - 2


def test_merge_is_off_on_red_with_its_reason_and_send_back_needs_a_line(shell):
    pg, host = shell
    green, red = pg.locator(".arena-result", has_text="Add the queue"), pg.locator(".arena-result", has_text="Test it offline")
    assert "20 / 20 passed" in green.inner_text() and "14 files · $0.42" in green.inner_text()
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
    pg.mouse.move(150, 500)                                                                           # nothing moves under the pointer: it settles when the pointer leaves
    pg.locator(".arena-result", has_text="Add the queue").wait_for(state="detached", timeout=WAIT_MS)      # it fades once, then it is gone


def test_drop_asks_first_and_merge_into_changes_the_branch(shell):
    pg, host = shell
    card = pg.locator(".arena-result", has_text="Add the queue")
    card.get_by_role("button", name="Drop…").click()
    assert pg.get_by_role("dialog", name="Drop this result?").is_visible()
    pg.get_by_role("dialog").get_by_role("button", name="Keep it").click()
    assert pg.get_by_role("dialog").count() == 0 and ("ideas.drop_task", {"slug": "sync", "task": "k2"}) not in host.log
    assert card.get_by_role("button", name="Drop…").evaluate("e => e === document.activeElement")     # the focus went back
    pg.locator("button.arena-into").click()
    assert pg.get_by_role("menuitemradio").count() == 2
    pg.get_by_role("menuitem", name="New branch…").click()
    pg.get_by_label("Name of the new branch").fill("next")
    pg.get_by_role("button", name="Make it").click()
    assert _sent(pg, host, ("ideas.into", {"branch": "next"}))
    pg.locator("button.arena-into").wait_for(timeout=WAIT_MS)


def test_esc_puts_the_drawer_away_and_keeps_its_tabs(shell):
    pg, host = shell
    _open_goal(pg, "Dark mode")
    pg.locator(".shell-drawer .board-sec").first.wait_for(timeout=WAIT_MS)
    pg.keyboard.press("Escape")
    pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)                                  # the drawer goes ...
    assert not [c for c in host.log if c[0] in ("ideas.merge", "ideas.back", "ideas.drop_task")]               # ... nothing merges by itself
    _open_goal(pg, "Dark mode")                                                                            # ... and its tab is kept: opening anything brings it back
    assert _drawer(pg).get_by_role("tab").count() == 1


def test_a_new_goal_comes_from_the_pile_and_lists_with_its_state_in_words(shell):
    pg, host = shell
    assert "starts tonight" in _goal_row(pg, "Dark mode").inner_text()
    dlg = _new_goal(pg)
    dlg.get_by_label("Your goal").fill("Offline sync")
    dlg.get_by_role("button", name="Add the goal").click()
    _goal_row(pg, "Offline sync").wait_for(timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.add", {"text": "Offline sync", "track": "ship-sync", "priority": "normal"}))      # the goal shown


def test_below_1024_no_strip_the_drawer_takes_the_window_and_the_results_join_the_bottom_row(gui):
    pg, host, errors = _open(gui, {"width": 900, "height": 800}, ready=".arena-phead")
    try:
        _show_goal(pg)
        assert pg.locator(".arena-today").count() == 0 and box(pg, ".arena-left")["width"] == 200                 # no strip, the left column 200 px
        assert pg.locator(".arena-look").count() == 0                                                         # the results are in the bottom row
        pg.locator(".arena-hc[data-kind=result]", has_text="Add the queue").wait_for(timeout=WAIT_MS)
        pg.locator(".arena-task[data-task=k2]").click()
        pg.locator(".shell-result").wait_for(timeout=WAIT_MS)
        drawer = box(pg, ".shell-drawer")
        assert drawer["x"] == 0 and drawer["width"] == 900                                                    # the drawer takes the window's width
        pg.get_by_role("button", name="Close the drawer").click()
        pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)
        assert pg.locator(".arena-task[data-task=k2]").is_visible()
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
        pg.locator(".arena").first.wait_for(timeout=WAIT_MS)
        assert _sent(pg, host, ("onboarding.skip", {})) and _sent(pg, host, ("onboarding.close", {}))
    finally:
        pg.close()
    assert not errors, "\n".join(errors)



# -- spec 34 round 2: dialogs, agents by task type, the phone from the shell -----------------------------------------

def adds(host):
    return [a for n, a in host.log if n == "ideas.add"]


def test_new_party_is_a_name_what_it_is_for_its_party_and_a_priority_then_reading_its_title_and_summary(shell):
    pg, host = shell
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    assert dlg.locator(".shell-craft-tile").count() == 10                                           # from the library: the four mixed, the five crafts, the Taskmaster alone
    dlg.locator('.shell-craft-tile[data-craft="design"]').click()                                   # the library's design party, in three bands
    leads, builds = dlg.get_by_role("region", name="Leads"), dlg.get_by_role("region", name="Builds")
    assert leads.locator('.shell-team-row[aria-pressed="true"]').get_attribute("data-agent") == "product-designer"
    assert builds.locator(".shell-team-seat:not(.is-empty)").count() == 2 and builds.locator(".shell-team-seat").count() == 3
    dlg.get_by_role("button", name="Take in: Analyst").click()                                      # another leader
    dlg.get_by_role("button", name="Take in: Copywriter").click()                                   # the third builder
    dlg.get_by_role("button", name="Take in: Grunt").click()                                        # a fourth: no seat
    assert builds.locator(".shell-team-seat:not(.is-empty)").count() == 3
    assert leads.locator('.shell-team-row[aria-pressed="true"]').get_attribute("data-agent") == "analyst"
    assert dlg.get_by_role("button", name="Save party").is_disabled()                               # a name or what it is for is required
    assert "led by Analyst" in dlg.inner_text()
    checks = dlg.get_by_role("group", name="Checks")                                                # the party's checkers, what they add
    assert "Accessibility reviewer" in checks.inner_text() and "Analyst" not in checks.inner_text()
    checks.get_by_label("Every goal: Accessibility reviewer").check()
    assert dlg.get_by_label("Deadline").count() == 0 and dlg.get_by_label("Description").count() == 0     # nothing else is asked
    assert dlg.get_by_label("Metric 1: what is measured").count() == 0 and dlg.get_by_label("Link 1", exact=True).count() == 0
    dlg.get_by_label("What it is for").fill("More people try Orkline.")
    dlg.get_by_text("High", exact=True).click()
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-new-party-1440x900.png"))
    dlg.get_by_role("button", name="Save party").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.goal_save")[0] == {"about": "More people try Orkline.", "leader": "analyst",
                                                      "team": ["ui-kit", "artist", "accessibility-reviewer", "copywriter"],
                                                      "every": ["accessibility-reviewer"], "priority": "high"}
    pg.locator(".shell-goal").wait_for(timeout=WAIT_MS)                                             # the party opens in the drawer: About this party
    assert "reading" in pg.locator(".shell-goal").inner_text()
    assert _party_card(pg, "more-people").count() == 1                                              # its heading among the parties
    g = host.goals["more-people"]
    g.update(title="Grow installs", state="asks", summary="Installs are the first step.", questions=["Which channel first?"], title_by="keeper",
             metrics=[{"name": "weekly installs", "target": "50", "how": "npm downloads, per week"}])
    host.bump({})
    pg.locator(".shell-goal").get_by_text("Installs are the first step.").wait_for(timeout=WAIT_MS)
    text = pg.locator(".shell-goal").inner_text()
    assert "Which channel first?" in text and "weekly installs" not in text and "Metrics" not in text      # a party has no metrics
    assert _party_card(pg, "more-people").locator(".arena-phead__name").get_attribute("title").startswith("Grow installs")
    pg.get_by_label("Answer 1: Which channel first?").fill("npm first")                              # §0: one round, one Send
    pg.locator(".shell-goal").get_by_role("button", name="Send").click()
    assert _sent(pg, host, ("ideas.answer", {"slug": "more-people", "answers": ["npm first"], "goal": True}))
    pg.get_by_role("button", name="Close the drawer").click()                                       # the party's screen goes: Edit is in the party line
    pg.get_by_role("button", name="Edit the party").click()                                         # Edit: name, what it is for and priority
    dlg = pg.get_by_role("dialog", name="Edit the party")
    assert dlg.get_by_label("Name", exact=True).input_value() == "Grow installs" and dlg.get_by_label("What it is for").input_value() == "More people try Orkline."
    dlg.get_by_label("What it is for").fill("More people try Orkline, and stay.")
    dlg.get_by_role("button", name="Save party").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.goal_save", 2)[-1] == {"slug": "more-people", "about": "More people try Orkline, and stay.", "priority": "high"}
    if pg.locator(".shell-drawer").count():
        pg.get_by_role("button", name="Close the drawer").click()
    pg.get_by_role("button", name="Edit the party").click()                                         # a corrected name is sent, and only then
    pg.get_by_role("dialog", name="Edit the party").get_by_label("Name", exact=True).fill("Grow weekly installs")
    pg.get_by_role("dialog", name="Edit the party").get_by_role("button", name="Save party").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.goal_save", 3)[-1]["title"] == "Grow weekly installs"


def test_a_party_with_a_verdict_of_before_says_it_as_history_and_nothing_asks_its_leader_to_accept_it(shell):
    pg, host = shell
    host.goals["land"] = host.goal("land", "Landing page", "high", "ready", order=3, leader=host.leader("growth"),
                                   metrics=[{"name": "weekly installs", "target": "50", "how": "npm"}], verdict={"met": False, "by": "Growth", "at": "2026-10-10T09:00:00"})
    host.ideas["page"] = host.idea("page", "The landing page", "done", 7, track="land")
    host.bump({})
    _show_goal(pg, "land")
    pg.get_by_role("button", name="About this party").click()
    view = pg.locator(".shell-goal")
    view.wait_for(timeout=WAIT_MS)
    assert "Before: not met yet, says Growth · 10 October" in " ".join(view.inner_text().split())          # its old verdict, kept as history
    assert view.get_by_role("button", name=re.compile("accept", re.I)).count() == 0 and "Verdict" not in view.inner_text() and "Metrics" not in view.inner_text()
    assert not [1 for n, _a in host.log if n == "ideas.goal_accept"]


def test_new_goal_needs_a_party_a_priority_and_one_button_and_a_closed_dialog_goes_to_the_night(shell):
    pg, host = shell
    dlg = _new_goal(pg)
    assert dlg.get_by_role("button", name="Add the goal").is_disabled() and dlg.get_by_role("button", name="Later").count() == 0
    assert dlg.get_by_label("Party", exact=True).locator("option").all_inner_texts() == ["Grow installs", "Ship sync"]     # by priority; no General
    assert dlg.get_by_label("Party", exact=True).input_value() == "ship-sync"                         # the party shown
    assert dlg.get_by_label("Priority", exact=True).input_value() == "normal"                        # its priority
    dlg.get_by_label("Party", exact=True).select_option("grow")
    assert dlg.get_by_label("Priority", exact=True).input_value() == "high"                          # follows the party until the person picks one
    dlg.get_by_label("Party", exact=True).select_option("ship-sync")
    dlg.get_by_label("Your goal").fill("Dark mode please")
    dlg.get_by_label("Priority", exact=True).select_option("high")
    dlg.get_by_role("button", name="Add the goal").click()
    _goal_row(pg, "Dark mode please").wait_for(timeout=WAIT_MS)                                       # at once: Taskmaster is reading it
    assert adds(host) == [{"text": "Dark mode please", "track": "ship-sync", "priority": "high"}]
    dlg = _new_goal(pg)                                                                             # closed with text: tonight's queue
    dlg.get_by_label("Your goal").fill("Later goal")
    pg.get_by_role("button", name="Close", exact=True).click()
    _new_ideas(pg).filter(has_text="Later goal").wait_for(timeout=WAIT_MS)                          # under New (n)
    assert adds(host)[-1] == {"text": "Later goal", "track": "ship-sync", "priority": "normal", "night": True}
    _new_goal(pg)                                                                                   # closed empty: nothing
    before = len(adds(host))
    pg.keyboard.press("Escape")
    pg.wait_for_function("() => !document.querySelector('[role=dialog]')", timeout=WAIT_MS)
    pg.wait_for_timeout(200)
    assert len(adds(host)) == before
    dlg = _new_goal(pg)                                                                             # Esc with text in it too
    dlg.get_by_label("Your goal").fill("Saved by Esc")
    pg.keyboard.press("Escape")
    _new_ideas(pg).filter(has_text="Saved by Esc").wait_for(timeout=WAIT_MS)
    assert adds(host)[-1]["night"] is True and adds(host)[-1]["text"] == "Saved by Esc"
    dlg = _new_goal(pg)                                                                             # Put it back: the same as closing it
    dlg.get_by_label("Your goal").fill("Put back")
    dlg.get_by_role("button", name="Put it back").click()
    _new_ideas(pg).filter(has_text="Put back").wait_for(timeout=WAIT_MS)
    assert adds(host)[-1]["night"] is True and adds(host)[-1]["text"] == "Put back"


def test_with_no_party_yet_new_goal_opens_new_party_first_and_then_itself_with_that_party(shell):
    pg, host = shell
    host.goals.pop("grow"), host.goals.pop("ship-sync")
    host.bump({})
    pg.get_by_text("No parties yet").wait_for(timeout=WAIT_MS)
    pg.get_by_role("button", name="New goal").click()
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.get_by_label("What it is for").fill("Make notes searchable.")
    dlg.get_by_role("button", name="Save party").click()
    goal = pg.get_by_role("dialog", name="New goal")
    goal.wait_for(timeout=WAIT_MS)
    assert goal.get_by_label("Party", exact=True).input_value() == "make-notes"


def test_one_goal_is_shown_the_first_by_priority_with_its_leader_and_the_goal_is_kept(gui):
    host = StubHost()
    host.goals["ship-sync"].update(craft="engineering", leader=host.leader("architect"), team=["tester", "reviewer"])
    pg, host, errors = _open(gui, host=host, ready=".arena")
    try:
        cards = _parties(pg).locator(".arena-phead")
        assert [c.get_attribute("data-goal") for c in cards.all()] == ["grow", "ship-sync"] and pg.locator(".arena-pnew").count() == 1      # the parties, no Operations, then + New party
        assert pg.locator('.arena-phead[aria-current=true]').get_attribute("data-goal") == "grow"                                    # none kept yet: the first by priority
        assert pg.locator(".arena").get_attribute("data-goal") == "grow"
        _show_goal(pg, "ship-sync")
        assert pg.locator(".arena-lead").get_by_role("button", name=re.compile("Architect")).count() == 1      # its leader under its heading in the left column
        assert _goal_row(pg, "Dark mode").count() == 1                                                        # its goals in Planning, not another party's
        assert _goal_row(pg, "Tag the notes").count() == 0
        pg.get_by_role("button", name="About this party").click()
        pg.locator(".shell-goal").wait_for(timeout=WAIT_MS)
        assert _sent(pg, host, ("ideas.goal", {"slug": "ship-sync"}))
        pg.reload()                                                                                         # the goal shown is kept
        pg.locator('.arena[data-goal="ship-sync"]').wait_for(timeout=WAIT_MS)
        assert pg.locator('.arena-phead[aria-current=true] .arena-phead__name').inner_text() == "Ship sync"
        pg.get_by_role("button", name="Close the drawer").click()                                           # the drawer came back with the page: its tabs were kept
        pg.get_by_role("button", name="Edit the party").click()
        assert pg.get_by_role("dialog", name="Edit the party").is_visible()
        pg.keyboard.press("Escape")
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_edit_the_party_changes_its_members_and_sends_them_only_when_changed(shell):
    pg, host = shell
    host.goals["ship-sync"].update(about="Sync between devices.", craft="engineering", leader=host.leader("architect"), team=["grunt", "reviewer"], every=[])
    host.bump({})
    pg.locator(".arena-lead", has_text="Architect").wait_for(timeout=WAIT_MS)                        # the window has read it
    pg.get_by_role("button", name="Edit the party").click()
    dlg = pg.get_by_role("dialog", name="Edit the party")
    party = dlg.get_by_role("group", name="The party")
    assert "led by Architect · builds: Grunt · checks: Reviewer" in party.inner_text()
    party.get_by_role("button", name="Change the party").click()
    party.get_by_role("button", name="Take in: Product manager").click()                              # another leader
    party.get_by_role("button", name="Take in: Tester").click()
    party.get_by_label("Every goal: Reviewer").check()
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-edit-party-1440x900.png"))
    dlg.get_by_role("button", name="Save party").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    got = _calls(pg, host, "ideas.goal_save")[-1]
    assert (got["leader"], got["team"], got["every"]) == ("product-manager", ["grunt", "reviewer", "tester"], ["reviewer"])


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


def test_a_high_goal_shows_a_sign_of_work_and_stop_leaves_it_stopped_a_low_one_waits_for_tonight(shell):
    pg, host = shell
    dlg = _new_goal(pg)
    dlg.get_by_label("Your goal").fill("Fast one")
    dlg.get_by_label("Priority", exact=True).select_option("high")
    dlg.get_by_role("button", name="Add the goal").click()
    row = _goal_row(pg, "Fast one")
    row.wait_for(timeout=WAIT_MS)
    assert row.locator(".ork-sign.work").count() == 1 and "Taskmaster is reading" in row.inner_text()   # the leader reads it: a sign and words
    assert pg.locator(".arena-member.is-lead").get_attribute("data-state") == "work"
    _open_goal(pg, "Fast one")                                                                        # its screen has Stop
    drawer = _drawer(pg)
    drawer.get_by_role("button", name="Stop", exact=True).click()
    assert _sent(pg, host, ("ideas.read_stop", {"slug": "fast-one"}))
    row = _new_ideas(pg).filter(has_text="Fast one")                                                  # stopped: a new one again, under New (n)
    row.wait_for(timeout=WAIT_MS)
    assert "stopped" in row.inner_text() and row.locator(".ork-sign.work").count() == 0
    low = _new_ideas(pg).filter(has_text="Offline mode")                                              # a Low one: tonight
    assert "tonight" in low.inner_text()
    power = pg.get_by_role("button", name=re.compile("Process now ·"))                                  # Process now reads the first new goal
    assert power.is_enabled() and "2 new goals" in power.inner_text()
    power.click()
    assert _sent(pg, host, ("ideas.queue", {"slug": "offline", "queue": "now", "via": "party"}))
    _open_goal(pg, "Fast one")                                                                        # Delete asks first
    drawer = _drawer(pg)
    drawer.get_by_role("button", name="Delete goal").click()
    drawer.get_by_role("button", name="Keep it").click()
    assert ("ideas.drop", {"slug": "fast-one"}) not in host.log
    drawer.get_by_role("button", name="Delete goal").click()
    drawer.get_by_role("button", name="Delete it").click()
    _goal_row(pg, "Fast one").wait_for(state="detached", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.drop", {"slug": "fast-one"}))
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.screenshot(path=str(SHOTS / "desktop-board-rows-1440x900.png"))


def test_what_waits_for_you_is_a_fan_of_the_goal_shown_the_questions_one_form_and_a_proposal_is_answered_in_its_item(shell):
    pg, host = shell
    assert pg.locator(".arena-hc").count() == 5                                                          # every stop of the project lies in the one hand (spec 54 §2.1)
    kinds = pg.locator(".arena-hc").evaluate_all("els => els.map(e => e.dataset.kind)")
    assert kinds == ["goal", "todo", "plan", "asks", "proposal"]                                         # urgency's order: what holds work back (the parties in the Board's order), then the proposal
    assert pg.locator(".arena-hc.is-other").count() == 2                                                  # the two of Grow installs say their party
    todo = pg.locator(".arena-hc[data-kind=todo]")
    assert "Sync ideas between the phone and the town" in todo.inner_text() and "API_KEY" in todo.inner_text()
    ask = _stop(pg, "asks")
    ask.get_by_role("button", name="Open…").click()                                                       # the spec's questions: a box each, one Send
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
    pg.wait_for_function("() => document.querySelectorAll('.arena-hc[data-kind=asks]').length === 0", timeout=WAIT_MS)
    _show_goal(pg, "grow")                                                                                # another goal: its own stops, and Ship sync's now say their party
    assert pg.locator(".arena-hc").evaluate_all("els => els.map(e => e.dataset.kind)") == ["goal", "todo", "plan", "proposal"]
    assert pg.locator(".arena-hc.is-other").evaluate_all("els => els.map(e => e.dataset.kind)") == ["todo", "plan"]
    goal = _stop(pg, "goal")
    goal.get_by_role("button", name="Open…").click()                                                      # a goal that asks
    pg.get_by_role("dialog", name="Questions: Grow installs").get_by_label("Answer 1: Which channel first?").fill("npm")
    pg.get_by_role("dialog").get_by_role("button", name="Send").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.answer", {"slug": "grow", "answers": ["npm"], "goal": True}))
    prop = _stop(pg, "proposal")                                                                          # a proposal: Take at the goal's priority, or No with a reason
    prop.get_by_role("button", name="Take: Tag the notes").click()
    pg.wait_for_function("() => document.querySelectorAll('.arena-hc[data-kind=proposal]').length === 0", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.proposal", {"slug": "tags", "take": True, "priority": "high"}))


def test_a_question_comes_with_its_answer_picked_one_press_takes_it(shell):
    pg, host = shell
    host.goals["grow"]["questions"] = ["Which channel first?"]
    host.goals["grow"]["asked"] = [{"ask": "Which channel first?", "choices": ["npm", "the forum"], "pick": 1, "why": "the forum answers in a day"}]
    host.bump({})
    _show_goal(pg, "grow")
    item = _stop(pg, "goal")
    forum, npm = item.get_by_role("button", name=re.compile("the forum")), item.get_by_role("button", name="npm", exact=True)
    assert "●" in forum.inner_text() and "primary" in forum.get_attribute("class") and "primary" not in npm.get_attribute("class")      # the pick is marked and primary
    assert "“Which channel first?”" in item.inner_text()                                                  # the question, in quotes
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-needs-you-1440x900.png"))
    forum.click()                                                                                         # a press answers
    assert _sent(pg, host, ("ideas.answer", {"slug": "grow", "answers": ["the forum"], "goal": True}))
    pg.locator(".ok-toast", has_text="Sent: the Taskmaster answers in a moment.").wait_for(timeout=WAIT_MS)


def test_with_several_questions_send_the_picks_or_open_the_form_with_them_filled_in(shell):
    pg, host = shell
    host.goals["grow"]["questions"] = ["Which channel first?", "Which month?"]
    host.goals["grow"]["asked"] = [{"ask": "Which channel first?", "choices": ["npm", "the forum"], "pick": 0, "why": "most installs come from it"},
                                   {"ask": "Which month?", "choices": ["November", "December"], "pick": 1, "why": ""}]
    host.bump({})
    _show_goal(pg, "grow")
    item = _stop(pg, "goal")
    assert item.get_by_role("button", name="npm").count() == 0                                            # more than one question: the picks, or the form
    item.get_by_role("button", name="Open…").click()                                                      # the form, the picks filled in
    dlg = pg.get_by_role("dialog", name="Questions: Grow installs")
    assert dlg.get_by_label("Answer 1: Which channel first?").input_value() == "npm"
    assert dlg.get_by_label("Answer 2: Which month?").input_value() == "December" and "most installs come from it" in dlg.inner_text()
    dlg.get_by_label("Answer 2: Which month?").fill("November")
    dlg.get_by_role("button", name="Send").click()
    assert _sent(pg, host, ("ideas.answer", {"slug": "grow", "answers": ["npm", "November"], "goal": True}))
    host.asked.remove("grow")
    host.bump({})
    _stop(pg, "goal").get_by_role("button", name="Send the picks").click()
    assert _sent(pg, host, ("ideas.answer", {"slug": "grow", "answers": ["npm", "December"], "goal": True}))


def test_a_proposal_declined_with_a_reason_or_without(shell):
    pg, host = shell
    _show_goal(pg, "grow")
    prop = _stop(pg, "proposal")
    prop.get_by_role("button", name="No: Tag the notes").click()
    prop.get_by_label("Why not: Tag the notes").fill("not now")
    prop.get_by_role("button", name="Decline: Tag the notes").click()
    pg.wait_for_function("() => document.querySelectorAll('.arena-hc[data-kind=proposal]').length === 0", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.proposal", {"slug": "tags", "take": False, "reason": "not now"}))


def test_a_check_that_has_not_run_is_skipped_from_the_spec_and_a_skipped_one_is_taken_again_before_a_plan(shell):
    pg, host = shell
    host.checks[1].update(applies=True, why="", state="", task="")                                   # no task yet: in the plan to come
    host.unplanned = True
    host.bump({})
    _open_goal(pg, "Sync ideas")
    checks = pg.locator(".shell-preview").get_by_role("list", name="Checks")
    checks.wait_for(timeout=WAIT_MS)
    assert checks.get_by_role("button", name="Skip the check: Reviewer").count() == 0                # passed: nothing to spare
    checks.get_by_role("button", name="Skip the check: Accessibility reviewer").click()
    assert _sent(pg, host, ("ideas.check_skip", {"slug": "sync", "by": "accessibility-reviewer"}))
    checks.get_by_text("skipped by you").wait_for(timeout=WAIT_MS)
    checks.get_by_role("button", name="Take the check again: Accessibility reviewer").click()         # before a plan: it can come back
    assert _sent(pg, host, ("ideas.check_skip", {"slug": "sync", "by": "accessibility-reviewer", "skip": False}))


def test_the_spec_shows_its_sections_and_stages_with_each_tasks_live_state(shell):
    pg, host = shell
    pg.locator(".arena-task[data-task=k3]").click()                                                         # an idea at work: its spec from its task
    pg.locator(".shell-task").get_by_role("button", name="Sync ideas between the phone and the town").click()
    stages = pg.locator(".shell-preview .board-sec[data-name=Stages]")
    stages.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-preview .board-sec").evaluate_all("els => els.map(e => e.dataset.name)") == SECTIONS
    checks = pg.locator(".shell-preview").get_by_role("list", name="Checks")                        # the team's checks of this idea
    assert [" ".join(t.split()) for t in checks.get_by_role("listitem").all_inner_texts()] == [
        "Reviewer passed", "Accessibility reviewer not needed: It changes no screen"]
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


def test_a_draft_the_tool_failed_says_why_in_the_spec_and_offers_try_again(shell):
    # the owner's 19 October: the draft's failure came as a toast of raw JSON on every refresh and the spec never opened
    pg, host = shell
    why = "Claude Code is not signed in, or its sign-in has expired. Claude Code said: Not logged in · Please run /login"
    host.ideas["offline"]["state_error"] = why
    _new_ideas(pg).filter(has_text="Offline mode").click()
    alert = pg.locator(".shell-preview .board-ideaview > .shell-error > p[role=alert]")
    alert.wait_for(timeout=WAIT_MS)
    assert alert.inner_text() == why and pg.locator(".ok-toast", has_text="not signed in").count() == 0
    pg.locator(".shell-preview .shell-error").get_by_role("button", name="Save logs").click()   # the words go with the logs
    assert _sent(pg, host, ("logs.save", {"said": why, "days": 1}))
    assert "drafts it tonight" not in pg.locator(".shell-preview").inner_text()
    pg.locator(".shell-preview").get_by_role("button", name="Try again").click()
    assert _sent(pg, host, ("ideas.queue", {"slug": "offline", "queue": "now"}))


def test_in_the_apps_window_a_right_click_copies_any_line_and_saves_logs_with_an_error(gui):
    # the owner's 19 October: any line of the page copied, an error with the day's logs
    host = StubHost()
    host.ideas["offline"]["state_error"] = "Claude Code is not signed in, or its sign-in has expired."
    pg, host, errors = _open(gui, host=host, query="&app=1")
    pg.context.grant_permissions(["clipboard-read", "clipboard-write"])
    card = _new_ideas(pg).filter(has_text="Offline mode")
    card.click(button="right")
    menu = pg.get_by_role("menu", name="Copy")
    menu.get_by_role("menuitem", name="Copy").click()
    assert menu.count() == 0 and "Offline mode" in pg.evaluate("navigator.clipboard.readText()")
    card.click()
    alert = pg.locator(".shell-preview .shell-error > p[role=alert]")
    alert.wait_for(timeout=WAIT_MS)
    alert.click(button="right")
    menu.get_by_role("menuitem", name="Save logs with it").click()
    assert _sent(pg, host, ("logs.save", {"said": "Claude Code is not signed in, or its sign-in has expired.", "days": 1}))
    _goal_row(pg, "Dark mode").click(button="right")
    pg.keyboard.press("Escape")                                                 # Esc closes the menu, not the tab under it
    assert menu.count() == 0 and alert.is_visible()
    pg.close()
    assert not errors, "\n".join(errors)


def test_in_a_browser_a_right_click_is_the_browsers_own(shell):
    pg, host = shell
    _new_ideas(pg).filter(has_text="Offline mode").click(button="right")
    assert pg.get_by_role("menu", name="Copy").count() == 0


def test_a_file_todo_shows_its_steps_and_uploads_the_file_and_a_secret_shows_its_steps_too(shell, tmp_path):
    pg, host = shell
    _stop(pg, "todo").get_by_role("button", name="Open…").click()                                   # steps on any kind: a secret has them too
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
    pg.locator(".arena-hc[data-kind=todo]", has_text="The Firebase config").wait_for(timeout=WAIT_MS)
    _stop(pg, "todo").get_by_role("button", name="Open…").click()
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
    _stop(pg, "todo").get_by_role("button", name="Open…").click()                                   # a file over 5 MB is refused in the dialog
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
    _agents(pg)
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
    assert files.count() == 1                                                                         # after the wait: beside
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.screenshot(path=str(SHOTS / "desktop-agents-chips-1440x900.png"))


def test_agents_add_an_agent_edit_it_and_give_it_a_task_type(shell):
    pg, host = shell
    agents = _agents(pg)
    assert "taskmaster" in agents.inner_text().lower() and "task types" not in agents.inner_text().lower()      # spec 36 §5: a monitor
    agents.get_by_role("button", name="+ Add agent").click()
    pg.get_by_role("dialog", name="Add an agent").get_by_role("button", name="Your own").click()
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
        pg.screenshot(path=str(SHOTS / "desktop-agents-1440x900.png"))


def test_every_dialog_has_a_dimmed_backdrop_an_opaque_panel_and_closes_on_esc(shell):
    pg, host = shell
    opens = [("New party", lambda: _new_party(pg)),
             ("New goal", lambda: pg.locator(".arena-new__pile").click()),
             ("Settings", lambda: pg.get_by_role("button", name="Settings").click()),
             ("Merge into", lambda: pg.locator("button.arena-into").click()),
             ("Drop this result?", lambda: pg.locator(".arena-result", has_text="Add the queue").get_by_role("button", name="Drop…").click()),
             ("Add an agent", lambda: (_agents(pg), pg.get_by_role("button", name="+ Add agent").click()))]
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


def test_the_stops_are_not_counted_a_closed_party_with_one_wears_a_sign_on_its_heading(shell):
    pg, host = shell
    assert pg.locator(".arena-phead .ork-count").count() == 0                                                                 # no count in the column (spec 54 §2.4)
    assert pg.locator(".arena-lead .ork-count.warning, .arena-goals .ork-count.warning, .arena-field .ork-count.warning").count() == 0      # nor of the party shown's stops
    ship = _party_card(pg, "ship-sync")
    assert ship.get_attribute("aria-current") == "true" and ship.locator(".ork-count, .arena-phead__stop").count() == 0     # the party shown: its stops lie in the hand
    grow = _party_card(pg, "grow")
    assert grow.locator(".ork-count").count() == 0 and grow.locator(".arena-phead__stop").count() == 1                      # a sign where its count was
    grow.click()
    pg.locator('.arena[data-goal="grow"]').wait_for(timeout=WAIT_MS)
    dot = _party_card(pg, "ship-sync").locator(".arena-phead__stop")                                                         # Ship sync's stops wait: the alert colour
    assert dot.count() == 1 and "is-danger" not in dot.get_attribute("class") and dot.get_attribute("title") == "3 wait in Ship sync"
    colour = dot.evaluate("e => getComputedStyle(e).color")
    assert colour == pg.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-alert)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")


def test_an_agent_is_one_line_with_its_head_its_name_how_many_and_what_a_task_costs(shell):
    pg, host = shell
    host.usd_task = {"grunt": 0.4}
    host.bump({})
    agents = _agents(pg)
    line = agents.locator(".shell-role[data-role=grunt] .shell-role__head")
    pg.wait_for_function("() => document.querySelector('.shell-role[data-role=grunt] .shell-role__head')?.getAttribute('aria-label')?.includes('$0.40')", timeout=WAIT_MS)
    assert line.get_attribute("aria-label") == "Grunts: an ork, Engineering, Seasoned; up to 8 at once; about $0.40 a task"
    assert " ".join(line.inner_text().split()).startswith("Grunts ×8 ≈ $0.40 a task Edit") and line.locator("img").count() == 1
    assert line.locator(".shell-role__week").inner_text() == "≈$1.25 today"                                 # its day, muted under the line
    assert "up to" not in line.inner_text() and "By Target" not in line.inner_text() and "tasks the first time" not in line.inner_text()
    tm = agents.locator(".shell-role[data-role=taskmaster] .shell-role__head")                       # its cost is its steps: no ×N, no cost of a task
    assert "×" not in tm.inner_text() and "a task" not in tm.inner_text()


def test_an_agent_chip_shows_its_short_name_on_two_lines_with_the_title_in_its_label(shell):
    pg, host = shell
    host.chip_extra = {"k3": {"short": "Retry offline", "idea_short": "Sync"}}
    host.bump({})
    _agents(pg)
    chip = pg.locator(".shell-chip", has_text="Retry offline")
    chip.wait_for(timeout=WAIT_MS)
    assert chip.get_attribute("title") == "Retry on a lost signal" and "Retry on a lost signal" in chip.get_attribute("aria-label")
    assert "Sync" in chip.locator(".shell-chip__idea").inner_text() and "Sync ideas between" not in chip.inner_text()
    assert chip.locator(".shell-chip__name").evaluate("e => getComputedStyle(e).webkitLineClamp") == "2"


def test_add_agent_opens_two_ways_from_the_library_and_your_own_and_the_built_in_two_show_what_they_are_told(shell):
    pg, host = shell
    _agents(pg).get_by_role("button", name="+ Add agent").click()
    choose = pg.get_by_role("dialog", name="Add an agent")
    choose.wait_for(timeout=WAIT_MS)
    assert choose.locator(".shell-library__row").count() > 5 and choose.get_by_role("button", name="Add Taskmaster").count() == 0   # the project's own are not offered
    row = choose.get_by_role("button", name="Add Copywriter")
    assert "Marketing" in row.inner_text() and row.locator("img").count() == 1                       # its head, name, craft and what it takes
    row.click()
    assert _sent(pg, host, ("ideas.role_add", {"id": "copywriter"}))
    pg.locator(".shell-role[data-slug='copywriter']").wait_for(timeout=WAIT_MS)
    pg.locator(".shell-agents").get_by_role("button", name="+ Add agent").click()                    # added: no longer offered
    choose.wait_for(timeout=WAIT_MS)
    assert choose.get_by_role("button", name="Add Copywriter").count() == 0
    choose.get_by_role("button", name="Your own").click()
    assert pg.get_by_role("dialog", name="Add agent").get_by_label("Name").is_visible()              # today's form
    assert pg.get_by_role("dialog", name="Add agent").locator(".shell-told").count() == 0
    pg.keyboard.press("Escape")
    pg.get_by_role("button", name="Edit Taskmaster").click()
    dlg = pg.get_by_role("dialog", name="Edit agent")
    told = dlg.locator(".shell-told")
    assert told.get_attribute("open") is None and "What it is told already" in told.inner_text()      # folded
    told.locator("summary").click()
    assert "The Taskmaster reads each step's prompt." in told.inner_text() and told.locator("textarea, input").count() == 0    # read only
    assert dlg.get_by_label("Added to what it is told").is_visible()


def test_about_this_party_has_what_the_party_did_closed_at_first_and_read_when_opened(shell):
    """Spec 43 B: a fold under The party; its lines, the logged `opened`; *No work yet* while no goal has a plan."""
    pg, host = shell
    pg.get_by_role("button", name="About this party").click()
    pg.locator(".shell-goal").wait_for(timeout=WAIT_MS)
    fold = pg.locator(".shell-goal .shell-party")
    assert fold.get_attribute("open") is None and not [1 for n, _a in host.log if n == "ideas.party"]          # closed at first: not asked for
    fold.locator("summary").click()
    pg.wait_for_function("() => document.querySelectorAll('.shell-goal .shell-party li').length === 4", timeout=WAIT_MS)
    assert [" ".join(t.split()) for t in fold.locator("li").all_inner_texts()] == PARTY_LINES
    assert _sent(pg, host, ("ideas.party", {"goal": "ship-sync"}))
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "party", "ref": "ship-sync", "device": "desktop"}))
    host.party = {"ideas": 0, "leader": PARTY["leader"], "members": [], "checks": []}
    fold.locator("summary").click()
    fold.locator("summary").click()
    pg.wait_for_function("() => document.querySelector('.shell-goal .shell-party li')?.innerText === 'No work yet'", timeout=WAIT_MS)
