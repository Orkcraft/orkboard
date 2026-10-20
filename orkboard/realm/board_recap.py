"""While you were away (docs/specs/42-coming-back.md §1): what the Board did since a device's last look, as data. A pure
read of the event log and the ledgers: no face, no model, it writes nothing, starts nothing and moves nothing.

    board_recap.build(root, state_dir, since, now, rows)      # §1.1's object
    board_recap.when("2026-10-20T09:00:00+02:00")             # a log's time or a ledger's, as a datetime

`root` is the project's folder (where the event log is). `rows`: the Board's `{"ideas": [...], "tracks": [...]}` (`ideas.board`), for titles and short names; an idea or a goal
the Board no longer has is left out of every list. Times are never compared as text.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from orkboard.realm import event_log, idea_spend, ideas

LOOK_BACK = dt.timedelta(days=1)         # the log is read from a day earlier (its lines carry an offset), then cut exactly


def when(text: object) -> dt.datetime | None:
    """A time as the log writes it (local ISO with an offset) or a ledger does (local, naive); None when it is neither."""
    try:
        got = dt.datetime.fromisoformat(str(text or ""))
    except ValueError:
        return None
    return got.astimezone()


def events_between(root: Path, since: dt.datetime, now: dt.datetime, *names: str) -> list[dict]:
    """The log's lines of these events whose time is in `[since, now)`, oldest first."""
    coarse = (since - LOOK_BACK).strftime("%Y-%m-%d")
    out = []
    for r in event_log.read(root, since=coarse):
        at = when(r.get("at"))
        if r.get("event") in names and at is not None and since <= at < now:
            out.append(r)
    return sorted(out, key=lambda r: when(r.get("at")))


def merges(events: list[dict]) -> tuple[int, int]:
    """(merged, merged the first time) over `task_state` lines: the person's merge and a result that lands by itself
    both write one; the first time is round 1. A check that found nothing (`clean`) is no result (spec 43 §1.4)."""
    merged = [r for r in events if r.get("state") == "merged" and r.get("clean") is not True]
    return len(merged), sum(1 for r in merged if int(r.get("round") or 1) <= 1)


def _int(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def build(root: Path, state_dir: Path, since: dt.datetime, now: dt.datetime, rows: dict, into: str = "dev") -> dict[str, Any]:
    from orkboard.realm.board_map import task_short           # board_map reads goal_flags, which reads `when`
    by_idea = {i["slug"]: i for i in rows.get("ideas") or []}
    by_goal = {g["slug"]: g for g in rows.get("tracks") or []}
    log = events_between(root, since, now, event_log.TASK_STATE, event_log.GOAL_ACCEPTED, event_log.NIGHT_RUN, event_log.PROPOSAL_MADE)

    def idea(slug: str) -> dict:
        i = by_idea[slug]
        return {"slug": slug, "short": i.get("short") or i.get("title") or slug, "title": i.get("title") or slug, "goal": i.get("track") or ""}

    states = [r for r in log if r["event"] == event_log.TASK_STATE]
    tasks, first = merges(states)
    mine: list[str] = []
    for r in states:
        slug = str(r.get("idea") or "")
        if r.get("state") == "merged" and r.get("clean") is not True and slug in by_idea and slug not in mine:
            mine.append(slug)
    done = [{**idea(s), "done": by_idea[s].get("state") == "done"} for s in mine]

    accepted: dict[str, dict] = {}
    for r in log:
        if r["event"] == event_log.GOAL_ACCEPTED and str(r.get("goal") or "") in by_goal:
            accepted[str(r["goal"])] = r
    flags = [{"goal": g, "short": by_goal[g].get("short") or by_goal[g].get("title") or g, "title": by_goal[g].get("title") or g,
              "met": bool(r.get("met")), "by": str(r.get("by") or "")} for g, r in accepted.items()]

    sums = {k: sum(_int(r.get(k)) for r in log if r["event"] == event_log.NIGHT_RUN) for k in ("drafted", "started", "refreshed", "proposed")}
    night = sums if any(sums.values()) else None

    proposed: list[dict] = []
    for r in log:
        slug = str(r.get("idea") or "")
        if r["event"] == event_log.PROPOSAL_MADE and slug in by_idea and by_idea[slug].get("state") == "proposed" \
                and not any(p["slug"] == slug for p in proposed):
            proposed.append(idea(slug))

    failed: list[dict] = []
    for r in states:
        slug, tid = str(r.get("idea") or ""), str(r.get("task") or "")
        if r.get("state") != "failed" or slug not in by_idea or any(f["slug"] == slug and f["_id"] == tid for f in failed):
            continue
        task = next((t for t in (ideas.plan(state_dir, slug) or {}).get("tasks") or [] if t.get("id") == tid), None)
        if task is not None and task.get("state") == "failed":
            failed.append({**{k: idea(slug)[k] for k in ("slug", "short", "title")}, "task": task_short(task), "_id": tid})
    for f in failed:
        f.pop("_id")

    spent = idea_spend.between(state_dir, since, now)
    out = {"since": since.isoformat(timespec="seconds"), "hours": max(0, round((now - since).total_seconds() / 3600)), "into": into,
           "merged": {"tasks": tasks, "first_time": first, "ideas": done}, "flags": flags, "night": night, "proposed": proposed,
           "failed": failed, "usd": None if spent is None else round(spent, 2), "nights": 0, "waits": {"you": 0, "review": 0}}
    out["empty"] = not (tasks or flags or proposed or failed or night)
    return out
