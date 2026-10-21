"""A goal's flag (docs/specs/50-parties-and-goals.md §2.2, decisions §63.3): the mark a goal gets, once, when the gate takes it
into main, or when it is done where there is no gate. It is kept beside the goal's state, `<state_dir>/ideas/<slug>/flag.json`,
with what the goal took (its tally). A party's flags are its goals' flags; a party's old flag (a verdict met,
`realm/goal_flags.py`) is history and stays where it is.

    idea_flag.tally(root, state_dir, "dark-mode")                  # {"tasks", "first_time", "usd", "days"}
    idea_flag.raise_flag(root, state_dir, "dark-mode", "gate", commit)   # writes the flag once; the one it has when it has one
    idea_flag.flag_of(state_dir, "dark-mode")                      # the flag as kept, None before it is raised
    idea_flag.commits_of(state_dir, "dark-mode")                   # the commits of its merged tasks (what `idea_gate.all_in` asks main)

No face, no model, no git: the host decides *when* (gui/ideas_gate.py); this module keeps and counts. A flag is never undone.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from orkboard.realm import board_recap, idea_spend, ideas

FLAG = "flag.json"
BY = ("gate", "done")               # the gate took it into main · it was done where there is no gate (or all its commits were in main already)


def flag_path(state_dir: Path, slug: str) -> Path:
    return ideas.state_folder(state_dir, slug) / FLAG


def flag_of(state_dir: Path, slug: str) -> dict | None:
    """The flag as kept (`{"at", "by", "commit", "tasks", "first_time", "usd", "days"}`); None before it is raised."""
    try:
        got = ideas._json(flag_path(state_dir, slug))
    except ValueError:
        return None
    return got if isinstance(got, dict) and got.get("at") else None


def commits_of(state_dir: Path, slug: str) -> list[str]:
    """The commits of the goal's merged tasks, in the plan's order, each once (a check that landed nothing has none)."""
    tasks = (ideas.plan(state_dir, slug) or {}).get("tasks") or []
    return list(dict.fromkeys(str(t["commit"]) for t in tasks if isinstance(t, dict) and t.get("state") == "merged" and t.get("commit")))


def _first_turn(state_dir: Path, slug: str) -> dt.datetime | None:
    """When the person's first words on the goal were kept (`talk.jsonl`'s first line): the goal's first state."""
    try:
        with (ideas.state_folder(state_dir, slug) / "talk.jsonl").open(encoding="utf-8") as f:
            row = json.loads(f.readline() or "null")
    except (OSError, ValueError):
        return None
    return board_recap.when(row.get("at")) if isinstance(row, dict) else None


def _first_spend(state_dir: Path, slug: str) -> dt.datetime | None:
    times = [t for r in idea_spend.read(ideas.state_folder(state_dir, slug) / idea_spend.FILE)
             if (t := board_recap.when(r.get("at"))) is not None]
    return min(times) if times else None


def tally(root: Path, state_dir: Path, slug: str, *, now: dt.datetime | None = None) -> dict:
    """What the goal took, as `goal_flags.tally` counts a party's, for one goal: its merged tasks (code and checks), of them
    those merged in their first round (never sent back), its $ (None when unpriced, never 0), and whole days from its first
    state to now (at least 1; None when no start is known). `root` is where the pages are (the faces' signature)."""
    tasks = [t for t in (ideas.plan(state_dir, slug) or {}).get("tasks") or [] if isinstance(t, dict) and t.get("state") == "merged"]
    spent = idea_spend.of_idea(state_dir, slug)["usd"]
    starts = [t for t in (_first_turn(state_dir, slug), _first_spend(state_dir, slug)) if t is not None]
    now = (now or dt.datetime.now()).astimezone()
    return {"tasks": len(tasks), "first_time": sum(1 for t in tasks if int(t.get("round") or 1) <= 1),
            "usd": round(spent, 2) if spent else None, "days": max(1, (now - min(starts)).days) if starts else None}


def raise_flag(root: Path, state_dir: Path, slug: str, by: str, commit: str = "") -> dict:
    """Write the goal's flag, `{"at", "by", "commit", **tally}`, once: a goal that has one keeps it, and that is what is
    returned. `by`: "gate" or "done". `commit`: the merge that took it into main (the last commit of its work when it is done)."""
    if by not in BY:
        raise ValueError(f"A flag is raised by the gate or when the goal is done, not {by!r}")
    with ideas.LOCK:
        have = flag_of(state_dir, slug)
        if have is not None:
            return have
        got = {"at": dt.datetime.now().isoformat(timespec="seconds"), "by": by, "commit": str(commit or ""),
               **tally(root, state_dir, slug)}
        ideas._write_json(flag_path(state_dir, slug), got)
    return got
