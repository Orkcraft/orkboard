"""The Map (docs/specs/39-map.md §1): a project's goals, ideas and tasks on one screen, as data. A pure read of what the
Board holds (the pages, `plan.json`, the claims' notes, the ledger): it writes nothing, starts nothing and writes no
words for a node's state — the faces word it with the functions that word the Board's row.

`row` and `idea_needs` are the Board's own (`gui/ideas_board.py` calls them), so a node and a Board row never differ.
`build` takes the host's reading of an idea's and a goal's state (`state_of`, `goal_state_of`: the keeper's busy flag
is the host's), else the files'.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Callable

from orkboard.realm import goal_flags, goal_verdict, idea_checks, idea_flag, idea_pick, idea_questions, idea_risk, idea_spend, idea_target, ideas, map_party, map_stage, roles
from orkboard.realm.idea_words import short_of

NEEDS = ("asks", "plan", "todo", "failed", "proposal")        # the Needs you kinds that sit on an idea, as a node names them
_HELD_FILES = re.compile(r"^files(?: beside)? · (.+)$")
_AFTER = re.compile(r"after (\d{1,2}:\d{2})")


def list_of_dicts(text: object) -> list[dict]:
    """A page field that holds a JSON list of objects (`checks`)."""
    try:
        got = json.loads(text) if str(text or "").strip() else []
    except ValueError:
        return []
    return [x for x in got if isinstance(x, dict)] if isinstance(got, list) else []


def list_of(text: object) -> list[str]:
    """A page field that holds a JSON list of text (`depends_on`, `risk_triggers`)."""
    try:
        got = json.loads(text) if str(text or "").strip() else []
    except ValueError:
        return []
    return [str(x) for x in got if isinstance(x, str)] if isinstance(got, list) else []


def idea_needs(root: Path, state_dir: Path, i: dict, st: dict, plan: dict | None, asks: list[str]) -> list[dict]:
    """What of one idea needs the person (spec 35 §10): its questions, its plan waiting, its to-dos, a failure, a proposal."""
    slug, state = i["slug"], st["state"]
    base = {"idea": slug, "goal": i["track"], "title": i["title"], "priority": i["priority"], "blocks": False,
            "at": ideas.touched_at(root, state_dir, slug)}
    tasks = (plan or {}).get("tasks") or []
    out = []
    if state == "asks":
        asked = [idea_questions.parse(q) for q in asks[:5]]
        out.append({**base, "kind": "asks", "text": asked[0]["ask"] if asked else "The keeper asks you", "questions": asks[:5],
                    "asked": asked})
    if state == "plan" and plan and not plan.get("passed_at"):
        out.append({**base, "kind": "plan", "text": "Plan ready" + (f" · {len(tasks)} tasks" if tasks else ""),
                    "at": str(plan.get("made_at") or base["at"])})
    if state == "proposed":
        out.append({**base, "kind": "proposal", "text": ideas.thesis(
            (ideas.idea_page(root, slug) or ideas.Page()).section("Gist")) or "The keeper proposes this"})
    if state == "failed":
        out.append({**base, "kind": "failed", "text": st.get("error") or "Something failed"})
    merged = {t.get("id") for t in tasks if t.get("state") == "merged"}
    if state == "working":
        for t in tasks:
            if t.get("state") == "failed":
                out.append({**base, "kind": "failed", "blocks": True, "text": f"{t.get('title', '')}: {t.get('error') or 'failed'}",
                            "at": str(t.get("finished") or base["at"])})
    if plan and state in ("plan", "working", "failed"):
        for td in plan.get("todos") or []:
            if td.get("done"):
                continue
            waits = [t for t in tasks if t.get("id") in (td.get("for") or []) and t.get("state") != "merged"
                     and set(t.get("after") or []) <= merged]
            out.append({**base, "kind": "todo", "text": td.get("title") or "", "blocks": state == "working" and bool(waits),
                        "at": str(plan.get("made_at") or base["at"]),
                        "todo": {k: td.get(k) for k in ("id", "title", "kind", "why", "choices", "steps", "accept", "done")}})
    return out


def task_short(t: dict) -> str:
    """A task's short name: the plan's, else made from its title (a plan of before spec 41)."""
    return str(t.get("short") or "") or short_of(str(t.get("title") or ""))


def _night_by(i: dict, st: dict, plan: dict | None) -> str:
    """Who put it off to the night, for what waits for it; "board" only while the idea is still Low (raised to High or Normal it is as the person's)."""
    low = i["priority"] == "low"
    if st["state"] == "raw" and ideas.queue_of(st) == "night":
        return ideas.night_by_of(st) if low else "person"
    if st["state"] == "plan" and (plan or {}).get("start_at") == "night":
        return "board" if low and (plan or {}).get("start_at_by") == "board" else "person"
    return ""


def row(root: Path, state_dir: Path, i: dict, st: dict, plan: dict | None, page: ideas.Page | None, asks: list[str],
        states: dict[str, dict], mine: list[dict]) -> dict:
    """An idea as `ideas.board` lists it: the state and what words it (queue, held_until, start_at, progress, waits_on)."""
    slug = i["slug"]
    tasks = (plan or {}).get("tasks") or []
    depends = list_of(page.get("depends_on")) if page else []
    return {"slug": slug, "title": i["title"], "short": i["short"], "track": i["track"], "order": i["order"],
            "state": st["state"], "size": i["size"], "thesis": i["thesis"], "asks": len(asks),
            "priority": i["priority"],
            "progress": {"done": sum(1 for t in tasks if t.get("state") == "merged"), "total": len(tasks)},
            "updated": ideas.touched_at(root, state_dir, slug),
            "queue": ideas.queue_of(st), "held_until": st["held_until"],
            "risk": idea_risk.level(page.get("risk")) if page and page.get("risk") else "",
            "risk_triggers": list_of(page.get("risk_triggers")) if page else [],
            "depends_on": depends,
            "waits_on": [d for d in depends if states.get(d, {}).get("state") != "done"],
            "start_at": str((plan or {}).get("start_at") or ""),
            "night_by": _night_by(i, st, plan),
            "in_needs_you": any(n["kind"] in ("asks", "plan", "proposal") for n in mine)}


def _by(task: dict, read: tuple[dict, dict]) -> dict:
    """The role a task runs as, `{slug, name}`; a role since dropped reads as Grunt."""
    slug = roles.task_slug(task, read)
    r = read[0].get(slug) or read[0].get(roles.GRUNT) or {}
    return {"slug": r.get("slug") or slug, "name": r.get("name") or slug}


def _asked(st: dict, asks: list[str], by_slug: dict, lead: dict | None, target: str) -> list[dict]:
    """An idea's questions with who asks each: the state's `asks_by` (spec 46 §1), else the goal's leader."""
    who = st.get("asks_by") if isinstance(st.get("asks_by"), list) else []
    out = []
    for n, q in enumerate(idea_questions.parse(a) for a in asks[:5]):
        r = by_slug.get(who[n]) if n < len(who) and isinstance(who[n], str) else None
        r = r or lead
        out.append({"ask": q["ask"], "choices": q.get("choices") or [], "pick": q.get("pick"), "why": q.get("why") or "",
                    "by": {"slug": r["slug"], "name": r["name"], "head": roles.head(r, target)} if r else None})
    return out


ERROR_CHARS = 300                       # a failed task's error as the Map carries it (spec 49 §2.4)
BRIEF_CHARS = 140                       # a party's brief (spec 50 §2.4)


def brief_of(g: dict) -> str:
    """What a party is for, in one short line (spec 50 §2.4): its Description's first paragraph, else its Summary's first line,
    at most 140 characters."""
    paragraph = next((p for p in re.split(r"\n\s*\n", str(g.get("about") or "").strip()) if p.strip()), "")
    text = " ".join(paragraph.split()) or " ".join(next((ln for ln in str(g.get("summary") or "").splitlines() if ln.strip()), "").split())
    return text if len(text) <= BRIEF_CHARS else text[:BRIEF_CHARS - 1].rstrip() + "…"


def _run_of(t: dict) -> dict:
    """What a task's run left, for its card (spec 49 §2.4): the failure as the runner wrote it (cut), a hold's or a stop's
    note, the round, what it cost (usd; None before it ran) and when it started (ISO, "" before)."""
    cost = t.get("cost")
    return {"error": str(t.get("error") or "")[:ERROR_CHARS], "note": str(t.get("note") or ""), "round": int(t.get("round") or 1),
            "cost": cost if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None,
            "started": str(t.get("started") or "")}


# -- the Map -------------------------------------------------------------------------------------------------

def _tiers(order: list[str], depends: dict[str, list[str]]) -> dict[str, int]:
    """1 for an idea that depends on none of its goal's ideas, else one more than the deepest it depends on (a cycle,
    which spec 35 §3 never closes, is read as no dependency rather than looped on)."""
    tier: dict[str, int] = {}
    walking: set[str] = set()

    def of(slug: str) -> int:
        if slug in tier:
            return tier[slug]
        walking.add(slug)
        deepest = max((of(d) for d in depends[slug] if d in depends and d not in walking), default=0)
        walking.discard(slug)
        tier[slug] = deepest + 1
        return tier[slug]

    for slug in order:
        of(slug)
    return tier


def _waits(node: dict, tasks: list[dict], titles: dict[str, str], page_waits: list[str], week: dict | None = None) -> dict | None:
    """Why a node that is not done does not move: the first that holds (spec 39 §1). Data, not words. `week`: {"until": the week's reset (local
    time, to the minute), "held": the Board's own Low work waits at night for the week} (spec 44 §4), or None with no week read."""
    if node["needs_you"] or any(t.get("state") == "picking" for t in tasks):          # a task that made variants waits for the person's pick (spec 51)
        return {"kind": "you", "ref": "", "title": "", "until": ""}
    if page_waits:
        return {"kind": "idea", "ref": page_waits[0], "title": titles.get(page_waits[0], page_waits[0]), "until": ""}
    held = [t for t in tasks if t.get("state") == "held"]
    for t in held:
        m = _HELD_FILES.match(str(t.get("note") or ""))
        if m:
            return {"kind": "files", "ref": m.group(1), "title": titles.get(m.group(1), m.group(1)), "until": ""}
    if node["held_until"]:
        return {"kind": "limits", "ref": "", "title": "", "until": node["held_until"]}
    for t in held:
        note = str(t.get("note") or "")
        got = _AFTER.search(note)
        if got and not note.startswith(("reserve", "week")):
            return {"kind": "limits", "ref": "", "title": "", "until": got.group(1)}
    for t in held:
        note = str(t.get("note") or "")
        got = _AFTER.search(note)
        if got and note.startswith("reserve"):
            return {"kind": "reserve", "ref": "", "title": "", "until": got.group(1)}
    for t in held:
        note = str(t.get("note") or "")
        got = _AFTER.search(note)
        if got and note.startswith("week"):
            return {"kind": "week", "ref": "", "title": "", "until": (week or {}).get("until") or ""}      # no week read: no time the faces can say
    if (node["queue"] == "night" or node["start_at"] == "night") and node.get("night_by") == "board" and (week or {}).get("held"):
        return {"kind": "week", "ref": "", "title": "", "until": week["until"]}      # the Board's own Low work, held at night by the pace
    if node["queue"] == "night" or node["start_at"] == "night":
        return {"kind": "night", "ref": "", "title": "", "until": ""}
    if node["queue"] == "hold":
        return {"kind": "stopped", "ref": "", "title": "", "until": ""}
    return None


def _week_of(settings: dict | None, limits: list | None, now: float) -> dict | None:
    """The Claude week as the Map words a wait on it: {"until": its reset, "held": the Board's own Low work waits at night for it}; None with no
    week read (spec 44 §4)."""
    got = idea_target.week(limits or [], now)
    if got is None:
        return None
    s = settings or {}
    night = idea_target.in_night(str(s.get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now))
    return {"until": dt.datetime.fromtimestamp(got["reset"]).strftime("%Y-%m-%dT%H:%M"),
            "held": night and bool(s.get("autostart", True)) and idea_target.pace(limits or [], now) == "behind"}


def build(root: Path, state_dir: Path, settings: dict | None = None, limits: list | None = None, now: float = 0.0, *,
          goal: str = "", rev: Any = "", state_of: Callable[[str], dict] | None = None,
          goal_state_of: Callable[[str], dict] | None = None) -> dict:
    """The Map of a project (spec 39 §1): `goal` one goal's slug (else every goal but General). Reads each idea's page,
    state and `plan.json` once; no git, no process, no write. `settings`, `limits` and `now` are the Board's (the faces
    word `until` and the gate); a held task already says when it goes on."""
    state_of = state_of or (lambda slug: ideas.state(state_dir, slug))
    goal_state_of = goal_state_of or (lambda slug: ideas.goal_state(state_dir, slug))
    tracks = [t for t in ideas.tracks(root, make=False) if t["slug"] != ideas.GENERAL]
    shown = [t for t in tracks if not goal or t["slug"] == goal]
    found = ideas.ideas(root)
    states = {i["slug"]: state_of(i["slug"]) for i in found}
    titles = {i["slug"]: i["title"] for i in found}
    place = {i["slug"]: n for n, i in enumerate(found)}
    pages = {i["slug"]: ideas.idea_page(root, i["slug"]) for i in found}
    depends = {s: list_of(p.get("depends_on")) if p else [] for s, p in pages.items()}

    # a done idea stays while an idea that stays depends on it, so every edge has both ends
    kept = {s for s, st in states.items() if st["state"] != "done"}
    todo = list(kept)
    while todo:
        for d in depends.get(todo.pop(), []):
            if d in states and d not in kept:
                kept.add(d)
                todo.append(d)

    goals, nodes, edges = [], [], []
    week = _week_of(settings, limits, now)
    target, read = idea_target.target_of(settings), roles.known(state_dir)         # a task's head: who does it, at what tier
    today = dt.date.fromtimestamp(now).isoformat() if now else dt.date.today().isoformat()
    for g in shown:
        mine = [i for i in found if i["track"] == g["slug"]]
        order = [i["slug"] for i in mine]
        inside = set(order)
        tier = _tiers(order, {s: [d for d in depends[s] if d in inside] for s in order})
        spent = idea_spend.of_goal(state_dir, g["slug"], order)["usd"]
        gst = goal_state_of(g["slug"])
        by_slug = read[0]
        checks = idea_checks.of_team(state_dir, g.get("team") or [], g.get("every") or [])
        checkers = {c["by"] for c in checks}
        team = [{"slug": s, "name": by_slug[s]["name"], "head": roles.head(by_slug[s], target), "checks": s in checkers,
                 "every": s in (g.get("every") or [])} for s in g.get("team") or [] if s in by_slug]
        lead = by_slug.get(g.get("leader") or roles.TASKMASTER) or by_slug.get(roles.TASKMASTER)
        verdict = goal_verdict.read(state_dir, g["slug"])
        goals.append({"slug": g["slug"], "title": g["title"], "short": g["short"], "priority": g["priority"], "state": gst["state"],
                      "craft": g.get("craft") or roles.DEFAULT_CRAFT, "race": roles.RACES.get(g.get("craft"), "peon"), "team": team,
                      "leader": {"slug": lead["slug"], "name": lead["name"], "head": roles.head(lead, target)} if lead else None,
                      "verdict": {"met": verdict.get("met") is True, "by": verdict.get("by") or "", "at": verdict.get("at") or "",
                                  **({"tally": goal_flags.tally(root, state_dir, g["slug"])} if verdict.get("met") is True else {})}
                      if verdict else None,
                      "brief": brief_of(g), "done_when": [m["name"] for m in g["metrics"]], "ideas": len(mine),
                      "done": sum(1 for s in order if states[s]["state"] == "done"),
                      "usd": None if spent is None else round(spent, 2)})
        mine_nodes, today_tasks = [], []
        for i in sorted(mine, key=lambda i: (tier[i["slug"]], place[i["slug"]])):
            slug, st, page = i["slug"], states[i["slug"]], pages[i["slug"]]
            plan = ideas.plan(state_dir, slug)
            tasks = (plan or {}).get("tasks") or []
            asks = ideas.items(page.section("Open questions")) if page else []
            needs = idea_needs(root, state_dir, i, st, plan, asks)
            r = row(root, state_dir, i, st, plan, page, asks, states, needs)
            started = any(t.get("state") not in (None, "waiting", "ready", "held") for t in tasks)
            est = (plan or {}).get("estimate")
            waves = map_stage.waves_of(tasks)
            node = {"slug": slug, "goal": g["slug"], "title": i["title"], "short": i["short"], "state": r["state"], "queue": r["queue"],
                    "element": st.get("element") or "", "flag": idea_flag.flag_of(state_dir, slug),
                    "held_until": r["held_until"], "start_at": r["start_at"], "night_by": r["night_by"], "by_pace": bool((plan or {}).get("by_pace")),
                    "priority": r["priority"], "size": r["size"],
                    "risk": r["risk"], "tier": tier[slug], "depends_on": r["depends_on"], "waits_on": r["waits_on"],
                    "waits": None, "needs_you": next((k for k in NEEDS if any(n["kind"] == k for n in needs)), "")
                    if r["state"] != "done" else "",
                    "progress": r["progress"],
                    "stage": map_stage.stage_of(r["state"], tasks, bool((plan or {}).get("passed_at"))), "round": map_stage.round_of(tasks),
                    "usd": idea_spend.of_idea(state_dir, slug)["usd"] if tasks else None,
                    "plan_estimate": {"usd_low": est.get("usd_low"), "usd_high": est.get("usd_high")} if isinstance(est, dict) and plan else None,
                    "asked": _asked(st, asks, by_slug, lead, target) if r["state"] == "asks" else [],
                    "tasks": [{"id": t.get("id"), "title": t.get("title") or "", "short": task_short(t), "state": t.get("state") or "waiting",
                               "after": list(t.get("after") or []), "tier": t.get("tier") or "",
                               "head": roles.task_head(state_dir, t, target, read),
                               "by": _by(t, read), "band": "check" if map_stage.is_check(t) else "build", "wave": waves[str(t.get("id"))],
                               **_run_of(t), "pick": idea_pick.map_of(t),
                               "tag": roles.KIND_LABELS.get(str(t.get("kind") or ""), roles.KIND_LABELS[roles.DEFAULT_KIND])} for t in tasks],
                    "checks": idea_checks.status(idea_checks.kept(list_of_dicts(page.get("checks")) if page else [], checks),
                                                 checks, tasks) if checks else [],
                    "estimate": {"usd_low": est.get("usd_low"), "usd_high": est.get("usd_high")}
                    if isinstance(est, dict) and plan and not started else None,
                    "by_itself": bool(plan) and plan.get("passed_by") == "auto",
                    "folded": slug not in kept, "updated": r["updated"]}
            if r["state"] != "done":
                node["waits"] = _waits(node, tasks, titles, r["waits_on"], week)
            nodes.append(node)
            mine_nodes.append(node)
            today_tasks += [t for t in tasks if t.get("state") == "merged" and str(t.get("finished") or "").startswith(today)]
            edges += [{"from": d, "to": slug} for d in r["depends_on"] if d in tier and slug in kept and d in kept]
        cost = sum(float(t["cost"]) for t in today_tasks if isinstance(t.get("cost"), (int, float)))
        goals[-1].update(party=map_party.party_of(goals[-1], mine_nodes), today={"merged": len(today_tasks), "usd": round(cost, 2)},
                         flags=sum(1 for n in mine_nodes if n["flag"]),
                         waits_main=sum(1 for n in mine_nodes if n["state"] == "done" and not n["flag"]))
    return {"goals": goals, "nodes": nodes, "edges": edges, "rev": rev}
