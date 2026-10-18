"""Spec 37 C: the gate on any repository (realm/gate_config.py, idea_git.gate_run, the runner's `tests`) and `ideas.doc`
reading no secret."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from orkcraft.gui import mobile
from orkcraft.gui.host import CommandError
from orkcraft.realm import gate_config, idea_git
from orkcraft.realm.idea_git import IdeaGit

from tests.test_gui_goals import host  # noqa: F401  (the host fixture)
from tests.test_idea_git import commit_in, git, repo  # noqa: F401  (a repository with no tests)
from tests.test_idea_runner import plan_of, reviewing, runner_of, tasks_of, town, wait_idle, wait_task  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent


def toml(root: Path, text: str) -> None:
    (root / "orkcraft.toml").write_text(text, encoding="utf-8")


def gate_in(repo: Path, **more):
    """A task worktree with one commit; `gate_run` on it."""
    g = IdeaGit(repo)
    path, _ = g.prepare("demo", "k1", "main")
    commit_in(path, "b.txt", "b\n")
    return g.gate_run(path, "main", threading.Event(), **more)


# -- the file --------------------------------------------------------------------------------------------------

def test_without_a_file_or_a_gate_table_the_gate_is_todays(tmp_path):
    assert gate_config.read(tmp_path) == gate_config.Gate() and not gate_config.read(tmp_path).custom
    toml(tmp_path, "[other]\nx = 1\n")
    assert gate_config.read(tmp_path) == gate_config.Gate()
    assert gate_config.Gate().always == idea_git.CRITICAL_TESTS == gate_config.CRITICAL_TESTS


def test_this_repository_keeps_todays_three_critical_tests_in_always():
    gate = gate_config.read(ROOT)
    assert gate.always == idea_git.CRITICAL_TESTS and not gate.error and not gate.custom
    assert (ROOT / "orkcraft.toml").is_file()


def test_the_gate_table_is_read_and_unknown_keys_are_ignored(tmp_path):
    toml(tmp_path, '[gate]\nrun = "npm test -- {files}"\nalways = ["t/a.test.js"]\nmap = ["t/{stem}.test.js"]\n'
                   'timeout_min = 5\nsurprise = true\n')
    gate = gate_config.read(tmp_path)
    assert (gate.run, gate.always, gate.map, gate.timeout_min, gate.error) == (
        "npm test -- {files}", ("t/a.test.js",), ("t/{stem}.test.js",), 5, "")


@pytest.mark.parametrize("text", ["[gate\nrun = ", "[gate]\nrun = 3\n", "[gate]\nalways = \"x\"\n", "[gate]\ntimeout_min = -1\n",
                                  "gate = 4\n"])
def test_a_broken_file_is_said_and_the_gate_is_todays(tmp_path, text):
    toml(tmp_path, text)
    gate = gate_config.read(tmp_path)
    assert gate.error.startswith("orkcraft.toml is not usable") and "ran as with no file" in gate.error
    assert not gate.custom and gate.always == idea_git.CRITICAL_TESTS


def test_files_hold_always_and_the_mapped_tests_that_exist_and_the_command_quotes_them(tmp_path):
    for rel in ("t/a.test.js", "t/widget.test.js", "src/my dir/test_m.py", "src/lib/core.py"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("")
    gate = gate_config.Gate(run="npm test -- {files}", always=("t/a.test.js", "t/gone.js"),
                            map=("t/{stem}.test.js", "t/{name}.nope", "{dir}/test_{stem}.py"))
    files = gate_config.gate_files(gate, ["src/widget.js", "src/my dir/m.py", "README.md", "src/__init__.py"], tmp_path)
    assert files == ["t/a.test.js", "t/widget.test.js", "src/my dir/test_m.py"]
    assert gate_config.command(gate, files) == "npm test -- t/a.test.js t/widget.test.js 'src/my dir/test_m.py'"
    assert gate_config.command(gate_config.Gate(run="make check"), []) == "make check"     # no {files}: as is
    assert gate_config.command(gate, []) is None                                            # {files} with none to give


def test_without_a_gate_table_the_files_are_those_of_today(tmp_path):
    (tmp_path / "tests").mkdir()
    for name in ("test_architecture.py", "test_cli.py", "test_updates.py", "test_ideas.py", "test_x.py"):
        (tmp_path / "tests" / name).write_text("")
    touched = ["orkcraft/realm/ideas.py", "orkcraft/gone.py", "tests/test_x.py", "README.md", "orkcraft/__init__.py"]
    assert gate_config.gate_files(gate_config.Gate(), touched, tmp_path) == [
        *idea_git.CRITICAL_TESTS, "tests/test_ideas.py", "tests/test_x.py"]


def test_test_argv_comes_from_gate_config_for_the_forge_and_the_jobs():
    from orkcraft.realm import forge, jobs
    assert gate_config.test_argv("pytest -q") == ["pytest", "-q"]
    assert gate_config.test_argv("pytest -q && ruff check .") == ["sh", "-c", "pytest -q && ruff check ."]
    assert forge.test_argv is gate_config.test_argv and jobs.test_argv is gate_config.test_argv
    assert not hasattr(forge, "_SHELL")


# -- the run -----------------------------------------------------------------------------------------------------

def test_nothing_to_run_is_not_a_pass(repo):
    run = gate_in(repo)
    assert run.ran is False and run.ok is True and run.code is None and "no tests ran" in run.out
    assert "no test files to run" not in run.out
    g = IdeaGit(repo)
    path, _ = g.prepare("demo", "k2", "main")
    commit_in(path, "c.txt", "c\n")
    ok, _out = g.gate(path, "main", threading.Event())
    assert ok is False                                    # the plain gate does not call it a pass either


def test_a_command_that_is_not_pytest_is_decided_by_its_exit_code(repo):
    toml(repo, '[gate]\nrun = "sh -c \'exit 0\'"\n')
    ok = gate_in(repo)
    assert (ok.ran, ok.ok, ok.code, ok.command) == (True, True, 0, "sh -c 'exit 0'")
    toml(repo, "[gate]\nrun = \"sh -c 'echo broke; exit 1'\"\n")
    bad = gate_in(repo)
    assert (bad.ran, bad.ok, bad.code) == (True, False, 1) and "broke" in bad.out


def test_the_command_gets_always_and_the_mapped_tests_quoted(repo):
    (repo / "t").mkdir()
    (repo / "t" / "b.t").write_text("")
    (repo / "t" / "other.t").write_text("")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "tests")
    toml(repo, '[gate]\nrun = "echo files: {files}"\nalways = ["t/other.t"]\nmap = ["t/{stem}.t"]\n')
    run = gate_in(repo)
    assert run.ok and run.command == "echo files: t/other.t t/b.t" and "files: t/other.t t/b.t" in run.out


def test_a_command_with_files_and_nothing_to_give_them_runs_nothing(repo):
    toml(repo, '[gate]\nrun = "echo {files}"\nalways = []\nmap = ["t/{stem}.t"]\n')
    run = gate_in(repo)
    assert run.ran is False and run.ok


def test_a_broken_file_is_said_in_the_output_and_the_gate_ran_as_today(repo):
    toml(repo, "[gate\n")
    run = gate_in(repo)
    assert run.ran is False and "orkcraft.toml is not usable" in run.out        # today's gate: no tests in this repository


def test_the_gate_reads_the_file_from_the_repository_not_from_the_task_worktree(repo):
    toml(repo, '[gate]\nrun = "sh -c \'exit 1\'"\n')
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "gate")
    g = IdeaGit(repo)
    path, _ = g.prepare("demo", "k1", "main")
    (path / "orkcraft.toml").write_text('[gate]\nrun = "true"\n')                   # a task cannot loosen its own gate
    git(path, "add", "-A")
    git(path, "commit", "-m", "edit the gate")
    assert g.gate_run(path, "main", threading.Event()).ok is False


# -- the result ---------------------------------------------------------------------------------------------------

def no_tests(town):                                                                   # noqa: F811
    git(town.repo, "rm", "-rq", "tests")
    git(town.repo, "commit", "-qm", "no tests")


def test_a_result_with_no_test_to_run_waits_at_review_even_when_review_is_off(town):
    no_tests(town)
    plan_of(town, [{"id": "k1"}])
    runner, _ = runner_of(town)                                                       # ideas.review: false
    before = git(town.repo, "rev-parse", "main")
    runner.start("demo")
    task = wait_task(runner, "k1", "review")
    assert task["tests"]["ran"] is False and task["tests"]["green"] is True and task["state"] == "review"
    assert git(town.repo, "rev-parse", "main") == before and not (town.repo / "k1.txt").exists()
    assert "no tests ran" in task["tests"]["tail"]
    assert runner.merge("demo", "k1") and (town.repo / "k1.txt").exists()               # Merge stays the person's press


def test_a_command_that_is_not_pytest_leaves_null_counts_and_lands_when_review_is_off(town):
    toml(town.repo, '[gate]\nrun = "sh -c \'exit 0\'"\n')
    git(town.repo, "add", "-A")
    git(town.repo, "commit", "-qm", "gate")
    plan_of(town, [{"id": "k1"}])
    runner, _ = runner_of(town)
    runner.start("demo")
    assert wait_idle(runner)["state"] == "done"
    tests = tasks_of(town)["k1"]["tests"]
    assert (tests["ran"], tests["passed"], tests["failed"], tests["green"], tests["exit"]) == (True, None, None, True, 0)
    assert tests["command"] == "sh -c 'exit 0'"


def test_pytest_keeps_its_counts_and_records_what_ran(town):
    plan_of(town, [{"id": "k1"}])
    runner, _ = reviewing(town)
    runner.start("demo")
    tests = wait_task(runner, "k1", "review")["tests"]
    assert tests["ran"] is True and tests["passed"] >= 3 and tests["failed"] == 0 and tests["green"] is True
    assert tests["command"].startswith("python -m pytest -q tests/test_architecture.py")


def test_a_task_from_before_reads_as_ran(town):
    plan_of(town, [{"id": "k1"}])
    plan = json.loads((town.state / "ideas" / "demo" / "plan.json").read_text())
    plan["tasks"][0].update(state="review", tests={"passed": 3, "failed": 0, "failing": [], "tail": "", "green": True},
                            diff={"files": 1, "added": 1, "removed": 0})
    (town.state / "ideas" / "demo" / "plan.json").write_text(json.dumps(plan))
    runner, _ = reviewing(town)
    assert runner.plan("demo")["tasks"][0]["tests"].get("ran", True) is True


# -- ideas.doc --------------------------------------------------------------------------------------------------

SECRET_PATHS = (".env", ".orkcraft/secrets.json", ".git/config", "id_ed25519", "keys/id_ed25519", ".env.production")


def test_a_linked_document_never_reads_a_secret_or_git_or_orkcraft(host):                  # noqa: F811
    repo = Path(host.town.repo_root)
    for rel in SECRET_PATHS:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("TOKEN=hunter2\n")
    (repo / ".env.example").write_text("TOKEN=\n")
    (repo / "notes.md").write_text("# Notes\n")
    for rel in SECRET_PATHS:
        with pytest.raises(CommandError, match="may hold secrets: open it in your own editor"):
            host.command("ideas.doc", {"path": rel})
    with pytest.raises(CommandError, match="may hold secrets"):
        host.command("ideas.doc", {"path": "/.git/config#top"})
    assert host.command("ideas.doc", {"path": ".env.example"})["text"] == "TOKEN=\n"
    assert host.command("ideas.doc", {"path": "notes.md"})["text"] == "# Notes\n"


def test_a_link_to_a_secret_is_a_secret(host, tmp_path):                                    # noqa: F811
    repo = Path(host.town.repo_root)
    (repo / ".env").write_text("TOKEN=hunter2\n")
    (repo / "readme-link.md").symlink_to(repo / ".env")
    with pytest.raises(CommandError, match="may hold secrets"):
        host.command("ideas.doc", {"path": "readme-link.md"})


def test_the_phone_reads_documents_through_the_same_command():
    assert "ideas.doc" in mobile.COMMANDS and mobile.COMMANDS["ideas.doc"] is None      # no phone-only path to the files
