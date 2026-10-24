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
from orkboard import __version__
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
                 "orders.answer", "phones.pair", "update.policy", "update.restart", "link.open"):
        assert not may(name, {}), name
    assert may("update.check") and may("update.install")         # a newer version, installed from the phone (shell-update.js)


def test_the_compact_snapshot_is_small_and_names_its_content(fake_repo):
    host = _host(fake_repo)
    host.tick()
    full, snap = host.snapshot(), host.command("mobile.snapshot")
    json.dumps(snap)
    assert snap["v"] == phones.API and snap["project"] == fake_repo.name
    assert len(json.dumps(snap)) < len(json.dumps(full))
    assert set(snap) == {"v", "project", "focus", "look", "ideas_rev", "ops_rev", "needs_you", "idea_states",
                         "review_count", "review_results", "limits", "reserve", "rate", "hud", "version", "update", "rev"}
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


def test_the_phone_sees_a_newer_version_small_and_installs_it(fake_repo, monkeypatch):
    """A newer Orkline on the phone (pwa/shell-update.js): what it is and a few notes, then `update.install` from the
    phone installs it on the computer, which restarts on it (gui/updates.py)."""
    from types import SimpleNamespace
    from orkboard.core import updates
    from orkboard.gui import updates as gui_updates
    host = _host(fake_repo)
    assert host.command("mobile.snapshot")["update"] is None
    host.updates._method = lambda: updates.Method("uv", (("uv", "tool", "upgrade", "orkboard"),))
    rels = [{"version": f"9.0.{n}", "notes": f"notes {n}"} for n in range(5, 0, -1)]
    host.updates._read(updates.State(manifest={"releases": rels}))
    u = host.command("mobile.snapshot")["update"]
    assert (u["version"], u["major"], u["critical"], u["can"], u["state"]) == ("9.0.5", True, False, True, "idle")
    assert u["notes"] == ["9.0.5: notes 5", "9.0.4: notes 4", "9.0.3: notes 3"] and u["current"] == __version__
    before = host.command("mobile.snapshot")["rev"]
    monkeypatch.setattr(gui_updates.threading, "Thread", lambda target, **kw: SimpleNamespace(start=target))
    monkeypatch.setattr(updates, "install", lambda way: updates.Result(True, "ok", "9.0.5"))
    monkeypatch.setattr(updates, "remember", lambda result, version: None)
    quits = []
    host.updates.quit = lambda: quits.append(1)
    assert BoardPhone.allowed(host, "update.install", {})
    host.command("update.install", BoardPhone.guard("update.install", {}, {"id": "d1"}))
    assert quits == [1] and host.updates.restart_wanted                 # the window closes: `orkboard` opens again on 9.0.5
    after = host.command("mobile.snapshot")
    assert after["update"]["state"] == "installed" and after["rev"] != before
    host.close()
