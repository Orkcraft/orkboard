"""The Board's night (docs/specs/35-goals-window.md §7, §8): once a night, at the start of `ideas.night` (the machine's
local time), and again inside it when the reserve held it. A mixin of `IdeaKeeper`.

    keeper.night_tick(now)           # from the keeper's clock: the night when it is due, in a thread
    keeper.run_night()               # the same, on this thread: its counts (the `night_run` event)

In this order, each step stopping at the reserve (realm/idea_target.py `reserve_held`):
  1. the `night` queue: draft → plan → autostart, by priority, then the person's order;
  2. the plans that start at night (`start_night(slug)`: the face hands them to the runner);
  3. refresh (balance, quality): a goal whose linked paths, or the paths its Summary names, changed since its `read_at`
     is read again on the `refresh` step; an unchanged goal costs nothing;
  4. proposals (balance 2, quality 3, thrift none): new ideas in the state `proposed`, never more than 3 waiting, a
     declined one read back from `<state_dir>/ideas/declined.jsonl`.

The camp's Night round (docs/design/night-round.md) is another thing and is not touched here.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import threading
import time
from pathlib import Path

from orkboard.realm import event_log, idea_target, ideas

RETRY_S = 600                     # a night the reserve held is tried again after this, inside the window
DECLINED, NIGHT = "declined.jsonl", "night.json"
DECLINED_READ, COMMITS_READ = 30, 50
_PATH = re.compile(r"`?([\w.-]+(?:/[\w.*-]+)+/?|[\w-]+\.(?:py|js|ts|tsx|md|json|toml|yaml|yml|css|html|sql))`?")


def _kw():
    from orkboard.core import idea_keeper
    return idea_keeper


def declined(state_dir: Path, last: int = DECLINED_READ) -> list[dict]:
    """The proposals turned down, the newest last: {title, goal, reason, at}."""
    try:
        lines = (Path(state_dir) / "ideas" / DECLINED).read_text(encoding="utf-8").splitlines()[-last:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append({k: str(row.get(k) or "") for k in ("title", "goal", "reason", "at")})
    return out


def decline(state_dir: Path, title: str, goal: str, reason: str = "") -> None:
    path = Path(state_dir) / "ideas" / DECLINED
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"title": title[:200], "goal": goal, "reason": " ".join(str(reason or "").split())[:300],
           "at": dt.datetime.now().isoformat(timespec="seconds")}
    with ideas.LOCK, path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _rank(i: dict) -> tuple:
    return ideas.PRIORITIES.index(i["priority"]), i["order"], i["slug"]


class NightMixin:
    # -- when -----------------------------------------------------------------------------------------------

    def _night_file(self) -> Path:
        return self.state_dir / "ideas" / NIGHT

    def night_state(self) -> dict:
        try:
            data = json.loads(self._night_file().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def night_key(self, now: float) -> str:
        start = idea_target.night_start(str((self.settings() or {}).get("night") or "01:00-07:00"),
                                        dt.datetime.fromtimestamp(now))
        return start.isoformat(timespec="minutes") if start else ""

    def night_tick(self, now: float) -> bool:
        """The night when it is due: once a window, and again (every RETRY_S) while the reserve held it."""
        key = self.night_key(now)
        if not key or self._night_busy:
            return False
        last = self.night_state()
        if last.get("key") == key and (not last.get("held") or now - self._night_tried < RETRY_S):
            return False
        self._night_tried, self._night_busy = now, True

        def run() -> None:
            try:
                self.run_night(key)
            finally:
                self._night_busy = False
        threading.Thread(target=run, daemon=True, name="idea-night").start()
        return True

    def _reserved(self) -> bool:
        """The reserve is reached: what runs by itself stops here."""
        try:
            limits = list(self.limits() or [])
        except Exception:
            limits = []
        return idea_target.reserve_held(limits, self.settings(), time.time()) is not None

    # -- the run ---------------------------------------------------------------------------------------------

    def run_night(self, key: str = "") -> dict:
        began = time.monotonic()
        key = key or self.night_key(time.time()) or dt.datetime.now().isoformat(timespec="minutes")
        counts = {"drafted": 0, "started": 0, "refreshed": 0, "proposed": 0, "held": 0}
        root = self.wiki_root()
        steps = (self._night_queue, self._night_starts, self._night_refresh, self._night_proposals)
        for step in steps:
            if self._may_run() or self.cancel.is_set():
                break
            step(root, counts)
        prev = self.night_state()
        data = {"key": key, "held": counts["held"] > 0, "at": dt.datetime.now().isoformat(timespec="seconds"),
                "head": self.head() or prev.get("head", ""), "head_before": prev.get("head", "") if prev.get("key") != key
                else prev.get("head_before", "")}
        ideas._write_json(self._night_file(), data)
        measure = counts.pop("measure", None) or {"step": "propose", "prompt_chars": 0, "tokens": None, "cost": None}
        self._ev(event_log.NIGHT_RUN, **counts, seconds=round(time.monotonic() - began, 1), **measure)
        return counts

    def _night_queue(self, root: Path, counts: dict) -> None:
        """1. the `night` queue, by priority then the person's order: each drafted (its plan and autostart follow)."""
        waiting = [i for i in ideas.ideas(root) if (st := ideas.state(self.state_dir, i["slug"]))["state"] == "raw"
                   and ideas.queue_of(st) == "night" and not self.busy(i["slug"])]
        for n, i in enumerate(sorted(waiting, key=_rank)):
            if self._reserved() or self.hold(i["slug"]):
                counts["held"] += len(waiting) - n
                return
            if self._sync(i["slug"], "drafting", lambda s=i["slug"]: self.draft_one(s)):
                counts["drafted"] += 1

    def _night_starts(self, root: Path, counts: dict) -> None:
        """2. the plans passed to start at night."""
        rows = [i for i in sorted(ideas.ideas(root), key=_rank)
                if (p := ideas.plan(self.state_dir, i["slug"])) and p.get("passed_at") and p.get("start_at") == "night"
                and ideas.state(self.state_dir, i["slug"])["state"] == "plan"]
        for n, i in enumerate(rows):
            if self._reserved():
                counts["held"] += len(rows) - n
                return
            try:
                if self.start_night(i["slug"]):
                    counts["started"] += 1
            except Exception:                     # one plan that cannot start never stops the night
                pass

    def goal_paths(self, root: Path, g: dict) -> list[str]:
        """The repository paths a goal reads: its links, and the paths its Summary names, that exist."""
        named = [m.group(1) for m in _PATH.finditer(g.get("summary") or "")]
        out = []
        for p in list(g.get("links") or []) + named:
            p = str(p).split("#")[0].strip().strip("`").lstrip("/")
            if p and "://" not in p and (self.repo_root / p).exists():
                out.append(p.rstrip("/"))
        return list(dict.fromkeys(out))

    def changed_since(self, commit: str) -> list[str] | None:
        """`git diff --name-only <commit>..HEAD`; None when it cannot be read."""
        from orkboard.realm.idea_git import _git
        if not re.fullmatch(r"[0-9a-f]{7,40}", commit or ""):
            return None
        try:
            proc = _git(self.repo_root, "diff", "--name-only", f"{commit}..HEAD")
        except Exception:
            return None
        return [x.strip() for x in proc.stdout.splitlines() if x.strip()] if proc.returncode == 0 else None

    def _night_refresh(self, root: Path, counts: dict) -> None:
        """3. a goal whose paths changed since its `read_at` is read again (balance, quality)."""
        if self.pick("refresh") is None:
            return
        for g in ideas.tracks(root, make=False):
            if g["slug"] == ideas.GENERAL:
                continue
            changed = self.changed_since(ideas.goal_state(self.state_dir, g["slug"])["read_at"])
            paths = self.goal_paths(root, g)
            if not changed or not any(c == p or c.startswith(p + "/") for c in changed for p in paths):
                continue
            if self._reserved() or self.window_until() is not None:
                counts["held"] += 1
                return
            hit = [c for c in changed if any(c == p or c.startswith(p + "/") for p in paths)]
            if self._sync(g["slug"], "goal", lambda s=g["slug"], h=hit: self.read_goal_one(s, "", "refresh", h), f"goal:{g['slug']}"):
                counts["refreshed"] += 1

    # -- proposals (§8) -----------------------------------------------------------------------------------------

    def commits_since(self, commit: str) -> str:
        from orkboard.realm.idea_git import _git
        args = ["log", "--oneline", f"-{COMMITS_READ}"] + ([f"{commit}..HEAD"] if re.fullmatch(r"[0-9a-f]{7,40}", commit or "") else [])
        try:
            proc = _git(self.repo_root, *args)
        except Exception:
            return ""
        return proc.stdout.strip() if proc.returncode == 0 else ""

    def propose_prompt(self, root: Path, n: int) -> str:
        """§0's `propose` context: each goal's title and its Summary's first line, its ideas' titles and states, the
        declined titles, at most 50 commit subjects. It reads no file."""
        goals = []
        for g in ideas.tracks(root, make=False):
            if g["slug"] == ideas.GENERAL:
                continue
            mine = "\n".join(f"  - {i['title']} ({ideas.state(self.state_dir, i['slug'])['state']})" for i in ideas.ideas(root, g["slug"]))
            goals.append(f"- {g['slug']}: {g['title']} — {ideas.thesis(g['summary']) or ideas.thesis(g['about'])}\n{mine or '  (no idea yet)'}")
        no = "\n".join(f"- {d['title']} (goal {d['goal']})" + (f": {d['reason']}" if d["reason"] else "") for d in declined(self.state_dir))
        st = self.night_state()
        since = st.get("head") if st.get("key") != self.night_key(time.time()) else st.get("head_before", "")
        subjects = "\n".join(line.split(" ", 1)[-1] for line in self.commits_since(since or "").splitlines())
        context = idea_target.cut([("The goals and their ideas", "\n".join(goals)),
                                   ("Proposals the person turned down (never propose these again)", no),
                                   ("The commits since the last night", subjects)], idea_target.CONTEXT["propose"])
        return f"""You are the keeper of this project's Task board. It is night: propose up to {n} new ideas the person
may want to take in the morning, each under one of the goals. {self.reads("propose", [])}

{context}Answer with one JSON object and nothing else:
{{"proposals": [{{"goal": "a goal's slug", "title": "a short title", "why": "two lines: why it moves the goal"}}]}}
"""

    def _night_proposals(self, root: Path, counts: dict) -> None:
        """4. up to N proposals by the Target, never more than 3 waiting in all."""
        kw = _kw()
        waiting = sum(1 for i in ideas.ideas(root) if ideas.state(self.state_dir, i["slug"])["state"] == "proposed")
        n = min(idea_target.PROPOSALS[self.target()], idea_target.MAX_WAITING - waiting)
        if n <= 0 or self.pick("propose") is None:
            return
        if self._reserved() or self.window_until() is not None:
            counts["held"] += 1
            return
        try:
            self._tls.slug = "night-proposals"
            text, *_rest = self.ask("propose", self.propose_prompt(root, n), tools=False)
        except Exception:                          # a night that cannot propose proposes nothing
            counts["measure"] = self.measure()
            return
        counts["measure"] = self.measure()
        answer = kw.first_json(text) or {}
        goals = {g["slug"] for g in ideas.tracks(root, make=False)} - {ideas.GENERAL}
        no = {d["title"].lower() for d in declined(self.state_dir, 1000)}
        for raw in answer.get("proposals") if isinstance(answer.get("proposals"), list) else []:
            if counts["proposed"] >= n or not isinstance(raw, dict):
                continue
            goal, title, why = kw._words(raw.get("goal"), 60), " ".join(kw._words(raw.get("title"), 120).split()), kw._words(raw.get("why"), 600)
            if goal not in goals or not title or not why or title.lower() in no:
                continue
            slug = ideas.add_idea(root, why, goal, self.state_dir)
            with ideas.LOCK:
                page = ideas.idea_page(root, slug)
                page.title = title
                ideas._write(root / ideas.IDEAS / f"{slug}.md", page.text())
                ideas._reindex(root)
            ideas.save_state(self.state_dir, slug, state="proposed", queue="")
            self._ev(event_log.PROPOSAL_MADE, idea=slug, goal=goal)
            self.publish(slug)
            counts["proposed"] += 1
