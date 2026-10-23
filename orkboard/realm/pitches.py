"""Ideation's pitches (docs/specs/65-ideation.md §2, §4–§6): a goal of a party led by the Investor is a pitch, a small idea judged
and never built. What its three calls answered (core/idea_judge.py) is kept beside its state, in `<state_dir>/ideas/<slug>/judge.json`;
its page gains one section, **Decision**, written by code from the Investor's answer (a hand edit of the page is read as it is).

    is_pitch(root, "dark-mode")                       # its party is led by the Investor
    clean_view(answer, "tech-view")                   # {for, against, question, size}: cut, `size` the Engineering view's only
    clean_case(answer)                                # {case, kills}
    clean_decision(answer, case_kills, offers, likes) # §3's answer cut and cleaned, §4's kill reasons applied
    offers(root, state_dir)                           # {party or preset: {name, types, preset}}: where a pitch may go, as what
    read(state_dir, slug); save(state_dir, slug, **changes); begin(state_dir, slug)
    passed(root, state_dir)                           # the pitches passed, newest first, with their why
    over_cap(root, state_dir)                         # the oldest passed beyond KEEP_PASSED: dropped as `ideas.drop` drops a goal
    face(root, state_dir, slug, state, target)        # what the faces read of a pitch (the Map's node, the page)
    sent_lines(root, state_dir, "ship-the-csv")       # a goal sent from a pitch: its views and decision, for its draft
    tally(root, state_dir, "ideas")                   # §6: judged, sent, passed, as decided, how many sent raised their flag

The kill reasons are code's, a closed list, each with its words; an invest with one of `RESHAPING` is a reshape. The interface's
words are today's (party, goal, pitch); the files keep the code's names (track, idea). No face, no model.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any

from orkboard.realm import goal_team, goal_types, idea_flag, ideas, library, roles
from orkboard.realm.idea_words import short_of

FILE = "judge.json"
TECH = "tech-view"                       # the one view with the repository's read-only tools, and the only one with a size
ANSWERS = ("invest", "reshape", "pass")
ANSWER_WORDS = {"invest": "Invest", "reshape": "Reshape", "pass": "Pass"}
KILLS = {"no_who": "No one it is for is named",
         "no_move": "It moves none of the parties' metrics",
         "repeat": "It repeats a goal done, in work or passed",
         "costly": "It costs more than it is likely to bring",
         "off": "It is outside what the project is for"}
RESHAPING = ("no_who", "no_move", "repeat")      # an invest with one of these is a reshape (§4)
PITCH_CHARS = 2000                       # a pitch's words (one box)
LINES, LINE_CHARS = 3, 200               # a view's for and against, the decision's why
CASE_CHARS, FIRST_CHARS, TEST_CHARS = 600, 300, 300
WHY_CHARS = 300                          # the person's line when they pass
KEEP_PASSED = 200                        # the passed pitches kept; the oldest beyond goes
PROMPT_PASSED = 20                       # the passed pitches a call reads, newest first
SENT_CHARS = 2000                        # what a goal sent from a pitch gives its draft
BEFORE = 2                               # the decisions kept from before a pitch was judged again
SIZES = ("S", "M", "L")
_EMPTY = {"views": {}, "case": None, "decision": None, "before": [], "judged_at": "", "passed": None, "sent": None}


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _line(value: object, limit: int) -> str:
    """One line of plain text, cut; "" for what is not text or a number."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return ""
    return " ".join(str(value).split())[:limit]


def _lines(value: object, most: int = LINES, each: int = LINE_CHARS) -> list[str]:
    if not isinstance(value, list):
        return []
    return [x for x in (_line(v, each) for v in value) if x][:most]


# -- whose: a pitch is a goal of a party the Investor leads ---------------------------------------------------------------

def is_ideation(root: Path, party: str) -> bool:
    """The party is led by the Investor (spec 65 §1)."""
    return bool(party) and ideas.track_page(root, party) is not None and goal_team.leader_of(root, party) == library.INVESTOR


def is_pitch(root: Path, slug: str) -> bool:
    page = ideas.idea_page(root, slug)
    return page is not None and is_ideation(root, page.get("track") or ideas.GENERAL)


# -- the answers, cut and cleaned (§3, §4) -------------------------------------------------------------------------------

def kills_of(*lists: object) -> list[str]:
    """The kill reasons said, joined in the order first said, each once; an id not in KILLS dropped."""
    out: list[str] = []
    for got in lists:
        for k in got if isinstance(got, list) else []:
            k = _line(k, 20).lower()
            if k in KILLS and k not in out:
                out.append(k)
    return out


def clean_view(answer: object, view: str) -> dict | None:
    """A view's answer as kept: `{for, against, question, size}`, at most three lines of 200 each; `size` (S, M, L or "") the
    Engineering view's only. None when it is not an object (the call is tried again)."""
    if not isinstance(answer, dict):
        return None
    size = _line(answer.get("size"), 2).upper()
    return {"for": _lines(answer.get("for")), "against": _lines(answer.get("against")), "question": _line(answer.get("question"), LINE_CHARS),
            "size": size if view == TECH and size in SIZES else ""}


def clean_case(answer: object) -> dict | None:
    """The skeptic's answer: `{case (≤ 600), kills}`; None when it is not an object."""
    if not isinstance(answer, dict):
        return None
    return {"case": " ".join(str(answer.get("case") or "").split())[:CASE_CHARS] if isinstance(answer.get("case"), str) else "",
            "kills": kills_of(answer.get("kills"))}


def clean_decision(answer: object, case_kills: list[str], offered: dict[str, dict], likes: dict[str, str]) -> dict:
    """The Investor's answer as kept (§3, §4): only its keys, cut. `offered`: `offers()` (a `where.party` that is neither a party of the
    project nor a preset, or a `type` that one is not offered, is emptied: the invest stands, the person picks); `likes`: the goals a
    `like` may name, {slug: title} (another is emptied). The kills of the skeptic and the Investor are joined; `repeat` without a
    `like` is dropped; an invest with a kill of RESHAPING is a reshape (`reshaped`). ValueError when its answer is not one of three."""
    if not isinstance(answer, dict) or _line(answer.get("answer"), 10).lower() not in ANSWERS:
        raise ValueError("the Investor's answer was not invest, reshape or pass")
    said = _line(answer.get("answer"), 10).lower()
    where = answer.get("where") if isinstance(answer.get("where"), dict) else {}
    party, kind = _line(where.get("party"), 60), _line(where.get("type"), 40)
    if party not in offered or said == "pass":
        party = kind = ""
    if kind not in (offered.get(party) or {}).get("types", ()):
        kind = ""
    like = _line(answer.get("like"), 100)
    like = like if like in likes else ""
    kills = kills_of(case_kills, answer.get("kills"))
    if not like:
        kills = [k for k in kills if k != "repeat"]
    reshaped = said == "invest" and any(k in RESHAPING for k in kills)
    final = "reshape" if reshaped else said
    return {"answer": final, "why": _lines(answer.get("why")), "where": {"party": party, "type": kind},
            "first": _line(answer.get("first"), FIRST_CHARS) if final != "pass" else "", "test": _line(answer.get("test"), TEST_CHARS),
            "kills": kills, "like": like, "reshaped": reshaped}


def offers(root: Path, state_dir: Path) -> dict[str, dict]:
    """Where a pitch may be sent (§3, §5): each party of the project (not General, not an Ideation party) with the goal types it is
    offered (`goal_types.offered`), then each party of the library not in the project (a preset whose leader and team no party has;
    Ideation's never), with what such a party would be offered. `{id: {name, types: [type ids], preset: bool}}`, parties first."""
    out: dict[str, dict] = {}
    have = []
    for t in ideas.tracks(root, make=False):
        if t["slug"] == ideas.GENERAL:
            continue
        lead = t.get("leader") or roles.TASKMASTER
        have.append((lead, sorted(t.get("team") or [])))
        if lead == library.INVESTOR:
            continue
        out[t["slug"]] = {"name": t["title"], "types": [x.id for x, _r in goal_types.offered(state_dir, root, t["slug"])], "preset": False}
    for p in library.presets():
        team = [*p["build"], *p["check"]]
        if p["lead"] == library.INVESTOR or (p["lead"], sorted(team)) in have or p["id"] in out:
            continue
        read = goal_types.Party.of(state_dir, root, p["lead"], team)
        out[p["id"]] = {"name": p["name"], "types": [x.id for x, _r in goal_types.offered(state_dir, root, "", read=read)], "preset": True}
    return out


# -- judge.json ----------------------------------------------------------------------------------------------------------

def _path(state_dir: Path, slug: str) -> Path:
    return ideas.state_folder(state_dir, slug) / FILE


def read(state_dir: Path, slug: str) -> dict:
    """What a pitch's calls answered: `{views: {view: {...}}, case, decision, before: [decision + at], judged_at, passed, sent}`."""
    try:
        data = ideas._json(_path(state_dir, slug)) or {}
    except ValueError:
        data = {}
    out = {k: data.get(k, v if not isinstance(v, (dict, list)) else type(v)()) for k, v in _EMPTY.items()}
    out["views"] = {k: v for k, v in (out["views"] if isinstance(out["views"], dict) else {}).items() if k in library.VIEWS and isinstance(v, dict)}
    out["before"] = [b for b in out["before"] if isinstance(b, dict)][:BEFORE] if isinstance(out["before"], list) else []
    return out


def save(state_dir: Path, slug: str, **changes: Any) -> dict:
    """Only the keys given change, under `ideas.LOCK`; `view=(id, answer)` adds one view."""
    with ideas.LOCK:
        data = read(state_dir, slug)
        if "view" in changes:
            vid, got = changes.pop("view")
            data["views"][vid] = got
        data.update({k: v for k, v in changes.items() if k in _EMPTY})
        ideas._write_json(_path(state_dir, slug), data)
    return data


def begin(state_dir: Path, slug: str) -> None:
    """A judging starts: the decision there was goes to `before` (the last two kept), the rest is answered anew."""
    with ideas.LOCK:
        data = read(state_dir, slug)
        if data["decision"]:
            data["before"] = [{**data["decision"], "at": data["judged_at"]}, *data["before"]][:BEFORE]
        data.update(views={}, case=None, decision=None, judged_at="", passed=None, sent=None)
        ideas._write_json(_path(state_dir, slug), data)


# -- the page's Decision section --------------------------------------------------------------------------------------------

def decision_text(decision: dict, offered: dict[str, dict], likes: dict[str, str]) -> str:
    """The page's **Decision** (§2): the answer and where, why, the first step, the cheapest test, the kill reasons, the goal it repeats."""
    where = decision.get("where") or {}
    to = (offered.get(where.get("party")) or {}).get("name") or ""
    kind = goal_types.get(where.get("type"))
    head = ANSWER_WORDS.get(decision.get("answer"), "")
    if to:
        head += f": the {to} party" + (f", as {kind.name}" if kind else "")
    lines = [f"**{head}**"]
    lines += [f"- {w}" for w in decision.get("why") or []]
    if decision.get("first"):
        lines.append(f"\nFirst step: {decision['first']}")
    if decision.get("test"):
        lines.append(f"Cheapest test: {decision['test']}")
    if decision.get("kills"):
        lines.append("\nKill reasons:\n" + "\n".join(f"- {KILLS[k]}" for k in decision["kills"] if k in KILLS))
    if decision.get("like"):
        lines.append(f"\nIt repeats: {likes.get(decision['like']) or decision['like']}")
    return "\n".join(lines).strip()


def rewrite(root: Path, slug: str, text: str) -> None:
    """The pitch's words changed by the person (Change and judge again): its Gist, and its title and short name from them."""
    with ideas.LOCK:
        page = ideas.idea_page(root, slug)
        if page is None:
            raise ValueError(f"No goal {slug!r}")
        first = ideas.thesis(text) or text.split("\n")[0]
        page.title = first if len(first) <= 80 else first[:77].rsplit(" ", 1)[0] + "…"
        page.set("short", short_of(first))
        page.set_section("Gist", text)
        ideas._write(Path(root) / ideas.IDEAS / f"{slug}.md", page.text())
        ideas._reindex(root)


def write_decision(root: Path, slug: str, text: str) -> None:
    """The page's Decision section written (or replaced), the rest of the page kept."""
    with ideas.LOCK:
        page = ideas.idea_page(root, slug)
        if page is None:
            return
        page.set_section("Decision", text)
        ideas._write(Path(root) / ideas.IDEAS / f"{slug}.md", page.text())


# -- the passed pitches (§5) ----------------------------------------------------------------------------------------------

def passed(root: Path, state_dir: Path) -> list[dict]:
    """The pitches passed, newest first: `{slug, title, why: [the decision's why], said: the person's line, at}`."""
    out = []
    for i in ideas.ideas(root):
        if ideas.state(state_dir, i["slug"])["state"] != "passed":
            continue
        j = read(state_dir, i["slug"])
        p = j["passed"] if isinstance(j["passed"], dict) else {}
        out.append({"slug": i["slug"], "title": i["title"], "why": list((j["decision"] or {}).get("why") or []),
                    "said": str(p.get("why") or ""), "at": str(p.get("at") or "")})
    return sorted(out, key=lambda r: r["at"], reverse=True)


def passed_lines(root: Path, state_dir: Path, most: int = PROMPT_PASSED, slugs: bool = False) -> str:
    """The passed pitches for a call: title (and slug) and their why, the newest first."""
    rows = []
    for r in passed(root, state_dir)[:most]:
        why = "; ".join([*r["why"], *([f"the person: {r['said']}"] if r["said"] else [])]) or "no reason kept"
        rows.append(f"- {r['slug'] + ': ' if slugs else ''}{r['title']} — {why}")
    return "\n".join(rows)


def over_cap(root: Path, state_dir: Path, keep: int | None = None) -> list[str]:
    """The passed pitches beyond `keep` (KEEP_PASSED), the oldest: their slugs."""
    return [r["slug"] for r in passed(root, state_dir)[KEEP_PASSED if keep is None else keep:]]


# -- what the faces read (the Map's node, the page) --------------------------------------------------------------------------

def _who(state_dir: Path, slug: str, target: str) -> dict:
    r = roles.role(state_dir, slug)
    a = library.get(slug)
    if r is None:
        r = {"slug": slug, "name": a.name if a else slug, "model": a.tier if a else "", "craft": a.craft if a else roles.DEFAULT_CRAFT}
    return {"slug": slug, "name": r["name"], "head": roles.head(r, target)}


def _kills(ids: list) -> list[dict]:
    return [{"id": k, "words": KILLS[k]} for k in ids or [] if k in KILLS]


def _decision(d: dict | None, offered: dict[str, dict], titles: dict[str, str]) -> dict | None:
    if not d:
        return None
    where = d.get("where") or {}
    party, kind = where.get("party") or "", goal_types.get(where.get("type"))
    to = offered.get(party) or {}
    return {"answer": d.get("answer") or "", "word": ANSWER_WORDS.get(d.get("answer"), ""), "why": list(d.get("why") or []),
            "where": {"party": party, "name": to.get("name") or "", "preset": bool(to.get("preset")),
                      "type": kind.id if kind else "", "type_name": kind.name if kind else ""},
            "first": d.get("first") or "", "test": d.get("test") or "", "kills": _kills(d.get("kills")),
            "like": {"slug": d["like"], "title": titles.get(d["like"]) or d["like"]} if d.get("like") else None,
            "reshaped": bool(d.get("reshaped")), **({"at": d["at"]} if d.get("at") else {})}


def face(root: Path, state_dir: Path, slug: str, state: str, target: str = "balance", offered: dict[str, dict] | None = None) -> dict:
    """A pitch as the faces read it (spec 65 §8): its state; its four views in their order, each `{slug, name, head, answered, for,
    against, question, size}`; the case against; the decision; what was sent or passed; the decisions from before. `offered`:
    `offers()` read once for many pitches."""
    j = read(state_dir, slug)
    offered = offers(root, state_dir) if offered is None else offered
    titles = {i["slug"]: i["title"] for i in ideas.ideas(root)}
    views = []
    for v in library.VIEWS:
        got = j["views"].get(v)
        views.append({**_who(state_dir, v, target), "answered": got is not None,
                      **{k: (got or {}).get(k, [] if k in ("for", "against") else "") for k in ("for", "against", "question", "size")}})
    case = j["case"] if isinstance(j["case"], dict) else None
    sent = j["sent"] if isinstance(j["sent"], dict) else None
    if sent:
        sent = {**sent, "name": (offered.get(sent.get("party")) or {}).get("name") or sent.get("party") or "",
                "title": titles.get(sent.get("goal")) or ""}
    return {"state": state, "views": views, "skeptic": _who(state_dir, library.SKEPTIC, target),
            "investor": _who(state_dir, library.INVESTOR, target),
            "case": {"case": case.get("case") or "", "kills": _kills(case.get("kills"))} if case else None,
            "decision": _decision(j["decision"], offered, titles), "sent": sent,
            "passed": j["passed"] if isinstance(j["passed"], dict) else None,
            "before": [x for x in (_decision(b, offered, titles) for b in j["before"]) if x]}


def stage_of(state: str, answered: int) -> str:
    """A pitch's stage on the Map, by the band whose words its party's stages carry (Pitch, Views, Decision): "planning" while it
    waits (raw, failed), "implementation" while its views answer, "checking" from the case against on (judged, sent, passed too)."""
    if state in ("raw", "failed"):
        return "planning"
    return "implementation" if state == "judging" and answered < len(library.VIEWS) else "checking"


def need_of(state_dir: Path, slug: str) -> dict:
    """What a judged pitch's row in Needs you adds (§5): `{kind: pitch, priority: low, blocks: false, text, answer}`."""
    d = read(state_dir, slug)["decision"] or {}
    word = ANSWER_WORDS.get(d.get("answer"), "")
    return {"kind": "pitch", "priority": "low", "blocks": False, "text": f"Judged: {word}" if word else "Judged", "answer": d.get("answer") or ""}


# -- a goal sent from a pitch (§5) ------------------------------------------------------------------------------------------

def sent_lines(root: Path, state_dir: Path, goal: str) -> str:
    """For the draft of a goal sent from a pitch: the pitch's views and decision, at most SENT_CHARS ("" for any other goal)."""
    src = ideas.state(state_dir, goal).get("from_pitch") or ""
    if not re.fullmatch(r"[a-z0-9-]+", src) or ideas.idea_page(root, src) is None:
        return ""
    j = read(state_dir, src)
    parts = []
    for v in library.VIEWS:
        got = j["views"].get(v)
        if got:
            a = library.get(v)
            parts.append(f"{a.name}: for: {'; '.join(got['for']) or '—'}. Against: {'; '.join(got['against']) or '—'}."
                         + (f" Asks: {got['question']}" if got.get("question") else "") + (f" Size: {got['size']}." if got.get("size") else ""))
    d = j["decision"] or {}
    if d:
        parts.append(f"The Investor: {ANSWER_WORDS.get(d.get('answer'), '')}. {' '.join(d.get('why') or [])}"
                     + (f" First step: {d['first']}" if d.get("first") else "") + (f" Cheapest test: {d['test']}" if d.get("test") else ""))
    if not parts:
        return ""
    text = "This goal was sent from Ideation; what its views and the Investor said (do not ask again what they answered):\n" + "\n".join(f"- {p}" for p in parts)
    return (text if len(text) <= SENT_CHARS else text[:SENT_CHARS - 1].rstrip() + "…") + "\n"


# -- measured (§6) ------------------------------------------------------------------------------------------------------------

def tally(root: Path, state_dir: Path, party: str) -> dict:
    """An Ideation party's work: `{judged, sent, passed, as_decided, flags}`. `as_decided`: of the pitches sent or passed, the share
    where the person did what the Investor said (None before any); `flags`: of the goals sent, how many raised their flag."""
    judged = sent = gone = done = flags = 0
    for i in ideas.ideas(root, party):
        state = ideas.state(state_dir, i["slug"])["state"]
        j = read(state_dir, i["slug"])
        judged += bool(j["decision"]) or bool(j["before"])
        for key in ("sent", "passed"):
            row = j[key] if isinstance(j[key], dict) and state == key else None
            if row is None:
                continue
            sent += key == "sent"
            gone += key == "passed"
            done += bool(row.get("as_decided"))
            if key == "sent" and row.get("goal") and idea_flag.flag_of(state_dir, row["goal"]):
                flags += 1
    decided = sent + gone
    return {"judged": judged, "sent": sent, "passed": gone, "as_decided": round(done / decided, 2) if decided else None, "flags": flags}
