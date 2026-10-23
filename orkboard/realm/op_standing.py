"""Standing briefs (docs/specs/66-team-briefs.md §3): a brief prepared on its own time, before a meeting.

    items = op_standing.load(root)                 # ops/standing.json: [{id, template, fields, days, at, before, last,
                                                   #  skipped}], at most MAX
    item = op_standing.clean(given, fields)        # the days, the time and the minutes before checked (ValueError in words)
    op_standing.due(item, now)                     # "add" (its time came today), "skip" (the meeting passed), or ""
    op_standing.words(item, "Before the daily")    # "Before the daily: weekdays 09:30"

`days` are the days of the week, Monday 0 to Sunday 6; `at` the meeting's time, local, `HH:MM`; `before` the minutes
before it the brief is added; `last` the day it was last added or skipped (once a day); `skipped` what its row says when
it was skipped ("" once added again). The file is the person's, mode 600, beside the operations (realm/op_runs.py).
Pure: no face, no model; Operations' tick (core/op_briefs.py) adds what is due.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import secrets
from pathlib import Path

from orkboard.realm import op_runs

FILE = "standing.json"
MAX = 12
BEFORE, BEFORE_MAX = 30, 240
TIME = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
OFF = "skipped: the machine was off"
KEYS = ("id", "template", "fields", "days", "at", "before", "last", "skipped")


def path(base: Path) -> Path:
    return Path(base) / FILE


def new_id() -> str:
    return f"st-{secrets.token_hex(4)}"


def load(base: Path) -> list[dict]:
    """The standing briefs as kept; a broken row is left out."""
    try:
        data = json.loads(path(base).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for row in data if isinstance(data, list) else []:
        if isinstance(row, dict) and isinstance(row.get("id"), str) and isinstance(row.get("template"), str):
            try:
                out.append({**clean(row, row.get("fields")), "id": row["id"], "template": row["template"],
                            "last": str(row.get("last") or ""), "skipped": str(row.get("skipped") or "")})
            except ValueError:
                continue
    return out[:MAX]


def save(base: Path, items: list[dict]) -> None:
    op_runs.write(path(base), json.dumps([{k: i.get(k) for k in KEYS} for i in items[:MAX]], ensure_ascii=False,
                                         indent=1))


def clean(given: dict, fields: object) -> dict:
    """The schedule as given, checked: one to seven days, a time `HH:MM`, 0 to BEFORE_MAX minutes before (BEFORE when
    not given). The fields are the caller's to check against the template's form."""
    days = given.get("days")
    if not isinstance(days, list) or not days or not all(isinstance(d, int) and not isinstance(d, bool)
                                                         and 0 <= d <= 6 for d in days):
        raise ValueError("Pick the days of the week it is prepared on")
    at = given.get("at")
    if not isinstance(at, str) or not TIME.match(at.strip()):
        raise ValueError("The meeting's time is HH:MM")
    before = given.get("before", BEFORE)
    if not isinstance(before, int) or isinstance(before, bool) or not 0 <= before <= BEFORE_MAX:
        raise ValueError(f"Minutes before is 0 to {BEFORE_MAX}")
    return {"fields": dict(fields) if isinstance(fields, dict) else {}, "days": sorted(set(days)), "at": at.strip(),
            "before": before}


def meeting(item: dict, day: dt.date) -> dt.datetime:
    hh, mm = (int(x) for x in item["at"].split(":"))
    return dt.datetime.combine(day, dt.time(hh, mm))


def due(item: dict, now: dt.datetime) -> str:
    """What today asks of it: "add" from `before` minutes before the meeting until it starts, "skip" once its meeting
    passed and it was neither added nor skipped today (the machine was off, or asleep), else ""."""
    today = now.date()
    if today.weekday() not in item.get("days", []) or item.get("last") == today.isoformat():
        return ""
    starts = meeting(item, today)
    if now >= starts:
        return "skip"
    return "add" if now >= starts - dt.timedelta(minutes=int(item.get("before", BEFORE))) else ""


def first_last(item: dict, now: dt.datetime) -> str:
    """`last` for a standing brief set or changed now: today when today's meeting has passed already (it is not a
    skip), else what it was, or ""."""
    today = now.date()
    if today.weekday() in item.get("days", []) and now >= meeting(item, today):
        return today.isoformat()
    return str(item.get("last") or "") if item.get("last") == today.isoformat() else ""


def days_words(days: list[int]) -> str:
    days = sorted(set(days))
    if days == list(range(7)):
        return "every day"
    if days == list(range(5)):
        return "weekdays"
    if days == [5, 6]:
        return "weekends"
    return ", ".join(DAY_NAMES[d] for d in days)


def words(item: dict, title: str) -> str:
    """Its row in Templates: *Before the daily: weekdays 09:30*."""
    return f"{title}: {days_words(item.get('days', []))} {item.get('at', '')}"
