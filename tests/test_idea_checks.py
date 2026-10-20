"""Spec 43 A (docs/specs/43-party-measured.md §1.2, §1.5): what a check task writes (`parse_findings`) and what the idea's Checks say
of it (`status`). The runner's side is in tests/test_idea_runner.py."""
from __future__ import annotations

import json

import pytest

from orkboard.realm import idea_checks, library


def ok(*rows):
    return json.dumps({"findings": [{"where": w, "what": "x", "fixed": f} for w, f in rows]})


def test_the_tags_are_the_first_takes_of_every_checker():
    assert idea_checks.TAGS == ("security", "review", "a11y", "datacheck", "edit")
    assert all(a.takes[0] in idea_checks.TAGS for a in library.LIBRARY if a.check is not None)


def test_parse_findings_reads_the_shape_strictly():
    assert idea_checks.parse_findings('{"findings": []}') == []
    assert idea_checks.parse_findings(ok(("a.py:1", True), ("b", False))) == [
        {"where": "a.py:1", "what": "x", "fixed": True}, {"where": "b", "what": "x", "fixed": False}]
    assert len(idea_checks.parse_findings(ok(*[("w", False)] * 20))) == 20
    assert idea_checks.parse_findings(ok(*[("w", False)] * 21)) is None


@pytest.mark.parametrize("text", [
    "", "{not json", "[]", '{"findings": {}}', '{"other": []}', '{"findings": ["x"]}',
    '{"findings": [{"where": "a", "what": "b"}]}',                                   # no `fixed`
    '{"findings": [{"where": "a", "what": "b", "fixed": "yes"}]}',                   # not a boolean
    '{"findings": [{"where": 1, "what": "b", "fixed": true}]}',                      # not text
    json.dumps({"findings": [{"where": "w" * 201, "what": "b", "fixed": True}]}),    # where: 200 at most
    json.dumps({"findings": [{"where": "a", "what": "b" * 301, "fixed": True}]}),    # what: 300 at most
])
def test_a_missing_file_bad_json_or_a_bad_shape_is_none(text):
    assert idea_checks.parse_findings(text) is None


def test_the_lengths_at_their_limits_pass():
    assert idea_checks.parse_findings(json.dumps({"findings": [{"where": "w" * 200, "what": "b" * 300, "fixed": False}]})) is not None


def test_status_says_found_fixed_and_left_once_the_task_ended():
    checks = idea_checks.of_team(None or __import__("pathlib").Path("/nonexistent"), ["security-reviewer", "reviewer", "accessibility-reviewer"])
    kept = [{"by": c["by"], "applies": True, "why": ""} for c in checks]
    tasks = [{"id": "k1", "kind": "security", "state": "merged", "findings": []},
             {"id": "k2", "kind": "review", "state": "review", "findings": [{"where": "a", "what": "b", "fixed": True},
                                                                              {"where": "c", "what": "d", "fixed": False}]},
             {"id": "k3", "kind": "a11y", "state": "running", "findings": [{"where": "a", "what": "b", "fixed": False}]}]
    got = {s["by"]: s for s in idea_checks.status(kept, checks, tasks)}
    assert (got["security-reviewer"]["found"], got["security-reviewer"]["fixed"], got["security-reviewer"]["left"]) == (0, 0, 0)
    assert (got["reviewer"]["found"], got["reviewer"]["fixed"], got["reviewer"]["left"]) == (2, 1, 1)
    assert (got["accessibility-reviewer"]["found"], got["accessibility-reviewer"]["fixed"], got["accessibility-reviewer"]["left"]) == (None, None, None)
    ended_before = idea_checks.status(kept[:1], checks[:1], [{"id": "k1", "kind": "security", "state": "merged"}])[0]
    assert (ended_before["found"], ended_before["fixed"], ended_before["left"]) == (None, None, None)       # before part A
    assert idea_checks.status(kept[:1], checks[:1], [])[0]["found"] is None
