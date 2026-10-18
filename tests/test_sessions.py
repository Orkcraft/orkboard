"""Sessions: the merged session sources (sources/sessions.py) and the command a session is resumed or deployed
with. The hook that records them (hooks/session.py) is Orkline's: its log line is written here as it writes it."""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from orkboard.sources import sessions as ss

REAL_REPO = Path(__file__).resolve().parent.parent.parent


def _logged(repo: Path, harness: str, session: str, tickets: list[str]) -> None:
    """A line of `<repo>/.orkcraft/sessions.jsonl` as Orkline's session hook (hooks/session.py `record`) writes it."""
    log = repo / ".orkcraft" / "sessions.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": "2026-10-18T09:00:00", "harness": harness, "event": "", "session": session, "tickets": tickets,
             "cwd": "", "transcript": "", "prompt": ""}
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _claude_transcript(folder: Path, sid: str, prompt: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    rows = [
        {"type": "queue-operation", "sessionId": sid},
        {"type": "user", "message": {"role": "user", "content": prompt}, "sessionId": sid},
        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "T9999"}]}},
    ]
    (folder / f"{sid}.jsonl").write_text("\n".join(json.dumps(r, separators=(",", ":")) for r in rows), encoding="utf-8")


def test_sessions_merge_log_transcripts_agy_and_git(fake_repo: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ORKCRAFT_CLAUDE_HOME", str(tmp_path / "claude"))
    monkeypatch.setenv("ORKCRAFT_AGY_HOME", str(tmp_path / "agy"))
    _claude_transcript(ss.claude_projects_dir(fake_repo), "loc-1", "поработай над [[T1001]]")
    (tmp_path / "agy" / "brain" / "conv-7").mkdir(parents=True)
    _logged(fake_repo, "agy", "conv-7", ["T1002"])                  # the hook heard agy's conversation, its ticket
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m",
                    "task(T1003): x\n\nClaude-Session: https://claude.ai/code/session_ABC123"], cwd=fake_repo, check=True)

    found = {s.key: s for s in ss.collect_sessions(fake_repo, max_age=0)}
    local = found["claude:loc-1"]
    assert local.tickets == {"T1001"} and local.title.startswith("поработай")  # tool results ignored
    assert found["agy:conv-7"].tickets == {"T1002"}
    web = found["claude-web:session_ABC123"]
    assert web.tickets == {"T1003"} and web.url.endswith("session_ABC123") and not web.resumable

    assert ss.resume_command(local)[-2:] == ["--resume", "loc-1"]
    assert ss.resume_command(found["agy:conv-7"])[-2:] == ["--conversation", "conv-7"]
    assert ss.resume_command(web) is None
    assert [s.key for s in ss.sessions_for(list(found.values()), "T1002")] == ["agy:conv-7"]


@pytest.fixture
def fake_cli(tmp_path: Path, monkeypatch) -> Path:
    """A stand-in for `claude`: prints its args and ticket, echoes one line back."""
    script = tmp_path / "fake-claude"
    script.write_text("#!/bin/bash\necho \"args:$* ticket:$ORKCRAFT_TICKET\"\nread line\necho \"you said:$line\"\nsleep 5\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("ORKCRAFT_CLAUDE_BIN", str(script))
    monkeypatch.setenv("ORKCRAFT_CLAUDE_HOME", str(tmp_path / "claude"))
    monkeypatch.setenv("ORKCRAFT_AGY_HOME", str(tmp_path / "agy"))
    return script


async def _wait_for(pilot, predicate, tries: int = 40):
    for _ in range(tries):
        if predicate():
            return True
        await pilot.pause(0.05)
    return predicate()


def test_deploy_command_passes_orders_as_one_safe_argument(monkeypatch):
    from orkboard.sources.sessions import deploy_command

    monkeypatch.setenv("ORKCRAFT_CLAUDE_BIN", "claude")
    assert deploy_command("claude", "") == ["claude"]
    assert deploy_command("claude", "You are Coder. Orders: take T1001; rm -rf nothing") == \
        ["claude", "You are Coder. Orders: take T1001; rm -rf nothing"]
    assert deploy_command("claude", "--dangerously-skip-permissions") == \
        ["claude", "Orders: --dangerously-skip-permissions"]
    assert deploy_command("agy", "anything") is None
