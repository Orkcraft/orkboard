"""Crash reports and usage stats in Orkboard (core/crashes.py, core/usage.py, orkGet's docs/crashes.md and usage.md):
what is Orkboard's own. The reporter and the stats are orkGet's copy, whose own tests run in orkGet once for each
product; here: the host reports the page's errors and a broken command by Orkboard's own files, names Orkboard in
what it sends, sends only after the one answer, and `orkboard usage` gives that answer."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from orkboard import product, settings
from orkboard.core import crashes, usage
from orkboard.gui import board_host


@pytest.fixture
def sharing(monkeypatch):
    """Usage stats and crash reports allowed here (conftest turns them off), a proxy address, no CI."""
    for name in ("ORKCRAFT_NO_USAGE", "DO_NOT_TRACK", "CI", "ORKCRAFT_USAGE_DEBUG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ORKCRAFT_USAGE_URL", "https://usage.example/v1/events")


def _wait(sent: list, n: int) -> None:
    for t in threading.enumerate():
        if t.name in ("crash-report", "usage"):
            t.join(5)
    assert len(sent) >= n, sent


def _yes() -> None:
    assert board_host.main(["usage", "on"]) == 0


def test_the_reporter_and_the_stats_are_orkgets_copy_bound_to_orkboard():
    import orkboard.orkget.crashes as copy_crashes
    import orkboard.orkget.usage as copy_usage
    assert crashes is copy_crashes and usage is copy_usage
    assert set(usage.EVENTS) == {"app_opened", "app_closed", "install_started", "install_step", "install_finished"}
    import orkboard
    assert crashes.roots() == [("orkboard", Path(orkboard.__file__).resolve().parent)]


def test_orkboards_own_frames_keep_their_path_in_the_package():
    where = crashes.roots()[0][1]
    f = crashes.frame(str(where / "gui" / "board_host.py"), "command", 12)
    assert f == {"file": "orkboard/gui/board_host.py", "function": "command", "line": 12, "in_app": True}


def test_the_page_reports_its_errors_by_its_own_scripts(sharing, fake_repo):
    _yes()
    host = board_host.Orkboard(fake_repo)
    try:
        sent: list = []
        host.crashes._send = lambda url, data: sent.append((url, json.loads(data)))
        host.command("crash.window", {"message": "TypeError: b.card is undefined for '/Users/ann/x'",
                                      "stack": "Board@http://127.0.0.1:5000/static/js/shell/shell.js:120:7\n"
                                               "render@http://127.0.0.1:5000/static/js/vendor/preact.js:1:9\n"
                                               "evil@file:///Users/ann/x.js:1:1"})
        _wait(sent, 1)
        url, body = sent[0]
        assert url == "https://usage.example/v1/crash" and body["product"] == "orkboard"
        event = body["items"][0]
        assert event["platform"] == "javascript" and event["where"] == "window"
        assert event["exceptions"][0]["value"] == "b.card is undefined for '…'"
        assert [f["file"] for f in event["exceptions"][0]["frames"]] == ["static/js/vendor/preact.js",
                                                                        "static/js/shell/shell.js"]
        assert "ann" not in json.dumps(sent)
    finally:
        host.close()


def test_a_broken_command_is_reported_with_its_name(sharing, fake_repo):
    from orkboard.gui.server import Server
    _yes()
    host = board_host.Orkboard(fake_repo)
    try:
        sent: list = []
        host.crashes._send = lambda url, data: sent.append(json.loads(data))
        host.commands["ideas.board"] = lambda a: 1 / 0
        reply = Server(host)._handle(json.dumps({"t": "cmd", "id": 1, "name": "ideas.board", "args": {}}))
        assert reply["ok"] is False and "ZeroDivisionError" in reply["error"]
        _wait(sent, 1)
        event = sent[0]["items"][0]
        assert event["command"] == "ideas.board" and event["exceptions"][0]["type"] == "ZeroDivisionError"
        assert any(f["file"] == "orkboard/gui/server.py" and f["in_app"] for f in event["exceptions"][0]["frames"])
        assert sent[0]["app_version"] == product.PRODUCT.version
    finally:
        host.close()


def test_nothing_is_sent_without_a_yes_but_the_traceback_stays_here(sharing, fake_repo, tmp_path):
    host = board_host.Orkboard(fake_repo)
    try:
        sent: list = []
        host.crashes._send = lambda url, data: sent.append(data)
        host.usage._send = lambda url, data: sent.append(data)
        try:
            raise KeyError("/home/someone/secret-plan.md")
        except KeyError as e:
            host.capture(e, "command")
    finally:
        host.close()
    assert sent == []
    (kept,) = (tmp_path / "crashes").glob("crash-*.txt")
    assert kept.name.startswith("crash-orkboard-") and "secret-plan" in kept.read_text()


def test_orkboard_says_when_it_opens_and_closes_and_nothing_else(sharing, fake_repo, monkeypatch):
    _yes()
    sent: list = []
    monkeypatch.setattr(usage, "_post", lambda url, data: sent.append((url, json.loads(data))))
    host = board_host.Orkboard(fake_repo)
    host.usage.track("building_built", type="lake")            # Orkline's event: never Orkboard's
    host.close()
    _wait(sent, 1)
    events = [e for _, body in sent for e in body["events"]]
    assert [e["event"] for e in events] == ["app_opened", "app_closed"]
    assert events[0]["props"]["face"] == "gui" and set(events[0]["props"]) <= {"face", "tools"}
    assert {body["product"] for _, body in sent} == {"orkboard"}
    assert {url for url, _ in sent} == {"https://usage.example/v1/events"}


def test_usage_on_off_and_status_give_the_one_answer(capsys):
    assert board_host.main(["usage", "status"]) == 0
    assert "usage stats and crash reports: not asked yet (off)" in capsys.readouterr().out
    assert board_host.main(["usage", "on", "--id", "a" * 32]) == 0
    m = settings.load()
    assert m.usage is True and m.install_id == "a" * 32
    assert f"install id: {'a' * 32}" in capsys.readouterr().out
    assert board_host.main(["usage", "off"]) == 0
    m = settings.load()
    assert m.usage is False and m.install_id == ""
    assert board_host.main(["usage", "on", "--id", "not-hex"]) == 2
    assert "--id must be 32 hex digits" in capsys.readouterr().err
    assert settings.load().usage is False


def test_a_folder_named_like_a_command_still_opens_as_a_folder(monkeypatch, tmp_path):
    opened, started = [], []
    monkeypatch.setattr(board_host, "start_folder", lambda folder, machine: started.append(folder) or tmp_path)
    monkeypatch.setattr(board_host, "run", lambda root, **kw: opened.append(root) or 0)
    assert board_host.main(["./usage"]) == 0
    assert started == [Path("./usage")] and opened == [tmp_path]
    assert board_host.main(["usage", "status"]) == 0 and len(opened) == 1      # the command opens no window
