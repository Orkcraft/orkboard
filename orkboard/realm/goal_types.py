"""The goal types (spec 52 §2.1, decisions §65.4–§65.5): the kinds of goal a party's leader deals (*New logo*, *Fix a bug*),
each with its sign (orkUI's), the few lines only the person can give (its asks), whether looks matter (Refs), the lens it
opens first, a line for the leader's draft and plan, and the kinds of work it needs of the party. When no one of the
party does one of them, the agent of the library who does is offered: a free seat joins, a full band swaps.

    of("product-designer")                          # its set: New screen, New icon, New logo, New feature
    get("product-designer/logo")                    # a type by the key a goal keeps ("<leader>/<id>"), or None
    taker("art", "design")                          # "artist": the agent of the library who does that kind of work
    met(state_dir, "art", ["artist", "product-designer"])      # someone of the party does it (not the Grunt filling in)
    missing(state_dir, root, "ship", ("art",))      # what the party misses for those kinds: who would join, who could leave
    of_plan(state_dir, plan["tasks"], party, leader)            # a plan's `missing`, after its roles are given
    still_missing(state_dir, root, "ship", plan["missing"])     # a plan's `missing` read against the party now
    prompt_line(state_dir, "dark-mode")             # "Its type: New logo. …\n" for the draft and plan prompts ("" with none)

A goal keeps its type in its state (`type`, realm/ideas.py `STATE_DEFAULT`), given once and never changed. A type is told
by its sign, never by a colour. The types' names and lines are the interface's words; `plan` keeps the code's.

No face, no model.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from orkboard.realm import goal_team, idea_spend, ideas, library, roles

LENSES = ("text", "code", "screen", "pain")      # realm/idea_lens.py ORDER
SIGNS = ("feature", "bug", "tidy", "screen", "picture", "logo", "target", "flask", "horn", "chart", "page", "text")  # orkUI's (spec 52 §1)
ASK_CHARS = 300                                  # an answer to an ask, the most kept
REFS = "refs"                                    # the id of Refs' links among a goal's asks
GONE = ("merged", "dropped")                     # a task no longer to do
DROPPED = "dropped by you"                       # a task dropped at Review fails with these words (core/idea_review.py)


@dataclass(frozen=True)
class Ask:
    id: str
    label: str                # ≤ 24 characters: the field's label
    hint: str = ""            # ≤ 60: its placeholder


@dataclass(frozen=True)
class GoalType:
    id: str                   # a slug, unique in its leader's set
    name: str                 # the interface's: "New logo"
    sign: str                 # orkUI's (SIGNS)
    line: str                 # what it makes, in one line (≤ 60 characters)
    needs: tuple[str, ...] = ()     # the kinds of work (roles.TASK_KINDS) someone of the party must take for it
    lens: str = "text"        # the lens New goal opens first, when the party offers it
    asks: tuple[Ask, ...] = ()      # at most three; none is required
    refs: bool = False        # the form asks for Refs: links and pictures the person likes
    plan: str = ""            # for the draft and the plan prompts, in the code's words


BUG_ASKS = (Ask("did", "What you did", "the steps, in order"), Ask("happened", "What happened", "what you saw"),
            Ask("expected", "What should have", "what you expected"))
BUG_PLAN = "Write a test that fails the way the person saw first, then the fix that makes it pass."
IN_THE_WAY = Ask("in-the-way", "What gets in the way", "what is hard to change today")
WHO_USES = Ask("who", "Who uses it", "and what they came to do")
MOVES = Ask("moves", "What it should move", "the number, and by how much")

TYPES: dict[str, tuple[GoalType, ...]] = {
    "taskmaster": (
        GoalType("feature", "New feature", "feature", "Something people can do that they could not"),
        GoalType("bug", "Fix a bug", "bug", "Something that goes wrong, made right", asks=BUG_ASKS, plan=BUG_PLAN),
        GoalType("tidy", "Clean up", "tidy", "The same behaviour in simpler code", asks=(IN_THE_WAY,),
                 plan="Change nothing a person or a caller sees; the tests stay green."),
    ),
    "architect": (
        GoalType("feature", "New feature", "feature", "A change across modules, shaped before it is written", lens="code",
                 asks=(Ask("avoid", "Must use or avoid", "a library, a pattern, a module not to touch"),),
                 plan="Shape it first: the modules, the steps and what tests each, then the code."),
        GoalType("bug", "Fix a bug", "bug", "Something that goes wrong, made right", lens="code", asks=BUG_ASKS, plan=BUG_PLAN),
        GoalType("restructure", "Restructure", "tidy", "Modules split or moved, one job each", lens="code",
                 asks=(IN_THE_WAY, Ask("shape", "Your idea of the shape", "how you would split it")),
                 plan="Keep the behaviour; move in steps that each pass the tests; keep the imports one way."),
    ),
    "product-designer": (
        GoalType("screen", "New screen", "screen", "A screen people get through, phone width first", ("uikit",), "screen",
                 (WHO_USES,), True, "Write the flow step by step, then the screen: what is on it and why; the UI kit adds "
                 "what is missing; then the build."),
        GoalType("icon", "New icon", "picture", "An icon in the pixel style, picked from a few", ("art",), "text",
                 (Ask("where", "Where it shows", "its place and its size"),), True,
                 "An Artist draws four to pick from (a pick of 4 images) at the icon's size; the one picked is put in place."),
        GoalType("logo", "New logo", "logo", "A mark for the product, picked from a few", ("art",), "text",
                 (Ask("says", "What it should say", "three words"),), True,
                 "An Artist draws four to pick from (a pick of 4 images); the one picked is put in place at every size the "
                 "product uses."),
        GoalType("feature", "New feature", "feature", "A flow and its screens, then the build", ("uikit",), "screen",
                 (WHO_USES,), True, "The flow first, then each screen of it, then the build."),
    ),
    "product-manager": (
        GoalType("pain", "Solve a pain", "target", "The smallest change that takes a pain away", lens="pain",
                 plan="Say who it is for and the pain; plan the smallest change that shows it gone."),
        GoalType("experiment", "Try an experiment", "flask", "A change shown to some people, then measured", ("experiment",),
                 "pain", (MOVES,), plan="An Experimenter writes the question, the split and the number that decides before "
                 "the change ships."),
        GoalType("launch", "Write the launch", "horn", "The words people read when it ships", ("text",),
                 asks=(Ask("where", "Where it goes", "the page, the post, the store"),)),
    ),
    "analyst": (
        GoalType("metric", "A new metric", "chart", "A number counted from the events", ("data",),
                 asks=(Ask("question", "The question it answers"),),
                 plan="Say how it is counted: the events, the window, what is left out; add the events that are not logged."),
        GoalType("report", "A report", "page", "Numbers that answer a question, from the tables", ("query",),
                 asks=(Ask("question", "The question"), Ask("reader", "Who reads it"))),
        GoalType("abtest", "An A/B test", "flask", "Two versions shown, one decided by a number", ("experiment",),
                 asks=(MOVES,), plan="Write the question, the split and the number that decides before it starts; do not "
                 "stop early."),
    ),
    "growth": (
        GoalType("landing", "A landing page", "page", "A page that says what the product does, and is found", ("text", "seo"),
                 asks=(Ask("for", "Who it is for"), Ask("from", "Where they come from")), refs=True),
        GoalType("post", "A launch post", "horn", "A post for one channel, ready for your yes", ("text",),
                 asks=(Ask("channel", "The channel"),), plan="Nothing is posted without the person's yes: write it ready for them."),
        GoalType("tagline", "A tagline", "text", "One line that says the product, picked from a few", ("text",),
                 plan="A Copywriter writes three to pick from (a pick of 3 texts)."),
    ),
}
GENERAL = roles.TASKMASTER                       # the general set: dealt by a leader with no set of its own
GRUNT_OWN = library.get(roles.GRUNT).takes       # the Grunt's own kinds (code, tests): met by the Grunt itself


def of(leader: str) -> tuple[GoalType, ...]:
    """A leader's set; the Taskmaster's (the general one) for a leader with none of its own."""
    return TYPES.get(leader) or TYPES[GENERAL]


def key(leader: str, type_id: str) -> str:
    return f"{leader}/{type_id}"


def get(type_key: object) -> GoalType | None:
    """The type a goal keeps by its key `"<leader>/<id>"`; None with none, or a key no leader deals."""
    leader, _, type_id = str(type_key or "").partition("/")
    a = library.get(leader)
    if leader not in TYPES and (a is None or a.band != "lead"):
        return None
    return next((t for t in of(leader) if t.id == type_id), None)


def words(kind: str) -> str:
    """A kind of work in a sentence (spec 52 §0): its label with its first letter lowered unless its second is a capital."""
    label = roles.KIND_LABELS.get(kind, kind)
    return label if len(label) > 1 and label[1].isupper() else label[:1].lower() + label[1:]


def craft_of(leader: str) -> str:
    a = library.get(leader)
    return a.craft if a is not None else roles.DEFAULT_CRAFT


def taker(kind: str, craft: str) -> str:
    """The agent of the library who does `kind`: the first builder or checker that takes it, of the leader's craft first,
    then the others in the library's order; "" when none (the work goes as today)."""
    pool = [a for a in library.LIBRARY if kind in a.takes and a.band in ("build", "check")]
    got = next((a for a in pool if a.craft == craft), None) or (pool[0] if pool else None)
    return got.id if got is not None else ""


def met(state_dir: Path, kind: str, party: list[str]) -> bool:
    """Whether someone of the party (its leader and team) does `kind`: the role a task of it runs as is not the Grunt, or it
    is one of the Grunt's own kinds. A kind the Grunt gets only by filling in is not met."""
    return kind in GRUNT_OWN or roles.role_for(state_dir, kind, list(party))["slug"] != roles.GRUNT


class Party:
    """What the types read of a party, once: its leader, its team and the leader's craft; who of it has work open and the
    week's runs, read when first asked."""

    def __init__(self, state_dir: Path, root: Path, slug: str) -> None:
        self.state_dir, self.root, self.slug = Path(state_dir), Path(root), slug
        self.leader = goal_team.leader_of(self.root, slug)
        self.team = goal_team.team_of(self.root, slug)
        self.craft = craft_of(self.leader)
        self._busy: set[str] | None = None
        self._week: dict | None = None

    @property
    def members(self) -> list[str]:
        return [*self.team, self.leader]

    def band(self, band: str) -> list[str]:
        return [s for s in self.team if goal_team.band_of(s) == band]

    def busy(self) -> set[str]:
        """The members with an open task: one of the party's goals' tasks that is not merged, dropped or done."""
        if self._busy is None:
            read, self._busy = roles.known(self.state_dir), set()
            for i in ideas.ideas(self.root, self.slug):
                if ideas.state(self.state_dir, i["slug"])["state"] == "done":
                    continue
                for t in (ideas.plan(self.state_dir, i["slug"]) or {}).get("tasks") or []:
                    if t.get("state") not in GONE and not (t.get("state") == "failed" and t.get("error") == DROPPED):
                        self._busy.add(roles.task_slug(t, read))
        return self._busy

    def runs(self, slug: str) -> int:
        """The tasks a member finished this week (as `ideas.agents`' `week`)."""
        if self._week is None:
            self._week = idea_spend.by_role(self.state_dir)
        return int((self._week.get(slug) or {}).get("finished") or 0)


def _row(p: Party, kind: str, agent: str) -> dict:
    a = library.get(agent)
    return {"kind": kind, "words": words(kind), "agent": agent, "name": a.name, "band": a.band,
            "free": len(p.band(a.band)) < library.SEATS[a.band]}


def _name(state_dir: Path, slug: str) -> str:
    r, a = roles.role(state_dir, slug), library.get(slug)
    return (r or {}).get("name") or (a.name if a else slug)


def missing(state_dir: Path, root: Path, party_slug: str, kinds, *, read: Party | None = None) -> list[dict]:
    """For each kind the party does not meet whose taker is not "", once each: `{kind, words, agent, name, band, free, out}`.
    `free`: the taker's band has a free seat; `out`: the members of that band with no open task, `[{slug, name, runs}]`, the
    fewest runs this week first, the band's later member first on a tie. A member with an open task never leaves this way.
    `read`: the party read once for many calls."""
    p = read or Party(state_dir, root, party_slug)
    out = []
    for kind in dict.fromkeys(kinds):
        if kind not in roles.TASK_KINDS or met(state_dir, kind, p.members) or not (agent := taker(kind, p.craft)):
            continue
        row = _row(p, kind, agent)
        band = p.band(row["band"])
        idle = [(n, s) for n, s in enumerate(band) if s not in p.busy()]
        row["out"] = [{"slug": s, "name": _name(state_dir, s), "runs": p.runs(s)}
                      for n, s in sorted(idle, key=lambda x: (p.runs(x[1]), -x[0]))]
        out.append(row)
    return out


def of_plan(state_dir: Path, tasks: list[dict], party: list[str], leader: str) -> list[dict]:
    """A plan's `missing` (spec 52 §2.6), after its roles are given: the kinds of its tasks the party (`party`: its team and
    leader) does not meet, `[{kind, agent}]` with `agent` the kind's taker, once each in the plan's order, those with no taker
    left out."""
    out, seen, craft = [], set(), craft_of(leader)
    for t in tasks:
        kind = str(t.get("kind") or roles.DEFAULT_KIND)
        if kind in seen:
            continue
        seen.add(kind)
        if not met(state_dir, kind, party) and (agent := taker(kind, craft)):
            out.append({"kind": kind, "agent": agent})
    return out


def still_missing(state_dir: Path, root: Path, party_slug: str, missed: object, *, read: Party | None = None) -> list[dict]:
    """A plan's `missing` read against the party now, `[{kind, words, agent, name, band, free}]`: a kind someone added since
    meets drops out; a party with no team has none."""
    if not isinstance(missed, list) or not missed:
        return []                                # a plan made before, or one that misses no one: the party is not read
    p = read or Party(state_dir, root, party_slug)
    if not p.team:
        return []
    out, seen = [], set()
    for m in missed:
        kind, agent = (m.get("kind"), m.get("agent")) if isinstance(m, dict) else ("", "")
        if kind in roles.TASK_KINDS and kind not in seen and library.get(str(agent)) is not None:
            seen.add(kind)
            if not met(state_dir, kind, p.members):
                out.append(_row(p, kind, str(agent)))
    return out


def prompt_line(state_dir: Path, slug: str) -> str:
    """For the draft and the plan prompts (spec 52 §2.5): `Its type: <name>. <plan>` (the name alone when the type has no
    plan line), "" for a goal with no type."""
    t = get(ideas.state(state_dir, slug).get("type"))
    if t is None:
        return ""
    return f"Its type: {t.name}." + (f" {t.plan}" if t.plan else "") + "\n"
