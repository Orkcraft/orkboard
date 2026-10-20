"""A question the Taskmaster asks of an idea or a goal (docs/specs/41-phone-round-3.md §9): what it asks, its choices,
the one it recommends and why — taken strictly from the model's answer, kept in the page as one line, read back.

    q = idea_questions.of({"ask": "Which store first?", "choices": ["App Store", "Google Play"], "pick": 0,
                           "why": "most of its users are on iPhone"})   # a goal's may say `by`: the slug of the member it is for
    idea_questions.all_of(answer["questions"], 3)       # the model's questions, each taken by `of`
    idea_questions.line(q)       # "Which store first? (**App Store** / Google Play) — most of its users are on iPhone"
    idea_questions.parse(line)   # {"ask", "choices", "pick", "why"}; a line of before ("… (one / other)") too
    idea_questions.picks(lines)  # each question's recommended choice ("" where it has none): Let the Taskmaster decide
    idea_questions.tally(lines, answers)   # how the person answered: picked, recommended, typed

The page is the memory: the line says the pick too (in bold), so the person reading the page sees it. No face, no model.
"""
from __future__ import annotations

import re

ASK_CHARS = 300
CHOICES = (2, 4)                 # a question's choices: at least, at most
CHOICE_CHARS = 40
WHY_CHARS = 120
BY_CHARS = 60                    # a role slug

# "<ask> (<choice> / **<pick>** / …)<?.!> — <why>": the choices in the last brackets that hold a slash.
_LINE = re.compile(r"^(.*?)\s*\(([^()]*/[^()]*)\)\s*([?.!]?)\s*(?:[—–]\s*(.*))?$")
_BOLD = re.compile(r"^\*\*(.+)\*\*$")


def _plain(value: object, limit: int) -> str:
    text = " ".join(value.split()) if isinstance(value, str) else ""
    return text if len(text) <= limit else text[:limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _choice_ok(c: str) -> bool:
    return 0 < len(c) <= CHOICE_CHARS and not set(c) & set("()/*")


def of(raw: object) -> dict | None:
    """A question from the model's answer, strictly: a dict {"ask", "choices", "pick", "why"} or a plain string (a
    model or a page of before). Choices that break the rules are dropped together (the ask stays, alone); `pick` is
    an index of them, else None. None for nothing to ask."""
    if isinstance(raw, str):
        q = parse(raw)
        return q if q["ask"] else None
    if not isinstance(raw, dict):
        return None
    ask = _plain(raw.get("ask"), ASK_CHARS)
    if not ask:
        return None
    choices = [" ".join(c.split()) for c in raw.get("choices") or [] if isinstance(c, str)] \
        if isinstance(raw.get("choices"), list) else []
    if not CHOICES[0] <= len(choices) <= CHOICES[1] or not all(_choice_ok(c) for c in choices) \
            or len({c.lower() for c in choices}) < len(choices):
        choices = []
    pick = raw.get("pick")
    if isinstance(pick, str):
        pick = next((n for n, c in enumerate(choices) if c.lower() == " ".join(pick.split()).lower()), None)
    pick = pick if isinstance(pick, int) and not isinstance(pick, bool) and 0 <= pick < len(choices) else None
    q = {"ask": ask, "choices": choices, "pick": pick, "why": _plain(raw.get("why"), WHY_CHARS) if choices else ""}
    if by := _plain(raw.get("by"), BY_CHARS).lower():          # whose view it answers (a goal's read, spec 46 §1); the page does not keep it
        q["by"] = by
    return q


def all_of(raw: object, limit: int) -> list[dict]:
    """The model's questions, each taken by `of`, at most `limit`."""
    return [q for q in (of(x) for x in raw) if q][:limit] if isinstance(raw, list) else []


def line(q: dict) -> str:
    """The page's line: the ask, its choices in brackets (the pick in bold), and why after a dash."""
    if not q.get("choices"):
        return q["ask"]
    said = " / ".join(f"**{c}**" if n == q.get("pick") else c for n, c in enumerate(q["choices"]))
    return f"{q['ask']} ({said})" + (f" — {q['why']}" if q.get("why") else "")


def parse(text: str) -> dict:
    """A page's line back into its question; a line with no valid choices is its ask alone."""
    text = " ".join(str(text or "").split())
    m = _LINE.match(text)
    if not m:
        return {"ask": text, "choices": [], "pick": None, "why": ""}
    raw = [c.strip() for c in m.group(2).split("/") if c.strip()]
    bold = [bool(_BOLD.match(c)) for c in raw]
    choices = [_BOLD.sub(r"\1", c).strip() for c in raw]
    if not CHOICES[0] <= len(choices) <= CHOICES[1] or not all(0 < len(c) <= CHOICE_CHARS for c in choices):
        return {"ask": text, "choices": [], "pick": None, "why": ""}
    ask = m.group(1).strip()
    if m.group(3) and not re.search(r"[?.!]$", ask):
        ask += m.group(3)
    return {"ask": ask, "choices": choices, "pick": bold.index(True) if sum(bold) == 1 else None,
            "why": (m.group(4) or "").strip()}


def asked_by(questions: list[dict], members: list[str], leader: str) -> list[str]:
    """Who asks each question of a goal's read, one slug per question in their order: the member whose view it answers
    (its `by`), else the leader (`taskmaster` with none) for its own and for a `by` that is no member (spec 46 §1)."""
    return [q["by"] if q.get("by") in members else leader for q in questions]


def picks(lines: list[str]) -> list[str]:
    """Each question's recommended choice, "" where it has none (Let the Taskmaster decide's answers)."""
    out = []
    for text in lines:
        q = parse(text)
        out.append(q["choices"][q["pick"]] if q["pick"] is not None else "")
    return out


def tally(lines: list[str], answers: list[str]) -> dict[str, int]:
    """How the person answered the questions, for the events: `picked` (one of its choices), `recommended` (its
    pick), `typed` (anything else written)."""
    out = {"picked": 0, "recommended": 0, "typed": 0}
    for n, text in enumerate(lines):
        said = " ".join(str(answers[n] if n < len(answers) else "").split())
        if not said:
            continue
        q = parse(text)
        hit = next((i for i, c in enumerate(q["choices"]) if c.lower() == said.lower()), None)
        if hit is None:
            out["typed"] += 1
            continue
        out["picked"] += 1
        out["recommended"] += hit == q["pick"]
    return out
