"""The Files pane's commands (docs/specs/37-board-and-line.md §8, Tests → D1; gui/board_files.py): the tree, a file
read and saved, and what never leaves the project or is never read."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest

from orkboard.gui import board_files
from orkboard.gui.board_host import CommandError, Orkboard
from orkboard.realm import event_log


@pytest.fixture
def host(fake_repo) -> Orkboard:
    (fake_repo / ".gitignore").write_text("build/\n*.log\n", encoding="utf-8")
    (fake_repo / "build").mkdir()
    (fake_repo / "build" / "out.js").write_text("x\n", encoding="utf-8")
    (fake_repo / "run.log").write_text("log\n", encoding="utf-8")
    (fake_repo / ".env").write_text("TOKEN=abc\n", encoding="utf-8")
    (fake_repo / "id_ed25519").write_text("-----BEGIN-----\n", encoding="utf-8")
    return Orkboard(fake_repo)


def _names(host, **args) -> list[str]:
    return [e["name"] for e in host.command("files.tree", args)["entries"]]


def test_the_tree_hides_git_and_orkcraft_and_the_ignored_files_behind_the_toggle(host, fake_repo):
    (fake_repo / ".orkcraft").mkdir(exist_ok=True)
    names = _names(host)
    assert ".git" not in names and ".orkcraft" not in names
    assert names[:3] == ["docs", "loot", "src"]                               # folders first, then files, by name
    assert "build" not in names and "run.log" not in names
    shown = _names(host, ignored=True)
    assert "build" in shown and "run.log" in shown and ".git" not in shown
    rows = {e["name"]: e for e in host.command("files.tree", {})["entries"]}
    assert set(rows["README.md"]) == {"name", "path", "dir", "size", "secret"}
    assert rows[".env"]["secret"] is True and rows["id_ed25519"]["secret"] is True and not rows["README.md"]["secret"]
    assert rows["src"]["dir"] is True and rows["README.md"]["size"] == (fake_repo / "README.md").stat().st_size
    assert [e["path"] for e in host.command("files.tree", {"dir": "src"})["entries"]] == ["src/app.py"]
    for bad in (".git", "../", ".orkcraft"):
        with pytest.raises(CommandError):
            host.command("files.tree", {"dir": bad})


def test_files_read_by_kind(host, fake_repo):
    md = host.command("files.read", {"path": "docs/notes.md"})
    assert md["kind"] == "markdown" and md["text"].startswith("# Notes") and "<h1>Notes</h1>" in md["html"]
    assert {"path", "kind", "text", "size", "mtime"} <= set(md)
    code = host.command("files.read", {"path": "src/app.py"})
    assert code["kind"] == "text" and code["text"] == "print('hello')\n" and "html" not in code
    (fake_repo / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\0\0\0")
    assert host.command("files.read", {"path": "logo.png"}) == {
        "path": "logo.png", "kind": "binary", "size": 11, "mtime": (fake_repo / "logo.png").stat().st_mtime_ns // 1000}
    (fake_repo / "big.txt").write_text("x" * (board_files.LARGE + 1), encoding="utf-8")
    big = host.command("files.read", {"path": "big.txt"})
    assert big["kind"] == "large" and "text" not in big and big["size"] == board_files.LARGE + 1
    (fake_repo / "md.html").write_text("<script>alert(1)</script>", encoding="utf-8")
    raw = (fake_repo / "raw.md")
    raw.write_text("<script>alert(1)</script>\n", encoding="utf-8")
    assert "<script>" not in host.command("files.read", {"path": "raw.md"})["html"]   # raw HTML off


def test_a_secret_reads_with_no_text(host, fake_repo):
    for name in (".env", "id_ed25519"):
        got = host.command("files.read", {"path": name})
        assert got["kind"] == "secret" and "text" not in got and "html" not in got
    (fake_repo / "notes-link.md").symlink_to(fake_repo / ".env")                # a link to a .env is a .env
    assert host.command("files.read", {"path": "notes-link.md"})["kind"] == "secret"
    (fake_repo / ".env.example").write_text("TOKEN=\n", encoding="utf-8")
    assert host.command("files.read", {"path": ".env.example"})["kind"] == "text"


def test_files_write_refusals(host, fake_repo, tmp_path):
    def write(path, text="new", mtime=None):
        return host.command("files.write", {"path": path, "text": text, "mtime": mtime})

    for bad in ("../x.md", "/etc/passwd", "src/../../x.md"):
        with pytest.raises(CommandError, match="not in the project|leaves the project"):
            write(bad)
    outside = tmp_path / "outside.md"
    outside.write_text("out\n", encoding="utf-8")
    (fake_repo / "out-link.md").symlink_to(outside)
    with pytest.raises(CommandError, match="leaves the project"):
        write("out-link.md", mtime=outside.stat().st_mtime_ns // 1000)
    assert outside.read_text() == "out\n"
    (fake_repo / "llm-wiki" / "general" / "pages" / "ideas").mkdir(parents=True)
    (fake_repo / "llm-wiki" / "general" / "pages" / "ideas" / "x.md").write_text("# x\n", encoding="utf-8")
    with pytest.raises(CommandError, match="Board page"):
        write("llm-wiki/general/pages/ideas/x.md")
    with pytest.raises(CommandError, match="Board page"):
        write("docs/pages/tracks/goal.md")
    for secret in (".env", "id_ed25519", "certs/server.pem", ".env.local"):
        with pytest.raises(CommandError, match="may hold secrets"):
            write(secret)
    with pytest.raises(CommandError, match="repository's own state"):
        write(".git/config")
    read = host.command("files.read", {"path": "docs/notes.md"})
    (fake_repo / "docs" / "notes.md").write_text("# Notes\n\nchanged by someone else\n", encoding="utf-8")
    os.utime(fake_repo / "docs" / "notes.md", ns=(read["mtime"] * 1000 + 5_000_000,) * 2)
    with pytest.raises(CommandError, match="changed on disk: reload"):
        write("docs/notes.md", "# Mine\n", read["mtime"])
    assert "someone else" in (fake_repo / "docs" / "notes.md").read_text()
    assert not [r for r in event_log.read(fake_repo) if r["event"] == "file_saved"]


def test_a_save_that_passes_writes_the_file_and_records_it_without_its_text(host, fake_repo):
    read = host.command("files.read", {"path": "docs/notes.md"})
    got = host.command("files.write", {"path": "docs/notes.md", "text": "# Notes\n\nsecret plan\n", "mtime": read["mtime"]})
    assert got["ok"] is True and got["mtime"] == (fake_repo / "docs" / "notes.md").stat().st_mtime_ns // 1000
    assert (fake_repo / "docs" / "notes.md").read_text() == "# Notes\n\nsecret plan\n"
    again = host.command("files.write", {"path": "docs/notes.md", "text": "# Notes\n", "mtime": got["mtime"]})
    assert again["ok"] is True                                                 # saved again on the mtime it gave
    new = host.command("files.write", {"path": "docs/new.md", "text": "fresh\n", "mtime": None})
    assert new["ok"] and (fake_repo / "docs" / "new.md").read_text() == "fresh\n"
    saved = [r for r in event_log.read(fake_repo) if r["event"] == "file_saved"]
    assert [(r["kind"], r["bytes"]) for r in saved] == [("markdown", 21), ("markdown", 8), ("markdown", 6)]
    assert "secret plan" not in (fake_repo / event_log.PATH).read_text()
    assert "notes.md" not in (fake_repo / event_log.PATH).read_text()


def test_reveal_opens_the_systems_app_from_the_desktop_only(host, fake_repo):
    opened = []
    files = board_files.Files(host.projects, opener=opened.append)
    assert files.reveal({"path": "README.md"}) == {"started": True}
    _wait(lambda: opened)
    assert opened == [(fake_repo / "README.md").resolve()]
    from orkboard.gui.ideas_args import IdeasError
    with pytest.raises(IdeasError, match="phone"):
        files.reveal({"path": "README.md", "device": "phone"})
    with pytest.raises(IdeasError, match="secrets"):
        files.reveal({"path": ".env"})
    assert len(opened) == 1


def _wait(done) -> None:
    deadline = time.monotonic() + 30
    while not done() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert done()


def test_reveal_runs_off_the_server_thread_and_tells_when_no_app_opened(host, fake_repo):
    from orkboard.gui.ideas_args import IdeasError
    gate, entered, toasts, ran = threading.Event(), threading.Event(), [], []
    project = host.projects.current()
    host.bus.subscribe("toast", toasts.append)
    project.bus.subscribe("background.ran", ran.append)

    def opener(path):
        entered.set()
        assert gate.wait(30)
        raise IdeasError("No app opened it: nothing to open it with")

    files = board_files.Files(host.projects, opener=opener)
    assert files.reveal({"path": "README.md"}) == {"started": True}
    assert entered.wait(30)
    assert host.command("projects.list")["current"]                     # another command answers meanwhile
    assert "already running" in files.reveal({"path": "README.md"})["error"]
    gate.set()
    _wait(lambda: ran)
    assert ran[0].data["ok"] is False and "No app opened it" in ran[0].data["said"]
    assert any("No app opened it" in t.data["message"] for t in toasts)


def test_no_project_no_files():
    with pytest.raises(CommandError, match="Open a folder first"):
        Orkboard().command("files.tree", {})
