"""Spec 43 F (docs/specs/43-party-measured.md §6, Tests → F): your parties — the file (save, the twelve, a taken name refused and replaced, drop,
`uses` at most 50, a broken file read as none and kept, mode 600), `ideas.party_save` from a goal with an agent of the person's own,
`ideas.goal_save` with `party` in another project, a later party change clearing it, accepting the goal marking `met`, `ideas.parties`, the
events. Code, no model."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, goal_team, jobs, own_parties, roles
from orkboard.realm import ideas


def repo(tmp_path: Path, name: str) -> Path:
    r = tmp_path / name
    r.mkdir()
    (r / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    for cmd in (["init"], ["config", "user.email", "t@x"], ["config", "user.name", "T"], ["add", "."], ["commit", "-m", "start"]):
        subprocess.run(["git", *cmd], cwd=r, check=True, capture_output=True)
    return r


@pytest.fixture
def host(fake_repo) -> Orkboard:
    return Orkboard(fake_repo)


def lean(**more):
    base = dict(name="Lean web", craft="engineering", leader="architect", team=["grunt", "tester", "reviewer"], every=["reviewer"], own=[])
    return own_parties.save(**{**base, **more})


# -- the file ------------------------------------------------------------------------------------------------------

def test_a_party_is_saved_listed_and_dropped_in_a_private_file_beside_the_settings():
    assert own_parties.list() == [] and not own_parties.path().exists()
    party = lean(own=[{"slug": "docs-scribe", "name": "Docs scribe", "craft": "design", "model": "", "max_parallel": 2, "instruction": "x", "takes": ["docs"],
                       "extra": "never kept"}])
    assert party.startswith("p-") and len(party) == 10
    (got,) = own_parties.list()
    assert got["id"] == party and got["name"] == "Lean web" and got["team"] == ["grunt", "tester", "reviewer"] and got["every"] == ["reviewer"]
    assert got["own"] == [{"slug": "docs-scribe", "name": "Docs scribe", "craft": "design", "model": "", "max_parallel": 2, "instruction": "x", "takes": ["docs"]}]
    assert got["uses"] == [] and got["saved"] and own_parties.path().name == "parties.json" and own_parties.path().parent == own_parties.settings.path().parent
    assert oct(own_parties.path().stat().st_mode & 0o777) == "0o600"
    assert json.loads(own_parties.path().read_text())["v"] == 1
    own_parties.drop(party)
    assert own_parties.list() == []
    with pytest.raises(own_parties.OwnPartyError, match="gone"):
        own_parties.drop(party)


def test_a_name_is_one_to_forty_characters_unique_whatever_its_case_and_replaced_only_when_asked():
    for bad in ("", "   ", "x" * 41):
        with pytest.raises(own_parties.OwnPartyError, match="1 to 40 characters"):
            lean(name=bad)
    first = lean()
    with pytest.raises(own_parties.OwnPartyError, match="You have a party named “Lean web”"):
        lean(name="lean  WEB")
    own_parties.used(first, "abc", "shop", "billing")
    again = lean(name="LEAN web", team=["grunt"], every=[], replace=True)
    assert again == first                                                                              # the same party, its uses kept
    (got,) = own_parties.list()
    assert got["team"] == ["grunt"] and got["name"] == "LEAN web" and len(got["uses"]) == 1


def test_at_most_twelve_parties_and_a_replace_of_the_twelfth_is_still_allowed():
    for n in range(12):
        lean(name=f"Party {n}")
    with pytest.raises(own_parties.OwnPartyError, match="You have 12 parties: remove one first"):
        lean(name="A thirteenth")
    lean(name="party 3", replace=True)
    assert len(own_parties.list()) == 12


def test_uses_are_kept_replaced_per_goal_marked_and_at_most_fifty():
    party = lean()
    own_parties.used(party, "aaaaaaaaaaaa", "shop", "billing")
    own_parties.used(party, "aaaaaaaaaaaa", "shop", "billing")                                       # the same goal again: one use
    own_parties.used(party, "bbbbbbbbbbbb", "blog", "billing")
    assert [(u["project"], u["goal"], u["met"]) for u in own_parties.list()[0]["uses"]] == [("aaaaaaaaaaaa", "billing", None), ("bbbbbbbbbbbb", "billing", None)]
    own_parties.mark("aaaaaaaaaaaa", "billing", True)
    own_parties.mark("aaaaaaaaaaaa", "billing", False)                                                # asked again: the last verdict
    own_parties.mark("aaaaaaaaaaaa", "billing", True)
    own_parties.mark("cccccccccccc", "billing", True)                                                 # no such use: nothing
    assert [u["met"] for u in own_parties.list()[0]["uses"]] == [True, None]
    for n in range(60):
        own_parties.used(party, "dddddddddddd", "docs", f"goal-{n}")
    uses = own_parties.list()[0]["uses"]
    assert len(uses) == 50 and uses[-1]["goal"] == "goal-59" and uses[0]["goal"] == "goal-10"       # the oldest dropped
    own_parties.used("p-00000000", "x", "x", "x")                                                     # an unknown party: nothing
    assert own_parties.project_key("/work/shop") == own_parties.project_key("/work/shop") and len(own_parties.project_key("/work/shop")) == 12


def test_a_file_of_another_shape_reads_as_none_and_is_kept_until_a_save():
    for text in ("not json", "[]", '{"v": 2, "parties": []}', '{"v": 1, "parties": "no"}'):
        own_parties.path().parent.mkdir(parents=True, exist_ok=True)
        own_parties.path().write_text(text)
        assert own_parties.list() == []
        own_parties.used("p-00000000", "x", "x", "x")
        own_parties.mark("x", "x", True)
        with pytest.raises(own_parties.OwnPartyError):
            own_parties.drop("p-00000000")
        assert own_parties.path().read_text() == text                                                  # not overwritten
    lean()
    assert len(own_parties.list()) == 1 and json.loads(own_parties.path().read_text())["v"] == 1       # a save writes it anew


# -- the commands --------------------------------------------------------------------------------------------------

def test_party_save_carries_an_agent_of_the_persons_own_and_refuses_a_taken_name_and_a_thirteenth(host):
    root = host.ideas.root()
    scribe = roles.save(host.ideas.state_dir, "Docs scribe", "warrior", 2, "You write docs.", None, ["docs"], "design")
    goal = host.command("ideas.goal_save", {"about": "Docs.", "craft": "design", "leader": "product-designer", "team": ["ui-kit", scribe, "accessibility-reviewer"],
                                            "every": ["accessibility-reviewer"]})["slug"]
    assert BoardPhone.allowed(host, "ideas.party_save", {}) and BoardPhone.allowed(host, "ideas.parties", {}) and BoardPhone.allowed(host, "ideas.party_drop", {})
    got = host.command("ideas.party_save", {"goal": goal, "name": "Design with docs"})
    (saved,) = own_parties.list()
    assert got == {"id": saved["id"]} and saved["craft"] == "design" and saved["leader"] == "product-designer"
    assert saved["team"] == ["ui-kit", scribe, "accessibility-reviewer"] and saved["every"] == ["accessibility-reviewer"]
    assert [o["slug"] for o in saved["own"]] == [scribe] and saved["own"][0]["instruction"] == "You write docs." and saved["own"][0]["takes"] == []   # the library's and built-in are not carried
    assert saved["own"][0]["craft"] == "design" and saved["own"][0]["model"] == "warrior" and saved["own"][0]["max_parallel"] == 2
    with pytest.raises(CommandError, match="You have a party named “Design with docs”"):
        host.command("ideas.party_save", {"goal": goal, "name": "design WITH docs"})
    assert host.command("ideas.party_save", {"goal": goal, "name": "design WITH docs", "replace": True})["id"] == saved["id"]
    with pytest.raises(CommandError, match="That goal is gone"):
        host.command("ideas.party_save", {"goal": "nope", "name": "x"})
    with pytest.raises(CommandError, match="name is missing"):
        host.command("ideas.party_save", {"goal": goal, "name": ""})
    for n in range(11):
        host.command("ideas.party_save", {"goal": goal, "name": f"Copy {n}"})
    with pytest.raises(CommandError, match="You have 12 parties: remove one first"):
        host.command("ideas.party_save", {"goal": goal, "name": "One more"})
    log = [r for r in event_log.read(host.repo_root) if r["event"] == "party_saved"]
    assert (log[0]["party"], log[0]["members"], log[0]["own"], log[0]["replaced"]) == (saved["id"], 4, 1, False) and log[1]["replaced"] is True
    assert host.command("ideas.party_drop", {"id": saved["id"]}) == {"ok": True}
    assert [r["party"] for r in event_log.read(host.repo_root) if r["event"] == "party_dropped"] == [saved["id"]]
    with pytest.raises(CommandError, match="That party is gone"):
        host.command("ideas.party_drop", {"id": saved["id"]})


def pick(host, party, **more):
    p = own_parties.get(party)
    return host.command("ideas.goal_save", {"about": "A goal.", "craft": p["craft"], "leader": p["leader"], "team": p["team"], "every": p["every"], "party": party, **more})


def test_a_party_picked_in_another_project_installs_its_own_agent_keeps_a_role_of_the_same_slug_and_says_so(host, tmp_path):
    root, state = host.ideas.root(), host.ideas.state_dir
    scribe = roles.save(state, "Docs scribe", "warrior", 2, "You write docs.", None, ["docs"], "design")
    goal = host.command("ideas.goal_save", {"about": "Docs.", "craft": "design", "leader": "product-designer", "team": ["ui-kit", scribe, "accessibility-reviewer"],
                                            "every": ["accessibility-reviewer"]})["slug"]
    party = host.command("ideas.party_save", {"goal": goal, "name": "Design with docs"})["id"]
    other = Orkboard(repo(tmp_path, "other"))
    assert roles.role(other.ideas.state_dir, scribe) is None
    got = pick(other, party)
    assert "notes" not in got and roles.role(other.ideas.state_dir, scribe)["instruction"] == "You write docs."      # made here, as the party says it
    assert roles.role(other.ideas.state_dir, "ui-kit") is not None                                          # the library's, as today
    g = next(t for t in other.command("ideas.board")["tracks"] if t["slug"] == got["slug"])
    assert g["party"] == party and g["team"] == ["ui-kit", scribe, "accessibility-reviewer"] and g["leader"]["slug"] == "product-designer"
    (use,) = own_parties.list()[0]["uses"]
    assert (use["project"], use["name"], use["goal"], use["met"]) == (own_parties.project_key(other.repo_root), "other", got["slug"], None)
    assert [r["party"] for r in event_log.read(other.repo_root) if r["event"] == "goal_saved"] == [party]
    # a third project already has an agent of that slug: its own stays as it is, and the answer says so
    third = Orkboard(repo(tmp_path, "third"))
    roles.save(third.ideas.state_dir, "Docs scribe", "laborer", 1, "Third's own words.", None, [], "design")
    got = pick(third, party)
    assert got["notes"] == ["Docs scribe is this project's already: kept as it is"]
    assert roles.role(third.ideas.state_dir, scribe)["instruction"] == "Third's own words." and roles.role(third.ideas.state_dir, scribe)["model"] == "laborer"
    assert len(own_parties.list()[0]["uses"]) == 2
    with pytest.raises(CommandError, match="That party is gone"):
        third.command("ideas.goal_save", {"about": "x", "party": "p-00000000"})


def test_only_the_party_s_id_sent_takes_the_party_as_it_was_saved(host):
    party = lean(name="Plain", team=["grunt", "reviewer"], every=["reviewer"], leader="architect")
    got = host.command("ideas.goal_save", {"about": "Only the id.", "party": party})
    assert goal_team.team_of(host.ideas.root(), got["slug"]) == ["grunt", "reviewer"] and goal_team.every_of(host.ideas.root(), got["slug"]) == ["reviewer"]
    assert goal_team.leader_of(host.ideas.root(), got["slug"]) == "architect" and goal_team.party_of(host.ideas.root(), got["slug"]) == party


def test_a_party_changed_afterwards_clears_the_goal_s_party_and_a_goal_never_changes_a_saved_party(host):
    party = lean()
    goal = pick(host, party)["slug"]
    root = host.ideas.root()
    assert goal_team.party_of(root, goal) == party
    host.command("ideas.goal_save", {"slug": goal, "title": "A corrected title"})                       # no party change: kept
    assert goal_team.party_of(root, goal) == party
    host.command("ideas.goal_save", {"slug": goal, "team": ["grunt"], "every": [], "leader": "architect"})
    assert goal_team.party_of(root, goal) == ""
    assert own_parties.get(party)["team"] == ["grunt", "tester", "reviewer"]                               # the saved party is as it was
    again = pick(host, party, slug=goal)["slug"]
    assert again == goal and goal_team.party_of(root, goal) == party
    host.command("ideas.goal_save", {"slug": goal, "leader": "product-manager"})                          # a leader alone changes it too
    assert goal_team.party_of(root, goal) == ""
    assert len(own_parties.list()[0]["uses"]) == 1                                                         # the same goal, one use


def test_accepting_a_goal_that_picked_a_party_marks_its_use_met(host, monkeypatch):
    from tests.test_goal_team import _wait
    party = lean(team=["grunt"], every=[], leader="product-manager", name="Product lean")
    verdict = [True]

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        if "accept the goal or" in prompt:
            return json.dumps({"met": verdict[0], "verdict": "ok", "metrics": [], "next": []}), 0.1, 10, "s"
        return json.dumps({"summary": "ok", "questions": [], "metrics": []}), 0.1, 10, "s"
    monkeypatch.setattr(jobs, "run_read", run_read)
    goal = pick(host, party)["slug"]
    _wait(host, goal, goal=True)
    plain = host.command("ideas.goal_save", {"about": "No saved party."})["slug"]                       # a goal with none marks nothing
    _wait(host, plain, goal=True)
    host.command("ideas.goal_accept", {"slug": plain})
    _wait(host, plain, goal=True)
    assert own_parties.list()[0]["uses"][0]["met"] is None
    for expected in (False, True):                                                                          # asked again: the last verdict
        verdict[0] = expected
        assert host.command("ideas.goal_accept", {"slug": goal}) == {"ok": True}
        for _ in range(300):
            time.sleep(0.02)
            if own_parties.list()[0]["uses"][0]["met"] is expected:
                break
        assert own_parties.list()[0]["uses"][0]["met"] is expected


def test_ideas_parties_counts_goals_projects_and_met(host, tmp_path):
    a, b = lean(), lean(name="Another", team=["grunt"], every=[])
    assert host.command("ideas.parties") == {"parties": [
        {"id": a, "name": "Lean web", "craft": "engineering", "leader": "architect", "team": ["grunt", "tester", "reviewer"], "every": ["reviewer"],
         "own": [], "goals": 0, "projects": 0, "met": 0, "saved": own_parties.list()[0]["saved"]},
        {"id": b, "name": "Another", "craft": "engineering", "leader": "architect", "team": ["grunt"], "every": [], "own": [], "goals": 0, "projects": 0, "met": 0,
         "saved": own_parties.list()[1]["saved"]}]}
    for project, goal, met in (("aaaaaaaaaaaa", "g1", True), ("aaaaaaaaaaaa", "g2", None), ("bbbbbbbbbbbb", "g3", False)):
        own_parties.used(a, project, "p", goal)
        if met is not None:
            own_parties.mark(project, goal, met)
    got = host.command("ideas.parties")["parties"][0]
    assert (got["goals"], got["projects"], got["met"]) == (3, 2, 1)
    scribe = roles.save(host.ideas.state_dir, "Scribe", "", 1, "", None, [], "design")
    own_parties.save("With scribe", "design", "product-designer", [scribe], [], [{"slug": scribe, "name": "Scribe"}])
    assert host.command("ideas.parties")["parties"][2]["own"] == ["Scribe"]
    json.dumps(host.command("ideas.parties"))
