"""Hints while a party is picked (docs/specs/43-party-measured.md §5): at most two plain lines about a party the person is
choosing, from what its checkers found lately and what the library says they fit. A hint never blocks Save and has no button.
No face, no model, it writes nothing.

    party_hints.hints(root, state_dir, "data", "analyst", ["data-engineer", "accessibility-reviewer"], [])
    # ["Accessibility reviewer seldom checks a Data goal: it checks when the idea changes what people see or use."]
"""
from __future__ import annotations

from pathlib import Path

from orkboard.realm import library, party_work, roles

MOST = 2                   # hints at most
ENOUGH = 8                 # checks a checker needs in the last 30 days before "found nothing" is said
DAYS = 30
CODE_CRAFTS = ("engineering", "product")    # the goals whose party should hold someone who writes code


def _name(state_dir: Path, slug: str) -> str:
    a = library.get(slug)
    if a is not None:
        return a.name
    r = roles.role(state_dir, slug)
    return r["name"] if r else slug


def _takes(state_dir: Path, slug: str) -> list[str]:
    """The task types an agent takes in a party: the library's, else the project's role's own."""
    a = library.get(slug)
    if a is not None:
        return list(a.takes)
    r = roles.role(state_dir, slug)
    return sorted(roles.takes_of(r, roles.kinds(state_dir))) if r else []


def _band(slug: str) -> str:
    a = library.get(slug)
    return a.band if a is not None else "build"


def _craft_words(craft: str) -> str:
    return f"{'an' if craft == 'engineering' else 'a'} {craft.capitalize()} goal"


def hints(root: Path, state_dir: Path, craft: str, leader: str, team: list[str], every: list[str]) -> list[str]:
    """§5's hints for the party (`craft` the goal's, "" when not known), in the spec's order and at most two."""
    root, state_dir = Path(root), Path(state_dir)
    checkers = [(i, a) for i in team if (a := library.get(i)) is not None and a.check is not None]
    out: list[str] = []
    if checkers:
        records = party_work.check_records(root, state_dir, DAYS)
        for i, a in checkers:
            r = records.get(i) or {}
            if int(r.get("checks") or 0) >= ENOUGH and not int(r.get("caught") or 0):
                out.append(f"{a.name} found nothing in its last {r['checks']} checks.")
    if craft in roles.CRAFTS:
        for _i, a in checkers:
            if a.check.fits and craft not in a.check.fits:
                out.append(f"{a.name} seldom checks {_craft_words(craft)}: it checks {a.check.applies}.")
    leader = leader or roles.TASKMASTER
    if craft in CODE_CRAFTS and not any("code" in _takes(state_dir, m) for m in [leader, *team]):
        out.append("No one in the party writes code: code tasks go to this project's agent for code (the Grunt when none).")
    if leader != roles.TASKMASTER and not any(_band(i) == "build" for i in team):
        out.append("No builders: each task goes to this project's agent for its type (the Grunt when none).")
    return out[:MOST]
