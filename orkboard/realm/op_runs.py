"""Operations' state, the person's (docs/specs/38-operations.md §1, §3, §6, §7, §9): never in a repository.

    root = op_runs.root()                 # ~/.config/orkcraft/ops/ (beside the machine settings)
    op_runs.save(root, run)               # runs/<id>.json, written whole, atomically, mode 600
    op_runs.load(root, id) · op_runs.runs(root)
    op_runs.trust(root, name)             # templates/<name>/trust.json: {version, clean, alone, why, today}
    op_runs.after_check(t, edited, 1)     # the way to *by itself*: pure functions, tested apart (§6)
    op_runs.stops(t, risk, doubts, 20, today)   # why an operation of a template that goes by itself stops at the check
    op_runs.rules(root, name) · take_rules · decline · proposal   # what a template learned (§7)
    op_runs.event(root, event_log.OP_ADDED, op=…)                 # ops/events.jsonl, by event_log's rules
    op_runs.spend(root, line)             # ops/spend.jsonl, idea_spend's line
    op_runs.ledger(root)                  # ops/ledger.jsonl: its calls' telemetry lines, never a project's
    op_runs.save_learn(root, name, given) # templates/<name>/learn.json: a learn call waiting for the window (§7)
    op_runs.forget_old(root, keep_days)   # a finished operation's texts and calls go after `keep_days`

Every file under `ops/` is mode 600 and its folders 700: a mail's words and an issue's live here only. No face.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import secrets
import threading
from pathlib import Path
from typing import Any

from orkboard import settings
from orkboard.realm import call_log, event_log, ideas

RUN_KEYS = ("id", "template", "version", "state", "fields", "found", "draft", "args", "doubts", "edited", "alone",
            "device", "link", "done_id", "why", "acted", "at", "done_at", "cost", "held_until", "held", "step",
            "again", "keep", "changes")       # Prepare again's: it was asked for, the parts kept, before → after
KEPT_KEYS = ("id", "template", "state", "link", "alone", "cost", "at", "done_at")      # after keep_days (§9)
STATES = ("preparing", "check", "acting", "done", "held", "failed", "dropped")
FINISHED = ("done", "failed", "dropped")
WHYS = ("clean", "edit", "rules", "not_right", "version", "reset")
MAX_RULES, RULE_CHARS, RULES_CHARS, DECLINED_READ = 3, 200, 4000, 10
_LOCK = threading.Lock()


def root() -> Path:
    """`ops/` beside the machine settings: `~/.config/orkcraft/ops/` (`$XDG_CONFIG_HOME`, `$ORKCRAFT_SETTINGS_FILE`)."""
    return settings.path().parent / "ops"


def _private_dir(folder: Path) -> Path:
    """The folder made, mode 700, and each folder above it up to `ops/` itself."""
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    chain = [folder, *folder.parents]
    top = next((n for n, p in enumerate(chain) if p.name == "ops"), 0)
    for p in chain[:top + 1]:
        try:
            os.chmod(p, 0o700)
        except OSError:
            pass
    return folder


def write(path: Path, text: str) -> None:
    """A file written whole, atomically, mode 600 (its folders 700)."""
    _private_dir(path.parent)
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def append(path: Path, row: dict) -> None:
    """A JSON line appended to a mode-600 file; a disk that refuses is ignored."""
    try:
        with _LOCK:
            _private_dir(path.parent)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def lines(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for raw in text.splitlines():
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


# -- one operation (§3) -----------------------------------------------------------------------------------------

def new_id() -> str:
    return f"op-{dt.datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


def _safe(op_id: object) -> str:
    text = str(op_id or "")
    if not text.startswith("op-") or not all(c.isalnum() or c == "-" for c in text) or len(text) > 60:
        raise KeyError(text)
    return text


def run_path(base: Path, op_id: str) -> Path:
    return base / "runs" / f"{_safe(op_id)}.json"


def blank(op_id: str, template: str, version: str, fields: dict, device: str = "desktop") -> dict:
    return {"id": op_id, "template": template, "version": version, "state": "preparing", "fields": dict(fields),
            "found": [], "draft": {}, "args": {}, "doubts": [], "edited": [], "alone": False, "device": device,
            "link": "", "done_id": "", "why": "", "acted": False, "at": now_iso(), "done_at": "", "cost": None,
            "held_until": "", "held": "", "step": ""}


def save(base: Path, run: dict) -> None:
    write(run_path(base, run["id"]), json.dumps({k: run.get(k) for k in RUN_KEYS if k in run}, ensure_ascii=False,
                                                indent=1))


def load(base: Path, op_id: str) -> dict | None:
    try:
        path = run_path(base, op_id)
    except KeyError:
        return None
    data = _json(path)
    return data if data.get("id") == op_id else None


def runs(base: Path) -> list[dict]:
    """Every operation, oldest first."""
    folder = base / "runs"
    try:
        files = sorted(folder.glob("op-*.json"))
    except OSError:
        return []
    out = [r for r in (_json(p) for p in files) if r.get("id")]
    return sorted(out, key=lambda r: str(r.get("at") or ""))


def add_cost(run: dict, cost: object) -> None:
    if isinstance(cost, (int, float)) and not isinstance(cost, bool):
        run["cost"] = round(float(run.get("cost") or 0.0) + float(cost), 6)


# -- a template's way to by itself (§6): pure functions ------------------------------------------------------

def _folder(base: Path, name: str) -> Path:
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise KeyError(name)
    return base / "templates" / name


def fresh_trust(version: str = "") -> dict:
    return {"version": version, "clean": 0, "alone": False, "why": "", "today": {"date": "", "alone_done": 0}}


def trust(base: Path, name: str) -> dict:
    got = _json(_folder(base, name) / "trust.json")
    out = fresh_trust()
    out.update({k: got[k] for k in ("version", "why") if isinstance(got.get(k), str)})
    if isinstance(got.get("clean"), int) and not isinstance(got.get("clean"), bool):
        out["clean"] = max(0, got["clean"])
    out["alone"] = got.get("alone") is True
    today = got.get("today") if isinstance(got.get("today"), dict) else {}
    out["today"] = {"date": str(today.get("date") or ""), "alone_done": int(today.get("alone_done") or 0)}
    return out


def save_trust(base: Path, name: str, t: dict) -> None:
    write(_folder(base, name) / "trust.json", json.dumps(t, ensure_ascii=False))


def _back(t: dict, why: str) -> dict:
    return {**t, "clean": 0, "alone": False, "why": why}


def after_check(t: dict, edited: bool, trust_after: int) -> dict:
    """A check passed: clean (no correction) counts towards by itself, at `trust_after` it goes by itself; a corrected
    one sends it back (`edit`)."""
    if edited:
        return _back(t, "edit")
    clean = int(t.get("clean") or 0) + 1
    if clean >= max(1, int(trust_after)):
        return {**t, "clean": clean, "alone": True, "why": "clean"}
    return {**t, "clean": clean}


def after_rules(t: dict) -> dict:
    """The person took the rules a correction made: it goes by itself (the owner's rule)."""
    return {**t, "alone": True, "why": "rules"}


def after_not_right(t: dict) -> dict:
    return _back(t, "not_right")


def after_reset(t: dict) -> dict:
    return _back(t, "reset")


def after_version(t: dict, version: str) -> dict:
    """The skill or the manifest changed on disk: back to checks. A first version seen is only kept."""
    if not t.get("version"):
        return {**t, "version": version}
    if t["version"] == version:
        return t
    return {**_back(t, "version"), "version": version}


def alone_today(t: dict, today: str) -> int:
    day = t.get("today") or {}
    return int(day.get("alone_done") or 0) if day.get("date") == today else 0


def after_alone(t: dict, today: str) -> dict:
    """One more done by itself today."""
    return {**t, "today": {"date": today, "alone_done": alone_today(t, today) + 1}}


def stops(t: dict, risk: str, doubts: list, daily_alone: int, today: str) -> str:
    """Why an operation of this template stops at the check: "" when it goes by itself; else `checks` (it does not
    go by itself), `high` (always checks with you), `doubt` (its prepare wrote one), `daily` (the day's cap). These
    stops change nothing of `trust.json`."""
    if risk == "high":
        return "high"
    if not t.get("alone"):
        return "checks"
    if doubts:
        return "doubt"
    if alone_today(t, today) >= max(1, int(daily_alone)):
        return "daily"
    return ""


def stop_words(stop: str, daily_alone: int) -> str:
    """What a check's row says of a stop, when its template goes by itself."""
    return {"doubt": "at your check · a doubt", "high": "always checks with you",
            "daily": f"checks again today: {daily_alone} done by itself"}.get(stop, "")


# -- rules (§7) -------------------------------------------------------------------------------------------------

def rules(base: Path, name: str) -> str:
    try:
        return (_folder(base, name) / "rules.md").read_text(encoding="utf-8")
    except (OSError, KeyError):
        return ""


def rule_lines(text: str) -> list[str]:
    return [line.strip().lstrip("-* ").strip() for line in (text or "").splitlines() if line.strip().lstrip("-* ")
            and not line.lstrip().startswith("#")]


def save_rules(base: Path, name: str, text: str) -> str:
    """The person's own edit: at most RULES_CHARS, a `#` or `##` heading made `###`. `trust.json` stays as it is."""
    cleaned = ideas.clean_text(str(text or ""))[:RULES_CHARS]
    write(_folder(base, name) / "rules.md", cleaned + ("\n" if cleaned else ""))
    return cleaned


def take_rules(base: Path, name: str, new: list[str]) -> str:
    """The lines appended to `rules.md`, each a bullet."""
    have = rules(base, name).rstrip("\n")
    text = (have + "\n" if have else "") + "\n".join(f"- {line}" for line in new)
    return save_rules(base, name, text)


def declined(base: Path, name: str, last: int = DECLINED_READ) -> list[dict]:
    return lines(_folder(base, name) / "declined.jsonl")[-last:]


def decline(base: Path, name: str, new: list[str], reason: str = "") -> None:
    append(_folder(base, name) / "declined.jsonl", {"lines": list(new), "reason": reason[:300], "at": now_iso()})


def _norm(line: str) -> str:
    return " ".join(line.casefold().split()).rstrip(".")


def new_rules(proposed: object, have: str, turned_down: list[dict]) -> list[str]:
    """The learn call's lines as kept: at most MAX_RULES, each at most RULE_CHARS, none that repeats one in the rules
    or one declined, none twice."""
    seen = {_norm(x) for x in rule_lines(have)}
    seen |= {_norm(x) for row in turned_down for x in row.get("lines") or [] if isinstance(x, str)}
    out: list[str] = []
    for line in proposed if isinstance(proposed, list) else []:
        if not isinstance(line, str):
            continue
        line = " ".join(line.split()).lstrip("-* ").strip()[:RULE_CHARS]
        if line and _norm(line) not in seen:
            seen.add(_norm(line))
            out.append(line)
        if len(out) == MAX_RULES:
            break
    return out


def proposal(base: Path, name: str) -> dict | None:
    """The rules proposal waiting for this template ({lines, why, op, at}); at most one."""
    got = _json(_folder(base, name) / "proposal.json")
    return got if got.get("lines") else None


def propose(base: Path, name: str, lines_: list[str], why: str, op_id: str) -> dict:
    """A new proposal replaces the old one."""
    row = {"lines": list(lines_), "why": why[:300], "op": op_id, "at": now_iso()}
    write(_folder(base, name) / "proposal.json", json.dumps(row, ensure_ascii=False))
    return row


def drop_proposal(base: Path, name: str) -> None:
    try:
        (_folder(base, name) / "proposal.json").unlink(missing_ok=True)
    except OSError:
        pass


def last_values(base: Path, name: str) -> dict:
    """The last values given to the template's `remember` fields."""
    return {k: v for k, v in _json(_folder(base, name) / "last.json").items() if isinstance(v, str)}


def remember(base: Path, name: str, values: dict) -> None:
    if values:
        write(_folder(base, name) / "last.json", json.dumps({**last_values(base, name), **values}, ensure_ascii=False))


# -- events and the ledger (§8, §11) ----------------------------------------------------------------------------

def event(base: Path, name: str, **fields: Any) -> bool:
    """One event in `ops/events.jsonl` by event_log's rules (its closed list, plain data)."""
    row = event_log.line(name, **fields)
    if row is None:
        return False
    append(base / "events.jsonl", row)
    return True


def spend(base: Path, row: dict) -> None:
    append(base / "spend.jsonl", row)


def ledger(base: Path) -> Path:
    """Operations' telemetry ledger (sources/telemetry.py's lines: when, model, cost, no text), made mode 600: its
    calls are charged here, never in a project's ledger (§9)."""
    path = base / "ledger.jsonl"
    if not path.exists():
        with _LOCK:
            _private_dir(path.parent)
            try:
                os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600))
            except OSError:
                pass
    return path


# -- a learn call waiting for the window (§7) --------------------------------------------------------------------

def save_learn(base: Path, name: str, given: dict) -> None:
    """What a template's learn call is given, kept until it runs: Orkboard closing with the window spent loses none."""
    write(_folder(base, name) / "learn.json", json.dumps(given, ensure_ascii=False))


def drop_learn(base: Path, name: str) -> None:
    try:
        (_folder(base, name) / "learn.json").unlink(missing_ok=True)
    except (OSError, KeyError):
        pass


def pending_learns(base: Path) -> dict[str, dict]:
    """template → what its waiting learn call is given."""
    out = {}
    for path in sorted((base / "templates").glob("*/learn.json")):
        got = _json(path)
        if isinstance(got.get("op"), str):
            out[path.parent.name] = {"op": got["op"], "not_right": got.get("not_right"),
                                     "changes": [c for c in got.get("changes") or [] if isinstance(c, dict)]}
    return out


# -- what stays private (§9) ------------------------------------------------------------------------------------

def forget_old(base: Path, keep_days: int, now: dt.datetime | None = None) -> int:
    """A finished operation older than `keep_days` keeps only KEPT_KEYS; its calls' prompts and outputs are removed
    from `ops/calls/` (their lines stay, with no text). How many were cut."""
    now = now or dt.datetime.now()
    cutoff = (now - dt.timedelta(days=max(1, int(keep_days)))).isoformat(timespec="seconds")
    cut: set[str] = set()
    for run in runs(base):
        if run.get("state") not in FINISHED or set(run) <= set(KEPT_KEYS):
            continue
        if str(run.get("done_at") or run.get("at") or "") >= cutoff:
            continue
        write(run_path(base, run["id"]), json.dumps({k: run.get(k) for k in KEPT_KEYS}, ensure_ascii=False, indent=1))
        cut.add(run["id"])
    calls = base / "calls"
    rows = call_log.read(calls)
    if cut and rows:
        for row in rows:
            if row.get("task") in cut and row.get("raw"):
                try:
                    (calls / str(row["raw"])).unlink(missing_ok=True)
                except OSError:
                    pass
                row["raw"], row["forgotten"] = "", True
        with call_log._LOCK:
            write(calls / call_log.LINES, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return len(cut)
