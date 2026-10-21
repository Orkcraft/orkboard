"""Pick one (docs/specs/51-pick-one.md §2, §8 A): what a task leaves in its worktree is read and checked (a type sniffed from the
bytes, the limits, the plain-words reasons), moved to the goal's state folder with its `pick.json`, and put to the person;
`ideas.pick` writes the one picked at its target and commits it, or asks for new ones; the Needs you row, the Map's task, the
events, today's rows and the push."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from orkboard.realm import event_log, idea_pick, lexicon, media_sniff
from tests import pick_files as pf
from tests.pick_files import ask, leave, task  # noqa: F401


# -- sniffing: the type is the bytes' --------------------------------------------------------------------------------

@pytest.mark.parametrize("name, data, mime", [
    ("a.png", pf.png(), "image/png"), ("a.jpg", pf.jpeg(), "image/jpeg"), ("a.gif", pf.gif(), "image/gif"),
    ("a.webp", pf.webp(), "image/webp"), ("a.svg", pf.svg(), "image/svg+xml"), ("a.wav", pf.wav(), "audio/wav"),
    ("a.mp3", pf.mp3(), "audio/mpeg"), ("a.ogg", pf.ogg(), "audio/ogg"), ("a.webm", pf.webm(), "video/webm"),
    ("a.mp4", pf.mp4(b"vide"), "video/mp4"), ("a.m4a", pf.mp4(b"soun"), "audio/mp4"),
    ("a.mp4", pf.mp4(moov=False), "video/mp4"),                                     # an `ftyp` box alone: a clip
    ("a.m4a", pf.mp4(moov=False, brand=b"M4A "), "audio/mp4"),                      # … unless its brand is a sound's
    ("a.txt", pf.text(), "text/plain"), ("a.txt", "Ork — «zug»".encode(), "text/plain"),
])
def test_a_files_type_is_sniffed_from_its_bytes(tmp_path, name, data, mime):
    assert media_sniff.sniff(pf.write(tmp_path, name, data)) == mime


def test_a_name_never_decides_and_what_is_not_a_known_type_is_none(tmp_path):
    assert media_sniff.sniff(pf.write(tmp_path, "logo.png", pf.wav())) == "audio/wav"             # a sound called a picture
    assert media_sniff.sniff(pf.write(tmp_path, "song.mp3", pf.png())) == "image/png"
    assert media_sniff.sniff(pf.write(tmp_path, "logo.svg", pf.text("<b>not a mark</b>"))) == "text/plain"
    assert media_sniff.sniff(pf.write(tmp_path, "x.png", b"")) is None                                # nothing
    assert media_sniff.sniff(pf.write(tmp_path, "x.txt", bytes(range(256)))) is None                  # not text
    assert media_sniff.sniff(pf.write(tmp_path, "x.txt", b"ab\x00cd")) is None
    assert media_sniff.sniff(pf.write(tmp_path, "x.txt", b"\xff\xfe\xfa")) is None
    assert media_sniff.sniff(tmp_path / "missing.png") is None
    # an SVG is XML whose root is <svg: a declaration, a comment and a doctype may come first
    doc = b'<!DOCTYPE svg [<!ENTITY a "b">]>\n<svg viewBox="0 0 1 1"/>'
    assert media_sniff.sniff(pf.write(tmp_path, "d.svg", doc)) == "image/svg+xml"
    assert media_sniff.sniff(pf.write(tmp_path, "h.svg", b"<html><svg></svg></html>")) == "text/plain"   # not its root
    assert media_sniff.sniff(pf.write(tmp_path, "b.svg", b"\xef\xbb\xbf" + pf.svg())) == "image/svg+xml"


@pytest.mark.parametrize("name, data, mime, expect", [
    ("a.png", pf.png(3, 2), "image/png", (3, 2, None)), ("a.jpg", pf.jpeg(40, 30), "image/jpeg", (40, 30, None)),
    ("a.gif", pf.gif(7, 5), "image/gif", (7, 5, None)), ("a.webp", pf.webp(16, 12), "image/webp", (16, 12, None)),
    ("b.webp", pf.webp(20, 10, "VP8 "), "image/webp", (20, 10, None)), ("c.webp", pf.webp(33, 9, "VP8X"), "image/webp", (33, 9, None)),
    ("a.svg", pf.svg(24, 12), "image/svg+xml", (24, 12, None)), ("b.svg", pf.svg(None, None), "image/svg+xml", (48, 36, None)),
    ("a.wav", pf.wav(0.5), "audio/wav", (None, None, 0.5)), ("a.mp3", pf.mp3(1000), "audio/mpeg", (None, None, 26.1)),
    ("b.mp3", pf.mp3(xing=False), "audio/mpeg", (None, None, None)),                            # no Xing header: null, not a guess
    ("a.ogg", pf.ogg(), "audio/ogg", (None, None, None)), ("a.webm", pf.webm(), "video/webm", (None, None, None)),
    ("a.mp4", pf.mp4(b"vide", 5, 320, 240), "video/mp4", (320, 240, 5.0)), ("a.m4a", pf.mp4(b"soun", 7), "audio/mp4", (None, None, 7.0)),
    ("b.mp4", pf.mp4(moov=False), "video/mp4", (None, None, None)), ("a.txt", pf.text(), "text/plain", (None, None, None)),
])
def test_the_size_and_the_length_are_read_from_the_header_else_null(tmp_path, name, data, mime, expect):
    got = media_sniff.measure(pf.write(tmp_path, name, data), mime)
    assert (got["w"], got["h"], got["seconds"]) == expect


def test_a_cut_file_reads_as_null_never_as_an_error(tmp_path):
    for name, data, mime in (("a.png", pf.png()[:12], "image/png"), ("a.jpg", pf.jpeg()[:6], "image/jpeg"),
                             ("a.wav", pf.wav()[:30], "audio/wav"), ("a.mp4", pf.mp4()[:60], "video/mp4"),
                             ("a.mp3", pf.mp3()[:6], "audio/mpeg"), ("a.gif", pf.gif()[:8], "image/gif")):
        assert media_sniff.measure(pf.write(tmp_path, name, data), mime) == {"w": None, "h": None, "seconds": None}


# -- the plan's ask --------------------------------------------------------------------------------------------------

def test_the_kinds_have_their_words_types_and_limits():
    k = idea_pick.KINDS
    assert list(k) == ["image", "audio", "video", "text"]
    assert (k["image"].word, k["audio"].many, k["video"].word, k["text"].many) == ("picture", "sounds", "clip", "texts")
    assert k["image"].mimes == ("image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml")
    assert k["audio"].mimes == ("audio/mpeg", "audio/ogg", "audio/wav", "audio/mp4")
    assert k["video"].mimes == ("video/mp4", "video/webm") and k["text"].mimes == ("text/plain", "text/markdown")
    assert [k[x].limit for x in k] == [10 * 2**20, 10 * 2**20, 50 * 2**20, 4096] and idea_pick.PICK_MAX == 120 * 2**20
    assert lexicon.term("pick") == "pick" and lexicon.term("pick", many=True) == "picks"


def test_a_plans_pick_is_kept_clean_or_not_at_all():
    good = {"n": 3, "kind": "image", "ask": "  A logo\nfor the app ", "target": "assets/logo.png"}
    assert idea_pick.clean_ask(good) == {"n": 3, "kind": "image", "ask": "A logo for the app", "target": "assets/logo.png"}
    for bad in ({**good, "n": 1}, {**good, "n": 7}, {**good, "n": True}, {**good, "n": "3"}, {**good, "kind": "code"},
                {**good, "ask": " "}, {**good, "target": ""}, {**good, "target": "/etc/passwd"}, {**good, "target": "../x.png"},
                {**good, "target": "a/../../x.png"}, {**good, "target": ".git/config"}, {**good, "target": ".orkcraft/x"},
                {**good, "target": ".orkcraft-pick/a.png"}, {**good, "target": "a\\b.png"}, {**good, "target": "a//b.png"},
                {**good, "target": "dir/"}, {**good, "target": "llm-wiki/general/pages/ideas/x.md"}, {**good, "target": "x" * 300},
                {**good, "target": "C:/x.png"}, "image", None, 3):
        assert idea_pick.clean_ask(bad) is None, bad
    assert idea_pick.clean_ask({**good, "ask": "x" * 500})["ask"] == "x" * idea_pick.ASK_MAX
    assert idea_pick.ask_of({"pick": good})["n"] == 3 and idea_pick.ask_of({}) is None


def test_the_map_says_a_task_waits_for_a_pick_only_while_it_does():
    assert idea_pick.map_of(task(3, "audio", state="picking", round=2)) == {"n": 3, "media": "audio", "round": 2}
    assert idea_pick.map_of(task(state="review")) is None and idea_pick.map_of({"state": "picking"}) is None


# -- reading what the task left ----------------------------------------------------------------------------------------

def test_a_valid_pick_is_read_with_its_keys_names_types_sizes_and_what_the_headers_say(tmp_path):
    leave(tmp_path, {"anchor.png": pf.png(3, 2), "wolf.svg": pf.svg(24, 12), "mark.jpg": pf.jpeg(40, 30)},
          names={"anchor.png": "anchor", "wolf.svg": "  wolf\n head  ", "mark.jpg": "x" * 40})
    got, why = idea_pick.read(tmp_path, task(3))
    assert why == "" and [v["key"] for v in got] == ["A", "B", "C"]
    assert [v["file"] for v in got] == ["a.png", "b.svg", "c.jpg"]                              # stored under the key, never the task's name
    assert [v["mime"] for v in got] == ["image/png", "image/svg+xml", "image/jpeg"]
    assert [(v["w"], v["h"]) for v in got] == [(3, 2), (24, 12), (40, 30)] and all(v["seconds"] is None for v in got)
    assert [v["name"] for v in got] == ["anchor", "wolf head", "x" * idea_pick.NAME_MAX]         # a name is one line, 24 characters
    assert got[0]["bytes"] == len(pf.png(3, 2)) and got[1]["why"] == "why wolf.svg"
    assert got[0]["src"] == tmp_path / ".orkcraft-pick" / "anchor.png"


def test_each_kind_is_read_as_its_own(tmp_path):
    leave(tmp_path / "s", {"a.wav": pf.wav(0.5), "b.mp3": pf.mp3(), "c.m4a": pf.mp4(b"soun", 9)})
    got, why = idea_pick.read(tmp_path / "s", task(3, "audio"))
    assert why == "" and [(v["mime"], v["seconds"]) for v in got] == [("audio/wav", 0.5), ("audio/mpeg", 26.1), ("audio/mp4", 9.0)]
    leave(tmp_path / "c", {"a.mp4": pf.mp4(b"vide", 5, 320, 240), "b.webm": pf.webm()})
    got, why = idea_pick.read(tmp_path / "c", task(2, "video"))
    assert why == "" and [(v["mime"], v["w"], v["h"], v["seconds"]) for v in got] == [("video/mp4", 320, 240, 5.0), ("video/webm", None, None, None)]
    leave(tmp_path / "t", {"a.txt": pf.text("Take it easy."), "b.md": pf.text("# Take it\n\nslow"), "c.markdown": pf.text("*now*")})
    got, why = idea_pick.read(tmp_path / "t", task(3, "text"))
    assert why == "" and [v["mime"] for v in got] == ["text/plain", "text/markdown", "text/markdown"]   # the name says only this
    assert [v["file"] for v in got] == ["a.txt", "b.md", "c.md"]


@pytest.mark.parametrize("what, expect", [
    ("no manifest", "The task left no variants: its list (.orkcraft-pick.json) is missing"),
    ("not json", "The task's list of variants is not valid JSON"),
    ("no list", "The task's list of variants is not as asked"),
    ("rows are not objects", "The task's list of variants is not as asked"),
    ("too many bytes", "The task's list of variants is too long"),
])
def test_a_manifest_missing_broken_or_odd_fails_in_plain_words(tmp_path, what, expect):
    pf.write(tmp_path / ".orkcraft-pick", "a.png", pf.png())
    manifest = tmp_path / ".orkcraft-pick.json"
    body = {"not json": "{no", "no list": '{"variants": 3}', "rows are not objects": '{"variants": [1, 2, 3]}',
            "too many bytes": json.dumps({"variants": [], "x": "y" * 70000})}
    if what != "no manifest":
        manifest.write_text(body[what], encoding="utf-8")
    got, why = idea_pick.read(tmp_path, task(3))
    assert got == [] and why.startswith(expect), why


def test_a_task_without_a_pick_has_nothing_to_read(tmp_path):
    assert idea_pick.read(tmp_path, {"id": "k1"}) == ([], "The task has no pick to make")


def test_a_wrong_count_names_what_was_left_and_what_the_plan_asked(tmp_path):
    leave(tmp_path, {"a.wav": pf.wav(), "b.wav": pf.wav(), "c.wav": pf.wav()})
    assert idea_pick.read(tmp_path, task(4, "audio")) == ([], "The task left 3 sounds; its plan asked for 4")
    leave(tmp_path / "one", {"a.png": pf.png()})
    assert idea_pick.read(tmp_path / "one", task(2)) == ([], "The task left 1 picture; its plan asked for 2")


def test_a_file_outside_the_folder_a_missing_one_or_a_link_is_refused(tmp_path):
    secret = pf.write(tmp_path, "secret.png", pf.png())
    tree = tmp_path / "tree"
    leave(tree, {"a.png": pf.png()}, rows=[{"name": "a", "file": "a.png"}, {"name": "b", "file": "../../secret.png"}])
    got, why = idea_pick.read(tree, task(2))
    assert got == [] and why.startswith("B is not a file in the variants' folder")
    for bad in ("/etc/passwd", str(secret), "sub/a.png", ".", "", None, 3, "missing.png"):
        leave(tree, {"a.png": pf.png()}, rows=[{"name": "a", "file": "a.png"}, {"name": "b", "file": bad}])
        got, why = idea_pick.read(tree, task(2))
        assert got == [] and why.startswith("B is not a file in the variants' folder"), bad
    (tree / ".orkcraft-pick" / "link.png").symlink_to(secret)                                      # a link out of the folder
    leave(tree, {"a.png": pf.png()}, rows=[{"name": "a", "file": "a.png"}, {"name": "b", "file": "link.png"}])
    assert idea_pick.read(tree, task(2))[1].startswith("B is not a file in the variants' folder")
    (tree / ".orkcraft-pick" / "b.png").write_bytes(pf.png())
    leave(tree, {"a.png": pf.png()}, rows=[{"name": "a", "file": "a.png"}, {"name": "b", "file": "a.png"}])
    assert idea_pick.read(tree, task(2)) == ([], "B is the same file as an earlier variant")
    (tree / ".orkcraft-pick").rename(tmp_path / "moved")                                          # no folder at all
    assert idea_pick.read(tree, task(2))[1].startswith("A is not a file in the variants' folder")


def test_a_kind_sniffed_from_the_bytes_that_its_name_lies_about_is_refused_in_plain_words(tmp_path):
    leave(tmp_path, {"a.wav": pf.wav(), "b.wav": pf.png(), "c.wav": pf.wav()})                    # B is called a sound; it is a picture
    assert idea_pick.read(tmp_path, task(3, "audio")) == ([], "B is a picture, not a sound")
    leave(tmp_path / "v", {"a.mp4": pf.mp4(b"vide"), "b.mp4": pf.mp4(b"soun")})
    assert idea_pick.read(tmp_path / "v", task(2, "video")) == ([], "B is a sound, not a clip")
    leave(tmp_path / "x", {"a.png": pf.png(), "b.png": pf.text("a text")})
    assert idea_pick.read(tmp_path / "x", task(2)) == ([], "B is a text, not a picture")
    leave(tmp_path / "u", {"a.png": pf.png(), "b.png": bytes(range(256))})
    assert idea_pick.read(tmp_path / "u", task(2)) == ([], "B is not a picture of a kind the Board takes (PNG, JPEG, GIF, WEBP or SVG)")


def test_each_limit_is_told_with_the_file_its_size_and_the_most(tmp_path):
    big = lambda n: pf.png() + bytes(n)                                                            # noqa: E731  (a PNG with a long tail)
    leave(tmp_path / "i", {"a.png": pf.png(), "b.png": big(11 * 2**20)})
    assert idea_pick.read(tmp_path / "i", task(2)) == ([], "B is 11 MB: a picture is at most 10 MB")
    leave(tmp_path / "j", {"a.png": pf.png(), "b.png": big(10 * 2**20 + 300_000)})                  # a little over: not "10 MB: at most 10 MB"
    assert idea_pick.read(tmp_path / "j", task(2)) == ([], "B is 10.3 MB: a picture is at most 10 MB")
    leave(tmp_path / "a", {"a.wav": pf.wav(), "b.wav": pf.wav(1) + bytes(11 * 2**20)})
    assert idea_pick.read(tmp_path / "a", task(2, "audio"))[1] == "B is 11 MB: a sound is at most 10 MB"
    leave(tmp_path / "c", {"a.mp4": pf.mp4(), "b.mp4": pf.mp4() + bytes(72 * 2**20)})
    assert idea_pick.read(tmp_path / "c", task(2, "video"))[1] == "B is 72 MB: a clip is at most 50 MB"
    leave(tmp_path / "t", {"a.txt": pf.text("ok"), "b.txt": pf.text("w" * 6000)})
    assert idea_pick.read(tmp_path / "t", task(2, "text")) == ([], "B is 6 KB: a text is at most 4 KB")
    leave(tmp_path / "t2", {"a.txt": pf.text("ok"), "b.txt": pf.text("w" * 4100)})
    assert idea_pick.read(tmp_path / "t2", task(2, "text")) == ([], "B is 4.1 KB: a text is at most 4 KB")
    leave(tmp_path / "ok", {"a.txt": pf.text("w" * 4096), "b.txt": pf.text("fine")})                # exactly the limit is within it
    assert idea_pick.read(tmp_path / "ok", task(2, "text"))[1] == ""


def test_a_pick_is_at_most_120_mb_in_all(tmp_path, monkeypatch):
    monkeypatch.setattr(idea_pick, "PICK_MAX", 12_000)
    leave(tmp_path, {"a.txt": pf.text("a" * 3000), "b.txt": pf.text("b" * 3000), "c.txt": pf.text("c" * 3000), "d.txt": pf.text("d" * 3000),
                     "e.txt": pf.text("e" * 3000)})
    assert idea_pick.read(tmp_path, task(5, "text")) == ([], "The variants are 15 KB in all: a pick is at most 12 KB")


# -- the move to the state folder ----------------------------------------------------------------------------------------

def test_the_files_move_to_the_goals_state_folder_with_their_pick_json_and_the_worktree_is_left_clean(tmp_path):
    tree, state = tmp_path / "tree", tmp_path / "state"
    leave(tree, {"anchor.png": pf.png(3, 2), "wolf.svg": pf.svg()}, names={"anchor.png": "anchor", "wolf.svg": "wolf"})
    t = task(2)
    variants, why = idea_pick.read(tree, t)
    got = idea_pick.store(state, "dark-mode", t, 1, variants, by="grunt", now="2026-10-21T10:00:00")
    folder = state / "ideas" / "dark-mode" / "picks" / "k1-r1"
    assert sorted(p.name for p in folder.iterdir()) == ["a.png", "b.svg", "pick.json"]
    assert (folder / "a.png").read_bytes() == pf.png(3, 2) and (folder / "b.svg").read_bytes() == pf.svg()
    kept = json.loads((folder / "pick.json").read_text())
    assert kept == got == {"id": "k1-r1", "task": "k1", "round": 1, "by": "grunt", "kind": "image", "ask": "A logo for the app",
                           "target": "assets/logo.png", "at": "2026-10-21T10:00:00", "variants": [
                               {"key": "A", "name": "anchor", "file": "a.png", "mime": "image/png", "bytes": len(pf.png(3, 2)), "w": 3, "h": 2,
                                "seconds": None, "why": "why anchor.png"},
                               {"key": "B", "name": "wolf", "file": "b.svg", "mime": "image/svg+xml", "bytes": len(pf.svg()), "w": 24, "h": 12,
                                "seconds": None, "why": "why wolf.svg"}]}
    assert not (tree / ".orkcraft-pick").exists() or not any((tree / ".orkcraft-pick").iterdir())      # moved, not copied
    idea_pick.discard(tree)
    assert not (tree / ".orkcraft-pick").exists() and not (tree / ".orkcraft-pick.json").exists()      # … and the folder and the manifest go
    assert idea_pick.load(state, "dark-mode", "k1-r1") == kept and idea_pick.current(state, "dark-mode", t) == kept
    assert idea_pick.load(state, "dark-mode", "k1-r2") is None and idea_pick.current(state, "dark-mode", {**t, "round": 2}) is None


def test_an_answer_is_kept_in_the_pick_and_the_old_round_stays_as_history(tmp_path):
    tree, state = tmp_path / "tree", tmp_path / "state"
    t = task(2)
    for rnd in (1, 2):
        leave(tree, {"a.png": pf.png(rnd, 1), "b.png": pf.png(rnd, 2)})
        variants, _ = idea_pick.read(tree, t)
        pick = idea_pick.store(state, "g", t, rnd, variants, now=f"2026-10-21T1{rnd}:00:00")
        idea_pick.discard(tree)
        if rnd == 1:
            assert not idea_pick.answered(pick)
            done = idea_pick.answer(state, "g", pick, None, "make them rounder", now="2026-10-21T11:30:00")
            assert done["picked"] is None and done["note"] == "make them rounder" and done["at"] == "2026-10-21T11:30:00"
            assert done["asked_at"] == "2026-10-21T11:00:00" and idea_pick.answered(idea_pick.load(state, "g", "k1-r1"))
    assert [p["round"] for p in idea_pick.history(state, "g", "k1")] == [1, 2]
    assert idea_pick.answered(idea_pick.history(state, "g", "k1")[0]) and not idea_pick.answered(idea_pick.history(state, "g", "k1")[1])
    assert (state / "ideas" / "g" / "picks" / "k1-r1" / "a.png").is_file()                              # the first round's files stay
    assert idea_pick.history(state, "g", "k9") == []


def test_a_round_stored_again_replaces_its_folder(tmp_path):
    tree, state = tmp_path / "tree", tmp_path / "state"
    for names in (("a.png", "b.png", "c.png"), ("a.png", "b.png")):
        leave(tree, {n: pf.png() for n in names})
        variants, _ = idea_pick.read(tree, task(len(names)))
        idea_pick.store(state, "g", task(len(names)), 1, variants)
    assert sorted(p.name for p in (state / "ideas" / "g" / "picks" / "k1-r1").iterdir()) == ["a.png", "b.png", "pick.json"]


def test_a_goal_slug_that_is_a_path_is_refused(tmp_path):
    with pytest.raises(ValueError):
        idea_pick.folder_of(tmp_path, "../x", "k1-r1")


def test_the_events_are_logged_by_name(tmp_path):
    assert event_log.PICK_ASKED == "pick_asked" and event_log.PICK_ASKED in event_log.EVENTS
    assert event_log.PICK_ANSWERED == "pick_answered" and event_log.PICK_ANSWERED in event_log.EVENTS
    assert event_log.record(tmp_path, event_log.PICK_ASKED, idea="g", task="k1", n=3, media="image", round=1)
    assert event_log.record(tmp_path, event_log.PICK_ANSWERED, idea="g", task="k1", key=None, note_chars=12, via="drawer", seconds=41.5, device="desktop")
    rows = event_log.read(tmp_path)
    assert [r["event"] for r in rows] == ["pick_asked", "pick_answered"] and rows[1]["key"] is None and rows[1]["via"] == "drawer"


# -- the runner: a task that makes variants ----------------------------------------------------------------------------------

import os  # noqa: E402
import stat  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from orkboard.core.idea_review import RunnerError  # noqa: E402
from orkboard.core.idea_runner import IdeaRunner  # noqa: E402

PICK_STUB = r'''#!{python}
import json, os, subprocess, sys
sys.path.insert(0, os.environ["STUB_TESTS"])
from tests import pick_files as pf
argv = sys.argv[1:]
resume = "--resume" in argv
branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
tid = branch.rsplit("/", 1)[-1]
modes = dict(p.split("=", 1) for p in os.environ.get("STUB_MODE", "").split(",") if "=" in p)
mode = modes.get(tid, modes.get("*", "edit")).split(":")

def git(*a):
    subprocess.run(["git", *a], check=True, capture_output=True)

def commit(path, text, msg):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w").write(text)
    git("add", "-A")
    git("-c", "user.name=Stub", "-c", "user.email=stub@x", "commit", "-m", msg)

def leave(files, rows=None):
    os.makedirs(".orkcraft-pick", exist_ok=True)
    for name, data in files.items():
        open(os.path.join(".orkcraft-pick", name), "wb").write(data)
    rows = rows if rows is not None else [{"name": n.split(".")[0], "file": n, "why": "because " + n} for n in files]
    open(".orkcraft-pick.json", "w").write(json.dumps({"variants": rows}))

round_ = 2 if resume else 1
if mode[0] == "pick":
    n = int(mode[1])
    leave({f"v{i}.png": pf.png(round_ * 10 + i, 2) for i in range(1, n + 1)})
    open("stray.txt", "w").write("not wanted\n")                        # "change nothing else": this is not kept
elif mode[0] == "pickcommit":                                          # it commits its own file besides
    leave({f"v{i}.png": pf.png(i, 2) for i in (1, 2)})
    commit("tool.py", "print(1)\n", "a script that made them")
elif mode[0] == "picknothing":
    pass
elif mode[0] == "pickwav":
    leave({"v1.png": pf.png(), "v2.png": pf.wav()})
elif mode[0] == "pickonly":
    leave({"v1.png": pf.png()})
elif mode[0] == "edit":
    commit(f"{tid}.txt", f"done by {tid}\n", f"{tid}: add {tid}.txt")
with open(os.environ["STUB_LOG"], "a") as f:
    f.write(json.dumps({"tid": tid, "resume": resume, "argv": argv}) + "\n")
print(json.dumps({"result": "done", "session_id": f"s-{tid}", "total_cost_usd": 0.01, "usage": {"input_tokens": 10, "output_tokens": 5}}))
'''


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "t@x")
    git(repo, "config", "user.name", "T")
    (repo / ".gitignore").write_text(".orkcraft/\n__pycache__/\n.pytest_cache/\nignored/\n")
    (repo / "tests").mkdir()
    for name in ("test_architecture.py", "test_cli.py", "test_updates.py"):
        (repo / "tests" / name).write_text("def test_ok():\n    assert True\n")
    (repo / "conftest.py").write_text("")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "start")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    stub = bindir / "claude"
    stub.write_text(PICK_STUB.replace("{python}", sys.executable))
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("STUB_LOG", str(tmp_path / "stub.jsonl"))
    monkeypatch.setenv("STUB_TESTS", str(Path(__file__).resolve().parents[1]))
    page = repo / "llm-wiki" / "general" / "pages" / "ideas" / "demo.md"
    page.parent.mkdir(parents=True)
    page.write_text("---\nowner: board\n---\n# Demo\n\n## Gist\nA demo goal.\n")
    made = SimpleNamespace(repo=repo, state=repo / ".orkcraft", log=tmp_path / "stub.jsonl", runners=[])
    yield made
    for runner in made.runners:                 # a task still running when the test ends must not write into the next test's log
        runner.stop_all()
        end = time.time() + 30
        while runner.busy() and time.time() < end:
            time.sleep(0.05)


def plan_of(rig, tasks: list[dict], slug: str = "demo") -> None:
    folder = rig.state / "ideas" / slug
    folder.mkdir(parents=True, exist_ok=True)
    full = [{"id": t["id"], "title": t.get("title", t["id"]), "brief": t.get("brief", "do " + t["id"]), "tier": "laborer",
             "kind": t.get("kind", "art"), "after": t.get("after", []), "state": "waiting", "branch": "", "commit": "", "session": "",
             "cost": None, "tokens": None, "started": "", "finished": "", "error": "", "note": "",
             **({"pick": t["pick"]} if "pick" in t else {})} for t in tasks]
    (folder / "plan.json").write_text(json.dumps({"idea": slug, "made_at": "x", "passed_at": "y", "todos": [], "tasks": full}))
    (folder / "state.json").write_text(json.dumps({"state": "plan"}))


def runner_of(rig, **ideas) -> IdeaRunner:
    bus = SimpleNamespace(publish=lambda topic, **data: None)
    settings = SimpleNamespace(ideas={"max_parallel": 1, "merge_into": "main", "push": False, "review": False, **ideas})
    runner = IdeaRunner(rig.repo, rig.state, settings, bus, limits=lambda: [])
    rig.runners.append(runner)
    return runner


def tasks_of(rig, slug: str = "demo") -> dict:
    return {t["id"]: t for t in json.loads((rig.state / "ideas" / slug / "plan.json").read_text())["tasks"]}


def wait_for(runner: IdeaRunner, rig, tid: str, states: tuple[str, ...], timeout: float = 90) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        runner.tick()
        task = tasks_of(rig)[tid]
        if task["state"] in states and not runner.busy():
            return task
        time.sleep(0.1)
    raise AssertionError(f"{tid} did not reach {states}: {tasks_of(rig)[tid]}")


def events_of(rig, name: str) -> list[dict]:
    return [r for r in event_log.read(rig.repo) if r["event"] == name]


def calls(rig) -> list[dict]:
    return [json.loads(ln) for ln in rig.log.read_text().splitlines()] if rig.log.exists() else []


PICK = {"n": 3, "kind": "image", "ask": "A logo for the app", "target": "assets/logo.png"}


def start_pick(rig, monkeypatch, mode: str = "pick:3", **ideas) -> IdeaRunner:
    monkeypatch.setenv("STUB_MODE", f"k1={mode}")
    plan_of(rig, [{"id": "k1", "title": "Draw the logo", "pick": PICK}, {"id": "k2", "title": "Use the logo", "after": ["k1"], "kind": "code"}])
    runner = runner_of(rig, **ideas)
    runner.start("demo")
    return runner


def test_a_task_that_makes_variants_waits_picking_with_its_files_in_the_state_folder_and_nothing_committed(rig, monkeypatch):
    runner = start_pick(rig, monkeypatch)
    task = wait_for(runner, rig, "k1", ("picking",))
    assert task["commit"] == "" and task["error"] == "" and task["finished"] and task["round"] == 1
    folder = rig.state / "ideas" / "demo" / "picks" / "k1-r1"
    pick = json.loads((folder / "pick.json").read_text())
    assert (pick["id"], pick["task"], pick["round"], pick["kind"], pick["ask"], pick["target"]) == (
        "k1-r1", "k1", 1, "image", "A logo for the app", "assets/logo.png")
    assert [(v["key"], v["name"], v["file"], v["mime"], v["w"], v["h"]) for v in pick["variants"]] == [
        ("A", "v1", "a.png", "image/png", 11, 2), ("B", "v2", "b.png", "image/png", 12, 2), ("C", "v3", "c.png", "image/png", 13, 2)]
    assert sorted(p.name for p in folder.iterdir()) == ["a.png", "b.png", "c.png", "pick.json"]
    assert pick["by"] == "grunt"
    # the worktree is as it was cut: no variants, no manifest, nothing the session did besides, and the branch has no commit
    path = rig.state / "worktrees"
    tree = next(path.iterdir())
    assert sorted(p.name for p in tree.iterdir() if not p.name.startswith(".git")) == ["conftest.py", "tests"]
    assert not (tree / "stray.txt").exists() and not (tree / ".orkcraft-pick").exists() and not (tree / ".orkcraft-pick.json").exists()
    assert git(tree, "rev-parse", "HEAD") == git(rig.repo, "rev-parse", "main") and git(rig.repo, "rev-parse", "main") == task["base"]
    assert tasks_of(rig)["k2"]["state"] == "waiting"                       # what waits for it waits
    state = json.loads((rig.state / "ideas" / "demo" / "state.json").read_text())
    assert state["state"] == "working"
    assert [(e["task"], e["n"], e["media"], e["round"]) for e in events_of(rig, "pick_asked")] == [("k1", 3, "image", 1)]
    assert [(e["task"], e["state"], e["was"]) for e in events_of(rig, "task_state") if e["state"] == "picking"] == [("k1", "picking", "running")]
    assert len(calls(rig)) == 1 and "pick_answered" not in {r["event"] for r in event_log.read(rig.repo)}
    assert (tasks_of(rig)["k1"]["pick"]) == PICK                            # the plan's ask stays on the task


def test_the_tasks_prompt_asks_for_the_variants_the_manifest_and_nothing_else(rig, monkeypatch):
    runner = runner_of(rig)
    plan_of(rig, [{"id": "k1", "title": "Draw the logo", "pick": PICK}, {"id": "k2", "kind": "code"}])
    plan = runner.plan("demo")
    asked = runner._prompt("demo", plan, plan["tasks"][0])
    assert "3 variants for the person to pick from" in asked and "Make 3 pictures (PNG, JPEG, GIF, WEBP or SVG; at most 10 MB each)" in asked
    assert "for this: A logo for the app" in asked and "`.orkcraft-pick/`" in asked and "`.orkcraft-pick.json`" in asked
    assert '"variants": [{"name": "24 characters at most", "file": "its file name in the folder", "why": "one line"}]' in asked
    assert "Change nothing else and commit nothing" in asked and "written to `assets/logo.png`" in asked
    assert ".orkcraft-pick" not in runner._prompt("demo", plan, plan["tasks"][1])             # an ordinary task is told nothing of it
    plan["tasks"][0].update(state="merged", picked={"key": "B", "name": "anchor", "note": "bluer"})
    assert 'The person picked B · anchor: "bluer"' in runner._prompt("demo", plan, {**plan["tasks"][1], "after": ["k1"]})
    plan["tasks"][0]["picked"] = {"key": "A", "name": "wolf", "note": ""}
    assert "The person picked A · wolf\n" in runner._prompt("demo", plan, {**plan["tasks"][1], "after": ["k1"]}) + "\n"


@pytest.mark.parametrize("mode, reason", [
    ("pick:2", "The task left 2 pictures; its plan asked for 3"),
    ("picknothing", "The task left no variants: its list (.orkcraft-pick.json) is missing"),
    ("pickwav", "The task left 2 pictures; its plan asked for 3"),
    ("edit", "The task left no variants"),
])
def test_a_manifest_missing_or_a_wrong_count_fails_the_task_in_plain_words_and_the_files_go(rig, monkeypatch, mode, reason):
    runner = start_pick(rig, monkeypatch, mode)
    task = wait_for(runner, rig, "k1", ("failed",))
    assert task["error"].startswith(reason) and task["commit"] == ""
    assert not (rig.state / "ideas" / "demo" / "picks").exists()
    tree = next((rig.state / "worktrees").iterdir())
    assert not (tree / ".orkcraft-pick").exists() and not (tree / ".orkcraft-pick.json").exists()
    state = json.loads((rig.state / "ideas" / "demo" / "state.json").read_text())
    assert state["state"] == "failed" and "The task left" in state["error"]


def test_a_kind_that_is_not_the_asked_one_fails_it(rig, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=pickwav")
    plan_of(rig, [{"id": "k1", "title": "Draw the logo", "pick": {**PICK, "n": 2}}])
    runner = runner_of(rig)
    runner.start("demo")
    assert wait_for(runner, rig, "k1", ("failed",))["error"] == "B is a sound, not a picture"


def test_what_the_task_committed_besides_its_variants_is_not_kept(rig, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=pickcommit")
    plan_of(rig, [{"id": "k1", "title": "Draw the logo", "pick": {**PICK, "n": 2}}])
    runner = runner_of(rig)
    runner.start("demo")
    task = wait_for(runner, rig, "k1", ("picking",))
    tree = next((rig.state / "worktrees").iterdir())
    assert not (tree / "tool.py").exists() and git(tree, "rev-parse", "HEAD") == task["base"]


def test_a_key_commits_the_picked_file_at_its_target_with_its_message_and_the_task_lands(rig, monkeypatch):
    runner = start_pick(rig, monkeypatch)
    wait_for(runner, rig, "k1", ("picking",))
    runner.pick("demo", "k1", "b", "  a bit bluer\n", device="phone", via="drawer")
    task = wait_for(runner, rig, "k1", ("merged",))
    assert git(rig.repo, "log", "-1", "--format=%s", task["commit"]) == "Draw the logo: B · v2"
    assert git(rig.repo, "show", "--stat", "--format=", task["commit"]).split()[0] == "assets/logo.png"      # that file alone
    assert (rig.repo / "assets" / "logo.png").read_bytes() == pf.png(12, 2)                   # B's file, nowhere else
    assert not (rig.repo / "stray.txt").exists() and task["picked"] == {"key": "B", "name": "v2", "note": "a bit bluer"}
    pick = json.loads((rig.state / "ideas" / "demo" / "picks" / "k1-r1" / "pick.json").read_text())
    assert (pick["picked"], pick["note"]) == ("B", "a bit bluer") and pick["asked_at"] and pick["at"] >= pick["asked_at"]
    [answer] = events_of(rig, "pick_answered")
    assert (answer["task"], answer["key"], answer["note_chars"], answer["via"], answer["device"]) == ("k1", "B", len("a bit bluer"), "drawer", "phone")
    assert isinstance(answer["seconds"], float)
    wait_for(runner, rig, "k2", ("merged",))
    assert [c["tid"] for c in calls(rig)] == ["k1", "k2"]                                      # no new turn for k1: the gate went on from the commit
    assert 'The person picked B · v2: "a bit bluer"' in calls(rig)[1]["argv"][1]               # the note, told to the task that waits for it
    assert json.loads((rig.state / "ideas" / "demo" / "state.json").read_text())["state"] == "done"


def test_with_review_on_the_picked_file_waits_at_review_as_any_change_does(rig, monkeypatch):
    runner = start_pick(rig, monkeypatch, review=True)
    wait_for(runner, rig, "k1", ("picking",))
    runner.pick("demo", "k1", "A", "", via="hand")
    task = wait_for(runner, rig, "k1", ("review",))
    assert task["tests"]["green"] and task["diff"]["files"] == 1 and "assets/logo.png" not in git(rig.repo, "ls-tree", "-r", "--name-only", "main")
    assert git(rig.repo, "log", "-1", "--format=%s", task["branch"]) == "Draw the logo: A · v1"
    assert runner.merge("demo", "k1") == git(rig.repo, "rev-parse", "main")
    assert (rig.repo / "assets" / "logo.png").read_bytes() == pf.png(11, 2)


def test_none_of_them_needs_a_note_then_runs_the_task_again_as_its_next_round_and_the_old_variants_stay(rig, monkeypatch):
    runner = start_pick(rig, monkeypatch)
    wait_for(runner, rig, "k1", ("picking",))
    for note in ("", "   \n"):
        with pytest.raises(RunnerError, match="A note says what to change: write one first"):
            runner.pick("demo", "k1", None, note)
    assert tasks_of(rig)["k1"]["state"] == "picking"                                            # a refusal leaves it asked
    runner.pick("demo", "k1", None, "rounder, and no anchor", via="screen")
    task = wait_for(runner, rig, "k1", ("picking",))
    assert task["round"] == 2 and len(calls(rig)) == 2 and calls(rig)[1]["resume"] is True
    first, second = (json.loads((rig.state / "ideas" / "demo" / "picks" / f"k1-r{n}" / "pick.json").read_text()) for n in (1, 2))
    assert first["picked"] is None and first["note"] == "rounder, and no anchor"                # the history keeps the answer
    assert "picked" not in second and [v["w"] for v in second["variants"]] == [21, 22, 23]
    assert (rig.state / "ideas" / "demo" / "picks" / "k1-r1" / "a.png").is_file()
    log = runner.log("demo", "k1")
    assert 'None of the last variants: "rounder, and no anchor"' in log and "Make 3 new ones" in log and "`.orkcraft-pick/`" in log
    [answer] = events_of(rig, "pick_answered")
    assert (answer["key"], answer["note_chars"], answer["via"]) == (None, len("rounder, and no anchor"), "screen")
    assert [(e["round"]) for e in events_of(rig, "pick_asked")] == [1, 2]
    runner.pick("demo", "k1", "C", "")                                                         # the second round's, then
    wait_for(runner, rig, "k1", ("merged",))
    assert (rig.repo / "assets" / "logo.png").read_bytes() == pf.png(23, 2)


def test_a_pick_answered_twice_a_task_not_picking_or_a_key_that_is_not_one_is_refused(rig, monkeypatch):
    runner = start_pick(rig, monkeypatch)
    with pytest.raises(RunnerError, match="That pick is answered already"):
        runner.pick("demo", "k1", "A", "")                                                      # not picking yet
    wait_for(runner, rig, "k1", ("picking",))
    for key in ("D", "", "Z", 1):
        with pytest.raises(RunnerError, match="Pick one of A, B, C"):
            runner.pick("demo", "k1", key, "")
    with pytest.raises(RunnerError, match="That task is gone"):
        runner.pick("demo", "k9", "A", "")
    runner.pick("demo", "k1", "A", "")
    with pytest.raises(RunnerError, match="That pick is answered already"):
        runner.pick("demo", "k1", "B", "")                                                      # twice
    wait_for(runner, rig, "k1", ("merged",))
    with pytest.raises(RunnerError, match="That pick is answered already"):
        runner.pick("demo", "k1", "B", "")
    assert (rig.repo / "assets" / "logo.png").read_bytes() == pf.png(11, 2)


def test_a_place_git_ignores_is_said_and_the_pick_stays_asked(rig, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=pick:2")
    plan_of(rig, [{"id": "k1", "title": "Draw the logo", "pick": {**PICK, "n": 2, "target": "ignored/logo.png"}}])
    runner = runner_of(rig)
    runner.start("demo")
    wait_for(runner, rig, "k1", ("picking",))
    with pytest.raises(RunnerError, match="ignored/logo.png is ignored by git"):
        runner.pick("demo", "k1", "A", "")
    assert tasks_of(rig)["k1"]["state"] == "picking" and "picked" not in json.loads(
        (rig.state / "ideas" / "demo" / "picks" / "k1-r1" / "pick.json").read_text())


def test_picking_waits_for_stop_all_start_again_and_goes_with_drop(rig, monkeypatch):
    runner = start_pick(rig, monkeypatch)
    wait_for(runner, rig, "k1", ("picking",))
    runner.stop_all()
    assert tasks_of(rig)["k1"]["state"] == "picking"                                            # it waits, spending nothing
    runner.start("demo")                                                                       # Start again keeps what waits for the person
    assert tasks_of(rig)["k1"]["state"] == "picking"
    runner.pick("demo", "k1", "B", "")                                                         # … and a stopped goal goes on with the answer
    wait_for(runner, rig, "k1", ("merged",))
    assert json.loads((rig.state / "ideas" / "demo" / "state.json").read_text())["state"] in ("working", "done")


def test_a_picking_task_can_be_dropped(rig, monkeypatch):
    runner = start_pick(rig, monkeypatch)
    wait_for(runner, rig, "k1", ("picking",))
    runner.drop_task("demo", "k1")
    assert tasks_of(rig)["k1"]["state"] == "failed" and tasks_of(rig)["k1"]["error"] == "dropped by you"
    with pytest.raises(RunnerError, match="That pick is answered already"):
        runner.pick("demo", "k1", "A", "")


def test_a_plan_task_without_a_valid_pick_is_an_ordinary_task(rig, monkeypatch):
    monkeypatch.setenv("STUB_MODE", "k1=edit")
    plan_of(rig, [{"id": "k1", "title": "Plain", "pick": {**PICK, "n": 1}}])
    runner = runner_of(rig)
    runner.start("demo")
    assert wait_for(runner, rig, "k1", ("merged",))["state"] == "merged"


# -- the host: ideas.pick, the Needs you row, the Map's task, today's rows and the push ------------------------------------------

import sys  # noqa: E402
import types  # noqa: E402

from orkboard.gui import media, phone_push  # noqa: E402
from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard  # noqa: E402
from orkboard.realm import board_today, ideas  # noqa: E402


@pytest.fixture
def host(fake_repo):
    h = Orkboard(fake_repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


def waiting_pick(host, scratch: Path, files: dict[str, bytes] | None = None, kind: str = "image", extra_task: bool = True) -> str:
    """A goal whose task k1 made variants and waits for the pick (and k2 after it), as the runner leaves it; the goal's slug."""
    root, state = host.ideas.root(), host.ideas.state_dir
    party = ideas.save_goal(root, None, "Brand", "About the brand", None, "normal")[0]
    slug = ideas.add_idea(root, "A logo for the app", party, state)
    ideas.save_state(state, slug, state="working")
    files = files or {"a.png": pf.png(3, 2), "b.svg": pf.svg(24, 12), "c.jpg": pf.jpeg(40, 30)}
    base = {"brief": "b", "tier": "warrior", "branch": "", "commit": "", "session": "", "cost": None, "tokens": None, "started": "", "error": "", "note": ""}
    tasks = [{**base, "id": "k1", "title": "Draw the logo", "short": "Logo", "kind": "art", "after": [], "state": "picking", "round": 1,
              "finished": "2026-10-21T10:00:00", "role": "grunt", "pick": ask(len(files), kind)},
             *([{**base, "id": "k2", "title": "Use the logo", "short": "Use it", "kind": "code", "after": ["k1"], "state": "waiting"}] if extra_task else [])]
    ideas.save_plan(state, slug, {"idea": slug, "made_at": "2026-10-21T09:00:00", "passed_at": None, "todos": [], "tasks": tasks})
    ideas.edit_plan(state, slug, lambda p: p.update(passed_at="2026-10-21T09:30:00"))
    pf.make_pick(state, scratch, files, slug=slug, kind=kind)
    host.ideas.rev += 1
    return slug


def pick_rows(host) -> list[dict]:
    return [n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "pick"]


def test_a_task_that_waits_for_a_pick_is_a_needs_you_row_with_its_variants_and_their_signed_addresses(host, tmp_path):
    slug = waiting_pick(host, tmp_path / "s")
    [row] = pick_rows(host)
    assert set(row) == {"kind", "slug", "idea", "goal", "task", "title", "short", "idea_title", "priority", "blocks", "by", "ask", "n", "media",
                        "variants", "round", "at"}
    assert (row["kind"], row["slug"], row["idea"], row["task"], row["title"], row["short"]) == ("pick", slug, slug, "k1", "Draw the logo", "Logo")
    assert (row["ask"], row["n"], row["media"], row["round"], row["at"], row["blocks"]) == ("A logo for the app", 3, "image", 1, row["at"], True)
    assert row["goal"] == ideas.tracks(host.ideas.root(), make=False)[-1]["slug"] and row["idea_title"] and row["priority"] == "normal"
    assert row["by"]["slug"] == "grunt" and row["by"]["name"] == "Grunt" and set(row["by"]["head"]) == {"craft", "race", "tier"}
    assert [(v["key"], v["name"], v["mime"], v["w"], v["h"], v["seconds"]) for v in row["variants"]] == [
        ("A", "a", "image/png", 3, 2, None), ("B", "b", "image/svg+xml", 24, 12, None), ("C", "c", "image/jpeg", 40, 30, None)]
    assert all(set(v) == {"key", "name", "why", "url", "mime", "w", "h", "seconds"} for v in row["variants"]) and row["variants"][0]["why"] == "why a.png"
    for v, data in zip(row["variants"], (pf.png(3, 2), pf.svg(24, 12), pf.jpeg(40, 30))):
        path, sig = v["url"].split("?s=")
        assert path == f"/media/{slug}/k1-r1/{v['key'].lower()}.{ {'image/png': 'png', 'image/svg+xml': 'svg', 'image/jpeg': 'jpg'}[v['mime']] }"
        assert media.check(path, sig) and media.serve("GET", v["url"], "", media.state_dirs(host)).read() == data       # the address opens the file
    assert host.ideas.snapshot()["needs_you"] == 1                                                    # it is an answer that waits


def test_the_row_of_a_text_pick_carries_its_words_inline_and_the_row_goes_when_it_is_answered(host, tmp_path):
    slug = waiting_pick(host, tmp_path / "s", {"a.txt": pf.text("Take it easy."), "b.md": pf.text("# Slow\n\ndown")}, kind="text")
    [row] = pick_rows(host)
    assert row["media"] == "text" and [(v["mime"], v["text"]) for v in row["variants"]] == [("text/plain", "Take it easy."), ("text/markdown", "# Slow\n\ndown")]
    assert all("url" in v for v in row["variants"])
    state = host.ideas.state_dir
    ideas.edit_plan(state, slug, lambda p: p["tasks"][0].update(state="running"))                         # not picking any more: no row
    assert pick_rows(host) == []
    ideas.edit_plan(state, slug, lambda p: p["tasks"][0].update(state="picking"))
    from orkboard.realm import idea_pick as ip
    ip.answer(state, slug, ip.current(state, slug, ideas.plan(state, slug)["tasks"][0]), "A", "")        # answered already: none either
    assert pick_rows(host) == []
    ideas.edit_plan(state, slug, lambda p: p["tasks"][0].update(state="picking", round=3))               # a round with no pick folder: none
    assert pick_rows(host) == []


def test_the_map_says_picking_with_its_pick_and_the_goal_waits_for_you(host, tmp_path):
    slug = waiting_pick(host, tmp_path / "s")
    got = host.command("ideas.map", {})
    node = next(n for n in got["nodes"] if n["slug"] == slug)
    assert [(t["id"], t["state"], t["pick"]) for t in node["tasks"]] == [("k1", "picking", {"n": 3, "media": "image", "round": 1}), ("k2", "waiting", None)]
    assert node["waits"] == {"kind": "you", "ref": "", "title": "", "until": ""}
    assert [r["task"] for r in pick_rows(host)] == ["k1"]
    ideas.edit_plan(host.ideas.state_dir, slug, lambda p: p["tasks"][0].update(state="review"))
    node = next(n for n in host.command("ideas.map", {})["nodes"] if n["slug"] == slug)
    assert node["tasks"][0]["pick"] is None


def test_ideas_pick_reaches_the_runner_with_its_key_note_and_where_and_its_refusals_are_plain_words(host, tmp_path, monkeypatch):
    seen = []

    class FakeRunner:
        def __init__(self, *a, **k):
            pass

        def pick(self, slug, tid, key, note, device="", via=""):
            seen.append((slug, tid, key, note, device, via))
            if note == "refuse":
                raise type("RunnerError", (Exception,), {})("That pick is answered already")

    monkeypatch.setitem(sys.modules, "orkboard.core.idea_runner", types.SimpleNamespace(IdeaRunner=FakeRunner))
    slug = waiting_pick(host, tmp_path / "s")
    a = {"slug": slug, "task": "k1"}
    assert host.command("ideas.pick", {**a, "key": "B", "note": "bluer", "via": "drawer"}) == {"ok": True}
    assert host.command("ideas.pick", {**a, "key": None, "note": "rounder", "via": "hand"}) == {"ok": True}
    assert host.command("ideas.pick", {**a, "key": "A"}) == {"ok": True}
    assert host.command("ideas.pick", {**a, "key": "C", "via": "screen", "device": "phone"}) == {"ok": True}
    assert host.command("ideas.pick", {**a, "key": "C", "via": "nowhere"}) == {"ok": True}
    assert host.command("ideas.pick", {**a, "key": "C", "via": "map"}) == {"ok": True}
    assert host.command("ideas.pick", {**a, "key": "C", "note": "x" * 3000}) == {"ok": True}
    assert seen[:3] == [(slug, "k1", "B", "bluer", "desktop", "drawer"), (slug, "k1", None, "rounder", "desktop", "hand"), (slug, "k1", "A", "", "desktop", "idea")]
    assert seen[3][4:] == ("phone", "screen") and seen[4][5] == "idea" and seen[5][5] == "map" and len(seen[6][3]) == 2000
    for bad, why in (({"key": 3}, "key is a variant's letter"), ({"key": "A", "note": 4}, "note is not text"), ({"key": "A", "task": ""}, "task is missing"),
                     ({"key": "A", "slug": ""}, "slug is missing")):
        with pytest.raises(CommandError, match=why):
            host.command("ideas.pick", {**a, **bad})
    with pytest.raises(CommandError, match="That pick is answered already"):
        host.command("ideas.pick", {**a, "key": "A", "note": "refuse"})


def test_the_phone_may_call_it_and_the_opened_stop_may_say_pick(host):
    assert "ideas.pick" in host.commands and BoardPhone.allowed(host, "ideas.pick", {}) and "ideas.pick" in host.command("mobile.hello")["commands"]
    assert host.command("ideas.log", {"event": "opened", "what": "pick", "ref": "k1", "via": "hand"}) == {"ok": True}
    [row] = [r for r in event_log.read(host.repo_root) if r["event"] == "opened"]
    assert (row["what"], row["ref"], row["via"]) == ("pick", "k1", "hand")


def test_today_says_pick_one_in_the_alert_tone_then_what_was_picked_or_that_new_ones_were_asked():
    lines = [{"at": "2026-10-21T10:00:00+00:00", "event": "pick_asked", "idea": "logo", "task": "k1", "n": 3, "media": "image", "round": 1},
             {"at": "2026-10-21T10:05:00+00:00", "event": "pick_answered", "idea": "logo", "task": "k1", "key": None, "note_chars": 9, "via": "hand", "seconds": 300.0},
             {"at": "2026-10-21T10:10:00+00:00", "event": "pick_asked", "idea": "logo", "task": "k1", "n": 3, "media": "image", "round": 2},
             {"at": "2026-10-21T10:15:00+00:00", "event": "pick_answered", "idea": "logo", "task": "k1", "key": "B", "note_chars": 0, "via": "drawer", "seconds": 300.0},
             {"at": "2026-10-21T10:16:00+00:00", "event": "pick_asked", "idea": "gone", "task": "k9", "n": 2, "media": "text", "round": 1},
             {"at": "2026-10-21T10:17:00+00:00", "event": "pick_asked", "idea": "logo", "n": 2, "media": "text", "round": 1}]       # no task: no row
    titles = {"ideas": {"logo": {"title": "A logo", "short": "Logo", "goal": "brand"}}, "goals": {}, "tasks": {"logo": {"k1": "Draw the logo"}}}
    rows = board_today.rows(lines, titles, since=None)
    assert [(r["mark"], r["tone"], r["words"], r["title"], r["goal"], r["idea"], r["task"], r["open"]) for r in rows] == [
        ("!", "alert", "Pick one", "gone", "", "gone", "k9", {"kind": "pick", "slug": "gone", "task": "k9"}),            # a task the Board lost reads as its goal's slug
        ("✓", "ok", "Picked B", "Draw the logo", "brand", "logo", "k1", {"kind": "pick", "slug": "logo", "task": "k1"}),
        ("!", "alert", "Pick one", "Draw the logo", "brand", "logo", "k1", {"kind": "pick", "slug": "logo", "task": "k1"}),
        ("↺", "muted", "New ones asked", "Draw the logo", "brand", "logo", "k1", {"kind": "pick", "slug": "logo", "task": "k1"}),
        ("!", "alert", "Pick one", "Draw the logo", "brand", "logo", "k1", {"kind": "pick", "slug": "logo", "task": "k1"})]


def test_ideas_today_joins_the_task_titles_of_the_pick_events(host, tmp_path):
    slug = waiting_pick(host, tmp_path / "s")
    event_log.record(host.repo_root, event_log.PICK_ASKED, idea=slug, task="k1", n=3, media="image", round=1)
    [row] = [r for r in host.command("ideas.today", {})["events"] if r["open"]["kind"] == "pick"]
    assert (row["mark"], row["tone"], row["words"], row["title"], row["task"]) == ("!", "alert", "Pick one", "Draw the logo", "k1")


def test_the_push_says_who_asks_to_pick_one_and_a_pick_that_waits_is_an_answer_that_waits(host, tmp_path):
    slug = waiting_pick(host, tmp_path / "s")
    pusher = host.pusher
    assert phone_push.PICK_WORDS == "{member} asks you to pick one" and "pick" not in phone_push.KIND_WORDS
    assert pusher._first() == ("Grunt asks you to pick one", "")
    assert pusher.words_needs(1) == "Grunt asks you to pick one"
    assert pusher.words_needs(3) == "3 wait for your answer · Grunt asks you to pick one"
    assert host.ideas.snapshot()["needs_you"] == 1 and pusher._waiting() == 1
    ideas.edit_plan(host.ideas.state_dir, slug, lambda p: p["tasks"][0].update(state="review"))
    host.ideas.rev += 1
    assert pusher._first() is None and pusher.words_needs(1) == "1 waits for your answer"
