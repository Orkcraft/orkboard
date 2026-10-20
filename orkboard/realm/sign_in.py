"""A tool's own sign-in, started and watched (docs/specs/45-sign-in.md §2): no face, no bus.

    run = sign_in.start("claude", os.environ, state_dir)    # Claude Code's `auth login`, in the browser it opens itself
    run.poll()          # None while it goes on, else an Outcome: done | failed (why) | none (no terminal: command)
    run.told()          # a person's Done (a tool that cannot be told it is signed in): the answer, then the Outcome
    run.cancel()        # the process stops (a terminal's window stays the person's)

**By browser** (Claude Code, Codex): `[bin, *sign_in]` with stdin closed, in the home folder, with Orkline's own
environment, so the sign-in lands where Orkline's runs look for it (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`…). Its words go to
`<state>/sign-in/<tool>.log`, every URL cut to its host: a sign-in link carries a one-time state, which is not kept.
**In a terminal** (pi, and the tools not checked yet): a script `<tool>.command` opened in a terminal window; the window
is the person's and is never closed; the run ends when `tools.signed_in` says so.

Nothing here reads, keeps or logs a code, a token or a password: the tool keeps its sign-in where it always does.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from orkboard import tools
from orkboard.realm import halt, harnesses, tool_errors, tool_run

WAIT_S = 600                        # a sign-in not done by then is stopped (`timeout`)
POLL_S = 5                          # a terminal sign-in is asked this often whether the tool is signed in
CHECK_PROMPT = "Reply with the one word: ok"   # a short real request, on the tool's cheapest tier (onboarding's Check)
PASTE = ("paste code", "device code")           # a browser that did not open: the tool asks for a code to paste
CODEX_PORT = 1455                   # Codex's sign-in listens here: one Codex sign-in at a time on the computer
KEEP_LINES = 200
# The variables of a tool's own config folder, which its sign-in must see as its runs do (the script exports them).
CONFIG_VARS = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "PI_CODING_AGENT_DIR", "HERMES_HOME")
LINUX_TERMINALS = (("x-terminal-emulator", "-e"), ("gnome-terminal", "--"), ("konsole", "-e"),
                   ("xfce4-terminal", "-x"), ("xterm", "-e"))
_URL = re.compile(r"https?://[^\s'\"<>)\]]+")


class SignInError(Exception):
    """A sign-in that cannot start; its text is shown to the person."""


@dataclass(frozen=True)
class Outcome:
    state: str                  # "done" | "failed" | "none"
    why: str = ""               # failed: timeout, cancelled, refused, no_browser, the check's words, the tool's last line
    command: str = ""           # none: the words to type in a terminal


def cut_urls(text: str) -> str:
    """`text` with every URL cut to its scheme and host."""
    def host(m: re.Match) -> str:
        u = urlsplit(m.group(0))
        return f"{u.scheme}://{u.netloc}" if u.netloc else "(link)"
    return _URL.sub(host, text)


def port_busy(port: int = CODEX_PORT) -> bool:
    """Whether something already listens on this port of the computer (another Codex sign-in)."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def tool_env(harness_id: str, env: dict, home: Path) -> dict[str, str]:
    """The environment of a sign-in: a run of the tool's own (the same PATH and config folders), never a project's."""
    h = harnesses.need(harness_id)
    return {**env, **h.env("ask", str(home))}


class Run:
    """One tool's sign-in, going on. Built by `start`."""

    def __init__(self, harness_id: str, by: str, *, clock: Callable[[], float], signed_in: Callable[..., bool | None],
                 ask: Callable[..., object], env: dict, proc: subprocess.Popen | None = None,
                 log: Path | None = None) -> None:
        self.harness, self.by, self.env = harness_id, by, env
        self.proc, self.log = proc, log
        self.outcome: Outcome | None = None
        self.lines: list[str] = []
        self._clock, self._signed_in, self._ask = clock, signed_in, ask
        self._began = clock()
        self._next = self._began              # a terminal's next ask whether the tool is signed in
        self._lock = threading.Lock()
        self._reader: threading.Thread | None = None
        if proc is not None:
            halt.started(proc, harness_id)
            self._reader = threading.Thread(target=self._read, daemon=True, name=f"sign-in-{harness_id}")
            self._reader.start()

    # -- the tool's words ---------------------------------------------------------------------------

    def _read(self) -> None:
        """Its output, line by line, to the log with every URL cut to its host."""
        try:
            with open(self.log, "a", encoding="utf-8") as f:
                for raw in self.proc.stdout or ():
                    line = cut_urls(raw.rstrip("\n"))
                    with self._lock:
                        self.lines = [*self.lines, line][-KEEP_LINES:]
                    f.write(line + "\n")
                    f.flush()
        except (OSError, ValueError):
            pass

    def _said(self) -> list[str]:
        with self._lock:
            return list(self.lines)

    # -- going on -----------------------------------------------------------------------------------

    def poll(self) -> Outcome | None:
        """None while it goes on, else how it ended (the same afterwards)."""
        if self.outcome is not None:
            return self.outcome
        if self.proc is not None:
            return self._poll_browser()
        return self._poll_terminal()

    def _poll_browser(self) -> Outcome | None:
        code = self.proc.poll()
        said = " ".join(self._said()).lower()
        if code is None and any(w in said for w in PASTE):
            return self._stop(Outcome("failed", "no_browser"))
        if code is None:
            if self._clock() - self._began > WAIT_S:
                return self._stop(Outcome("failed", "timeout"))
            return None
        if self._reader is not None:
            self._reader.join(2)
        if self._killed():
            return self._end(Outcome("failed", "cancelled"))
        if any(w in " ".join(self._said()).lower() for w in PASTE):
            return self._end(Outcome("failed", "no_browser"))
        if code == 0:
            return self._end(self._tell())
        last = next((ln.strip() for ln in reversed(self._said()) if ln.strip()), "")
        return self._end(Outcome("failed", last[:200] or f"exit {code}"))

    def _poll_terminal(self) -> Outcome | None:
        now = self._clock()
        if now - self._began > WAIT_S:
            return self._end(Outcome("failed", "timeout"))
        if now < self._next:
            return None
        self._next = now + POLL_S
        if self._signed_in(self.harness, self.env) is True:
            return self._end(Outcome("done"))
        return None

    def told(self) -> Outcome:
        """The person says it is done (*Done*): ask the tool, else check it with a short real request."""
        if self.outcome is None:
            self._end(self._tell())
        return self.outcome

    def _tell(self) -> Outcome:
        """The sign-in ended: `signed_in` True is done, False is refused, None is the Check (a short ask)."""
        got = self._signed_in(self.harness, self.env)
        if got is True:
            return Outcome("done")
        if got is False:
            return Outcome("failed", "refused")
        try:
            self._ask(self.harness, CHECK_PROMPT, "laborer")
        except Exception as e:                       # a timeout or Stop all is a failure like any other
            err = e if isinstance(e, tool_errors.ToolError) else tool_errors.ToolError(self.harness, str(e))
            return Outcome("failed", tool_errors.plainly(err))
        return Outcome("done")

    def cancel(self) -> Outcome:
        """Stops the process (a terminal's window stays the person's)."""
        if self.outcome is not None:
            return self.outcome
        return self._stop(Outcome("failed", "cancelled"))

    # -- ending -------------------------------------------------------------------------------------

    def _stop(self, outcome: Outcome) -> Outcome:
        proc = self.proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except OSError:
                pass
        return self._end(outcome)

    def _killed(self) -> bool:
        """Whether Stop all killed the process (then the sign-in is cancelled, not refused)."""
        try:
            halt.ended(self.proc)
        except halt.Halted:
            return True
        return False

    def _end(self, outcome: Outcome) -> Outcome:
        if self.proc is not None:
            try:
                halt.ended(self.proc)
            except halt.Halted:
                outcome = Outcome("failed", "cancelled")
        self.outcome = outcome
        return outcome


def _script(harness: harnesses.Harness, env: dict, platform: str, path: str) -> str:
    """The text of a terminal sign-in's script: the home folder, the environment's PATH and the tool's config folders,
    then the tool's own sign-in."""
    argv = [path, *harness.sign_in]
    kept = {k: env[k] for k in ("PATH", *CONFIG_VARS) if env.get(k)}
    if platform == "win32":
        lines = ["@echo off", 'cd /d "%USERPROFILE%"', *[f'set "{k}={v}"' for k, v in kept.items()],
                 subprocess.list2cmdline(argv)]
        return "\r\n".join(lines) + "\r\n"
    lines = ["#!/bin/sh", 'cd ~ || exit 1', *[f"export {k}={shlex.quote(v)}" for k, v in kept.items()],
             "exec " + " ".join(shlex.quote(a) for a in argv)]
    return "\n".join(lines) + "\n"


def opener(platform: str, script: Path, which: Callable[[str], str | None]) -> list[str] | None:
    """The argv that opens `script` in a terminal window; None when this computer has none."""
    if platform == "darwin":
        return ["open", "-a", "Terminal", str(script)]
    if platform == "win32":
        return ["cmd", "/c", "start", "", "cmd", "/k", str(script)]
    for name, flag in LINUX_TERMINALS:
        if which(name):
            return [name, flag, str(script)]
    return None


def start(harness_id: str, env: dict, state_dir: Path, platform: str = sys.platform,
          which: Callable[[str], str | None] = shutil.which, popen: Callable = subprocess.Popen, *,
          clock: Callable[[], float] = time.monotonic, signed_in: Callable[..., bool | None] = tools.signed_in,
          ask: Callable[..., object] | None = None, home: Path | None = None, by: str | None = None) -> Run:
    """The tool's own sign-in started (`by` "terminal": in a terminal window, whatever the tool's own way is). Raises SignInError for a tool that is unknown or not found on this computer."""
    h = harnesses.get(harness_id)
    if h is None:
        raise SignInError(f"{harness_id} is not one of the AI tools")
    path = which(h.bin)
    if not path:
        raise SignInError(f"{h.title} is not found on this computer")
    home = Path.home() if home is None else Path(home)
    run_env = tool_env(harness_id, env, home)
    folder = Path(state_dir) / "sign-in"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    ask = ask or tool_run.ask
    common = dict(clock=clock, signed_in=signed_in, ask=ask, env=run_env)
    if (by or h.sign_in_by) == "browser":
        log = folder / f"{h.id}.log"
        log.write_text("", encoding="utf-8")
        log.chmod(0o600)
        try:
            proc = popen([path, *h.sign_in], cwd=str(home), env=run_env, stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        except OSError as e:
            raise SignInError(f"{h.title}'s sign-in could not start: {e}") from None
        return Run(h.id, "browser", proc=proc, log=log, **common)
    script = folder / (f"{h.id}.cmd" if platform == "win32" else f"{h.id}.command")
    script.write_text(_script(h, run_env, platform, path), encoding="utf-8", newline="")
    script.chmod(0o700)
    run = Run(h.id, "terminal", **common)
    argv = opener(platform, script, which)
    if argv is not None:
        try:
            popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                  start_new_session=True)
        except OSError:
            argv = None
    if argv is None:
        run.outcome = Outcome("none", command=h.login)
    return run
