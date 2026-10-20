"""The lens a new idea is written with (decisions §53): beside its text — always there, and enough alone —, what the person
points at in the way of the goal's party. An engineer's lens points at parts of the repository (realm/code_map.py) with a
note; a designer's at a screen of the app, with areas marked on it and a note for each; a product manager's at whom it is for
and what hurts them (a segment and its pain). The goal's leader's lens is open first; the party's others are a tap away;
a lens no one in the party has is not offered.

    lenses(state_dir, root, "ship")      # {"lenses": [{"id": "text"}, {"id": "code", "by": "Architect", ...}], "default": "code"}
    clean(state_dir, [{"kind": "pain", "segment": "Shop owners", "pain": "Orders get lost"}])   # checked, a screen kept
    save(state_dir, "dark-mode", got); read(state_dir, "dark-mode")
    attached(state_dir, "dark-mode")     # for a keeper's prompt: the photos, then what the lens pointed at

Kept beside the idea's state (`<state_dir>/ideas/<slug>/lens.json`). A screen is kept for the project
(`<state_dir>/screens/`), so the next idea picks it again; a segment and its pains too (`<state_dir>/segments.json`).
No face, no model.
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from orkboard.hooks.warder import is_secret
from orkboard.realm import goal_team, idea_photos, ideas, library, roles

LENSES = {"engineering": "code", "design": "screen", "product": "pain"}   # a craft's lens; the others write text
ORDER = ("text", "code", "screen", "pain")
MAX_ATTACHED = 4
MAX_PATHS = 12
MAX_MARKS = 8
MAX_SEGMENTS = 40
MAX_PAINS = 20
HIDDEN = {".git", ".orkcraft"}


def _words(v: object, n: int) -> str:
    return " ".join(str(v or "").split())[:n]


def _craft(state_dir: Path, slug: str) -> tuple[str, str]:
    """An agent's craft and name: the project's role, else the library's."""
    r = roles.role(state_dir, slug)
    a = library.get(slug)
    craft = (r or {}).get("craft") or (a.craft if a else "") or roles.DEFAULT_CRAFT
    return craft, (r or {}).get("name") or (a.name if a else slug)


def lenses(state_dir: Path, root: Path, goal: str) -> dict:
    """The lenses a goal's party offers, in ORDER, and the one open first: its leader's (text with the Taskmaster)."""
    leader = goal_team.leader_of(root, goal) if goal else roles.TASKMASTER
    party = [leader, *goal_team.team_of(root, goal)] if goal else []
    by: dict[str, dict] = {}
    for slug in party:
        if slug == roles.TASKMASTER:
            continue
        craft, name = _craft(state_dir, slug)
        lens = LENSES.get(craft)
        if lens and lens not in by:
            by[lens] = {"id": lens, "by": name, "slug": slug}
    first = "text"
    if leader != roles.TASKMASTER:
        first = LENSES.get(_craft(state_dir, leader)[0], "text")
    return {"lenses": [{"id": "text"}, *(by[k] for k in ORDER if k in by)], "default": first if first in by else "text"}


# -- what a project keeps: its segments and pains, its screens -----------------------------------------------------

def _segments_file(state_dir: Path) -> Path:
    return Path(state_dir) / "segments.json"


def segments(state_dir: Path) -> list[dict]:
    got = ideas._json(_segments_file(state_dir)) or {}
    out = []
    for s in got.get("segments") or []:
        if isinstance(s, dict) and _words(s.get("segment"), 120):
            out.append({"segment": _words(s["segment"], 120), "pains": [_words(p, 300) for p in s.get("pains") or [] if _words(p, 300)]})
    return out


def keep_segment(state_dir: Path, segment: str, pain: str) -> None:
    """A segment and its pain kept for the next idea: the latest first."""
    if not segment:
        return
    with ideas.LOCK:
        got = segments(state_dir)
        mine = next((s for s in got if s["segment"].lower() == segment.lower()), None)
        if mine is None:
            mine = {"segment": segment, "pains": []}
        got = [mine] + [s for s in got if s is not mine]
        if pain:
            mine["pains"] = [pain] + [p for p in mine["pains"] if p.lower() != pain.lower()]
            mine["pains"] = mine["pains"][:MAX_PAINS]
        ideas._write_json(_segments_file(state_dir), {"segments": got[:MAX_SEGMENTS]})


def _screens_dir(state_dir: Path) -> Path:
    return Path(state_dir) / "screens"


def screens(state_dir: Path) -> list[dict]:
    """The project's screens, the latest first: {id, name, path} (the path relative to the repository)."""
    got = ideas._json(_screens_dir(state_dir) / "screens.json") or {}
    out = []
    for s in got.get("screens") or []:
        p = _screens_dir(state_dir) / f"{s.get('id')}.{s.get('ext')}"
        if isinstance(s, dict) and p.is_file():
            out.append({"id": s["id"], "name": s.get("name") or "A screen", "path": p.relative_to(Path(state_dir).parent).as_posix()})
    return out


def keep_screen(state_dir: Path, raw: bytes, name: str) -> str:
    """A screen kept for the project (the same picture kept once); its id."""
    ext = idea_photos._kind(raw)
    sid = hashlib.sha1(raw).hexdigest()[:12]
    with ideas.LOCK:
        d = _screens_dir(state_dir)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{sid}.{ext}").write_bytes(raw)
        got = ideas._json(d / "screens.json") or {}
        old = [s for s in got.get("screens") or [] if isinstance(s, dict) and s.get("id") != sid]
        ideas._write_json(d / "screens.json", {"screens": [{"id": sid, "ext": ext, "name": name or "A screen"}, *old][:40]})
    return sid


def screen_data(state_dir: Path, sid: str) -> dict | None:
    """A kept screen as a face shows it: {id, name, type, data (base64)}; None when there is none."""
    s = next((x for x in screens(state_dir) if x["id"] == sid), None)
    if s is None:
        return None
    raw = (Path(state_dir).parent / s["path"]).read_bytes()
    kind = idea_photos._kind(raw)
    return {"id": sid, "name": s["name"], "type": f"image/{'jpeg' if kind == 'jpg' else kind}", "data": base64.b64encode(raw).decode()}


# -- an idea's attachments -------------------------------------------------------------------------------------------

def _unit(v: object) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("A mark is a place on the screen") from None
    return round(min(1.0, max(0.0, x)), 4)


def _path_ok(root: Path, rel: str) -> bool:
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts or any(x in HIDDEN for x in p.parts) or is_secret(rel):
        return False
    return rel == "." or (root / p).exists()


def clean(state_dir: Path, raw: object, repo: Path | None = None) -> list[dict]:
    """What the lens pointed at, checked (ValueError says plainly what is wrong); a new screen is kept. `repo`: where a
    part pointed at must be (the state dir's parent by default)."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("What the lens points at is a list")
    if len(raw) > MAX_ATTACHED:
        raise ValueError(f"At most {MAX_ATTACHED} things go with an idea")
    root = Path(repo) if repo is not None else Path(state_dir).parent
    out = []
    for a in raw:
        kind = a.get("kind") if isinstance(a, dict) else None
        if kind == "pain":
            segment, pain = _words(a.get("segment"), 120), _words(a.get("pain"), 300)
            if not segment and not pain:
                continue
            out.append({"kind": "pain", "segment": segment, "pain": pain})
        elif kind == "code":
            paths = [p for p in (a.get("paths") or []) if isinstance(p, str)][:MAX_PATHS]
            if not paths:
                continue
            bad = [p for p in paths if not _path_ok(root, p)]
            if bad:
                raise ValueError(f"Not a part of the repository: {bad[0]}")
            out.append({"kind": "code", "paths": paths, "note": _words(a.get("note"), 1000)})
        elif kind == "screen":
            sid = _words(a.get("screen"), 40)
            if isinstance(a.get("image"), dict):
                raw_img = idea_photos.decode([a["image"]])[0]
                sid = keep_screen(state_dir, raw_img, _words(a.get("name"), 60))
            if not sid or not any(s["id"] == sid for s in screens(state_dir)):
                raise ValueError("That screen is gone")
            marks = []
            for m in (a.get("marks") or [])[:MAX_MARKS]:
                if not isinstance(m, dict):
                    continue
                x, y, w, h = (_unit(m.get(k)) for k in ("x", "y", "w", "h"))
                if w <= 0 or h <= 0:
                    continue
                marks.append({"x": x, "y": y, "w": min(w, 1 - x), "h": min(h, 1 - y), "note": _words(m.get("note"), 300)})
            out.append({"kind": "screen", "screen": sid, "marks": marks, "note": _words(a.get("note"), 1000)})
        else:
            raise ValueError("A lens points at code, a screen or a pain")
    return out


def _file(state_dir: Path, slug: str) -> Path:
    return Path(state_dir) / "ideas" / slug / "lens.json"


def save(state_dir: Path, slug: str, got: list[dict]) -> None:
    if not got:
        return
    with ideas.LOCK:
        ideas._write_json(_file(state_dir, slug), {"lens": got})
        for a in got:
            if a["kind"] == "pain":
                keep_segment(state_dir, a["segment"], a["pain"])


def read(state_dir: Path, slug: str) -> list[dict]:
    """What the lens pointed at, as kept; a screen with its name and path."""
    got = (ideas._json(_file(state_dir, slug)) or {}).get("lens") or []
    shown = {s["id"]: s for s in screens(state_dir)}
    return [a | ({"name": shown[a["screen"]]["name"], "path": shown[a["screen"]]["path"]} if a.get("kind") == "screen" and a.get("screen") in shown else {})
            for a in got if isinstance(a, dict)]


def _pct(v: float) -> str:
    return f"{round(v * 100)} %"


def prompt_lines(state_dir: Path, slug: str) -> str:
    """For a keeper's prompt: what the person pointed at with the lens ("" with nothing)."""
    rows = []
    for a in read(state_dir, slug):
        if a["kind"] == "code":
            rows.append(f"- These parts of the repository (read them first): {', '.join(a['paths'])}"
                        + (f". What to change there: {a['note']}" if a["note"] else ""))
        elif a["kind"] == "screen" and a.get("path"):
            marks = "; ".join(f"{n}) from {_pct(m['x'])} to {_pct(m['x'] + m['w'])} across and {_pct(m['y'])} to "
                              f"{_pct(m['y'] + m['h'])} down" + (f": {m['note']}" if m["note"] else "")
                              for n, m in enumerate(a["marks"], 1))
            rows.append(f"- The screen \"{a['name']}\" ({a['path']}: look at it first)"
                        + (f", with areas marked (from its top left corner): {marks}" if marks else "")
                        + (f". {a['note']}" if a["note"] else ""))
        elif a["kind"] == "pain":
            rows.append(f"- Whom it is for: {a['segment'] or 'not said'}; what hurts them: {a['pain'] or 'not said'}")
    return ("The person pointed with the lens of the goal's party; keep to it:\n" + "\n".join(rows) + "\n") if rows else ""


def attached(state_dir: Path, slug: str) -> str:
    """Everything that came with the idea's text, for a keeper's prompt: its photos, then what the lens pointed at."""
    return idea_photos.prompt_lines(state_dir, slug) + prompt_lines(state_dir, slug)
