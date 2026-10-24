"""The agents' roles and the task types (spec 34 §3, decisions §46): a role is a name, a model, an instruction and
how many may work at once; each task type is given one role.

    roles(state_dir)                       # the roles, the built-in two first
    save(state_dir, "Docs scribe", "warrior", 2, "Write plainly.")      # its slug
    drop(state_dir, "docs-scribe")         # its task types go back to Grunt
    kinds(state_dir)                       # {"code": "grunt", "tests": "grunt", …}
    set_kind(state_dir, "docs", "docs-scribe")
    role_for(state_dir, "docs")            # the role a task of that type runs as

One small file per role, `<state_dir>/roles/<slug>.md` (front matter `name, model, max_parallel, craft`; the body is the
instruction), so it is seen and undone by hand; the types' roles are `<state_dir>/roles/kinds.json`. **Taskmaster**
(the keeper) and **Grunt** (the default worker) exist by themselves: they can be edited, not deleted.

A role is who; the Target is how much thinking (spec 36 §3): a model is "" **By Target** (the task's own tier,
shifted by the Target; every role but the Taskmaster, and a new agent's default) or a tier (`elder · warrior ·
laborer`); the Taskmaster picks a tier only. A file that names another model (written before, or by hand) keeps it
and runs it (`hand_set`). An instruction is at most 600 characters; a longer one in its file goes to the ork cut at
its last sentence end (`instruction`, the file's whole text in `instruction_long`) until the person saves. An agent
takes its task types (`save(..., takes=[...])`); Grunt takes what no other agent takes.

A role's **craft** is what its work is (decisions §53): engineering, design, data or marketing; the page draws it as the
head of its race in orkUI (an ork, an elf, a goblin, a gnome: `RACES`), wearing its tier's gear (`head_tier`). Taskmaster
and Grunt are orks: engineering, always. A file without a craft is engineering.

    head(r, "balance")                     # {"craft": "design", "race": "elf", "tier": "elder"}: the head a role wears (a role's own `race`,
                                           # front matter, when orkUI's copy has its head at that tier: spec 68 §1.3)
    task_head(state_dir, task, "thrift")   # the head of the role a task runs (or will run) as, at the tier it runs at
    known(state_dir)                       # (roles by slug, kinds): read once, handed to many task_head calls

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
# A task's kind is its tag: the kind of work it is, what decides who of a goal's team does it (realm/library.py).
TASK_KINDS = ("code", "tests", "docs", "text", "research", "review", "architecture", "design", "uikit", "a11y", "art",
              "data", "query", "metrics", "experiment", "seo", "campaign", "community", "security", "datacheck", "edit",
              "gamedesign", "level", "sound", "playtest", "aso")
KIND_LABELS = {"code": "Code", "tests": "Tests", "docs": "Docs", "text": "Text for people", "research": "Research",
               "review": "Review of a change", "architecture": "Architecture", "design": "Screens and flows",
               "uikit": "UI kit", "a11y": "Accessibility", "art": "Pixel art", "data": "Data pipelines and tables",
               "query": "Queries", "metrics": "Metrics", "experiment": "Experiments", "seo": "Search (SEO)",
               "campaign": "Launch and campaigns", "community": "Community", "security": "Security check",
               "datacheck": "Data check", "edit": "Editing", "gamedesign": "Game design", "level": "Levels",
               "sound": "Sound", "playtest": "Playtest", "aso": "Store pages (ASO)"}
# What each kind is, for the Taskmaster's plan prompt.
KIND_LINES = {"code": "the code a change needs", "tests": "tests only", "docs": "the repository's docs",
              "text": "text for people: pages, posts, release notes", "research": "finding out, no change",
              "review": "reading a change and saying what breaks", "architecture": "how a wide change is split and ordered",
              "design": "flows and screens", "uikit": "components and tokens of the design system",
              "a11y": "accessibility checks and fixes", "art": "pixel art: icons, heads, pictures",
              "data": "events, tables and the jobs that fill them", "query": "queries for a report",
              "metrics": "counting a party's metrics", "experiment": "an A/B test", "seo": "search: pages found by their words",
              "campaign": "a launch, its channels and what they bring", "community": "answers to people, what they ask",
              "security": "a security check of a change", "datacheck": "checking numbers and personal data",
              "edit": "editing texts people read", "gamedesign": "the rules, the loop and the balance of a game",
              "level": "a level: its layout, its path and its pace", "sound": "sounds and music, picked by ear",
              "playtest": "playing a change through and saying where it breaks or bores",
              "aso": "an app store's page: its keywords, texts and screenshots"}
DEFAULT_KIND = "code"
MAX_PARALLEL = (1, 8)
NAME_CHARS, INSTRUCTION_CHARS = 40, 600
READ_CHARS = 4000                  # of an instruction written before spec 36, the most a read keeps
TIERS = ("elder", "warrior", "laborer")
CRAFTS = ("engineering", "design", "data", "marketing", "product")
CRAFT_LABELS = {"engineering": "Engineering", "design": "Design", "data": "Data", "marketing": "Marketing", "product": "Product"}
# orkUI's race ids: ork, elf, goblin, gnome; product is the undead's (a mummy in Orkline 0.2: a lich until orkUI draws one)
RACES = {"engineering": "peon", "design": "elf", "data": "goblin", "marketing": "gnome", "product": "lich"}
# orkUI's copy of the races' heads (design/orkui.py): a role's own race (spec 68 §1.3) is worn only once its file is here.
RACE_FILES = Path(__file__).resolve().parents[1] / "design" / "system" / "orkui" / "races"
# What the built-in two are told already, beside the field that adds to it (spec 41 §8): their prompts are Orkboard's own.
TOLD = {
    TASKMASTER: "Each of its steps (reading a party, drafting a goal's spec, taking your answers, planning, the night's "
                "proposals) has its own prompt in Orkboard, with only what that step needs. What you write here goes "
                "before each step it runs; a party's leader, where it has one, runs that party's steps in its place.",
    GRUNT: "Every task's prompt says where it works (its own git worktree and branch), where the goal's spec is, its "
           "task and the tasks before it, the names of the secrets it may use, and that the gate then runs the critical "
           "tests and those of what it touched. Claude Code reads the project's CLAUDE.md itself. What you write here "
           "goes first.",
}
DEFAULT_CRAFT = "engineering"                    # the orks': Taskmaster's, Grunt's and every role's written before crafts
_DEFAULTS = {
    TASKMASTER: {"name": "Taskmaster", "model": "elder", "max_parallel": 1, "instruction": "", "craft": DEFAULT_CRAFT},
    GRUNT: {"name": "Grunt", "model": "", "max_parallel": 8, "instruction": "", "craft": DEFAULT_CRAFT},
}
LOCK = threading.RLock()


def folder(state_dir: Path) -> Path:
    return Path(state_dir) / "roles"


def models(current: str = "") -> list[dict]:
    """What a role may run on: {"id", "label"} — By Target, then the three tiers in today's words (Veteran, Seasoned,
    Novice: realm/lexicon.py) with the harness's model small;
    `current`, a model set by hand in a role's file, as one more option for that role."""
    from orkboard.realm import harnesses, tiers
    h = harnesses.get("claude")
    out = [{"id": "", "label": "By Target"}]
    out += [{"id": t, "label": tiers.TIER_LABELS[t] + (f" · {h.models[t]}" if h and t in h.models else "")} for t in TIERS]
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
    base = _DEFAULTS.get(slug, {"name": slug, "model": "", "max_parallel": 1, "instruction": "", "craft": DEFAULT_CRAFT})
    try:
        mp = int(page.get("max_parallel") or base["max_parallel"])
    except ValueError:
        mp = base["max_parallel"]
    body = (text[m.end():] if (m := ideas._FENCE.match(text)) else text).strip()[:READ_CHARS]
    return {"slug": slug, "name": page.get("name") or base["name"], "model": page.get("model", base["model"]),
            "max_parallel": min(max(mp, MAX_PARALLEL[0]), MAX_PARALLEL[1]), "instruction": for_prompt(body),
            "instruction_long": body if len(body) > INSTRUCTION_CHARS else "", "builtin": slug in BUILTIN,
            "craft": _craft(page.get("craft"), slug), "race": _race(page.get("race"), slug),
            "takes": [k for k in (page.get("takes") or "").split(",") if k.strip() in TASK_KINDS]}


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


def _craft(value: object, slug: str | None) -> str:
    """A role's craft as read: one of CRAFTS; the built-in two's, and anything unknown, engineering."""
    value = str(value or "").strip().lower()
    return value if value in CRAFTS and slug not in BUILTIN else DEFAULT_CRAFT


def _race(value: object, slug: str | None) -> str:
    """A role's own race as read: a word of lower-case letters ("" for none; the built-in two have none)."""
    value = str(value or "").strip().lower()
    return value if re.fullmatch(r"[a-z]{1,20}", value) and slug not in BUILTIN else ""


def own_race(race: str, craft: str, tier: str = "elder") -> str:
    """The race drawn for an agent: its own `race` when orkUI's copy has its head at that tier (`races/<race>-<tier>.png`), else its
    craft's (a lich for a skeleton until orkUI 0.5.0 is copied)."""
    craft = craft if craft in CRAFTS else DEFAULT_CRAFT
    if _race(race, None) and tier in TIERS and (RACE_FILES / f"{race}-{tier}.png").is_file():
        return race
    return RACES[craft]


def _write(state_dir: Path, r: dict) -> None:
    page = ideas.Page([("name", r["name"]), ("model", r["model"]), ("max_parallel", str(r["max_parallel"])),
                       ("craft", r.get("craft") or DEFAULT_CRAFT), *([("race", r["race"])] if r.get("race") else []),
                       *([("takes", ",".join(r["takes"]))] if r.get("takes") else [])])
    text = page.text() + (f"\n{r['instruction'].strip()}\n" if r["instruction"].strip() else "")
    ideas._write(_path(state_dir, r["slug"]), text)


def save(state_dir: Path, name: str, model: object, max_parallel: object, instruction: object = "",
         slug: str | None = None, takes: list[str] | None = None, craft: str | None = None) -> str:
    """A role made or edited. A new one keeps the name it is given; the built-in two keep their names too (editable).
    `takes`: the task types it takes (a type another agent had moves here, one unticked goes back to Grunt); None
    leaves them as they are. Grunt takes what no other agent takes and the Taskmaster takes none: refused. `craft`: one
    of CRAFTS (None keeps the role's, a new one's is engineering); Taskmaster and Grunt are orks, engineering only."""
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
    if craft is not None and craft not in CRAFTS:
        raise ValueError("A craft is engineering, design, data or marketing")
    if craft not in (None, DEFAULT_CRAFT) and slug in BUILTIN:
        raise ValueError("Taskmaster and Grunt are orks: their craft is engineering")
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
                           "max_parallel": _clean_parallel(max_parallel), "instruction": text,
                           "craft": craft or (old or {}).get("craft") or DEFAULT_CRAFT, "race": (old or {}).get("race") or "",
                           "takes": (old or {}).get("takes") or []})
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


def install(state_dir: Path, slug: str, name: str, model: str, craft: str, instruction: str, takes: tuple[str, ...], race: str = "") -> None:
    """A role from the library (realm/library.py), its slug given: written once, never over one that is there. `race`: the agent's own
    (spec 68 §1.3), kept in the file so `head` draws it."""
    with LOCK:
        if role(state_dir, slug) is not None or slug in BUILTIN:
            return
        _write(state_dir, {"slug": slug, "name": name, "model": model, "max_parallel": 2, "instruction": instruction,
                           "craft": craft, "race": _race(race, slug), "takes": [k for k in takes if k in TASK_KINDS]})


def install_own(state_dir: Path, own: dict) -> bool:
    """An agent of the person's own that a saved party carries (realm/own_parties.py), made a role of this project with its slug: written
    once, never over a role of that slug (the project's own stays as it is). True when it was written."""
    slug = str(own.get("slug") or "")
    name = " ".join(str(own.get("name") or "").split())[:NAME_CHARS]
    if not re.fullmatch(r"[a-z0-9-]{1,60}", slug) or slug in BUILTIN or not name:
        return False
    with LOCK:
        if _read(state_dir, slug) is not None:
            return False
        try:
            model = _model(own.get("model"), slug, None)
        except ValueError:
            model = ""
        try:
            many = _clean_parallel(own.get("max_parallel") or 2)
        except ValueError:
            many = 2
        craft = own.get("craft") if own.get("craft") in CRAFTS else DEFAULT_CRAFT
        _write(state_dir, {"slug": slug, "name": name, "model": model, "max_parallel": many,
                           "instruction": str(own.get("instruction") or "").replace("\r\n", "\n").strip()[:INSTRUCTION_CHARS],
                           "craft": craft, "takes": [k for k in own.get("takes") or [] if k in TASK_KINDS]})
    return True


def takes_of(r: dict, kinds_: dict[str, str]) -> set[str]:
    """The kinds of work a role takes: its own (a library agent's `takes`) and the project's task types given to it."""
    return set(r.get("takes") or []) | {k for k, s in kinds_.items() if s == r.get("slug")}


def role_for(state_dir: Path, kind: str, team: list[str] | None = None) -> dict:
    """The role a task of this kind runs as (a task without a known kind is code): in a goal with a `team`, the first
    of the team whose own kinds hold it, then the first the project gives it to (Grunt's are every kind no one else
    has, so Grunt never takes a kind a specialist of the team takes); else, and with no team, the project's role for
    it (Grunt when none)."""
    kind = kind if kind in TASK_KINDS else DEFAULT_KIND
    kinds_ = kinds(state_dir)
    members = [r for slug in team or [] if slug != TASKMASTER and (r := role(state_dir, slug)) is not None]
    for r in [r for r in members if kind in (r.get("takes") or [])] + [r for r in members if kind in takes_of(r, kinds_)]:
        return r
    return role(state_dir, kinds_[kind]) or role(state_dir, GRUNT)


def head_tier(model: str, target: str, task_tier: str = "warrior") -> str:
    """The tier a role's head wears for a task of `task_tier` under the Target: a role on a tier, that tier; a model set
    by hand, that model's tier; By Target, the task's tier shifted by the Target (a middle task's when no task is named:
    thrift a novice, balance a seasoned, quality a veteran)."""
    from orkboard.realm import idea_target
    return idea_target.tier_of(idea_target.task_pick(task_tier or "warrior", target, str(model or ""))[0])


def head(r: dict, target: str, task_tier: str = "warrior") -> dict:
    """The head the page draws for a role: {"craft", "race", "tier"} (orkUI races/<race>-<tier>.png)."""
    craft = r.get("craft") if r.get("craft") in CRAFTS else DEFAULT_CRAFT
    tier = head_tier(str(r.get("model") or ""), target, task_tier)
    return {"craft": craft, "race": own_race(str(r.get("race") or ""), craft, tier), "tier": tier}


def known(state_dir: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """The roles by slug and the task types' roles, read once for many `task_head`s."""
    return {r["slug"]: r for r in roles(state_dir)}, kinds(state_dir)


def task_slug(task: dict, read: tuple[dict, dict]) -> str:
    """The slug of the role a task runs as: its `role`, else its type's role, else Grunt. `read`: `known()`."""
    kind = str(task.get("kind") or "")
    return str(task.get("role") or "") or read[1].get(kind if kind in TASK_KINDS else DEFAULT_KIND, GRUNT)


def task_head(state_dir: Path, task: dict, target: str, read: tuple[dict, dict] | None = None) -> dict:
    """The head of who does a task: the role it ran as (its type's role before it ran), at the tier it ran at (before it
    ran, the tier it will run at: its planned tier shifted by the Target, a role's own model winning). `read`: `known()`."""
    by_slug, _kinds = read = read or known(state_dir)
    r = by_slug.get(task_slug(task, read)) or by_slug.get(GRUNT) or role(state_dir, GRUNT)
    got = head(r, target, str(task.get("tier") or "warrior"))
    if task.get("ran_tier") in TIERS:
        got["tier"] = task["ran_tier"]
    return got


def spend_today(tasks: list[tuple[str, dict]]) -> dict[str, float]:
    """{role slug: today's cost} of (role, task) pairs whose task was started today."""
    today, out = dt.date.today().isoformat(), {}
    for slug, t in tasks:
        if str(t.get("started") or "").startswith(today) and isinstance(t.get("cost"), (int, float)):
            out[slug] = round(out.get(slug, 0.0) + float(t["cost"]), 4)
    return out
