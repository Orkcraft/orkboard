"""The gate: what dev holds that main lacks, and the one merge that moves main (docs/specs/49-one-window.md §2.1,
decisions §49.5). Git reads and the merge, no face.

    shas, files = idea_gate.waiting(git, "dev", "main")      # `git rev-list main..dev` (newest first), the files `main...dev` changes
    idea_gate.ideas_in(shas, rows)                           # the ideas with a merged task whose `commit` is among them
    idea_gate.all_in(git, shas, "main")                      # every sha is in main already (a goal's flag, spec 50 §2.2)
    got = idea_gate.merge(git, "dev", "main", push=True)     # main moved to dev's work: {"commit", "how", "commits", "files", "note", "pushed"}

`git` is an `IdeaGit` (realm/idea_git.py). `merge` runs under the repository's lock. When main is an ancestor of dev,
main is fast-forwarded to dev the way a result lands (`IdeaGit._fast_forward`: a root checkout on main moves with
`merge --ff-only` and is refused with its files when they are changed, else `update-ref`). Otherwise (main moved since)
a merge commit is made in a worktree of its own, detached at main, and main is fast-forwarded to it. Whatever is
refused, main is as it was and no worktree is left behind. Nothing here moves dev.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from orkboard.realm import worktrees
from orkboard.realm.idea_git import PUSH_TIMEOUT_S, IdeaGit, _git, _ok

_SHA = re.compile(r"[0-9a-f]{7,64}")

WORKTREE = "gate-merge"                      # the merge commit's worktree, under `.orkcraft/worktrees/`
IDENTITY = ("-c", "user.name=Orkline", "-c", "user.email=orkline@localhost")


class GateRefused(RuntimeError):
    """The gate does not merge, in plain words; main is as it was."""


def same(into: str, main: str) -> bool:
    """dev and main are one branch, or main does not exist: there is no gate."""
    return not main or main == into


def refusal_same(into: str, main: str) -> str:
    if not main:
        return "This folder has no main branch: there is no gate"
    if into == main:
        return f"Results merge into {main} itself: there is no gate"
    return f"{main} is {into} here: there is no gate"


def _ref(name: str) -> str:
    return f"refs/heads/{name}"


def waiting(git: IdeaGit, into: str, main: str) -> tuple[list[str], int]:
    """(the commits `into` holds that `main` lacks, newest first; the count of files they change): ([], 0) when either
    branch is missing or nothing waits. One read of `rev-list` for all the ideas, one of `diff` for the files."""
    if not all(worktrees.branch_exists(git.root, b) for b in (into, main)):
        return [], 0
    shas = _git(git.root, "rev-list", f"{_ref(main)}..{_ref(into)}", "--").stdout.split()
    if not shas:
        return [], 0
    names = _git(git.root, "diff", "--name-only", "-z", f"{_ref(main)}...{_ref(into)}", "--").stdout.split("\0")
    return shas, sum(1 for n in names if n)


def ideas_in(shas: Iterable[str], rows: Iterable[tuple[str, str, str, list[dict]]]) -> list[dict]:
    """`rows`: (slug, title, goal, tasks) of each idea in the Board's order. The ideas with a merged task whose `commit`
    is among `shas`, each `{slug, title, goal, tasks}` with the count of such tasks."""
    held = set(shas)
    out = []
    for slug, title, goal, tasks in rows:
        n = sum(1 for t in tasks if t.get("state") == "merged" and str(t.get("commit") or "") in held)
        if n:
            out.append({"slug": slug, "title": title, "goal": goal, "tasks": n})
    return out


def all_in(git: IdeaGit, shas: Iterable[str], main: str) -> bool:
    """Every sha is in `main` (an ancestor of it); no sha is False. One `rev-list` of the shas that main does not hold: a sha
    git does not know, or a branch that is not there, is not in main either."""
    held = list(dict.fromkeys(str(s) for s in shas if s))
    if not held or not main or not all(_SHA.fullmatch(s) for s in held):
        return False
    got = _git(git.root, "rev-list", "--max-count=1", *held, "--not", _ref(main), "--")
    return got.returncode == 0 and not got.stdout.strip()


def merge(git: IdeaGit, into: str, main: str, push: bool = False) -> dict[str, Any]:
    """Main moved to the work in `into`, then pushed when asked. {"commit" (main's new head), "how" ("fast-forward" |
    "merge"), "commits" (the shas it brought), "files", "note" (the push's, as `land`'s: "" when pushed or no origin),
    "pushed"}. Raises GateRefused in plain words; RuntimeError when git cannot move main (a root checkout with the
    files changed): either way main is as it was."""
    with git.lock:
        if same(into, main):
            raise GateRefused(refusal_same(into, main))
        shas, files = waiting(git, into, main)
        if not shas:
            raise GateRefused(f"Nothing in {into} waits for {main}")
        old, new = (_ok(_git(git.root, "rev-parse", _ref(b))) for b in (main, into))
        if _git(git.root, "merge-base", "--is-ancestor", old, new).returncode == 0:
            how, tip = "fast-forward", new
        else:
            how, tip = "merge", _merge_commit(git, into, main, old)
        git._fast_forward(main, old, tip)
        note = git.push(main) if push else ""
        pushed = bool(push and not note and "origin" in _git(git.root, "remote").stdout.split())
    return {"commit": tip, "how": how, "commits": shas, "files": files, "note": note, "pushed": pushed}


def _merge_commit(git: IdeaGit, into: str, main: str, old: str) -> str:
    """*Merge dev into main*, made in a worktree of its own detached at main (`old`); the commit. A conflict aborts the
    merge. The worktree is gone either way."""
    path = worktrees.worktree_path(git.root, WORKTREE)
    git.remove(path)                                           # a leftover of an earlier try
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _ok(_git(git.root, "worktree", "add", "--detach", str(path), old))
        done = _git(path, *IDENTITY, "merge", "--no-ff", "-m", f"Merge {into} into {main}", _ref(into), timeout=PUSH_TIMEOUT_S)
        if done.returncode != 0:
            files = _git(path, "diff", "--name-only", "--diff-filter=U").stdout.split()
            _git(path, "merge", "--abort")
            if files:
                raise GateRefused(f"{into} and {main} conflict in {', '.join(files)}: merge {main} into {into} first")
            raise GateRefused(" ".join((done.stderr or done.stdout).split())[:300] or "The merge failed")
        return git.head(path)
    finally:
        git.remove(path)
