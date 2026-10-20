"""Spec 39 A (docs/specs/39-map.md, Tests → A): the Map's data on a fixture board, `ideas.map` on the host and the phone,
and `opened` with `via`. Code, no model."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import board_map, event_log, idea_spend, ideas


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
        with pytest.raises(CommandError, match="That goal is gone"):
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
                                     "head": {"craft": "engineering", "race": "peon", "tier": "warrior"}, "tag": "Code"}   # who does it: a Grunt; its tag
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
