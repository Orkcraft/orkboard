"""What a party costs, before it starts (docs/specs/43-party-measured.md §3): about what an idea costs with a leader, its builders
and its checkers, from this project's own ideas once there are enough of them, a first guess before. A pure read of the plans and the
ledgers: no face, no model, it writes nothing.

    party_price.price(root, state_dir, settings, "architect", ["grunt", "tester", "reviewer"], every=["reviewer"])   # §3.1's object

`root` is the Board's tree (the ideas' pages), `settings` the Board's (its Target). The basis is the project's newest `BASIS` ideas
with a plan; the price is *learned* from `idea_spend.TOO_FEW` of them with priced lines. A task costs what `ideas.roles` says an
agent's task costs (its week's spend by its tasks that ended from `TOO_FEW` of them, else a task at its head's tier).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from orkboard.realm import goal_team, idea_checks, idea_spend, idea_target, ideas, library, plans, roles

BASIS = 20                          # the project's newest ideas with a plan
GUESS_TASKS = 3                     # tasks (not checks) an idea has, before the project has any
GUESS_SHARE = 0.5                   # the share of ideas a check applies to, before the project says
SPREAD = (0.5, 1.5)                 # low and high, as `idea_keeper.estimate` spreads a plan's


def _who(state_dir: Path, slug: str) -> dict:
    """An agent as the project has it; a library agent not installed yet as the library has it."""
    r = roles.role(state_dir, slug)
    if r is not None:
        return r
    a = library.get(slug)
    return {"slug": slug, "name": a.name if a else slug, "model": "", "craft": a.craft if a else roles.DEFAULT_CRAFT,
            "tier": a.tier if a else "warrior"}


def task_usd(state_dir: Path, slug: str, target: str, week: dict, costs: dict) -> float:
    """About what a task of this agent costs (as `gui/ideas_roles.py` `_usd_task` says it): its week's spend by its tasks that ended,
    from `TOO_FEW` of them on; else a task at its head's tier."""
    r = _who(state_dir, slug)
    mine = week.get(slug) or {}
    if mine.get("spent") and int(mine.get("finished") or 0) >= idea_spend.TOO_FEW:         # (tasks that ended with no priced line say nothing)
        return float(mine["spent"]) / int(mine["finished"])
    tier = roles.head_tier(str(r.get("model") or ""), target, str(r.get("tier") or "warrior"))
    return float(costs.get(tier, plans.DEFAULT_COST["warrior"]))


def _made(state_dir: Path, slug: str, plan: dict) -> str:
    if plan.get("made_at"):
        return str(plan["made_at"])
    try:
        return dt.datetime.fromtimestamp((Path(state_dir) / "ideas" / slug / "plan.json").stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return ""


def basis(root: Path, state_dir: Path) -> list[tuple[str, dict]]:
    """The project's newest ideas with a plan, newest first: [(slug, plan)]."""
    got = [(s, p) for i in ideas.ideas(root) if (p := ideas.plan(state_dir, i["slug"])) and (p.get("tasks") or []) for s in [i["slug"]]]
    return sorted(got, key=lambda sp: _made(state_dir, *sp), reverse=True)[:BASIS]


def _round(usd: float) -> float:
    return round(usd, 2)


def price(root: Path, state_dir: Path, settings: dict, leader: str, team: list[str], every: list[str]) -> dict[str, Any]:
    """§3.1's object: {low, high, learned, ideas, checks: [{by, name, usd, share, every}]}."""
    target = idea_target.target_of(settings)
    rows = basis(root, state_dir)
    spend = {s: idea_spend.of_idea(state_dir, s) for s, _p in rows}
    priced = [s for s, _p in rows if spend[s]["usd"] is not None and sum(v["calls"] for v in spend[s]["stages"].values())]
    learned = len(priced) >= idea_spend.TOO_FEW

    # the leader's steps
    lead = _who(state_dir, leader or roles.TASKMASTER)
    steps = [sum(v for k in ("spec", "plan") if (v := spend[s]["stages"][k]["usd"]) is not None) for s in priced
             if any(spend[s]["stages"][k]["usd"] is not None for k in ("spec", "plan"))]
    if learned and steps:
        steps_usd = sum(steps) / len(steps)
    else:
        tier = roles.head_tier(str(lead.get("model") or ""), target, str(lead.get("tier") or "elder"))
        steps_usd = plans.DEFAULT_COST[tier] * 2

    # the work: the tasks that are not checks, at what a task of the party's builders costs
    week, costs = idea_spend.by_role(state_dir), idea_spend.tier_costs(state_dir)
    builders = [s for s in team if goal_team.band_of(s) == "build"] or [roles.GRUNT]
    per_task = sum(task_usd(state_dir, s, target, week, costs) for s in builders) / len(builders)
    counts = [sum(1 for t in p["tasks"] if str(t.get("kind") or "") not in idea_checks.TAGS) for _s, p in rows]
    tasks = sum(counts) / len(counts) if learned and counts else GUESS_TASKS
    work = tasks * per_task

    # each check: what a task of its checker costs, and the share of ideas it applies to
    drafted: dict[str, list[bool]] = {}
    for s, _p in rows:
        page = ideas.idea_page(root, s)
        for x in (ideas._json_list(page.get("checks")) if page is not None else []):
            if isinstance(x, dict) and isinstance(x.get("by"), str):
                drafted.setdefault(x["by"], []).append(bool(x.get("applies")) and not x.get("skipped"))
    checks, added = [], 0.0
    for by in [s for s in team if goal_team.band_of(s) == "check"]:
        usd, always = task_usd(state_dir, by, target, week, costs), by in (every or [])
        said = drafted.get(by, [])
        share = 1.0 if always else (sum(said) / len(said) if len(said) >= idea_spend.TOO_FEW else GUESS_SHARE)
        added += usd * share
        checks.append({"by": by, "name": _who(state_dir, by)["name"], "usd": _round(usd), "share": round(share, 2), "every": always})

    base = steps_usd + work + added
    return {"low": _round(base * SPREAD[0]), "high": _round(base * SPREAD[1]), "learned": learned, "ideas": len(rows), "checks": checks}
