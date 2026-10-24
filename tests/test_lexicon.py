"""One word for each concept: the Camp's when it says who, a plain one when it says what a thing does. The town's
building types (realm/catalog.py) and its plain labels (realm/modes.py) are Orkline's, and their checks stay there."""
from __future__ import annotations

from orkboard.realm import lexicon


def test_a_concept_has_one_word():
    assert lexicon.term("watchtower") == "External listeners"
    assert lexicon.term("road", many=True) == "roads"
    assert lexicon.term("ork") == "ork" and lexicon.term("ork", many=True) == "orks"
    assert lexicon.term("orc.town_hall") == "Workchief" and lexicon.term("town_hall") == "Town Hall"
    assert lexicon.term("chore", many=True) == "to-dos"


def test_an_old_camp_spelling_reads_in_todays_word():
    say = lexicon.words
    assert say("Spawn Ork") == "Add ork"
    assert say("3 orks in the Barracks") == "3 orks in the Agent pool"
    assert say("Orks wait on the road") == "Orks wait on the road"            # who keeps its word
    assert say("🧌 GARRISON") == "🧌 ORKS"
    assert say("No buildings in this orkspace yet.") == "No buildings in this orkspace yet."
    assert say("Ask the Workchief") == "Ask the Workchief"
    assert say("Ask the Warchief") == "Ask the Workchief" and say("The Warchief's chat") == "The Workchief's chat"
    assert say("Standing orders & trigger") == "Instructions & trigger"
    assert say("📯 War Horn") == "📯 Stop all" and say("Not enough food") == "No ork slots left"
    assert say("Wandering Ghost") == "Wandering Ghost" and say("Inbox Ghost") == "Inbox Ghost"   # a kin, never a preview


def test_a_word_inside_another_stays():
    say = lexicon.words
    assert say("Orkcraft: work downtown, a roadmap") == "Orkcraft: work downtown, a roadmap"
    assert say("the goldfish") == "the goldfish"


def test_the_gui_gets_every_spelling():
    table = dict(lexicon.table())
    assert table["Watchtower"] == "External listeners" and table["Chores"] == "To-dos"
    assert table["GARRISON"] == "ORKS"
    assert "orks" not in table and "Workchief" not in table and "road" not in table   # nothing to change
    assert table["Warchief"] == "Workchief" and table["WARCHIEF"] == "WORKCHIEF"


def test_a_path_is_not_a_concept():
    say = lexicon.words
    assert say("./loot/ and loot/screenshots, src/roads.py") == "./loot/ and loot/screenshots, src/roads.py"
    assert say("the loot.") == "the output."


def test_the_heaviest_tier_is_a_veteran_and_the_nights_council_are_the_elders():
    say = lexicon.words
    assert say("★★★ Elder — opus") == "★★★ Veteran — opus" and say("Default — Quality: Elder") == "Default — Quality: Veteran"
    assert say("The Elders advise") == "The Elders advise" and lexicon.term("elders", many=True) == "Elders"
    from orkboard.realm import tiers
    assert tiers.label("elder").endswith("Veteran") and say("warrior") == "warrior"   # a setting's value stays


def test_the_glossary_says_what_each_word_replaced():
    rows = {key: (word, was) for key, word, was in lexicon.glossary()}
    assert rows["watchtower"] == ("External listeners", "Watchtower")
    assert rows["ork"] == ("ork", "")


def test_the_test_bench_and_its_mechanic_under_every_name_they_had():
    """The Test bench was the Alchemist's Lab and its ork a Brewmaster, then a Gearhead: the Mechanic now."""
    assert lexicon.words("Alchemist's Lab") == "Test bench"
    assert lexicon.words("Gearhead") == lexicon.words("Brewmaster") == "Mechanic"
    assert lexicon.words("🧪 Mechanic") == "🧪 Mechanic" and lexicon.words("Alchemist") == "Alchemist"


def test_the_town_scroll_is_the_town_file_and_a_project_is_its_folder():
    """docs/design/projects.md §2: "Project" is the folder an orkspace works in, so the scroll is the Town file."""
    assert lexicon.term("town_scroll") == "Town file" and lexicon.term("town_scroll", many=True) == "Town files"
    assert lexicon.words("Saved to the Town Scroll") == "Saved to the Town file"
    assert lexicon.term("project") == "Project" and lexicon.term("project", many=True) == "Projects"


def test_what_was_a_goal_is_a_party_and_what_was_an_idea_is_a_goal():
    """Decisions §63.1: the interface says party for the code's track (a goal's page) and goal for the code's idea. A goal is
    today's word, never an old spelling; `idea` keeps its own (the interface says an old *idea* in today's word) and `track` its."""
    say = lexicon.words
    assert lexicon.term("track") == "party" and lexicon.term("track", many=True) == "parties"
    assert lexicon.term("idea") == "goal" and lexicon.term("idea", many=True) == "goals"
    assert lexicon.term("party") == "party" and lexicon.term("party", many=True) == "parties"      # the members, unchanged
    assert say("the goal") == "the goal" and say("Goal") == "Goal"                                  # "Goal" is no longer the Target's old word
    assert say("your tracks") == "your parties" and say("Track") == "Party"
    assert say("New idea") == "New goal" and say("3 ideas") == "3 goals"                            # an old idea in today's word (spec 50 §2.1)
    rows = {key: (word, was) for key, word, was in lexicon.glossary()}
    assert rows["track"] == ("party", "track") and rows["idea"] == ("goal", "idea") and rows["steward_goal"] == ("Target", "")
    assert rows["flag"] == ("flag", "") and rows["pick"] == ("pick", "")                            # spec 51: the stop Pick one
    assert lexicon.term("pick") == "pick" and lexicon.term("pick", many=True) == "picks"
    table = dict(lexicon.table())
    assert table["track"] == "party" and table["Tracks"] == "Parties" and "Goal" not in table and "goal" not in table


def test_a_goal_type_is_what_kind_of_goal_a_leader_deals_spec_52():
    """Spec 52 §2.8: `goal_type`, today's word with no old spelling (the interface seldom says it: it says the type's name)."""
    assert lexicon.term("goal_type") == "goal type" and lexicon.term("goal_type", many=True) == "goal types"
    rows = {key: (word, was) for key, word, was in lexicon.glossary()}
    assert rows["goal_type"] == ("goal type", "")
    assert lexicon.words("New goal: your own, or pick its type") == "New goal: your own, or pick its type"


def test_the_lines_of_stage_and_goal_type_say_what_the_leader_and_the_team_decide_spec_59():
    """Spec 59 §0: a stage is worded by its leader; a goal type is what a party's team can take on. (The glossary's lines are the comments of `TERMS`.)"""
    from pathlib import Path
    source = Path(lexicon.__file__).read_text(encoding="utf-8")
    stage = next(l for l in source.splitlines() if l.lstrip().startswith('_t("stage"'))
    goal_type = next(l for l in source.splitlines() if l.lstrip().startswith('_t("goal_type"'))
    assert "its leader words them" in stage and "Concept, Build, Playtest" in stage and "Planning, Implementation, Checking" in stage
    assert "a party's team can take on" in goal_type and "specs 52 and 59" in goal_type and "leader deals" not in goal_type
    assert lexicon.term("stage") == "stage" and lexicon.term("goal_type") == "goal type"


def test_a_plan_change_is_the_leaders_re_plan_of_what_is_left_spec_62():
    """Spec 62 §0: one word for the leader's re-plan of what is left after a goal's spec changed; today's word, no old spelling."""
    assert lexicon.term("plan_change") == "plan change" and lexicon.term("plan_change", many=True) == "plan changes"
    assert {key: (word, was) for key, word, was in lexicon.glossary()}["plan_change"] == ("plan change", "")
    from pathlib import Path
    line = next(l for l in Path(lexicon.__file__).read_text(encoding="utf-8").splitlines() if l.lstrip().startswith('_t("plan_change"'))
    assert "spec 62" in line and "Take the new plan" in line and "plan_change.json" in line
    assert lexicon.words("Take the new plan") == "Take the new plan" and lexicon.words("The plan changes · +2") == "The plan changes · +2"


def test_a_route_a_release_and_out_are_the_words_of_spec_67_and_the_skeleton_is_a_race():
    """Spec 68 §0: a goal's route across parties, a release (a goal of A release) and out (the person said it is in the stores); the skeleton."""
    assert (lexicon.term("idea_route"), lexicon.term("idea_route", many=True)) == ("route", "routes")
    assert (lexicon.term("release"), lexicon.term("release", many=True)) == ("release", "releases") and lexicon.term("release_out") == "out"
    assert (lexicon.term("race.skeleton"), lexicon.term("race.skeleton", many=True)) == ("skeleton", "skeletons")
    rows = {key: (word, was) for key, word, was in lexicon.glossary()}
    assert all(rows[k][1] == "" for k in ("idea_route", "release", "release_out", "race.skeleton"))
    from pathlib import Path
    lines = {k: next(l for l in Path(lexicon.__file__).read_text(encoding="utf-8").splitlines() if l.lstrip().startswith(f'_t("{k}"'))
             for k in ("idea_route", "release", "release_out", "race.skeleton")}
    assert all("spec 68" in line for line in lines.values()) and "orkUI 0.5.0" in lines["race.skeleton"]


def test_the_orkmaster_and_the_projects_level_are_the_words_of_spec_70():
    """Spec 70 §0: the project's ork (it deals the parties and a goal's party; it plans nothing) and the project's level."""
    from pathlib import Path
    assert lexicon.term("orkmaster") == "Orkmaster" and lexicon.term("project_level") == "The project"
    rows = {key: (word, was) for key, word, was in lexicon.glossary()}
    assert rows["orkmaster"] == ("Orkmaster", "") and rows["project_level"] == ("The project", "")
    lines = {k: next(l for l in Path(lexicon.__file__).read_text(encoding="utf-8").splitlines() if l.lstrip().startswith(f'_t("{k}"'))
             for k in ("orkmaster", "project_level")}
    assert all("spec 70" in line for line in lines.values()) and "plans nothing" in lines["orkmaster"]
