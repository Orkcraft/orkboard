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
    today's word, never an old spelling (B adds the `was` of `idea` with its templates); `track` keeps only its own."""
    say = lexicon.words
    assert lexicon.term("track") == "party" and lexicon.term("track", many=True) == "parties"
    assert lexicon.term("idea") == "goal" and lexicon.term("idea", many=True) == "goals"
    assert lexicon.term("party") == "party" and lexicon.term("party", many=True) == "parties"      # the members, unchanged
    assert say("the goal") == "the goal" and say("Goal") == "Goal"                                  # "Goal" is no longer the Target's old word
    assert say("your tracks") == "your parties" and say("Track") == "Party"
    rows = {key: (word, was) for key, word, was in lexicon.glossary()}
    assert rows["track"] == ("party", "track") and rows["idea"] == ("goal", "") and rows["steward_goal"] == ("Target", "")
    assert rows["flag"] == ("flag", "")
    table = dict(lexicon.table())
    assert table["track"] == "party" and table["Tracks"] == "Parties" and "Goal" not in table and "goal" not in table
