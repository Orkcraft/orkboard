"""How orks call Claude Code: its argv builders and flags (split from harnesses.py).

Read-only and web tool lists, the one-shot, reading, working and tool-limited calls, `--add-dir` for read folders,
and `_claude_run`, the run flags the installed CLI lists (effort, budget, no session persistence; `cli_has`, which
reads its `--help`, is in realm/harness_tools.py with the other process this package starts). The
registry that wires them to a `Harness` stays in realm/harnesses.py, which re-exports every name here.
"""
from __future__ import annotations

import json
from pathlib import Path

from orkboard.realm.harness_tools import EFFORTS, _HELP, _model, cli_has, effort_supported, json_lines  # noqa: F401


# Claude Code ---------------------------------------------------------------------------------------

CLAUDE_READ_ONLY = ["--allowedTools", "Read,Grep,Glob",
                    "--disallowedTools", "Bash,Edit,Write,MultiEdit,NotebookEdit,WebFetch,WebSearch"]
CLAUDE_READ_WEB = ["--allowedTools", "Read,Grep,Glob,WebSearch,WebFetch",
                   "--disallowedTools", "Bash,Edit,Write,MultiEdit,NotebookEdit"]


def _claude_mcp() -> list[str]:
    """A Test bench run's MCP servers only (realm/cassette.py): its configuration, and none of the person's own."""
    from orkboard.env import getenv
    path = getenv("MCP_CONFIG")
    return ["--mcp-config", path, "--strict-mcp-config"] if path else []


def _claude_ask(h, prompt, folder, model):
    return [h.bin, "-p", prompt, "--output-format", "json", *_model("--model", model), *_claude_mcp()]


def _claude_read(h, prompt, workdir, model, web):
    return [h.bin, "-p", prompt, "--output-format", "json", *(CLAUDE_READ_WEB if web else CLAUDE_READ_ONLY),
            *_model("--model", model), *_claude_mcp()]


# Every built-in tool a carrier must not have; MCP tools not in --allowedTools are refused in -p (their schemas are
# still shown: an operation's prepare writes its action's arguments from one, spec 38 §4). None allowed: no list.
CLAUDE_NO_TOOLS = "Bash,Edit,Write,MultiEdit,NotebookEdit,WebFetch,WebSearch,Read,Grep,Glob,Task,TodoWrite"


def _claude_call(h, prompt, workdir, model, allow):
    return [h.bin, "-p", prompt, "--output-format", "stream-json", "--verbose",
            *(["--allowedTools", ",".join(allow)] if allow else []), "--disallowedTools", CLAUDE_NO_TOOLS, *_model("--model", model),
            *_claude_mcp()]


def claude_error(stdout: str) -> str:
    """Why a run of Claude Code failed, from its result envelope (`--output-format json`, or stream-json's last
    `result` event): its own words ("Not logged in · Please run /login") when it is an error, else "". The envelope
    puts `is_error` and `result` after `usage`, so a line cut from the raw JSON never says why."""
    try:
        events = [json.loads(stdout.strip())]
    except ValueError:
        events = json_lines(stdout)
    for event in reversed(events):
        if not isinstance(event, dict) or event.get("type", "result") != "result":
            continue
        subtype = str(event.get("subtype") or "")
        if event.get("is_error") is True or subtype.startswith("error"):
            for key in ("result", "error"):
                if isinstance(event.get(key), str) and event[key].strip():
                    return event[key].strip()
            return subtype or str(event.get("terminal_reason") or "") or "error"
    return ""


def _claude_read_dirs(dirs: list[str]) -> list[str]:
    """`--add-dir` for each folder, and no edit there (`//` makes a rule's path absolute)."""
    out = [a for d in dirs for a in ("--add-dir", d)]
    rules = [f"{tool}(/{Path(d).as_posix()}/**)" for d in dirs if Path(d).is_absolute()
             for tool in ("Edit", "Write", "MultiEdit", "NotebookEdit")]
    return out + (["--disallowedTools", ",".join(rules)] if rules else [])


def _claude_work(h, prompt, workdir, model, resume):
    return [h.bin, "-p", prompt, "--output-format", "json", "--permission-mode", "acceptEdits",
            *_model("--model", model), *(["--resume", resume] if resume else []), *_claude_mcp()]


def _claude_run(h, model, effort="", budget=None, one_shot=False):
    """`--effort <level>` (a known level, never on the laborer tier), `--max-budget-usd <x>`, `--no-session-persistence`:
    each only when the installed CLI lists it."""
    from orkboard.realm.harnesses import tier_of_model
    out = []
    if effort in EFFORTS and (h.tier_for(model) or tier_of_model(model)) != "laborer" and cli_has(h, "--effort"):
        out += ["--effort", effort]
    if isinstance(budget, (int, float)) and budget > 0 and cli_has(h, "--max-budget-usd"):
        out += ["--max-budget-usd", f"{budget:.2f}"]
    if one_shot and cli_has(h, "--no-session-persistence"):
        out.append("--no-session-persistence")
    return out
