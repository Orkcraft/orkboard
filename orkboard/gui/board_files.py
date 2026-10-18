"""The Files pane's commands (docs/specs/37-board-and-line.md §8): the shown project's tree, a file read, written and
opened in the system's app.

    files = Files(projects)
    host.commands.update(files.commands())   # files.tree, files.read, files.write, files.reveal

Nothing leaves the project (a `..`, a link out); `.git/` and `.orkcraft/` are never shown, read or written; what may
hold a secret (the Warder's `is_secret`: `.env*`, keys, certificates, credentials) is listed but never read or
written: *open it in your own editor*. A Board page (`pages/ideas/`, `pages/tracks/`) opens on the Board, which
commits it (spec 35 §13), so it is never saved from here. A save is refused when the file changed on disk since it
was read (its `mtime`, in microseconds).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from orkboard.gui import markdown
from orkboard.gui.board_background import Background
from orkboard.gui.ideas_args import IdeasError, _str
from orkboard.gui.ideas_goals import HIDDEN_DIRS, NO_SECRETS
from orkboard.hooks.warder import is_secret
from orkboard.realm import event_log
from orkboard.realm.idea_git import BOARD_PAGE, lock_of

LARGE = 1024 * 1024                  # a file over this is not read: its size and Open in the system
SNIFF = 8192                         # the bytes looked at for a NUL (a binary file)
MARKDOWN = (".md", ".markdown", ".mdown", ".mkd")
TREE_MAX = 5000                      # the entries one folder lists at most
CHANGED = "changed on disk: reload"


def _mtime(st: os.stat_result) -> int:
    return st.st_mtime_ns // 1000


def kind_of(name: str) -> str:
    return "markdown" if name.lower().endswith(MARKDOWN) else "text"


class Files:
    def __init__(self, projects: Any, opener: Callable[[Path], None] | None = None) -> None:
        self.projects = projects
        self.background = Background()
        self.opener = opener or _open_in_system

    # -- paths -----------------------------------------------------------------------------------------------

    def _root(self) -> Path:
        return self.projects.current(need=True).root.resolve()

    def _resolve(self, raw: object, allow_root: bool = False) -> tuple[Path, Path, str]:
        """(the project's folder, the path resolved, the path as the project names it); refused when it leaves the
        project or is under `.git/` or `.orkcraft/`."""
        root = self._root()
        text = str(raw or "").replace("\\", "/").strip()
        if "\0" in text or text.startswith("/") or (len(text) > 1 and text[1] == ":"):
            raise IdeasError("That path is not in the project")
        parts = [p for p in text.split("/") if p and p != "."]
        if ".." in parts:
            raise IdeasError("That path leaves the project")
        if not parts and not allow_root:
            raise IdeasError("path is missing")
        asked = root.joinpath(*parts)
        try:
            real = asked.resolve()
        except (OSError, RuntimeError):
            raise IdeasError("That path cannot be read") from None
        if real != root and root not in real.parents:
            raise IdeasError("That path leaves the project")
        rel = "/".join(parts)
        inside = real.relative_to(root).parts
        if any(p in HIDDEN_DIRS for p in parts) or any(p in HIDDEN_DIRS for p in inside):
            raise IdeasError("That folder is the repository's own state: it is not shown")
        return root, real, rel

    @staticmethod
    def _secret(rel: str, root: Path, real: Path) -> bool:
        """The name asked for, or the file it resolves to, may hold a secret (a link to a `.env` is a `.env`)."""
        return is_secret(rel) or (real != root and is_secret(real.relative_to(root).as_posix()))

    # -- the tree --------------------------------------------------------------------------------------------

    def tree(self, args: dict) -> dict:
        """One level of a folder: folders first, then files, by name; `.git/` and `.orkcraft/` never; the git-ignored
        entries only with `ignored`."""
        root, folder, rel = self._resolve(args.get("dir") or "", allow_root=True)
        if not folder.is_dir():
            raise IdeasError("That folder is gone")
        show_ignored = args.get("ignored") is True
        rows = []
        try:
            entries = sorted(os.scandir(folder), key=lambda e: e.name.lower())
        except OSError:
            raise IdeasError("That folder cannot be read") from None
        for e in entries[:TREE_MAX]:
            if e.name in HIDDEN_DIRS:
                continue
            path = f"{rel}/{e.name}" if rel else e.name
            try:
                is_dir = e.is_dir()             # a link to a folder in the project is one
                size = 0 if is_dir else e.stat(follow_symlinks=False).st_size
            except OSError:
                is_dir, size = False, 0
            rows.append({"name": e.name, "path": path, "dir": is_dir, "size": size, "secret": is_secret(path)})
        if not show_ignored and rows:
            hidden = _ignored(root, [r["path"] + ("/" if r["dir"] else "") for r in rows])
            rows = [r for r in rows if r["path"] not in hidden]
        rows.sort(key=lambda r: (not r["dir"], r["name"].lower()))
        return {"entries": rows}

    # -- one file --------------------------------------------------------------------------------------------

    def read(self, args: dict) -> dict:
        """A file as the preview shows it: Markdown (its text and `html`), text, or only its size (binary, over 1 MB,
        or `secret`: never its text)."""
        root, real, rel = self._resolve(_str(args, "path", 1000))
        if real.is_dir():
            raise IdeasError("That is a folder")
        if args.get("device") == "phone" and kind_of(real.name) != "markdown":
            raise IdeasError("The phone reads Markdown files only")    # a `.md` link to code is code
        try:
            st = real.stat()
        except OSError:
            raise IdeasError("That file is gone") from None
        out: dict[str, Any] = {"path": rel, "size": st.st_size, "mtime": _mtime(st)}
        if self._secret(rel, root, real):
            return {**out, "kind": "secret"}
        if st.st_size > LARGE:
            return {**out, "kind": "large"}
        try:
            data = real.read_bytes()
        except OSError:
            raise IdeasError("That file cannot be read") from None
        try:
            if b"\0" in data[:SNIFF]:
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "a NUL")
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return {**out, "kind": "binary"}
        kind = kind_of(rel)
        out.update(kind=kind, text=text)
        if kind == "markdown":
            out["html"] = markdown.render(text)
        return out

    def write(self, args: dict) -> dict:
        """A file saved as the person edited it, refused in words: outside the project, a Board page, a secret-looking
        path, or a file that changed on disk since it was read (`mtime`). A new file is saved with `mtime` null."""
        text = args.get("text")
        if not isinstance(text, str):
            raise IdeasError("text is not text")
        root, real, rel = self._resolve(_str(args, "path", 1000))
        if BOARD_PAGE.search(rel) or BOARD_PAGE.search(real.relative_to(root).as_posix()):
            raise IdeasError("That is a Board page: edit it on the Board, which commits it")
        if self._secret(rel, root, real):
            raise IdeasError(NO_SECRETS)
        data = text.encode("utf-8")
        if len(data) > LARGE:
            raise IdeasError("That text is larger than 1 MB: edit it in your own editor")
        mtime = args.get("mtime")
        with lock_of(root):
            if real.is_dir():
                raise IdeasError("That is a folder")
            if real.exists():
                if isinstance(mtime, bool) or not isinstance(mtime, int) or _mtime(real.stat()) != mtime:
                    raise IdeasError(CHANGED)
            elif mtime is not None:
                raise IdeasError(CHANGED)                  # it was read, and is gone since
            if not real.parent.is_dir():
                raise IdeasError("Its folder is gone")
            mode = real.stat().st_mode & 0o7777 if real.exists() else None
            fd, tmp = tempfile.mkstemp(dir=real.parent, prefix=".orkboard-", suffix=".tmp")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                if mode is not None:
                    os.chmod(tmp, mode)
                os.replace(tmp, real)
            except OSError as e:
                Path(tmp).unlink(missing_ok=True)
                raise IdeasError(f"That file could not be saved: {e.strerror or e}") from None
            new = _mtime(real.stat())
        project = self.projects.current(need=True)
        if not project.host.demo:                     # its kind and size only: never the path or the text
            event_log.record(project.root, event_log.FILE_SAVED, kind=kind_of(rel), bytes=len(data))
        return {"ok": True, "mtime": new}

    def reveal(self, args: dict) -> dict:
        """The file in the system's app for it, started off the server's thread (desktop only: the phone may not send
        it). The path is checked at once; an app that did not open is told on the project's bus (`RAN`)."""
        if args.get("device") == "phone":
            raise IdeasError("Not from a phone")
        root, real, rel = self._resolve(_str(args, "path", 1000))
        if not real.exists():
            raise IdeasError("That file is gone")
        if self._secret(rel, root, real):
            raise IdeasError(NO_SECRETS)
        project = self.projects.current(need=True)

        def work() -> str:
            try:
                self.opener(real)
            except IdeasError as e:                 # nothing else shows it: the press already got its answer
                project.host.call(lambda: project.toast(str(e), title="Open in the system", severity="warning"))
                raise
            return ""
        return self.background.start(project, "reveal", "open", work)

    def commands(self) -> dict[str, Callable[[dict], Any]]:
        return {"files.tree": self.tree, "files.read": self.read, "files.write": self.write,
                "files.reveal": self.reveal}


def _ignored(root: Path, paths: list[str]) -> set[str]:
    """The paths git ignores here (none when the folder has no git), without a trailing slash."""
    if not (root / ".git").exists():
        return set()
    try:
        done = subprocess.run(["git", "check-ignore", "--stdin", "-z"], cwd=root, input="\0".join(paths) + "\0",
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    return {p.rstrip("/") for p in done.stdout.split("\0") if p}


def _open_in_system(path: Path) -> None:
    """The system's app for a file: `open` on macOS, the shell's association on Windows, `xdg-open` elsewhere."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif os.name == "nt":
            os.startfile(str(path))           # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        raise IdeasError(f"No app opened it: {e.strerror or e}") from None
