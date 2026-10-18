"""An idea's risk, by rules no model can talk down (docs/specs/35-goals-window.md §4), and who passes its plan (§5).

    got = assess(touches=["src/auth/login.py"], texts=["Add a token check"], tasks=3, risk_model="low")
    got.risk, got.triggers, got.line       # "medium", ["secrets, sign-in, payments"], "Risk: Medium — secrets, …"
    decide("low", "normal")                # "start" · "night" · "wait"

`risk = max(risk_model, the triggers)`. The triggers read the idea's `touches` as paths and its spec and plan (titles,
briefs, Out, Risks) as words: whole words, any case. A trigger matched by mistake only makes a plan wait for the
person: the safe side. No face, no model.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field

LEVELS = ("low", "medium", "high")
WIDE_FOLDERS, WIDE_TASKS = 5, 6

SECRETS = "secrets, sign-in, payments"
DATA = "data: schema, migrations, deletion"
CI = "CI and deploy"
API = "a public API"
WIDE = "wide"
OUTWARD = "outward and irreversible"
OWN = "the repository's own"


def _words(*phrases: str) -> re.Pattern:
    """Whole words, any case; a space in a phrase is any run of spaces; `…` is a few words between."""
    parts = []
    for p in phrases:
        bits = [r"\s+".join(re.escape(w) for w in side.split()) for side in p.split("…")]
        parts.append(r"\b" + r"\b.{0,40}?\b".join(bits) + r"\b")
    return re.compile("|".join(parts), re.I | re.S)


# (name, at least, path test, words)
TRIGGERS = (
    (SECRETS, "medium", ("auth", "login", "oauth"),
     _words("token", "secret", "password", "credential", "payment", "billing", "invoice", "stripe", "checkout")),
    (DATA, "medium", ("migrations/", "alembic/", "*.sql", "schema"), _words("drop table", "truncate", "delete … data", "wipe")),
    (CI, "medium", (".github/workflows/", "Dockerfile*", "docker-compose*", "deploy", "infra/", "terraform/", "k8s/", "helm/"),
     _words("deploy", "release")),
    (API, "medium", (), _words("public API", "breaking change")),
    (OUTWARD, "high", (), _words("send an email", "send a message", "post to", "publish", "tweet", "notify users", "charge",
                                 "refund", "push to main", "delete the branch")),
)


@dataclass
class Risk:
    risk: str = "low"
    triggers: list[str] = field(default_factory=list)
    why: dict[str, str] = field(default_factory=dict)     # trigger → what matched (a path or a word)

    @property
    def line(self) -> str:
        """The Risks section's first line: the risk and what raised it."""
        if not self.triggers:
            return f"Risk: {self.risk.capitalize()}"
        said = ", ".join(f"{t} (`{self.why[t]}`)" if self.why.get(t) else t for t in self.triggers)
        return f"Risk: {self.risk.capitalize()} — {said}"


def level(value: object) -> str:
    value = str(value or "").strip().lower()
    return value if value in LEVELS else "low"


def higher(a: str, b: str) -> str:
    return max(level(a), level(b), key=LEVELS.index)


def _norm(path: str) -> str:
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def _path_hit(path: str, pattern: str) -> bool:
    p, pat = _norm(path).lower(), pattern.lower()
    if "*" in pat:
        name = p.rstrip("/").rsplit("/", 1)[-1]
        return fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(p, pat) or fnmatch.fnmatch(p, f"*/{pat}")
    if pat.endswith("/"):
        return f"/{p}/".find(f"/{pat}") >= 0 or p.startswith(pat)
    return pat in p


def _top(path: str) -> str:
    return _norm(path).split("/", 1)[0]


def assess(touches: list[str] = (), texts: list[str] = (), tasks: int = 0, risk_model: str = "low",
           risk_paths: list[str] = ()) -> Risk:
    """The idea's risk: the model's, raised by every trigger that matches (in the table's order)."""
    out = Risk(level(risk_model))
    paths = [str(t).strip() for t in touches or () if str(t).strip()]
    text = "\n".join(str(t) for t in texts or ())

    def hit(name: str, at_least: str, why: str) -> None:
        if name not in out.triggers:
            out.triggers.append(name)
            out.why[name] = why
        out.risk = higher(out.risk, at_least)

    for name, at_least, patterns, words in TRIGGERS:
        found = next((pat for p in paths for pat in patterns if _path_hit(p, pat)), "")     # the rule, as the line says it
        if found:
            hit(name, at_least, found)
            continue
        m = words.search(text)
        if m:
            hit(name, at_least, " ".join(m.group(0).split()))
    tops = {_top(p) for p in paths if "/" in _norm(p)}
    if len(tops) > WIDE_FOLDERS:
        hit(WIDE, "medium", f"{len(tops)} top-level folders")
    elif tasks > WIDE_TASKS:
        hit(WIDE, "medium", f"{tasks} tasks")
    own = next((p for p in paths for g in risk_paths or () if str(g).strip() and fnmatch.fnmatch(p, str(g).strip())), "")
    if own:
        hit(OWN, "medium", own)
    return out


def strip_line(risks: str) -> str:
    """A Risks section without the board's own first line (its words are not the spec's)."""
    lines = (risks or "").split("\n")
    return "\n".join(lines[1:]) if lines and lines[0].startswith("Risk:") else (risks or "")


# -- autostart: who passes the plan (§5) --------------------------------------------------------------------------

AUTOSTART = {  # risk → priority → what the board does
    "low": {"high": "start", "normal": "start", "low": "night"},
    "medium": {"high": "start", "normal": "wait", "low": "wait"},
    "high": {"high": "wait", "normal": "wait", "low": "wait"},
}


def decide(risk: str, priority: str) -> str:
    """"start" (passed by the board), "night" (passed, starts inside the night window) or "wait" (for the person)."""
    return AUTOSTART[level(risk)].get(str(priority or "normal").lower(), "wait")
