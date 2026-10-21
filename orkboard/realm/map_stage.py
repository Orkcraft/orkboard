"""An idea's stage on the Map (docs/specs/48-map-ideas.md §1): worked out from its state and its plan, never written by hand.
Planning, Implementation, Checking, then Done. Pure: no file, no model, no words (the faces word it).
"""
from __future__ import annotations

from orkboard.realm import idea_checks

PLANNING = ("raw", "reading", "asks", "ready", "planning", "plan", "proposed")        # the states before a plan is passed
_GONE = ("merged", "dropped")                                                          # a task that is no longer to do


def is_check(task: dict) -> bool:
    return str(task.get("kind") or "") in idea_checks.TAGS


def stage_of(state: str, tasks: list[dict], passed: bool) -> str:
    """"planning" · "implementation" · "checking" · "done" (spec 48 §1.1). `passed`: the plan was passed (`passed_at`)."""
    if state == "done":
        return "done"
    if state in PLANNING or not passed or not tasks:
        return "planning"
    if any(not is_check(t) and t.get("state") not in _GONE for t in tasks):
        return "implementation"
    return "checking"


def round_of(tasks: list[dict]) -> int:
    """1, or the highest round a task is in (a task sent back runs again as round 2)."""
    return max([1, *(int(t.get("round") or 1) for t in tasks)])


def waves_of(tasks: list[dict]) -> dict[str, int]:
    """{task id: its wave}: 1 for a task that waits for none, else one more than the deepest it waits for (a cycle, which a
    plan never has, reads as no dependency)."""
    after = {str(t.get("id")): [str(a) for a in t.get("after") or []] for t in tasks}
    wave: dict[str, int] = {}
    walking: set[str] = set()

    def of(tid: str) -> int:
        if tid in wave:
            return wave[tid]
        walking.add(tid)
        deepest = max((of(a) for a in after[tid] if a in after and a not in walking), default=0)
        walking.discard(tid)
        wave[tid] = deepest + 1
        return wave[tid]

    for tid in after:
        of(tid)
    return wave
