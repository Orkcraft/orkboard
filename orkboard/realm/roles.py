"""The agents' roles and the task types (spec 34 §3, decisions §46): a role is a name, a model, an instruction and
how many may work at once; each task type is given one role.

    roles(state_dir)                       # the roles, the built-in two first
    save(state_dir, "Docs scribe", "warrior", 2, "Write plainly.")      # its slug
    drop(state_dir, "docs-scribe")         # its task types go back to Grunt
    kinds(state_dir)                       # {"code": "grunt", "tests": "grunt", …}
    set_kind(state_dir, "docs", "docs-scribe")
    role_for(state_dir, "docs")            # the role a task of that type runs as

One small file per role, `<state_dir>/roles/<slug>.md` (front matter `name, model, max_parallel`; the body is the
instruction), so it is seen and undone by hand; the types' roles are `<state_dir>/roles/kinds.json`. **Taskmaster**
(the keeper) and **Grunt** (the default worker) exist by themselves: they can be edited, not deleted.

A role is who; the Target is how much thinking (spec 36 §3): a model is "" **By Target** (the task's own tier,
shifted by the Target; every role but the Taskmaster, and a new agent's default) or a tier (`elder · warrior ·
laborer`); the Taskmaster picks a tier only. A file that names another model (written before, or by hand) keeps it
and runs it (`hand_set`). An instruction is at most 600 characters; a longer one in its file goes to the ork cut at
its last sentence end (`instruction`, the file's whole text in `instruction_long`) until the person saves. An agent
takes its task types (`save(..., takes=[...])`); Grunt takes what no other agent takes.

No face, no model.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import threading
from pathlib import Path

from orkboard.realm import ideas

TASKMASTER, GRUNT = "taskmaster", "grunt"
BUILTIN = (TASKMASTER, GRUNT)
TASK_KINDS = ("code", "tests", "docs", "text", "research")
KIND_LABELS = {"code": "Code", "tests": "Tests", "docs": "Docs", "text": "Text for people", "research": "Research"}
DEFAULT_KIND = "code"
MAX_PARALLEL = (1, 8)
NAME_CHARS, INSTRUCTION_CHARS = 40, 600
READ_CHARS = 4000                  # of an instruction written before spec 36, the most a read keeps
TIERS = ("elder", "warrior", "laborer")
_DEFAULTS = {
    TASKMASTER: {"name": "Taskmaster", "model": "elder", "max_parallel": 1, "instruction": ""},
    GRUNT: {"name": "Grunt", "model": "", "max_parallel": 8, "instruction": ""},
}
LOCK = threading.RLock()


def folder(state_dir: Path) -> Path:
    return Path(state_dir) / "roles"


def models(current: str = "") -> list[dict]:
    """What a role may run on: {"id", "label"} — By Target, then the three tiers with the harness's model small;
    `current`, a model set by hand in a role's file, as one more option for that role."""
    from orkboard.realm import harnesses
    h = harnesses.get("claude")
    out = [{"id": "", "label": "By Target"}]
    out += [{"id": t, "label": t.capitalize() + (f" · {h.models[t]}" if h and t in h.models else "")} for t in TIERS]
    if current and current not in TIERS:
        out.append({"id": current, "label": f"{current} (set by hand)"})
    return out


def hand_set(r: dict) -> bool:
    """Whether a role's model was set by hand (a model, not By Target or a tier)."""
    return bool(r.get("model")) and r.get("model") not in TIERS


def _model(value: object, slug: str | None, old: dict | None) -> str:
    """By Target (not the Taskmaster's), a tier, or the model the role's file names already (kept, never changed
    silently)."""
    value = str(value or "").strip()
    if value in TIERS or (value == "" and slug != TASKMASTER):
        return value
    if old is not None and value and value == old.get("model") and re.fullmatch(r"[\w.\[\]-]{1,60}", value):
        return value
    raise ValueError("The Taskmaster runs on a tier: pick one" if slug == TASKMASTER and not value
                     else "Pick a model from the list")


def for_prompt(text: str) -> str:
    """An instruction as it goes to the ork: at most 600 characters, cut at its last sentence end within them."""
    text = text.strip()
    if len(text) <= INSTRUCTION_CHARS:
        return text
    head = text[:INSTRUCTION_CHARS + 1]
    ends = [m.end() for m in re.finditer(r"[.!?…](?=\s|$)", head) if m.end() <= INSTRUCTION_CHARS]
    return head[:ends[-1]].strip() if ends else text[:INSTRUCTION_CHARS].strip()


def _clean_parallel(value: object) -> int:
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError("At most how many at once is a number from 1 to 8") from None
    if not MAX_PARALLEL[0] <= n <= MAX_PARALLEL[1]:
        raise ValueError("At most how many at once is a number from 1 to 8")
    return n


def _path(state_dir: Path, slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", slug or ""):
        raise ValueError(f"No agent {slug!r}")
    return folder(state_dir) / f"{slug}.md"


def _read(state_dir: Path, slug: str) -> dict | None:
    try:
        text = _path(state_dir, slug).read_text(encoding="utf-8").replace("\r\n", "\n")
    except (OSError, ValueError):
        return None
    page = ideas.parse(text)
    base = _DEFAULTS.get(slug, {"name": slug, "model": "", "max_parallel": 1, "instruction": ""})
    try:
        mp = int(page.get("max_parallel") or base["max_parallel"])
    except ValueError:
        mp = base["max_parallel"]
    body = (text[m.end():] if (m := ideas._FENCE.match(text)) else text).strip()[:READ_CHARS]
    return {"slug": slug, "name": page.get("name") or base["name"], "model": page.get("model", base["model"]),
            "max_parallel": min(max(mp, MAX_PARALLEL[0]), MAX_PARALLEL[1]), "instruction": for_prompt(body),
            "instruction_long": body if len(body) > INSTRUCTION_CHARS else "", "builtin": slug in BUILTIN}


def role(state_dir: Path, slug: str) -> dict | None:
    got = _read(state_dir, slug)
    if got is None and slug in _DEFAULTS:
        return {"slug": slug, **_DEFAULTS[slug], "instruction_long": "", "builtin": True}
    return got


def roles(state_dir: Path) -> list[dict]:
    """The built-in two, then the person's, by name."""
    out = [role(state_dir, s) for s in BUILTIN]
    mine = []
    for path in sorted(folder(state_dir).glob("*.md")) if folder(state_dir).is_dir() else []:
        if path.stem not in BUILTIN and (r := _read(state_dir, path.stem)) is not None:
            mine.append(r)
    return out + sorted(mine, key=lambda r: (r["name"].lower(), r["slug"]))


def _write(state_dir: Path, r: dict) -> None:
    page = ideas.Page([("name", r["name"]), ("model", r["model"]), ("max_parallel", str(r["max_parallel"]))])
    text = page.text() + (f"\n{r['instruction'].strip()}\n" if r["instruction"].strip() else "")
    ideas._write(_path(state_dir, r["slug"]), text)


def save(state_dir: Path, name: str, model: object, max_parallel: object, instruction: object = "",
         slug: str | None = None, takes: list[str] | None = None) -> str:
    """A role made or edited. A new one keeps the name it is given; the built-in two keep their names too (editable).
    `takes`: the task types it takes (a type another agent had moves here, one unticked goes back to Grunt); None
    leaves them as they are. Grunt takes what no other agent takes and the Taskmaster takes none: refused."""
    name = " ".join(str(name or "").split())[:NAME_CHARS]
    if not name:
        raise ValueError("An agent needs a name")
    text = str(instruction or "").replace("\r\n", "\n").strip()
    if len(text) > INSTRUCTION_CHARS:
        raise ValueError(f"An instruction is at most {INSTRUCTION_CHARS} characters")
    if takes and slug in BUILTIN:
        raise ValueError("Grunt takes what no other agent takes" if slug == GRUNT
                         else "The Taskmaster plans, it does not do tasks: pick a Grunt or an agent of your own")
    if bad := [k for k in takes or [] if k not in TASK_KINDS]:
        raise ValueError(f"No task type {bad[0]!r}")
    with LOCK:
        old = None
        if slug:
            old = role(state_dir, slug)
            if old is None:
                raise ValueError(f"No agent {slug!r}")
        else:
            taken = {r["slug"] for r in roles(state_dir)}
            base = ideas.slugify(name) if ideas.slugify(name) not in BUILTIN else f"{ideas.slugify(name)}-2"
            slug, n = base, 2
            while slug in taken or slug in BUILTIN:
                slug, n = f"{base}-{n}", n + 1
        if any(r["name"].lower() == name.lower() and r["slug"] != slug for r in roles(state_dir)):
            raise ValueError(f"There is an agent called {name} already")
        _write(state_dir, {"slug": slug, "name": name, "model": _model(model, slug, old),
                           "max_parallel": _clean_parallel(max_parallel), "instruction": text})
        if takes is not None and slug not in BUILTIN:
            _save_kinds(state_dir, {k: slug if k in takes else (GRUNT if r == slug else r)
                                    for k, r in kinds(state_dir).items()})
    return slug


def drop(state_dir: Path, slug: str) -> list[str]:
    """A role the person made goes; the task types it had go back to Grunt (returned)."""
    if slug in BUILTIN:
        raise ValueError("Taskmaster and Grunt can be edited, not deleted")
    with LOCK:
        if _read(state_dir, slug) is None:
            raise ValueError(f"No agent {slug!r}")
        back = [k for k, r in kinds(state_dir).items() if r == slug]
        _path(state_dir, slug).unlink(missing_ok=True)
        if back:
            _save_kinds(state_dir, {**kinds(state_dir), **{k: GRUNT for k in back}})
    return back


def kinds(state_dir: Path) -> dict[str, str]:
    """{task type: role slug}, every type named; a type whose role is gone is Grunt's."""
    try:
        raw = json.loads((folder(state_dir) / "kinds.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    raw = raw if isinstance(raw, dict) else {}
    known = {r["slug"] for r in roles(state_dir)}
    return {k: (raw.get(k) if raw.get(k) in known and raw.get(k) != TASKMASTER else GRUNT) for k in TASK_KINDS}


def _save_kinds(state_dir: Path, data: dict) -> None:
    ideas._write(folder(state_dir) / "kinds.json", json.dumps(data, indent=1) + "\n")


def set_kind(state_dir: Path, kind: str, slug: str) -> None:
    if kind not in TASK_KINDS:
        raise ValueError(f"No task type {kind!r}")
    with LOCK:
        if role(state_dir, slug) is None:
            raise ValueError(f"No agent {slug!r}")
        if slug == TASKMASTER:
            raise ValueError("The Taskmaster plans, it does not do tasks: pick a Grunt or an agent of your own")
        _save_kinds(state_dir, {**kinds(state_dir), kind: slug})


def role_for(state_dir: Path, kind: str) -> dict:
    """The role a task of this type runs as (a task without a known type is code)."""
    kind = kind if kind in TASK_KINDS else DEFAULT_KIND
    return role(state_dir, kinds(state_dir)[kind]) or role(state_dir, GRUNT)


def spend_today(tasks: list[tuple[str, dict]]) -> dict[str, float]:
    """{role slug: today's cost} of (role, task) pairs whose task was started today."""
    today, out = dt.date.today().isoformat(), {}
    for slug, t in tasks:
        if str(t.get("started") or "").startswith(today) and isinstance(t.get("cost"), (int, float)):
            out[slug] = round(out.get(slug, 0.0) + float(t["cost"]), 4)
    return out
