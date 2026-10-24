"""A release (docs/specs/67-release-and-route.md §3, decisions §81.5–§81.6): a goal of the type *A release*, a version and the goals
that go in. **What goes in** is the flags raised since the last release that is out, in the parties the release's party
*releases from*; the person ticks them. A release keeps its own file beside its state, `<state_dir>/ideas/<slug>/release.json`
(`{version, goals, out, at}`), and the goals that go in are never written: their route reads the releases (realm/idea_route.py).

    read(state_dir, "release-1-4")                 # {version, goals, out, at}; None for a goal that is not a release
    index(root, state_dir)                         # every release of the project: [{goal, party, version, goals, out, at}]
    holding(root, state_dir)                       # {goal that goes in: [the releases that hold it]}
    releases_from(root, "release")                 # the slugs the party was set to release from ([] = the default)
    sources(root, "release")                       # the parties it releases from now: the default, the set ones, or itself
    candidates(root, state_dir, "release")         # [{goal, title, party, party_name, element, at, commit, held}], newest flag first
    since(root, state_dir, "release")              # {version, out} of the party's last release that is out; None before the first
    tally(root, state_dir, "release")               # a Release party's work: {made, out, goals, days}
    wait(root, state_dir, "release")               # how many candidates are not held (a party that offers *A release*; else 0)
    make(root, state_dir, "release-1-4", "1.4", ["dark-mode"], "release")      # the release's file; ValueError for a goal not listed or held
    out(root, state_dir, "release-1-4")            # the release is out now (only after its own flag, once); the date
    prompt_lines(root, state_dir, "release-1-4")   # for the draft and plan prompts: the version and the goals that go in ("" for any other goal)

Orkboard never submits, uploads or tags: *out* is the person's word (spec 67 §3.5). No face, no model.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from orkboard.realm import goal_team, goal_types, idea_element, idea_flag, ideas, library

FILE = "release.json"
KEY = "releases_from"                    # a party's page, front matter: a JSON list of party slugs
PROMPT_CHARS = 3000                      # what the draft's and the plan's prompts read of the goals that go in
VERSION_CHARS = 40
DONE_CHARS = 200                         # of one goal's Done when lines in the prompt


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def version_of(value: object) -> str:
    return " ".join(value.split())[:VERSION_CHARS] if isinstance(value, str) else ""


def _path(state_dir: Path, slug: str) -> Path:
    return ideas.state_folder(state_dir, slug) / FILE


def read(state_dir: Path, slug: str) -> dict | None:
    """A release's file as kept, `{version, goals, out, at}`; None for a goal that is not a release."""
    try:
        got = ideas._json(_path(state_dir, slug))
    except ValueError:
        return None
    if got is None:
        return None
    goals = got.get("goals")
    return {"version": version_of(got.get("version")), "goals": [g for g in goals if isinstance(g, str)] if isinstance(goals, list) else [],
            "out": str(got.get("out") or ""), "at": str(got.get("at") or "")}


def index(root: Path, state_dir: Path, found: list[dict] | None = None) -> list[dict]:
    """Every release of the project (a release goal dropped is gone with its page), oldest first: `{goal, party, version, goals, out, at}`.
    `found`: `ideas.ideas(root)` when the caller has it read."""
    out = []
    for i in ideas.ideas(root) if found is None else found:
        if (got := read(state_dir, i["slug"])) is not None:
            out.append({"goal": i["slug"], "party": i["track"], **got})
    return sorted(out, key=lambda r: (r["at"], r["goal"]))


def holding(root: Path, state_dir: Path, rows: list[dict] | None = None) -> dict[str, list[dict]]:
    """{goal that goes in: the releases that hold it}, oldest release first. `rows`: `index()` read once."""
    held: dict[str, list[dict]] = {}
    for r in index(root, state_dir) if rows is None else rows:
        for g in r["goals"]:
            held.setdefault(g, []).append(r)
    return held


def step_of(r: dict) -> dict:
    """A release as a goal's route and a flag say it: `{goal, party, version, out}`."""
    return {"goal": r["goal"], "party": r["party"], "version": r["version"], "out": r["out"]}


# -- Releases from ---------------------------------------------------------------------------------------------------------

def releases_from(root: Path, party: str) -> list[str]:
    """The party slugs a party was set to release from, as its page keeps them ([] when never set: the default)."""
    page = ideas.track_page(root, party)
    return [s for s in ideas._json_list(page.get(KEY)) if isinstance(s, str)] if page is not None else []


def set_releases_from(root: Path, party: str, slugs: object) -> list[str]:
    """Kept on the party's page: the parties of the project but the party itself, Ideation's and General (each once, at most the project's);
    [] is the default. ValueError for something that is not a list of parties."""
    if not isinstance(slugs, list) or any(not isinstance(s, str) for s in slugs):
        raise ValueError("Releases from is a list of parties")
    with ideas.LOCK:
        page = ideas.track_page(root, party)
        if page is None:
            raise ValueError(f"No party {party!r}")
        known = {t["slug"] for t in ideas.tracks(root, make=False) if t["slug"] not in (ideas.GENERAL, party) and t.get("leader") != library.INVESTOR}
        if bad := [s for s in slugs if s not in known]:
            raise ValueError(f"No party {bad[0]!r} to release from")
        kept = list(dict.fromkeys(slugs))
        if page.get(KEY, "") != (json.dumps(kept) if kept else ""):
            page.set(KEY, json.dumps(kept) if kept else "")
            ideas._write(Path(root) / ideas.TRACKS / f"{party}.md", page.text())
    return kept


def sources(root: Path, party: str) -> list[str]:
    """The parties a party releases from now: for a Release party (the Release manager leads it) the ones it was set to, else every party
    of the project but General, Ideation and itself; for any other party, itself."""
    page = ideas.track_page(root, party)
    if page is None or (page.get("leader") or "") != library.RELEASE_MANAGER:
        return [party]
    every = [t["slug"] for t in ideas.tracks(root, make=False)
             if t["slug"] not in (ideas.GENERAL, party) and t.get("leader") != library.INVESTOR]
    set_ = [s for s in releases_from(root, party) if s in every]
    return set_ or every


# -- What goes in ----------------------------------------------------------------------------------------------------------

def since(root: Path, state_dir: Path, party: str, rows: list[dict] | None = None) -> dict | None:
    """The party's last release that is out, `{version, out}`; None before its first."""
    outs = [r for r in (index(root, state_dir) if rows is None else rows) if r["party"] == party and r["out"]]
    last = max(outs, key=lambda r: (r["out"], r["at"]), default=None)
    return {"version": last["version"], "out": last["out"]} if last else None


def candidates(root: Path, state_dir: Path, party: str, rows: list[dict] | None = None) -> list[dict]:
    """The goals with a flag in the parties `party` releases from, raised after its last release that is out (all of them before the first),
    newest first: `{goal, title, party, party_name, element, at, commit, held}`. `held`: the version of an open release (not out) that holds
    it, else ""; a held one cannot be ticked. A release's own flag is never listed."""
    rows = index(root, state_dir) if rows is None else rows
    last = (since(root, state_dir, party, rows) or {}).get("out") or ""
    held = {g: r["version"] or "a release" for g, rs in holding(root, state_dir, rows).items() for r in rs if not r["out"]}   # an open release's version
    isrelease = {r["goal"] for r in rows}
    names = {t["slug"]: t["title"] for t in ideas.tracks(root, make=False)}
    out = []
    for p in sources(root, party):
        for i in ideas.ideas(root, p):
            flag = idea_flag.flag_of(state_dir, i["slug"])
            if flag is None or i["slug"] in isrelease or (last and str(flag["at"]) <= last):
                continue
            out.append({"goal": i["slug"], "title": i["title"], "party": p, "party_name": names.get(p, p),
                        "element": idea_element.of(state_dir, i["slug"]), "at": flag["at"], "commit": str(flag.get("commit") or ""),
                        "held": held.get(i["slug"], "")})
    return sorted(out, key=lambda c: (c["at"], c["goal"]), reverse=True)


def offers(state_dir: Path, root: Path, party: str, rel: str | None = None) -> bool:
    """Whether the party is offered *A release* (realm/goal_types.py `offered`: its Release party alone when the project has one). `rel`:
    `goal_types.release_party(root)` when the caller has it read. The types are asked only of a party with someone who writes store pages."""
    if (ideas.track_page(root, party) or ideas.Page()).get("leader") == library.INVESTOR:
        return False
    rel = goal_types.release_party(root) if rel is None else rel
    if rel:
        return party == rel
    if not any("aso" in goal_types._takes(state_dir, m) for m in goal_team.team_of(root, party)):
        return False                             # *A release* needs `aso`: no one takes it, the type is not offered (and the types not read)
    return any(t.id == "release" for t, _rows in goal_types.offered(state_dir, root, party))


def wait(root: Path, state_dir: Path, party: str, rows: list[dict] | None = None, rel: str | None = None) -> int:
    """How many flags wait for a release in `party` (a party that offers *A release*): its candidates not held; 0 for any other."""
    if not offers(state_dir, root, party, rel):
        return 0
    return sum(1 for c in candidates(root, state_dir, party, rows) if not c["held"])


# -- make, out --------------------------------------------------------------------------------------------------------------

def check(root: Path, state_dir: Path, party: str, goes_in: object) -> list[str]:
    """The slugs ticked for a release of `party`, each once, checked against what goes in: ValueError (in the person's words) for a goal
    that is not listed (it has no flag in a party this one releases from, or it was in a release that is out) or one another open
    release holds."""
    if goes_in is None:
        return []
    if not isinstance(goes_in, list) or any(not isinstance(s, str) for s in goes_in):
        raise ValueError("goes_in is a list of goals")
    listed = {c["goal"]: c for c in candidates(root, state_dir, party)}
    out = []
    for slug in dict.fromkeys(s.strip() for s in goes_in):
        c = listed.get(slug)
        if c is None:
            raise ValueError("That goal has not raised its flag in a party this release takes from")
        if c["held"]:
            raise ValueError(f"“{c['title']}” is in {c['held']} already")
        out.append(slug)
    return out


def make(state_dir: Path, slug: str, version: object, goals: list[str]) -> dict:
    """The release's file written (`out` empty): `{version, goals, out, at}`. Call `check` first; this keeps what it is given."""
    got = {"version": version_of(version), "goals": list(goals), "out": "", "at": _now()}
    with ideas.LOCK:
        ideas._write_json(_path(state_dir, slug), got)
    return got


def out(root: Path, state_dir: Path, slug: str) -> dict:
    """The release is out now: `{out, goals, days}`. ValueError: not a release; its own flag not raised (it is not in main); out already.
    `days`: whole days from its first goal's flag to now (None when no goal that went in has a flag)."""
    with ideas.LOCK:
        rel = read(state_dir, slug)
        if rel is None:
            raise ValueError("That goal is not a release")
        if rel["out"]:
            raise ValueError(f"{rel['version'] or 'This release'} is out already")
        if idea_flag.flag_of(state_dir, slug) is None:
            raise ValueError("Its flag is not raised yet: a release goes out once it is in main")
        now = _now()
        ideas._write_json(_path(state_dir, slug), {**rel, "out": now})
    return {"out": now, "goals": len(rel["goals"]), "days": _days(state_dir, {**rel, "out": now})}


# -- measured (§4) ------------------------------------------------------------------------------------------------------------

def _days(state_dir: Path, r: dict) -> int | None:
    """Whole days from the first flag of the goals that went into a release to its going out; None when none has a flag or it is not out."""
    firsts = []
    for g in r["goals"]:
        flag = idea_flag.flag_of(state_dir, g)
        try:
            firsts.append(dt.datetime.fromisoformat(flag["at"])) if flag else None
        except (ValueError, TypeError):
            pass
    try:
        return max(0, (dt.datetime.fromisoformat(r["out"]) - min(firsts)).days) if firsts and r["out"] else None
    except (ValueError, TypeError):
        return None


def tally(root: Path, state_dir: Path, party: str, rows: list[dict] | None = None) -> dict:
    """A Release party's work (spec 43 §2, spec 67 §4): `{made, out, goals, days}`: the releases made, those out, goals a release (the
    average over those made; None before one) and the days from a flag to out (the average over those out with a flag; None before one)."""
    mine = [r for r in (index(root, state_dir) if rows is None else rows) if r["party"] == party]
    days = [d for r in mine if (d := _days(state_dir, r)) is not None]
    return {"made": len(mine), "out": sum(1 for r in mine if r["out"]),
            "goals": round(sum(len(r["goals"]) for r in mine) / len(mine), 1) if mine else None,
            "days": round(sum(days) / len(days), 1) if days else None}


# -- the prompts -----------------------------------------------------------------------------------------------------------

def prompt_lines(root: Path, state_dir: Path, slug: str) -> str:
    """For the draft's and the plan's prompts, beside the type's line: the version and, for each goal that goes in, its title, its Done when
    and its flag's commit, at most PROMPT_CHARS (the last goals cut first, *and k more* said); "" for a goal that is not a release. Nothing
    else of the parties is read."""
    rel = read(state_dir, slug)
    if rel is None:
        return ""
    head = (f"This goal is a release. Its version: {rel['version']}.\n" if rel["version"] else "This goal is a release. Its version is not set yet.\n")
    if not rel["goals"]:
        return head + "No goal goes in yet: plan only the version, its notes and the stores' list.\n"
    head += "The goals that go in (nothing else goes in; plan no new work):\n"
    lines, used = [], len(head)
    for n, g in enumerate(rel["goals"]):
        page = ideas.idea_page(root, g)
        if page is None:
            continue
        done = "; ".join(ideas.items(page.section("Done when")))[:DONE_CHARS]
        flag = idea_flag.flag_of(state_dir, g) or {}
        line = f"- {page.title or g}" + (f" — Done when: {done}" if done else "") + (f" — flag: commit {flag['commit']}" if flag.get("commit") else "") + "\n"
        rest = len(rel["goals"]) - n
        if used + len(line) > PROMPT_CHARS - len(f"- and {rest} more\n"):
            lines.append(f"- and {rest} more\n")
            break
        lines.append(line)
        used += len(line)
    return head + "".join(lines)
