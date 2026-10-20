"""Spec 43 A (docs/specs/43-party-measured.md §1, Tests → A): a check says what it found. The findings file's shape, the ask in a check
task's prompt, and how a check task ends with a stub `claude` that writes its findings (the runner's fixtures)."""
from __future__ import annotations

import json
import subprocess

import pytest

from orkboard.core.idea_runner import RunnerError
from orkboard.core.idea_task import FINDINGS_ASK
from orkboard.realm import event_log, idea_checks
from tests.test_idea_runner import calls, git, plan_of, reviewing, runner_of, tasks_of, town, wait_idle, wait_task  # noqa: F401


def text(*items, **more):
    return json.dumps({"findings": list(items), **more})


def finding(**over):
    return {"where": "a.py:1", "what": "a bug", "fixed": False, **over}


def test_the_tags_are_the_checkers_first_kinds():
    assert idea_checks.TAGS == ("security", "review", "a11y", "datacheck", "edit")
    assert idea_checks.FINDINGS_FILE == ".orkcraft-findings.json"


def test_parse_findings_is_strict_about_the_shape_twenty_at_most_and_the_lengths():
    assert idea_checks.parse_findings(text()) == []
    assert idea_checks.parse_findings(text(finding(fixed=True))) == [finding(fixed=True)]
    assert idea_checks.parse_findings(text(*[finding()] * 20)) is not None
    assert idea_checks.parse_findings(text(*[finding()] * 21)) is None
    assert idea_checks.parse_findings(text(finding(where="w" * 200), finding(what="x" * 300))) is not None
    assert idea_checks.parse_findings(text(finding(where="w" * 201))) is None
    assert idea_checks.parse_findings(text(finding(what="x" * 301))) is None
    for bad in ("", "not json", "[]", "null", '{"findings": 3}', '{"other": []}', text({"where": "a", "what": "b"}),
                text({"where": "a", "what": "b", "fixed": "yes"}), text({"where": 1, "what": "b", "fixed": True}), text("a bug"), None, 5):
        assert idea_checks.parse_findings(bad) is None, bad
    assert idea_checks.parse_findings(text(finding(extra=1))) == [finding()]            # only the three fields are kept


def test_counts_and_status_say_found_fixed_and_left_and_null_before_a_task_ends():
    assert idea_checks.counts([finding(fixed=True), finding(), finding()]) == {"found": 3, "fixed": 1, "left": 2}
    assert idea_checks.counts([]) == {"found": 0, "fixed": 0, "left": 0}
    assert idea_checks.counts(None) == {"found": None, "fixed": None, "left": None}
    checks = [{"by": "reviewer", "name": "Reviewer", "tag": "review", "tier": "elder", "applies": "x", "done": "y", "task": "z", "every": False}]
    kept = [{"by": "reviewer", "applies": True, "why": ""}]
    row = idea_checks.status(kept, checks, [{"id": "k2", "kind": "review", "state": "review", "findings": [finding(fixed=True), finding()]}])[0]
    assert (row["found"], row["fixed"], row["left"], row["state"]) == (2, 1, 1, "review")
    row = idea_checks.status(kept, checks, [{"id": "k2", "kind": "review", "state": "running"}])[0]
    assert (row["found"], row["fixed"], row["left"]) == (None, None, None)
    row = idea_checks.status(kept, checks, [])[0]
    assert (row["found"], row["state"]) == (None, "")


def test_a_check_task_s_prompt_ends_with_the_ask_and_another_task_s_does_not(town):
    plan_of(town, [{"id": "k1"}, {"id": "k2", "kind": "review", "after": ["k1"]}])
    runner, _ = runner_of(town)
    plan = runner.plan("demo")
    check, other = runner._prompt("demo", plan, plan["tasks"][1]), runner._prompt("demo", plan, plan["tasks"][0])
    assert check.endswith(FINDINGS_ASK) and ".orkcraft-findings.json" in check and "at most 20" in check
    assert "findings" not in other


def test_clean_and_no_change_is_merged_with_no_commit_no_review_and_nothing_lands(town, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=check_clean")
    plan_of(town, [{"id": "k1", "kind": "review"}])
    runner, _ = reviewing(town)                                   # Review is on: a clean check still does not wait there
    before = git(town.repo, "rev-parse", "main")
    runner.start("demo")
    assert wait_idle(runner)["state"] == "done"
    task = tasks_of(town)["k1"]
    assert task["state"] == "merged" and task["commit"] == "" and task["note"] == "clean" and task["findings"] == []
    assert git(town.repo, "rev-parse", "main") == before
    assert task["tests"]["ran"] is False and task["diff"] == {"files": 0, "added": 0, "removed": 0}
    assert not list((town.repo / ".orkcraft" / "worktrees").glob("*"))
    assert not (town.repo / idea_checks.FINDINGS_FILE).exists()
    log = [r for r in event_log.read(town.repo) if r["event"] in ("task_state", "check_done")]
    merged = next(r for r in log if r["event"] == "task_state" and r["state"] == "merged")
    assert merged["check"] is True and merged["clean"] is True
    done = next(r for r in log if r["event"] == "check_done")
    assert (done["idea"], done["task"], done["found"], done["fixed"], done["left"], done["round"]) == ("demo", "k1", 0, 0, 0, 1)
    assert not [r for r in event_log.read(town.repo) if r["event"] == "result_ready"]


def test_findings_left_and_no_change_wait_at_review_even_with_review_off_and_the_file_is_never_committed(town, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=check_left")
    plan_of(town, [{"id": "k1", "kind": "review"}])
    runner, _ = runner_of(town, review=False)                     # `ideas.review` off: findings left still go to Review
    runner.start("demo")
    task = wait_task(runner, "k1", "review")
    assert task["note"] == "2 left" and len(task["findings"]) == 2 and task["commit"] == ""
    assert task["diff"]["files"] == 0 and task["tests"]["green"] is True
    assert idea_checks.FINDINGS_FILE not in git(town.repo, "log", "--all", "--name-only", "--format=")
    done = next(r for r in event_log.read(town.repo) if r["event"] == "check_done")
    assert (done["found"], done["fixed"], done["left"]) == (2, 0, 2)
    assert next(r for r in event_log.read(town.repo) if r["event"] == "task_state" and r["state"] == "review")["check"] is True
    assert len(calls(town)) == 1


def test_all_fixed_with_changes_takes_todays_path_and_lands_when_review_is_off(town, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=check_fixed")
    plan_of(town, [{"id": "k1", "kind": "review"}])
    runner, _ = runner_of(town, review=False)
    runner.start("demo")
    assert wait_idle(runner)["state"] == "done"
    task = tasks_of(town)["k1"]
    assert task["state"] == "merged" and task["commit"] and task["note"] == "" and task["findings"][0]["fixed"] is True
    assert (town.repo / "k1.txt").read_text() == "fixed by k1\n"
    assert not (town.repo / idea_checks.FINDINGS_FILE).exists()
    assert idea_checks.FINDINGS_FILE not in git(town.repo, "log", "--all", "--name-only", "--format=")


def test_changes_with_some_left_wait_at_review_after_a_green_gate_with_review_off(town, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=check_mixed")
    plan_of(town, [{"id": "k1", "kind": "review"}])
    runner, _ = runner_of(town, review=False)
    runner.start("demo")
    task = wait_task(runner, "k1", "review")
    assert task["note"] == "1 left" and task["tests"]["green"] is True and task["tests"]["ran"] and task["diff"]["files"] == 1
    assert [f["fixed"] for f in task["findings"]] == [True, False]
    done = next(r for r in event_log.read(town.repo) if r["event"] == "check_done")
    assert (done["found"], done["fixed"], done["left"]) == (2, 1, 1)


def test_no_findings_file_twice_fails_with_its_words_and_the_second_try_asks_again(town, monkeypatch):
    for mode in ("check_none", "check_bad"):
        monkeypatch.setenv("STUB_MODE", f"k1={mode}")
        plan_of(town, [{"id": "k1", "kind": "review"}])
        runner, _ = reviewing(town)
        runner.start("demo")
        state = wait_idle(runner)
        assert state["state"] == "failed" and "the check said nothing: no findings file" in state["error"], mode
        task = tasks_of(town)["k1"]
        assert task["state"] == "failed" and task["error"] == "the check said nothing: no findings file"
        assert len(calls(town)) >= 2
        assert FINDINGS_ASK in " ".join(calls(town)[1]["argv"])                # the retry asks for the file again
        town.log.unlink()


def test_a_findings_file_written_at_the_retry_is_taken(town, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=check_late")
    plan_of(town, [{"id": "k1", "kind": "review"}])
    runner, _ = reviewing(town)
    runner.start("demo")
    assert wait_idle(runner)["state"] == "done"
    assert [c["resume"] for c in calls(town)] == [False, True]
    task = tasks_of(town)["k1"]
    assert task["state"] == "merged" and task["note"] == "clean"


def test_a_claim_of_a_fix_with_no_change_counts_as_left(town, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=check_claims")
    plan_of(town, [{"id": "k1", "kind": "review"}])
    runner, _ = reviewing(town)
    runner.start("demo")
    task = wait_task(runner, "k1", "review")
    assert task["note"] == "1 left" and task["findings"][0]["fixed"] is False


def test_fix_them_sends_back_and_the_check_runs_again_in_round_2(town, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=check_left")
    plan_of(town, [{"id": "k1", "kind": "review"}])
    runner, _ = reviewing(town)
    runner.start("demo")
    wait_task(runner, "k1", "review")
    runner.back("demo", "k1", "Fix the findings left:\na.py:1: a bug")
    monkeypatch.setenv("STUB_MODE", "k1=check_late")              # on the resume it finds nothing more
    task = wait_task(runner, "k1", "merged")
    assert task["round"] == 2 and task["note"] == "clean" and task["findings"] == []
    prompt = runner.log("demo", "k1")
    assert "The findings left from the last round:\n- a.py:1: a bug" in prompt and FINDINGS_ASK in prompt.split("== round 2")[1]
    decided = [r for r in event_log.read(town.repo) if r["event"] == "result_decided"]
    assert decided and decided[0]["decision"] == "back"


def test_leave_them_with_no_commit_merges_nothing_and_keeps_the_note(town, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=check_left")
    plan_of(town, [{"id": "k1", "kind": "review"}, {"id": "k2", "after": ["k1"]}])
    runner, _ = reviewing(town)
    runner.start("demo")
    wait_task(runner, "k1", "review")
    dev = git(town.repo, "rev-parse", "dev")
    assert runner.merge("demo", "k1") == ""
    task = tasks_of(town)["k1"]
    assert task["state"] == "merged" and task["commit"] == "" and task["note"] == "2 left"
    assert git(town.repo, "rev-parse", "dev") == dev                # nothing landed
    assert not list((town.repo / ".orkcraft" / "worktrees").glob("*k1*"))
    decided = [r for r in event_log.read(town.repo) if r["event"] == "result_decided"]
    assert decided[0]["decision"] == "merge" and decided[0]["pushed"] is False
    wait_task(runner, "k2", "review")                              # its dependant goes on


def test_leave_them_with_fixes_lands_them_as_a_merge_does_today(town, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=check_mixed")
    plan_of(town, [{"id": "k1", "kind": "review"}])
    runner, _ = reviewing(town)
    runner.start("demo")
    wait_task(runner, "k1", "review")
    commit = runner.merge("demo", "k1")
    assert commit and git(town.repo, "rev-parse", "dev") == commit
    assert git(town.repo, "show", "dev:k1.txt") == "fixed by k1"


def test_drop_still_drops_a_check_s_result(town, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=check_left")
    plan_of(town, [{"id": "k1", "kind": "review"}])
    runner, _ = reviewing(town)
    runner.start("demo")
    wait_task(runner, "k1", "review")
    runner.drop_task("demo", "k1")
    assert tasks_of(town)["k1"]["state"] == "failed" and tasks_of(town)["k1"]["error"] == "dropped by you"
