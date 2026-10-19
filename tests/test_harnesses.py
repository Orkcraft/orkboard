"""The registry of AI tools (realm/harnesses.py): every tool answers, reads and works through it, and
its output is read the same way whatever the tool."""
from __future__ import annotations

import json

import pytest

from orkboard.realm import harnesses, tool_run


def _lines(*events: dict) -> str:
    return "\n".join(json.dumps(e) for e in events)


def test_every_tool_is_registered_once_in_order():
    assert harnesses.ids() == ("claude", "agy", "codex", "hermes", "pi", "cursor")
    assert all(len(h.mark) == 1 for h in harnesses.REGISTRY.values())


@pytest.mark.parametrize("tool", harnesses.ids())
def test_a_prompt_never_reads_as_a_flag(tool, tmp_path):
    h = harnesses.need(tool)
    for cmd in (h.ask("-rm everything", tmp_path), h.read("-x", tmp_path), h.work("-x", tmp_path)):
        if h.stdin_prompt:
            assert "-rm everything" not in cmd and "-x" not in cmd
        else:
            i = cmd.index("-rm everything") if "-rm everything" in cmd else cmd.index("-x")
            assert cmd[i - 1] in ("-p", "--print", "--")                    # it is a flag's value or after --
    assert h.interactive("-x") in (None, [*h.interactive(), *h.deploy_args, "Orders: -x"])


def test_an_unchained_agy_asks_nothing_and_stays_in_its_sandbox(tmp_path):
    # agy's --print denies every command it would ask about and ends its turn empty, so an ork that runs its
    # tests first came back with nothing; unchained (autonomy.FREE) it skips the asking, never the sandbox.
    h = harnesses.need("agy")
    assert "--dangerously-skip-permissions" not in h.work("x", tmp_path)
    free = h.work("x", tmp_path, free=True)
    assert "--dangerously-skip-permissions" in free and "--sandbox" in free
    assert harnesses.need("claude").work("x", tmp_path, free=True) == harnesses.need("claude").work("x", tmp_path)


def test_hermes_reads_its_stream():
    out = _lines({"type": "system", "subtype": "init", "model": "m", "session_id": "20261007_120000_abcdef"},
                 {"type": "text", "text": "par"}, {"type": "text", "text": "tial"},
                 {"type": "result", "session_id": "20261007_120000_abcdef", "exit_code": 0, "text": "the answer",
                  "tokens": {"input": 10, "output": 5, "total": 15}})
    assert harnesses.hermes_result(out) == ("the answer", None, 15, "20261007_120000_abcdef")
    assert harnesses.hermes_error(_lines({"type": "result", "error": "no provider"})) == "no provider"
    h = harnesses.need("hermes")
    assert "--toolsets" in h.read("x", "/r") and "write" not in " ".join(h.read("x", "/r"))
    assert h.env("read", "/r")["HERMES_WRITE_SAFE_ROOT"] == harnesses.NOWHERE           # reading writes nowhere
    assert h.env("work", "/w")["HERMES_WRITE_SAFE_ROOT"] == "/w"                        # working: its worktree


def test_pi_sums_its_messages_and_their_price():
    usage = lambda n, usd: {"totalTokens": n, "cost": {"total": usd}}                  # noqa: E731
    out = _lines({"type": "session", "version": 3, "id": "u-1", "cwd": "/r"},
                 {"type": "message_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "a"}],
                                                     "usage": usage(100, 0.01)}},
                 {"type": "message_end", "message": {"role": "toolResult", "content": []}},
                 {"type": "message_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}],
                                                     "usage": usage(50, 0.02)}})
    text, cost, tokens, session = harnesses.pi_result(out)
    assert (text, round(cost, 4), tokens, session) == ("done", 0.03, 150, "u-1")
    h = harnesses.need("pi")
    read = h.read("x", "/r")
    assert "--no-tools" in h.ask("x", "/f") and read[read.index("--tools") + 1] == "read,grep,find,ls"
    assert read[read.index("-e") + 1].endswith("orkcraft.ts")                         # the Warder rides along


def test_claude_says_why_it_failed_from_its_envelope():
    # the owner's 19 October: a draft said only `claude exited with 1: {"duration_api_ms":0,…`; the envelope puts
    # is_error and result after usage, so a line cut from the raw JSON never says why
    env = {"duration_api_ms": 0, "stop_reason": "stop_sequence", "session_id": "s-1", "total_cost_usd": 0,
           "usage": {"input_tokens": 0, "output_tokens": 0}, "type": "result", "is_error": True, "num_turns": 1,
           "subtype": "success", "result": "Not logged in · Please run /login"}
    out = json.dumps(env)
    assert harnesses.claude_error(out) == "Not logged in · Please run /login"
    assert harnesses.claude_error(_lines({"type": "system", "subtype": "init"}, env)) == env["result"]   # stream-json
    assert harnesses.claude_error(json.dumps({**env, "is_error": False})) == ""
    assert harnesses.claude_error(json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True})) \
        == "error_max_turns"
    assert harnesses.claude_error("error: unknown option '--nope'") == ""          # its stderr says it then
    err = tool_run.failure("claude", 1, out, "")
    assert str(err) == "claude exited with 1: Not logged in · Please run /login" and err.kind == "login"


def test_cursor_reads_its_result_line():
    out = _lines({"type": "system", "subtype": "init", "session_id": "c-1", "model": "Auto"},
                 {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
                  "session_id": "c-1"},
                 {"type": "result", "subtype": "success", "is_error": False, "result": "hi", "session_id": "c-1",
                  "usage": {"inputTokens": 7, "outputTokens": 3, "cacheReadTokens": 0, "cacheWriteTokens": 0}})
    assert harnesses.cursor_result(out) == ("hi", None, 10, "c-1")
    assert harnesses.cursor_error(_lines({"type": "result", "subtype": "error", "is_error": True, "result": "bad model"})) \
        == "bad model"
    assert "--mode" in harnesses.need("cursor").read("x", "/r")                         # ask: never edits


def test_a_model_moves_between_tools_by_its_tier():
    assert harnesses.model_on("codex", "haiku") == "gpt-luna"
    assert harnesses.model_on("codex", "gemini-3.1-pro-high") == "gpt-astra"   # a version of agy's family
    assert harnesses.model_on("claude", "elder") == "opus"
    assert harnesses.model_on("agy", "my-own-model") == "my-own-model"
    assert harnesses.model_on("pi", "opus") == ""                       # no tiers: its own default


@pytest.mark.parametrize("tool, answer, expect", [
    ("hermes", _lines({"type": "result", "session_id": "s", "text": "{}", "tokens": {"total": 3}}), ("{}", None)),
    ("pi", _lines({"type": "session", "id": "s"}, {"type": "message_end", "message": {
        "role": "assistant", "content": [{"type": "text", "text": "{}"}], "usage": {"totalTokens": 3, "cost": {"total": 0.5}}}}),
     ("{}", 0.5)),
    ("cursor", _lines({"type": "result", "result": "{}", "session_id": "s"}), ("{}", None)),
])
def test_a_decision_runs_on_any_tool(tool, answer, expect, tmp_path, monkeypatch):
    fake, record = tmp_path / f"fake-{tool}", tmp_path / "argv.json"
    fake.write_text("#!/usr/bin/env python3\nimport json, os, sys\n"
                    "stdin = '' if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()\n"
                    f"json.dump({{'argv': sys.argv[1:], 'stdin': stdin, 'env': dict(os.environ)}}, open({str(record)!r}, 'w'))\n"
                    f"sys.stdout.write({answer!r})\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv(f"ORKCRAFT_{tool.upper()}_BIN", str(fake))
    assert tool_run.ask(tool, "plan it") == expect          # what builders.ask in Orkline wraps
    rec = json.loads(record.read_text())
    assert ("plan it" in rec["argv"]) != (rec["stdin"] == "plan it")
    assert not any(k.startswith("ORKCRAFT_") for k in rec["env"])
    assert tool_run.resolve("main") in harnesses.ids()


def test_logins_of_the_new_tools_are_told_from_disk(tmp_path):
    from orkboard import tools
    home = tmp_path
    assert tools._hermes_login({}, home) == (None, "subscription")
    (home / ".hermes").mkdir()
    (home / ".hermes" / ".env").write_text("OPENROUTER_API_KEY=sk-x\n", encoding="utf-8")
    assert tools._hermes_login({}, home) == (True, "api")
    (home / ".hermes" / "auth.json").write_text('{"providers": {"nous": {}}}', encoding="utf-8")
    assert tools._hermes_login({}, home) == (True, "subscription")
    (home / ".pi" / "agent").mkdir(parents=True)
    (home / ".pi" / "agent" / "auth.json").write_text('{"anthropic": {"type": "oauth"}}', encoding="utf-8")
    assert tools._pi_login({}, home) == (True, "subscription")
    assert tools._cursor_login({"CURSOR_API_KEY": "k"}, home) == (True, "subscription")
    assert tools._cursor_login({}, home) == (None, "subscription")
    found = tools.detect(which=lambda b: f"/bin/{b}" if b in ("pi", "cursor-agent") else None,
                         run=lambda *a, **k: type("P", (), {"stdout": "1.0.4", "stderr": "", "returncode": 0})(),
                         env={}, home=home)
    assert [s.id for s in found if s.found] == ["pi", "cursor"] and found[4].logged_in


def test_autonomy_says_what_each_new_tool_changes():
    from orkboard import autonomy
    free = autonomy.guide(autonomy.FREE, ("hermes", "pi", "cursor"))
    assert "hermes --yolo" in free and "cursor-agent --force" in free and "never asks" in free
    chains = autonomy.guide(0, ("hermes", "cursor"))
    assert "--yolo" not in chains and "--force" not in chains


def test_a_tool_that_names_its_cache_its_own_way_counts_what_it_read_from_it():
    """agy: a warm cache's call reads most of its input from the cache, apart; counted, it weighs as a cold one."""
    cold = {"input_tokens": 21_900, "output_tokens": 100}
    warm = {"input_tokens": 2_000, "output_tokens": 100, "cache_read_tokens": 19_800, "cachedContentTokenCount": 0}
    assert harnesses._tokens_of(cold) == 22_000 and harnesses._tokens_of(warm) == 21_900
    assert harnesses._tokens_of({"input_tokens": 5, "cache_read_input_tokens": 7, "cache_hit": True}) == 12


def test_a_call_is_held_to_its_tools_and_takes_effort_budget_and_one_shot(monkeypatch, tmp_path):
    """Spec 38 §4: `call` gains effort, budget and one shot as `read` has them; with no tool allowed, no list."""
    h = harnesses.get("claude")
    from orkboard.realm import harness_claude
    monkeypatch.setattr(harness_claude, "cli_has", lambda h, flag: True)     # where `_claude_run` looks it up
    argv = h.call("do it", tmp_path, ["mcp__a__b"], "warrior", effort="medium", budget=0.3, one_shot=True)
    assert argv[argv.index("--allowedTools") + 1] == "mcp__a__b"
    assert argv[argv.index("--disallowedTools") + 1] == harnesses.CLAUDE_NO_TOOLS
    assert argv[-5:] == ["--effort", "medium", "--max-budget-usd", "0.30", "--no-session-persistence"]
    bare = h.call("learn", tmp_path, [], "laborer", effort="low", one_shot=True)
    assert "--allowedTools" not in bare and "--effort" not in bare and bare[-1] == "--no-session-persistence"


def test_a_calls_stream_is_read_into_its_events():
    from orkboard.realm import jobs
    out = "\n".join(json.dumps(e) for e in [
        {"type": "system", "subtype": "init", "tools": ["mcp__a__b", "Read"]},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "…"},
                                                      {"type": "tool_use", "id": "t1", "name": "mcp__a__b",
                                                       "input": {"x": 1}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": True,
                                                  "content": [{"type": "text", "text": "no such field"}]}]}},
        {"type": "result", "result": "{}", "total_cost_usd": 0.02}])
    events, result = jobs.call_events(out + "\nnot json")
    assert events == [{"type": "init", "tools": ["mcp__a__b", "Read"]},
                      {"type": "tool_use", "id": "t1", "name": "mcp__a__b", "input": {"x": 1}},
                      {"type": "tool_result", "id": "t1", "is_error": True, "text": "no such field"}]
    assert result["total_cost_usd"] == 0.02
