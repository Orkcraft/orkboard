"""The repository's parts and how they depend on one another, for the architect's lens (realm/idea_lens.py): each folder
of source files is a part; a part uses another when one of its files imports one of the other's. Python's `import` and
`from … import`, JavaScript's and TypeScript's `import … from "./…"`, `import("./…")` and `require("./…")` are read;
what is imported from outside the repository is left out.

    parts(root)        # [{"path": "orkboard/realm", "files": ["ideas.py", …], "count": 40, "uses": [...], "used_by": [...]}]

Folders git and the machine keep (.git, .orkcraft), installed packages and builds are not read, nor a file that may hold
a secret. At most MAX_FILES files are read. No face, no model.
"""
from __future__ import annotations

import re
from pathlib import Path

from orkboard.hooks.warder import is_secret

SKIP = {".git", ".orkcraft", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", ".next", ".tox",
        ".mypy_cache", ".pytest_cache", "site-packages", "coverage", ".idea", ".vscode"}
PY = {".py"}
JS = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}
MAX_FILES = 4000
MAX_BYTES = 400_000
FILES_SHOWN = 60

_PY_FROM = re.compile(r"^\s*from\s+(\.*)([\w.]*)\s+import\s+([\w*, ()]+)", re.M)
_PY_IMPORT = re.compile(r"^\s*import\s+([\w.]+(?:\s*,\s*[\w.]+)*)", re.M)
_JS = re.compile(r"""(?:\bfrom\s*|\bimport\s*\(\s*|\brequire\s*\(\s*|^\s*import\s+)["'](\.{1,2}/[^"']+)["']""", re.M)


def _sources(root: Path) -> list[Path]:
    out: list[Path] = []
    stack = [root]
    while stack and len(out) < MAX_FILES:
        d = stack.pop()
        try:
            entries = sorted(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.name in SKIP or (e.name.startswith(".") and e.is_dir()):
                continue
            if e.is_symlink():
                continue
            if e.is_dir():
                stack.append(e)
            elif e.suffix in PY | JS and not is_secret(e.relative_to(root).as_posix()):
                out.append(e)
                if len(out) >= MAX_FILES:
                    break
    return out


def _part(rel: Path) -> str:
    return rel.parent.as_posix() if rel.parent.as_posix() != "." else "."


def _py_targets(root: Path, rel: Path, text: str, known: set[str]) -> set[str]:
    """The repository files a Python file imports, as paths relative to the root."""
    got: set[str] = set()

    def find(dotted: str, base: Path | None = None) -> None:
        bits = [b for b in dotted.split(".") if b]
        start = base if base is not None else Path()
        for n in range(len(bits), 0, -1):             # the longest that is a file or a package of the repository
            p = start.joinpath(*bits[:n])
            for cand in (p.with_suffix(".py").as_posix(), (p / "__init__.py").as_posix()):
                if cand in known:
                    got.add(cand)
                    return
        if base is not None and not bits:
            init = (start / "__init__.py").as_posix()
            if init in known:
                got.add(init)

    for dots, mod, names in _PY_FROM.findall(text):
        if dots:
            base = rel.parent
            for _ in range(len(dots) - 1):
                base = base.parent
            find(mod, base)
            if not mod:                                    # `from . import a, b`: each a module beside it
                for name in re.findall(r"\w+", names):
                    find(name, base)
        else:
            find(mod)
            for name in re.findall(r"\w+", names):         # `from pkg import module`
                find(f"{mod}.{name}")
    for line in _PY_IMPORT.findall(text):
        for mod in re.split(r"\s*,\s*", line):
            find(mod.strip())
    return got


def _js_targets(rel: Path, text: str, known: set[str]) -> set[str]:
    got: set[str] = set()
    for spec in _JS.findall(text):
        p = (rel.parent / spec).as_posix()
        parts: list[str] = []
        for bit in p.split("/"):
            if bit == "..":
                if parts:
                    parts.pop()
            elif bit not in ("", "."):
                parts.append(bit)
        base = "/".join(parts)
        for cand in (base, *(base + e for e in JS), *(f"{base}/index{e}" for e in JS)):
            if cand in known:
                got.add(cand)
                break
    return got


def parts(root: Path) -> list[dict]:
    """The repository's parts: each folder of source files, its files, the parts it uses and the parts that use it."""
    root = Path(root)
    files = _sources(root)
    rels = [f.relative_to(root) for f in files]
    known = {r.as_posix() for r in rels}
    names: dict[str, list[str]] = {}
    uses: dict[str, set[str]] = {}
    for f, rel in zip(files, rels):
        part = _part(rel)
        names.setdefault(part, []).append(rel.name)
        uses.setdefault(part, set())
        try:
            if f.stat().st_size > MAX_BYTES:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        found = _py_targets(root, rel, text, known) if f.suffix in PY else _js_targets(rel, text, known)
        uses[part] |= {_part(Path(t)) for t in found} - {part}
    used_by: dict[str, set[str]] = {p: set() for p in names}
    for p, us in uses.items():
        for u in us:
            used_by.setdefault(u, set()).add(p)
    return [{"path": p, "files": sorted(names[p])[:FILES_SHOWN], "count": len(names[p]),
             "uses": sorted(uses.get(p, ())), "used_by": sorted(used_by.get(p, ()))} for p in sorted(names)]
