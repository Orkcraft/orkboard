"""What a goal's party did (docs/specs/43-party-measured.md §2): its leader's steps, each member's tasks, each checker's
checks, read from the goal's ideas' plans, their kept checks and the ledgers. No face, no model, it writes nothing.

    party_work.work(root, state_dir, "billing")   # {"ideas", "leader", "members", "checks"}

`root` is the Board's tree (where the pages are); `target` (the project's Target) only sets the heads' tiers.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from orkboard.realm import goal_team, idea_checks, idea_spend, idea_target, ideas, library, roles
from orkboard.realm.board_map import list_of_dicts

LEAD_STAGES = ("goal", "spec", "plan")        # the leader's steps in the ledger (idea_spend.STAGES)
ENDED = ("merged", "failed")
QUIET_RUN = 8                                 # a checker whose newest eight checks in a goal all ended clean in round 1 (spec 43 §4.2)


def _sum(values: list[float | None]) -> float | None:
    """The priced values' sum, rounded; None when none is priced (never 0 for nothing priced)."""
    priced = [v for v in values if v is not None]
    return round(sum(priced), 2) if priced else None


def _who(state_dir: Path, slug: str, target: str, known: dict[str, dict]) -> dict:
    """{slug, name, head} of a role; one the project dropped is the library's name (or its slug) with the Grunt's head."""
    r = known.get(slug)
    if r is not None:
        return {"slug": slug, "name": r["name"], "head": roles.head(r, target)}
    a = library.get(slug)
    return {"slug": slug, "name": a.name if a is not None else slug, "head": roles.head(known[roles.GRUNT], target)}


def _checker_of(task: dict) -> str:
    """Whose check task it is (core/idea_task.py `checker_of`, which realm may not import): its role, else the library's."""
    return str(task.get("role") or "") or next((a.id for a in library.LIBRARY if a.check is not None and a.takes[0] == task.get("kind")), "")


def _leader_usd(state_dir: Path, goal: str, slugs: list[str]) -> float | None:
    stages = idea_spend.of_goal(state_dir, goal, slugs)["stages"]
    return _sum([stages[s]["usd"] for s in LEAD_STAGES if stages[s]["calls"]])


def work(root: Path, state_dir: Path, goal: str, target: str = idea_target.DEFAULT) -> dict:
    """§2.1's object for a goal: `ideas` (those with a plan), the leader with its $, the members (the goal's builders first,
    in the party's order, then the others) with their tasks, and the checks (the party's checkers, then any other whose check
    task ran)."""
    root, state_dir = Path(root), Path(state_dir)
    known = {r["slug"]: r for r in roles.roles(state_dir)}
    kinds = roles.kinds(state_dir)
    team, every = goal_team.team_of(root, goal), goal_team.every_of(root, goal)
    planned = []
    for i in ideas.ideas(root, goal):
        plan = ideas.plan(state_dir, i["slug"])
        if plan:
            planned.append((i["slug"], plan))
    slugs = [s for s, _p in planned]
    lead = _who(state_dir, goal_team.leader_of(root, goal), target, known)
    members: dict[str, dict] = {}
    checks: dict[str, dict] = {}

    def check_row(by: str) -> dict:
        if by not in checks:
            checks[by] = {**{k: v for k, v in _who(state_dir, by, target, known).items() if k != "slug"}, "by": by, "applied": 0,
                          "skipped": 0, "clean": 0, "caught": 0, "left": 0, "before": 0, "usd": [], "ran": False}
        return checks[by]

    for slug in team:                                                   # the party's checkers, in its order
        a = library.get(slug)
        if a is not None and a.check is not None:
            check_row(slug)
    for slug, plan in planned:
        spent = idea_spend.of_idea(state_dir, slug)["tasks"]
        for t in plan.get("tasks") or []:
            if not isinstance(t, dict):
                continue
            usd = (spent.get(str(t.get("id") or "")) or {}).get("usd")
            if str(t.get("kind") or "") in idea_checks.TAGS:
                row = check_row(_checker_of(t))
                row["ran"] = True
                row["usd"].append(usd)
                findings, state = t.get("findings"), t.get("state")
                if isinstance(findings, list):
                    left = idea_checks.counts(findings)["left"]
                    row["left"] += left
                    if state in ("merged", "review"):
                        clean = not findings and int(t.get("round") or 1) <= 1
                        row["clean" if clean else "caught"] += 1
                elif state == "merged":
                    row["before"] += 1
                continue
            if t.get("state") not in ENDED:
                continue
            slug_ = str(t.get("role") or "") or kinds.get(str(t.get("kind") or ""), roles.GRUNT)
            m = members.setdefault(slug_, {"tasks": 0, "merged": 0, "first_time": 0, "usd": []})
            m["tasks"] += 1
            m["usd"].append(usd)
            if t["state"] == "merged":
                m["merged"] += 1
                m["first_time"] += int(t.get("round") or 1) <= 1
    for slug in slugs:                                                  # what the drafts said of each check, once every task is read
        page = ideas.idea_page(root, slug)
        for k in list_of_dicts(page.get("checks")) if page else []:
            row = checks.get(str(k.get("by") or ""))
            if row is None:
                continue
            if k.get("skipped") is True:
                row["skipped"] += 1
            elif k.get("applies") is not False:
                row["applied"] += 1
    builders = [s for s in team if s in members and goal_team.band_of(s) == "build"]
    order = builders + [s for s in members if s not in builders]
    return {"ideas": len(planned),
            "leader": {**lead, "usd": _leader_usd(state_dir, goal, slugs)},
            "members": [{**_who(state_dir, s, target, known), "tasks": members[s]["tasks"], "merged": members[s]["merged"],
                         "first_time": members[s]["first_time"], "usd": _sum(members[s]["usd"])} for s in order],
            "checks": [{**{k: v for k, v in c.items() if k not in ("usd", "ran")}, "usd": _sum(c["usd"])}
                       for by, c in checks.items() if by in team or c["ran"]]}


# -- what a check is worth (spec 43 §4) ---------------------------------------------------------------------------

def _read_checks(root: Path, state_dir: Path, goal: str | None = None):
    """(task, checker, usd) of every check task that read its findings and ended (merged, or in review with findings),
    over the ideas of a goal, or of the project's goals."""
    for i in ideas.ideas(root, goal) if goal else ideas.ideas(root):
        plan = ideas.plan(state_dir, i["slug"])
        spent = idea_spend.of_idea(state_dir, i["slug"])["tasks"] if plan else {}
        for t in (plan or {}).get("tasks") or []:
            if isinstance(t, dict) and str(t.get("kind") or "") in idea_checks.TAGS and isinstance(t.get("findings"), list) \
                    and t.get("state") in ("merged", "review"):
                yield t, _checker_of(t), (spent.get(str(t.get("id") or "")) or {}).get("usd")


def check_records(root: Path, state_dir: Path, days: int) -> dict[str, dict]:
    """{checker: check_record} of every checker whose check tasks ended with findings read in the last `days`."""
    since = (dt.datetime.now() - dt.timedelta(days=days)).isoformat(timespec="seconds")
    out: dict[str, dict] = {}
    for t, by, usd in _read_checks(Path(root), Path(state_dir)):
        if str(t.get("finished") or "") < since:
            continue
        row = out.setdefault(by, {"checks": 0, "clean": 0, "caught": 0, "left": 0, "usd": []})
        row["checks"] += 1
        row["clean" if not t["findings"] and int(t.get("round") or 1) <= 1 else "caught"] += 1
        row["left"] += idea_checks.counts(t["findings"])["left"]
        row["usd"].append(usd)
    return {by: {**{k: v for k, v in r.items() if k != "usd"}, "usd_per_check": _per_check(r["usd"], r["checks"])} for by, r in out.items()}


def _per_check(usd: list[float | None], checks: int) -> float | None:
    """What a check costs: the mean of the checks priced, said from `idea_spend.TOO_FEW` checks on."""
    priced = [u for u in usd if u is not None]
    return round(sum(priced) / len(priced), 2) if checks >= idea_spend.TOO_FEW and priced else None


def check_record(root: Path, state_dir: Path, by: str, days: int) -> dict:
    """§4.1: the checker's check tasks that ended with findings in the last `days`, across the project's goals:
    `{"checks", "clean", "caught", "left", "usd_per_check"}` (`usd_per_check` null under `TOO_FEW` checks)."""
    return check_records(root, state_dir, days).get(by) or {"checks": 0, "clean": 0, "caught": 0, "left": 0, "usd_per_check": None}


def quiet_run(root: Path, state_dir: Path, goal: str, by: str, runs: int = QUIET_RUN) -> dict | None:
    """The checker's newest `runs` check tasks in this goal's ideas, when all of them ended clean in round 1:
    `{"at": <when the newest ended>, "usd": <a check's mean cost, or null>}`; None otherwise (fewer, or one caught)."""
    mine = sorted(((str(t.get("finished") or ""), t, usd) for t, who, usd in _read_checks(Path(root), Path(state_dir), goal) if who == by),
                  key=lambda x: x[0])[-runs:]
    if len(mine) < runs or any(t["findings"] or int(t.get("round") or 1) > 1 for _at, t, _u in mine):
        return None
    priced = [u for _at, _t, u in mine if u is not None]
    return {"at": mine[-1][0], "usd": round(sum(priced) / len(priced), 2) if priced else None}
