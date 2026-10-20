"""The night's proposal to take a checker out of a goal's party (docs/specs/43-party-measured.md §4.2): a checker whose
newest eight checks in a goal all ended clean in round 1 is proposed to be taken out (it spares money). Code decides, no
model is called. No face.

    party_proposals.night(root, state_dir)        # the proposals made now: [(goal, checker, runs)]
    party_proposals.rows(root, state_dir)         # Needs you's `party` rows
    party_proposals.decline(state_dir, goal, by, reason)

Kept: `<state_dir>/goals/<slug>/party-proposal.json` (one per goal) and `party-declined.jsonl` (a decline each).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from orkboard.realm import goal_team, goal_verdict, ideas, library, party_work, roles

PROPOSAL, DECLINED = "party-proposal.json", "party-declined.jsonl"
MAX_DECLINES = 200


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def proposal(state_dir: Path, goal: str) -> dict | None:
    got = ideas._json(ideas.goal_folder(state_dir, goal) / PROPOSAL)
    return got if isinstance(got, dict) and isinstance(got.get("by"), str) and got["by"] else None


def remove(state_dir: Path, goal: str) -> None:
    try:
        (ideas.goal_folder(state_dir, goal) / PROPOSAL).unlink()
    except OSError:
        pass


def declines(state_dir: Path, goal: str) -> list[dict]:
    """The declines of a goal, the oldest first: {by, at, reason}."""
    try:
        lines = (ideas.goal_folder(state_dir, goal) / DECLINED).read_text(encoding="utf-8").splitlines()[-MAX_DECLINES:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append({k: str(row.get(k) or "") for k in ("by", "at", "reason")})
    return out


def decline(state_dir: Path, goal: str, by: str, reason: str = "") -> None:
    path = ideas.goal_folder(state_dir, goal) / DECLINED
    row = {"by": by, "at": _now(), "reason": " ".join(str(reason or "").split())[:300]}
    with ideas.LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _name(state_dir: Path, by: str) -> str:
    r = roles.role(state_dir, by)
    a = library.get(by)
    return r["name"] if r else (a.name if a is not None else by)


def night(root: Path, state_dir: Path) -> list[tuple[str, str, int]]:
    """Propose, for each goal with a party, no met verdict and no proposal waiting, the first checker of its party whose
    newest `QUIET_RUN` checks in the goal all ended clean in round 1, unless the goal declined it since the newest of them.
    Returns [(goal, checker, runs)] of the proposals kept now."""
    made = []
    for g in ideas.tracks(root, make=False):
        goal = g["slug"]
        team = goal_team.team_of(root, goal)
        if not team or proposal(state_dir, goal) is not None or (goal_verdict.read(state_dir, goal) or {}).get("met") is True:
            continue
        for by in team:
            a = library.get(by)
            if a is None or a.check is None:
                continue
            quiet = party_work.quiet_run(root, state_dir, goal, by)
            if quiet is None or any(d["by"] == by and d["at"] >= quiet["at"] for d in declines(state_dir, goal)):
                continue
            with ideas.LOCK:
                ideas._write_json(ideas.goal_folder(state_dir, goal) / PROPOSAL,
                                  {"by": by, "runs": party_work.QUIET_RUN, "usd": quiet["usd"], "at": _now()})
            made.append((goal, by, party_work.QUIET_RUN))
            break                                   # one waiting per goal
    return made


def rows(root: Path, state_dir: Path) -> list[dict]:
    """Needs you's `party` rows: a proposal kept for a goal that still has the checker in its party."""
    out = []
    for g in ideas.tracks(root, make=False):
        got = proposal(state_dir, g["slug"])
        if got is None:
            continue
        if got["by"] not in goal_team.team_of(root, g["slug"]):
            remove(state_dir, g["slug"])            # the party changed since: nothing to take out
            continue
        name, usd = _name(state_dir, got["by"]), got.get("usd")
        text = f"It found nothing in the last {int(got.get('runs') or party_work.QUIET_RUN)} ideas"
        text += f"; a check costs about ${float(usd):.2f}." if isinstance(usd, (int, float)) else "."
        out.append({"idea": "", "goal": g["slug"], "kind": "party", "by": got["by"], "title": f"Take {name} out of {g['title']}'s party?",
                    "text": text, "priority": g["priority"], "blocks": False, "at": str(got.get("at") or "")})
    return out
