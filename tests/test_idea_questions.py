"""realm/idea_questions.py (docs/specs/41-phone-round-3.md §9): a question's choices, the Taskmaster's pick and why."""
from __future__ import annotations

from orkboard.realm import idea_questions as iq


def test_a_question_from_the_model_is_taken_strictly():
    q = iq.of({"ask": " Which store  first? ", "choices": ["App Store", "Google Play"], "pick": 0, "why": "iPhone first"})
    assert q == {"ask": "Which store first?", "choices": ["App Store", "Google Play"], "pick": 0, "why": "iPhone first"}
    assert iq.of({"ask": "A?", "choices": ["x", "y"], "pick": "Y"})["pick"] == 1               # a pick by its words
    assert iq.of({"ask": "A?", "choices": ["x", "y"], "pick": 2})["pick"] is None              # out of range
    assert iq.of({"ask": "A?", "choices": ["x", "y"], "pick": True})["pick"] is None
    for bad in (["only one"], ["a", "b", "c", "d", "e"], ["a/b", "c"], ["x" * 41, "y"], ["same", "Same"], "a / b"):
        assert iq.of({"ask": "A?", "choices": bad, "pick": 0, "why": "w"}) == {"ask": "A?", "choices": [], "pick": None, "why": ""}
    assert iq.of({"ask": "", "choices": ["x", "y"]}) is None and iq.of(3) is None and iq.of(None) is None
    assert len(iq.of({"ask": "A?", "choices": ["x", "y"], "why": "w " * 200})["why"]) <= iq.WHY_CHARS
    assert iq.of("Which week? (this / next)") == {"ask": "Which week?", "choices": ["this", "next"], "pick": None, "why": ""}
    assert iq.all_of([{"ask": "A?"}, 5, "B?", "C?"], 2) == [{"ask": "A?", "choices": [], "pick": None, "why": ""},
                                                          {"ask": "B?", "choices": [], "pick": None, "why": ""}]
    assert iq.all_of("not a list", 3) == []


def test_the_pages_line_says_the_pick_in_bold_and_reads_back():
    q = {"ask": "Which store first?", "choices": ["App Store", "Google Play"], "pick": 0, "why": "iPhone first"}
    line = iq.line(q)
    assert line == "Which store first? (**App Store** / Google Play) — iPhone first"
    assert iq.parse(line) == q
    assert iq.line({"ask": "Why?", "choices": [], "pick": None, "why": ""}) == "Why?"
    assert iq.parse("Which store first (App Store / Google Play)?") == {
        "ask": "Which store first?", "choices": ["App Store", "Google Play"], "pick": None, "why": ""}   # a line of before
    assert iq.parse("Pick one (a / b / c / d / e)")["choices"] == []
    assert iq.parse("Both bold (**a** / **b**)")["pick"] is None
    assert iq.parse("") == {"ask": "", "choices": [], "pick": None, "why": ""}


def test_a_goal_s_question_may_say_who_it_is_for_and_the_page_does_not_keep_it():
    """Spec 46 §1: `by` is the slug of the member whose view the question answers; the line is the same."""
    q = iq.of({"ask": "Which?", "choices": ["a", "b"], "pick": 1, "by": "Reviewer"})
    assert q["by"] == "reviewer" and iq.line(q) == "Which? (a / **b**)"
    assert "by" not in iq.of({"ask": "Which?"}) and "by" not in iq.parse(iq.line(q))
    assert iq.asked_by([q, {"ask": "x", "by": "ghost"}, {"ask": "y"}], ["reviewer"], "taskmaster") == ["reviewer", "taskmaster", "taskmaster"]
