"""The local event log (realm/event_log.py, docs/design/dogfood-logs.md §3): exact, local, never sent."""
import datetime as dt
import io
import json
import zipfile

from orkboard.realm import analytics, event_log


def test_an_event_is_one_exact_line_in_the_towns_folder(tmp_path):
    assert event_log.record(tmp_path, event_log.ASKED, building="pool", ork="Grunt", task="t1", harness="claude",
                            text="Which port?", options=["8080", "3000"], via="block")
    [row] = event_log.read(tmp_path)
    assert (tmp_path / ".orkcraft" / "usage" / "events.jsonl").is_file()
    assert row["event"] == "question_asked" and row["text"] == "Which port?" and row["options"] == ["8080", "3000"]
    assert dt.datetime.fromisoformat(row["at"]).tzinfo is not None


def test_an_unknown_event_or_no_root_writes_nothing(tmp_path):
    assert not event_log.record(tmp_path, "something_else", x=1)
    assert not event_log.record(None, event_log.ASKED, text="demo")
    assert event_log.read(tmp_path) == []


def test_only_plain_data_is_kept_and_long_text_is_cut(tmp_path):
    event_log.record(tmp_path, event_log.ASSUMED, text="x" * 5000, obj=object(), n=3, ok=True)
    [row] = event_log.read(tmp_path)
    assert len(row["text"]) == event_log.TEXT_MAX and "obj" not in row and row["n"] == 3 and row["ok"] is True


def test_counts_and_the_weeks_summary(tmp_path):
    old = dt.datetime(2026, 10, 1, 9, tzinfo=dt.timezone.utc)
    (tmp_path / event_log.PATH).parent.mkdir(parents=True)
    (tmp_path / event_log.PATH).write_text(json.dumps(event_log.line(event_log.ASKED, at=old)) + "\nnot json\n")
    for who, waited in (("person", 600), ("person", 60), ("steward", 5), ("person", 120)):
        event_log.record(tmp_path, event_log.ANSWERED, building="pool", task="t", who=who, waited_s=waited)
    event_log.record(tmp_path, event_log.STOPPED, building="pool", task="t")
    c = event_log.counts(tmp_path, since="2026-10-10")
    assert c["question_answered"] == 4 and c["run_stopped_on_question"] == 1 and c["question_asked"] == 0
    assert event_log.counts(tmp_path)["question_asked"] == 1
    s = event_log.summary(tmp_path, since="2026-10-10")
    assert s["answer_wait_median_s"] == 120 and s["counts"]["quest_done"] == 0


def test_the_analytics_zip_carries_the_periods_events(tmp_path):
    today = dt.date.today().isoformat()
    event_log.record(tmp_path, event_log.QUEST_DONE, quest="1", seconds=40)
    z = zipfile.ZipFile(io.BytesIO(analytics.pack(tmp_path, [today], {}, lambda b, d: [], lambda b, d: [])))
    [row] = [json.loads(x) for x in z.read("events.jsonl").decode().splitlines()]
    assert row["event"] == "quest_done" and row["quest"] == "1"


def test_the_gate_merging_dev_into_main_is_an_event_with_its_counts(tmp_path):
    assert event_log.GATE_MERGED == "gate_merged" and event_log.GATE_MERGED in event_log.EVENTS
    assert event_log.record(tmp_path, event_log.GATE_MERGED, commits=3, ideas=2, files=5, how="merge", pushed=False,
                            into="dev", main="main", device="desktop")
    [row] = event_log.read(tmp_path)
    assert (row["event"], row["commits"], row["ideas"], row["files"], row["how"], row["pushed"]) == ("gate_merged", 3, 2, 5, "merge", False)
    assert event_log.counts(tmp_path)["gate_merged"] == 1 and len(set(event_log.EVENTS)) == len(event_log.EVENTS)


def test_a_goal_raising_its_flag_is_an_event_with_what_it_took(tmp_path):
    """Spec 50 §2.2: `idea_flagged` — the goal, its party, who raised it, its tally (usd null when unpriced, never 0)."""
    assert event_log.IDEA_FLAGGED == "idea_flagged" and event_log.IDEA_FLAGGED in event_log.EVENTS
    assert event_log.record(tmp_path, event_log.IDEA_FLAGGED, idea="dark-mode", goal="ux", by="gate", tasks=4, first_time=3, usd=None, days=2)
    [row] = event_log.read(tmp_path)
    assert (row["event"], row["idea"], row["goal"], row["by"], row["tasks"], row["first_time"], row["usd"], row["days"]) == (
        "idea_flagged", "dark-mode", "ux", "gate", 4, 3, None, 2)
    assert event_log.counts(tmp_path)["idea_flagged"] == 1


def test_a_pick_asked_and_answered_are_events_with_what_the_measure_needs(tmp_path):
    """Spec 51 §2.4, §4: `pick_asked` and `pick_answered` — how many, of which kind, which round; which key (null: none), a note's length, where, how long."""
    assert event_log.record(tmp_path, event_log.PICK_ASKED, idea="dark-mode", task="k2", n=4, media="image", round=1)
    assert event_log.record(tmp_path, event_log.PICK_ANSWERED, idea="dark-mode", task="k2", key="B", note_chars=0, via="hand", seconds=12.5, device="phone")
    asked, answered = event_log.read(tmp_path)
    assert (asked["event"], asked["n"], asked["media"], asked["round"]) == ("pick_asked", 4, "image", 1)
    assert (answered["key"], answered["note_chars"], answered["via"], answered["seconds"], answered["device"]) == ("B", 0, "hand", 12.5, "phone")
    assert event_log.counts(tmp_path)["pick_asked"] == 1 and event_log.counts(tmp_path)["pick_answered"] == 1


def test_a_goal_of_a_type_who_joins_and_a_plans_missing_are_in_the_events_spec_52(tmp_path):
    """Spec 52 §2.7: `idea_added` with its type, asks answered, Refs' pictures, who joined and who left; `goal_saved` with
    joined, out and via; `plan_passed` with who joined and how many kinds the plan missed."""
    assert event_log.record(tmp_path, event_log.IDEA_ADDED, idea="logo", track="brand", type="product-designer/logo", asks=1,
                            refs=2, joined="artist", out="", device="desktop")
    assert event_log.record(tmp_path, event_log.GOAL_SAVED, goal="brand", new=False, joined="artist", out="ui-kit", via="type")
    assert event_log.record(tmp_path, event_log.PLAN_PASSED, idea="logo", tasks=3, by="person", joined="", missing=1)
    added, saved, passed = event_log.read(tmp_path)
    assert (added["type"], added["asks"], added["refs"], added["joined"], added["out"]) == ("product-designer/logo", 1, 2, "artist", "")
    assert (saved["joined"], saved["out"], saved["via"]) == ("artist", "ui-kit", "type")
    assert (passed["joined"], passed["missing"]) == ("", 1)
    from pathlib import Path
    source = Path(event_log.__file__).read_text(encoding="utf-8")
    assert "type (its goal type's key" in source and 'via ("type"' in source and "missing (how many kinds" in source     # the fields named where the events are
