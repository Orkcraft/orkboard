"""Spec 35 §1, §5, §6, §9, §12, §13 on the runner: the Target's tier and effort with the tool and model recorded, the
night gate and Start now, the reserve for what started by itself (never the person's press), High first, a file
to-do's path in the environment only, and the gate refusing a result that edits the Board's pages."""
from __future__ import annotations

import datetime as dt
import json
import threading
from types import SimpleNamespace

import pytest

from orkboard.core.idea_runner import IdeaRunner
from orkboard.realm import event_log, idea_secrets
from orkboard.sources.limits import Limit

from tests.test_idea_runner import git, plan_of, town  # noqa: F401  (the fixture repository with a stub claude)


def _runner(town, limits=None, night="01:00-07:00", **more):
    settings = SimpleNamespace(ideas={"max_parallel": 1, "merge_into": "main", "push": False, "review": True,
                                      "night": night, "reserve_day": 0.3, "reserve_night": 0.1, **more})
    r = IdeaRunner(town.repo, town.state, settings, None, limits=limits or (lambda: []), events=True)
    launched = []
    r._spawn = lambda slug, tid, cancel, again: launched.append((slug, tid))    # no session: only who starts
    return r, launched


def _pass(town, slug="demo", **plan):
    path = town.state / "ideas" / slug / "plan.json"
    data = json.loads(path.read_text())
    data.update(plan)
    path.write_text(json.dumps(data))


def _now_in(night: bool) -> str:
    """A night window that holds now, or one that does not."""
    h = dt.datetime.now().hour
    return f"{h:02d}:00-{(h + 1) % 24:02d}:00" if night else f"{(h + 2) % 24:02d}:00-{(h + 3) % 24:02d}:00"


def test_a_task_runs_on_the_targets_tier_with_its_tool_and_model_recorded(town):
    plan_of(town, [{"id": "k1", "tier": "warrior"}])
    r, launched = _runner(town, target="thrift")
    r.start("demo")
    (task,) = r.plan("demo")["tasks"]
    assert launched == [("demo", "k1")] and task["ran_tier"] == "laborer" and task["effort"] == "low"
    assert task["tool"] == "claude" and "haiku" in task["model"] and task["tier"] == "warrior"
    (e,) = [x for x in event_log.read(town.repo) if x["event"] == "task_state" and x["state"] == "running"]
    assert (e["ran_tier"], e["effort"], e["tool"]) == ("laborer", "low", "claude") and "haiku" in e["model"]


def test_a_plan_that_starts_at_night_waits_outside_the_window_and_starts_inside(town):
    plan_of(town, [{"id": "k1"}])
    _pass(town, start_at="night", passed_by="auto")
    r, launched = _runner(town, night=_now_in(False))
    r.start("demo")
    assert launched == [] and r.plan("demo")["tasks"][0]["state"] == "ready"    # not held: it waits for the night
    r, launched = _runner(town, night=_now_in(True))
    r.start("demo")
    assert launched == [("demo", "k1")]


def test_the_reserve_holds_what_started_by_itself_and_never_the_persons_press(town):
    reset = dt.datetime.now() + dt.timedelta(hours=2)
    limits = lambda: [Limit("claude", "", "session", 0.2, reset)]               # noqa: E731  above NEARLY, below 0.3
    plan_of(town, [{"id": "k1"}])
    _pass(town, passed_by="auto")
    r, launched = _runner(town, limits=limits, night=_now_in(False))
    r.start("demo")
    (task,) = r.plan("demo")["tasks"]
    assert launched == [] and task["state"] == "held" and task["note"] == f"reserve · after {reset:%H:%M}"
    plan_of(town, [{"id": "k1"}])
    _pass(town, passed_by="person")
    r, launched = _runner(town, limits=limits, night=_now_in(False))
    r.start("demo")
    assert launched == [("demo", "k1")]
    plan_of(town, [{"id": "k1"}])
    _pass(town, passed_by="auto")
    r, launched = _runner(town, limits=limits, night=_now_in(True))            # at night the reserve is 0.10
    r.start("demo")
    assert launched == [("demo", "k1")]


def test_high_goes_before_normal(town):
    for slug in ("normal-one", "high-one"):
        plan_of(town, [{"id": "k1"}], slug=slug)
        _pass(town, slug, passed_by="person")
    r, launched = _runner(town)
    r.rank = lambda slug: (0 if slug.startswith("high") else 1,)
    r._active = ["normal-one", "high-one"]
    for slug in r._active:
        (town.state / "ideas" / slug / "state.json").write_text(json.dumps({"state": "working"}))
    r.tick()
    assert launched == [("high-one", "k1")]                                     # one slot: High takes it


def test_a_file_todos_path_is_in_the_tasks_environment_and_only_named_in_its_prompt(town):
    plan_of(town, [{"id": "k1"}], todos=[{"id": "t2", "title": "the config", "kind": "file", "for": ["k1"], "done": True,
                                          "value": "conf.json"}])
    path = idea_secrets.put_file(town.state, "demo", "t2", "conf.json", b'{"k": "file-secret"}')
    r, _ = _runner(town)
    plan = r.plan("demo")
    env = r._env("demo", "k1", plan)
    assert env["ORKCRAFT_FILE_T2"] == str(path) and str(town.repo / ".orkcraft") in str(path)
    prompt = r._prompt("demo", plan, plan["tasks"][0])
    assert "The file is at $ORKCRAFT_FILE_T2" in prompt and str(path) not in prompt and "file-secret" not in prompt
    assert "file-secret" not in (town.state / "ideas" / "demo" / "plan.json").read_text()
    assert not git(town.repo, "status", "--porcelain", "--ignored", "--", "llm-wiki").count("conf.json")


def test_the_gate_refuses_a_result_that_edits_the_boards_pages(town):
    plan_of(town, [{"id": "k1"}])
    r, _ = _runner(town)
    path, _branch = r.git.prepare("demo", "k1", "main")
    start = r.git.head(path)
    page = path / "llm-wiki" / "general" / "pages" / "ideas" / "other.md"
    page.parent.mkdir(parents=True)
    page.write_text("---\nowner: board\n---\n# Other\n")
    git(path, "add", "-A")
    git(path, "-c", "user.name=T", "-c", "user.email=t@x", "commit", "-qm", "edit a page")
    problem, out = r._check(path, start, threading.Event(), "t")
    assert "never edits the Board's pages" in problem and "pages/ideas/other.md" in problem and out == ""
    r.git.remove(path)
