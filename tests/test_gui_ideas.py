"""The board's host commands (spec 29a §6), the phone's allowlist and its compact snapshot, on Orkboard's host
(gui/board_host.py; Orkline ran them on its town's host too, spec 37 B)."""
from __future__ import annotations

import base64
import json
import sys
import time
import types
from pathlib import Path

import pytest

from orkboard.core import idea_keeper
from orkboard.gui import ideas as gui_ideas
from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import idea_secrets, ideas, jobs, roles, tool_run

BOARD_COMMANDS = {"ideas.board", "ideas.page", "ideas.add", "ideas.say", "ideas.plan", "ideas.start", "ideas.move",
                  "ideas.edit", "ideas.track_add", "ideas.track_set", "ideas.todo", "ideas.drop", "ideas.stop",
                  "ideas.review_list", "ideas.diff", "ideas.merge", "ideas.back", "ideas.drop_task",
                  "ideas.stop_task", "ideas.agents", "ideas.task", "ideas.into", "ideas.log", "ideas.logs", "ideas.goal_save",
                  "ideas.goal", "ideas.read_now", "ideas.roles", "ideas.role_save", "ideas.role_add", "ideas.role_drop",
                  "ideas.kind_set", "ideas.gate", "ideas.gate_merge", "ideas.today", "ideas.pick"}          # … and spec 49's three, spec 51's one


@pytest.fixture
def host(fake_repo) -> Orkboard:
    h = Orkboard(fake_repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


def _wait(host, slug):
    for _ in range(300):
        if not host.ideas.keeper.busy(slug):
            return
        time.sleep(0.01)
    raise AssertionError("the keeper never finished")


def _add(host, text, **more):
    """An idea under a goal (spec 35 §3: no idea without one, never General), waiting for the night unless asked."""
    root = host.ideas.root()
    goal = next((t["slug"] for t in ideas.tracks(root, make=False) if t["slug"] != "general"), None) or ideas.add_track(root, "First goal")
    return host.command("ideas.add", {"text": text, "track": goal, "night": True, **more})


def _plan(host, slug, todos=()):
    data = {"idea": slug, "made_at": "2026-10-17T09:00:00", "passed_at": None,
            "estimate": {"tasks": 1, "usd_low": 0.15, "usd_high": 0.45},
            "todos": list(todos),
            "tasks": [{"id": "k1", "title": "Do it", "brief": "b", "tier": "warrior", "after": [], "state": "ready",
                       "branch": "", "commit": "", "session": "", "cost": None, "tokens": None, "started": "",
                       "finished": "", "error": "", "note": ""}]}
    ideas.save_plan(host.ideas.state_dir, slug, data)
    ideas.save_state(host.ideas.state_dir, slug, state="plan")


def test_every_board_command_is_the_hosts_and_a_phones(host):
    assert BOARD_COMMANDS <= set(host.commands)
    assert all(BoardPhone.allowed(host, c, {}) for c in BOARD_COMMANDS)
    assert BOARD_COMMANDS <= set(host.command("mobile.hello")["commands"])


def test_drop_an_idea_and_read_the_board_and_its_page(host):
    rev = host.snapshot()["ideas_rev"]
    slug = _add(host, "Dark mode\nfor the night")["slug"]
    board = host.command("ideas.board")
    json.dumps(board)
    assert [t["slug"] for t in board["tracks"]] == ["first-goal"] and board["tracks"][0]["count"] == 1
    (i,) = board["ideas"]
    assert i["slug"] == slug and i["state"] == "raw" and i["thesis"] == "Dark mode" and i["track"] == "first-goal"
    assert i["progress"] == {"done": 0, "total": 0} and i["updated"]
    assert set(i) == {"slug", "title", "short", "track", "order", "state", "size", "thesis", "asks", "progress", "updated",
                      "priority",                 # spec 34 §4: ideas gain a priority
                      "queue", "held_until", "risk", "risk_triggers", "depends_on", "waits_on", "start_at",
                      "in_needs_you",             # spec 35 §12
                      "night_by"}                 # spec 44 §4: who put it off to the night
    assert i["priority"] == "normal" and board["tracks"][0]["priority"] == "normal" and board["tracks"][0]["state"] == "raw"
    assert board["needs_you"] == [] and board["rev"] > rev      # spec 35 §10: `today` became `needs_you`, the batch went
    page = host.command("ideas.page", {"slug": slug})
    assert [s["name"] for s in page["sections"]] == list(ideas.SECTIONS)
    assert page["sections"][0] == {"name": "Gist", "thesis": "Dark mode", "text": "Dark mode\nfor the night"}
    assert page["talk"][0]["who"] == "you" and page["plan"] is None and page["busy"] is False
    assert (host.ideas.root() / "pages/ideas" / f"{slug}.md").exists()   # spec 35 §13: in the Board's own tree
    with pytest.raises(CommandError, match="gone"):
        host.command("ideas.page", {"slug": "nope"})
    with pytest.raises(CommandError, match="text is missing"):
        _add(host, "  ")


def test_tracks_move_edit_and_drop(host):
    a = _add(host, "alpha")["slug"]
    b = _add(host, "beta")["slug"]
    ux = host.command("ideas.track_add", {"title": "UX"})["slug"]
    assert host.command("ideas.track_set", {"slug": ux, "about": "Calm", "criteria": ["fewer clicks"],
                                            "deadline": "2026-12-01"}) == {"ok": True}
    host.command("ideas.move", {"slug": b, "before": a})
    assert [i["slug"] for i in host.command("ideas.board")["ideas"]] == [b, a]
    host.command("ideas.move", {"slug": a, "track": ux})
    t = {t["slug"]: t for t in host.command("ideas.board")["tracks"]}
    assert t[ux]["count"] == 1 and t[ux]["criteria"] == ["fewer clicks"] and t[ux]["deadline"] == "2026-12-01"
    host.command("ideas.edit", {"slug": a, "section": "Risks", "text": "none"})
    assert host.command("ideas.page", {"slug": a})["sections"][4]["text"] == "none"
    with pytest.raises(CommandError, match="no section"):
        host.command("ideas.edit", {"slug": a, "section": "Bogus", "text": "x"})
    with pytest.raises(CommandError, match="deadline"):
        host.command("ideas.track_set", {"slug": ux, "deadline": "tomorrow"})
    host.command("ideas.drop", {"slug": a})
    assert [i["slug"] for i in host.command("ideas.board")["ideas"]] == [b]


def test_say_and_plan_run_the_keeper_in_the_background(host, monkeypatch):
    calls = []

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):   # spec 35 §0's effort, budget
        calls.append({"harness": harness, "model": model, "resume": resume})
        if "turn it into" in prompt:
            return json.dumps({"tasks": [{"id": "a", "title": "T", "brief": "B", "tier": "laborer"}]}), 0.1, 10, "s"
        return json.dumps({"reply": "ok", "sections": {"Why": "because"}, "questions": []}), 0.1, 10, "sess-9"

    monkeypatch.setattr(jobs, "run_read", run_read)
    host.command("ideas.board_set", {"autostart": False})          # spec 35 §5: off, the plan waits for the person
    slug = _add(host, "x")["slug"]
    assert host.command("ideas.say", {"slug": slug, "text": "why?", "section": "Why"}) == {"ok": True}
    _wait(host, slug)
    assert calls[0]["harness"] == "claude" and calls[0]["resume"] == ""
    assert ideas.state(host.ideas.state_dir, slug)["session"] == ""      # spec 35 §0: no session kept …
    host.command("ideas.say", {"slug": slug, "text": "and?"})
    _wait(host, slug)
    assert calls[1]["resume"] == ""                                     # … and none resumed
    host.command("ideas.plan", {"slug": slug})
    _wait(host, slug)
    page = host.command("ideas.page", {"slug": slug})
    assert page["state"] == "plan" and page["plan"]["tasks"][0]["tier"] == "laborer"
    needs = host.command("ideas.board")["needs_you"]
    assert [{k: n[k] for k in ("idea", "kind", "title", "text")} for n in needs] == [
        {"idea": slug, "kind": "plan", "title": "x", "text": "Plan ready · 1 tasks"}]
    assert host.snapshot()["needs_you"] == 1


def test_the_demo_runs_no_model(fake_repo):
    host = Orkboard(fake_repo, demo=True)
    slug = _add(host, "x")["slug"]
    assert host.command("ideas.board")["demo"] is True
    with pytest.raises(CommandError, match="demo runs no model"):
        host.command("ideas.say", {"slug": slug, "text": "hi"})
    host.close()


def test_start_without_a_runner_says_so_and_passes_nothing(host, monkeypatch):
    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", None)     # this build has no runner
    slug = _add(host, "x")["slug"]
    _plan(host, slug)
    with pytest.raises(CommandError, match="runner is not in this build"):
        host.command("ideas.start", {"slug": slug})
    assert ideas.plan(host.ideas.state_dir, slug)["passed_at"] is None


def test_start_passes_the_plan_to_the_runner_and_stop_all_reaches_it(host, monkeypatch):
    seen = []

    class FakeRunner:
        def __init__(self, repo_root, state_dir, settings, bus, **kw):
            seen.append(("made", settings.ideas["merge_into"]))
            self.bus = bus

        def start(self, slug):
            seen.append(("start", slug))

        def stop(self, slug):
            seen.append(("stop", slug))

        def tick(self):
            seen.append(("tick",))

        def stop_all(self):
            seen.append(("stop_all",))

    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", types.SimpleNamespace(IdeaRunner=FakeRunner))
    slug = _add(host, "x")["slug"]
    _plan(host, slug)
    host.command("ideas.start", {"slug": slug})
    assert seen[:2] == [("made", "dev"), ("start", slug)]
    assert ideas.plan(host.ideas.state_dir, slug)["passed_at"]
    assert host.command("ideas.page", {"slug": slug})["state"] == "working"
    host.ideas.tick(1000.0)
    assert ("tick",) in seen
    host.command("ideas.stop", {"slug": slug})
    host.command("halt")
    assert ("stop", slug) in seen and ("stop_all",) in seen


def test_a_secret_todo_is_stored_and_the_plan_says_stored(host):
    slug = _add(host, "x")["slug"]
    _plan(host, slug, [
        {"id": "t1", "title": "API_KEY", "kind": "secret", "why": "w", "choices": [], "steps": [], "for": ["k1"],
         "done": False, "value": None},
        {"id": "t2", "title": "Which", "kind": "choice", "why": "w", "choices": ["a", "b"], "steps": [], "for": [],
         "done": False, "value": None}])
    today = [n["todo"] for n in host.command("ideas.board")["needs_you"] if n["kind"] == "todo"]   # spec 35 §10
    assert [t["id"] for t in today] == ["t1", "t2"] and "value" not in today[0]
    with pytest.raises(CommandError, match="needs its value"):
        host.command("ideas.todo", {"idea": slug, "id": "t1", "done": True})
    host.command("ideas.todo", {"idea": slug, "id": "t1", "done": True, "value": "sk-secret"})
    plan_text = (host.ideas.state_dir / "ideas" / slug / "plan.json").read_text()
    assert "sk-secret" not in plan_text and json.loads(plan_text)["todos"][0]["value"] == "stored"
    assert idea_secrets.get(host.ideas.state_dir, slug, "t1") == "sk-secret"
    assert json.loads(plan_text)["tasks"][0]["state"] == "ready"
    with pytest.raises(CommandError, match="choices"):
        host.command("ideas.todo", {"idea": slug, "id": "t2", "done": True, "value": "c"})
    host.command("ideas.todo", {"idea": slug, "id": "t2", "done": True, "value": "b"})
    assert [n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "todo"] == []
    host.command("ideas.drop", {"slug": slug})
    assert idea_secrets.get(host.ideas.state_dir, slug, "t1") is None


def test_the_snapshot_carries_focus_and_the_phone_hears_an_idea(host):
    snap = host.snapshot()
    assert snap["focus"] == "board" and "ideas_rev" in snap and snap["needs_you"] == 0
    before = BoardPhone.phone_snapshot(host)
    assert before["focus"] == "board" and before["needs_you"] == 0
    slug = _add(host, "phone idea")["slug"]
    mid = BoardPhone.phone_snapshot(host)
    assert mid["ideas_rev"] > before["ideas_rev"] and mid["rev"] != before["rev"]
    assert [i["state"] for i in mid["idea_states"] if i["slug"] == slug] == ["raw"]     # raw: nothing asks yet
    ideas.save_state(host.ideas.state_dir, slug, state="asks")
    host.ideas.changed(slug)
    after = BoardPhone.phone_snapshot(host)
    assert after["needs_you"] == 1 and after["rev"] != mid["rev"]                        # the phone gets it
    assert {"slug": slug, "title": "phone idea", "state": "asks"} in after["idea_states"]
    assert BoardPhone.phone_snapshot(host)["rev"] == after["rev"]                        # once: nothing new to push


def test_the_runner_bus_hops_to_the_hosts_thread(host):
    hops = []
    host.town.call = lambda fn, *a: hops.append(fn)
    gui_ideas._Hop(host.board).publish(idea_keeper.CHANGED, slug="x")       # the shown project's Board, on the host's call
    rev = host.ideas.rev
    assert len(hops) == 1
    hops[0]()
    assert host.ideas.rev == rev + 1


def test_a_lost_reading_shows_as_new(host):
    slug = _add(host, "x")["slug"]
    ideas.save_state(host.ideas.state_dir, slug, state="reading")     # the host closed while the keeper read
    assert host.command("ideas.page", {"slug": slug})["state"] == "raw"


def test_the_snapshot_writes_nothing_into_a_town_that_has_no_board_yet(host):
    host.snapshot()
    assert not (Path(host.town.repo_root) / "llm-wiki").exists()


# -- spec 33: Review, Agents, the top bar's limits ---------------------------------------------------------

from orkboard.sources.limits import Limit
import datetime as dt


def _review(host, slug="r", tests=None, state="review", **more):
    """An idea with one task in `state`, as the runner leaves it."""
    ideas.add_idea(host.ideas.root(), "A review idea", "general", host.ideas.state_dir)
    slug = ideas.ideas(host.ideas.root())[-1]["slug"]
    _plan(host, slug)
    ideas.edit_plan(host.ideas.state_dir, slug, lambda p: p["tasks"][0].update(
        state=state, branch=f"idea/{slug}/k1", round=2, finished="2026-10-17T10:00:00", cost=0.42,
        tests=tests or {"passed": 20, "failed": 0, "failing": [], "tail": "20 passed", "green": True},
        diff={"files": 14, "added": 320, "removed": 41}, **more))
    return slug


def test_review_list_has_the_spec_shape_and_the_phones_may_call_it(host):
    empty = host.command("ideas.review_list")
    assert {k: empty[k] for k in ("into", "push", "results")} == {"into": "dev", "push": False, "results": []}
    assert "dev" in empty["branches"]                       # the branch it merges into is always offered
    slug = _review(host)
    got = host.command("ideas.review_list")
    json.dumps(got)
    (r,) = got["results"]
    assert set(r) == {"idea", "idea_title", "task", "title", "round", "tests", "diff", "cost", "conflict", "finished",
                      "work", "rework", "estimate", "over"}       # spec 36 §4
    assert r["idea"] == slug and r["task"] == "k1" and r["round"] == 2 and r["diff"]["files"] == 14
    assert BoardPhone.allowed(host, "ideas.merge", {"slug": slug, "task": "k1"})


def test_a_check_s_result_has_the_checker_and_its_findings_and_another_task_s_has_neither(host):
    """Spec 43 A: a row of a check task gains `check` (the checker's name) and `findings`."""
    found = [{"where": "a.py:1", "what": "a bug", "fixed": False}, {"where": "b.py:2", "what": "another", "fixed": True}]
    plain = _review(host)
    (r,) = host.command("ideas.review_list")["results"]
    assert "check" not in r and "findings" not in r
    slug = _review(host, kind="review", role="reviewer", findings=found, note="1 left")
    rows = {x["idea"]: x for x in host.command("ideas.review_list")["results"]}
    assert rows[slug]["check"] == "Reviewer" and rows[slug]["findings"] == found and "check" not in rows[plain]
    other = _review(host, kind="security", findings=[])                     # a role of another slug: the checker of its tag
    assert {x["idea"]: x for x in host.command("ideas.review_list")["results"]}[other]["check"] == "Security reviewer"


def test_the_snapshot_counts_results_and_the_phone_is_pushed_when_one_arrives(host):
    before = BoardPhone.phone_snapshot(host)
    assert before["review_count"] == 0
    slug = _review(host)
    host.ideas.changed(slug)
    after = BoardPhone.phone_snapshot(host)
    assert after["review_count"] == 1 and after["review_results"] == [{"idea": slug, "task": "k1", "title": "Do it"}]
    assert after["rev"] != before["rev"]                                                 # the phone is pushed
    assert BoardPhone.phone_snapshot(host)["rev"] == after["rev"]                        # once


def test_the_limits_are_the_smallest_remaining_of_each_installed_tools_rows(host, monkeypatch):
    soon = dt.datetime(2026, 10, 17, 18, 0)
    rows = [Limit("claude", "", "session", 0.62, soon), Limit("claude", "", "weekly", 0.9, None),
            Limit("agy", "Pro", "daily", 0.4, soon), Limit("agy", "Flash", "daily", 0.7, soon),
            Limit("codex", "", "", None, None, "not installed"), Limit("limits", "—", "—", None, None, "off")]
    monkeypatch.setattr(host, "limits", lambda: rows)
    got = host.snapshot()["limits"]
    assert [x["provider"] for x in got] == ["claude", "agy"]
    claude = got[0]
    assert claude["name"] == "Claude" and claude["left"] == 0.62
    assert claude["rows"][0] == {"window": "5h", "left": 0.62, "reset": "2026-10-17T18:00"}
    assert claude["rows"][1]["window"] == "week" and got[1]["left"] == 0.4
    assert BoardPhone.phone_snapshot(host)["limits"][0]["left"] == 0.62


def test_a_tool_turned_on_whose_limits_were_not_read_stays_and_says_why(host, monkeypatch):
    # the owner's 19 October: Claude was missing from the limits without a word; a tool not turned on stays out
    rows = [Limit("agy", "Pro", "daily", 0.4, None), Limit("claude", "", "", None, None, "Not logged in · Please run /login"),
            Limit("codex", "", "", None, None, "not installed")]
    monkeypatch.setattr(host, "limits", lambda: rows)
    host.machine.tools["claude"].enabled, host.machine.tools["codex"].enabled = True, False
    got = host.snapshot()["limits"]
    assert [(x["provider"], x["left"]) for x in got] == [("claude", None), ("agy", 0.4)]
    assert got[0] == {"provider": "claude", "name": "Claude", "left": None, "error": "Not logged in · Please run /login",
                      "rows": []}
    host.ideas.log_limits(force=True)                                    # an unread tool logs no limits_read
    rows[:1] = [Limit("agy", "Gemini Models", "weekly", 0.87, None), Limit("agy", "Claude and GPT models", "session", 1.0, None)]
    agy = host.snapshot()["limits"][1]                                   # a tool with groups: each row says whose
    assert [r["window"] for r in agy["rows"]] == ["Gemini Models · week", "Claude and GPT models · 5h"]


def test_a_draft_the_tool_failed_says_why_on_the_page_not_as_its_error(host, monkeypatch):
    # the owner's 19 October: the page's `error` read as the command's own, so it toasted on every refresh and the
    # idea never opened; the line is the tool's failure in plain words, with what to do
    said = json.dumps({"type": "result", "is_error": True, "subtype": "success", "result": "Not logged in · Please run /login",
                       "usage": {"input_tokens": 0, "output_tokens": 0}})

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        raise tool_run.failure(harness, 1, said, "")

    monkeypatch.setattr(jobs, "run_read", run_read)
    slug = _add(host, "Dark mode", night=False)["slug"]                  # Normal: drafted at once
    _wait(host, slug)
    page = host.command("ideas.page", {"slug": slug})
    assert "error" not in page and page["state"] == "raw"
    assert page["state_error"].startswith("Claude Code is not signed in, or its sign-in has expired.")
    assert "Not logged in · Please run /login" in page["state_error"] and "{" not in page["state_error"]


def test_agents_shows_the_taskmaster_and_a_chip_per_live_task(host):
    first = host.command("ideas.agents")
    assert first["done_today"] == [] and [r["role"] for r in first["roles"]] == ["taskmaster", "grunt"]
    assert {k: first["roles"][0][k] for k in ("name", "state", "waits_on", "chips")} == {
        "name": "Taskmaster", "state": "waiting", "waits_on": None, "chips": []}
    assert first["roles"][1]["name"] == "Grunts" and first["roles"][1]["chips"] == []      # spec 34: a block per role
    slug = _review(host)
    ideas.save_state(host.ideas.state_dir, slug, state="working")
    other = _add(host, "asking idea")["slug"]
    ideas.save_state(host.ideas.state_dir, other, state="asks")
    got = host.command("ideas.agents")
    tm, grunts = got["roles"][:2]
    assert tm["state"] == "waiting" and tm["waits_on"]["idea"] == other and "asking idea" in tm["waits_on"]["text"]
    assert tm["chips"] == [{"idea": other, "title": "asking idea", "short": "Asking idea", "state": "waiting"}]
    (chip,) = grunts["chips"]
    assert chip["state"] == "review" and chip["task"] == "k1" and chip["idea"] == slug and chip["tier"] == "warrior"
    assert chip["head"] == {"craft": "engineering", "race": "peon", "tier": "warrior"}            # a Grunt, an ork (decisions §53)
    assert tm["head"] == {"craft": "engineering", "race": "peon", "tier": "elder"} and grunts["head"]["race"] == "peon"
    assert host.command("ideas.task", {"slug": slug, "task": "k1"})["head"] == chip["head"]           # the task, the plan: the same head
    assert host.command("ideas.page", {"slug": slug})["plan"]["tasks"][0]["head"] == chip["head"]
    ideas.edit_plan(host.ideas.state_dir, slug, lambda p: p["tasks"][0].update(
        state="merged", finished=dt.datetime.now().isoformat(timespec="seconds")))
    got = host.command("ideas.agents")
    assert got["roles"][1]["chips"] == [] and got["done_today"] == [{"idea": slug, "task": "k1", "title": "Do it", "role": "grunt"}]


def test_task_returns_its_fields_idea_title_and_log(host):
    slug = _review(host)
    got = host.command("ideas.task", {"slug": slug, "task": "k1"})
    assert got["id"] == "k1" and got["idea_title"] == "A review idea" and got["log"] == "" and got["round"] == 2
    with pytest.raises(CommandError, match="gone"):
        host.command("ideas.task", {"slug": slug, "task": "zz"})


def test_the_answers_at_review_reach_the_runner_and_its_refusals_are_plain_words(host, monkeypatch):
    seen = []

    class FakeRunner:
        def __init__(self, *a, **k):
            pass

        def merge(self, slug, tid, device=""):
            seen.append(("merge", slug, tid))
            return "abc123"

        def back(self, slug, tid, why, device=""):
            seen.append(("back", slug, tid, why))

        def drop_task(self, slug, tid, device=""):
            seen.append(("drop", slug, tid))

        def stop_task(self, slug, tid, device=""):
            seen.append(("stop", slug, tid))

        def log(self, slug, tid):
            return "the log"

    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", types.SimpleNamespace(IdeaRunner=FakeRunner))
    slug = _review(host)
    a = {"slug": slug, "task": "k1"}
    assert host.command("ideas.merge", a) == {"ok": True, "commit": "abc123"}
    assert host.command("ideas.back", {**a, "why": "rename it"}) == {"ok": True}
    assert host.command("ideas.drop_task", a) == {"ok": True} and host.command("ideas.stop_task", a) == {"ok": True}
    assert seen == [("merge", slug, "k1"), ("back", slug, "k1", "rename it"), ("drop", slug, "k1"),
                    ("stop", slug, "k1")]
    assert host.command("ideas.task", a)["log"] == "the log"
    with pytest.raises(CommandError, match="why is missing"):
        host.command("ideas.back", a)

    class Refusing(FakeRunner):
        def merge(self, slug, tid, device=""):
            raise type("RunnerError", (Exception,), {})("Its tests are red: send it back")

    host.ideas._runner = Refusing()
    with pytest.raises(CommandError, match="tests are red"):
        host.command("ideas.merge", a)


def test_into_sets_the_branch_made_when_missing_and_the_push_switch(host):
    import subprocess
    root = Path(host.town.repo_root)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@x", "commit", "-q", "--allow-empty", "-m", "start"],
                   cwd=root, check=True)
    assert host.command("ideas.into", {"branch": "next"}) == {"ok": True}
    assert host.command("ideas.review_list")["into"] == "next"
    assert subprocess.run(["git", "rev-parse", "--verify", "next"], cwd=root, capture_output=True).returncode == 0
    host.command("ideas.into", {"push": True})
    assert host.command("ideas.review_list")["push"] is True and host.command("ideas.review_list")["into"] == "next"
    with pytest.raises(CommandError):
        host.command("ideas.into", {"branch": "bad name"})
    with pytest.raises(CommandError, match="branch is missing"):
        host.command("ideas.into", {})


# -- spec 33 §9: every action logged ----------------------------------------------------------------------------

import io
import zipfile

from orkboard.realm import event_log


def _events(host, *names):
    return [r for r in event_log.read(Path(host.town.repo_root)) if not names or r["event"] in names]


def test_each_action_writes_its_event_with_its_fields_and_the_device(host):
    slug = _add(host, "Dark mode for the night")["slug"]
    (e,) = _events(host, "idea_added")
    assert e["idea"] == slug and e["track"] == "first-goal" and e["chars"] == 23 and e["device"] == "desktop"
    host.command("ideas.say", {"slug": slug, "text": "Does it follow the system?", "section": "Risks", "device": "phone"})
    _wait(host, slug)
    (e,) = _events(host, "idea_said")
    assert e["section"] == "Risks" and e["text"] == "Does it follow the system?" and e["chars"] == 26 and e["device"] == "phone"
    assert e["device"] == "phone"                                   # the phone listener puts it there (BoardPhone.guard)
    assert BoardPhone.guard("ideas.say", {"slug": "x", "device": "desktop"}, {"id": "p", "name": "P"})["device"] == "phone"
    host.command("ideas.into", {"push": True})
    (e,) = _events(host, "into_changed")
    assert e["branch"] == "dev" and e["push"] is True and e["device"] == "desktop"


def test_the_keepers_states_and_the_plan_are_logged_and_a_secret_never(host, monkeypatch):
    slug = _add(host, "x")["slug"]
    todos = [{"id": "t1", "title": "API_KEY", "kind": "secret", "why": "", "choices": [], "steps": [], "for": ["k1"], "done": False, "value": None}]
    _plan(host, slug, todos)
    host.ideas.changed(slug)
    (made,) = _events(host, "plan_made")
    assert made["idea"] == slug and made["tasks"] == 1 and made["todos"] == 1 and made["usd_low"] == 0.15
    states = [(r["state"], r["was"]) for r in _events(host, "keeper_state")]
    assert ("plan", "raw") in states or states[-1][0] == "plan"

    class Runner:
        def __init__(self, *a, **k):
            pass

        def start(self, slug):
            pass

        def stop_all(self):
            pass
    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", types.SimpleNamespace(IdeaRunner=Runner))
    host.command("ideas.todo", {"idea": slug, "id": "t1", "done": True, "value": "s3cr3t-value"})
    (done,) = _events(host, "todo_done")
    assert done["todo"] == "t1" and done["kind"] == "secret" and done["seconds"] is not None
    host.command("ideas.start", {"slug": slug, "via": "map"})
    (passed,) = _events(host, "plan_passed")
    assert passed["idea"] == slug and passed["tasks"] == 1 and passed["seconds"] is not None
    assert passed["via"] == "map"                                               # spec 41 §4: Start on the Map
    host.command("halt")
    (stop,) = _events(host, "stop_all")
    assert stop["device"] == "desktop"
    assert "s3cr3t-value" not in event_log.path(Path(host.town.repo_root)).read_text()


def test_opened_goes_through_ideas_log_and_nothing_else_does(host):
    assert host.command("ideas.log", {"event": "opened", "what": "result", "ref": "sync/k2"}) == {"ok": True}
    (e,) = _events(host, "opened")
    assert (e["what"], e["ref"], e["device"]) == ("result", "sync/k2", "desktop")
    for bad in ({"event": "idea_added", "what": "idea"}, {"event": "stop_all"}, {"event": "nope"}, {"event": "opened", "what": "elsewhere"}):
        with pytest.raises(CommandError):
            host.command("ideas.log", bad)
    assert [e["event"] for e in _events(host)] == ["project_opened", "opened"]      # the host opened the project first


def test_the_logs_zip_holds_the_events_the_ideas_and_no_secret(host):
    slug = _add(host, "Logs idea")["slug"]
    _plan(host, slug)
    (host.ideas.state_dir / "ideas" / slug / "k1.log").write_text("== round 1\nthe key was ••••\n")
    host.command("ideas.log", {"event": "opened", "what": "tab", "ref": "review"})
    name, data = host.day_logs.pack_period(1)
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    assert "events.jsonl" in names and f"ideas/{slug}/plan.json" in names and f"ideas/{slug}/state.json" in names
    assert f"ideas/{slug}/k1.log" in names
    assert b'"event": "opened"' in z.read("events.jsonl")
    got = host.command("ideas.logs", {"days": 1})
    assert got["name"].endswith(".zip") and zipfile.ZipFile(io.BytesIO(__import__("base64").b64decode(got["data"]))).namelist()


def test_a_keeper_calls_record_names_its_idea_so_the_two_logs_join(tmp_path):
    from orkboard.realm import call_log
    call_log.keep_days(tmp_path)
    try:
        call_log.record({"ORKCRAFT_ORC": "board/keeper", "ORKCRAFT_IDEA": "dark-mode"}, "read", "claude", "m", "p", "o", "", 0, 1.0)
        call_log.record({"ORKCRAFT_ORC": "ideas/dark-mode-k1", "ORKCRAFT_IDEA": "dark-mode", "ORKCRAFT_TASK": "k1"}, "work", "claude", "m", "p", "o", "", 0, 1.0)
        lines = [x for b in (tmp_path / call_log.DAYS).rglob(call_log.LINES) for x in call_log.read(b.parent)]
    finally:
        call_log.keep_days(None)
    assert {(x.get("idea"), x.get("task")) for x in lines} == {("dark-mode", None), ("dark-mode", "k1")}


# -- spec 36 §4, §7: Review's cost against the plan, `dear`, `ideas.spend`, the roles' week and types ----------------

def test_a_result_has_its_cost_split_and_against_its_planned_share(host):
    from orkboard.realm import idea_spend
    slug = _review(host, ran_tier="warrior")
    state = host.ideas.state_dir
    for step, rnd, cost in (("task", 1, 0.3), ("task", 2, 0.1), ("fix", 2, 0.02)):
        idea_spend.append(state, idea_spend.line(step, "grunt", "claude", "sonnet", "warrior", "low", None, cost, "k1", rnd), idea=slug)
    (r,) = host.command("ideas.review_list")["results"]
    assert r["work"] == 0.3 and r["rework"] == 0.12
    assert r["estimate"] == {"low": 0.15, "high": 0.45} and r["over"] is None       # 0.42 a result, warrior's default
    ideas.edit_plan(state, slug, lambda p: p["tasks"][0].update(cost=0.9))
    assert host.command("ideas.review_list")["results"][0]["over"] == 2.0           # 0.9 / 0.45


def test_merge_sends_dear_only_when_it_is_ticked(host, monkeypatch):
    seen = []

    class FakeRunner:
        def __init__(self, *a, **k):
            pass

        def merge(self, slug, tid, device="", **more):
            seen.append(more)
            return "abc"

    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", types.SimpleNamespace(IdeaRunner=FakeRunner))
    slug = _review(host)
    host.command("ideas.merge", {"slug": slug, "task": "k1"})
    host.command("ideas.merge", {"slug": slug, "task": "k1", "dear": True})
    assert seen == [{}, {"dear": True}]
    with pytest.raises(CommandError, match="true or false"):
        host.command("ideas.merge", {"slug": slug, "task": "k1", "dear": "yes"})


def test_ideas_spend_gives_an_ideas_and_a_goals_money_and_the_phone_may_call_it(host):
    from orkboard.realm import idea_spend
    slug = _add(host, "an idea that costs")["slug"]
    goal = ideas.idea_page(host.ideas.root(), slug).get("track")
    state = host.ideas.state_dir
    idea_spend.append(state, idea_spend.line("draft", "taskmaster", "claude", "opus", "elder", "medium", None, 0.5), idea=slug)
    idea_spend.append(state, idea_spend.line("goal", "taskmaster", "claude", "opus", "elder", "medium", None, 0.25), goal=goal)
    got = host.command("ideas.spend", {"idea": slug})
    assert got["usd"] == 0.5 and got["stages"]["spec"]["usd"] == 0.5 and set(got) == {"usd", "unpriced", "stages", "tasks"}
    g = host.command("ideas.spend", {"goal": goal})
    assert g["usd"] == 0.75 and g["stages"]["goal"]["usd"] == 0.25 and g["merged"] == 0 and g["usd_per_merged"] is None
    for bad in ({"idea": "ghost"}, {"goal": "ghost"}, {}):
        with pytest.raises(CommandError):
            host.command("ideas.spend", bad)
    assert "ideas.spend" in host.commands and BoardPhone.allowed(host, "ideas.spend", {"idea": slug})


def test_roles_gain_their_types_week_and_hand_model_and_role_save_takes_types(host):
    from orkboard.realm import idea_spend
    idea_spend.forget()
    slug = host.command("ideas.role_save", {"name": "Scribe", "model": "", "max_parallel": 1,
                                            "instruction": "Write plainly.", "kinds": ["docs", "text"]})["slug"]
    got = {r["slug"]: r for r in host.command("ideas.roles")["roles"]}
    assert got[slug]["kinds"] == ["docs", "text"] and got[slug]["model"] == "" and got[slug]["hand_model"] is False
    assert got["grunt"]["kinds"] == [k for k in roles.TASK_KINDS if k not in ("docs", "text")] and got["taskmaster"]["kinds"] == []
    assert got["taskmaster"]["week"] == {"spent": 0, "plans": 0, "first_time": 0, "finished": 0, "merged": 0}
    assert got[slug]["week"] is None                                                # no task of its finished yet
    assert next(k for k in host.command("ideas.roles")["kinds"] if k["kind"] == "docs")["role"] == slug
    host.command("ideas.role_save", {"slug": slug, "name": "Scribe", "model": "", "max_parallel": 1, "kinds": ["docs"]})
    assert next(k for k in host.command("ideas.roles")["kinds"] if k["kind"] == "text")["role"] == "grunt"
    with pytest.raises(CommandError, match="600"):
        host.command("ideas.role_save", {"slug": slug, "name": "Scribe", "model": "", "max_parallel": 1, "instruction": "x" * 601})
    with pytest.raises(CommandError):
        host.command("ideas.role_save", {"slug": "grunt", "name": "Grunt", "model": "", "max_parallel": 8, "kinds": ["code"]})
    saved = _events(host, "role_saved")
    assert [(e["kinds"], e["instruction_chars"]) for e in saved] == [(["docs", "text"], 14), (["docs"], 0)]
    blocks = {b["role"]: b for b in host.command("ideas.agents")["roles"]}
    assert all("week" in b for b in blocks.values()) and blocks["taskmaster"]["week"]["plans"] == 0


def test_an_agents_craft_is_saved_and_every_role_says_the_head_it_wears(host):
    slug = host.command("ideas.role_save", {"name": "Layout", "model": "elder", "max_parallel": 1, "craft": "design"})["slug"]
    got = host.command("ideas.roles")
    mine = {r["slug"]: r for r in got["roles"]}
    assert mine[slug]["craft"] == "design" and mine[slug]["head"] == {"craft": "design", "race": "elf", "tier": "elder"}
    assert mine["grunt"]["head"] == {"craft": "engineering", "race": "peon", "tier": "warrior"}          # By Target, balance
    assert [(c["craft"], c["race"]) for c in got["crafts"]] == [("engineering", "peon"), ("design", "elf"), ("data", "goblin"),
                                                               ("marketing", "gnome"), ("product", "lich")]
    assert got["crafts"][2]["heads"] == {"": "warrior", "elder": "elder", "warrior": "warrior", "laborer": "laborer"}
    host.command("ideas.role_save", {"slug": slug, "name": "Layout", "model": "elder", "max_parallel": 1})
    assert {r["slug"]: r for r in host.command("ideas.roles")["roles"]}[slug]["craft"] == "design"             # kept when not sent
    assert _events(host, "role_saved")[-1]["craft"] == "design"
    for bad in ({"craft": "sorcery"}, {"craft": 3}, {"slug": "taskmaster", "name": "Taskmaster", "model": "elder", "craft": "data"}):
        with pytest.raises(CommandError):
            host.command("ideas.role_save", {"name": "X", "model": "", "max_parallel": 1, **bad})
    block = next(b for b in host.command("ideas.agents")["roles"] if b["role"] == slug)
    assert block["head"] == {"craft": "design", "race": "elf", "tier": "elder"}


def test_every_role_says_its_record_of_the_last_30_days_spec_42_d(host):
    from orkboard.realm import idea_spend
    root, state = host.ideas.root(), host.ideas.state_dir
    scribe = host.command("ideas.role_save", {"name": "Scribe", "model": "", "max_parallel": 1, "kinds": ["docs"]})["slug"]
    few = host.command("ideas.role_save", {"name": "Few", "model": "", "max_parallel": 1})["slug"]
    goal = ideas.add_track(root, "Docs goal")
    idea = ideas.add_idea(root, "Write the guide", goal, state)
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    tasks = [{"id": f"k{n}", "title": f"T{n}", "state": "merged", "round": 2 if n == 4 else 1, "role": scribe, "finished": now} for n in range(1, 5)]
    tasks += [{"id": "f1", "title": "F", "state": "merged", "round": 1, "role": few, "finished": now},
              {"id": "old", "title": "Old", "state": "merged", "round": 1, "role": scribe, "finished": "2020-01-01T00:00:00"}]
    folder = state / "ideas" / idea
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(json.dumps({"idea": idea, "tasks": tasks}))
    for n in range(1, 5):
        idea_spend.append(state, idea_spend.line("task", scribe, "claude", "m", "warrior", "", None, 0.5, f"k{n}", 1), idea=idea)
    idea_spend.append(state, idea_spend.line("plan", "taskmaster", "claude", "m", "elder", "", None, 0.2), idea=idea)
    idea_spend.forget()
    got = {r["slug"]: r for r in host.command("ideas.roles")["roles"]}
    json.dumps(got)
    assert got[scribe]["record"] == {"days": 30, "finished": 4, "merged": 4, "first_time": 3, "usd_per_merged": 0.5}
    assert got[few]["record"] == {"days": 30, "finished": 1, "merged": 1, "first_time": 1, "usd_per_merged": None}     # under TOO_FEW: no price
    assert got["grunt"]["record"] is None                                                                          # no row
    assert got["taskmaster"]["record"] == {"days": 30, "plans": 1, "finished": 5, "first_time": 4}                    # of its plans' tasks


# -- spec 49 A: the reserve, each role's tool, where a press was -------------------------------------------------------

def _night_around(hours: float) -> str:
    """A night window `hours` from now, an hour long (HH:MM-HH:MM, local time; it may cross midnight)."""
    now = dt.datetime.now()
    return f"{now + dt.timedelta(hours=hours):%H:%M}-{now + dt.timedelta(hours=hours + 1):%H:%M}"


def test_the_snapshot_carries_the_reserve_by_day_and_inside_the_night_window_and_the_phones_rev_follows(host):
    host.ideas.save_settings({**host.ideas.settings_now(), "night": _night_around(2), "reserve_day": 0.25, "reserve_night": 0.05})
    day = host.snapshot()
    assert day["reserve"] == {"share": 0.25, "night": False}
    phone = BoardPhone.phone_snapshot(host)
    assert phone["reserve"] == {"share": 0.25, "night": False}
    host.ideas.save_settings({**host.ideas.settings_now(), "night": _night_around(-0.5)})      # now is inside it: no change of the Board
    night = host.snapshot()
    assert night["reserve"] == {"share": 0.05, "night": True} and night["ideas_rev"] == day["ideas_rev"]
    moved = BoardPhone.phone_snapshot(host)
    assert moved["reserve"] == {"share": 0.05, "night": True} and moved["rev"] != phone["rev"]   # the phone is sent it again
    assert BoardPhone.phone_snapshot(host)["rev"] == moved["rev"]
    json.dumps(moved)


def test_the_reserve_is_the_default_shares_until_the_person_changes_them(host):
    host.ideas.save_settings({**host.ideas.settings_now(), "night": _night_around(2)})
    assert host.snapshot()["reserve"] == {"share": 0.3, "night": False}
    host.ideas.save_settings({**host.ideas.settings_now(), "night": _night_around(-0.5)})
    assert host.snapshot()["reserve"] == {"share": 0.1, "night": True}
    assert Orkboard().snapshot()["reserve"] == {"share": 0.3, "night": False}                  # no project open: the day's


def test_every_role_says_the_tool_it_runs_on_and_the_taskmasters_is_the_keepers(host, monkeypatch):
    from orkboard.core import idea_runner
    from orkboard.realm import harnesses
    host.command("ideas.role_save", {"name": "Scribe", "model": "", "max_parallel": 1, "kinds": ["docs"]})
    claude = {"id": "claude", "name": "Claude"}
    assert idea_runner.HARNESS == idea_keeper.HARNESS == "claude" and harnesses.title("claude") == "Claude Code"
    for got in (host.command("ideas.roles")["roles"], host.command("ideas.agents")["roles"]):
        assert len(got) == 3 and all(r["harness"] == claude for r in got)
    monkeypatch.setattr(idea_keeper, "HARNESS", "codex")
    monkeypatch.setattr(idea_runner, "HARNESS", "agy")
    for got, key in ((host.command("ideas.roles")["roles"], "slug"), (host.command("ideas.agents")["roles"], "role")):
        by = {r[key]: r["harness"] for r in got}
        assert by["taskmaster"] == {"id": "codex", "name": "Codex"}
        assert by["grunt"] == by["scribe"] == {"id": "agy", "name": "Antigravity"}


def test_a_start_or_a_queue_says_where_the_press_was_when_it_is_one_of_via(host, monkeypatch):
    from orkboard.gui import ideas_args

    class Runner:
        def __init__(self, *a, **k):
            pass

        def start(self, slug):
            pass

        def tick(self):
            pass

        def stop_all(self):
            pass
    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", types.SimpleNamespace(IdeaRunner=Runner))
    assert gui_ideas.VIA is ideas_args.VIA and {"hand", "party", "today", "gate"} <= set(gui_ideas.VIA)
    assert {"gate", "today"} <= set(gui_ideas.OPENED)
    assert [ideas_args._via({"via": v}) for v in gui_ideas.VIA] == list(gui_ideas.VIA)           # a press from anywhere VIA names
    assert [ideas_args._via(a) for a in ({}, {"via": ""}, {"via": "elsewhere"}, {"via": None}, {"via": 3}, {"via": ["map"]})] == ["idea"] * 6
    first, second, third = (_add(host, f"idea {n}")["slug"] for n in (1, 2, 3))
    _plan(host, first)
    host.command("ideas.start", {"slug": first, "via": "hand"})
    host.command("ideas.queue", {"slug": second, "queue": "night", "via": "party"})
    host.command("ideas.queue", {"slug": third, "queue": "night", "via": "map"})
    _plan(host, second)
    ideas.edit_plan(host.ideas.state_dir, second, lambda p: p.update(start_at="night"))
    ideas.save_state(host.ideas.state_dir, second, state="plan")
    host.command("ideas.start_now", {"slug": second, "via": "today"})
    assert [(e["idea"], e["via"]) for e in _events(host, "plan_passed")] == [(first, "hand")]
    assert [(e["idea"], e["via"]) for e in _events(host, "idea_queued")] == [(second, "party"), (third, "map")]
    assert [(e["idea"], e["via"]) for e in _events(host, "plan_started_now")] == [(second, "today")]


def test_the_gate_and_the_strip_are_opened_and_logged_through_ideas_log(host):
    for what, via in (("gate", "hand"), ("gate", "gate"), ("today", "today"), ("idea", "party"), ("task", "hand"), ("result", "map")):
        assert host.command("ideas.log", {"event": "opened", "what": what, "ref": "x", "via": via}) == {"ok": True}
    assert [(e["what"], e["via"]) for e in _events(host, "opened")] == [
        ("gate", "hand"), ("gate", "gate"), ("today", "today"), ("idea", "party"), ("task", "hand"), ("result", "map")]
    with pytest.raises(CommandError, match="hand"):
        host.command("ideas.log", {"event": "opened", "what": "gate", "via": "elsewhere"})
    with pytest.raises(CommandError, match="gate, today"):
        host.command("ideas.log", {"event": "opened", "what": "elsewhere"})


# -- spec 50 A: a goal's element and flag, and no acceptance by itself -----------------------------------------------------------

def test_a_new_goal_answers_with_its_element_and_every_card_of_it_will_wear_it(host):
    first, second = _add(host, "Dark mode for the night"), _add(host, "Larger text")
    assert (first["element"], second["element"]) == ("meadow", "ice") and set(first) == {"slug", "queue", "element", "type", "joined"}
    assert ideas.state(host.ideas.state_dir, first["slug"])["element"] == "meadow"
    nodes = {n["slug"]: n["element"] for n in host.command("ideas.map", {})["nodes"]}
    assert nodes == {first["slug"]: "meadow", second["slug"]: "ice"}


def test_ideas_flags_gains_the_goals_flags_every_partys_newest_first_and_keeps_the_old_ones(host):
    from orkboard.realm import idea_flag
    assert host.command("ideas.flags", {}) == {"flags": [], "goals": []}
    a, b, c = _add(host, "Dark mode for the night")["slug"], _add(host, "Larger text")["slug"], _add(host, "Not flagged")["slug"]
    other = ideas.add_track(host.ideas.root(), "Second party")
    d = host.command("ideas.add", {"text": "In another party", "track": other, "night": True})["slug"]
    state, root = host.ideas.state_dir, host.ideas.root()
    for slug, at in ((a, "2026-10-19T09:00:00"), (b, "2026-10-21T09:00:00"), (d, "2026-10-20T09:00:00")):
        idea_flag.raise_flag(root, state, slug, "gate", "c" * 40)
        path = ideas.state_folder(state, slug) / "flag.json"
        path.write_text(json.dumps({**json.loads(path.read_text()), "at": at}))
    got = host.command("ideas.flags", {})
    json.dumps(got)
    assert got["flags"] == [] and [g["slug"] for g in got["goals"]] == [b, d, a]                      # newest first, every party's
    assert got["goals"][0] == {"slug": b, "title": "Larger text", "short": "Larger text", "goal": "first-goal", "element": "ice",
                               "at": "2026-10-21T09:00:00", "tasks": 0, "first_time": 0, "usd": None, "days": got["goals"][0]["days"]}
    assert got["goals"][1]["goal"] == "second-party" and c not in {g["slug"] for g in got["goals"]}


def test_nothing_accepts_a_party_when_its_goals_are_all_done(host, monkeypatch):
    called = []
    monkeypatch.setattr(host.ideas.keeper, "accept_goal", lambda slug: called.append(slug))
    slug = _add(host, "Dark mode for the night")["slug"]
    ideas.save_state(host.ideas.state_dir, slug, state="working")
    host.ideas.changed(slug)                                                                          # seen at work …
    ideas.save_state(host.ideas.state_dir, slug, state="done")
    host.ideas.changed(slug)                                                                          # … then done: the party's last goal
    assert called == [] and not hasattr(host.ideas, "_accept_when_done")
    assert "ideas.goal_accept" in host.commands                                                       # asked for a party of before, it stays


def test_what_the_host_says_to_a_person_says_party_for_the_container_and_goal_for_the_idea_spec_50(host):
    """Spec 50 §2.6: errors the host sends a face are in today's words (decisions §63); keys, commands and prompts keep the code's."""
    def says(command: str, args: dict) -> str:
        with pytest.raises(CommandError) as err:
            host.command(command, args)
        return str(err.value)

    assert says("ideas.add", {"text": "x"}) == "A goal needs a party"
    assert says("ideas.add", {"text": "x", "track": "general"}) == "A goal needs a party"
    assert says("ideas.add", {"text": "x", "track": "nope"}) == "That party is gone"
    assert says("ideas.page", {"slug": "nope"}) == "That goal is gone"
    assert says("ideas.start", {"slug": "nope"}) == "This goal has no plan yet: Take it to work first"
    assert says("ideas.map", {"goal": "nope"}) == says("ideas.goal", {"slug": "nope"}) == says("ideas.party", {"goal": "nope"}) == "That party is gone"
    assert says("ideas.words", {"track": "nope"}) == says("ideas.spend", {"goal": "nope"}) == "That party is gone"
    assert says("ideas.spend", {"idea": "nope"}) == says("ideas.read_stop", {"slug": "nope"}) == "That goal is gone"
    assert says("ideas.move", {"slug": "nope"}) == "No goal 'nope'" and says("ideas.edit", {"slug": "nope", "priority": "high"}) == "Priority is High, Normal or Low"
    slug = _add(host, "Dark mode for the night")["slug"]
    assert says("ideas.move", {"slug": slug, "track": "nope"}) == "No party 'nope'"
    with pytest.raises(ValueError, match="^A party needs a title$"):
        ideas.add_track(host.ideas.root(), " ")
    assert says("ideas.goal_save", {"title": "", "about": ""}) == "A party needs a description, or at least a title"
    host.ideas.keeper._busy[slug] = "reading"
    assert says("ideas.drop", {"slug": slug}) == "The keeper is busy with this goal: a moment"
    assert says("ideas.edit", {"slug": slug, "section": "Gist", "text": "x"}) == "The keeper is writing this goal: a moment"
    with pytest.raises(idea_keeper.KeeperError, match="^The keeper is busy with this goal: a moment$"):
        host.ideas.keeper._claim(slug, "draft")
    host.ideas.keeper._busy.pop(slug)
    host.ideas.keeper._busy["goal:first-goal"] = "reading"
    with pytest.raises(idea_keeper.KeeperError, match="^The keeper is busy with this party: a moment$"):
        host.ideas.keeper._claim("goal:first-goal", "goal")


# -- spec 52 A: New goal by its type, its asks, who joins; a plan's missing ---------------------------------------------------

from orkboard.realm import goal_team, goal_types, library     # noqa: E402


def _party(host, team=(), leader="taskmaster", title="Ship"):
    """A party with its leader and team as Edit the party keeps them (no reading: no model)."""
    root, state = host.ideas.root(), host.ideas.state_dir
    slug, _new = ideas.save_goal(root, None, title, "About " + title, None, "normal")
    library.install(state, [s for s in (*team, leader) if library.get(s) is not None])
    goal_team.set_team(root, slug, list(team), leader=leader)
    return slug


def _new(host, party, text="A goal", **more):
    """A goal added at the press of Add the goal; Low, so nothing is drafted (no model)."""
    return host.command("ideas.add", {"text": text, "track": party, "priority": "low", **more})


def _says(host, command, args):
    with pytest.raises(CommandError) as err:
        host.command(command, args)
    return str(err.value)


def test_a_goal_of_a_type_keeps_its_key_and_another_leaders_type_is_refused(host):
    ship = _party(host, leader="architect")
    got = _new(host, ship, type="restructure")
    assert got["type"] == "architect/restructure" and got["joined"] is None and set(got) == {"slug", "queue", "element", "type", "joined"}
    assert ideas.state(host.ideas.state_dir, got["slug"])["type"] == "architect/restructure"
    blank = _new(host, ship, "A blank one")
    assert blank["type"] == "" and ideas.state(host.ideas.state_dir, blank["slug"])["type"] == ""
    assert _says(host, "ideas.add", {"text": "x", "track": ship, "type": "logo"}) == "Ship's leader has no goal type “logo”"
    other = _party(host, title="Other")
    host.command("ideas.move", {"slug": got["slug"], "track": other})
    assert ideas.state(host.ideas.state_dir, got["slug"])["type"] == "architect/restructure"      # a goal moved keeps its own


def test_the_asks_are_written_after_the_goals_text_in_the_types_order(host):
    ship = _party(host, leader="product-designer")
    got = _new(host, ship, "A logo for the app", type="logo", asks={"refs": "  dribbble.com/a\n  b.png ", "says": " calm,  quick, ours ", })
    page = ideas.idea_page(host.ideas.root(), got["slug"])
    assert page.section("Gist") == "A logo for the app\n\nWhat it should say: calm, quick, ours\nRefs: dribbble.com/a b.png"
    assert page.title == "A logo for the app"
    bug = _new(host, _party(host, title="Bugs"), "The login breaks", type="bug",
               asks={"expected": "I am in", "did": "1. Open 2. Sign in", "happened": "  ", })
    assert ideas.idea_page(host.ideas.root(), bug["slug"]).section("Gist") == (
        "The login breaks\n\nWhat you did: 1. Open 2. Sign in\nWhat should have: I am in")            # an empty one left out
    long = _new(host, ship, "Long", type="icon", asks={"where": "x" * 400})
    assert ideas.idea_page(host.ideas.root(), long["slug"]).section("Gist").endswith("Where it shows: " + "x" * 300)
    assert _says(host, "ideas.add", {"text": "x", "track": ship, "type": "logo", "asks": {"who": "me"}}) == "New logo has no field “who”"
    assert _says(host, "ideas.add", {"text": "x", "track": "bugs", "type": "bug", "asks": {"refs": "a"}}) == "Fix a bug has no field “refs”"
    assert _says(host, "ideas.add", {"text": "x", "track": ship, "asks": {"says": "a"}}) == "A goal with no type has no fields of its own"
    assert _says(host, "ideas.add", {"text": "x", "track": ship, "type": "logo", "asks": ["a"]}) == "asks are the goal type's fields, by their ids"


def test_a_free_seat_joins_the_party_before_the_goal_is_added(host):
    ship = _party(host, ["grunt"], leader="product-designer")
    got = _new(host, ship, "A logo", type="logo", join={"add": "artist"})
    assert got["joined"] == {"add": "artist", "out": ""}
    assert goal_team.team_of(host.ideas.root(), ship) == ["grunt", "artist"] and roles.role(host.ideas.state_dir, "artist") is not None
    (saved,) = _events(host, "goal_saved")
    assert (saved["goal"], saved["joined"], saved["out"], saved["via"], saved["team"], saved["new"]) == (ship, "artist", "", "type", ["grunt", "artist"], False)
    (added,) = _events(host, "idea_added")
    assert (added["type"], added["asks"], added["refs"], added["joined"], added["out"]) == ("product-designer/logo", 0, 0, "artist", "")
    assert _says(host, "ideas.add", {"text": "x", "track": ship, "type": "logo", "join": {"add": "artist"}}) == "Artist is not what this goal misses"
    assert _says(host, "ideas.add", {"text": "x", "track": ship, "type": "screen", "join": {"add": "artist"}}) == "Artist is not what this goal misses"
    assert _says(host, "ideas.add", {"text": "x", "track": ship, "join": {"add": "ui-kit"}}) == "Design system designer is not what this goal misses"


def test_a_full_band_swaps_a_member_with_no_open_work_and_out_is_required(host, monkeypatch):
    ship = _party(host, ["grunt", "tester", "ui-kit"], leader="product-designer")
    busy = _new(host, ship, "Busy")["slug"]
    ideas.save_plan(host.ideas.state_dir, busy, {"idea": busy, "tasks": [{"id": "k1", "title": "t", "kind": "tests", "role": "tester", "state": "running"}], "todos": []})
    assert _says(host, "ideas.add", {"text": "x", "track": ship, "type": "icon", "join": {"add": "artist"}}) == "The party is full: pick who leaves"
    assert _says(host, "ideas.add", {"text": "x", "track": ship, "type": "icon", "join": {"add": "artist", "out": "tester"}}) == "Tester has work open: it cannot leave"
    assert _says(host, "ideas.add", {"text": "x", "track": ship, "type": "icon", "join": {"add": "artist", "out": "reviewer"}}) == "Reviewer is not one of the party's builders"
    assert goal_team.team_of(host.ideas.root(), ship) == ["grunt", "tester", "ui-kit"] and len(ideas.ideas(host.ideas.root(), ship)) == 1     # refused: nothing changed
    goal_team.set_team(host.ideas.root(), ship, ["grunt", "tester", "ui-kit"], every=["ui-kit"])
    got = _new(host, ship, "An icon", type="icon", join={"add": "artist", "out": "ui-kit"})
    assert got["joined"] == {"add": "artist", "out": "ui-kit"}
    assert goal_team.team_of(host.ideas.root(), ship) == ["grunt", "tester", "artist"] and goal_team.every_of(host.ideas.root(), ship) == []    # in its seat
    saved = _events(host, "goal_saved")[-1]
    assert (saved["joined"], saved["out"], saved["via"]) == ("artist", "ui-kit", "type")


def test_the_party_changes_before_the_goal_both_under_the_lock_and_never_for_tonight(host, monkeypatch):
    import threading
    seen = []

    def held() -> bool:
        free = []
        t = threading.Thread(target=lambda: free.append(ideas.LOCK.acquire(blocking=False) and (ideas.LOCK.release() or True)))
        t.start()
        t.join()
        return not free[0]

    set_team, add_idea = goal_team.set_team, ideas.add_idea
    monkeypatch.setattr(goal_team, "set_team", lambda *a, **k: (seen.append(("party", held())), set_team(*a, **k))[1])
    monkeypatch.setattr(ideas, "add_idea", lambda *a, **k: (seen.append(("goal", held())), add_idea(*a, **k))[1])
    ship = _party(host, ["grunt"], leader="product-designer")
    seen.clear()
    _new(host, ship, "A logo", type="logo", join={"add": "artist"})
    assert seen == [("party", True), ("goal", True)]
    seen.clear()
    kept = host.command("ideas.add", {"text": "Kept for tonight", "track": ship, "night": True, "type": "screen", "join": {"add": "ui-kit"}})
    assert seen == [("goal", True)] and kept["joined"] is None and kept["type"] == "product-designer/screen"
    assert goal_team.team_of(host.ideas.root(), ship) == ["grunt", "artist"]


class _Runner:
    started: list = []

    def __init__(self, *a, **k):
        pass

    def start(self, slug):
        _Runner.started.append(slug)

    def tick(self):
        pass

    def stop_all(self):
        pass


def _missing_plan(host, slug, tasks, missing):
    ideas.save_plan(host.ideas.state_dir, slug, {"idea": slug, "made_at": "2026-10-22T09:00:00", "passed_at": None, "todos": [],
                                                 "estimate": {"tasks": len(tasks)}, "tasks": tasks, "missing": missing})
    ideas.save_state(host.ideas.state_dir, slug, state="plan")


def test_add_and_start_joins_the_party_then_gives_the_tasks_not_started_their_new_member(host, monkeypatch):
    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", types.SimpleNamespace(IdeaRunner=_Runner))
    ship = _party(host, ["grunt"], leader="product-designer")
    slug = _new(host, ship, "A logo")["slug"]
    task = {"title": "t", "brief": "b", "tier": "warrior", "after": []}
    _missing_plan(host, slug, [{**task, "id": "k1", "kind": "art", "role": "grunt", "state": "ready"},
                               {**task, "id": "k2", "kind": "art", "role": "grunt", "state": "review"},
                               {**task, "id": "k3", "kind": "code", "role": "grunt", "state": "waiting"}],
                  [{"kind": "art", "agent": "artist"}])
    (row,) = [n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "plan"]
    assert row["missing"] == [{"kind": "art", "words": "pixel art", "agent": "artist", "name": "Artist", "band": "build", "free": True}]
    assert host.command("ideas.page", {"slug": slug})["plan"]["missing"] == row["missing"]                # the drawer's plan says the same
    assert _says(host, "ideas.start", {"slug": slug, "join": {"add": "ui-kit"}}) == "Design system designer is not what this plan misses"
    host.command("ideas.start", {"slug": slug, "join": {"add": "artist"}, "via": "hand"})
    assert goal_team.team_of(host.ideas.root(), ship) == ["grunt", "artist"]
    plan = ideas.plan(host.ideas.state_dir, slug)
    assert [t["role"] for t in plan["tasks"]] == ["artist", "grunt", "grunt"] and plan["passed_by"] == "person"     # in Review: as it was
    assert (_events(host, "goal_saved")[-1]["via"], _events(host, "goal_saved")[-1]["joined"]) == ("plan", "artist")
    passed = _events(host, "plan_passed")[-1]
    assert (passed["joined"], passed["missing"], passed["via"]) == ("artist", 1, "hand")


def test_add_and_start_is_refused_when_the_band_is_full_and_start_without_changes_no_one(host, monkeypatch):
    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", types.SimpleNamespace(IdeaRunner=_Runner))
    ship = _party(host, ["grunt", "tester", "ui-kit"], leader="product-designer")
    slug = _new(host, ship, "A logo")["slug"]
    _missing_plan(host, slug, [{"id": "k1", "title": "t", "brief": "b", "kind": "art", "role": "grunt", "state": "ready", "tier": "warrior", "after": []}],
                  [{"kind": "art", "agent": "artist"}])
    assert [n["missing"] for n in host.command("ideas.board")["needs_you"] if n["kind"] == "plan"][0][0]["free"] is False
    assert _says(host, "ideas.start", {"slug": slug, "join": {"add": "artist"}}) == "The party is full: change a member in Edit the party"
    assert ideas.plan(host.ideas.state_dir, slug)["passed_at"] is None
    host.command("ideas.start", {"slug": slug})                                                            # Start without
    assert goal_team.team_of(host.ideas.root(), ship) == ["grunt", "tester", "ui-kit"]
    assert ideas.plan(host.ideas.state_dir, slug)["tasks"][0]["role"] == "grunt"
    passed = _events(host, "plan_passed")[-1]
    assert (passed["joined"], passed["missing"]) == ("", 1) and not _events(host, "goal_saved")


def test_edit_the_party_logs_goal_saved_with_no_one_joined(host):
    ship = _party(host, ["grunt"])
    host.ideas._ev(event_log.GOAL_SAVED, {}, goal=ship, new=False)                   # as gui/ideas_goals.py's goal_save writes it
    (saved,) = _events(host, "goal_saved")
    assert (saved["joined"], saved["out"], saved["via"]) == ("", "", "")


def test_the_map_gives_a_partys_types_the_most_used_first_with_what_each_misses_and_a_goals_type(host):
    ship = _party(host, ["grunt"], leader="product-designer")
    for type_id in ("logo", "icon", "logo"):
        _new(host, ship, f"A {type_id}", type=type_id)
    moved = _new(host, _party(host, title="Other"), "A bug", type="bug")["slug"]
    host.command("ideas.move", {"slug": moved, "track": ship})                        # another leader's type: not counted here
    got = host.command("ideas.map", {"goal": ship})
    (party,) = got["goals"]
    assert [(t["id"], t["used"]) for t in party["types"]] == [("logo", 2), ("icon", 1), ("screen", 0), ("feature", 0)]
    logo = party["types"][0]
    assert {k: logo[k] for k in ("name", "sign", "lens", "refs")} == {"name": "New logo", "sign": "logo", "lens": "text", "refs": True}
    assert logo["asks"] == [{"id": "says", "label": "What it should say", "hint": "three words"}]
    assert [(m["agent"], m["free"], m["out"]) for m in logo["missing"]] == [("artist", True, [{"slug": "grunt", "name": "Grunt", "runs": 0}])]
    assert [m["agent"] for m in party["types"][2]["missing"]] == ["ui-kit"]
    nodes = {n["title"]: n["type"] for n in got["nodes"]}
    assert nodes["A logo"] == {"id": "logo", "name": "New logo", "sign": "logo"} and nodes["A bug"] == {"id": "bug", "name": "Fix a bug", "sign": "bug"}
    assert [t["id"] for t in host.command("ideas.map", {"goal": "other"})["goals"][0]["types"]] == ["feature", "bug", "tidy"]     # its bug moved out: the set's order


def _file_todo(tid="t1", **more):
    return {"id": tid, "title": "Reference picture", "kind": "file", "why": "w", "choices": [], "steps": [],
            "for": ["k1"], "done": False, "value": None, **more}


def _todo_of(host, slug, tid="t1"):
    plan = json.loads((host.ideas.state_dir / "ideas" / slug / "plan.json").read_text())
    return next(t for t in plan["todos"] if t["id"] == tid), plan


def test_a_to_do_of_each_kind_can_be_gone_without(host):
    slug = _add(host, "x")["slug"]
    _plan(host, slug, [
        _file_todo(),
        {"id": "t2", "title": "API_KEY", "kind": "secret", "why": "", "choices": [], "steps": [], "for": ["k1"], "done": False, "value": None},
        {"id": "t3", "title": "Which", "kind": "choice", "why": "", "choices": ["a", "b"], "steps": [], "for": ["k1"], "done": False, "value": None},
        {"id": "t4", "title": "Check it", "kind": "confirm", "why": "", "choices": [], "steps": [], "for": ["k1"], "done": False, "value": None}])
    for tid in ("t1", "t2", "t3", "t4"):
        host.command("ideas.todo", {"idea": slug, "id": tid, "done": True, "skip": True})
        todo, plan = _todo_of(host, slug, tid)
        assert todo["done"] is True and todo["skipped"] is True and todo["value"] is None
    assert plan["tasks"][0]["state"] == "ready"
    assert [e["skipped"] for e in _events(host, "todo_done")] == [True] * 4
    host.command("ideas.todo", {"idea": slug, "id": "t3", "done": False})
    todo, _ = _todo_of(host, slug, "t3")
    assert todo["done"] is False and "skipped" not in todo


def test_going_without_a_secret_keeps_its_stored_value(host):
    slug = _add(host, "x")["slug"]
    _plan(host, slug, [{"id": "t1", "title": "API_KEY", "kind": "secret", "why": "", "choices": [], "steps": [], "for": ["k1"], "done": False, "value": None}])
    host.command("ideas.todo", {"idea": slug, "id": "t1", "done": True, "value": "sk-1"})
    host.command("ideas.todo", {"idea": slug, "id": "t1", "done": True, "skip": True})
    todo, _ = _todo_of(host, slug)
    assert todo["skipped"] is True and todo["value"] == "stored"
    assert idea_secrets.get(host.ideas.state_dir, slug, "t1") == "sk-1"


def test_a_file_to_do_can_be_described_instead_and_a_file_replaces_the_words(host):
    slug = _add(host, "x")["slug"]
    _plan(host, slug, [_file_todo()])
    for empty in ("", "   "):
        with pytest.raises(CommandError, match="Say what it should look like"):
            host.command("ideas.todo", {"idea": slug, "id": "t1", "done": True, "words": empty})
    host.command("ideas.todo", {"idea": slug, "id": "t1", "done": True, "words": "  A grey ork at dusk.  "})
    todo, plan = _todo_of(host, slug)
    assert todo["done"] and todo["value"] == "A grey ork at dusk." and todo["words"] is True and "skipped" not in todo
    assert plan["tasks"][0]["state"] == "ready"
    (done,) = _events(host, "todo_done")
    assert done["words"] is True and done["skipped"] is False and "dusk" not in json.dumps(done)
    host.command("ideas.todo", {"idea": slug, "id": "t1", "done": True, "words": "x" * 3000})
    assert len(_todo_of(host, slug)[0]["value"]) == 2000
    host.command("ideas.todo", {"idea": slug, "id": "t1", "done": True, "file": {"name": "ork.png", "data": base64.b64encode(b"png").decode()}})
    todo, _ = _todo_of(host, slug)
    assert todo["value"] == "ork.png" and "words" not in todo
    host.command("ideas.todo", {"idea": slug, "id": "t1", "done": False})
    assert "skipped" not in _todo_of(host, slug)[0]


def test_words_are_for_a_file_to_do_only(host):
    slug = _add(host, "x")["slug"]
    _plan(host, slug, [{"id": "t1", "title": "Which", "kind": "choice", "why": "", "choices": ["a", "b"], "steps": [], "for": ["k1"], "done": False, "value": None}])
    with pytest.raises(CommandError, match="choices"):
        host.command("ideas.todo", {"idea": slug, "id": "t1", "done": True, "words": "whatever"})
