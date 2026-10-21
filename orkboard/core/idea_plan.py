"""The small helpers of a plan (core/idea_keeper.py re-exports them): a task as plan.json keeps it, the price range of its tasks, which
of them are ready to start, and an error as the idea's state keeps it. Split from the keeper to keep both under ~600 lines.
"""
from __future__ import annotations

from orkboard.realm import plans, tool_errors
from orkboard.realm.idea_words import short_of


def _task(tid: str, title: str, brief: str, kind: str, tier: str, after: list[str]) -> dict:
    """A task of a plan as plan.json keeps it, waiting; its short name by code (the plan's answer may give its own)."""
    return {"id": tid, "title": title, "short": short_of(title),
            "brief": brief, "kind": kind, "tier": tier, "after": after, "state": "waiting",
            "branch": "", "commit": "", "session": "", "cost": None, "tokens": None, "started": "", "finished": "",
            "error": "", "note": ""}


def estimate(tasks: list[dict], tiers: list[str] | None = None, costs: dict[str, float] | None = None) -> dict:
    """The price range of the tasks, counted on the tiers they will run on (`tiers`, else their planned ones), at
    `costs` a task per tier (the board's own, `idea_spend.tier_costs`), else `plans.DEFAULT_COST`; ±50 %."""
    tiers = tiers if tiers is not None else [t.get("tier", "warrior") for t in tasks]
    costs = costs or plans.DEFAULT_COST
    base = sum(costs.get(tier, plans.DEFAULT_COST.get(tier, plans.DEFAULT_COST["warrior"])) for tier in tiers)
    return {"tasks": len(tasks), "usd_low": round(base * 0.5, 2), "usd_high": round(base * 1.5, 2)}


def readiness(data: dict) -> None:
    """A task not started yet is `ready` when what it waits for is done (its `after`, its to-dos), else `waiting`."""
    merged = {t["id"] for t in data.get("tasks") or [] if t.get("state") == "merged"}
    blocked = {f for td in data.get("todos") or [] if not td.get("done") for f in td.get("for") or []}
    for t in data.get("tasks") or []:
        if t.get("state") in ("waiting", "ready"):
            t["state"] = "ready" if set(t.get("after") or []) <= merged and t["id"] not in blocked else "waiting"


def _why(e: Exception) -> str:
    """An error as the idea's state keeps it (300 characters): an AI tool's failure in plain words, its own words and
    what to do (tool_errors.PLAIN_CHARS)."""
    if isinstance(e, InterruptedError):
        return "stopped"
    if isinstance(e, tool_errors.ToolError):
        return tool_errors.plainly(e)
    return (str(e) or type(e).__name__).strip()[:300]
