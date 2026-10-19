"""A goal's team from the library (decisions §53; realm/library.py, realm/goal_team.py): the library's agents and their
instructions, a team kept on the goal and its agents made roles of the project, each task tagged by its kind of work and
given to the one of the team who does that kind, Grunt for the rest."""
from __future__ import annotations

import json
import re
import sys

import pytest

from orkboard.gui.board_host import CommandError, Orkboard
from orkboard.realm import goal_team, ideas, jobs, library, roles


@pytest.fixture
def host(fake_repo) -> Orkboard:
    h = Orkboard(fake_repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


def _wait(host, slug="", goal=False):
    import time
    k = host.ideas.keeper
    for _ in range(400):
        if not (k.busy_goal(slug) if goal else k.busy(slug)):
            return
        time.sleep(0.01)


def test_the_library_is_makers_and_checkers_of_each_craft_each_with_its_kinds_and_an_instruction_within_the_limit():
    by_craft = {c: [a for a in library.LIBRARY if a.craft == c] for c in roles.CRAFTS}
    assert {c: len(v) for c, v in by_craft.items()} == {"engineering": 5, "design": 4, "data": 5, "marketing": 5}
    checkers = {c: [a.name for a in v if a.check] for c, v in by_craft.items()}
    assert checkers == {"engineering": ["Tester", "Security reviewer", "Reviewer"], "design": ["Design system designer", "Accessibility reviewer"],
                        "data": ["Analyst", "Data reviewer"], "marketing": ["Editor", "SEO"]}   # each craft has its checks
    assert [a.name for a in by_craft["design"]] == ["Product designer", "Design system designer", "Accessibility reviewer", "Artist"]
    assert len({a.id for a in library.LIBRARY}) == len(library.LIBRARY) and library.get("grunt").id in roles.BUILTIN
    for a in library.LIBRARY:
        assert a.tier in roles.TIERS and a.takes and set(a.takes) <= set(roles.TASK_KINDS), a.id
        assert len(a.instruction) <= roles.INSTRUCTION_CHARS and roles.for_prompt(a.instruction) == a.instruction, a.id
        assert a.id == "grunt" or a.instruction.endswith((".", "!", "?")), a.id
        said = f"{a.name} {a.line} {a.instruction}"
        assert not re.search(r"\borcs?\b|orchestrat", said, re.I), a.id          # CLAUDE.md: ork, orkestration
        if a.check:
            assert a.check.applies.startswith("when ") and a.check.done[0].isupper() and a.check.task.endswith("."), a.id
    every = {k for a in library.LIBRARY for k in a.takes}
    assert every == set(roles.TASK_KINDS) - {"docs", "research"}                     # docs and research stay the project's (Grunt)
    assert set(roles.KIND_LABELS) == set(roles.KIND_LINES) == set(roles.TASK_KINDS)


def test_a_team_routes_each_kind_to_its_specialist_and_the_rest_to_grunt(tmp_path):
    library.install(tmp_path, ["grunt", "product-designer", "accessibility-reviewer", "analyst"])
    team = ["grunt", "product-designer", "accessibility-reviewer", "analyst"]
    assert roles.role_for(tmp_path, "design", team)["slug"] == "product-designer"    # Grunt first in the team: still the designer's
    assert roles.role_for(tmp_path, "a11y", team)["slug"] == "accessibility-reviewer"
    assert roles.role_for(tmp_path, "metrics", team)["slug"] == "analyst"
    assert roles.role_for(tmp_path, "code", team)["slug"] == "grunt"
    assert roles.role_for(tmp_path, "seo", team)["slug"] == "grunt"                  # no one of the team does it
    assert roles.role_for(tmp_path, "design")["slug"] == "grunt"                     # no team: the project's, as before
    assert set(roles.kinds(tmp_path).values()) == {"grunt"}                          # installing gives the project no type


def test_goal_save_with_a_team_makes_its_agents_keeps_the_team_and_never_overwrites_an_agent(host):
    slug = host.command("ideas.goal_save", {"about": "A landing page that sells.", "craft": "design",
                                            "team": ["product-designer", "analyst", "taskmaster"]})["slug"]
    _wait(host, slug, goal=True)
    g = next(t for t in host.command("ideas.board")["tracks"] if t["slug"] == slug)
    assert g["team"] == ["product-designer", "analyst"]                              # the Taskmaster plans for every team
    pd = roles.role(host.ideas.state_dir, "product-designer")
    assert pd["name"] == "Product designer" and pd["craft"] == "design" and pd["model"] == "elder" and pd["takes"] == ["design"]
    assert pd["instruction"] == library.get("product-designer").instruction
    host.command("ideas.role_save", {"slug": "product-designer", "name": "Product designer", "model": "", "max_parallel": 1,
                                     "instruction": "Mine now."})
    host.command("ideas.goal_save", {"about": "Another page.", "craft": "design", "team": ["product-designer"]})
    assert roles.role(host.ideas.state_dir, "product-designer")["instruction"] == "Mine now."   # the person's edit stays
    assert roles.role(host.ideas.state_dir, "product-designer")["takes"] == ["design"]
    with pytest.raises(CommandError, match="No agent 'wizard'"):
        host.command("ideas.goal_save", {"about": "x", "team": ["wizard"]})
    with pytest.raises(CommandError, match="at most 5"):
        host.command("ideas.goal_save", {"about": "x", "team": [a.id for a in library.LIBRARY[:6]]})
    got = host.command("ideas.roles")
    assert len(got["library"]) == len(library.LIBRARY) == 19 and got["suggested"] == 2
    artist = next(a for a in got["library"] if a["id"] == "artist")
    assert {"craft": "design", "race": "elf", "tier": "laborer", "takes": ["art"], "check": None}.items() <= artist.items()
    a11y = next(a for a in got["library"] if a["id"] == "accessibility-reviewer")
    assert a11y["check"]["applies"] == "when the idea changes what people see or use"


def test_the_plan_tags_each_task_and_gives_it_to_the_team_member_who_does_that_kind(host, monkeypatch):
    seen = []

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        seen.append(prompt)
        if "turn it into" in prompt:
            return json.dumps({"tasks": [
                {"id": "a", "title": "Screens", "brief": "Draw the flow", "kind": "design", "tier": "warrior"},
                {"id": "b", "title": "Contrast", "brief": "Check it", "kind": "a11y", "tier": "laborer", "after": ["a"]},
                {"id": "c", "title": "Wire it", "brief": "Code it", "kind": "code", "tier": "warrior", "after": ["a"]},
                {"id": "d", "title": "Odd", "brief": "x", "kind": "spells", "tier": "warrior"}]}), 0.1, 10, "s"
        if "saved a goal" in prompt:
            return json.dumps({"summary": "ok", "questions": [], "metrics": []}), 0.1, 10, "s"
        return json.dumps({"gist": "A page.", "why": "", "size": "S", "priority": "normal", "before": "", "questions": []}), 0.1, 10, "s"

    monkeypatch.setattr(jobs, "run_read", run_read)
    host.command("ideas.board_set", {"autostart": False})
    goal = host.command("ideas.goal_save", {"about": "A landing page.", "craft": "design",
                                            "team": ["grunt", "product-designer", "accessibility-reviewer"]})["slug"]
    _wait(host, goal, goal=True)
    slug = host.command("ideas.add", {"text": "The hero section", "track": goal, "night": True})["slug"]
    host.command("ideas.read_now", {"slug": slug})
    _wait(host, slug)
    host.command("ideas.plan", {"slug": slug})
    _wait(host, slug)
    prompt = next(p for p in seen if "turn it into" in p)
    assert '"uikit" (components and tokens of the design system)' in prompt
    assert "The goal's team, by the tags each does: Grunt (" in prompt and "Product designer (design)" in prompt
    assert "Accessibility reviewer (a11y)" in prompt
    tasks = host.command("ideas.page", {"slug": slug})["plan"]["tasks"]
    assert [(t["kind"], t["role"]) for t in tasks] == [("design", "product-designer"), ("a11y", "accessibility-reviewer"),
                                                       ("code", "grunt"), ("code", "grunt")]   # an unknown tag is code
    assert [t["head"]["race"] for t in tasks] == ["elf", "elf", "peon", "peon"]
    from orkboard.core.idea_runner import IdeaRunner
    assert IdeaRunner._role(host.ideas.keeper, tasks[0])["slug"] == "product-designer"
    assert goal_team.for_idea(host.ideas.root(), slug) == ["grunt", "product-designer", "accessibility-reviewer"]
    assert ideas.state(host.ideas.state_dir, slug)["state"] == "plan"


def test_the_team_s_checks_go_in_the_spec_and_the_plan_where_they_apply_and_every_idea_s_always(host, monkeypatch):
    """A team sets how deep an idea is worked (realm/idea_checks.py): each checker's check, where it applies, adds its
    Done when line and its task after the work; where it does not, the spec says why; one set to every idea applies always."""
    seen = []

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        seen.append(prompt)
        if "turn it into" in prompt:
            return json.dumps({"tasks": [{"id": "a", "title": "Query", "brief": "Write it", "kind": "query", "tier": "laborer"},
                                         {"id": "b", "title": "Wire it", "brief": "Code it", "kind": "code", "tier": "warrior"}]}), 0.1, 10, "s"
        if "saved a goal" in prompt:
            return json.dumps({"summary": "ok", "questions": [], "metrics": []}), 0.1, 10, "s"
        return json.dumps({"gist": "A weekly report.", "why": "", "size": "S", "priority": "normal", "before": "", "questions": [],
                           "done_when": ["The report shows last week"],
                           "checks": [{"by": "accessibility-reviewer", "applies": False, "why": "It changes no screen"},
                                      {"by": "reviewer", "applies": False, "why": "small"}]}), 0.1, 10, "s"

    monkeypatch.setattr(jobs, "run_read", run_read)
    host.command("ideas.board_set", {"autostart": False})
    goal = host.command("ideas.goal_save", {"about": "Weekly numbers.", "craft": "data", "every": ["reviewer", "seo"],
                                            "team": ["grunt", "accessibility-reviewer", "reviewer", "sql"]})["slug"]
    _wait(host, goal, goal=True)
    assert next(t for t in host.command("ideas.board")["tracks"] if t["slug"] == goal)["every"] == ["reviewer"]   # only the team's
    slug = host.command("ideas.add", {"text": "A weekly report", "track": goal, "night": True})["slug"]
    host.command("ideas.read_now", {"slug": slug})
    _wait(host, slug)
    draft = next(p for p in seen if "write its spec" in p)
    assert "accessibility-reviewer (Accessibility reviewer): applies when the idea changes what people see or use" in draft
    assert "reviewer (Reviewer): applies to every idea" in draft and '"checks": [{"by"' in draft
    page = host.command("ideas.page", {"slug": slug})
    done = next(s["text"] for s in page["sections"] if s["name"] == "Done when")
    assert "The report shows last week" in done and "The change was reviewed and no blocking finding is left" in done   # every idea: always
    assert "accessibility check" not in done
    assert [(c["by"], c["applies"], c["why"]) for c in page["checks"]] == [
        ("accessibility-reviewer", False, "It changes no screen"), ("reviewer", True, "")]
    host.command("ideas.plan", {"slug": slug})
    _wait(host, slug)
    plan_prompt = next(p for p in seen if "turn it into" in p)
    assert 'Reviewer: a task tagged "review", after the work it checks' in plan_prompt and "Accessibility reviewer: a task" not in plan_prompt
    page = host.command("ideas.page", {"slug": slug})
    tasks = page["plan"]["tasks"]
    assert [(t["id"], t["title"], t["kind"], t["role"], t["after"]) for t in tasks] == [
        ("k1", "Query", "query", "sql", []), ("k2", "Wire it", "code", "grunt", []),
        ("k3", "Check: Reviewer", "review", "reviewer", ["k1", "k2"])]                  # the plan left it out: added, after the work
    assert [(c["by"], c["state"]) for c in page["checks"]] == [("accessibility-reviewer", ""), ("reviewer", "waiting")]


def test_a_check_s_status_is_its_task_s_passed_once_merged_and_none_where_it_does_not_apply(tmp_path):
    from orkboard.realm import idea_checks
    checks = idea_checks.of_team(tmp_path, ["grunt", "reviewer", "seo", "tester"], every=["tester"])
    assert [c["by"] for c in checks] == ["reviewer", "seo", "tester"] and [c["every"] for c in checks] == [False, False, True]
    kept = idea_checks.kept([{"by": "seo", "applies": False, "why": "No page"}, {"by": "tester", "applies": False}], checks)
    assert kept == [{"by": "reviewer", "applies": True, "why": ""}, {"by": "seo", "applies": False, "why": "No page"},
                    {"by": "tester", "applies": True, "why": ""}]                    # left out: applies; every idea: always
    tasks = [{"id": "k1", "kind": "code", "state": "merged"}, {"id": "k2", "kind": "review", "state": "merged"},
             {"id": "k3", "kind": "tests", "state": "running"}]
    assert [(s["by"], s["state"]) for s in idea_checks.status(kept, checks, tasks)] == [
        ("reviewer", "passed"), ("seo", ""), ("tester", "running")]
