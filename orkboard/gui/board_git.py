"""The Git section's commands (docs/specs/37-board-and-line.md §8), on the shown project's root checkout:
`git.status`, `git.diff`, `git.branches`, `git.commit`, `git.switch`, `git.pull`, `git.push` (realm/repo_git.py does the
git). A pull and a push run off the server's thread (gui/board_background.py): they answer `{"started": true}`, and
`git.status` says which one `running` is and the outcome of the last one (`last`).

    git = Git(projects)
    host.commands.update(git.commands())

The work branch is the project's `merge_into` (its Board settings). A commit and a push are recorded in the project's
event log (`git_committed`, `git_pushed`). Desktop only: the phone may send none of them (gui/board_host.py
`BoardPhone`).
"""
from __future__ import annotations

from typing import Any, Callable

from orkboard import settings
from orkboard.gui.board_background import Background
from orkboard.gui.ideas_args import IdeasError, _device, _str
from orkboard.realm import event_log
from orkboard.realm.repo_git import RepoGit


class Git:
    def __init__(self, projects: Any) -> None:
        self.projects = projects
        self.background = Background()

    def _git(self) -> tuple[Any, RepoGit]:
        project = self.projects.current(need=True)
        return project, RepoGit(project.root)

    def _ev(self, project: Any, event: str, **fields: Any) -> None:
        if not project.host.demo:
            event_log.record(project.root, event, **fields)

    def status(self, args: dict) -> dict:
        project, git = self._git()
        work = str(project.board.board_settings().get("merge_into") or settings.IDEAS["merge_into"])
        return {**git.status(work), "running": self.background.running(project, "git"),
                "last": self.background.last(project, "git")}

    def branches(self, args: dict) -> dict:
        """The local branches, the work branch and main first, the current one marked."""
        project, git = self._git()
        work = str(project.board.board_settings().get("merge_into") or settings.IDEAS["merge_into"])
        rows = git.branches()
        rank = {work: 0, "main": 1}
        rows.sort(key=lambda r: (rank.get(r["name"], 2), r["name"].lower()))
        return {"branches": rows}

    def diff(self, args: dict) -> dict:
        return self._git()[1].diff(_str(args, "path", 1000))

    def commit(self, args: dict) -> dict:
        project, git = self._git()
        paths = args.get("paths")
        try:
            sha = git.commit(paths if isinstance(paths, list) else [], args.get("message") or "")
        except ValueError as e:
            return {"error": str(e)}
        self._ev(project, event_log.GIT_COMMITTED, files=len(paths), device=_device(args))
        project.ideas.changed("")
        return {"ok": True, "commit": sha}

    def switch(self, args: dict) -> dict:
        project, git = self._git()
        try:
            git.switch(_str(args, "branch", 200))
        except ValueError as e:
            return {"error": str(e)}
        project.ideas.changed("")
        return {"ok": True}

    def pull(self, args: dict) -> dict:
        project, git = self._git()
        return self.background.start(project, "git", "pull", git.pull, then=lambda: project.ideas.changed(""))

    def push(self, args: dict) -> dict:
        project, git = self._git()
        device = _device(args)

        def work() -> str:
            branch, said = git.push()
            self._ev(project, event_log.GIT_PUSHED, branch=branch, device=device)
            return said
        return self.background.start(project, "git", "push", work)

    def commands(self) -> dict[str, Callable[[dict], Any]]:
        def read(fn: Callable[[dict], Any]) -> Callable[[dict], Any]:
            def run(args: dict) -> Any:
                try:
                    return fn(args)
                except ValueError as e:         # a read git refused: in words, as the Board's
                    raise IdeasError(str(e)) from None
            return run

        return {"git.status": read(self.status), "git.diff": read(self.diff),
                "git.branches": read(self.branches), "git.commit": self.commit,
                "git.switch": self.switch, "git.pull": self.pull, "git.push": self.push}
