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


def ask(n: int = 3, kind: str = "image", target: str = "assets/logo.png", text: str = "A logo for the app") -> dict:
    return {"n": n, "kind": kind, "ask": text, "target": target}


def task(n: int = 3, kind: str = "image", **more) -> dict:
    return {"id": "k1", "title": "Draw the logo", "short": "Logo", "state": "running", "round": 1, "pick": ask(n, kind), **more}


def leave(tree: Path, files: dict[str, bytes], names: dict[str, str] | None = None, rows: list | None = None) -> None:
    """What a task leaves: each file into `.orkcraft-pick/` and a manifest of them (`rows` instead when given)."""
    for name, data in files.items():
        pf.write(tree / idea_pick.PICK_DIR, name, data)
    tree.mkdir(parents=True, exist_ok=True)
    rows = rows if rows is not None else [{"name": (names or {}).get(f, f.split(".")[0]), "file": f, "why": f"why {f}"} for f in files]
    (tree / idea_pick.PICK_FILE).write_text(json.dumps({"variants": rows}), encoding="utf-8")


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
