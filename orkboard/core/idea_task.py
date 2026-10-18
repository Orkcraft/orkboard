"""A task's own parts of the runner (core/idea_runner.py, which imports this one): the gate on its worktree (`_check`,
`_tests_of`), its environment (`_env`) and its prompt (`_prompt`). `IdeaRunner` has them through `TaskMixin`.
"""
from __future__ import annotations

import threading
from pathlib import Path

from orkboard.realm import idea_secrets
from orkboard.realm.idea_git import BOARD_PAGE, CRITICAL_TESTS, env_name, has_summary, parse_tests, read_secret, spec_paths


def _r():
    """The runner's module (it imports this one: looked up when a task runs)."""
    from orkboard.core import idea_runner
    return idea_runner


class TaskMixin:
    """Needs the runner's `repo_root`, `state_dir`, `settings`, `git`, `_gate_runs` and `_role`."""

    def _tests_of(self, path: Path, out: str, problem: str | None) -> dict:
        """The result's `tests` (spec 37 §5): pytest's counts when its summary line is there, else `null` counts and the
        exit code; `ran` False when the gate found nothing to run; `command` as run."""
        run = self._gate_runs.pop(str(path), None)
        tests = parse_tests(out)
        tests["green"] = problem is None
        tests["ran"] = run.ran if run else True
        tests["command"] = run.command if run else ""
        if run and run.ran:
            tests["exit"] = run.code
            if not has_summary(out):
                tests["passed"] = tests["failed"] = None
        return tests

    def _check(self, path: Path, start_sha: str, cancel: threading.Event, title: str = "") -> tuple[str | None, str]:
        """(None, the gate's run) when the task's work passes; else (what is wrong, in words the session can act on,
        the gate's run: "" when the gate did not run). What the session left uncommitted is committed first, under
        the task's title: its session may edit files but not run git."""
        self.git.commit_left(path, title)
        if not self.git.commits(path, start_sha):
            return "You changed no file. Make the change the task asks for in this worktree.", ""
        board = [f for f in self.git.touched(path, str(_r().setting(self.settings, "merge_into") or "dev")) if BOARD_PAGE.search(f)]
        if board:                          # spec 35 §13: the Board's pages are the Board's
            return f"A task never edits the Board's pages: put back {', '.join(board[:5])} as they were.", ""
        if self.git.dirty(path):
            return ("You left uncommitted changes: `git status` shows them. Commit them (or remove what is not "
                    "work)."), ""
        run = self.git.gate_run(path, start_sha, cancel)
        self._gate_runs[str(path)] = run
        return (None if run.ok else f"The tests failed:\n{run.out[-3000:]}"), run.out

    def _env(self, slug: str, tid: str, plan: dict) -> dict[str, str]:
        """The task's environment: who runs (for the town's counts) and the values of its `secret` to-dos."""
        env = {"ORKCRAFT_ORC": f"ideas/{slug}-{tid}", "ORKCRAFT_IDEA": slug, "ORKCRAFT_TASK": tid}
        for todo in plan.get("todos") or []:
            if not isinstance(todo, dict) or todo.get("kind") != "secret" or tid not in (todo.get("for") or []):
                continue
            name = env_name(str(todo.get("title") or ""))
            value = read_secret(self.state_dir, slug, str(todo.get("id") or "")) if name else None
            if name and value:
                env[name] = value
        return {**env, **idea_secrets.file_env(self.state_dir, slug, plan, tid)}

    # -- the prompt ------------------------------------------------------------------------------

    def _prompt(self, slug: str, plan: dict, task: dict) -> str:
        """Stable first (spec 36 §6): the role's instruction and the finishing rules; then the task's own: where, its
        spec's path, the task, its `after` tasks, the secrets' names. No CLAUDE.md: Claude Code reads it itself."""
        spec, deps = spec_paths(self.repo_root, self.state_dir, slug)
        after = set(task.get("after") or [])
        done = [f"- {t.get('id')} · {t.get('title', '')} ({t.get('state')})"
                + (f" — merged: {'; '.join(t.get('subjects') or [])}" if t.get("state") == "merged" and t.get("subjects") else "")
                + f"\n  {t.get('brief', '')}" for t in plan.get("tasks") or [] if t.get("id") in after]
        env = self._env(slug, task.get("id"), plan)
        files = [n for n in env if n.startswith("ORKCRAFT_FILE_")]
        secrets = [n for n in env if n not in ("ORKCRAFT_ORC", "ORKCRAFT_IDEA", "ORKCRAFT_TASK", *files)]
        parts, role = [], self._role(task)
        if (instruction := str(role.get("instruction") or "").strip()):
            parts.append(f"# Your role: {role['name']}\n\n{instruction}")
        parts.append("# When you are done\n\nCommit your work with git if you can, with clear messages; what you "
                     "leave changed is committed for you under the task's title. Then the gate runs "
                     f"`python -m pytest -q {' '.join(CRITICAL_TESTS)}` and the test files of the modules you touch, "
                     "and a red gate comes back to you once, in this session.")
        parts += [
            f"You do one task of the idea `{slug}` in this repository: a git worktree on branch "
            f"`idea/{slug}/{task.get('id')}`, cut from `{_r().setting(self.settings, 'merge_into') or 'main'}`. "
            "Work only here.",
            "# The idea\n\n" + (f"Its spec is at `{spec}` in this worktree: read it if you need it."
                                  + "".join(f" It depends on `{d}`." for d in deps) if spec else "(its spec was not found)"),
            f"# Your task: {task.get('title', '')}\n\n{task.get('brief', '')}",
        ]
        if done:
            parts.append("# The tasks before yours\n\n" + "\n".join(done))
        if secrets:
            parts.append("The environment holds " + ", ".join(secrets) + ": use them from the environment, never "
                         "print them, write them to a file or commit them.")
        parts += [f"The file is at ${name}; copy it into the repository only if the task says so." for name in files]
        return "\n\n".join(parts)
