"""The person's git on a project's own checkout (docs/specs/37-board-and-line.md §8): what changed, a file's diff,
a commit of the files they ticked, a branch switched, a pull (fast-forward only) and a push (on their press only).

    git = RepoGit(repo_root)
    git.status("dev")                    # {"branch", "work_branch", "upstream", "ahead", "behind", "files": [...]}
    git.diff("src/app.py")               # one file in `ideas.diff`'s shape
    git.commit(["src/app.py"], "Fix")    # the new commit's sha
    git.switch("main"); git.pull(); git.push()

Every call is `git` with fixed arguments (no shell), in the repository's root checkout, under its one lock
(`idea_git.lock_of`), the lock the runner and the Board's tree take: never in a task's worktree or the Board's tree.
No rebase, reset, force or stash. A secret-looking file (the Warder's `is_secret`) and the Board's own state
(`.orkcraft/`) are never offered nor committed. Errors are ValueError, in words. No face, no model, no bus.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from orkboard.hooks.warder import is_secret
from orkboard.realm.idea_git import BRANCH_NAME, PATCH_FILE, lock_of

GIT_TIMEOUT_S = 60
REMOTE_TIMEOUT_S = 120               # a pull or a push talks to origin
MESSAGE_CHARS = 5_000
COUNT_MAX = 1024 * 1024              # an untracked file's lines are counted up to this size
_STATES = {"M": "modified", "T": "modified", "A": "added", "D": "deleted", "R": "renamed", "C": "added",
           "U": "conflicted"}


def offered(path: str) -> bool:
    """Whether a changed file is shown and may be committed: not secret-looking, not the Board's own state."""
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    return bool(parts) and not is_secret(path) and ".orkcraft" not in parts and ".git" not in parts


class RepoGit:
    def __init__(self, repo_root: Path) -> None:
        self.root = Path(repo_root).resolve()
        self.lock = lock_of(self.root)

    def _git(self, *args: str, timeout: int = GIT_TIMEOUT_S) -> subprocess.CompletedProcess:
        """`git <args>` in the root checkout, under the repository's lock; never a prompt for a password."""
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
        with self.lock:
            try:
                return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True,
                                      timeout=timeout, env=env)
            except subprocess.TimeoutExpired:
                raise ValueError("Git took too long and was stopped") from None
            except OSError as e:
                raise ValueError(f"Git is not installed or did not answer: {e}") from None

    def _ok(self, *args: str, timeout: int = GIT_TIMEOUT_S) -> str:
        done = self._git(*args, timeout=timeout)
        if done.returncode != 0:
            raise ValueError(" ".join((done.stderr or done.stdout).split())[:300] or f"git {args[0]} failed")
        return done.stdout

    # -- reading ---------------------------------------------------------------------------------------------

    def _head(self) -> bool:
        return self._git("rev-parse", "--verify", "-q", "HEAD").returncode == 0

    def status(self, work_branch: str = "") -> dict:
        """The branch, the work branch it is compared with by the page, its upstream with ahead / behind, and the
        changed files with their + / − (an untracked file's lines all added)."""
        out = self._ok("status", "--porcelain=v2", "--branch", "-z", "--untracked-files=all")
        branch, upstream, ahead, behind = "", "", 0, 0
        files: list[dict] = []
        records = out.split("\0")
        i = 0
        while i < len(records):
            rec = records[i]
            i += 1
            if rec.startswith("# branch.head "):
                head = rec[len("# branch.head "):]
                branch = "" if head == "(detached)" else head
            elif rec.startswith("# branch.upstream "):
                upstream = rec[len("# branch.upstream "):]
            elif rec.startswith("# branch.ab "):
                m = re.match(r"# branch\.ab \+(\d+) -(\d+)", rec)
                if m:
                    ahead, behind = int(m.group(1)), int(m.group(2))
            elif rec.startswith("1 "):
                xy, path = rec.split(" ", 8)[1], rec.split(" ", 8)[8]
                files.append({"path": path, "status": _state(xy)})
            elif rec.startswith("2 "):
                xy, path = rec.split(" ", 9)[1], rec.split(" ", 9)[9]
                i += 1                                  # the name it had
                files.append({"path": path, "status": "renamed" if "R" in xy else _state(xy)})
            elif rec.startswith("u "):
                files.append({"path": rec.split(" ", 10)[10], "status": "conflicted"})
            elif rec.startswith("? "):
                files.append({"path": rec[2:], "status": "untracked"})
        counts = self._numstat()
        shown = []
        for f in files:
            if not offered(f["path"]):
                continue
            added, removed = counts.get(f["path"], (0, 0))
            if f["status"] == "untracked":
                added, removed = self._lines(f["path"]), 0
            shown.append({**f, "added": added, "removed": removed})
        return {"branch": branch, "work_branch": work_branch, "upstream": upstream, "ahead": ahead,
                "behind": behind, "files": shown}

    def _numstat(self) -> dict[str, tuple[int, int]]:
        if not self._head():
            return {}
        out = {}
        for ln in self._git("diff", "--numstat", "--no-renames", "HEAD").stdout.splitlines():
            a, r, name = (ln.split("\t", 2) + ["", "", ""])[:3]
            out[name] = (int(a) if a.isdigit() else 0, int(r) if r.isdigit() else 0)
        return out

    def _lines(self, rel: str) -> int:
        path = self.root / rel
        try:
            if path.is_symlink() or path.stat().st_size > COUNT_MAX:
                return 0
            data = path.read_bytes()
        except OSError:
            return 0
        if b"\0" in data[:8192]:
            return 0
        return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)

    def changed(self) -> dict[str, str]:
        """The files that changed and may be offered: path → status."""
        return {f["path"]: f["status"] for f in self.status()["files"]}

    def diff(self, rel: str) -> dict:
        """One changed file against the last commit, in `ideas.diff`'s shape (a patch over PATCH_FILE: None)."""
        rel = _rel(rel)
        if not offered(rel):
            raise ValueError("That file may hold secrets: open it in your own editor")
        status = self.changed().get(rel)
        if status is None:
            raise ValueError("That file has no changes")
        if status == "untracked":
            done = self._git("diff", "--no-color", "--no-index", "--", os.devnull, rel)
            patch = done.stdout if done.returncode in (0, 1) else ""
        elif self._head():
            patch = self._git("diff", "--no-color", "--no-renames", "HEAD", "--", rel).stdout
        else:
            patch = self._git("diff", "--no-color", "--no-renames", "--cached", "--", rel).stdout
        added = sum(1 for ln in patch.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
        removed = sum(1 for ln in patch.splitlines() if ln.startswith("-") and not ln.startswith("---"))
        truncated = len(patch) > PATCH_FILE
        branch = self.status()["branch"]
        return {"base": "HEAD", "branch": branch, "commits": [], "truncated": truncated,
                "files": [{"path": rel, "added": added, "removed": removed, "patch": None if truncated else patch}]}

    # -- writing ---------------------------------------------------------------------------------------------

    def commit(self, paths: list[str], message: str) -> str:
        """A commit of the ticked files only (what else was staged stays staged, out of it): the new commit's sha."""
        message = message.strip() if isinstance(message, str) else ""
        if not message:
            raise ValueError("A commit needs a message")
        if len(message) > MESSAGE_CHARS:
            raise ValueError(f"The message is longer than {MESSAGE_CHARS} characters")
        if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
            raise ValueError("Tick the files to commit")
        rels = list(dict.fromkeys(_rel(p) for p in paths))
        with self.lock:
            changed = self.changed()
            for rel in rels:
                if not offered(rel):
                    raise ValueError(f"{rel} may hold secrets: it is never committed from here")
                if rel not in changed:
                    raise ValueError(f"{rel} has no changes to commit")
            self._ok("add", "-A", "--", *rels)
            if self._head():
                self._ok("commit", "--only", "-m", message, "--", *rels)
            else:                                       # the first commit: nothing else may be staged
                staged = [p for p in self._ok("diff", "--cached", "--name-only", "-z").split("\0") if p]
                extra = [p for p in staged if p not in rels]
                if extra:
                    self._ok("restore", "--staged", "--", *extra)
                self._ok("commit", "-m", message)
            return self._ok("rev-parse", "HEAD").strip()

    def switch(self, branch: str) -> None:
        """The root checkout on another branch; refused with uncommitted changes (untracked files stay)."""
        name = branch.strip() if isinstance(branch, str) else ""
        if not BRANCH_NAME.fullmatch(name) or ".." in name or name.startswith(("-", "/")) or name.endswith("/"):
            raise ValueError(f"{name!r} is not a branch name")
        with self.lock:
            dirty = [ln for ln in self._ok("status", "--porcelain", "--untracked-files=no").splitlines() if ln.strip()]
            if dirty:
                raise ValueError(f"{len(dirty)} file{'s' if len(dirty) != 1 else ''} with uncommitted changes: "
                                 "commit them before you switch branch")
            self._ok("switch", name)

    def pull(self) -> str:
        """`git pull --ff-only` from the upstream: what it brought, in a sentence. A branch that diverged is refused."""
        with self.lock:
            st = self.status()
            if not st["branch"]:
                raise ValueError("No branch is checked out: switch to one first")
            if not st["upstream"]:
                raise ValueError(f"{st['branch']} has no upstream on origin to pull from")
            old = self._ok("rev-parse", "HEAD").strip()
            done = self._git("pull", "--ff-only", "--no-rebase", timeout=REMOTE_TIMEOUT_S)
            if done.returncode != 0:
                text = " ".join((done.stderr or done.stdout).split())
                if "fast-forward" in text.lower() or "diverg" in text.lower():
                    raise ValueError(f"{st['branch']} and {st['upstream']} have diverged: a pull only fast-forwards, "
                                     "so nothing was changed")
                raise ValueError(f"The pull failed: {text[:300]}")
            new = self._ok("rev-parse", "HEAD").strip()
            if new == old:
                return f"{st['branch']} is up to date with {st['upstream']}"
            n = len([c for c in self._ok("rev-list", f"{old}..{new}").split() if c])
            return f"Pulled {n} commit{'s' if n != 1 else ''} into {st['branch']}"

    def push(self) -> tuple[str, str]:
        """`git push` of the current branch to origin (its upstream, else origin/<branch>, set as its upstream):
        (the branch, what was done in a sentence). Never forced."""
        with self.lock:
            st = self.status()
            branch = st["branch"]
            if not branch:
                raise ValueError("No branch is checked out: switch to one first")
            if "origin" not in self._ok("remote").split():
                raise ValueError("This repository has no origin to push to")
            if st["upstream"]:
                done = self._git("push", timeout=REMOTE_TIMEOUT_S)
            else:
                done = self._git("push", "--set-upstream", "origin", branch, timeout=REMOTE_TIMEOUT_S)
            if done.returncode != 0:
                raise ValueError("The push failed: " + " ".join((done.stderr or done.stdout).split())[:300])
            return branch, f"Sent {branch} to origin"


def _state(xy: str) -> str:
    for c in xy:
        if c in _STATES:
            return _STATES[c]
    return "modified"


def _rel(path: str) -> str:
    """A path in the repository as git names it; one that leaves it is refused."""
    rel = str(path or "").replace("\\", "/").strip()
    parts = [p for p in rel.split("/") if p and p != "."]
    if not parts or rel.startswith("/") or ".." in parts or "\0" in rel or rel.startswith("-"):
        raise ValueError("That path is not in the project")
    return "/".join(parts)
