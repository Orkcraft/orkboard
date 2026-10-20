"""A tool's run (spec 37 §3.1): the tool a step names as it runs, what goes on its stdin, the process itself and its
wait under Stop all, and what came of it (text, cost, tokens, session) or the error it ended with; and one answer of
a tool in an empty folder (`ask`, the onboarding's Check and the town's decisions through `realm/builders.py`).

Orkboard's: the Board's keeper and runner run a tool through `realm/jobs.py`, the town's roads through
`realm/road_agents.py`; both read these from here (`road_agents` and `roads` re-export them for the line).
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

from orkboard import settings
from orkboard.realm import call_log, halt, harnesses, tool_errors
from orkboard.sources import telemetry

CALL_TIMEOUT_S = 240            # one answer of a tool (`ask`)


def resolve(harness: str) -> str:
    """A step's tool as it runs: `main` (or nothing) is the machine's main tool."""
    if harness and harness != harnesses.MAIN:
        return harness
    return settings.main_tool()


def harness_stdin(harness: str, prompt: str) -> str | None:
    """What goes on stdin: a tool that reads its prompt there (Codex: no argv limit, never taken for a
    flag); the others take it as an argument."""
    h = harnesses.get(harness)
    return h.stdin(prompt) if h else None


def result_of(harness: str, stdout: str, before: int | dict = 0,
              model: str = "") -> tuple[str, float | None, int | None, str]:
    """(text, cost, tokens, session) of one run of a tool; `model` is what it was asked to run on
    (a tool that prints tokens and no price is priced from it). It is read when a run ended without a failure, so a host
    that watches hears it (`tool_errors.ran`, spec 45 §3)."""
    tool_errors.ran(harness)
    h = harnesses.get(harness)
    return h.outcome(stdout, before, model) if h else harnesses.json_result(stdout, before)


def codex_thread_usage(thread: str, env: dict | None = None) -> dict | None:
    """What a Codex thread has used so far: the last `token_count` total in its rollout
    (`$CODEX_HOME/sessions/YYYY/MM/DD/rollout-<ts>-<thread>.jsonl`), which `exec resume` starts its
    running total from. None when there is none (a compressed rollout is not read)."""
    env = os.environ if env is None else env
    if not thread:
        return None
    home = Path(env["CODEX_HOME"]) if env.get("CODEX_HOME") else Path.home() / ".codex"
    usage = None
    for rollout in sorted((home / "sessions").glob(f"*/*/*/rollout-*-{glob.escape(thread)}.jsonl")):
        try:
            lines = rollout.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            if '"token_count"' not in line:
                continue
            try:
                payload = json.loads(line).get("payload")
            except (ValueError, AttributeError):
                continue
            info = payload.get("info") if isinstance(payload, dict) and payload.get("type") == "token_count" else None
            total = info.get("total_token_usage") if isinstance(info, dict) else None
            if harnesses._plain_tokens(total) is not None:
                usage = total
    return usage


def run_proc(cmd: list[str], cwd: Path, env: dict, stdin: str | None,
             wait: Callable[[subprocess.Popen], None], harness: str = "") -> tuple[int, str, str]:
    """(exit code, stdout, stderr) of one harness call. Its output goes to temporary files, so a
    long answer or a stream of events never fills a pipe while `wait` polls the process."""
    with tempfile.TemporaryFile("w+") as out, tempfile.TemporaryFile("w+") as err:
        try:
            proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.PIPE if stdin is not None else None,
                                    stdout=out, stderr=err, text=True, start_new_session=True)
        except FileNotFoundError as e:
            raise tool_errors.missing(harness, cmd[0]) if harness else RuntimeError(f"{cmd[0]} not found") from e
        if stdin is not None:
            try:
                proc.stdin.write(stdin)
                proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass
        wait(proc)
        out.seek(0)
        err.seek(0)
        return proc.returncode, out.read(), err.read()


def wait(proc: subprocess.Popen, cancel: threading.Event, timeout_s: int, who: str = "",
         agent: bool = False) -> None:
    """Until it ends, `cancel` is set (InterruptedError) or the time is up; 🛑 Stop all kills it (Halted)."""
    halt.started(proc, who, agent)
    try:
        wait_for(proc, cancel, timeout_s)
    finally:
        halt.ended(proc)


def wait_for(proc: subprocess.Popen, cancel: threading.Event, timeout_s: int) -> None:
    deadline = time.monotonic() + timeout_s
    while proc.poll() is None:
        if cancel.wait(0.2) or time.monotonic() > deadline:
            proc.terminate()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
            if cancel.is_set():
                raise InterruptedError("stopped")
            raise RuntimeError(f"no answer within {timeout_s} s")


def failure(harness: str, code: int, stdout: str, stderr: str) -> tool_errors.ToolError:
    """The error of a harness call that exited with `code` (its str(): "<harness> exited with <code>: …")."""
    h = harnesses.get(harness)
    why = (h.error(stdout) if h else "") or (stderr or stdout).strip()
    return tool_errors.ToolError(harness, why, code)


def call(h: harnesses.Harness, prompt: str, model: str | None) -> subprocess.CompletedProcess:
    """One non-interactive answer of `h` in an empty temporary folder, without orkcraft's own
    variables. Raises RuntimeError when the CLI is missing or silent, Stopped on 🛑 Halt All."""
    with tempfile.TemporaryDirectory(prefix="orkcraft-mason-") as empty:
        env = {**{k: v for k, v in os.environ.items() if not k.startswith("ORKCRAFT_")}, **h.env("ask", empty)}
        cmd = h.ask(prompt, empty, model or "")
        try:
            return halt.run(cmd, input=h.stdin(prompt), cwd=empty, env=env, timeout=CALL_TIMEOUT_S,   # 🛑 Halt All
                            who=h.id, agent=True)
        except FileNotFoundError as e:
            raise tool_errors.ToolError(h.id, f"{h.title} CLI not found ({cmd[0]}) — install it or set "
                                        f"ORKCRAFT_{h.id.upper()}_BIN", kind=tool_errors.MISSING) from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"no answer within {CALL_TIMEOUT_S} s") from e
        except halt.Halted as e:
            raise halt.Stopped() from e


def ask(harness_id: str, prompt: str, model: str | None = None,
        call: Callable[[harnesses.Harness, str, str | None], subprocess.CompletedProcess] = call) -> tuple[str, float | None]:
    """One answer of a tool in an empty folder (`model`: its own, a tier word, or another tool's model
    — harnesses.model_on; None keeps its default). Raises RuntimeError on failure."""
    h = harnesses.need(harness_id)
    start = time.monotonic()
    replayed = call_log.answer("ask", prompt)                # a recorded answer, when a check plays one back
    proc = subprocess.CompletedProcess([], *replayed) if replayed is not None else call(h, prompt, model)
    if proc.returncode != 0:
        call_log.record(None, "ask", h.id, model or "", prompt, proc.stdout, proc.stderr, proc.returncode,
                        time.monotonic() - start, who=f"{h.id} -p")
        why = h.error(proc.stdout) or (proc.stderr or proc.stdout).strip()
        raise tool_errors.ToolError(h.id, why, proc.returncode)
    tool_errors.ran(h.id)
    text, cost, tokens, _ = h.outcome(proc.stdout, 0, model or "")
    call_log.record(None, "ask", h.id, model or "", prompt, proc.stdout, proc.stderr, proc.returncode,
                    time.monotonic() - start, cost, tokens, who=f"{h.id} -p")
    if not text.strip() and (why := h.error(proc.stdout)):
        raise tool_errors.ToolError(h.id, f"{h.id} gave no answer: {why}")
    telemetry.charge(cost, f"{h.id} -p {model or 'default'}", tokens=tokens, model=model or "")   # no transcript: 🪙 here
    return text, cost
