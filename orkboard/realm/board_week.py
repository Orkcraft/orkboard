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
