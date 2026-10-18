"""The board's keeper (spec 29a §4, spec 35) with the model call stubbed: the draft, the talk and its compaction, the plan."""
from __future__ import annotations

import datetime as dt
import json
import time

import pytest

from orkcraft.core import idea_keeper
from orkcraft.core.idea_keeper import IdeaKeeper, KeeperError
from orkcraft.realm import ideas


class Model:
    """Answers in turn; remembers what it was asked."""

    def __init__(self, *answers) -> None:
        self.answers, self.asked = list(answers), []

    def __call__(self, tier, prompt, resume="", effort=""):
        self.asked.append({"tier": tier, "prompt": prompt, "resume": resume, "effort": effort})
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return (answer if isinstance(answer, str) else json.dumps(answer)), 0.01, 1000, "sess-1"


@pytest.fixture
def keeper(tmp_path):
    root, state = tmp_path / "wiki", tmp_path / ".orkcraft"
    settings = {"batch_minutes": 30, "idle_hours": 24}
    published = []
    k = IdeaKeeper(tmp_path, state, lambda: root, lambda: settings, published.append)
    k.root, k.state, k.published, k.settings_now = root, state, published, settings
    k._context = lambda session, tokens: int(tokens or 0)
    return k


def _wait(k, slug):
    for _ in range(200):
        if not k.busy(slug):
            return
        time.sleep(0.01)
    raise AssertionError("the keeper never finished")


def test_the_draft_reads_a_raw_idea_on_the_draft_step(keeper):
    # spec 35 §3: the batch on the laborer tier went; a raw idea is drafted (elder · medium on balance), its goal given
    ux = ideas.add_track(keeper.root, "UX")
    slug = ideas.add_idea(keeper.root, "dark mode pls", ux, state_dir=keeper.state)
    keeper.call = model = Model("Sure! ```json\n" + json.dumps(
        {"gist": "Dark mode for the board.\nAt night it glares.", "why": "Moves: calm at night", "size": "m",
         "questions": ["Every screen or the board only?", "Follow the OS?"], "evil": "x"}) + "\n```")
    keeper.draft_one(slug)
    assert model.asked[0]["tier"] == "elder" and "dark mode pls" in model.asked[0]["prompt"]
    assert "index.md" in model.asked[0]["prompt"] or "Index" in model.asked[0]["prompt"]
    page = ideas.idea_page(keeper.root, slug)
    assert page.section("Gist").startswith("Dark mode for the board.") and page.section("Why") == "Moves: calm at night"
    assert page.get("size") == "M" and page.get("track") == ux
    assert ideas.items(page.section("Open questions")) == ["Every screen or the board only?", "Follow the OS?"]
    st = ideas.state(keeper.state, slug)
    assert st["state"] == "asks" and st["batch_at"]


def test_a_broken_answer_leaves_the_idea_new(keeper):
    slug = ideas.add_idea(keeper.root, "x", state_dir=keeper.state)
    keeper.call = Model("no json here")
    keeper.draft_one(slug)
    st = ideas.state(keeper.state, slug)
    assert st["state"] == "raw" and "JSON" in st["error"]
    assert ideas.idea_page(keeper.root, slug).section("Gist") == "x"


def test_tick_drafts_no_raw_idea_by_day_and_never_in_the_demo(keeper):
    # spec 35 §3: no 30-minute batch; a raw idea waits for the night (or a draft at once)
    slug = ideas.add_idea(keeper.root, "y", state_dir=keeper.state)
    keeper.settings_now["night"] = "00:00-00:01"
    keeper.call = Model()
    noon = dt.datetime.now().replace(hour=12, minute=0).timestamp()
    assert not keeper.tick(noon) and not keeper.tick(noon + 31 * 60)
    assert ideas.state(keeper.state, slug)["state"] == "raw" and keeper.call.asked == []
    keeper.demo = True
    ideas.add_idea(keeper.root, "z", state_dir=keeper.state)
    assert not keeper.tick(noon + 120 * 60)
    with pytest.raises(KeeperError, match="demo"):
        keeper.say(slug, "hi")


def test_the_talk_keeps_one_session_and_writes_only_known_sections(keeper):
    slug = ideas.add_idea(keeper.root, "export csv", state_dir=keeper.state)
    keeper.call = model = Model(
        {"reply": "Big files stream.", "sections": {"Risks": "Big files.\n## not a heading", "Hacked": "no",
                                                   "Decisions": "no"},
         "decisions": ["Stream rows, never load the file"], "questions": ["Which delimiter?"]},
        {"reply": "Comma it is.", "sections": {}, "decisions": ["Comma"], "questions": []})
    keeper.say(slug, "What about big files?", "Risks")
    _wait(keeper, slug)
    first = model.asked[0]
    assert first["tier"] == "elder" and first["resume"] == "" and "The idea's page now" in first["prompt"]
    page = ideas.idea_page(keeper.root, slug)
    assert page.section("Risks") == "Big files.\n### not a heading" and page.section("Hacked") == ""
    assert "Stream rows" in page.section("Decisions")
    st = ideas.state(keeper.state, slug)
    assert st["session"] == "sess-1" and st["state"] == "asks"
    keeper.say(slug, "Comma.", "Open questions")
    _wait(keeper, slug)
    assert model.asked[1]["resume"] == "sess-1" and "The idea's page now" not in model.asked[1]["prompt"]
    assert ideas.state(keeper.state, slug)["state"] == "ready"
    talk = ideas.talk(keeper.state, slug)
    assert [(t["who"], t["text"]) for t in talk] == [("you", "What about big files?"), ("keeper", "Big files stream."),
                                                     ("you", "Comma."), ("keeper", "Comma it is.")]
    assert "talk.jsonl" not in "".join(a["prompt"] for a in model.asked)   # the archive is never read back


def test_compaction_after_a_day_or_past_60_percent(keeper):
    now = dt.datetime(2026, 10, 17, 12, 0)
    fresh_at = (now - dt.timedelta(hours=2)).isoformat()
    assert keeper.fresh({"session": ""}, now)
    assert not keeper.fresh({"session": "s", "session_at": fresh_at, "context": 1000}, now)
    assert keeper.fresh({"session": "s", "session_at": (now - dt.timedelta(hours=25)).isoformat(), "context": 0}, now)
    assert keeper.fresh({"session": "s", "session_at": fresh_at, "context": int(0.61 * idea_keeper.WINDOW)}, now)
    keeper.settings_now["idle_hours"] = 1
    assert keeper.fresh({"session": "s", "session_at": fresh_at, "context": 0}, now)


def test_a_failed_turn_is_said_in_the_talk(keeper):
    slug = ideas.add_idea(keeper.root, "x", state_dir=keeper.state)
    keeper.call = Model(RuntimeError("claude: not logged in"))
    keeper.say(slug, "hello")
    _wait(keeper, slug)
    assert "not logged in" in ideas.talk(keeper.state, slug)[-1]["text"]


def test_the_plan_is_strict_and_estimated(keeper):
    slug = ideas.add_idea(keeper.root, "export csv", state_dir=keeper.state)
    tasks = [{"id": "a", "title": "Writer", "brief": "Write rows", "tier": "warrior"},
             {"id": "b", "title": "Button", "brief": "Add a button", "tier": "laborer", "after": ["a", "zzz"]},
             {"id": "c", "title": "no brief"},
             {"id": "d", "title": "Hard", "brief": "Think", "tier": "god"}]
    tasks += [{"id": f"x{n}", "title": f"T{n}", "brief": "b", "tier": "elder"} for n in range(10)]
    keeper.call = Model({"tasks": tasks, "todos": [
        {"id": "s", "title": "api key", "kind": "secret", "why": "to call it", "for": ["b"]},
        {"id": "q", "title": "Delimiter", "kind": "choice", "choices": [",", ";"], "for": ["a"]},
        {"id": "z", "title": "bad", "kind": "magic"}]})
    keeper.plan(slug)
    _wait(keeper, slug)
    plan = ideas.plan(keeper.state, slug)
    assert ideas.state(keeper.state, slug)["state"] == "plan"
    ids = [t["id"] for t in plan["tasks"]]
    assert ids == [f"k{n}" for n in range(1, 9)]                       # at most 8, renamed
    assert plan["tasks"][1]["after"] == ["k1"] and plan["tasks"][2]["tier"] == "warrior"
    assert [t["title"] for t in plan["todos"]] == ["API_KEY", "Delimiter"]
    assert plan["todos"][0] == {"id": "t1", "title": "API_KEY", "kind": "secret", "why": "to call it", "choices": [],
                                "steps": [], "for": ["k2"], "done": False, "value": None}
    assert [t["state"] for t in plan["tasks"][:3]] == ["waiting", "waiting", "ready"]
    tiers = [t["tier"] for t in plan["tasks"]]
    base = sum({"elder": 1.0, "warrior": 0.3, "laborer": 0.05}[t] for t in tiers)
    assert plan["estimate"] == {"tasks": 8, "usd_low": round(base * 0.5, 2), "usd_high": round(base * 1.5, 2)}
    assert plan["passed_at"] is None and plan["idea"] == slug


def test_a_plan_with_no_task_goes_back_and_a_passed_plan_is_never_rewritten(keeper):
    slug = ideas.add_idea(keeper.root, "x", state_dir=keeper.state)
    ideas.save_state(keeper.state, slug, state="ready")
    keeper.call = Model({"tasks": []})
    keeper.plan(slug)
    _wait(keeper, slug)
    st = ideas.state(keeper.state, slug)
    assert st["state"] == "ready" and "No plan" in st["error"]
    ideas.save_plan(keeper.state, slug, {"idea": slug, "passed_at": "2026-10-17T10:00:00", "tasks": [], "todos": []})
    with pytest.raises(KeeperError, match="passed"):
        keeper.plan(slug)


def test_first_json_reads_through_prose():
    assert idea_keeper.first_json('x {bad} y {"a": 1} z') == {"a": 1}
    assert idea_keeper.first_json("[1, 2]") is None and idea_keeper.first_json("") is None
