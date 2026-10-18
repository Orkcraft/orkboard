"""The core and the domain have no face (docs/design/gui-migration.md §2): they never import the GUI, and
nothing imports a terminal toolkit — the terminal UI is gone (docs/design/calm-town.md §9).

Every import counts, a lazy one inside a function too."""
from __future__ import annotations

import ast
from fnmatch import fnmatchcase
from pathlib import Path

import pytest

from orkboard import layers

ROOT = Path(__file__).resolve().parents[1] / "orkboard"
FACELESS = ["core", "realm", "design"]
FORBIDDEN = ("textual", "rich")


def _imports(path: Path) -> list[tuple[int, str]]:
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out += [(node.lineno, a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.append((node.lineno, node.module))
    return out


@pytest.mark.parametrize("package", FACELESS)
def test_no_face_in(package):
    bad = []
    for path in sorted((ROOT / package).rglob("*.py")):
        for line, module in _imports(path):
            top = module.split(".")[0]
            if top in FORBIDDEN or module.startswith("orkboard.gui"):
                bad.append(f"{path.relative_to(ROOT.parent)}:{line} imports {module}")
    assert not bad, "\n".join(bad)


def test_loading_the_core_loads_no_face():
    """Transitively too: importing every module of core/, realm/ and design/ pulls in no toolkit."""
    import subprocess
    import sys
    modules = [f"orkboard.{p.relative_to(ROOT).with_suffix('').as_posix().replace('/', '.')}"
               for package in FACELESS for p in sorted((ROOT / package).rglob("*.py"))]
    modules = [m.removesuffix(".__init__") for m in modules]
    code = ("import importlib, sys\n"
            f"for m in {modules!r}: importlib.import_module(m)\n"
            "print(sorted({n.split('.')[0] for n in sys.modules} & {'textual', 'rich'}))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]", out.stdout + out.stderr


def test_the_terminal_ui_stays_gone():
    """No module imports Textual or Rich, and the TUI's packages do not come back."""
    bad = [f"{path.relative_to(ROOT.parent)}:{line} imports {module}"
           for path in sorted(ROOT.rglob("*.py")) for line, module in _imports(path)
           if module.split(".")[0] in FORBIDDEN]
    bad += [f"orkboard/{name} is back" for name in ("tui", "screens", "widgets", "wm", "app.py", "theme.py")
            if (ROOT / name).is_file() or any((ROOT / name).rglob("*.py"))]
    assert not bad, "\n".join(bad)


# A module that knows the agent tools (`realm/harnesses.py`) and starts processes itself registers them in
# `realm/halt.py`, the one list of what runs: the HUD counts agents from it and 🛑 Stop all kills what is on it.
# These start only short commands that are not agents, or keep their own list (tech-debt T13).
STARTS_WITHOUT_HALT = {
    "realm/model_families.py": "asks a tool for its model list; no model runs",
    "realm/masonry.py": "git log",
    "sources/sessions.py": "git log",
    "tools.py": "a tool's version and login state",
    "core/sessions.py": "the Terminals' sessions; Stop all interrupts them through Sessions.interrupt_all",
}
_STARTS = {("subprocess", "Popen"), ("subprocess", "run"), ("subprocess", "call"), ("subprocess", "check_output"),
           ("pty", "fork"), ("os", "execvpe"), ("os", "execvp")}


def _starts_and_names(path: Path) -> tuple[bool, set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    starts = any(isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and (n.value.id, n.attr) in _STARTS
                 for n in ast.walk(tree))
    names = {m.split(".")[-1] for _line, m in _imports(path)}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            names |= {a.name for a in n.names}
    return starts, names


def test_whoever_starts_an_agent_registers_it_in_halt():
    bad = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel == "realm/halt.py":
            continue
        starts, names = _starts_and_names(path)
        if starts and "harnesses" in names and "halt" not in names and rel not in STARTS_WITHOUT_HALT:
            bad.append(f"{rel} starts processes and knows the agent tools, but never uses realm/halt.py")
    assert not bad, "\n".join(bad)
    assert all((ROOT / rel).is_file() for rel in STARTS_WITHOUT_HALT), "a listed module is gone: drop it from the list"


# Orkboard and Orkline (docs/specs/37-board-and-line.md): the modules of `layers.BOARD` import only each other. Every
# edge out of it is listed here, `importer → imported`, and the list only shrinks (spec 37 B and C cut them).
KNOWN: set[tuple[str, str]] = set()


def _new_edges(found, known):
    return [f"{layers.short(a)} imports {layers.short(b)} ({path.relative_to(ROOT.parent)}:{line}): cut it, or add "
            f"the module to BOARD when all its own imports are Orkboard's"
            for a, b, path, line in found if (layers.short(a), layers.short(b)) not in known]


def test_orkboard_imports_only_orkboard():
    bad = _new_edges(layers.edges(), KNOWN)
    assert not bad, "\n".join(bad)


def test_orkboard_check_sees_a_line_import(tmp_path):
    """The check can fail: a Board module importing a line module (absolute, relative or lazy) is an edge."""
    pkg = tmp_path / "orkboard"
    (pkg / "core").mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "core" / "__init__.py").write_text("")
    (pkg / "core" / "idea_x.py").write_text(
        "from orkboard import camp\nfrom .. import camp as c2\n\ndef f():\n    import orkboard.camp\n")
    (pkg / "camp.py").write_text("")
    mods = {"orkboard": pkg / "__init__.py", "orkboard.core": pkg / "core" / "__init__.py",
            "orkboard.core.idea_x": pkg / "core" / "idea_x.py", "orkboard.camp": pkg / "camp.py"}
    found = layers.edges(root=mods)
    assert sorted(line for _a, _b, _p, line in found) == [1, 2, 5]
    assert {(a, b) for a, b, _p, _l in found} == {("orkboard.core.idea_x", "orkboard.camp")}


def test_known_edges_still_exist():
    present = {(layers.short(a), layers.short(b)) for a, b, _p, _l in layers.edges()}
    gone = sorted(KNOWN - present)
    assert not gone, "\n".join(f"{a} -> {b} is gone from the code: remove it from KNOWN" for a, b in gone)


def test_every_board_pattern_matches():
    names = set(layers.modules())
    dead = [p for p in layers.BOARD + layers.SPLIT if not any(fnmatchcase(n, p) for n in names)]
    assert not dead, f"matches no module: {dead}"


def test_orkboard_starts_alone(tmp_path):
    """Spec 37 §4: in a fresh interpreter, Orkboard's host and its server, built on a fixture repository (no port
    opened), load only `BOARD` modules of the package: none of the town's (a namespace package, `orkboard.realm`,
    holds no code of its own)."""
    import os
    import subprocess
    import sys
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    code = ("import sys\n"
            "from orkboard.gui.board_host import Orkboard\n"
            "from orkboard.gui.server import Server\n"
            f"host = Orkboard({str(repo)!r})\n"
            "server = Server(host)\n"
            "assert host.command('ideas.board')['tracks'] is not None and server.page()\n"
            "print('\\n'.join(sorted(n for n, m in list(sys.modules.items())\n"
            "                          if (n == 'orkboard' or n.startswith('orkboard.')) and getattr(m, '__file__', None))))")
    env = {**os.environ, "ORKCRAFT_SETTINGS_FILE": str(tmp_path / "settings.json"),
           "XDG_CONFIG_HOME": str(tmp_path / "config"), "ORKCRAFT_NO_UPDATE": "1"}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=tmp_path)
    assert out.returncode == 0, out.stderr
    loaded = out.stdout.split()
    assert "orkboard.gui.board_host" in loaded and "orkboard.gui.ideas" in loaded and "orkboard.gui.server" in loaded
    line = [n for n in loaded if not layers.matches(n)]
    assert not line, f"Orkboard loaded the line's modules: {line}"
