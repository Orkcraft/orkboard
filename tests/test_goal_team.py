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


def test_the_library_is_four_of_each_craft_each_with_its_kinds_and_an_instruction_within_the_limit():
    by_craft = {c: [a for a in library.LIBRARY if a.craft == c] for c in roles.CRAFTS}
    assert {c: len(v) for c, v in by_craft.items()} == {c: 4 for c in roles.CRAFTS}
    assert [a.name for a in by_craft["design"]] == ["Product designer", "Design system designer", "Accessibility reviewer", "Artist"]
    assert len({a.id for a in library.LIBRARY}) == len(library.LIBRARY) and library.get("grunt").id in roles.BUILTIN
    for a in library.LIBRARY:
        assert a.tier in roles.TIERS and a.takes and set(a.takes) <= set(roles.TASK_KINDS), a.id
        assert len(a.instruction) <= roles.INSTRUCTION_CHARS and roles.for_prompt(a.instruction) == a.instruction, a.id
        assert a.id == "grunt" or a.instruction.endswith((".", "!", "?")), a.id
        said = f"{a.name} {a.line} {a.instruction}"
        assert not re.search(r"\borcs?\b|orchestrat", said, re.I), a.id          # CLAUDE.md: ork, orkestration
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
    assert len(got["library"]) == 16 and got["suggested"] == 2
    assert {"id": "artist", "craft": "design", "race": "elf", "tier": "laborer", "takes": ["art"]}.items() <= got["library"][7].items()


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
