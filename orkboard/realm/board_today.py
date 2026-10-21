"""Today's events (docs/specs/49-one-window.md §2.2): the event log since local midnight as the rows of the strip beside the
Board's field. A pure read of lines already read: no face, no git, no write.

    board_today.rows(lines, titles, into="dev", since=board_today.midnight(now))     # newest first, at most 40

`lines`: the log's lines (`event_log.read`), oldest first; `titles`: the Board's names for them,
`{"ideas": {slug: {"title", "short"?, "goal"}}, "goals": {slug: title}, "tasks": {slug: {task id: title}}}`; a title the Board no
longer has reads as the slug (a task's as its idea's title, else the idea's slug). `into`: the branch a merge went into
(a line that says its own wins). One row per line of these events, the rest skipped:

    task_state merged        ✓ ok     merged into <into>      (a check that found nothing, `clean`, landed nothing: no row)
    task_state failed        ✗ danger failed
    result_decided back/fix  ↺ muted  sent back
    result_decided drop      ✗ muted  dropped
    plan_passed              ▸ ink    the work started
    idea_answered, goal_answered   ·  muted  you answered
    proposal_answered        + / · muted taken / left out
    gate_merged              ✓ ok     dev merged into main    (title dev → main; the line's own `into` and `main` win)
    idea_flagged             ⚑ ok     is in main              (title: the goal's short name; spec 50 §2.4)

A row is `{at ("HH:MM", local), mark, tone, words, title, goal, idea, task, open}`: `goal` is its idea's goal (the gate's row
has none: it belongs to every goal), `open` what a click opens, `{kind, slug, task?}`: a `result` (the code a merge or a
sent-back task made), a `task` (a failure's, a drop's), an `idea`, a `goal` (the one answered) or the `gate`.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Iterable

from orkboard.realm import board_recap, event_log

LIMIT = 40                                 # the most rows the strip shows


def midnight(now: dt.datetime) -> dt.datetime:
    """Local midnight of the day `now` is in (an aware time, so the log's lines are placed by their instants)."""
    return dt.datetime.combine(now.astimezone().date(), dt.time.min).astimezone()


def _get(table: Any, key: str) -> Any:
    return table.get(key) if isinstance(table, dict) else None


def _idea_of(titles: dict, slug: str) -> tuple[str, str]:
    """(the idea's title, its goal's slug); (the slug, "") for an idea the Board no longer has."""
    got = _get(titles.get("ideas"), slug)
    got = got if isinstance(got, dict) else {}
    return str(got.get("title") or slug), str(got.get("goal") or "")


def _says(r: dict, into: str) -> tuple[str, str, str, str] | None:
    """(mark, tone, words, what a click opens) of an idea's or a task's line; None for a line with no row."""
    event, state, decision = r.get("event"), r.get("state"), r.get("decision")
    if event == event_log.TASK_STATE and state == "merged" and r.get("clean") is not True:
        return "✓", "ok", f"merged into {r.get('into') or into}", "result"
    if event == event_log.TASK_STATE and state == "failed":
        return "✗", "danger", "failed", "task"
    if event == event_log.RESULT_DECIDED and decision in ("back", "fix"):
        return "↺", "muted", "sent back", "result"
    if event == event_log.RESULT_DECIDED and decision == "drop":
        return "✗", "muted", "dropped", "task"
    if event == event_log.PLAN_PASSED:
        return "▸", "ink", "the work started", "idea"
    if event == event_log.IDEA_ANSWERED:
        return "·", "muted", "you answered", "idea"
    if event == event_log.PROPOSAL_ANSWERED:
        return ("+", "muted", "taken", "idea") if r.get("take") is True else ("·", "muted", "left out", "idea")
    return None


def _row(r: dict, titles: dict, into: str) -> dict | None:
    event = r.get("event")
    if event == event_log.GATE_MERGED:
        a, b = str(r.get("into") or into), str(r.get("main") or "main")
        return _made(r, "✓", "ok", f"{a} merged into {b}", f"{a} → {b}", "", "", "", {"kind": "gate", "slug": ""})
    if event == event_log.IDEA_FLAGGED:
        slug = str(r.get("idea") or "")
        title, goal = _idea_of(titles, slug)
        short = str((_get(titles.get("ideas"), slug) or {}).get("short") or "") or title
        return _made(r, "⚑", "ok", "is in main", short, goal or str(r.get("goal") or ""), slug, "", {"kind": "idea", "slug": slug}) if slug else None
    if event == event_log.GOAL_ANSWERED:
        slug = str(r.get("goal") or "")
        title = str(_get(titles.get("goals"), slug) or slug)
        return _made(r, "·", "muted", "you answered", title, slug, "", "", {"kind": "goal", "slug": slug}) if slug else None
    says, idea, tid = _says(r, into), str(r.get("idea") or ""), str(r.get("task") or "")
    if says is None or not idea or (says[3] != "idea" and not tid):
        return None
    mark, tone, words, kind = says
    title, goal = _idea_of(titles, idea)
    if kind == "idea":
        return _made(r, mark, tone, words, title, goal, idea, "", {"kind": "idea", "slug": idea})
    title = str(_get(_get(titles.get("tasks"), idea), tid) or "") or title        # a task the Board lost reads as its idea
    return _made(r, mark, tone, words, title, goal, idea, tid, {"kind": kind, "slug": idea, "task": tid})


def _made(r: dict, mark: str, tone: str, words: str, title: str, goal: str, idea: str, task: str, where: dict) -> dict:
    at = board_recap.when(r.get("at"))
    return {"at": at.strftime("%H:%M") if at else "", "mark": mark, "tone": tone, "words": words, "title": title, "goal": goal,
            "idea": idea, "task": task, "open": where}


def rows(lines: Iterable[dict], titles: dict, into: str = "dev", since: dt.datetime | None = None, limit: int = LIMIT) -> list[dict]:
    """The strip's rows, newest first (a line written later wins a tie), at most `limit`. `since`: lines before it (by
    their instants) are left out, local midnight for the strip."""
    cut = since.astimezone() if since is not None else None
    kept: list[tuple[dt.datetime, dict]] = []
    for r in lines:
        at = board_recap.when(r.get("at"))
        if at is None or (cut is not None and at < cut):
            continue
        got = _row(r, titles, into)
        if got is not None:
            kept.append((at, got))
    kept.reverse()                          # the log is oldest first: a tie goes to the later line
    kept.sort(key=lambda p: p[0], reverse=True)
    return [row for _at, row in kept[:max(0, limit)]]
