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


def test_the_library_is_leaders_builders_and_checkers_each_with_its_kinds_and_an_instruction_within_the_limit():
    by_band = {b: [a.name for a in library.LIBRARY if a.band == b] for b in ("lead", "build", "check")}
    assert by_band["lead"] == ["Taskmaster", "Product manager", "Architect", "Product designer", "Game designer", "Analyst", "Growth",
                               "Investor", "Release manager"]                             # Ideation's (spec 65 §1), Release's (spec 67 §1)
    assert by_band["check"] == ["Security reviewer", "Reviewer", "Accessibility reviewer", "Playtester", "Data reviewer", "Editor",
                                "Skeptic", "Release checker"]
    assert all((a.check is not None) == (a.band == "check" and not a.pitch) for a in library.LIBRARY)   # a check is a checker's; the Skeptic checks pitches only
    assert library.get("product-manager").craft == "product" and roles.RACES["product"] == "lich"   # undead, for now
    for craft, (lead, builds, checks) in library.PARTIES.items():                         # a craft's party fits its seats
        assert library.get(lead).band == "lead" and all(library.get(s).band == "build" for s in builds), craft
        assert all(library.get(s).band == "check" for s in checks) and len(builds) <= 3 and len(checks) <= 2, craft
        assert not goal_team.seats([*builds, *checks], lead), craft
    assert len({a.id for a in library.LIBRARY}) == len(library.LIBRARY) and library.get("grunt").id in roles.BUILTIN
    for a in library.LIBRARY:
        assert a.tier in roles.TIERS and a.takes and (set(a.takes) <= set(roles.TASK_KINDS)) != a.pitch, a.id   # a pitch agent takes a pitch kind only
        assert len(a.instruction) <= roles.INSTRUCTION_CHARS and roles.for_prompt(a.instruction) == a.instruction, a.id
        assert a.id in roles.BUILTIN or a.instruction.endswith((".", "!", "?")), a.id      # the built-in two keep their own
        said = f"{a.name} {a.line} {a.instruction}"
        assert not re.search(r"\borcs?\b|orchestrat", said, re.I), a.id          # CLAUDE.md: ork, orkestration
        if a.check:
            assert a.check.applies.startswith("when ") and a.check.done[0].isupper() and a.check.task.endswith("."), a.id
    every = {k for a in library.LIBRARY if not a.pitch for k in a.takes}
    assert every == set(roles.TASK_KINDS) - {"docs"}                                 # docs stay the project's (Grunt)
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
    slug = host.command("ideas.goal_save", {"about": "A landing page that sells.", "craft": "design", "leader": "product-designer",
                                            "team": ["ui-kit", "accessibility-reviewer", "taskmaster"]})["slug"]
    _wait(host, slug, goal=True)
    g = next(t for t in host.command("ideas.board")["tracks"] if t["slug"] == slug)
    assert g["team"] == ["ui-kit", "accessibility-reviewer"] and g["leader"]["slug"] == "product-designer"   # the leader leads, not in the team
    assert g["leader"]["head"]["race"] == "elf" and g["verdict"] is None
    pd = roles.role(host.ideas.state_dir, "product-designer")
    assert pd["name"] == "Product designer" and pd["craft"] == "design" and pd["model"] == "elder" and pd["takes"] == ["design"]
    assert pd["instruction"] == library.get("product-designer").instruction
    host.command("ideas.role_save", {"slug": "product-designer", "name": "Product designer", "model": "", "max_parallel": 1,
                                     "instruction": "Mine now."})
    host.command("ideas.goal_save", {"about": "Another page.", "craft": "design", "leader": "product-designer", "team": []})
    assert roles.role(host.ideas.state_dir, "product-designer")["instruction"] == "Mine now."   # the person's edit stays
    assert roles.role(host.ideas.state_dir, "product-designer")["takes"] == ["design"]
    with pytest.raises(CommandError, match="No agent 'wizard'"):
        host.command("ideas.goal_save", {"about": "x", "team": ["wizard"]})
    with pytest.raises(CommandError, match="at most 3 builders"):
        host.command("ideas.goal_save", {"about": "x", "team": ["grunt", "tester", "sql", "seo"]})
    with pytest.raises(CommandError, match="at most 2 checkers"):
        host.command("ideas.goal_save", {"about": "x", "team": ["reviewer", "editor", "data-reviewer"]})
    with pytest.raises(CommandError, match="does not lead"):
        host.command("ideas.goal_save", {"about": "x", "leader": "grunt", "team": []})
    with pytest.raises(CommandError, match="A leader leads"):
        host.command("ideas.goal_save", {"about": "x", "team": ["architect"]})
    got = host.command("ideas.roles")
    assert len(got["library"]) == len(library.LIBRARY) == 36 and got["suggested"] == 2              # 26, Ideation's six (spec 65) and Release's four (spec 67)
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
    goal = host.command("ideas.goal_save", {"about": "A landing page.", "craft": "design", "leader": "product-designer",
                                            "team": ["grunt", "accessibility-reviewer"]})["slug"]
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
    assert goal_team.for_idea(host.ideas.root(), slug) == ["grunt", "accessibility-reviewer"]
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
    checks = idea_checks.of_team(tmp_path, ["grunt", "reviewer", "editor", "security-reviewer"], every=["security-reviewer"])
    assert [c["by"] for c in checks] == ["reviewer", "editor", "security-reviewer"] and [c["every"] for c in checks] == [False, False, True]
    kept = idea_checks.kept([{"by": "editor", "applies": False, "why": "No text"}, {"by": "security-reviewer", "applies": False}], checks)
    assert kept == [{"by": "reviewer", "applies": True, "why": ""}, {"by": "editor", "applies": False, "why": "No text"},
                    {"by": "security-reviewer", "applies": True, "why": ""}]         # left out: applies; every idea: always
    tasks = [{"id": "k1", "kind": "code", "state": "merged"}, {"id": "k2", "kind": "review", "state": "merged"},
             {"id": "k3", "kind": "security", "state": "running"}]
    assert [(s["by"], s["state"]) for s in idea_checks.status(kept, checks, tasks)] == [
        ("reviewer", "passed"), ("editor", ""), ("security-reviewer", "running")]


def test_the_map_s_goal_carries_its_team_and_its_ideas_their_checks(host):
    from orkboard.realm import idea_checks
    goal = host.command("ideas.goal_save", {"about": "A settings screen.", "craft": "design", "every": ["reviewer"],
                                            "leader": "product-designer", "team": ["accessibility-reviewer", "reviewer"]})["slug"]
    _wait(host, goal, goal=True)
    slug = host.command("ideas.add", {"text": "Dark mode", "track": goal, "night": True})["slug"]
    ideas.set_meta(host.ideas.root(), slug, checks=json.dumps([{"by": "accessibility-reviewer", "applies": False, "why": "No screen"}]))
    m = host.command("ideas.map", {})
    g = next(x for x in m["goals"] if x["slug"] == goal)
    assert (g["craft"], g["race"]) == ("design", "elf")
    assert [(t["slug"], t["name"], t["head"]["race"], t["checks"], t["every"]) for t in g["team"]] == [
        ("accessibility-reviewer", "Accessibility reviewer", "elf", True, False), ("reviewer", "Reviewer", "peon", True, True)]
    node = next(n for n in m["nodes"] if n["slug"] == slug)
    assert [(c["by"], c["applies"], c["state"]) for c in node["checks"]] == [("accessibility-reviewer", False, ""), ("reviewer", True, "")]
    assert idea_checks.DONE == ("merged",)


def test_a_goal_s_steps_run_as_its_leader_its_voice_and_model_and_the_taskmaster_leads_by_default(host, monkeypatch):
    from orkboard.realm import harnesses
    seen = []

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        seen.append({"prompt": prompt, "model": model})
        if "saved a goal" in prompt:
            return json.dumps({"summary": "ok", "questions": [], "metrics": [{"name": "weekly reports", "how": "count"}]}), 0.1, 10, "s"
        return json.dumps({"gist": "A report.", "why": "", "size": "S", "priority": "normal", "before": "", "questions": []}), 0.1, 10, "s"

    monkeypatch.setattr(jobs, "run_read", run_read)
    led = host.command("ideas.goal_save", {"about": "Weekly numbers.", "craft": "data", "leader": "analyst", "team": ["sql"]})["slug"]
    _wait(host, led, goal=True)
    assert seen[-1]["prompt"].startswith("You are Analyst, the leader of this goal's party")
    assert library.get("analyst").instruction in seen[-1]["prompt"]
    assert seen[-1]["model"] == harnesses.get("claude").pick("warrior")                  # the Analyst's tier, not the Taskmaster's
    idea = host.command("ideas.add", {"text": "A weekly report", "track": led, "night": True})["slug"]
    host.command("ideas.read_now", {"slug": idea})
    _wait(host, idea)
    draft = next(c["prompt"] for c in seen if "write its spec" in c["prompt"])
    assert draft.startswith("You are Analyst")                                         # the idea's draft: its goal's leader's
    plain = host.command("ideas.goal_save", {"about": "Faster tests."})["slug"]          # no leader picked: the Taskmaster's
    _wait(host, plain, goal=True)
    assert seen[-1]["prompt"].startswith("You are the keeper") and seen[-1]["model"] == harnesses.get("claude").pick("elder")
    g = next(t for t in host.command("ideas.board")["tracks"] if t["slug"] == plain)
    assert g["leader"]["slug"] == "taskmaster" and g["leader"]["name"] == "Taskmaster"
    # spec 41 §8: the Taskmaster's own instruction goes before each step it runs (it went nowhere before)
    host.command("ideas.role_save", {"slug": "taskmaster", "name": "Taskmaster", "model": "elder", "max_parallel": 1,
                                     "instruction": "Answer in Russian."})
    again = host.command("ideas.goal_save", {"about": "Fewer flaky tests."})["slug"]
    _wait(host, again, goal=True)
    assert seen[-1]["prompt"].startswith("Answer in Russian.\n\nYou are the keeper")


def test_a_party_is_never_accepted_by_itself_but_the_person_can_still_ask_its_leader(host, monkeypatch):
    """Spec 50 §2.2: nothing accepts a party when its goals are all done (no model call); `ideas.goal_accept` stays, for a party
    with metrics written before, and its verdict is kept as history."""
    seen = []

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        seen.append(prompt)
        if "accept the goal or" in prompt:
            return json.dumps({"met": False, "verdict": "Reports ship, but nobody reads them yet.",
                               "metrics": [{"name": "weekly reports", "status": "not met", "why": "0 opened"}, {"name": "x", "status": "odd"}],
                               "next": ["Mail the report every Monday"]}), 0.1, 10, "s"
        return json.dumps({"summary": "ok", "questions": []}), 0.1, 10, "s"

    monkeypatch.setattr(jobs, "run_read", run_read)
    goal = host.command("ideas.goal_save", {"about": "Weekly numbers.", "craft": "product", "leader": "product-manager", "team": [],
                                            "metrics": [{"name": "weekly reports", "target": "10 opened"}]})["slug"]
    _wait(host, goal, goal=True)
    a = ideas.add_idea(host.ideas.root(), "A weekly report", goal, host.ideas.state_dir)
    ideas.save_state(host.ideas.state_dir, a, state="working")
    host.ideas._state_event(a)                                                          # seen working …
    ideas.save_state(host.ideas.state_dir, a, state="done")
    host.ideas._state_event(a)                                                          # … then done: the party's last goal
    _wait(host, goal, goal=True)
    assert not any("accept the goal or" in p for p in seen)                             # no model call: nothing accepts a party by itself
    g = next(t for t in host.command("ideas.board")["tracks"] if t["slug"] == goal)
    assert g["verdict"] is None
    assert host.command("ideas.goal_accept", {"slug": goal}) == {"ok": True}           # asked, from the party (a party with metrics of before)
    _wait(host, goal, goal=True)
    prompt = next(p for p in seen if "accept the goal or" in p)
    assert prompt.startswith("You are Product manager") and "weekly reports → 10 opened" in prompt and "A weekly report" in prompt
    g = next(t for t in host.command("ideas.board")["tracks"] if t["slug"] == goal)
    v = g["verdict"]
    assert v["met"] is False and v["by"] == "Product manager" and v["next"] == ["Mail the report every Monday"]
    assert v["metrics"] == [{"name": "weekly reports", "status": "not met", "why": "0 opened"}, {"name": "x", "status": "unknown", "why": ""}]
    from orkboard.realm import event_log
    from pathlib import Path
    assert [e for e in event_log.read(Path(host.repo_root)) if e["event"] == "goal_accepted"][-1]["met"] is False
    assert host.command("ideas.goal_accept", {"slug": goal}) == {"ok": True}           # asked again
    _wait(host, goal, goal=True)
    assert sum(1 for p in seen if "accept the goal or" in p) == 2


def test_a_check_skipped_before_the_plan_is_left_out_and_after_it_its_task_is_taken_out_before_it_runs(host):
    from orkboard.realm import idea_checks
    slug = host.command("ideas.goal_save", {"about": "Sync that holds.", "craft": "engineering", "leader": "architect",
                                            "team": ["grunt", "reviewer"]})["slug"]
    idea = host.command("ideas.add", {"text": "Retry a lost sync", "track": slug, "priority": "low"})["slug"]
    root, state = host.ideas.root(), host.ideas.state_dir
    keeper = host.ideas.keeper
    host.command("ideas.check_skip", {"slug": idea, "by": "reviewer"})                       # before a plan: left out of it
    kept = keeper.idea_checks(root, idea)
    assert kept == [{"by": "reviewer", "applies": True, "why": "", "skipped": True}]
    assert idea_checks.plan_lines(kept, keeper.team_checks(root, idea)) == ""
    tasks = [{"id": "k1", "title": "Retry", "kind": "code", "after": []}]
    assert idea_checks.with_check_tasks(tasks, kept, keeper.team_checks(root, idea), lambda *a: {"id": a[0], "kind": a[3]}) == tasks
    assert "reviewer" not in keeper.draft_prompt(root, idea)                                  # not asked of in the draft either
    host.command("ideas.check_skip", {"slug": idea, "by": "reviewer", "skip": False})         # taken again, before a plan
    assert not keeper.idea_checks(root, idea)[0].get("skipped")

    ideas.save_plan(state, idea, {"idea": idea, "todos": [], "tasks": [                       # a plan with its check task, after the work
        {"id": "k1", "title": "Retry", "kind": "code", "state": "merged", "after": []},
        {"id": "k2", "title": "Check: Reviewer", "kind": "review", "state": "waiting", "after": ["k1"]},
        {"id": "k3", "title": "Notes", "kind": "docs", "state": "waiting", "after": ["k2"]}]})
    host.command("ideas.check_skip", {"slug": idea, "by": "reviewer"})
    plan = ideas.plan(state, idea)
    assert [t["id"] for t in plan["tasks"]] == ["k1", "k3"] and plan["tasks"][1]["after"] == []      # what waited for it does not
    st = idea_checks.status(keeper.idea_checks(root, idea), keeper.team_checks(root, idea), plan["tasks"])
    assert st[0]["skipped"] and st[0]["state"] == "" and st[0]["task"] == ""
    with pytest.raises(CommandError, match="comes back with the goal's next plan"):
        host.command("ideas.check_skip", {"slug": idea, "by": "reviewer", "skip": False})
    with pytest.raises(CommandError, match="no such check"):
        host.command("ideas.check_skip", {"slug": idea, "by": "editor"})
    lines = [json.loads(x) for x in (fake_repo_events(host)).read_text().splitlines()]
    skipped = [x for x in lines if x.get("event") == "check_skipped"]
    assert [(x["by"], x["skipped"], x["task"]) for x in skipped] == [("reviewer", True, ""), ("reviewer", False, ""), ("reviewer", True, "k2")]


def test_a_check_under_way_cannot_be_skipped(host):
    slug = host.command("ideas.goal_save", {"about": "x", "craft": "engineering", "leader": "architect", "team": ["reviewer"]})["slug"]
    idea = host.command("ideas.add", {"text": "y", "track": slug, "priority": "low"})["slug"]
    ideas.save_plan(host.ideas.state_dir, idea, {"idea": idea, "todos": [], "tasks": [
        {"id": "k1", "title": "Check: Reviewer", "kind": "review", "state": "review", "after": []}]})
    with pytest.raises(CommandError, match="under way"):
        host.command("ideas.check_skip", {"slug": idea, "by": "reviewer"})


def fake_repo_events(host):
    from pathlib import Path
    from orkboard.realm import event_log
    return event_log.path(Path(host.repo_root))


def test_a_goals_party_saved_alone_keeps_its_words_and_is_not_read_again(host, monkeypatch):
    # spec 41 §7: the phone changes a goal's team from its screen; nothing else is sent, nothing is emptied
    calls = []

    def run_read(harness, prompt, workdir, cancel, model="", env=None, resume="", timeout_s=0, **kw):
        calls.append(prompt)
        return json.dumps({"summary": "ok", "questions": [], "metrics": []}), 0.1, 10, "s"

    monkeypatch.setattr(jobs, "run_read", run_read)
    slug = host.command("ideas.goal_save", {"about": "A landing page that sells.", "craft": "design", "priority": "high"})["slug"]
    _wait(host, slug, goal=True)
    read = len(calls)
    host.command("ideas.goal_save", {"slug": slug, "team": ["ui-kit"], "every": [], "leader": "product-designer"})
    _wait(host, slug, goal=True)
    g = next(t for t in host.command("ideas.board")["tracks"] if t["slug"] == slug)
    assert g["team"] == ["ui-kit"] and g["leader"]["slug"] == "product-designer"
    assert g["about"] == "A landing page that sells." and g["priority"] == "high" and g["craft"] == "design"
    assert len(calls) == read                                                    # its party alone: no reading
    host.command("ideas.goal_save", {"slug": slug, "about": "A landing page that sells, in two languages."})
    _wait(host, slug, goal=True)
    assert len(calls) == read + 1 and next(t for t in host.command("ideas.board")["tracks"] if t["slug"] == slug)["team"] == ["ui-kit"]


def test_an_agent_of_the_library_is_added_once_and_each_agent_says_about_what_a_task_costs(host):
    # spec 41 §8
    got = host.command("ideas.roles")
    assert next(a for a in got["library"] if a["id"] == "grunt")["installed"] is True
    assert next(a for a in got["library"] if a["id"] == "copywriter")["installed"] is False
    assert host.command("ideas.role_add", {"id": "copywriter"}) == {"slug": "copywriter"}
    got = host.command("ideas.roles")
    assert next(a for a in got["library"] if a["id"] == "copywriter")["installed"] is True
    cw = next(r for r in got["roles"] if r["slug"] == "copywriter")
    assert cw["instruction"] == library.get("copywriter").instruction and cw["craft"] == "marketing"
    with pytest.raises(CommandError, match="already this project's"):
        host.command("ideas.role_add", {"id": "copywriter"})
    with pytest.raises(CommandError, match="No agent 'wizard' in the library"):
        host.command("ideas.role_add", {"id": "wizard"})
    by = {r["slug"]: r for r in got["roles"]}
    assert by["taskmaster"]["usd_task"] is None and by["grunt"]["usd_task"] == got["tier_costs"][by["grunt"]["head"]["tier"]]
    assert by["copywriter"]["usd_task"] == round(got["tier_costs"][cw["head"]["tier"]], 2)
    assert by["taskmaster"]["told"] == roles.TOLD["taskmaster"] and "worktree" in by["grunt"]["told"]
    assert "told" not in by["copywriter"]
    blocks = {b["role"]: b for b in host.command("ideas.agents")["roles"]}
    assert blocks["grunt"]["usd_task"] == by["grunt"]["usd_task"] and blocks["taskmaster"]["usd_task"] is None


def test_the_leaders_preamble_says_it_plans_the_goals_and_no_longer_that_it_accepts_the_party(host):
    """Spec 50 §2.5: a party's steps run as its leader, who plans; nothing accepts a party by itself."""
    from orkboard.core.idea_lead import LeadMixin
    voice = LeadMixin.voice({"name": "Product manager", "instruction": "Be brief."})
    assert voice.startswith("You are Product manager, the leader of this goal's party: you plan its ideas. Be brief.")
    assert "accept" not in voice


def test_seats_count_against_the_leaders_stages_and_the_refusal_names_the_leader():
    """Spec 59 §2.3: four builders and one checker with the Game designer, three and two with any other leader."""
    four = ["grunt", "artist", "level-designer", "sound-designer"]
    assert goal_team.seats(four, "game-designer") == "" and goal_team.seats([*four, "aso"], "game-designer") == "A party led by Game designer has at most 4 builders"
    assert goal_team.seats(four, "architect") == "A party led by Architect has at most 3 builders"
    assert goal_team.seats(four[:3], "architect") == "" and goal_team.seats(four[:3]) == ""
    assert goal_team.seats(four[:3] + ["reviewer"], "game-designer") == "" and goal_team.seats(["playtester", "reviewer"], "game-designer") == "A party led by Game designer has at most 1 checkers"
    assert goal_team.seats(["reviewer", "editor"], "growth") == "" and goal_team.seats(["reviewer", "editor", "data-reviewer"], "growth") == "A party led by Growth has at most 2 checkers"
    assert goal_team.seats(four[:4], "") == "A party led by Taskmaster has at most 3 builders"
    assert goal_team.SEATS == 5 and goal_team.seats(["playtester"], "game-designer") == ""
