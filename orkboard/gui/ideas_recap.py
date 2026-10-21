"""Coming back (docs/specs/42-coming-back.md) as `gui/ideas.py`'s `Ideas` has it: `ideas.recap`, what the Board did since a
device's last look (realm/board_recap.py), and `ideas.today`, today's events as rows (spec 49 §2.2, realm/board_today.py). It
reads and changes nothing; B, F, G and H add their readers here. Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from orkboard.gui.ideas_args import IdeasError
from orkboard.realm import board_recap, board_today, board_week, event_log, goal_flags, ideas, op_runs

RECAP_DAYS = 30                          # a last look older than this is taken as this many days ago


class RecapMixin:
    def recap(self, args: dict) -> dict:
        """`{"since": <ms since the epoch>}`: §1.1's object for this project, `waits` filled from the snapshot."""
        ms = args.get("since")
        if not isinstance(ms, (int, float)) or isinstance(ms, bool):
            raise IdeasError("`since` is the last look, in milliseconds")
        now = dt.datetime.now().astimezone()
        try:
            since = dt.datetime.fromtimestamp(ms / 1000).astimezone()
        except (OverflowError, OSError, ValueError):
            raise IdeasError("`since` is the last look, in milliseconds") from None
        if since > now:
            raise IdeasError("`since` is ahead of now")
        since = max(since, now - dt.timedelta(days=RECAP_DAYS))
        got = board_recap.build(Path(self.host.repo_root), self.state_dir, since, now, self.board(make=False), into=self._into())
        snap = self.snapshot()
        got["waits"] = {"you": int(snap.get("needs_you") or 0), "review": int(snap.get("review_count") or 0)}
        got["nights"] = board_week.streak(Path(self.host.repo_root), self.settings_now(), now)
        return got

    def today(self, args: dict) -> dict:
        """`{}`: `{events: [{at, mark, tone, words, title, goal, idea, task, open}]}`, the event log since local midnight,
        newest first, at most 40 (spec 49 §2.2): the titles joined from the Board, a title it no longer has read as the slug."""
        since = board_today.midnight(dt.datetime.now())
        lines = event_log.read(Path(self.host.repo_root), since=(since - dt.timedelta(days=1)).strftime("%Y-%m-%d"))
        root = self.root(False)
        names = {i["slug"]: {"title": i["title"], "short": i["short"], "goal": i["track"]} for i in ideas.ideas(root)}
        mine = {str(r.get("idea") or "") for r in lines if r.get("event") in (event_log.TASK_STATE, event_log.RESULT_DECIDED)}
        tasks = {slug: {str(t.get("id")): str(t.get("title") or "") for t in (ideas.plan(self.state_dir, slug) or {}).get("tasks") or []}
                 for slug in mine if slug in names}
        titles = {"ideas": names, "goals": {t["slug"]: t["title"] for t in ideas.tracks(root, make=False)}, "tasks": tasks}
        return {"events": board_today.rows(lines, titles, into=self._into(), since=since)}

    def flags(self, args: dict) -> dict:
        """`{}`: `{flags, goals}`. `flags`: the parties' old flags, goals accepted by their leader against their metrics, newest
        first (spec 42 §2). `goals`: the goals' flags, every party's, newest first (spec 50 §2.4): the faces filter by `goal`."""
        root = self.root(False)
        return {"flags": goal_flags.flags(root, self.state_dir), "goals": goal_flags.goals(root, self.state_dir)}

    def week_work(self, args: dict) -> dict:
        """`{}`: the work of the last seven days beside today's spend, and the nights (spec 42 §6)."""
        return board_week.this_week(Path(self.host.repo_root), self.state_dir, self.settings_now(), dt.datetime.now().astimezone(),
                                    self.board(make=False), ops_base=op_runs.root(), into=self._into(),
                                    limits=list(self.host.limits() or []))

    def week(self, args: dict) -> dict:
        """`{"week"?}`: last week (an ISO week, `2026-W42`; default the last full one), Monday to Sunday (spec 42 §7)."""
        week = args.get("week")
        if week is not None and (not isinstance(week, str) or (week and board_week.week_start(week) is None)):
            raise IdeasError("`week` is an ISO week, like 2026-W42")
        return board_week.last_week(Path(self.host.repo_root), self.state_dir, self.settings_now(), dt.datetime.now().astimezone(),
                                    self.board(make=False), week=week or "", into=self._into())
