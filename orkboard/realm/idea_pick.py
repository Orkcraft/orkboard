"""Pick one (docs/specs/51-pick-one.md §2, decisions §64): a task of the plan may end with two to six variants of one kind
(pictures, sounds, clips or texts) instead of a change; the person picks one, with a note, or none.

    idea_pick.clean_ask(raw)                 # a plan's task `pick`: {"n", "kind", "ask", "target"}, else None
    variants, why = idea_pick.read(worktree, task)    # the task's files and manifest, checked; else ([], what is wrong, in plain words)
    pick = idea_pick.store(state_dir, slug, task, rnd, variants, by="grunt")    # the files move to the goal's state folder
    idea_pick.discard(worktree)              # the folder and the manifest leave the worktree
    idea_pick.current(state_dir, slug, task) # the pick of the task's round (pick.json), None before one
    idea_pick.answer(state_dir, slug, pick, picked="B", note="…")      # pick.json gains what the person said
    idea_pick.map_of(task)                   # {"n", "media", "round"} while the task is `picking`, else None

The task writes each variant as a file into `.orkcraft-pick/` at its worktree's root and a manifest `.orkcraft-pick.json`:
`{"variants": [{"name": "<24 characters at most>", "file": "<its name in the folder>", "why": "<one line>"}]}`. Nothing of it
is committed (as a check's findings file, realm/idea_checks.py): it is read, moved to `<state>/ideas/<goal>/picks/<task>-r<round>/`
with a `pick.json`, and the worktree is put back. A file's type is sniffed from its bytes (realm/media_sniff.py), never from its
name: that a text is Markdown is the one thing the name says. A variant is stored as `<key>.<ext>` (`a.png`), so a name the task
chose can never be a path, a dot-file or a surprise in a URL.

No face, no model. The route that serves the files is gui/media.py.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path

from orkboard.realm import ideas, media_sniff
from orkboard.realm.idea_git import BOARD_PAGE

PICK_DIR = ".orkcraft-pick"                  # at the worktree's root: the variants
PICK_FILE = ".orkcraft-pick.json"            # … and their manifest
PICKS = "picks"                              # <state>/ideas/<goal>/picks/<task>-r<round>/
MANIFEST_BYTES = 64 * 1024
N_MIN, N_MAX = 2, 6
NAME_MAX, WHY_MAX, ASK_MAX, TARGET_MAX, NOTE_MAX = 24, 300, 200, 200, 2000
KB, MB = 1024, 1024 * 1024
PICK_MAX = 120 * MB                          # all the files of one pick
VARIANT_KEYS = ("key", "name", "file", "mime", "bytes", "w", "h", "seconds", "why")
EXT = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp", "image/svg+xml": "svg",
       "audio/mpeg": "mp3", "audio/ogg": "ogg", "audio/wav": "wav", "audio/mp4": "m4a", "video/mp4": "mp4",
       "video/webm": "webm", "text/plain": "txt", "text/markdown": "md"}
MARKDOWN = (".md", ".markdown")


@dataclass(frozen=True)
class Kind:
    key: str                  # what the plan says: "image"
    word: str                 # what a person reads, one of them: "picture"
    many: str                 # … and several: "pictures"
    mimes: tuple[str, ...]    # the media types it may hold
    limit: int                # the most bytes of one file
    formats: str              # for the ask and for a reason: "PNG, JPEG, GIF, WEBP or SVG"


KINDS: dict[str, Kind] = {k.key: k for k in (
    Kind("image", "picture", "pictures", ("image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"), 10 * MB,
         "PNG, JPEG, GIF, WEBP or SVG"),
    Kind("audio", "sound", "sounds", ("audio/mpeg", "audio/ogg", "audio/wav", "audio/mp4"), 10 * MB, "MP3, OGG, WAV or M4A"),
    Kind("video", "clip", "clips", ("video/mp4", "video/webm"), 50 * MB, "MP4 or WEBM"),
    Kind("text", "text", "texts", ("text/plain", "text/markdown"), 4 * KB, "UTF-8 text or Markdown"),
)}


def kind_of(mime: str) -> Kind | None:
    """The kind a media type belongs to."""
    return next((k for k in KINDS.values() if mime in k.mimes), None)


def count_words(n: int, kind: Kind) -> str:
    """`3 sounds`, `1 sound`."""
    return f"{n} {kind.word if n == 1 else kind.many}"


def size_words(n: int, limit: int = 0) -> str:
    """A size in words, to the nearest MB (KB under one): `72 MB`, `6 KB`. Over its `limit` by a little it gets a decimal, so that
    what is over a limit never reads as the limit itself: `10.2 MB`."""
    unit, name = (MB, "MB") if n >= MB else (KB, "KB")
    whole = max(1, round(n / unit))
    if limit and n > limit and whole * unit <= limit:
        return f"{-(-n * 10 // unit) / 10:.1f} {name}"
    return f"{whole} {name}"


def _a(word: str) -> str:
    return ("an " if word[:1] in "aeiou" else "a ") + word


# -- the plan's ask --------------------------------------------------------------------------------------------

def clean_target(value: object) -> str:
    """The repository path the picked file is written to, as the plan says it: relative, forward slashes, inside the project,
    never git's own, the machine's own or a Board page; "" for anything else."""
    if not isinstance(value, str):
        return ""
    text = value.strip()
    parts = text.split("/")
    if (not text or len(text) > TARGET_MAX or text.startswith(("/", "~")) or "\\" in text or re.match(r"^[A-Za-z]:", text)
            or any(p in ("", ".", "..") or re.search(r"[\x00-\x1f]", p) for p in parts)
            or parts[0] in (".git", ".orkcraft") or parts[0].startswith(".orkcraft-") or BOARD_PAGE.search(text)):
        return ""
    return text


def clean_ask(raw: object) -> dict | None:
    """A plan's task `pick` as plan.json keeps it, `{"n": 2–6, "kind", "ask": one line, "target"}`; None for a missing one or one
    that is not (the task is then an ordinary task)."""
    if not isinstance(raw, dict):
        return None
    n, kind = raw.get("n"), raw.get("kind")
    ask, target = " ".join(str(raw.get("ask") or "").split())[:ASK_MAX], clean_target(raw.get("target"))
    if isinstance(n, bool) or not isinstance(n, int) or not N_MIN <= n <= N_MAX or kind not in KINDS or not ask or not target:
        return None
    return {"n": n, "kind": kind, "ask": ask, "target": target}


def ask_of(task: dict) -> dict | None:
    """The task's `pick` as it was kept (a task that makes variants), else None."""
    return clean_ask(task.get("pick")) if isinstance(task, dict) else None


def picked_words(picked: dict) -> str:
    """What the tasks that wait for a picked variant are told: `The person picked B · anchor: "<note>"`."""
    note = " ".join(str(picked.get("note") or "").split())
    return f"The person picked {picked.get('key')} · {picked.get('name')}" + (f': "{note}"' if note else "")


def map_of(task: dict) -> dict | None:
    """What the Map says of a task that waits for a pick, `{"n", "media", "round"}`; None for any other."""
    ask = ask_of(task)
    if ask is None or task.get("state") != "picking":
        return None
    return {"n": ask["n"], "media": ask["kind"], "round": int(task.get("round") or 1)}


# -- reading what the task left --------------------------------------------------------------------------------

def _key(i: int) -> str:
    return chr(ord("A") + i)


def _text(value: object, limit: int) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def _manifest(worktree: Path) -> tuple[list | None, str]:
    path = worktree / PICK_FILE
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise OSError
        with path.open("rb") as f:
            raw = f.read(MANIFEST_BYTES + 1)
    except OSError:
        return None, f"The task left no variants: its list ({PICK_FILE}) is missing"
    if len(raw) > MANIFEST_BYTES:
        return None, "The task's list of variants is too long"
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None, "The task's list of variants is not valid JSON"
    rows = data.get("variants") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        return None, 'The task\'s list of variants is not as asked: {"variants": [{"name", "file", "why"}]}'
    return rows, ""


def _file(folder: Path, name: object) -> Path | None:
    """The file `name` names inside the variants' folder: a plain name of a plain file that is really in it, else None."""
    if not isinstance(name, str) or not name or name != Path(name).name or name in (".", ".."):
        return None
    path = folder / name
    try:
        if not stat.S_ISREG(path.lstat().st_mode) or path.resolve().parent != folder.resolve():
            return None
    except OSError:
        return None
    return path


def read(worktree: Path, task: dict) -> tuple[list[dict], str]:
    """(the variants, "") the task left in its worktree, else ([], what is wrong, in plain words). Valid is: the manifest is JSON
    with the `n` variants its plan asked for, each file inside the folder, its type sniffed from its bytes and of the task's
    kind, each within the kind's limit and all within `PICK_MAX`. A variant is `{"key", "name", "file" (as it will be stored),
    "mime", "bytes", "w", "h", "seconds", "why", "src" (where it is now)}`; the name is cut to `NAME_MAX`."""
    ask = ask_of(task)
    if ask is None:
        return [], "The task has no pick to make"
    kind, folder = KINDS[ask["kind"]], worktree / PICK_DIR
    rows, why = _manifest(worktree)
    if rows is None:
        return [], why
    if len(rows) != ask["n"]:
        return [], f"The task left {count_words(len(rows), kind)}; its plan asked for {ask['n']}"
    out, seen, total = [], set(), 0
    for i, row in enumerate(rows):
        key, name = _key(i), row.get("file")
        src = _file(folder, name) if folder.is_dir() and not folder.is_symlink() else None
        if src is None:
            return [], f"{key} is not a file in the variants' folder ({name if isinstance(name, str) and name else 'no file named'})"
        if name in seen:
            return [], f"{key} is the same file as an earlier variant"
        seen.add(name)
        mime = media_sniff.sniff(src)
        if mime == "text/plain" and name.lower().endswith(MARKDOWN):
            mime = "text/markdown"
        if mime is None:
            return [], f"{key} is not {_a(kind.word)} of a kind the Board takes ({kind.formats})"
        if mime not in kind.mimes:
            return [], f"{key} is {_a(kind_of(mime).word)}, not {_a(kind.word)}"
        size = src.stat().st_size
        if size > kind.limit:
            return [], f"{key} is {size_words(size, kind.limit)}: {_a(kind.word)} is at most {size_words(kind.limit)}"
        total += size
        out.append({"key": key, "name": _text(row.get("name"), NAME_MAX) or Path(name).stem[:NAME_MAX], "file": f"{key.lower()}.{EXT[mime]}",
                    "mime": mime, "bytes": size, **media_sniff.measure(src, mime), "why": _text(row.get("why"), WHY_MAX), "src": src})
    if total > PICK_MAX:
        return [], f"The variants are {size_words(total, PICK_MAX)} in all: a pick is at most {size_words(PICK_MAX)}"
    return out, ""


def discard(worktree: Path) -> None:
    """The folder and the manifest leave the worktree (a pick stored, or a task that failed)."""
    shutil.rmtree(worktree / PICK_DIR, ignore_errors=True)
    try:
        (worktree / PICK_FILE).unlink()
    except OSError:
        pass


# -- the store: <state>/ideas/<goal>/picks/<task>-r<round>/ ------------------------------------------------------

def pick_id(task_id: str, rnd: int) -> str:
    return f"{task_id}-r{rnd}"


def folder_of(state_dir: Path, slug: str, pid: str) -> Path:
    return ideas.state_folder(state_dir, slug) / PICKS / pid


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _write(path: Path, data: dict) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def store(state_dir: Path, slug: str, task: dict, rnd: int, variants: list[dict], by: str = "", now: str = "") -> dict:
    """Move the variants `read` returned into the pick's folder and write its `pick.json`
    (`{"id", "task", "round", "by", "kind", "ask", "target", "at", "variants": [{"key", "name", "file", "mime", "bytes", "w", "h",
    "seconds", "why"}]}`); a folder of the same round is replaced. The pick is returned. Nothing is left in the worktree of them."""
    ask, pid = ask_of(task) or {}, pick_id(str(task.get("id")), rnd)
    folder = folder_of(state_dir, slug, pid)
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    for v in variants:
        shutil.move(str(v["src"]), str(folder / v["file"]))
    data = {"id": pid, "task": str(task.get("id")), "round": rnd, "by": by, "kind": ask.get("kind"), "ask": ask.get("ask"),
            "target": ask.get("target"), "at": now or _now(), "variants": [{k: v[k] for k in VARIANT_KEYS} for v in variants]}
    _write(folder / "pick.json", data)
    return data


def load(state_dir: Path, slug: str, pid: str) -> dict | None:
    """A pick's `pick.json`; None when the folder is gone or its file is not a pick's."""
    try:
        data = json.loads((folder_of(state_dir, slug, pid) / "pick.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("variants"), list) and data.get("id") == pid else None


def current(state_dir: Path, slug: str, task: dict) -> dict | None:
    """The pick of the task's round, the one the person is asked to answer."""
    return load(state_dir, slug, pick_id(str(task.get("id")), int(task.get("round") or 1)))


def answered(pick: dict) -> bool:
    return "picked" in pick


def answer(state_dir: Path, slug: str, pick: dict, picked: str | None, note: str, now: str = "") -> dict:
    """The pick with what the person said: `picked` (a key, or null for none of them), `note`, and `at` the time of the answer
    (`asked_at` keeps the time it was asked)."""
    data = {**pick, "asked_at": pick.get("at"), "picked": picked, "note": note, "at": now or _now()}
    _write(folder_of(state_dir, slug, str(pick["id"])) / "pick.json", data)
    return data


def next_round(state_dir: Path, slug: str, task_id: str) -> int:
    """The round a task that makes variants starts at: after the last it made (1 when it made none), so a task started anew never
    replaces the history of the variants before."""
    return 1 + max([int(d.get("round") or 0) for d in history(state_dir, slug, task_id)], default=0)


def history(state_dir: Path, slug: str, task_id: str) -> list[dict]:
    """The task's picks, round by round, oldest first (the history of the variants it made)."""
    base = ideas.state_folder(state_dir, slug) / PICKS
    found = [d for p in sorted(base.glob(f"{task_id}-r*")) if p.is_dir() and (d := load(state_dir, slug, p.name)) is not None] \
        if base.is_dir() else []
    return sorted(found, key=lambda d: int(d.get("round") or 0))
