"""A tool's own sign-in (docs/specs/45-sign-in.md, Tests → A): each tool's way (`realm/harnesses.py`), `tools.signed_in`,
a sign-in run with a fake process and clock (`realm/sign_in.py`), when a sign-in helps (`realm/tool_errors.py`), the host's
service (`core/sign_ins.py`), the work held for it and run again, the Map's wait and need, the Check row, the events and the
desktop-only commands. Nothing here starts a real tool, a browser or a terminal."""
from __future__ import annotations

import datetime as dt
import io
import json
import subprocess
import time
from types import SimpleNamespace

import pytest

from orkboard import settings, tools
from orkboard.core import bus as b
from orkboard.core.idea_keeper import IdeaKeeper
from orkboard.core.idea_runner import IdeaRunner
from orkboard.core.op_runner import OpRunner
from orkboard.core.sign_ins import HOLD_H, SignInError, SignIns
from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import board_map, event_log, harnesses, ideas, jobs, op_runs, sign_in, tool_errors
from orkboard.realm.sign_in import CHECK_PROMPT, WAIT_S, Outcome
from tests.ops_stub import Stub, stream
from tests.test_idea_runner import plan_of, tasks_of, town  # noqa: F401  (the runner's repository and stub claude)
from tests.test_op_runner import WHAT, prepared, wait as wait_op

LOGIN = "Not logged in · Please run /login"


def login_error(harness: str = "claude", said: str = LOGIN) -> tool_errors.ToolError:
    return tool_errors.ToolError(harness, said, 1)


# -- each tool's own sign-in (§1) ---------------------------------------------------------------------------------

def test_each_tool_has_its_own_sign_in_and_login_words_are_as_they_were():
    table = {"claude": (("auth", "login"), "browser", "", "claude  (then /login)"),
             "codex": (("login",), "browser", "", "codex login"),
             "cursor": (("login",), "terminal", "", "cursor-agent login"),
             "agy": (("login",), "terminal", "", "agy login"),
             "pi": ((), "terminal", "/login", "pi  (then /login)"),
             "hermes": (("setup",), "terminal", "", "hermes setup")}
    assert set(table) == set(harnesses.ids())
    for tid, (argv, by, typed, login) in table.items():
        h = harnesses.need(tid)
        assert (h.sign_in, h.sign_in_by, h.sign_in_type, h.login) == (argv, by, typed, login), tid


def fake_run(version="2.1.304", status=None, codex="Not logged in"):
    def run(argv, **kw):
        tail = argv[1:]
        if tail == ["--version"]:
            return subprocess.CompletedProcess(argv, 0, f"{version} (Claude Code)\n", "")
        if tail == ["auth", "status"]:
            if status is None:
                raise AssertionError("auth status asked")
            return subprocess.CompletedProcess(argv, 0 if status["loggedIn"] else 1, json.dumps(status), "")
        if tail == ["login", "status"]:
            return subprocess.CompletedProcess(argv, 1, "", codex)
        return subprocess.CompletedProcess(argv, 0, "", "")
    return run


def test_signed_in_tells_each_tool_without_a_model_call(tmp_path):
    home, which = tmp_path, lambda name: f"/bin/{name}"
    # Claude Code: `auth status` from 2.1.41 on, else its files
    assert tools.signed_in("claude", {}, fake_run(status={"loggedIn": True}), home, which) is True
    assert tools.signed_in("claude", {}, fake_run(status={"loggedIn": False}), home, which) is False
    assert tools.signed_in("claude", {}, fake_run("2.1.30"), home, which) is None            # too old to ask, no files
    (home / ".claude").mkdir()
    (home / ".claude" / ".credentials.json").write_text("{}")
    assert tools.signed_in("claude", {}, fake_run("2.1.30"), home, which) is True
    # Codex: auth.json, else `login status`
    assert tools.signed_in("codex", {}, fake_run(), home, which) is False
    (home / ".codex").mkdir()
    (home / ".codex" / "auth.json").write_text(json.dumps({"auth_mode": "chatgpt", "tokens": {}}))
    assert tools.signed_in("codex", {}, fake_run(), home, which) is True
    # pi, Hermes Agent and Cursor read their files; Antigravity and an unknown tool cannot be told
    assert tools.signed_in("pi", {}, fake_run(), home, which) is None
    (home / ".pi" / "agent").mkdir(parents=True)
    (home / ".pi" / "agent" / "auth.json").write_text(json.dumps({"anthropic": {"type": "oauth"}}))
    assert tools.signed_in("pi", {}, fake_run(), home, which) is True
    assert tools.signed_in("hermes", {}, fake_run(), home, which) is None
    assert tools.signed_in("cursor", {"CURSOR_API_KEY": "k"}, fake_run(), home, which) is True
    assert tools.signed_in("agy", {}, fake_run(), home, which) is None
    assert tools.signed_in("nobody", {}, fake_run(), home, which) is None


# -- a sign-in run (§2) --------------------------------------------------------------------------------------------

class Proc:
    """A fake process: it says `lines`, and ends with `code` (None: still going) once polled `ends` times."""

    def __init__(self, argv, lines=(), code=None, **kw) -> None:
        self.argv, self.kw, self.stdout = argv, kw, io.StringIO("".join(f"{ln}\n" for ln in lines))
        self.returncode, self.pid, self.terminated = code, 99999, False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated, self.returncode = True, -15

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.returncode = -9


class Spawner:
    """`popen`: remembers every process it was asked to start."""

    def __init__(self, lines=(), code=None, fail=False) -> None:
        self.lines, self.code, self.fail, self.procs = lines, code, fail, []

    def __call__(self, argv, **kw):
        if self.fail:
            raise OSError("no such file")
        self.procs.append(Proc(argv, self.lines, self.code, **kw))
        return self.procs[-1]


class Clock:
    def __init__(self, now=1000.0) -> None:
        self.now = now

    def __call__(self):
        return self.now


def begin(tid, tmp_path, popen, platform="linux", signed=None, asked=None, clock=None, env=None, which=None):
    asked = [] if asked is None else asked

    def ask(harness, prompt, model=None):
        asked.append((harness, prompt, model))
        if isinstance(signed, Exception):
            raise signed

    return sign_in.start(tid, {"PATH": "/usr/bin", "HOME": str(tmp_path)} if env is None else env, tmp_path / "state",
                         platform, which or (lambda name: f"/bin/{name}"), popen, clock=clock or Clock(),
                         signed_in=lambda h, e=None: signed if isinstance(signed, bool) or signed is None else None,
                         ask=ask, home=tmp_path), asked


def test_the_browser_way_runs_the_tools_own_sign_in_in_the_home_folder_with_stdin_closed(tmp_path):
    spawn = Spawner(["Opening your browser…"])
    env = {"PATH": "/opt/bin:/usr/bin", "CLAUDE_CONFIG_DIR": "/work/claude"}
    run, _ = begin("claude", tmp_path, spawn, signed=True, env=env)
    proc = spawn.procs[0]
    assert proc.argv == ["/bin/claude", "auth", "login"] and proc.kw["cwd"] == str(tmp_path)
    assert proc.kw["stdin"] == subprocess.DEVNULL and proc.kw["env"]["CLAUDE_CONFIG_DIR"] == "/work/claude"
    assert proc.kw["env"]["PATH"] == "/opt/bin:/usr/bin" and run.by == "browser"
    assert run.poll() is None
    proc.returncode = 0
    assert run.poll() == Outcome("done")                             # exit 0 and signed in: told
    assert run.poll() == Outcome("done")                             # and the same afterwards


def test_a_run_that_ends_with_another_code_failed_with_its_last_line(tmp_path):
    spawn = Spawner(["starting", "Login failed: access denied"], code=1)
    run, _ = begin("codex", tmp_path, spawn)
    assert run.poll() == Outcome("failed", "Login failed: access denied")


def test_a_run_not_done_in_wait_s_is_stopped_as_timeout(tmp_path):
    clock, spawn = Clock(), Spawner()
    run, _ = begin("claude", tmp_path, spawn, clock=clock)
    clock.now += WAIT_S - 1
    assert run.poll() is None
    clock.now += 2
    assert run.poll() == Outcome("failed", "timeout") and spawn.procs[0].terminated


def test_a_browser_that_did_not_open_asks_for_a_code_and_ends_as_no_browser(tmp_path):
    spawn = Spawner(["Browser didn't open? Paste code here if prompted >"])
    run, _ = begin("claude", tmp_path, spawn)
    for _ in range(50):
        if (out := run.poll()) is not None:
            break
        time.sleep(0.02)
    assert out == Outcome("failed", "no_browser") and spawn.procs[0].terminated


def test_the_log_holds_no_url_past_its_host(tmp_path):
    spawn = Spawner(["Open https://claude.com/cai/oauth/authorize?code=true&state=SECRETSTATE in a browser",
                     "callback http://localhost:5555/callback?code=abc123"], code=0)
    run, _ = begin("claude", tmp_path, spawn, signed=True)
    assert run.poll() == Outcome("done")
    text = (tmp_path / "state" / "sign-in" / "claude.log").read_text()
    assert "https://claude.com" in text and "http://localhost:5555" in text
    assert "SECRETSTATE" not in text and "abc123" not in text and "/callback" not in text
    assert sign_in.cut_urls("go https://a.example/x?y=1 now") == "go https://a.example now"


def test_told_by_signed_in_true_false_or_the_check(tmp_path):
    run, asked = begin("claude", tmp_path, Spawner(code=0), signed=False)
    assert run.poll() == Outcome("failed", "refused") and asked == []
    run, asked = begin("claude", tmp_path, Spawner(code=0), signed=None)                    # cannot be told: the Check
    assert run.poll() == Outcome("done") and asked == [("claude", CHECK_PROMPT, "laborer")]
    words = tool_errors.ToolError("claude", "401 unauthorized", 1)
    run, _ = begin("claude", tmp_path, Spawner(code=0), signed=words)
    out = run.poll()
    assert out.state == "failed" and out.why.startswith("Claude Code is not signed in")


def test_cancel_stops_the_process(tmp_path):
    spawn = Spawner()
    run, _ = begin("claude", tmp_path, spawn)
    assert run.cancel() == Outcome("failed", "cancelled") and spawn.procs[0].terminated
    assert run.poll() == Outcome("failed", "cancelled")


def test_a_tool_not_found_or_unknown_cannot_start(tmp_path):
    with pytest.raises(SignInError, match="not found on this computer"):
        begin("claude", tmp_path, Spawner(), which=lambda name: None)
    with pytest.raises(SignInError, match="not one of the AI tools"):
        begin("nobody", tmp_path, Spawner())


def test_the_terminal_way_writes_a_script_and_opens_it_in_a_window(tmp_path):
    spawn = Spawner()
    env = {"PATH": "/opt/bin:/usr/bin", "PI_CODING_AGENT_DIR": "/work/pi", "SECRET_TOKEN": "t0ken"}
    run, _ = begin("pi", tmp_path, spawn, signed=None, env=env)
    script = tmp_path / "state" / "sign-in" / "pi.command"
    assert (script.stat().st_mode & 0o777) == 0o700
    text = script.read_text()
    assert text.splitlines()[:2] == ["#!/bin/sh", "cd ~ || exit 1"]
    assert "export PATH=/opt/bin:/usr/bin" in text and "export PI_CODING_AGENT_DIR=/work/pi" in text
    assert text.rstrip().endswith("exec /bin/pi") and "t0ken" not in text and "SECRET" not in text
    assert spawn.procs[0].argv == ["x-terminal-emulator", "-e", str(script)] and run.by == "terminal"
    assert run.poll() is None                                          # cannot be told: only the person's Done
    assert run.told() == Outcome("done") and run.poll() == Outcome("done")      # the Check answered


def test_the_script_of_a_tool_with_arguments_names_them(tmp_path):
    begin("hermes", tmp_path, Spawner())
    assert (tmp_path / "state" / "sign-in" / "hermes.command").read_text().rstrip().endswith("exec /bin/hermes setup")


@pytest.mark.parametrize("platform, argv", [
    ("darwin", ["open", "-a", "Terminal", "{script}"]),
    ("win32", ["cmd", "/c", "start", "", "cmd", "/k", "{script}"]),
])
def test_the_opener_per_platform(tmp_path, platform, argv):
    spawn = Spawner()
    begin("pi", tmp_path, spawn, platform=platform)
    name = "pi.cmd" if platform == "win32" else "pi.command"
    script = tmp_path / "state" / "sign-in" / name
    assert spawn.procs[0].argv == [a.replace("{script}", str(script)) for a in argv]
    if platform == "win32":
        assert script.read_bytes().startswith(b"@echo off\r\ncd /d")


def test_linux_tries_each_terminal_in_turn_and_none_found_says_what_to_type(tmp_path):
    order = [("x-terminal-emulator", "-e"), ("gnome-terminal", "--"), ("konsole", "-e"), ("xfce4-terminal", "-x"),
             ("xterm", "-e")]
    for n, (name, flag) in enumerate(order):
        spawn = Spawner()
        left = {m for m, _ in order[n:]}                             # the ones before it are missing
        begin("pi", tmp_path, spawn, which=lambda x, left=left: f"/bin/{x}" if x in left or x == "pi" else None)
        assert spawn.procs[0].argv[:2] == [name, flag]
    spawn = Spawner()
    run, _ = begin("pi", tmp_path, spawn, which=lambda x: "/bin/pi" if x == "pi" else None)
    assert spawn.procs == [] and run.poll() == Outcome("none", command="pi  (then /login)")
    run, _ = begin("pi", tmp_path, Spawner(fail=True))                # a terminal that cannot start is none too
    assert run.poll().state == "none"


def test_a_terminal_sign_in_ends_when_the_tool_says_signed_in_and_after_wait_s(tmp_path):
    clock, answers = Clock(), [False]
    run = sign_in.start("pi", {"PATH": "/usr/bin"}, tmp_path / "state", "linux", lambda n: f"/bin/{n}", Spawner(),
                        clock=clock, signed_in=lambda h, e=None: answers[0], ask=lambda *a: None, home=tmp_path)
    assert run.poll() is None
    answers[0] = True
    clock.now += 1
    assert run.poll() is None                                          # asked every POLL_S, not before
    clock.now += sign_in.POLL_S
    assert run.poll() == Outcome("done")
    late = sign_in.start("pi", {}, tmp_path / "state", "linux", lambda n: f"/bin/{n}", Spawner(), clock=clock,
                         signed_in=lambda h, e=None: False, ask=lambda *a: None, home=tmp_path)
    clock.now += WAIT_S + 1
    assert late.poll() == Outcome("failed", "timeout")


# -- when a sign-in helps (§3) --------------------------------------------------------------------------------------

def test_helps_unless_a_key_is_set_or_another_claude_renews_or_only_weak_words_and_signed_in():
    never = lambda *a, **k: (_ for _ in ()).throw(AssertionError("asked"))           # noqa: E731
    err = login_error()
    assert tool_errors.helps(err, {}, never) is True
    assert tool_errors.helps(err, {"ANTHROPIC_API_KEY": "k"}, never) is False
    assert tool_errors.helps(err, {"ANTHROPIC_AUTH_TOKEN": "k"}, never) is False
    assert tool_errors.helps(login_error("codex", "401 unauthorized"), {"CODEX_API_KEY": "k"}, never) is False
    assert tool_errors.helps(login_error("codex", "401 unauthorized"), {}, never) is True
    assert tool_errors.helps(login_error("cursor", "401 unauthorized"), {"CURSOR_API_KEY": "k"}, never) is False
    renewing = login_error(said="Not logged in: another Claude Code process is refreshing the token")
    assert tool_errors.helps(renewing, {}, never) is False
    weak = login_error(said="Failed to authenticate with the OAuth server")
    assert tool_errors.helps(weak, {}, lambda h, e=None: True) is False
    assert tool_errors.helps(weak, {}, lambda h, e=None: False) is True
    assert tool_errors.helps(weak, {}, lambda h, e=None: None) is True
    assert tool_errors.helps(tool_errors.ToolError("claude", "429 rate limit", 1), {}, never) is False   # not a login


def test_watch_hears_each_login_failure_and_each_run_that_ended_well_and_swallows_its_errors():
    seen, ok = [], []
    stop = tool_errors.watch(lambda e: seen.append(e))
    tool_errors.watch(lambda e: 1 / 0)                      # its own error never stops the work
    tool_errors.watch_ok(ok.append)
    first = login_error()
    tool_errors.ToolError("claude", "429 rate limit", 1)    # not a login
    tool_errors.ran("codex")
    assert seen == [first] and ok == ["codex"]
    stop()
    login_error()
    assert len(seen) == 1


def test_nothing_is_watched_until_a_host_watches():
    # (the conftest drops every watcher after each test) the words of a failure are as they were
    err = login_error()
    assert tool_errors.what_to_do(err) == tool_errors.claude_sign_in(err.detail)
    tool_errors.ran("claude")


def test_what_to_do_says_sign_in_opens_when_the_host_judged_a_sign_in_helps(tmp_path):
    signins = fresh(tmp_path)[0]
    err = login_error()
    assert tool_errors.what_to_do(err) == "Sign in opens Claude Code's sign-in. In a terminal: claude, then /login."
    assert tool_errors.what_to_do(login_error("codex", "401 unauthorized")) == \
        "Sign in opens Codex's sign-in. In a terminal: codex login."
    assert signins.blocked("claude") and signins.blocked("codex")


# -- the host's service (§4) ----------------------------------------------------------------------------------------

def fresh(tmp_path, env=None, signed=None, root=None, **kw):
    """A SignIns that watches, with a fake process per start and a clock of its own."""
    spawn, clock, bus = Spawner(), Clock(), b.Bus()
    seen = []
    bus.subscribe(b.ANY, seen.append)
    state = {"signed": signed}

    def start(harness, env_, state_dir, platform="linux", which=None, **k):
        return sign_in.start(harness, env_, state_dir, platform, which or (lambda n: f"/bin/{n}"), spawn, clock=clock,
                             signed_in=lambda h, e=None: state["signed"], ask=lambda *a: None, home=tmp_path)

    s = SignIns(bus, {} if env is None else env, tmp_path / "state", clock, start=start, which=lambda n: f"/bin/{n}",
                signed_in=lambda h, e=None: state["signed"], port_busy=lambda: False, threaded=False, root=root, **kw)
    s.watch()
    s.spawn, s.clock_, s.events, s.state = spawn, clock, seen, state
    return s, bus


def topics(s, topic):
    return [e.data for e in s.events if e.topic == topic]


def test_a_failure_a_sign_in_helps_begins_an_episode_with_auto(tmp_path):
    s, _ = fresh(tmp_path)
    assert s.snapshot() == [] and not s.blocked("claude")
    login_error()
    [e] = s.snapshot()
    assert e["harness"] == "claude" and e["tool"] == "Claude Code" and e["state"] == "needed" and e["by"] == "browser"
    assert e["auto"] is True and e["where"] == "ask" and e["waiting"] == 0 and s.blocked("claude")
    assert topics(s, b.SIGN_IN)[-1]["state"] == "needed"
    login_error()                                                # a second failure: the same episode
    assert len(topics(s, b.SIGN_IN)) == 1
    tool_errors.ToolError("claude", "429 rate limit", 1)         # a failure a sign-in does not help is never kept
    assert [x["harness"] for x in s.snapshot()] == ["claude"]


def test_a_key_set_where_orkline_runs_keeps_no_episode(tmp_path):
    s, _ = fresh(tmp_path, env={"ANTHROPIC_API_KEY": "k"})
    login_error()
    assert s.snapshot() == [] and not s.blocked("claude")


def test_the_snapshot_lists_the_tools_in_the_registrys_order(tmp_path):
    s, _ = fresh(tmp_path)
    login_error("pi", "Not logged in")
    login_error("codex", "401 unauthorized")
    login_error("claude")
    assert [e["harness"] for e in s.snapshot()] == [h for h in harnesses.ids() if h in ("claude", "codex", "pi")]


def test_start_opens_one_run_per_tool_and_auto_is_taken_once(tmp_path):
    s, _ = fresh(tmp_path)
    login_error()
    first = s.start("claude", auto=True)
    assert first["state"] == "open" and first["auto"] is False and len(s.spawn.procs) == 1
    assert s.spawn.procs[0].argv == ["/bin/claude", "auth", "login"]
    assert s.start("claude")["state"] == "open" and len(s.spawn.procs) == 1          # never a second
    s.cancel("claude")
    assert s.entry("claude")["state"] == "failed" and s.entry("claude")["why"] == "cancelled"
    assert s.start("claude", auto=True)["state"] == "failed" and len(s.spawn.procs) == 1     # auto only once
    assert s.start("claude")["state"] == "open" and len(s.spawn.procs) == 2                  # Sign in again, any time
    login_error()                                                  # a second failure opens nothing by itself
    assert s.entry("claude")["auto"] is False


def test_the_run_ending_well_is_done_and_publishes_signed_in(tmp_path):
    s, _ = fresh(tmp_path, signed=True)
    login_error()
    s.start("claude")
    s.spawn.procs[0].returncode = 0
    s.clock_.now += 7
    s.tick()
    assert s.snapshot() == [] and not s.blocked("claude")
    assert topics(s, b.SIGNED_IN) == [{"harness": "claude"}]
    assert topics(s, b.SIGN_IN)[-1]["state"] == "done"


def test_a_run_that_fails_leaves_the_episode_going_and_offers_sign_in_again(tmp_path):
    s, _ = fresh(tmp_path, signed=False)
    login_error()
    s.start("claude")
    s.spawn.procs[0].returncode = 0
    s.tick()
    [e] = s.snapshot()
    assert e["state"] == "failed" and e["why"] == "refused" and s.blocked("claude")


def test_no_terminal_is_none_with_the_words_to_type(tmp_path):
    s, _ = fresh(tmp_path)
    s._which = lambda n: "/bin/pi" if n == "pi" else None
    s._start = lambda *a, **k: sign_in.start("pi", {}, tmp_path / "state", "linux",
                                              lambda n: "/bin/pi" if n == "pi" else None, Spawner(), home=tmp_path)
    login_error("pi", "Not logged in")
    e = s.start("pi")
    assert e["state"] == "none" and e["command"] == "pi  (then /login)"


def test_done_is_the_persons_word_for_a_tool_that_cannot_be_told(tmp_path):
    s, _ = fresh(tmp_path)
    login_error("agy", "Not logged in")
    s.start("agy")
    assert s.entry("agy")["by"] == "terminal" and s.entry("agy")["state"] == "open"
    s.tick()
    assert s.entry("agy")["state"] == "open"                         # nothing tells it
    s.done("agy")
    assert s.entry("agy")["state"] == "done" and topics(s, b.SIGNED_IN) == [{"harness": "agy"}]
    with pytest.raises(SignInError):
        s.done("agy")


def test_a_run_of_the_tool_that_ended_well_ends_the_episode_as_elsewhere(tmp_path):
    s, _ = fresh(tmp_path)
    login_error()
    s.start("claude")
    tool_errors.ran("claude")
    assert s.entry("claude")["state"] == "done" and s.spawn.procs[0].terminated
    assert topics(s, b.SIGNED_IN) == [{"harness": "claude"}]
    tool_errors.ran("claude")                                        # nothing to end now
    assert len(topics(s, b.SIGNED_IN)) == 1


def test_a_failure_right_after_a_sign_in_of_a_tool_that_says_signed_in_begins_nothing(tmp_path):
    s, _ = fresh(tmp_path, signed=True)
    login_error()
    tool_errors.ran("claude")
    err = login_error()                                              # a run that began before the sign-in
    assert s.snapshot() == [] and s.holds(err)                      # held, and let go at once
    s.clock_.now += 3600
    s.state["signed"] = None
    login_error()
    assert s.blocked("claude")                                       # a new episode


def test_stop_all_cancels_an_open_run_and_quitting_stops_the_runs(tmp_path):
    s, _ = fresh(tmp_path)
    login_error()
    s.start("claude")
    s.stop_all()
    assert s.spawn.procs[0].terminated and s.entry("claude")["why"] == "cancelled"
    s.start("claude")
    s.close()
    assert s.spawn.procs[1].terminated
    login_error("codex", "401 unauthorized")                         # nothing is watched any more
    assert s.entry("codex") is None


def test_one_codex_sign_in_at_a_time_on_the_computer(tmp_path):
    busy = [True]
    s, _ = fresh(tmp_path)
    s._port_busy = lambda: busy[0]
    login_error("codex", "401 unauthorized")
    assert s.start("codex")["state"] == "open" and s.spawn.procs == []        # waits for the first one's port
    s.tick()
    assert s.spawn.procs == []
    busy[0] = False
    s.clock_.now += 10
    s.tick()
    assert s.spawn.procs[0].argv == ["/bin/codex", "login"]


def test_a_tool_told_not_signed_in_and_then_signed_in_elsewhere_ends_the_episode(tmp_path):
    s, _ = fresh(tmp_path, signed=False)
    login_error()
    s.clock_.now += 31
    s.tick()                                                        # asked: not signed in
    assert s.blocked("claude")
    s.state["signed"] = True
    s.clock_.now += 31
    s.tick()
    assert not s.blocked("claude") and topics(s, b.SIGNED_IN) == [{"harness": "claude"}]


def test_the_events_are_written_to_the_shown_projects_log_only(tmp_path):
    root = tmp_path / "project"
    s, _ = fresh(tmp_path, signed=True, root=lambda: root)
    login_error()
    s.start("claude")
    s.clock_.now += 12
    tool_errors.ran("claude")
    rows = event_log.read(root)
    assert [r["event"] for r in rows] == ["sign_in_needed", "signed_in"]
    assert rows[0]["harness"] == "claude" and rows[0]["where"] == "ask"
    assert rows[1]["by"] == "elsewhere" and rows[1]["s"] == 12
    none, _ = fresh(tmp_path / "other")
    login_error("codex", "401 unauthorized")
    assert not (tmp_path / "other" / ".orkcraft").exists() and none.blocked("codex")


def test_a_failed_sign_in_writes_sign_in_failed(tmp_path):
    root = tmp_path / "project"
    s, _ = fresh(tmp_path, root=lambda: root)
    login_error()
    s.start("claude")
    s.cancel("claude")
    assert [r["event"] for r in event_log.read(root)] == ["sign_in_needed", "sign_in_failed"]
    assert event_log.read(root)[1]["why"] == "cancelled"


def test_where_names_what_failed_first(tmp_path):
    s, _ = fresh(tmp_path)
    with tool_errors.doing("task"):
        login_error()
    assert s.entry("claude")["where"] == "task"


# -- the work waits for it (§6) -------------------------------------------------------------------------------------

def runner_with(town, signins):
    events = []
    bus = SimpleNamespace(publish=lambda topic, **data: events.append((topic, data)))
    cfg = SimpleNamespace(ideas={"max_parallel": 1, "merge_into": "main", "push": False, "review": False})
    return IdeaRunner(town.repo, town.state, cfg, bus, sign_ins=signins)


def until(fn, timeout=30.0):
    end = time.time() + timeout
    while time.time() < end:
        if (got := fn()):
            return got
        time.sleep(0.05)
    raise AssertionError("never happened")


def refuse_login(monkeypatch, said=LOGIN):
    real = jobs.run_work
    state = {"refuse": True}

    def run_work(*a, **k):
        if state["refuse"]:
            raise tool_errors.ToolError("claude", said, 1)
        return real(*a, **k)

    monkeypatch.setattr(jobs, "run_work", run_work)
    return state


def test_a_task_that_hit_a_refused_sign_in_is_held_and_runs_again_once_signed_in(town, tmp_path, monkeypatch):
    signins, _ = fresh(tmp_path / "cfg")
    refuse = refuse_login(monkeypatch)
    plan_of(town, [{"id": "k1"}])
    runner = runner_with(town, signins)
    runner.start("demo")
    task = until(lambda: (t := tasks_of(town)["k1"])["state"] == "held" and t)
    assert task["held_for"] == "sign_in" and task["harness"] == "claude" and task["error"] == ""
    assert "Claude Code is not signed in" in task["held_line"]
    due = dt.datetime.fromisoformat(task["held_until"]).timestamp()
    assert abs(due - (time.time() + HOLD_H * 3600)) < 120
    assert signins.entry("claude")["where"] == "task" and runner.held_for("claude") == 1
    until(lambda: not runner.busy())
    runner.tick()
    assert tasks_of(town)["k1"]["state"] == "held"                 # still signed out: it waits
    refuse["refuse"] = False
    tool_errors.ran("claude")                                      # signed in again
    end = time.time() + 60
    while time.time() < end and tasks_of(town)["k1"]["state"] != "merged":
        runner.tick()
        time.sleep(0.1)
    assert tasks_of(town)["k1"]["state"] == "merged" and not tasks_of(town)["k1"].get("held_for")


def test_a_task_held_for_a_day_fails_as_it_did_with_the_line(town, tmp_path, monkeypatch):
    signins, _ = fresh(tmp_path / "cfg")
    refuse_login(monkeypatch)
    plan_of(town, [{"id": "k1"}])
    runner = runner_with(town, signins)
    runner.start("demo")
    until(lambda: tasks_of(town)["k1"]["state"] == "held")
    until(lambda: not runner.busy())
    plan = json.loads((town.state / "ideas" / "demo" / "plan.json").read_text())
    plan["tasks"][0]["held_until"] = (dt.datetime.now() - dt.timedelta(minutes=1)).isoformat(timespec="seconds")
    (town.state / "ideas" / "demo" / "plan.json").write_text(json.dumps(plan))
    runner.tick()
    task = tasks_of(town)["k1"]
    assert task["state"] == "failed" and task["error"].startswith("Claude Code is not signed in")


def test_a_failed_or_cancelled_sign_in_leaves_what_is_held_held(town, tmp_path, monkeypatch):
    signins, _ = fresh(tmp_path / "cfg")
    refuse_login(monkeypatch)
    plan_of(town, [{"id": "k1"}])
    runner = runner_with(town, signins)
    runner.start("demo")
    until(lambda: tasks_of(town)["k1"]["state"] == "held")
    until(lambda: not runner.busy())
    signins.start("claude")
    signins.cancel("claude")
    runner.tick()
    assert tasks_of(town)["k1"]["state"] == "held" and signins.entry("claude")["state"] == "failed"


def test_a_task_that_starts_while_the_tool_needs_its_sign_in_is_held_at_once(town, tmp_path, monkeypatch):
    signins, _ = fresh(tmp_path / "cfg")
    login_error()                                                    # the episode began elsewhere
    called = []
    monkeypatch.setattr(jobs, "run_work", lambda *a, **k: called.append(1))
    plan_of(town, [{"id": "k1"}, {"id": "k2"}])
    runner = runner_with(town, signins)
    runner.start("demo")
    runner.tick()
    states = {k: t["state"] for k, t in tasks_of(town).items()}
    assert states["k1"] == "held" and called == [] and tasks_of(town)["k1"]["held_for"] == "sign_in"


def test_a_key_in_the_environment_fails_the_task_as_today(town, tmp_path, monkeypatch):
    signins, _ = fresh(tmp_path / "cfg", env={"ANTHROPIC_API_KEY": "k"})
    refuse_login(monkeypatch)
    plan_of(town, [{"id": "k1"}])
    runner = runner_with(town, signins)
    runner.start("demo")
    until(lambda: tasks_of(town)["k1"]["state"] == "failed")
    assert "held_for" not in tasks_of(town)["k1"]


@pytest.fixture
def keeper(tmp_path):
    root, state = tmp_path / "wiki", tmp_path / ".orkcraft"
    signins, _ = fresh(tmp_path / "cfg")
    settings_ = {"batch_minutes": 30, "idle_hours": 24}
    k = IdeaKeeper(tmp_path, state, lambda: root, lambda: settings_, lambda slug: None, sign_ins=signins)
    k.root, k.state, k.signins = root, state, signins
    return k


class Answers:
    def __init__(self, *answers) -> None:
        self.answers = list(answers)

    def __call__(self, tier, prompt, effort="", budget=None):
        got = self.answers.pop(0)
        if isinstance(got, Exception):
            raise got
        return json.dumps(got), 0.01, 1000, "s"


NOON = dt.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0).timestamp()      # outside the night

DRAFT = {"gist": "Dark mode.\nAt night it glares.", "why": "calm", "size": "m", "questions": []}


def test_a_draft_that_hit_a_refused_sign_in_waits_and_the_clock_drafts_it_once_signed_in(keeper):
    slug = ideas.add_idea(keeper.root, "dark mode", state_dir=keeper.state)
    ideas.save_state(keeper.state, slug, queue="now")
    keeper.call = Answers(login_error())
    keeper.draft_one(slug)
    st = ideas.state(keeper.state, slug)
    assert st["state"] == "raw" and st["error"] == "" and st["held_for"] == "sign_in" and st["held_until"]
    assert keeper.signins.entry("claude")["where"] == "ask"       # (draft_one on this thread; a run says "draft")
    assert keeper.held_for("claude") == 1
    assert keeper.tick(now=NOON) is False and ideas.state(keeper.state, slug)["held_for"] == "sign_in"
    keeper.call = Answers(DRAFT, {"tasks": []})
    tool_errors.ran("claude")
    keeper.tick(now=NOON + 100)
    until(lambda: not keeper.busy(slug) and ideas.state(keeper.state, slug)["state"] != "raw")
    st = ideas.state(keeper.state, slug)
    assert st["held_for"] == "" and st["held_until"] == "" and st["state"] != "raw"       # the hold lifted, drafted
    assert ideas.idea_page(keeper.root, slug).section("Gist").startswith("Dark mode.")


def test_a_plan_that_hit_a_refused_sign_in_waits_for_it(keeper):
    slug = ideas.add_idea(keeper.root, "dark mode", state_dir=keeper.state)
    keeper.call = Answers(DRAFT)
    ideas.save_state(keeper.state, slug, state="ready")
    keeper.call = Answers(login_error())
    keeper.plan_one(slug, "ready")
    st = ideas.state(keeper.state, slug)
    assert st["state"] == "ready" and st["error"] == "" and st["held_for"] == "sign_in" and st["held_until"]


def test_what_the_keeper_starts_by_itself_waits_while_the_tool_needs_its_sign_in(keeper):
    slug = ideas.add_idea(keeper.root, "dark mode", state_dir=keeper.state)
    login_error()
    assert keeper.hold(slug) is True
    assert ideas.state(keeper.state, slug)["held_for"] == "sign_in"
    assert keeper.draft(slug) is False                              # held, nothing called
    assert ideas.state(keeper.state, slug)["state"] == "raw"


def test_an_idea_held_a_day_fails_with_the_line(keeper):
    slug = ideas.add_idea(keeper.root, "dark mode", state_dir=keeper.state)
    ideas.save_state(keeper.state, slug, queue="now")
    keeper.call = Answers(login_error())
    keeper.draft_one(slug)
    past = dt.datetime.fromtimestamp(NOON - 60).isoformat(timespec="seconds")
    ideas.save_state(keeper.state, slug, held_until=past)
    keeper.tick(now=NOON)
    st = ideas.state(keeper.state, slug)
    assert st["held_for"] == "" and st["error"].startswith("Claude Code is not signed in")


def test_a_key_fails_the_draft_as_today(tmp_path):
    root, state = tmp_path / "wiki", tmp_path / ".orkcraft"
    signins, _ = fresh(tmp_path / "cfg", env={"ANTHROPIC_API_KEY": "k"})
    k = IdeaKeeper(tmp_path, state, lambda: root, lambda: {}, lambda slug: None, sign_ins=signins)
    slug = ideas.add_idea(root, "x", state_dir=state)
    k.call = Answers(login_error())
    k.draft_one(slug)
    st = ideas.state(state, slug)
    assert st["state"] == "raw" and st["held_for"] == "" and "not signed in" in st["error"]


@pytest.fixture
def ops(tmp_path, monkeypatch):
    stub = Stub(tmp_path, monkeypatch)
    signins, _ = fresh(tmp_path / "cfg")
    r = OpRunner(tmp_path / "ops", settings=lambda: settings.clean_ops({"servers": {"jira": "Atlassian"}}),
                 limits=lambda: [], sign_ins=signins)
    r.stub, r.signins = stub, signins
    yield r
    r.stop_all()
    r.wait_idle()


def test_an_operations_prepare_that_hit_a_refused_sign_in_is_held_and_goes_on(ops):
    ops.stub.answer(stream([], text=LOGIN, error=True), code=1)
    op_id = ops.add("jira-task", WHAT)
    run = wait_op(ops, op_id, "held")
    assert run["held"] == "prepare" and run["held_for"] == "sign_in" and ops.held_for("claude") == 1
    assert dt.datetime.fromisoformat(run["held_until"]) > dt.datetime.now() + dt.timedelta(hours=HOLD_H - 1)
    ops.tick(0)
    assert op_runs.load(ops.base, op_id)["state"] == "held"        # still signed out
    prepared(ops.stub)
    tool_errors.ran("claude")
    ops.tick(100)
    assert wait_op(ops, op_id, "check")["state"] == "check"
    assert op_runs.load(ops.base, op_id)["held_for"] in ("", None)


def test_an_operations_action_that_did_nothing_for_a_refused_sign_in_is_held_not_failed(ops):
    prepared(ops.stub)
    run = wait_op(ops, ops.add("jira-task", WHAT), "check")
    ops.stub.answer(stream([], text=LOGIN, error=True), code=1)
    ops.act(run["id"], {}, {})
    held = wait_op(ops, run["id"], "held")
    assert held["held"] == "act" and held["held_for"] == "sign_in" and held["acted"] is not True


def test_an_operations_run_held_a_day_fails_with_its_line(ops):
    ops.stub.answer(stream([], text=LOGIN, error=True), code=1)
    op_id = ops.add("jira-task", WHAT)
    run = wait_op(ops, op_id, "held")
    run["held_until"] = (dt.datetime.now() - dt.timedelta(minutes=1)).isoformat(timespec="seconds")
    op_runs.save(ops.base, run)
    ops.tick(0)
    failed = op_runs.load(ops.base, op_id)
    assert failed["state"] == "failed" and "not signed in" in failed["why"]


# -- the Map, the needs, the Check row (§7) -------------------------------------------------------------------------

def test_the_map_says_a_task_or_an_idea_waits_for_the_sign_in():
    until_ = "2026-10-21T10:00:00"
    held = {"needs_you": "", "held_until": "", "queue": "", "start_at": ""}
    task = {"state": "held", "held_for": "sign_in", "harness": "claude", "held_until": until_}
    got = board_map._waits(held, [task], {}, [])
    assert got == {"kind": "sign_in", "ref": "claude", "title": "Claude Code", "tool": "Claude Code", "until": until_}
    idea = {**held, "held_for": "sign_in", "held_until": until_}
    assert board_map._waits(idea, [], {}, [])["kind"] == "sign_in"
    limit = {**held, "held_until": until_}
    assert board_map._waits(limit, [], {}, [])["kind"] == "limits"                 # a window is as it was


def test_a_need_per_tool_that_needs_a_sign_in_and_holds_work():
    entries = [{"harness": "claude", "tool": "Claude Code", "state": "needed", "waiting": 3, "since": 1000.0},
               {"harness": "codex", "tool": "Codex", "state": "failed", "waiting": 0, "since": 1000.0}]
    [need] = board_map.sign_in_needs(entries)
    assert need["kind"] == "sign_in" and need["harness"] == "claude" and need["tool"] == "Claude Code"
    assert need["waiting"] == 3 and need["text"] == "Claude Code is not signed in, or its sign-in has expired."


def test_a_check_that_fails_for_the_sign_in_says_so_on_its_row(tmp_path):
    from orkboard.gui.onboarding import Onboarding
    s, _ = fresh(tmp_path)
    town = SimpleNamespace(machine=settings.load(), demo=False, call=lambda fn, *a: fn(*a))
    status = tools.ToolStatus(tools.TOOLS[0], found=True)
    asked = []

    def ask(tool, prompt, model=None):
        asked.append((tool, prompt, model))
        raise login_error(tool)

    ob = Onboarding(SimpleNamespace(town=town, on_change=lambda: None), detect=lambda: [status],
                    detect_others=lambda: [])
    ob._ask = ask
    ob.checks["claude"] = {"state": "running"}
    ob._check_run("claude")
    assert asked == [("claude", CHECK_PROMPT, "laborer")]
    row = ob.checks["claude"]
    assert row["state"] == "failed" and row["sign_in"] is True and row["kind"] == "login"
    assert s.entry("claude")["where"] == "check"                    # and no need: the Check adds none (no work waits)
    assert board_map.sign_in_needs(s.snapshot()) == []
    ob.checks["claude"] = {"state": "running"}
    ob._ask = lambda *a: (_ for _ in ()).throw(tool_errors.ToolError("claude", "429 rate limit", 1))
    ob._check_run("claude")
    assert ob.checks["claude"]["sign_in"] is False


# -- the commands, desktop only (§5) ---------------------------------------------------------------------------------

@pytest.fixture
def host(fake_repo):
    h = Orkboard(fake_repo)
    yield h
    h.close()


def test_the_commands_are_the_desktops_and_never_the_phones(host):
    for name in ("tools.sign_in", "tools.sign_in_cancel", "tools.sign_in_done"):
        assert name in host.commands and not BoardPhone.allowed(host, name, {"harness": "claude"})
    assert "sign_in" not in host.phone_snapshot()


def test_the_command_opens_the_tools_sign_in_and_refuses_an_unknown_or_missing_tool(host, tmp_path):
    spawn = Spawner()
    host.sign_ins._start = lambda harness, env, state_dir, **k: sign_in.start(
        harness, env, state_dir, "linux", lambda n: f"/bin/{n}", spawn, home=tmp_path)
    host.sign_ins._which = lambda n: f"/bin/{n}"
    assert host.snapshot()["sign_in"] == []
    login_error()
    [e] = host.snapshot()["sign_in"]
    assert e["state"] == "needed" and e["auto"] is True
    got = host.command("tools.sign_in", {"harness": "claude", "auto": True})
    assert got["state"] == "open" and got["auto"] is False and spawn.procs[0].argv == ["/bin/claude", "auth", "login"]
    again = host.command("tools.sign_in", {"harness": "claude", "auto": True})     # the second page: the entry as it is
    assert again["state"] == "open" and len(spawn.procs) == 1
    assert host.command("tools.sign_in_cancel", {"harness": "claude"})["why"] == "cancelled"
    with pytest.raises(CommandError, match="not one of the AI tools"):
        host.command("tools.sign_in", {"harness": "nobody"})
    host.sign_ins._which = lambda n: None
    with pytest.raises(CommandError, match="not found on this computer"):
        host.command("tools.sign_in", {"harness": "codex"})
    with pytest.raises(CommandError, match="Say which"):
        host.command("tools.sign_in", {})
    with pytest.raises(CommandError, match="true or false"):
        host.command("tools.sign_in", {"harness": "claude", "auto": "yes"})


def test_stop_all_cancels_an_open_sign_in_and_the_need_counts_what_waits(host, tmp_path):
    spawn = Spawner()
    host.sign_ins._start = lambda harness, env, state_dir, **k: sign_in.start(
        harness, env, state_dir, "linux", lambda n: f"/bin/{n}", spawn, home=tmp_path)
    host.sign_ins._which = lambda n: f"/bin/{n}"
    login_error()
    host.command("tools.sign_in", {"harness": "claude"})
    host.command("halt", {})
    assert spawn.procs[0].terminated and host.sign_ins.entry("claude")["why"] == "cancelled"
    host.sign_ins._waiting = lambda harness: 2
    board = host.command("ideas.board", {})
    need = next(n for n in board["needs_you"] if n["kind"] == "sign_in")
    assert need["waiting"] == 2 and need["blocks"] is True
    assert host.snapshot()["needs_you"] >= 1


def test_a_demo_watches_nothing(fake_repo):
    host = Orkboard(fake_repo, demo=True)
    login_error()
    assert host.snapshot()["sign_in"] == []
    host.close()
