"""Operations' templates (docs/specs/38-operations.md §2): a Claude skill with Orkboard's manifest beside it.

    found = op_templates.find()                    # {name: Template}: the built-in ones, the person's winning by name
    t = found["jira-task"]
    op_templates.unusable(t, servers, claude=True) # "" or why it cannot be added from, in words
    op_templates.tools(t, servers)                 # (the prepare's tools, the action's tool) as the CLI spells them
    op_templates.clean_fields(t, given, last)      # the form checked (ValueError in words), defaults and remembered
    op_templates.put(args, "additional_fields.priority.name", "High")   # a value written at its `at`
    op_templates.bound(t, servers)                 # a brief's bound reads, their tools as the CLI spells them

A template **acts** (`[act]`: one tool, spec 38) or **briefs** (`[brief]`: it reads, writes a page for the person and
does nothing outside; docs/specs/66-team-briefs.md §1), never both. A template about people (`people = true`, spec 66
§2) says what it reads (`reads`), and each Slack tool it names is bound to the channels the person named
(`[[prepare.bound]]`) or is a bound's lookup, else it is refused at load. `follow` names the field whose last kept
brief the next one starts from (§4).

A template is a skill folder holding `orkboard.toml` beside its `SKILL.md`: the person's in `<claude home>/skills/`
(`$CLAUDE_HOME`, else `~/.claude`, as `sources/sessions.py` reads it), the built-in ones in `orkboard/ops_templates/`.
Orkboard never writes either file; a skill without the manifest is not a template; a broken manifest is listed with
its problem in words and cannot be added from. Its version is the sha256 of both files as read. No face, no model.
"""
from __future__ import annotations

import copy
import hashlib
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from orkboard.env import getenv

MANIFEST = "orkboard.toml"
SKILL = "SKILL.md"
BUILTIN = Path(__file__).resolve().parents[1] / "ops_templates"
RISKS = ("low", "medium", "high")
TYPES = ("text", "long", "choice")
DRAFT_TYPES = ("text", "long")
MAX_FIELDS, MAX_DRAFT, VALUE_MAX = 8, 4, 4000
NAME = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
FOLDER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
AT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){0,5}$")
TOOL = re.compile(r"^mcp__(\{[a-z][a-z0-9_]{0,39}\}|[A-Za-z0-9_-]+)__[A-Za-z0-9_.-]{1,100}$")
KEY = re.compile(r"\{([a-z][a-z0-9_]{0,39})\}")
ARG = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,59}$")
READS_MAX, MAX_BOUND = 200, 6
SLACK_ONLY = "a brief about people reads only the channels named"


@dataclass
class Template:
    name: str                                   # its folder's name
    folder: Path
    title: str = ""
    risk: str = "medium"
    servers: dict[str, str] = field(default_factory=dict)    # key → what it is for ("Jira")
    fields: list[dict] = field(default_factory=list)
    draft: list[dict] = field(default_factory=list)
    prepare: list[str] = field(default_factory=list)          # tool names with {key}
    act: str = ""                                             # "" for a brief
    act_label: str = ""                                       # the check's button: the action's, or a brief's Keep
    brief: bool = False                                       # it prepares a page to read, does nothing outside (spec 66)
    people: bool = False                                      # about people: spec 66 §2's line, held by code
    reads: str = ""                                           # what it reads, said on its form
    follow: str = ""                                          # the field whose last kept brief the next one starts from
    bound: list[dict] = field(default_factory=list)           # [{tool, arg, field, lookup}]: a read held to named values
    version: str = ""
    skill: str = ""                                           # SKILL.md as read
    problem: str = ""                                         # "" a template that works; else why not, in words
    builtin: bool = False

    def field_of(self, name: str) -> dict | None:
        return next((f for f in self.fields if f["name"] == name), None)


def claude_home() -> Path:
    return Path(getenv("CLAUDE_HOME") or Path.home() / ".claude")


def find(home: Path | None = None, builtin: Path | None = None) -> dict[str, Template]:
    """Every template, by name: the built-in ones, then the person's (a person's with a built-in's name replaces it)."""
    out: dict[str, Template] = {}
    for base, mine in ((builtin or BUILTIN, True), ((home or claude_home()) / "skills", False)):
        try:
            folders = sorted(p for p in base.iterdir() if p.is_dir())
        except OSError:
            continue
        for folder in folders:
            if FOLDER.match(folder.name) and (folder / MANIFEST).is_file():
                out[folder.name] = read(folder, builtin=mine)
    return out


def read(folder: Path, builtin: bool = False) -> Template:
    """One template as its files say; a broken one has its `problem` in words."""
    t = Template(folder.name, folder, title=folder.name, builtin=builtin)
    try:
        raw_toml = (folder / MANIFEST).read_bytes()
        raw_skill = (folder / SKILL).read_bytes() if (folder / SKILL).is_file() else b""
    except OSError:
        t.problem = "its files cannot be read"
        return t
    t.version = hashlib.sha256(raw_skill + b"\0" + raw_toml).hexdigest()
    t.skill = raw_skill.decode("utf-8", errors="replace")
    if not raw_skill:
        t.problem = f"it has no {SKILL}"
        return t
    try:
        data = tomllib.loads(raw_toml.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        t.problem = f"its {MANIFEST} is not TOML: {str(e).splitlines()[0][:200]}"
        return t
    try:
        _fill(t, data)
    except ValueError as e:
        t.problem = str(e)
    return t


def _text(value: object, what: str, most: int = 200, need: bool = True) -> str:
    if value is None and not need:
        return ""
    if not isinstance(value, str) or (need and not value.strip()) or len(value) > most:
        raise ValueError(f"{what} is missing or not a short text")
    return value.strip()


def _fill(t: Template, data: dict) -> None:
    t.title = _text(data.get("title"), "its title", 80)
    t.risk = data.get("risk", "medium")
    if t.risk not in RISKS:
        raise ValueError("its risk is low, medium or high")
    servers = data.get("servers", {})
    if not isinstance(servers, dict) or not all(isinstance(k, str) and NAME.match(k) and isinstance(v, str)
                                                and v.strip() for k, v in servers.items()):
        raise ValueError("its servers are {key = \"what it is for\"}")
    t.servers = {k: v.strip()[:60] for k, v in servers.items()}
    fields, draft = data.get("fields", []), data.get("draft", [])
    if not isinstance(fields, list) or len(fields) > MAX_FIELDS:
        raise ValueError(f"it has more than {MAX_FIELDS} fields")
    if not isinstance(draft, list) or not draft or len(draft) > MAX_DRAFT:
        raise ValueError(f"its draft has one to {MAX_DRAFT} parts")
    names: set[str] = set()
    t.fields = [_field(f, names) for f in fields]
    t.draft = [_part(p, names) for p in draft]
    prepare = data.get("prepare", {})
    tools = prepare.get("tools", []) if isinstance(prepare, dict) else None
    if not isinstance(tools, list) or not all(isinstance(x, str) and TOOL.match(x) for x in tools):
        raise ValueError("its [prepare] tools are MCP tool names: mcp__{key}__tool")
    t.prepare = list(dict.fromkeys(tools))
    if "act" in data and "brief" in data:
        raise ValueError("a template briefs or acts, not both: it has [act] and [brief]")
    if "brief" in data:
        brief = data["brief"]
        if not isinstance(brief, dict):
            raise ValueError("its [brief] is a table with its label")
        t.brief, t.act_label = True, _text(brief.get("label"), "its [brief] label", 60)
        if any(x.get("at") for x in [*t.fields, *t.draft]):
            raise ValueError("a brief has no action: its fields and draft parts have no at")
    else:
        act = data.get("act", {})
        if not isinstance(act, dict) or not isinstance(act.get("tool"), str) or not TOOL.match(act["tool"]):
            raise ValueError("its [act] names exactly one MCP tool: mcp__{key}__tool")
        t.act = act["tool"]
        t.act_label = _text(act.get("label"), "its [act] label", 60)
    for tool in [*t.prepare, *([t.act] if t.act else [])]:
        for key in KEY.findall(tool):
            if key not in t.servers:
                raise ValueError(f"{tool} names {{{key}}}, which its servers do not")
    if t.act and t.act in t.prepare:
        raise ValueError("its action's tool is not one it may read with")
    _people(t, data, prepare)


def _people(t: Template, data: dict, prepare: dict) -> None:
    """`people`, `reads`, `follow` and `[[prepare.bound]]` (spec 66 §2, §4). A template about people says what it
    reads, is at least `medium`, and each Slack tool it names is bound or a bound's lookup."""
    if not isinstance(data.get("people", False), bool):
        raise ValueError("its people is true or false")
    t.people = data.get("people", False)
    t.reads = _text(data.get("reads"), "its reads (what it reads, said on its form)", READS_MAX, need=t.people)
    if t.people and t.risk == "low":
        t.risk = "medium"
    follow = data.get("follow")
    if follow is not None:
        if not t.brief or not isinstance(follow, str) or t.field_of(follow) is None:
            raise ValueError("its follow names one of its fields, and only a brief follows")
        t.follow = follow
    raw = prepare.get("bound", [])
    if not isinstance(raw, list) or len(raw) > MAX_BOUND:
        raise ValueError(f"its [[prepare.bound]] are at most {MAX_BOUND} tables")
    for b in raw:
        lookup = b.get("lookup", "") if isinstance(b, dict) else None
        if not isinstance(b, dict) or b.get("tool") not in t.prepare or not isinstance(b.get("arg"), str) \
                or not ARG.match(b["arg"]) or not isinstance(b.get("field"), str) or t.field_of(b["field"]) is None \
                or (lookup and lookup not in t.prepare) or not isinstance(lookup, str):
            raise ValueError("a [[prepare.bound]] names one of its [prepare] tools, its argument and one of its "
                             "fields (and its lookup, one of its tools)")
        t.bound.append({"tool": b["tool"], "arg": b["arg"], "field": b["field"], "lookup": lookup})
    if t.people:
        held = {b["tool"] for b in t.bound} | {b["lookup"] for b in t.bound if b["lookup"]}
        if any(slack(t, tool) and tool not in held for tool in t.prepare):
            raise ValueError(SLACK_ONLY)


def slack(t: Template, tool: str) -> bool:
    """A Slack tool: its server's key, what that server is for, or its server's name says Slack."""
    keys = KEY.findall(tool)
    if keys:
        return any(key == "slack" or "slack" in t.servers.get(key, "").casefold() for key in keys)
    return "slack" in tool.split("__")[1].casefold()


def _field(raw: object, names: set[str]) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("a field is a [[fields]] table")
    name = raw.get("name")
    if not isinstance(name, str) or not NAME.match(name) or name in names:
        raise ValueError("a field's name is a word of its own (a–z, 0–9, _)")
    names.add(name)
    f: dict[str, Any] = {"name": name, "label": _text(raw.get("label"), f"the field {name}'s label", 80),
                         "type": raw.get("type", "text")}
    if f["type"] not in TYPES:
        raise ValueError(f"the field {name}'s type is text, long or choice")
    for key in ("required", "remember"):
        if not isinstance(raw.get(key, False), bool):
            raise ValueError(f"the field {name}'s {key} is true or false")
        f[key] = raw.get(key, False)
    f["hint"] = _text(raw.get("hint"), f"the field {name}'s hint", 200, need=False)
    if f["type"] == "choice":
        options = raw.get("options")
        if not isinstance(options, list) or not options or not all(isinstance(o, str) and o.strip() for o in options):
            raise ValueError(f"the field {name} is a choice without options")
        f["options"] = [o.strip()[:80] for o in options][:30]
    default = raw.get("default", "")
    if not isinstance(default, str) or (f["type"] == "choice" and default and default not in f["options"]):
        raise ValueError(f"the field {name}'s default is not one of its options")
    f["default"] = default[:VALUE_MAX]
    f["at"] = _at(raw.get("at"), name)
    return f


def _part(raw: object, names: set[str]) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("a draft part is a [[draft]] table")
    name = raw.get("name")
    if not isinstance(name, str) or not NAME.match(name) or name in names:
        raise ValueError("a draft part's name is a word of its own, not a field's")
    names.add(name)
    kind = raw.get("type", "text")
    if kind not in DRAFT_TYPES:
        raise ValueError(f"the draft part {name}'s type is text or long")
    return {"name": name, "label": _text(raw.get("label"), f"the draft part {name}'s label", 80), "type": kind,
            "at": _at(raw.get("at"), name)}


def _at(value: object, name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or not AT.match(value):
        raise ValueError(f"{name}'s at is a dotted path into the action's arguments")
    return value


# -- the servers ---------------------------------------------------------------------------------------------

def spelled(server: str) -> str:
    """A server's name as the CLI spells it in a tool's name (`claude.ai Gmail` → `claude_ai_Gmail`)."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", server.strip())


def resolve(tool: str, servers: dict[str, str]) -> str | None:
    """A tool's name with each `{key}` the person's server for it; None when a key has none."""
    missing = [k for k in KEY.findall(tool) if not servers.get(k)]
    if missing:
        return None
    return KEY.sub(lambda m: spelled(servers[m.group(1)]), tool)


def tools(t: Template, servers: dict[str, str]) -> tuple[list[str], str]:
    """(the prepare's tools, the action's tool) as the CLI spells them; raises ValueError when a key has no server."""
    got = [resolve(x, servers) for x in t.prepare]
    act = resolve(t.act, servers) if t.act else ""          # a brief has no action
    if act is None or any(x is None for x in got):
        raise ValueError(unusable(t, servers))
    return [x for x in got if x], act


def bound(t: Template, servers: dict[str, str]) -> list[dict]:
    """A brief's bound reads, each tool and lookup as the CLI spells them (one whose key has no server is left out:
    the template is then unusable)."""
    out = []
    for b in t.bound:
        tool, lookup = resolve(b["tool"], servers), (resolve(b["lookup"], servers) if b["lookup"] else "")
        if tool is not None and lookup is not None:
            out.append({**b, "tool": tool, "lookup": lookup})
    return out


def short(tool: str) -> str:
    """A tool's own name, without its server (`mcp__x__createJiraIssue` → `createJiraIssue`)."""
    return tool.rsplit("__", 1)[-1]


def what_of(t: Template, tool: str, servers: dict[str, str] | None = None) -> str:
    """What a tool's server is for ("Jira"), the tool named with its `{key}` or as resolved from `servers`; else
    the template's title."""
    if not KEY.findall(tool) and servers:
        tool = next((raw for raw in [*t.prepare, t.act] if raw and resolve(raw, servers) == tool), tool)
    keys = KEY.findall(tool)
    return t.servers.get(keys[0], t.title) if keys else t.title


def unusable(t: Template, servers: dict[str, str], claude: bool = True) -> str:
    """Why the template cannot be added from, in words; "" when it can."""
    if t.problem:
        return f"{t.title} cannot be used: {t.problem}"
    if not claude:
        return "Operations run on Claude Code, which is not installed here"
    for key in dict.fromkeys(k for tool in [*t.prepare, t.act] if tool for k in KEY.findall(tool)):
        if not servers.get(key):
            what = t.servers.get(key, key)
            return f"{what} is not connected: add its MCP server to Claude Code, then pick it here"
    return ""


# -- the skill and the form -------------------------------------------------------------------------------------

def skill_body(t: Template) -> str:
    """SKILL.md without its front matter."""
    text = t.skill.replace("\r\n", "\n")
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            text = text[end + 4:].split("\n", 1)[1] if "\n" in text[end + 4:] else ""
    return text.strip()


def clean_fields(t: Template, given: object, last: dict | None = None) -> dict[str, str]:
    """The form as given, checked: each field of the template (a default, else the last value of a `remember` one,
    when none is given), a required one present, a choice among its options, at most VALUE_MAX characters. Raises
    ValueError in words; an unknown name is dropped."""
    given = given if isinstance(given, dict) else {}
    out: dict[str, str] = {}
    for f in t.fields:
        value = given.get(f["name"])
        if value is None:
            value = (last or {}).get(f["name"]) if f.get("remember") else None
            value = f.get("default", "") if value is None else value
        if not isinstance(value, str):
            raise ValueError(f"{f['label']} is a text")
        value = value.strip() if f["type"] != "long" else value.strip("\n ")
        if len(value) > VALUE_MAX:
            raise ValueError(f"{f['label']} is longer than {VALUE_MAX} characters")
        if f.get("required") and not value:
            raise ValueError(f"{f['label']} is needed")
        if f["type"] == "choice" and value and value not in f["options"]:
            raise ValueError(f"{f['label']} is one of: {', '.join(f['options'])}")
        out[f["name"]] = value
    return out


def clean_draft(t: Template, given: object) -> dict[str, str]:
    """The draft parts the template names, each a text of at most VALUE_MAX; anything else dropped."""
    given = given if isinstance(given, dict) else {}
    out = {}
    for p in t.draft:
        value = given.get(p["name"])
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = str(value)
        out[p["name"]] = value[:VALUE_MAX] if isinstance(value, str) else ""
    return out


def put(args: dict, at: str, value: Any) -> dict:
    """`value` written at the dotted path `at` of `args` (made where missing; a non-object on the way replaced)."""
    keys = at.split(".")
    here = args
    for key in keys[:-1]:
        if not isinstance(here.get(key), dict):
            here[key] = {}
        here = here[key]
    here[keys[-1]] = value
    return args


def with_values(t: Template, args: dict, fields: dict, draft: dict) -> dict:
    """The arguments with every field and draft part that has `at` written into them: they say what the check shows."""
    out = copy.deepcopy(args) if isinstance(args, dict) else {}
    for f in t.fields:
        if f.get("at") and f["name"] in fields:
            put(out, f["at"], fields[f["name"]])
    for p in t.draft:
        if p.get("at") and p["name"] in draft:
            put(out, p["at"], draft[p["name"]])
    return out


def public(t: Template) -> dict:
    """What `ops.list` shows of a template's form: its fields and draft parts as the manifest says them."""
    return {"name": t.name, "title": t.title, "risk": t.risk, "fields": [dict(f) for f in t.fields],
            "draft": [dict(p) for p in t.draft], "act_label": t.act_label, "brief": t.brief, "people": t.people,
            "reads": t.reads, "follow": t.follow}


def same_value(a: object, b: object) -> bool:
    """Two values of a follow field as the same person or team: compared as written, trimmed, ignoring case (spec 66
    §4); an empty one is no one."""
    a, b = str(a or "").strip().casefold(), str(b or "").strip().casefold()
    return bool(a) and a == b
