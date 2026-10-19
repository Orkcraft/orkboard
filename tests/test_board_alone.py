"""Orkboard on its own (docs/specs/37-board-and-line.md §3, §4, §9, Tests → B): a tool's run, the machine's tools and
tiers read without the town, its Wiki, its snapshot, its phone, its first screen and its command.

The Board's own suites (tests/test_gui_ideas.py, tests/test_gui_goals.py) run on Orkboard's host (`gui/board_host.py`
`Orkboard`); in Orkline they ran on its town's host too."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

from orkboard import settings
from orkboard.core import treasury
from orkboard.core.board_limits import BoardLimits
from orkboard.gui import pwa
from orkboard.gui.board_host import BoardPhone, CommandError, Orkboard
from orkboard.gui.server import Server
from orkboard.realm import wiki
from orkboard.sources.limits import Limit
from tests.test_gui_ideas import BOARD_COMMANDS


@pytest.fixture
def host(fake_repo) -> Orkboard:
    h = Orkboard(fake_repo)
    yield h
    sys.modules.pop("orkboard.core.idea_runner", None)


# -- the line cut (§3, §4) ------------------------------------------------------------------------------------

def test_a_run_faked_where_tool_run_starts_it_is_the_boards(monkeypatch):
    """`tool_run.run_proc = fake` reaches the Board's runs (realm/jobs.py reads realm/tool_run.py)."""
    from orkboard.realm import jobs, tool_run
    seen = []
    monkeypatch.setattr(tool_run, "run_proc", lambda cmd, *a, **k: seen.append(cmd) or (0, '{"result": "ok"}', ""))
    assert jobs.run_read("claude", "read it", Path.cwd(), threading.Event())[0] == "ok" and seen


def test_the_machines_main_tool_and_tiers_are_read_cached_from_settings(tmp_path, monkeypatch):
    from orkboard.realm import harnesses, tiers
    file = tmp_path / "machine.json"
    monkeypatch.setenv("ORKCRAFT_SETTINGS_FILE", str(file))
    m = settings.MachineSettings()
    m.tools = {"claude": settings.ToolChoice(enabled=False), "codex": settings.ToolChoice(enabled=True)}
    m.tier_models = {"codex": {"elder": "gpt-6-astra"}}
    settings.save(m, file)
    assert settings.main_tool() == "codex" == tiers.tool_of({})
    assert harnesses.tier_choices() == {"codex": {"elder": "gpt-6-astra"}}
    assert settings.cached() is settings.cached()                     # one read, kept until the file changes


def test_an_orkspaces_worktree_is_orklines():
    """`link`, `unlink` and `cwd_for` (an orkspace's worktree) stay in Orkline: Orkboard's worktrees has none."""
    from orkboard.realm import worktrees
    assert not any(hasattr(worktrees, name) for name in ("link", "unlink", "cwd_for"))
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


# -- Orkboard's host (§4) ----------------------------------------------------------------------------------------

def test_the_snapshot_holds_only_what_the_shell_reads(host):
    snap = host.snapshot()
    assert set(snap) == {"focus", "onboarding", "ideas_rev", "ops_rev", "needs_you", "idea_states", "review_count",
                         "review_results", "limits", "hud", "repo", "projects", "update"}
    assert snap["projects"] == host.command("projects.list")                         # the switcher (spec 37 §8)
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
    assert all(BoardPhone.allowed(host, c, {}) for c in BOARD_COMMANDS)
    assert BoardPhone.allowed(host, "halt", {}) and not BoardPhone.allowed(host, "act", {"id": "pit"})
    assert not BoardPhone.allowed(host, "ideas.nothing", {})
    assert BoardPhone.guard("ideas.add", {"text": "x", "link": "lan"}, {"id": "d1"}) == {
        "text": "x", "device": "phone", "link": "paired"}
    snap = BoardPhone.phone_snapshot(host)
    assert snap["focus"] == "board" and snap["rev"] == BoardPhone.phone_snapshot(host)["rev"]
    assert host.command("mobile.snapshot", {"since": snap["rev"]}) == {"v": 1, "rev": snap["rev"], "same": True}


def test_the_first_screen_saves_the_tools_and_raises_no_town(fake_repo, tmp_path, monkeypatch):
    from orkboard import tools
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


def test_a_tool_turned_on_at_the_first_screen_is_drawn_on(fake_repo, monkeypatch):
    # the owner's 19 October: "Turn on Antigravity at my own risk" left its box empty (the page draws its rows from the
    # state pushed, and none was), so a later click sent the stale rows back
    from orkboard import tools
    monkeypatch.setenv("ORKCRAFT_ONBOARDING", "1")
    monkeypatch.setattr(tools, "detect", lambda *a, **k: [tools.ToolStatus(t, found=t.id in ("claude", "agy"), version="2")
                                                          for t in tools.TOOLS])
    monkeypatch.setattr(tools, "detect_others", lambda *a, **k: [])
    board = Orkboard(fake_repo)
    board.onboarding._finder.join(5)
    rows = {r["id"]: r for r in board.snapshot()["onboarding"]["tools"]["rows"]}
    assert rows["claude"]["enabled"] and not rows["agy"]["enabled"]            # experimental: off until its warning
    pushed = []
    monkeypatch.setattr(board.onboarding.host, "on_change", lambda *a, **k: pushed.append(1))
    board.command("onboarding.tools", {"tools": {"agy": {**rows["agy"], "enabled": True, "risk_read": True}}})
    assert pushed                                                              # the page is pushed its new rows
    rows = {r["id"]: r for r in board.snapshot()["onboarding"]["tools"]["rows"]}
    assert rows["agy"]["enabled"] and rows["claude"]["enabled"]
    board.command("onboarding.tools", {"tools": {"claude": {**rows["claude"], "billing": "api"}}})
    assert len(pushed) == 2 and board.snapshot()["onboarding"]["tools"]["rows"][0]["billing"] == "api"


def test_the_page_is_board_js_in_offices_look_and_the_phones_board_app_js(host):
    server = Server(host)
    page = server.page().decode()
    assert 'src="/static/board.js"' in page and "app.js" not in page and 'data-look="office"' in page
    assert server.phones.entry == "board-app.js"
    for phone in (pwa.serve("GET", "/app/"), pwa.serve("GET", "/app/", entry="board-app.js")):
        page = phone.decode("utf-8", "replace")
        assert 'src="board-app.js"' in page and 'src="app.js"' not in page


def test_orkboard_starts_on_the_project_and_board_is_the_old_habit(fake_repo, monkeypatch):
    from orkboard.gui import board_host
    started = []
    monkeypatch.setattr(board_host, "run", lambda root, browser=False, port=0: started.append((root, browser, port)) or 0)
    monkeypatch.setenv("ORKCRAFT_NO_UPDATE", "1")
    assert board_host.main(["--repo", str(fake_repo), "board", "--browser", "--port", "8765"]) == 0   # `orkboard board`
    assert started == [(fake_repo.resolve(), True, 8765)]
    assert board_host.main(["--repo", str(fake_repo), "--browser"]) == 0
    assert started[-1] == (fake_repo.resolve(), True, 0)
    monkeypatch.chdir(fake_repo / "src")                                  # the folder it was started in, as Orkline's
    assert board_host.main([]) == 0 and started[-1] == (fake_repo.resolve(), False, 0)


def test_outside_a_project_it_starts_on_the_start_screen_and_a_refused_folder_is_said(tmp_path, monkeypatch, capsys):
    """Spec 37 §8: no folder, no last project and none it was started in: the start screen (Open folder…, Recent);
    a folder that may not be a project is refused in words."""
    from orkboard.gui import board_host
    started = []
    monkeypatch.setattr(board_host, "run", lambda root, browser=False, port=0: started.append(root) or 0)
    monkeypatch.chdir(tmp_path)
    assert board_host.main([]) == 0 and started == [None]
    assert board_host.main([str(Path.home())]) == 1 and started == [None]
    assert "home folder" in capsys.readouterr().err
