"""About what an idea costs with a party, before it starts (docs/specs/43-party-measured.md §3): the leader's steps, the work
of the builders and each checker's check, from the project's last ideas when it has them, else from the defaults. No face,
no model, it writes nothing.

    party_price.price(root, state_dir, settings, "product-manager", ["tester", "reviewer"], ["reviewer"])
    # {"low", "high", "learned", "ideas", "checks": [{"by", "name", "usd", "share", "every"}]}

`root` is the Board's tree (where the pages are), `state_dir` the project's state, `settings` the Board's (its Target).
"""
from __future__ import annotations

from pathlib import Path

from orkboard.realm import goal_team, idea_checks, idea_spend, idea_target, ideas, library, plans, roles
from orkboard.realm.board_map import list_of_dicts

BASIS = 20                 # the newest ideas with a plan that a price is learned from
GUESS_TASKS = 3            # tasks of the work an idea has, before the project's own are known
GUESS_SHARE = 0.5          # the share of ideas a check applies to, before the project's own is known
STEPS_PER_TIER = 2         # a first guess of the leader's steps: this many runs at its tier
SPREAD = (0.5, 1.5)        # as `idea_keeper.estimate` spreads a plan's


def _role(state_dir: Path, slug: str, known: dict[str, dict]) -> dict:
    """A role as the project has it; an agent of the library not installed yet, as it will be installed (its tier its model)."""
    r = known.get(slug)
    if r is not None:
        return r
    a = library.get(slug)
    if a is not None:
        return {"slug": a.id, "name": a.name, "craft": a.craft, "model": a.tier}
    return known[roles.GRUNT]


def _task_usd(r: dict, week: dict, costs: dict, target: str) -> float:
    """About what a task of a role costs (`gui/ideas_roles.py` `_usd_task`): its week's spend by its tasks that ended, from
    `idea_spend.TOO_FEW` of them on; else a task's at its head's tier."""
    mine = week.get(r["slug"]) or {}
    if mine.get("spent") is not None and int(mine.get("finished") or 0) >= idea_spend.TOO_FEW:
        return float(mine["spent"]) / int(mine["finished"])
    tier = roles.head(r, target)["tier"]
    return float(costs.get(tier, plans.DEFAULT_COST.get(tier, plans.DEFAULT_COST["warrior"])))


def _basis(root: Path, state_dir: Path) -> list[tuple[str, dict]]:
    """(slug, plan) of the project's newest `BASIS` ideas with a plan, by the time of the plan's file."""
    found = []
    for i in ideas.ideas(root):
        plan = ideas.plan(state_dir, i["slug"])
        if plan:
            try:
                at = (ideas.state_folder(state_dir, i["slug"]) / "plan.json").stat().st_mtime
            except OSError:
                at = 0.0
            found.append((at, i["slug"], plan))
    found.sort(key=lambda x: x[0], reverse=True)
    return [(slug, plan) for _at, slug, plan in found[:BASIS]]


def _usd(value: float) -> float:
    return round(float(value), 2)


def price(root: Path, state_dir: Path, settings: dict | None, leader: str, team: list[str], every: list[str]) -> dict:
    """§3.1's object for a party: `leader`, `team` (its builders and checkers) and `every` (the checkers whose check applies
    to every idea) as the picker has them."""
    root, state_dir = Path(root), Path(state_dir)
    target = idea_target.target_of(settings)
    known = {r["slug"]: r for r in roles.roles(state_dir)}
    week, costs = idea_spend.by_role(state_dir), idea_spend.tier_costs(state_dir)
    basis = _basis(root, state_dir)
    spend = {slug: idea_spend.of_idea(state_dir, slug) for slug, _p in basis}
    priced = [slug for slug, s in spend.items() if s["usd"] is not None]
    learned = len(priced) >= idea_spend.TOO_FEW

    lead = _role(state_dir, leader or roles.TASKMASTER, known)
    if learned:
        steps_each = [sum(spend[s]["stages"][st]["usd"] or 0.0 for st in ("spec", "plan")) for s in priced]
        steps = sum(steps_each) / len(steps_each)
    else:
        tier = roles.head(lead, target)["tier"]
        steps = plans.DEFAULT_COST[tier] * STEPS_PER_TIER

    builders = [s for s in team if goal_team.band_of(s) == "build"]
    each = [_task_usd(_role(state_dir, s, known), week, costs, target) for s in builders] or [_task_usd(known[roles.GRUNT], week, costs, target)]
    tasks = (sum(sum(1 for t in p.get("tasks") or [] if isinstance(t, dict) and str(t.get("kind") or "") not in idea_checks.TAGS)
                 for _s, p in basis) / len(basis)) if learned else GUESS_TASKS
    work = tasks * (sum(each) / len(each))

    drafted: dict[str, list[bool]] = {}                    # per checker: for each idea drafted with it, whether it applied
    for slug, _p in basis:
        page = ideas.idea_page(root, slug)
        for k in list_of_dicts(page.get("checks")) if page else []:
            drafted.setdefault(str(k.get("by") or ""), []).append(k.get("applies") is not False and k.get("skipped") is not True)
    checks, added = [], 0.0
    for slug in team:
        a = library.get(slug)
        if a is None or a.check is None or goal_team.band_of(slug) != "check":
            continue
        each_check = slug in every
        seen = drafted.get(slug, [])
        share = 1.0 if each_check else (sum(seen) / len(seen) if len(seen) >= idea_spend.TOO_FEW else GUESS_SHARE)
        usd = _task_usd(_role(state_dir, slug, known), week, costs, target)
        checks.append({"by": slug, "name": a.name, "usd": _usd(usd), "share": round(share, 2), "every": each_check})
        added += usd * share
    base = steps + work + added
    return {"low": _usd(base * SPREAD[0]), "high": _usd(base * SPREAD[1]), "learned": learned, "ideas": len(basis), "checks": checks}
