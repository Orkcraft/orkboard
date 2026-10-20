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


SAVED = "/home/me/Downloads/orkboard-logs-2026-10-19-120000.zip"            # what logs.save answers

class StubHost:
    """What part A's commands answer, in the shapes of §5; every change bumps `ideas_rev` and pushes a snapshot."""

    def __init__(self, look="camp", onboarding=None):
        self.look, self.onboarding, self.rev, self.log, self.ws = look, onboarding, 1, [], None
        self.party: dict = {"ideas": 0, "leader": None, "members": [], "checks": []}    # ideas.party (spec 43 B)
        self.price_hints = []
        self.sign_in: list[dict] = []                 # the snapshot's `sign_in` (spec 45 §4): the tools not signed in, as core/sign_ins.py serves them
        self.sign_in_needs: list[dict] = []           # the sign-in rows of Needs you (realm/board_map.py `sign_in_needs`)
        self.own_parties: list[dict] = []                                             # ideas.parties (spec 43 F)
        self.price_low, self.price_high, self.price_learned = 1.9, 5.7, True          # ideas.party_price (spec 43 C)
        self.plan = make_plan()
        self.into, self.push = "dev", False
        self.paired = [{"id": "p1", "name": "Pixel 8", "seen": "2026-10-17T09:30:00"}]
        self.target, self.autostart, self.night = "balance", True, "01:00-07:00"
        self.awake = {"mode": "carts", "why": "", "holding": False, "battery": False, "can": True, "how": "systemd-inhibit", "machine": "Mac", "paired": True}   # awake.state (spec 47 §3)
        self.awake_offer = ""                         # phones.list's awake_offer: "Mac" while the offer is to be asked
        self.goals = {"general": self.goal("general", "General", "normal", "ready", order=0),
                      "ship-sync": self.goal("ship-sync", "Ship sync", "normal", "ready", summary="Sync is the first thing a second device needs.\nIt touches sync.py.")}
        self.roles = {"taskmaster": {"slug": "taskmaster", "name": "Taskmaster", "model": "elder", "max_parallel": 1, "instruction": "", "builtin": True},
                      "grunt": {"slug": "grunt", "name": "Grunt", "model": "", "max_parallel": 8, "instruction": "", "builtin": True}}
        self.kinds = {k: "grunt" for k in ("code", "tests", "docs", "text", "research")}
        self.chip_extra: dict[str, dict] = {}             # spec 41 §3: a chip's short / idea_short, by task id
        self.usd_task: dict[str, float | None] = {}       # spec 41 §8: a role's cost a task by slug (`usd_task`)
        self.record: dict[str, dict | None] = {}          # spec 42 §4: a role's record of the last 30 days by slug (`record`)
        self.check_week: dict[str, dict | None] = {}      # spec 43 §4.1: a checker's check of the last 7 days by slug
        self.party_needs: list[dict] = []                 # spec 43 §4.2: the night's party proposals waiting (Needs you's `party` rows)
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
        self.trails: dict[str, dict] = {}             # spec 46: a goal's trail by slug: {at, busy, ideas: [its proposals' slugs, in the trail's order]}
        self.lens = {"lenses": [{"id": "text"}], "default": "text", "segments": [], "screens": []}    # ideas.lens
        self.unplanned = False                        # sync's spec says no plan yet (its tasks stay on the Board)
        self.checks = [{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "passed", "task": "k1", "tier": "elder"},   # sync's
                       {"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": False, "why": "It changes no screen", "state": "",
                        "task": "", "tier": "warrior"}]
        self.parts: list[dict] = []                                                                  # ideas.lens_code
        self.screen_png = ""                                                                         # ideas.lens_screen

    def lay_out(self, goal, titles, at="2026-10-20T09:00:00"):
        """The goal's leader laid out `titles` (spec 46 §3): each an idea in the state `proposed`, the goal's trail."""
        slugs = []
        for n, title in enumerate(titles):
            slug = f"t-{goal}-{n + 1}"
            self.ideas[slug] = self.idea(slug, title, "proposed", 30 + n, track=goal)
            slugs.append(slug)
        self.trails[goal] = {"at": at, "busy": False, "ideas": slugs}
        self.bump({})

    def waiting_trail(self, goal):
        return [s for s in self.trails.get(goal, {}).get("ideas", []) if self.ideas.get(s, {}).get("state") == "proposed"]

    def trail_of(self, goal):
        """A goal's `trail` {at, waiting, busy} (gui/ideas_goals.py `trail_rows`)."""
        got = self.trails.get(goal) or {}
        return {"at": got.get("at", ""), "busy": bool(got.get("busy")), "waiting": len(self.waiting_trail(goal))}

    def trail_needs(self):
        out = []
        for goal in self.trails:
            waiting = self.waiting_trail(goal)
            g = self.goals[goal]
            if waiting:
                out.append({"kind": "trail", "idea": "", "goal": goal, "title": g["title"], "short": g.get("short") or g["title"],
                            "text": f"{len(waiting)} ideas laid out", "priority": g["priority"], "blocks": False, "at": self.trails[goal]["at"],
                            "ideas": [{"slug": s, "title": self.ideas[s]["title"], "short": self.ideas[s]["title"]} for s in waiting]})
        return out

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
        return [n for n in out if (n["idea"] or n["goal"]) not in gone] + [base | n for n in self.party_needs] + list(self.sign_in_needs) + self.trail_needs()

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
                 **({"check": t["check"], "findings": t["findings"]} if "check" in t else {})}
                for t in self.plan["tasks"] if t["state"] == "review"]

    def snapshot(self):
        return {"t": "state", "state": {
            "focus": "board", "ideas_rev": self.rev, "look": self.look, "project": "orkline", "demo": False, "onboarding": self.onboarding or False,
            "words": [], "resources": {}, "orkspaces": [], "buildings": [], "roads": [], "alerts": [], "score": {},
            "limits": self.limits, "review_count": len(self.results()), "needs_you": 1, "sign_in": json.loads(json.dumps(self.sign_in)),
            "hud": {"gold": "$2.40", "show_gold": True, "lumber": "120k"}}}

    def page(self, slug):
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

    def handle(self, name, a):
        self.log.append((name, a))
        if name == "ideas.board":
            ideas = [i | {"thesis": "Gist in one line", "progress": {"done": 1, "total": 5} if i["slug"] == "sync" else {"done": 0, "total": 0}}
                     for i in self.ideas.values()]
            return {"tracks": [g | {"count": sum(1 for i in ideas if i["track"] == g["slug"]), "trail": self.trail_of(g["slug"])} for g in self.goals.values()],
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
                       "check_week": None, "head": {"craft": "engineering", "race": "peon", "tier": "elder"},
                       "state": "waiting", "waits_on": {"idea": "dark", "text": "waiting for your answers on “Dark mode”"}, "chips": []},
                      {"role": "grunt", "name": "Grunts", "model": "", "max_parallel": 8, "builtin": True, "spend_today": 1.25, "chips": chips,
                       "kinds": [k for k, r in self.kinds.items() if r == "grunt"], "usd_task": self.usd_task.get("grunt"),
                       "check_week": self.check_week.get("grunt"), "head": {"craft": "engineering", "race": "peon", "tier": "warrior"}}]
            blocks += [{"role": r["slug"], "name": r["name"], "model": r["model"], "max_parallel": r["max_parallel"], "builtin": False, "spend_today": 0,
                        "chips": [], "kinds": [k for k, x in self.kinds.items() if x == r["slug"]], "usd_task": self.usd_task.get(r["slug"]),
                        "check_week": self.check_week.get(r["slug"]), "head": r.get("head")} for r in self.roles.values() if not r["builtin"]]
            return {"roles": blocks, "done_today": [{"idea": "sync", "task": "k1", "title": "Read the sync code", "role": "grunt"}]}
        if name == "ideas.roles":
            return {"roles": [r | {"spend_today": 0, "record": self.record.get(r["slug"])} | ({"told": self.told[r["slug"]]} if r["slug"] in self.told else {}) for r in self.roles.values()],
                    "kinds": self.kind_list(),
                    "models": [{"id": "", "label": "The task's own tier"}, {"id": "elder", "label": "Elder tier (opus)"},
                               {"id": "warrior", "label": "Warrior tier (sonnet)"}, {"id": "laborer", "label": "Laborer tier (haiku)"}],
                    "library": [x | {"installed": x["id"] in self.roles} for x in library.listed()], "suggested": library.SUGGESTED, "seats": library.SEATS,
                    "parties": library.parties(), "tier_costs": dict(plans.DEFAULT_COST)}
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
                                         leader=self.leader(a.get("leader")) or old.get("leader"))
            return self.bump({"slug": slug})
        if name == "ideas.party":
            return json.loads(json.dumps(self.party))
        if name == "ideas.party_price":                                            # spec 43 C: a price, each checker adds $0.35
            checkers = [i for i in a.get("team", []) if i in ("reviewer", "accessibility-reviewer", "editor", "data-reviewer", "security-reviewer")]
            return {"low": self.price_low, "high": self.price_high, "learned": self.price_learned, "ideas": 12 if self.price_learned else 0,
                    "hints": list(self.price_hints),
                    "checks": [{"by": i, "name": i, "usd": 0.35, "share": 1 if i in a.get("every", []) else 0.5, "every": i in a.get("every", [])}
                               for i in checkers]}
        if name == "ideas.goal_accept":
            self.goals[a["slug"]]["busy"] = True
            return self.bump({"ok": True})
        if name == "ideas.goal":
            g = self.goals[a["slug"]]
            return g | {"description": g["about"], "talk": [], "busy": g.get("busy") or g["state"] == "reading", "sections": [], "trail": self.trail_of(a["slug"])}
        if name == "ideas.trail":                     # Lay out ideas (spec 46 §4): the goal's leader is laying it out now
            self.trails.setdefault(a["goal"], {"at": "", "ideas": []})["busy"] = True
            return self.bump({"ok": True})
        if name == "ideas.trail_take":                # Take all: each proposal of the goal that waits, taken
            for s in self.waiting_trail(a["goal"]):
                self.ideas[s].update(state="raw", queue="now")
            return self.bump({"ok": True})
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
        if name == "ideas.parties":                                                # spec 43 F: the person's parties
            return {"parties": json.loads(json.dumps(self.own_parties))}
        if name == "ideas.party_save":
            g = self.goals[a["goal"]]
            taken = next((p for p in self.own_parties if p["name"].lower() == a["name"].lower()), None)
            if taken and not a.get("replace"):
                return {"error": f"You have a party named “{taken['name']}”"}
            keep = {"name": a["name"], "craft": g.get("craft", "engineering"), "leader": (g.get("leader") or {}).get("slug", "taskmaster"),
                    "team": list(g.get("team", [])), "every": list(g.get("every", [])), "own": [], "goals": 0, "projects": 0, "met": 0, "saved": "2026-10-20T10:00:00"}
            if taken:
                taken.update(keep)
                return {"id": taken["id"]}
            self.own_parties.append({"id": f"p-{len(self.own_parties) + 1}", **keep})
            return {"id": self.own_parties[-1]["id"]}
        if name == "ideas.party_drop":
            self.own_parties = [p for p in self.own_parties if p["id"] != a["id"]]
            return {"ok": True}
        if name == "ideas.party_answer":
            self.party_needs = [n for n in self.party_needs if n["goal"] != a["goal"]]
            return self.bump({"ok": True})
        if name == "ideas.proposal":
            self.proposals.append(a["slug"])
            if a["slug"] in self.ideas and any(a["slug"] in t["ideas"] for t in self.trails.values()):     # a trail proposal: taken, or turned down
                if a.get("take"):
                    self.ideas[a["slug"]].update(state="raw", queue="now")
                else:
                    self.ideas.pop(a["slug"])
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
                    "tail_trusted": True, "tailscale": True, "fingerprint": "AB:CD", "open": [], "pairing": 100, "awake_offer": self.awake_offer}
        if name == "awake.state":
            return dict(self.awake)
        if name == "awake.set":
            self.awake["mode"] = a["mode"]
            return dict(self.awake)
        if name == "awake.offer":
            self.awake_offer = ""
            if a.get("yes"):
                self.awake["mode"] = "phone"
            return dict(self.awake)
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
        if name in ("tools.sign_in", "tools.sign_in_cancel", "tools.sign_in_done"):       # spec 45 §5: the desktop's commands
            e = next((x for x in self.sign_in if x["harness"] == a["harness"]), None)
            if e is None:
                return {"error": "That tool needs no sign-in"}
            if name == "tools.sign_in":
                e.update(state="open", why="", command="", **({"auto": False} if a.get("auto") is not True else {}))
            elif name == "tools.sign_in_cancel":
                e.update(state="failed", why="cancelled")
            else:
                self.sign_in = [x for x in self.sign_in if x is not e]
            return self.bump(dict(e))
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


def _open(gui, viewport=None, host=None, ready=".shell-card", query=""):
    server, browser = gui
    host = host or StubHost()
    pg = browser.new_page(viewport=viewport or {"width": 1440, "height": 900})
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url + query)
    if ready:
        pg.wait_for_selector(ready, timeout=WAIT_MS)
    return pg, host, errors


def _show_goal(pg, slug="ship-sync"):
    """The Board shows one goal (as the phone's): this one, picked in its select (and kept, as the person's last)."""
    pg.locator(f'.board-goals__select option[value="{slug}"]').wait_for(state="attached", timeout=WAIT_MS)
    pg.get_by_label("Goal", exact=True).select_option(slug)


def _needs(pg):
    """Needs you: the right column (spec 46 §6.3), its rows under its head."""
    pg.locator(".shell-review").get_by_role("heading", name="Needs you").wait_for(timeout=WAIT_MS)
    pg.locator(".shell-review .board-today").wait_for(timeout=WAIT_MS)


def _board(pg):
    """The Board's tab (the left column's: Board · Files)."""
    pg.locator(".shell-board").get_by_role("tab", name="Board").click()


@pytest.fixture
def shell(gui):
    pg, host, errors = _open(gui)
    _show_goal(pg)                                    # most of the stub's ideas are Ship sync's
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
    unread = top.locator(".shell-limit").nth(2)                  # a tool turned on whose limits were not read: never missing
    assert "is-unread" in unread.get_attribute("class") and "?" in unread.inner_text() and "%" not in unread.inner_text()
    unread.hover()
    assert "Codex: limits not read" in unread.locator(".shell-pop").inner_text() and "Not logged in" in unread.inner_text()
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

    _needs(pg)
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


def test_a_checks_card_says_what_it_found_and_has_fix_them_and_leave_them(shell):
    """Spec 43 A §1.4: under the title "Found 3: 1 fixed, 2 left" and the findings left; Fix them sends back with them as its why; Leave them merges."""
    pg, host = shell
    none = {"passed": 0, "failed": 0, "failing": [], "tail": "", "green": True, "ran": False}
    host.plan["tasks"].append(task("k6", "Check: Reviewer", "review", ["k5"], tests=none, diff={"files": 0, "added": 0, "removed": 0}, check="Reviewer",
                                   findings=[{"where": "sync.py:12", "what": "the retry never stops", "fixed": True},
            {"where": "queue.py:3", "what": "a lost signal drops the item", "fixed": False},
            {"where": "queue.py:40", "what": "the queue is not emptied", "fixed": False}], note="2 left"))
    host.plan["tasks"].append(task("k7", "Check: Editor", "review", ["k5"], tests=none, diff={"files": 0, "added": 0, "removed": 0}, check="Editor",
                                   findings=[{"where": "a", "what": "b", "fixed": True}]))
    host.plan["tasks"].append(task("k8", "Check: Security reviewer", "review", ["k5"], tests=none, diff={"files": 0, "added": 0, "removed": 0},
                                   check="Security reviewer", findings=[{"where": "auth.py:9", "what": "a token is logged", "fixed": False}]))
    host.bump({})
    card = pg.locator(".shell-card", has_text="Check: Reviewer")
    card.wait_for(timeout=WAIT_MS)
    text = card.inner_text()
    assert "Found 3: 1 fixed, 2 left" in text and "queue.py:3 · a lost signal drops the item" in text and "queue.py:40 · the queue is not emptied" in text
    assert "the retry never stops" not in text                                                            # only the findings left are listed
    assert "Found" not in pg.locator(".shell-card", has_text="Check: Editor").inner_text()                # nothing left: today's card
    assert pg.locator(".shell-card", has_text="Check: Editor").get_by_role("button", name="Merge into dev").is_enabled()
    card.get_by_role("button", name="Fix them").click()
    line = card.get_by_label("What to fix, in one line")
    why = "Fix the findings left: queue.py:3: a lost signal drops the item; queue.py:40: the queue is not emptied"
    assert line.input_value() == why
    card.locator(".shell-actions__line .ork-btn.primary").click()
    assert _sent(pg, host, ("ideas.back", {"slug": "sync", "task": "k6", "why": why}))
    pg.locator(".shell-card", has_text="Check: Security reviewer").get_by_role("button", name="Leave them").click()
    assert _sent(pg, host, ("ideas.merge", {"slug": "sync", "task": "k8"}))


def test_the_ideas_checks_say_clean_or_what_they_found(shell):
    pg, host = shell
    host.checks[0].update(found=0, fixed=0, left=0)
    host.checks[1].update(applies=True, why="", state="passed", found=2, fixed=1, left=1)
    host.bump({})
    pg.locator(".board-card", has_text="Sync ideas").click()
    checks = pg.locator(".shell-preview").get_by_role("list", name="Checks")
    checks.wait_for(timeout=WAIT_MS)
    assert [" ".join(t.split()) for t in checks.get_by_role("listitem").all_inner_texts()] == [
        "Reviewer clean", "Accessibility reviewer found 2: 1 fixed, 1 left"]


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
    assert _sent(pg, host, ("ideas.add", {"text": "Offline sync", "track": "ship-sync", "priority": "normal"}))      # the goal shown


def test_below_1024_the_phones_layout_three_tabs_and_the_preview_on_its_own_screen(gui):
    pg, host, errors = _open(gui, {"width": 900, "height": 800}, ready=".shell-tabs")
    try:
        tabs = pg.locator(".shell-tabs")
        labels = tabs.get_by_role("tab").evaluate_all("els => els.map(e => e.getAttribute('aria-label'))")
        assert [x.split(":")[0].split(",")[0] for x in labels] == ["Board", "Agents", "Needs you"]          # the phone's order
        needs = tabs.get_by_role("tab", name="Needs you")
        assert needs.get_attribute("aria-label") == "Needs you: 4 wait for your answer, 2 results to check"
        assert "warning" in needs.locator(".shell-count").get_attribute("class") and needs.locator(".shell-count").inner_text() == "6"   # an answer waits: the signal
        assert needs.locator("use").get_attribute("href").endswith("#warning-diamond")
        assert pg.locator(".shell-review").is_hidden() and pg.locator(".shell-board").is_visible()
        needs.click()
        assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "tab", "ref": "needs", "device": "desktop"}))
        assert pg.locator(".shell-review").is_visible() and pg.locator(".shell-review .board-need").count() > 0 and pg.locator(".shell-reviewing").is_visible()
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
    assert dlg.locator(".shell-craft-tile").count() == 6                                            # its craft: one row of five and Mixed
    assert dlg.locator('.shell-craft-tile[aria-pressed="true"]').get_attribute("data-craft") == "engineering"     # Engineering is picked at the start
    assert dlg.get_by_label("Description").evaluate("e => e === document.activeElement")            # the description is focused
    assert dlg.get_by_role("button", name="Save goal").is_disabled()                                 # a description is required
    assert dlg.get_by_role("button", name="Next").count() == 0 and dlg.get_by_role("list", name="Step 1 of 3").count() == 0   # one sheet, no steps
    dlg.locator('.shell-craft-tile[data-craft="design"]').click()                                   # the craft's party, in the seats at once
    assert "Design: " in dlg.locator(".shell-craft-line").inner_text()
    team = dlg.get_by_role("region", name="Team")
    assert "Leads: Product designer" in team.inner_text()                                           # folded to one line
    team.locator("[data-change=team]").click()                                                      # three folds, Leads open
    leads, builds, checks_ = dlg.get_by_role("region", name="Leads"), dlg.get_by_role("region", name="Builds"), dlg.get_by_role("region", name="Checks")
    assert leads.locator('.shell-team-row[aria-pressed="true"]').get_attribute("data-agent") == "product-designer"
    assert builds.locator(".shell-team-row").count() == 0                                           # one fold open at a time
    dlg.get_by_role("button", name="Take in: Analyst").click()                                      # another leader: a pick folds Leads and opens Builds
    assert leads.locator(".shell-team-row").count() == 0 and builds.locator(".shell-team-seat").count() == 3
    assert builds.locator(".shell-team-seat:not(.is-empty)").count() == 2
    dlg.get_by_role("button", name="Take in: Copywriter").click()                                   # the third builder
    dlg.get_by_role("button", name="Take in: Grunt").click()                                        # a fourth: no seat
    assert builds.locator(".shell-team-seat:not(.is-empty)").count() == 3
    leads.get_by_role("button", name="Leads").click()                                               # a fold's head opens it again, the other closes
    assert leads.locator('.shell-team-row[aria-pressed="true"]').get_attribute("data-agent") == "analyst" and builds.locator(".shell-team-row").count() == 0
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-new-goal-team-1440x900.png"))
    dlg.locator('[data-done="lead"]').click()                                                       # every fold closed by Done: back to the line
    assert "Leads: Analyst" in team.inner_text() and team.locator("[data-change=team]").is_visible()
    assert "1 check, where each applies" in dlg.get_by_role("region", name="Checks").inner_text()  # the checks, folded to one line
    dlg.get_by_role("region", name="Checks").locator("[data-change=checks]").click()
    checks = dlg.get_by_role("group", name="Checks")                                                # the party's checkers, what they add
    assert "Accessibility reviewer" in checks.inner_text() and "Analyst" not in checks.inner_text()
    checks.get_by_label("Every idea: Accessibility reviewer").check()
    dlg.locator('[data-done="checks"]').click()
    assert "1 check, 1 on every idea" in dlg.get_by_role("region", name="Checks").inner_text()
    assert dlg.get_by_label("Title").count() == 0 and dlg.get_by_label("Deadline").count() == 0     # nothing else is asked
    assert dlg.get_by_label("Metric 1: what is measured").count() == 0 and dlg.get_by_label("Link 1", exact=True).count() == 0
    dlg.get_by_label("Description").fill("More people try Orkline.")
    dlg.get_by_text("High", exact=True).click()
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-new-goal-1440x900.png"))
    dlg.get_by_role("button", name="Save goal").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.goal_save")[0] == {"about": "More people try Orkline.", "craft": "design", "leader": "analyst",
                                                      "team": ["ui-kit", "artist", "accessibility-reviewer", "copywriter"],
                                                      "every": ["accessibility-reviewer"], "priority": "high"}
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


def test_a_goal_whose_ideas_are_done_is_accepted_by_its_leader_and_its_next_ideas_are_added(shell):
    pg, host = shell
    host.goals["land"] = host.goal("land", "Landing page", "high", "ready", order=3, leader=host.leader("growth"),
                                   metrics=[{"name": "weekly installs", "target": "50", "how": "npm"}])
    host.ideas["page"] = host.idea("page", "The landing page", "done", 7, track="land")
    host.bump({})
    pg.get_by_label("Goal", exact=True).select_option("land")
    pg.get_by_role("button", name="Open goal Landing page").click()
    verdict = pg.locator(".shell-goal").get_by_role("region", name="Verdict")
    verdict.get_by_role("button", name="Ask Growth to accept").click()
    assert _sent(pg, host, ("ideas.goal_accept", {"slug": "land"}))
    assert "Growth" in pg.locator(".shell-goal").get_by_role("region", name="Team").inner_text()      # the leader, first in the party
    host.goals["land"].update(busy=False, verdict={"met": False, "by": "Growth", "verdict": "Installs are at 30 a week, not 50.",
                                                    "metrics": [{"name": "weekly installs", "status": "not met", "why": "30 a week on npm"}],
                                                    "next": ["A post on the forum"]})
    host.bump({})
    verdict.get_by_text("Not met yet").wait_for(timeout=WAIT_MS)
    assert "30 a week on npm" in verdict.inner_text() and "by Growth" in verdict.inner_text()
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-goal-verdict-1440x900.png"))
    verdict.get_by_role("button", name="Add as idea: A post on the forum").click()
    assert _sent(pg, host, ("ideas.add", {"text": "A post on the forum", "track": "land", "priority": "normal"}))


def test_new_idea_needs_a_goal_a_priority_and_one_button_and_a_closed_dialog_goes_to_the_night(shell):
    pg, host = shell
    pg.get_by_role("button", name="New idea").click()
    dlg = pg.get_by_role("dialog", name="New idea")
    assert dlg.get_by_role("button", name="Add", exact=True).is_disabled() and dlg.get_by_role("button", name="Later").count() == 0
    assert dlg.get_by_label("Goal", exact=True).locator("option").all_inner_texts() == ["Grow installs", "Ship sync"]     # by priority; no General
    assert dlg.get_by_label("Goal", exact=True).input_value() == "ship-sync"                         # the goal shown
    assert dlg.get_by_label("Priority", exact=True).input_value() == "normal"                        # its priority
    dlg.get_by_label("Goal", exact=True).select_option("grow")
    assert dlg.get_by_label("Priority", exact=True).input_value() == "high"                          # follows the goal until the person picks one
    dlg.get_by_label("Goal", exact=True).select_option("ship-sync")
    dlg.get_by_label("Your idea").fill("Dark mode please")
    dlg.get_by_label("Priority", exact=True).select_option("high")
    dlg.get_by_role("button", name="Add", exact=True).click()
    pg.locator(".board-card", has_text="Dark mode please").wait_for(timeout=WAIT_MS)
    assert adds(host) == [{"text": "Dark mode please", "track": "ship-sync", "priority": "high"}]
    pg.get_by_role("button", name="New idea").click()                                               # closed with text: tonight's queue
    pg.get_by_label("Your idea").fill("Later idea")
    pg.get_by_role("button", name="Close", exact=True).click()
    pg.locator(".board-card", has_text="Later idea").wait_for(timeout=WAIT_MS)
    assert adds(host)[-1] == {"text": "Later idea", "track": "ship-sync", "priority": "normal", "night": True}
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
    pg.locator('.board-goals__select option[value=""]').wait_for(state="attached", timeout=WAIT_MS)
    pg.get_by_role("button", name="New idea").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    dlg.get_by_label("Description").fill("Make notes searchable.")
    dlg.get_by_role("button", name="Save goal").click()
    idea = pg.get_by_role("dialog", name="New idea")
    idea.wait_for(timeout=WAIT_MS)
    assert idea.get_by_label("Goal", exact=True).input_value() == "make-notes"


def test_the_board_shows_one_goal_its_card_its_party_and_its_ideas_and_the_goal_is_kept(gui):
    host = StubHost()
    host.goals["ship-sync"].update(craft="engineering", leader=host.leader("architect"), team=["tester", "reviewer"])
    for slug, name, craft, tier in (("tester", "Tester", "engineering", "laborer"), ("reviewer", "Reviewer", "engineering", "elder")):
        host.roles[slug] = {"slug": slug, "name": name, "model": tier, "max_parallel": 2, "instruction": "", "builtin": False,
                            "craft": craft, "head": {"craft": craft, "race": "peon", "tier": tier}}
    pg, host, errors = _open(gui, host=host)
    try:
        sel = pg.get_by_label("Goal", exact=True)
        pg.locator('.board-goals__select option[value="grow"]').wait_for(state="attached", timeout=WAIT_MS)
        assert "All goals" not in sel.locator("option").all_inner_texts()                               # one goal at a time
        assert sel.input_value() == "grow"                                                                # none kept yet: the first by priority
        assert pg.locator(".board-card").count() == 0 and "More people try Orkline." in pg.locator(".board-goal").inner_text()
        sel.select_option("ship-sync")
        card = pg.locator(".board-goal")
        assert card.locator(".board-goals__line").inner_text() == "Sync is the first thing a second device needs."
        assert "Led by Architect · Tester, Reviewer" in card.inner_text()                                 # its party: the leader first
        assert card.locator("img.ork-race__head").count() == 3
        assert "0 of 5 ideas done · 1 working" in card.inner_text()                                       # how far its ideas are
        assert pg.locator(".board-card", has_text="Dark mode").count() == 1
        if os.environ.get("ORKCRAFT_SHOTS"):
            SHOTS.mkdir(parents=True, exist_ok=True)
            pg.screenshot(path=str(SHOTS / "desktop-board-goal-1440x900.png"))
        pg.get_by_role("button", name="Open goal Ship sync").click()
        pg.locator(".shell-goal").wait_for(timeout=WAIT_MS)
        assert _sent(pg, host, ("ideas.goal", {"slug": "ship-sync"}))
        pg.reload()                                                                                       # the goal shown is kept
        pg.locator('.board-goals__select option[value="grow"]').wait_for(state="attached", timeout=WAIT_MS)
        assert pg.get_by_label("Goal", exact=True).input_value() == "ship-sync"
        pg.get_by_role("button", name="Edit goal Ship sync").click()
        assert pg.get_by_role("dialog", name="Edit goal").is_visible()
        pg.keyboard.press("Escape")
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_edit_goal_changes_the_party_and_sends_it_only_when_changed(shell):
    pg, host = shell
    host.goals["ship-sync"].update(about="Sync between devices.", craft="engineering", leader=host.leader("architect"), team=["grunt", "reviewer"], every=[])
    host.bump({})
    pg.locator(".board-goal", has_text="Led by Architect").wait_for(timeout=WAIT_MS)                 # the Board has read it
    pg.get_by_role("button", name="Edit goal Ship sync").click()
    dlg = pg.get_by_role("dialog", name="Edit goal")
    party = dlg.get_by_role("group", name="Party")
    assert "led by Architect · builds: Grunt · checks: Reviewer" in party.inner_text()
    party.get_by_role("button", name="Change the party").click()
    party.get_by_role("button", name="Take in: Product manager").click()                              # another leader
    party.get_by_role("button", name="Take in: Tester").click()
    party.get_by_label("Every idea: Reviewer").check()
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-edit-goal-party-1440x900.png"))
    dlg.get_by_role("button", name="Save goal").click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    got = _calls(pg, host, "ideas.goal_save")[-1]
    assert (got["leader"], got["team"], got["every"]) == ("product-manager", ["grunt", "reviewer", "tester"], ["reviewer"])


def _prices(host):
    return [a for n, a in host.log if n == "ideas.party_price"]


def _price_calls(pg, host, n, ms=WAIT_MS):
    for _ in range(ms // 50):
        if len(_prices(host)) >= n:
            break
        pg.wait_for_timeout(50)
    return _prices(host)


def test_new_goal_says_a_partys_price_when_the_picker_opens_and_after_a_seat_changes(shell):
    pg, host = shell
    pg.get_by_role("button", name="New goal").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    line = dlg.locator(".shell-party-price")
    line.wait_for(timeout=WAIT_MS)                                                                  # asked when the sheet opens: Engineering's party
    assert " ".join(line.inner_text().split()) == "This party: about $2–6 an idea from this project's last 12 ideas"
    assert _price_calls(pg, host, 1)[0]["craft"] == "engineering"
    dlg.locator('.shell-craft-tile[data-craft="design"]').click()
    assert _price_calls(pg, host, 2)[-1] == {"leader": "product-designer", "team": ["ui-kit", "artist", "accessibility-reviewer"], "every": [], "craft": "design"}
    dlg.locator("[data-change=team]").click()
    dlg.get_by_role("button", name="Take in: Analyst").click()                                      # two changes inside 300 ms: one call
    dlg.get_by_role("button", name="Take in: Copywriter").click()
    got = _price_calls(pg, host, 3)
    pg.wait_for_timeout(600)
    assert len(_prices(host)) == 3 and got[-1]["leader"] == "analyst" and "copywriter" in got[-1]["team"]
    host.price_learned, host.price_low, host.price_high = False, 0.4, 1.2
    dlg.get_by_role("button", name="Take out: Copywriter").click()
    pg.wait_for_function("() => document.querySelector('.shell-party-price')?.textContent.includes('a first guess')", timeout=WAIT_MS)
    assert " ".join(line.inner_text().split()) == "This party: about $0.40–1.20 an idea a first guess: it learns from this project's ideas"
    dlg.locator("[data-change=checks]").click()
    checks = dlg.get_by_role("group", name="Checks")
    row = checks.locator(".shell-check-row", has_text="Accessibility reviewer")
    assert "adds about $0.35 to an idea it checks · about half of them" in row.inner_text()
    assert "an idea they all apply to" not in checks.inner_text()                                   # the tier-cost sum is gone
    row.get_by_label("Every idea: Accessibility reviewer").check()
    pg.wait_for_function("() => document.querySelector('.shell-check-row')?.textContent.includes('every idea')", timeout=WAIT_MS)
    assert "adds about $0.35 to an idea it checks · every idea" in row.inner_text()
    assert _prices(host)[-1]["every"] == ["accessibility-reviewer"]


def test_edit_goal_says_the_price_when_the_party_is_changed(shell):
    pg, host = shell
    host.goals["ship-sync"].update(about="Sync between devices.", craft="engineering", leader=host.leader("architect"), team=["grunt", "reviewer"], every=[])
    host.bump({})
    pg.locator(".board-goal", has_text="Led by Architect").wait_for(timeout=WAIT_MS)
    pg.get_by_role("button", name="Edit goal Ship sync").click()
    party = pg.get_by_role("dialog", name="Edit goal").get_by_role("group", name="Party")
    assert not _prices(host) and party.locator(".shell-party-price").count() == 0                   # not asked before the picker opens
    party.get_by_role("button", name="Change the party").click()
    party.locator(".shell-party-price").wait_for(timeout=WAIT_MS)
    assert _price_calls(pg, host, 1) == [{"leader": "architect", "team": ["grunt", "reviewer"], "every": [], "craft": "engineering"}]
    assert "This party: about $2–6 an idea" in party.locator(".shell-party-price").inner_text()
    assert "adds about $0.35 to an idea it checks · about half of them" in party.get_by_role("group", name="Checks").inner_text()


def test_the_hints_are_said_under_the_price_line_muted_and_save_stays_enabled(shell):
    pg, host = shell
    host.price_hints = ["Reviewer found nothing in its last 12 checks.", "No builders: each task goes to this project's agent for its type (the Grunt when none)."]
    pg.get_by_role("button", name="New goal").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    dlg.locator('.shell-craft-tile[data-craft="data"]').click()
    hints = dlg.locator(".shell-party-hint")
    hints.first.wait_for(timeout=WAIT_MS)
    assert _price_calls(pg, host, 2)[-1]["craft"] == "data"
    assert hints.all_inner_texts() == host.price_hints and "ok-tone-muted" in hints.first.get_attribute("class")
    host.price_hints = []                                                                            # a change that fits: the hints go
    dlg.locator("[data-change=team]").click()
    dlg.get_by_role("button", name="Builds").click()
    dlg.get_by_role("button", name="Take in: Copywriter").click()
    pg.wait_for_function("() => document.querySelectorAll('.shell-party-hint').length === 0", timeout=WAIT_MS)
    dlg.get_by_label("Description").fill("Count the sign-ups.")                                      # Save is never held by a hint
    assert dlg.get_by_role("button", name="Save goal").is_enabled()


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


def test_needs_you_is_the_right_column_of_every_goal_s_rows_the_questions_one_form_and_a_proposal_is_answered_in_its_row(shell):
    pg, host = shell
    assert pg.locator(".shell-board .board-today").count() == 0                                     # not on the Board: the right column's
    assert "4" in pg.locator(".shell-review > header").inner_text()                                # a proposal is no count
    assert "export" not in pg.locator(".board-ideas").inner_text().lower() and "Search the notes" not in pg.locator(".board-ideas").inner_text()    # each idea in one place
    _needs(pg)
    kinds = pg.locator(".board-need, .board-proposal").evaluate_all("els => els.map(e => e.dataset.kind)")
    assert kinds == ["todo", "plan", "asks", "goal", "proposal"]                                    # the host's order; proposals last
    assert "Sync ideas between the phone and the town" in pg.locator(".board-need").first.inner_text() and "API_KEY" in pg.locator(".board-need").first.inner_text()
    assert "A spec asks · Ship sync" in pg.locator(".board-need[data-kind=asks]").inner_text()      # every goal's: each row says its goal
    pg.get_by_role("button", name="More: Search the notes").click()                                # the spec's questions: a box each, one Send
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
    pg.get_by_role("button", name="More: Grow installs").click()                                   # a goal that asks
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


def test_a_question_comes_with_its_answer_picked_one_send_takes_it_and_later_puts_a_row_away(shell):
    pg, host = shell
    host.goals["grow"]["questions"] = ["Which channel first?"]
    host.goals["grow"]["asked"] = [{"ask": "Which channel first?", "choices": ["npm", "the forum"], "pick": 1, "why": "the forum answers in a day"}]
    host.bump({})
    _needs(pg)
    row = pg.locator(".board-need[data-kind=goal]")
    row.get_by_role("button", name="the forum").wait_for(timeout=WAIT_MS)
    forum = row.get_by_role("button", name="the forum")
    assert forum.get_attribute("aria-pressed") == "true" and "Recommended" in forum.inner_text()      # the pick is pressed, and said in words
    assert row.get_by_role("button", name="npm").get_attribute("aria-pressed") == "false"
    assert "the forum answers in a day" in row.inner_text()                                           # its why, under the question
    assert row.get_by_role("button", name="Send: Grow installs").is_enabled()                         # one tap takes every recommendation
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-needs-you-1440x900.png"))
    row.get_by_role("button", name="Send: Grow installs").click()
    assert _sent(pg, host, ("ideas.answer", {"slug": "grow", "answers": ["the forum"], "goal": True}))
    tab = pg.locator(".shell-review > header")
    before = tab.inner_text()
    pg.get_by_role("button", name="Later: Export notes").click()                                    # put away here; nothing is sent
    pg.locator(".board-need[data-kind=plan]").wait_for(state="detached", timeout=WAIT_MS)
    assert tab.inner_text() != before
    pg.get_by_role("button", name="Put away for later (1): show").click()
    assert pg.locator(".board-list.is-later .board-need[data-kind=plan]").count() == 1


def test_a_choice_can_be_changed_more_fills_the_picks_and_let_the_taskmaster_decide_answers_with_them(shell):
    pg, host = shell
    host.goals["grow"]["questions"] = ["Which channel first?", "Which month?"]
    host.goals["grow"]["asked"] = [{"ask": "Which channel first?", "choices": ["npm", "the forum"], "pick": 0, "why": "most installs come from it"},
                                   {"ask": "Which month?", "choices": [], "pick": None, "why": ""}]
    host.bump({})
    _needs(pg)
    row = pg.locator(".board-need[data-kind=goal]")
    row.get_by_role("button", name="the forum").wait_for(timeout=WAIT_MS)
    row.get_by_role("button", name="the forum").click()                                              # another choice replaces the pick
    assert row.get_by_role("button", name="the forum").get_attribute("aria-pressed") == "true"
    assert row.get_by_role("button", name="npm").get_attribute("aria-pressed") == "false"
    row.get_by_role("button", name="More: Grow installs").click()                                     # the form, the picks filled in
    dlg = pg.get_by_role("dialog", name="Questions: Grow installs")
    assert dlg.get_by_label("Answer 1: Which channel first?").input_value() == "the forum"
    assert dlg.get_by_label("Answer 2: Which month?").input_value() == "" and "most installs come from it" in dlg.inner_text()
    dlg.get_by_label("Answer 2: Which month?").fill("November")
    dlg.get_by_role("button", name="Send").click()
    assert _sent(pg, host, ("ideas.answer", {"slug": "grow", "answers": ["the forum", "November"], "goal": True}))
    host.asked.remove("grow")
    host.bump({})
    pg.get_by_role("button", name="Let the Taskmaster decide: Grow installs").click()
    assert _sent(pg, host, ("ideas.answer", {"slug": "grow", "decide": True, "goal": True}))


def test_a_proposal_declined_with_a_reason_or_without(shell):
    pg, host = shell
    _needs(pg)
    prop = pg.locator(".board-proposal")
    prop.get_by_role("button", name="No: Tag the notes").click()
    prop.get_by_label("Why not: Tag the notes").fill("not now")
    prop.get_by_role("button", name="Decline: Tag the notes").click()
    pg.wait_for_function("() => document.querySelectorAll('.board-proposal').length === 0", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.proposal", {"slug": "tags", "take": False, "reason": "not now"}))


PARTY_ROW = {"kind": "party", "idea": "", "goal": "grow", "by": "reviewer", "title": "Take Reviewer out of Grow installs' party?",
             "text": "It found nothing in the last 8 ideas; a check costs about $0.35.", "priority": "high"}


def test_a_party_proposal_is_answered_in_its_row_taken_out_or_kept_and_is_never_counted(shell):
    pg, host = shell
    host.party_needs = [dict(PARTY_ROW)]
    host.bump({})
    assert "4" in pg.locator(".shell-review > header").inner_text()                                   # a party's proposal is no count either
    _needs(pg)
    kinds = pg.locator(".board-need, .board-proposal").evaluate_all("els => els.map(e => e.dataset.kind)")
    assert kinds[-2:] == ["proposal", "party"]                                                          # sorted last with the proposals
    row = pg.locator(".board-proposal[data-kind=party]")
    text = row.inner_text()
    assert "Take Reviewer out of Grow installs' party?" in text and "It found nothing in the last 8 ideas; a check costs about $0.35." in text
    assert "A party's proposal" in text
    row.get_by_role("button", name="Keep it: " + PARTY_ROW["title"]).click()                           # Keep it asks why, optional
    row.get_by_label("Why not: " + PARTY_ROW["title"]).fill("it guards the invoices")
    row.get_by_role("button", name="Keep: " + PARTY_ROW["title"]).click()
    pg.wait_for_function("() => document.querySelectorAll('.board-proposal[data-kind=party]').length === 0", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.party_answer", {"goal": "grow", "take": False, "reason": "it guards the invoices"}))


def test_a_party_proposal_taken_out_sends_no_reason(shell):
    pg, host = shell
    host.party_needs = [dict(PARTY_ROW)]
    host.bump({})
    _needs(pg)
    pg.get_by_role("button", name="Take it out: " + PARTY_ROW["title"]).click()
    pg.wait_for_function("() => document.querySelectorAll('.board-proposal[data-kind=party]').length === 0", timeout=WAIT_MS)
    assert _sent(pg, host, ("ideas.party_answer", {"goal": "grow", "take": True}))


def test_a_checkers_line_ends_with_its_check_of_the_week(shell):
    pg, host = shell
    host.usd_task = {"grunt": 0.4}
    host.check_week = {"grunt": {"checks": 6, "clean": 4, "caught": 2, "left": 1, "usd_per_check": None}}      # any role with a check_week says it
    host.bump({})
    week = pg.locator(".shell-agents .shell-role[data-role=grunt] .shell-role__week")
    pg.wait_for_function("() => document.querySelector('.shell-role[data-role=grunt] .shell-role__week')?.textContent.includes('its check')", timeout=WAIT_MS)
    assert week.inner_text() == "≈$1.25 today · its check: 6 ideas, caught 2"
    host.check_week = {"grunt": {"checks": 1, "clean": 1, "caught": 0, "left": 0, "usd_per_check": None}}
    host.bump({})
    pg.wait_for_function("() => document.querySelector('.shell-role[data-role=grunt] .shell-role__week')?.textContent.endsWith('its check: 1 idea, caught 0')", timeout=WAIT_MS)
    host.check_week = {"grunt": {"checks": 0, "clean": 0, "caught": 0, "left": 0, "usd_per_check": None}}
    host.bump({})
    pg.wait_for_function("() => document.querySelector('.shell-role[data-role=grunt] .shell-role__week')?.textContent === '≈$1.25 today'", timeout=WAIT_MS)


def test_a_check_that_has_not_run_is_skipped_from_the_spec_and_a_skipped_one_is_taken_again_before_a_plan(shell):
    pg, host = shell
    host.checks[1].update(applies=True, why="", state="", task="")                                   # no task yet: in the plan to come
    host.unplanned = True
    host.bump({})
    pg.locator(".board-card", has_text="Sync ideas").click()
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
    pg.locator(".board-card", has_text="Sync ideas").click()
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
    pg.locator(".board-card", has_text="Offline mode").click()
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
    _show_goal(pg)
    pg.context.grant_permissions(["clipboard-read", "clipboard-write"])
    card = pg.locator(".board-card", has_text="Offline mode")
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
    pg.locator(".board-card", has_text="Dark mode").click(button="right")
    pg.keyboard.press("Escape")                                                 # Esc closes the menu, not the tab under it
    assert menu.count() == 0 and alert.is_visible()
    pg.close()
    assert not errors, "\n".join(errors)


def test_in_a_browser_a_right_click_is_the_browsers_own(shell):
    pg, host = shell
    pg.locator(".board-card", has_text="Offline mode").click(button="right")
    assert pg.get_by_role("menu", name="Copy").count() == 0


def test_a_file_todo_shows_its_steps_and_uploads_the_file_and_a_secret_shows_its_steps_too(shell, tmp_path):
    pg, host = shell
    _needs(pg)
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
             ("Add an agent", lambda: pg.get_by_role("button", name="+ Add agent").click()),
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


def test_the_needs_you_count_is_the_warning_and_review_s_stays_plain(shell):
    pg, host = shell
    count = pg.locator(".shell-review > header .shell-count")                                          # the right column's head
    assert "warning" in count.get_attribute("class") and count.inner_text() == "4"                    # an answer waits: the warning colour
    colour = count.evaluate("e => getComputedStyle(e).backgroundColor")
    assert colour == pg.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-warning)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
    review = pg.locator(".shell-reviewing .shell-count")
    assert review.count() == 1 and "warning" not in review.get_attribute("class")                     # Review's section count stays plain


def test_an_agent_is_one_line_with_its_head_its_name_how_many_and_what_a_task_costs(shell):
    pg, host = shell
    host.usd_task = {"grunt": 0.4}
    host.bump({})
    agents = pg.locator(".shell-agents")
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
    chip = pg.locator(".shell-chip", has_text="Retry offline")
    chip.wait_for(timeout=WAIT_MS)
    assert chip.get_attribute("title") == "Retry on a lost signal" and "Retry on a lost signal" in chip.get_attribute("aria-label")
    assert "Sync" in chip.locator(".shell-chip__idea").inner_text() and "Sync ideas between" not in chip.inner_text()
    assert chip.locator(".shell-chip__name").evaluate("e => getComputedStyle(e).webkitLineClamp") == "2"


def test_add_agent_opens_two_ways_from_the_library_and_your_own_and_the_built_in_two_show_what_they_are_told(shell):
    pg, host = shell
    pg.locator(".shell-agents").get_by_role("button", name="+ Add agent").click()
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


PARTY = {"ideas": 9, "leader": {"slug": "product-manager", "name": "Product manager", "head": {"craft": "product", "race": "lich", "tier": "elder"}, "usd": 4.1},
         "members": [{"slug": "grunt", "name": "Grunt", "head": {"craft": "engineering", "race": "peon", "tier": "warrior"}, "tasks": 14, "merged": 13, "first_time": 12, "usd": 9.2}],
         "checks": [{"by": "accessibility-reviewer", "name": "Accessibility reviewer", "head": {"craft": "engineering", "race": "peon", "tier": "warrior"},
                     "applied": 6, "skipped": 1, "clean": 4, "caught": 2, "left": 1, "before": 2, "usd": 1.8}]}
PARTY_LINES = ['Product manager (leads): ≈$4.10 for the goal, the drafts and the plans', 'Grunt: 14 tasks, 12 merged the first time · ≈$9.20', 'Accessibility reviewer: checked 6 ideas: 4 clean, caught 2 (1 left) · ≈$1.80 · skipped 1 · 2 before findings were kept']


def test_the_goals_screen_has_a_fold_for_what_its_party_did_closed_at_first_and_read_when_opened(shell):
    pg, host = shell
    host.party = PARTY
    pg.get_by_label("Goal", exact=True).select_option("ship-sync")
    pg.get_by_role("button", name="Open goal Ship sync").click()
    sec = pg.locator(".shell-goal").get_by_role("region", name="What the party did")
    fold = sec.get_by_role("button", name="What the party did")
    fold.wait_for(timeout=WAIT_MS)
    assert fold.get_attribute("aria-expanded") == "false" and not [1 for n, _a in host.log if n == "ideas.party"]    # closed: not asked for
    fold.click()
    sec.get_by_role("list", name="What the party did").wait_for(timeout=WAIT_MS)
    assert [" ".join(t.split()) for t in sec.locator("li").all_inner_texts()] == PARTY_LINES
    assert sec.locator("li img.ork-race__head").count() == 3                                       # a head each, the words in the text face
    assert _sent(pg, host, ("ideas.party", {"goal": "ship-sync"}))
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "party", "ref": "ship-sync", "device": "desktop"}))
    fold.click()
    assert fold.get_attribute("aria-expanded") == "false" and sec.locator("li").count() == 0


def test_a_goal_with_no_work_yet_says_so(shell):
    pg, host = shell
    pg.get_by_label("Goal", exact=True).select_option("ship-sync")
    pg.get_by_role("button", name="Open goal Ship sync").click()
    sec = pg.locator(".shell-goal").get_by_role("region", name="What the party did")
    sec.get_by_role("button", name="What the party did").click()
    sec.get_by_text("No work yet").wait_for(timeout=WAIT_MS)


# -- spec 43 F: your parties ---------------------------------------------------------------------------------------------------

LEAN = {"id": "p-1", "name": "Lean web", "craft": "design", "leader": "product-designer", "team": ["ui-kit", "accessibility-reviewer"],
        "every": ["accessibility-reviewer"], "own": [], "goals": 3, "projects": 2, "met": 2, "saved": "2026-10-20T10:00:00"}


def _dialogs(pg, answer=True):
    """Every native confirm from now on is answered; the messages are kept."""
    said = []
    pg.on("dialog", lambda d: (said.append(d.message), d.accept() if answer else d.dismiss()))
    return said


def test_save_this_party_asks_a_name_saves_it_and_a_taken_name_asks_to_replace(shell):
    pg, host = shell
    host.goals["ship-sync"].update(craft="engineering", leader=host.leader("architect"), team=["grunt", "reviewer"], every=[])
    pg.get_by_label("Goal", exact=True).select_option("ship-sync")
    pg.get_by_role("button", name="Open goal Ship sync").click()
    team = pg.locator(".shell-goal").get_by_role("region", name="Team")
    team.get_by_role("button", name="Save this party").click()
    name = team.get_by_label("Name of your party")
    assert name.input_value() == "Engineering party"                                               # filled with the craft's
    name.fill("Lean web")
    team.get_by_role("button", name="Save", exact=True).click()
    assert _sent(pg, host, ("ideas.party_save", {"goal": "ship-sync", "name": "Lean web"}))
    pg.get_by_text("Saved: pick it for a goal in any project.").wait_for(timeout=WAIT_MS)
    said = _dialogs(pg)
    team.get_by_role("button", name="Save this party").click()
    team.get_by_label("Name of your party").fill("lean WEB")
    team.get_by_role("button", name="Save", exact=True).click()
    assert _sent(pg, host, ("ideas.party_save", {"goal": "ship-sync", "name": "lean WEB", "replace": True}))
    assert said == ["Replace your party “Lean web”?"] and len(host.own_parties) == 1


def test_a_replace_that_is_declined_saves_nothing(shell):
    pg, host = shell
    host.own_parties = [dict(LEAN)]
    host.goals["ship-sync"].update(craft="engineering", leader=host.leader("architect"), team=["grunt"], every=[])
    pg.get_by_label("Goal", exact=True).select_option("ship-sync")
    pg.get_by_role("button", name="Open goal Ship sync").click()
    team = pg.locator(".shell-goal").get_by_role("region", name="Team")
    said = _dialogs(pg, answer=False)
    team.get_by_role("button", name="Save this party").click()
    team.get_by_label("Name of your party").fill("Lean web")
    team.get_by_role("button", name="Save", exact=True).click()
    for _ in range(10):
        if said:
            break
        pg.wait_for_timeout(50)
    assert said == ["Replace your party “Lean web”?"] and not [1 for n, _a in host.log if n == "ideas.party_save"]
    assert team.get_by_label("Name of your party").is_visible()                                     # the name stays to be changed


def test_your_parties_fill_the_craft_and_the_seats_in_new_goal_and_the_id_goes_with_the_save(shell):
    pg, host = shell
    host.own_parties = [dict(LEAN)]
    pg.get_by_role("button", name="New goal").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    mine = dlg.get_by_role("region", name="Your parties")
    mine.wait_for(timeout=WAIT_MS)
    chip = mine.get_by_role("button", name="Pick your party “Lean web”")
    assert " ".join(chip.inner_text().split()) == "Lean web 3 goals in 2 projects · 2 met" and chip.locator("img.ork-race__head").count() == 3
    chip.click()
    assert chip.get_attribute("aria-pressed") == "true"
    line = " ".join(dlg.get_by_role("region", name="Team").inner_text().split())
    assert "Leads: Product designer" in line and "Accessibility reviewer" in line and "Grunt" not in line      # the engineering party's seats are gone
    assert dlg.locator('.shell-craft-tile[aria-pressed="true"]').get_attribute("data-craft") == "design"        # the craft is the party's
    dlg.locator("[data-change=checks]").click()
    assert dlg.get_by_role("group", name="Checks").get_by_label("Every idea: Accessibility reviewer").is_checked()
    dlg.get_by_label("Description").fill("A landing page.")
    dlg.get_by_role("button", name="Save goal").click()
    got = _calls(pg, host, "ideas.goal_save")[-1]
    assert (got["party"], got["craft"], got["leader"], got["team"], got["every"]) == (
        "p-1", "design", "product-designer", ["ui-kit", "accessibility-reviewer"], ["accessibility-reviewer"])


def test_a_seat_changed_after_picking_a_party_drops_its_id_and_the_save_sends_none(shell):
    pg, host = shell
    host.own_parties = [dict(LEAN)]
    pg.get_by_role("button", name="New goal").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    chip = dlg.get_by_role("button", name="Pick your party “Lean web”")
    chip.click()
    dlg.locator("[data-change=team]").click()
    dlg.get_by_role("button", name="Builds").click()
    dlg.get_by_role("button", name="Take in: Copywriter").click()                                   # a seat changed
    assert chip.get_attribute("aria-pressed") == "false"
    dlg.get_by_label("Description").fill("A landing page.")
    dlg.get_by_role("button", name="Save goal").click()
    got = _calls(pg, host, "ideas.goal_save")[-1]
    assert "party" not in got and "copywriter" in got["team"]


def test_a_party_picked_in_edit_goal_is_sent_and_remove_asks_first(shell):
    pg, host = shell
    host.own_parties = [dict(LEAN)]
    host.goals["ship-sync"].update(about="Sync between devices.", craft="engineering", leader=host.leader("architect"), team=["grunt"], every=[])
    host.bump({})
    pg.locator(".board-goal", has_text="Led by Architect").wait_for(timeout=WAIT_MS)
    pg.get_by_role("button", name="Edit goal Ship sync").click()
    party = pg.get_by_role("dialog", name="Edit goal").get_by_role("group", name="Party")
    assert party.get_by_role("region", name="Your parties").count() == 0                            # not before the picker opens
    party.get_by_role("button", name="Change the party").click()
    mine = party.get_by_role("region", name="Your parties")
    said = _dialogs(pg, answer=False)
    mine.get_by_role("button", name="Remove your party “Lean web”").click()
    for _ in range(10):
        if said:
            break
        pg.wait_for_timeout(50)
    assert said == ["Remove your party “Lean web”? Goals that use it keep their agents."]
    assert not [1 for n, _a in host.log if n == "ideas.party_drop"] and mine.get_by_role("button", name="Pick your party “Lean web”").is_visible()
    mine.get_by_role("button", name="Pick your party “Lean web”").click()
    pg.get_by_role("dialog", name="Edit goal").get_by_role("button", name="Save goal").click()
    got = _calls(pg, host, "ideas.goal_save")[-1]
    assert (got["party"], got["leader"], got["team"]) == ("p-1", "product-designer", ["ui-kit", "accessibility-reviewer"])


def test_remove_your_party_drops_it_after_the_person_agrees(shell):
    pg, host = shell
    host.own_parties = [dict(LEAN)]
    pg.get_by_role("button", name="New goal").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    said = _dialogs(pg)
    dlg.get_by_role("button", name="Remove your party “Lean web”").click()
    assert _sent(pg, host, ("ideas.party_drop", {"id": "p-1"}))
    dlg.get_by_role("region", name="Your parties").wait_for(state="detached", timeout=WAIT_MS)       # the row goes with its last party
    assert said == ["Remove your party “Lean web”? Goals that use it keep their agents."]


def _awake_field(pg):
    pg.get_by_role("button", name="Settings").click()
    group = pg.get_by_role("group", name="Keep the computer awake")
    group.wait_for(timeout=WAIT_MS)
    return group


def test_keep_the_computer_awake_has_three_choices_and_the_lines_of_its_state(shell):
    pg, host = shell
    group = _awake_field(pg)
    assert _sent(pg, host, ("awake.state", {}))
    assert [t.strip() for t in group.locator(".shell-seg__one").all_inner_texts()] == ["Never", "While the orks work", "Stay reachable from your phone"]
    assert group.locator(".shell-seg__one.is-on").inner_text().strip() == "While the orks work"
    text = group.inner_text()
    assert "On power, it does not sleep by itself while an ork or an operation is at work" in text
    assert "Not holding now: nothing to do." in text and "The screen still turns off." in text
    for why, line in (("work", "Holding now: an ork is at work."), ("tonight", "Holding now: the Board has work for tonight."),
                      ("phone", "Holding now: a phone is paired.")):
        host.awake |= {"why": why}
        pg.keyboard.press("Escape")
        group = _awake_field(pg)
        assert line in group.inner_text(), why
    host.awake |= {"battery": True}
    pg.keyboard.press("Escape")
    group = _awake_field(pg)
    assert "On battery now, so it may sleep." in group.inner_text() and "Holding now" not in group.inner_text()
    host.awake |= {"battery": False, "can": False}
    pg.keyboard.press("Escape")
    group = _awake_field(pg)
    text = group.inner_text()
    assert "This computer gives Orkline no way to keep it awake: set its power settings" in text and "The screen still turns off." not in text
    host.awake |= {"can": True, "mode": "phone", "paired": False}
    pg.keyboard.press("Escape")
    group = _awake_field(pg)
    text = group.inner_text()
    assert "On power, it does not sleep by itself while Orkline is open and a phone is paired" in text and "No phone is paired yet: Pair a phone, above." in text
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.screenshot(path=str(SHOTS / "desktop-awake-1440x900.png"))


def test_a_choice_of_keep_the_computer_awake_is_sent_at_once_and_never_says_the_old_word(shell):
    pg, host = shell
    group = _awake_field(pg)
    group.get_by_text("Never", exact=True).click()
    assert _sent(pg, host, ("awake.set", {"mode": "off"}))
    group.get_by_text("The computer sleeps as its power settings say.").wait_for(timeout=WAIT_MS)
    assert "Holding now" not in group.inner_text() and "The screen still turns off." not in group.inner_text()
    group.get_by_text("Stay reachable from your phone").click()
    assert _sent(pg, host, ("awake.set", {"mode": "phone"}))
    assert "carts" not in group.inner_text().lower()


def _after_pairing(pg, host, answer):
    host.awake_offer = "Mac"
    pg.get_by_role("button", name="Settings").click()
    pg.get_by_role("button", name="Pair a phone").click()
    dlg = pg.get_by_role("dialog", name="Pair a phone")
    dlg.locator("img.gui-phones__qr").wait_for(timeout=WAIT_MS)
    host.paired = host.paired + [{"id": "p2", "name": "iPhone 15", "seen": "2026-10-20T09:30:00"}]       # a phone scans the code
    offer = dlg.get_by_role("group", name="Keep the computer awake")
    offer.wait_for(timeout=5000)
    assert "Paired: iPhone 15." in dlg.inner_text()
    assert "Keep this Mac awake so your phone can reach it all day? Only on power." in offer.inner_text()
    offer.get_by_role("button", name=answer).click()
    offer.wait_for(state="detached", timeout=WAIT_MS)
    return dlg


def test_after_pairing_the_offer_to_keep_the_mac_awake_is_asked_once_and_yes_is_sent(shell):
    pg, host = shell
    _after_pairing(pg, host, "Yes")
    assert _sent(pg, host, ("awake.offer", {"yes": True}))


def test_not_now_to_the_offer_is_sent_and_the_offer_is_gone(shell):
    pg, host = shell
    dlg = _after_pairing(pg, host, "Not now")
    assert _sent(pg, host, ("awake.offer", {"yes": False}))
    assert dlg.get_by_role("group", name="Keep the computer awake").count() == 0 and "Paired: iPhone 15." in dlg.inner_text()

def test_an_agents_chip_started_by_the_pace_says_the_week_has_room(gui):
    host = StubHost()
    host.chip_extra = {"k3": {"pace": True}}
    pg, host, errors = _open(gui, host=host)
    _show_goal(pg)
    chips = pg.locator(".shell-agents .shell-chip")
    assert "by itself: the week has room" in chips.filter(has_text="Retry on a lost signal").inner_text()
    assert "the week has room" not in chips.filter(has_text="Dark palette").inner_text()             # by itself, but not by the pace
    pg.close()
    assert not errors, "\n".join(errors)


# -- Spec 46 C: the desktop catches up with the phone ----------------------------------------------------------------------------


def _store(pg, script):
    """Runs `script(m)` with the shell's store module (the page keeps one instance of it)."""
    pg.evaluate("async (src) => { const m = await import(document.querySelector('link[href$=\"shell.css\"]').href.replace('shell.css', 'store.js')); return new Function('m', src)(m); }", script)


def test_the_goal_select_ends_with_new_goal_which_opens_it_and_keeps_the_goal_and_the_boards_button_stays(shell):
    pg, host = shell
    select = pg.get_by_label("Goal", exact=True)
    assert select.locator("option").all_inner_texts()[-1] == "New goal…"                              # the last option (spec 46 §6.1)
    assert pg.locator(".board-goals__bar").get_by_role("button", name="New goal", exact=True).is_visible()   # the Board's stays
    assert select.input_value() == "ship-sync"
    select.select_option(label="New goal…")
    dlg = pg.get_by_role("dialog", name="New goal")
    dlg.wait_for(timeout=WAIT_MS)
    assert select.input_value() == "ship-sync"                                                        # the select keeps the goal shown
    pg.keyboard.press("Escape")
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    assert select.input_value() == "ship-sync"
    pg.locator(".board-goals__bar").get_by_role("button", name="New goal", exact=True).click()
    assert pg.get_by_role("dialog", name="New goal").is_visible()


def test_new_goal_is_one_sheet_save_waits_for_words_the_craft_sets_the_party_and_the_save_sends_the_three_steps_arguments(shell):
    pg, host = shell
    pg.locator(".board-goals__bar").get_by_role("button", name="New goal", exact=True).click()
    dlg = pg.get_by_role("dialog", name="New goal")
    save = dlg.get_by_role("button", name="Save goal")
    assert save.is_disabled() and [b.inner_text() for b in dlg.locator(".shell-modal__foot button").all()] == ["Cancel", "Save goal"]   # in the modal's foot
    assert [b.get_attribute("aria-label") for b in dlg.locator(".shell-craft-tile").all()] == ["Engineering", "Design", "Data", "Marketing", "Product", "Mixed"]
    dlg.get_by_label("Description").fill("   ")
    assert save.is_disabled()                                                                         # blanks are no words
    dlg.locator('.shell-craft-tile[data-craft="product"]').click()
    assert "Product: " in dlg.locator(".shell-craft-line").inner_text()                               # the picked one's word and line under the row
    assert "Leads: Product manager" in dlg.get_by_role("region", name="Team").inner_text()
    dlg.get_by_label("Description").fill("Know who it is for.")
    assert save.is_enabled()
    save.click()
    pg.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=WAIT_MS)
    got = _calls(pg, host, "ideas.goal_save")[0]
    assert got["craft"] == "product" and got["leader"] == "product-manager" and got["about"] == "Know who it is for." and got["priority"] == "normal"
    assert set(got) >= {"about", "craft", "leader", "team", "every", "priority"}


def test_the_right_column_is_needs_you_with_the_signal_its_rows_then_review_with_its_count_and_the_left_has_no_needs_you_tab(shell):
    pg, host = shell
    assert [t.lower() for t in pg.locator(".shell-board").get_by_role("tab").all_inner_texts()] == ["board"]             # the Needs you tab goes (Files with projects)
    head = pg.locator(".shell-review > header")
    assert head.get_by_role("heading", name="Needs you").is_visible()
    count = head.locator(".shell-count")
    assert "warning" in count.get_attribute("class") and count.inner_text() == "4"                    # the signal while an answer waits
    review = pg.get_by_role("region", name="Review")
    assert review.get_by_role("heading", name="Review").inner_text().split()[-1] == "2"
    assert review.locator(".shell-into").get_by_role("button", name="Merge into dev").is_visible() and review.locator(".shell-card").count() == 2
    rows, section = box(pg, ".shell-review .board-today"), box(pg, ".shell-reviewing")
    assert rows["y"] < section["y"]                                                                   # the rows, then Review
    assert pg.locator(".shell-review .board-need").count() >= 4
    assert pg.locator(".shell-board .board-today").count() == 0                                       # none on the left


def test_a_kept_needs_tab_reads_board_and_a_card_s_link_to_needs_you_focuses_the_right_column(shell):
    pg, host = shell
    _store(pg, "m.leftTab.value = 'needs';")
    pg.wait_for_timeout(200)
    assert pg.locator(".shell-board .shell-ltab.is-on").inner_text().lower() == "board" and pg.locator(".shell-board .board-goals").is_visible()
    _store(pg, "m.showNeeds();")
    pg.wait_for_function("() => document.activeElement === document.querySelector('.shell-review')", timeout=WAIT_MS)


def test_nothing_in_needs_you_or_review_says_nothing_waits_for_you(shell):
    pg, host = shell
    host.asked = ["sync", "export", "search", "grow"]
    host.proposals = ["tags"]
    for t in host.plan["tasks"]:
        if t["state"] == "review":
            t["state"] = "merged"
    host.bump({})
    pg.get_by_text("Nothing waits for you.").wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-review > header .shell-count").count() == 0 and pg.locator(".shell-review .shell-card").count() == 0


# -- Spec 46 D: the trail's faces on the desktop ----------------------------------------------------------------------------------

REVIEWER = {"slug": "reviewer", "name": "Reviewer", "head": {"craft": "engineering", "race": "peon", "tier": "elder"}}
LEADER = {"slug": "taskmaster", "name": "Taskmaster", "head": {"craft": "engineering", "race": "peon", "tier": "elder"}}


def test_a_goals_questions_say_who_asks_with_the_head_and_the_name_in_the_row_and_in_its_form(shell):
    pg, host = shell
    host.goals["grow"]["questions"] = ["Which channel first?", "Who checks the invoices?"]
    host.goals["grow"]["asked"] = [{"ask": "Which channel first?", "choices": ["npm", "the forum"], "pick": 0, "why": "", "by": LEADER},
                                   {"ask": "Who checks the invoices?", "choices": [], "pick": None, "why": "", "by": REVIEWER}]
    host.bump({})
    _needs(pg)
    row = pg.locator(".board-need[data-kind=goal]")
    row.locator(".board-quick__q").nth(1).wait_for(timeout=WAIT_MS)
    first, second = row.locator(".board-quick__q").nth(0), row.locator(".board-quick__q").nth(1)
    assert "Taskmaster asks:" in first.inner_text() and "Reviewer asks:" in second.inner_text()          # the leader's own too
    assert second.get_attribute("data-by") == "reviewer"
    for q in (first, second):
        assert q.locator("img.ork-race__head.small").count() == 1                                        # the head of who asks, 12 × 11
    row.get_by_role("button", name="More: Grow installs").click()
    dlg = pg.get_by_role("dialog", name="Questions: Grow installs")
    dlg.locator(".board-quick__by").nth(1).wait_for(timeout=WAIT_MS)
    assert "Reviewer asks:" in dlg.inner_text() and dlg.locator("img.ork-race__head.small").count() == 2


def test_the_trail_row_names_the_goal_and_its_first_three_ideas_take_all_sends_the_goal_and_the_count_is_unchanged(shell):
    pg, host = shell
    before = pg.locator(".shell-review > header .shell-count").inner_text()
    host.lay_out("ship-sync", ["Write the queue", "Retry on a lost signal", "Test it offline", "Write the notes", "Release it"])
    _needs(pg)
    row = pg.locator(".board-need[data-kind=trail]")
    row.wait_for(timeout=WAIT_MS)
    assert row.locator("b").first.inner_text() == "Ship sync: 5 ideas laid out" and row.locator("svg use[href$='#flag']").count() == 1
    assert row.locator(".board-trail__ideas li").all_inner_texts() == ["Write the queue", "Retry on a lost signal", "Test it offline", "and 2 more"]
    assert "primary" in row.get_by_role("button", name="Take all: Ship sync").get_attribute("class")
    assert pg.locator(".shell-review > header .shell-count").inner_text() == before                    # it blocks nothing: out of the count
    kinds = pg.locator(".board-need, .board-proposal").evaluate_all("els => els.map(e => e.dataset.kind)")
    assert kinds[-1] == "trail"                                                                          # among the proposals, last
    row.get_by_role("button", name="Take all: Ship sync").click()
    assert _sent(pg, host, ("ideas.trail_take", {"goal": "ship-sync", "via": "needs"}))
    row.wait_for(state="detached", timeout=WAIT_MS)


def test_a_trail_proposal_is_a_row_of_the_boards_ideas_with_take_and_no(shell):
    pg, host = shell
    host.lay_out("ship-sync", ["Write the queue", "Retry on a lost signal", "Test it offline"])
    ideas = pg.locator(".board-ideas")
    ideas.locator(".board-card-row.is-trail").nth(2).wait_for(timeout=WAIT_MS)
    rows = ideas.locator(".board-card-row.is-trail")
    assert rows.locator(".board-card__title").all_inner_texts() == ["Write the queue", "Retry on a lost signal", "Test it offline"]     # the trail's order
    assert rows.first.locator(".board-state").inner_text() == "proposed"
    rows.nth(1).get_by_role("button", name="No: Retry on a lost signal").click()
    assert rows.nth(1).get_by_label("Why not: Retry on a lost signal").input_value() == ""
    rows.nth(1).get_by_role("button", name="Decline: Retry on a lost signal").click()
    assert _sent(pg, host, ("ideas.proposal", {"slug": "t-ship-sync-2", "take": False, "via": "board"}))
    rows.first.get_by_role("button", name="Take: Write the queue").click()
    assert _sent(pg, host, ("ideas.proposal", {"slug": "t-ship-sync-1", "take": True, "via": "board"}))
    pg.wait_for_function("() => document.querySelectorAll('.board-card-row.is-trail').length === 1", timeout=WAIT_MS)


def test_lay_out_ideas_shows_only_while_the_goal_is_ready_and_no_trail_waits_and_the_goal_says_who_is_laying_out(shell):
    pg, host = shell
    host.goals["ship-sync"]["leader"] = REVIEWER | {"slug": "product-manager", "name": "Product manager"}
    host.bump({})
    pg.get_by_role("button", name="Open goal Ship sync").click()
    lay = pg.locator(".shell-goal").get_by_role("button", name="Lay out ideas")
    lay.wait_for(timeout=WAIT_MS)
    lay.click()
    assert _sent(pg, host, ("ideas.trail", {"goal": "ship-sync"}))
    pg.wait_for_function("() => document.querySelector('.board-goal').innerText.includes('is laying out its ideas…')", timeout=WAIT_MS)
    assert "Product manager is laying out its ideas…" in pg.locator(".board-goal").inner_text()
    pg.wait_for_function("() => document.querySelector('.shell-goal .board-bar').innerText.includes('is laying out its ideas…')", timeout=WAIT_MS)
    assert pg.locator(".shell-goal").get_by_role("button", name="Lay out ideas").is_disabled()
    host.trails["ship-sync"]["busy"] = False
    host.lay_out("ship-sync", ["Write the queue"])                                                          # a trail that waits: no Lay out ideas
    pg.wait_for_function("() => ![...document.querySelectorAll('.shell-goal button')].some((b) => b.textContent === 'Lay out ideas')", timeout=WAIT_MS)
