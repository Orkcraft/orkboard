"""Open folder's system dialog (gui/folder_dialog.py; the owner's notes of 19 October, 3): the window's dialog, else the
system's, on a thread of its own; a token, then what came of it."""
from __future__ import annotations

import sys
import time
import types

import pytest

from orkboard.gui import folder_dialog
from orkboard.gui.board_host import BoardPhone, Orkboard


@pytest.fixture(autouse=True)
def no_window(monkeypatch):
    monkeypatch.setattr(folder_dialog, "_window", None)
    monkeypatch.setattr(folder_dialog, "_picks", {})


def _done(token: str) -> dict:
    for _ in range(300):
        got = folder_dialog.result(token)
        if got["state"] != "open":
            return got
        time.sleep(0.01)
    raise AssertionError("the dialog never answered")


def test_the_systems_dialog_on_each_machine():
    every = lambda name: f"/usr/bin/{name}"                                       # noqa: E731
    mac = folder_dialog.command("/Users/me/code", "darwin", every)
    assert mac[0] == "osascript" and 'default location (POSIX file "/Users/me/code")' in mac[-1]
    assert "Choose a project's folder" in mac[-1]
    assert folder_dialog.command("/x", "win32", every)[0] == "/usr/bin/powershell"
    assert folder_dialog.command("/x", "linux", every)[:3] == ["zenity", "--file-selection", "--directory"]
    assert folder_dialog.command("/x", "linux", lambda n: "/k" if n == "kdialog" else None)[:2] == ["kdialog", "--getexistingdirectory"]
    assert folder_dialog.command("/x", "linux", lambda n: None) is None                  # none here: the path is typed
    assert folder_dialog.command("/x", "win32", lambda n: None) is None


def test_a_dialog_answers_by_its_token_and_is_forgotten_once_read():
    token = folder_dialog.start("~/code", ask=lambda begin: "/home/me/code/shop")
    assert _done(token) == {"state": "done", "path": "/home/me/code/shop", "why": ""}
    assert folder_dialog.result(token)["state"] == "error"                             # read once
    assert _done(folder_dialog.start(ask=lambda begin: None))["state"] == "none"          # cancelled

    def none(begin):
        raise folder_dialog.Unavailable("No folder dialog on this computer: type the folder's path.")
    got = _done(folder_dialog.start(ask=none))
    assert got["state"] == "error" and "type the folder's path" in got["why"] and "error" not in got

    def broken(begin):
        raise OSError("boom")
    assert "The folder dialog failed: OSError: boom" == _done(folder_dialog.start(ask=broken))["why"]   # never the server's


def test_the_apps_window_asks_with_its_own_dialog(monkeypatch, tmp_path):
    asked = []

    class Window:
        def create_file_dialog(self, kind, directory=""):
            asked.append((kind, directory))
            return (str(tmp_path / "shop"),)

    monkeypatch.setitem(sys.modules, "webview", types.SimpleNamespace(FOLDER_DIALOG=20))
    folder_dialog.attach(Window())
    assert folder_dialog.native(str(tmp_path)) == str(tmp_path / "shop")
    assert asked == [(20, str(tmp_path))]
    assert folder_dialog.native("/no/such/folder") == str(tmp_path / "shop") and asked[-1][1] != "/no/such/folder"


def test_no_dialog_here_says_to_type_the_path(monkeypatch):
    monkeypatch.setattr(folder_dialog, "command", lambda begin="": None)
    with pytest.raises(folder_dialog.Unavailable, match="type the folder's path"):
        folder_dialog.native()


def test_the_commands_are_the_desktops_and_never_a_phones(fake_repo):
    host = Orkboard(fake_repo)
    token = host.command("folders.pick", {"start": ""})["token"]
    assert isinstance(token, str) and host.command("folders.picked", {"token": token})["state"] in ("open", "none", "error")
    assert not BoardPhone.allowed(host, "folders.pick", {}) and not BoardPhone.allowed(host, "folders.picked", {})
