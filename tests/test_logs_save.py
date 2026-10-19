"""Save logs (gui/logs_save.py, realm/diagnostics.py; the owner's notes of 19 October): an error's Save logs and the
gear's day logs go to the Downloads folder as one zip with where Orkboard runs, never an environment's value."""
from __future__ import annotations

import io
import json
import types
import zipfile

import pytest

from orkboard import tools
from orkboard.gui import logs_save
from orkboard.gui.board_host import BoardPhone, Orkboard
from orkboard.realm import diagnostics

ABOUT = {"orkboard": "x", "tools": [], "env": {}}


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()


def _host(packed):
    return types.SimpleNamespace(day_logs=types.SimpleNamespace(pack_period=lambda days: packed), machine=None)


def _names(data: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {n: z.read(n).decode("utf-8") for n in z.namelist()}


def test_the_days_zip_gains_where_orkboard_runs_and_the_words_on_the_screen(tmp_path):
    got = _names(logs_save.pack(_host(("a.zip", _zip({"README.md": "# The day", "2026-10-19/board/calls.jsonl": "{}\n"}))),
                                said="Claude Code is not signed in", about=ABOUT))
    assert got["README.md"] == "# The day" and "2026-10-19/board/calls.jsonl" in got
    assert json.loads(got["about.json"]) == ABOUT and got["on-screen.txt"] == "Claude Code is not signed in\n"
    empty = _names(logs_save.pack(_host(None), about=ABOUT))                  # nothing kept yet: about.json still
    assert "No model call is kept" in empty["README.md"] and "about.json" in empty and "on-screen.txt" not in empty


def test_saved_in_the_downloads_folder_and_shown_only_there(tmp_path):
    (tmp_path / "Downloads").mkdir()
    assert logs_save.folder(tmp_path) == tmp_path / "Downloads"
    assert logs_save.folder(tmp_path / "nowhere") == tmp_path / "nowhere"                # no Downloads: the home folder
    where = tmp_path / "Downloads"
    got = logs_save.save(_host(None), where=where, about=ABOUT)
    path = where / got["name"]
    assert got["path"] == str(path) and path.is_file() and got["name"].startswith("orkboard-logs-")
    started = []
    assert logs_save.show(str(path), where, start=lambda cmd, **kw: started.append(cmd)) == {"ok": True}
    assert started == [logs_save.reveal_cmd(path)]
    (tmp_path / "secret.zip").write_bytes(b"x")
    for other in (tmp_path / "secret.zip", where / "notes.txt", where / "orkboard-logs-gone.zip"):
        with pytest.raises(logs_save.LogsError, match="Only logs saved by Orkline"):
            logs_save.show(str(other), where, start=lambda cmd, **kw: started.append(cmd))
    assert len(started) == 1


def test_the_systems_way_to_show_a_file():
    assert logs_save.reveal_cmd(logs_save.Path("/u/Downloads/a.zip"), "darwin") == ["open", "-R", "/u/Downloads/a.zip"]
    assert logs_save.reveal_cmd(logs_save.Path("/u/Downloads/a.zip"), "linux") == ["xdg-open", "/u/Downloads"]
    assert logs_save.reveal_cmd(logs_save.Path("C:/u/a.zip"), "win32")[0] == "explorer"


def test_an_environments_values_are_never_written():
    env = {"ANTHROPIC_API_KEY": "sk-ant-secret", "CLAUDE_CODE_OAUTH_TOKEN": "tok", "PATH": "/opt/homebrew/bin:/usr/bin",
           "CLAUDE_CONFIG_DIR": "/Users/me/.claude-work", "SECRET_OTHER": "x", "ORKBOARD_FROM": "app"}
    got = diagnostics.env_of(env)
    assert got == {"ANTHROPIC_API_KEY": "set", "CLAUDE_CODE_OAUTH_TOKEN": "set", "PATH": "/opt/homebrew/bin:/usr/bin",
                   "CLAUDE_CONFIG_DIR": "/Users/me/.claude-work", "ORKBOARD_FROM": "app"}
    claude = next(t for t in tools.TOOLS if t.id == "claude")
    seen = [tools.ToolStatus(claude, found=True, path="/usr/local/bin/claude", version="1.0.3", logged_in=True)]
    machine = types.SimpleNamespace(tools={"claude": types.SimpleNamespace(enabled=True, billing="subscription")})
    said = {"code": 1, "loggedIn": False, "authMethod": "none", "configDirectory": "/Users/me/.claude-work"}
    about = diagnostics.about(machine, detect=lambda: seen, env=env, auth=lambda path: said)
    text = json.dumps(about)
    assert "sk-ant-secret" not in text and "tok\"" not in text and about["launched"] == "app"
    assert about["tools"] == [{"id": "claude", "found": True, "path": "/usr/local/bin/claude", "version": "1.0.3",
                               "signed_in": True, "billing_seen": "subscription", "turned_on": True, "billing": "subscription",
                               "auth_status": said}]


def test_claude_says_its_sign_in_as_this_process_sees_it_and_names_no_person():
    import subprocess as sp
    asked = []

    def run(cmd, **kw):
        asked.append((cmd, kw["env"].get("CLAUDE_CONFIG_DIR")))
        return sp.CompletedProcess(cmd, 1, json.dumps({"loggedIn": False, "authMethod": "none", "email": "me@x.org",
                                                       "configDirectory": "/Users/me/.claude", "orgName": "Mine"}), "")
    got = tools.claude_auth("/usr/local/bin/claude", run, env={"CLAUDE_CONFIG_DIR": "/Users/me/.claude"})
    assert got == {"code": 1, "loggedIn": False, "authMethod": "none", "configDirectory": "/Users/me/.claude"}
    assert asked == [(["/usr/local/bin/claude", "auth", "status"], "/Users/me/.claude")]
    assert tools.claude_auth("/x", lambda cmd, **kw: sp.CompletedProcess(cmd, 1, "Not logged in\nRun claude", "")) == \
        {"code": 1, "said": "Not logged in"}

    def gone(cmd, **kw):
        raise OSError("no such file")
    assert tools.claude_auth("/x", gone) == {}


def test_the_commands_are_the_desktops_and_never_a_phones(fake_repo, tmp_path, monkeypatch):
    monkeypatch.setattr(logs_save, "folder", lambda home=None: tmp_path)
    monkeypatch.setattr(diagnostics, "about", lambda machine=None, **kw: ABOUT)
    host = Orkboard(fake_repo)
    got = host.command("logs.save", {"said": "it failed", "days": 1})
    assert (tmp_path / got["name"]).is_file() and _names((tmp_path / got["name"]).read_bytes())["on-screen.txt"] == "it failed\n"
    assert host.command("logs.show", {"path": "/etc/passwd"}) == {"error": "Only logs saved by Orkline are shown"}
    assert not BoardPhone.allowed(host, "logs.save", {}) and not BoardPhone.allowed(host, "logs.show", {})
