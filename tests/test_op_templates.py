"""Operations' templates (docs/specs/38-operations.md §2, §5, Tests → A): the person's and the built-in found, the
person's winning; a skill without the manifest skipped; a broken manifest listed with its problem; servers; the
version; the form; the built-in two and the wheel that ships them."""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from orkboard.realm import op_templates

MANIFEST = '''title = "Ship a thing"
risk = "medium"
servers = { jira = "Jira" }
nonsense = "ignored"

[[fields]]
name = "what"
label = "What"
type = "long"
required = true

[[fields]]
name = "level"
label = "Level"
type = "choice"
options = ["a", "b"]
default = "a"
at = "fields.level"

[[fields]]
name = "team"
label = "Team"
remember = true

[[draft]]
name = "summary"
label = "Title"
at = "summary"

[prepare]
tools = ["mcp__{jira}__getJiraIssue"]

[act]
tool = "mcp__{jira}__createJiraIssue"
label = "Create in Jira"
'''


def skill(folder: Path, manifest: str | None = MANIFEST, text: str = "---\nname: x\n---\n\n# Do it\nWell.\n") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(text, encoding="utf-8")
    if manifest is not None:
        (folder / "orkboard.toml").write_text(manifest, encoding="utf-8")
    return folder


def test_the_built_in_two_and_the_persons_are_found_the_persons_winning(tmp_path):
    home = tmp_path / "claude"
    skill(home / "skills" / "jira-task")                       # a person's with a built-in's name replaces it
    skill(home / "skills" / "mine")
    skill(home / "skills" / "plain-skill", manifest=None)      # a skill without orkboard.toml is no template
    found = op_templates.find(home)
    assert set(found) == {"jira-task", "email-reply", "mine"}
    assert found["jira-task"].title == "Ship a thing" and not found["jira-task"].builtin
    assert found["email-reply"].builtin and found["mine"].problem == ""


def test_the_claude_home_is_read_as_sessions_reads_it(tmp_path, monkeypatch):
    monkeypatch.setenv("ORKCRAFT_CLAUDE_HOME", str(tmp_path / "ch"))
    skill(tmp_path / "ch" / "skills" / "mine")
    assert "mine" in op_templates.find()
    monkeypatch.delenv("ORKCRAFT_CLAUDE_HOME")
    assert op_templates.claude_home() == Path.home() / ".claude"


def test_an_unknown_key_is_ignored_and_a_broken_manifest_has_its_problem(tmp_path):
    t = op_templates.read(skill(tmp_path / "ok"))
    assert t.problem == "" and [f["name"] for f in t.fields] == ["what", "level", "team"]
    broken = op_templates.read(skill(tmp_path / "bad", MANIFEST.replace('risk = "medium"', 'risk = "wild"')))
    assert broken.problem == "its risk is low, medium or high"
    assert "not TOML" in op_templates.read(skill(tmp_path / "toml", "title = ")).problem
    two = op_templates.read(skill(tmp_path / "two", MANIFEST.replace('[act]\ntool = "mcp__{jira}__createJiraIssue"',
                                                                     '[act]\ntool = "mcp__{gmail}__create_draft"')))
    assert "{gmail}" in two.problem
    many = MANIFEST + "".join(f'\n[[fields]]\nname = "f{n}"\nlabel = "F"\n' for n in range(6))
    assert "more than 8 fields" in op_templates.read(skill(tmp_path / "many", many)).problem
    assert op_templates.unusable(broken, {"jira": "Atlassian"}).startswith("Ship a thing cannot be used: its risk")


def test_a_key_is_resolved_from_the_servers_and_a_missing_one_makes_it_unusable(tmp_path):
    t = op_templates.read(skill(tmp_path / "t"))
    assert op_templates.unusable(t, {}) == ("Jira is not connected: add its MCP server to Claude Code, then pick it "
                                            "here")
    assert op_templates.tools(t, {"jira": "claude.ai Atlassian"}) == (
        ["mcp__claude_ai_Atlassian__getJiraIssue"], "mcp__claude_ai_Atlassian__createJiraIssue")
    assert op_templates.unusable(t, {"jira": "Atlassian"}) == ""
    assert op_templates.unusable(t, {"jira": "Atlassian"}, claude=False).startswith("Operations run on Claude Code")
    with pytest.raises(ValueError, match="Jira is not connected"):
        op_templates.tools(t, {})


def test_the_version_moves_with_the_skill_and_the_manifest_not_the_rules(tmp_path):
    folder = skill(tmp_path / "t")
    v1 = op_templates.read(folder).version
    (folder / "rules.md").write_text("- a rule\n", encoding="utf-8")
    assert op_templates.read(folder).version == v1
    (folder / "SKILL.md").write_text("# Other\n", encoding="utf-8")
    v2 = op_templates.read(folder).version
    (folder / "orkboard.toml").write_text(MANIFEST.replace("Ship a thing", "Ship it"), encoding="utf-8")
    assert len({v1, v2, op_templates.read(folder).version}) == 3


def test_the_skill_is_read_without_its_front_matter(tmp_path):
    t = op_templates.read(skill(tmp_path / "t"))
    assert op_templates.skill_body(t) == "# Do it\nWell."


def test_the_form_refuses_a_missing_required_field_and_a_choice_off_its_options(tmp_path):
    t = op_templates.read(skill(tmp_path / "t"))
    with pytest.raises(ValueError, match="What is needed"):
        op_templates.clean_fields(t, {"what": "  "})
    with pytest.raises(ValueError, match="Level is one of: a, b"):
        op_templates.clean_fields(t, {"what": "x", "level": "c"})
    with pytest.raises(ValueError, match="longer than 4000"):
        op_templates.clean_fields(t, {"what": "x" * 4001})
    got = op_templates.clean_fields(t, {"what": "x", "other": "dropped"}, last={"team": "Core", "what": "no"})
    assert got == {"what": "x", "level": "a", "team": "Core"}            # remember prefills the last value


def test_every_at_is_written_into_the_arguments():
    t = op_templates.Template("t", Path("."), fields=[{"name": "p", "at": "additional_fields.priority.name"},
                                                      {"name": "epic", "at": ""}],
                              draft=[{"name": "summary", "at": "summary"}])
    args = op_templates.with_values(t, {"summary": "old", "additional_fields": {"x": 1}, "projectKey": "ABC"},
                                    {"p": "High", "epic": "ABC-1"}, {"summary": "New"})
    assert args == {"summary": "New", "additional_fields": {"x": 1, "priority": {"name": "High"}}, "projectKey": "ABC"}


def test_the_built_in_two_say_what_the_spec_says():
    found = op_templates.find(Path("/nonexistent"))
    jira, mail = found["jira-task"], found["email-reply"]
    assert not jira.problem and not mail.problem
    assert (jira.title, jira.risk, jira.act_label) == ("New Jira task", "medium", "Create in Jira")
    assert [(f["name"], f["type"]) for f in jira.fields] == [("what", "long"), ("project", "text"),
                                                             ("priority", "choice"), ("type", "choice"), ("epic", "text")]
    assert jira.field_of("what")["required"] and jira.field_of("project")["remember"]
    assert jira.field_of("priority")["options"] == ["Highest", "High", "Medium", "Low", "Lowest"]
    assert jira.field_of("priority")["default"] == "Medium" and jira.field_of("priority")["at"]
    assert jira.field_of("type")["options"] == ["Task", "Bug", "Story"] and jira.field_of("type")["at"]
    assert not jira.field_of("epic")["at"]                    # the prepare resolves it
    assert [p["name"] for p in jira.draft] == ["summary", "description"]
    assert [op_templates.short(x) for x in jira.prepare] == ["getAccessibleAtlassianResources", "getVisibleJiraProjects",
                                                             "searchJiraIssuesUsingJql", "getJiraIssue"]
    assert op_templates.short(jira.act) == "createJiraIssue" and jira.servers == {"jira": "Jira"}
    assert (mail.title, mail.act_label) == ("Reply to an email", "Save as a draft in Gmail")
    assert [f["name"] for f in mail.fields] == ["find", "say", "tone"]
    assert mail.field_of("tone")["options"] == ["short", "warm", "formal"] and mail.field_of("tone")["default"] == "short"
    assert [p["name"] for p in mail.draft] == ["subject", "body"]
    assert [op_templates.short(x) for x in mail.prepare] == ["search_threads", "get_thread"]
    assert op_templates.short(mail.act) == "create_draft" and mail.servers == {"gmail": "Gmail"}


def test_a_built_wheel_ships_the_templates(tmp_path):
    root = Path(__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "-w",
                          str(tmp_path), str(root)], capture_output=True, text=True, cwd=tmp_path)
    if out.returncode != 0 and "No module named pip" in out.stderr:
        out = subprocess.run(["uv", "build", "--wheel", "-o", str(tmp_path), str(root)], capture_output=True,
                             text=True, cwd=tmp_path)
    assert out.returncode == 0, out.stderr[-2000:]
    wheel = next(tmp_path.glob("orkboard-*.whl"))
    names = zipfile.ZipFile(wheel).namelist()
    for name in ("jira-task", "email-reply"):
        assert f"orkboard/ops_templates/{name}/orkboard.toml" in names
        assert f"orkboard/ops_templates/{name}/SKILL.md" in names
