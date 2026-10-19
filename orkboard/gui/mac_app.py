"""Orkboard as a Mac app of its own (the owner's notes of 19 October, 1): `orkboard --make-app` puts Orkboard.app in
~/Applications, so it opens from the Dock, Launchpad and Spotlight as any app does, in its own window; and the window,
however it was started, is named Orkboard in the menu bar and the Dock, with its icon, not Python's.

The bundle is a launcher, not a copy: its one script starts the installed Orkboard (the Python it was made with) on
the last project, through the person's login shell and with the PATH it was made with, since an app opened from the
Dock gets neither (and without them no AI tool, git or brew is found). Its output goes to ~/Library/Logs/Orkboard.log.
Made again after a reinstall moves Orkboard's Python; an update of Orkboard itself needs nothing.

    make(Path.home() / "Applications", sys.executable, os.environ["PATH"])   # → …/Orkboard.app
    dress("Orkboard", ICON)                # in the window's process, before its window: the name and the Dock icon
"""
from __future__ import annotations

import os
import plistlib
import shlex
import struct
import sys
from pathlib import Path

from orkboard import __version__

NAME = "Orkboard"
BUNDLE_ID = "works.ork.orkboard"
INSTALL = "orkboard[gui] @ git+https://github.com/orkWorks/orkBoard"
ICON = Path(__file__).resolve().parent / "static" / "pwa" / "icon-512.png"


def icns(png: bytes) -> bytes:
    """An .icns of one 512 × 512 PNG (`ic09`): macOS draws it at every size the Dock and Finder need."""
    entry = b"ic09" + struct.pack(">I", 8 + len(png)) + png
    return b"icns" + struct.pack(">I", 8 + len(entry)) + entry


def info_plist() -> bytes:
    return plistlib.dumps({
        "CFBundleName": NAME, "CFBundleDisplayName": NAME, "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleExecutable": NAME, "CFBundleIconFile": f"{NAME}.icns", "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": __version__, "CFBundleVersion": __version__,
        "LSMinimumSystemVersion": "11.0", "NSHighResolutionCapable": True,
    })


def launcher(python: str, path: str) -> str:
    """The bundle's script: Orkboard through the login shell (its profile's PATH and settings) with `path` before it."""
    run = " ".join(shlex.quote(a) for a in (python, "-m", "orkboard.gui.board_host"))
    return "\n".join([
        "#!/bin/sh",
        "# Orkboard.app, made by `orkboard --make-app`: Orkboard on the last project, in its own window.",
        "# An app opened from the Dock has neither the shell's PATH nor its settings, so both are given here.",
        f"export PATH={shlex.quote(path)}\"${{PATH:+:$PATH}}\"",
        'mkdir -p "$HOME/Library/Logs"',
        '# the person\'s own shell when it reads `"$@"` as sh does (fish does not), else a Mac\'s own zsh',
        'case "${SHELL:-}" in */bash|*/zsh|*/sh|*/ksh) login="$SHELL" ;; *) login=/bin/zsh ;; esac',
        f'exec "$login" -lc \'exec "$@"\' orkboard {run} >>"$HOME/Library/Logs/Orkboard.log" 2>&1',
        "",
    ])


def make(folder: Path, python: str, path: str, icon: Path = ICON) -> Path:
    """Orkboard.app in `folder` (made again in place when it is there): its plist, its script and its icon."""
    app = Path(folder).expanduser() / f"{NAME}.app"
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True, exist_ok=True)
    (contents / "Resources").mkdir(parents=True, exist_ok=True)
    (contents / "Info.plist").write_bytes(info_plist())
    script = contents / "MacOS" / NAME
    script.write_text(launcher(python, path), encoding="utf-8")
    script.chmod(0o755)
    (contents / "Resources" / f"{NAME}.icns").write_bytes(icns(Path(icon).read_bytes()))
    return app


def make_here(folder: Path | None = None, platform: str = sys.platform) -> int:
    """`orkboard --make-app`: Orkboard.app in ~/Applications; says where, or why not."""
    if platform != "darwin":
        sys.stderr.write("orkboard: Orkboard.app is a Mac app; here Orkboard opens with `orkboard`\n")
        return 1
    app = make(folder or Path.home() / "Applications", sys.executable, os.environ.get("PATH", ""))
    print(f"{app} is made: open Orkboard from the Dock, Launchpad or Spotlight.")
    try:
        import webview  # noqa: F401
    except ImportError:
        print("It opens in the browser until pywebview is installed: uv tool install --reinstall "
              f"'{INSTALL}'")
    return 0


def dress(name: str = NAME, icon: Path = ICON) -> None:
    """In the window's process, before its window: the app's name in the menu bar and the Dock, and its icon, in place
    of Python's. A Mac only; anything missing (pyobjc, the icon) leaves Python's, never stops the window."""
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication, NSImage
        from Foundation import NSBundle
        bundle = NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        if info is not None:
            info["CFBundleName"] = name
        image = NSImage.alloc().initWithContentsOfFile_(str(icon))
        if image is not None:
            NSApplication.sharedApplication().setApplicationIconImage_(image)
    except Exception:                                  # Python's own name and icon stay
        pass
