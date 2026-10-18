"""The open projects (docs/specs/37-board-and-line.md §8): several at once, one shown, each with its own Board.

    projects = Projects(host)
    projects.open(path)              # a folder becomes a project (refused in words), and the shown one
    projects.current()               # the shown project (None: the start screen)
    projects.use(path)               # another open project is shown: nothing of the others stops
    projects.close(path, stop=True)  # its keeper and runner stop; it leaves the switcher
    projects.commands()              # projects.* and the Board's ideas.*, which reach the shown project

A project is a repository's folder; its Board is a `BoardHost` (gui/board_host.py) with a bus of its own, its
`Ideas` (keeper, runner, claims, night) and its day logs: an event of one Board never reaches another's. The host's
own services (the limits, the spend, the phones, updates, the onboarding) are the host's, once per host, not per
project. The open projects and the recent ones are the machine's settings (`projects_open`, `projects_recent`).
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from orkboard import settings
from orkboard.core import bus as b
from orkboard.gui.board_host import BoardHost, BoardLogs
from orkboard.gui.ideas_args import IdeasError, _device, _str
from orkboard.realm import call_log, event_log, project_folder

NO_PROJECT = "Open a folder first"


class Project:
    """One open project: its folder, its Board (`BoardHost`, `Ideas`) on a bus of its own, its day logs."""

    def __init__(self, root: Path, host: Any) -> None:
        from orkboard.gui.ideas import Ideas
        self.root = Path(root)
        self.path = str(self.root)
        self.name = self.root.name or self.path
        self.host = host
        self.bus = b.Bus()
        self.logs = BoardLogs(self.root)
        self.board = BoardHost(self.root, host, bus=self.bus, toast=self.toast, call=lambda fn, *a: host.call(fn, *a),
                               budget_ok=lambda: host.budget_ok(self.root), limits=lambda: host.limits(),
                               day_logs=self.logs, demo=host.demo)
        self.ideas = Ideas(self.board)
        self.commands: dict[str, Callable[[dict], Any]] = self.ideas.commands()
        self._off = self.bus.subscribe(b.ANY, host._event)

    def toast(self, message: str, title: str = "", severity: str = "information", timeout: float | None = None,
              kind: str = "") -> None:
        """The host's toast; with more than one project open it names its project."""
        if len(self.host.projects.open_ones) > 1:
            title = f"{self.name} · {title}" if title else self.name
        self.host.toast(message, title=title, severity=severity, timeout=timeout, kind=kind)

    def counts(self) -> dict[str, int]:
        """What the switcher says of it: its ideas at work, what needs the person, the results at Review."""
        snap = self.ideas.snapshot()
        return {"working": sum(1 for i in snap["idea_states"] if i["state"] == "working"),
                "needs_you": int(snap["needs_you"]), "review": int(snap["review_count"])}

    def close(self) -> None:
        self.ideas.stop_all()
        self.ideas.tree_flush(force=True)
        self._off()


class Projects:
    def __init__(self, host: Any) -> None:
        self.host = host
        self._open: dict[str, Project] = {}
        self._current = ""

    # -- reading ---------------------------------------------------------------------------------------------

    @property
    def open_ones(self) -> list[Project]:
        return list(self._open.values())

    def current(self, need: bool = False) -> Project | None:
        got = self._open.get(self._current)
        if got is None and need:
            raise IdeasError(NO_PROJECT)
        return got

    def _find(self, path: object) -> Project:
        key = _key(path)
        if key not in self._open:
            raise IdeasError("That project is not open")
        return self._open[key]

    def list(self, args: dict | None = None) -> dict[str, Any]:
        """`projects.list`: the shown project, the open ones with their counts, and the recent ones not open."""
        rows = []
        for p in self._open.values():
            try:
                counts = p.counts()
            except Exception:                   # a broken Board never breaks the switcher
                counts = {"working": 0, "needs_you": 0, "review": 0}
            rows.append({"path": p.path, "name": p.name, **counts})
        recent = [{"path": r, "name": Path(r).name or r} for r in self.host.machine.projects_recent
                  if r not in self._open and Path(r).is_dir()]
        return {"current": self._current or None, "open": rows, "recent": recent}

    # -- the switcher's commands -----------------------------------------------------------------------------

    def open(self, path: object, device: str = "desktop", show: bool = True, keep: bool = True) -> Project:
        """The folder as an open project (an open one is only shown again); refused in words. `show`: it becomes
        the shown one; `keep`: the machine's settings remember it."""
        why = project_folder.refusal(str(path or ""))
        if why:
            raise IdeasError(why)
        key = _key(path)
        got = self._open.get(key)
        if got is None:
            m = self.host.machine
            new = key not in m.projects_open and key not in m.projects_recent
            got = self._open[key] = Project(Path(key), self.host)
            if not self.host.demo:
                event_log.record(got.root, event_log.PROJECT_OPENED, new=new, git=project_folder.has_git(got.root),
                                 device=device)
        if show or not self._current:
            self._show(got)
        else:                                   # its day logs took the call log: it stays the shown one's
            call_log.keep_days(self.current().root)
        if keep:
            self._remember()
        self.host.on_change()
        return got

    def _show(self, project: Project) -> None:
        self._current = project.path
        recent = self.host.machine.projects_recent
        self.host.machine.projects_recent = [project.path, *[r for r in recent if r != project.path]][
            :settings.PROJECTS_RECENT]
        self.host.shown(project)

    def _remember(self) -> None:
        self.host.machine.projects_open = list(self._open)[:settings.PROJECTS_OPEN]
        if not self.host.demo:
            settings.save(self.host.machine)

    def use(self, path: object) -> None:
        self._show(self._find(path))
        self._remember()
        self.host.on_change()

    def close(self, path: object, stop: bool = False) -> int:
        """The project leaves the switcher, its keeper and runner stopped; with tasks running and no `stop`, nothing
        is done and their count is returned."""
        project = self._find(path)
        running = project.ideas.running()
        if running and not stop:
            return running
        project.close()
        if not self.host.demo:
            event_log.record(project.root, event_log.PROJECT_CLOSED, stopped=bool(running))
        del self._open[project.path]
        if self._current == project.path:
            self._current = ""
            if self._open:
                self._show(next(iter(self._open.values())))
            else:
                self.host.shown(None)
        self._remember()
        self.host.on_change()
        return 0

    def restore(self) -> None:
        """The projects open when the host last closed, opened again (a folder that went or is refused is
        dropped); the last shown of them is shown."""
        for path in list(self.host.machine.projects_open):
            try:
                self.open(path, show=False, keep=False)
            except IdeasError:
                pass
        last = next((r for r in self.host.machine.projects_recent if r in self._open), "")
        if last:
            self._show(self._open[last])
        self._remember()

    # -- every Board ----------------------------------------------------------------------------------------

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        for p in list(self._open.values()):
            p.ideas.tick(now)

    def stop_all(self, device: str = "desktop") -> None:
        for p in list(self._open.values()):
            p.ideas.stop_all(device=device)

    def close_all(self) -> None:
        for p in list(self._open.values()):
            p.close()

    def commands(self) -> dict[str, Callable[[dict], Any]]:
        """`projects.*`, and the Board's `ideas.*`, each sent to the shown project's Board."""
        def board(name: str) -> Callable[[dict], Any]:
            return lambda a: self.current(need=True).commands[name](a)

        out: dict[str, Callable[[dict], Any]] = {name: board(name) for name in _board_commands()}
        out.update({
            "projects.list": self.list,
            "projects.open": self._open_cmd,
            "projects.start_git": self._start_git,
            "projects.use": lambda a: self.use(_path(a)) or {"ok": True},
            "projects.close": self._close_cmd,
        })
        return out

    def _open_cmd(self, args: dict) -> dict:
        try:
            project = self.open(_path(args), device=_device(args))
        except IdeasError as e:
            return {"error": str(e)}
        return {"ok": True, "git": project_folder.has_git(project.root)}

    def _start_git(self, args: dict) -> dict:
        try:
            said = project_folder.start_git(_path(args))
        except ValueError as e:
            return {"error": str(e)}
        self.host.on_change()
        return {"ok": True, "said": said or "Git was already here"}

    def _close_cmd(self, args: dict) -> dict:
        stop = args.get("stop", False)
        if not isinstance(stop, bool):
            raise IdeasError("stop is true or false")
        running = self.close(_path(args), stop=stop)
        return {"running": running} if running else {"ok": True}


def _key(path: object) -> str:
    """An open project's key: its folder, absolute and resolved."""
    try:
        return str(Path(str(path)).expanduser().resolve())
    except (OSError, RuntimeError):
        raise IdeasError("That folder cannot be read") from None


def _path(args: dict) -> str:
    path = _str(args, "path", 1000).strip()
    if not path:
        raise IdeasError("path is missing")
    return path


class _Names:
    """Stands in for an `Ideas` while its command table is read for its names only."""

    def __getattr__(self, name: str) -> Any:
        return lambda *a, **k: None


def _board_commands() -> list[str]:
    from orkboard.gui.ideas import Ideas
    return list(Ideas.commands(_Names()))      # type: ignore[arg-type]
