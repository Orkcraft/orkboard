"""The gate's command and files for a repository (docs/specs/37-board-and-line.md §5).

    gate = read(repo_root)                       # orkcraft.toml `[gate]`, else today's gate (pytest on the critical tests)
    files = gate_files(gate, touched, worktree)  # `always`, then the touched files' tests that exist
    argv = test_argv(command)                    # words, or `sh -c` when the command needs a shell

`orkcraft.toml` is tracked at the repository's root; an unknown key is ignored, a bad file is said in `Gate.error`
and the gate runs as with no file."""
from __future__ import annotations

import shlex
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

FILE = "orkcraft.toml"
CRITICAL_TESTS = ("tests/test_architecture.py", "tests/test_cli.py", "tests/test_updates.py")
DEFAULT_MAP = ("tests/test_{stem}.py",)
_SHELL = ("&&", "||", "|", ";", "$(", "`", ">", "<", "*", "~")   # what only a shell reads in a command line


def test_argv(cmd: str) -> list[str]:
    """The operator's test command as a process to start: as words, or through `sh -c` when it needs a shell
    (`pytest -q && ruff check .`: split into words, `&&` reached pytest as an argument and every run failed)."""
    if any(mark in cmd for mark in _SHELL):
        return ["sh", "-c", cmd]
    return shlex.split(cmd)


@dataclass(frozen=True)
class Gate:
    run: str = ""                                  # "" = today's gate: pytest on the files
    always: tuple[str, ...] = CRITICAL_TESTS
    map: tuple[str, ...] = DEFAULT_MAP
    timeout_min: float | None = None               # None = the caller's default
    error: str = field(default="", compare=False)  # a bad file, in words

    @property
    def custom(self) -> bool:
        return bool(self.run)


def _strings(value: object, key: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"[gate] {key} must be a list of strings")
    return tuple(value)


def read(repo_root: Path) -> Gate:
    """The repository's `[gate]`; today's gate with no file or no `[gate]`, and with a bad file (`error` says why)."""
    path = Path(repo_root) / FILE
    if not path.is_file():
        return Gate()
    try:
        table = tomllib.loads(path.read_text(encoding="utf-8")).get("gate")
        if table is None:
            return Gate()
        if not isinstance(table, dict):
            raise ValueError("[gate] must be a table")
        run = table.get("run", "")
        if not isinstance(run, str):
            raise ValueError("[gate] run must be a string")
        minutes = table.get("timeout_min")
        if minutes is not None and (isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or minutes <= 0):
            raise ValueError("[gate] timeout_min must be a number of minutes above 0")
        return Gate(run=run.strip(), always=_strings(table.get("always", list(CRITICAL_TESTS)), "always"),
                    map=_strings(table.get("map", list(DEFAULT_MAP)), "map"), timeout_min=minutes)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, ValueError) as e:
        return Gate(error=f"{FILE} is not usable ({' '.join(str(e).split())[:200]}): the gate ran as with no file")


def gate_files(gate: Gate, touched: list[str], root: Path) -> list[str]:
    """`always`, then each touched file's tests by `map` (`{stem}`, `{name}`, `{dir}`); only those that exist. With no
    `run` (today's gate) a touched test file counts as its own test."""
    out = [a for a in gate.always]
    for name in touched:
        p = Path(name)
        if not gate.custom and p.parts[:1] == ("tests",) and p.suffix == ".py" and p.name.startswith("test_"):
            out.append(p.as_posix())
            continue
        if p.stem == "__init__":
            continue
        if not gate.custom and p.suffix != ".py":
            continue
        for pattern in gate.map:
            out.append(pattern.replace("{stem}", p.stem).replace("{name}", p.name).replace("{dir}", p.parent.as_posix()))
    seen: list[str] = []
    for f in out:
        if f not in seen and (Path(root) / f).is_file():
            seen.append(f)
    return seen


def command(gate: Gate, files: list[str]) -> str | None:
    """The custom command with `{files}` filled in (quoted); as is without `{files}`. None: it needs files and has none."""
    if "{files}" not in gate.run:
        return gate.run
    if not files:
        return None
    return gate.run.replace("{files}", " ".join(shlex.quote(f) for f in files))
