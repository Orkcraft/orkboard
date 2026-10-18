"""Spec 35 §13 on a fixture repository: the Board's own tree, detached at the work branch; a write is one commit of its
pages only and fast-forwards the branch (in place when the root is on it, by update-ref when not); the person checks
out the branch and back cleanly; uncommitted changes in those files hold it until the next write; writes within 10 s
are one commit; a task's worktree holds the specs; the move copies, commits, then removes only untracked copies."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from orkboard.gui.board_host import Orkboard
from orkboard.realm import event_log, ideas
from orkboard.realm.idea_git import BoardTree, IdeaGit

WIKI = "llm-wiki/general"


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@x")
    git(repo, "config", "user.name", "T")
    (repo / ".gitignore").write_text(".orkcraft/\n")
    (repo / "app.py").write_text("x = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "start")
    return repo


def _tree(repo):
    t = BoardTree(repo, repo / ".orkcraft", WIKI, lambda: "dev")
    t.ensure()
    return t


def _page(t, name, text="# Page\n"):
    path = t.root() / "pages" / "ideas" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_the_tree_is_detached_at_the_work_branch(repo):
    t = _tree(repo)
    assert subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=t.path).returncode != 0
    assert git(t.path, "rev-parse", "HEAD") == git(repo, "rev-parse", "dev") and git(repo, "branch", "--show-current") == "main"


def test_a_write_is_one_commit_of_the_pages_only_and_moves_the_branch_by_update_ref(repo):
    t = _tree(repo)
    _page(t, "a.md")
    (t.path / "stray.txt").write_text("not a page\n")
    t.note("Dark mode", "drafted", 0.0)
    got = t.flush(force=True)
    assert got["commit"] and got["pages"] == 1 and got["held"] == ""
    assert git(repo, "rev-parse", "dev") == got["commit"] and git(repo, "rev-parse", "main") != got["commit"]
    assert git(repo, "show", "--name-only", "--format=%an|%s", "dev").splitlines() == [
        "Orkline board|board: Dark mode — drafted", "", f"{WIKI}/pages/ideas/a.md"]
    assert not (repo / WIKI).exists()                                    # the person's tree is not touched


def test_in_place_when_the_root_is_on_the_branch_and_the_person_checks_out_cleanly(repo):
    t = _tree(repo)
    git(repo, "checkout", "-q", "dev")
    _page(t, "b.md")
    t.note("B", "edited", 0.0)
    assert t.flush(force=True)["held"] == ""
    assert (repo / WIKI / "pages" / "ideas" / "b.md").exists()             # moved in place: its files came along
    git(repo, "checkout", "-q", "main")
    git(repo, "checkout", "-q", "dev")
    assert git(repo, "status", "--porcelain") == ""


def test_uncommitted_changes_in_those_files_hold_it_and_the_next_write_lands_it(repo):
    t = _tree(repo)
    _page(t, "c.md", "# one\n")
    t.flush(force=True)
    git(repo, "checkout", "-q", "dev")
    (repo / WIKI / "pages" / "ideas" / "c.md").write_text("# the person's own edit\n")
    _page(t, "c.md", "# two\n")
    got = t.flush(force=True)
    assert got["commit"] and "uncommitted" in got["held"] and git(repo, "rev-parse", "dev") != got["commit"]
    git(repo, "checkout", "--", f"{WIKI}/pages/ideas/c.md")
    _page(t, "d.md")
    got = t.flush(force=True)
    assert got["held"] == "" and git(repo, "rev-parse", "dev") == got["commit"]
    assert (repo / WIKI / "pages" / "ideas" / "c.md").read_text() == "# two\n"


def test_writes_within_ten_seconds_are_one_commit(repo):
    t = _tree(repo)
    before = git(repo, "rev-list", "--count", "dev")
    _page(t, "e.md")
    t.note("E", "drafted", 100.0)
    assert t.flush(105.0) is None                                           # not due yet
    _page(t, "f.md")
    t.note("F", "edited", 105.0)
    got = t.flush(110.0)
    assert got["pages"] == 2 and int(git(repo, "rev-list", "--count", "dev")) == int(before) + 1


def test_a_tasks_worktree_holds_the_specs_committed_before_it(repo):
    t = _tree(repo)
    _page(t, "spec.md", "# The spec\n")
    t.flush(force=True)
    path, _branch = IdeaGit(repo).prepare("spec", "k1", "dev")
    assert (path / WIKI / "pages" / "ideas" / "spec.md").read_text() == "# The spec\n"


def test_the_tree_follows_its_branch_when_a_task_landed(repo):
    t = _tree(repo)
    git(repo, "checkout", "-q", "dev")
    (repo / "landed.py").write_text("y = 2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "a task landed")
    _page(t, "g.md")
    got = t.flush(force=True)
    assert got["held"] == "" and git(repo, "log", "-1", "--format=%s", "dev").startswith("board:")
    assert (t.path / "landed.py").exists() and git(repo, "status", "--porcelain") == ""


def test_the_move_copies_commits_then_removes_only_untracked_copies(repo):
    legacy = repo / WIKI
    (legacy / "pages" / "ideas").mkdir(parents=True)
    (legacy / "pages" / "ideas" / "tracked.md").write_text("# tracked\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "a tracked page")
    (legacy / "pages" / "ideas" / "loose.md").write_text("# loose\n")
    git(repo, "branch", "dev", "HEAD~1")                                   # dev does not hold either page
    t = _tree(repo)
    got = t.move(legacy)
    assert got["commit"] and git(repo, "log", "-1", "--format=%s", "dev") == "board: the pages move to dev"
    assert (t.root() / "pages" / "ideas" / "loose.md").read_text() == "# loose\n"
    assert not (legacy / "pages" / "ideas" / "loose.md").exists()           # untracked: removed after the commit
    assert (legacy / "pages" / "ideas" / "tracked.md").exists()             # tracked: left alone


def test_the_host_keeps_its_pages_in_the_tree_and_logs_each_commit(fake_repo):
    (fake_repo / ".gitignore").write_text(".orkcraft/\n")
    host = Orkboard(fake_repo)
    root = host.ideas.root()
    assert ".orkcraft/board" in root.as_posix()
    goal = ideas.add_track(root, "In the tree")
    host.command("ideas.add", {"text": "an idea", "track": goal, "night": True})
    got = host.ideas.tree_flush(force=True)
    assert got["commit"] and got["held"] == ""
    assert git(fake_repo, "show", "--format=%s", "-s", "dev").startswith("board: ")
    (e,) = [r for r in event_log.read(Path(fake_repo)) if r["event"] == "board_committed"]
    assert e["commit"] == got["commit"] and e["pages"] >= 2 and e["what"]
    assert not (fake_repo / "llm-wiki").exists()


def test_the_host_says_board_held_when_the_person_has_changes_in_those_files(fake_repo):
    (fake_repo / ".gitignore").write_text(".orkcraft/\n")
    host = Orkboard(fake_repo)
    root = host.ideas.root()
    goal = ideas.add_track(root, "Held")
    host.ideas.tree_flush(force=True)
    git(fake_repo, "checkout", "-q", "dev")
    rel = (root / "pages" / "tracks" / f"{goal}.md").relative_to(fake_repo / ".orkcraft" / "board")
    (fake_repo / rel).write_text("# mine\n")
    host.command("ideas.track_set", {"slug": goal, "about": "Changed by the Board"})
    got = host.ideas.tree_flush(force=True)
    assert got["commit"] and got["held"]
    (e,) = [r for r in event_log.read(Path(fake_repo)) if r["event"] == "board_held"]
    assert "uncommitted" in e["why"]


def test_the_clock_alone_makes_no_tree_and_no_branch(fake_repo):
    host = Orkboard(fake_repo)
    host.ideas.keeper._tick_at = float("-inf")
    host.ideas.tick()
    host.ideas.keeper.run_night()
    assert not (fake_repo / ".orkcraft" / "board").exists()
    assert "dev" not in git(fake_repo, "branch", "--list", "dev")
