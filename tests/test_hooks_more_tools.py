"""The Warder for Hermes, Cursor and pi (hooks/warder.py, hooks/pi_extension.py): each tool's payload is judged as the
Claude Code tool it is, and each hears the verdict its way. Installing the hooks (hooks/install.py) is Orkline's."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from orkboard.hooks import pi_extension, warder


def _warder(monkeypatch, capsys, harness: str, payload: dict) -> str:
    monkeypatch.setattr(sys, "argv", ["warder", harness])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(warder, "log", lambda *a, **k: None)
    assert warder.main() == 0
    return capsys.readouterr().out.strip()


@pytest.mark.parametrize("harness, payload", [
    ("hermes", {"tool_name": "terminal", "tool_input": {"command": "rm -rf /"}, "cwd": "/tmp"}),
    ("cursor", {"hook_event_name": "preToolUse", "tool_name": "Shell", "tool_input": {"command": "rm -rf /"},
                "workspace_roots": ["/tmp"]}),
    ("cursor", {"hook_event_name": "beforeShellExecution", "command": "rm -rf /", "cwd": "/tmp"}),
    ("pi", {"tool_name": "bash", "tool_input": {"command": "rm -rf /"}, "cwd": "/tmp"}),
])
def test_each_tool_hears_a_deny_its_way(monkeypatch, capsys, harness, payload):
    said = json.loads(_warder(monkeypatch, capsys, harness, payload))
    if harness == "hermes":
        assert said["decision"] == "block" and "Warder" in said["reason"]
    elif harness == "cursor":
        assert said["permission"] == "deny" and "Warder" in said["agent_message"]
    else:
        assert said["decision"] == "deny"


def test_a_secret_file_is_kept_from_every_tool(monkeypatch, capsys):
    for harness, name, args in (("hermes", "read_file", {"path": ".env"}), ("cursor", "Read", {"path": ".env"}),
                                ("pi", "read", {"path": ".env"})):
        out = _warder(monkeypatch, capsys, harness, {"tool_name": name, "tool_input": args, "cwd": "/tmp"})
        assert "deny" in out or "block" in out


def test_an_ask_goes_to_hermes_own_gate_and_nothing_said_is_nothing(monkeypatch, capsys):
    said = json.loads(_warder(monkeypatch, capsys, "hermes",
                              {"tool_name": "terminal", "tool_input": {"command": "git reset --hard"}, "cwd": "/tmp"}))
    assert said["action"] == "approve"
    assert _warder(monkeypatch, capsys, "hermes", {"tool_name": "terminal", "tool_input": {"command": "ls"}}) == ""
    assert _warder(monkeypatch, capsys, "cursor", {"tool_name": "Shell", "tool_input": {"command": "ls"}}) == "{}"


def test_pi_extension_carries_this_python_and_is_written_once(tmp_path: Path):
    path = pi_extension.write(tmp_path / "x.ts")
    text = path.read_text()
    assert json.dumps(sys.executable) in text and 'pi.on("tool_call"' in text and "block: true" in text
    mtime = path.stat().st_mtime_ns
    assert pi_extension.write(tmp_path / "x.ts") == path and path.stat().st_mtime_ns == mtime
