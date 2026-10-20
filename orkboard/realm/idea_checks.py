"""The checks a goal's team holds its ideas to (realm/library.py `Check`): the team sets how deep an idea is worked. Each
checker of the team asks, of every idea of the goal, whether its check applies; when it does, its line goes in the spec's
Done when and its task in the plan, after the work it checks; when it does not, the Taskmaster says why. A checker set
to `every` idea applies always.

    of_team(state_dir, ["accessibility-reviewer", "grunt"], every=["reviewer"])   # the team's checks
    draft_lines(checks)               # for the draft prompt: each check, when it applies, its Done when line
    kept(answer.get("checks"), checks)  # what the draft said, as the page keeps it: [{"by", "applies", "why", "skipped"?}]
    skip(kept_, checks, "reviewer")   # the person skips a check: kept with `skipped`
    plan_lines(kept_, checks)         # for the plan prompt: the checks that apply, each one task
    with_check_tasks(tasks, kept_, checks)  # the plan's tasks, a check task added where the plan left one out
    status(kept_, checks, tasks)      # for a face: each check, whether it applies, why not, its task's state, what it found
    parse_findings(text)              # what a check task wrote in FINDINGS_FILE: its findings, or None

A check is its checker's: an agent of the library the project has as a role (its instruction may be the person's now),
its check the library's. No face, no model.
"""
from __future__ import annotations

import json
from pathlib import Path

from orkboard.realm import library, roles

DONE = ("merged",)                   # a check task in these states has passed
TAGS = tuple(dict.fromkeys(a.takes[0] for a in library.LIBRARY if a.check is not None))   # a check task's `kind`
FINDINGS_FILE = ".orkcraft-findings.json"    # a check task writes what it found here; the runner reads it and removes it
FINDINGS_MAX, WHERE_MAX, WHAT_MAX, FINDINGS_BYTES = 20, 200, 300, 64 * 1024


def parse_findings(text: str) -> list[dict] | None:
    """The findings a check task wrote, `{"findings": [{"where", "what", "fixed"}]}`, read strictly: at most 20, `where` at
    most 200 characters, `what` at most 300, `fixed` true or false. None for bad JSON or any other shape."""
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None
    rows = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(rows, list) or len(rows) > FINDINGS_MAX:
        return None
    out = []
    for x in rows:
        if not isinstance(x, dict) or not isinstance(x.get("where"), str) or not isinstance(x.get("what"), str) \
                or not isinstance(x.get("fixed"), bool) or len(x["where"]) > WHERE_MAX or len(x["what"]) > WHAT_MAX:
            return None
        out.append({"where": x["where"], "what": x["what"], "fixed": x["fixed"]})
    return out


def counts(findings: object) -> dict:
    """{found, fixed, left} of a task's findings; all three None while it has none (it has not ended)."""
    if not isinstance(findings, list):
        return {"found": None, "fixed": None, "left": None}
    fixed = sum(1 for f in findings if isinstance(f, dict) and f.get("fixed") is True)
    return {"found": len(findings), "fixed": fixed, "left": len(findings) - fixed}


def of_team(state_dir: Path, team: list[str], every: list[str] | None = None) -> list[dict]:
    """The checks of a team, in its order: {by, name, tag, tier, applies, done, task, every}."""
    out = []
    for slug in team or []:
        a = library.get(slug)
        if a is None or a.check is None:
            continue
        r = roles.role(state_dir, slug)
        out.append({"by": slug, "name": (r or {}).get("name") or a.name, "tag": a.takes[0], "tier": a.tier,
                    "applies": a.check.applies, "done": a.check.done, "task": a.check.task, "every": slug in (every or [])})
    return out


def draft_lines(checks: list[dict]) -> str:
    """The draft prompt's part: each check with when it applies and the line it adds ("" with no check)."""
    if not checks:
        return ""
    rows = "\n".join(f"- {c['by']} ({c['name']}): " + ("applies to every idea" if c["every"] else f"applies {c['applies']}")
                     + f'; its Done when line: "{c["done"]}"' for c in checks)
    return ("The goal's team checks its ideas. For each check below, decide whether it applies to this idea; when it "
            "does, add its Done when line to done_when as written; say it in \"checks\" either way, with a one-line why "
            "when it does not apply:\n" + rows + "\n")


def kept(answer: object, checks: list[dict]) -> list[dict]:
    """What the draft said of the team's checks, as the page keeps it: one per check, in the team's order. A check the
    draft left out applies (the safer side); one set to every idea applies whatever it said. One the person skipped stays
    skipped."""
    said = {}
    for x in answer if isinstance(answer, list) else []:
        if isinstance(x, dict) and isinstance(x.get("by"), str):
            said[x["by"]] = x
    out = []
    for c in checks:
        x = said.get(c["by"], {})
        applies = True if c["every"] or "applies" not in x else bool(x.get("applies"))
        why = "" if applies else " ".join(str(x.get("why") or "").split())[:200] or "Does not apply"
        out.append({"by": c["by"], "applies": applies, "why": why, **({"skipped": True} if x.get("skipped") is True else {})})
    return out


def on(kept_: list[dict]) -> set[str]:
    """The checks an idea goes through: the ones that apply, not skipped."""
    return {k["by"] for k in kept_ if k["applies"] and not k.get("skipped")}


def skip(kept_: list[dict], checks: list[dict], by: str, skipped: bool = True) -> list[dict]:
    """The kept checks with `by` skipped (or not again); ValueError when the team has no such check."""
    if not any(c["by"] == by for c in checks):
        raise ValueError("The goal's party has no such check")
    rows = kept(kept_, checks)
    for k in rows:
        if k["by"] == by:
            k.pop("skipped", None)
            if skipped:
                k["skipped"] = True
    return rows


def plan_lines(kept_: list[dict], checks: list[dict]) -> str:
    """The plan prompt's part: the checks this spec must pass, each one task with its tag, after the work it checks."""
    go = on(kept_)
    rows = [f'- {c["name"]}: a task tagged "{c["tag"]}", after the work it checks: {c["task"]}' for c in checks if c["by"] in go]
    return ("The checks this spec must pass, one task each:\n" + "\n".join(rows) + "\n") if rows else ""


def with_check_tasks(tasks: list[dict], kept_: list[dict], checks: list[dict], make) -> list[dict]:
    """The plan's tasks with a check task for each check that applies and has none of its tag yet, after every other
    task. `make(id, title, brief, tag, tier, after)`: a task as the plan writes it (core/idea_keeper.py `_task`)."""
    go = on(kept_)
    out = list(tasks)
    for c in checks:
        if c["by"] in go and not any(t.get("kind") == c["tag"] for t in out):
            out.append(make(f"k{len(out) + 1}", f"Check: {c['name']}", c["task"], c["tag"], c["tier"], [t["id"] for t in tasks]))
    return out


def status(kept_: list[dict], checks: list[dict], tasks: list[dict]) -> list[dict]:
    """Each check for a face: {by, name, applies, why, state, task, skipped, tier, found, fixed, left}: its task's state
    ("" before a plan; "passed" merged), its task's id ("" with none), whether the person skipped it, the tier it runs at,
    and what it found (null before its task ends, or when it ended without findings)."""
    byc = {c["by"]: c for c in checks}
    out = []
    for k in kept_:
        c = byc.get(k["by"])
        if c is None:
            continue
        t = next((t for t in tasks if t.get("kind") == c["tag"]), None)
        state = "" if t is None else "passed" if t.get("state") in DONE else str(t.get("state") or "")
        skipped = bool(k.get("skipped")) and (t is None or t.get("state") not in DONE)
        out.append({"by": k["by"], "name": c["name"], "applies": k["applies"], "why": k["why"], "state": state if k["applies"] and not skipped else "",
                    "task": (t or {}).get("id") or "", "skipped": skipped, "tier": c["tier"],
                    **counts((t or {}).get("findings") if (t or {}).get("state") in ("review", *DONE) else None)})
    return out
