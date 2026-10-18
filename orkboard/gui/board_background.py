"""A command that may take long, run off the server's thread (docs/specs/37-board-and-line.md §8): a pull or a push
talks to origin for up to 120 s, and the server answers every page command on one thread.

    background = Background()
    background.start(project, "git", "push", work)    # {"started": True}; a second one in the group is refused
    background.running(project, "git")                # the name of the one running, or ""

`work()` runs on a thread of its own and returns what to say, or raises `ValueError` / `IdeasError` (in words). The
outcome is published on the project's bus (`RAN`: group, op, ok, said), on the host's thread, and kept as the group's
`last` until the next one starts. The page asks `git.status` while it runs.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

from orkboard.gui.ideas_args import IdeasError

RAN = "background.ran"          # group, op, ok, said: a command run off the server's thread finished


class Background:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running: dict[tuple[str, str], str] = {}
        self._last: dict[tuple[str, str], dict] = {}

    def running(self, project: Any, group: str) -> str:
        with self._lock:
            return self._running.get((project.path, group), "")

    def last(self, project: Any, group: str) -> dict | None:
        with self._lock:
            return self._last.get((project.path, group))

    def start(self, project: Any, group: str, op: str, work: Callable[[], str],
              then: Callable[[], None] | None = None) -> dict:
        """Starts `work` and answers at once; one at a time per project and group, a second is refused in words.
        `then` runs on the host's thread after a success (a refresh of the Board)."""
        key = (project.path, group)
        with self._lock:
            if key in self._running:
                return {"error": f"a {self._running[key]} is already running"}
            self._running[key] = op
            self._last.pop(key, None)
        threading.Thread(target=self._run, args=(project, key, group, op, work, then), daemon=True,
                         name=f"orkboard-{group}-{op}").start()
        return {"started": True}

    def _run(self, project: Any, key: tuple[str, str], group: str, op: str, work: Callable[[], str],
             then: Callable[[], None] | None) -> None:
        ok, said = True, ""
        try:
            said = work() or ""
        except (ValueError, IdeasError) as e:
            ok, said = False, str(e)
        except Exception as e:                      # an outcome always arrives, whatever went wrong
            ok, said = False, f"{type(e).__name__}: {e}"
        with self._lock:
            self._running.pop(key, None)
            self._last[key] = {"op": op, "ok": ok, "said": said}

        def publish() -> None:
            if ok and then is not None:
                then()
            project.bus.publish(RAN, group=group, op=op, ok=ok, said=said)
        project.host.call(publish)
