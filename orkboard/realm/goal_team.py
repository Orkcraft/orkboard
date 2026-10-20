"""A goal's team (decisions §53): the agents of the project who do its tasks, picked from the library when the goal is
made (realm/library.py). It is kept on the goal's page (`team`, a JSON list of role slugs); the Taskmaster plans for
every team and is never in the list.

    set_team(root, "ship", ["product-designer", "reviewer"], every=["reviewer"])   # kept, at most SEATS; `every`: checkers
                                                                # whose check applies to every idea (realm/idea_checks.py)
    team_of(root, "ship")                                       # ["product-designer", "reviewer"]; [] with none
    every_of(root, "ship")                                      # ["reviewer"]
    for_idea(root, "dark-mode")                                 # the team of the idea's goal; every_for_idea, its every

A goal's party (library.SEATS): one leader — the goal's steps (its reading, its ideas' drafts, answers and plans, and
accepting the goal) run as it; the Taskmaster when none is picked —, at most three builders and two checkers (the team).

    party_of(root, "ship")                                      # the id of the person's saved party it was picked from, "" if none

    leader_of(root, "ship")                                     # "product-manager"; "taskmaster" when none was picked
    seats(team, leader)                                         # the error of a party that has too many in a band, else ""

A goal with no team works as before: each task type goes to the project's role for it (Grunt when none).

No face, no model.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from orkboard.realm import ideas

SEATS = 5


def clean(team: object) -> list[str]:
    """The slugs of a team as given: known shapes only, no Taskmaster, each once, at most SEATS."""
    if not isinstance(team, (list, tuple)):
        raise ValueError("A team is a list of agents")
    got = [str(s).strip() for s in team if re.fullmatch(r"[a-z0-9-]{1,60}", str(s).strip()) and str(s).strip() != "taskmaster"]
    if len(dict.fromkeys(got)) > SEATS:
        raise ValueError(f"A team has at most {SEATS} agents")
    return list(dict.fromkeys(got))


def band_of(slug: str) -> str:
    """An agent's band in a party: the library's, a person's own agent a builder."""
    from orkboard.realm import library
    a = library.get(slug)
    return a.band if a is not None else "build"


def seats(team: list[str], leader: str = "") -> str:
    """Why a party does not fit its seats ("" when it does): one leader, three builders, two checkers at most."""
    from orkboard.realm import library
    if leader and band_of(leader) != "lead":
        return f"{leader} does not lead: pick a leader of the library"
    for band, words in (("build", "builders"), ("check", "checkers")):
        if sum(1 for s in team if band_of(s) == band) > library.SEATS[band]:
            return f"A party has at most {library.SEATS[band]} {words}"
    if any(band_of(s) == "lead" for s in team):
        return "A leader leads: it is not one of the builders or checkers"
    return ""


def leader_of(root: Path, slug: str) -> str:
    page = ideas.track_page(root, slug)
    return (page.get("leader") if page is not None else "") or "taskmaster"


def set_team(root: Path, slug: str, team: list[str], every: list[str] | None = None, leader: str | None = None,
             party: str | None = None) -> None:
    """The goal's party kept. `party`: the id of the person's saved party (realm/own_parties.py) it was picked from, kept on
    the page; a party that comes out different from the goal's (and `party` not given) is no longer that one: the id goes."""
    with ideas.LOCK:
        page = ideas.track_page(root, slug)
        if page is None:
            raise ValueError(f"No goal {slug!r}")
        kept = clean(team)
        was = (page.get("team"), page.get("team_every"), page.get("leader") or "")
        page.set("team", json.dumps(kept))
        page.set("team_every", json.dumps([s for s in clean(every or []) if s in kept]))
        if leader is not None:
            page.set("leader", leader if leader != "taskmaster" else "")
        if party is not None:
            page.set("party", party)
        elif page.get("party") and was != (page.get("team"), page.get("team_every"), page.get("leader") or ""):
            page.set("party", "")
        ideas._write(Path(root) / ideas.TRACKS / f"{slug}.md", page.text())


def party_of(root: Path, slug: str) -> str:
    page = ideas.track_page(root, slug)
    return (page.get("party") if page is not None else "") or ""


def team_of(root: Path, slug: str) -> list[str]:
    page = ideas.track_page(root, slug)
    return ideas._json_list(page.get("team")) if page is not None else []


def every_of(root: Path, slug: str) -> list[str]:
    page = ideas.track_page(root, slug)
    return ideas._json_list(page.get("team_every")) if page is not None else []


def for_idea(root: Path, idea: str) -> list[str]:
    page = ideas.idea_page(root, idea)
    return team_of(root, page.get("track") or ideas.GENERAL) if page is not None else []


def every_for_idea(root: Path, idea: str) -> list[str]:
    page = ideas.idea_page(root, idea)
    return every_of(root, page.get("track") or ideas.GENERAL) if page is not None else []
