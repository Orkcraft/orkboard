"""The runner's part of Pick one (docs/specs/51-pick-one.md §2.2, §2.3): a task that makes variants ends by waiting for the person,
and the person's answer carries it on. `PickMixin` is on `IdeaRunner` (core/idea_runner.py, which imports this one).

    runner.pick(slug, tid, "B", "a bit darker", device="phone", via="hand")   # the variant B is committed at the plan's target
    runner.pick(slug, tid, None, "rounder, please")                           # none of them: the task runs again as its next round

After its session a task that makes variants leaves its files and manifest in the worktree (realm/idea_pick.py `read`). They move to
the goal's state folder and the task is `picking`: it holds its worktree and branch, spends nothing and waits (Stop all leaves it
be; Drop ends it). **A key**: the picked file is written to `target` in the task's worktree and committed alone (*<task>: B · <name>*),
and the task goes on as any task with a change does (the gate, then Review or the merge as the project says), the note told to the tasks
that wait for it. **None**: a note is required; the task runs again as the next round and the last round's variants stay as history.
"""
from __future__ import annotations

import datetime as dt
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any

from orkboard.core.idea_review import RunnerError
from orkboard.realm import event_log, idea_pick

ANSWERED = "That pick is answered already"


def _r():
    """The runner's module (it imports this one: looked up when a command runs)."""
    from orkboard.core import idea_runner
    return idea_runner


class PickMixin:
    """Needs the runner's `state_dir`, `git`, `_lock`, `_runs`, `_active`, `_task`, `_set_task`, `_set_idea`, `_spawn`, `_emit`, `_log`,
    `_role` and `tick`."""

    def _variants(self, slug: str, tid: str, task: dict, path: Path, start_sha: str, rnd: int) -> bool:
        """After the session of a task that makes variants: read them, move them to the goal's state folder, put the worktree back as it
        was cut, and wait for the person (True). A pick that is missing, broken, of another kind or over a limit fails the task with the
        reason in plain words (RuntimeError, the files removed)."""
        variants, why = idea_pick.read(path, task)
        if why:
            idea_pick.discard(path)
            raise RuntimeError(why)
        ask = idea_pick.ask_of(task) or {}
        idea_pick.store(self.state_dir, slug, task, rnd, variants, by=self._role(task)["slug"])
        idea_pick.discard(path)
        self.git.restore(path, start_sha)                          # "change nothing else": what else it did is not wanted
        self._set_task(slug, tid, state="picking", finished=_r().now_iso(), error="", note="", conflict="")
        self._emit(event_log.PICK_ASKED, idea=slug, task=tid, n=ask["n"], media=ask["kind"], round=rnd)
        self._log(slug, tid, f"== {idea_pick.count_words(ask['n'], idea_pick.KINDS[ask['kind']])} to pick from · {_r().now_iso()}\n")
        return True

    def _take(self, slug: str, task: dict, pick: dict, variant: dict) -> str:
        """Write the variant to the pick's target in the task's worktree and commit it, alone; its message. RunnerError in words."""
        target = idea_pick.clean_target(pick.get("target"))
        message = f"{task.get('title') or task.get('id')}: {variant['key']} · {variant['name']}"
        if not target:
            raise RunnerError("The place the plan names for it is not one a file can be written to")
        try:
            path = self.git.reopen(slug, str(task.get("id")))
            dest, root = path / target, os.path.realpath(path)
            if os.path.commonpath([root, os.path.realpath(dest.parent)]) != root:
                raise RunnerError("The place the plan names for it is outside the project")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.is_symlink():                                          # a link of the project's own is replaced, never followed out of it
                dest.unlink()
            shutil.copyfile(idea_pick.folder_of(self.state_dir, slug, str(pick["id"])) / variant["file"], dest)
            self.git.commit_file(path, target, message)
        except RunnerError:
            raise
        except (OSError, RuntimeError) as e:
            raise RunnerError(" ".join(str(e).split())[:300] or "The picked file could not be committed") from None
        return message

    def pick(self, slug: str, tid: str, key: str | None, note: str = "", device: str = "desktop", via: str = "") -> None:
        """The person's answer to a task that waits for a pick. `key`: a variant's letter, or None for none of them (then `note`, what to
        change, is required). RunnerError, in plain words, when it is answered already or the task is not `picking`."""
        note = str(note or "").strip()[:idea_pick.NOTE_MAX]
        with self._lock:
            task = self._task(slug, tid)
            pick = idea_pick.current(self.state_dir, slug, task) if task.get("state") == "picking" else None
            if pick is None or idea_pick.answered(pick) or (slug, tid) in self._runs:
                raise RunnerError(ANSWERED)
            keys = [str(v.get("key")) for v in pick["variants"]]
            key = str(key).strip().upper() if key is not None else None
            if key is None and not note:
                raise RunnerError("A note says what to change: write one first")
            if key is not None and key not in keys:
                raise RunnerError(f"Pick one of {', '.join(keys)}")
            rnd = int(task.get("round") or 1)
            asked = _since(pick.get("at"))
            if key is None:
                idea_pick.answer(self.state_dir, slug, pick, None, note)
                self._set_task(slug, tid, state="running", round=rnd + 1, why=note, error="", note="", finished="", conflict="")
                again: dict[str, Any] = {"why": note, "files": [], "pick": True}
            else:
                variant = next(v for v in pick["variants"] if v.get("key") == key)
                self._take(slug, task, pick, variant)                         # before anything is said answered: a refusal leaves it asked
                idea_pick.answer(self.state_dir, slug, pick, key, note)
                self._set_task(slug, tid, state="running", why="", error="", note=note, finished="", conflict="",
                               picked={"key": key, "name": variant["name"], "note": note})
                again = {"why": "", "files": [], "taken": True}
            self._emit(event_log.PICK_ANSWERED, idea=slug, task=tid, key=key, note_chars=len(note),
                       via=via, seconds=asked, device=device or "desktop", round=rnd)
            if slug not in self._active:
                self._active.append(slug)
                self._set_idea(slug, "working")
            self._spawn(slug, tid, threading.Event(), again)
        self._changed(slug)


def _since(iso: object) -> float | None:
    """Seconds since an ISO time (None when it is not one)."""
    try:
        return round(max(0.0, time.time() - dt.datetime.fromisoformat(str(iso)).timestamp()), 1)
    except ValueError:
        return None
