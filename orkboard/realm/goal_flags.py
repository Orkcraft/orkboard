"""A goal's flag and what it took (docs/specs/42-coming-back.md §2): a goal accepted by its leader against its metrics
(`realm/goal_verdict.py`, `met`) is a flag; its tally is the numbers under it. A pure read of the pages, the plans, the ledgers and
the event log: no face, no model, it writes nothing.

    goal_flags.tally(root, state_dir, "offline-mode")    # {"ideas", "results", "first_time", "usd", "days"}
    goal_flags.flags(root, state_dir)                    # [{"goal", "title", "short", "by", "at", "tally"}], newest first: a party's old flags
    goal_flags.goals(root, state_dir)                    # [{"slug", "title", "short", "goal", "element", "at", "tasks", …}], newest first: the goals' flags

`root` is the Board's tree (where the pages are); the event log is the project's, `state_dir`'s parent.
"""
from __future__ import annotations

import datetime as dt
import threading
from pathlib import Path

from orkboard.realm import board_recap, event_log, goal_verdict, idea_element, idea_flag, idea_spend, ideas

_STARTS: dict[str, tuple[tuple[int, int], dict[str, dt.datetime]]] = {}      # event log → ((mtime, size), goal → its first `goal_saved`)
_LOCK = threading.Lock()


def _saved(project: Path) -> dict[str, dt.datetime]:
    """Each goal's first `goal_saved` with `new: true`, read from the log again only when the log changed."""
    target = event_log.path(project)
    try:
        stat = target.stat()
    except OSError:
        return {}
    key, sign = str(target), (stat.st_mtime_ns, stat.st_size)
    with _LOCK:
        hit = _STARTS.get(key)
    if hit is not None and hit[0] == sign:
        return hit[1]
    found: dict[str, dt.datetime] = {}
    for r in event_log.read(project):
        at = board_recap.when(r.get("at"))
        if r.get("event") == event_log.GOAL_SAVED and r.get("new") is True and at is not None and str(r.get("goal") or ""):
            found[r["goal"]] = min(found.get(r["goal"], at), at)
    with _LOCK:
        _STARTS[key] = (sign, found)
    return found


def _first(path: Path) -> dt.datetime | None:
    """The oldest `at` of a ledger's lines."""
    times = [t for r in idea_spend.read(path) if (t := board_recap.when(r.get("at"))) is not None]
    return min(times) if times else None


def tally(root: Path, state_dir: Path, goal: str) -> dict:
    """The goal's ideas that are done, the tasks of their plans that are merged and, of those, merged the first time; the goal's
    $ (None when unpriced, never 0); whole days from the goal's start to its verdict (at least 1; None when no start is known)."""
    mine = [i["slug"] for i in ideas.ideas(root, goal)]
    done = [s for s in mine if ideas.state(state_dir, s)["state"] == "done"]
    merged = [t for s in done for t in (ideas.plan(state_dir, s) or {}).get("tasks") or [] if t.get("state") == "merged"]
    spent = idea_spend.of_goal(state_dir, goal, mine)
    total = spent["usd"] if spent["usd"] else None
    starts = [t for t in [_saved(Path(state_dir).parent).get(goal), _first(ideas.goal_folder(state_dir, goal) / idea_spend.FILE),
                          *(_first(Path(state_dir) / "ideas" / s / idea_spend.FILE) for s in mine)] if t is not None]
    verdict = board_recap.when((goal_verdict.read(state_dir, goal) or {}).get("at"))
    days = max(1, (verdict - min(starts)).days) if starts and verdict is not None else None
    return {"ideas": len(done), "results": len(merged), "first_time": sum(1 for t in merged if int(t.get("round") or 1) <= 1),
            "usd": None if total is None else round(total, 2), "days": days}


def flags(root: Path, state_dir: Path) -> list[dict]:
    """Every goal (General never) whose verdict is met, newest first."""
    out = []
    for g in ideas.tracks(root, make=False):
        verdict = goal_verdict.read(state_dir, g["slug"]) if g["slug"] != ideas.GENERAL else None
        if verdict and verdict.get("met") is True:
            out.append({"goal": g["slug"], "title": g["title"], "short": g["short"], "by": verdict.get("by") or "",
                        "at": verdict.get("at") or "", "tally": tally(root, state_dir, g["slug"])})
    return sorted(out, key=lambda f: (board_recap.when(f["at"]) or dt.datetime.fromtimestamp(0)).timestamp(), reverse=True)


def goals(root: Path, state_dir: Path) -> list[dict]:
    """The flags of the goals (spec 50 §2.2, §2.4), every party's, newest first: a goal's slug, title, short name, its party's
    slug (`goal`, the code's name), its element, and its flag's `at` and tally (`tasks`, `first_time`, `usd`, `days`). The faces
    filter by `goal`; a party's old flags (what `flags` lists) are history and stay where they are."""
    out = []
    for i in ideas.ideas(root):
        flag = idea_flag.flag_of(state_dir, i["slug"])
        if flag is not None:
            out.append({"slug": i["slug"], "title": i["title"], "short": i["short"], "goal": i["track"],
                        "element": idea_element.of(state_dir, i["slug"]), "at": flag["at"],
                        **{k: flag.get(k) for k in ("tasks", "first_time", "usd", "days")}})
    return sorted(out, key=lambda f: (board_recap.when(f["at"]) or dt.datetime.fromtimestamp(0).astimezone()).timestamp(), reverse=True)
