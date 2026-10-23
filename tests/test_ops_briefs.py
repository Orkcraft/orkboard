"""Team briefs on Operations (docs/specs/66-team-briefs.md §1–§6, §8 → A), against the stub `claude` of spec 38's tests:
a brief's manifest and its way with Keep and no action; templates about people (the fixed rule in the prompts, the
rules that judge a person dropped, the bound reads checked against the calls, a Slack read with no bound refused, the
events with no value); follow and Forget; standing briefs on the tick; the four built-in ones; `follow_days`."""
from __future__ import annotations

import datetime as dt
import gzip
import json
import time

import pytest

from orkboard import settings
from orkboard.core import op_briefs
from orkboard.core.op_commands import OpsError
from orkboard.core.op_runner import BRIEF_LINE, PEOPLE_RULE, OpRunner
from orkboard.realm import event_log, op_runs, op_standing, op_templates
from orkboard.sources.limits import Limit
from tests.ops_stub import Stub, mode, stream

SERVERS = {"jira": "Atlassian", "github": "github", "slack": "slack"}
ANA = {"who": "Ana Lima", "notes": "Ask about the Quokka migration", "repos": "acme/shop", "team": "ABC"}
DAILY = {"team": "ABC", "repos": "acme/shop", "channels": "#team-checkout"}
LIST = "mcp__slack__slack_list_channels"
HISTORY = "mcp__slack__slack_get_channel_history"
CHANNELS = json.dumps({"ok": True, "channels": [{"id": "C01", "name": "team-checkout", "topic": {"value": "x"}},
                                                {"id": "C02", "name": "random"}]})


@pytest.fixture
def stub(tmp_path, monkeypatch):
    return Stub(tmp_path, monkeypatch)


@pytest.fixture
def runner(tmp_path, stub):
    box = {"ops": settings.clean_ops({"servers": SERVERS}), "limits": []}
    r = OpRunner(tmp_path / "ops", settings=lambda: box["ops"], limits=lambda: box["limits"])
    r.box = box
    yield r
    r.stop_all()
    r.wait_idle()


def tools_of(name: str) -> list[str]:
    return op_templates.tools(op_templates.find()[name], SERVERS)[0]


def briefed(stub, name="one-on-one", text="## Their work\n- ABC-1 done", uses=(), doubts=(), found=()) -> None:
    part = "agenda" if name == "one-on-one" else "brief"
    stub.answer(stream(tools_of(name), uses=list(uses),
                       text=json.dumps({"draft": {part: text}, "found": list(found), "doubts": list(doubts),
                                        "args": {"never": "kept"}})))


def wait(runner, op_id, *states, timeout=10.0) -> dict:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        run = op_runs.load(runner.base, op_id)
        if run and run["state"] in states and op_id not in runner.running():
            return run
        time.sleep(0.02)
    raise AssertionError(f"{op_id} never reached {states}: {op_runs.load(runner.base, op_id)}")


def at_check(runner, stub, name="one-on-one", fields=ANA, **kw) -> dict:
    briefed(stub, name, **kw)
    return wait(runner, runner.add(name, fields), "check", "done", "failed")


def flag(argv, name):
    return argv[argv.index(name) + 1] if name in argv else None


def trust(runner, name="one-on-one") -> dict:
    return op_runs.trust(runner.base, name)


def manifest(folder, body: str, skill: str = "# A brief\nRead and write.\n"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(skill, encoding="utf-8")
    (folder / "orkboard.toml").write_text(body, encoding="utf-8")
    return op_templates.read(folder)


HEAD = '''title = "Mine"
servers = {{ slack = "Slack", jira = "Jira" }}
{extra}
[[fields]]
name = "who"
label = "Who"

[[fields]]
name = "channels"
label = "Channels"

[[draft]]
name = "brief"
label = "Brief"
type = "long"

[prepare]
tools = ["mcp__{{jira}}__getJiraIssue", "mcp__{{slack}}__slack_list_channels", "mcp__{{slack}}__slack_get_channel_history"]
{bound}
'''
BRIEF = '[brief]\nlabel = "Keep it"\n'
ACT = '[act]\ntool = "mcp__{jira}__createJiraIssue"\nlabel = "Create in Jira"\n'
BOUND = ('[[prepare.bound]]\ntool = "mcp__{slack}__slack_get_channel_history"\narg = "channel_id"\nfield = "channels"\n'
         'lookup = "mcp__{slack}__slack_list_channels"\n')


# -- §1 a brief -------------------------------------------------------------------------------------------------------

def test_a_template_briefs_or_acts_never_both(tmp_path):
    both = manifest(tmp_path / "both", HEAD.format(extra="", bound="") + BRIEF + ACT)
    assert both.problem == "a template briefs or acts, not both: it has [act] and [brief]"
    alone = manifest(tmp_path / "alone", HEAD.format(extra="", bound="") + BRIEF)
    assert alone.problem == "" and alone.brief and alone.act == "" and alone.act_label == "Keep it"
    assert op_templates.tools(alone, {"jira": "J", "slack": "S"})[1] == ""         # no action's tool
    acts = manifest(tmp_path / "acts", HEAD.format(extra="", bound="") + ACT)
    assert acts.problem == "" and not acts.brief and acts.act_label == "Create in Jira"
    assert manifest(tmp_path / "none", HEAD.format(extra="", bound="")).problem.startswith("its [act] names")
    at = HEAD.format(extra="", bound="").replace('type = "long"\n', 'type = "long"\nat = "body"\n') + BRIEF
    assert manifest(tmp_path / "at", at).problem == "a brief has no action: its fields and draft parts have no at"
    low = manifest(tmp_path / "low", HEAD.format(extra='risk = "low"', bound="") + BRIEF)
    assert low.risk == "low"                                                   # a brief's least is low …
    about = manifest(tmp_path / "about", HEAD.format(extra='risk = "low"\npeople = true\nreads = "Slack: #a"',
                                                       bound=BOUND) + BRIEF)
    assert about.problem == "" and about.risk == "medium"                      # … a template about people's medium


def test_a_briefs_way_has_no_action(runner, stub):
    run = at_check(runner, stub)
    assert run["state"] == "check" and run["brief"] is True and run["args"] == {}   # the answer's args are not kept
    argv = stub.calls()[0]["argv"]
    assert flag(argv, "--allowedTools").split(",") == tools_of("one-on-one")
    prompt = flag(argv, "-p")
    assert prompt.startswith(BRIEF_LINE) and "The action's tool" not in prompt and '"args"' not in prompt
    with pytest.raises(OpsError, match="A brief does nothing outside: Keep for the 1:1"):
        runner.act(run["id"], {}, {})
    with pytest.raises(OpsError, match="Who changed: Prepare again first"):
        runner.keep(run["id"], {"who": "Bob"}, {})
    runner.keep(run["id"], {}, {})
    kept = wait(runner, run["id"], "done")
    assert kept["acted"] is False and kept["link"] == "" and kept["draft"]["agenda"].startswith("## Their work")
    assert len(stub.calls()) == 1                                              # Keep calls nothing
    states = [json.loads(x).get("event") for x in (runner.base / "events.jsonl").read_text().splitlines()]
    assert states == ["op_added", "op_prepared", "op_checked", "op_kept", "op_trust"]


def test_a_clean_keep_counts_and_the_next_goes_by_itself(runner, stub):
    runner.keep(at_check(runner, stub)["id"])
    assert trust(runner)["alone"] and trust(runner)["why"] == "clean"
    briefed(stub)
    alone = wait(runner, runner.add("one-on-one", {**ANA, "who": "Bob"}), "done", "check")
    assert alone["state"] == "done" and alone["alone"] is True and alone["done_at"]   # preparing → done, no check
    assert trust(runner)["today"]["alone_done"] == 1
    runner.not_right(alone["id"], "put the stuck items first")                 # Not right, as an action's
    assert not trust(runner)["alone"] and trust(runner)["why"] == "not_right"


def test_a_corrected_keep_asks_the_learn_call(runner, stub):
    run = at_check(runner, stub)
    stub.answer(stream([], text=json.dumps({"rules": ["Put the stuck items first"], "why": "the person's order"})))
    runner.keep(run["id"], {}, {"agenda": "## Where they got stuck\n- ABC-2\n## Their work\n- ABC-1 done"})
    runner.wait_idle()
    assert not trust(runner)["alone"] and trust(runner)["why"] == "edit"
    assert op_runs.load(runner.base, run["id"])["draft"]["agenda"].startswith("## Where they got stuck")
    learn = flag(stub.calls()[-1]["argv"], "-p")
    assert "--allowedTools" not in stub.calls()[-1]["argv"] and "→ '## Where they got stuck" in learn
    assert op_runs.proposal(runner.base, "one-on-one")["lines"] == ["Put the stuck items first"]


# -- §2 templates about people ---------------------------------------------------------------------------------------

def test_a_people_templates_prompts_hold_the_rule_and_a_rule_judging_a_person_is_dropped(runner, stub):
    run = at_check(runner, stub)
    prompt = flag(stub.calls()[0]["argv"], "-p")
    assert PEOPLE_RULE in prompt and prompt.index("Its rules") < prompt.index(PEOPLE_RULE) < prompt.index("The fields")
    stub.answer(stream([], text=json.dumps({"rules": ["Give each person a rating from 1 to 5",
                                                      "Name their weaknesses first", "Put the stuck items first",
                                                      "Rank the team by commits"], "why": "w"})))
    runner.keep(run["id"], {}, {"agenda": "other"})
    runner.wait_idle()
    assert PEOPLE_RULE in flag(stub.calls()[-1]["argv"], "-p")                 # the learn call gets it too
    assert op_runs.proposal(runner.base, "one-on-one")["lines"] == ["Put the stuck items first"]
    briefed(stub, "refinement-brief")
    wait(runner, runner.add("refinement-brief", {"team": "ABC"}), "check")
    assert PEOPLE_RULE not in flag(stub.calls()[-1]["argv"], "-p")             # not about people: no rule


@pytest.mark.parametrize("line,judges", [("Rate them by their performance", True), ("Note who is lazy", True),
                                         ("List her strengths and weak sides", True), ("Score each one", True),
                                         ("Show the ranking of the team", True), ("Say how productive he was", True),
                                         ("Put the stuck items first", False), ("Link every ticket", False),
                                         ("Ask what gets in the way of the release", False)])
def test_people_words(line, judges):
    assert op_briefs.about_people(line) is judges


def test_a_people_template_with_a_slack_read_and_no_bound_is_refused_at_load(tmp_path):
    people = 'people = true\nreads = "Slack: the channels you name"'
    open_read = manifest(tmp_path / "open", HEAD.format(extra=people, bound="") + BRIEF)
    assert open_read.problem == op_templates.SLACK_ONLY == "a brief about people reads only the channels named"
    bound = manifest(tmp_path / "bound", HEAD.format(extra=people, bound=BOUND) + BRIEF)
    assert bound.problem == "" and bound.bound[0]["arg"] == "channel_id"       # the list of channels is its lookup
    no_lookup = BOUND.replace('lookup = "mcp__{slack}__slack_list_channels"\n', "")
    assert manifest(tmp_path / "nolook", HEAD.format(extra=people, bound=no_lookup) + BRIEF).problem == op_templates.SLACK_ONLY
    assert manifest(tmp_path / "work", HEAD.format(extra="", bound="") + BRIEF).problem == ""   # not about people
    unsaid = manifest(tmp_path / "unsaid", HEAD.format(extra="people = true", bound=BOUND) + BRIEF)
    assert unsaid.problem.startswith("its reads")                              # what it reads is said on its form
    wrong = manifest(tmp_path / "wrong", HEAD.format(extra=people, bound=BOUND.replace('"channels"', '"nope"')) + BRIEF)
    assert wrong.problem.startswith("a [[prepare.bound]] names one of its [prepare] tools")


def _raws(base, op_id) -> list:
    rows = [r for r in op_runs.lines(base / "calls" / "calls.jsonl") if r.get("task") == op_id]
    return [r for r in rows if r.get("raw") and (base / "calls" / r["raw"]).exists()]


@pytest.mark.parametrize("channel", ["C01", "team-checkout", "#Team-Checkout"])
def test_a_bound_read_of_a_named_channel_passes(runner, stub, channel):
    run = at_check(runner, stub, "daily-brief", DAILY,
                   uses=[(LIST, {}, False, CHANNELS), (HISTORY, {"channel_id": channel, "limit": 50})])
    assert run["state"] == "check" and _raws(runner.base, run["id"])


@pytest.mark.parametrize("given", [{"channel_id": "C02"}, {"channel_id": "random"}, {"limit": 5},
                                   {"channel_id": ["C01", "C02"]}])
def test_a_bound_read_of_a_channel_not_named_fails_the_brief_and_removes_its_output(runner, stub, given):
    run = at_check(runner, stub, "daily-brief", DAILY,
                   uses=[(LIST, {}, False, CHANNELS), (HISTORY, given, False, "the secret of #random")])
    assert run["state"] == "failed" and run["why"] == "it read a channel you did not name: nothing was kept"
    assert run["acted"] is False and run["draft"] == {} and run["found"] == []
    rows = [r for r in op_runs.lines(runner.base / "calls" / "calls.jsonl") if r.get("task") == run["id"]]
    assert rows and all(r["raw"] == "" and r["forgotten"] for r in rows) and not _raws(runner.base, run["id"])
    texts = "".join(gzip.decompress(p.read_bytes()).decode() for p in (runner.base / "calls").glob("*.gz"))
    assert "the secret of #random" not in texts


def test_a_lookup_cut_short_still_names_its_channels():
    long = json.dumps({"channels": [{"id": f"C{n:03d}", "name": f"c{n}", "purpose": "p" * 50} for n in range(400)]})
    cut = long[:-2000]                                                        # an answer cut short: not JSON any more
    bounds = [{"tool": HISTORY, "arg": "channel_id", "field": "channels", "lookup": LIST}]
    events = [{"type": "tool_use", "id": "a", "name": LIST, "input": {}},
              {"type": "tool_result", "id": "a", "is_error": False, "text": cut},
              {"type": "tool_use", "id": "b", "name": HISTORY, "input": {"channel_id": "C123"}}]
    assert op_briefs.breach(bounds, events, {"channels": "c123"}) == ""
    assert op_briefs.breach(bounds, events, {"channels": "c124"}) == HISTORY


def test_the_events_of_a_people_template_hold_no_fields_value(runner, stub):
    runner.keep(at_check(runner, stub)["id"])
    briefed(stub, "daily-brief", uses=[(LIST, {}, False, CHANNELS), (HISTORY, {"channel_id": "C01"})])
    wait(runner, runner.add("daily-brief", DAILY), "check")
    runner.forget_value("one-on-one", "Ana Lima")
    runner.standing_add("daily-brief", DAILY, [0, 1, 2, 3, 4], "09:30")
    text = (runner.base / "events.jsonl").read_text()
    for value in (*ANA.values(), *DAILY.values(), "team-checkout", "Ana"):
        assert value not in text, value
    assert {"op_kept", "op_forgot", "op_standing"} <= {json.loads(x)["event"] for x in text.splitlines()}


# -- §4 follow, §2 Forget ----------------------------------------------------------------------------------------------

def test_follow_gives_the_last_kept_brief_of_the_same_value_and_keeps_one_per_value(runner, stub):
    first = at_check(runner, stub, text="Last time: promised the Quokka plan by Friday")
    runner.keep(first["id"])
    briefed(stub)
    second = wait(runner, runner.add("one-on-one", {**ANA, "who": "  ana lima "}), "done", "check")
    prompt = flag(stub.calls()[-1]["argv"], "-p")
    assert "Last time (the last brief kept for the same Who" in prompt and "promised the Quokka plan" in prompt
    assert second["follows"] == first["id"]
    briefed(stub)
    bob = wait(runner, runner.add("one-on-one", {**ANA, "who": "Bob"}), "done", "check")
    assert "promised the Quokka plan" not in flag(stub.calls()[-1]["argv"], "-p") and bob["follows"] == ""
    assert "(none kept yet)" in flag(stub.calls()[-1]["argv"], "-p")
    if second["state"] == "check":
        runner.keep(second["id"])
    older = op_runs.load(runner.base, first["id"])
    assert set(older) <= set(op_runs.KEPT_KEYS)                                 # one kept per value: the older is cut
    assert op_runs.load(runner.base, bob["id"])["draft"]                         # another value's stays


def _kept(base, op_id, who, days_ago, template="one-on-one", brief=True):
    when = (dt.datetime.now() - dt.timedelta(days=days_ago)).isoformat(timespec="seconds")
    run = {**op_runs.blank(op_id, template, "v", {"who": who}, brief=brief), "state": "done",
           "draft": {"agenda": f"about {who}"}, "at": when, "done_at": when}
    op_runs.save(base, run)


def test_the_last_kept_brief_of_a_value_is_kept_up_to_follow_days(tmp_path):
    base = tmp_path / "ops"
    _kept(base, "op-ana-1", "Ana", 30)                                         # the last of Ana: past keep_days, kept
    _kept(base, "op-bob-1", "Bob", 120)                                        # the last of Bob, past follow_days
    _kept(base, "op-jira-1", "Ana", 30, template="jira-task", brief=False)     # not a follow brief: keep_days
    op_runs.forget_old(base, 14, follow={"one-on-one": "who"}, follow_days=90)
    assert op_runs.load(base, "op-ana-1")["draft"]
    assert set(op_runs.load(base, "op-bob-1")) <= set(op_runs.KEPT_KEYS)
    assert set(op_runs.load(base, "op-jira-1")) <= set(op_runs.KEPT_KEYS)
    assert op_runs.last_kept(base, "one-on-one", "who", " ANA ")["id"] == "op-ana-1"
    op_runs.forget_old(base, 14, follow={"one-on-one": "who"}, follow_days=20)
    assert set(op_runs.load(base, "op-ana-1")) <= set(op_runs.KEPT_KEYS)


def test_follow_gives_nothing_older_than_follow_days(runner, stub):
    _kept(runner.base, "op-ana-old", "Ana Lima", 100)
    briefed(stub)
    run = wait(runner, runner.add("one-on-one", ANA), "check")
    assert run["follows"] == "" and "about Ana Lima" not in flag(stub.calls()[-1]["argv"], "-p")


def test_forget_removes_every_operation_and_call_of_that_value_and_no_other(runner, stub):
    ana = at_check(runner, stub)
    runner.keep(ana["id"])
    runner.trust_reset("one-on-one")                                           # the next ones stop at the check
    briefed(stub)
    ana2 = wait(runner, runner.add("one-on-one", {**ANA, "who": "ANA LIMA"}), "check")
    briefed(stub)
    bob = wait(runner, runner.add("one-on-one", {**ANA, "who": "Bob"}), "check", "done")
    st = runner.standing_add("one-on-one", ANA, [0], "10:00")
    other = runner.standing_add("one-on-one", {**ANA, "who": "Bob"}, [0], "10:00")
    assert runner.forget_value("one-on-one", " ana lima ") == 2
    assert op_runs.load(runner.base, ana["id"]) is None and op_runs.load(runner.base, ana2["id"]) is None
    assert op_runs.load(runner.base, bob["id"])["fields"]["who"] == "Bob" and _raws(runner.base, bob["id"])
    assert not _raws(runner.base, ana["id"]) and not _raws(runner.base, ana2["id"])
    texts = "".join(gzip.decompress(p.read_bytes()).decode() for p in (runner.base / "calls").glob("*.gz"))
    assert "Ana Lima" not in texts and "ANA LIMA" not in texts
    assert [i["id"] for i in op_standing.load(runner.base)] == [other] and st != other
    with pytest.raises(OpsError, match="Before the daily follows no one"):
        runner.forget_value("daily-brief", "ABC")
    with pytest.raises(OpsError, match="Say whose: Who"):
        runner.forget_value("one-on-one", "  ")


# -- §3 standing briefs ------------------------------------------------------------------------------------------------

MONDAY = dt.datetime(2026, 10, 19, 8, 0)


def test_a_standing_brief_is_checked_and_kept_mode_600(runner):
    runner.clock = lambda: MONDAY
    with pytest.raises(OpsError, match="Pick the days of the week"):
        runner.standing_add("daily-brief", DAILY, [], "09:30")
    with pytest.raises(OpsError, match="The meeting's time is HH:MM"):
        runner.standing_add("daily-brief", DAILY, [0], "25:00")
    with pytest.raises(OpsError, match="New Jira task acts: only a brief is prepared before a meeting"):
        runner.standing_add("jira-task", {"what": "x"}, [0], "09:30")
    with pytest.raises(OpsError, match="Who is needed"):
        runner.standing_add("one-on-one", {}, [0], "09:30")
    st = runner.standing_add("daily-brief", DAILY, [0, 1, 2, 3, 4], "09:30")
    path = runner.base / "standing.json"
    assert mode(path) == 0o600
    item = op_standing.load(runner.base)[0]
    assert item == {"id": st, "template": "daily-brief", "fields": {**DAILY, "since": "the last working day"},
                    "days": [0, 1, 2, 3, 4], "at": "09:30", "before": 30, "last": "", "skipped": ""}
    assert op_standing.words(item, "Before the daily") == "Before the daily: weekdays 09:30"
    runner.standing_change(st, {"at": "10:00", "before": 15})
    assert op_standing.load(runner.base)[0]["at"] == "10:00"
    runner.standing_stop(st)
    assert op_standing.load(runner.base) == []
    for n in range(op_standing.MAX):
        runner.standing_add("daily-brief", DAILY, [n % 7], "09:30")
    with pytest.raises(OpsError, match="At most 12 standing briefs"):
        runner.standing_add("daily-brief", DAILY, [0], "09:30")


def test_a_standing_brief_is_added_at_its_time_once_a_day_and_skipped_when_its_meeting_passed(runner, stub):
    runner.clock = lambda: MONDAY
    st = runner.standing_add("daily-brief", DAILY, [0, 1], "09:30", 30)
    runner.standing(MONDAY.replace(hour=8, minute=59))
    assert op_runs.runs(runner.base) == []
    briefed(stub, "daily-brief")
    runner.standing(MONDAY.replace(hour=9, minute=5))
    runner.standing(MONDAY.replace(hour=9, minute=10))                       # once a day
    added = op_runs.runs(runner.base)
    assert len(added) == 1 and added[0]["standing"] == st and added[0]["device"] == "standing"
    assert wait(runner, added[0]["id"], "check")["fields"]["channels"] == "#team-checkout"
    tuesday = MONDAY + dt.timedelta(days=1)
    runner.standing(tuesday.replace(hour=9, minute=40))                      # the machine was off past the meeting
    runner.standing(tuesday.replace(hour=11))
    assert len(op_runs.runs(runner.base)) == 1
    item = op_standing.load(runner.base)[0]
    assert item["skipped"] == "skipped: the machine was off" and item["last"] == tuesday.date().isoformat()
    runner.standing(tuesday + dt.timedelta(days=1, hours=1, minutes=10))      # Wednesday is not one of its days
    assert len(op_runs.runs(runner.base)) == 1
    whats = [json.loads(x).get("what") for x in (runner.base / "events.jsonl").read_text().splitlines()
             if json.loads(x)["event"] == "op_standing"]
    assert whats == ["set", "added", "skipped"]


def test_a_standing_brief_set_after_todays_meeting_is_no_skip(runner):
    runner.clock = lambda: MONDAY.replace(hour=11)
    runner.standing_add("daily-brief", DAILY, [0], "09:30")
    runner.standing(MONDAY.replace(hour=11, minute=1))
    assert op_standing.load(runner.base)[0]["skipped"] == "" and op_runs.runs(runner.base) == []


def test_a_standing_brief_keeps_the_reserve_and_the_persons_own_does_not(runner, stub):
    later = dt.datetime.now() + dt.timedelta(hours=3)
    runner.box["limits"] = [Limit("claude", "", "session", 0.08, later)]     # under any reserve, over NEARLY
    runner.clock = lambda: MONDAY
    runner.standing_add("daily-brief", DAILY, [0], "09:30")
    runner.standing(MONDAY.replace(hour=9, minute=5))
    held = wait(runner, op_runs.runs(runner.base)[0]["id"], "held")
    assert held["why"] == "waits for limits: prepared when the window allows" and not stub.calls()
    briefed(stub)
    own = wait(runner, runner.add("one-on-one", ANA), "check")                # the person's press: no reserve
    assert own["state"] == "check"
    runner.clock = lambda: MONDAY.replace(hour=12)
    runner.tick(0)
    assert op_runs.load(runner.base, held["id"])["state"] == "held"
    runner.box["limits"] = [Limit("claude", "", "session", 0.8, later)]
    briefed(stub, "daily-brief")
    runner.tick(100)
    assert wait(runner, held["id"], "check")["state"] == "check"


def test_a_standing_brief_waits_for_the_cap_instead_of_being_refused(runner, stub):
    runner.cap = lambda: (11.0, 10.0)
    runner.clock = lambda: MONDAY
    runner.standing_add("daily-brief", DAILY, [0], "09:30")
    runner.standing(MONDAY.replace(hour=9, minute=5))
    held = wait(runner, op_runs.runs(runner.base)[0]["id"], "held")
    assert held["held"] == "prepare" and not stub.calls()


# -- §5 the four built-in briefs, §6 the setting, ops.list -----------------------------------------------------------

def test_the_four_built_in_briefs_as_spec_66_says_them():
    found = op_templates.find()
    daily, retro, refine, one = (found[n] for n in ("daily-brief", "retro-brief", "refinement-brief", "one-on-one"))
    for t in (daily, retro, refine, one):
        assert t.problem == "" and t.brief and t.act == "" and t.builtin
        assert t.reads and not any(op_templates.short(x).startswith(("create", "edit", "add", "post", "update",
                                                                         "merge", "slack_post", "slack_reply"))
                                   for x in t.prepare)                       # each reads, changes nothing
    assert (daily.people, retro.people, refine.people, one.people) == (True, True, False, True)
    assert (daily.follow, retro.follow, refine.follow, one.follow) == ("", "team", "", "who")
    assert [t.act_label for t in (daily, retro, refine, one)] == ["Keep for the daily", "Keep for the retro",
                                                                  "Keep for the refinement", "Keep for the 1:1"]
    assert [f["name"] for f in daily.fields] == ["team", "repos", "channels", "since"]
    assert all(daily.field_of(n)["remember"] for n in ("team", "repos", "channels"))
    assert daily.field_of("since")["options"] == ["the last working day", "yesterday"]
    assert [f["name"] for f in retro.fields] == ["team", "sprint", "repos", "channels"]
    assert retro.field_of("sprint")["required"] and all(retro.field_of(n)["remember"] for n in ("team", "repos", "channels"))
    assert [f["name"] for f in refine.fields] == ["team", "which", "count"]
    assert refine.field_of("which")["options"] == ["the next sprint", "the top of the backlog"]
    assert refine.field_of("count")["options"] == ["5", "10", "20"] and refine.servers == {"jira": "Jira"}
    assert [f["name"] for f in one.fields] == ["who", "notes", "repos", "team"]
    assert one.field_of("who")["required"] and one.field_of("notes")["type"] == "long" and one.field_of("team")["remember"]
    assert [p["name"] for p in one.draft] == ["agenda"] and [p["name"] for p in daily.draft] == ["brief"]
    assert not any(op_templates.slack(one, x) for x in one.prepare) and "Slack: none" in one.reads   # a 1:1 reads no Slack
    assert not any(op_templates.slack(refine, x) for x in refine.prepare)
    for t in (daily, retro):
        assert t.servers == {"jira": "Jira", "github": "GitHub", "slack": "Slack"}
        assert {op_templates.short(b["tool"]): (b["arg"], b["field"], op_templates.short(b["lookup"])) for b in t.bound} == {
            "slack_get_channel_history": ("channel_id", "channels", "slack_list_channels"),
            "slack_get_thread_replies": ("channel_id", "channels", "slack_list_channels")}
        assert "never direct messages" in t.reads
    assert daily.reads == ("Jira: the project you name · GitHub: the repos you name · Slack: the channels you name, "
                           "never direct messages")
    shorts = {n: {op_templates.short(x) for x in found[n].prepare} for n in found}
    assert {"searchJiraIssuesUsingJql", "list_pull_requests", "pull_request_read", "slack_get_channel_history"} <= shorts["daily-brief"]
    assert {"lookupJiraAccountId", "search_users", "search_pull_requests"} <= shorts["one-on-one"]
    assert shorts["refinement-brief"] == {"getAccessibleAtlassianResources", "getVisibleJiraProjects",
                                          "searchJiraIssuesUsingJql", "getJiraIssue"}


def test_follow_days_is_a_setting():
    assert settings.OPS["follow_days"] == 90 and settings.clean_ops(None)["follow_days"] == 90
    assert settings.clean_ops({"follow_days": 30})["follow_days"] == 30
    for broken in (7, 400, "30", True):
        assert settings.clean_ops({"follow_days": broken})["follow_days"] == 90


def test_ops_list_says_what_a_brief_reads_and_its_standing_briefs(stub, fake_repo):
    from orkboard.gui.board_host import CommandError, Orkboard
    host = Orkboard(fake_repo)
    try:
        host.command("ops.set", {"servers": SERVERS, "follow_days": 60})
        listed = host.command("ops.list")
        assert listed["settings"]["follow_days"] == 60
        with pytest.raises(CommandError, match="Keep the last 1:1 brief for 14 to 365 days"):
            host.command("ops.set", {"follow_days": 7})
        rows = {t["name"]: t for t in listed["templates"]}
        one = rows["one-on-one"]
        assert one["brief"] and one["people"] and one["follow"] == "who" and one["act_label"] == "Keep for the 1:1"
        assert one["reads"].startswith("Jira: the issues they own") and one["does"] == "prepares a page, does nothing outside"
        assert one["forget"] == {"field": "who", "label": "Who"} and "forget" not in rows["daily-brief"]
        assert not rows["refinement-brief"]["people"] and "does" not in rows["jira-task"]
        assert rows["jira-task"]["brief"] is False and rows["jira-task"]["reads"] == ""
        host.ops.runner.clock = lambda: MONDAY
        st = host.command("ops.standing_add", {"template": "daily-brief", "fields": DAILY, "days": [0, 1, 2, 3, 4],
                                               "at": "09:30"})["id"]
        row = host.command("ops.list")["standing"][0]
        assert row["id"] == st and row["words"] == "Before the daily: weekdays 09:30" and row["title"] == "Before the daily"
        assert set(row) == {*op_standing.KEYS, "title", "words"}
        assert host.command("ops.standing_change", {"id": st, "at": "10:15"}) == {"ok": True}
        assert host.command("ops.list")["standing"][0]["words"] == "Before the daily: weekdays 10:15"
        assert host.command("ops.standing_stop", {"id": st}) == {"ok": True}
        assert host.command("ops.list")["standing"] == []
        assert host.command("ops.forget", {"template": "one-on-one", "value": "Nobody"}) == {"removed": 0}
        assert not [r for r in event_log.read(fake_repo) if r["event"].startswith("op_")]   # never a project's log
    finally:
        host.ops.stop_all()
        host.ops.runner.wait_idle()
        host.close()
