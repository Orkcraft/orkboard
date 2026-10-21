"""A goal's party on the Map, one state each (docs/specs/48-map-ideas.md §1): the leader, then the team, each *at work*, *next*,
*tonight*, *free*, or *needs* (the work stopped on it). Pure, from the nodes `board_map.build` made; it writes no words.
"""
from __future__ import annotations

from orkboard.realm import goal_team

_LEAD_NEEDS = ("asks", "plan", "proposal")       # the Needs you kinds the leader's work stops on
_PLANNING_WORK = ("reading", "planning")


def leader_state(goal_state: str, nodes: list[dict]) -> tuple[str, str]:
    """(state, why) of the goal's leader."""
    open_ = [n for n in nodes if n["state"] != "done"]
    for kind in _LEAD_NEEDS:
        if any(n["needs_you"] == kind for n in open_):
            return "needs", kind
    if goal_state == "reading" or any(n["state"] in _PLANNING_WORK for n in open_):
        return "work", ""
    planning = [n for n in open_ if n["stage"] == "planning"]
    if any(n["queue"] == "night" or n["start_at"] == "night" for n in planning):
        return "tonight", ""
    if any(n["state"] in ("raw", "ready") for n in planning):
        return "next", ""
    return "free", ""


def member_state(slug: str, nodes: list[dict]) -> tuple[str, str]:
    """(state, why) of a builder or a checker: by the tasks that run as it. A result in review is not a stop on it."""
    mine = [(n, t) for n in nodes if n["state"] != "done" for t in n["tasks"] if t["by"]["slug"] == slug]
    states = [t["state"] for _n, t in mine]
    if "failed" in states:
        return "needs", "failed"
    if any(s in ("running", "testing") for s in states):
        return "work", ""
    if any(t["state"] in ("held", "ready", "waiting") and (n["start_at"] == "night" or (n["waits"] or {}).get("kind") == "night")
           for n, t in mine):
        return "tonight", ""
    if any(s in ("held", "ready", "waiting") for s in states):
        return "next", ""
    return "free", ""


def party_of(goal: dict, nodes: list[dict]) -> list[dict]:
    """The leader and the team as `{slug, name, head, band, state, why}`."""
    out = []
    lead = goal.get("leader")
    if lead:
        state, why = leader_state(goal["state"], nodes)
        out.append({**lead, "band": "lead", "state": state, "why": why})
    for m in goal["team"]:
        state, why = member_state(m["slug"], nodes)
        out.append({"slug": m["slug"], "name": m["name"], "head": m["head"], "band": "check" if m["checks"] else goal_team.band_of(m["slug"]),
                    "state": state, "why": why})
    return out
