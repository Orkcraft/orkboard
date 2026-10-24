"""What a goal's party did (docs/specs/43-party-measured.md §2): each member's tasks, merged the first time and $, each checker's
ideas checked, clean, caught, left and $, from the goal's ideas' plans. A pure read: no face, no model, it writes nothing.

    party_work.work(root, state_dir, "billing")        # §2.1's object (an Ideation party's with `pitches`: realm/pitches.py `tally`)

`root` is the Board's tree (where the goal's and the ideas' pages are), `state_dir` the project's state. A goal's party is its
leader, its builders and its checkers (realm/goal_team.py). A *check task* is one whose `kind` is a checker's tag
(realm/idea_checks.py `TAGS`); the others are the work. Times and costs are the ledgers' own: a `usd` is `None` when nothing
of it was priced, never 0.
"""
from __future__ import annotations

import datetime as dt
import time
from pathlib import Path
from typing import Any

from orkboard.realm import board_recap, goal_team, idea_checks, idea_spend, ideas, library, pitches, roles

QUIET_RUN = 8                            # check tasks of a goal that all ended clean in round 1: the night proposes to take the checker out
ENDED = ("merged", "failed")             # a task that has an end: the work counts from here
CHECKED = ("merged", "review")          # a check task that has said what it found: merged, or waiting for the person


def who(state_dir: Path, slug: str, target: str = "balance") -> dict:
    """{slug, name, head} of an agent of the project (a library agent not installed yet by its library name)."""
    r = roles.role(state_dir, slug)
    if r is None:
        a = library.get(slug)
        r = {"slug": slug, "name": a.name if a else slug, "model": "", "craft": a.craft if a else roles.DEFAULT_CRAFT}
    return {"slug": slug, "name": r["name"], "head": roles.head(r, target)}


def _sum(values: list[float | None]) -> float | None:
    """The priced values' sum, rounded to cents; None when none was priced."""
    priced = [v for v in values if v is not None]
    return round(sum(priced), 2) if priced else None


def _kept(root: Path, slug: str) -> list[dict]:
    page = ideas.idea_page(root, slug)
    return [x for x in (ideas._json_list(page.get("checks")) if page is not None else []) if isinstance(x, dict)]


def _builders(root: Path, goal: str) -> list[str]:
    return [s for s in goal_team.team_of(root, goal) if goal_team.band_of(s) == "build"]


def _checkers(root: Path, goal: str) -> list[str]:
    return [s for s in goal_team.team_of(root, goal) if goal_team.band_of(s) == "check"]


def check_by(task: dict) -> str:
    """The checker of a check task: its role when it is a library checker, else the library's checker of its tag."""
    role = str(task.get("role") or "")
    return role if idea_checks.is_checker(role) else idea_checks.checker_of_tag(str(task.get("kind") or ""))


def work(root: Path, state_dir: Path, goal: str, target: str = "balance") -> dict[str, Any]:
    """§2.1's object for a goal. `target`: the Board's Target, for the heads' gear."""
    slugs = [i["slug"] for i in ideas.ideas(root, goal)]
    plans = {s: p for s in slugs if (p := ideas.plan(state_dir, s)) and (p.get("tasks") or [])}
    split = {s: idea_spend.of_idea(state_dir, s)["tasks"] for s in plans}
    team = goal_team.team_of(root, goal)

    spent = idea_spend.of_goal(state_dir, goal, slugs)["stages"]
    steps = [spent[k] for k in ("goal", "spec", "plan")]
    leader = {**who(state_dir, goal_team.leader_of(root, goal), target),
              "usd": _sum([s["usd"] for s in steps]) if sum(s["calls"] for s in steps) else None}

    by_role: dict[str, list[tuple[str, dict]]] = {}
    by_check: dict[str, list[tuple[str, dict]]] = {}
    for slug, plan in plans.items():
        for t in plan["tasks"]:
            if str(t.get("kind") or "") in idea_checks.TAGS:
                if (c := check_by(t)):
                    by_check.setdefault(c, []).append((slug, t))
            elif t.get("state") in ENDED:
                r = str(t.get("role") or "") or roles.role_for(state_dir, str(t.get("kind") or ""), team)["slug"]
                by_role.setdefault(r, []).append((slug, t))

    def usd_of(rows: list[tuple[str, dict]]) -> float | None:
        return _sum([(split[s].get(str(t.get("id"))) or {}).get("usd") for s, t in rows])

    order = [s for s in _builders(root, goal) if s in by_role] + [s for s in by_role if s not in _builders(root, goal)]
    members = []
    for slug in order:
        rows = by_role[slug]
        merged = [t for _s, t in rows if t.get("state") == "merged"]
        members.append({**who(state_dir, slug, target), "tasks": len(rows), "merged": len(merged),
                        "first_time": sum(1 for t in merged if int(t.get("round") or 1) <= 1), "usd": usd_of(rows)})

    team_checks = {c["by"]: c for c in idea_checks.of_team(state_dir, team, goal_team.every_of(root, goal))}
    kept = {s: _kept(root, s) for s in plans}
    names = _checkers(root, goal) + [s for s in by_check if s not in _checkers(root, goal)]
    checks = []
    for by in names:
        applied = skipped = 0
        for slug in plans:
            said = {x.get("by"): x for x in kept[slug]}
            if by in team_checks:                            # the team's checker: a draft that left it out means it applies
                row = idea_checks.kept(kept[slug], [team_checks[by]])[0]
            else:
                row = said.get(by) or {"applies": False}
            if row.get("applies") and row.get("skipped"):
                skipped += 1
            elif row.get("applies"):
                applied += 1
        rows = by_check.get(by, [])
        clean = caught = before = left = 0
        for _slug, t in rows:
            if t.get("state") not in CHECKED:
                continue
            found = t.get("findings") if isinstance(t.get("findings"), list) else None
            if found:
                caught += 1
                left += idea_checks.counts(found)["left"]
            elif int(t.get("round") or 1) > 1:
                caught += 1                                   # sent back: the round before had something to fix
            elif found is None:
                before += 1
            else:
                clean += 1
        checks.append({"by": by, **{k: v for k, v in who(state_dir, by, target).items() if k != "slug"},
                       "applied": applied, "skipped": skipped, "clean": clean, "caught": caught, "left": left, "before": before,
                       "usd": usd_of(rows)})
    out = {"ideas": len(plans), "leader": leader, "members": members, "checks": checks}
    if goal_team.leader_of(root, goal) == library.INVESTOR:       # Ideation: its pitches judged, sent, passed (spec 65 §6)
        out["pitches"] = pitches.tally(root, state_dir, goal)
    return out


# -- what a check is worth (spec 43 §4) ------------------------------------------------------------------------

def _verdict(t: dict) -> str:
    """What a check task that has said what it found found: "clean" (round 1, nothing found), "caught" (a finding, or sent back),
    "" when it has not said (running, failed, or kept before findings were)."""
    found = t.get("findings") if isinstance(t.get("findings"), list) else None
    if t.get("state") not in CHECKED or found is None:
        return ""
    return "caught" if found or int(t.get("round") or 1) > 1 else "clean"


_CACHE: dict[tuple[str, str, int], tuple[float, dict[str, dict]]] = {}
CACHE_S = 30.0


def forget() -> None:
    """The cache of `check_record` cleared (a test, or a change the person should see at once)."""
    _CACHE.clear()


def _scan(root: Path, state_dir: Path, days: int, now: dt.datetime) -> dict[str, dict]:
    """Every checker's record over the last `days`, from one read of the plans."""
    since = now - dt.timedelta(days=days)
    sums: dict[str, dict] = {}
    for i in ideas.ideas(root):
        plan = ideas.plan(state_dir, i["slug"])
        per = None
        for t in (plan or {}).get("tasks") or []:
            at = board_recap.when(t.get("finished"))
            if str(t.get("kind") or "") not in idea_checks.TAGS or not (v := _verdict(t)) or at is None or not since <= at <= now:
                continue
            per = per if per is not None else idea_spend.of_idea(state_dir, i["slug"])["tasks"]
            row = sums.setdefault(check_by(t), {"checks": 0, "clean": 0, "caught": 0, "left": 0, "spent": []})
            row["checks"] += 1
            row["clean"] += v == "clean"
            row["caught"] += v == "caught"
            row["left"] += idea_checks.counts(t["findings"])["left"]
            row["spent"].append((per.get(str(t.get("id"))) or {}).get("usd"))
    return sums


def check_record(root: Path, state_dir: Path, by: str, days: int, now: dt.datetime | None = None) -> dict[str, Any]:
    """{checks, clean, caught, left, usd_per_check}: the checker's check tasks that ended with findings in the last `days`, across the
    project's goals. `usd_per_check` from `idea_spend.TOO_FEW` checks, else None (and None while they are unpriced). Cached for 30 s
    (as `idea_spend.by_role` is) unless `now` is given."""
    key, mono = (str(root), str(state_dir), int(days)), time.monotonic()
    hit = _CACHE.get(key) if now is None else None
    if hit is None or mono - hit[0] >= CACHE_S:
        hit = (mono, _scan(root, state_dir, days, (now or dt.datetime.now()).astimezone()))
        if now is None:
            _CACHE[key] = hit
    row = hit[1].get(by) or {"checks": 0, "clean": 0, "caught": 0, "left": 0, "spent": []}
    usd = _sum(row["spent"])
    return {"checks": row["checks"], "clean": row["clean"], "caught": row["caught"], "left": row["left"],
            "usd_per_check": round(usd / row["checks"], 2) if row["checks"] >= idea_spend.TOO_FEW and usd is not None else None}


def quiet_run(root: Path, state_dir: Path, goal: str, by: str, oldest: bool = False) -> str | None:
    """When the checker's newest `QUIET_RUN` check tasks in this goal's ideas all ended clean in round 1: the time the newest of them
    finished (the oldest with `oldest`: a decline holds until all eight are after it); else None. A check that failed, was sent back or
    found something ends the run."""
    done: list[tuple[str, str]] = []
    for i in ideas.ideas(root, goal):
        for t in (ideas.plan(state_dir, i["slug"]) or {}).get("tasks") or []:
            if str(t.get("kind") or "") in idea_checks.TAGS and check_by(t) == by and t.get("finished") and t.get("state") in ("merged", "review", "failed"):
                done.append((str(t["finished"]), _verdict(t)))
    newest = sorted(done, reverse=True)[:QUIET_RUN]
    return newest[-1 if oldest else 0][0] if len(newest) == QUIET_RUN and all(v == "clean" for _at, v in newest) else None
