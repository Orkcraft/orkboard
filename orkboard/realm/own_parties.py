"""The person's own parties (docs/specs/43-party-measured.md §6): a goal's party saved from its screen and picked again for a goal in any
project. Kept as Operations are (decisions §51.1), for every project: `parties.json` beside the machine's settings
(`~/.config/orkcraft/parties.json`), written whole and atomically, mode 600, never in a repository. No face, no model.

    own_parties.list()                                   # [{"id", "name", "craft", "leader", "team", "every", "own", "saved", "uses", "preset"?}]
    own_parties.save("Lean web", "engineering", "architect", ["grunt", "reviewer"], ["reviewer"], own=[])   # → its id
                                                         # `preset=`: the library's party it started from (spec 59), kept when given
    own_parties.drop(id)
    own_parties.used(id, project, name, goal)            # a goal that picked it
    own_parties.mark(project, goal, met)                 # the goal's leader accepted it (or not): the last verdict

`own`: every member (the leader too) that is neither a library agent nor built in, as its role file says it at the save; the Taskmaster
and the Grunt are never carried. A file of another shape reads as none and is not overwritten until a save.
"""
from __future__ import annotations

import builtins
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import threading
from pathlib import Path

from orkboard import settings

MAX = 12                            # parties
NAME_CHARS = 40
USES = 50                           # a party's uses kept, the oldest dropped
FILE = "parties.json"
OWN_KEYS = ("slug", "name", "craft", "model", "max_parallel", "instruction", "takes")
_LOCK = threading.RLock()


class OwnPartyError(ValueError):
    """A save or a drop the file refuses, in plain words."""


def path() -> Path:
    return settings.path().parent / FILE


def project_key(project: Path | str) -> str:
    """A project as a saved party's uses name it: 12 hex of the sha1 of its path (as the tabs' keys are)."""
    return hashlib.sha1(str(project).encode()).hexdigest()[:12]


def _read() -> dict | None:
    """The file as it is; None when it is missing, broken or of another shape."""
    try:
        data = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("v") == 1 and isinstance(data.get("parties"), builtins.list) else None


def _write(parties: list[dict]) -> None:
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps({"v": 1, "parties": parties}, ensure_ascii=False, indent=1) + "\n")
        os.replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def list() -> builtins.list[dict]:                                  # noqa: A001 — the spec's name
    """The parties kept, in the order they were saved."""
    return [p for p in (_read() or {}).get("parties", []) if isinstance(p, dict) and re.fullmatch(r"p-[0-9a-f]{8}", str(p.get("id") or ""))]


def get(party_id: str) -> dict | None:
    return next((p for p in list() if p["id"] == party_id), None)


def _slugs(rows: object) -> builtins.list[str]:
    return [str(s) for s in rows if isinstance(s, str)] if isinstance(rows, (builtins.list, tuple)) else []


def _own(rows: object) -> builtins.list[dict]:
    return [{k: r.get(k) for k in OWN_KEYS if k in r} for r in (rows if isinstance(rows, (builtins.list, tuple)) else []) if isinstance(r, dict) and r.get("slug")]


def save(name: str, craft: str, leader: str, team: object, every: object, own: object = (), replace: bool = False, preset: str = "") -> str:
    """The party kept under its name: its id. A taken name (whatever its case) is refused unless `replace`, which keeps the party's id and
    its uses; a thirteenth party is refused. `preset`: the id of the library's party it started from (spec 59), kept as the one optional key
    `preset` when it is one (a file without it reads as before)."""
    name = " ".join(str(name or "").split())
    if not 1 <= len(name) <= NAME_CHARS:
        raise OwnPartyError(f"Name the party in 1 to {NAME_CHARS} characters")
    with _LOCK:
        parties = list()
        same = next((p for p in parties if str(p.get("name") or "").lower() == name.lower()), None)
        if same is not None and not replace:
            raise OwnPartyError(f"You have a party named “{same['name']}”")
        if same is None and len(parties) >= MAX:
            raise OwnPartyError(f"You have {MAX} parties: remove one first")
        row = {"id": same["id"] if same else f"p-{secrets.token_hex(4)}", "name": name, "craft": str(craft or ""), "leader": str(leader or "taskmaster"),
               "team": _slugs(team), "every": _slugs(every), "own": _own(own), "saved": dt.datetime.now().isoformat(timespec="seconds"),
               "uses": (same or {}).get("uses") or [], **({"preset": preset} if re.fullmatch(r"[a-z][a-z-]{0,29}", str(preset or "")) else {})}
        _write([row if p is same else p for p in parties] if same else [*parties, row])
    return row["id"]


def drop(party_id: str) -> None:
    with _LOCK:
        parties = list()
        if not any(p["id"] == party_id for p in parties):
            raise OwnPartyError("That party is gone")
        _write([p for p in parties if p["id"] != party_id])


def used(party_id: str, project: str, name: str, goal: str) -> None:
    """A goal of a project picked the party: a use (the goal's earlier use of it, in the same project, is replaced), at most USES."""
    with _LOCK:
        parties = list()
        got = next((p for p in parties if p["id"] == party_id), None)
        if got is None:
            return
        earlier = [u for u in got.get("uses") or [] if u.get("project") == project and u.get("goal") == goal]
        uses = [u for u in got.get("uses") or [] if not (u.get("project") == project and u.get("goal") == goal)]
        uses.append({"project": project, "name": str(name)[:100], "goal": goal, "at": dt.datetime.now().isoformat(timespec="seconds"),
                     "met": earlier[-1].get("met") if earlier else None})
        got["uses"] = uses[-USES:]
        _write(parties)


def mark(project: str, goal: str, met: bool, party_id: str = "") -> None:
    """The goal was accepted (or not) by its leader: the last verdict, on its use of the party the goal has now (asked again, the later
    one); without `party_id` every use of the goal."""
    with _LOCK:
        parties = list()
        hit = False
        for p in parties:
            if party_id and p.get("id") != party_id:
                continue
            for u in p.get("uses") or []:
                if u.get("project") == project and u.get("goal") == goal:
                    u["met"], hit = bool(met), True
        if hit:
            _write(parties)
