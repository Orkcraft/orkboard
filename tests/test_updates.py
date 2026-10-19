"""Updates (core/updates.py, gui/updates.py, orkGet's docs/updates.md): what is Orkboard's own. The updater is orkGet's
copy (orkboard/orkget/updates.py), whose own tests — the list, the policies, how each kind of install upgrades — run in
orkGet once for each product with Orkboard's profile; here: that the copy is the one bound to Orkboard's profile, its
list, its window, its command line and its restart."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from orkboard import __version__, commands, product, settings
from orkboard.core import updates

ROOT = Path(__file__).resolve().parents[1]


def manifest(*rels: tuple[str, bool]) -> dict:
    return {"releases": [{"version": v, "critical": c, "notes": f"notes of {v}"} for v, c in rels]}


@pytest.fixture
def on(monkeypatch):
    """Updates are read here (conftest turns them off for every other test)."""
    monkeypatch.delenv("ORKCRAFT_NO_UPDATE", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv(updates.UPDATED_ENV, raising=False)


class Runs:
    """subprocess.run as a script: each command answered from `answers` (by its first words), all kept."""

    def __init__(self, version: str = "9.0.0", fail: str = "", status: str = "", branch: str = "main"):
        self.calls: list[list[str]] = []
        self.version, self.fail, self.status, self.branch = version, fail, status, branch

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        line = " ".join(cmd)
        if "import orkboard" in line:
            return SimpleNamespace(returncode=0, stdout=self.version + "\n", stderr="")
        if " status " in f" {line} ":
            return SimpleNamespace(returncode=0, stdout=self.status, stderr="")
        if "symbolic-ref" in line:
            return SimpleNamespace(returncode=0 if self.branch else 1, stdout=self.branch + "\n", stderr="")
        if self.fail and self.fail in line:
            return SimpleNamespace(returncode=1, stdout="", stderr="no network")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")


# -- the copy, bound to Orkboard -----------------------------------------------------------------

def test_the_updater_is_orkgets_copy_bound_to_orkboard():
    import orkboard.orkget.updates as copy
    assert updates is copy and copy.__file__.endswith("orkboard/orkget/updates.py")
    assert updates.url() == product.PRODUCT.manifest


def test_orkboard_reads_its_own_list_never_orklines():
    assert product.PRODUCT.manifest == "https://raw.githubusercontent.com/Orkcraft/orkboard/main/updates.json"
    assert product.PRODUCT.source == "git+https://github.com/Orkcraft/orkboard"
    assert updates.state_path().name == "orkboard-updates.json"            # Orkline's cache is updates.json


def test_the_repositorys_list_names_this_version_last():
    """Orkboard's first version has no list (spec 37 §9); once a release adds updates.json, this holds."""
    if not (ROOT / "updates.json").is_file():
        pytest.skip("no updates.json in this repository yet")
    data = json.loads((ROOT / "updates.json").read_text(encoding="utf-8"))
    rels = updates.releases(data)
    assert rels and len(rels) == len(data["releases"]), "every release in updates.json is well formed"
    assert rels[0].version == __version__, "a release raises orkboard.__version__ and lists it in updates.json"


def test_a_checkout_of_orkboard_pulls_and_an_offer_is_over_this_version(tmp_path):
    root = tmp_path / "orkboard-src"
    (root / ".git").mkdir(parents=True)
    (root / "orkboard").mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "orkboard"\n', encoding="utf-8")
    way = updates.method(root / "orkboard", prefix=str(root / ".venv"), which=lambda name: None)
    assert way.kind == "git" and way.steps == (("git", "-C", str(root), "pull", "--ff-only"),)
    assert updates.offer(manifest((__version__, True))) is None
    assert updates.offer(manifest(("9.0.0", False))).version == "9.0.0"


def test_a_failed_install_at_a_launch_says_orkboard_opens_on_this_version(on, tmp_path, monkeypatch):
    said = []
    monkeypatch.setattr(updates, "method", lambda: updates.Method("pipx", (("pipx", "upgrade", "orkboard"),)))
    found = updates.at_launch([], "critical", say=said.append, now=10.0, file=tmp_path / "s.json",
                              read=lambda: manifest(("9.0.0", True)), run=Runs(fail="pipx"),
                              execv=lambda *a: pytest.fail("restarted after a failed install"))
    assert found.version == "9.0.0" and any(f"Orkboard opens on {__version__}" in line for line in said)


# -- the command line ---------------------------------------------------------------------------

def test_update_check_says_what_is_out(on, tmp_path, monkeypatch, capsys):
    from orkboard.gui import board_host
    where = tmp_path / "updates.json"
    where.write_text(json.dumps(manifest(("9.0.0", True))), encoding="utf-8")
    monkeypatch.setenv("ORKCRAFT_UPDATE_URL", where.as_uri())
    assert board_host.main(["update", "check"]) == 0
    out = capsys.readouterr().out
    assert "Orkboard 9.0.0 is out — a critical update" in out and "notes of 9.0.0" in out


def test_update_says_when_this_is_the_latest_and_when_updates_are_off(on, tmp_path, monkeypatch, capsys):
    where = tmp_path / "updates.json"
    where.write_text(json.dumps(manifest((__version__, False))), encoding="utf-8")
    monkeypatch.setenv("ORKCRAFT_UPDATE_URL", where.as_uri())
    assert commands.main(["update"]) == 0 and f"Orkboard {__version__} is the latest" in capsys.readouterr().out
    monkeypatch.setenv("ORKCRAFT_NO_UPDATE", "1")
    assert commands.main(["update", "check"]) == 0 and "updates are off here" in capsys.readouterr().out


def test_update_sets_the_policy(capsys):
    assert commands.main(["update", "ask"]) == 0
    assert settings.load().updates == "ask" and "nothing installs by itself" in capsys.readouterr().out
    assert commands.main(["update", "critical"]) == 0 and settings.load().updates == "critical"


# -- the policy ---------------------------------------------------------------------------------

def test_the_policy_is_kept_and_a_broken_one_is_the_default():
    s = settings.MachineSettings.from_dict({"updates": "auto"})
    assert s.updates == "auto" and s.to_dict()["updates"] == "auto"
    assert settings.MachineSettings.from_dict({"updates": "yolo"}).updates == "critical"
    assert settings.MachineSettings().updates == "critical"


# -- the window ---------------------------------------------------------------------------------

def test_the_window_installs_on_a_click_and_restarts(fake_repo, monkeypatch):
    from orkboard.gui import updates as gui_updates
    from orkboard.gui.board_host import CommandError, Orkboard
    host = Orkboard(fake_repo)
    up = host.updates
    assert host.snapshot()["update"] is None
    with pytest.raises(CommandError):
        host.command("update.install")
    up._method = lambda: updates.Method("pipx", (("pipx", "upgrade", "orkboard"),))
    up._read(updates.State(manifest=manifest(("9.0.0", True))))
    snap = host.snapshot()["update"]
    assert snap["version"] == "9.0.0" and snap["critical"] and snap["can"] and snap["state"] == "idle"
    started = []                               # the install's thread runs at once
    monkeypatch.setattr(gui_updates.threading, "Thread",
                        lambda target, **kw: SimpleNamespace(start=lambda: started.append(target) or target()))
    monkeypatch.setattr(updates, "install", lambda way: updates.Result(True, "ok", "9.0.0"))
    monkeypatch.setattr(updates, "remember", lambda result, version: None)
    quits = []
    up.quit = lambda: quits.append(1)
    host.command("update.install")
    assert started and up.state == "installed" and up.restart_wanted and quits == [1]
    host.close()


def test_the_window_says_a_failed_install_and_keeps_running(fake_repo, monkeypatch):
    from orkboard.gui import updates as gui_updates
    from orkboard.gui.board_host import Orkboard
    host = Orkboard(fake_repo)
    up = host.updates
    up._method = lambda: updates.Method("pipx", (("pipx", "upgrade", "orkboard"),))
    up._read(updates.State(manifest=manifest(("9.0.0", False))))
    monkeypatch.setattr(gui_updates.threading, "Thread",
                        lambda target, **kw: SimpleNamespace(start=target))
    monkeypatch.setattr(updates, "install", lambda way: updates.Result(False, "no network"))
    monkeypatch.setattr(updates, "remember", lambda result, version: None)
    up.quit = lambda: pytest.fail("restarted after a failed install")
    host.command("update.install")
    snap = host.snapshot()["update"]
    assert snap["state"] == "failed" and snap["error"] == "no network" and not up.restart_wanted
    host.command("update.policy", {"policy": "ask"})
    assert host.town.machine.updates == "ask" and settings.load().updates == "ask"
    host.close()


def test_the_window_never_reads_the_list_in_the_demo_or_when_off(fake_repo, monkeypatch):
    from orkboard.gui.board_host import Orkboard
    host = Orkboard(fake_repo)
    monkeypatch.setattr(updates, "check_later", lambda on_done=None: pytest.fail("read while off"))
    host.updates.tick(0.0)                     # conftest: ORKCRAFT_NO_UPDATE
    host.close()


def test_the_restart_runs_the_same_command(monkeypatch):
    seen = []
    monkeypatch.delenv(updates.UPDATED_ENV, raising=False)
    updates.restart(["--repo", "/p", "--browser"], "9.0.0", execv=lambda exe, args: seen.append((exe, args)))
    assert seen == [(sys.executable, [sys.executable, "-m", "orkboard.gui.board_host", "--repo", "/p", "--browser"])]
