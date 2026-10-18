"""Each model call is kept and charged where it belongs (docs/specs/37-board-and-line.md §8, 38 §1, §9): a project's
keeper and runner in that project's day log and ledger whether it is shown or not, Operations' in the person's folder,
concurrent calls of two projects and an operation each in their own place; Operations held by the person's cap."""
from __future__ import annotations

import datetime as dt
import json
import threading
from pathlib import Path

import pytest

from orkboard.core import treasury
from orkboard.gui.board_host import CommandError, Orkboard
from orkboard.realm import call_log, op_runs
from orkboard.sources import telemetry
from tests.ops_stub import Stub, stream

SECRET = "Zebra-Quokka invoice 4471"


@pytest.fixture
def stub(tmp_path, monkeypatch):
    return Stub(tmp_path, monkeypatch, mcp="Atlassian: https://mcp.atlassian.com/v1/sse - ✓ Connected\n")


@pytest.fixture
def two(tmp_path, fake_repo, stub):
    import shutil
    a, b = fake_repo, tmp_path / "other"
    shutil.copytree(fake_repo, b)
    host = Orkboard(a)
    host.projects.open(b, show=False)
    host.command("ops.set", {"servers": {"jira": "Atlassian"}})
    yield host, a, b
    host.ops.stop_all()
    host.ops.runner.wait_idle()
    host.close()


def _logged(root: Path) -> list[dict]:
    return [line for path in sorted((root / call_log.DAYS).rglob(call_log.LINES)) for line in call_log.read(path.parent)]


def test_two_projects_and_an_operation_calling_at_once_each_keep_their_own(two, stub):
    host, a, b = two
    assert host.repo_root == a                                   # `a` is shown; `b` is open, not shown
    result = stream([], text="{}", cost=0.25)[-1:]                # one JSON envelope: a read, a work, a call
    stub.answer(result, sleep=0.6, keep=True)                    # every call answers, slowly: they overlap
    keeper_a = host.projects._find(a).ideas.keeper
    runner_b = host.projects._find(b).ideas.runner(need=True)
    calls = [
        threading.Thread(target=lambda: keeper_a._claude("laborer", "sort the Board of a")),
        threading.Thread(target=lambda: runner_b._session("idea", "t1", b, threading.Event(), "",
                                                          {"ORKCRAFT_ORC": "ideas/idea-t1", "ORKCRAFT_TASK": "t1"},
                                                          "work in b", "", {"cost": None, "tokens": None})),
    ]
    for t in calls:
        t.start()
    op_id = host.command("ops.add", {"template": "jira-task", "fields": {"what": SECRET, "project": "ABC"}})["id"]
    for t in calls:
        t.join(15)
    assert host.ops.runner.wait_idle(15)
    assert len(stub.calls()) == 3

    in_a, in_b = _logged(a), _logged(b)
    assert [(x["who"], x["mode"]) for x in in_a] == [("keeper", "read")]
    assert [(x["who"], x["mode"]) for x in in_b] == [("idea-t1", "work")]
    today = dt.date.today().isoformat()
    assert call_log.read(call_log.day_folder(b, today, "ideas"))[0]["task"] == "t1"
    ops_lines = call_log.read(host.ops.base / "calls")
    assert [(x["side"], x["task"]) for x in ops_lines] == [("ops", op_id)]

    assert [(x["building"], x["usd"]) for x in telemetry.calls(a)] == [("board", 0.25)]
    assert [(x["building"], x["usd"]) for x in telemetry.calls(b)] == [("ideas", 0.25)]
    assert [x["building"] for x in telemetry.ledger_lines(op_runs.ledger(host.ops.base))] == ["ops"]
    for root in (a, b):                                          # nothing of the operation in a project
        text = "\n".join(p.read_text(errors="replace") for p in (root / ".orkcraft").rglob("*") if p.is_file()
                         and p.suffix != ".gz")
        assert SECRET not in text and op_id not in text and '"ops"' not in text


def test_a_call_no_one_placed_goes_to_the_shown_project_and_a_bench_block_wins(tmp_path):
    a, b, bench = tmp_path / "a", tmp_path / "b", tmp_path / "bench"
    call_log.keep_days(a)
    telemetry.keep_ledger(a)
    try:
        call_log.record({"ORKCRAFT_ORC": "board/keeper"}, "read", "claude", "", "p", "", "", 0, 1.0)
        telemetry.charge(0.1, "claude reader")
        with call_log.of_project(b):
            call_log.record({"ORKCRAFT_ORC": "board/keeper"}, "read", "claude", "", "p", "", "", 0, 1.0)
            telemetry.charge(0.2, "claude reader")
            with call_log.kept(bench / "calls", "building"):      # a Test bench's block: every call is its own
                call_log.record({"ORKCRAFT_ORC": "board/keeper"}, "read", "claude", "", "p", "", "", 0, 1.0)
        seen = []
        other = threading.Thread(target=lambda: seen.append(telemetry.ledger_now()))   # another thread: not placed
        with call_log.apart(tmp_path / "ops" / "calls", "ops", tmp_path / "ops" / "ledger.jsonl"):
            other.start()
            other.join()
            call_log.record({}, "call", "claude", "", "p", "", "", 0, 1.0)
            telemetry.charge(0.3, "claude call")
    finally:
        call_log.keep_days(None)
    assert len(_logged(a)) == 1 and len(_logged(b)) == 1 and len(call_log.read(bench / "calls")) == 1
    assert [x["usd"] for x in telemetry.calls(a)] == [0.1] and [x["usd"] for x in telemetry.calls(b)] == [0.2]
    assert seen == [telemetry.ledger_of(a)]
    assert [x["side"] for x in call_log.read(tmp_path / "ops" / "calls")] == ["ops"]
    assert [x["usd"] for x in telemetry.ledger_lines(tmp_path / "ops" / "ledger.jsonl")] == [0.3]


# -- the person's cap (spec 38 §1) -------------------------------------------------------------------------------------

def _spent(path: Path, usd: float, when: dt.datetime | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    at = (when or dt.datetime.now()).astimezone().isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": at, "building": "board", "usd": usd}) + "\n")


def _cap(root: Path, usd: float) -> None:
    (root / ".orkcraft.json").write_text(json.dumps({"budget": {"gold_session_limit_usd": usd}}), encoding="utf-8")


def test_the_persons_cap_is_the_smallest_of_the_open_projects_over_the_days_spend_of_all(two, stub):
    host, a, b = two
    _cap(a, 8.0)
    _cap(b, 5.0)
    _spent(telemetry.ledger_of(a), 2.0)
    _spent(telemetry.ledger_of(a), 9.0, dt.datetime.now() - dt.timedelta(days=1))    # yesterday's: not today's
    _spent(telemetry.ledger_of(b), 1.5)
    ledger = op_runs.ledger(host.ops.base)
    _spent(ledger, 1.0)
    assert host.persons_cap(ledger) == (4.5, 5.0) and not host.ops.runner.capped()
    _spent(ledger, 0.5)
    assert host.persons_cap(ledger) == (5.0, 5.0) and host.ops.runner.capped()
    with pytest.raises(CommandError, match="The day's spend cap is reached"):
        host.command("ops.add", {"template": "jira-task", "fields": {"what": "x", "project": "ABC"}})
    assert not stub.calls()
    host.projects.close(b)                                       # `a`'s cap is the smallest now
    assert host.persons_cap(ledger) == (3.5, 8.0) and not host.ops.runner.capped()


def test_with_no_project_open_the_cap_is_the_default(tmp_path):
    ledger = tmp_path / "ops" / "ledger.jsonl"
    _spent(ledger, 1.0)
    assert treasury.persons_cap([], ledger) == (1.0, treasury.GOLD_LIMIT_USD)
    root = tmp_path / "p"
    root.mkdir()
    _cap(root, 0)
    assert treasury.persons_cap([root], ledger) == (1.0, 0.0)    # a cap of 0 is none: nothing is held
