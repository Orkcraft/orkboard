"""`orkboard` in a real browser (docs/specs/37-board-and-line.md §4, Tests → B): Orkboard's own host and server on a
fixture repository, its keeper stubbed. On the desktop (1 440 × 900) the four panes, a goal saved, its question in Needs you;
on a paired phone (390 × 844) the phone shell, the same, with no horizontal scroll. Neither asks for a camp file: nothing
under js/camp/, js/buildings/, sprites/ or v3/ (the network log). Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS
is set."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
pw = pytest.importorskip("playwright.async_api")

from orkboard.gui import phone_tls  # noqa: E402
from orkboard.gui.board_host import Orkboard  # noqa: E402
from orkboard.gui.server import Server  # noqa: E402
from orkboard.realm import jobs  # noqa: E402
from tests.test_phones import _listening  # noqa: E402
from tests.browser_kit import CHROMIUM, WAIT_MS, launch, spki  # noqa: E402

pytestmark = pytest.mark.browser

SHOTS = Path(__file__).resolve().parent.parent / "docs" / "design" / "img" / "v1"
CAMP = ("/js/camp/", "/js/buildings/", "/sprites/", "/v3/", "/camp/")
GOAL = {"summary": "Installs are the first step.\nCount them weekly.", "questions": ["Which channel first?"],
        "metrics": [{"name": "weekly installs", "how": "npm downloads, per week"}], "reply": "Noted."}


@pytest.fixture
def board(tmp_path, monkeypatch):
    """Orkboard on a fixture repository, its keeper answering a goal with a question: (host, repo)."""
    for key, value in {"ORKCRAFT_SETTINGS_FILE": tmp_path / "settings.json", "ORKCRAFT_ONBOARDING": "0",
                       "ORKCRAFT_LIMITS": "0", "ORKCRAFT_NO_UPDATE": "1", "XDG_CONFIG_HOME": tmp_path / "config"}.items():
        monkeypatch.setenv(key, str(value))
    repo = tmp_path / "project"
    (repo / "src").mkdir(parents=True)
    (repo / "README.md").write_text("# Demo project\n", encoding="utf-8")
    git = ["git", "-c", "user.email=test@orkcraft.local", "-c", "user.name=Test Runner"]
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run([*git, "add", "-A"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-qm", "init"], cwd=repo, check=True)
    monkeypatch.setattr(jobs, "run_read", lambda *a, **k: (json.dumps(GOAL), 0.01, 10, "s-1"))
    return Orkboard(repo)


def _camp(urls: list[str]) -> list[str]:
    return [u for u in urls if any(part in u for part in CAMP)]


def test_orkboard_on_the_desktop_the_four_panes_a_goal_saved_and_needs_you_no_camp_file(board):
    server = Server(board)
    thread = server.start_thread()
    with playwright.sync_playwright() as p:
        browser = launch(p)
        try:
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            pg = ctx.new_page()
            urls: list[str] = []
            errors: list[str] = []
            ctx.on("request", lambda r: urls.append(r.url))
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(server.url)
            pg.get_by_role("tablist", name="Parties").wait_for(timeout=WAIT_MS)
            pg.get_by_text("No parties yet").wait_for(timeout=WAIT_MS)                              # the window: the party switch in the top bar, the arena under it
            assert pg.locator(".arena-pswitch").is_visible() and pg.locator(".shell-board, .shell-agents, .shell-split").count() == 0
            assert pg.evaluate("document.documentElement.dataset.look") == "office"
            assert pg.locator(".gui-hud, .gui-camp, .gui-town, .gui-foot").count() == 0
            pg.locator(".arena-pswitch__new").click()                                                    # + in the top bar: New party
            dlg = pg.get_by_role("dialog", name="New party")
            dlg.locator('.shell-craft-tile[data-craft="marketing"]').click()          # a party of the library: its leader, builders and checkers
            dlg.get_by_label("What it is for").fill("More people try Orkline.")
            dlg.get_by_role("button", name="Save party").click()
            pg.locator(".shell-goal").get_by_role("region", name="The party").wait_for(timeout=WAIT_MS)
            for pane in (".arena-left", ".arena-field", ".arena-look", ".arena-team", ".shell-drawer"):                # the window's regions, on the real host's data
                assert pg.locator(pane).is_visible(), pane
            g = next(t for t in board.command("ideas.board")["tracks"] if t["team"])
            assert (g["leader"]["slug"], g["team"]) == ("growth", ["copywriter", "seo", "editor"])
            made = {r["slug"]: r for r in board.command("ideas.roles")["roles"]}
            assert made["copywriter"]["craft"] == "marketing" and made["growth"]["takes"] == ["campaign"]   # the party's agents: the project's roles
            team = pg.locator(".shell-goal").get_by_role("region", name="The party")             # the party's screen says who is in it
            team.wait_for(timeout=WAIT_MS)
            assert "Copywriter" in team.inner_text() and "Growth" in team.inner_text()
            pg.locator(".arena-hc[data-kind=goal]").wait_for(timeout=WAIT_MS)                    # the keeper's question: a stop along the bottom
            assert "Which channel first?" in pg.locator(".arena-hc[data-kind=goal]").inner_text()
            assert any(n["kind"] == "goal" for n in board.command("ideas.board")["needs_you"])
            assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            if os.environ.get("ORKCRAFT_SHOTS"):
                SHOTS.mkdir(parents=True, exist_ok=True)
                pg.screenshot(path=str(SHOTS / "orkboard-desktop-1440x900.png"))
            assert not _camp(urls), _camp(urls)
            assert any(u.endswith("/static/board.js") for u in urls) and not any(u.endswith("/static/app.js") for u in urls)
            assert not errors, errors
        finally:
            browser.close()
            server.stop()
            thread.join(10)


@pytest.mark.asyncio
async def test_orkboard_on_a_phone_the_shell_the_same_no_camp_file_no_horizontal_scroll(board):
    board.command("ideas.goal_save", {"about": "More people try Orkline.", "priority": "high"})
    server = Server(board)
    server.phones.bind = "127.0.0.1"
    task = asyncio.create_task(server.run())
    for _ in range(200):
        if server.ready.is_set():
            break
        await asyncio.sleep(0.02)
    try:
        offer = server.host.command("phones.pair")
        await _listening(server)
        async with pw.async_playwright() as p:
            flags = [f"--ignore-certificate-errors-spki-list={spki(phone_tls.paths(server.phones.cert_folder)[0])}"]
            try:
                browser = await (p.chromium.launch(executable_path=CHROMIUM, args=flags) if CHROMIUM
                                 else p.chromium.launch(args=flags))
            except Exception as e:                         # noqa: BLE001 — no browser here
                pytest.skip(f"no Chromium for Playwright here: {e}")
            try:
                ctx = await browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True,
                                                ignore_https_errors=True)
                urls: list[str] = []
                errors: list[str] = []
                ctx.on("request", lambda r: urls.append(r.url))         # the page's and its service worker's
                page = await ctx.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                await page.goto(f"{server.phones.address}/app/#pair={offer['code']}")
                await page.locator(".gchips .gchip").first.wait_for(timeout=WAIT_MS)                      # the one window: the goals as chips, no tab bar (spec 49 §10)
                assert await page.locator(".board-tabs").count() == 0 and await page.get_by_role("tab", name="Needs you").count() == 0
                assert [(await b.get_attribute("aria-label")).split(":")[0] for b in await page.get_by_role("tab").all()] == ["Planning", "Implementation", "Checking"]   # the stage switch
                ask = page.locator('.hc[data-kind="goal"]')                                                # Needs you: the signal (spec 41 §1) lies along the bottom
                await ask.wait_for(timeout=WAIT_MS)
                await ask.click(position={"x": 14, "y": 12})
                await page.get_by_text("Which channel first?").first.wait_for(timeout=WAIT_MS)             # the goal's question, as on the desktop
                await page.keyboard.press("Escape")
                bar = page.locator(".board-bar")                                                           # the menu, the goals
                assert await page.locator(".gchips .gchip").first.is_visible() and await bar.get_by_role("button", name="Menu").is_visible()
                assert await page.evaluate("document.documentElement.dataset.look") == "office"
                assert await page.locator(".dock, .camp, .grid, .head").count() == 0
                assert await page.evaluate("document.documentElement.scrollWidth <= 390 && document.body.scrollWidth <= 390")
                if os.environ.get("ORKCRAFT_SHOTS"):
                    SHOTS.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(SHOTS / "orkboard-phone-390x844.png"))
                await page.wait_for_function("navigator.serviceWorker.controller !== null || !window.isSecureContext",
                                             timeout=WAIT_MS)
                await page.wait_for_timeout(500)                      # the worker's install fetched its list
                assert not _camp(urls), _camp(urls)
                assert any(u.endswith("/app/board-app.js") for u in urls) and not any(u.endswith("/app/app.js") for u in urls)
                assert any("sw.js?app=board" in u for u in urls)
                assert not errors, errors
            finally:
                await browser.close()
    finally:
        server.stop()
        await asyncio.wait_for(task, 10)
