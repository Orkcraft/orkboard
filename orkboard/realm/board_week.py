"""The Board's weeks (docs/specs/42-coming-back.md §6–§8): its nights and the work of the last seven days. A pure read of the event
log and the ledgers: no face, no model, it writes nothing.

    board_week.nights(root, settings, now)             # [{"date", "kind": "worked" | "idle" | "off"}], newest first
    board_week.this_week(root, state_dir, settings, now, rows, ops_base=None)    # §6.2's object

`root` is the project's folder (where the event log is), `settings` the Board's (`night`: "01:00-07:00"), `rows` the `ideas.board`
object. Times are the machine's.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from orkboard.realm import board_recap, event_log, idea_spend

WEEK = dt.timedelta(days=7)
WORKED_STATES = ("review", "merged")
_WORK_KEYS = ("drafted", "started", "refreshed", "proposed")


def window(spec: object) -> tuple[int, int] | None:
    """The night's (start, end) in minutes of the day; None when the Board has none."""
    try:
        a, b = (int(h) * 60 + int(m) for h, m in (part.split(":") for part in str(spec).split("-")))
    except ValueError:
        return None
    return (a, b) if a != b and 0 <= a < 1440 and 0 <= b < 1440 else None


def _span(day: dt.date, win: tuple[int, int]) -> tuple[dt.datetime, dt.datetime]:
    """The night that ends on `day`: the evening before for a window that crosses midnight."""
    a, b = win
    midnight = dt.datetime.combine(day, dt.time())
    end = midnight + dt.timedelta(minutes=b)
    start = (midnight if a < b else midnight - dt.timedelta(days=1)) + dt.timedelta(minutes=a)
    return start.astimezone(), end.astimezone()


def nights(root: Path, settings: dict, now: dt.datetime, n: int = 7) -> list[dict]:
    """The last `n` nights that have ended, newest first; each `worked` (a result reached Review or merged, or a night run that did
    something), `idle` (a night run, nothing worked) or `off` (no night run: Orkline was not running, or the night was turned off)."""
    win = window((settings or {}).get("night"))
    if win is None:
        return []
    now = now.astimezone()
    day = now.date()
    if _span(day, win)[1] > now:
        day -= dt.timedelta(days=1)
    spans = [(day - dt.timedelta(days=k), *_span(day - dt.timedelta(days=k), win)) for k in range(n)]
    log = board_recap.events_between(root, spans[-1][1], now, event_log.TASK_STATE, event_log.NIGHT_RUN)
    out = []
    for date, start, end in spans:
        inside = [r for r in log if start <= board_recap.when(r["at"]) < end]
        ran = [r for r in inside if r["event"] == event_log.NIGHT_RUN]
        worked = any(r["event"] == event_log.TASK_STATE and r.get("state") in WORKED_STATES for r in inside) or \
            any(board_recap._int(r.get(k)) > 0 for r in ran for k in _WORK_KEYS)
        out.append({"date": date.isoformat(), "kind": "worked" if worked else "idle" if ran else "off"})
    return out


def this_week(root: Path, state_dir: Path, settings: dict, now: dt.datetime, rows: dict, ops_base: Path | None = None,
              into: str = "dev") -> dict[str, Any]:
    now = now.astimezone()
    since = now - WEEK
    spent = idea_spend.between(state_dir, since, now)
    ops = idea_spend.between_file(Path(ops_base) / "spend.jsonl", since, now) if ops_base is not None else None
    merged, first = board_recap.merges(board_recap.events_between(root, since, now, event_log.TASK_STATE))
    kinds = [x["kind"] for x in nights(root, settings, now)]
    tonight = sum(1 for i in rows.get("ideas") or [] if i.get("state") != "done" and (i.get("queue") == "night" or i.get("start_at") == "night"))
    return {"usd": None if spent is None else round(spent, 2), "ops_usd": None if ops is None else round(ops, 2), "merged": merged,
            "first_time": first,
            "usd_per_merged": round(spent / merged, 2) if merged >= idea_spend.TOO_FEW and spent is not None else None,
            "nights": {k: kinds.count(k) for k in ("worked", "idle", "off")}, "tonight": tonight,
            "night_on": window((settings or {}).get("night")) is not None, "into": into}


# -- last week (spec 42 §7) ------------------------------------------------------------------------------------

def iso_week(day: dt.date) -> str:
    year, week, _d = day.isocalendar()
    return f"{year}-W{week:02d}"


def week_start(week: str) -> dt.date | None:
    """The Monday of an ISO week (`2026-W42`); None for anything else."""
    try:
        year, number = week.split("-W")
        return dt.date.fromisocalendar(int(year), int(number), 1)
    except (ValueError, AttributeError):
        return None


def _bounds(monday: dt.date) -> tuple[dt.datetime, dt.datetime]:
    return (dt.datetime.combine(monday, dt.time()).astimezone(), dt.datetime.combine(monday + dt.timedelta(days=7), dt.time()).astimezone())


def _results(root: Path, state_dir: Path, since: dt.datetime, until: dt.datetime) -> dict:
    merged, first = board_recap.merges(board_recap.events_between(root, since, until, event_log.TASK_STATE))
    spent = idea_spend.between(state_dir, since, until)
    return {"merged": merged, "first_time": first, "usd": None if spent is None else round(spent, 2),
            "usd_per_merged": round(spent / merged, 2) if merged >= idea_spend.TOO_FEW and spent is not None else None}


def last_week(root: Path, state_dir: Path, settings: dict, now: dt.datetime, rows: dict, week: str = "", into: str = "dev") -> dict[str, Any]:
    """The week before this one, Monday to Sunday (or `week`, an ISO week), as §7.1 has it."""
    now = now.astimezone()
    monday = week_start(week) if week else None
    if monday is None:
        monday = now.date() - dt.timedelta(days=now.weekday() + 7)
    since, until = _bounds(monday)
    prev_since, prev_until = _bounds(monday - dt.timedelta(days=7))
    by_idea = {i["slug"]: i for i in rows.get("ideas") or []}
    by_goal = {g["slug"]: g for g in rows.get("tracks") or []}
    now_week = _results(root, state_dir, since, until)
    prior = _results(root, state_dir, prev_since, prev_until)
    log = board_recap.events_between(root, since, until, event_log.KEEPER_STATE, event_log.GOAL_ACCEPTED, event_log.IDEA_ANSWERED,
                                     event_log.GOAL_ANSWERED)

    done: dict[str, set[str]] = {}
    for r in log:
        i = by_idea.get(str(r.get("idea") or ""))
        if r["event"] == event_log.KEEPER_STATE and r.get("state") == "done" and i is not None and i.get("track") in by_goal:
            done.setdefault(i["track"], set()).add(i["slug"])
    goals = [{"goal": g, "short": by_goal[g].get("short") or by_goal[g].get("title") or g, "title": by_goal[g].get("title") or g,
              "done": len(slugs)} for g, slugs in done.items() if g != "general"]

    accepted: dict[str, dict] = {}
    for r in log:
        if r["event"] == event_log.GOAL_ACCEPTED and str(r.get("goal") or "") in by_goal:
            accepted[str(r["goal"])] = r
    flags = [{"goal": g, "short": by_goal[g].get("short") or by_goal[g].get("title") or g, "title": by_goal[g].get("title") or g,
              "met": bool(r.get("met")), "by": str(r.get("by") or "")} for g, r in accepted.items()]

    cost = {s: usd for s, usd in idea_spend.by_idea_between(state_dir, since, until).items() if s in by_idea and usd >= 0.01}
    top = max(cost, key=cost.get) if cost else None
    dearest = {"slug": top, "short": by_idea[top].get("short") or by_idea[top].get("title") or top, "title": by_idea[top].get("title") or top,
               "usd": round(cost[top], 2)} if top else None

    everything = event_log.read(root)
    added = {r["idea"]: board_recap.when(r["at"]) for r in everything if r.get("event") == event_log.IDEA_ADDED and r.get("idea")}
    first_merge: dict[str, dt.datetime] = {}
    for r in everything:
        at = board_recap.when(r.get("at"))
        if r.get("event") == event_log.TASK_STATE and r.get("state") == "merged" and at is not None:
            first_merge[str(r.get("idea") or "")] = min(first_merge.get(str(r.get("idea") or ""), at), at)
    quick = [(int((at - added[s]).total_seconds() // 60), s) for s, at in first_merge.items()
             if s in by_idea and s in added and added[s] is not None and since <= at < until]
    fastest = None
    if quick:
        minutes, slug = min(quick)
        fastest = {"slug": slug, "short": by_idea[slug].get("short") or by_idea[slug].get("title") or slug,
                   "title": by_idea[slug].get("title") or slug, "minutes": max(0, minutes)}

    answered = [r for r in log if r["event"] in (event_log.IDEA_ANSWERED, event_log.GOAL_ANSWERED)]
    answers = {"answers": sum(board_recap._int(r.get("answers")) for r in answered),
               "recommended": sum(board_recap._int(r.get("recommended")) for r in answered),
               "decided": sum(1 for r in answered if r.get("decided") is True)} if answered else None

    kinds = [x["kind"] for x in nights(root, settings, min(now, until), 7)] if until > since else []
    out = {"week": iso_week(monday), "from": monday.isoformat(), "to": (monday + dt.timedelta(days=6)).isoformat(), "into": into, **now_week,
           "before": {k: prior[k] for k in ("merged", "first_time", "usd_per_merged")} if prior["merged"] else None,
           "goals": goals, "flags": flags, "dearest": dearest, "fastest": fastest, "answers": answers,
           "nights": {k: kinds.count(k) for k in ("worked", "idle", "off")}, "streak": 0}
    out["empty"] = not (now_week["merged"] or flags or goals)
    return out
