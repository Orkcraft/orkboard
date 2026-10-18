"""Spec 35 §4, §5: an idea's risk by rules (a case per trigger row), whole words in any case, the repository's own paths,
the max with the model's, the Risks line; who passes a plan (the nine cells)."""
from __future__ import annotations

import pytest

from orkboard.realm import idea_risk
from orkboard.realm.idea_risk import assess


@pytest.mark.parametrize("touches,texts,trigger,level", [
    (["src/auth/session.py"], [], idea_risk.SECRETS, "medium"),
    ([], ["Keep the API Token out of the logs"], idea_risk.SECRETS, "medium"),
    (["db/migrations/0002_add.py"], [], idea_risk.DATA, "medium"),
    (["schema/users.sql"], [], idea_risk.DATA, "medium"),
    ([], ["Delete the old user data at start"], idea_risk.DATA, "medium"),
    ([".github/workflows/ci.yml"], [], idea_risk.CI, "medium"),
    (["Dockerfile"], [], idea_risk.CI, "medium"),
    ([], ["then RELEASE it"], idea_risk.CI, "medium"),
    ([], ["this is a Breaking Change for callers"], idea_risk.API, "medium"),
    ([f"d{n}/x.py" for n in range(6)], [], idea_risk.WIDE, "medium"),
    ([], ["We send an email to every user"], idea_risk.OUTWARD, "high"),
    ([], ["push to main when green"], idea_risk.OUTWARD, "high"),
])
def test_each_trigger_raises_the_risk(touches, texts, trigger, level):
    got = assess(touches, texts)
    assert trigger in got.triggers and got.risk == level


def test_whole_words_only_and_a_quiet_spec_stays_low():
    assert assess([], ["tokens of the lexer, a releases page, republished"]).risk == "low"
    assert assess(["src/app.py"], ["Add a dark mode toggle"]).triggers == []


def test_wide_by_tasks_the_repositorys_own_paths_and_the_max_with_the_models():
    assert idea_risk.WIDE in assess([], [], tasks=7).triggers and assess([], [], tasks=6).risk == "low"
    got = assess(["billing_core/x.py"], [], risk_paths=["billing_core/*"])
    assert idea_risk.OWN in got.triggers and got.risk == "medium"
    assert assess([], [], risk_model="high").risk == "high"                      # the model's own stays
    assert assess([".github/workflows/x.yml"], [], risk_model="low").risk == "medium"   # the rules raise it
    assert assess([], ["notify users"], risk_model="medium").risk == "high"


def test_the_risks_line_says_the_risk_and_what_raised_it():
    assert assess([".github/workflows/ci.yml"], []).line == "Risk: Medium — CI and deploy (`.github/workflows/`)"
    assert assess([], []).line == "Risk: Low"
    assert idea_risk.strip_line("Risk: Medium — x\n\nProduct:\n- y") == "\nProduct:\n- y"


@pytest.mark.parametrize("risk,priority,what", [
    ("low", "high", "start"), ("low", "normal", "start"), ("low", "low", "night"),
    ("medium", "high", "start"), ("medium", "normal", "wait"), ("medium", "low", "wait"),
    ("high", "high", "wait"), ("high", "normal", "wait"), ("high", "low", "wait")])
def test_the_nine_cells_of_autostart(risk, priority, what):
    assert idea_risk.decide(risk, priority) == what
