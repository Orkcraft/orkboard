"""A task's own parts of the runner (core/idea_runner.py, which imports this one): the gate on its worktree (`_check`,
`_tests_of`), its environment (`_env`) and its prompt (`_prompt`). `IdeaRunner` has them through `TaskMixin`.
"""
from __future__ import annotations

import threading
from pathlib import Path

from orkboard.realm import idea_checks, idea_pick, idea_secrets
from orkboard.realm.idea_git import BOARD_PAGE, CRITICAL_TESTS, env_name, has_summary, parse_tests, read_secret, spec_paths


FINDINGS_ASK = (
    f"When you are done, write what you found to `{idea_checks.FINDINGS_FILE}` at the worktree's root, as JSON: "
    '`{"findings": [{"where": "file:line, or the screen", "what": "one line: what goes wrong", "fixed": true}]}`, the worst first, '
    'at most 20. Write `{"findings": []}` when you found nothing that blocks, and then change nothing else. Fix only what is small '
    'and certain; leave the rest as findings with `"fixed": false`.')
NO_FINDINGS = "You left no findings file and changed no file. Write your findings file, as the task asks."
PICK_BACK = """The person looked at your last variants and picked none of them:

None of the last variants: "{note}"

Make {n} new ones in this same worktree."""
NO_RUN = {"passed": 0, "failed": 0, "failing": [], "tail": "", "green": True, "ran": False, "command": ""}      # a check that changed no file: no gate ran
NO_DIFF = {"files": 0, "added": 0, "removed": 0}


def is_check(task: dict) -> bool:
    """A check task: its `kind` is a checker's tag (realm/idea_checks.py `TAGS`)."""
    return str(task.get("kind") or "") in idea_checks.TAGS


def _r():
    """The runner's module (it imports this one: looked up when a task runs)."""
    from orkboard.core import idea_runner
    return idea_runner


def is_pick(task: dict) -> bool:
    """A task that ends with variants for the person to pick from (spec 51): its plan's task has a `pick`; a check never does."""
    return not is_check(task) and idea_pick.ask_of(task) is not None


def pick_ask(task: dict) -> str:
    """What a task that makes variants is told besides its brief (spec 51 §2.2): how many, of which kind, for what, where to write
    them and the manifest, and that it changes nothing else (as a check's findings file, they are read and never committed)."""
    ask = idea_pick.ask_of(task) or {}
    kind = idea_pick.KINDS[ask["kind"]]
    return (f"This task ends with {ask['n']} variants for the person to pick from, not with a change. Make {ask['n']} {kind.many} "
            f"({kind.formats}; at most {idea_pick.size_words(kind.limit)} each) for this: {ask['ask']}\n"
            f"Write each as a file into `{idea_pick.PICK_DIR}/` at the worktree's root, and a manifest `{idea_pick.PICK_FILE}` at the root, as JSON: "
            '`{"variants": [{"name": "24 characters at most", "file": "its file name in the folder", "why": "one line"}]}`, '
            f"exactly {ask['n']}, each different from the others. Make the files with your own tools. Change nothing else and commit nothing: "
            f"the person picks one, and it is written to `{ask['target']}` for you.")


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

    def _paced_elsewhere(self, slug: str) -> bool:
        """Another plan of the project already runs by day because the week had room (it is not finished)."""
        for other in self._active:
            if other != slug and ((p := self.plan(other)) or {}).get("by_pace") and not all(t.get("state") in ("merged", "failed") for t in p["tasks"]):
                return True
        return False

    def _mark_pace(self, slug: str) -> None:
        """The plan started by day by the pace: it says so (`by_pace`, which the Map and Agents read) and no longer waits for the night."""
        plan = self.plan(slug)
        if plan is not None and (not plan.get("by_pace") or plan.get("start_at") == "night"):
            plan["by_pace"] = True
            plan["start_at"] = None
            self._write(self._dir(slug) / "plan.json", plan)

    def _checker_of(self, task: dict) -> str:
        """The checker's slug of a check task: its role, else the library's checker of its tag."""
        role = str(task.get("role") or "")
        if role and idea_checks.is_checker(role):
            return role
        return idea_checks.checker_of_tag(str(task.get("kind") or ""))

    def _again_ask(self, task: dict) -> str:
        """What a check task is told besides a send back's line: the findings left of the last round, and the ask for the file again."""
        left = [f for f in task.get("findings") or [] if isinstance(f, dict) and not f.get("fixed")]
        rows = "".join(f"\n- {f.get('where')}: {f.get('what')}" for f in left)
        return (f"\n\nThe findings left from the last round:{rows}" if rows else "") + "\n\n" + FINDINGS_ASK

    def _findings_round(self, path: Path, start_sha: str, title: str) -> tuple[list[dict] | None, bool]:
        """(the findings a check task wrote, whether it changed a file): its findings file is read (at most 64 KB) and removed before
        the commit, so it is never committed; `None` for a missing file, bad JSON or a bad shape. What it left is committed here."""
        target, text = path / idea_checks.FINDINGS_FILE, ""
        try:
            with target.open("rb") as f:
                raw = f.read(idea_checks.FINDINGS_BYTES + 1)
            text = raw.decode("utf-8") if len(raw) <= idea_checks.FINDINGS_BYTES else ""
        except (OSError, UnicodeDecodeError):
            pass
        try:
            target.unlink()
        except OSError:
            pass
        self.git.commit_left(path, title)
        return idea_checks.parse_findings(text), bool(self.git.commits(path, start_sha))

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
                + f"\n  {t.get('brief', '')}" + (f"\n  {idea_pick.picked_words(t['picked'])}" if t.get("picked") else "")
                for t in plan.get("tasks") or [] if t.get("id") in after]
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
        elif is_pick(task):
            parts.append(pick_ask(task))
        return "\n\n".join(parts)

    def _again_prompt(self, slug: str, plan: dict, task: dict, again: dict, base: str) -> tuple[str, str]:
        """(what a task is told, the session it resumes) when it goes on: a send back, the gate's conflict, a pick of none of them
        (spec 51 §2.3); a pick taken needs no turn, the gate runs on what was committed. The task's own prompt comes first when
        there is no session to resume."""
        resume = str(task.get("session") or "")
        if again.get("taken"):
            return "", resume
        extra, tests = "", task.get("tests") or {}
        if again["files"]:
            extra += (f"Your branch conflicted with `{base}` in {', '.join(again['files'])}. The merge of "
                      f"`{base}` into your branch is open in this worktree: rebase onto {base} and resolve "
                      "it by editing those files until no conflict marker is left (keep what both sides "
                      "meant). Do not abort the merge.\n\n")
        if tests and not tests.get("green", not tests.get("failed")):
            extra += f"The tests were red:\n{tests.get('tail', '')}\n\n"
        if again.get("pick"):
            prompt = PICK_BACK.format(note=again["why"], n=(idea_pick.ask_of(task) or {}).get("n")) + "\n\n" + pick_ask(task)
        else:
            prompt = _r().BACK.format(why=again["why"], extra=extra)
            if resume and is_check(task):
                prompt += self._again_ask(task)
        if not resume:
            prompt = self._prompt(slug, plan, task) + "\n\n" + prompt
        return prompt, resume
