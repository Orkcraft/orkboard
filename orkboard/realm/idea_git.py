"""The git of an idea's tasks (docs/specs/29a-board-focus.md §5): a worktree per task, the gate, the merge.

    g = IdeaGit(repo_root)
    path, branch = g.prepare(slug, task_id, "main")      # a worktree off the local `main`, branch idea/<slug>/<id>
    g.commits(path, base) / g.touched(path, base)        # what the task committed since it left the base
    ok, tail = g.gate(path, cancel)                      # the critical tests + the test files of touched modules
    commit, subjects, note = g.land(path, branch, "main", push=True)   # rebase, fast-forward main, push
    read_secret(state_dir, slug, todo_id)                # a `secret` to-do's value, from where part A stored it
    g.ensure_branch("dev") / g.branches()                # the branch results merge into (made when missing)
    g.stats(path, base) / g.diff(branch, base)           # what a task changed, counted / with its patches (Review)
    parse_tests(output)                                  # pytest's summary line → {"passed","failed","failing","tail"}
    tree = BoardTree(repo_root, state_dir, "llm-wiki/general", lambda: "dev")   # the Board's pages (spec 35 §13)
    tree.ensure(); tree.note("Dark mode", "drafted"); tree.flush(force=True)    # one commit of its pages, `dev` moved

Every call runs git with fixed arguments (no shell). One lock per repository (`lock_of`) holds every change
of refs and worktrees, so two tasks never rebase or fast-forward at once. A task that fails or conflicts never
moves `merge_into`: the rebase happens on its own branch in its own worktree, and `merge_into` moves only by
a fast-forward to a commit that already holds it.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import NamedTuple

from orkboard.realm import gate_config, jobs, worktrees

GIT_TIMEOUT_S = 60
PUSH_TIMEOUT_S = 120
CRITICAL_TESTS = gate_config.CRITICAL_TESTS     # only the default `always`; a repository's orkcraft.toml names its own
TEST_TAIL = 3000
GATE_KEEP = 60000
PATCH_FILE = 60 * 1024               # a file's patch shown up to this, else "too large to show"
PATCH_ALL = 300 * 1024               # … and all of a result's patches up to this
BRANCH_NAME = re.compile(r"[\w./-]{1,100}")
SECRETS_FILE = "secrets.json"
KEYRING_SERVICE = "orkline"

_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


class Conflict(RuntimeError):
    """The task's branch does not rebase cleanly onto `merge_into`."""


def lock_of(repo_root: Path) -> threading.RLock:
    """The one lock of a repository: refs, worktrees and the root checkout change under it."""
    key = str(Path(repo_root).resolve())
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.RLock())


def _git(cwd: Path, *args: str, timeout: int = GIT_TIMEOUT_S) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _ok(proc: subprocess.CompletedProcess) -> str:
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip()[:300] or f"git failed ({proc.returncode})")
    return proc.stdout.strip()


def branch_of(slug: str, task_id: str) -> str:
    return f"idea/{slug}/{task_id}"


def _worktree_id(slug: str, task_id: str) -> str:
    raw = re.sub(r"[^a-z0-9_-]+", "-", f"idea-{slug}-{task_id}".lower()).strip("-")
    return raw[:64].rstrip("-") or "idea"


def test_files(touched: list[str], root: Path) -> list[str]:
    """The critical tests, and the test files named after the modules the diff touches (CLAUDE.md "Alpha"):
    `orkcraft/realm/ideas.py` → `tests/test_ideas.py`, a touched test file itself; only those that exist."""
    return gate_config.gate_files(gate_config.Gate(), touched, root)


class GateRun(NamedTuple):
    """What the gate did: `ran` is False when it found nothing to run (never green), `code` the command's exit code."""
    ok: bool
    out: str
    ran: bool = True
    command: str = ""
    code: int | None = None


class IdeaGit:
    def __init__(self, repo_root: Path) -> None:
        self.root = Path(repo_root)
        self.lock = lock_of(self.root)

    # -- the task's worktree ---------------------------------------------------------------------

    def prepare(self, slug: str, task_id: str, base: str) -> tuple[Path, str]:
        """A fresh worktree on branch `idea/<slug>/<task id>`, cut from the local `base` (a leftover of an
        earlier try is removed, and its branch cut anew)."""
        branch = branch_of(slug, task_id)
        if not worktrees.valid_branch(self.root, branch):
            raise RuntimeError(f"{branch!r} is not a valid branch name")
        with self.lock:
            _ok(_git(self.root, "rev-parse", "--verify", f"refs/heads/{base}"))
            path = worktrees.worktree_path(self.root, _worktree_id(slug, task_id))
            self.remove(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            _ok(_git(self.root, "worktree", "add", "-B", branch, str(path), base))
        return path, branch

    def remove(self, path: Path) -> None:
        with self.lock:
            if path.exists():
                try:
                    worktrees.remove(self.root, path, force=True)
                except worktrees.WorktreeError:
                    pass
            _git(self.root, "worktree", "prune")

    def head(self, path: Path) -> str:
        return _ok(_git(path, "rev-parse", "HEAD"))

    def commits(self, path: Path, base: str) -> list[str]:
        """The subjects of what the branch committed since it left `base`, oldest first."""
        out = _git(path, "log", "--reverse", "--format=%s", f"{base}..HEAD").stdout
        return [ln for ln in out.splitlines() if ln.strip()]

    def touched(self, path: Path, base: str) -> list[str]:
        out = _git(path, "diff", "--name-only", f"{base}...HEAD").stdout
        return [ln for ln in out.splitlines() if ln.strip()]

    def dirty(self, path: Path) -> bool:
        return bool(_git(path, "status", "--porcelain").stdout.strip())

    def commit_left(self, path: Path, message: str) -> bool:
        """Commit what the session left uncommitted (a session in `acceptEdits` edits files but may not run git):
        True when it made a commit. Orkline is its author; ignored files stay out, as `git add -A` leaves them."""
        if not self.dirty(path):
            return False
        _ok(_git(path, "add", "-A"))
        _ok(_git(path, "-c", "user.name=Orkline", "-c", "user.email=orkline@localhost", "commit", "-q", "-m",
                 message.strip()[:200] or "Orkline: the task's work"))
        return True

    # -- the gate --------------------------------------------------------------------------------

    def gate(self, path: Path, base: str, cancel: threading.Event,
             timeout_s: int = jobs.TEST_TIMEOUT_S) -> tuple[bool, str]:
        """(passed, the output's tail) of the gate; a run that found nothing to run is not passed."""
        run = self.gate_run(path, base, cancel, timeout_s)
        out = run.out
        return run.ok and run.ran, out[-TEST_TAIL - 200:] if len(out) > TEST_TAIL + 200 else out

    def gate_run(self, path: Path, base: str, cancel: threading.Event,
                 timeout_s: int = jobs.TEST_TIMEOUT_S) -> GateRun:
        """The gate (spec 37 §5): the repository's `[gate]` in orkcraft.toml, else pytest on the critical tests and the
        touched modules'. Nothing to run is `ran=False`, never a pass; the whole run is `out` (the command, then its
        output up to GATE_KEEP)."""
        gate = gate_config.read(self.root)
        note = f"\n! {gate.error}" if gate.error else ""
        files = gate_config.gate_files(gate, self.touched(path, base), path)
        if gate.custom:
            line = gate_config.command(gate, files)
            argv = gate_config.test_argv(line) if line else []
        else:
            line = f"python -m pytest -q {' '.join(files)}"
            # No cache, no bytecode: the gate leaves the worktree as the session left it (land checks it is clean).
            argv = [self.python(), "-m", "pytest", "-q", "-p", "no:cacheprovider", *files] if files else []
        if not argv:
            return GateRun(True, f"no tests ran: no test file maps to what the task touched{note}", False, line or gate.run)
        if gate.timeout_min:
            timeout_s = int(gate.timeout_min * 60)
        try:
            proc = subprocess.Popen(argv, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                    start_new_session=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        except OSError as e:
            return GateRun(False, f"$ {line}\n{argv[0]} could not start: {e}{note}", True, line, 127)
        out_box: list[str] = []
        reader = threading.Thread(target=lambda: out_box.append(proc.stdout.read() if proc.stdout else ""),
                                  daemon=True)
        reader.start()
        jobs._wait(proc, cancel, timeout_s, "ideas/gate")
        reader.join(5)
        out = out_box[0] if out_box else ""
        return GateRun(proc.returncode == 0, f"$ {line}\n{out[-GATE_KEEP:]}{note}", True, line, proc.returncode)

    def python(self) -> str:
        """The repository's own Python when it has one (`.venv`, where its test tools are), else Orkline's."""
        for rel in (".venv/bin/python", ".venv/Scripts/python.exe"):
            if (self.root / rel).is_file():
                return str(self.root / rel)
        return sys.executable

    # -- the branch results merge into ------------------------------------------------------------

    def branches(self) -> list[str]:
        """The local branches, the task branches (idea/…) left out."""
        out = _git(self.root, "for-each-ref", "--format=%(refname:short)", "refs/heads").stdout.split()
        return [b for b in out if not b.startswith("idea/")]

    def default_branch(self) -> str:
        """The repository's default branch: origin's HEAD, else main or master, else the one checked out."""
        ref = _git(self.root, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD").stdout.strip()
        names = [ref.split("/", 1)[1]] if "/" in ref else []
        names += ["main", "master", _git(self.root, "symbolic-ref", "-q", "--short", "HEAD").stdout.strip()]
        return next((n for n in names if n and worktrees.branch_exists(self.root, n)), "")

    def ensure_branch(self, name: str) -> bool:
        """`name` exists locally: made from the default branch's head when missing (True when made)."""
        if not BRANCH_NAME.fullmatch(name or "") or ".." in name or not worktrees.valid_branch(self.root, name):
            raise RuntimeError(f"{name!r} is not a branch name")
        with self.lock:
            if worktrees.branch_exists(self.root, name):
                return False
            base = self.default_branch()
            if not base:
                raise RuntimeError("the repository has no commit to start the branch from")
            _ok(_git(self.root, "branch", name, base))
        return True

    def reopen(self, slug: str, task_id: str) -> Path:
        """The task's worktree on its branch: as it is, else made again from the branch (a held result)."""
        branch = branch_of(slug, task_id)
        path = worktrees.worktree_path(self.root, _worktree_id(slug, task_id))
        with self.lock:
            if (path / ".git").exists():
                return path
            if not worktrees.branch_exists(self.root, branch):
                raise RuntimeError("the task's branch is gone")
            self.remove(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            _ok(_git(self.root, "worktree", "add", str(path), branch))
        return path

    def merge_in(self, path: Path, into: str) -> list[str]:
        """Merge `into` into the task's branch to fix a conflict: the files still in conflict (the merge stays
        open for the session to resolve them), [] when it merged cleanly."""
        with self.lock:
            done = _git(path, "-c", "user.name=Orkline", "-c", "user.email=orkline@localhost", "merge", "--no-edit",
                        into, timeout=PUSH_TIMEOUT_S)
            if done.returncode == 0:
                return []
            files = _git(path, "diff", "--name-only", "--diff-filter=U").stdout.split()
            if not files:
                _git(path, "merge", "--abort")
                raise RuntimeError((done.stderr or done.stdout).strip()[:300] or "the merge failed")
            return files

    def merging(self, path: Path) -> bool:
        return _git(path, "rev-parse", "-q", "--verify", "MERGE_HEAD").returncode == 0

    # -- what a task changed -----------------------------------------------------------------------

    def stats(self, path: Path, base: str) -> dict:
        """{"files", "added", "removed"} of what the branch changed since `base`."""
        files = added = removed = 0
        for ln in _git(path, "diff", "--numstat", f"{base}...HEAD").stdout.splitlines():
            a, _, r = ln.split("\t", 2)[:3] if ln.count("\t") >= 2 else ("0", "0", "")
            files += 1
            added += int(a) if a.isdigit() else 0
            removed += int(r) if r.isdigit() else 0
        return {"files": files, "added": added, "removed": removed}

    def diff(self, branch: str, base: str) -> dict:
        """The commits and the files a branch changed since `base`, each file's patch (a file's up to PATCH_FILE
        and all of them up to PATCH_ALL; the rest None: too large to show)."""
        rng = f"{base}...{branch}"
        commits = []
        for ln in _git(self.root, "log", "--reverse", "--format=%H%x09%s", f"{base}..{branch}").stdout.splitlines():
            sha, _, subject = ln.partition("\t")
            commits.append({"sha": sha[:10], "subject": subject})
        counts = {}
        for ln in _git(self.root, "diff", "--numstat", "--no-renames", rng).stdout.splitlines():
            a, r, name = (ln.split("\t", 2) + ["", "", ""])[:3]
            counts[name] = (int(a) if a.isdigit() else 0, int(r) if r.isdigit() else 0)
        patches: dict[str, str] = {}
        whole = _git(self.root, "diff", "--no-renames", "--no-color", rng, timeout=PUSH_TIMEOUT_S).stdout
        for chunk in re.split(r"(?m)^(?=diff --git )", whole):
            m = re.match(r"diff --git a/(.*?) b/(.*)\n", chunk)
            if m:
                patches[m.group(2)] = chunk
        files, used, truncated = [], 0, False
        for name, (added, removed) in counts.items():
            patch: str | None = patches.get(name, "")
            if patch is not None and (len(patch) > PATCH_FILE or used + len(patch) > PATCH_ALL):
                patch, truncated = None, True
            used += len(patch or "")
            files.append({"path": name, "added": added, "removed": removed, "patch": patch})
        return {"base": base, "branch": branch, "commits": commits, "files": files, "truncated": truncated}

    # -- the merge -------------------------------------------------------------------------------

    def _checked_out_in_root(self, branch: str) -> bool:
        head = _git(self.root, "symbolic-ref", "-q", "HEAD").stdout.strip()
        return head == f"refs/heads/{branch}"

    def land(self, path: Path, branch: str, into: str, push: bool = True) -> tuple[str, list[str], str]:
        """Rebase the task's branch onto the current `into`, fast-forward `into` to it and push when asked:
        (the new head of `into`, the subjects it brought, a note). Raises Conflict on a conflicting rebase,
        RuntimeError when `into` cannot move; either way `into` is as it was."""
        with self.lock:
            if self.dirty(path):
                raise RuntimeError("the task left uncommitted changes")
            # a branch that already holds `into` (a conflict fixed by merging it in) is fast-forwarded as it is
            held = _git(path, "merge-base", "--is-ancestor", into, "HEAD").returncode == 0
            rebase = None if held else _git(path, "rebase", into, timeout=PUSH_TIMEOUT_S)
            if rebase is not None and rebase.returncode != 0:
                files = _git(path, "diff", "--name-only", "--diff-filter=U").stdout.split()
                _git(path, "rebase", "--abort")
                raise Conflict("conflicts with " + into + (" in " + ", ".join(files) if files else ""))
            new = self.head(path)
            old = _ok(_git(self.root, "rev-parse", f"refs/heads/{into}"))
            if _git(self.root, "merge-base", "--is-ancestor", old, new).returncode != 0:
                raise RuntimeError(f"{into} moved during the merge")
            subjects = [s for s in _git(self.root, "log", "--reverse", "--format=%s", f"{old}..{new}")
                        .stdout.splitlines() if s.strip()]
            if old != new:
                self._fast_forward(into, old, new)
            note = self.push(into) if push else ""
        return new, subjects, note

    def _fast_forward(self, into: str, old: str, new: str) -> None:
        if self._checked_out_in_root(into):
            touched = [ln for ln in _git(self.root, "diff", "--name-only", old, new).stdout.splitlines() if ln]
            busy = [ln for ln in _git(self.root, "status", "--porcelain", "--", *touched).stdout.splitlines()
                    if ln.strip()] if touched else []
            if busy:
                files = ", ".join(ln[3:] for ln in busy)
                raise RuntimeError(f"{into} is checked out with uncommitted changes in {files}")
            _ok(_git(self.root, "merge", "--ff-only", new, timeout=PUSH_TIMEOUT_S))
        else:
            _ok(_git(self.root, "update-ref", f"refs/heads/{into}", new, old))

    def push(self, branch: str) -> str:
        """`git push origin <branch>` when there is an origin: a note ("" when pushed or no origin)."""
        if "origin" not in _git(self.root, "remote").stdout.split():
            return ""
        done = _git(self.root, "push", "origin", branch, timeout=PUSH_TIMEOUT_S)
        if done.returncode != 0:
            return f"push failed: {(done.stderr or done.stdout).strip()[:200]}"
        return ""


# -- secrets of `secret` to-dos (stored by part A, §3) ------------------------------------------------

def secret_keys(slug: str, todo_id: str) -> tuple[str, ...]:
    return (f"ideas/{slug}/{todo_id}", f"{slug}/{todo_id}")


def read_secret(state_dir: Path, slug: str, todo_id: str) -> str | None:
    """A `secret` to-do's value from where part A stores it: the OS keychain (`keyring`, service "orkline"), else
    `<state_dir>/secrets.json` (flat by key, or {slug: {id: v}})."""
    keys = secret_keys(slug, todo_id)
    try:
        import keyring                                         # type: ignore[import-not-found]
        for key in keys:
            value = keyring.get_password(KEYRING_SERVICE, key)
            if value:
                return value
    except Exception:
        pass
    try:
        data = json.loads((Path(state_dir) / SECRETS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    for key in keys:
        if isinstance(data.get(key), str):
            return data[key]
    nested = data.get(slug) if isinstance(data.get(slug), dict) else (data.get("ideas") or {}).get(slug)
    value = nested.get(todo_id) if isinstance(nested, dict) else None
    return value if isinstance(value, str) else None


ENV_NAME = re.compile(r"\b[A-Z][A-Z0-9_]{1,63}\b")


def env_name(title: str) -> str:
    """The environment variable a `secret` to-do's title names (`Add API_KEY` → `API_KEY`), else ""."""
    names = ENV_NAME.findall(title or "")
    return next((n for n in names if "_" in n), names[0] if names else "")


_SUMMARY = re.compile(r"(\d+) (passed|failed|error|errors)\b")
_FAILED_LINE = re.compile(r"^(?:FAILED|ERROR) (\S+)")


def has_summary(output: str) -> bool:
    """pytest's summary line is in the output (a run of another command has none: only its exit code speaks)."""
    return any(_SUMMARY.search(ln) and (" in " in ln or ln.strip().startswith("=")) for ln in (output or "").splitlines())


def parse_tests(output: str, keep_lines: int = 40) -> dict:
    """The gate's run in the shape Review shows: pytest's summary line (`2 failed, 18 passed in 1.2s`) gives the
    counts, its `FAILED path::name` lines the names (at most 20). A run without pytest's summary counts nothing."""
    passed = failed = 0
    lines = (output or "").splitlines()
    for ln in reversed(lines):
        found = _SUMMARY.findall(ln)
        if found and (" in " in ln or ln.strip().startswith("=")):
            for n, what in found:
                if what == "passed":
                    passed = int(n)
                else:
                    failed += int(n)
            break
    names: list[str] = []
    for ln in lines:
        m = _FAILED_LINE.match(ln.strip())
        if m and m.group(1) not in names:
            names.append(m.group(1))
    return {"passed": passed, "failed": failed, "failing": names[:20], "tail": "\n".join(lines[-keep_lines:])}


# -- the Board's own tree (spec 35 §13) ----------------------------------------------------------------------------

BOARD_PAGE = re.compile(r"(^|/)pages/(ideas|tracks)/[^/]+\.md$")     # a Board page, wherever its Wiki is
BOARD_NAME, BOARD_EMAIL = "Orkline board", "board@orkline.local"
COMMIT_AFTER_S = 10.0                # the writes within this as one commit


def spec_paths(repo_root: Path, state_dir: Path, slug: str) -> tuple[str, list[str]]:
    """An idea's spec as a path in a task's worktree (the work branch holds the Board's pages), and the paths of the
    specs it depends on: named, never pasted (spec 35 §0, §13). ("", []) when not found."""
    for base in (Path(state_dir) / "board", Path(repo_root)):
        found = [p for pattern in (f"llm-wiki/*/pages/ideas/{slug}.md", f"*/pages/ideas/{slug}.md", f"pages/ideas/{slug}.md")
                 for p in base.glob(pattern) if p.is_file()]
        if not found:
            continue
        page = max(found, key=lambda p: p.stat().st_mtime)
        try:
            head = page.read_text(encoding="utf-8")[:20000]
        except OSError:
            head = ""
        m = re.search(r"^depends_on:[ \t]*(\[.*\])$", head, re.M)
        try:
            deps = [d for d in json.loads(m.group(1)) if isinstance(d, str)] if m else []
        except ValueError:
            deps = []
        folder = page.relative_to(base).parent
        return page.relative_to(base).as_posix(), [(folder / f"{d}.md").as_posix() for d in deps]
    return "", []


class BoardTree:
    """The Board's pages in a worktree of their own, `<state_dir>/board/`, detached at the work branch's tip: it locks
    no branch, so the person can check out any. A change is a commit of the Board's pages only (the writes within 10 s
    as one), author *Orkline board*; the work branch is then fast-forwarded to it under the repository's lock, by
    `IdeaGit._fast_forward`'s rules (in place when the person's checkout is on it, by `update-ref` when not). Refused
    when the person has uncommitted changes in those files: held, tried again at the next write. Nothing is pushed."""

    def __init__(self, repo_root: Path, state_dir: Path, wiki_rel: str, branch) -> None:
        self.git = IdeaGit(Path(repo_root))
        self.path = Path(state_dir) / "board"
        self.wiki_rel, self.branch = wiki_rel.strip("/"), branch
        self._since: float | None = None
        self._notes: list[tuple[str, str]] = []
        self.held = ""

    def exists(self) -> bool:
        return (self.path / ".git").exists()

    def root(self) -> Path:
        return self.path / self.wiki_rel

    def pages(self) -> list[str]:
        return [f"{self.wiki_rel}/pages/tracks", f"{self.wiki_rel}/pages/ideas"]

    def _tip(self) -> str:
        return _ok(_git(self.git.root, "rev-parse", f"refs/heads/{self.branch()}"))

    def ensure(self) -> None:
        """The tree, made when missing (detached at the work branch's tip), else moved to the tip when behind."""
        with self.git.lock:
            self.git.ensure_branch(self.branch())
            if not self.exists():
                _git(self.git.root, "worktree", "prune")
                self.path.parent.mkdir(parents=True, exist_ok=True)
                _ok(_git(self.git.root, "worktree", "add", "--detach", str(self.path), self.branch()))
            else:
                self.follow()

    def follow(self) -> None:
        """A tree behind its branch (a task landed) moves to the tip; one that holds commits of its own the branch has
        not taken is rebased onto the tip (its pages never conflict: a task never edits them)."""
        tip, head = self._tip(), self.git.head(self.path)
        if tip == head or _git(self.path, "merge-base", "--is-ancestor", tip, head).returncode == 0:
            return
        if _git(self.path, "merge-base", "--is-ancestor", head, tip).returncode == 0:
            _ok(_git(self.path, "checkout", "-q", "--detach", tip))
        elif _git(self.path, "rebase", "-q", tip, timeout=PUSH_TIMEOUT_S).returncode != 0:
            _git(self.path, "rebase", "--abort")
            raise RuntimeError(f"the Board's tree could not follow {self.branch()}")

    def note(self, title: str, what: str, now: float) -> None:
        """A write of the Board's: committed with the others within COMMIT_AFTER_S."""
        if self._since is None:
            self._since = now
        self._notes.append((" ".join(str(title or "the Board").split())[:80], what))

    def due(self, now: float) -> bool:
        return self._since is not None and now - self._since >= COMMIT_AFTER_S

    def flush(self, now: float = 0.0, force: bool = False, message: str = "") -> dict | None:
        """Commit the Board's pages when due (or `force`) and fast-forward the work branch: {"commit", "pages", "what",
        "held"} (commit "" when nothing changed), None when nothing was due."""
        if not self.exists() or not (force or self.due(now)):
            return None
        title, what = self._notes[0] if self._notes else ("the Board", "edited")
        self._since, self._notes = None, []
        out = {"commit": "", "pages": 0, "what": what, "held": ""}
        with self.git.lock:
            folders = [p for p in self.pages() if (self.path / p).is_dir()]
            if folders:
                _git(self.path, "add", "-A", "--", *folders)
            staged = [f for f in _git(self.path, "diff", "--cached", "--name-only").stdout.splitlines() if f.strip()]
            if staged:
                _ok(_git(self.path, "-c", f"user.name={BOARD_NAME}", "-c", f"user.email={BOARD_EMAIL}", "commit", "-q",
                         "-m", message or f"board: {title} — {what}", "--author", f"{BOARD_NAME} <{BOARD_EMAIL}>"))
                out.update(commit=self.git.head(self.path), pages=len(staged))
            out["held"] = self.land()
        return out

    def land(self) -> str:
        """The work branch fast-forwarded to the tree: "" when it moved (or had nothing to take), else why it is held."""
        try:
            self.follow()
            tip, head = self._tip(), self.git.head(self.path)
            if tip != head:
                self.git._fast_forward(self.branch(), tip, head)
        except RuntimeError as e:
            self.held = str(e)[:300]
            return self.held
        self.held = ""
        return ""

    def move(self, legacy: Path) -> dict | None:
        """The first start after spec 35: the Board's pages in the person's Wiki that the work branch does not hold are
        copied into the tree and committed; then, and only then, the person's untracked copies are removed (they would
        block a checkout of the work branch). Tracked copies are left alone."""
        copied = []
        for folder in ("pages/tracks", "pages/ideas"):
            for page in sorted((Path(legacy) / folder).glob("*.md")) if (Path(legacy) / folder).is_dir() else []:
                target = self.root() / folder / page.name
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(page.read_bytes())
                    copied.append(page)
        if not copied:
            return None
        got = self.flush(force=True, message=f"board: the pages move to {self.branch()}")
        if got and got["commit"]:
            for page in copied:
                rel = page.resolve().relative_to(self.git.root.resolve()).as_posix()
                if _git(self.git.root, "ls-files", "--error-unmatch", "--", rel).returncode != 0:
                    page.unlink(missing_ok=True)
        return got
