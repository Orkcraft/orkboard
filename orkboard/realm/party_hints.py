"""Quiet hints while a party is picked (docs/specs/43-party-measured.md §5): at most two lines, in this order, never a block —
a checker that has found nothing lately, a checker that seldom applies to the goal's craft, no one in the party who writes code, and a
leader with no builder. A pure read of the plans and the library: no face, no model, it writes nothing.

    party_hints.hints(root, state_dir, "data", "analyst", ["accessibility-reviewer"], [])   # ["Accessibility reviewer seldom checks a Data goal: …"]
"""
from __future__ import annotations

from pathlib import Path

from orkboard.realm import goal_team, library, party_work, roles

MOST = 2                            # hints at most
LONG_QUIET = 8                      # checks (the last 30 days) with none caught before a checker is said to find nothing


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def takes_code(state_dir: Path, slug: str) -> bool:
    """Whether an agent of the party takes `code`: the library's, else the person's own (a role's `takes`, or the project's task types given to it)."""
    a = library.get(slug)
    if a is not None:
        return "code" in a.takes
    r = roles.role(state_dir, slug)
    return r is not None and "code" in roles.takes_of(r, roles.kinds(state_dir))


def hints(root: Path, state_dir: Path, craft: str, leader: str, team: list[str], every: list[str] | None = None) -> list[str]:
    """The hints for a party of `leader` and `team` of a goal of `craft` ("" when it has none, a Mixed goal), at most two."""
    members = [s for s in team if goal_team.band_of(s) == "build" or goal_team.band_of(s) == "check"]
    checkers = [s for s in team if goal_team.band_of(s) == "check" and library.get(s) is not None and library.get(s).check is not None]
    lead = leader or roles.TASKMASTER
    out: list[str] = []
    for by in checkers:                                                                           # 1. a check that has found nothing lately
        record = party_work.check_record(root, state_dir, by, 30)
        if record["checks"] >= LONG_QUIET and record["caught"] == 0:
            out.append(f"{party_work.who(state_dir, by)['name']} found nothing in its last {record['checks']} checks.")
    if craft in roles.CRAFTS:
        word = roles.CRAFT_LABELS[craft]
        for by in checkers:                                                                       # 2. a check that seldom applies to this craft
            a = library.get(by)
            if craft not in a.check.fits:
                out.append(f"{a.name} seldom checks {_article(word)} {word} goal: it checks {a.check.applies}.")
        if craft in ("engineering", "product") and not any(takes_code(state_dir, s) for s in [*members, *([lead] if lead != roles.TASKMASTER else [])]):
            out.append("No one in the party writes code: code tasks go to this project's agent for code (the Grunt when none).")   # 3.
    if lead != roles.TASKMASTER and not any(goal_team.band_of(s) == "build" for s in team):       # 4. a leader and no builder
        out.append("No builders: each task goes to this project's agent for its type (the Grunt when none).")
    return out[:MOST]
