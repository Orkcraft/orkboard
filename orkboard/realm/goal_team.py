"""A goal's team (decisions §53): the agents of the project who do its tasks, picked from the library when the goal is
made (realm/library.py). It is kept on the goal's page (`team`, a JSON list of role slugs); the Taskmaster plans for
every team and is never in the list.

    set_team(root, "ship", ["product-designer", "reviewer"], every=["reviewer"])   # kept, at most SEATS; `every`: checkers
                                                                # whose check applies to every idea (realm/idea_checks.py)
    team_of(root, "ship")                                       # ["product-designer", "reviewer"]; [] with none
    every_of(root, "ship")                                      # ["reviewer"]
    for_idea(root, "dark-mode")                                 # the team of the idea's goal; every_for_idea, its every

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


def set_team(root: Path, slug: str, team: list[str], every: list[str] | None = None) -> None:
    with ideas.LOCK:
        page = ideas.track_page(root, slug)
        if page is None:
            raise ValueError(f"No goal {slug!r}")
        kept = clean(team)
        page.set("team", json.dumps(kept))
        page.set("team_every", json.dumps([s for s in clean(every or []) if s in kept]))
        ideas._write(Path(root) / ideas.TRACKS / f"{slug}.md", page.text())


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
