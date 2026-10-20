"""Spec 43 F (docs/specs/43-party-measured.md §6, Tests → F): the person's own parties, kept beside the machine's settings,
saved from a goal and picked for a goal in any project."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.realm import event_log, goal_team, ideas, jobs, own_parties, roles


@pytest.fixture
def host(fake_repo) -> Orkboard:
    h = Orkboard(fake_repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


@pytest.fixture
def other(tmp_path) -> Orkboard:
    """A second project on the same machine."""
    repo = tmp_path / "second"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
    (repo / "README.md").write_text("# Second\n", encoding="utf-8")
    h = Orkboard(repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    """The keeper reads a goal in the background: stubbed."""
    monkeypatch.setattr(jobs, "run_read", lambda *a, **k: (json.dumps({"summary": "ok", "questions": [], "metrics": []}), 0.01, 10, "s"))


def _wait(host, slug):
    import time
    for _ in range(400):
        if not host.ideas.keeper.busy_goal(slug):
            return
        time.sleep(0.01)


def _scribe(host) -> None:
    roles.save(host.ideas.state_dir, "Docs scribe", "", 2, "Write plainly.", takes=["docs"], craft="design")


def _goal(host, **kw) -> str:
    got = host.command("ideas.goal_save", {"about": "Docs people read.", "craft": "design", "leader": "architect",
                                           "team": ["docs-scribe", "reviewer"], "every": ["reviewer"], **kw})["slug"]
    _wait(host, got)
    return got


def _events(host, name):
    return [e for e in event_log.read(Path(host.repo_root)) if e["event"] == name]


def test_save_keeps_the_twelve_refuses_a_taken_name_and_replaces_it():
    a = own_parties.save("Lean web", "engineering", "architect", ["grunt", "tester"], ["tester", "x"], [])
    assert a.startswith("p-") and own_parties.list()[0]["every"] == ["tester"]
    with pytest.raises(ValueError, match="You have a party named “Lean web”"):
        own_parties.save("lean WEB", "design", "taskmaster", [], [], [])
    assert own_parties.save("lean web", "design", "taskmaster", [], [], [], replace=True) == a
    assert [(p["id"], p["name"], p["craft"]) for p in own_parties.list()] == [(a, "lean web", "design")]
    for n in range(11):
        own_parties.save(f"Party {n}", "data", "taskmaster", [], [], [])
    with pytest.raises(ValueError, match="You have 12 parties: remove one first"):
        own_parties.save("One too many", "data", "taskmaster", [], [], [])
    own_parties.save("Lean web", "data", "taskmaster", [], [], [], replace=True)      # replacing is not adding
    for bad in ("", "x" * 41):
        with pytest.raises(ValueError):
            own_parties.save(bad, "data", "taskmaster", [], [], [])
    own_parties.drop(a)
    assert len(own_parties.list()) == 11
    with pytest.raises(ValueError, match="gone"):
        own_parties.drop(a)


def test_the_file_is_the_persons_own_mode_600_and_never_in_a_repository(fake_repo):
    own_parties.save("Lean web", "engineering", "taskmaster", [], [], [])
    p = own_parties.path()
    assert p.name == "parties.json" and p.parent == Path(os.environ["ORKCRAFT_SETTINGS_FILE"]).parent
    assert stat.S_IMODE(p.stat().st_mode) == 0o600 and json.loads(p.read_text())["v"] == 1
    assert not str(p).startswith(str(fake_repo))


def test_a_file_of_another_shape_reads_as_none_and_is_kept_until_a_save():
    p = own_parties.path()
    p.parent.mkdir(parents=True, exist_ok=True)
    for text in ("not json", json.dumps({"v": 2, "parties": []}), json.dumps([1, 2])):
        p.write_text(text)
        assert own_parties.list() == [] and p.read_text() == text
        own_parties.mark("x", "g", True)
        own_parties.used("p-1", "x", "n", "g")
        assert p.read_text() == text
    own_parties.save("Lean web", "engineering", "taskmaster", [], [], [])
    assert [x["name"] for x in own_parties.list()] == ["Lean web"]


def test_a_party_has_at_most_fifty_uses_the_oldest_dropped_and_a_goal_one_use():
    pid = own_parties.save("Lean web", "engineering", "taskmaster", [], [], [])
    for n in range(55):
        own_parties.used(pid, "aaaaaaaaaaaa", "app", f"goal-{n}")
    uses = own_parties.list()[0]["uses"]
    assert len(uses) == 50 and uses[0]["goal"] == "goal-5" and uses[-1]["goal"] == "goal-54"
    own_parties.mark("aaaaaaaaaaaa", "goal-54", True)
    own_parties.used(pid, "aaaaaaaaaaaa", "app", "goal-54")                      # asked again: a new use, not yet met
    uses = own_parties.list()[0]["uses"]
    assert len(uses) == 50 and uses[-1]["met"] is None and own_parties.counts(own_parties.list()[0]) == {"goals": 50, "projects": 1, "met": 0}


def test_party_save_carries_an_agent_of_the_persons_own_and_not_the_librarys(host):
    _scribe(host)
    goal = _goal(host)
    pid = host.command("ideas.party_save", {"goal": goal, "name": "  Docs   party "})["id"]
    p = own_parties.get(pid)
    assert p["name"] == "Docs party" and p["craft"] == "design" and p["leader"] == "architect"
    assert p["team"] == ["docs-scribe", "reviewer"] and p["every"] == ["reviewer"]
    assert p["own"] == [{"slug": "docs-scribe", "name": "Docs scribe", "craft": "design", "model": "", "max_parallel": 2,
                         "instruction": "Write plainly.", "takes": ["docs"]}]
    e = _events(host, "party_saved")[-1]
    assert (e["party"], e["members"], e["own"], e["replaced"], e["device"]) == (pid, 3, 1, False, "desktop")


def test_party_save_refuses_a_taken_name_unless_replace_and_a_thirteenth_and_a_gone_goal(host):
    goal = _goal(host, team=["reviewer"])
    host.command("ideas.party_save", {"goal": goal, "name": "Lean web"})
    with pytest.raises(CommandError, match="You have a party named “Lean web”"):
        host.command("ideas.party_save", {"goal": goal, "name": "lean web"})
    host.command("ideas.party_save", {"goal": goal, "name": "lean web", "replace": True})
    assert _events(host, "party_saved")[-1]["replaced"] is True and len(own_parties.list()) == 1
    for n in range(11):
        host.command("ideas.party_save", {"goal": goal, "name": f"P{n}"})
    with pytest.raises(CommandError, match="You have 12 parties: remove one first"):
        host.command("ideas.party_save", {"goal": goal, "name": "P99"})
    with pytest.raises(CommandError, match="That goal is gone"):
        host.command("ideas.party_save", {"goal": "nope", "name": "x"})


def test_a_party_used_in_another_project_installs_its_agent_keeps_the_one_it_has_and_says_so(host, other):
    _scribe(host)
    pid = host.command("ideas.party_save", {"goal": _goal(host), "name": "Docs party"})["id"]
    assert roles.role(other.ideas.state_dir, "docs-scribe") is None
    got = other.command("ideas.goal_save", {"about": "More docs.", "craft": "design", "leader": "architect",
                                            "team": ["docs-scribe", "reviewer"], "every": ["reviewer"], "party": pid})
    _wait(other, got["slug"])
    assert "notes" not in got
    r = roles.role(other.ideas.state_dir, "docs-scribe")
    assert (r["name"], r["craft"], r["instruction"], r["takes"], r["max_parallel"]) == ("Docs scribe", "design", "Write plainly.", ["docs"], 2)
    root = other.ideas.root()
    assert goal_team.party_of(root, got["slug"]) == pid and goal_team.team_of(root, got["slug"]) == ["docs-scribe", "reviewer"]
    use = own_parties.get(pid)["uses"][-1]
    assert use["project"] == own_parties.project_id(other.repo_root) and use["name"] == "second" and use["goal"] == got["slug"]
    assert _events(other, "goal_saved")[-1]["party"] == pid and _events(host, "goal_saved")[-1]["party"] == ""
    # a project with a role of that slug of its own keeps it, and the answer says so
    (Path(other.repo_root).parent / "third").mkdir()
    third = Orkboard(Path(other.repo_root).parent / "third")
    roles.save(third.ideas.state_dir, "Docs scribe", "", 5, "Its own words.", takes=["docs"], craft="data")
    again = third.command("ideas.goal_save", {"about": "Docs.", "craft": "design", "team": ["docs-scribe"], "party": pid})
    assert again["notes"] == ["Docs scribe is this project's already: kept as it is"]
    kept = roles.role(third.ideas.state_dir, "docs-scribe")
    assert kept["instruction"] == "Its own words." and kept["craft"] == "data" and kept["max_parallel"] == 5
    assert len({u["project"] for u in own_parties.get(pid)["uses"]}) == 2
    with pytest.raises(CommandError, match="That party is gone"):
        other.command("ideas.goal_save", {"about": "x", "party": "p-nothere"})


def test_a_later_party_change_clears_the_party_and_the_same_party_saved_again_keeps_it(host):
    pid = own_parties.save("Lean web", "engineering", "taskmaster", ["reviewer"], [], [])
    slug = host.command("ideas.goal_save", {"about": "Ship it.", "leader": "taskmaster", "team": ["reviewer"], "party": pid})["slug"]
    _wait(host, slug)
    root = host.ideas.root()
    assert goal_team.party_of(root, slug) == pid
    host.command("ideas.goal_save", {"slug": slug, "team": ["reviewer"], "every": [], "leader": "taskmaster"})
    assert goal_team.party_of(root, slug) == pid                                 # nothing changed
    host.command("ideas.goal_save", {"slug": slug, "priority": "high"})
    assert goal_team.party_of(root, slug) == pid                                 # no party sent
    host.command("ideas.goal_save", {"slug": slug, "team": ["reviewer"], "every": ["reviewer"]})
    assert goal_team.party_of(root, slug) == ""
    assert [t for t in host.command("ideas.board")["tracks"] if t["slug"] == slug][0]["party"] == ""
    assert own_parties.get(pid)["team"] == ["reviewer"] and own_parties.get(pid)["every"] == []     # a goal never changes a saved party
    host.command("ideas.goal_save", {"slug": slug, "team": [], "leader": "architect", "party": pid})
    assert goal_team.party_of(root, slug) == pid
    host.command("ideas.goal_save", {"slug": slug, "leader": "product-manager"})
    assert goal_team.party_of(root, slug) == ""


def test_accepting_the_goal_marks_its_use_met_and_asked_again_the_last_verdict(host, monkeypatch):
    pid = own_parties.save("Lean web", "engineering", "taskmaster", [], [], [])
    slug = host.command("ideas.goal_save", {"about": "Ship it.", "team": [], "party": pid})["slug"]
    _wait(host, slug)
    plain = host.command("ideas.goal_save", {"about": "No party."})["slug"]
    _wait(host, plain)
    k, project = host.ideas.keeper, own_parties.project_id(host.repo_root)
    for met in (True, False, True):
        monkeypatch.setattr(k, "ask", lambda *a, **kw: (json.dumps({"met": met, "verdict": "v", "metrics": [], "next": []}), 0, 0, ""))
        k.accept_one(slug)
        k.accept_one(plain)
        assert own_parties.get(pid)["uses"][0]["met"] is met
    assert own_parties.counts(own_parties.get(pid))["met"] == 1


def test_parties_counts_and_drop(host, other):
    pid = own_parties.save("Lean web", "engineering", "architect", ["grunt"], [], [{"slug": "x", "name": "Xer", "craft": "data", "model": "",
                                                                                  "max_parallel": 1, "instruction": "", "takes": []}])
    assert host.command("ideas.parties", {})["parties"] == [{"id": pid, "name": "Lean web", "craft": "engineering", "leader": "architect",
        "team": ["grunt"], "every": [], "own": ["Xer"], "goals": 0, "projects": 0, "met": 0, "saved": own_parties.get(pid)["saved"]}]
    for h in (host, other, other):
        own_parties.used(pid, own_parties.project_id(h.repo_root), "p", f"g{id(h) % 7}-{len(own_parties.get(pid)['uses'])}")
    own_parties.mark(own_parties.project_id(other.repo_root), own_parties.get(pid)["uses"][-1]["goal"], True)
    got = host.command("ideas.parties", {})["parties"][0]
    assert (got["goals"], got["projects"], got["met"]) == (3, 2, 1)
    assert BoardPhone.allowed(Orkboard(), "ideas.parties", {}) and BoardPhone.allowed(Orkboard(), "ideas.party_save", {})
    assert host.command("ideas.party_drop", {"id": pid}) == {"ok": True}
    assert host.command("ideas.parties", {})["parties"] == [] and _events(host, "party_dropped")[-1]["party"] == pid
    with pytest.raises(CommandError, match="That party is gone"):
        host.command("ideas.party_drop", {"id": pid})
