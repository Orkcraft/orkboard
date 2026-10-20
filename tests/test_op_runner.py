"""Operations' runner against a stub `claude` printing stream-json (docs/specs/38-operations.md §3–§7, Tests → A): the
prepare's and the action's command lines and prompts, what code reads of their events, the way to by itself through
the runner, the learn call, the limits and the queue."""
from __future__ import annotations

import datetime as dt
import json
import shutil
import threading
import time

import pytest

from orkboard import settings
from orkboard.core.op_commands import OpsError
from orkboard.core.op_runner import MAX_PARALLEL, OpRunner
from orkboard.realm import harnesses, idea_target, op_runs, op_templates
from orkboard.sources.limits import Limit
from tests.ops_stub import ARGS, Stub, mode, stream

PREP = [f"mcp__Atlassian__{n}" for n in ("getAccessibleAtlassianResources", "getVisibleJiraProjects",
                                          "searchJiraIssuesUsingJql", "getJiraIssue")]
ACT = "mcp__Atlassian__createJiraIssue"
INIT = [*PREP, ACT, "mcp__Atlassian__editJiraIssue"]
WHAT = {"what": "Checkout fails on Safari", "project": "ABC", "epic": "Checkout"}
DONE = '{"id": "ABC-141", "link": "https://acme.atlassian.net/browse/ABC-141"}'


@pytest.fixture
def stub(tmp_path, monkeypatch):
    return Stub(tmp_path, monkeypatch)


@pytest.fixture
def runner(tmp_path, stub):
    box = {"ops": settings.clean_ops({"servers": {"jira": "Atlassian", "gmail": "Gmail"}}), "limits": []}
    r = OpRunner(tmp_path / "ops", settings=lambda: box["ops"], limits=lambda: box["limits"])
    r.box = box
    yield r
    r.stop_all()
    r.wait_idle()


def prepared(stub, args=None, draft=None, found=(), doubts=(), tools=INIT, **answer) -> None:
    body = {"args": {"cloudId": "c1", "projectKey": "ABC"} if args is None else args,
            "draft": {"summary": "Fix the checkout on Safari", "description": "Why: …"} if draft is None else draft,
            "found": list(found), "doubts": list(doubts), **answer}
    stub.answer(stream(tools, text=json.dumps(body)))


def wait(runner, op_id, *states, timeout=10.0) -> dict:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        run = op_runs.load(runner.base, op_id)
        if run and run["state"] in states and op_id not in runner.running():
            return run
        time.sleep(0.02)
    raise AssertionError(f"{op_id} never reached {states}: {op_runs.load(runner.base, op_id)}")


def at_check(runner, stub, **kw) -> dict:
    prepared(stub, **kw)
    return wait(runner, runner.add("jira-task", WHAT), "check", "acting", "done", "failed")


def flag(argv, name):
    return argv[argv.index(name) + 1] if name in argv else None


# -- the prepare ----------------------------------------------------------------------------------------------

def test_the_prepares_command_allows_only_its_tools_in_the_empty_folder(runner, stub):
    run = at_check(runner, stub)
    call = stub.calls()[0]
    argv = call["argv"]
    assert flag(argv, "--allowedTools").split(",") == PREP and ACT not in flag(argv, "--allowedTools")
    assert flag(argv, "--disallowedTools") == harnesses.CLAUDE_NO_TOOLS
    assert flag(argv, "--output-format") == "stream-json" and "--resume" not in argv
    assert call["cwd"] == str(runner.base / "work") and call["task"] == run["id"]
    assert flag(argv, "--effort") == "medium" and flag(argv, "--max-budget-usd") == "0.30"
    assert "--no-session-persistence" in argv and flag(argv, "--model") == "sonnet"      # balance: warrior · medium


def test_the_flags_go_only_when_the_cli_lists_them(tmp_path, monkeypatch):
    stub = Stub(tmp_path, monkeypatch, help="Usage: claude [options]")
    r = OpRunner(tmp_path / "ops", settings=lambda: {"servers": {"jira": "Atlassian"}})
    prepared(stub)
    wait(r, r.add("jira-task", WHAT), "check")
    argv = stub.calls()[0]["argv"]
    assert not {"--effort", "--max-budget-usd", "--no-session-persistence"} & set(argv)


def test_the_prompt_holds_the_skill_its_rules_and_the_fields_within_its_cap(runner, stub):
    op_runs.take_rules(runner.base, "jira-task", ["A title starts with the component in brackets"])
    at_check(runner, stub)
    prompt = flag(stub.calls()[0]["argv"], "-p")
    skill = op_templates.skill_body(op_templates.find()["jira-task"])
    assert "name: jira-task" not in prompt and skill.splitlines()[0] in prompt
    assert "A title starts with the component in brackets" in prompt and "Checkout fails on Safari" in prompt
    assert "Use only the tools listed; change nothing; put into doubts" in prompt
    from orkboard.core.op_runner import PREPARE_LINE
    assert len(prompt) <= idea_target.CONTEXT["op_prepare"] + len(PREPARE_LINE)
    runner.wait_idle()
    big = {**WHAT, "what": "x" * 4000}
    op_runs.save_rules(runner.base, "jira-task", "- rule\n" * 600)
    prepared(stub)
    wait(runner, runner.add("jira-task", big), "check")
    assert len(flag(stub.calls()[1]["argv"], "-p")) <= idea_target.CONTEXT["op_prepare"] + len(PREPARE_LINE)


def test_a_tool_missing_from_init_fails_it_before_any_answer_is_read(runner, stub):
    run = at_check(runner, stub, tools=PREP)                     # the action's tool is not on the server
    assert run["state"] == "failed" and run["acted"] is False and run["draft"] == {}
    assert run["why"] == "Jira's server has no createJiraIssue: check the server picked in Operations' gear"


def test_the_answer_is_kept_as_its_keys_cut_and_every_at_written(runner, stub):
    found = [{"label": f"L{n}", "value": "v" * 400} for n in range(9)]
    run = at_check(runner, stub, found=found, doubts=[f"d{n}" for n in range(8)], extra={"x": 1},
                   draft={"summary": "Fix it", "description": "Why", "other": "dropped"})
    assert run["state"] == "check" and set(run["draft"]) == {"summary", "description"}
    assert len(run["found"]) == 6 and len(run["found"][0]["value"]) == 300 and len(run["doubts"]) == 5
    assert run["args"] == {"cloudId": "c1", "projectKey": "ABC", "summary": "Fix it", "description": "Why",
                           "issueTypeName": "Task", "additional_fields": {"priority": {"name": "Medium"}}}
    assert "extra" not in run


def test_no_json_fails_it_with_nothing_done(runner, stub):
    stub.answer(stream(INIT, text="I could not do it"))
    run = wait(runner, runner.add("jira-task", WHAT), "failed")
    assert run["acted"] is False and run["why"] == "the answer was not the JSON it was asked for"
    prepared(stub)
    runner.retry(run["id"])                                      # nothing was done: Try again
    assert wait(runner, run["id"], "check")["state"] == "check"


def test_the_form_is_checked_on_add(runner):
    with pytest.raises(OpsError, match="What needs doing is needed"):
        runner.add("jira-task", {"project": "ABC"})
    with pytest.raises(OpsError, match="Priority is one of"):
        runner.add("jira-task", {**WHAT, "priority": "Urgent"})
    with pytest.raises(OpsError, match="That template is gone"):
        runner.add("nothing", WHAT)


def test_a_template_not_connected_or_broken_cannot_be_added_from(runner, tmp_path):
    runner.box["ops"] = settings.clean_ops({"servers": {}})
    with pytest.raises(OpsError, match="Jira is not connected: add its MCP server to Claude Code"):
        runner.add("jira-task", WHAT)
    folder = tmp_path / "home" / ".claude" / "skills" / "broken"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text("# x\n")
    (folder / "orkboard.toml").write_text('title = "Broken"\nrisk = "wild"\n')
    with pytest.raises(OpsError, match="Broken cannot be used: its risk is low, medium or high"):
        runner.add("broken", {})


def test_remember_prefills_the_last_value(runner, stub):
    at_check(runner, stub)
    run = at_check(runner, stub)
    assert run["fields"]["project"] == "ABC"
    prepared(stub)
    other = wait(runner, runner.add("jira-task", {"what": "Another"}), "check")
    assert other["fields"]["project"] == "ABC"


# -- the action ---------------------------------------------------------------------------------------------------

def act(runner, stub, run, uses, text=DONE, fields=None, draft=None, rules=None, **kw) -> dict:
    stub.answer(stream([*INIT], uses=uses, text=text, **kw))
    if rules is not None:                                        # the learn call's answer, after the action's
        stub.answer(stream([], text=json.dumps({"rules": rules, "why": "made general"})))
    runner.act(run["id"], fields or {}, draft or {})
    return wait(runner, run["id"], "done", "failed")


def test_the_action_allows_only_its_tool_and_one_equal_call_is_done(runner, stub):
    run = at_check(runner, stub)
    done = act(runner, stub, run, [(ACT, ARGS)])
    argv = stub.calls()[-1]["argv"]
    assert flag(argv, "--allowedTools") == ACT and flag(argv, "--disallowedTools") == harnesses.CLAUDE_NO_TOOLS
    assert flag(argv, "--model") == "haiku" and "--effort" not in argv          # the laborer tier: no effort
    assert done["state"] == "done" and done["done_id"] == "ABC-141" and done["acted"] is True
    assert done["link"] == "https://acme.atlassian.net/browse/ABC-141" and done["cost"] == pytest.approx(0.02)


def test_a_link_that_is_not_web_is_none(runner, stub):
    run = at_check(runner, stub)
    assert act(runner, stub, run, [(ACT, ARGS)], text='{"id": "1", "link": "javascript:alert(1)"}')["link"] == ""


def test_no_call_is_nothing_done_and_it_may_be_tried_again(runner, stub):
    run = at_check(runner, stub)
    failed = act(runner, stub, run, [])
    assert failed["acted"] is False and failed["why"] == "nothing was done" and failed["step"] == "act"
    stub.answer(stream(INIT, uses=[(ACT, ARGS)], text=DONE))
    runner.retry(run["id"])
    assert wait(runner, run["id"], "done", "failed")["state"] == "done"


@pytest.mark.parametrize("uses", [[(ACT, {"summary": "other"})], [("mcp__Atlassian__editJiraIssue", ARGS)],
                                  [(ACT, ARGS), (ACT, ARGS)]], ids=["other input", "another tool", "two calls"])
def test_anything_but_exactly_what_was_checked_is_acted_and_never_tried_again(runner, stub, uses):
    run = at_check(runner, stub)
    failed = act(runner, stub, run, uses)
    assert failed["state"] == "failed" and failed["acted"] is True
    assert failed["why"] == "it did not do exactly what was checked: look in Jira"
    with pytest.raises(OpsError, match="add it again"):
        runner.retry(run["id"])
    again = runner.again(run["id"])                              # the person's knowing press: a new one
    assert again != run["id"] and op_runs.load(runner.base, again)["fields"] == failed["fields"]


def test_a_tool_error_fails_it_with_its_first_line(runner, stub):
    run = at_check(runner, stub)
    failed = act(runner, stub, run, [(ACT, ARGS, True, "\nField 'priority' cannot be set\nmore")])
    assert failed["acted"] is True and failed["why"] == "Field 'priority' cannot be set"


def test_stop_while_acting_may_have_acted(runner, stub):
    run = at_check(runner, stub)
    stub.answer(stream(INIT, uses=[(ACT, ARGS)], text=DONE), sleep=20)
    runner.act(run["id"], {}, {})
    end = time.monotonic() + 10
    while len(stub.calls()) < 2 and time.monotonic() < end:
        time.sleep(0.02)
    runner.stop(run["id"])
    failed = wait(runner, run["id"], "failed")
    assert failed["acted"] is None and failed["why"] == "stopped while doing it: look in Jira before you add it again"


def test_stop_while_preparing_fails_it_with_nothing_done(runner, stub):
    prepared(stub)
    stub.answer(stream(INIT, text="{}"), sleep=20)
    stub.calls()
    (stub.dir / "answers" / "0001.json").unlink()                # the slow one comes first
    op_id = runner.add("jira-task", WHAT)
    end = time.monotonic() + 10
    while not stub.calls() and time.monotonic() < end:
        time.sleep(0.02)
    runner.stop(op_id)
    failed = wait(runner, op_id, "failed")
    assert failed["acted"] is False and failed["why"] == "stopped"


def test_a_correction_without_at_needs_prepare_again(runner, stub):
    run = at_check(runner, stub)
    with pytest.raises(OpsError, match="Epic changed: Prepare again first"):
        runner.act(run["id"], {"epic": "Payments"}, {})
    prepared(stub, draft={"summary": "New title", "description": "New"})
    runner.prepare_again(run["id"], {"epic": "Payments"}, {"summary": "Mine"})
    again = wait(runner, run["id"], "check")
    assert again["fields"]["epic"] == "Payments" and again["draft"] == {"summary": "Mine", "description": "New"}
    assert again["args"]["summary"] == "Mine" and again["edited"] == ["epic", "summary"]


# -- by itself, through the runner (§6) -------------------------------------------------------------------------

def trust(runner) -> dict:
    return op_runs.trust(runner.base, "jira-task")


def test_a_clean_check_sends_it_by_itself_and_the_next_one_goes_without_asking(runner, stub):
    act(runner, stub, at_check(runner, stub), [(ACT, ARGS)])
    assert trust(runner)["alone"] and trust(runner)["why"] == "clean"
    prepared(stub)
    stub.answer(stream(INIT, uses=[(ACT, ARGS)], text=DONE))
    done = wait(runner, runner.add("jira-task", WHAT), "done", "failed")
    assert done["state"] == "done" and done["alone"] is True
    assert trust(runner)["today"]["alone_done"] == 1
    assert trust(runner)["done_alone"] == 1 and trust(runner)["alone_since"] != ""             # spec 42 §5: since the day it went, one done


def test_three_clean_checks_when_trust_after_is_three(runner, stub):
    runner.box["ops"] = settings.clean_ops({**runner.box["ops"], "trust_after": 3})
    for n in range(3):
        assert not trust(runner)["alone"]
        act(runner, stub, at_check(runner, stub), [(ACT, ARGS)])
        assert trust(runner)["clean"] == n + 1
    assert trust(runner)["alone"]


def test_a_correction_sends_it_back_and_the_learn_call_proposes_rules(runner, stub):
    act(runner, stub, at_check(runner, stub), [(ACT, ARGS)])
    assert trust(runner)["alone"]
    op_runs.decline(runner.base, "jira-task", ["Never write please"], "")
    run = at_check(runner, stub, doubts=["maybe ABC-140"])       # a doubt: it stops at the check, trust unchanged
    assert run["state"] == "check" and run["why"] == "at your check · a doubt" and trust(runner)["alone"]
    act(runner, stub, run, [(ACT, ARGS)], draft={"summary": "[Checkout] Fix Safari"}, fields={"priority": "High"},
        rules=["A title starts with the component in brackets: [Checkout] …", "Never write please"])
    runner.wait_idle()
    assert not trust(runner)["alone"] and trust(runner)["why"] == "edit" and trust(runner)["clean"] == 0
    learn = stub.calls()[-1]["argv"]
    assert "--allowedTools" not in learn and flag(learn, "--disallowedTools") == harnesses.CLAUDE_NO_TOOLS
    prompt = flag(learn, "-p")
    assert "'Fix the checkout on Safari' → '[Checkout] Fix Safari'" in prompt and "'Medium' → 'High'" in prompt
    assert "Never write please" in prompt                        # the declined, so it is not proposed again
    got = op_runs.proposal(runner.base, "jira-task")
    assert got["lines"] == ["A title starts with the component in brackets: [Checkout] …"] and got["op"] == run["id"]
    runner.rules_answer("jira-task", take=True)
    assert trust(runner)["alone"] and trust(runner)["why"] == "rules"
    assert "[Checkout]" in op_runs.rules(runner.base, "jira-task") and op_runs.proposal(runner.base, "jira-task") is None


def test_no_to_the_rules_keeps_it_checking(runner, stub):
    run = at_check(runner, stub)
    act(runner, stub, run, [(ACT, ARGS)], draft={"summary": "Other"}, rules=["Titles in English"])
    runner.wait_idle()
    runner.rules_answer("jira-task", take=False, reason="no")
    assert not trust(runner)["alone"] and op_runs.declined(runner.base, "jira-task")[-1]["lines"] == ["Titles in English"]


def test_not_right_sends_it_back_and_teaches(runner, stub):
    act(runner, stub, at_check(runner, stub), [(ACT, ARGS)])
    prepared(stub)
    stub.answer(stream(INIT, uses=[(ACT, ARGS)], text=DONE))
    done = wait(runner, runner.add("jira-task", WHAT), "done")
    stub.answer(stream([], text=json.dumps({"rules": [], "why": "nothing general"})))
    runner.not_right(done["id"], "the epic was wrong")
    runner.wait_idle()
    assert not trust(runner)["alone"] and trust(runner)["why"] == "not_right"
    assert "the epic was wrong" in flag(stub.calls()[-1]["argv"], "-p")
    assert op_runs.proposal(runner.base, "jira-task") is None     # nothing general: the clean checks do it
    with pytest.raises(OpsError, match="went by itself"):
        runner.not_right(at_check(runner, stub)["id"])          # at the check: it did not go by itself


def test_a_new_version_and_check_again_send_it_back(runner, stub, tmp_path):
    home = tmp_path / "home" / ".claude" / "skills" / "jira-task"
    shutil.copytree(op_templates.BUILTIN / "jira-task", home)
    act(runner, stub, at_check(runner, stub), [(ACT, ARGS)])
    assert trust(runner)["alone"]
    (home / "SKILL.md").write_text((home / "SKILL.md").read_text() + "\nOne more line.\n")
    assert at_check(runner, stub)["state"] == "check" and trust(runner)["why"] == "version"
    op_runs.save_trust(runner.base, "jira-task", op_runs.after_rules(trust(runner)))
    runner.trust_reset("jira-task")
    assert not trust(runner)["alone"] and trust(runner)["why"] == "reset"


def test_a_high_risk_and_the_days_cap_stop_it_without_changing_its_trust(runner, stub, tmp_path):
    home = tmp_path / "home" / ".claude" / "skills" / "jira-task"
    shutil.copytree(op_templates.BUILTIN / "jira-task", home)
    act(runner, stub, at_check(runner, stub), [(ACT, ARGS)])
    runner.box["ops"] = settings.clean_ops({**runner.box["ops"], "daily_alone": 1})
    today = dt.date.today().isoformat()
    op_runs.save_trust(runner.base, "jira-task", op_runs.after_alone(trust(runner), today))
    before = (runner.base / "templates" / "jira-task" / "trust.json").read_text()
    run = at_check(runner, stub)
    assert run["state"] == "check" and run["why"] == "checks again today: 1 done by itself"
    toml = home / "orkboard.toml"
    toml.write_text(toml.read_text().replace('risk = "medium"', 'risk = "high"'))
    trust_now = op_runs.after_version(op_runs.trust(runner.base, "jira-task"),
                                      op_templates.read(home).version)
    op_runs.save_trust(runner.base, "jira-task", {**trust_now, "alone": True})
    before = (runner.base / "templates" / "jira-task" / "trust.json").read_text()
    run = at_check(runner, stub)
    assert run["state"] == "check" and run["why"] == "always checks with you"
    assert (runner.base / "templates" / "jira-task" / "trust.json").read_text() == before


# -- the limits and the queue (§1) -----------------------------------------------------------------------------------

def test_a_spent_window_holds_the_prepare_until_it_is_back(runner, stub):
    soon = dt.datetime.now() + dt.timedelta(hours=1)
    runner.box["limits"] = [Limit("claude", "", "session", 0.02, soon)]
    op_id = runner.add("jira-task", WHAT)
    held = wait(runner, op_id, "held")
    assert held["held_until"] == soon.isoformat(timespec="seconds") and not stub.calls()
    runner.tick(0)
    assert op_runs.load(runner.base, op_id)["state"] == "held"
    runner.box["limits"] = [Limit("claude", "", "session", 0.2, soon)]   # below the day's reserve: no reserve here
    prepared(stub)
    runner.tick(100)
    assert wait(runner, op_id, "check")["state"] == "check"


def test_at_most_two_run_at_once(runner, stub):
    stub.answer(stream(INIT, text="{}"), sleep=0.6, keep=True)
    ids = [runner.add("jira-task", WHAT) for _ in range(3)]
    most = 0
    end = time.monotonic() + 10
    while time.monotonic() < end and not runner.wait_idle(0.01):
        most = max(most, len(runner.running()))
    assert most == MAX_PARALLEL == 2
    assert all(op_runs.load(runner.base, i)["state"] == "check" for i in ids)


def test_what_the_host_lost_is_prepared_again_or_failed_as_maybe_done(tmp_path, stub):
    base = tmp_path / "ops"
    lost_prep = op_runs.blank("op-lost-1", "jira-task", "v", WHAT)
    lost_act = {**op_runs.blank("op-lost-2", "jira-task", "v", WHAT), "state": "acting"}
    op_runs.save(base, lost_prep)
    op_runs.save(base, lost_act)
    prepared(stub)
    r = OpRunner(base, settings=lambda: {"servers": {"jira": "Atlassian"}})
    r.start()
    assert wait(r, "op-lost-1", "check")["state"] == "check"
    gone = op_runs.load(base, "op-lost-2")
    assert gone["state"] == "failed" and gone["acted"] is None and "look in Jira" in gone["why"]


def test_each_call_has_its_ledger_line_and_its_events_hold_no_text(runner, stub):
    act(runner, stub, at_check(runner, stub), [(ACT, ARGS)])
    lines = op_runs.lines(runner.base / "spend.jsonl")
    assert [line["step"] for line in lines] == ["op_prepare", "op_act"] and lines[0]["template"] == "jira-task"
    assert lines[0]["cost"] == 0.01 and lines[0]["tokens"]["in"] == 100 and lines[0]["op"]
    events = (runner.base / "events.jsonl").read_text()
    assert [json.loads(x)["event"] for x in events.splitlines()] == [
        "op_added", "op_prepared", "op_checked", "op_done", "op_trust"]
    assert "Safari" not in events and "Checkout" not in events


# -- the person's cap (§1) and a learn call held across a restart (§7) ----------------------------------------------

CAP_WORDS = "The day's spend cap is reached"


def test_the_days_spend_cap_holds_the_call_and_refuses_the_persons_press(runner, stub):
    reads = []
    runner.cap = lambda: reads.append(1) or ((0.0, 10.0) if len(reads) == 1 else runner.box["spent"])
    runner.box["spent"] = (10.5, 10.0)
    op_id = runner.add("jira-task", WHAT)                         # the press passed; the call waits at its start
    held = wait(runner, op_id, "held")
    assert held["why"] == "waits: the day's spend cap is reached" and held["held"] == "prepare" and not stub.calls()
    assert held["held_until"].endswith("T00:00:00")                # the day's spend starts again at midnight
    with pytest.raises(OpsError, match=CAP_WORDS) as refused:
        runner.add("jira-task", WHAT)
    assert "$10.50 of $10.00" in str(refused.value)
    runner.tick(0)
    assert op_runs.load(runner.base, op_id)["state"] == "held" and not stub.calls()
    runner.box["spent"] = (3.0, 10.0)                             # the cap raised (or a new day)
    prepared(stub)
    runner.tick(100)
    run = wait(runner, op_id, "check")
    assert run["state"] == "check" and run["why"] == ""
    runner.box["spent"] = (10.0, 10.0)
    for press in (lambda: runner.act(op_id, {}, {}), lambda: runner.prepare_again(op_id, {}, {})):
        with pytest.raises(OpsError, match=CAP_WORDS):
            press()
    assert op_runs.load(runner.base, op_id)["state"] == "check"


def test_no_cap_is_none_and_the_default_cap_is_operations_own_spend(tmp_path, stub):
    from orkboard.core import treasury
    r = OpRunner(tmp_path / "ops", settings=lambda: {"servers": {"jira": "Atlassian"}})
    assert r.cap() == (0.0, treasury.GOLD_LIMIT_USD) and not r.capped()
    today = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    op_runs.ledger(r.base).write_text(json.dumps({"at": today, "usd": treasury.GOLD_LIMIT_USD}) + "\n")
    assert r.capped()
    r.cap = lambda: (99.0, 0.0)                                   # a cap of 0 is none
    assert not r.capped()


def test_a_learn_call_held_by_a_spent_window_runs_after_a_restart(tmp_path, stub):
    soon = dt.datetime.now() + dt.timedelta(hours=1)
    base = tmp_path / "ops"
    first = OpRunner(base, settings=lambda: {"servers": {"jira": "Atlassian"}},
                     limits=lambda: [Limit("claude", "", "session", 0.02, soon)])
    first.learn("jira-task", "op-1", changes=[{"label": "Summary", "before": "Fix it", "after": "[Checkout] Fix it"}])
    first.wait_idle()
    kept = base / "templates" / "jira-task" / "learn.json"
    assert kept.is_file() and mode(kept) == 0o600 and not stub.calls()        # held: nothing called, nothing lost
    assert json.loads(kept.read_text())["changes"][0]["after"] == "[Checkout] Fix it"
    stub.answer(stream([], text=json.dumps({"rules": ["A title starts with the component in brackets"], "why": "w"})))
    again = OpRunner(base, settings=lambda: {"servers": {"jira": "Atlassian"}})                  # Orkboard opened again
    again.start()
    assert again.wait_idle()
    assert "'Fix it' → '[Checkout] Fix it'" in flag(stub.calls()[-1]["argv"], "-p")
    assert op_runs.proposal(base, "jira-task")["lines"] == ["A title starts with the component in brackets"]
    assert not kept.exists()


def test_a_learn_call_waits_for_the_cap_and_its_template_gone_drops_it(tmp_path, stub):
    base = tmp_path / "ops"
    r = OpRunner(base, settings=lambda: {"servers": {"jira": "Atlassian"}}, cap=lambda: (11.0, 10.0))
    r.learn("jira-task", "op-1", not_right="the epic")
    r.wait_idle()
    assert (base / "templates" / "jira-task" / "learn.json").is_file() and not stub.calls()
    op_runs.save_learn(base, "gone-one", {"op": "op-2", "changes": [], "not_right": ""})
    r.cap = lambda: (1.0, 10.0)
    stub.answer(stream([], text=json.dumps({"rules": [], "why": ""})))
    r.start()
    assert r.wait_idle()
    assert len(stub.calls()) == 1 and not list((base / "templates").glob("*/learn.json"))


def test_busy_is_a_call_running_or_waiting_in_the_queue(runner):
    """Spec 47 §3: the computer is kept awake while an operation's call runs or waits."""
    assert not runner.busy()
    runner._queue.append(("op-1", "prepare"))
    assert runner.busy()
    runner._queue.clear()
    runner._running["op-1"] = threading.Event()
    assert runner.busy()
    runner._running.clear()
    assert not runner.busy()
