"""The gate, dev → main (docs/specs/49-one-window.md §2.1): `ideas.gate` and `ideas.gate_merge` on a real fixture repository
(realm/idea_gate.py, gui/ideas_gate.py)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, idea_gate, ideas
from orkboard.realm.idea_git import IdeaGit


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit_in(path: Path, name: str, text: str) -> str:
    (path / name).write_text(text)
    git(path, "add", "-A")
    git(path, "commit", "-m", f"edit {name}")
    return git(path, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """main holds `a.txt` (start) and `old.txt` (older work); dev is cut from it. Nothing else is checked out but main."""
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-b", "main")
    git(r, "config", "user.email", "t@x")
    git(r, "config", "user.name", "T")
    (r / ".gitignore").write_text(".orkcraft/\n")
    (r / "a.txt").write_text("a\n")
    git(r, "add", "-A")
    git(r, "commit", "-m", "start")
    commit_in(r, "old.txt", "older work\n")
    git(r, "branch", "dev")
    return r


@pytest.fixture
def host(repo: Path):
    h = Orkboard(repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


def land(repo: Path, slug: str, task: str, name: str, text: str = "x\n") -> str:
    """A task's work landed in dev the way the runner does: its commit is dev's new head."""
    g = IdeaGit(repo)
    path, branch = g.prepare(slug, task, "dev")
    commit_in(path, name, text)
    commit, _subjects, _note = g.land(path, branch, "dev", push=False)
    g.remove(path)
    return commit


def idea(host, text: str) -> str:
    root = host.ideas.root()
    goal = next((t["slug"] for t in ideas.tracks(root, make=False) if t["slug"] != "general"), None) or ideas.add_track(root, "First goal")
    return host.command("ideas.add", {"text": text, "track": goal, "night": True})["slug"]


def merged(host, slug: str, **commits: str) -> None:
    """The idea's plan: a merged task per `id=commit` (a commit of "" for a check that landed nothing), a task at Review."""
    tasks = [{"id": tid, "title": f"Task {tid}", "state": "merged", "commit": c, "after": []} for tid, c in commits.items()]
    tasks.append({"id": "rv", "title": "Waiting", "state": "review", "commit": "", "after": []})
    ideas.save_plan(host.ideas.state_dir, slug, {"idea": slug, "made_at": "2026-10-21T09:00:00", "passed_at": None, "tasks": tasks})


def events(host, name: str = "gate_merged") -> list[dict]:
    return [r for r in event_log.read(Path(host.repo_root)) if r["event"] == name]


@pytest.fixture
def work(host, repo):
    """dev two tasks of one idea ahead of main (two files), another idea's task already in main, a third's still at Review."""
    first, second = idea(host, "Sync the queue\nwith the server"), idea(host, "Retry on failure")
    c1 = land(repo, first, "k1", "q.txt", "queue\n")
    c2 = land(repo, first, "k2", "r.txt", "retry\n")
    merged(host, first, k1=c1, k2=c2)
    merged(host, second, k1=git(repo, "rev-parse", "main"), c1="")
    return first, second, c1, c2


# -- ideas.gate ---------------------------------------------------------------------------------------------------

def test_the_gate_counts_what_dev_holds_and_lists_the_ideas_by_their_tasks_commits(host, repo, work, monkeypatch):
    first, _second, c1, c2 = work
    reads = []
    real = idea_gate._git
    monkeypatch.setattr(idea_gate, "_git", lambda cwd, *a, **k: reads.append(a[0]) or real(cwd, *a, **k))
    got = host.command("ideas.gate")
    assert reads.count("rev-list") == 1                                                      # one read for all the ideas
    assert got == {"into": "dev", "main": "main", "same": False, "commits": 2, "files": 2,
                   "ideas": [{"slug": first, "title": "Sync the queue", "goal": "first-goal", "tasks": 2}]}
    assert host.command("ideas.gate") == got and BoardPhone.allowed(host, "ideas.gate", {}) and BoardPhone.allowed(host, "ideas.gate_merge", {})
    assert git(repo, "rev-list", "main..dev").split() == [c2, c1]


def test_ideas_come_in_the_boards_order_and_a_task_counts_once_per_commit():
    rows = [("b", "B", "g", [{"state": "merged", "commit": "c2"}, {"state": "merged", "commit": "c3"}]),
            ("a", "A", "g", [{"state": "merged", "commit": "c1"}, {"state": "review", "commit": "c1"}, {"state": "merged", "commit": ""},
                             {"state": "merged"}, {"state": "merged", "commit": "elsewhere"}]),
            ("none", "None", "g", [])]
    assert idea_gate.ideas_in(["c1", "c2", "c3"], rows) == [{"slug": "b", "title": "B", "goal": "g", "tasks": 2},
                                                           {"slug": "a", "title": "A", "goal": "g", "tasks": 1}]
    assert idea_gate.ideas_in([], rows) == []


def test_nothing_waits_when_dev_is_main_and_there_is_no_gate_when_they_are_one_branch(host, repo):
    assert host.command("ideas.gate") == {"into": "dev", "main": "main", "same": False, "commits": 0, "files": 0, "ideas": []}
    host.command("ideas.into", {"branch": "main"})
    assert host.command("ideas.gate") == {"into": "main", "main": "main", "same": True, "commits": 0, "files": 0, "ideas": []}
    with pytest.raises(CommandError, match="there is no gate"):
        host.command("ideas.gate_merge")
    assert events(host) == []


def test_without_a_main_there_is_no_gate(tmp_path):
    bare = tmp_path / "fresh"
    bare.mkdir()
    git(bare, "init", "-b", "main")                                                          # no commit yet: no main branch
    h = Orkboard(bare)
    assert h.command("ideas.gate") == {"into": "dev", "main": "", "same": True, "commits": 0, "files": 0, "ideas": []}
    with pytest.raises(CommandError, match="no main branch: there is no gate"):
        h.command("ideas.gate_merge")
    plain = tmp_path / "plain"
    plain.mkdir()
    assert Orkboard(plain).command("ideas.gate")["same"] is True                             # not a git folder at all


def test_all_in_is_every_sha_in_main_and_no_sha_is_false(repo, monkeypatch):
    """Spec 50 §2.2: a goal's flag asks main whether every commit of its merged tasks is in it, with one git call."""
    g = IdeaGit(repo)
    c1 = land(repo, "x", "k1", "q.txt")
    old, reads, real = git(repo, "rev-parse", "main"), [], idea_gate._git
    monkeypatch.setattr(idea_gate, "_git", lambda cwd, *a, **k: reads.append(a[0]) or real(cwd, *a, **k))
    assert idea_gate.all_in(g, [old], "main") is True and reads == ["rev-list"]                # one git call
    assert idea_gate.all_in(g, [old, c1], "main") is False and idea_gate.all_in(g, [c1], "main") is False
    assert idea_gate.all_in(g, [old, old], "main") is True
    assert idea_gate.all_in(g, [], "main") is False and idea_gate.all_in(g, [""], "main") is False      # no sha is False
    assert idea_gate.all_in(g, ["0" * 40], "main") is False and idea_gate.all_in(g, ["--all"], "main") is False
    assert idea_gate.all_in(g, [old], "nowhere") is False and idea_gate.all_in(g, [old], "") is False
    monkeypatch.undo()
    git(repo, "merge", "-q", "--ff-only", "dev")
    assert idea_gate.all_in(g, [old, c1], "main") is True


# -- ideas.gate_merge ---------------------------------------------------------------------------------------------

def test_main_is_fast_forwarded_to_dev_the_checkout_follows_and_it_is_logged(host, repo, work):
    first, _second, _c1, c2 = work
    rev = host.snapshot()["ideas_rev"]
    got = host.command("ideas.gate_merge")
    assert got == {"ok": True, "commit": c2, "note": ""}
    assert git(repo, "rev-parse", "main") == git(repo, "rev-parse", "dev") == c2
    assert (repo / "q.txt").read_text() == "queue\n" and (repo / "r.txt").exists()          # main is checked out: its files follow
    assert git(repo, "status", "--porcelain", "--", "q.txt", "r.txt") == ""
    (e,) = events(host)
    assert (e["commits"], e["ideas"], e["files"], e["how"], e["pushed"], e["device"]) == (2, 1, 2, "fast-forward", False, "desktop")
    assert (e["into"], e["main"]) == ("dev", "main")
    assert host.snapshot()["ideas_rev"] > rev                                                # every face reads again
    assert host.command("ideas.gate")["commits"] == 0 and host.command("ideas.gate")["ideas"] == []
    with pytest.raises(CommandError, match="Nothing in dev waits for main"):
        host.command("ideas.gate_merge")
    assert len(events(host)) == 1


def test_main_not_checked_out_moves_by_update_ref_and_the_phone_is_logged_as_the_phone(host, repo, work):
    git(repo, "checkout", "-q", "-b", "work")                                                # the person's own branch is checked out
    host.command("ideas.gate_merge", {"device": "phone"})
    assert git(repo, "rev-parse", "main") == git(repo, "rev-parse", "dev") and not (repo / "q.txt").exists()
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "work" and events(host)[0]["device"] == "phone"


def test_main_checked_out_with_a_touched_file_changed_is_refused_with_its_files(host, repo):
    c = land(repo, idea(host, "Change a"), "k1", "a.txt", "dev's a\n")
    (repo / "a.txt").write_text("the owner's own edit\n")
    before = git(repo, "rev-parse", "main")
    with pytest.raises(CommandError, match="uncommitted changes in a.txt"):
        host.command("ideas.gate_merge")
    assert git(repo, "rev-parse", "main") == before and (repo / "a.txt").read_text() == "the owner's own edit\n"
    assert git(repo, "rev-parse", "dev") == c and events(host) == []


def worktrees(repo: Path) -> list[str]:
    return [ln for ln in git(repo, "worktree", "list", "--porcelain").splitlines() if ln.startswith("worktree ")]


def test_a_merge_commit_is_made_when_main_moved_and_no_worktree_is_left(host, repo, work):
    first, _second, c1, c2 = work
    other = commit_in(repo, "main-only.txt", "main moved\n")                                 # main is ahead of where dev was cut
    got = host.command("ideas.gate_merge")
    main = git(repo, "rev-parse", "main")
    assert got == {"ok": True, "commit": main, "note": ""} and main not in (other, c2)
    assert git(repo, "log", "-1", "--format=%s", "main") == "Merge dev into main"
    assert git(repo, "rev-parse", "main^1") == other and git(repo, "rev-parse", "main^2") == c2
    assert (repo / "q.txt").exists() and (repo / "main-only.txt").exists() and git(repo, "status", "--porcelain") == ""
    assert git(repo, "rev-parse", "dev") == c2                                               # the gate never moves dev
    assert not (repo / ".orkcraft" / "worktrees" / idea_gate.WORKTREE).exists()
    assert not [w for w in worktrees(repo) if idea_gate.WORKTREE in w]
    (e,) = events(host)
    assert (e["how"], e["commits"], e["ideas"], e["files"]) == ("merge", 2, 1, 2)
    assert host.command("ideas.gate")["commits"] == 0


def test_a_conflict_is_refused_main_is_as_it_was_and_no_worktree_is_left(host, repo):
    land(repo, idea(host, "Change a"), "k1", "a.txt", "dev's a\n")
    other = commit_in(repo, "a.txt", "main's a\n")
    with pytest.raises(CommandError, match=r"^dev and main conflict in a\.txt: merge main into dev first$"):
        host.command("ideas.gate_merge")
    assert git(repo, "rev-parse", "main") == other and git(repo, "status", "--porcelain") == ""
    assert (repo / "a.txt").read_text() == "main's a\n"
    assert not (repo / ".orkcraft" / "worktrees" / idea_gate.WORKTREE).exists() and not [w for w in worktrees(repo) if idea_gate.WORKTREE in w]
    assert events(host) == []
    c = commit_in(repo, "z.txt", "z\n")                                                      # the next try is not blocked by a leftover
    with pytest.raises(CommandError, match="conflict in a.txt"):
        host.command("ideas.gate_merge")
    assert git(repo, "rev-parse", "main") == c


# -- pushing main -------------------------------------------------------------------------------------------------

def origin(repo: Path, tmp_path: Path) -> Path:
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True)
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "origin", "main")
    return bare


def test_main_is_pushed_when_the_project_pushes_after_merging(host, repo, work, tmp_path):
    bare = origin(repo, tmp_path)
    host.command("ideas.into", {"push": True})
    got = host.command("ideas.gate_merge")
    assert got["note"] == "" and git(bare, "rev-parse", "main") == git(repo, "rev-parse", "main") == got["commit"]
    assert events(host)[0]["pushed"] is True


def test_main_is_not_pushed_when_the_project_does_not_push(host, repo, work, tmp_path):
    bare = origin(repo, tmp_path)
    before = git(bare, "rev-parse", "main")
    host.command("ideas.gate_merge")
    assert git(bare, "rev-parse", "main") == before != git(repo, "rev-parse", "main") and events(host)[0]["pushed"] is False


def test_a_push_that_fails_is_a_note_and_main_has_moved_all_the_same(host, repo, work, tmp_path):
    git(repo, "remote", "add", "origin", str(tmp_path / "nowhere.git"))
    host.command("ideas.into", {"push": True})
    got = host.command("ideas.gate_merge")
    assert got["note"].startswith("push failed") and got["commit"] == git(repo, "rev-parse", "main") == git(repo, "rev-parse", "dev")
    assert events(host)[0]["pushed"] is False


def test_the_push_note_is_empty_when_there_is_no_origin(host, repo, work):
    host.command("ideas.into", {"push": True})
    got = host.command("ideas.gate_merge")
    assert got["note"] == "" and events(host)[0]["pushed"] is False                           # nothing was pushed, and nothing failed
