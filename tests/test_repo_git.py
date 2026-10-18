"""The Git section (docs/specs/37-board-and-line.md §8, Tests → D1; realm/repo_git.py, gui/board_git.py): status
with ahead / behind and + / −, a file's diff, a commit of the ticked files only, switch, pull (fast-forward only) and
push (only on its command), every call under the repository's lock and with no shell."""
from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

import pytest

from orkboard.gui.board_host import CommandError, Orkboard
from orkboard.realm import event_log, repo_git
from orkboard.realm.idea_git import lock_of


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def _who(repo: Path) -> None:
    git(repo, "config", "user.email", "t@orkcraft.local")
    git(repo, "config", "user.name", "T")


@pytest.fixture
def repos(tmp_path) -> tuple[Path, Path, Path]:
    """An origin (bare), the project cloned from it, and another clone that pushes to origin meanwhile."""
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-b", "main")
    _who(seed)
    (seed / "app.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
    (seed / "README.md").write_text("# App\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "first")
    git(tmp_path, "clone", "--bare", str(seed), str(origin))
    repo, other = tmp_path / "project", tmp_path / "other"
    for clone in (repo, other):
        git(tmp_path, "clone", str(origin), str(clone))
        _who(clone)
    return origin, repo, other


@pytest.fixture
def host(repos) -> Orkboard:
    return Orkboard(repos[1])


def test_status_with_ahead_behind_and_counts(host, repos):
    _origin, repo, other = repos
    (other / "remote.txt").write_text("r\n", encoding="utf-8")
    git(other, "add", ".")
    git(other, "commit", "-m", "theirs")
    git(other, "push")
    git(repo, "fetch")
    (repo / "local.txt").write_text("l\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "mine")
    (repo / "app.py").write_text("a = 1\nb = 3\nc = 4\n", encoding="utf-8")
    (repo / "new.py").write_text("x\ny\n", encoding="utf-8")
    (repo / ".env").write_text("K=1\n", encoding="utf-8")
    st = host.command("git.status")
    assert set(st) == {"branch", "work_branch", "upstream", "ahead", "behind", "files", "running", "last"}
    assert (st["branch"], st["work_branch"], st["upstream"], st["ahead"], st["behind"]) == (
        "main", "dev", "origin/main", 1, 1)
    files = {f["path"]: f for f in st["files"]}
    assert files["app.py"] == {"path": "app.py", "status": "modified", "added": 2, "removed": 1}
    assert files["new.py"] == {"path": "new.py", "status": "untracked", "added": 2, "removed": 0}
    assert ".env" not in files                                                # a secret-looking file is never offered


def test_a_files_diff_in_ideas_diff_shape(host, repos):
    repo = repos[1]
    (repo / "app.py").write_text("a = 1\nb = 3\n", encoding="utf-8")
    got = host.command("git.diff", {"path": "app.py"})
    assert set(got) == {"base", "branch", "commits", "files", "truncated"}
    (f,) = got["files"]
    assert (f["path"], f["added"], f["removed"]) == ("app.py", 1, 1) and "+b = 3" in f["patch"]
    (repo / "new.md").write_text("hello\n", encoding="utf-8")
    assert "+hello" in host.command("git.diff", {"path": "new.md"})["files"][0]["patch"]
    with pytest.raises(CommandError, match="no changes"):
        host.command("git.diff", {"path": "README.md"})
    with pytest.raises(CommandError, match="not in the project"):
        host.command("git.diff", {"path": "../x"})


def test_a_commit_takes_the_ticked_files_only(host, repos):
    repo = repos[1]
    (repo / "app.py").write_text("a = 2\n", encoding="utf-8")
    (repo / "README.md").write_text("# Changed\n", encoding="utf-8")
    (repo / "new.py").write_text("n\n", encoding="utf-8")
    git(repo, "add", "README.md")                                             # staged by the person, not ticked
    got = host.command("git.commit", {"paths": ["app.py", "new.py"], "message": "Fix a"})
    assert got["ok"] is True and got["commit"] == git(repo, "rev-parse", "HEAD").strip()
    assert sorted(git(repo, "show", "--name-only", "--format=", "HEAD").split()) == ["app.py", "new.py"]
    assert git(repo, "log", "-1", "--format=%s").strip() == "Fix a"
    assert [f["path"] for f in host.command("git.status")["files"]] == ["README.md"]
    (committed,) = [r for r in event_log.read(repo) if r["event"] == "git_committed"]
    assert (committed["files"], committed["device"]) == (2, "desktop")
    (repo / ".env").write_text("K=1\n", encoding="utf-8")
    assert "secrets" in host.command("git.commit", {"paths": [".env"], "message": "x"})["error"]
    assert "message" in host.command("git.commit", {"paths": ["README.md"], "message": " "})["error"]
    assert "no changes" in host.command("git.commit", {"paths": ["app.py"], "message": "x"})["error"]


def test_switch_is_refused_with_uncommitted_changes(host, repos):
    repo = repos[1]
    git(repo, "branch", "feature")
    (repo / "app.py").write_text("dirty\n", encoding="utf-8")
    got = host.command("git.switch", {"branch": "feature"})
    assert "uncommitted changes" in got["error"] and git(repo, "branch", "--show-current").strip() == "main"
    git(repo, "checkout", "--", "app.py")
    (repo / "scratch.txt").write_text("untracked stays\n", encoding="utf-8")
    assert host.command("git.switch", {"branch": "feature"}) == {"ok": True}
    assert git(repo, "branch", "--show-current").strip() == "feature"
    assert "not a branch name" in host.command("git.switch", {"branch": "--force"})["error"]


def _done(host, op: str) -> dict:
    """A pull or a push starts and answers at once; wait for its outcome (`git.status`'s `last`)."""
    assert host.command(f"git.{op}") == {"started": True}
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        st = host.command("git.status")
        if not st["running"] and st["last"]:
            return st["last"]
        time.sleep(0.02)
    raise AssertionError(f"git.{op} did not finish")


def test_pull_fast_forwards_only(host, repos):
    _origin, repo, other = repos
    (other / "remote.txt").write_text("r\n", encoding="utf-8")
    git(other, "add", ".")
    git(other, "commit", "-m", "theirs")
    git(other, "push")
    got = _done(host, "pull")
    assert got == {"op": "pull", "ok": True, "said": "Pulled 1 commit into main"} and (repo / "remote.txt").exists()
    assert "up to date" in _done(host, "pull")["said"]
    (other / "remote.txt").write_text("r2\n", encoding="utf-8")
    git(other, "commit", "-am", "theirs again")
    git(other, "push")
    (repo / "local.txt").write_text("l\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "mine")
    head = git(repo, "rev-parse", "HEAD")
    got = _done(host, "pull")
    assert got["ok"] is False and "diverged" in got["said"] and git(repo, "rev-parse", "HEAD") == head      # nothing changed


def test_push_only_on_its_command(host, repos):
    origin, repo, _other = repos
    (repo / "app.py").write_text("a = 9\n", encoding="utf-8")
    host.command("git.commit", {"paths": ["app.py"], "message": "Nine"})
    assert git(origin, "rev-parse", "main") != git(repo, "rev-parse", "HEAD")    # a commit is not pushed
    assert _done(host, "push") == {"op": "push", "ok": True, "said": "Sent main to origin"}
    assert git(origin, "rev-parse", "main") == git(repo, "rev-parse", "HEAD")
    (pushed,) = [r for r in event_log.read(repo) if r["event"] == "git_pushed"]
    assert (pushed["branch"], pushed["device"]) == ("main", "desktop")
    git(repo, "switch", "-c", "topic")
    assert _done(host, "push")["ok"] and git(origin, "rev-parse", "topic")    # a new branch gets its upstream
    git(repo, "remote", "remove", "origin")
    assert "no origin" in _done(host, "push")["said"]


def test_every_call_is_under_the_lock_with_no_shell(host, repos, monkeypatch):
    repo = repos[1]
    lock, real, seen = lock_of(repo), subprocess.run, []

    def run(argv, *a, **k):
        assert isinstance(argv, list) and argv[0] == "git" and not k.get("shell")
        assert lock._is_owned(), argv
        seen.append(argv[1])
        return real(argv, *a, **k)

    monkeypatch.setattr(repo_git.subprocess, "run", run)
    (repo / "app.py").write_text("a = 5\n", encoding="utf-8")
    host.command("git.status")
    host.command("git.diff", {"path": "app.py"})
    host.command("git.commit", {"paths": ["app.py"], "message": "Five"})
    host.command("git.switch", {"branch": "main"})
    _done(host, "pull")
    _done(host, "push")
    assert {"status", "diff", "add", "commit", "switch", "pull", "push"} <= set(seen)
    assert not {"rebase", "reset", "stash"} & set(seen) and "--force" not in str(seen)


def test_the_work_branch_is_the_projects_merge_into(host, repos):
    host.command("ideas.into", {"branch": "release"})
    assert host.command("git.status")["work_branch"] == "release"


# -- off the server's thread ---------------------------------------------------------------------------------------

def test_a_push_runs_off_the_server_thread_and_a_second_press_is_refused(host, repos, monkeypatch):
    origin, repo, _other = repos
    (repo / "app.py").write_text("a = 9\n", encoding="utf-8")
    host.command("git.commit", {"paths": ["app.py"], "message": "Nine"})
    gate, entered, real = threading.Event(), threading.Event(), repo_git.RepoGit.push

    def slow(self):                                  # a fake slow git: the push is held until the test lets it go
        entered.set()
        assert gate.wait(30)
        return real(self)

    monkeypatch.setattr(repo_git.RepoGit, "push", slow)
    seen = []
    host.projects.current().bus.subscribe("background.ran", seen.append)
    assert host.command("git.push") == {"started": True}
    assert entered.wait(30)
    st = host.command("git.status")                  # another command answers while the push is held
    assert (st["running"], st["last"]) == ("push", None)
    assert host.command("git.push") == {"error": "a push is already running"}
    assert host.command("git.pull") == {"error": "a push is already running"}
    assert git(origin, "rev-parse", "main") != git(repo, "rev-parse", "HEAD")
    gate.set()
    deadline = time.monotonic() + 30
    while not seen and time.monotonic() < deadline:
        time.sleep(0.02)
    assert [(e.data["op"], e.data["ok"], e.data["said"]) for e in seen] == [("push", True, "Sent main to origin")]
    st = host.command("git.status")
    assert st["running"] == "" and st["last"]["ok"] is True
    assert git(origin, "rev-parse", "main") == git(repo, "rev-parse", "HEAD")


def test_the_branches_work_branch_and_main_first_the_current_marked(host, repos):
    repo = repos[1]
    for name in ("zeta", "alpha", "dev"):
        git(repo, "branch", name)
    git(repo, "switch", "alpha")
    got = host.command("git.branches")["branches"]
    assert [b["name"] for b in got] == ["dev", "main", "alpha", "zeta"]            # the work branch (dev), then main
    assert [b["name"] for b in got if b["current"]] == ["alpha"]
    assert {b["name"]: b["upstream"] for b in got}["main"] == "origin/main" and got[0]["upstream"] == ""
    (repo / "app.py").write_text("dirty\n", encoding="utf-8")
    assert "uncommitted" in host.command("git.switch", {"branch": "main"})["error"]
