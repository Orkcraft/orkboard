"""Your parties (docs/specs/43-party-measured.md §6): parties the person saved from a goal, kept in their own folder and
picked for a goal in any project, as Operations are (decisions §51.1): `parties.json` beside the machine's settings
(`~/.config/orkcraft/parties.json`), written whole and atomically, mode 600, never in a repository.

    save("Lean web", "engineering", "architect", ["grunt", "tester"], ["reviewer"], own)    # its id; a taken name refused
    save(..., replace=True)              # the party of that name (whatever its case) is written over, its id and uses kept
    carry(state_dir, "architect", team)  # `own` for a save: the members that are neither the library's nor built in
    list() · drop(id) · used(id, project, name, goal) · mark(project, goal, met, party=None)
    install(state_dir, own)              # a party's own agents made roles of a project: (installed names, names kept as they were)
    project_id(repo_root)                # 12 hex: sha1 of the project's path

A file of another shape reads as none and is not overwritten until a save. No face, no model.
"""
from __future__ import annotations

import builtins
import datetime as dt
import hashlib
import json
import re
import secrets
import threading
from pathlib import Path

from orkboard import settings
from orkboard.realm import library, op_runs, roles

MAX, NAME_CHARS, MAX_USES = 12, 40, 50
LOCK = threading.RLock()
_LIST = builtins.list                      # `list()` below is the contract's name for the person's parties


def path() -> Path:
    return settings.path().parent / "parties.json"


def project_id(repo_root: Path | str) -> str:
    return hashlib.sha1(str(Path(repo_root)).encode("utf-8")).hexdigest()[:12]


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _slugs(value: object) -> list[str]:
    return [s for s in value if isinstance(s, str) and re.fullmatch(r"[a-z0-9-]{1,60}", s)] if isinstance(value, _LIST) else []


def _own(value: object) -> list[dict]:
    out = []
    for o in value if isinstance(value, _LIST) else []:
        if not isinstance(o, dict) or not _slugs([o.get("slug")]):
            continue
        out.append({"slug": o["slug"], "name": " ".join(str(o.get("name") or o["slug"]).split())[:roles.NAME_CHARS],
                    "craft": o.get("craft") if o.get("craft") in roles.CRAFTS else roles.DEFAULT_CRAFT,
                    "model": o.get("model") if isinstance(o.get("model"), str) else "",
                    "max_parallel": o.get("max_parallel") if isinstance(o.get("max_parallel"), int) else 2,
                    "instruction": str(o.get("instruction") or "")[:roles.INSTRUCTION_CHARS],
                    "takes": [k for k in o.get("takes") or [] if k in roles.TASK_KINDS] if isinstance(o.get("takes"), _LIST) else []})
    return out


def _uses(value: object) -> list[dict]:
    out = []
    for u in value if isinstance(value, _LIST) else []:
        if isinstance(u, dict) and isinstance(u.get("project"), str) and isinstance(u.get("goal"), str):
            out.append({"project": u["project"], "name": str(u.get("name") or "")[:100], "goal": u["goal"],
                        "at": str(u.get("at") or ""), "met": u["met"] if isinstance(u.get("met"), bool) else None})
    return out[-MAX_USES:]


def _party(p: object) -> dict | None:
    if not isinstance(p, dict) or not isinstance(p.get("id"), str) or not isinstance(p.get("name"), str) or not p["name"].strip():
        return None
    return {"id": p["id"], "name": p["name"], "craft": p.get("craft") if p.get("craft") in roles.CRAFTS else roles.DEFAULT_CRAFT,
            "leader": p["leader"] if isinstance(p.get("leader"), str) and p["leader"] else roles.TASKMASTER,
            "team": _slugs(p.get("team")), "every": _slugs(p.get("every")), "own": _own(p.get("own")),
            "saved": str(p.get("saved") or ""), "uses": _uses(p.get("uses"))}


def _read() -> list[dict]:
    try:
        raw = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, dict) or raw.get("v") != 1 or not isinstance(raw.get("parties"), _LIST):
        return []
    return [p for p in map(_party, raw["parties"]) if p is not None]


def _write(parties: list[dict]) -> None:
    op_runs.write(path(), json.dumps({"v": 1, "parties": parties}, indent=1) + "\n")


def list() -> list[dict]:                                                                      # noqa: A001 (the contract's name)
    """The person's parties, in the order they were saved."""
    with LOCK:
        return _read()


def get(party_id: str) -> dict | None:
    return next((p for p in _read() if p["id"] == party_id), None)


def carry(state_dir: Path, leader: str, team: list[str]) -> list[dict]:
    """`own` for a save: every member (the leader too) that is neither a library agent nor built in, as its role file says it, with the task types the project gives it (they are what it takes)."""
    out, kinds = [], roles.kinds(state_dir)
    for slug in dict.fromkeys([leader, *team]):
        if slug in roles.BUILTIN or library.get(slug) is not None or (r := roles.role(state_dir, slug)) is None:
            continue
        out.append({k: r[k] for k in ("slug", "name", "craft", "model", "max_parallel", "instruction")} | {"takes": [k for k in roles.TASK_KINDS if k in roles.takes_of(r, kinds)]})
    return _own(out)


def save(name: str, craft: str, leader: str, team: list[str], every: list[str], own: list[dict], replace: bool = False) -> str:
    """The party kept; its id. A name is 1 to 40 characters, unique whatever its case: a taken one is refused unless `replace`
    (the party of that name is written over, its id and uses kept); at most MAX parties."""
    name = " ".join(str(name or "").split())
    if not 1 <= len(name) <= NAME_CHARS:
        raise ValueError(f"A party's name is 1 to {NAME_CHARS} characters")
    if craft not in roles.CRAFTS:
        raise ValueError("A party has a craft")
    with LOCK:
        parties = _read()
        same = next((p for p in parties if p["name"].lower() == name.lower()), None)
        if same is not None and not replace:
            raise ValueError(f"You have a party named “{same['name']}”")
        if same is None and len(parties) >= MAX:
            raise ValueError(f"You have {MAX} parties: remove one first")
        kept = {"name": name, "craft": craft, "leader": leader or roles.TASKMASTER, "team": _slugs(team),
                "every": [s for s in _slugs(every) if s in team], "own": _own(own), "saved": _now()}
        if same is not None:
            parties[parties.index(same)] = {**same, **kept}
            _write(parties)
            return same["id"]
        pid = f"p-{secrets.token_hex(4)}"
        _write([*parties, {"id": pid, **kept, "uses": []}])
        return pid


def drop(party_id: str) -> None:
    with LOCK:
        parties = _read()
        if not any(p["id"] == party_id for p in parties):
            raise ValueError("That party is gone")
        _write([p for p in parties if p["id"] != party_id])


def used(party_id: str, project: str, name: str, goal: str) -> None:
    """A goal of a project picked the party: one use a goal (asked again, it is new); the oldest beyond MAX_USES dropped."""
    with LOCK:
        parties = _read()
        p = next((x for x in parties if x["id"] == party_id), None)
        if p is None:
            return
        p["uses"] = [u for u in p["uses"] if (u["project"], u["goal"]) != (project, goal)]
        p["uses"] = [*p["uses"], {"project": project, "name": name, "goal": goal, "at": _now(), "met": None}][-MAX_USES:]
        _write(parties)


def mark(project: str, goal: str, met: bool, party: str | None = None) -> None:
    """The goal was accepted: its use of a party (`party`: the one it has, else any) says whether it was met (the last verdict)."""
    with LOCK:
        parties, changed = _read(), False
        for p in parties:
            if party is not None and p["id"] != party:
                continue
            for u in p["uses"]:
                if (u["project"], u["goal"]) == (project, goal):
                    u["met"], changed = bool(met), True
        if changed:
            _write(parties)


def counts(p: dict) -> dict:
    """A party's record: `goals` (its uses), `projects` (the distinct ones among them), `met` (the uses accepted as met)."""
    return {"goals": len(p["uses"]), "projects": len({u["project"] for u in p["uses"]}), "met": sum(1 for u in p["uses"] if u["met"] is True)}


def install(state_dir: Path, own: list[dict], only: list[str] | None = None) -> tuple[list[str], list[str]]:
    """A party's own agents made roles of the project (`only`: these slugs): written as `roles.install` writes one, never over a
    role of that slug. Returns the names made and the names of roles the project had already (kept as they are)."""
    made, kept = [], []
    for o in own:
        if only is not None and o["slug"] not in only:
            continue
        if o["slug"] in roles.BUILTIN or roles.role(state_dir, o["slug"]) is not None:
            kept.append(o["name"])
            continue
        roles.install(state_dir, o["slug"], o["name"], o["model"], o["craft"], o["instruction"], tuple(o["takes"]), o["max_parallel"])
        made.append(o["name"])
    return made, kept
