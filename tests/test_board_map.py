"""Spec 39 A (docs/specs/39-map.md, Tests → A): the Map's data on a fixture board, `ideas.map` on the host and the phone,
and `opened` with `via`. Code, no model."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import board_map, event_log, goal_team, idea_change, idea_spend, ideas, library, map_party


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def _goal(root, title, priority="normal", metrics=None):
    slug, _new = ideas.save_goal(root, None, title, "About " + title, metrics, priority)
    return slug


def _idea(root, state_dir, goal, text, state="ready", depends=(), **more):
    slug = ideas.add_idea(root, text, goal, state_dir)
    if depends:
        ideas.set_meta(root, slug, depends_on=json.dumps(list(depends)))
    ideas.save_state(state_dir, slug, state=state, **more)
    return slug


def _plan(state_dir, slug, tasks, **more):
    folder = state_dir / "ideas" / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "plan.json").write_text(json.dumps({"idea": slug, "made_at": "2026-10-18T09:00:00", "todos": [],
                                                  "tasks": tasks, **more}))


def _t(tid, state, after=(), note=""):
    return {"id": tid, "title": f"Task {tid}", "tier": "warrior", "state": state, "after": list(after), "note": note}


def _roles(state, *slugs):
    """Library agents as roles of the project (a party's members are roles of it)."""
    library.install(state, list(slugs))


def _board(host):
    ideas_ = host.ideas
    return ideas_.root(), ideas_.state_dir


def _node(got, slug):
    return next(n for n in got["nodes"] if n["slug"] == slug)


@pytest.fixture
def fixture(host):
    root, state = _board(host)
    one = _goal(root, "Speed", "high", [{"name": "done when it is fast", "target": "1s", "how": "a test"}])
    two = _goal(root, "Docs")
    a = _idea(root, state, one, "Cache the table", "done")
    b = _idea(root, state, one, "Index the runs", "working", depends=[a])
    c = _idea(root, state, one, "Page the runs", "ready", depends=[a, b])
    d = _idea(root, state, two, "Write the guide", "ready", depends=[c])        # another goal's idea: no edge
    loose = _idea(root, state, ideas.GENERAL, "A loose idea", "ready")
    return host, root, state, {"one": one, "two": two, "a": a, "b": b, "c": c, "d": d, "loose": loose}


def test_goals_nodes_tiers_and_edges(fixture):
    host, root, state, f = fixture
    got = host.command("ideas.map", {})
    assert [g["slug"] for g in got["goals"]] == [f["one"], f["two"]] and f["loose"] not in {n["slug"] for n in got["nodes"]}
    assert (_node(got, f["a"])["tier"], _node(got, f["b"])["tier"], _node(got, f["c"])["tier"]) == (1, 2, 3)   # two parents: the deeper
    assert _node(got, f["d"])["tier"] == 1 and _node(got, f["d"])["depends_on"] == [f["c"]]
    assert {(e["from"], e["to"]) for e in got["edges"]} == {(f["a"], f["b"]), (f["a"], f["c"]), (f["b"], f["c"])}
    assert [n["slug"] for n in got["nodes"] if n["goal"] == f["one"]] == [f["a"], f["b"], f["c"]]
    g = got["goals"][0]
    assert g["done_when"] == ["done when it is fast"] and (g["ideas"], g["done"]) == (3, 1) and g["priority"] == "high"
    assert got["rev"] == host.ideas.rev


def test_one_goal_and_a_goal_that_is_gone(fixture):
    host, _root, _state, f = fixture
    got = host.command("ideas.map", {"goal": f["two"]})
    assert [g["slug"] for g in got["goals"]] == [f["two"]] and {n["goal"] for n in got["nodes"]} == {f["two"]}
    for bad in ("nope", ideas.GENERAL):
        with pytest.raises(CommandError, match="That party is gone"):
            host.command("ideas.map", {"goal": bad})


def test_a_node_carries_its_boards_row_for_every_state(host):
    root, state = _board(host)
    g = _goal(root, "Every state")
    slugs = [_idea(root, state, g, f"Idea {s}", s) for s in ideas.STATES]
    _plan(state, slugs[ideas.STATES.index("working")], [_t("k1", "merged"), _t("k2", "running")], start_at="night")
    row_of = {r["slug"]: r for r in host.command("ideas.board")["ideas"]}
    nodes = {n["slug"]: n for n in host.command("ideas.map", {})["nodes"]}
    assert set(nodes) == set(row_of)
    for slug, n in nodes.items():
        for k in ("state", "queue", "held_until", "start_at", "priority", "size", "risk", "depends_on", "waits_on",
                  "progress", "updated"):
            assert n[k] == row_of[slug][k], (slug, k)


def test_waits_come_in_the_specs_order(host):
    root, state = _board(host)
    g = _goal(root, "Waits")
    base = _idea(root, state, g, "Base idea", "working")
    other = _idea(root, state, g, "Other idea", "working")
    plan_only = {"made_at": "2026-10-18T09:00:00"}

    waiting = _idea(root, state, g, "Waits for base", "plan", depends=[base])        # a plan waiting: you, before idea
    _plan(state, waiting, [_t("k1", "ready")], **plan_only)
    follower = _idea(root, state, g, "Follows base", "ready", depends=[base])
    files = _idea(root, state, g, "Same files", "working")
    _plan(state, files, [_t("k1", "held", note=f"files · {other}")], passed_at="x")
    limits = _idea(root, state, g, "Limits", "working")
    _plan(state, limits, [_t("k1", "held", note="after 18:00")], passed_at="x")
    reserve = _idea(root, state, g, "Reserve", "working")
    _plan(state, reserve, [_t("k1", "held", note="reserve · after 19:30")], passed_at="x")
    held = _idea(root, state, g, "Held keeper", "raw", queue="now", held_until="2026-10-19T20:00:00")
    night = _idea(root, state, g, "Tonight", "raw", queue="night")
    night_plan = _idea(root, state, g, "Night plan", "working")
    _plan(state, night_plan, [_t("k1", "ready")], start_at="night", passed_at="x")
    stopped = _idea(root, state, g, "Stopped", "raw", queue="hold")
    free = _idea(root, state, g, "Free", "working")
    _plan(state, free, [_t("k1", "running")], passed_at="x")

    n = {x["slug"]: x for x in host.command("ideas.map", {})["nodes"]}
    none = {"ref": "", "title": "", "until": ""}
    assert n[waiting]["waits"] == {"kind": "you", **none} and n[waiting]["needs_you"] == "plan"
    assert n[follower]["waits"] == {"kind": "idea", "ref": base, "title": "Base idea", "until": ""} and n[follower]["needs_you"] == ""
    assert n[files]["waits"] == {"kind": "files", "ref": other, "title": "Other idea", "until": ""}
    assert n[limits]["waits"] == {"kind": "limits", "ref": "", "title": "", "until": "18:00"}
    assert n[reserve]["waits"] == {"kind": "reserve", "ref": "", "title": "", "until": "19:30"}
    assert n[held]["waits"] == {"kind": "limits", "ref": "", "title": "", "until": "2026-10-19T20:00:00"}
    assert n[night]["waits"]["kind"] == "night" and n[night_plan]["waits"]["kind"] == "night"
    assert n[stopped]["waits"]["kind"] == "stopped"
    assert n[free]["waits"] is None and n[base]["waits"] is None


def test_needs_you_names_the_kind(host):
    root, state = _board(host)
    g = _goal(root, "Needs")
    asks = _idea(root, state, g, "Asks", "asks")
    proposed = _idea(root, state, g, "Proposed", "proposed")
    failed = _idea(root, state, g, "Failed", "failed", error="boom")
    todo = _idea(root, state, g, "Todo", "working")
    _plan(state, todo, [_t("k1", "ready")], passed_at="x", todos=[{"id": "t1", "title": "Paste the key", "kind": "secret", "for": ["k1"]}])
    n = {x["slug"]: x for x in host.command("ideas.map", {})["nodes"]}
    assert (n[asks]["needs_you"], n[proposed]["needs_you"], n[failed]["needs_you"], n[todo]["needs_you"]) == \
        ("asks", "proposal", "failed", "todo")
    assert all(n[s]["waits"]["kind"] == "you" for s in (asks, proposed, failed, todo))
    # spec 41 §9: an asking idea's row carries each question's choices, pick and why; its line is the ask alone
    ideas.set_section(root, asks, "Open questions", "- Which store first? (**App Store** / Google Play) — iPhone first")
    row = next(r for r in host.command("ideas.board")["needs_you"] if r.get("idea") == asks)
    assert row["text"] == "Which store first?" and row["asked"] == [
        {"ask": "Which store first?", "choices": ["App Store", "Google Play"], "pick": 0, "why": "iPhone first"}]


def test_tasks_estimate_and_by_itself(host):
    root, state = _board(host)
    g = _goal(root, "Plans")
    est = {"tasks": 2, "usd_low": 0.4, "usd_high": 1.2}
    fresh = _idea(root, state, g, "Fresh plan", "plan")
    _plan(state, fresh, [_t("k1", "waiting"), _t("k2", "ready", after=["k1"])], estimate=est, passed_by="auto", passed_at="x")
    begun = _idea(root, state, g, "Begun plan", "working")
    _plan(state, begun, [_t("k1", "merged"), _t("k2", "running", after=["k1"])], estimate=est, passed_by="person", passed_at="x")
    none = _idea(root, state, g, "No plan", "ready")
    n = {x["slug"]: x for x in host.command("ideas.map", {})["nodes"]}
    assert n[fresh]["estimate"] == {"usd_low": 0.4, "usd_high": 1.2} and n[fresh]["by_itself"] is True
    assert n[begun]["estimate"] is None and n[begun]["by_itself"] is False and n[begun]["progress"] == {"done": 1, "total": 2}
    assert n[begun]["tasks"][1] == {"id": "k2", "title": "Task k2", "short": "Task k2", "state": "running", "after": ["k1"], "tier": "warrior",
                                     "head": {"craft": "engineering", "race": "peon", "tier": "warrior"}, "tag": "Code",   # who does it: a Grunt; its tag
                                     "by": {"slug": "grunt", "name": "Grunt"}, "band": "build", "wave": 2,
                                     "error": "", "note": "", "round": 1, "cost": None, "started": "", "pick": None}
    assert n[none]["tasks"] == [] and n[none]["estimate"] is None and n[none]["by_itself"] is False


def test_folded_is_a_done_idea_no_open_one_depends_on_and_every_edge_has_both_ends(host):
    root, state = _board(host)
    g = _goal(root, "Folds")
    a = _idea(root, state, g, "Done base", "done")
    b = _idea(root, state, g, "Done middle", "done", depends=[a])
    c = _idea(root, state, g, "Open top", "ready", depends=[b])
    lone = _idea(root, state, g, "Done lone", "done")
    pair = _idea(root, state, g, "Done pair", "done", depends=[lone])
    got = host.command("ideas.map", {})
    n = {x["slug"]: x for x in got["nodes"]}
    assert {s: n[s]["folded"] for s in (a, b, c, lone, pair)} == {a: False, b: False, c: False, lone: True, pair: True}
    shown = {s for s, x in n.items() if not x["folded"]}
    assert got["edges"] == [{"from": a, "to": b}, {"from": b, "to": c}] and all(e["from"] in shown and e["to"] in shown for e in got["edges"])


def test_a_goals_spend_is_null_when_nothing_is_priced(host):
    root, state = _board(host)
    g = _goal(root, "Spend")
    s = _idea(root, state, g, "Spent", "working")
    row = idea_spend.line("task", "grunt", "claude", "opus", "warrior", "medium", idea_spend.tokens_of({"in": 1, "out": 1}), 12.404, "k1", 1, "")
    assert idea_spend.append(state, row, idea=s)
    other = _goal(root, "Free of cost")
    _idea(root, state, other, "Nothing priced", "ready")
    unpriced = _goal(root, "Unpriced")
    u = _idea(root, state, unpriced, "Unpriced call", "working")
    idea_spend.append(state, {**row, "cost": None}, idea=u)
    usd = {x["slug"]: x["usd"] for x in host.command("ideas.map", {})["goals"]}
    assert usd[g] == 12.4 and usd[unpriced] is None and usd[other] in (0, 0.0, None)


def test_two_hundred_ideas_build_in_under_200_ms_and_nothing_is_written_or_started(host, monkeypatch):
    root, state = _board(host)
    g = _goal(root, "Big")
    prev = []
    for n in range(200):
        slug = _idea(root, state, g, f"Idea number {n}", "working" if n % 3 else "done", depends=prev[-2:] if n % 5 else ())
        _plan(state, slug, [_t("k1", "merged"), _t("k2", "running", after=["k1"])], passed_at="x")
        prev.append(slug)
    host.command("ideas.map", {})                                                   # the first read warms the files
    before = sorted((p, p.stat().st_mtime_ns) for p in list(root.rglob("*")) + list(state.rglob("*")) if p.is_file())

    def no(*a, **k):
        raise AssertionError("the Map starts no process")
    monkeypatch.setattr(subprocess, "Popen", no)
    monkeypatch.setattr(subprocess, "run", no)
    best = 9.0
    for _ in range(3):
        began = time.perf_counter()
        got = board_map.build(root, state, {}, [], time.time(), rev=0)
        best = min(best, time.perf_counter() - began)
    assert len(got["nodes"]) == 200 and best < 0.2
    assert before == sorted((p, p.stat().st_mtime_ns) for p in list(root.rglob("*")) + list(state.rglob("*")) if p.is_file())


def test_the_command_is_the_phones_too_and_needs_a_project():
    assert BoardPhone.allowed(Orkboard(), "ideas.map", {})
    with pytest.raises(CommandError, match="Open a folder first"):
        Orkboard().command("ideas.map", {})


def test_opened_with_via_is_written_and_an_old_line_reads_empty(host):
    host.command("ideas.log", {"event": "opened", "what": "map"})
    host.command("ideas.log", {"event": "opened", "what": "idea", "ref": "x", "via": "map"})
    with pytest.raises(CommandError, match="via"):
        host.command("ideas.log", {"event": "opened", "what": "idea", "ref": "x", "via": "elsewhere"})
    rows = [r for r in event_log.read(Path(host.town.repo_root)) if r["event"] == "opened"]
    assert [(r["what"], r.get("via")) for r in rows] == [("map", ""), ("idea", "map")]
    event_log.path(Path(host.town.repo_root)).open("a", encoding="utf-8").write(
        json.dumps({"at": "2026-10-01T09:00:00", "event": "opened", "what": "idea", "ref": "old", "device": "desktop"}) + "\n")
    assert event_log.read(Path(host.town.repo_root))[-1]["via"] == ""


def test_a_goal_accepted_has_its_verdict_at_and_a_met_one_its_tally_spec_42(fixture):
    from orkboard.realm import goal_verdict
    host, root, state, f = fixture
    goal_verdict.save(state, f["one"], {"met": True, "verdict": "x"}, by="Product manager")
    goal_verdict.save(state, f["two"], {"met": False, "verdict": "x"}, by="Growth")
    got = {g["slug"]: g for g in host.command("ideas.map", {})["goals"]}
    met, no = got[f["one"]]["verdict"], got[f["two"]]["verdict"]
    assert met["at"] and met["met"] is True and set(met["tally"]) == {"ideas", "results", "first_time", "usd", "days"}
    assert met["tally"]["ideas"] == 1                                  # "Cache the table" is done
    assert no["at"] and "tally" not in no


# -- spec 48 A: the stage, the party's states, the idea's card ------------------------------------------------------

def test_a_node_has_its_stage_round_spend_and_estimate_spec_48(host):
    root, state = _board(host)
    g = _goal(root, "Stages")
    est = {"tasks": 2, "usd_low": 0.4, "usd_high": 1.2}
    raw = _idea(root, state, g, "Raw", "raw")
    waiting = _idea(root, state, g, "Waiting", "plan")
    _plan(state, waiting, [_t("k1", "ready")], estimate=est)
    building = _idea(root, state, g, "Building", "working")
    _plan(state, building, [{**_t("k1", "merged"), "round": 1}, {**_t("k2", "running", after=["k1"]), "round": 2}], estimate=est, passed_at="x")
    _roles(state, "reviewer")
    check = _t("k9", "ready", after=["k1"])
    checking = _idea(root, state, g, "Checking", "working")
    _plan(state, checking, [_t("k1", "merged"), {**check, "kind": "review", "role": "reviewer"}], passed_at="x", estimate=est)
    done = _idea(root, state, g, "Done", "done")
    n = {x["slug"]: x for x in host.command("ideas.map", {})["nodes"]}
    assert [n[s]["stage"] for s in (raw, waiting, building, checking, done)] == ["planning", "planning", "implementation", "checking", "done"]
    assert (n[building]["round"], n[raw]["round"]) == (2, 1)
    assert n[raw]["usd"] is None and n[raw]["plan_estimate"] is None
    assert n[building]["plan_estimate"] == {"usd_low": 0.4, "usd_high": 1.2} and n[building]["estimate"] is None     # `estimate` is before it starts
    assert n[waiting]["plan_estimate"] == n[waiting]["estimate"]
    assert [(t["wave"], t["band"]) for t in n[checking]["tasks"]] == [(1, "build"), (2, "check")]
    assert n[checking]["tasks"][1]["by"]["slug"] == "reviewer"


def test_asked_says_who_asks_and_results_wait_on_their_idea(host):
    root, state = _board(host)
    g = _goal(root, "Asks")
    asks = _idea(root, state, g, "Asks", "asks")
    ideas.set_section(root, asks, "Open questions", "- Which store first? (**App Store** / Google Play) — iPhone first")
    other = _idea(root, state, g, "Other", "ready")
    n = {x["slug"]: x for x in host.command("ideas.map", {})["nodes"]}
    assert n[asks]["asked"][0]["ask"] == "Which store first?" and n[asks]["asked"][0]["by"]["slug"] == "taskmaster"     # the leader's: no `asks_by`
    assert (n[asks]["asked"][0]["choices"], n[asks]["asked"][0]["pick"], n[asks]["asked"][0]["why"]) == (["App Store", "Google Play"], 0, "iPhone first")
    assert n[other]["asked"] == [] and n[asks]["results"] == []
    review = _idea(root, state, g, "In review", "working")
    _plan(state, review, [{**_t("k1", "review"), "tests": {"passed": 20, "failed": 0, "failing": [], "tail": ""}, "cost": 0.42,
                          "finished": "2026-10-20T10:00:00", "diff": {"files": 14, "added": 3, "removed": 1}}], passed_at="x")
    got = {x["slug"]: x for x in host.command("ideas.map", {})["nodes"]}
    assert [(r["task"], r["tests"]["passed"], r["diff"]["files"]) for r in got[review]["results"]] == [("k1", 20, 14)]
    assert got[asks]["results"] == []


def test_the_partys_states_and_todays_merges_spec_48(host):
    root, state = _board(host)
    g = _goal(root, "Party")
    _roles(state, "reviewer", "architect")
    goal_team.set_team(root, g, ["grunt", "reviewer"], leader="architect")
    hot = _idea(root, state, g, "Hot", "working")
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    _plan(state, hot, [{**_t("k1", "merged"), "finished": now, "cost": 0.3}, _t("k2", "running", after=["k1"]),
                       {**_t("k3", "ready", after=["k2"]), "kind": "review", "role": "reviewer"}], passed_at="x")
    got = host.command("ideas.map", {"goal": g})["goals"][0]
    states = {m["slug"]: (m["state"], m["why"], m["band"]) for m in got["party"]}
    assert states["grunt"] == ("work", "", "build") and states["reviewer"] == ("next", "", "check") and states["architect"][0] == "free"
    assert got["today"] == {"merged": 1, "usd": 0.3}
    ideas.save_state(state, hot, state="plan")
    _plan(state, hot, [_t("k1", "ready")])
    assert {m["slug"]: m["state"] for m in host.command("ideas.map", {"goal": g})["goals"][0]["party"]}["architect"] == "needs"
    ideas.save_state(state, hot, state="working")
    _plan(state, hot, [_t("k1", "failed")], passed_at="x")
    got = {m["slug"]: (m["state"], m["why"]) for m in host.command("ideas.map", {"goal": g})["goals"][0]["party"]}
    assert got["grunt"] == ("needs", "failed")


def test_a_result_in_review_is_not_a_stop_on_its_agent_spec_48(host):
    root, state = _board(host)
    g = _goal(root, "Review is no signal")
    _roles(state, "architect")
    goal_team.set_team(root, g, ["grunt"], leader="architect")
    slug = _idea(root, state, g, "Reviewing", "working")
    _plan(state, slug, [_t("k1", "review")], passed_at="x")
    party = {m["slug"]: m["state"] for m in host.command("ideas.map", {"goal": g})["goals"][0]["party"]}
    assert party["grunt"] == "free" and party["architect"] == "free"


def test_a_task_that_waits_for_a_pick_is_picking_with_its_pick_and_its_member_and_goal_wait_for_you_spec_51(host):
    root, state = _board(host)
    g = _goal(root, "Brand")
    _roles(state, "architect")
    goal_team.set_team(root, g, ["grunt"], leader="architect")
    slug = _idea(root, state, g, "A logo", "working")
    logo = {**_t("k1", "picking"), "round": 2, "pick": {"n": 4, "kind": "audio", "ask": "A jingle", "target": "assets/jingle.mp3"}}
    _plan(state, slug, [logo, _t("k2", "waiting", after=["k1"])], passed_at="x")
    got = host.command("ideas.map", {"goal": g})
    node = got["nodes"][0]
    assert [(t["id"], t["state"], t["pick"]) for t in node["tasks"]] == [("k1", "picking", {"n": 4, "media": "audio", "round": 2}), ("k2", "waiting", None)]
    assert node["waits"] == {"kind": "you", "ref": "", "title": "", "until": ""} and node["stage"] == "implementation"
    assert {m["slug"]: (m["state"], m["why"]) for m in got["goals"][0]["party"]}["grunt"] == ("needs", "pick")
    _plan(state, slug, [{**logo, "state": "running"}, _t("k2", "waiting", after=["k1"])], passed_at="x")        # no longer picking: no pick, no wait
    node = host.command("ideas.map", {"goal": g})["nodes"][0]
    assert node["tasks"][0]["pick"] is None and node["waits"] is None


# -- spec 49 A: what a task's run left, and the recommended answer --------------------------------------------------

def test_a_task_carries_its_failure_note_round_cost_and_start_spec_49(host):
    root, state = _board(host)
    g = _goal(root, "Runs")
    slug = _idea(root, state, g, "Runs", "working")
    long = "The test run failed:\n" + "x" * 400
    _plan(state, slug, [{**_t("k1", "failed"), "error": long, "round": 2, "cost": 0.42, "started": "2026-10-21T09:12:00"},
                        {**_t("k2", "held", after=["k1"], note="reserve · after 18:00")},
                        {**_t("k3", "ready", after=["k1"], note="stopped by you"), "cost": 0},
                        {**_t("k4", "waiting", after=["k2"]), "cost": "free", "error": None, "round": 0}], passed_at="x")
    tasks = {t["id"]: t for t in next(n for n in host.command("ideas.map", {})["nodes"] if n["slug"] == slug)["tasks"]}
    k1, k2, k3, k4 = (tasks[k] for k in ("k1", "k2", "k3", "k4"))
    assert k1["error"] == long[:300] and len(k1["error"]) == 300 and k1["error"].startswith("The test run failed:\nxxx")    # as the runner wrote it, cut
    assert (k1["round"], k1["cost"], k1["started"], k1["note"]) == (2, 0.42, "2026-10-21T09:12:00", "")
    assert (k2["note"], k2["error"], k2["cost"], k2["started"], k2["round"]) == ("reserve · after 18:00", "", None, "", 1)       # null before it ran
    assert (k3["note"], k3["cost"]) == ("stopped by you", 0)
    assert (k4["cost"], k4["error"], k4["round"]) == (None, "", 1)                                                            # nothing odd gets through
    json.dumps(tasks)
    assert k1["id"] == "k1" and k1["state"] == "failed" and k1["after"] == [] and k2["after"] == ["k1"] and k1["wave"] == 1   # the old fields stay


def test_a_question_says_its_recommended_choice_and_why_spec_49(host):
    root, state = _board(host)
    g = _goal(root, "Asks")
    slug = _idea(root, state, g, "Asks", "asks")
    ideas.set_section(root, slug, "Open questions", "\n".join([
        "- Which store first? (**App Store** / Google Play) — iPhone first",
        "- Which store after? (App Store / Google Play)",
        "- Anything else to know?"]))
    asked = next(n for n in host.command("ideas.map", {})["nodes"] if n["slug"] == slug)["asked"]
    assert [(q["ask"], q["choices"], q["pick"], q["why"]) for q in asked] == [
        ("Which store first?", ["App Store", "Google Play"], 0, "iPhone first"),
        ("Which store after?", ["App Store", "Google Play"], None, ""),               # no pick: null
        ("Anything else to know?", [], None, "")]                                    # no choices: the person writes
    assert all(set(q) == {"ask", "choices", "pick", "why", "by"} for q in asked)


def test_a_node_has_its_element_and_its_flag_and_a_party_its_flags_waits_and_brief_spec_50(host):
    from orkboard.realm import idea_flag
    root, state = _board(host)
    g = _goal(root, "Speed")
    other = _goal(root, "Docs")
    flagged = _idea(root, state, g, "Cache the table", "done")
    waiting = _idea(root, state, g, "Index the runs", "done")
    open_one = _idea(root, state, g, "Page the runs", "working", element="lava")
    _idea(root, state, other, "Write the guide", "done")
    _plan(state, flagged, [_t("k1", "merged"), _t("k2", "merged")])
    pure = board_map.build(root, state, {}, [], time.time(), rev=0)                               # the pure read gives none: it writes nothing
    assert {n["slug"]: n["element"] for n in pure["nodes"]} == {n["slug"]: "" if n["slug"] != open_one else "lava" for n in pure["nodes"]}
    assert all(n["flag"] is None for n in pure["nodes"]) and all((p["flags"], p["waits_main"]) == (0, 1 if p["slug"] == other else 2) for p in pure["goals"])
    flag = idea_flag.raise_flag(root, state, flagged, "gate", "c" * 40)
    got = host.command("ideas.map", {})
    nodes = {n["slug"]: n for n in got["nodes"]}
    assert nodes[flagged]["flag"] == {**flag, "release": None} and set(flag) == {"at", "by", "commit", "tasks", "first_time", "usd", "days"} and flag["tasks"] == 2
    assert nodes[waiting]["flag"] is None and nodes[open_one]["flag"] is None
    assert all(n["element"] in ("meadow", "ice", "dust", "void", "lava") for n in nodes.values()) and nodes[open_one]["element"] == "lava"
    parties = {p["slug"]: p for p in got["goals"]}
    assert (parties[g]["flags"], parties[g]["waits_main"]) == (1, 1)                              # one flagged; one done, waiting for main; one at work
    assert (parties[other]["flags"], parties[other]["waits_main"]) == (0, 1)
    json.dumps(got)


def test_a_partys_brief_is_its_descriptions_first_paragraph_else_its_summarys_first_line_in_140_characters(host):
    root, state = _board(host)
    both = ideas.save_goal(root, None, "Both", "The first paragraph\nruns over two lines.\n\nThe second paragraph is not the brief.", None, "normal")[0]
    long = ideas.save_goal(root, None, "Long", "w" * 200, None, "normal")[0]
    titled = ideas.save_goal(root, None, "Only a title", "", None, "normal")[0]
    ideas.write_goal_reading(root, titled, "\nSummary line one\nline two", {}, [])
    bare = ideas.save_goal(root, None, "Bare", "", None, "normal")[0]
    briefs = {g["slug"]: g["brief"] for g in host.command("ideas.map", {})["goals"]}
    assert briefs[both] == "The first paragraph runs over two lines."
    assert briefs[long] == "w" * 139 + "…" and len(briefs[long]) == 140
    assert briefs[titled] == "Summary line one" and briefs[bare] == ""


def test_a_plan_rows_missing_is_read_against_the_party_now_and_a_node_says_its_type_spec_52(host):
    """Spec 52 §2.2, §2.6: Needs you's plan row says what no one of the party does, read now (a member added since drops out;
    a plan made before has none); a node carries its type `{id, name, sign}`, None with none or an unknown key."""
    root, state = _board(host)
    g = _goal(root, "Brand")
    _roles(state, "grunt", "product-designer")
    goal_team.set_team(root, g, ["grunt"], leader="product-designer")
    slug = _idea(root, state, g, "A logo", state="plan", type="product-designer/logo")
    blank = _idea(root, state, g, "Blank", state="ready")
    odd = _idea(root, state, g, "Odd", state="ready", type="nobody/logo")
    _plan(state, slug, [_t("k1", "ready")], passed_at=None, missing=[{"kind": "art", "agent": "artist"}])
    i = next(x for x in ideas.ideas(root) if x["slug"] == slug)

    def row():
        (got,) = [n for n in board_map.idea_needs(root, state, i, ideas.state(state, slug), ideas.plan(state, slug), []) if n["kind"] == "plan"]
        return got["missing"]
    assert row() == [{"kind": "art", "words": "pixel art", "agent": "artist", "name": "Artist", "band": "build", "free": True}]
    _roles(state, "artist")
    goal_team.set_team(root, g, ["grunt", "artist"])
    assert row() == []                                                                          # the Artist joined since
    goal_team.set_team(root, g, ["grunt"])
    ideas.edit_plan(state, slug, lambda p: p.pop("missing"))
    assert row() == []                                                                          # a plan made before has none
    nodes = {n["slug"]: n for n in board_map.build(root, state, goal=g)["nodes"]}
    assert nodes[slug]["type"] == {"id": "logo", "name": "New logo", "sign": "logo"}
    assert nodes[blank]["type"] is None and nodes[odd]["type"] is None


def test_a_plan_change_waiting_is_one_stop_of_kind_change_beside_the_plans_spec_62(host):
    """Spec 62 §4.1–§4.2: while `plan_change.json` is there and can be taken, a stop `{idea, goal, title, priority, blocks: false, at: made_at, kind:
    "change", text, why, added, changed, dropped, usd_low, usd_high}`; the Map's node keeps its needs_you; the hand sorts it as a plan."""
    root, state = _board(host)
    g = _goal(root, "Speed")
    slug = _idea(root, state, g, "Cache the table", "working", priority="normal")
    planning = _idea(root, state, g, "Index the runs", "plan")
    _plan(state, slug, [_t("k1", "merged"), _t("k2", "ready", ["k1"]), _t("k3", "waiting", ["k2"])], passed_at="2026-10-23T09:30:00")
    _plan(state, planning, [_t("k1", "ready")], passed_at=None)
    stops = lambda: [n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "change"]      # noqa: E731
    assert stops() == []
    change = {"made_at": "2026-10-23T11:00:00", "why": "csv only now", "changed": ["Out"], "estimate": {"usd_low": 0.1, "usd_high": 0.4},
              "change": [{"id": "k2", "title": "Write csv"}], "drop": ["k3"], "add": [{"key": "n1", "title": "Stream", "brief": "b"}] * 2}
    idea_change.write(state, slug, change)
    before = (state / "ideas" / slug / "plan_change.json").stat().st_mtime_ns
    (stop,) = stops()
    assert stop == {"idea": slug, "goal": g, "title": "Cache the table", "priority": "normal", "blocks": False, "at": "2026-10-23T11:00:00",
                    "kind": "change", "text": "The plan changes · +2 · 1 changed · −1", "why": "csv only now", "added": 2, "changed": 1,
                    "dropped": 1, "usd_low": 0.1, "usd_high": 0.4}
    kinds = [(n["idea"], n["kind"]) for n in host.command("ideas.board")["needs_you"]]
    assert kinds == [(planning, "plan"), (slug, "change")]                                         # as a plan: by priority, then the oldest
    nodes = {n["slug"]: n for n in host.command("ideas.map", {})["nodes"]}
    assert nodes[slug]["needs_you"] == "change" and nodes[planning]["needs_you"] == "plan"        # the Map's node names it: its goal's row is marked
    party = next(m for x in host.command("ideas.map", {})["goals"] if x["slug"] == g for m in x["party"] if m.get("band") == "lead")
    assert (party["state"], party["why"]) == ("needs", "plan")                                   # the leader stops on its plan first, then on its change
    assert map_party.leader_state("working", [{"state": "working", "needs_you": "change"}]) == ("needs", "change")
    assert (state / "ideas" / slug / "plan_change.json").stat().st_mtime_ns == before            # a read writes nothing
    # what cannot be taken any more is shown nowhere; a change of nothing says so
    ideas.edit_plan(state, slug, lambda p: [p["tasks"][1].update(state="running", started="x"), p["tasks"][2].update(state="running", started="x")])
    (stop,) = stops()
    assert (stop["added"], stop["changed"], stop["dropped"], stop["text"]) == (2, 0, 0, "The plan changes · +2")
    idea_change.write(state, slug, {**change, "add": []})
    assert stops() == []
    idea_change.write(state, slug, {**change, "change": [], "drop": [], "add": []})
    (stop,) = stops()
    assert stop["text"] == "The plan stays as it is" and (stop["added"], stop["changed"], stop["dropped"]) == (0, 0, 0)
    ideas.save_state(state, slug, state="done")
    assert stops() == []


def test_the_hand_sorts_a_plan_change_as_a_plan_not_last_and_not_blocking_spec_62():
    from orkboard.gui.ideas_board import sort_needs
    row = lambda kind, priority="normal", at="2026-10-23T10:00:00", blocks=False: {"kind": kind, "priority": priority, "at": at, "blocks": blocks}      # noqa: E731
    got = sort_needs([row("proposal", "high"), row("plan", "low"), row("change", "high", "2026-10-23T12:00:00"), row("change", "high", "2026-10-23T11:00:00"),
                      row("failed", blocks=True), row("plan", "high", "2026-10-23T09:00:00")])
    assert [(n["kind"], n["priority"], n["at"][11:13]) for n in got] == [
        ("failed", "normal", "10"), ("plan", "high", "09"), ("change", "high", "11"), ("change", "high", "12"), ("plan", "low", "10"), ("proposal", "high", "10")]
