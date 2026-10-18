"""What the board's model calls cost, kept with their idea, and added up (docs/specs/36-agents-spend.md §1, §2, §6).

    idea_spend.append(state_dir, idea_spend.line("plan", "taskmaster", ...), idea="dark-mode")   # one call's line
    idea_spend.of_idea(state_dir, "dark-mode")     # {"usd", "unpriced", "stages": {...}, "tasks": {...}}
    idea_spend.of_goal(state_dir, "speed", ["dark-mode", ...])   # its own lines and its ideas', with $ a merged task
    idea_spend.by_role(state_dir, days=7)          # {role: {"spent", "merged", "first_time", "finished", ...}}
    idea_spend.tier_costs(state_dir)               # $ a task per tier: the mean of the last 20 that ran on it

**The ledger** (§1): one JSON line per call, appended where its work lives — a keeper call on an idea or a task's turn
in `<state_dir>/ideas/<slug>/spend.jsonl`, on a goal in `<state_dir>/goals/<slug>/spend.jsonl`, the night's proposals
in `<state_dir>/ideas/spend-board.jsonl`; a deleted idea's lines move to `<state_dir>/ideas/spend-gone.jsonl` with
how its tasks ended, so the week keeps what it cost. A line: `at, step, task?, round?, role, tool, model, tier,
effort, tokens {in, out, cache_read, cache_write}, cost` — `cost` is the tool's $ at API prices, `None` when unpriced,
never 0; a token count the tool's reader does not split apart is `None` (`total` then holds the sum it gave).
Appending never troubles the work: a disk that refuses is ignored.

**The rollup** (§2): code, no model. A sum of priced lines is $; a sum of only unpriced lines is `None` (shown *—*).
No face.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

STAGES = ("goal", "spec", "plan", "work", "rework", "dropped")
STEP_STAGE = {"goal": "goal", "refresh": "goal", "draft": "spec", "answer": "spec", "talk": "spec", "plan": "plan"}
TOKEN_KEYS = ("in", "out", "cache_read", "cache_write")
FILE = "spend.jsonl"
BOARD, GONE = "spend-board.jsonl", "spend-gone.jsonl"
LEARN_LAST = 20                    # a tier's cost is the mean of the board's last 20 finished tasks on it (§6)
TOO_FEW = 3                        # $ a merged result is said from 3 merged on
CACHE_S = 60.0
_SLUG = re.compile(r"[a-z0-9-]+")
_LOCK = threading.Lock()
_CACHE: dict[tuple[str, int], tuple[float, dict]] = {}


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _num(value: object) -> float | int | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def tokens_of(usage: object = None, total: object = None) -> dict:
    """The line's tokens: a split usage ({"in", "out", "cache_read"[, "cache_write"]}) as it is, else only the
    total the tool gave (`total`), each count it did not split `None`."""
    out: dict[str, Any] = {k: None for k in TOKEN_KEYS}
    if isinstance(usage, dict):
        out.update({k: _num(usage.get(k)) for k in TOKEN_KEYS})
    if all(v is None for v in out.values()) and _num(total) is not None:
        out["total"] = total
    return out


def line(step: str, role: str, tool: str, model: str, tier: str, effort: str, tokens: dict | None, cost: object,
         task: str = "", round: int | None = None, at: str = "") -> dict:
    row: dict[str, Any] = {"at": at or _now(), "step": step}
    if task:
        row.update(task=task, round=int(round or 1))
    row.update(role=role, tool=tool, model=model, tier=tier, effort=effort or "", tokens=tokens or tokens_of(),
               cost=_num(cost))
    return row


def ledger(state_dir: Path, idea: str = "", goal: str = "") -> Path | None:
    """Where a line goes: its idea's, its goal's, else the board's own (the night's proposals); None for a name
    that is not a slug."""
    name = idea or goal
    if name and not _SLUG.fullmatch(name):
        return None
    if idea:
        return Path(state_dir) / "ideas" / idea / FILE
    if goal:
        return Path(state_dir) / "goals" / goal / FILE
    return Path(state_dir) / "ideas" / BOARD


def append(state_dir: Path, row: dict, idea: str = "", goal: str = "") -> bool:
    """One line appended; False when nothing was written (a bad name, a disk that refused)."""
    target = ledger(state_dir, idea, goal)
    if target is None:
        return False
    try:
        with _LOCK:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        return False
    return True


def task_line(state_dir: Path, slug: str, task: dict, step: str, tool: str, model: str, cost: object,
              tokens: object) -> bool:
    """A task's turn (`task` in its round, `fix` for the gate's retry inside it), as the runner has it."""
    return append(state_dir, line(step, str(task.get("role") or "grunt"), tool, model,
                                  str(task.get("ran_tier") or task.get("tier") or ""), str(task.get("effort") or ""),
                                  tokens_of(None, tokens), cost, str(task.get("id") or ""), task.get("round")), idea=slug)


def read(path: Path) -> list[dict]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    rows = []
    for raw in text.splitlines():
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _plan(state_dir: Path, slug: str) -> dict:
    try:
        data = json.loads((Path(state_dir) / "ideas" / slug / "plan.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _tasks(plan: dict) -> dict[str, dict]:
    return {str(t.get("id")): t for t in plan.get("tasks") or [] if isinstance(t, dict)}


def keep_gone(state_dir: Path, slug: str) -> None:
    """Before an idea's folder goes (`ideas.drop`): its lines to `spend-gone.jsonl`, each with its idea and, for a
    task's, how the task ended (`ended`, `finished`, `last_round`)."""
    if not _SLUG.fullmatch(slug or ""):
        return
    rows = read(Path(state_dir) / "ideas" / slug / FILE)
    if not rows:
        return
    tasks = _tasks(_plan(state_dir, slug))
    out = []
    for row in rows:
        row = {**row, "idea": slug}
        if (t := tasks.get(str(row.get("task") or ""))) is not None:
            row.update(ended=t.get("state") or "", finished=t.get("finished") or "", last_round=int(t.get("round") or 1))
        out.append(row)
    try:
        with _LOCK, (Path(state_dir) / "ideas" / GONE).open("a", encoding="utf-8") as f:
            f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
    except OSError:
        pass


# -- the rollup ---------------------------------------------------------------------------------------

def usd(rows: list[dict]) -> float | None:
    """The priced lines' $; None when every line is unpriced; 0 when there is none."""
    priced = [c for r in rows if (c := _num(r.get("cost"))) is not None]
    if rows and not priced:
        return None
    return round(sum(priced), 4)


def _tokens(rows: list[dict]) -> int:
    n = 0
    for r in rows:
        t = r.get("tokens") if isinstance(r.get("tokens"), dict) else {}
        split = [v for k in TOKEN_KEYS if (v := _num(t.get(k))) is not None]
        n += int(sum(split)) if split else int(_num(t.get("total")) or 0)
    return n


def _stage(row: dict, failed: bool) -> str:
    step = str(row.get("step") or "")
    if step in STEP_STAGE:
        return STEP_STAGE[step]
    if step not in ("task", "fix"):
        return ""
    if failed:
        return "dropped"
    return "work" if step == "task" and int(row.get("round") or 1) <= 1 else "rework"


def _split(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """A task's lines apart: round 1's own turns (work), and the rounds after with the gate's retries (rework)."""
    work = [r for r in rows if r.get("step") == "task" and int(r.get("round") or 1) <= 1]
    return work, [r for r in rows if r not in work]


def _stages(rows: list[dict], failed: Callable[[dict], bool]) -> dict[str, dict]:
    by: dict[str, list[dict]] = {s: [] for s in STAGES}
    for r in rows:
        if stage := _stage(r, failed(r)):
            by[stage].append(r)
    return {s: {"usd": usd(rs), "tokens": _tokens(rs), "calls": len(rs)} for s, rs in by.items()}


def of_idea(state_dir: Path, slug: str) -> dict:
    """{"usd", "unpriced", "stages": {stage: {"usd", "tokens", "calls"}}, "tasks": {tid: {"usd", "work", "rework"}}}:
    a task that ended `failed` (dropped or failed) counts in *dropped*, not in work or rework."""
    rows = read(Path(state_dir) / "ideas" / slug / FILE) if _SLUG.fullmatch(slug or "") else []
    tasks = _tasks(_plan(state_dir, slug))
    failed = {tid for tid, t in tasks.items() if t.get("state") == "failed"}
    per: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("step") in ("task", "fix") and r.get("task"):
            per.setdefault(str(r["task"]), []).append(r)
    split = {}
    for tid, rs in per.items():
        work, rework = _split(rs)
        split[tid] = {"usd": usd(rs), "work": usd(work), "rework": usd(rework)}
    return {"usd": usd(rows), "unpriced": sum(1 for r in rows if _num(r.get("cost")) is None),
            "stages": _stages(rows, lambda r: str(r.get("task") or "") in failed), "tasks": split}


def of_goal(state_dir: Path, slug: str, idea_slugs: list[str] | tuple = ()) -> dict:
    """Its own lines (stage *goal*) and its ideas' stages summed (`idea_slugs`: the goal's ideas, as the face reads
    them from the pages), with `merged` (its tasks merged) and `usd_per_merged`."""
    own = read(Path(state_dir) / "goals" / slug / FILE) if _SLUG.fullmatch(slug or "") else []
    rows, failed, merged = list(own), set(), 0
    for idea in idea_slugs:
        if not _SLUG.fullmatch(idea or ""):
            continue
        tasks = _tasks(_plan(state_dir, idea))
        merged += sum(1 for t in tasks.values() if t.get("state") == "merged")
        for r in read(Path(state_dir) / "ideas" / idea / FILE):
            rows.append(r)
            if (tasks.get(str(r.get("task") or "")) or {}).get("state") == "failed":
                failed.add(id(r))
    total = usd(rows)
    return {"usd": total, "unpriced": sum(1 for r in rows if _num(r.get("cost")) is None),
            "stages": _stages(rows, lambda r: id(r) in failed), "merged": merged,
            "usd_per_merged": round(total / merged, 4) if merged and total is not None else None}


def _all_lines(state_dir: Path) -> list[dict]:
    """Every ledger's lines, each with its idea (the board's and the goals' with none)."""
    base = Path(state_dir)
    rows = [{**r, "idea": "", "board": True} for r in read(base / "ideas" / BOARD)]
    rows += read(base / "ideas" / GONE)
    for path in sorted((base / "ideas").glob(f"*/{FILE}")):
        rows += [{**r, "idea": path.parent.name} for r in read(path)]
    for path in sorted((base / "goals").glob(f"*/{FILE}")):
        rows += [{**r, "idea": ""} for r in read(path)]
    return rows


def _finished(state_dir: Path, gone: list[dict]) -> dict[tuple[str, str], dict]:
    """(idea, task) → {"state", "finished", "round", "role"} of every task that ended (merged or failed): the plans'
    and the deleted ideas' (from their lines in `spend-gone.jsonl`)."""
    out = {}
    for path in sorted((Path(state_dir) / "ideas").glob("*/plan.json")):
        for tid, t in _tasks(_plan(state_dir, path.parent.name)).items():
            if t.get("state") in ("merged", "failed"):
                out[(path.parent.name, tid)] = {"state": t["state"], "finished": str(t.get("finished") or ""),
                                                "round": int(t.get("round") or 1), "role": str(t.get("role") or "grunt")}
    for r in gone:
        key = (str(r.get("idea") or ""), str(r.get("task") or ""))
        if r.get("ended") in ("merged", "failed") and key[1] and key not in out:
            out[key] = {"state": r["ended"], "finished": str(r.get("finished") or ""),
                        "round": int(r.get("last_round") or 1), "role": str(r.get("role") or "grunt")}
    return out


def by_role(state_dir: Path, days: int = 7) -> dict[str, dict]:
    """{role: {"spent", "merged", "first_time", "finished", "usd_per_merged"}} over the tasks that ended in the last
    `days`; the Taskmaster's row: its own lines' $ (`spent`), the plans it made, and `first_time` / `finished` over
    every task of its plans, whoever did them. Cached for 60 s."""
    key, now = (str(Path(state_dir).resolve()), int(days)), time.monotonic()
    with _LOCK:
        hit = _CACHE.get(key)
    if hit is not None and now - hit[0] < CACHE_S:
        return hit[1]
    since = (dt.datetime.now() - dt.timedelta(days=days)).isoformat(timespec="seconds")
    rows = _all_lines(state_dir)
    ended = {k: t for k, t in _finished(state_dir, [r for r in rows if "ended" in r]).items() if t["finished"] >= since}
    per: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        if r.get("step") in ("task", "fix") and r.get("task"):
            per.setdefault((str(r.get("idea") or ""), str(r["task"])), []).append(r)
    out: dict[str, dict] = {}
    for k, t in ended.items():
        row = out.setdefault(t["role"], {"lines": [], "merged": 0, "first_time": 0, "finished": 0})
        row["lines"] += per.get(k, [])
        row["finished"] += 1
        row["merged"] += t["state"] == "merged"
        row["first_time"] += t["state"] == "merged" and t["round"] <= 1
    for row in out.values():
        spent = usd(row.pop("lines"))
        row["spent"] = spent
        row["usd_per_merged"] = round(spent / row["merged"], 4) if row["merged"] >= TOO_FEW and spent is not None else None
    mine = [r for r in rows if r.get("role") == "taskmaster" and str(r.get("at") or "") >= since]
    out["taskmaster"] = {"spent": usd(mine), "plans": sum(1 for r in mine if r.get("step") == "plan"),
                         "first_time": sum(1 for t in ended.values() if t["state"] == "merged" and t["round"] <= 1),
                         "finished": len(ended), "merged": sum(1 for t in ended.values() if t["state"] == "merged")}
    with _LOCK:
        _CACHE[key] = (now, out)
    return out


def forget() -> None:
    """The cache of `by_role` cleared (a test, or a change the person should see at once)."""
    with _LOCK:
        _CACHE.clear()


# -- the estimate that learns (§6) and Review's cost against it (§4) -----------------------------------

def tier_costs(state_dir: Path, last: int = LEARN_LAST) -> dict[str, float]:
    """$ a task per tier: the mean cost of the board's last `last` finished tasks (merged or failed) that ran on
    it (`ran_tier`), else `plans.DEFAULT_COST`."""
    from orkcraft.realm import plans
    runs: dict[str, list[tuple[str, float]]] = {}
    for path in sorted((Path(state_dir) / "ideas").glob("*/plan.json")):
        for t in _tasks(_plan(state_dir, path.parent.name)).values():
            cost = _num(t.get("cost"))
            if t.get("state") in ("merged", "failed") and t.get("ran_tier") and cost is not None:
                runs.setdefault(str(t["ran_tier"]), []).append((str(t.get("finished") or ""), float(cost)))
    out = dict(plans.DEFAULT_COST)
    for tier, got in runs.items():
        if tier in out and got:
            newest = [c for _at, c in sorted(got, reverse=True)[:last]]
            out[tier] = sum(newest) / len(newest)
    return out


def estimate_of(task: dict, costs: dict[str, float]) -> dict:
    """A result's planned share: the learned cost of the tier it ran on, ±50 % ({"low", "high"})."""
    from orkcraft.realm import plans
    tier = str(task.get("ran_tier") or task.get("tier") or "warrior")
    base = costs.get(tier, plans.DEFAULT_COST.get(tier, plans.DEFAULT_COST["warrior"]))
    return {"low": round(base * 0.5, 2), "high": round(base * 1.5, 2)}


def over(cost: object, estimate: dict) -> float | None:
    """`cost / high`, to one place, when the cost is over the estimate's high end; else None."""
    cost, high = _num(cost), _num(estimate.get("high"))
    return round(cost / high, 1) if cost is not None and high and cost > high else None
