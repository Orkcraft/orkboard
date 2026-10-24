"""Usage stats and crash reports in Orkboard (docs/specs/41-orkget.md §7): orkGet's copy bound to Orkboard's profile,
one answer per machine with Orkline, `app_opened` and `app_closed` only, the page's own errors reported, and
`orkboard usage …` from the terminal. Nothing leaves the machine here: what would be sent is caught."""
from __future__ import annotations

import json
import sys

import pytest

from orkboard import settings
from orkboard.core import crashes, usage
from orkboard.orkget import crashes as copy_crashes


@pytest.fixture
def sent(monkeypatch):
    """Usage stats and crash reports on, and what they would send kept here instead."""
    monkeypatch.delenv("ORKCRAFT_NO_USAGE", raising=False)
    monkeypatch.delenv("CI", raising=False)
    out: list[tuple[str, dict]] = []
    keep = lambda url, data: out.append((url, json.loads(data)))   # noqa: E731
    monkeypatch.setattr("orkboard.orkget.usage._post", keep)
    monkeypatch.setattr(copy_crashes, "_post", keep)
    return out


def test_orkboard_sends_only_its_two_events():
    assert set(usage.events("orkboard")) - {"install_started", "install_step", "install_finished"} \
        == {"app_opened", "app_closed"}
    assert usage.clean("building_built", {"type": "lake"}) is None                 # Orkline's own: never Orkboard's
    assert usage.clean("app_opened", {"face": "gui", "tools": ["claude"], "project": "secret"}) \
        == {"face": "gui", "tools": ["claude"]}


def test_nothing_is_sent_before_a_yes(fake_repo, sent):
    from orkboard.gui.board_host import Orkboard
    host = Orkboard(fake_repo)
    assert host.snapshot()["usage_ask"] is True
    host.opened()
    host.close()
    assert sent == []


def test_a_yes_says_hello_as_orkboard_and_a_close_says_goodbye(fake_repo, sent):
    from orkboard.gui.board_host import Orkboard
    host = Orkboard(fake_repo)
    assert host.command("usage.share", {"share": True}) is True
    assert settings.load().usage is True and len(settings.load().install_id) == 32      # one answer for the machine
    assert host.snapshot()["usage_ask"] is False
    host.close()
    events = [e for url, body in sent if url.endswith("/v1/events") for e in body["events"]]
    assert [e["event"] for e in events] == ["app_opened", "app_closed"]
    body = next(body for url, body in sent if url.endswith("/v1/events"))
    assert body["product"] == "orkboard" and body["install_id"] == settings.load().install_id
    sessions = [body for url, body in sent if url.endswith("/v1/crash")]
    assert sessions and all(b["product"] == "orkboard" for b in sessions)


def test_a_no_forgets_the_id_and_sends_nothing(fake_repo, sent):
    from orkboard.gui.board_host import Orkboard
    host = Orkboard(fake_repo)
    host.command("usage.share", {"share": True})
    host.command("usage.share", {"share": False})
    sent.clear()
    host.opened()
    host.close()
    assert sent == [] and settings.load().install_id == "" and settings.load().usage is False


def test_the_pages_error_is_kept_and_reported_as_orkboards(fake_repo, sent, tmp_path):
    from orkboard.gui.board_host import Orkboard
    host = Orkboard(fake_repo)
    host.command("usage.share", {"share": True})
    host.command("crash.window", {"message": "TypeError: x is undefined at /home/me/secret.js",
                                  "stack": "at draw (http://127.0.0.1:5/static/js/shell/update.js:12:3)"})
    reports = [item for url, body in sent if url.endswith("/v1/crash") for item in body["items"]
               if item["type"] == "event"]
    assert len(reports) == 1, "the page's error goes to the proxy"
    said = json.dumps(reports)
    assert "secret" not in said and "/home/me" not in said and "static/js/shell/update.js" in said
    host.close()


def test_a_crash_is_kept_on_this_machine_named_with_orkboard(fake_repo, tmp_path):
    from orkboard.gui.board_host import Orkboard
    host = Orkboard(fake_repo)
    try:
        raise ValueError("broke")
    except ValueError as e:
        crashes.capture(e, where="command")
    files = list(crashes.log_dir().glob("crash-*"))
    assert files and all("orkboard" in f.name for f in files)
    host.close()


def test_the_host_puts_the_hooks_back_when_it_closes(fake_repo):
    from orkboard.gui.board_host import Orkboard
    before = sys.excepthook
    host = Orkboard(fake_repo)
    assert sys.excepthook is not before
    host.close()
    assert sys.excepthook is before


# -- the terminal -------------------------------------------------------------------------------------------------

def test_orkboard_usage_on_keeps_the_installers_id(capsys):
    from orkboard.gui.board_host import main
    assert main(["usage", "on", "--id", "a" * 32]) == 0
    assert settings.load().usage is True and settings.load().install_id == "a" * 32
    assert "install id: " + "a" * 32 in capsys.readouterr().out
    assert main(["usage", "off"]) == 0 and settings.load().install_id == ""
    assert main(["usage", "on", "--id", "nope"]) == 2


def test_a_folder_named_usage_still_opens(monkeypatch, tmp_path):
    from orkboard.gui import board_host
    seen = []
    monkeypatch.setattr(board_host, "run", lambda root, **kw: seen.append(root) or 0)
    (tmp_path / "usage").mkdir()
    monkeypatch.chdir(tmp_path)
    assert board_host.main(["./usage"]) == 0 and seen == [(tmp_path / "usage").resolve()]
