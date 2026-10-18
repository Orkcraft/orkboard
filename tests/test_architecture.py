"""The core and the domain have no face: they never import the GUI, and nothing imports a terminal toolkit. Orkboard
stands alone (docs/specs/37-board-and-line.md §9): every import of the package names one of its own modules, and it
starts with no module of Orkline's (`orkcraft`) present.

Every import counts, a lazy one inside a function too."""
from __future__ import annotations

import ast
from fnmatch import fnmatchcase
from pathlib import Path

import pytest

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
    "sources/sessions.py": "git log",
    "tools.py": "a tool's version and login state",
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


# Orkboard stands alone (docs/specs/37-board-and-line.md §9): it was cut from Orkline along `layers.BOARD`, so every
# module is Orkboard's. What is left of that boundary: each import of the package names a module of the package.
PACKAGE = "orkboard"


def modules(root: Path = ROOT) -> dict[str, Path]:
    """Every module of the package by dotted name (a package's `__init__` is the package's name)."""
    out = {}
    for path in sorted(root.rglob("*.py")):
        parts = list(path.relative_to(root.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        out[".".join(parts)] = path
    return out


def packages(mods: dict[str, Path]) -> set[str]:
    """The packages the modules sit in, a namespace package (`orkboard.realm`, no `__init__`) too."""
    return {name.rsplit(".", n)[0] for name in mods for n in range(1, name.count(".") + 1)}


def _defined(path: Path | None) -> set[str]:
    """The names a package's `__init__` defines itself (`from orkboard import __version__` is one, not a module)."""
    if path is None:
        return set()
    names = set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names |= {t.id for t in targets if isinstance(t, ast.Name)}
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names |= {(a.asname or a.name).split(".")[0] for a in node.names}
    return names


def missing_imports(mods: dict[str, Path]) -> list[tuple[str, int, str]]:
    """`(file, line, module)` for every import of the package, a lazy and a relative one too, that names no module
    or package of it: `from orkboard.realm import catalog` names `orkboard.realm.catalog`, unless the package's
    `__init__` defines `catalog` itself."""
    known, folders = set(mods), packages(mods)
    out = []
    for name, path in mods.items():
        package = name if path.name == "__init__.py" else name.rpartition(".")[0]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                targets = [(a.name, None) for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    up = package.split(".")[:len(package.split(".")) - (node.level - 1)]
                    base = ".".join(up + ([node.module] if node.module else []))
                targets = [(base, a.name) for a in node.names]
            else:
                continue
            for base, attr in targets:
                if base.split(".")[0] != PACKAGE:
                    continue
                if base not in known and base not in folders:
                    out.append((str(path), node.lineno, base))
                elif (attr and attr != "*" and base in folders and f"{base}.{attr}" not in known | folders
                      and attr not in _defined(mods.get(base))):
                    out.append((str(path), node.lineno, f"{base}.{attr}"))       # a package's name is a module
    return out


def test_every_import_of_the_package_is_one_of_its_modules():
    bad = [f"{Path(f).relative_to(ROOT.parent)}:{line} imports {module}, which is not in the package"
           for f, line, module in missing_imports(modules())]
    assert not bad, "\n".join(bad)


def test_the_check_sees_an_import_of_a_module_that_is_not_here(tmp_path):
    """The check can fail: a module importing one the package does not have (absolute, relative or lazy)."""
    pkg = tmp_path / "orkboard"
    (pkg / "core").mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "core" / "__init__.py").write_text("")
    (pkg / "core" / "idea_x.py").write_text(
        "from orkboard import camp\nfrom .. import camp as c2\nfrom orkboard.core import idea_x\n\n"
        "def f():\n    import orkboard.camp\n")
    found = missing_imports(modules(pkg))
    assert sorted(line for _f, line, _m in found) == [1, 2, 6]
    assert {m for _f, _l, m in found} == {"orkboard.camp"}


def test_orkboard_starts_alone(tmp_path):
    """Spec 37 §9: in a fresh interpreter, Orkboard's host and its server, built on a fixture repository (no port
    opened), load the package's own modules, and no module of Orkline's (`orkcraft`) is there to load."""
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
            "                          if n.split('.')[0] in ('orkboard', 'orkcraft') and getattr(m, '__file__', None))))")
    env = {**os.environ, "ORKCRAFT_SETTINGS_FILE": str(tmp_path / "settings.json"),
           "XDG_CONFIG_HOME": str(tmp_path / "config"), "ORKCRAFT_NO_UPDATE": "1"}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=tmp_path)
    assert out.returncode == 0, out.stderr
    loaded = out.stdout.split()
    assert "orkboard.gui.board_host" in loaded and "orkboard.gui.ideas" in loaded and "orkboard.gui.server" in loaded
    mods = modules()
    line = [n for n in loaded if n not in mods]
    assert not line, f"Orkboard loaded modules that are not its own: {line}"
