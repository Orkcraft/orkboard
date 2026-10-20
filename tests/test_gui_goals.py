"""Spec 34 on the host: a goal by dialog and read at once, an idea read now or later, the keeper's priority and place,
the agents' roles and the task types, each with its event. The model call is stubbed (`jobs.run_read`)."""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, idea_photos, ideas, jobs, roles

NEW_COMMANDS = {"ideas.goal_save", "ideas.goal", "ideas.read_now", "ideas.roles", "ideas.role_save", "ideas.role_drop",
                "ideas.kind_set", "ideas.doc"}
GOAL = {"title": "Grow installs", "about": "More people try Orkline.", "priority": "high", "deadline": "2026-12-01",
        "metrics": [{"name": "weekly installs", "target": "50"}, {"name": "", "target": "x"}],
        "links": ["docs/specs/34-v1-round-2.md", "https://example.com/post", "docs/specs/34-v1-round-2.md"]}


@pytest.fixture
def host(fake_repo) -> Orkboard:
    h = Orkboard(fake_repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


@pytest.fixture
def model(monkeypatch):
    """A stubbed keeper: answers by what it is asked; `seen` holds every call."""
    seen = []
    answers = {"goal": {"summary": "Installs are the first step.\nCount them weekly.", "questions": ["Which channel first?"],
                        "metrics": [{"name": "weekly installs", "how": "npm downloads, per week"}], "reply": "Noted."},
               "idea": {"gist": "Dark mode.\nIt glares at night.", "why": "Moves weekly installs.", "size": "S",
                        "priority": "high", "priority_why": "Helps night users stay.", "before": "", "questions": []}}

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        kind = "goal" if "saved a goal" in prompt else "idea"
        if "lay out its ideas" in prompt:                      # a read that ends `ready` lays out its trail (spec 46 §3)
            return json.dumps({"ideas": []}), 0.01, 10, "s-1"
        seen.append({"kind": kind, "model": model, "prompt": prompt, "env": env})
        return json.dumps(answers[kind]), 0.01, 10, "s-1"

    monkeypatch.setattr(jobs, "run_read", run_read)
    run_read.seen, run_read.answers = seen, answers
    return run_read


def _add(host, text, **more):
    """An idea under a goal (spec 35 §3: no idea without one), waiting for the night unless asked."""
    root = host.ideas.root()
    goal = next((t["slug"] for t in ideas.tracks(root, make=False) if t["slug"] != "general"), None) or ideas.add_track(root, "First goal")
    return host.command("ideas.add", {"text": text, "track": goal, "night": True, **more})


def _wait(host, slug="", goal=False):
    k = host.ideas.keeper
    for _ in range(400):
        if not (k.busy_goal(slug) if goal else k.busy(slug)):
            return
        time.sleep(0.01)
    raise AssertionError("the keeper never finished")


def _events(host, name):
    return [r for r in event_log.read(Path(host.town.repo_root)) if r["event"] == name]


def test_the_new_commands_are_the_hosts_and_a_phones(host):
    assert NEW_COMMANDS <= set(host.commands)
    assert all(BoardPhone.allowed(host, c, {}) for c in NEW_COMMANDS)


def test_a_goal_saved_is_read_by_the_keeper_at_once_and_written(host, model):
    slug = host.command("ideas.goal_save", GOAL)["slug"]
    assert slug == "grow-installs"
    _wait(host, slug, goal=True)
    (call,) = model.seen
    assert call["model"] == "opus" or "opus" in call["model"]                     # spec 35 §1: the goal step is elder
    assert "More people try Orkline." in call["prompt"] and "weekly installs" in call["prompt"]
    assert "Write the specs" in call["prompt"] or "34-v1-round-2" in call["prompt"]            # a linked file is read …
    assert "https://example.com/post (a web link: not fetched)" in call["prompt"]            # … a URL only named
    g = host.command("ideas.goal", {"slug": slug})
    assert g["state"] == "asks" and g["priority"] == "high" and g["deadline"] == "2026-12-01"
    assert g["summary"].startswith("Installs are the first step.") and g["questions"] == ["Which channel first?"]
    assert g["metrics"] == [{"name": "weekly installs", "target": "50", "how": "npm downloads, per week"}]
    assert g["links"] == ["docs/specs/34-v1-round-2.md", "https://example.com/post"] and g["description"] == "More people try Orkline."
    text = (host.ideas.root() / "pages/tracks/grow-installs.md").read_text()      # spec 35 §13: the Board's tree
    assert "priority: high" in text and "## Summary" in text and "## Metrics" in text and "## Open questions" in text
    board = host.command("ideas.board")
    row = next(t for t in board["tracks"] if t["slug"] == slug)
    assert row["state"] == "asks" and row["priority"] == "high" and row["metrics"] and row["links"]
    assert {"idea": "", "goal": slug, "kind": "goal", "title": "Grow installs", "text": "Which channel first?"} in [
        {k: n[k] for k in ("idea", "goal", "kind", "title", "text")} for n in board["needs_you"]]     # spec 35 §10
    saved = _events(host, "goal_saved")[0]
    assert saved["goal"] == slug and saved["new"] is True and saved["priority"] == "high" and saved["device"] == "desktop"
    assert saved["metrics"] == ["weekly installs"] and len(saved["links"]) == 2
    read = _events(host, "goal_read")[0]
    assert read["goal"] == slug and read["state"] == "asks" and read["seconds"] is not None


def test_editing_a_goal_sends_it_again_and_keeps_what_the_keeper_wrote(host, model):
    slug = host.command("ideas.goal_save", GOAL)["slug"]
    _wait(host, slug, goal=True)
    model.answers["goal"] = {"summary": "Second reading.", "questions": [], "metrics": []}
    host.command("ideas.goal_save", {**GOAL, "slug": slug, "title": "Grow installs fast", "priority": "low"})
    _wait(host, slug, goal=True)
    assert len(model.seen) == 2
    g = host.command("ideas.goal", {"slug": slug})
    assert g["state"] == "ready" and g["summary"] == "Second reading." and g["title"] == "Grow installs fast"
    assert g["metrics"][0]["how"] == "npm downloads, per week"           # how it is counted stays until the keeper says otherwise
    assert [e["new"] for e in _events(host, "goal_saved")] == [True, False]


def test_a_goal_is_checked_and_listed_by_priority(host, model):
    with pytest.raises(CommandError, match="title"):
        host.command("ideas.goal_save", {"title": " "})
    with pytest.raises(CommandError, match="Priority"):
        host.command("ideas.goal_save", {"title": "X", "priority": "urgent"})
    with pytest.raises(CommandError, match="deadline"):
        host.command("ideas.goal_save", {"title": "X", "deadline": "soon"})
    low = host.command("ideas.goal_save", {"title": "Later thing", "priority": "low"})["slug"]
    high = host.command("ideas.goal_save", {"title": "Urgent thing", "priority": "high"})["slug"]
    normal = host.command("ideas.goal_save", {"title": "Plain thing"})["slug"]
    for s in (low, high, normal):
        _wait(host, s, goal=True)
    assert [t["slug"] for t in host.command("ideas.board")["tracks"]] == [high, normal, low]


def test_the_answer_to_a_goals_question_is_the_same_talk_on_the_goal(host, model):
    slug = host.command("ideas.goal_save", GOAL)["slug"]
    _wait(host, slug, goal=True)
    model.answers["goal"] = {"summary": "Clear now.", "questions": [], "reply": "Thanks, npm first."}
    assert host.command("ideas.say", {"slug": slug, "text": "npm first"}) == {"ok": True}
    _wait(host, slug, goal=True)
    g = host.command("ideas.goal", {"slug": slug})
    assert g["state"] == "ready" and [(t["who"], t["text"]) for t in g["talk"]] == [("you", "npm first"), ("keeper", "Thanks, npm first.")]
    assert "npm first" in model.seen[-1]["prompt"]


def test_an_idea_added_now_is_read_at_once_later_waits_for_the_batch(host, model):
    # spec 35 §3: `now` became the queue (Normal → drafted at once; the closed dialog's `night` waits); with no
    # question the plan follows at once (this stub answers it with no plan, so the idea stays ready)
    later = _add(host, "wait for the batch")["slug"]
    now = _add(host, "dark mode please", night=False)["slug"]
    _wait(host, now)
    assert [c["kind"] for c in model.seen][:1] == ["idea"] and "dark mode please" in model.seen[0]["prompt"]
    assert ideas.state(host.ideas.state_dir, later)["state"] == "raw"
    assert ideas.state(host.ideas.state_dir, now)["state"] == "ready"
    assert [e["now"] for e in _events(host, "idea_added")] == [False, True]
    seen = len(model.seen)
    host.command("ideas.read_now", {"slug": later})                      # the card's Process now
    _wait(host, later)
    assert len(model.seen) > seen and ideas.state(host.ideas.state_dir, later)["state"] == "ready"
    with pytest.raises(CommandError, match="read this idea already"):
        host.command("ideas.read_now", {"slug": later})


def test_the_keeper_fills_an_ideas_priority_with_one_line_why_and_proposes_its_place(host, model):
    # spec 35 §3: the priority is the person's; the keeper no longer proposes one, and still proposes the place
    first = _add(host, "first idea")["slug"]
    second = _add(host, "second idea")["slug"]
    model.answers["idea"]["before"] = first
    host.command("ideas.read_now", {"slug": second})
    _wait(host, second)
    page = host.command("ideas.page", {"slug": second})
    why = next(s["text"] for s in page["sections"] if s["name"] == "Why")
    assert why == "Moves weekly installs." and "Priority:" not in why
    board = host.command("ideas.board")
    assert [(i["slug"], i["priority"]) for i in board["ideas"]] == [(second, "normal"), (first, "normal")]


def test_the_persons_drag_wins_over_the_keepers_place(host, model):
    a = _add(host, "alpha idea")["slug"]
    b = _add(host, "beta idea")["slug"]
    host.command("ideas.move", {"slug": b})                              # the person drags b to the end: theirs now
    model.answers["idea"]["before"] = a
    host.command("ideas.read_now", {"slug": b})
    _wait(host, b)
    assert [i["slug"] for i in host.command("ideas.board")["ideas"]] == [a, b]


def test_roles_are_made_edited_dropped_and_the_built_ins_refused(host):
    got = host.command("ideas.roles")
    assert [r["slug"] for r in got["roles"]] == ["taskmaster", "grunt"] and all(r["spend_today"] == 0 for r in got["roles"])
    assert [(k["kind"], k["label"], k["role"]) for k in got["kinds"]][:5] == [
        ("code", "Code", "grunt"), ("tests", "Tests", "grunt"), ("docs", "Docs", "grunt"),
        ("text", "Text for people", "grunt"), ("research", "Research", "grunt")]
    assert [k["kind"] for k in got["kinds"]] == list(roles.TASK_KINDS) and all(k["role"] == "grunt" for k in got["kinds"])
    assert [m["id"] for m in got["models"]] == ["", "elder", "warrior", "laborer"]      # spec 36 §3: By Target, the tiers
    slug = host.command("ideas.role_save", {"name": "Docs scribe", "model": "laborer", "max_parallel": 2,
                                            "instruction": "Write plainly."})["slug"]
    assert host.command("ideas.kind_set", {"kind": "docs", "role": slug}) == {"ok": True}
    got = host.command("ideas.roles")
    assert next(r for r in got["roles"] if r["slug"] == slug)["instruction"] == "Write plainly."
    assert next(k for k in got["kinds"] if k["kind"] == "docs")["role"] == slug
    host.command("ideas.role_save", {"slug": slug, "name": "Scribe", "model": "warrior", "max_parallel": 3, "instruction": ""})
    assert next(r for r in host.command("ideas.roles")["roles"] if r["slug"] == slug)["name"] == "Scribe"
    for slug_ in ("taskmaster", "grunt"):
        with pytest.raises(CommandError, match="edited, not deleted"):
            host.command("ideas.role_drop", {"slug": slug_})
    with pytest.raises(CommandError, match="at once"):
        host.command("ideas.role_save", {"name": "Bad", "model": "warrior", "max_parallel": 99})
    assert host.command("ideas.role_drop", {"slug": slug}) == {"ok": True}
    assert next(k for k in host.command("ideas.roles")["kinds"] if k["kind"] == "docs")["role"] == "grunt"
    saved, dropped, kind = (_events(host, n) for n in ("role_saved", "role_dropped", "kind_set"))
    assert [(e["role"], e["model"], e["max_parallel"], e["new"]) for e in saved] == [
        (slug, "laborer", 2, True), (slug, "warrior", 3, False)]
    assert dropped[0]["role"] == slug and dropped[0]["kinds"] == ["docs"] and kind[0]["kind"] == "docs"


def test_agents_is_a_block_per_role_and_spend_is_summed_by_role(host):
    slug = host.command("ideas.role_save", {"name": "Scribe", "model": "laborer", "max_parallel": 1})["slug"]
    idea = _add(host, "an idea with work")["slug"]
    state = host.ideas.state_dir
    task = lambda tid, role, cost: {"id": tid, "title": tid, "brief": "b", "tier": "laborer", "kind": "docs", "role": role,  # noqa: E731
                                    "after": [], "state": "running", "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "cost": cost}
    ideas.save_plan(state, idea, {"idea": idea, "made_at": "x", "passed_at": None, "todos": [],
                                  "tasks": [task("k1", slug, 0.25), task("k2", slug, 0.5), task("k3", "grunt", 1.0)]})
    ideas.save_state(state, idea, state="working")
    blocks = {b["role"]: b for b in host.command("ideas.agents")["roles"]}
    assert list(blocks) == ["taskmaster", "grunt", slug]
    assert [c["task"] for c in blocks[slug]["chips"]] == ["k1", "k2"] and blocks[slug]["chips"][0]["role"] == slug
    assert [c["task"] for c in blocks["grunt"]["chips"]] == ["k3"]
    assert blocks[slug]["spend_today"] == 0.75 and blocks["grunt"]["spend_today"] == 1.0
    spent = {r["slug"]: r["spend_today"] for r in host.command("ideas.roles")["roles"]}
    assert spent[slug] == 0.75


def test_the_plan_marks_each_task_with_its_type():
    from orkboard.core import idea_keeper
    plan = idea_keeper.make_plan("x", {"tasks": [
        {"title": "a", "brief": "b", "kind": "docs"}, {"title": "c", "brief": "d"}, {"title": "e", "brief": "f", "kind": "poetry"}]})
    assert [t["kind"] for t in plan["tasks"]] == ["docs", "code", "code"]


def test_the_keepers_talk_and_plans_run_on_the_taskmasters_model(host, model):
    slug = _add(host, "talk to me")["slug"]
    model.answers["idea"] = {"reply": "ok", "sections": {}, "questions": []}
    host.command("ideas.say", {"slug": slug, "text": "hello"})
    _wait(host, slug)
    assert "opus" in model.seen[-1]["model"]                                         # the Taskmaster's default: the elder tier
    host.command("ideas.role_save", {"slug": "taskmaster", "name": "Taskmaster", "model": "laborer", "max_parallel": 1})   # a tier only (spec 36 §3)
    host.command("ideas.say", {"slug": slug, "text": "again"})
    _wait(host, slug)
    assert "haiku" in model.seen[-1]["model"]


def test_a_linked_document_is_read_from_the_repository_or_the_wiki_only(host):
    repo = Path(host.town.repo_root)
    (repo / "notes.md").write_text("# Notes\nhello\n")
    assert host.command("ideas.doc", {"path": "notes.md"}) == {"path": "notes.md", "text": "# Notes\nhello\n", "truncated": False,
                                                              "html": "<h1>Notes</h1>\n<p>hello</p>\n"}   # spec 37 §8
    slug = _add(host, "an idea")["slug"]
    assert "an idea" in host.command("ideas.doc", {"path": f"pages/ideas/{slug}.md"})["text"]       # a Wiki page
    for bad in ("../outside.md", "/etc/passwd", "nope.md", "https://example.com/x"):
        with pytest.raises(CommandError):
            host.command("ideas.doc", {"path": bad})


def test_a_goal_has_a_craft_its_race_s_head_engineering_when_new_and_kept_when_left_out(host, model):
    """A goal's craft (decisions §53): the person's pick on the phone, its race beside it; engineering by default, an
    unknown one refused, and an edit that leaves it out keeps it (the desktop's dialog does not send it)."""
    slug = host.command("ideas.goal_save", {"about": "A landing page that sells.", "craft": "design"})["slug"]
    _wait(host, slug, goal=True)
    g = next(t for t in host.command("ideas.board", {})["tracks"] if t["slug"] == slug)
    assert (g["craft"], g["race"]) == ("design", "elf")
    host.command("ideas.goal_save", {"slug": slug, "about": "A landing page that sells well."})
    _wait(host, slug, goal=True)
    assert next(t for t in host.command("ideas.board", {})["tracks"] if t["slug"] == slug)["craft"] == "design"
    plain = host.command("ideas.goal_save", {"about": "Faster tests."})["slug"]
    _wait(host, plain, goal=True)
    g = next(t for t in host.command("ideas.board", {})["tracks"] if t["slug"] == plain)
    assert (g["craft"], g["race"]) == ("engineering", "peon")
    with pytest.raises(CommandError, match="Craft is"):
        host.command("ideas.goal_save", {"slug": plain, "about": "Faster tests.", "craft": "alchemy"})
    assert ideas.CRAFTS == roles.CRAFTS


PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32).decode()
JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 32).decode()


def test_photos_go_with_an_idea_beside_its_state_and_the_taskmaster_reads_them_first(host, model):
    """New idea's photos (realm/idea_photos.py): kept in the idea's state folder, named in the draft's and the plan's
    prompts as paths in the repository; a bad one refuses the idea whole, and deleting the idea deletes them."""
    root = host.ideas.root()
    goal = ideas.add_track(root, "Ship v1")
    for bad, why in (([{"data": base64.b64encode(b"not an image").decode()}], "JPEG, a PNG or a WebP"),
                     ([{"data": "@@@"}], "did not arrive whole"), ([{"data": JPEG}] * 5, "At most 4 photos")):
        with pytest.raises(CommandError, match=why):
            host.command("ideas.add", {"text": "Cut off", "track": goal, "night": True, "photos": bad})
    assert ideas.ideas(root, goal) == []                                                     # nothing half made
    slug = host.command("ideas.add", {"text": "The login screen is cut off", "track": goal, "night": True,
                                      "photos": [{"data": JPEG}, {"data": PNG}]})["slug"]
    assert idea_photos.listed(host.ideas.state_dir, slug) == [f".orkcraft/ideas/{slug}/photos/1.jpg", f".orkcraft/ideas/{slug}/photos/2.png"]
    assert (idea_photos.folder(host.ideas.state_dir, slug) / "1.jpg").read_bytes()[:3] == b"\xff\xd8\xff"
    prompt = host.ideas.keeper.draft_prompt(root, slug)
    assert "read each one first" in prompt and f"- .orkcraft/ideas/{slug}/photos/2.png" in prompt
    assert f".orkcraft/ideas/{slug}/photos/1.jpg" in host.ideas.keeper.plan_prompt(root, slug)
    assert _events(host, "idea_added")[-1]["photos"] == 2
    host.command("ideas.drop", {"slug": slug})
    assert idea_photos.listed(host.ideas.state_dir, slug) == []


def test_the_words_of_a_goal_complete_new_idea_titles_first_then_its_terms(host):
    root = host.ideas.root()
    slug = ideas.save_goal(root, None, "Offline first", "The phone keeps working offline: the SyncQueue in sync_queue.py holds edits.")[0]
    host.command("ideas.add", {"text": "Queue the edits while offline", "track": slug, "night": True})
    got = host.command("ideas.words", {"track": slug})
    assert got["track"] == slug and got["words"][0] == "Offline first"
    assert "offline" in got["words"] and "SyncQueue" in got["words"] and "sync_queue.py" in got["words"]
    assert "while" not in got["words"] and "the" not in got["words"]
    assert BoardPhone.allowed(host, "ideas.words", {"track": slug})                         # the phone asks for them
    with pytest.raises(CommandError, match="That goal is gone"):
        host.command("ideas.words", {"track": "nope"})


def test_needs_you_carries_every_question_with_its_likely_answers_and_one_answered_on_the_phone_leaves_the_rest_to_decide(host, model):
    """The phone answers a question in its card (shell-needs.js): the row carries the questions, the Taskmaster is asked to end
    each with its likely answers "(one / other)", and a goal's answers may be fewer than its questions."""
    model.answers["goal"] = {"summary": "Installs first.", "questions": ["Which channel first? (npm / brew)", "Which week?"], "metrics": []}
    slug = host.command("ideas.goal_save", GOAL)["slug"]
    _wait(host, slug, goal=True)
    assert '"choices": ["two to four likely answers, each at most 40 characters"]' in model.seen[0]["prompt"]
    row = next(n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "goal")
    assert row["questions"] == ["Which channel first? (npm / brew)", "Which week?"] and row["text"] == "Which channel first?"
    assert [{k: v for k, v in a.items() if k != "by"} for a in row["asked"]] == [
        {"ask": "Which channel first?", "choices": ["npm", "brew"], "pick": None, "why": ""},
        {"ask": "Which week?", "choices": [], "pick": None, "why": ""}]                           # a plain string of before
    assert [a["by"]["slug"] for a in row["asked"]] == ["taskmaster", "taskmaster"]               # the leader's own (spec 46 §1)
    host.command("ideas.answer", {"slug": slug, "answers": ["npm"], "goal": True})
    _wait(host, slug, goal=True)
    said = model.seen[-1]["prompt"]
    assert "Which channel first? (npm / brew) — npm" in said and "Which week? — (no answer: decide)" in said


def test_a_goals_question_comes_with_its_answer_picked_and_may_be_left_to_the_taskmaster(host, model):
    # spec 41 §9: the choices, the pick and why from the model's answer; the page's line says the pick in bold
    model.answers["goal"] = {"summary": "Installs first.", "metrics": [], "questions": [
        {"ask": "Which channel first?", "choices": ["npm", "brew"], "pick": 1, "why": "most testers are on a Mac"},
        {"ask": "Which week?", "choices": ["this", "next"], "pick": "next", "why": ""},
        {"ask": "Bad choices?", "choices": ["a/b", "c"], "pick": 0}]}
    slug = host.command("ideas.goal_save", GOAL)["slug"]
    _wait(host, slug, goal=True)
    row = next(n for n in host.command("ideas.board")["needs_you"] if n["kind"] == "goal")
    assert row["questions"][0] == "Which channel first? (npm / **brew**) — most testers are on a Mac"
    assert [q["pick"] for q in row["asked"]] == [1, 1, None] and {k: v for k, v in row["asked"][2].items() if k != "by"} == {"ask": "Bad choices?", "choices": [], "pick": None, "why": ""}
    host.command("ideas.answer", {"slug": slug, "decide": True, "goal": True})
    _wait(host, slug, goal=True)
    said = model.seen[-1]["prompt"]
    assert "— brew" in said and "Which week? (this / **next**) — next" in said and "Bad choices? — (no answer: decide)" in said
    got = _events(host, "goal_answered")[-1]
    assert got["decided"] is True and got["answers"] == 2 and got["recommended"] == 0


def test_a_goal_row_says_the_saved_party_it_was_picked_from_and_goal_saved_logs_it(host, model):
    from orkboard.realm import own_parties
    pid = own_parties.save("Lean web", "engineering", "taskmaster", ["reviewer"], [], [])
    slug = host.command("ideas.goal_save", {"about": "Ship it.", "team": ["reviewer"], "party": pid})["slug"]
    assert next(t for t in host.command("ideas.board")["tracks"] if t["slug"] == slug)["party"] == pid
    assert host.command("ideas.goal", {"slug": slug})["party"] == pid
    assert [e for e in event_log.read(Path(host.repo_root)) if e["event"] == "goal_saved"][-1]["party"] == pid
