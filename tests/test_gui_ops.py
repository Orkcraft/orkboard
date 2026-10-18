"""Operations on Orkboard's host (docs/specs/38-operations.md §1, §8, §9, §11, Tests → A): one per host, its commands
with no project open, its rows in every project's Needs you, the phone, Stop all, and what stays private."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

from orkboard import settings
from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, op_runs
from tests.ops_stub import ARGS, Stub, mode, stream
from tests.test_op_runner import ACT, DONE, INIT, prepared

SECRET = "Zebra-Quokka invoice 4471"
WHAT = {"what": SECRET, "project": "ABC"}


@pytest.fixture
def stub(tmp_path, monkeypatch):
    return Stub(tmp_path, monkeypatch, mcp="Checking MCP server health…\n\nAtlassian: https://mcp.atlassian.com/v1/sse "
                "- ✓ Connected\nclaude.ai Gmail: https://gmail.mcp.claude.com/mcp - ✓ Connected\n")


def connected(host: Orkboard) -> Orkboard:
    host.command("ops.set", {"servers": {"jira": "Atlassian", "gmail": "claude.ai Gmail"}})
    return host


@pytest.fixture
def host(fake_repo, stub):
    h = connected(Orkboard(fake_repo))
    yield h
    h.ops.stop_all()
    h.ops.runner.wait_idle()
    h.close()


def wait(host, op_id, *states, timeout=10.0) -> dict:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        run = op_runs.load(host.ops.base, op_id)
        if run and run["state"] in states and op_id not in host.ops.runner.running():
            return run
        time.sleep(0.02)
    raise AssertionError(f"{op_id}: {op_runs.load(host.ops.base, op_id)}")


def checked(host, stub, fields=WHAT, **kw) -> dict:
    prepared(stub, draft={"summary": f"Pay the {SECRET}", "description": SECRET}, **kw)
    return wait(host, host.command("ops.add", {"template": "jira-task", "fields": fields})["id"], "check", "failed")


# -- one per host ---------------------------------------------------------------------------------------------

def test_operations_is_the_hosts_and_works_with_no_project_open(stub):
    host = connected(Orkboard(None))
    assert host.project is None and "ops.add" in host.commands
    with pytest.raises(CommandError, match="Open a folder first"):
        host.command("ideas.board")
    listed = host.command("ops.list")
    assert set(listed) == {"templates", "runs", "settings", "servers_needed"}
    assert listed["servers_needed"] == {"jira": "Jira", "gmail": "Gmail"}
    jira = next(t for t in listed["templates"] if t["name"] == "jira-task")
    assert {"name", "title", "risk", "fields", "draft", "act_label", "state", "clean"} <= set(jira)
    assert jira["state"] == "checks" and "unusable" not in jira and jira["act_label"] == "Create in Jira"
    run = checked(host, stub)
    assert run["state"] == "check" and host.snapshot()["needs_you"] == 1
    row = next(r for r in host.command("ops.list")["runs"] if r["id"] == run["id"])
    assert {"id", "template", "state", "title", "found", "draft", "fields", "doubts", "alone", "link", "why", "acted",
            "held_until", "cost", "at"} <= set(row) and row["title"] == "New Jira task"
    host.ops.runner.wait_idle()


def test_showing_another_project_changes_nothing_of_it(fake_repo, stub, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=other, check=True)
    host = connected(Orkboard(fake_repo))
    ops = host.ops
    run = checked(host, stub)
    host.projects.open(other)
    assert host.ops is ops and host.repo_root == other.resolve()
    needs = host.command("ideas.board")["needs_you"]
    assert [n["kind"] for n in needs] == ["op"] and needs[0]["op"] == run["id"]
    assert needs[0]["text"] == f"Pay the {SECRET}" and needs[0]["title"] == "New Jira task"
    host.projects.use(fake_repo)
    assert [n["op"] for n in host.command("ideas.board")["needs_you"] if n["kind"] == "op"] == [run["id"]]
    host.close()


def test_a_template_not_connected_says_so_and_cannot_be_added_from(fake_repo, stub):
    host = Orkboard(fake_repo)
    jira = next(t for t in host.command("ops.list")["templates"] if t["name"] == "jira-task")
    assert jira["unusable"] == "Jira is not connected: add its MCP server to Claude Code, then pick it here"
    with pytest.raises(CommandError, match="Jira is not connected"):
        host.command("ops.add", {"template": "jira-task", "fields": WHAT})


def test_without_claude_code_operations_says_so_and_adds_nothing(fake_repo, monkeypatch):
    monkeypatch.setenv("ORKCRAFT_CLAUDE_BIN", "/nonexistent/claude")
    host = connected(Orkboard(fake_repo))
    jira = next(t for t in host.command("ops.list")["templates"] if t["name"] == "jira-task")
    assert jira["unusable"] == "Operations run on Claude Code, which is not installed here"
    with pytest.raises(CommandError, match="not installed"):
        host.command("ops.add", {"template": "jira-task", "fields": WHAT})
    assert not op_runs.runs(host.ops.base)


# -- Needs you (§8) ----------------------------------------------------------------------------------------------

def test_needs_you_has_op_op_failed_and_op_rules_last_and_out_of_the_count(host, stub):
    run = checked(host, stub)
    stub.answer(stream(INIT, uses=[(ACT, ARGS)], text=DONE))
    stub.answer(stream([], text=json.dumps({"rules": ["Titles start with a verb"], "why": "x"})))
    host.command("ops.act", {"id": run["id"], "draft": {"summary": "Corrected"}})
    wait(host, run["id"], "done")
    host.ops.runner.wait_idle()
    failed = checked(host, stub, tools=["nothing"])
    waiting = checked(host, stub)
    rev = host.snapshot()["ops_rev"]
    kinds = [n["kind"] for n in host.command("ideas.board")["needs_you"]]
    assert sorted(kinds[:2]) == ["op", "op_failed"] and kinds[-1] == "op_rules"
    rules = next(n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "op_rules")
    assert rules["lines"] == ["Titles start with a verb"] and rules["op"] == run["id"]
    assert host.snapshot()["needs_you"] == 2 and host.phone_snapshot()["needs_you"] == 2
    host.command("ops.drop", {"id": failed["id"]})
    host.command("ops.drop", {"id": waiting["id"]})
    assert host.snapshot()["ops_rev"] > rev and host.snapshot()["needs_you"] == 0
    assert "ops_rev" in host.phone_snapshot()
    host.command("ops.rules_answer", {"template": "jira-task", "take": True})
    jira = next(t for t in host.command("ops.list")["templates"] if t["name"] == "jira-task")
    assert jira["state"] == "alone" and jira["state_words"] == "goes by itself" and "proposal" not in jira


# -- the phone and Stop all ------------------------------------------------------------------------------------------

def test_the_phone_may_send_every_ops_command(host):
    names = [n for n in host.commands if n.startswith("ops.")]
    assert len(names) == 15 and all(BoardPhone.allowed(host, n, {}) for n in names)
    assert not BoardPhone.allowed(host, "ops.nothing", {})
    assert BoardPhone.guard("ops.add", {"template": "jira-task"})["device"] == "phone"


def test_the_phones_add_says_the_phone(host, stub):
    prepared(stub)
    op_id = host.command("ops.add", BoardPhone.guard("ops.add", {"template": "jira-task", "fields": WHAT}))["id"]
    assert wait(host, op_id, "check")["device"] == "phone"
    added = [json.loads(x) for x in (host.ops.base / "events.jsonl").read_text().splitlines()]
    assert added[0]["event"] == "op_added" and added[0]["device"] == "phone"


def test_stop_all_stops_a_running_operation(host, stub):
    run = checked(host, stub)
    stub.answer(stream(INIT, uses=[(ACT, ARGS)], text=DONE), sleep=20)
    host.command("ops.act", {"id": run["id"]})
    end = time.monotonic() + 10
    while len(stub.calls()) < 2 and time.monotonic() < end:
        time.sleep(0.02)
    host.command("halt")
    stopped = wait(host, run["id"], "failed")
    assert stopped["acted"] is None and "look in Jira" in stopped["why"]


# -- the settings and the gear -----------------------------------------------------------------------------------------

def test_ops_set_checks_and_keeps_the_persons_settings(host):
    got = host.command("ops.set", {"target": "quality", "trust_after": 3, "daily_alone": 50})
    assert got["target"] == "quality" and got["trust_after"] == 3 and got["daily_alone"] == 50
    assert settings.load().ops["trust_after"] == 3 and settings.load().ops["servers"]["jira"] == "Atlassian"
    for bad, words in (({"target": "max"}, "thrift, balance or quality"), ({"trust_after": 9}, "1 to 5"),
                       ({"daily_alone": 0}, "1 to 100")):
        with pytest.raises(CommandError, match=words):
            host.command("ops.set", bad)
    assert host.command("ops.set", {"servers": {"gmail": ""}})["servers"] == {"jira": "Atlassian"}


def test_the_gear_lists_the_servers_claude_mcp_list_prints(host):
    assert host.command("ops.servers") == {"servers": ["Atlassian", "claude.ai Gmail"]}


def test_the_rules_are_the_persons_to_read_and_save(host):
    before = op_runs.trust(host.ops.base, "jira-task")
    op_runs.save_trust(host.ops.base, "jira-task", before)
    host.command("ops.rules_save", {"template": "jira-task", "text": "# Titles\n- start with a verb\n"})
    assert host.command("ops.rules", {"template": "jira-task"}) == {"text": "### Titles\n- start with a verb\n"}
    assert op_runs.trust(host.ops.base, "jira-task") == before
    with pytest.raises(CommandError, match="longer than 4000"):
        host.command("ops.rules_save", {"template": "jira-task", "text": "x" * 4001})


# -- what stays private (§9) -------------------------------------------------------------------------------------------

def _texts(folder: Path) -> str:
    out = []
    for p in folder.rglob("*"):
        if p.is_file() and ".git" not in p.relative_to(folder).parts[:1]:
            data = p.read_bytes()
            if p.suffix == ".gz":
                import gzip
                data = gzip.decompress(data)
            out.append(data.decode("utf-8", errors="replace"))
    return "\n".join(out)


def test_nothing_of_an_operation_lands_in_the_project(host, stub, fake_repo):
    run = checked(host, stub)
    stub.answer(stream(INIT, uses=[(ACT, ARGS)], text=DONE))
    host.command("ops.act", {"id": run["id"]})
    assert wait(host, run["id"], "done")["state"] == "done"
    assert SECRET not in _texts(fake_repo)                           # nor its .orkcraft/logs/ nor its event log
    assert not [r for r in event_log.read(fake_repo) if r["event"].startswith("op_")]
    calls = host.ops.base / "calls"
    assert SECRET in _texts(calls) and len(op_runs.lines(calls / "calls.jsonl")) == 2
    for p in host.ops.base.rglob("*"):
        if p.is_file() and p.parent.name != "calls":
            assert mode(p) == 0o600, p
    assert mode(host.ops.base) == 0o700
    assert SECRET not in (host.ops.base / "events.jsonl").read_text()
    assert host.ops.base == settings.path().parent / "ops" and fake_repo not in host.ops.base.parents


def test_after_keep_days_its_texts_and_calls_are_gone_and_its_row_stays(host, stub):
    run = checked(host, stub)
    stub.answer(stream(INIT, uses=[(ACT, ARGS)], text=DONE))
    host.command("ops.act", {"id": run["id"]})
    done = wait(host, run["id"], "done")
    old = {**done, "done_at": "2026-01-01T10:00:00", "at": "2026-01-01T09:00:00"}
    op_runs.save(host.ops.base, old)
    host.ops.runner._forgot = ""
    host.ops.runner.forget()
    kept = op_runs.load(host.ops.base, run["id"])
    assert set(kept) == set(op_runs.KEPT_KEYS) and kept["link"] == done["link"]
    assert SECRET not in _texts(host.ops.base)
    row = next(r for r in host.command("ops.list")["runs"] if r["id"] == run["id"])
    assert row["state"] == "done" and row["fields"] == {} and row["link"]
