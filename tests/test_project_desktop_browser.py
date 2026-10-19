"""The project on the desktop, in a real browser (docs/specs/37-board-and-line.md §8, Tests → D2; 1 440 × 900): Open folder on
a fixture, the switcher with two projects and their counts, the start screen, the Files pane (a Markdown file rendered,
edited and saved; a code file with line numbers; a `.env` greyed) and the Git section (a changed file's diff, a commit,
*changed on disk: reload* after the file changes underneath)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

from orkboard.gui import folder_dialog  # noqa: E402
from orkboard.gui.board_host import Orkboard  # noqa: E402
from orkboard.gui.server import Server  # noqa: E402
from orkboard.realm import jobs  # noqa: E402
from tests.browser_kit import WAIT_MS, launch  # noqa: E402

pytestmark = pytest.mark.browser

GOAL = {"summary": "Installs are the first step.", "questions": ["Which channel first?"],
        "metrics": [{"name": "weekly installs", "how": "npm downloads, per week"}], "reply": "Noted."}
GIT = ["git", "-c", "user.email=test@orkcraft.local", "-c", "user.name=Test Runner"]


def _repo(path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    for key, value in (("user.email", "test@orkcraft.local"), ("user.name", "Test Runner")):    # the commit button commits as the repository
        subprocess.run(["git", "config", key, value], cwd=path, check=True)
    subprocess.run([*GIT, "add", "-A"], cwd=path, check=True)
    subprocess.run([*GIT, "commit", "-qm", "init"], cwd=path, check=True)
    return path


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Two fixture repositories (`shop` open, `blog` not yet) and Orkboard on `shop`: (host, shop, blog)."""
    for key, value in {"ORKCRAFT_SETTINGS_FILE": tmp_path / "settings.json", "ORKCRAFT_ONBOARDING": "0",
                       "ORKCRAFT_LIMITS": "0", "ORKCRAFT_NO_UPDATE": "1", "XDG_CONFIG_HOME": tmp_path / "config"}.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setattr(jobs, "run_read", lambda *a, **k: (json.dumps(GOAL), 0.01, 10, "s-1"))
    monkeypatch.setattr(folder_dialog, "native", lambda begin="": None)          # Open folder's system dialog: cancelled
    shop = _repo(tmp_path / "shop", {"README.md": "# Shop\n\nSells **things**.\n", "src/app.py": "import os\n\nprint('hello')\n",
                                     ".env": "TOKEN=abc\n", ".gitignore": "build/\n", "build/out.js": "x\n"})
    blog = _repo(tmp_path / "blog", {"README.md": "# Blog\n"})
    return Orkboard(shop), shop, blog


def _serve(host):
    server = Server(host)
    return server, server.start_thread()


def _page(browser, server):
    pg = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(server.url)
    pg.locator(".shell").wait_for(timeout=WAIT_MS)
    return pg, errors


def _run(world, body):
    host = world[0]
    server, thread = _serve(host)
    with playwright.sync_playwright() as p:
        browser = launch(p)
        try:
            pg, errors = _page(browser, server)
            body(pg, host)
            assert not errors, errors
        finally:
            browser.close()
            server.stop()
            thread.join(10)


def _files_tab(pg):
    pg.get_by_role("tab", name="Files").click()
    pg.locator(".shell-tree__row").first.wait_for(timeout=WAIT_MS)


def test_open_folder_the_switcher_with_two_projects_and_their_counts(world):
    host, shop, blog = world
    host.command("ideas.goal_save", {"about": "More people try the shop.", "priority": "high"})

    def body(pg, host):
        pg.locator(".shell-proj__btn").wait_for(timeout=WAIT_MS)
        assert pg.locator(".shell-proj__btn").inner_text().startswith("shop")
        pg.locator(".board-need[data-kind=goal]").wait_for(timeout=WAIT_MS)
        pg.keyboard.press("Control+o")                                              # Open folder…, as an IDE
        dlg = pg.get_by_role("dialog", name="Open folder")
        dlg.get_by_label("Folder").fill(str(Path.home()))                           # refused, in words
        dlg.get_by_role("button", name="Open folder").click()
        assert "home folder" in dlg.locator("[role=alert]").inner_text()
        dlg.get_by_label("Folder").fill(str(blog))
        dlg.get_by_role("button", name="Open folder").click()
        dlg.wait_for(state="detached", timeout=WAIT_MS)
        pg.locator(".shell-proj__btn", has_text="blog").wait_for(timeout=WAIT_MS)
        assert pg.locator(".board-need[data-kind=goal]").count() == 0               # shop's goal is not seen in blog
        pg.locator(".shell-proj__btn").click()
        rows = pg.locator(".shell-proj__one")
        assert rows.count() == 2
        shop_row = pg.locator(f".shell-proj__one[data-path='{shop.resolve()}']")
        assert "needs you 1" in shop_row.inner_text()                               # the counts, live
        shop_row.click()
        pg.locator(".shell-proj__btn").filter(has_text="shop").wait_for(timeout=WAIT_MS)
        pg.locator(".board-need[data-kind=goal]").wait_for(timeout=WAIT_MS)
        assert host.command("projects.list")["current"] == str(shop.resolve())
    _run(world, body)


def test_open_folder_opens_the_systems_dialog_and_the_folder_chosen_opens(world, monkeypatch):
    # the owner's 19 October: a project's folder chosen in the system's picker, not typed
    host, shop, blog = world
    asked = []
    monkeypatch.setattr(folder_dialog, "native", lambda begin="": asked.append(begin) or str(blog))

    def body(pg, host):
        pg.locator(".shell-proj__btn").wait_for(timeout=WAIT_MS)
        pg.keyboard.press("Control+o")                                              # the dialog at once, as an IDE's
        pg.locator(".shell-proj__btn", has_text="blog").wait_for(timeout=WAIT_MS)
        assert pg.get_by_role("dialog", name="Open folder").count() == 0 and asked == [""]
    _run(world, body)


def test_with_no_dialog_here_the_path_is_typed_and_choose_says_why(world, monkeypatch):
    host, shop, blog = world

    def none(begin=""):
        raise folder_dialog.Unavailable("No folder dialog on this computer: type the folder's path.")
    monkeypatch.setattr(folder_dialog, "native", none)

    def body(pg, host):
        pg.keyboard.press("Control+o")
        dlg = pg.get_by_role("dialog", name="Open folder")
        choose = dlg.get_by_role("button", name="Choose…")
        choose.wait_for(timeout=WAIT_MS)
        pg.wait_for_function("() => !document.querySelector('[role=dialog] button[disabled]:not([type=submit])')", timeout=WAIT_MS)
        assert dlg.locator("[role=alert]").count() == 0                            # at once: quiet
        choose.click()
        dlg.locator("[role=alert]").wait_for(timeout=WAIT_MS)
        assert "type the folder's path" in dlg.locator("[role=alert]").inner_text()
        dlg.get_by_label("Folder").fill(str(blog))
        dlg.get_by_role("button", name="Open folder").click()
        pg.locator(".shell-proj__btn", has_text="blog").wait_for(timeout=WAIT_MS)
    _run(world, body)


def test_a_folder_without_git_offers_start_git_here(world, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "notes.txt").write_text("hello\n", encoding="utf-8")

    def body(pg, host):
        pg.keyboard.press("Control+o")
        dlg = pg.get_by_role("dialog", name="Open folder")
        dlg.get_by_label("Folder").fill(str(plain))
        dlg.get_by_role("button", name="Open folder").click()
        dlg = pg.get_by_role("dialog", name="Start git here?")
        dlg.get_by_role("button", name="Start git here").click()
        dlg.wait_for(state="detached", timeout=WAIT_MS)
        assert (plain / ".git").is_dir()
    _run(world, body)


def test_the_start_screen_with_no_project_open_and_recent(tmp_path, monkeypatch, world):
    host, shop, blog = world
    host.command("projects.close", {"path": str(shop)})          # shop stays in Recent
    assert host.command("projects.list")["current"] is None

    def body(pg, host):
        pg.get_by_role("main", name="Start").wait_for(timeout=WAIT_MS)
        assert pg.get_by_role("button", name="Open folder…").is_visible()
        assert pg.locator(".shell-start__recent").get_by_role("button", name="shop").is_visible()
        assert pg.locator(".shell-board").count() == 0                              # no Board without a project
        pg.locator(".shell-start__recent").get_by_role("button", name="shop").click()
        pg.locator(".shell-board").wait_for(timeout=WAIT_MS)
        pg.locator(".shell-proj__btn", has_text="shop").wait_for(timeout=WAIT_MS)
    _run(world, body)


def test_files_markdown_rendered_edited_and_saved_code_with_line_numbers_env_greyed(world):
    host, shop, blog = world

    def body(pg, host):
        _files_tab(pg)
        names = pg.locator(".shell-tree__row").all_inner_texts()
        assert ".git/" not in names and ".orkcraft/" not in names and "build/" not in names   # ignored: behind the toggle
        pg.get_by_label("Show git-ignored files").check(force=True)
        pg.locator(".shell-tree__row", has_text="build/").wait_for(timeout=WAIT_MS)
        pg.get_by_label("Show git-ignored files").uncheck(force=True)
        env = pg.locator(".shell-tree__row.is-secret", has_text=".env")
        assert "may hold secrets: open it in your own editor" in env.get_attribute("title")
        env.click()
        assert "may hold secrets" in pg.locator("[data-kind=secret]").inner_text()
        assert "TOKEN" not in pg.locator(".shell-preview").inner_text()            # never read
        pg.locator(".shell-tree__row", has_text="README.md").click()               # Markdown, rendered
        assert pg.locator(".shell-md h1").inner_text() == "Shop"
        assert pg.locator(".shell-md strong").inner_text() == "things"
        pg.get_by_role("region", name="Preview").get_by_role("button", name="Edit", exact=True).click()
        box = pg.get_by_label("Editor")
        box.fill("# Shop\n\nSells **many things**.\n")
        pg.keyboard.press("Control+s")
        pg.locator(".shell-md").wait_for(timeout=WAIT_MS)
        assert "many things" in pg.locator(".shell-md strong").inner_text()
        assert (shop / "README.md").read_text(encoding="utf-8") == "# Shop\n\nSells **many things**.\n"
        pg.locator(".shell-tree__row", has_text="src/").click()                    # a folder opens one level
        pg.locator(".shell-tree__row", has_text="app.py").click()
        pg.locator(".shell-code").wait_for(timeout=WAIT_MS)
        assert pg.locator(".shell-code__nos").inner_text().split() == ["1", "2", "3"]
        assert "print('hello')" in pg.locator(".shell-code__text").inner_text()
        pg.get_by_role("region", name="Preview").get_by_role("button", name="Edit", exact=True).click()                              # leaving with changes asks
        pg.get_by_label("Editor").fill("changed\n")
        pg.get_by_role("button", name="Cancel").click()
        dlg = pg.get_by_role("dialog", name="Unsaved changes")
        dlg.get_by_role("button", name="Keep editing").click()
        assert pg.get_by_label("Editor").input_value() == "changed\n"
        pg.get_by_role("button", name="Cancel").click()
        pg.get_by_role("dialog", name="Unsaved changes").get_by_role("button", name="Discard changes").click()
        assert (shop / "src" / "app.py").read_text(encoding="utf-8").startswith("import os")
    _run(world, body)


def test_changed_on_disk_reload_after_the_file_changes_underneath(world):
    host, shop, blog = world

    def body(pg, host):
        _files_tab(pg)
        pg.locator(".shell-tree__row", has_text="README.md").click()
        pg.get_by_role("region", name="Preview").get_by_role("button", name="Edit", exact=True).click()
        pg.get_by_label("Editor").fill("# Mine\n")
        (shop / "README.md").write_text("# Someone else's\n", encoding="utf-8")   # underneath
        os.utime(shop / "README.md", (1_900_000_000, 1_900_000_000))
        pg.get_by_role("button", name="Save").click()
        alert = pg.locator(".shell-edit__why")
        alert.wait_for(timeout=WAIT_MS)
        assert "changed on disk: reload" in alert.inner_text()
        assert (shop / "README.md").read_text(encoding="utf-8") == "# Someone else's\n"     # nothing overwritten
        alert.get_by_role("button", name="Reload").click()
        pg.locator(".shell-md h1").wait_for(timeout=WAIT_MS)
        assert pg.locator(".shell-md h1").inner_text() == "Someone else's"
    _run(world, body)


def test_git_section_a_changed_files_diff_and_a_commit(world):
    host, shop, blog = world
    (shop / "src" / "app.py").write_text("import os\n\nprint('hello, world')\n", encoding="utf-8")
    (shop / "notes.txt").write_text("new\n", encoding="utf-8")
    (shop / ".env").write_text("TOKEN=changed\n", encoding="utf-8")

    def body(pg, host):
        _files_tab(pg)
        git = pg.get_by_role("region", name="Git")
        git.locator("[data-git=branch]").wait_for(timeout=WAIT_MS)
        git.locator(".shell-git__file").first.wait_for(timeout=WAIT_MS)
        rows = git.locator(".shell-git__file")
        assert rows.count() == 2                                                    # the .env is never offered
        assert ".env" not in git.inner_text().replace(".envrc", "")
        app = git.locator(".shell-git__file", has_text="src/app.py")
        assert "modified" in app.inner_text().lower() and "+1" in app.inner_text() and "−1" in app.inner_text()
        app.get_by_role("button", name="src/app.py").click()                        # its diff, in the preview
        pg.locator(".shell-patch__line.is-add", has_text="hello, world").wait_for(timeout=WAIT_MS)
        assert pg.locator(".shell-patch__line.is-del", has_text="print('hello')").count() == 1
        assert git.get_by_role("button", name="Commit").is_disabled()               # nothing ticked
        git.get_by_label("Commit src/app.py").check()
        git.get_by_label("Commit message").fill("Greet the world")
        git.get_by_role("button", name="Commit 1 file").click()
        git.locator(".shell-git__file", has_text="src/app.py").wait_for(state="detached", timeout=WAIT_MS)
        assert git.locator(".shell-git__file", has_text="notes.txt").count() == 1   # only the ticked file went
        log = subprocess.run(["git", "log", "--format=%s", "-1"], cwd=shop, capture_output=True, text=True).stdout.strip()
        assert log == "Greet the world"
        assert "sends your code to origin" in git.get_by_role("button", name="Push").get_attribute("title").lower()
    _run(world, body)


def test_git_section_push_shows_pushing_then_the_outcome(world, tmp_path):
    host, shop, blog = world
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "remote", "add", "origin", str(origin)], cwd=shop, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=shop, check=True)

    def body(pg, host):
        _files_tab(pg)
        git = pg.get_by_role("region", name="Git")
        git.locator("[data-git=branch]").wait_for(timeout=WAIT_MS)
        git.get_by_role("button", name="Push").click()
        git.locator("[data-git=last]", has_text="to origin").wait_for(timeout=WAIT_MS)       # the outcome, in words
        assert "Sent" in git.locator("[data-git=last]").inner_text()
        assert subprocess.run(["git", "rev-parse", "main"], cwd=origin, capture_output=True, text=True).returncode == 0
        assert git.get_by_role("button", name="Push").is_enabled()
    _run(world, body)


def test_switch_branch_is_a_list_with_the_work_branch_and_main_first(world):
    host, shop, blog = world
    subprocess.run(["git", "branch", "-M", "main"], cwd=shop, check=True)
    for name in ("zeta", "dev"):
        subprocess.run(["git", "branch", name], cwd=shop, check=True)

    def body(pg, host):
        _files_tab(pg)
        git = pg.get_by_role("region", name="Git")
        git.locator("[data-git=branch]").wait_for(timeout=WAIT_MS)
        git.get_by_role("button", name="Switch branch").click()
        dlg = pg.get_by_role("dialog", name="Switch branch")
        items = dlg.get_by_role("list", name="Branches").get_by_role("listitem")
        items.first.wait_for(timeout=WAIT_MS)
        names = [i.locator("code").inner_text() for i in items.all()]
        assert names == ["dev", "main", "zeta"], names
        here = dlg.locator("[aria-current=true]")
        assert "you are here" in here.inner_text() and here.is_disabled()
        items.filter(has_text="zeta").click()
        dlg.wait_for(state="detached", timeout=WAIT_MS)
        git.locator("[data-git=branch]", has_text="zeta").wait_for(timeout=WAIT_MS)
    _run(world, body)


def test_a_restored_project_without_git_offers_start_git_without_an_error(world, tmp_path):
    host, shop, blog = world
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "notes.txt").write_text("hello\n", encoding="utf-8")
    host.projects.open(plain, keep=False)                       # as a project restored at startup is: shown, no dialog

    def body(pg, host):
        _files_tab(pg)
        git = pg.get_by_role("region", name="Git")
        git.get_by_role("button", name="Start git here").wait_for(timeout=WAIT_MS)
        assert "no git" in git.inner_text()
        assert "not a git repository" not in pg.inner_text("body").lower()          # git.status was never asked
        git.get_by_role("button", name="Start git here").click()
        git.locator("[data-git=branch]").wait_for(timeout=WAIT_MS)
        assert (plain / ".git").is_dir()
    _run(world, body)
