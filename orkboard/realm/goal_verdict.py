"""A goal's verdict (decisions §53): when its ideas are done, its leader accepts it against its metrics — met or not, each
metric's status with why, and what to do next. Kept beside the goal's state (`<state_dir>/goals/<slug>/verdict.json`).

    save(state_dir, "ship", {"met": False, "verdict": "…", "metrics": [...], "next": [...]}, by="Product manager")
    read(state_dir, "ship")      # the verdict as kept, None before the first

No face, no model.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from orkboard.realm import ideas

STATUSES = ("met", "not met", "unknown")
MAX_NEXT = 3


def clean(answer: object) -> dict:
    """The leader's answer, strictly: met (bool), the verdict in words, each metric's status and why, the next ideas."""
    a = answer if isinstance(answer, dict) else {}
    words = lambda v, n: " ".join(str(v or "").split())[:n]                 # noqa: E731
    metrics = []
    for m in a.get("metrics") if isinstance(a.get("metrics"), list) else []:
        if isinstance(m, dict) and words(m.get("name"), 200):
            status = str(m.get("status") or "").lower()
            metrics.append({"name": words(m.get("name"), 200), "status": status if status in STATUSES else "unknown",
                            "why": words(m.get("why"), 400)})
    nxt = [words(x, 200) for x in a.get("next") if isinstance(x, str) and x.strip()][:MAX_NEXT] if isinstance(a.get("next"), list) else []
    return {"met": a.get("met") is True, "verdict": words(a.get("verdict"), 1200), "metrics": metrics[:8], "next": nxt}


def save(state_dir: Path, slug: str, answer: object, by: str = "") -> dict:
    got = {**clean(answer), "by": by, "at": dt.datetime.now().isoformat(timespec="seconds")}
    with ideas.LOCK:
        ideas._write_json(ideas.goal_folder(state_dir, slug) / "verdict.json", got)
    return got


def read(state_dir: Path, slug: str) -> dict | None:
    got = ideas._json(ideas.goal_folder(state_dir, slug) / "verdict.json")
    return got if isinstance(got, dict) else None
