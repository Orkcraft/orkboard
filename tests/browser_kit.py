"""What the browser tests share (they came with Orkline's tests/test_gui_browser.py and tests/test_pwa_browser.py, which
drive the town and stay there): Chromium through Playwright, the preinstalled one (`/opt/pw-browsers/chromium`, or
$ORKCRAFT_CHROMIUM) else Playwright's own; the desktop's page served by Orkboard's host on a fixture project; and the
certificate pin a phone's browser is given.

A test module that imports it is skipped where Playwright or Chromium is missing; `-m browser` runs them alone."""
from __future__ import annotations

import base64
import hashlib
import os
import subprocess
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

from orkboard.gui.board_host import Orkboard  # noqa: E402
from orkboard.gui.server import Server  # noqa: E402

CHROMIUM = next((p for p in (os.environ.get("ORKCRAFT_CHROMIUM", ""), "/opt/pw-browsers/chromium") if p and Path(p).exists()),
                None)
WAIT_MS = 10_000


def launch(p):
    """Chromium as this machine has it: the preinstalled one, else Playwright's own (sync API)."""
    return p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()


def _can_launch() -> bool:
    try:
        with playwright.sync_playwright() as p:
            launch(p).close()
        return True
    except Exception:
        return False


if not _can_launch():
    pytest.skip("no Chromium for Playwright here", allow_module_level=True)


def spki(cert: Path) -> str:
    """The certificate's public key as Chromium names one it trusts: base64 of the SPKI's sha256."""
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    key = x509.load_pem_x509_certificate(cert.read_bytes()).public_key()
    der = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return base64.b64encode(hashlib.sha256(der).digest()).decode()


@pytest.fixture(scope="module")
def gui(tmp_path_factory):
    """One project, Orkboard's host and server, one browser for the module (the same settings as
    `isolated_layout_file`): `(server, browser)`."""
    tmp = tmp_path_factory.mktemp("gui")
    pw = playwright.sync_playwright().start()
    browser = launch(pw)
    mp = pytest.MonkeyPatch()
    for key, value in {"ORKCRAFT_SETTINGS_FILE": tmp / "settings.json", "ORKCRAFT_LOOK": "office",
                       "XDG_CACHE_HOME": tmp / "cache", "XDG_CONFIG_HOME": tmp / "config", "ORKCRAFT_ONBOARDING": "0",
                       "ORKCRAFT_LIMITS": "0", "ORKCRAFT_NO_UPDATE": "1", "ORKCRAFT_MODEL_LIST": "0",
                       "ORKCRAFT_STATE_DIR": tmp / "state"}.items():
        mp.setenv(key, str(value))
    repo = tmp / "project"
    (repo / "src").mkdir(parents=True)
    (repo / "README.md").write_text("# Demo project\n\nA small project for the browser check.\n", encoding="utf-8")
    (repo / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    git = ["git", "-c", "user.email=test@orkcraft.local", "-c", "user.name=Test Runner"]
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run([*git, "add", "-A"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-qm", "init"], cwd=repo, check=True)
    server = Server(Orkboard(repo))
    thread = server.start_thread()
    yield server, browser
    browser.close()
    pw.stop()
    server.stop()
    thread.join(10)
    mp.undo()
