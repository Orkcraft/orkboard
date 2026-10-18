"""A project is a repository's folder (docs/specs/37-board-and-line.md §8): what may not be one, starting git in one,
and the id its state is kept under.

    refusal(path)        # "" when the folder may be a project, else why not, in plain words
    has_git(path)        # it is a git repository's work tree
    start_git(path)      # git init and a first commit (unless too large): what was done, in a sentence
    project_id(path)     # a short hash of the folder's path (the to-dos' secrets are kept under it)

No face, no model, no bus.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

# A first commit takes the files as they are; a folder larger than this is started by the person, with their own
# .gitignore (spec 37 §8: "unless it would be too large").
FIRST_COMMIT_FILES = 20_000
FIRST_COMMIT_BYTES = 500 * 1024 * 1024
# What a first commit leaves out (realm/jobs.py FIRST_IGNORE), so it is not counted either.
SKIPPED = {".git", ".orkcraft", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
# The system's folders: never a project, nor anything in them.
SYSTEM = ("/bin", "/boot", "/dev", "/etc", "/lib", "/lib64", "/proc", "/sbin", "/sys", "/usr", "/System",
          "/private/etc", "C:/Windows", "C:/Program Files", "C:/Program Files (x86)", "C:/ProgramData")
# The system's folders that hold the person's own folders: never a project themselves (their folders may be).
SYSTEM_TOP = ("/", "/Users", "/home", "/var", "/opt", "/tmp", "/private", "/private/var", "/Volumes", "/mnt",
              "/media", "/srv", "/root", "/Library", "/Applications", "C:/", "C:/Users")
# The person's folders that hold secrets or the machine's settings: never a project, nor anything in them.
HOME_PRIVATE = (".ssh", ".gnupg", ".aws", ".config", ".local", ".cache", "Library")


def _norm(path: Path) -> str:
    return path.as_posix().rstrip("/") or "/"


def _within(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def refusal(path: str | Path) -> str:
    """Why this folder may not be a project ("" when it may): it is not there, it is the home folder, one of the
    system's or of the person's private ones, Orkboard's own, or inside a repository's `.git` or a Board's state."""
    raw = str(path or "").strip()
    if not raw or "\0" in raw:
        return "Pick a folder"
    try:
        folder = Path(raw).expanduser().resolve()
    except (OSError, RuntimeError):
        return "That folder cannot be read"
    if not folder.is_dir():
        return "That folder is not there"
    home = Path.home().resolve()
    if folder == home:
        return "Your home folder holds everything you have: open one of its project folders instead"
    norm = _norm(folder)
    if any(norm.lower() == top.lower().rstrip("/") or (top == "/" and norm == "/") for top in SYSTEM_TOP):
        return "That is one of the system's folders: open a project folder inside it instead"
    if any(norm.lower() == s.lower() or norm.lower().startswith(s.lower() + "/") for s in SYSTEM):
        return "That is one of the system's folders: it cannot be a project"
    if any(_within(folder, home / name) for name in HOME_PRIVATE):
        return "That folder holds your machine's settings or keys: it cannot be a project"
    own = Path(__file__).resolve().parents[1]           # the orkboard package
    if _within(folder, own) or "site-packages" in folder.parts or "dist-packages" in folder.parts:
        return "That is Orkline's own folder: it cannot be a project"
    if ".git" in folder.parts or ".orkcraft" in folder.parts:
        return "That folder is inside a repository's own state: open the repository's folder instead"
    if not os.access(folder, os.R_OK | os.X_OK):
        return "That folder cannot be read"
    return ""


def has_git(path: str | Path) -> bool:
    """The folder is a git work tree (its own `.git`, a folder or a worktree's file)."""
    return (Path(path) / ".git").exists()


def _too_large(folder: Path) -> str:
    files = size = 0
    for top, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIPPED]
        for name in names:
            files += 1
            try:
                size += (Path(top) / name).lstat().st_size
            except OSError:
                pass
            if files > FIRST_COMMIT_FILES or size > FIRST_COMMIT_BYTES:
                return (f"That folder is too large for a first commit (over {FIRST_COMMIT_FILES:,} files or "
                        f"{FIRST_COMMIT_BYTES // (1024 * 1024)} MB): start git there yourself, with a .gitignore")
    return ""


def start_git(path: str | Path) -> str:
    """Git in a folder that may be a project: `git init`, a .gitignore when there is none (secrets, caches and
    `.orkcraft/` left out) and a first commit of the files as they are, unless they are too many. What was done, in a
    sentence ("" when git was there with a commit already). Raises ValueError with the reason when it may not."""
    why = refusal(path)
    if why:
        raise ValueError(why)
    folder = Path(path).expanduser().resolve()
    if not has_git(folder):
        why = _too_large(folder)
        if why:
            raise ValueError(why)
    from orkboard.realm import jobs
    try:
        return jobs.ensure_repo(folder)
    except RuntimeError as e:
        raise ValueError(f"Git could not start here: {e}") from None


def project_id(path: str | Path) -> str:
    """A project's id: a short hash of its folder's path, the same on every run on this machine."""
    folder = Path(path).expanduser()
    try:
        folder = folder.resolve()
    except (OSError, RuntimeError):
        pass
    text = folder.as_posix().lower() if sys.platform in ("darwin", "win32") else folder.as_posix()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
