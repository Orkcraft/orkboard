"""The mobile API on Orkboard's host (docs/design/mobile.md; gui/board_host.py `BoardPhone`): the handshake, the
compact snapshot and what a phone may send. Orkline's phone face (gui/mobile.py: the town's acts, its questions, the
notifier) stays there."""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from orkboard.gui import phones
from orkboard.gui.board_host import BoardPhone, Orkboard
from orkboard.gui.server import PROTOCOL, Server


def _host(repo: Path) -> Orkboard:
    return Orkboard(repo)


def test_every_command_a_phone_may_send_is_one_the_host_has(fake_repo):
    host = _host(fake_repo)
    assert set(BoardPhone.COMMANDS) <= set(host.commands)
    hello = host.command("mobile.hello")
    json.dumps(hello)
    assert hello["name"] == "orkcraft" and hello["api"] == phones.API
    assert "ideas.board" in hello["commands"] and "halt" in hello["commands"]


def test_a_phone_may_send_the_boards_commands_and_halt_but_not_build_or_type(fake_repo):
    host = _host(fake_repo)
    may = lambda name, args=None: BoardPhone.allowed(host, name, args)      # noqa: E731
    assert may("halt") and may("mobile.snapshot") and may("ideas.answer") and may("ideas.merge")
    assert not may("ideas.nothing") and not may("act", {"id": "pit", "act": "drop"})
    for name in ("town.build", "town.demolish", "term.input", "sessions.new", "hut.move", "roads.lay",
                 "orders.answer", "phones.pair", "update.install", "link.open"):
        assert not may(name, {}), name


def test_the_compact_snapshot_is_small_and_names_its_content(fake_repo):
    host = _host(fake_repo)
    host.tick()
    full, snap = host.snapshot(), host.command("mobile.snapshot")
    json.dumps(snap)
    assert snap["v"] == phones.API and snap["project"] == fake_repo.name
    assert len(json.dumps(snap)) < len(json.dumps(full))
    assert set(snap) == {"v", "project", "focus", "look", "ideas_rev", "ops_rev", "needs_you", "idea_states",
                         "review_count", "review_results", "limits", "hud", "rev"}
    assert snap["focus"] == "board" and snap["look"] == "office"
    assert "words" not in snap and "projects" not in snap
    assert host.command("mobile.snapshot", {"since": snap["rev"]}) == {"v": phones.API, "rev": snap["rev"],
                                                                       "same": True}
    host.command("ideas.track_add", {"title": "A goal"})                   # what the Board holds: the phone's too
    moved = host.command("mobile.snapshot", {"since": snap["rev"]})
    assert not moved.get("same") and moved["ideas_rev"] > snap["ideas_rev"]
    assert host.command("mobile.snapshot", {"since": "older"})["idea_states"] == []


@pytest.mark.asyncio
async def test_the_version_handshake_takes_the_token(fake_repo):
    server = Server(_host(fake_repo))
    task = asyncio.create_task(server.run())
    for _ in range(100):
        if server.ready.is_set():
            break
        await asyncio.sleep(0.02)

    def get(path: str, headers: dict | None = None) -> tuple[int, dict]:
        req = urllib.request.Request(f"{server.origin}{path}", headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, {}
    try:
        assert (await asyncio.to_thread(get, "/api/version"))[0] == 403
        assert (await asyncio.to_thread(get, "/api/version?t=guess"))[0] == 403
        status, body = await asyncio.to_thread(get, f"/api/version?t={server.token}")
        assert status == 200 and body == {"name": "orkcraft", "version": body["version"], "protocol": PROTOCOL,
                                          "api": phones.API}
        status, _ = await asyncio.to_thread(get, "/api/version", {"Authorization": f"Bearer {server.token}"})
        assert status == 200
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)
