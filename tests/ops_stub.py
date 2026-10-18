"""A stub `claude` for Operations' tests (docs/specs/38-operations.md, Tests → A): it prints stream-json as a real
`claude -p --output-format stream-json` does, from answers the test queues, and keeps every command line it got.

    stub = Stub(tmp_path, monkeypatch, help="--effort --max-budget-usd --no-session-persistence")
    stub.answer(stream(tools=[...], text='{"args": {}}'))     # the next call's events, in order
    stream(uses=[(ACT, ARGS)])                                # … a tool called with the arguments it was told
    stub.calls()                                              # [{"argv", "cwd", "task"}] of the calls made
"""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

SCRIPT = r'''#!{python}
import json, os, sys, time
d = {folder!r}
args = sys.argv[1:]
if args == ["--help"]:
    print(open(os.path.join(d, "help")).read())
    sys.exit(0)
if args[:2] == ["mcp", "list"]:
    print(open(os.path.join(d, "mcp")).read())
    sys.exit(0)
seen = os.path.join(d, "seen")
n = len(os.listdir(seen))
with open(os.path.join(seen, "%03d.json" % n), "w") as f:
    json.dump({"argv": args, "cwd": os.getcwd(), "task": os.environ.get("ORKCRAFT_TASK", "")}, f)
queue = sorted(os.listdir(os.path.join(d, "answers")))
if not queue:
    print(json.dumps({"type": "result", "result": "no answer queued", "is_error": True}))
    sys.exit(1)
path = os.path.join(d, "answers", queue[0])
spec = json.load(open(path))
if not spec.get("keep"):
    os.remove(path)
prompt = args[args.index("-p") + 1] if "-p" in args else ""
checked = json.loads(prompt.split("Arguments:\n", 1)[1]) if "Arguments:\n" in prompt else None
for event in spec["events"]:                  # "__ARGS__": the arguments the action was told to call with
    for part in (event.get("message") or {}).get("content") or []:
        if part.get("input") == "__ARGS__":
            part["input"] = checked
for event in spec.get("before", []):
    print(json.dumps(event), flush=True)
time.sleep(spec.get("sleep", 0))
for event in spec["events"]:
    print(json.dumps(event), flush=True)
sys.exit(spec.get("code", 0))
'''

ARGS = "__ARGS__"
ALL_FLAGS = "--effort <level> --max-budget-usd <amount> --no-session-persistence"


class Stub:
    def __init__(self, tmp_path: Path, monkeypatch, help: str = ALL_FLAGS, mcp: str = "") -> None:
        from orkboard.realm import harnesses
        self.dir = tmp_path / "stub"
        for sub in ("seen", "answers"):
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        (self.dir / "help").write_text(help, encoding="utf-8")
        (self.dir / "mcp").write_text(mcp, encoding="utf-8")
        self.bin = self.dir / "claude"
        self.bin.write_text(SCRIPT.replace("{python}", sys.executable).replace("{folder!r}", repr(str(self.dir))),
                            encoding="utf-8")
        self.bin.chmod(self.bin.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        monkeypatch.setenv("ORKCRAFT_CLAUDE_BIN", str(self.bin))
        harnesses._HELP.clear()
        self._n = 0

    def answer(self, events: list[dict], code: int = 0, sleep: float = 0.0, keep: bool = False,
               before: list[dict] | None = None) -> None:
        self._n += 1
        (self.dir / "answers" / f"{self._n:04d}.json").write_text(json.dumps(
            {"events": events, "code": code, "sleep": sleep, "keep": keep, "before": before or []}), encoding="utf-8")

    def calls(self) -> list[dict]:
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((self.dir / "seen").glob("*.json"))]


def stream(tools: list[str] = (), uses: list[tuple] = (), text: str = "", cost: float = 0.01,
           error: bool = False) -> list[dict]:
    """A call's stream-json: its `init` (the tools it has), each tool call `(name, input[, is_error, text])` with its
    result, and its `result`."""
    out: list[dict] = [{"type": "system", "subtype": "init", "tools": list(tools), "session_id": "s"}]
    for n, use in enumerate(uses):
        name, given = use[0], use[1]
        failed = bool(use[2]) if len(use) > 2 else False
        said = use[3] if len(use) > 3 else ("refused" if failed else '{"key": "ABC-1"}')
        out.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": f"tu{n}", "name": name, "input": given}]}})
        out.append({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"tu{n}", "is_error": failed, "content": said}]}})
    out.append({"type": "result", "subtype": "error_during_execution" if error else "success", "is_error": error,
                "result": text, "total_cost_usd": cost,
                "usage": {"input_tokens": 100, "output_tokens": 20, "cache_read_input_tokens": 5}})
    return out


def mode(path: Path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)
