"""Machine settings (`$XDG_CONFIG_HOME/orkcraft/settings.json`): what onboarding asks once per machine.

    s = settings.load()              # never raises; defaults for anything missing or broken
    s.tools["claude"].billing        # "subscription" | "api"
    s.quiet                          # 🌙 do-not-disturb hours (schedule.py)
    s.work                           # the person's working hours: quiet for questions (schedule.py `at_work`)
    s.autonomy                       # 0 ⛓️ in chains · 1 🕰 on the clock · 2 ⛓️‍💥 unchained (autonomy.py)
    s.autonomy_wait                  # minutes a question waits for the operator (1..60)
    s.rebuild_wait                   # hours (the operator around) a rebuild waits (1..48)
    s.profile                        # who the operator is and how their day goes (realm/intents.py)
    s.growth                         # the operator's mascot stage and deeds (realm/growth.py)
    s.usage, s.install_id            # anonymous usage stats: None not asked yet (core/usage.py)
    s.updates                        # auto | critical | ask: which updates install by themselves (core/updates.py)
    s.phones, s.phone_port           # the paired phones (only their tokens' hashes) and their listener's port (gui/pairing.py)
    s.look                           # camp | office: how the GUI draws the town for this person (docs/design/portrait.md)
    s.dnd_until                      # Do not disturb: "" off, "on" until turned off, else an ISO time (disturb.py)
    s.focus                          # "board": the window and the phone show only the board (spec 29a §1); "" the town
    s.ideas                          # the board's keeper and runner: batch_minutes, idle_hours, max_parallel, … (IDEAS;
                                     # `wiki`, the Board's Wiki folder, only when set: spec 37 §3.5); a project's own
                                     # Board settings start from them (`board_of`)
    s.projects_open                  # the open projects' folders, in the switcher's order (spec 37 §8)
    s.projects_recent                # the projects last shown, newest first (at most PROJECTS_RECENT)
    s.ops                            # Operations, the person's (docs/specs/38-operations.md §1): target, trust_after, … (OPS)
    settings.save(s)

    board_of(repo_root, s.ideas)     # a project's Board settings: `<repo>/.orkcraft/board.json` over the machine's
    save_board(repo_root, values)    # … written there (machine-local, git-ignored)

The tools the operator leads and how each is paid for, and the quiet hours of their day (design:
docs/design/onboarding.md). There is one look now: `mode`, `office` and `office_days` of older
settings files still load and are ignored, and are no longer written. `look` is not a mode: it changes
only how the GUI draws (docs/design/portrait.md §3).
Orkline never stores an API key here: `billing` only says how the CLI is paid for.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from orkboard import autonomy as autonomy_
from orkboard.env import getenv
from orkboard.realm import harnesses
from orkboard.schedule import Span

TOOLS = harnesses.ids()
BILLINGS = ("subscription", "api")
PROFILE_TEXT = ("orchestration", "role", "role_other", "industry", "industry_other", "day_other", "kin")
PROFILE_LISTS = ("day", "mcp")   # mcp: the MCP servers the orks may use (gui/onboarding.py)
UPDATES = ("auto", "critical", "ask")   # core/updates.py POLICIES
LOOKS = ("camp", "office", "shift")
# When the computer is kept from sleeping (gui/away.py): never, while carts are in work, or also while a phone is
# paired, so it can reach the town all day (decisions-2026-10 §18). Both only on power.
KEEP_AWAKE = ("off", "carts", "phone")
# "shift": Office while the work day lasts, Camp the rest of the day (docs/design/portrait.md §3) — the default.
SHIFT = (9 * 60, 17 * 60)                # the work day, in minutes from midnight: 09:00–17:00


def default_look() -> str:
    """The look of a machine that has picked none: by the shift (`ORKCRAFT_LOOK` names another: the tests' Camp)."""
    look = getenv("LOOK")
    return look if look in LOOKS else "shift"


def look_now(s: "MachineSettings", now=None) -> str:
    """The look the GUI draws now: camp | office; by the shift, Office within its hours."""
    if s.look != "shift":
        return s.look
    import datetime as dt
    t = now or dt.datetime.now()
    return "office" if shift(s).contains(t.hour * 60 + t.minute) else "camp"


def shift(s: "MachineSettings") -> Span:
    """The work day the look follows: the person's working hours once set, else 09:00–17:00."""
    return s.work or Span(SHIFT[0], SHIFT[1] - SHIFT[0])
# The board's keeper and runner (spec 29a): how often the batch reads new ideas, when a talk's session is
# compacted, how many tasks run at once, which branch they merge into (`dev`: the testers' default, spec 33 §4),
# whether it is pushed (off), and whether a result waits for the person at Review (on; off merges by itself).
# Spec 35: the Board's Target (thrift · balance · quality), whether a safe plan starts by itself, the night's window
# (local time), the share of the window kept for the person by day and at night, and the repository's own risky paths.
# `batch_minutes` is kept, unused (the batch went in spec 35), so older settings keep loading.
IDEAS = {"batch_minutes": 30, "idle_hours": 24, "max_parallel": 1, "merge_into": "dev", "push": False, "review": True,
         "target": "balance", "autostart": True, "night": "01:00-07:00", "reserve_day": 0.3, "reserve_night": 0.1,
         "risk_paths": []}
IDEA_TARGETS = ("thrift", "balance", "quality")
NIGHT = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$")
FOCUSES = ("", "board")
RECENT_FOLDERS = 8                       # the recent folders a Wiki's picker offers               # the GUI's two looks; camp the default
# Operations (docs/specs/38-operations.md §1): the tier and effort of its calls, the clean checks in a row before a
# template goes by itself, the most it does by itself a day, how long a finished operation keeps its texts, and each
# template's server key → the MCP server's name on this machine.
OPS = {"target": "balance", "trust_after": 1, "daily_alone": 20, "keep_days": 14, "servers": {}}
PROJECTS_RECENT = 10                     # the projects the switcher's Recent remembers (spec 37 §8)
PROJECTS_OPEN = 20                       # the most projects open at once
# The Board's settings that are the project's (spec 37 §8): read from `<repo>/.orkcraft/board.json`, the machine's
# `ideas` being the defaults a new project starts from; `risk_paths` is the tracked `orkcraft.toml`'s `[board]`.
BOARD = ("target", "autostart", "night", "merge_into", "push", "review", "wiki", "max_parallel", "reserve_day",
         "reserve_night")
BOARD_FILE = Path(".orkcraft") / "board.json"


@dataclass
class ToolChoice:
    enabled: bool = False
    billing: str = "subscription"


@dataclass
class MachineSettings:
    tools: dict[str, ToolChoice] = field(default_factory=lambda: {t: ToolChoice() for t in TOOLS})
    onboarded: bool = False       # the machine's part of onboarding is done
    quiet: Span | None = None     # 🌙 do-not-disturb hours; None = off
    work: Span | None = None      # the person's working hours (no push or toast for questions); None = not set
    autonomy: int = autonomy_.DEFAULT_LEVEL   # 0 chains · 1 clock · 2 free; kept as a word (autonomy.py)
    autonomy_wait: int = autonomy_.DEFAULT_WAIT   # a question: minutes
    rebuild_wait: int = autonomy_.DEFAULT_REBUILD   # a rebuild: hours the operator is around
    profile: dict = field(default_factory=dict)   # orchestration, role, industry (+ _other), day, ai_tools
    growth: dict = field(default_factory=dict)    # stage (1–4) and deeds {id: date}: the operator's, every camp's
    # The 🛡 Warder's agy hook was checked on a live agy here (docs/design/agy-guard.md, smoke test):
    # only then does onboarding say the Warder guards agy and install its hook. Off until someone does.
    agy_warder_checked: bool = False
    usage: bool | None = None     # anonymous usage stats (core/usage.py): None until the operator answers
    install_id: str = ""          # a random id while they share them; forgotten when they stop
    keep_awake: str = "carts"     # KEEP_AWAKE: when the computer does not sleep by itself, on power (gui/away.py)
    awake_offered: bool = False   # "keep it awake for the phone" was asked once, when a phone paired (js/phones.js)
    fire: bool = True             # flames over a building whose ork has waited a minute or more (the GUI's huts)
    updates: str = "critical"     # which updates install by themselves when the town opens (core/updates.py)
    main_tool: str = ""           # the tool decisions run on (realm/harnesses.py); "" the first one on
    # The phones paired with this machine's towns (docs/design/mobile.md §2): id, name, the SHA-256 of the
    # device token (never the token), when paired and when last seen. The Town Scroll never holds them.
    phones: list = field(default_factory=list)
    phone_port: int = 0           # the phone listener's port, kept so a paired phone finds it again; 0 not chosen
    look: str = field(default_factory=default_look)   # how the GUI draws the town: camp | office | shift (portrait.md §3)
    dnd_until: str = ""           # Do not disturb: "" off, "on" until turned off, else when it ends (disturb.py)
    recent_folders: list = field(default_factory=list)   # the folders last connected to a Wiki, newest first (gui/folders.py)
    # The model a tier runs on, per tool, chosen in Settings → AI tools: {"agy": {"elder": "gemini-3.1-pro-high"}}.
    # A family (`gemini-flash-high`) is its newest model; absent, the tier's own family (realm/harnesses.py `pick`).
    tier_models: dict = field(default_factory=dict)
    focus: str = "board"          # FOCUSES: "board" shows only the board (alpha's default), "" the whole town
    ideas: dict = field(default_factory=lambda: dict(IDEAS))   # the board's keeper and runner (IDEAS)
    projects_open: list = field(default_factory=list)     # the open projects' folders, in the switcher's order
    projects_recent: list = field(default_factory=list)   # the projects last shown, newest first
    ops: dict = field(default_factory=lambda: clean_ops(None))   # Operations (OPS)

    def to_dict(self) -> dict:
        return {
            "tools": {t: {"enabled": c.enabled, "billing": c.billing} for t, c in self.tools.items()},
            "onboarded": self.onboarded,
            "quiet": self.quiet.to_dict() if self.quiet else None,
            "work": self.work.to_dict() if self.work else None,
            "autonomy": autonomy_.word(self.autonomy),
            "autonomy_wait": self.autonomy_wait,
            "rebuild_wait": self.rebuild_wait,
            "profile": self.profile,
            "growth": self.growth,
            "agy_warder_checked": self.agy_warder_checked,
            "usage": {"share": self.usage, "id": self.install_id},
            "fire": self.fire,
            "keep_awake": self.keep_awake,
            "awake_offered": self.awake_offered,
            "updates": self.updates,
            "main_tool": self.main_tool,
            "phones": [dict(p) for p in self.phones],
            "phone_port": self.phone_port,
            "look": self.look,
            "dnd_until": self.dnd_until,
            "recent_folders": list(self.recent_folders),
            "tier_models": {t: dict(m) for t, m in self.tier_models.items()},
            "focus": self.focus,
            "ideas": dict(self.ideas),
            "projects_open": list(self.projects_open),
            "projects_recent": list(self.projects_recent),
            "ops": {**self.ops, "servers": dict(self.ops.get("servers") or {})},
        }

    @classmethod
    def from_dict(cls, data: dict) -> MachineSettings:
        s = cls()
        tools = data.get("tools") if isinstance(data.get("tools"), dict) else {}
        for t in TOOLS:
            raw = tools.get(t)
            if isinstance(raw, dict):
                billing = raw.get("billing")
                s.tools[t] = ToolChoice(enabled=bool(raw.get("enabled", False)),
                                        billing=billing if billing in BILLINGS else "subscription")
        s.onboarded = bool(data.get("onboarded", False))
        s.quiet = Span.from_dict(data.get("quiet"))
        s.work = Span.from_dict(data.get("work"))
        s.autonomy = autonomy_.of(data.get("autonomy"))
        s.autonomy_wait = autonomy_.wait_of(data.get("autonomy_wait"))
        s.rebuild_wait = autonomy_.rebuild_of(data.get("rebuild_wait"))
        s.profile = clean_profile(data.get("profile"))
        s.growth = clean_growth(data.get("growth"))
        s.agy_warder_checked = data.get("agy_warder_checked") is True
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        s.usage = usage.get("share") if isinstance(usage.get("share"), bool) else None
        s.fire = data.get("fire") is not False
        s.keep_awake = awake_mode(data.get("keep_awake"))
        s.awake_offered = data.get("awake_offered") is True
        s.updates = data["updates"] if data.get("updates") in UPDATES else "critical"
        s.main_tool = data["main_tool"] if data.get("main_tool") in TOOLS else ""
        s.phones = clean_phones(data.get("phones"))
        port = data.get("phone_port")
        s.phone_port = port if isinstance(port, int) and not isinstance(port, bool) and 1024 <= port <= 65535 else 0
        s.look = data["look"] if data.get("look") in LOOKS else default_look()
        s.dnd_until = clean_dnd(data.get("dnd_until"))
        recent = data.get("recent_folders")
        s.recent_folders = [str(x)[:1000] for x in recent if isinstance(x, str) and x.strip()][:RECENT_FOLDERS] \
            if isinstance(recent, list) else []
        s.tier_models = clean_tier_models(data.get("tier_models"))
        s.focus = data["focus"] if data.get("focus") in FOCUSES else "board"
        s.ideas = clean_ideas(data.get("ideas"))
        s.projects_open = clean_folders(data.get("projects_open"), PROJECTS_OPEN)
        s.projects_recent = clean_folders(data.get("projects_recent"), PROJECTS_RECENT)
        s.ops = clean_ops(data.get("ops"))
        install_id = usage.get("id")
        if s.usage:                   # a broken id is drawn again: the stats never carry what was in the file
            ok = isinstance(install_id, str) and re.fullmatch(r"[0-9a-f]{32}", install_id)
            s.install_id = install_id if ok else uuid.uuid4().hex
        return s


def clean_tier_models(raw: object) -> dict[str, dict[str, str]]:
    """{tool: {tier: model}} as stored: known tools and tiers, a model of a few words; the rest dropped."""
    out: dict[str, dict[str, str]] = {}
    for tool, tiers in (raw.items() if isinstance(raw, dict) else ()):
        if tool not in TOOLS or not isinstance(tiers, dict):
            continue
        kept = {tier: model.strip()[:100] for tier, model in tiers.items()
                if tier in harnesses.TIERS and isinstance(model, str) and re.fullmatch(r"[\w.:/@\[\]()][\w.:/@\[\]() -]{0,99}", model.strip())}
        if kept:
            out[tool] = kept
    return out


def clean_ideas(raw: object) -> dict:
    """The board's keeper and runner settings: every key of IDEAS, a broken value as its default."""
    raw = raw if isinstance(raw, dict) else {}
    out = {**IDEAS, "risk_paths": []}
    for k, lo, hi in (("batch_minutes", 1, 24 * 60), ("idle_hours", 1, 24 * 14), ("max_parallel", 1, 8)):
        v = raw.get(k)
        if isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi:
            out[k] = v
    branch = raw.get("merge_into")
    if isinstance(branch, str) and re.fullmatch(r"[\w./-]{1,100}", branch) and ".." not in branch:
        out["merge_into"] = branch
    for k in ("push", "review", "autostart"):
        if isinstance(raw.get(k), bool):
            out[k] = raw[k]
    if raw.get("target") in IDEA_TARGETS:
        out["target"] = raw["target"]
    night = raw.get("night")
    if isinstance(night, str) and NIGHT.match(night.strip()) and night.strip()[:5] != night.strip()[6:]:
        out["night"] = night.strip()
    for k in ("reserve_day", "reserve_night"):
        v = raw.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 0.9:
            out[k] = round(float(v), 3)
    paths = raw.get("risk_paths")
    if isinstance(paths, list):
        out["risk_paths"] = [p.strip()[:200] for p in paths if isinstance(p, str) and p.strip()][:50]
    wiki = raw.get("wiki")              # the Board's Wiki, a folder in the repository (spec 37 §3.5); kept only when set
    if isinstance(wiki, str) and (wiki := wiki.strip().strip("/")) and re.fullmatch(r"[\w. /-]{1,200}", wiki) \
            and ".." not in wiki.split("/"):
        out["wiki"] = wiki
    return out


def clean_ops(raw: object) -> dict:
    """Operations' settings: every key of OPS, a broken value as its default; `servers` keeps a key of a word and a
    server's name as `claude mcp list` prints it."""
    raw = raw if isinstance(raw, dict) else {}
    out = {**OPS, "servers": {}}
    if raw.get("target") in IDEA_TARGETS:
        out["target"] = raw["target"]
    for k, lo, hi in (("trust_after", 1, 5), ("daily_alone", 1, 100), ("keep_days", 1, 365)):
        v = raw.get(k)
        if isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi:
            out[k] = v
    servers = raw.get("servers")
    for key, name in (servers.items() if isinstance(servers, dict) else ()):
        if isinstance(key, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,39}", key) and isinstance(name, str) \
                and name.strip() and len(name.strip()) <= 100 and name.isprintable():
            out["servers"][key] = name.strip()
    return out


def clean_folders(raw: object, most: int) -> list[str]:
    """Absolute folders as stored, each once, at most `most`; anything else dropped."""
    out: list[str] = []
    for x in raw if isinstance(raw, list) else []:
        if isinstance(x, str) and x.strip() and len(x) <= 1000 and "\0" not in x and Path(x).is_absolute() \
                and x not in out:
            out.append(x)
    return out[:most]


# -- a project's Board settings (spec 37 §8) ---------------------------------------------------------------------

_BOARD_CACHE: dict = {}


def _read_cached(file: Path, parse) -> object:
    """`parse(text)` of a file, read again only when it changed (the runner asks for a setting often); None when
    there is no file or it is broken."""
    try:
        st = file.stat()
    except OSError:
        return None
    stamp = (st.st_mtime_ns, st.st_size)
    got = _BOARD_CACHE.get(str(file))
    if got is None or got[0] != stamp:
        try:
            value = parse(file.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            value = None
        got = (stamp, value)
        _BOARD_CACHE[str(file)] = got
    return got[1]


def risk_paths_of(repo_root: Path) -> list[str] | None:
    """The repository's own risky paths, `orkcraft.toml` `[board] risk_paths` (tracked: a fact of the repository);
    None when it names none."""
    import tomllib
    table = _read_cached(Path(repo_root) / "orkcraft.toml", tomllib.loads)
    board = table.get("board") if isinstance(table, dict) else None
    paths = board.get("risk_paths") if isinstance(board, dict) else None
    if not isinstance(paths, list):
        return None
    return clean_ideas({"risk_paths": paths})["risk_paths"]


def board_of(repo_root: Path, defaults: dict | None) -> dict:
    """A project's Board settings: the machine's `ideas` (`defaults`), the project's `board.json` over them (only
    the keys of BOARD), `risk_paths` from its `orkcraft.toml` when it names some; every key of IDEAS."""
    own = _read_cached(Path(repo_root) / BOARD_FILE, json.loads)
    merged = dict(defaults or IDEAS)
    if isinstance(own, dict):
        merged.update({k: own[k] for k in BOARD if k in own})
    out = clean_ideas(merged)
    paths = risk_paths_of(repo_root)
    if paths is not None:
        out["risk_paths"] = paths
    return out


def save_board(repo_root: Path, values: dict) -> dict:
    """The project's Board settings, written to `<repo>/.orkcraft/board.json` (git-ignored there): the keys of BOARD
    as `clean_ideas` keeps them. What was written."""
    cleaned = clean_ideas(values)
    data = {k: cleaned[k] for k in BOARD if k in cleaned}
    if "wiki" not in cleaned:
        data["wiki"] = ""                   # no Wiki of its own: the machine's is not taken either
    file = Path(repo_root) / BOARD_FILE
    _write(file, data)
    _BOARD_CACHE.pop(str(file), None)
    ignore = file.parent / ".gitignore"
    try:
        have = ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
        if file.name not in have:
            ignore.write_text("\n".join([*have, file.name]) + "\n", encoding="utf-8")
    except OSError:
        pass
    return data


def awake_mode(raw: object) -> str:
    """One of KEEP_AWAKE; the old true / false (and nothing) read as "carts" / "off", as they behaved."""
    if raw in KEEP_AWAKE:
        return str(raw)
    return "off" if raw is False else "carts"


def clean_dnd(raw: object) -> str:
    """Do not disturb as stored: "on", an ISO time it ends at, else "" (off)."""
    if raw == "on":
        return "on"
    if isinstance(raw, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d)?", raw):
        return raw
    return ""


def clean_phones(raw: object) -> list[dict]:
    """The paired phones that are whole: an id, a name, a token's hash; anything else is dropped (a phone
    whose entry broke pairs again)."""
    out: list[dict] = []
    for p in raw if isinstance(raw, list) else []:
        if not isinstance(p, dict):
            continue
        pid, name, digest = p.get("id"), p.get("name"), p.get("hash")
        if not (isinstance(pid, str) and re.fullmatch(r"[0-9a-f]{16}", pid) and isinstance(digest, str)
                and re.fullmatch(r"[0-9a-f]{64}", digest) and isinstance(name, str) and name.strip()):
            continue
        if any(o["id"] == pid for o in out):
            continue
        entry = {"id": pid, "name": name.strip()[:60], "hash": digest,
                 "paired": str(p.get("paired") or "")[:32], "seen": str(p.get("seen") or "")[:32]}
        if (push := clean_push(p.get("push"))) is not None:
            entry["push"] = push
        out.append(entry)
    return out


PUSH_KEY = re.compile(r"[A-Za-z0-9_-]{1,200}")


def clean_push(raw: object) -> dict | None:
    """A phone's Web Push subscription (docs/specs/42-coming-back.md §3.3): its push service's endpoint, the two keys, when it
    was made and the day the morning's push was sent; None for anything else (a bad one drops the whole subscription)."""
    if not isinstance(raw, dict):
        return None
    endpoint, p256dh, auth = raw.get("endpoint"), raw.get("p256dh"), raw.get("auth")
    morning = raw.get("morning") or ""
    if not (isinstance(endpoint, str) and re.fullmatch(r"https://[^\s]{1,1016}", endpoint) and len(endpoint) <= 1024
            and isinstance(p256dh, str) and PUSH_KEY.fullmatch(p256dh) and isinstance(auth, str) and PUSH_KEY.fullmatch(auth)
            and isinstance(morning, str) and (not morning or re.fullmatch(r"\d{4}-\d\d-\d\d", morning))):
        return None
    return {"endpoint": endpoint, "p256dh": p256dh, "auth": auth, "at": str(raw.get("at") or "")[:32], "morning": morning}


def clean_growth(raw: object) -> dict:
    """The mascot's stage (1–4) and the deeds done with their dates; {} for anything else."""
    if not isinstance(raw, dict):
        return {}
    out: dict = {}
    if isinstance(raw.get("stage"), int) and 1 <= raw["stage"] <= 4:
        out["stage"] = raw["stage"]
    deeds = raw.get("deeds")
    if isinstance(deeds, dict):
        out["deeds"] = {str(k)[:40]: str(v)[:20] for k, v in list(deeds.items())[:40] if isinstance(v, str)}
    return out


def clean_profile(raw: object) -> dict:
    """Only the known keys, as strings and lists of strings; {} for anything else."""
    if not isinstance(raw, dict):
        return {}
    out: dict = {k: str(raw[k])[:200] for k in PROFILE_TEXT if isinstance(raw.get(k), str) and raw[k].strip()}
    for k in PROFILE_LISTS:
        if isinstance(raw.get(k), list):
            out[k] = [str(x)[:40] for x in raw[k] if isinstance(x, str)][:20]
    tools_ = raw.get("ai_tools")
    if isinstance(tools_, dict):
        rated = {}
        for t, r in list(tools_.items())[:20]:
            if not isinstance(r, dict):
                continue
            keep: dict = {k: bool(r.get(k)) for k in ("like", "dislike")}
            keep.update({k: str(r[k])[:40] for k in ("title", "good", "weak") if isinstance(r.get(k), str) and r[k]})
            rated[str(t)[:40]] = keep
        if rated:
            out["ai_tools"] = rated
    return out


def path() -> Path:
    """`$ORKCRAFT_SETTINGS_FILE`, else `$XDG_CONFIG_HOME/orkcraft/settings.json`."""
    env = getenv("SETTINGS_FILE")
    if env:
        return Path(env).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME", "").strip() or str(Path.home() / ".config")
    return Path(base) / "orkcraft" / "settings.json"


def load(file: Path | None = None) -> MachineSettings:
    file = file or path()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return MachineSettings()
    return MachineSettings.from_dict(data) if isinstance(data, dict) else MachineSettings()


_CACHE: dict = {}


def cached() -> MachineSettings:
    """The machine settings on disk, read again only when the file changed (the map, a step's tool and its tiers
    ask often). Orkboard's and the line's: `realm/builders.py` `_machine()` reads it."""
    file = path()
    try:
        key = (str(file), file.stat().st_mtime_ns)
    except OSError:
        key = (str(file), None)
    if _CACHE.get("key") != key:
        _CACHE.update(key=key, machine=load(file))
    return _CACHE["machine"]


def main_tool(machine: MachineSettings | None = None) -> str:
    """The machine's main tool (read from disk when not given: the chosen one if it is on, else the first on);
    Claude Code when none is on, as before there was a choice."""
    machine = machine or cached()
    return harnesses.main([t for t, c in machine.tools.items() if c.enabled], machine.main_tool) or "claude"


def preset_role(role_id: str, file: Path | None = None, kin: str = "") -> bool:
    """`orkcraft --role`: the role the landing page was told, kept for the onboarding to open on.
    `kin`: the page named a class with two roles (gnome), so the GUI's onboarding asks which of the two.
    It never overrides a role the operator picked in an onboarding they finished. True when kept."""
    s = load(file)
    if s.onboarded and s.profile.get("role"):
        return False
    s.profile = {k: v for k, v in {**s.profile, "role": role_id, "kin": kin}.items() if k != "kin" or kin}
    save(s, file)
    return True


def preset_look(look: str, file: Path | None = None) -> bool:
    """`orkcraft --look`: the look the landing page was told (camp | office), so the town first opens in it.
    Like `preset_role`, it never overrides a look the operator has lived with since a finished onboarding
    (they switch it in Settings). True when kept."""
    if look not in LOOKS:
        raise ValueError(look)
    s = load(file)
    if s.onboarded:
        return False
    s.look = look
    save(s, file)
    return True


def _raw(file: Path) -> dict:
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(file: Path, data: dict) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_suffix(file.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(file)


def save(s: MachineSettings, file: Path | None = None) -> None:
    """The settings as `s` has them, but the paired phones as the file has them: only `save_phones`
    writes those, so a town that loaded the settings before a phone was forgotten never brings it back."""
    file = file or path()
    data = s.to_dict()
    raw = _raw(file)
    data["phones"], data["phone_port"] = raw.get("phones", []), raw.get("phone_port", 0)
    _write(file, data)


def save_phones(phones: list[dict], port: int, file: Path | None = None) -> None:
    """The paired phones and their listener's port, everything else in the file as it is (gui/pairing.py)."""
    file = file or path()
    raw = _raw(file)
    raw["phones"], raw["phone_port"] = clean_phones(phones), port
    _write(file, raw)
