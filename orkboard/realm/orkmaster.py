"""The Orkmaster (docs/specs/70-orkmaster-and-the-project.md §1, decisions §85): the project's ork. It deals the parties New party offers
and suggests a goal's party. By rules, with no model; it plans nothing, moves nothing, writes nothing.

    ORKMASTER                                   # {"id", "name", "race", "tier"}: the head the faces draw
    deal(root, state_dir)                       # every preset once, in the order New party shows: [{"id", "why", "n"}]
    party_for(state_dir, root, "logo")          # the project's parties but General, each how it fits a goal type: [{party, name, fits, missing}]
    suggested(parties)                          # the slug `party_for`'s answer suggests

`why` of a deal row: `flags_wait` (Release first: no party releases and `n` flags wait), `no_pitches` (Ideation next: no party judges small
ideas), `have` (the project has one: last), else "". No face, no model, no write.
"""
from __future__ import annotations

from pathlib import Path

from orkboard.realm import goal_types, idea_flag, ideas, library

ORKMASTER = {"id": "orkmaster", "name": "Orkmaster", "race": "peon", "tier": "elder"}
RELEASE, IDEATION = "release", "ideation"       # the presets' ids


def flags_by_party(root: Path, state_dir: Path, tracks: list[dict] | None = None) -> dict[str, int]:
    """{party slug: goals with a flag} of every party but General and Ideation's (what a Release party would release from)."""
    out = {}
    for t in tracks if tracks is not None else ideas.tracks(root, make=False):
        if t["slug"] == ideas.GENERAL or (t.get("leader") or "") == library.INVESTOR:
            continue
        out[t["slug"]] = sum(1 for i in ideas.ideas(root, t["slug"]) if idea_flag.flag_of(state_dir, i["slug"]) is not None)
    return out


def deal(root: Path, state_dir: Path, *, tracks: list[dict] | None = None, flags: dict[str, int] | None = None) -> list[dict]:
    """Every preset of the library once, as `[{"id", "why", "n"}]` (spec 70 §1.1): Release first when the project has no party the Release
    manager leads and flags wait (`flags_wait`, `n` their count); Ideation next when no party the Investor leads (`no_pitches`); then the
    others in the library's order; last, Release and Ideation when the project has one (`have`). `tracks`, `flags` (`flags_by_party`):
    what the caller has read already."""
    tracks = ideas.tracks(root, make=False) if tracks is None else tracks
    leaders = {t.get("leader") or "" for t in tracks}
    has_release, has_pitches = library.RELEASE_MANAGER in leaders, library.INVESTOR in leaders
    n = 0 if has_release else sum((flags_by_party(root, state_dir, tracks) if flags is None else flags).values())
    ids = [p["id"] for p in library.presets()]
    rows = {i: {"id": i, "why": "", "n": 0} for i in ids}
    head, tail = [], []
    if has_release:
        rows[RELEASE]["why"] = "have"
        tail.append(RELEASE)
    elif n > 0:
        rows[RELEASE].update(why="flags_wait", n=n)
        head.append(RELEASE)
    if has_pitches:
        rows[IDEATION]["why"] = "have"
        tail.append(IDEATION)
    else:
        rows[IDEATION]["why"] = "no_pitches"
        head.append(IDEATION)
    rest = [i for i in ids if i not in head and i not in tail]
    return [rows[i] for i in [*head, *rest, *tail]]


def party_for(state_dir: Path, root: Path, type_id: str | None = None) -> list[dict]:
    """The project's parties but General, in the Board's order, each `{"party", "name", "fits", "missing": [{"agent", "name"}]}` (spec 70
    §1.2). With a goal type (a catalog id): `fits` is `whole` (the party is offered it with nothing missing), then `missing` (offered with
    someone missing, `missing` says who), then `none`; Ideation's party is always `none`. Without: `fits` is "", Ideation's last with `pitch`.
    ValueError for a type the catalog lacks."""
    t = None
    if type_id:
        t = goal_types.get(type_id)
        if t is None:
            raise ValueError(f"No goal type {type_id!r}")
    rows, pitch = [], []
    for track in ideas.tracks(root, make=False):
        if track["slug"] == ideas.GENERAL:
            continue
        row = {"party": track["slug"], "name": track["title"], "fits": "", "missing": []}
        if (track.get("leader") or "") == library.INVESTOR:
            row["fits"] = "none" if t else "pitch"
            (rows if t else pitch).append(row)
            continue
        if t:
            got = next((m for o, m in goal_types.offered(state_dir, root, track["slug"]) if o.id == t.id), None)
            row["fits"] = "none" if got is None else "missing" if got else "whole"
            row["missing"] = [{"agent": m["agent"], "name": m["name"]} for m in got or []]
        rows.append(row)
    if t:
        return sorted(rows, key=lambda r: ("whole", "missing", "none").index(r["fits"]))
    return rows + pitch


def suggested(parties: list[dict]) -> str:
    """The first party that takes the type whole, else the first that misses someone, else the first; "" with no party."""
    for fit in ("whole", "missing"):
        for r in parties:
            if r["fits"] == fit:
                return r["party"]
    return parties[0]["party"] if parties else ""
