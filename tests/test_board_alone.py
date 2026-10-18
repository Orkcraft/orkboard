"""Orkboard on its own (docs/specs/37-board-and-line.md §3, §4, Tests → B): the line cut, the Board's commands on
Orkboard's host answering as on Orkline's, its Wiki, its snapshot, its phone, its first screen and its command.

The Board's own suites (tests/test_gui_ideas.py, tests/test_gui_goals.py) run here a second time, on Orkboard's host
(`gui/board_host.py` `Orkboard`) in place of Orkline's (`gui/host.py` `Host`): the same commands, the same answers."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

from orkcraft import cli, layers, settings
from orkcraft.core import treasury
from orkcraft.core.board_limits import BoardLimits
from orkcraft.gui import pwa
from orkcraft.gui.board_host import BoardPhone, CommandError, Orkboard
from orkcraft.gui.host import Host
from orkcraft.gui.server import Server
from orkcraft.realm import checkpoint, ideas, wiki
from orkcraft.sources.limits import Limit
from tests import test_architecture as architecture
from tests import test_gui_goals as goals_suite
from tests import test_gui_ideas as ideas_suite


@pytest.fixture
def host(fake_repo) -> Orkboard:
    checkpoint.ensure(fake_repo)
    h = Orkboard(fake_repo)
    yield h
    sys.modules.pop("orkcraft.core.idea_runner", None)


model = goals_suite.model
TOWN_ONLY = {"test_the_focus_is_a_machine_setting"}     # Orkline's focus "" is the town; Orkboard's is always the Board
for _suite, _tag in ((ideas_suite, "ideas"), (goals_suite, "goals")):
    for _name, _test in vars(_suite).items():
        if _name.startswith("test_") and callable(_test) and _name not in TOWN_ONLY:
            globals()[f"test_orkboard_{_tag}__{_name[5:]}"] = _test


# -- the line cut (§3, §4) ------------------------------------------------------------------------------------

def test_no_module_holds_both_and_no_edge_is_known():
    assert layers.SPLIT == () and architecture.KNOWN == set()
    assert layers.edges() == []


def test_a_run_faked_where_the_town_fakes_it_is_the_boards_too(monkeypatch):
    """`road_agents.run_proc = fake` reaches the Board's runs (realm/jobs.py reads realm/tool_run.py)."""
    from orkcraft.realm import jobs, road_agents, tool_run
    seen = []
    monkeypatch.setattr(road_agents, "run_proc", lambda cmd, *a, **k: seen.append(cmd) or (0, '{"result": "ok"}', ""))
    assert tool_run.run_proc is road_agents.run_proc
    assert jobs.run_read("claude", "read it", Path.cwd(), threading.Event())[0] == "ok" and seen


def test_the_machines_main_tool_and_tiers_are_read_cached_from_settings(tmp_path, monkeypatch):
    from orkcraft.realm import builders, harnesses, tiers
    file = tmp_path / "machine.json"
    monkeypatch.setenv("ORKCRAFT_SETTINGS_FILE", str(file))
    m = settings.MachineSettings()
    m.tools = {"claude": settings.ToolChoice(enabled=False), "codex": settings.ToolChoice(enabled=True)}
    m.tier_models = {"codex": {"elder": "gpt-6-astra"}}
    settings.save(m, file)
    assert settings.main_tool() == "codex" == builders.main_tool() == tiers.tool_of({})
    assert harnesses.tier_choices() == {"codex": {"elder": "gpt-6-astra"}}
    assert settings.cached() is builders._machine()                  # one read, kept until the file changes


def test_an_orkspaces_worktree_is_the_towns_and_its_old_names_still_answer():
    from orkcraft.realm import orkspace_trees, worktrees
    assert worktrees.cwd_for is orkspace_trees.cwd_for and worktrees.link is orkspace_trees.link
    with pytest.raises(AttributeError):
        worktrees.nothing_here


# -- the Wiki (§3.5) --------------------------------------------------------------------------------------------

def test_orkboards_wiki_is_the_setting_else_the_general_one(fake_repo):
    board = Orkboard(fake_repo)
    assert board.ideas.wiki() == wiki.root_of(fake_repo.resolve(), None, "general")
    board.machine.ideas = settings.clean_ideas({**board.machine.ideas, "wiki": "docs/board/"})
    assert board.machine.ideas["wiki"] == "docs/board"
    assert board.ideas.wiki() == fake_repo.resolve() / "docs" / "board"
    assert "wiki" not in settings.clean_ideas({"wiki": "../out"}) and "wiki" not in settings.clean_ideas({"wiki": ""})


def test_orklines_board_finds_the_towns_wiki_as_before(fake_repo):
    from orkcraft.core import buildings
    town_host = Host(fake_repo, auto_commit=False)
    assert town_host.ideas.wiki() == wiki.root_of(fake_repo, None, "general")     # no Wiki in the camp: the default
    spec = buildings.type_spec(town_host.town, "scrolls")
    spec["config"] = {**(spec.get("config") or {}), "topic": "team"}
    bid = buildings.raise_spec(town_host.town, spec).id
    found = town_host.town.worker(bid).wiki_root
    assert town_host.wiki_of() == Path(found) and town_host.ideas.wiki() == Path(found)
    town_host.close()


# -- Orkboard's host (§4) ----------------------------------------------------------------------------------------

def test_the_snapshot_holds_only_what_the_shell_reads(host):
    snap = host.snapshot()
    assert set(snap) == {"focus", "onboarding", "ideas_rev", "needs_you", "idea_states", "review_count",
                         "review_results", "limits", "hud", "repo", "update"}
    assert snap["focus"] == "board" and set(snap["hud"]) == {"show_gold", "gold", "lumber"}
    assert snap["repo"] == str(host.repo_root) and snap["onboarding"] is None      # a machine set up: no first screen
    json.dumps(snap)


def test_the_commands_are_the_boards_stop_all_updates_and_links(host):
    assert {"halt", "link.open", "crash.window", "update.check"} <= set(host.commands)
    assert not {"town.build", "act", "orders.answer", "sessions.new", "onboarding.town"} & set(host.commands)
    assert host.command("halt", {}) == 0
    with pytest.raises(CommandError, match="Only web links"):
        host.command("link.open", {"url": "file:///etc/passwd"})
    with pytest.raises(CommandError, match="Unknown command"):
        host.command("town.build", {})


def test_the_budget_is_the_towns_cap_on_this_runs_spend(fake_repo):
    board = Orkboard(fake_repo)
    assert board.budget_ok()
    (fake_repo / ".orkcraft.json").write_text(json.dumps({"budget": {"gold_session_limit_usd": 1.5}}), encoding="utf-8")
    assert treasury.budget(fake_repo) == (1.5, treasury.LUMBER_LIMIT_TOKENS)
    board.spend = type(board.spend)(spent_usd=2.0)
    assert not board.budget_ok() and treasury.over(2.0, 1.5) and not treasury.over(2.0, 0)


def test_the_limits_are_read_on_their_clock_and_handed_to_the_board(tmp_path):
    reads = []
    lim = BoardLimits(tmp_path, lambda fn, *a: fn(*a),
                      fetch=lambda root: reads.append(root) or [Limit("claude", "", "session", 0.5, None)])
    lim.tick(0.0)
    for _ in range(100):
        if lim():
            break
        threading.Event().wait(0.01)
    lim.tick(60.0)                                                      # not due again for ten minutes
    assert [x.provider for x in lim()] == ["claude"] and len(reads) == 1


def test_a_phone_may_send_the_boards_commands_and_stop_all_only(host):
    assert all(BoardPhone.allowed(host, c, {}) for c in ideas_suite.BOARD_COMMANDS)
    assert BoardPhone.allowed(host, "halt", {}) and not BoardPhone.allowed(host, "act", {"id": "pit"})
    assert not BoardPhone.allowed(host, "ideas.nothing", {})
    assert BoardPhone.guard("ideas.add", {"text": "x", "link": "lan"}, {"id": "d1"}) == {
        "text": "x", "device": "phone", "link": "paired"}
    snap = BoardPhone.phone_snapshot(host)
    assert snap["focus"] == "board" and snap["rev"] == BoardPhone.phone_snapshot(host)["rev"]
    assert host.command("mobile.snapshot", {"since": snap["rev"]}) == {"v": 1, "rev": snap["rev"], "same": True}


def test_the_first_screen_saves_the_tools_and_raises_no_town(fake_repo, tmp_path, monkeypatch):
    from orkcraft import tools
    monkeypatch.setenv("ORKCRAFT_ONBOARDING", "1")
    file = Path(settings.path())
    monkeypatch.setattr(tools, "detect", lambda *a, **k: [tools.ToolStatus(t, found=t.id == "claude", version="2")
                                                          for t in tools.TOOLS])
    monkeypatch.setattr(tools, "detect_others", lambda *a, **k: [])
    board = Orkboard(fake_repo)
    board.onboarding._finder.join(5)
    first = board.snapshot()["onboarding"]
    assert first["step"] == "tools" and first["steps"] == ["tools"] and first["tools"]["ready"]
    assert [r["id"] for r in first["tools"]["rows"]] == ["claude"]
    assert {"onboarding.tools", "onboarding.check", "onboarding.skip"} <= set(board.commands)
    assert not {"onboarding.town", "onboarding.role", "onboarding.survey"} & set(board.commands)
    assert board.command("onboarding.skip", {}) is None
    assert board.snapshot()["onboarding"] is None
    saved = settings.load(file)
    assert saved.onboarded and saved.tools["claude"].enabled
    assert not (fake_repo / ".orkcraft.json").exists()                 # no town was raised


def test_the_page_is_board_js_in_offices_look_and_the_phones_board_app_js(host):
    server = Server(host)
    page = server.page().decode()
    assert 'src="/static/board.js"' in page and "app.js" not in page and 'data-look="office"' in page
    assert server.phones.entry == "board-app.js"
    phone = pwa.serve("GET", "/app/").decode("utf-8", "replace")
    assert 'src="app.js"' in phone                                      # Orkline's phone, as before
    board = pwa.serve("GET", "/app/", entry="board-app.js").decode("utf-8", "replace")
    assert 'src="board-app.js"' in board and 'src="app.js"' not in board
    town = Server(Host(host.repo_root, auto_commit=False))
    assert 'src="/static/app.js"' in town.page().decode() and town.phones.entry == "app.js"


def test_orkcraft_board_starts_orkboard_on_the_project(fake_repo, monkeypatch):
    from orkcraft.gui import board_host
    started = []
    monkeypatch.setattr(board_host, "run", lambda root, browser=False, port=0: started.append((root, browser, port)) or 0)
    monkeypatch.setenv("ORKCRAFT_NO_UPDATE", "1")
    assert cli.main(["--repo", str(fake_repo), "board", "--browser", "--port", "8765"]) == 0
    assert started == [(fake_repo.resolve(), True, 8765)]
    assert board_host.main(["--repo", str(fake_repo), "--browser"]) == 0
    assert started[-1] == (fake_repo.resolve(), True, 0)
