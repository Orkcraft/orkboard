"""Open folder's system dialog (the owner's notes of 19 October, 3): a project's folder chosen in the system's own
picker, not typed.

A page (in the app's window or a browser) gets no path from a picker of its own, so the host picks: pywebview's folder
dialog in the app's window (`attach` hands it the window, board_host.run), else the system's (`osascript`,
`zenity`/`kdialog`, PowerShell). A dialog runs on a thread of its own, so the socket never waits for it:
`folders.pick` gives a token, `folders.picked` what came of it. With no dialog on the machine the path is typed, as
before. The same as Orkline's Wiki folders (orkcraft/gui/folders.py), for a project's folder; desktop only (a phone
never opens a dialog on the computer: gui/board_host.py `BoardPhone`).

    attach(window)                         # the app's window: its own folder dialog
    token = start("~/code")                # the dialog opened on a thread
    result(token)                          # {"state": "open" | "done" | "none" | "error", "path", "why"}
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Callable

PROMPT = "Choose a project's folder"
DIALOG_TIMEOUT_S = 15 * 60
KEEP = 32                                              # dialogs whose answer is kept until it is read

_window = None                                         # the app's pywebview window
_picks: dict[str, dict] = {}                           # token → {state, path, why}
_lock = threading.Lock()


class Unavailable(RuntimeError):
    """No folder dialog on this machine: the path is typed."""


def attach(window: Any) -> None:
    """The app's window: its own folder dialog."""
    global _window
    _window = window


def command(begin: str = "", platform: str = sys.platform,
            which: Callable[[str], str | None] = shutil.which) -> list[str] | None:
    """The system's folder dialog as a command (None when this machine has none)."""
    begin = begin or str(Path.home())
    if platform == "darwin" and which("osascript"):
        where = begin.replace("\\", "\\\\").replace('"', '\\"')
        return ["osascript", "-e", f'POSIX path of (choose folder with prompt "{PROMPT}" '
                                   f'default location (POSIX file "{where}"))']
    if platform.startswith("win"):
        ps = which("powershell") or which("pwsh")
        if ps:
            return [ps, "-NoProfile", "-STA", "-Command",
                    "Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                    f"$d.Description = '{PROMPT}'; if ($d.ShowDialog() -eq 'OK') {{ $d.SelectedPath }}"]
        return None
    if which("zenity"):
        return ["zenity", "--file-selection", "--directory", f"--title={PROMPT}", f"--filename={begin.rstrip('/')}/"]
    if which("kdialog"):
        return ["kdialog", "--getexistingdirectory", begin, "--title", PROMPT]
    return None


def native(begin: str = "") -> str | None:
    """Ask with the window's dialog, else the system's: the folder chosen, None when it was cancelled; Unavailable when
    there is none."""
    begin = str(Path(begin).expanduser()) if begin.strip() and Path(begin).expanduser().is_dir() else str(Path.home())
    window = _window
    if window is not None:
        import webview
        kind = getattr(getattr(webview, "FileDialog", None), "FOLDER", None) or getattr(webview, "FOLDER_DIALOG")
        got = window.create_file_dialog(kind, directory=begin)
        if not got:
            return None
        return str(got[0] if isinstance(got, (list, tuple)) else got)
    cmd = command(begin)
    if cmd is None:
        raise Unavailable("No folder dialog on this computer: type the folder's path.")
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=DIALOG_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Unavailable(str(e)) from None
    path = done.stdout.strip()
    return (path.rstrip("/") or "/") if done.returncode == 0 and path else None


def start(begin: str = "", ask: Callable[[str], str | None] | None = None) -> str:
    """Open the dialog on a thread of its own: a token for `result`."""
    token = uuid.uuid4().hex[:12]
    ask = ask or native
    with _lock:
        while len(_picks) >= KEEP:                     # answers never read: the oldest goes
            _picks.pop(next(iter(_picks)))
        _picks[token] = {"state": "open", "path": "", "why": ""}

    def run() -> None:
        try:
            path = ask(begin)
            got = {"state": "done", "path": path, "why": ""} if path else {"state": "none", "path": "", "why": ""}
        except Unavailable as e:
            got = {"state": "error", "path": "", "why": str(e)}
        except Exception as e:                         # a dialog must never take the server down
            got = {"state": "error", "path": "", "why": f"The folder dialog failed: {type(e).__name__}: {e}"[:200]}
        with _lock:
            if token in _picks:
                _picks[token] = got

    threading.Thread(target=run, daemon=True, name="folder-dialog").start()
    return token


def result(token: str) -> dict:
    """What came of a dialog: {state: open | done | none | error, path, why} (`why` an error's words, never the reply's
    `error`, which the page reads as the command's own); forgotten once it is read."""
    with _lock:
        got = dict(_picks.get(token) or {"state": "error", "path": "", "why": "No such dialog"})
        if got["state"] != "open":
            _picks.pop(token, None)
    return got


def commands() -> dict[str, Callable[[dict], Any]]:
    """`folders.pick` `{"start"?}` → `{"token"}`; `folders.picked` `{"token"}` → `result`."""
    def pick(args: dict) -> dict:
        begin = args.get("start")
        return {"token": start(begin if isinstance(begin, str) else "")}

    def picked(args: dict) -> dict:
        token = args.get("token")
        return result(token if isinstance(token, str) else "")

    return {"folders.pick": pick, "folders.picked": picked}
