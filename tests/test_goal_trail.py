"""Spec 46 B, the trail: a goal's read that ends `ready` has its leader lay out the goal's ideas as proposals; Lay out ideas
and Take all; an idea the person adds joins that trail. The model call is stubbed."""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest

from orkboard.core.idea_keeper import IdeaKeeper
from orkboard.gui.board_host import CommandError, Orkboard
from orkboard.realm import board_map, event_log, goal_team, idea_target, ideas, jobs, library

TRAIL_MARK, DRAFT_MARK = "lay out its ideas", "write its spec"
DRAFT = {"title": "Drafted", "gist": "A thing.\nIt does it.", "why": "Moves it", "done_when": ["it works"], "risk": "low",
         "risk_why": "small", "touches": ["src/app.py"], "depends_on": [], "size": "M", "before": "", "questions": []}


def ideas_of(*titles, **more):
    return {"ideas": [{"key": f"t{n + 1}", "title": t, "short": f"Short {n + 1}", "why": f"Why {t}.\nIt moves it.", **more}
                      for n, t in enumerate(titles)]}


class Model:
    """The keeper's call: the goal's read, the trail, a draft; remembers every call. `trail` may be a function of the prompt."""

    def __init__(self, trail=None, goal=None, draft=None) -> None:
        self.trail, self.goal, self.draft = trail if trail is not None else {"ideas": []}, goal or {"summary": "S.", "metrics": [], "questions": []}, draft or DRAFT
        self.calls, self.lock = [], threading.Lock()
        self.running, self.overlap, self.order = 0, False, []

    def __call__(self, tier, prompt, effort="", budget=None):
        kind = "trail" if TRAIL_MARK in prompt else "draft" if DRAFT_MARK in prompt else "goal" if "saved a goal" in prompt else "?"
        with self.lock:
            self.calls.append({"kind": kind, "tier": tier, "prompt": prompt, "effort": effort, "budget": budget})
            if kind == "draft":
                self.running += 1
                self.overlap |= self.running > 1
                self.order.append(prompt)
        try:
            if kind == "trail":
                got = self.trail(prompt) if callable(self.trail) else self.trail
            elif kind == "draft":
                time.sleep(0.03)
                got = self.draft
            else:
                got = self.goal
            if isinstance(got, Exception):
                raise got
            return json.dumps(got), 0.01, 100, "s"
        finally:
            if kind == "draft":
                with self.lock:
                    self.running -= 1

    def of(self, kind):
        return [c for c in self.calls if c["kind"] == kind]


@pytest.fixture
def keeper(tmp_path):
    root, state = tmp_path / "wiki", tmp_path / ".orkcraft"
    settings = {"target": "balance"}
    k = IdeaKeeper(tmp_path, state, lambda: root, lambda: settings)
    k.root, k.state, k.settings_now = root, state, settings
    return k


def _goal(k, ideas_n=0, leader="architect"):
    library.install(k.state, ["tester", "reviewer", "architect"])
    slug = ideas.save_goal(k.root, None, "Ship the sync", "Make the sync reliable.")[0]
    goal_team.set_team(k.root, slug, ["tester", "reviewer"], [], leader)
    for n in range(ideas_n):
        ideas.add_idea(k.root, f"An idea of the person {n}", slug, k.state)
    return slug


def _wait(k, slug):
    for _ in range(600):
        if not k.busy(f"goal:{slug}"):
            return
        time.sleep(0.01)
    raise AssertionError("the keeper never finished")


def _read(k, slug, **kw):
    k.read_goal(slug, **kw)
    _wait(k, slug)


def _events(k, name):
    return [r for r in event_log.read(k.repo_root) if r["event"] == name]


def _waiting(k, slug):
    return [i["title"] for i in k.trail_waiting(slug)]


def _extra(k, slug):
    return board_map.proposal_state(k.state, slug)


# -- the step -------------------------------------------------------------------------------------------------------

def test_the_trail_step_its_caps_and_how_many_ideas_a_lay_out_writes():
    assert idea_target.pick("trail", "thrift") == ("elder", "low") and idea_target.pick("trail", "balance") == ("elder", "medium")
    assert idea_target.pick("trail", "quality") == ("elder", "high")
    assert idea_target.CONTEXT["trail"] == 10_000 and idea_target.READS["trail"] == 4 and idea_target.budget("trail", "balance") == 0.60
    assert idea_target.TRAIL == {"thrift": 3, "balance": 5, "quality": 7}


# -- when it is laid out --------------------------------------------------------------------------------------------

def test_a_read_that_ends_ready_lays_out_once_and_not_on_a_goal_with_three_ideas_a_refresh_or_a_read_that_asks(keeper):
    keeper.call = model = Model(trail=ideas_of("Queue the writes", "Retry the sync"))
    slug = _goal(keeper)
    _read(keeper, slug)
    assert [c["kind"] for c in model.calls] == ["goal", "trail"]
    assert _waiting(keeper, slug) == ["Queue the writes", "Retry the sync"]
    st = json.loads((keeper.state / "goals" / slug / "state.json").read_text())
    assert st["state"] == "ready" and st["trail_at"] and len(st["trail"]) == 2 and st["error"] == ""
    ev = _events(keeper, "trail_laid")
    assert len(ev) == 1 and ev[0]["goal"] == slug and ev[0]["ideas"] == 2 and ev[0]["dropped"] == 0 and ev[0]["via"] == "read"
    assert ev[0]["step"] == "trail" and ev[0]["prompt_chars"] and ev[0]["tokens"] and ev[0]["cost"] == 0.01
    _read(keeper, slug, said="One more word")                       # read again: it has laid out already
    assert [c["kind"] for c in model.calls].count("trail") == 1
    # a goal whose ideas the person wrote already (three) is the person's to lay out
    three = ideas.save_goal(keeper.root, None, "Three ideas", "Already planned.")[0]
    for n in range(3):
        ideas.add_idea(keeper.root, f"Idea {n}", three, keeper.state)
    _read(keeper, three)
    assert [c["kind"] for c in model.calls].count("trail") == 1 and not json.loads((keeper.state / "goals" / three / "state.json").read_text()).get("trail_at")
    # a refresh never lays out; nor does a read that asks
    two = _goal2 = ideas.save_goal(keeper.root, None, "Two", "Two words.")[0]
    keeper.read_goal_one(two, "", "refresh", ["src/app.py"])
    assert [c["kind"] for c in model.calls].count("trail") == 1
    keeper.call = model2 = Model(goal={"summary": "S.", "metrics": [], "questions": [{"ask": "Which?", "choices": ["a", "b"], "pick": 0}]})
    asks = ideas.save_goal(keeper.root, None, "Asks", "Needs words.")[0]
    _read(keeper, asks)
    assert ideas.goal_state(keeper.state, asks)["state"] == "asks" and not model2.of("trail")


@pytest.mark.parametrize("target,most", [("thrift", 3), ("balance", 5), ("quality", 7)])
def test_at_most_three_five_or_seven_ideas_by_the_target_and_the_leader_runs_the_step(keeper, target, most):
    keeper.settings_now["target"] = target
    keeper.call = model = Model(trail=ideas_of(*[f"Idea number {n}" for n in range(9)]))
    slug = _goal(keeper)
    _read(keeper, slug)
    assert len(_waiting(keeper, slug)) == most and _events(keeper, "trail_laid")[0]["dropped"] == 9 - most
    (call,) = model.of("trail")
    assert call["prompt"].startswith("You are Architect, the leader of this goal's party")            # decisions §53: its steps run as it
    assert (call["tier"], call["effort"], call["budget"]) == (*idea_target.pick("trail", target), idea_target.budget("trail", target))


def test_its_context_the_goal_its_ideas_its_party_and_what_was_turned_down(keeper):
    from orkboard.core import idea_night
    keeper.call = model = Model(trail=ideas_of("Anything"))
    slug = _goal(keeper)
    idea_night.decline(keeper.state, "Rewrite in Rust", slug, "no way")
    idea_night.decline(keeper.state, "Another goal's", "elsewhere", "")
    ideas.add_idea(keeper.root, "A person's idea about the cache", slug, keeper.state)
    other = ideas.add_track(keeper.root, "Elsewhere")
    ideas.add_idea(keeper.root, "Open idea of another goal", other, keeper.state)
    keeper.lay_out(slug, "read")
    prompt = model.of("trail")[0]["prompt"]
    for part in ("The goal:", "Its summary:", "Its metrics:", "Its ideas:", "Its links (paths):", "Its party:", "Rewrite in Rust: no way",
                 "A person's idea about the cache", "Open idea of another goal", "Tester", "Reviewer", "done when:"):
        assert part in prompt, part
    assert "Another goal's" not in prompt
    assert prompt.index("The goal:") < prompt.index("Its ideas:") < prompt.index("Its party:") < prompt.index("The other goals' open ideas")


# -- written strictly -----------------------------------------------------------------------------------------------

def test_written_strictly_proposed_by_trail_after_the_goals_ideas_with_depends_from_keys_and_slugs(keeper):
    from orkboard.core import idea_night
    slug = _goal(keeper, ideas_n=1)
    mine = ideas.ideas(keeper.root, slug)[0]
    idea_night.decline(keeper.state, "Turned Down", slug, "")
    answer = {"ideas": [
        {"key": "a", "title": "First step", "short": "First", "why": "Does it.\nMoves metric one.", "after": [mine["slug"], "ghost"], "by": "tester"},
        {"key": "b", "title": "Second step", "short": "A short name that is far too long to fit a chip", "why": "Then that.", "after": ["a", "c", "nope"], "by": "wizard"},
        {"key": "c", "title": "Third step", "why": "Last.", "after": ["b"]},                                # b is set first (a and c); c after b would then close a cycle
        {"key": "d", "title": "turned down", "why": "no"},
        {"key": "e", "title": f"  {mine['title'].upper()} ", "why": "same as the person's"},
        {"key": "f", "title": "First STEP", "why": "twice"},
        {"key": "g", "title": "", "why": "nameless"}, "not a dict"]}
    keeper.call = Model(trail=answer)
    keeper.lay_out(slug, "person")
    assert _waiting(keeper, slug) == ["First step", "Second step", "Third step"]            # after the goal's idea, in the answer's order
    first, second, third = (i for i in ideas.ideas(keeper.root, slug) if i["slug"] != mine["slug"])
    orders = [i["order"] for i in ideas.ideas(keeper.root, slug)]
    assert orders == sorted(orders) and ideas.ideas(keeper.root, slug)[0]["slug"] == mine["slug"]
    page = ideas.idea_page(keeper.root, first["slug"])
    assert page.section("Gist").startswith("Does it.") and page.title == "First step" and first["short"] == "First"
    assert second["short"] == "Second step"                                                  # a short that does not fit is made from the title
    assert ideas.state(keeper.state, first["slug"])["state"] == "proposed"
    assert _extra(keeper, first["slug"]) == {"proposed_by": "trail", "trail_by": "tester", "same_as": ""}
    assert _extra(keeper, second["slug"])["trail_by"] == "" and _extra(keeper, third["slug"])["trail_by"] == ""      # an unknown one: none
    deps = lambda s: board_map.list_of(ideas.idea_page(keeper.root, s).get("depends_on"))
    assert deps(first["slug"]) == [mine["slug"]] and deps(second["slug"]) == [first["slug"], third["slug"]] and deps(third["slug"]) == []
    assert _events(keeper, "trail_laid")[0]["ideas"] == 3 and _events(keeper, "trail_laid")[0]["dropped"] == 4 and _events(keeper, "trail_laid")[0]["via"] == "person"


def test_a_cycle_in_after_is_cut(keeper):
    slug = _goal(keeper)
    keeper.call = Model(trail={"ideas": [{"key": "a", "title": "One", "why": "x", "after": ["b"]}, {"key": "b", "title": "Two", "why": "y", "after": ["a"]}]})
    keeper.lay_out(slug, "person")
    one, two = ideas.ideas(keeper.root, slug)
    deps = lambda s: board_map.list_of(ideas.idea_page(keeper.root, s).get("depends_on"))
    assert deps(one["slug"]) == [two["slug"]] and deps(two["slug"]) == []                   # the second edge would close a cycle


def test_a_failed_call_writes_nothing_and_the_goal_stays_ready_with_its_error_then_lay_out_tries_again(keeper):
    slug = _goal(keeper)
    keeper.call = model = Model(trail=RuntimeError("boom"))
    _read(keeper, slug)
    st = ideas.goal_state(keeper.state, slug)
    assert st["state"] == "ready" and "boom" in st["error"] and not ideas.ideas(keeper.root, slug)
    assert not _events(keeper, "trail_laid") and not json.loads((keeper.state / "goals" / slug / "state.json").read_text()).get("trail_at")
    model.trail = ideas_of("Now it works")
    keeper.lay_out_goal(slug)
    _wait(keeper, slug)
    assert _waiting(keeper, slug) == ["Now it works"] and ideas.goal_state(keeper.state, slug)["error"] == ""
    assert _events(keeper, "trail_laid")[0]["via"] == "person"


def test_a_call_that_runs_out_of_its_budget_writes_nothing(keeper):
    slug = _goal(keeper)
    keeper.call = Model(trail=Exception("budget exceeded"))
    _read(keeper, slug)
    assert ideas.goal_state(keeper.state, slug)["error"] and not ideas.ideas(keeper.root, slug)


def test_lay_out_ideas_is_refused_in_plain_words(keeper):
    keeper.call = Model(trail=ideas_of("One"))
    slug = _goal(keeper)
    with pytest.raises(Exception, match="being read, or waits for your answers"):
        keeper.lay_out_goal(slug)                                                          # not read yet: `raw`
    ideas.save_goal_state(keeper.state, slug, state="ready")
    keeper.lay_out(slug, "read")
    with pytest.raises(Exception, match="take them or say No first"):
        keeper.lay_out_goal(slug)
    with pytest.raises(Exception, match="goal is gone"):
        keeper.lay_out_goal("nope")
    for i in keeper.trail_waiting(slug):
        ideas.drop(keeper.root, i["slug"], keeper.state)
    keeper.call = gate = Model(trail=lambda p: (gate_wait.wait(5), ideas_of("Two"))[1])
    gate_wait = threading.Event()
    keeper.lay_out_goal(slug)
    assert keeper.trailing(slug)
    with pytest.raises(Exception, match="busy|being read"):
        keeper.lay_out_goal(slug)
    gate_wait.set()
    _wait(keeper, slug)
    assert not keeper.trailing(slug)
    for i in keeper.trail_waiting(slug):
        ideas.drop(keeper.root, i["slug"], keeper.state)
    keeper.limits_now = []
    keeper.settings_now["target"] = "balance"
    keeper.demo = True
    with pytest.raises(Exception, match="demo"):
        keeper.lay_out_goal(slug)


def test_the_night_counts_trail_proposals_as_waiting_and_a_proposal_without_proposed_by_is_the_nights(keeper):
    from orkboard.core import idea_night
    slug = _goal(keeper)
    keeper.call = Model(trail=ideas_of("One", "Two", "Three", "Four"))
    keeper.lay_out(slug, "person")
    assert len(keeper.trail_waiting(slug)) == 4                      # a lay out is not held by MAX_WAITING
    keeper.call = model = Model()
    keeper.call = lambda *a, **k: (_ for _ in ()).throw(AssertionError("the night proposed while 4 wait"))
    counts = {"proposed": 0}
    keeper._night_proposals(keeper.root, counts)
    assert counts["proposed"] == 0
    night = idea_night.write_proposal(keeper.root, keeper.state, slug, "The night's", "Why.")
    assert _extra(keeper, night)["proposed_by"] == "" and not board_map.is_trail(keeper.state, night)


# -- the draft: needed_by, same_as ----------------------------------------------------------------------------------

def test_an_idea_the_person_adds_makes_the_goals_undrafted_ideas_wait_for_it_and_names_a_proposal_that_does_the_same(keeper):
    slug = _goal(keeper)
    keeper.call = Model(trail=ideas_of("Wait for me", "Another proposal"))
    keeper.lay_out(slug, "person")
    waits, twin = (i["slug"] for i in ideas.ideas(keeper.root, slug))
    raw = ideas.add_idea(keeper.root, "A raw idea", slug, keeper.state, queue="night")
    done = ideas.add_idea(keeper.root, "A drafted idea", slug, keeper.state)
    ideas.save_state(keeper.state, done, state="ready")
    other = ideas.add_track(keeper.root, "Elsewhere")
    foreign = ideas.add_idea(keeper.root, "Not this goal's", other, keeper.state)
    mine = ideas.add_idea(keeper.root, "The person's new idea", slug, keeper.state)
    keeper.call = model = Model(draft={**DRAFT, "needed_by": [waits, raw, done, foreign, mine, "ghost", waits], "same_as": twin})
    keeper.draft_one(mine)
    deps = lambda s: board_map.list_of(ideas.idea_page(keeper.root, s).get("depends_on"))
    assert deps(waits) == [mine] and deps(raw) == [mine] and deps(done) == [] and deps(foreign) == []      # drafted and foreign untouched
    assert _extra(keeper, twin)["same_as"] == mine and ideas.state(keeper.state, twin)["state"] == "proposed"   # nothing removed
    drafted = _events(keeper, "idea_drafted")[0]
    assert drafted["needed_by"] == 2 and drafted["same_as"] is True
    prompt = model.of("draft")[0]["prompt"]
    assert "needed_by" in prompt and "same_as" in prompt and f"{waits}: Wait for me (proposed)" in prompt


def test_needed_by_never_closes_a_cycle_and_never_passes_max_depends(keeper):
    from orkboard.core import idea_draft
    slug = _goal(keeper)
    a = ideas.add_idea(keeper.root, "Idea a", slug, keeper.state, queue="night")
    mine = ideas.add_idea(keeper.root, "The person's new idea", slug, keeper.state)
    keeper.call = Model(draft={**DRAFT, "depends_on": [a], "needed_by": [a]})                # it waits for a: a cannot wait for it
    keeper.draft_one(mine)
    assert board_map.list_of(ideas.idea_page(keeper.root, a).get("depends_on")) == []
    full = ideas.add_idea(keeper.root, "Idea full", slug, keeper.state, queue="night")
    others = [ideas.add_idea(keeper.root, f"Dependency {n}", slug, keeper.state, queue="night") for n in range(idea_draft.MAX_DEPENDS)]
    ideas.set_meta(keeper.root, full, depends_on=json.dumps(others))
    second = ideas.add_idea(keeper.root, "A second new idea", slug, keeper.state)
    keeper.call = Model(draft={**DRAFT, "depends_on": [], "needed_by": [full]})
    keeper.draft_one(second)
    assert second not in board_map.list_of(ideas.idea_page(keeper.root, full).get("depends_on"))


# -- the host: Needs you, the payloads, Take all, the proposal's via -------------------------------------------------

@pytest.fixture
def host(fake_repo, monkeypatch):
    h = Orkboard(fake_repo)
    h.model = Model(trail=ideas_of("First step", "Second step", "Third step", "Fourth step"), goal={"summary": "S.", "metrics": [], "questions": []})

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        return h.model("", prompt, kw.get("effort", ""), kw.get("budget"))

    monkeypatch.setattr(jobs, "run_read", run_read)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


def _hwait(host, slug):
    for _ in range(800):
        k = host.ideas.keeper
        if not k.busy_goal(slug) and not any(k.busy(i["slug"]) for i in ideas.ideas(host.ideas.root(False))):
            return
        time.sleep(0.01)
    raise AssertionError("the keeper never finished")


def _hostevents(host, name):
    return [r for r in event_log.read(Path(host.town.repo_root)) if r["event"] == name]


def _saved(host, **more):
    slug = host.command("ideas.goal_save", {"about": "Make the sync reliable.", "priority": "high", "team": ["tester"], "leader": "architect", **more})["slug"]
    _hwait(host, slug)
    return slug


def test_needs_you_has_one_trail_row_per_goal_the_nights_proposals_still_one_each_all_out_of_the_count(host):
    slug = _saved(host)
    other = host.command("ideas.goal_save", {"about": "Another goal entirely."})["slug"]
    _hwait(host, other)
    host.ideas.keeper.call = lambda *a, **k: ("{}", None, 1, "")
    from orkboard.core import idea_night
    night = idea_night.write_proposal(host.ideas.root(), host.ideas.state_dir, slug, "The night's", "Why.")
    board = host.command("ideas.board")
    rows = [n for n in board["needs_you"] if n["kind"] == "trail"]
    assert {r["goal"] for r in rows} == {slug, other} and len(rows) == 2
    row = next(r for r in rows if r["goal"] == slug)
    goal = next(t for t in board["tracks"] if t["slug"] == slug)
    assert row["text"] == "4 ideas laid out" and row["blocks"] is False and row["priority"] == "high" and row["idea"] == ""
    assert row["title"] == goal["title"] and row["short"] == goal["short"] and row["at"] == goal["trail"]["at"] != ""
    assert [i["title"] for i in row["ideas"]] == ["First step", "Second step", "Third step", "Fourth step"] and set(row["ideas"][0]) == {"slug", "title", "short"}
    proposals = [n for n in board["needs_you"] if n["kind"] == "proposal"]
    assert [p["idea"] for p in proposals] == [night]                                             # none of the trail's is a row of its own
    from orkboard.gui.ideas_board import sort_needs
    ask = {"kind": "asks", "blocks": False, "priority": "low", "at": "2030", "idea": "x"}
    assert [n["kind"] for n in sort_needs([*board["needs_you"], ask])][0] == "asks"               # a trail row sits among the proposals, last
    assert host.ideas.snapshot()["needs_you"] == 0                                                 # out of the count
    assert goal["trail"] == {"at": row["at"], "waiting": 4, "busy": False}


def test_the_board_and_the_map_carry_a_goals_trail_and_a_nodes_proposed_by_trail_by_and_same_as(host):
    slug = _saved(host)
    ideas_now = [i["slug"] for i in ideas.ideas(host.ideas.root(False), slug)]
    host.ideas.keeper._busy[f"goal:{slug}"] = "trail"
    host.ideas.keeper._trail_busy().add(slug)
    got = host.command("ideas.map")
    goal = next(g for g in got["goals"] if g["slug"] == slug)
    assert goal["trail"]["waiting"] == 4 and goal["trail"]["busy"] is True and goal["trail"]["at"]
    host.ideas.keeper._busy.pop(f"goal:{slug}")
    host.ideas.keeper._trail_busy().discard(slug)
    ideas.save_state(host.ideas.state_dir, ideas_now[0], trail_by="tester", same_as=ideas_now[1])
    nodes = {n["slug"]: n for n in host.command("ideas.map")["nodes"]}
    first = nodes[ideas_now[0]]
    assert first["proposed_by"] == "trail" and first["trail_by"]["slug"] == "tester" and set(first["trail_by"]) == {"slug", "name", "head"}
    assert first["same_as"] == {"slug": ideas_now[1], "short": nodes[ideas_now[1]]["short"]} and nodes[ideas_now[1]]["trail_by"] is None
    assert nodes[ideas_now[1]]["same_as"] is None
    assert next(g for g in host.command("ideas.goal", {"slug": slug}).items() if g[0] == "trail")[1]["waiting"] == 4
    person = host.command("ideas.add", {"text": "The person's own", "track": slug, "night": True})["slug"]
    assert {n["slug"]: n for n in host.command("ideas.map")["nodes"]}[person]["proposed_by"] == ""


def test_ideas_trail_is_the_command_and_a_goal_not_ready_or_with_a_trail_waiting_is_refused(host):
    slug = _saved(host)
    with pytest.raises(CommandError, match="take them or say No first"):
        host.command("ideas.trail", {"goal": slug})
    for i in host.ideas.keeper.trail_waiting(slug):
        host.command("ideas.proposal", {"slug": i["slug"], "take": False})
    ideas.save_goal_state(host.ideas.state_dir, slug, state="asks")
    with pytest.raises(CommandError, match="being read, or waits for your answers"):
        host.command("ideas.trail", {"goal": slug})
    ideas.save_goal_state(host.ideas.state_dir, slug, state="ready")
    host.model.trail = ideas_of("A fresh one")
    host.command("ideas.trail", {"goal": slug})
    _hwait(host, slug)
    assert [i["title"] for i in host.ideas.keeper.trail_waiting(slug)] == ["A fresh one"]
    assert _hostevents(host, "trail_laid")[-1]["via"] == "person"
    with pytest.raises(CommandError):
        host.command("ideas.trail", {"goal": "nope"})


def test_take_all_takes_each_at_the_goals_priority_drafts_the_now_ones_one_at_a_time_in_order_and_sends_low_ones_to_the_night(host):
    slug = _saved(host)
    order = [i["slug"] for i in host.ideas.keeper.trail_waiting(slug)]
    host.command("ideas.trail_take", {"goal": slug, "via": "needs"})
    _hwait(host, slug)
    assert all(ideas.idea_page(host.ideas.root(False), s).get("priority") == "high" for s in order)
    assert not host.model.overlap and len(host.model.order) == 4                                       # one at a time
    assert all(host.ideas.keeper.busy(s) == "" for s in order)
    taken = _hostevents(host, "trail_taken")
    assert len(taken) == 1 and taken[0]["goal"] == slug and taken[0]["ideas"] == 4 and taken[0]["via"] == "needs"
    assert not host.ideas.keeper.trail_waiting(slug)
    with pytest.raises(CommandError, match="No laid-out ideas"):
        host.command("ideas.trail_take", {"goal": slug})


def test_the_drafts_run_in_the_trails_order(host):
    slug = _saved(host)
    seen = []
    keeper = host.ideas.keeper
    real = keeper.draft_one
    keeper.draft_one = lambda s: (seen.append(s), real(s))[1]
    order = [i["slug"] for i in keeper.trail_waiting(slug)]
    host.command("ideas.trail_take", {"goal": slug})
    _hwait(host, slug)
    assert seen == order


def test_a_low_goals_trail_goes_to_the_night_and_drafts_nothing(host):
    slug = _saved(host, priority="low")
    host.command("ideas.trail_take", {"goal": slug})
    _hwait(host, slug)
    root = host.ideas.root(False)
    mine = ideas.ideas(root, slug)
    assert len(mine) == 4 and all(ideas.state(host.ideas.state_dir, i["slug"])["state"] == "raw"
                                  and ideas.queue_of(ideas.state(host.ideas.state_dir, i["slug"])) == "night" for i in mine)
    assert not host.model.of("draft")


def test_stop_all_stops_take_all_and_what_is_left_waits_for_the_person(host):
    slug = _saved(host)
    keeper = host.ideas.keeper
    gate, started = threading.Event(), threading.Event()
    real = keeper.draft_one

    def slow(s):
        started.set()
        gate.wait(5)
        return real(s)

    keeper.draft_one = slow
    order = [i["slug"] for i in keeper.trail_waiting(slug)]
    host.command("ideas.trail_take", {"goal": slug})
    assert started.wait(5)
    keeper.stop_all()
    gate.set()
    _hwait(host, slug)
    states = [(ideas.state(host.ideas.state_dir, s)["state"], ideas.queue_of(ideas.state(host.ideas.state_dir, s))) for s in order]
    assert [q for _s, q in states[1:]] == ["hold"] * 3
    assert len(host.model.of("draft")) <= 1


def test_a_proposal_answered_says_where_and_who_made_it_and_a_trail_proposal_is_taken_at_its_goals_priority(host):
    slug = _saved(host)
    night = __import__("orkboard.core.idea_night", fromlist=["x"]).write_proposal(host.ideas.root(), host.ideas.state_dir, slug, "The night's", "Why.")
    first, second = [i["slug"] for i in host.ideas.keeper.trail_waiting(slug)][:2]
    host.command("ideas.proposal", {"slug": first, "take": True, "via": "map"})
    host.command("ideas.proposal", {"slug": second, "take": False, "reason": "no", "via": "needs"})
    host.command("ideas.proposal", {"slug": night, "take": False, "via": "bogus"})
    _hwait(host, slug)
    got = _hostevents(host, "proposal_answered")
    assert [(e["take"], e["via"], e["proposed_by"]) for e in got] == [(True, "map", "trail"), (False, "needs", "trail"), (False, "idea", "night")]
    assert ideas.idea_page(host.ideas.root(False), first).get("priority") == "high"
