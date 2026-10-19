"""Orkboard as a Mac app of its own (gui/mac_app.py; the owner's notes of 19 October, 1): `orkboard --make-app` makes
Orkboard.app, a launcher through the login shell with the PATH it was made with; the window wears Orkboard's name and
icon, not Python's."""
from __future__ import annotations

import os
import plistlib
import subprocess
import sys
import types

from orkboard.gui import board_host, mac_app


def test_the_app_is_a_plist_a_script_and_an_icon(tmp_path):
    app = mac_app.make(tmp_path, "/opt/ork/python3", "/opt/homebrew/bin:/usr/bin")
    assert app == tmp_path / "Orkboard.app"
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    assert info["CFBundleName"] == "Orkboard" and info["CFBundleExecutable"] == "Orkboard"
    assert info["CFBundleIdentifier"] == "works.ork.orkboard" and info["CFBundleIconFile"] == "Orkboard.icns"
    script = app / "Contents" / "MacOS" / "Orkboard"
    assert os.access(script, os.X_OK)
    text = script.read_text(encoding="utf-8")
    assert "export PATH=/opt/homebrew/bin:/usr/bin" in text and "/opt/ork/python3 -m orkboard.gui.board_host" in text
    assert "Library/Logs/Orkboard.log" in text
    icon = (app / "Contents" / "Resources" / "Orkboard.icns").read_bytes()
    png = mac_app.ICON.read_bytes()
    assert icon[:4] == b"icns" and int.from_bytes(icon[4:8], "big") == len(icon) and icon[8:12] == b"ic09"
    assert icon.endswith(png)
    assert mac_app.make(tmp_path, "/opt/ork/python3", "/usr/bin") == app                      # made again in place


def test_the_launcher_starts_orkboard_through_the_login_shell_with_its_path(tmp_path):
    seen = tmp_path / "seen.txt"
    python = tmp_path / "python3"                    # a Python that says how it was started
    python.write_text(f'#!/bin/sh\necho "$PATH" > {seen}\necho "$@" >> {seen}\n', encoding="utf-8")
    python.chmod(0o755)
    app = mac_app.make(tmp_path, str(python), "/made/with/this")
    home = tmp_path / "mac-home"                     # the Dock's HOME, apart from the tests' own
    home.mkdir()
    subprocess.run([str(app / "Contents" / "MacOS" / "Orkboard")], check=True, timeout=30,
                   env={"HOME": str(home), "SHELL": "/bin/sh", "PATH": "/usr/bin:/bin"})
    path, args = seen.read_text(encoding="utf-8").splitlines()
    assert "/made/with/this" in path.split(":") and args == "-m orkboard.gui.board_host"   # the profile may add its own
    assert (home / "Library" / "Logs" / "Orkboard.log").exists()


def test_make_app_is_a_macs(capsys, monkeypatch, tmp_path):
    assert mac_app.make_here(tmp_path, platform="linux") == 1
    assert "Mac app" in capsys.readouterr().err
    monkeypatch.setattr(mac_app.sys, "platform", "linux")
    assert board_host.main(["--make-app"]) == 1
    monkeypatch.setattr(mac_app, "make", lambda folder, python, path: tmp_path / "Orkboard.app")
    assert mac_app.make_here(tmp_path, platform="darwin") == 0
    assert "Orkboard.app is made" in capsys.readouterr().out


def test_the_window_wears_orkboards_name_and_icon_on_a_mac(monkeypatch):
    calls = []
    info: dict = {}

    class Bundle:
        def localizedInfoDictionary(self):
            return None

        def infoDictionary(self):
            return info

    class App:
        def setApplicationIconImage_(self, image):
            calls.append(("icon", image))

    class Image:
        @staticmethod
        def alloc():
            return Image()

        def initWithContentsOfFile_(self, path):
            calls.append(("image", path))
            return "the-image"

    monkeypatch.setitem(sys.modules, "AppKit", types.SimpleNamespace(
        NSApplication=types.SimpleNamespace(sharedApplication=lambda: App()), NSImage=Image))
    monkeypatch.setitem(sys.modules, "Foundation", types.SimpleNamespace(NSBundle=types.SimpleNamespace(mainBundle=lambda: Bundle())))
    monkeypatch.setattr(mac_app.sys, "platform", "darwin")
    mac_app.dress()
    assert info["CFBundleName"] == "Orkboard" and calls == [("image", str(mac_app.ICON)), ("icon", "the-image")]
    monkeypatch.delitem(sys.modules, "AppKit")
    monkeypatch.setitem(sys.modules, "AppKit", None)                                     # no pyobjc: Python's stay
    mac_app.dress()
    monkeypatch.setattr(mac_app.sys, "platform", "linux")
    calls.clear()
    mac_app.dress()
    assert calls == []


def test_the_name_and_icon_only_when_a_window_opens(monkeypatch):
    dressed, made = [], []

    class Webview:
        @staticmethod
        def create_window(*a, **k):
            made.append(dressed[:])
            return types.SimpleNamespace(destroy=lambda: None)

        @staticmethod
        def start():
            return None

    host = types.SimpleNamespace(updates=types.SimpleNamespace(quit=None))
    server = types.SimpleNamespace(url="http://127.0.0.1:1", stop=lambda: None)
    thread = types.SimpleNamespace(join=lambda *a: None)
    monkeypatch.setitem(sys.modules, "webview", Webview)
    board_host.show(host, server, thread, False, toolkit=lambda: True, dress=lambda: dressed.append(1))
    assert made == [[1]]                                                             # before its window
    monkeypatch.setattr(board_host, "_in_browser", lambda *a: None)
    board_host.show(host, server, thread, True, toolkit=lambda: True, dress=lambda: dressed.append(2))
    assert dressed == [1]                                                            # the browser: no Dock icon
