"""A goal's route across parties (docs/specs/67-release-and-route.md §2, decisions §81.2–§81.4): where it came from, where it is, where it
went. Read from what the Board keeps (the pitch a goal was sent from, its flag, the releases it went into) and one small file beside its
state, `<state_dir>/ideas/<slug>/route.json` (`{"moved": [{from, to, at, by}]}`, the last 20). A goal moves to another party only before
its work starts (`move`).

    route(root, state_dir, "dark-mode")        # [{step, party, goal, at, …}], oldest first; [] for a goal with only its party step
    move(root, state_dir, "dark-mode", "web")  # to another party: refused once a task has run; else recorded and moved (realm/ideas.py `move`)
    started(state_dir, "dark-mode")            # whether its work has started
    goal_state(root, state_dir, "pitch")       # a sent pitch's goal: its party, state, tasks, flag and release (`dropped` when it is gone)

The steps: `pitch` {answer, word, title}, `moved` {from, to} (its `party` is the one it was moved from), `party` {state, done, total},
`main` {by}, `release` {version, out}; each has `step`, `party`, `goal` (the slug a press opens) and `at`. The faces word them. No face, no model.
"""
from __future__ import annotations

import re
from pathlib import Path

from orkboard.realm import idea_flag, ideas, pitches, releases

FILE = "route.json"
KEEP = 20                                # the moves kept
RUNNING = ("waiting", "ready")           # a task in these has not run
STARTED = "Its work has started in {party}: a goal moves only before its work starts. Add a new goal there."


def _path(state_dir: Path, slug: str) -> Path:
    return ideas.state_folder(state_dir, slug) / FILE


def moves(state_dir: Path, slug: str) -> list[dict]:
    """The moves kept, oldest first: `{from, to, at, by}`."""
    try:
        got = (ideas._json(_path(state_dir, slug)) or {}).get("moved")
    except ValueError:
        return []
    return [{k: str(m.get(k) or "") for k in ("from", "to", "at", "by")} for m in got if isinstance(m, dict)][-KEEP:] if isinstance(got, list) else []


def started(state_dir: Path, slug: str, st: dict | None = None, plan: dict | None = None) -> bool:
    """Whether the goal's work has started: its plan passed, a task past waiting and ready, or it is working or done."""
    st = st or ideas.state(state_dir, slug)
    plan = plan if plan is not None else ideas.plan(state_dir, slug)
    return (st["state"] in ("working", "done") or bool((plan or {}).get("passed_at"))
            or any(t.get("state") not in (*RUNNING, None) for t in (plan or {}).get("tasks") or []))


def move(root: Path, state_dir: Path, slug: str, to: str | None = None, before: str | None = None, by: str = "") -> dict:
    """The goal to another party and/or before another goal (`ideas.move`). To another party it is refused once its work has started
    (ValueError, STARTED), else recorded in `route.json`. Within its party (its order) nothing is recorded. `{from, to, moved}`."""
    with ideas.LOCK:
        page = ideas.idea_page(root, slug)
        if page is None:
            raise ValueError(f"No goal {slug!r}")
        was = page.get("track") or ideas.GENERAL
        now = to or was
        if now != was and started(state_dir, slug):
            names = {t["slug"]: t["title"] for t in ideas.tracks(root, make=False)}
            raise ValueError(STARTED.format(party=names.get(was, was)))
        ideas.move(root, slug, to, before, by=by)
        if now != was:
            row = {"from": was, "to": now, "at": ideas._now(), "by": by}
            ideas._write_json(_path(state_dir, slug), {"moved": [*moves(state_dir, slug), row][-KEEP:]})
    return {"from": was, "to": now, "moved": now != was}


def _tasks(plan: dict | None) -> tuple[int, int]:
    tasks = (plan or {}).get("tasks") or []
    return sum(1 for t in tasks if t.get("state") == "merged"), len(tasks)


def steps(root: Path, state_dir: Path, slug: str, page: ideas.Page | None = None, st: dict | None = None, plan: dict | None = None,
          held: dict | None = None) -> list[dict]:
    """Every step of the route, its `party` step among them (`route` leaves a route of that alone out). `page`, `st`, `plan` and `held`
    (`releases.holding`) when the caller has them read."""
    page = page or ideas.idea_page(root, slug)
    st = st or ideas.state(state_dir, slug)
    plan = plan if plan is not None else ideas.plan(state_dir, slug)
    held = releases.holding(root, state_dir) if held is None else held
    party = (page.get("track") if page is not None else "") or ideas.GENERAL
    out = []
    src = str(st.get("from_pitch") or "")
    if re.fullmatch(r"[a-z0-9-]+", src) and (pitch := ideas.idea_page(root, src)) is not None:
        j = pitches.read(state_dir, src)
        answer = str((j["decision"] or {}).get("answer") or "")
        out.append({"step": "pitch", "party": pitch.get("track") or ideas.GENERAL, "goal": src, "at": j["judged_at"], "answer": answer,
                    "word": pitches.ANSWER_WORDS.get(answer, ""), "title": pitch.title or src})
    out += [{"step": "moved", "party": m["from"], "goal": slug, "at": m["at"], "from": m["from"], "to": m["to"]} for m in moves(state_dir, slug)]
    done, total = _tasks(plan)
    out.append({"step": "party", "party": party, "goal": slug, "at": (moves(state_dir, slug) or [{"at": ""}])[-1]["at"],
                "state": st["state"], "done": done, "total": total})
    if (flag := idea_flag.flag_of(state_dir, slug)) is not None:
        out.append({"step": "main", "party": party, "goal": slug, "at": flag["at"], "by": flag.get("by") or ""})
    out += [{"step": "release", "at": r["out"] or r["at"], **releases.step_of(r)} for r in held.get(slug, [])]
    return out


def route(root: Path, state_dir: Path, slug: str, **read) -> list[dict]:
    """A goal's route, oldest first (§2.1); [] for a goal with only its `party` step (the faces draw nothing). `read`: `steps`' reads."""
    got = steps(root, state_dir, slug, **read)
    return got if len(got) > 1 else []


def goal_state(root: Path, state_dir: Path, pitch: str, held: dict | None = None) -> dict | None:
    """What became of the goal a pitch was sent (§2.4): `{goal, party, state, done, total, flag, release}`; `flag` its date ("" before),
    `release` the last release that holds it (`{goal, party, version, out}`) or None. A goal dropped since: `state: "dropped"`, nothing
    else. None for a pitch not sent."""
    sent = pitches.read(state_dir, pitch)["sent"]
    goal = str((sent or {}).get("goal") or "") if isinstance(sent, dict) else ""
    if not goal:
        return None
    page = ideas.idea_page(root, goal)
    if page is None:
        return {"goal": goal, "party": "", "state": "dropped", "done": 0, "total": 0, "flag": "", "release": None}
    held = releases.holding(root, state_dir) if held is None else held
    done, total = _tasks(ideas.plan(state_dir, goal))
    flag = idea_flag.flag_of(state_dir, goal)
    mine = held.get(goal) or []
    return {"goal": goal, "party": page.get("track") or ideas.GENERAL, "state": ideas.state(state_dir, goal)["state"], "done": done,
            "total": total, "flag": flag["at"] if flag else "", "release": releases.step_of(mine[-1]) if mine else None}
