"""When an AI tool fails: what kind of failure it is, in one plain line, and what the person can do.

    raise ToolError("claude", why, code=1)    # a run of a tool failed (str(): "claude exited with 1: …")
    tool_errors.classify(text, code)          # "missing" | "login" | "limit" | "network" | "other"
    tool_errors.plainly(err)                  # the failure in one line for a page: what happened, its words, what to do
    tool_errors.claude_sign_in(said)          # Claude Code's refused sign-in: a key set here, or another config folder
    tool_errors.report(err, enabled, main)    # what the failure says on the bus (core: Town.tool_failed)

A face shows the report as a toast: "<Tool> hit an error", the line, and Switch to another tool that is
installed, Retry, Details (the tool's own words, kept whole to copy). A service never shows it itself.
"""
from __future__ import annotations

import os
import re
import shutil
import threading
from typing import Callable, Iterable

from orkboard.realm import harnesses

MISSING, LOGIN, LIMIT, NETWORK, OTHER = "missing", "login", "limit", "network", "other"
KINDS = (MISSING, LOGIN, LIMIT, NETWORK, OTHER)
DETAIL_KEEP = 4000                   # the tool's own words kept for Details
PLAIN_CHARS = 600                    # `plainly`'s line: what happened, the tool's words, the step

# The first kind whose words are in the tool's output (lower case). Order matters: a 401 that says
# "connection" is a login.
_WORDS: tuple[tuple[str, re.Pattern], ...] = (
    (MISSING, re.compile(r"command not found|not found \(|cli not found|^\S+ not found$|no such file or directory"
                         r"|is not recognized as an internal|enoent")),
    (LOGIN, re.compile(r"not logged in|log ?in again|please (run )?/?log ?in|/login|logged out|unauthori[sz]ed"
                       r"|\b401\b|authenticat|invalid (x-)?api[ _-]?key|api key (is )?(missing|invalid|not set)"
                       r"|(token|session|credentials?|login) (has )?expired|expired (token|session|credentials?)"
                       r"|no credentials|oauth|sign ?in")),
    (LIMIT, re.compile(r"\b429\b|\b529\b|rate[ _-]?limit|too many requests|overloaded|usage limit|limit reached"
                       r"|hit your limit|quota|resource[ _-]exhausted|capacity|credit balance")),
    (NETWORK, re.compile(r"econnrefused|econnreset|enotfound|etimedout|eai_again|getaddrinfo|network"
                         r"|connection (refused|reset|error|timed out)|could not connect|unable to connect"
                         r"|failed to connect|could not resolve|name resolution|socket hang up|fetch failed|offline")),
)

# What happened, in one line; {tool} is its title.
LINES = {
    MISSING: "{tool} is not installed, or Orkline cannot find it on this computer.",
    LOGIN: "{tool} is not signed in, or its sign-in has expired.",
    LIMIT: "{tool} hit a usage limit or its service is overloaded.",
    NETWORK: "{tool} could not reach its service. Check the internet connection.",
    OTHER: "{tool} stopped with an error before it finished.",
}


class ToolError(RuntimeError):
    """A run of an AI tool failed. Its str() is the line logs always had ("codex exited with 1: …");
    `detail` keeps the tool's own words whole, `kind` says what kind of failure it is."""

    def __init__(self, harness: str, detail: str, code: int | None = None, kind: str = "") -> None:
        self.harness, self.code = harness, code
        self.detail = (detail or "").strip()[:DETAIL_KEEP]
        self.kind = kind if kind in KINDS else classify(self.detail, code)
        if code is None:
            said = self.detail[:300]
        else:
            said = f"{harness} exited with {code}: {self.detail[:300]}"
        super().__init__(said)
        _LAST.error = self


_LAST = threading.local()       # the newest ToolError made on each thread (`taken`)


def taken() -> ToolError | None:
    """The newest AI tool failure on this thread since the last call, even one a caller turned into an
    error string of its result (a face's job reads it to offer Switch and Retry)."""
    error = getattr(_LAST, "error", None)
    _LAST.error = None
    return error


def classify(text: str, code: int | None = None) -> str:
    """The kind of a tool's failure from its words (and exit code: 127 is a command not found)."""
    low = (text or "").lower()
    if code == 127:
        return MISSING
    for kind, words in _WORDS:
        if words.search(low):
            return kind
    return OTHER


def missing(harness: str, command: str) -> ToolError:
    """The tool's command is not on this computer."""
    return ToolError(harness, f"{command} not found", kind=MISSING)


def installed(harness_id: str, which: Callable[[str], str | None] | None = None) -> bool:
    h = harnesses.get(harness_id)
    return bool(h and (which or shutil.which)(h.bin))


def others(failed: str, enabled: Iterable[str], which: Callable[[str], str | None] | None = None,
           broken: Iterable[str] = ()) -> list[dict]:
    """The tools to switch to: installed here, not the one that failed nor one that failed to start or
    sign in (`broken`), nor an experimental one that is off (agy: on only past its warning, in Settings); the
    ones turned on in Settings first, in the registry's order."""
    on, broken, which = set(enabled), set(broken) | {failed}, which or shutil.which
    found = [h for h in harnesses.REGISTRY.values()
             if h.id not in broken and (h.id in on or not h.experimental) and which(h.bin)]
    found.sort(key=lambda h: h.id not in on)
    return [{"id": h.id, "title": h.title, "mark": h.mark, "on": h.id in on} for h in found]


def install_hint(failed: str, which: Callable[[str], str | None] | None = None) -> str:
    """How to get a second tool to switch to, when there is none."""
    which = which or shutil.which
    for h in harnesses.REGISTRY.values():
        if h.id != failed and not which(h.bin):
            return f"No other AI tool is installed. To have one to switch to, install {h.title}: {h.install}"
    return "No other AI tool is installed."


def what_to_do(err: ToolError) -> str:
    """The step the person can take for this kind, beyond Switch and Retry ("" when none)."""
    h = harnesses.get(err.harness)
    if h is None:
        return ""
    if err.kind == MISSING:
        return f"Install it: {h.install}"
    if err.kind == LOGIN:
        return claude_sign_in(err.detail) if err.harness == "claude" else f"Sign in again in a terminal: {h.login}"
    if err.kind == LIMIT:
        return "Wait a few minutes, or switch to another tool."
    return ""


def plainly(err: ToolError, cap: int = PLAIN_CHARS) -> str:
    """The failure in one plain line for a page: what happened, the tool's own words, and the step to take ("Claude Code
    is not signed in, or its sign-in has expired. Claude Code said: … If claude works in your terminal, …"); the
    tool's words are cut first when the line is longer than `cap`."""
    title = harnesses.title(err.harness)
    line, step = LINES[err.kind].format(tool=title), what_to_do(err)
    room = cap - len(line) - len(step) - len(title) - 9
    words = err.detail if len(err.detail) <= room else err.detail[:max(0, room - 1)].rstrip() + "…"
    said = f"{title} said: {words}" if err.detail and room > 20 else ""
    return " ".join(x for x in (line, said, step) if x)[:cap]


def claude_sign_in(said: str, env: dict | None = None) -> str:
    """What to do when Claude Code refused its sign-in, by its words (code.claude.com/docs/en/errors) and the
    environment this process gives it: `claude -p` takes ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY before a
    subscription's sign-in whenever one is set, and its sign-in is kept per config folder (CLAUDE_CONFIG_DIR), so a
    `claude` that works in a terminal may find none here."""
    env = dict(os.environ) if env is None else env
    low = (said or "").lower()
    key = next((k for k in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY") if env.get(k)), "")
    if key and ("api key" in low or "invalid" in low or "401" in low):
        return f"{key} is set where Orkline runs, and claude -p uses it before your sign-in: remove it or fix the key."
    if "not logged in" in low or "no valid credential" in low:
        return ("If claude works in your terminal, Orkline runs it with another config folder (CLAUDE_CONFIG_DIR) or "
                "another claude: Save logs shows which. Else sign in in a terminal: claude, then /login.")
    return "Sign in again in a terminal: claude, then /login."


def report(err: ToolError, enabled: Iterable[str], main: str, where: str = "",
           which: Callable[[str], str | None] | None = None, broken: Iterable[str] = ()) -> dict:
    """What a tool's failure says on the bus (`bus.TOOL_ERROR`). `main`: the machine's main tool —
    Switch changes it, so it is offered only when the tool that failed was the main one."""
    title = harnesses.title(err.harness)
    is_main = err.harness == main
    switch = others(err.harness, enabled, which, broken) if is_main else []
    if not is_main:
        hint = f"This step is set to use {title}. Choose another tool in its building's settings."
    elif not switch:
        hint = install_hint(err.harness, which)
    else:
        hint = ""
    h = harnesses.get(err.harness)
    return {"harness": err.harness, "tool": title, "mark": h.mark if h else "", "kind": err.kind, "where": where,
            "title": f"{title} hit an error", "line": LINES[err.kind].format(tool=title),
            "action": what_to_do(err), "detail": err.detail or str(err), "code": err.code,
            "switch": switch, "hint": hint, "main": is_main}
