"""How orks call the AI tools other than Claude Code: agy, Codex, Hermes, pi and Cursor (split from harnesses.py).

Each tool has its argv builder (`_agy`, `codex_exec`, `_hermes`, `_pi`, `_cursor`) and, where it prints JSONL, its
result and error readers (`codex_result`, `hermes_result`, `pi_result`, `cursor_result`, …). The registry that
wires them to a `Harness` stays in realm/harnesses.py, which re-exports every name here; Claude Code's builders
are in realm/harness_claude.py. Nothing here imports the registry.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

from orkboard.sources import pricing


EFFORTS = ("low", "medium", "high", "xhigh", "max")      # the CLI's levels
_HELP: dict[str, str] = {}                                # the CLI's path → its `--help`


def cli_has(h, flag: str) -> bool:
    """Whether the installed CLI lists `flag` in its `--help`: read once per CLI, then cached. It runs in an empty
    folder with only PATH and HOME, so nothing of the town reaches it."""
    path = shutil.which(h.bin) or h.bin
    if path not in _HELP:
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "USERPROFILE", "SYSTEMROOT")}
        try:
            with tempfile.TemporaryDirectory() as empty:
                proc = subprocess.run([path, "--help"], cwd=empty, env=env, capture_output=True, text=True, timeout=15)
            _HELP[path] = (proc.stdout or "") + (proc.stderr or "")
        except (OSError, subprocess.SubprocessError, ValueError):
            _HELP[path] = ""
    return flag in _HELP[path]


def effort_supported(h) -> bool:
    return cli_has(h, "--effort")


def _model(flag: str, model: str) -> list[str]:
    return [flag, model] if model else []


def json_lines(stdout: str) -> list[dict]:
    events = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _plain_tokens(usage) -> int | None:
    vals = [usage[k] for k in ("input_tokens", "output_tokens") if isinstance(usage.get(k), int)] \
        if isinstance(usage, dict) else []
    return sum(vals) if vals else None



CODEX_USAGE_KEYS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens",
                    "reasoning_output_tokens")


def codex_usage_since(total: dict, before: dict | None) -> dict:
    """A thread's running usage less what it had used before (key by key, never below 0)."""
    before = before if isinstance(before, dict) else {}
    return {k: max(int(total.get(k) or 0) - int(before.get(k) or 0), 0) for k in CODEX_USAGE_KEYS}


def codex_config_model(env: dict | None = None) -> str:
    """The `model` at the top of `$CODEX_HOME/config.toml` (~/.codex): what `codex exec` runs on when
    orkcraft passes no `--model`; "" when it names none or cannot be read."""
    env = os.environ if env is None else env
    home = Path(env["CODEX_HOME"]) if env.get("CODEX_HOME") else Path.home() / ".codex"
    try:
        model = tomllib.loads((home / "config.toml").read_text(encoding="utf-8")).get("model")
    except (OSError, ValueError):
        return ""
    return model.strip() if isinstance(model, str) else ""


def codex_result(stdout: str, before: int | dict = 0, model: str = "") -> tuple[str, float | None, int | None, str]:
    """(text, cost, tokens, session) of `codex exec --json`: the last agent message, the tokens of this
    run (cached input is part of the input) and the thread id. Each `turn.completed.usage` is the
    thread's running total (openai/codex `usage_from_last_total`), so the last one counts, less
    `before`: what the thread had already used when this run resumed it — its token count, or its
    usage block (`roads.codex_thread_usage`), which also lets the run be priced.

    Codex prints no price: the cost comes from `model` (the `--model` orkcraft passed, else the one in
    Codex's config.toml) and `pricing.OPENAI_PRICES` — an API-equivalent estimate for a ChatGPT
    login. An unknown model, or a resumed run whose earlier usage is not known, is None, never $0."""
    text, usage, session = "", None, ""
    for event in json_lines(stdout):
        kind, item = event.get("type"), event.get("item")
        if kind == "thread.started":
            session = str(event.get("thread_id") or "")
        elif kind == "item.completed" and isinstance(item, dict) and item.get("type") == "agent_message":
            text = str(item.get("text") or "")
        elif kind == "turn.completed" and _plain_tokens(event.get("usage")) is not None:
            usage = event["usage"]
    if usage is None:
        return text.strip(), None, None, session
    before_tokens = (_plain_tokens(before) or 0) if isinstance(before, dict) else int(before or 0)
    tokens = max(_plain_tokens(usage) - before_tokens, 0)
    cost = None
    if isinstance(before, dict) or not before:
        cost = pricing.codex_usage_cost(model or codex_config_model(), codex_usage_since(usage, before or None))
    return text.strip(), cost, tokens, session


def codex_error(stdout: str) -> str:
    """Why a `codex exec --json` run failed, from its events ("" when they do not say)."""
    for event in reversed(json_lines(stdout)):
        error = event.get("error")
        if event.get("type") == "turn.failed" and isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if event.get("type") == "error" and event.get("message"):
            return str(event["message"])
    return ""


# agy (Antigravity) -------------------------------------------------------------------------------

def _agy(h, prompt, workdir, model):
    return [h.bin, "--print", prompt, *_model("--model", model), "--mode", "accept-edits", "--sandbox",
            "--add-dir", workdir, "--output-format", "json"]


# Codex -------------------------------------------------------------------------------------------

CODEX_WEB = {False: 'web_search="disabled"', True: 'web_search="live"'}   # Codex searches by default


def codex_exec(h, sandbox: str, model: str = "", web: bool = False, resume: str = "") -> list[str]:
    """`codex exec` with its prompt on stdin (`-`) and JSONL events on stdout, in the folder it is
    started in. The sandbox goes in as config: `exec resume` takes no `--sandbox`."""
    return [h.bin, "exec", *(["resume", resume] if resume else []), "-", "--json", "--skip-git-repo-check",
            "-c", f'sandbox_mode="{sandbox}"', "-c", CODEX_WEB[web], *_model("--model", model)]


# Hermes Agent (Nous Research) ---------------------------------------------------------------------
# `hermes chat -q … --oneshot --format stream-json`: JSONL, the last `result` line carries the text,
# the tokens and the session id; no price (only `-z --usage-file` prices, and `-z` approves every
# command, so it is never used). Its tools come as toolsets; `file` can write, so a reading agent gets
# HERMES_WRITE_SAFE_ROOT on a path nothing can be written under. The prompt comes on stdin. Dangerous commands are refused in a
# one-shot run (`approvals.single_query_mode: deny`, its default). docs/design/harnesses.md

def hermes_result(stdout: str, before: int = 0) -> tuple[str, float | None, int | None, str]:
    text, tokens, session, parts = "", None, "", []
    for event in json_lines(stdout):
        kind = event.get("type")
        if kind == "system" and event.get("session_id"):
            session = str(event["session_id"])
        elif kind == "text" and isinstance(event.get("text"), str):
            parts.append(event["text"])
        elif kind == "result":
            session = str(event.get("session_id") or session)
            text = str(event.get("text") or "")
            t = event.get("tokens")
            if isinstance(t, dict) and isinstance(t.get("total"), int):
                tokens = t["total"]
    return (text or "".join(parts)).strip(), None, tokens, session


def hermes_error(stdout: str) -> str:
    for event in reversed(json_lines(stdout)):
        if event.get("type") == "result" and event.get("error"):
            return str(event["error"])
    return ""


HERMES_READ = "file,search"
HERMES_WORK = "file,terminal,search"
NOWHERE = "/dev/null/orkcraft"       # a write root no file can be made under


def _hermes(h, prompt, model, toolsets, resume=""):
    return [h.bin, "chat", "--query-file", "-", "--oneshot", "--format", "stream-json", "--toolsets", toolsets,
            *_model("--model", model), *(["--resume", resume] if resume else [])]


def _hermes_env(h, mode, workdir):
    # hooks run headless (the Warder, hooks/install.py) and file tools write only where they may
    return {"HERMES_ACCEPT_HOOKS": "1", "HERMES_WRITE_SAFE_ROOT": workdir if mode == "work" and workdir else NOWHERE}


# pi (earendil-works/pi, formerly badlogic/pi-mono) -------------------------------------------------
# `pi --mode json … -- <prompt>`: JSONL; the first line is the session header (its id), each assistant
# `message_end` carries the text and `usage` with `cost.total` in USD. pi has no approvals and no
# sandbox: what it may do is the tools it is given (`--tools`). Project extensions wait for trust
# headless, so only orkcraft's own (`-e`, hooks/install.py) run.

def pi_result(stdout: str, before: int = 0) -> tuple[str, float | None, int | None, str]:
    text, cost, tokens, session = "", None, None, ""
    for event in json_lines(stdout):
        kind = event.get("type")
        if kind == "session" and event.get("id"):
            session = session or str(event["id"])
        msg = event.get("message") if kind == "message_end" else None
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, list):
            said = "".join(str(c.get("text") or "") for c in content if isinstance(c, dict) and c.get("type") == "text")
            text = said or text
        usage = msg.get("usage")
        if isinstance(usage, dict):
            if isinstance(usage.get("totalTokens"), int):
                tokens = (tokens or 0) + usage["totalTokens"]
            total = (usage.get("cost") or {}).get("total") if isinstance(usage.get("cost"), dict) else None
            if isinstance(total, (int, float)):
                cost = (cost or 0.0) + float(total)
    return text.strip(), cost, tokens, session


def pi_error(stdout: str) -> str:
    for event in reversed(json_lines(stdout)):
        msg = event.get("message")
        if isinstance(msg, dict) and msg.get("stopReason") in ("error", "aborted"):
            return str(msg.get("errorMessage") or msg.get("stopReason"))
    return ""


PI_READ = "read,grep,find,ls"
PI_WORK = "read,grep,find,ls,edit,write,bash"


def pi_guard() -> list[str]:
    """`-e <orkcraft's extension>`: the Warder and the session log in every pi orkcraft starts."""
    from orkboard.hooks import pi_extension
    path = pi_extension.write()
    return ["-e", str(path)] if path else []


def _pi(h, prompt, model, tools, session="", keep=False):
    return [h.bin, "--mode", "json", *pi_guard(), *(["--tools", tools] if tools else ["--no-tools"]),
            *([] if keep or session else ["--no-session"]), *(["--session", session] if session else []),
            *_model("--model", model), "--", prompt]


# Cursor CLI (`cursor-agent`) -----------------------------------------------------------------------
# `cursor-agent -p --output-format stream-json --trust`: JSONL; the `result` line carries the text,
# the session (chat) id and `usage` in camelCase; no price (the plan pays). The prompt goes on stdin:
# `--resume` takes an optional value and would swallow it. `--mode ask` reads and never edits.

def cursor_result(stdout: str, before: int = 0) -> tuple[str, float | None, int | None, str]:
    text, tokens, session, said = "", None, "", []
    for event in json_lines(stdout):
        kind = event.get("type")
        session = str(event.get("session_id") or session)
        msg = event.get("message")
        if kind == "assistant" and isinstance(msg, dict) and isinstance(msg.get("content"), list):
            said.append("".join(str(c.get("text") or "") for c in msg["content"] if isinstance(c, dict)))
        elif kind == "result":
            text = str(event.get("result") or "")
            usage = event.get("usage")
            if isinstance(usage, dict):
                vals = [usage[k] for k in ("inputTokens", "outputTokens", "cacheReadTokens", "cacheWriteTokens")
                        if isinstance(usage.get(k), int)]
                tokens = sum(vals) if vals else None
    return (said[-1] if said else text).strip(), None, tokens, session


def cursor_error(stdout: str) -> str:
    for event in reversed(json_lines(stdout)):
        if event.get("type") == "result" and (event.get("is_error") or event.get("subtype") == "error"):
            return str(event.get("result") or event.get("error") or "error")
    return ""


def _cursor(h, model, mode="", resume=""):
    return [h.bin, "-p", "--output-format", "stream-json", "--trust",
            *(["--mode", mode] if mode else ["--force", "--sandbox", "enabled"]),
            *_model("--model", model), *([f"--resume={resume}"] if resume else [])]
