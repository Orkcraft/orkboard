"""The project, as in an IDE (docs/specs/37-board-and-line.md §8, Tests → D1): several projects open at once, one
shown, each with its own Board; the Board's settings the project's; Open folder and Start git here; the to-dos'
secrets per project; what the phone may do; `orkboard <folder>`."""
from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from orkboard import settings
from orkboard.gui import ideas as gui_ideas
from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, idea_secrets, ideas, project_folder


def make_repo(tmp_path: Path, name: str) -> Path:
    repo = tmp_path / name
    (repo / "src").mkdir(parents=True)
    (repo / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    (repo / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    for args in (["init", "-b", "main"], ["config", "user.email", "t@orkcraft.local"], ["config", "user.name", "T"],
                 ["add", "."], ["commit", "-m", "first"]):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    return repo


@pytest.fixture
def two(tmp_path) -> tuple[Path, Path]:
    return make_repo(tmp_path, "shop"), make_repo(tmp_path, "blog")


@pytest.fixture
def runners(monkeypatch) -> list:
    """A runner per Board, faked: each remembers its repository, what it started and whether it was stopped."""
    made: list = []

    class FakeRunner:
        def __init__(self, repo_root, state_dir, settings, bus, **kw):
            self.repo, self.settings, self.ticks, self.stopped = Path(repo_root), settings, 0, 0
            self._runs: dict = {}
            made.append(self)

        def start(self, slug):
            self._runs[(slug, "k1")] = object()

        def tick(self):
            self.ticks += 1

        def stop(self, slug):
            self._runs = {k: v for k, v in self._runs.items() if k[0] != slug}

        def stop_all(self):
            self.stopped += 1
            self._runs.clear()

    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", types.SimpleNamespace(IdeaRunner=FakeRunner))
    yield made
    sys.modules.pop("orkboard.core.idea_runner", None)


def _goal_and_idea(host: Orkboard, text: str) -> str:
    goal = host.command("ideas.track_add", {"title": f"Goal of {text}"})["slug"]
    return host.command("ideas.add", {"text": text, "track": goal, "night": True})["slug"]


def _plan(host: Orkboard, slug: str) -> None:
    ideas.save_plan(host.ideas.state_dir, slug, {
        "idea": slug, "made_at": "2026-10-17T09:00:00", "passed_at": None, "todos": [],
        "estimate": {"tasks": 1, "usd_low": 0.1, "usd_high": 0.2},
        "tasks": [{"id": "k1", "title": "Do it", "brief": "b", "tier": "warrior", "after": [], "state": "ready",
                   "branch": "", "commit": "", "session": "", "cost": None, "tokens": None, "started": "",
                   "finished": "", "error": "", "note": ""}]})
    ideas.save_state(host.ideas.state_dir, slug, state="plan")


# -- several at once, one shown ----------------------------------------------------------------------------------

def test_two_projects_each_have_their_own_board_and_runner(two, runners):
    shop, blog = two
    host = Orkboard()
    assert host.command("projects.list") == {"current": None, "open": [], "recent": []}     # the start screen
    with pytest.raises(CommandError, match="Open a folder first"):
        host.command("ideas.board")
    assert host.command("projects.open", {"path": str(shop)}) == {"ok": True, "git": True}
    in_shop = _goal_and_idea(host, "a cart for the shop")
    assert host.command("projects.open", {"path": str(blog)}) == {"ok": True, "git": True}
    assert host.repo_root == blog.resolve()                                    # the folder opened is shown
    board = host.command("ideas.board")
    assert in_shop not in {i["slug"] for i in board["ideas"]}                  # nothing of one is seen in the other
    assert not any(t["title"] == "Goal of a cart for the shop" for t in board["tracks"])
    in_blog = _goal_and_idea(host, "a post for the blog")

    for slug in (in_blog,):
        _plan(host, slug)
        host.command("ideas.start", {"slug": slug})
    host.command("projects.use", {"path": str(shop)})
    assert host.repo_root == shop.resolve() and in_blog not in {i["slug"] for i in host.command("ideas.board")["ideas"]}
    _plan(host, in_shop)
    host.command("ideas.start", {"slug": in_shop})
    assert sorted(r.repo.name for r in runners) == ["blog", "shop"]           # each its own runner

    host.command("projects.use", {"path": str(blog)})                          # showing the other stops nothing
    host.tick(1000.0)
    assert all(r.ticks == 1 and r._runs for r in runners)
    listed = host.command("projects.list")
    assert listed["current"] == str(blog.resolve())
    assert [(p["name"], p["working"]) for p in listed["open"]] == [("shop", 1), ("blog", 1)]
    assert set(listed["open"][0]) == {"path", "name", "git", "working", "needs_you", "review"}

    host.command("halt")                                                       # Stop all: every project's
    assert all(r.stopped == 1 and not r._runs for r in runners)


def test_close_with_a_running_task_asks_and_stops_only_with_stop(two, runners):
    shop, blog = two
    host = Orkboard(shop)
    host.command("projects.open", {"path": str(blog)})
    slug = _goal_and_idea(host, "x")
    _plan(host, slug)
    host.command("ideas.start", {"slug": slug})
    (blog_runner,) = runners
    assert host.command("projects.close", {"path": str(blog)}) == {"running": 1}
    assert blog_runner._runs and str(blog.resolve()) in [p["path"] for p in host.command("projects.list")["open"]]
    assert host.command("projects.close", {"path": str(blog), "stop": True}) == {"ok": True}
    assert not blog_runner._runs and blog_runner.stopped == 1
    listed = host.command("projects.list")
    assert listed["current"] == str(shop.resolve()) and [p["name"] for p in listed["open"]] == ["shop"]
    assert listed["recent"] == [{"path": str(blog.resolve()), "name": "blog"}]
    (closed,) = [r for r in event_log.read(blog) if r["event"] == "project_closed"]
    assert closed["stopped"] is True
    assert host.command("projects.close", {"path": str(shop)}) == {"ok": True}  # nothing running: closes at once
    assert host.command("projects.list")["current"] is None and host.snapshot()["repo"] == ""


def test_the_open_projects_are_remembered_and_opened_again(two):
    shop, blog = two
    host = Orkboard(shop)
    host.command("projects.open", {"path": str(blog)})
    host.command("projects.use", {"path": str(shop)})
    saved = settings.load()
    assert saved.projects_open == [str(shop.resolve()), str(blog.resolve())]
    assert saved.projects_recent[0] == str(shop.resolve())
    again = Orkboard(restore=True)
    assert again.repo_root == shop.resolve() and len(again.projects.open_ones) == 2
    with pytest.raises(CommandError, match="not open"):
        again.command("projects.use", {"path": str(shop.parent / "nowhere")})
    opened = [r for r in event_log.read(shop) if r["event"] == "project_opened"]
    assert [(r["new"], r["git"], r["device"]) for r in opened] == [(True, True, "desktop"), (False, True, "desktop")]


# -- the Board's settings are the project's ----------------------------------------------------------------------

def test_a_projects_board_json_wins_over_the_machines_and_a_new_one_starts_from_them(two):
    shop, blog = two
    host = Orkboard(shop)
    host.machine.ideas = settings.clean_ideas({**host.machine.ideas, "merge_into": "trunk", "target": "thrift"})
    assert host.command("ideas.review_list")["into"] == "trunk"                # no board.json: the machine's
    host.command("ideas.board_set", {"target": "quality"})
    host.command("ideas.into", {"push": True})
    own = json.loads((shop / ".orkcraft" / "board.json").read_text())
    assert own["target"] == "quality" and own["push"] is True and own["merge_into"] == "trunk"
    assert "board.json" in (shop / ".orkcraft" / ".gitignore").read_text().split()
    assert settings.load().ideas["target"] == settings.IDEAS["target"]        # the machine's are not written
    host.command("projects.open", {"path": str(blog)})
    assert host.command("ideas.board_set", {})["target"] == "thrift"           # a new project: the machine's
    host.command("projects.use", {"path": str(shop)})
    assert host.command("ideas.board_set", {})["target"] == "quality"
    assert gui_ideas._Settings(host.board).ideas["push"] is True               # what the runner reads


def test_risk_paths_are_the_repositorys_orkcraft_toml(fake_repo):
    host = Orkboard(fake_repo)
    host.machine.ideas = settings.clean_ideas({**host.machine.ideas, "risk_paths": ["machine/*"]})
    assert host.board.board_settings()["risk_paths"] == ["machine/*"]
    (fake_repo / "orkcraft.toml").write_text('[board]\nrisk_paths = ["billing/*", "infra/**"]\n', encoding="utf-8")
    assert host.board.board_settings()["risk_paths"] == ["billing/*", "infra/**"]
    (fake_repo / ".orkcraft").mkdir(exist_ok=True)
    (fake_repo / ".orkcraft" / "board.json").write_text(json.dumps({"risk_paths": ["no/*"], "max_parallel": 3}))
    got = host.board.board_settings()
    assert got["risk_paths"] == ["billing/*", "infra/**"] and got["max_parallel"] == 3   # board.json holds no risk


def test_the_wiki_and_the_work_branch_are_the_projects(fake_repo):
    host = Orkboard(fake_repo)
    host.board.save_board_settings({**host.board.board_settings(), "wiki": "docs/board"})
    assert host.ideas.wiki() == fake_repo.resolve() / "docs" / "board"
    assert "wiki" not in host.machine.ideas


# -- Open folder, Start git here ---------------------------------------------------------------------------------

def test_open_folder_refuses_in_words_and_offers_git(tmp_path):
    host = Orkboard()
    got = host.command("projects.open", {"path": str(Path.home())})
    assert set(got) == {"error"} and "home folder" in got["error"]
    assert "not there" in host.command("projects.open", {"path": str(tmp_path / "nowhere")})["error"]
    assert "system" in host.command("projects.open", {"path": "/usr"})["error"]
    (Path.home() / ".ssh" / "keys").mkdir(parents=True)
    assert project_folder.refusal("/") and "keys" in project_folder.refusal(Path.home() / ".ssh" / "keys")
    assert "Orkline's own" in project_folder.refusal(Path(project_folder.__file__).parent)
    plain = tmp_path / "notes"
    plain.mkdir()
    (plain / "todo.md").write_text("- a\n", encoding="utf-8")
    (plain / ".env").write_text("KEY=1\n", encoding="utf-8")
    assert host.command("projects.open", {"path": str(plain)}) == {"ok": True, "git": False}
    row = lambda: next(r for r in host.command("projects.list")["open"] if r["path"] == str(plain.resolve()))   # noqa: E731
    assert row()["git"] is False and next(r for r in host.snapshot()["projects"]["open"]
                                          if r["path"] == str(plain.resolve()))["git"] is False
    got = host.command("projects.start_git", {"path": str(plain)})
    assert got["ok"] is True and "first commit" in got["said"]
    tracked = subprocess.run(["git", "ls-files"], cwd=plain, capture_output=True, text=True, check=True).stdout.split()
    assert "todo.md" in tracked and ".env" not in tracked                     # a secret left out of the first commit
    assert host.command("projects.start_git", {"path": str(plain)}) == {"ok": True, "said": "Git was already here"}
    assert row()["git"] is True
    assert "home folder" in host.command("projects.start_git", {"path": str(Path.home())})["error"]


def test_start_git_refuses_a_folder_too_large_for_a_first_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(project_folder, "FIRST_COMMIT_FILES", 3)
    big = tmp_path / "big"
    big.mkdir()
    for n in range(5):
        (big / f"f{n}.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="too large"):
        project_folder.start_git(big)
    assert not (big / ".git").exists()


# -- the to-dos' secrets are the project's -----------------------------------------------------------------------

class _Keychain:
    def __init__(self) -> None:
        self.kept: dict = {}

    def set_password(self, service, name, value):
        self.kept[(service, name)] = value

    def get_password(self, service, name):
        return self.kept.get((service, name))

    def delete_password(self, service, name):
        self.kept.pop((service, name), None)


@pytest.mark.parametrize("keychain", [False, True])
def test_two_projects_with_the_same_idea_and_todo_keep_two_secrets(two, monkeypatch, keychain):
    kc = _Keychain()
    if keychain:
        monkeypatch.setattr(idea_secrets, "_keychain", lambda: kc)
    shop, blog = (p / ".orkcraft" for p in two)
    idea_secrets.put(shop, "dark-mode", "t1", "shop-key")
    idea_secrets.put(blog, "dark-mode", "t1", "blog-key")
    assert idea_secrets.get(shop, "dark-mode", "t1") == "shop-key"
    assert idea_secrets.get(blog, "dark-mode", "t1") == "blog-key"
    assert idea_secrets.account(shop, "dark-mode", "t1") != idea_secrets.account(blog, "dark-mode", "t1")
    idea_secrets.forget(shop, "dark-mode", ["t1"])
    assert idea_secrets.get(shop, "dark-mode", "t1") is None and idea_secrets.get(blog, "dark-mode", "t1") == "blog-key"


def test_a_secret_under_the_old_account_is_read_once_and_moved(fake_repo, monkeypatch):
    from orkboard.realm.idea_git import read_secret
    kc = _Keychain()
    monkeypatch.setattr(idea_secrets, "_keychain", lambda: kc)
    state = fake_repo / ".orkcraft"
    kc.set_password(idea_secrets.SERVICE, "dark-mode/t1", "old-key")
    assert read_secret(state, "dark-mode", "t1") == "old-key"                 # the runner's reader finds it
    assert kc.get_password(idea_secrets.SERVICE, "dark-mode/t1") is None
    assert kc.get_password(idea_secrets.SERVICE, idea_secrets.account(state, "dark-mode", "t1")) == "old-key"
    monkeypatch.setattr(idea_secrets, "_keychain", lambda: None)              # the file, as without a keychain
    state.mkdir(exist_ok=True)
    (state / "secrets.json").write_text(json.dumps({"dark-mode/t2": "file-key"}))
    assert idea_secrets.get(state, "dark-mode", "t2") == "file-key"
    kept = json.loads((state / "secrets.json").read_text())
    assert kept == {idea_secrets.account(state, "dark-mode", "t2"): "file-key"}


# -- the phone -----------------------------------------------------------------------------------------------------

def test_the_phone_may_switch_projects_and_read_markdown_only(fake_repo):
    host = Orkboard(fake_repo)
    may = lambda name, args=None: BoardPhone.allowed(host, name, args or {})     # noqa: E731
    assert may("projects.list") and may("projects.use", {"path": "x"})
    assert may("files.read", {"path": "docs/notes.md"}) and may("files.read", {"path": "README.MD"})
    assert not may("files.read", {"path": "src/app.py"}) and not may("files.read", {})
    for name in ("files.write", "files.tree", "files.reveal", "projects.open", "projects.close", "projects.start_git",
                 "git.status", "git.diff", "git.branches", "git.commit", "git.switch", "git.pull", "git.push"):
        assert name in host.commands and not may(name, {"path": "README.md"}), name
    assert BoardPhone.guard("projects.use", {"path": "x"}, {"id": "d1"})["device"] == "phone"
    assert host.command("files.read", BoardPhone.guard("files.read", {"path": "README.md"}))["kind"] == "markdown"
    (fake_repo / "code.md").symlink_to(fake_repo / "src" / "app.py")
    with pytest.raises(CommandError, match="Markdown files only"):
        host.command("files.read", BoardPhone.guard("files.read", {"path": "code.md"}))


# -- `orkboard <folder>` ------------------------------------------------------------------------------------------

def test_orkboard_opens_the_folder_named_else_the_last_shown(two, monkeypatch, tmp_path):
    from orkboard.gui import board_host
    shop, blog = two
    started = []
    monkeypatch.setattr(board_host, "run", lambda root, browser=False, port=0: started.append(root) or 0)
    assert board_host.main([str(blog)]) == 0 and started[-1] == blog.resolve()
    assert board_host.main(["board", str(shop), "--browser"]) == 0 and started[-1] == shop.resolve()
    m = settings.load()
    m.projects_recent = [str(blog.resolve())]
    settings.save(m)
    monkeypatch.chdir(tmp_path)
    assert board_host.main([]) == 0 and started[-1] == blog.resolve()
