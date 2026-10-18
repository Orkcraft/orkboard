"""Operations' state (docs/specs/38-operations.md §1, §3, §6, §7, §9, Tests → A): the person's folder, mode 600; the
way to by itself as pure functions; rules kept, declined and proposed; old texts forgotten."""
from __future__ import annotations

import datetime as dt
import json

from orkboard import settings
from orkboard.realm import call_log, op_runs
from tests.ops_stub import mode


def test_the_folder_is_beside_the_machine_settings(tmp_path, monkeypatch):
    assert op_runs.root() == settings.path().parent / "ops"
    monkeypatch.delenv("ORKCRAFT_SETTINGS_FILE")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert op_runs.root() == tmp_path / "xdg" / "orkcraft" / "ops"


def test_a_run_is_written_whole_and_private(tmp_path):
    base = tmp_path / "ops"
    run = op_runs.blank(op_runs.new_id(), "jira-task", "v1", {"what": "a secret word"})
    op_runs.save(base, run)
    path = op_runs.run_path(base, run["id"])
    assert mode(path) == 0o600 and mode(path.parent) == 0o700 and mode(base) == 0o700
    assert op_runs.load(base, run["id"])["fields"] == {"what": "a secret word"}
    assert op_runs.load(base, "../etc") is None and [r["id"] for r in op_runs.runs(base)] == [run["id"]]
    assert set(op_runs.load(base, run["id"])) <= set(op_runs.RUN_KEYS)


# -- by itself (§6) --------------------------------------------------------------------------------------------

def test_a_clean_check_sends_it_by_itself_at_trust_after():
    t = op_runs.fresh_trust("v1")
    one = op_runs.after_check(t, edited=False, trust_after=1)
    assert one["alone"] and one["why"] == "clean" and one["clean"] == 1
    three = t
    for n in range(2):
        three = op_runs.after_check(three, edited=False, trust_after=3)
        assert not three["alone"] and three["clean"] == n + 1
    three = op_runs.after_check(three, edited=False, trust_after=3)
    assert three["alone"] and three["clean"] == 3


def test_a_correction_not_right_a_new_version_and_check_again_send_it_back():
    alone = op_runs.after_check(op_runs.fresh_trust("v1"), False, 1)
    for back, why in ((op_runs.after_check(alone, True, 1), "edit"), (op_runs.after_not_right(alone), "not_right"),
                      (op_runs.after_version(alone, "v2"), "version"), (op_runs.after_reset(alone), "reset")):
        assert not back["alone"] and back["clean"] == 0 and back["why"] == why
    assert op_runs.after_version(alone, "v1") == alone                    # the same version: nothing changes
    assert op_runs.after_version(op_runs.fresh_trust(), "v1")["version"] == "v1"     # a first one is only kept
    assert op_runs.after_rules(op_runs.after_check(alone, True, 1)) == {**op_runs.after_check(alone, True, 1),
                                                                        "alone": True, "why": "rules"}


def test_a_doubt_a_high_risk_and_the_days_cap_stop_it_at_the_check():
    today = "2026-10-18"
    alone = op_runs.after_check(op_runs.fresh_trust("v1"), False, 1)
    assert op_runs.stops(alone, "medium", [], 20, today) == ""
    assert op_runs.stops(alone, "medium", ["maybe ABC-140"], 20, today) == "doubt"
    assert op_runs.stops(alone, "high", [], 20, today) == "high"
    assert op_runs.stops(op_runs.fresh_trust(), "medium", [], 20, today) == "checks"
    done = alone
    for _ in range(2):
        done = op_runs.after_alone(done, today)
    assert op_runs.stops(done, "medium", [], 2, today) == "daily"
    assert op_runs.stops(done, "medium", [], 2, "2026-10-19") == ""         # a new day
    assert op_runs.stop_words("daily", 20) == "checks again today: 20 done by itself"
    assert op_runs.stop_words("doubt", 20) == "at your check · a doubt"


# -- rules (§7) ----------------------------------------------------------------------------------------------------

def test_a_repeated_or_declined_line_is_dropped_and_at_most_three_kept():
    have = "### Titles\n- A title starts with the component in brackets.\n"
    declined = [{"lines": ["Never use the word please"]}]
    got = op_runs.new_rules(["a title starts with the component in brackets", "never use the word Please.",
                             "One", "One", "Two", "Three", "Four", 7, "x" * 300], have, declined)
    assert got == ["One", "Two", "Three"]
    assert op_runs.new_rules(["y" * 300], "", []) == ["y" * 200]


def test_take_appends_no_declines_one_proposal_waits_and_a_save_cleans_headings(tmp_path):
    base = tmp_path / "ops"
    op_runs.save_trust(base, "jira-task", op_runs.fresh_trust("v1"))
    op_runs.propose(base, "jira-task", ["first"], "why", "op-1")
    op_runs.propose(base, "jira-task", ["second"], "why", "op-2")
    assert op_runs.proposal(base, "jira-task")["lines"] == ["second"]      # a new one replaces the old
    op_runs.take_rules(base, "jira-task", ["A", "B"])
    op_runs.take_rules(base, "jira-task", ["C"])
    assert op_runs.rules(base, "jira-task") == "- A\n- B\n- C\n"
    op_runs.decline(base, "jira-task", ["D"], "too strict")
    assert op_runs.declined(base, "jira-task") == [{"lines": ["D"], "reason": "too strict",
                                                    "at": op_runs.declined(base, "jira-task")[0]["at"]}]
    trust = (base / "templates" / "jira-task" / "trust.json").read_text()
    op_runs.save_rules(base, "jira-task", "# Mine\n## Two\n- keep\n")
    assert op_runs.rules(base, "jira-task") == "### Mine\n### Two\n- keep\n"
    assert (base / "templates" / "jira-task" / "trust.json").read_text() == trust
    assert mode(base / "templates" / "jira-task" / "rules.md") == 0o600


# -- forgetting (§9) ------------------------------------------------------------------------------------------------

def test_after_keep_days_a_finished_run_keeps_its_row_and_its_calls_go(tmp_path):
    base = tmp_path / "ops"
    old = {**op_runs.blank("op-old-1", "jira-task", "v", {"what": "secret"}), "state": "done", "link": "https://x/1",
           "draft": {"summary": "secret"}, "at": "2026-09-01T10:00:00", "done_at": "2026-09-01T10:01:00", "cost": 0.2}
    new = {**op_runs.blank("op-new-1", "jira-task", "v", {"what": "fresh"}), "state": "done",
           "done_at": dt.datetime.now().isoformat(timespec="seconds")}
    waiting = {**op_runs.blank("op-wait-1", "jira-task", "v", {"what": "waits"}), "state": "check",
               "at": "2026-09-01T10:00:00"}
    for run in (old, new, waiting):
        op_runs.save(base, run)
    with call_log.kept(base / "calls", "ops"):
        call_log.record({"ORKCRAFT_TASK": "op-old-1"}, "call", "claude", "", "the secret prompt", "out", "", 0, 1.0)
        call_log.record({"ORKCRAFT_TASK": "op-new-1"}, "call", "claude", "", "the fresh prompt", "out", "", 0, 1.0)
    assert op_runs.forget_old(base, 14) == 1
    assert op_runs.load(base, "op-old-1") == {k: old[k] for k in op_runs.KEPT_KEYS}
    assert op_runs.load(base, "op-new-1")["fields"] == {"what": "fresh"}
    assert op_runs.load(base, "op-wait-1")["fields"] == {"what": "waits"}       # not finished: kept whole
    lines = call_log.read(base / "calls")
    assert [bool(line["raw"]) for line in lines] == [False, True] and lines[0]["forgotten"]
    texts = "".join(p.read_bytes().decode("latin-1") for p in (base / "calls").iterdir())
    assert "secret" not in texts and len(list((base / "calls").glob("*.json.gz"))) == 1
    assert op_runs.forget_old(base, 14) == 0


def test_an_event_is_plain_data_in_the_persons_folder(tmp_path):
    base = tmp_path / "ops"
    assert op_runs.event(base, "op_added", op="op-1", template="jira-task", version="abc", device="desktop")
    assert not op_runs.event(base, "op_nothing", op="op-1")
    row = json.loads((base / "events.jsonl").read_text())
    assert row["event"] == "op_added" and mode(base / "events.jsonl") == 0o600
