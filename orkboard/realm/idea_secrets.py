"""The value of a `secret` to-do of an idea's plan (spec 29a §3): kept with the machine's secrets, never in a page,
in plan.json or in a prompt.

Where: the OS keychain through `keyring` when it is importable (service `orkcraft-ideas`, account
`<project id>/<idea slug>/<to-do id>`: the project's id is a hash of its folder's path, spec 37 §8, so two projects
with the same idea and to-do keep two secrets), else `<state_dir>/secrets.json` with mode 600, git-ignored, under the
same name. A secret under the old account (`<idea slug>/<to-do id>`) is read once and moved. plan.json says only
`"value": "stored"`; the runner reads the value back here and hands it to the task's session as an environment
variable named in the to-do's title.

    put(state_dir, "dark-mode", "t1", "sk-…")
    get(state_dir, "dark-mode", "t1") == "sk-…"
    forget(state_dir, "dark-mode")          # the idea was dropped

A `file` to-do's file (spec 35 §9) is kept beside them: `<state_dir>/ideas/<slug>/files/<to-do id>-<name>`, mode 600,
never in the repository, a page, plan.json (which says only the name) or a prompt's text. The task that waits for it
gets its path in the environment (`ORKCRAFT_FILE_T2`).

    put_file(state_dir, "dark-mode", "t2", "google-services.json", data)
    file_env(state_dir, "dark-mode", plan, "k1")    # {"ORKCRAFT_FILE_T2": "/…/files/t2-google-services.json"}
    forget_files(state_dir, "dark-mode")

No face, no model, no bus.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from orkboard.env import getenv
from orkboard.realm.project_folder import project_id

SERVICE = "orkcraft-ideas"
FILE = "secrets.json"
_NAME = re.compile(r"^[a-z0-9-]+/[A-Za-z0-9_-]{1,40}$")

try:                                    # an optional extra: `pip install keyring`
    import keyring                      # type: ignore[import-not-found]
except ImportError:                     # pragma: no cover - depends on the machine
    keyring = None


def _keychain():
    """The keychain, unless the tests keep it out (`ORKCRAFT_LOGINS_FILE`, as realm/logins.py)."""
    return None if getenv("LOGINS_FILE") else keyring


def key(slug: str, todo_id: str) -> str:
    name = f"{slug}/{todo_id}"
    if not _NAME.match(name):
        raise ValueError("Not a to-do of an idea")
    return name


def account(state_dir: Path, slug: str, todo_id: str) -> str:
    """The name a to-do's secret is kept under: the project's (`<state_dir>` is `<repo>/.orkcraft`), then the to-do's."""
    return f"{project_id(Path(state_dir).parent)}/{key(slug, todo_id)}"


def _path(state_dir: Path) -> Path:
    return state_dir / FILE


def _read(state_dir: Path) -> dict:
    try:
        data = json.loads(_path(state_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(state_dir: Path, data: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    _ignored(state_dir)
    tmp = _path(state_dir).with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(_path(state_dir))


def _ignored(state_dir: Path) -> None:
    """`secrets.json` is git-ignored in the town's folder even where the folder itself is not."""
    path = state_dir / ".gitignore"
    try:
        have = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    except OSError:
        have = []
    if FILE not in have:
        path.write_text("\n".join([*have, FILE]) + "\n", encoding="utf-8")


def put(state_dir: Path, slug: str, todo_id: str, value: str) -> str:
    """Keep the value; where it went: "keychain" or "file". A copy under the old account goes."""
    name, old = account(state_dir, slug, todo_id), key(slug, todo_id)
    kc = _keychain()
    if kc is not None:
        try:
            kc.set_password(SERVICE, name, value)
            _forget_old(kc, old)
            data = _read(state_dir)
            if name in data or old in data:     # an older copy in the file goes
                data.pop(name, None)
                data.pop(old, None)
                _write(state_dir, data)
            return "keychain"
        except Exception:                       # no secret service running: the file, as without it
            pass
    data = _read(state_dir)
    data[name] = value
    data.pop(old, None)
    _write(state_dir, data)
    return "file"


def _forget_old(kc, old: str) -> None:
    try:
        if kc.get_password(SERVICE, old) is not None:
            kc.delete_password(SERVICE, old)
    except Exception:
        pass


def get(state_dir: Path, slug: str, todo_id: str) -> str | None:
    """The value under the project's account; one under the old account (before spec 37 §8) is moved to it."""
    name, old = account(state_dir, slug, todo_id), key(slug, todo_id)
    kc = _keychain()
    if kc is not None:
        try:
            value = kc.get_password(SERVICE, name)
            if value is not None:
                return value
        except Exception:
            pass
    data = _read(state_dir)
    value = data.get(name)
    if isinstance(value, str):
        return value
    found = None
    if kc is not None:
        try:
            found = kc.get_password(SERVICE, old)
        except Exception:
            found = None
    if found is None and isinstance(data.get(old), str):
        found = data[old]
    if found is not None:
        put(state_dir, slug, todo_id, found)    # read once, and moved
    return found


def forget(state_dir: Path, slug: str, todo_ids: list[str] = ()) -> None:
    """The idea's secrets go (all of the file's, and the keychain's for the to-dos named), the old accounts' too."""
    kc = _keychain()
    for todo_id in todo_ids:
        for name in (account(state_dir, slug, todo_id), key(slug, todo_id)):
            try:
                if kc is not None:
                    kc.delete_password(SERVICE, name)
            except Exception:
                pass
    data = _read(state_dir)
    mine = (f"{project_id(Path(state_dir).parent)}/{slug}/", f"{slug}/")
    kept = {k: v for k, v in data.items() if not k.startswith(mine)}
    if kept != data:
        _write(state_dir, kept)


# -- a file to-do's file (spec 35 §9) -----------------------------------------------------------------------------

FILE_MAX = 5 * 1024 * 1024             # the most a file to-do takes
_FILE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def file_name(name: str) -> str:
    """A file's name as it is kept: its last part, plain characters only, never hidden."""
    base = str(name or "").replace("\\", "/").rsplit("/", 1)[-1]
    base = _FILE_NAME.sub("_", base).strip("._")[:120]
    if not base:
        raise ValueError("The file needs a name")
    return base


def files_dir(state_dir: Path, slug: str) -> Path:
    key(slug, "t1")                     # the slug is an idea's
    return Path(state_dir) / "ideas" / slug / "files"


def put_file(state_dir: Path, slug: str, todo_id: str, name: str, data: bytes, accept: list[str] = ()) -> Path:
    """Keep a to-do's file (mode 600); an earlier file of the same to-do goes. Its path."""
    key(slug, todo_id)
    name = file_name(name)
    if len(data) > FILE_MAX:
        raise ValueError("The file is larger than 5 MB")
    exts = [str(e).lower().lstrip(".") for e in accept or () if str(e).strip()]
    if exts and name.lower().rsplit(".", 1)[-1] not in exts and not any(name.lower().endswith("." + e) for e in exts):
        raise ValueError("That file is not one it takes: " + ", ".join("." + e for e in exts))
    folder = files_dir(state_dir, slug)
    folder.mkdir(parents=True, exist_ok=True)
    _ignored(Path(state_dir))
    for old in folder.glob(f"{todo_id}-*"):
        old.unlink(missing_ok=True)
    path = folder / f"{todo_id}-{name}"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.chmod(path, 0o600)
    return path


def file_path(state_dir: Path, slug: str, todo_id: str) -> Path | None:
    key(slug, todo_id)
    folder = files_dir(state_dir, slug)
    found = sorted(folder.glob(f"{todo_id}-*")) if folder.is_dir() else []
    return found[0] if found else None


def env_of(todo_id: str) -> str:
    return "ORKCRAFT_FILE_" + re.sub(r"[^A-Z0-9_]", "_", str(todo_id).upper())


def file_env(state_dir: Path, slug: str, plan: dict, task_id: str) -> dict[str, str]:
    """The paths of the file to-dos a task waits for, by their variable."""
    out = {}
    for todo in plan.get("todos") or []:
        if isinstance(todo, dict) and todo.get("kind") == "file" and task_id in (todo.get("for") or []):
            path = file_path(state_dir, slug, str(todo.get("id") or ""))
            if path is not None:
                out[env_of(str(todo["id"]))] = str(path)
    return out


def forget_files(state_dir: Path, slug: str) -> None:
    """The idea's files go (it was dropped)."""
    import shutil
    shutil.rmtree(files_dir(state_dir, slug), ignore_errors=True)
