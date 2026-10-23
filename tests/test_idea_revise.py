"""Spec 62 A (docs/specs/62-spec-after-start.md, Tests → A): what changed since the plan, the leader's plan change (the keeper's model call
stubbed), its being taken by the runner under its lock, kept, or dropped by itself, the stop, the events and the word."""
from __future__ import annotations

import datetime as dt
import json
import threading
import time

import pytest

from orkboard.core import idea_keeper
from orkboard.core.idea_keeper import IdeaKeeper, KeeperError
from orkboard.core.idea_runner import IdeaRunner, Run, RunnerError
from orkboard.realm import event_log, idea_change, idea_checks, idea_target, ideas
from orkboard.sources.limits import Limit

STEPS = (("propose a plan change", "revise"), ("turn it into a plan", "plan"), ("Rewrite only that section", "talk"))
CHECK = idea_checks.TAGS[0]                      # a check task's kind
OLD = "2026-10-23T10:00:00"                      # when a task started
NEW_PLAN = {"tasks": [{"id": "a", "title": "The table", "brief": "Add it", "tier": "warrior"}]}


class Model:
    """Answers by what it is asked (the step the prompt says); a list is a sequence (its last repeats); remembers every call."""

    def __init__(self, **answers) -> None:
        self.answers, self.asked, self.gate = answers, [], {}

    def __call__(self, tier, prompt, effort="", budget=None):
        step = next((s for k, s in STEPS if k in prompt), "?")
        self.asked.append({"step": step, "tier": tier, "prompt": prompt, "effort": effort, "budget": budget})
        if step in self.gate:
            self.gate[step].wait(5)
        got = self.answers.get(step, {})
        if isinstance(got, list):
            got = got.pop(0) if len(got) > 1 else got[0]
        if isinstance(got, Exception):
            raise got
        return (got if isinstance(got, str) else json.dumps(got)), 0.02, 1000, ""

    def of(self, step):
        return [a for a in self.asked if a["step"] == step]


@pytest.fixture
def keeper(fake_repo, tmp_path):
    root, state = tmp_path / "wiki", fake_repo / ".orkcraft"
    settings = {"target": "balance", "autostart": True, "night": "01:00-07:00"}
    k = IdeaKeeper(fake_repo, state, lambda: root, lambda: settings)
    k.root, k.state, k.settings_now, k.limits_now, k.repo = root, state, settings, [], fake_repo
    k.limits = lambda: k.limits_now
    k.goal = ideas.add_track(root, "Ship the table")
    return k


def _wait(k, slug):
    for _ in range(300):
        if not k.busy(slug):
            return
        time.sleep(0.01)
    raise AssertionError("the keeper never finished")


def _plan(keeper, slug, rows, passed=True, state="working", **more):
    """plan.json as the plan call and the runner leave it: `rows` are (id, state, after, kind?); a task that is not waiting, ready or held
    has started. Written as it is, past `save_plan`'s refusal of a passed plan."""
    tasks = []
    for tid, st, after, *kind in rows:
        t = idea_keeper._task(tid, f"Task {tid}", f"Do {tid}", kind[0] if kind else "code", "warrior", list(after))
        t.update(state=st, role="", **({"started": OLD} if st not in ("waiting", "ready", "held") else {}))
        tasks.append(t)
    data = {"idea": slug, "made_at": "2026-10-23T09:00:00", "passed_at": "2026-10-23T09:30:00" if passed else None,
            "passed_by": "person", "estimate": idea_keeper.estimate(tasks), "todos": [], "tasks": tasks, **more}
    ideas._write_json(ideas.state_folder(keeper.state, slug) / "plan.json", data)
    ideas.save_state(keeper.state, slug, state=state if passed else "plan")
    return data


def _idea(keeper, text="export csv", **kw):
    return ideas.add_idea(keeper.root, text, keeper.goal, keeper.state, **kw)


def _tasks(keeper, slug):
    return {t["id"]: t for t in ideas.plan(keeper.state, slug)["tasks"]}


def _events(keeper, event):
    return [r for r in event_log.read(keeper.repo) if r["event"] == event]


# -- §1: what changed since the plan ------------------------------------------------------------------------------

def test_the_sections_that_make_a_plan_are_what_the_plan_prompt_reads(keeper):
    """`PLAN_SECTIONS` is what `plan_prompt` reads of the spec (and so what `revise_prompt` shows of it)."""
    slug = _idea(keeper)
    for name in ideas.SECTIONS:
        ideas.set_section(keeper.root, slug, name, f"TEXT-{name.replace(' ', '-')}")
    read = lambda prompt: [n for n in ideas.SECTIONS if f"TEXT-{n.replace(' ', '-')}" in prompt]      # noqa: E731
    assert read(keeper.plan_prompt(keeper.root, slug)) == [n for n in ideas.SECTIONS if n in idea_change.PLAN_SECTIONS]
    assert read(keeper.revise_prompt(keeper.root, slug)) == [*read(keeper.plan_prompt(keeper.root, slug)), "Decisions"]     # …and what was decided
    assert idea_change.PLAN_SECTIONS == ("Gist", "Done when", "Out", "Risks", "Depends on")


def test_a_talk_keeps_the_plan_sections_it_wrote_and_no_other(keeper):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "ready", [])], passed=False)
    keeper.call = model = Model(talk=[
        {"reply": "Out it is.", "sections": {"Out": "No export of images"}, "decisions": ["No images"]},
        {"reply": "Same.", "sections": {"Out": "No export of images"}},                            # the text is the same
        {"reply": "Why.", "sections": {"Why": "People ask for it"}},                                 # not a plan section
        {"reply": "Asked.", "sections": {"Open questions": "- Which delimiter?"}},
        {"reply": "Done when.", "sections": {"Done when": "- A file downloads"}},
        {"reply": "Gist.", "sections": {"Gist": "Export the table as csv"}},
        {"reply": "Out again.", "sections": {"Out": "No export of images or pdf"}}])             # once each, in PLAN_SECTIONS' order
    seen = []
    for section in ("Out", "Out", "Why", "Open questions", "Done when", "Gist", "Out"):
        keeper.say(slug, f"About {section}", section)
        _wait(keeper, slug)
        seen.append(ideas.state(keeper.state, slug)["changed"])
    assert seen == [["Out"], ["Out"], ["Out"], ["Out"], ["Done when", "Out"], ["Gist", "Done when", "Out"], ["Gist", "Done when", "Out"]]
    assert ideas.idea_page(keeper.root, slug).section("Why") == "People ask for it" and len(model.asked) == 7


def test_a_talk_while_a_change_waits_keeps_what_changed_and_the_change_stays(keeper):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"])])
    idea_change.mark(keeper.state, slug, ["Gist"])
    idea_change.write(keeper.state, slug, {"why": "w", "change": [{"id": "k2", "title": "Two"}], "drop": [], "add": [], "changed": ["Gist"],
                                           "estimate": {"usd_low": 0, "usd_high": 0}})
    keeper.call = Model(talk={"reply": "Out.", "sections": {"Out": "No export of images"}})
    keeper.say(slug, "No images", "Out")
    _wait(keeper, slug)
    assert ideas.state(keeper.state, slug)["changed"] == ["Gist", "Out"] and idea_change.read(keeper.state, slug)["change"][0]["id"] == "k2"
    assert ideas.state(keeper.state, slug)["state"] == "working"                       # the talk does not move the goal


def test_a_goal_with_no_plan_keeps_nothing_changed(keeper):
    slug = _idea(keeper)                                           # the draft and the answer write the spec before any plan
    keeper.call = Model(talk={"reply": "Out.", "sections": {"Out": "No export of images"}})
    keeper.say(slug, "No images", "Out")
    _wait(keeper, slug)
    assert ideas.idea_page(keeper.root, slug).section("Out") == "No export of images"
    assert ideas.state(keeper.state, slug)["changed"] == []
    idea_change.set_section(keeper.root, keeper.state, slug, "Risks", "Big files")
    assert ideas.state(keeper.state, slug)["changed"] == []


def test_a_section_by_hand_is_kept_as_a_talks_is(keeper):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"])])
    idea_change.set_section(keeper.root, keeper.state, slug, "Depends on", "other-goal")
    idea_change.set_section(keeper.root, keeper.state, slug, "Depends on", "other-goal")            # the same text
    idea_change.set_section(keeper.root, keeper.state, slug, "Why", "Because")
    idea_change.set_section(keeper.root, keeper.state, slug, "Stages", "1. k1")
    assert ideas.state(keeper.state, slug)["changed"] == ["Depends on"]
    idea_change.set_section(keeper.root, keeper.state, slug, "Gist", "Export csv, quickly")
    assert idea_change.changed_of(ideas.state(keeper.state, slug)) == ["Gist", "Depends on"]
    assert ideas.state(keeper.state, _idea(keeper, "another"))["changed"] == []
    with pytest.raises(ValueError, match="no section"):
        idea_change.set_section(keeper.root, keeper.state, slug, "Bogus", "x")


def test_a_plan_made_clears_what_changed_and_the_change_that_waited(keeper):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "ready", [])], passed=False, state="plan")
    idea_change.set_section(keeper.root, keeper.state, slug, "Out", "No images")
    idea_change.write(keeper.state, slug, {"why": "x", "change": [], "drop": [], "add": [], "changed": ["Out"], "estimate": {"usd_low": 0, "usd_high": 0}})
    assert ideas.state(keeper.state, slug)["changed"] == ["Out"]
    keeper.call = Model(plan=NEW_PLAN)
    keeper.plan(slug)                                              # Re-plan, before the start
    _wait(keeper, slug)
    assert ideas.state(keeper.state, slug)["changed"] == [] and idea_change.read(keeper.state, slug) is None
    assert [t["id"] for t in ideas.plan(keeper.state, slug)["tasks"]] == ["k1"]


# -- §2: Re-plan what is left ------------------------------------------------------------------------------------

def test_re_plan_what_is_left_refuses_in_words(keeper):
    keeper.call = Model(revise={})
    with pytest.raises(KeeperError, match="gone"):
        keeper.revise("nothing")
    slug = _idea(keeper)
    with pytest.raises(KeeperError, match="This goal has no plan yet"):
        keeper.revise(slug)
    _plan(keeper, slug, [("k1", "ready", [])], passed=False, state="plan")
    with pytest.raises(KeeperError, match="Its plan is not started: Re-plan it"):
        keeper.revise(slug)
    _plan(keeper, slug, [("k1", "merged", [])], state="done")
    with pytest.raises(KeeperError, match="This goal is done"):
        keeper.revise(slug)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"])])
    keeper.demo = True
    with pytest.raises(KeeperError, match="demo"):
        keeper.revise(slug)
    keeper.demo, keeper.budget_ok = False, lambda: False
    with pytest.raises(KeeperError, match="spend limit"):
        keeper.revise(slug)
    keeper.budget_ok = lambda: True
    reset = dt.datetime.now() + dt.timedelta(hours=1)
    keeper.limits_now = [Limit("claude", "", "session", 0.01, reset)]
    with pytest.raises(KeeperError, match="spent"):
        keeper.revise(slug)
    keeper.limits_now = []
    assert keeper.call.asked == [] and ideas.state(keeper.state, slug)["state"] == "working"
    keeper.call.gate["revise"] = release = threading.Event()
    keeper.revise(slug)
    assert keeper.busy(slug) == "planning" and ideas.state(keeper.state, slug)["state"] == "working"      # busy as Re-plan; the state stays
    with pytest.raises(KeeperError, match="The keeper is busy with this goal: a moment"):
        keeper.revise(slug)
    release.set()
    _wait(keeper, slug)


def test_the_prompt_holds_the_tasks_not_started_and_names_the_started_ones_as_staying(keeper):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "running", ["k1"]), ("k3", "review", ["k1"]), ("k4", "ready", ["k1"]),
                         ("k5", "waiting", ["k4"]), ("k6", "held", []), ("k7", "failed", []), ("k8", "waiting", ["k1", "k5"], CHECK)])
    ideas.set_section(keeper.root, slug, "Decisions", "\n".join(f"- line {n}" for n in range(1, 16)))
    idea_change.mark(keeper.state, slug, ["Out", "Gist"])
    prompt = keeper.revise_prompt(keeper.root, slug)
    context = prompt[prompt.index("The spec:"):prompt.index("Rules:")]
    done, at_work, not_started = (context.split(h)[1] for h in ("Done (", "At work (", "Not started:"))
    assert "These sections changed since the plan: Gist, Out." in context and "- line 15" in context and "- line 5" not in context
    assert "k1 Task k1" in context.split("At work")[0] and "k2 Task k2: Do k2" in at_work and "k3 Task k3: Do k3" in at_work
    assert "(these stay as they are)" in context and "k7 Task k7" in context.split("Not started")[0]
    rows = [json.loads(line) for line in not_started.strip().splitlines() if line.startswith("{")]
    assert [r["id"] for r in rows] == ["k4", "k5", "k6", "k8"]
    assert set(rows[1]) == {"id", "title", "short", "brief", "kind", "tier", "after"} and rows[1]["after"] == ["k4"]
    assert rows[3]["check"] is True and "check" not in rows[0]
    assert "k2" not in not_started and "k3" not in not_started and "k1" not in not_started.replace('"k1"', "")
    assert "never change, drop or redo a task there" in prompt and "Answer with one JSON object" in prompt
    assert "These sections changed" not in keeper.revise_prompt(keeper.root, slug).replace("These sections changed since the plan: Gist, Out.", "")
    idea_change.clear(keeper.state, slug)
    assert "The person asked to look again." in keeper.revise_prompt(keeper.root, slug)


def test_the_prompt_is_cut_to_the_plan_contexts_size(keeper):
    slug = _idea(keeper)
    for name in idea_change.PLAN_SECTIONS:
        ideas.set_section(keeper.root, slug, name, f"{name} " + "words " * 3000)
    _plan(keeper, slug, [("k1", "merged", [])] + [(f"k{n}", "waiting", ["k1"]) for n in range(2, 9)])
    data = ideas.plan(keeper.state, slug)
    for t in data["tasks"]:
        t["brief"] = "brief " * 1000
    ideas._write_json(ideas.state_folder(keeper.state, slug) / "plan.json", data)
    prompt = keeper.revise_prompt(keeper.root, slug)
    context = prompt[prompt.index("The spec:"):prompt.index("Rules:")]
    assert len(context) <= idea_target.CONTEXT["plan"] + 60
    assert context.count('"id": "k') >= 3 and "Not started" in context and "Gist" in context


def test_the_call_is_made_on_the_plan_step_and_the_plan_change_is_saved_beside_the_plan(keeper):
    slug = _idea(keeper)
    plan = _plan(keeper, slug, [("k1", "merged", []), ("k2", "running", ["k1"]), ("k3", "ready", ["k1"]), ("k4", "waiting", ["k3"]),
                                ("k5", "waiting", ["k1", "k2", "k3", "k4"], CHECK)])
    before = json.dumps(ideas.plan(keeper.state, slug), sort_keys=True)
    idea_change.mark(keeper.state, slug, ["Out"])
    keeper.call = model = Model(revise={
        "why": "  The export is csv only now.\n", "drop": ["k4"],
        "change": [{"id": "k3", "title": "Write the csv", "short": "Csv writer", "brief": "Write rows as csv.", "kind": "tests", "tier": "laborer", "after": ["k2"]}],
        "add": [{"key": "n1", "title": "Stream rows", "brief": "Stream big files", "kind": "code", "tier": "elder", "after": ["k3"]}]})
    keeper.revise(slug)
    _wait(keeper, slug)
    (call,) = model.of("revise")
    assert (call["tier"], call["effort"], call["budget"]) == (*idea_target.pick("plan", "balance"), idea_target.budget("plan", "balance"))
    saved = idea_change.read(keeper.state, slug)
    assert json.dumps(ideas.plan(keeper.state, slug), sort_keys=True) == before          # nothing is applied, no task touched
    assert set(saved) == {"made_at", "why", "changed", "change", "drop", "add", "estimate"}
    assert saved["why"] == "The export is csv only now." and saved["changed"] == ["Out"] and saved["drop"] == ["k4"]
    assert saved["change"] == [{"id": "k3", "title": "Write the csv", "short": "Csv writer", "brief": "Write rows as csv.", "kind": "tests",
                                "tier": "laborer", "after": ["k2"], "role": ""}]
    assert saved["add"] == [{"key": "n1", "title": "Stream rows", "short": "Stream rows", "brief": "Stream big files", "kind": "code",
                             "tier": "elder", "after": ["k3"], "role": ""}]
    assert ideas.state(keeper.state, slug)["state"] == "working" and ideas.state(keeper.state, slug)["error"] == ""
    assert saved["made_at"] and idea_change.summary(saved, ideas.plan(keeper.state, slug)) == {
        "made_at": saved["made_at"], "why": saved["why"], "added": 1, "changed": 1, "dropped": 1, "usd_low": saved["estimate"]["usd_low"],
        "usd_high": saved["estimate"]["usd_high"], "rows": [{"op": "add", "id": "", "title": "Stream rows"},
                                                           {"op": "change", "id": "k3", "title": "Write the csv"},
                                                           {"op": "drop", "id": "k4", "title": "Task k4"}]}
    keeper.call = Model(revise={"why": "Again", "change": [], "drop": [], "add": []})
    keeper.revise(slug)                                          # a newer one replaces it
    _wait(keeper, slug)
    again = idea_change.read(keeper.state, slug)
    assert again["why"] == "Again" and again["change"] == [] and again["drop"] == [] and again["add"] == [] and again["estimate"] == {"usd_low": 0.0, "usd_high": 0.0}
    assert idea_change.text_of(idea_change.summary(again, ideas.plan(keeper.state, slug))) == "The plan stays as it is"


def test_an_answer_that_changes_a_started_task_names_an_unknown_id_or_closes_a_cycle_is_cut(keeper):
    slug = _idea(keeper)
    plan = _plan(keeper, slug, [("k1", "merged", []), ("k2", "running", ["k1"]), ("k3", "waiting", ["k1"]), ("k4", "waiting", ["k3"]),
                                ("k5", "waiting", ["k4"]), ("k6", "waiting", ["k1", "k2", "k3", "k4", "k5"], CHECK)])
    got = idea_revise_clean(plan, {
        "why": "x", "drop": ["k1", "k2", "k9", "k5", "k6", "k5"],
        "change": [{"id": "k2", "title": "Started"}, {"id": "k9", "title": "Unknown"}, {"id": "k6", "title": "A check"},
                   {"id": "k1", "title": "Merged"}, {"id": "k4", "title": "Task k4"},                      # nothing changes: left out
                   {"id": "k3", "title": "Third", "after": ["k5", "k1", "zzz", "k3", "k6"]}, {"id": "k3", "title": "Twice"}],
        "add": [{"key": "x", "title": "First", "brief": "b", "after": ["k3", "nothing", "x2", "k5"]},
                {"key": "x2", "title": "Second", "brief": "b", "after": ["x", "k4"], "kind": CHECK, "tier": "god"},
                {"title": "No brief"}, {"brief": "No title"}, "no", {"title": "Third", "brief": "b", "after": ["x"]}]})
    assert got["drop"] == ["k5"]                                    # the merged, the started, the unknown and the check stay; once
    assert [c["id"] for c in got["change"]] == ["k3"]
    assert got["change"][0]["after"] == ["k1"]                      # k5 waits for k3 (a cycle), zzz is nothing, k3 itself, k6 a check
    assert got["change"][0]["title"] == "Third" and got["change"][0]["brief"] == "Do k3" and got["change"][0]["kind"] == "code"
    first, second, third = got["add"]
    assert (first["key"], second["key"], third["key"]) == ("n1", "n2", "n3")
    assert first["after"] == ["k3", "n2"] and second["after"] == ["k4"]                  # n2 waits for n1 would close a cycle; k5 is dropped
    assert second["kind"] == "code" and second["tier"] == "warrior"                    # a check's tag and an unknown tier give way
    assert third["after"] == ["n1"] and len(got["add"]) == 3


def idea_revise_clean(plan, answer):
    from orkboard.core import idea_revise
    return idea_revise.clean_change(plan, answer)


def test_an_answer_with_too_many_tasks_or_not_an_object_is_cut_or_refused(keeper):
    from orkboard.core import idea_revise
    plan = {"tasks": [{"id": "k1", "title": "One", "state": "waiting", "after": [], "started": ""}]}
    got = idea_revise.clean_change(plan, {"add": [{"title": f"T{n}", "brief": "b"} for n in range(12)]})
    assert len(got["add"]) == idea_keeper.MAX_TASKS and got["add"][-1]["key"] == "n8"
    assert idea_revise.clean_change(plan, {}) == {"why": "", "change": [], "drop": [], "add": []}
    with pytest.raises(KeeperError, match="not a plan change"):
        idea_revise.clean_change(plan, None)


def test_a_failed_call_is_the_goals_error_and_saves_nothing(keeper):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"])])
    keeper.call = Model(revise=RuntimeError("claude: not logged in"))
    keeper.revise(slug)
    _wait(keeper, slug)
    st = ideas.state(keeper.state, slug)
    assert st["state"] == "working" and st["error"].startswith("No plan change: ") and "not logged in" in st["error"]
    assert idea_change.read(keeper.state, slug) is None and _events(keeper, event_log.PLAN_REVISED) == []
    keeper.call = Model(revise="no json at all")
    keeper.revise(slug)
    _wait(keeper, slug)
    assert "JSON" in ideas.state(keeper.state, slug)["error"] and idea_change.read(keeper.state, slug) is None
    keeper.call = Model(revise={"why": "fine", "change": [], "drop": [], "add": []})
    keeper.revise(slug)
    _wait(keeper, slug)
    assert ideas.state(keeper.state, slug)["error"] == "" and idea_change.read(keeper.state, slug)["why"] == "fine"


def test_a_failed_goals_own_error_is_kept_when_the_leader_finds_nothing_to_say(keeper):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "failed", [])], state="failed")
    ideas.save_state(keeper.state, slug, error="Task k1: dropped by you")
    keeper.call = Model(revise={"why": "Nothing", "change": [], "drop": [], "add": []})
    keeper.revise(slug)                                            # a failed goal's tasks wait for its work to start again
    _wait(keeper, slug)
    assert ideas.state(keeper.state, slug)["error"] == "Task k1: dropped by you" and ideas.state(keeper.state, slug)["state"] == "failed"


def test_the_estimate_is_what_it_adds_or_saves_and_negative_when_it_saves(keeper):
    slug = _idea(keeper)
    plan = _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"]), ("k3", "waiting", ["k2"])])
    for t in plan["tasks"]:
        t["tier"] = "warrior"
    plan["tasks"][2]["tier"] = "elder"
    ideas._write_json(ideas.state_folder(keeper.state, slug) / "plan.json", plan)
    costs = {"elder": 1.0, "warrior": 0.3, "laborer": 0.05}                            # the board's default price of a task
    price = lambda *tiers: idea_keeper.estimate([{}] * len(tiers), list(tiers), costs)      # noqa: E731
    keeper.call = Model(revise=[{"why": "More", "add": [{"title": "Big", "brief": "b", "tier": "elder"}, {"title": "Small", "brief": "b", "tier": "laborer"}]},
                                {"why": "Less", "drop": ["k3"], "change": [{"id": "k2", "tier": "laborer"}]},
                                {"why": "Same", "drop": ["k2"], "add": [{"title": "Same again", "brief": "b", "tier": "warrior"}]}])
    keeper.revise(slug)
    _wait(keeper, slug)
    more = idea_change.read(keeper.state, slug)["estimate"]
    assert more == {k: price("elder", "laborer")[k] for k in ("usd_low", "usd_high")} and more["usd_low"] > 0
    keeper.revise(slug)
    _wait(keeper, slug)
    less = idea_change.read(keeper.state, slug)["estimate"]                          # k2 warrior → laborer, k3 elder gone
    assert less == {k: round(price("laborer")[k] - price("warrior", "elder")[k], 2) for k in ("usd_low", "usd_high")}
    assert less["usd_low"] < 0 and less["usd_high"] < less["usd_low"]               # negative when it saves; the low end is the smaller saving
    keeper.revise(slug)
    _wait(keeper, slug)
    assert idea_change.read(keeper.state, slug)["estimate"] == {"usd_low": 0.0, "usd_high": 0.0}      # one warrior goes, one comes


def test_plan_revised_carries_the_sections_the_counts_the_price_and_the_calls_measure(keeper):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"]), ("k3", "waiting", ["k2"])])
    idea_change.mark(keeper.state, slug, ["Done when", "Gist"])
    keeper.call = Model(revise={"why": "w", "drop": ["k3"], "add": [{"title": "New", "brief": "b"}], "change": [{"id": "k2", "title": "Second"}]})
    keeper.revise(slug)
    _wait(keeper, slug)
    (row,) = _events(keeper, event_log.PLAN_REVISED)
    saved = idea_change.read(keeper.state, slug)
    assert row["idea"] == slug and row["changed"] == ["Gist", "Done when"] and (row["added"], row["changed_n"], row["dropped"]) == (1, 1, 1)
    assert (row["usd_low"], row["usd_high"]) == (saved["estimate"]["usd_low"], saved["estimate"]["usd_high"])
    assert row["step"] == "plan" and row["prompt_chars"] > 100 and row["cost"] == 0.02 and row["tokens"]["total"] == 1000


# -- the file, its summary and its words ---------------------------------------------------------------------------

def test_the_tasks_are_put_in_order_for_the_stages_a_change_adds_its_tasks_last():
    from orkboard.core import idea_draft
    tasks = [{"id": "k1", "title": "One", "after": ["k3"]}, {"id": "k2", "title": "Two", "after": []}, {"id": "k3", "title": "Three", "after": ["k2"]},
             {"id": "k4", "title": "Four", "after": ["k9"]}]
    ordered = idea_change.in_order(tasks)
    assert [t["id"] for t in ordered] == ["k2", "k3", "k1", "k4"]
    assert idea_draft.stages({"tasks": ordered}).splitlines() == ["1. k2 Two (M) ∥ k4 Four (M), after k9", "2. k3 Three (M), after k2", "3. k1 One (M), after k3"]
    assert idea_draft.stages({"tasks": tasks}).startswith("1. k1 One (M), after k3 ∥ k2 Two")             # as they stand, k1 is a wave too early
    assert [t["id"] for t in idea_change.in_order([{"id": "a", "after": ["b"]}, {"id": "b", "after": ["a"]}])] == ["a", "b"]      # a cycle: as it stands


def test_the_stops_text_says_only_the_parts_that_are_not_zero():
    said = lambda a, c, d: idea_change.text_of({"added": a, "changed": c, "dropped": d})      # noqa: E731
    assert said(2, 1, 1) == "The plan changes · +2 · 1 changed · −1"
    assert said(0, 3, 0) == "The plan changes · 3 changed" and said(1, 0, 2) == "The plan changes · +1 · −2"
    assert said(0, 0, 0) == "The plan stays as it is"


def test_a_summary_counts_what_taking_it_now_would_do(keeper):
    slug = _idea(keeper)
    plan = _plan(keeper, slug, [("k1", "merged", []), ("k2", "running", ["k1"]), ("k3", "ready", ["k1"]), ("k4", "waiting", ["k3"])])
    change = {"made_at": "2026-10-23T11:00:00", "why": "w", "changed": [], "estimate": {"usd_low": -0.1, "usd_high": -0.3},
              "change": [{"id": "k2", "title": "Gone on"}, {"id": "k3", "title": "Third"}], "drop": ["k4", "k9"], "add": []}
    said = idea_change.summary(change, plan)
    assert (said["added"], said["changed"], said["dropped"]) == (0, 1, 1) and [r["id"] for r in said["rows"]] == ["k3", "k4"]
    assert said["made_at"] == "2026-10-23T11:00:00" and said["usd_low"] == -0.1 and said["usd_high"] == -0.3
    assert idea_change.summary(change, None)["rows"] == []


def test_a_plan_change_is_dropped_by_itself(keeper):
    """Spec 62 §3.3: when the goal is done, when its plan is made again, and when every task it names has started and it adds nothing."""
    slug = _idea(keeper)
    base = {"why": "w", "changed": ["Out"], "estimate": {"usd_low": 0.1, "usd_high": 0.3}, "drop": [], "add": []}
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"]), ("k3", "waiting", ["k2"])])
    idea_change.write(keeper.state, slug, {**base, "change": [{"id": "k2", "title": "Two"}], "drop": ["k3"]})
    plan = ideas.plan(keeper.state, slug)
    assert idea_change.live(keeper.state, slug, plan, "working") is not None and not idea_change.settle(keeper.state, slug)
    assert idea_change.live(keeper.state, slug, plan, "done") is None              # done: shown nowhere (a read drops nothing)
    assert idea_change.read(keeper.state, slug) is not None
    ideas.save_state(keeper.state, slug, state="done")
    assert idea_change.settle(keeper.state, slug) and idea_change.read(keeper.state, slug) is None
    ideas.save_state(keeper.state, slug, state="working")
    idea_change.write(keeper.state, slug, {**base, "change": [{"id": "k2", "title": "Two"}], "drop": ["k3"]})
    ideas.edit_plan(keeper.state, slug, lambda p: p["tasks"][1].update(state="running", started=OLD))
    assert idea_change.live(keeper.state, slug, ideas.plan(keeper.state, slug), "working") is not None      # k3 can still go
    ideas.edit_plan(keeper.state, slug, lambda p: p["tasks"][2].update(state="running", started=OLD))
    assert idea_change.live(keeper.state, slug, ideas.plan(keeper.state, slug), "working") is None
    assert idea_change.settle(keeper.state, slug) and idea_change.read(keeper.state, slug) is None
    idea_change.write(keeper.state, slug, {**base, "change": [{"id": "k2", "title": "Two"}], "drop": ["k3"], "add": [{"key": "n1", "title": "N", "brief": "b"}]})
    assert idea_change.live(keeper.state, slug, ideas.plan(keeper.state, slug), "working") is not None      # it adds: it stays
    idea_change.write(keeper.state, slug, {**base, "change": [], "drop": [], "add": []})
    assert idea_change.live(keeper.state, slug, ideas.plan(keeper.state, slug), "working") is not None      # a change of nothing: its stop says so
    ideas.edit_plan(keeper.state, slug, lambda p: p.update(passed_at=None))
    assert idea_change.live(keeper.state, slug, ideas.plan(keeper.state, slug), "plan") is None and idea_change.settle(keeper.state, slug)
    assert idea_change.read(keeper.state, slug) is None and not idea_change.settle(keeper.state, slug)


# -- §3.2: taken by the runner, under its lock ----------------------------------------------------------------------

@pytest.fixture
def runner(fake_repo):
    r = IdeaRunner(fake_repo, fake_repo / ".orkcraft", {"ideas": {"max_parallel": 4}}, None, limits=lambda: [], events=False)
    r.launched = []

    def launch(slug, task):                                       # no work is really done
        task.update(state="running", started=OLD)
        r._runs[(slug, task["id"])] = Run(threading.current_thread(), threading.Event())
        r.launched.append(task["id"])
    r._launch = launch
    return r


def _change(**more):
    return {"made_at": "2026-10-23T11:00:00", "why": "w", "changed": [], "estimate": {"usd_low": 0, "usd_high": 0},
            "change": [], "drop": [], "add": [], **more}


def _row(tid, **more):
    return {"id": tid, "title": f"New {tid}", "short": f"New {tid}", "brief": f"Brief {tid}", "kind": "docs", "tier": "laborer", "after": [], "role": "", **more}


def _add(key, **more):
    return {"key": key, "title": f"Added {key}", "short": f"Add {key}", "brief": f"Brief {key}", "kind": "code", "tier": "elder", "after": [], "role": "", **more}


def test_the_runner_applies_it_only_under_its_lock(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"])])
    done = threading.Event()
    taking = threading.Thread(target=lambda: (runner.revise_tasks(slug, _change(add=[_add("n1")])), done.set()))
    with runner._lock:                                      # the tick, or Review's answer, holds it
        taking.start()
        assert not done.wait(0.3) and list(_tasks(keeper, slug)) == ["k1", "k2"]
    assert done.wait(5) and list(_tasks(keeper, slug)) == ["k1", "k2", "k3"]


def test_the_plan_is_read_fresh_inside_the_lock(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"]), ("k3", "waiting", ["k2"])])
    change = _change(drop=["k3"], change=[_row("k2")])                          # made while k2 and k3 were not started
    with runner._lock:
        started = threading.Thread(target=lambda: runner.revise_tasks(slug, change))
        started.start()
        ideas.edit_plan(keeper.state, slug, lambda p: p["tasks"][1].update(state="running", started=OLD))      # …and k2 starts before it takes the lock
    started.join(5)
    after = _tasks(keeper, slug)
    assert list(after) == ["k1", "k2"] and after["k2"]["title"] == "Task k2" and after["k2"]["state"] == "running"


def test_taking_a_plan_change_drops_changes_and_adds_under_the_lock(keeper, runner):
    slug = _idea(keeper)
    plan = _plan(keeper, slug, [("k1", "merged", []), ("k2", "running", ["k1"]), ("k3", "ready", ["k1"]), ("k4", "waiting", ["k3"]),
                                ("k5", "waiting", ["k3", "k4"]), ("k6", "waiting", ["k1", "k2", "k3", "k4", "k5"], CHECK)],
                 todos=[{"id": "t1", "title": "A key", "kind": "confirm", "for": ["k5"], "done": False}], extra="kept")
    ideas._write_json(ideas.state_folder(keeper.state, slug) / "plan.json", {**plan, "tasks": [{**t, "branch": f"idea/{slug}/{t['id']}", "note": "n"}
                                                                                              for t in plan["tasks"]]})
    before = {t["id"]: dict(t) for t in ideas.plan(keeper.state, slug)["tasks"]}
    got = runner.revise_tasks(slug, _change(
        drop=["k4", "k2"], change=[_row("k3", after=["k2", "n1"], role="grunt"), _row("k2"), _row("k9")],
        add=[_add("n1", after=["k3", "k1", "k4"]), _add("n2", after=["n1", "k5", "zzz"], role="grunt")]))
    after = _tasks(keeper, slug)
    assert got == {"added": 2, "changed": 1, "dropped": 1, "left": ["Task k2"]}      # k2 started meanwhile; k9 is gone: neither is counted
    assert list(after) == ["k1", "k2", "k3", "k5", "k6", "k7", "k8"]
    assert after["k2"] == before["k2"]                                               # at work: as it is
    k3 = after["k3"]
    assert (k3["title"], k3["short"], k3["brief"], k3["kind"], k3["tier"], k3["role"]) == ("New k3", "New k3", "Brief k3", "docs", "laborer", "grunt")
    assert k3["after"] == ["k2", "k7"]                                               # n1 (k7) was named by the change first: it cannot wait for k3 as well
    assert k3["id"] == "k3" and k3["branch"] == before["k3"]["branch"] and k3["note"] == "n" and k3["started"] == ""
    assert k3["state"] == "waiting"                                                  # it was ready; now it waits for k2, not merged
    assert after["k5"]["after"] == ["k3"]                                            # out of the others' after, as skip_task does
    k7, k8 = after["k7"], after["k8"]
    assert (k7["state"], k7["after"], k7["title"], k7["kind"], k7["tier"], k7["role"], k7["short"]) == ("waiting", ["k1"], "Added n1", "code", "elder", "", "Add n1")
    assert k8["after"] == ["k7", "k5"] and k8["role"] == "grunt" and k7["brief"] == "Brief n1" and k7["branch"] == "" and k7["cost"] is None
    assert after["k6"]["after"] == ["k1", "k2", "k3", "k5", "k7", "k8"]               # the check task waits for the new tasks too
    new = ideas.plan(keeper.state, slug)
    assert new["passed_at"] == plan["passed_at"] and new["passed_by"] == "person" and new["extra"] == "kept" and new["todos"] == plan["todos"]
    assert new["estimate"]["tasks"] == 7 and new["estimate"]["usd_low"] > plan["estimate"]["usd_low"]      # made again from its tasks
    assert ideas.state(keeper.state, slug)["state"] == "working"


def test_an_added_task_never_takes_an_id_used_before(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"]), ("k3", "waiting", ["k1"]), ("k4", "waiting", ["k1"])],
          todos=[{"id": "t1", "title": "Key", "kind": "confirm", "for": ["k6"], "done": False}])
    runner.skip_task(slug, "k3")                                                      # a gap is not filled
    (ideas.state_folder(keeper.state, slug) / "k7.log").write_text("a task that ran\n")
    runner.revise_tasks(slug, _change(add=[_add("n1"), _add("n2")]))
    assert list(_tasks(keeper, slug)) == ["k1", "k2", "k4", "k8", "k9"]               # past k4, the to-do's k6 and the log's k7
    runner.skip_task(slug, "k9")
    runner.revise_tasks(slug, _change(add=[_add("n1")]))
    assert len(_tasks(keeper, slug)) == 5 and not set(_tasks(keeper, slug)) & {"k3", "k6", "k7"}       # a skipped task's id is not one that was used


def test_a_task_that_started_meanwhile_is_left_and_a_change_of_only_such_tasks_changes_nothing(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "running", []), ("k2", "review", ["k1"]), ("k3", "ready", ["k1"]), ("k4", "waiting", [])])
    ideas.edit_plan(keeper.state, slug, lambda p: p["tasks"][2].update(note="stopped by you", started=OLD))      # stopped on its own: it ran
    before = (ideas.state_folder(keeper.state, slug) / "plan.json").read_text()
    got = runner.revise_tasks(slug, _change(drop=["k1"], change=[_row("k2"), _row("k3")]))
    assert got == {"added": 0, "changed": 0, "dropped": 0, "left": ["Task k1", "Task k2", "Task k3"]}
    assert (ideas.state_folder(keeper.state, slug) / "plan.json").read_text() == before
    with pytest.raises(RunnerError, match="no plan"):
        runner.revise_tasks("nothing", _change())


def test_a_ready_task_that_now_waits_for_one_not_merged_waits_and_one_that_waits_for_merged_stays_ready(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "ready", ["k1"]), ("k3", "ready", ["k1"]), ("k4", "held", ["k1"])])
    runner.revise_tasks(slug, _change(change=[_row("k2", after=["k1"]), _row("k3", after=["k4"]), _row("k4", after=[])]))
    after = _tasks(keeper, slug)
    assert after["k2"]["state"] == "ready" and after["k3"]["state"] == "waiting" and after["k4"]["state"] == "held"


def test_a_changed_task_given_no_after_keeps_what_it_waits_for(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "waiting", ["k1"]), ("k3", "waiting", ["k1", "k2"])])
    row = {k: v for k, v in _row("k3").items() if k != "after"}
    runner.revise_tasks(slug, _change(change=[row]))
    assert _tasks(keeper, slug)["k3"]["after"] == ["k1", "k2"] and _tasks(keeper, slug)["k3"]["title"] == "New k3"


def test_an_added_task_is_taken_up_as_any_waiting_task_on_the_next_tick(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "running", ["k1"])])
    runner._active.append(slug)
    runner._runs[(slug, "k2")] = Run(threading.current_thread(), threading.Event())             # k2 is at work
    runner.revise_tasks(slug, _change(add=[_add("n1", after=["k1"]), _add("n2", after=["k2"])]))
    assert runner.launched == ["k3"]                                                  # n1 waits for merged k1: ready, then started; n2 waits for k2
    after = _tasks(keeper, slug)
    assert after["k3"]["state"] == "running" and after["k4"]["state"] == "waiting" and after["k4"]["after"] == ["k2"]
    ideas.edit_plan(keeper.state, slug, lambda p: p["tasks"][1].update(state="merged"))
    runner.tick()
    assert runner.launched == ["k3", "k4"]


def test_a_failed_goal_keeps_its_state_and_its_new_tasks_wait_for_its_work_to_start_again(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "failed", ["k1"])], state="failed")
    runner.revise_tasks(slug, _change(add=[_add("n1", after=["k1"])]))
    assert ideas.state(keeper.state, slug)["state"] == "failed" and runner.launched == []
    assert _tasks(keeper, slug)["k3"]["state"] == "waiting"
    runner.start(slug)                                                                # Start again: the new task is taken up with the rest
    assert "k3" in runner.launched


def test_taking_it_when_everything_is_merged_but_the_added_tasks_keeps_the_goal_working(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "merged", ["k1"])])
    runner.revise_tasks(slug, _change(add=[_add("n1", after=["k2"])]))
    assert ideas.state(keeper.state, slug)["state"] == "working" and _tasks(keeper, slug)["k3"]["after"] == ["k2"]


def test_an_add_that_waits_for_a_check_or_closes_a_cycle_through_one_is_left_out(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "waiting", ["k1"]), ("k3", "waiting", ["k1", "k2"], CHECK)])
    runner.revise_tasks(slug, _change(add=[_add("n1", after=["k3", "k2"])]))         # the check will wait for n1: n1 cannot wait for it
    after = _tasks(keeper, slug)
    assert after["k4"]["after"] == ["k2"] and after["k3"]["after"] == ["k1", "k2", "k4"]


def test_a_started_check_task_does_not_wait_for_the_added_tasks(keeper, runner):
    slug = _idea(keeper)
    _plan(keeper, slug, [("k1", "merged", []), ("k2", "review", ["k1"], CHECK)])
    runner.revise_tasks(slug, _change(add=[_add("n1", after=["k1"])]))
    assert _tasks(keeper, slug)["k2"]["after"] == ["k1"] and "k3" in _tasks(keeper, slug)
