"""A task's own parts of the runner (core/idea_runner.py, which imports this one): the gate on its worktree (`_check`,
`_tests_of`), its environment (`_env`) and its prompt (`_prompt`); and how a check task ends (spec 43 §1: `_check_round`,
which reads the findings it wrote). `IdeaRunner` has them through `TaskMixin`.
"""
from __future__ import annotations

import threading
from pathlib import Path

from orkboard.realm import event_log, idea_checks, idea_secrets, library
from orkboard.realm.idea_git import BOARD_PAGE, CRITICAL_TESTS, _git, env_name, has_summary, parse_tests, read_secret, spec_paths

FINDINGS_ASK = (f"When you are done, write what you found to `{idea_checks.FINDINGS_FILE}` at the worktree's root, as JSON: "
                '`{"findings": [{"where": "file:line, or the screen", "what": "one line: what goes wrong", "fixed": true}]}`, '
                'the worst first, at most 20. Write `{"findings": []}` when you found nothing that blocks, and then change '
                "nothing else. Fix only what is small and certain; leave the rest as findings with `\"fixed\": false`.")
NO_CHANGE = "You changed no file"
NO_FINDINGS = "the check said nothing: no findings file"


def is_check(task: dict) -> bool:
    """A check task: its `kind` is a checker's tag (idea_checks.TAGS)."""
    return str(task.get("kind") or "") in idea_checks.TAGS


def checker_of(task: dict) -> str:
    """The slug of the checker whose task it is: the agent the plan gave it, else the library's for its tag."""
    return str(task.get("role") or "") or next((a.id for a in library.LIBRARY if a.check is not None and a.takes[0] == task.get("kind")), "")


FINDINGS_ASK = (
    f"When you are done, write what you found to `{idea_checks.FINDINGS_FILE}` at the worktree's root, as JSON: "
    '`{"findings": [{"where": "file:line, or the screen", "what": "one line: what goes wrong", "fixed": true}]}`, the worst first, '
    'at most 20. Write `{"findings": []}` when you found nothing that blocks, and then change nothing else. Fix only what is small '
    'and certain; leave the rest as findings with `"fixed": false`.')
NO_FINDINGS = "You left no findings file and changed no file. Write your findings file, as the task asks."
NO_RUN = {"passed": 0, "failed": 0, "failing": [], "tail": "", "green": True, "ran": False, "command": ""}      # a check that changed no file: no gate ran
NO_DIFF = {"files": 0, "added": 0, "removed": 0}


def is_check(task: dict) -> bool:
    """A check task: its `kind` is a checker's tag (realm/idea_checks.py `TAGS`)."""
    return str(task.get("kind") or "") in idea_checks.TAGS


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

    def _check(self, path: Path, start_sha: str, cancel: threading.Event, title: str = "", check: bool = False) -> tuple[str | None, str]:
        """(None, the gate's run) when the task's work passes; else (what is wrong, in words the session can act on,
        the gate's run: "" when the gate did not run). What the session left uncommitted is committed first, under
        the task's title: its session may edit files but not run git."""
        self.git.commit_left(path, title)
        if not self.git.commits(path, start_sha):
            return (f"{NO_CHANGE} and wrote no findings file." if check else
                    f"{NO_CHANGE}. Make the change the task asks for in this worktree."), ""
        board = [f for f in self.git.touched(path, str(_r().setting(self.settings, "merge_into") or "dev")) if BOARD_PAGE.search(f)]
        if board:                          # spec 35 §13: the Board's pages are the Board's
            return f"A task never edits the Board's pages: put back {', '.join(board[:5])} as they were.", ""
        if self.git.dirty(path):
            return ("You left uncommitted changes: `git status` shows them. Commit them (or remove what is not "
                    "work)."), ""
        run = self.git.gate_run(path, start_sha, cancel)
        self._gate_runs[str(path)] = run
        return (None if run.ok else f"The tests failed:\n{run.out[-3000:]}"), run.out

    # -- how a check task ends (spec 43 §1.3) ---------------------------------------------------------

    def _take_findings(self, path: Path) -> list[dict] | None:
        """What the check wrote in its findings file (at most 64 KB), which is removed so it is never committed: the
        findings, or None for no file, bad JSON or a bad shape. A file the session committed itself is taken out as well."""
        file = path / idea_checks.FINDINGS_FILE
        try:
            text = file.read_text(encoding="utf-8", errors="replace") if file.stat().st_size <= idea_checks.FINDINGS_BYTES else None
        except OSError:
            text = None
        try:
            file.unlink()
        except OSError:
            pass
        if _git(path, "ls-files", "--error-unmatch", idea_checks.FINDINGS_FILE).returncode == 0:
            _git(path, "rm", "-q", "-f", "--cached", idea_checks.FINDINGS_FILE)
        return None if text is None else idea_checks.parse_findings(text)

    def _check_round(self, slug: str, tid: str, path: Path, start_sha: str, task: dict, spent: dict, env: dict,
                     emitted: bool) -> tuple[bool, list[dict] | None]:
        """A check task's round, after its session: read the findings, commit what it left, then (done, findings).
        `done` when it ends here: nothing found and nothing changed (merged, `clean`, nothing lands), or findings left and
        nothing changed (at Review whatever `ideas.review` says). Otherwise the gate goes on as for any task."""
        findings = self._take_findings(path)
        self.git.commit_left(path, str(task.get("title") or ""))
        diff = self.git.stats(path, start_sha)
        self._set_task(slug, tid, findings=findings)
        n = idea_checks.counts(findings)
        if findings is not None and not emitted:
            self._emit(event_log.CHECK_DONE, idea=slug, task=tid, by=checker_of(task), found=n["found"], fixed=n["fixed"],
                       left=n["left"], round=int(task.get("round") or 1), cost=spent["cost"])
        if findings is None or diff["files"]:
            return False, findings
        if not n["left"]:
            self._set_task(slug, tid, state="merged", commit="", subjects=[], note="clean", tests=None, diff=diff,
                           finished=_r().now_iso(), error="", conflict="")
            self._log(slug, tid, f"== clean: it found nothing · {_r().now_iso()}\n", env)
            self.git.remove(path)
            return True, findings
        tests = {"passed": 0, "failed": 0, "failing": [], "tail": "", "green": True, "ran": False, "command": ""}
        self._set_task(slug, tid, state="review", tests=tests, diff=diff, conflict="", finished=_r().now_iso(), error="",
                       note=f"{n['left']} left")
        self._log(slug, tid, f"== at Review, {n['left']} left · {_r().now_iso()}\n", env)
        return True, findings

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
        if is_check(task):
            parts.append(FINDINGS_ASK)
        return "\n\n".join(parts)
