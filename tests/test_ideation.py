"""Spec 65 A (docs/specs/65-ideation.md §1–§7, Tests → A): Ideation's agents, preset, stages and fixed seats; a pitch's own way; its three
read-only calls (the keeper's model call stubbed), each as its role; the answers cut and cleaned; Send, Change and judge again, Pass and
the 200 kept; the night; Stop all; the events; Needs you's row; what the faces read."""
from __future__ import annotations

import datetime as dt
import json
import sys
import threading
import time

import pytest

from orkboard.core.idea_keeper import IdeaKeeper
from orkboard.gui.board_host import CommandError, Orkboard
from orkboard.realm import event_log, goal_team, goal_types, idea_target, ideas, library, party_price, pitches, roles
from orkboard.sources.limits import Limit

STEPS = (("Read this pitch alone", "pitch_view"), ("Make the case against this pitch", "pitch_case"),
         ("Decide whether to invest", "pitch_decide"), ("write its spec straight away", "draft"), ("turn it into a plan", "plan"),
         ("saved a goal", "goal"))
TEAM = [*library.VIEWS, library.SKEPTIC]
WORDS = "a dark mode for the night shift, SECRET-WORDS"


def view_of(prompt: str) -> str:
    """Which view a pitch_view prompt is for (by its name: `as its Market view`)."""
    return next(v for v in library.VIEWS if f"as its {library.get(v).name}:" in prompt)


def VIEW(prompt: str) -> dict:
    v = view_of(prompt)
    return {"for": [f"TOKEN-{v} for", "x" * 500, "two", "three", "four"], "against": [f"TOKEN-{v} against"], "question": f"Who, {v}?",
            "size": "M"}


CASE = {"case": "It solves nothing anyone asked for.", "kills": ["costly", "nonsense"]}


def DECIDE(party="ship", type_="bug", answer="invest", kills=(), like=""):
    return {"answer": answer, "why": ["People on night shifts asked.", "Cheap."], "where": {"party": party, "type": type_},
            "first": "Add a dark theme toggle to the settings screen.", "test": "Ask five night-shift users.", "kills": list(kills),
            "like": like, "extra": "dropped"}


class Model:
    """Answers by the step its prompt says (a callable gets the prompt; a list is a sequence, its last repeats); remembers every call,
    with the tools its thread asked for and the role it spoke as; `gate` holds a step's calls."""

    def __init__(self, keeper=None, **answers) -> None:
        self.keeper, self.answers, self.asked, self.gate, self.lock = keeper, answers, [], {}, threading.Lock()

    def __call__(self, tier, prompt, effort="", budget=None):
        step = next((s for k, s in STEPS if k in prompt), "?")
        tls = getattr(self.keeper, "_tls", None)
        with self.lock:
            self.asked.append({"step": step, "tier": tier, "prompt": prompt, "effort": effort, "budget": budget,
                               "tools": getattr(tls, "tools", None), "as": getattr(tls, "as_role", ""),
                               "view": view_of(prompt) if step == "pitch_view" else ""})
            got = self.answers.get(step, {})
            if isinstance(got, list):
                got = got.pop(0) if len(got) > 1 else got[0]
        if step in self.gate:
            self.gate[step].wait(5)
        got = got(prompt) if callable(got) else got
        if isinstance(got, Exception):
            raise got
        return (got if isinstance(got, str) else json.dumps(got)), 0.01, 100, ""

    def of(self, step):
        return [a for a in self.asked if a["step"] == step]


def _wait(k, slug):
    for _ in range(500):
        if not k.busy(slug):
            return
        time.sleep(0.01)
    raise AssertionError("the keeper never finished")


@pytest.fixture
def keeper(fake_repo, tmp_path):
    """A keeper with a project: an Engineering party `ship` (with a metric) and an Ideation party `ideas`."""
    root, state = tmp_path / "wiki", fake_repo / ".orkcraft"
    settings = {"target": "balance", "autostart": True, "night": "01:00-07:00"}
    k = IdeaKeeper(fake_repo, state, lambda: root, lambda: settings)
    k.root, k.state, k.settings_now, k.limits_now = root, state, settings, []
    k.limits = lambda: k.limits_now
    k.ship = ideas.add_track(root, "Ship")
    ideas.write_goal_reading(root, k.ship, "", {}, [], metrics=[{"name": "night users", "target": "100", "how": ""}])
    library.install(state, ["architect", "grunt", "tester", "reviewer"])
    goal_team.set_team(root, k.ship, ["grunt", "tester", "reviewer"], leader="architect")
    k.ideas = ideas.add_track(root, "Ideas")
    library.install(state, [library.INVESTOR, *TEAM])
    goal_team.set_team(root, k.ideas, TEAM, leader=library.INVESTOR)
    return k


def _pitch(k, text=WORDS, **kw):
    return ideas.add_idea(k.root, text, k.ideas, k.state, **kw)


def _judged(k, slug, model=None):
    k.call = model or Model(k, pitch_view=VIEW, pitch_case=CASE, pitch_decide=DECIDE())
    k.judge(slug)
    _wait(k, slug)
    return k.call


# -- §1: the agents, the preset, the stages, the seats ------------------------------------------------------------------

def test_the_six_agents_of_ideation_follow_the_marketing_ones_with_their_craft_tier_band_and_a_pitch_kind_only():
    ids = [a.id for a in library.LIBRARY]
    assert ids[ids.index("community") + 1:] == ["investor", "product-view", "market-view", "tech-view", "design-view", "skeptic"]
    rows = {a.id: (a.name, a.craft, a.tier, a.band, a.takes, a.line) for a in library.LIBRARY if a.pitch}
    assert rows == {
        "investor": ("Investor", "product", "elder", "lead", ("pitch",), "Decides whether to invest in an idea: where to take it, or why not"),
        "product-view": ("Product view", "product", "warrior", "build", ("pitch-product",), "Who it is for, what it moves, what it leaves out"),
        "market-view": ("Market view", "marketing", "warrior", "build", ("pitch-market",), "Who would want it, how they would hear of it, what it is like"),
        "tech-view": ("Engineering view", "engineering", "warrior", "build", ("pitch-tech",), "What it touches, how big it is, what it risks"),
        "design-view": ("Design view", "design", "warrior", "build", ("pitch-design",), "Where it lives on screen, the flow, what it costs people"),
        "skeptic": ("Skeptic", "product", "warrior", "check", ("pitch-against",), "Makes the strongest case not to do it")}
    assert not any(k in roles.TASK_KINDS for a in library.LIBRARY if a.pitch for k in a.takes)        # the Taskmaster plans no work for them
    assert roles.RACES[library.get("investor").craft] == "lich" and library.get("investor").check is None
    told = library.get("investor").instruction
    assert len(told) <= roles.INSTRUCTION_CHARS and told.startswith("You decide whether to invest the team's time in an idea.")
    assert all(w in told for w in ("someone it is for is named", "a metric the project has", "reshape it", "pass", "case against",
                                   "cheapest way to know before building"))
    for v in [*library.VIEWS, "skeptic"]:
        said = library.get(v).instruction
        assert len(said) <= roles.INSTRUCTION_CHARS and "invent no number, no user, no competitor" in said and "I cannot tell from here" in said, v
    assert "never the same case twice in other words" in library.get("skeptic").instruction
    listed = {a["id"]: a for a in library.listed()}
    assert listed["investor"]["pitch"] is True and listed["grunt"]["pitch"] is False


def test_the_ideation_preset_follows_website_and_the_investors_stages_are_pitch_views_decision():
    got = library.presets()
    i = [p["id"] for p in got].index("ideation")
    assert got[i - 1]["id"] == "website" and got[i] == {
        "id": "ideation", "name": "Ideation", "line": "Small ideas: invest, reshape or pass, and why", "craft": "product", "race": "lich",
        "mixed": True, "lead": "investor", "build": ["product-view", "market-view", "tech-view", "design-view"], "check": ["skeptic"]}
    assert library.stages()["investor"] == {"lead": "Pitch", "build": "Views", "check": "Decision", "seats": {"lead": 1, "build": 4, "check": 1}}
    assert not goal_team.seats(TEAM, "investor")


def test_seats_refuse_ideation_without_a_view_with_a_code_agent_and_a_view_elsewhere():
    whole = "Ideation reads every pitch from all four sides: its views and the skeptic stay"
    assert goal_team.seats([v for v in TEAM if v != "market-view"], "investor") == whole           # a view out
    assert goal_team.seats([*TEAM[:3], "grunt", "skeptic"], "investor") == whole                     # a code agent for a view
    assert goal_team.seats([*TEAM, "grunt"], "investor") == whole                                    # one more
    assert goal_team.seats(list(library.VIEWS), "investor") == whole                                 # no skeptic
    only = "The views judge pitches: they are in Ideation only"
    assert goal_team.seats(["grunt", "market-view"], "architect") == only
    assert goal_team.seats(["skeptic"], "") == only and goal_team.seats(["grunt", "skeptic"], "product-manager") == only


def test_ideation_is_offered_no_goal_type_and_prices_a_pitch_at_its_calls_caps(keeper):
    assert goal_types.offered(keeper.state, keeper.root, keeper.ideas) == []
    read = goal_types.Party.of(keeper.state, keeper.root, "investor", TEAM)
    assert goal_types.offered(keeper.state, keeper.root, "", read=read) == []
    got = party_price.price(keeper.root, keeper.state, {"target": "balance"}, "investor", TEAM, [])
    assert got == {"low": 0.29, "high": 0.58, "learned": False, "ideas": 0, "checks": [], "pitch": True}       # 4 × 0.08 + 0.06 + 0.20
    assert party_price.price(keeper.root, keeper.state, {"target": "thrift"}, "investor", TEAM, [])["high"] == 0.29


# -- §3: the calls ---------------------------------------------------------------------------------------------------

def test_a_pitch_is_judged_its_views_alone_the_engineering_view_alone_with_tools_the_skeptic_on_the_views_the_investor_on_the_parties(keeper):
    slug = _pitch(keeper)
    model = _judged(keeper, slug)
    st = ideas.state(keeper.state, slug)
    assert st["state"] == "judged" and st["error"] == ""
    views = model.of("pitch_view")
    assert sorted(a["view"] for a in views) == sorted(library.VIEWS) and len(views) == 4
    for a in views:
        assert "TOKEN-" not in a["prompt"], a["view"]                                    # each alone: no view's prompt holds another's answer
        assert a["tools"] is (a["view"] == "tech-view") and a["as"] == a["view"]
        assert a["prompt"].startswith(f"You are the {library.get(a['view']).name} of this project's Ideation party.")
        assert WORDS in a["prompt"] and "- ship: Ship" in a["prompt"] and "night users" in a["prompt"]
        assert ("size" in a["prompt"]) is (a["view"] == "tech-view")
        assert (a["tier"], a["effort"], a["budget"]) == ("warrior", "low", 0.08)
    (case,) = model.of("pitch_case")
    assert all(f"TOKEN-{v} for" in case["prompt"] for v in library.VIEWS) and case["tools"] is False and case["as"] == "skeptic"
    assert (case["tier"], case["effort"], case["budget"]) == ("warrior", "low", 0.06)
    (decide,) = model.of("pitch_decide")
    assert decide["as"] == "investor" and decide["tools"] is False and (decide["tier"], decide["effort"], decide["budget"]) == ("elder", "low", 0.2)
    assert "It solves nothing anyone asked for." in decide["prompt"] and "TOKEN-market-view against" in decide["prompt"]
    assert "- ship: Ship; its goal types: bug, tidy, shaped-feature, restructure" in decide["prompt"]             # the parties with the types each is offered
    assert "- game: Game (a party of the library, not in the project yet)" in decide["prompt"]
    assert "ideation" not in decide["prompt"].split("Where it may go")[1].split("The project's parties")[0]   # never Ideation itself
    j = pitches.read(keeper.state, slug)
    assert j["views"]["tech-view"]["size"] == "M" and j["views"]["market-view"]["size"] == ""           # the Engineering view's only
    assert len(j["views"]["product-view"]["for"]) == 3 and len(j["views"]["product-view"]["for"][1]) == 200
    assert j["case"] == {"case": "It solves nothing anyone asked for.", "kills": ["costly"]}
    assert j["decision"] == {"answer": "invest", "why": ["People on night shifts asked.", "Cheap."], "where": {"party": "ship", "type": "bug"},
                             "first": "Add a dark theme toggle to the settings screen.", "test": "Ask five night-shift users.",
                             "kills": ["costly"], "like": "", "reshaped": False}
    page = ideas.idea_page(keeper.root, slug)
    assert page.section("Gist") == WORDS                                                   # the pitch is kept as written
    assert page.section("Decision").startswith("**Invest: the Ship party, as Fix a bug**")
    assert "Cheapest test: Ask five night-shift users." in page.section("Decision") and "It costs more than it is likely to bring" in page.section("Decision")
    assert st["measure"]["step"] == "pitch" and st["measure"]["cost"] == 0.06


def test_the_target_picks_each_steps_tier_and_effort_and_a_model_set_on_agents_wins(keeper):
    keeper.settings_now["target"] = "thrift"
    model = _judged(keeper, _pitch(keeper))
    assert {(a["tier"], a["effort"]) for a in model.of("pitch_view") + model.of("pitch_case")} == {("laborer", "")}
    assert (model.of("pitch_decide")[0]["tier"], model.of("pitch_decide")[0]["effort"]) == ("warrior", "medium")
    keeper.settings_now["target"] = "quality"
    path = roles.folder(keeper.state) / "market-view.md"
    path.write_text(path.read_text().replace("model: warrior", "model: haiku"))           # the person's own model for the Market view
    model = _judged(keeper, _pitch(keeper, "another pitch"))
    assert {a["view"]: a["tier"] for a in model.of("pitch_view")} == {"product-view": "warrior", "market-view": "haiku",
                                                                       "tech-view": "warrior", "design-view": "warrior"}
    assert model.of("pitch_decide")[0]["tier"] == "elder" and model.of("pitch_decide")[0]["effort"] == "medium"
    assert idea_target.pick("pitch_view", "quality") == ("warrior", "medium")


def test_a_view_that_fails_once_is_tried_again_and_twice_fails_the_pitch(keeper):
    def flaky(fails):
        seen = {"n": 0}

        def answer(prompt):
            if view_of(prompt) == "market-view" and seen["n"] < fails:
                seen["n"] += 1
                return "no json here"
            return VIEW(prompt)
        return answer
    slug = _pitch(keeper)
    model = _judged(keeper, slug, Model(keeper, pitch_view=flaky(1), pitch_case=CASE, pitch_decide=DECIDE()))
    assert ideas.state(keeper.state, slug)["state"] == "judged" and len([a for a in model.of("pitch_view") if a["view"] == "market-view"]) == 2
    other = _pitch(keeper, "a second pitch")
    model = _judged(keeper, other, Model(keeper, pitch_view=flaky(2), pitch_case=CASE, pitch_decide=DECIDE()))
    st = ideas.state(keeper.state, other)
    assert (st["state"], st["error"]) == ("failed", "Market view did not answer: try again")
    assert model.of("pitch_decide") == [] and pitches.read(keeper.state, other)["decision"] is None      # never decided on fewer than four
    assert keeper.judge(other) is True                                                    # Try again
    _wait(keeper, other)


def test_a_decision_that_is_not_json_or_not_one_of_three_fails_the_pitch(keeper):
    slug = _pitch(keeper)
    _judged(keeper, slug, Model(keeper, pitch_view=VIEW, pitch_case=CASE, pitch_decide="I would invest, I think."))
    assert ideas.state(keeper.state, slug)["error"] == "the answer was not the JSON it was asked for"
    _judged(keeper, slug, Model(keeper, pitch_view=VIEW, pitch_case=CASE, pitch_decide={**DECIDE(), "answer": "maybe"}))
    assert ideas.state(keeper.state, slug)["error"] == "the Investor's answer was not invest, reshape or pass"


# -- §4: cut and cleaned -----------------------------------------------------------------------------------------------

def test_the_answer_is_cut_and_cleaned_unknown_party_type_like_and_kills_go_and_an_invest_without_who_is_a_reshape(keeper):
    offered = pitches.offers(keeper.root, keeper.state)
    assert offered["ship"]["preset"] is False and "bug" in offered["ship"]["types"] and offered["game"]["preset"] is True
    assert "ideas" not in offered and "ideation" not in offered
    likes = {"dark-mode": "Dark mode"}
    got = pitches.clean_decision(DECIDE("nowhere", "feature"), [], offered, likes)
    assert got["where"] == {"party": "", "type": ""} and got["answer"] == "invest"             # the invest stands, the person picks
    assert pitches.clean_decision(DECIDE("ship", "logo"), [], offered, likes)["where"] == {"party": "ship", "type": ""}
    assert pitches.clean_decision(DECIDE("game", "level"), [], offered, likes)["where"] == {"party": "game", "type": "level"}
    got = pitches.clean_decision(DECIDE(like="not-a-goal", kills=["repeat", "bogus", "off"]), ["costly", "off"], offered, likes)
    assert got["like"] == "" and got["kills"] == ["costly", "off"] and got["answer"] == "invest"   # repeat without like dropped
    got = pitches.clean_decision(DECIDE(like="dark-mode", kills=["repeat"]), [], offered, likes)
    assert (got["answer"], got["reshaped"], got["kills"], got["like"]) == ("reshape", True, ["repeat"], "dark-mode")
    got = pitches.clean_decision(DECIDE(kills=["no_who"]), [], offered, likes)
    assert (got["answer"], got["reshaped"], got["where"]["party"]) == ("reshape", True, "ship")      # it may still name where
    got = pitches.clean_decision(DECIDE(answer="pass"), ["no_move"], offered, likes)
    assert got["where"] == {"party": "", "type": ""} and got["first"] == "" and got["kills"] == ["no_move"]
    assert pitches.clean_decision(DECIDE(kills=["costly"]), [], offered, likes)["answer"] == "invest"     # only no_who, no_move, repeat reshape
    long = {**DECIDE(), "why": ["w" * 900] * 5, "first": "f" * 900, "test": "t" * 900}
    got = pitches.clean_decision(long, [], offered, likes)
    assert len(got["why"]) == 3 and len(got["why"][0]) == 200 and len(got["first"]) == 300 and len(got["test"]) == 300
    assert set(got) == {"answer", "why", "where", "first", "test", "kills", "like", "reshaped"}
    with pytest.raises(ValueError):
        pitches.clean_decision({"answer": "yes"}, [], offered, likes)
    assert list(pitches.KILLS) == ["no_who", "no_move", "repeat", "costly", "off"]


def test_an_invest_without_who_is_judged_a_reshape_and_its_page_says_why(keeper):
    slug = _pitch(keeper)
    _judged(keeper, slug, Model(keeper, pitch_view=VIEW, pitch_case={"case": "Who is it for?", "kills": ["no_who"]}, pitch_decide=DECIDE()))
    d = pitches.read(keeper.state, slug)["decision"]
    assert d["answer"] == "reshape" and d["reshaped"] and d["kills"] == ["no_who"]
    assert ideas.idea_page(keeper.root, slug).section("Decision").startswith("**Reshape: the Ship party, as Fix a bug**")
    assert "No one it is for is named" in ideas.idea_page(keeper.root, slug).section("Decision")


# -- §7: the night, Stop all -------------------------------------------------------------------------------------------

def test_the_night_judges_a_pitch_put_off_first_held_by_the_window_and_never_by_the_reserve(keeper):
    goal = ideas.add_idea(keeper.root, "a goal for tonight", keeper.ship, keeper.state, queue="night")
    slug = _pitch(keeper, queue="night")
    reset = dt.datetime.now() + dt.timedelta(hours=3)
    keeper.limits_now = [Limit("claude", "", "session", 0.08, reset)]                     # the reserve reached, not the window
    keeper.call = model = Model(keeper, pitch_view=VIEW, pitch_case=CASE, pitch_decide=DECIDE(), draft={})
    counts = keeper.run_night("2026-10-23T01:00")
    assert ideas.state(keeper.state, slug)["state"] == "judged" and counts["drafted"] == 1 and counts["held"] >= 1
    assert ideas.state(keeper.state, goal)["state"] == "raw" and model.of("draft") == []      # the goal waits for the reserve
    other = _pitch(keeper, "a second pitch", queue="night")
    keeper.limits_now = [Limit("claude", "", "session", 0.03, reset)]                     # the window nearly spent: it waits too
    counts = keeper.run_night("2026-10-24T01:00")
    assert ideas.state(keeper.state, other)["state"] == "raw" and ideas.state(keeper.state, other)["held_until"] and counts["drafted"] == 0


def test_stop_all_stops_a_judging_pitch_failed_and_stopped(keeper):
    slug = _pitch(keeper)
    keeper.call = model = Model(keeper, pitch_view=VIEW, pitch_case=CASE, pitch_decide=DECIDE())
    model.gate["pitch_view"] = held = threading.Event()
    keeper.judge(slug)
    for _ in range(200):
        if model.of("pitch_view"):
            break
        time.sleep(0.01)
    keeper.stop_all()
    held.set()
    _wait(keeper, slug)
    st = ideas.state(keeper.state, slug)
    assert (st["state"], st["error"]) == ("failed", "stopped") and model.of("pitch_decide") == []


def test_the_draft_and_the_plan_refuse_a_pitch_and_a_raw_pitch_is_judged_where_a_goal_would_be_drafted(keeper):
    from orkboard.core.idea_keeper import KeeperError
    slug = _pitch(keeper)
    with pytest.raises(KeeperError, match="A pitch is judged, not built: send it to a party first"):
        keeper.plan(slug)
    keeper.call = model = Model(keeper, pitch_view=VIEW, pitch_case=CASE, pitch_decide=DECIDE())
    keeper.draft(slug)                                                                   # Add's, the clock's and Process now's way
    _wait(keeper, slug)
    assert ideas.state(keeper.state, slug)["state"] == "judged" and model.of("draft") == []


# -- §5, §6: the commands, the events, Needs you, the faces -------------------------------------------------------------

@pytest.fixture
def host(fake_repo):
    h = Orkboard(fake_repo)
    h.model = h.ideas.keeper.call = Model(h.ideas.keeper, pitch_view=VIEW, pitch_case=CASE, pitch_decide=DECIDE(),
                                          goal={"summary": "", "questions": []}, draft={"title": "Dark theme", "questions": []})
    h.ship = h.command("ideas.goal_save", {"title": "Ship", "about": "Ship it.", "craft": "engineering", "leader": "architect",
                                           "team": ["grunt", "tester", "reviewer"]})["slug"]
    h.party = h.command("ideas.goal_save", {"title": "Ideas", "about": "Small ideas.", "craft": "product", "leader": "investor",
                                            "team": TEAM, "preset": "ideation"})["slug"]
    for g in (h.ship, h.party):
        for _ in range(300):
            if not h.ideas.keeper.busy_goal(g):
                break
            time.sleep(0.01)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


def _add_pitch(host, text=WORDS, **more):
    slug = host.command("ideas.add", {"text": text, "track": host.party, **more})["slug"]
    _wait(host.ideas.keeper, slug)
    return slug


def _events(host, name):
    return [r for r in event_log.read(host.ideas.host.repo_root) if r["event"] == name]


def test_the_party_is_made_only_whole_and_a_view_is_refused_elsewhere(host):
    with pytest.raises(CommandError, match="Ideation reads every pitch from all four sides"):
        host.command("ideas.goal_save", {"about": "Fewer.", "leader": "investor", "team": TEAM[1:]})
    with pytest.raises(CommandError, match="The views judge pitches: they are in Ideation only"):
        host.command("ideas.goal_save", {"about": "Mixed.", "leader": "architect", "team": ["grunt", "market-view"]})
    price = host.command("ideas.party_price", {"leader": "investor", "team": TEAM, "craft": "product"})
    assert price["pitch"] is True and price["types"] == [] and price["hints"] == [] and price["high"] == 0.58


def test_a_pitch_is_added_judged_and_refused_by_the_plans_commands(host):
    slug = _add_pitch(host, "x" * 3000)
    assert len(ideas.idea_page(host.ideas.root(), slug).section("Gist")) == pitches.PITCH_CHARS
    assert ideas.state(host.ideas.state_dir, slug)["state"] == "judged"
    for name, args in (("ideas.start", {"slug": slug}), ("ideas.plan", {"slug": slug}), ("ideas.revise", {"slug": slug}),
                       ("ideas.answer", {"slug": slug, "answers": []}), ("ideas.say", {"slug": slug, "text": "hi"}),
                       ("ideas.todo", {"idea": slug, "id": "t1"}), ("ideas.start_now", {"slug": slug})):
        with pytest.raises(CommandError, match="A pitch is judged, not built: send it to a party first"):
            host.command(name, args)
    with pytest.raises(CommandError, match="A pitch has no goal type"):
        host.command("ideas.add", {"text": "typed", "track": host.party, "type": "bug"})
    held = host.command("ideas.add", {"text": "kept for later", "track": host.party, "hold": True})
    assert held["queue"] == "hold" and ideas.state(host.ideas.state_dir, held["slug"])["state"] == "raw"
    host.command("ideas.judge", {"slug": held["slug"]})
    _wait(host.ideas.keeper, held["slug"])
    assert ideas.state(host.ideas.state_dir, held["slug"])["state"] == "judged"


def test_what_the_faces_read_of_a_pitch_on_its_page_and_its_map_node_and_needs_you_out_of_the_count(host):
    slug = _add_pitch(host)
    page = host.command("ideas.page", {"slug": slug})
    p = page["pitch"]
    assert set(p) == {"state", "views", "skeptic", "investor", "case", "decision", "sent", "passed", "before"} and p["state"] == "judged"
    assert [v["slug"] for v in p["views"]] == list(library.VIEWS) and all(v["answered"] for v in p["views"])
    assert set(p["views"][0]) == {"slug", "name", "head", "answered", "for", "against", "question", "size"}
    assert p["views"][2]["name"] == "Engineering view" and p["views"][2]["head"]["race"] == "peon" and p["views"][2]["size"] == "M"
    assert p["case"] == {"case": "It solves nothing anyone asked for.", "kills": [{"id": "costly", "words": "It costs more than it is likely to bring"}]}
    assert p["decision"]["word"] == "Invest" and p["decision"]["where"] == {"party": host.ship, "name": "Ship", "preset": False,
                                                                            "type": "bug", "type_name": "Fix a bug"}
    assert p["investor"]["name"] == "Investor" and p["investor"]["head"]["race"] == "lich" and p["sent"] is None and p["before"] == []
    assert host.command("ideas.page", {"slug": ideas.add_idea(host.ideas.root(), "a goal", host.ship, host.ideas.state_dir)})["pitch"] is None
    m = host.command("ideas.map", {"goal": host.party})
    (g,) = m["goals"]
    assert g["ideation"] is True and g["passed"] == 0 and g["types"] == [] and g["stages"]["build"] == {"word": "Views", "seats": 4}
    (node,) = m["nodes"]
    assert node["pitch"]["decision"]["answer"] == "invest" and node["needs_you"] == "pitch" and node["stage"] == "checking"
    board = host.command("ideas.board")
    row = next(n for n in board["needs_you"] if n["idea"] == slug)
    assert (row["kind"], row["priority"], row["blocks"], row["text"], row["answer"]) == ("pitch", "low", False, "Judged: Invest", "invest")
    host.ideas.rev += 1
    assert host.snapshot()["needs_you"] == 0                                              # it waits for the person, it holds nothing


def test_send_adds_the_goal_in_the_party_with_its_type_and_the_from_ideation_line_and_its_draft_reads_the_views(host):
    slug = _add_pitch(host)
    with pytest.raises(CommandError, match="Make the Game party first"):
        host.command("ideas.pitch_send", {"slug": slug, "party": "game"})
    with pytest.raises(CommandError, match="That party is gone"):
        host.command("ideas.pitch_send", {"slug": slug, "party": host.party})
    got = host.command("ideas.pitch_send", {"slug": slug, "party": host.ship})
    assert (got["party"], got["type"], got["queue"]) == (host.ship, "bug", "now")
    _wait(host.ideas.keeper, got["slug"])
    root, state = host.ideas.root(), host.ideas.state_dir
    gist = ideas.idea_page(root, got["slug"]).section("Gist")
    assert gist.startswith("Add a dark theme toggle to the settings screen.") and "From Ideation: " in gist and f"({slug})" in gist
    assert ideas.idea_page(root, got["slug"]).get("track") == host.ship and ideas.state(state, got["slug"])["type"] == "bug"
    assert ideas.state(state, got["slug"])["from_pitch"] == slug
    (draft,) = host.model.of("draft")
    assert "This goal was sent from Ideation" in draft["prompt"] and "TOKEN-market-view for" in draft["prompt"] and "Ask five night-shift users." in draft["prompt"]
    assert ideas.state(state, slug)["state"] == "sent"
    sent = host.command("ideas.page", {"slug": slug})["pitch"]["sent"]
    assert (sent["party"], sent["goal"], sent["as_decided"], sent["name"]) == (host.ship, got["slug"], True, "Ship")
    with pytest.raises(CommandError, match="This pitch is sent"):
        host.command("ideas.pitch_send", {"slug": slug, "party": host.ship})
    (ev,) = _events(host, event_log.PITCH_SENT)
    assert (ev["goal"], ev["to"], ev["type"], ev["as_decided"]) == (slug, host.ship, "bug", True)


def test_pass_keeps_it_a_later_pitchs_prompts_hold_its_why_and_the_oldest_beyond_the_cap_goes(host, monkeypatch):
    slug = _add_pitch(host, "a pitch to pass")
    assert host.command("ideas.pitch_pass", {"slug": slug, "why": "Not now,   not ever."}) == {"ok": True, "dropped": []}
    assert ideas.state(host.ideas.state_dir, slug)["state"] == "passed" and ideas.idea_page(host.ideas.root(), slug) is not None
    later = _add_pitch(host, "a later pitch")
    for a in [*host.model.of("pitch_view")[-4:], host.model.of("pitch_decide")[-1]]:
        assert f"{slug}: a pitch to pass — People on night shifts asked.; Cheap.; the person: Not now, not ever." in a["prompt"]
    m = host.command("ideas.map", {"goal": host.party})
    assert m["goals"][0]["passed"] == 1 and next(n for n in m["nodes"] if n["slug"] == slug)["folded"] is True
    monkeypatch.setattr(pitches, "KEEP_PASSED", 1)
    was = pitches.read(host.ideas.state_dir, slug)["passed"]
    pitches.save(host.ideas.state_dir, slug, passed={**was, "at": "2026-10-01T09:00:00"})      # passed before the next one
    got = host.command("ideas.pitch_pass", {"slug": later})
    assert got["dropped"] == [slug] and ideas.idea_page(host.ideas.root(), slug) is None
    assert pitches.KEEP_PASSED == 1 and pitches.passed(host.ideas.root(), host.ideas.state_dir)[0]["slug"] == later
    evs = _events(host, event_log.PITCH_PASSED)
    assert [(e["goal"], e["as_decided"], e["has_reason"]) for e in evs] == [(slug, False, True), (later, False, False)]


def test_the_cap_is_two_hundred():
    assert pitches.KEEP_PASSED == 200 and pitches.PROMPT_PASSED == 20


def test_change_and_judge_again_keeps_the_last_two_decisions_and_a_passed_pitch_is_judged_again(host):
    slug = _add_pitch(host)
    host.model.answers["pitch_decide"] = [DECIDE(answer="reshape"), DECIDE(answer="pass"), DECIDE()]
    host.command("ideas.pitch_again", {"slug": slug, "text": "A dark mode, only for the night shift's own screen"})
    _wait(host.ideas.keeper, slug)
    page = ideas.idea_page(host.ideas.root(), slug)
    assert page.section("Gist") == "A dark mode, only for the night shift's own screen" and page.title.startswith("A dark mode, only")
    host.command("ideas.pitch_pass", {"slug": slug})
    host.command("ideas.pitch_again", {"slug": slug})                                    # Judged again: its words as they are
    _wait(host.ideas.keeper, slug)
    host.command("ideas.pitch_again", {"slug": slug})
    _wait(host.ideas.keeper, slug)
    p = host.command("ideas.page", {"slug": slug})["pitch"]
    assert p["decision"]["answer"] == "invest" and [b["answer"] for b in p["before"]] == ["pass", "reshape"]
    assert p["passed"] is None
    evs = _events(host, event_log.PITCH_AGAIN)
    assert [(e["goal"], e["changed"]) for e in evs] == [(slug, True), (slug, False), (slug, False)]


def test_the_events_hold_no_pitchs_words_and_the_party_counts_what_the_person_did(host):
    slug = _add_pitch(host)
    other = _add_pitch(host, "another pitch, OTHER-WORDS")
    host.command("ideas.pitch_send", {"slug": slug, "party": host.ship})
    host.command("ideas.pitch_pass", {"slug": other, "why": "PASS-WORDS"})
    rows = [r for r in event_log.read(host.ideas.host.repo_root) if r["event"].startswith("pitch_")]
    assert {r["event"] for r in rows} == {"pitch_judged", "pitch_sent", "pitch_passed"}
    text = json.dumps(rows)
    assert "SECRET-WORDS" not in text and "OTHER-WORDS" not in text and "PASS-WORDS" not in text
    judged = next(r for r in rows if r["event"] == "pitch_judged")
    assert set(judged) >= {"goal", "answer", "kills", "tokens", "cost", "seconds"} and judged["answer"] == "invest"
    assert judged["kills"] == ["costly"] and judged["cost"] == 0.06
    assert {pitches_event for pitches_event in event_log.EVENTS if pitches_event.startswith("pitch_")} == {
        "pitch_judged", "pitch_sent", "pitch_passed", "pitch_again"}
    work = host.command("ideas.party", {"goal": host.party})
    assert work["pitches"] == {"judged": 2, "sent": 1, "passed": 1, "as_decided": 0.5, "flags": 0}
    assert "pitches" not in host.command("ideas.party", {"goal": host.ship})


def test_the_words_are_in_the_glossary():
    from orkboard.realm import lexicon
    assert lexicon.term("pitch") == "pitch" and lexicon.term("pitch", many=True) == "pitches"
    assert lexicon.term("pitch_view", many=True) == "views" and lexicon.term("pitch_case") == "the case against"
    assert lexicon.term("pitch_decision") == "decision" and lexicon.term("pitch_passed") == "passed"
    rows = {key: (word, was) for key, word, was in lexicon.glossary()}
    assert all(rows[k][1] == "" for k in ("pitch", "pitch_view", "pitch_case", "pitch_decision", "pitch_passed"))
