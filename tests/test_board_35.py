"""Spec 35 on the host, the model call stubbed (`jobs.run_read`): a goal from a description, an idea that needs a goal,
the queue, autostart and Start now, Needs you as one list, proposals, a file to-do, the Board's commands and events."""
from __future__ import annotations

import base64
import json
import sys
import time
import types
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, idea_secrets, ideas, jobs

NEW = {"ideas.answer", "ideas.queue", "ideas.read_stop", "ideas.start_now", "ideas.proposal", "ideas.board_set"}


@pytest.fixture
def host(fake_repo) -> Orkboard:
    (fake_repo / "src" / "board.py").write_text("x = 1\n")
    h = Orkboard(fake_repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


@pytest.fixture
def model(monkeypatch):
    """The keeper's calls: answered by step; every call's arguments kept."""
    seen, answers = [], {
        "goal": {"title": "Runs at a glance", "summary": "The table lives in src/app.py.\nIt reads runs.",
                 "metrics": [{"name": "done when the table shows", "target": "1 table", "how": "a browser test"},
                             {"name": "done when it sorts", "target": "3 keys", "how": "a unit test"}],
                 "links": ["src/app.py", "src/nope.py", "https://example.com", "../outside.md"], "questions": []},
        "draft": {"title": "The table", "gist": "A table.", "why": "w", "done_when": ["it shows"], "risk": "low",
                  "touches": ["src/app.py"], "questions": []},
        "plan": {"tasks": [{"id": "k1", "title": "Add the table", "brief": "b", "tier": "warrior"}]}}

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, effort="", budget=None,
                 one_shot=False, tools=True):
        step = ("trail" if "lay out its ideas" in prompt else "goal" if "saved a goal" in prompt else "draft" if "write its spec" in prompt
                else "plan" if "turn it into a plan" in prompt else "other")
        seen.append({"step": step, "model": model, "resume": resume, "effort": effort, "budget": budget,
                     "one_shot": one_shot, "prompt": prompt})
        return json.dumps(answers.get(step, {})), None, 10, ""

    monkeypatch.setattr(jobs, "run_read", run_read)
    run_read.seen, run_read.answers = seen, answers
    return run_read


class FakeRunner:
    started: list = []

    def __init__(self, *a, **k):
        FakeRunner.started = []

    def start(self, slug):
        FakeRunner.started.append(slug)

    def stop(self, slug):
        pass

    def tick(self):
        pass

    def stop_all(self):
        pass


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", types.SimpleNamespace(IdeaRunner=FakeRunner))
    FakeRunner.started = []
    return FakeRunner


def _wait(host, slug="", goal=False):
    k = host.ideas.keeper
    for _ in range(500):
        if not (k.busy_goal(slug) if goal else k.busy(slug)):
            return
        time.sleep(0.01)
    raise AssertionError("the keeper never finished")


def _events(host, name):
    return [r for r in event_log.read(Path(host.town.repo_root)) if r["event"] == name]


def _goal(host, about="Show the runs at a glance.", priority="normal", **more):
    slug = host.command("ideas.goal_save", {"about": about, "priority": priority, **more})["slug"]
    _wait(host, slug, goal=True)
    return slug


def test_the_new_commands_are_the_hosts_and_a_phones(host):
    assert NEW <= set(host.commands) and all(BoardPhone.allowed(host, c, {}) for c in NEW)


def test_a_goal_from_a_description_and_a_priority_is_read_at_once_and_written(host, model):
    slug = _goal(host, priority="high")
    (call, trail) = model.seen                                               # the read, then the trail it lays out (spec 46 §3)
    assert trail["step"] == "trail" and trail["effort"] == "medium"
    assert call["step"] == "goal" and "opus" in call["model"] and call["effort"] == "high" and call["budget"] == 1.0
    assert call["resume"] == "" and call["one_shot"] is True and "Show the runs at a glance." in call["prompt"]
    g = host.command("ideas.goal", {"slug": slug})
    assert g["title"] == "Runs at a glance" and g["title_by"] == "keeper" and g["priority"] == "high"
    assert g["summary"].startswith("The table lives in src/app.py.") and g["state"] == "ready"
    assert [(m["name"], m["how"]) for m in g["metrics"]] == [("done when the table shows", "a browser test"),
                                                             ("done when it sorts", "a unit test")]
    assert g["links"] == ["src/app.py"]                                      # only paths that exist, never a URL
    st = ideas.goal_state(host.ideas.state_dir, slug)
    assert len(st["read_at"]) == 40 and st["read_at"] == host.ideas.keeper.head()
    (read,) = _events(host, "goal_read")
    assert read["tier"] and read["effort"] == "high" and read["step"] == "goal" and read["cost"] is None
    host.command("ideas.goal_save", {"slug": slug, "about": "Show runs.", "priority": "high", "title": "My own title"})
    _wait(host, slug, goal=True)
    assert host.command("ideas.goal", {"slug": slug})["title"] == "My own title"   # the person's: never rewritten
    assert host.command("ideas.goal", {"slug": slug})["title_by"] == "person"
    assert next(t for t in host.command("ideas.board")["tracks"] if t["slug"] == slug)["title_by"] == "person"


def test_an_idea_needs_a_goal_high_and_normal_are_drafted_at_once_low_and_night_wait(host, model, runner):
    with pytest.raises(CommandError, match="needs a goal"):
        host.command("ideas.add", {"text": "x"})
    with pytest.raises(CommandError, match="needs a goal"):
        host.command("ideas.add", {"text": "x", "track": "general"})
    g = _goal(host)
    seen = len(model.seen)
    high = host.command("ideas.add", {"text": "a high one", "track": g, "priority": "high"})
    _wait(host, high["slug"])
    normal = host.command("ideas.add", {"text": "a normal one", "track": g})
    _wait(host, normal["slug"])
    low = host.command("ideas.add", {"text": "a low one", "track": g, "priority": "low"})
    closed = host.command("ideas.add", {"text": "closed dialog", "track": g, "priority": "high", "night": True})
    assert [high["queue"], normal["queue"], low["queue"], closed["queue"]] == ["now", "now", "night", "night"]
    drafted = [c["prompt"] for c in model.seen[seen:] if c["step"] == "draft"]
    assert len(drafted) == 2 and "a high one" in drafted[0] and "a normal one" in drafted[1]
    assert ideas.state(host.ideas.state_dir, low["slug"])["state"] == "raw"
    rows = {i["slug"]: i for i in host.command("ideas.board")["ideas"]}
    assert rows[low["slug"]]["queue"] == "night" and rows[normal["slug"]]["priority"] == "normal"
    added = _events(host, "idea_added")
    assert [(e["priority"], e["queue"]) for e in added] == [("high", "now"), ("normal", "now"), ("low", "night"), ("high", "night")]
    assert all(c["resume"] == "" and c["one_shot"] for c in model.seen)       # §0: no call ever resumes a session


def test_autostart_starts_what_is_safe_and_passed_by_says_who(host, model, runner):
    g = _goal(host)
    slug = host.command("ideas.add", {"text": "safe", "track": g})["slug"]
    _wait(host, slug)
    plan = ideas.plan(host.ideas.state_dir, slug)
    assert plan["passed_by"] == "auto" and runner.started == [slug] and plan.get("start_at") is None
    (passed,) = _events(host, "plan_passed")
    assert passed["by"] == "auto" and passed["risk"] == "low" and passed["priority"] == "normal"
    (made,) = _events(host, "plan_made")
    assert made["step"] == "plan" and made["prompt_chars"] > 0 and made["tokens"] == {"total": 10} and made["cost"] is None


def test_autostart_off_or_a_question_or_a_stopped_plan_waits_for_the_person(host, model, runner):
    g = _goal(host)
    host.command("ideas.board_set", {"autostart": False})
    a = host.command("ideas.add", {"text": "off", "track": g})["slug"]
    _wait(host, a)
    assert ideas.plan(host.ideas.state_dir, a).get("passed_at") is None and runner.started == []
    host.command("ideas.board_set", {"autostart": True})
    model.answers["draft"] = {**model.answers["draft"], "questions": ["Which columns?"]}
    b = host.command("ideas.add", {"text": "asks", "track": g})["slug"]
    _wait(host, b)
    assert ideas.state(host.ideas.state_dir, b)["state"] == "asks" and ideas.plan(host.ideas.state_dir, b) is None
    host.command("ideas.start", {"slug": a})                                  # the person passes it …
    assert ideas.plan(host.ideas.state_dir, a)["passed_by"] == "person"
    host.command("ideas.stop", {"slug": a})                                   # … and stops it: it waits for them now
    ideas.edit_plan(host.ideas.state_dir, a, lambda p: p.update(passed_at=None))
    ideas.save_state(host.ideas.state_dir, a, state="plan")
    assert host.ideas.autostart(a) == "" and ideas.plan(host.ideas.state_dir, a).get("passed_at") is None


def test_a_low_safe_plan_starts_at_night_and_start_now_clears_it(host, model, runner):
    g = _goal(host, priority="low")
    slug = host.command("ideas.add", {"text": "low and safe", "track": g, "priority": "low"})["slug"]
    ideas.save_state(host.ideas.state_dir, slug, state="raw")
    host.ideas.keeper.draft_one(slug)
    plan = ideas.plan(host.ideas.state_dir, slug)
    assert plan["start_at"] == "night" and plan["passed_by"] == "auto" and runner.started == []
    row = next(i for i in host.command("ideas.board")["ideas"] if i["slug"] == slug)
    assert row["start_at"] == "night" and row["state"] == "plan" and not row["in_needs_you"]
    host.command("ideas.start_now", {"slug": slug, "via": "map"})
    assert ideas.plan(host.ideas.state_dir, slug)["start_at"] is None and runner.started == [slug]
    assert [(e["idea"], e["via"]) for e in _events(host, "plan_started_now")] == [(slug, "map")]       # spec 41 §4
    assert "via" not in _events(host, "plan_passed")[-1]                       # passed by the board: no press
    with pytest.raises(CommandError, match="does not wait for the night"):
        host.command("ideas.start_now", {"slug": slug})


def test_needs_you_is_one_list_blocks_then_priority_then_age_proposals_last(host, model, runner):
    g = _goal(host)
    root, sd = host.ideas.root(), host.ideas.state_dir
    mk = lambda text, prio, state: (lambda s: (ideas.save_state(sd, s, state=state), s)[1])(ideas.add_idea(root, text, g, sd, prio))  # noqa: E731
    prop = mk("a proposal", "high", "proposed")
    asks_low = mk("asks low", "low", "asks")
    asks_high = mk("asks high", "high", "asks")
    work = mk("working", "low", "working")
    ideas.save_plan(sd, work, {"idea": work, "made_at": "2026-10-18T09:00:00", "passed_at": "x", "todos": [
        {"id": "t1", "title": "API_KEY", "kind": "secret", "why": "", "steps": ["Open the console"], "for": ["k1"], "done": False}],
        "tasks": [{"id": "k1", "title": "Use it", "state": "waiting", "after": []},
                  {"id": "k2", "title": "Broke", "state": "failed", "error": "boom", "after": []},
                  {"id": "k3", "title": "Waits", "state": "held", "note": "after 18:00", "after": []}]})
    needs = host.command("ideas.board")["needs_you"]
    kinds = [(n["kind"], n["title"]) for n in needs]
    assert kinds[:2] in ([("todo", "working"), ("failed", "working")], [("failed", "working"), ("todo", "working")])
    assert all(n["blocks"] for n in needs[:2]) and kinds[2:] == [("asks", "asks high"), ("asks", "asks low"), ("proposal", "a proposal")]
    assert needs[0]["goal"] == g and {"kind", "idea", "goal", "title", "text", "priority", "blocks", "at"} <= set(needs[0])
    assert not any(n["kind"] == "held" or "18:00" in n["text"] for n in needs)          # held leaves Needs you
    todo = next(n for n in needs if n["kind"] == "todo")["todo"]
    assert todo["steps"] == ["Open the console"]                              # steps on a secret
    assert host.snapshot()["needs_you"] == 4 and prop                          # the count leaves proposals out
    assert asks_low and asks_high


def test_a_proposal_taken_joins_the_queue_one_declined_is_kept_for_the_night(host, model, runner):
    g = _goal(host)
    root, sd = host.ideas.root(), host.ideas.state_dir
    take = ideas.add_idea(root, "why take", g, sd)
    no = ideas.add_idea(root, "why not", g, sd)
    for s in (take, no):
        ideas.save_state(sd, s, state="proposed")
    host.command("ideas.proposal", {"slug": take, "take": True, "priority": "low"})
    assert ideas.state(sd, take)["state"] == "raw" and ideas.state(sd, take)["queue"] == "night"
    host.command("ideas.proposal", {"slug": no, "take": False, "reason": "not now"})
    assert ideas.idea_page(root, no) is None
    from orkboard.core import idea_night
    assert idea_night.declined(sd)[-1]["reason"] == "not now" and idea_night.declined(sd)[-1]["goal"] == g
    assert [(e["take"], e["has_reason"]) for e in _events(host, "proposal_answered")] == [(True, False), (False, True)]


def test_queue_read_stop_and_board_set(host, model, runner):
    g = _goal(host)
    slug = host.command("ideas.add", {"text": "tonight", "track": g, "night": True})["slug"]
    host.command("ideas.read_stop", {"slug": slug})
    assert ideas.state(host.ideas.state_dir, slug)["queue"] == "hold"
    host.command("ideas.queue", {"slug": slug, "queue": "night"})
    assert ideas.state(host.ideas.state_dir, slug)["queue"] == "night"
    host.command("ideas.queue", {"slug": slug, "queue": "now", "via": "map"})
    _wait(host, slug)
    assert [(e["queue"], e["via"]) for e in _events(host, "idea_queued")] == [("night", "idea"), ("now", "map")]   # spec 41 §4
    assert ideas.state(host.ideas.state_dir, slug)["state"] != "raw"
    got = host.command("ideas.board_set", {"target": "quality", "night": "22:00-05:00", "device": "phone"})
    assert got == {"target": "quality", "autostart": True, "night": "22:00-05:00"}
    board = host.command("ideas.board")
    assert (board["target"], board["autostart"], board["night"]) == ("quality", True, "22:00-05:00")
    with pytest.raises(CommandError, match="thrift, balance or quality"):
        host.command("ideas.board_set", {"target": "cheap"})
    (e,) = _events(host, "board_set")
    assert e["target"] == "quality" and e["night"] == "22:00-05:00" and e["device"] == "phone"
    assert [e["idea"] for e in _events(host, "keeper_stopped")] == [slug]


def test_a_file_todo_is_kept_outside_the_repository_and_off_the_plan(host, model, runner):
    g = _goal(host)
    slug = host.command("ideas.add", {"text": "needs a file", "track": g, "night": True})["slug"]
    ideas.save_plan(host.ideas.state_dir, slug, {"idea": slug, "made_at": "x", "passed_at": None, "tasks": [
        {"id": "k1", "title": "Use it", "brief": "b", "state": "waiting", "after": []}], "todos": [
        {"id": "t2", "title": "the Firebase config", "kind": "file", "why": "", "steps": ["Download it"], "accept": ["json"],
         "for": ["k1"], "done": False, "value": None}]})
    ideas.save_state(host.ideas.state_dir, slug, state="plan")
    data = base64.b64encode(b'{"project": "x-secret"}').decode()
    with pytest.raises(CommandError, match="paired link"):
        host.command("ideas.todo", {"idea": slug, "id": "t2", "done": True, "file": {"name": "g.json", "data": data},
                                    "device": "phone"})
    with pytest.raises(CommandError, match="not one it takes"):
        host.command("ideas.todo", {"idea": slug, "id": "t2", "done": True, "file": {"name": "g.txt", "data": data}})
    host.command("ideas.todo", {"idea": slug, "id": "t2", "done": True, "file": {"name": "google-services.json", "data": data}})
    plan_text = (host.ideas.state_dir / "ideas" / slug / "plan.json").read_text()
    assert "x-secret" not in plan_text and json.loads(plan_text)["todos"][0]["value"] == "google-services.json"
    path = idea_secrets.file_path(host.ideas.state_dir, slug, "t2")
    assert path.read_bytes() == b'{"project": "x-secret"}' and oct(path.stat().st_mode & 0o777) == "0o600"
    assert host.ideas.state_dir in path.parents and not list(Path(host.town.repo_root).glob("**/google-services.json"))[1:]
    guarded = BoardPhone.guard("ideas.todo", {"idea": slug, "link": "paired"}, {"id": "p1", "name": "Phone"})
    assert guarded["link"] == "paired" and BoardPhone.guard("ideas.todo", {"link": "paired"}, {})["device"] == "phone"
    assert "link" not in BoardPhone.guard("ideas.todo", {"link": "paired"}, {})
    host.command("ideas.drop", {"slug": slug})
    assert not path.exists()


def test_the_agents_chips_say_by_itself_tonight_and_why_held(host, runner):
    root, sd = host.ideas.root(), host.ideas.state_dir
    g = ideas.add_track(root, "Chips")
    a = ideas.add_idea(root, "auto", g, sd)
    b = ideas.add_idea(root, "night", g, sd)
    task = lambda tid, state, note="": {"id": tid, "title": tid, "brief": "b", "tier": "warrior", "kind": "code",  # noqa: E731
                                        "after": [], "state": state, "note": note, "started": ""}
    ideas.save_plan(sd, a, {"idea": a, "passed_at": "x", "passed_by": "auto", "todos": [],
                            "tasks": [task("k1", "held", "reserve · after 18:00"), task("k2", "held", "after 19:00")]})
    ideas.save_plan(sd, b, {"idea": b, "passed_at": "x", "passed_by": "auto", "start_at": "night", "todos": [],
                            "tasks": [task("k1", "ready")]})
    chips = [c for r in host.command("ideas.agents")["roles"] for c in r.get("chips") or [] if c.get("task")]
    got = {(c["idea"], c["task"]): c for c in chips}
    assert got[(a, "k1")]["by"] == "auto" and got[(a, "k1")]["note"].startswith("reserve") and not got[(a, "k1")]["night"]
    assert got[(a, "k2")]["note"] == "after 19:00" and got[(b, "k1")]["night"] is True
