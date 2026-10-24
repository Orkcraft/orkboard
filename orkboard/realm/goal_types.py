"""The goal types (specs 52 and 59, decisions §65.4–§65.5, §72): the kinds of goal a party's team can take on (*New logo*, *Fix a
bug*), each with its sign (orkUI's), the few lines only the person can give (its asks), whether looks matter (Refs), the lens
it opens first, a line for the leader's draft and plan, and the kinds of work it needs of the party. One catalog; a party is
offered the types its team can do, and few others: one it misses one agent for only when the leader itself does another part
of it (the agent of the library who does is offered: a free seat joins, a full band swaps).

    CATALOG                                         # every type, in order
    get("logo")                                     # a type by the id a goal keeps; an old key ("product-designer/logo") too
    offered(state_dir, root, "ship")                # [(type, missing)]: what the party can take on, and who each misses
    offered(state_dir, root, "", read=Party.of(state_dir, root, leader, team))      # the same for a leader and a team not saved
    taker("art", "design")                          # "artist": the agent of the library who does that kind of work
    met(state_dir, "art", ["artist", "product-designer"])      # someone of the party does it (not the Grunt filling in)
    missing(state_dir, root, "ship", ("art",))      # what the party misses for those kinds: who would join, who could leave
    of_plan(state_dir, plan["tasks"], party, leader)            # a plan's `missing`, after its roles are given
    still_missing(state_dir, root, "ship", plan["missing"])     # a plan's `missing` read against the party now
    prompt_line(state_dir, "dark-mode")             # "Its type: New logo. …\n" for the draft and plan prompts ("" with none)

A goal keeps its type in its state (`type`, realm/ideas.py `STATE_DEFAULT`) by the catalog's id, given once and never changed. A
type is told by its sign, never by a colour. The types' names and lines are the interface's words; `plan` keeps the code's.

No face, no model.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from orkboard.realm import goal_team, idea_spend, ideas, library, roles

LENSES = ("text", "code", "screen", "pain")      # realm/idea_lens.py ORDER
SIGNS = ("feature", "bug", "tidy", "screen", "picture", "logo", "target", "flask", "horn", "chart", "page", "restructure", "abtest", "landing", "post", "tagline", "text",
         "mechanic", "level", "balance", "character", "release", "store", "tune")  # orkUI's (spec 52 §1); the last seven are A0's (spec 59 §1.1)
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
    id: str                   # a slug, unique in the catalog
    name: str                 # the interface's: "New logo"
    sign: str                 # orkUI's (SIGNS)
    line: str                 # what it makes, in one line (≤ 60 characters)
    needs: tuple[str, ...] = ()     # the kinds of work (roles.TASK_KINDS) someone of the party must take for it
    lens: str = "text"        # the lens New goal opens first, when the party offers it
    asks: tuple[Ask, ...] = ()      # at most three; none is required
    refs: bool = False        # the form asks for Refs: links and pictures the person likes
    plan: str = ""            # for the draft and the plan prompts, in the code's words
    over: str = ""            # the id of the more general type it stands in for, or ""


BUG_ASKS = (Ask("did", "What you did", "the steps, in order"), Ask("happened", "What happened", "what you saw"),
            Ask("expected", "What should have", "what you expected"))
BUG_PLAN = "Write a test that fails the way the person saw first, then the fix that makes it pass."
IN_THE_WAY = Ask("in-the-way", "What gets in the way", "what is hard to change today")
WHO_USES = Ask("who", "Who uses it", "and what they came to do")
MOVES = Ask("moves", "What it should move", "the number, and by how much")

CATALOG: tuple[GoalType, ...] = (
    GoalType("feature", "New feature", "feature", "Something people can do that they could not", ("code",)),
    GoalType("bug", "Fix a bug", "bug", "Something that goes wrong, made right", ("code",), asks=BUG_ASKS, plan=BUG_PLAN),
    GoalType("tidy", "Clean up", "tidy", "The same behaviour in simpler code", ("code",), asks=(IN_THE_WAY,),
             plan="Change nothing a person or a caller sees; the tests stay green."),
    GoalType("shaped-feature", "New feature", "feature", "A change across modules, shaped before it is written",
             ("architecture",), "code", (Ask("avoid", "Must use or avoid", "a library, a pattern, a module not to touch"),),
             plan="Shape it first: the modules, the steps and what tests each, then the code.", over="feature"),
    GoalType("restructure", "Restructure", "restructure", "Modules split or moved, one job each", ("architecture",), "code",
             (IN_THE_WAY, Ask("shape", "Your idea of the shape", "how you would split it")),
             plan="Keep the behaviour; move in steps that each pass the tests; keep the imports one way."),
    GoalType("screen", "New screen", "screen", "A screen people get through, phone width first", ("design", "uikit"), "screen",
             (WHO_USES,), True, "Write the flow step by step, then the screen: what is on it and why; the UI kit adds "
             "what is missing; then the build."),
    GoalType("icon", "New icon", "picture", "An icon in the pixel style, picked from a few", ("art",), "text",
             (Ask("where", "Where it shows", "its place and its size"),), True,
             "An Artist draws four to pick from (a pick of 4 images) at the icon's size; the one picked is put in place."),
    GoalType("logo", "New logo", "logo", "A mark for the product, picked from a few", ("art",), "text",
             (Ask("says", "What it should say", "three words"),), True,
             "An Artist draws four to pick from (a pick of 4 images); the one picked is put in place at every size the "
             "product uses."),
    GoalType("flow-feature", "New feature", "feature", "A flow and its screens, then the build", ("uikit",), "screen",
             (WHO_USES,), True, "The flow first, then each screen of it, then the build.", "feature"),
    GoalType("pain", "Solve a pain", "target", "The smallest change that takes a pain away", ("research",), lens="pain",
             plan="Say who it is for and the pain; plan the smallest change that shows it gone."),
    GoalType("experiment", "Try an experiment", "flask", "A change shown to some people, then measured",
             ("research", "experiment"), "pain", (MOVES,), plan="An Experimenter writes the question, the split and the "
             "number that decides before the change ships.", over="abtest"),
    GoalType("launch", "Write the launch", "horn", "The words people read when it ships", ("research", "text"),
             asks=(Ask("where", "Where it goes", "the page, the post, the store"),)),
    GoalType("metric", "A new metric", "chart", "A number counted from the events", ("data",),
             asks=(Ask("question", "The question it answers"),),
             plan="Say how it is counted: the events, the window, what is left out; add the events that are not logged."),
    GoalType("report", "A report", "page", "Numbers that answer a question, from the tables", ("query",),
             asks=(Ask("question", "The question"), Ask("reader", "Who reads it"))),
    GoalType("abtest", "An A/B test", "abtest", "Two versions shown, one decided by a number", ("metrics", "experiment"),
             asks=(MOVES,), plan="Write the question, the split and the number that decides before it starts; do not "
             "stop early."),
    GoalType("landing", "A landing page", "landing", "A page that says what the product does, and is found", ("text", "seo"),
             asks=(Ask("for", "Who it is for"), Ask("from", "Where they come from")), refs=True),
    GoalType("post", "A launch post", "post", "A post for one channel, ready for your yes", ("campaign", "text"),
             asks=(Ask("channel", "The channel"),), plan="Nothing is posted without the person's yes: write it ready for them."),
    GoalType("tagline", "A tagline", "tagline", "One line that says the product, picked from a few", ("text",),
             plan="A Copywriter writes three to pick from (a pick of 3 texts)."),
    GoalType("mechanic", "New mechanic", "mechanic", "A rule the player plays by, tried before it is built in", ("gamedesign",),
             asks=(Ask("verb", "What the player does", "the verb, in one line"), Ask("fun", "Why it is fun", "what they get from it")),
             plan="Write the rule and its loop first (what the player does, sees and gets), then a playable prototype; its "
             "numbers in the balance file."),
    GoalType("level", "New level", "level", "A level laid out, built and played through", ("level",),
             asks=(Ask("teaches", "What it teaches", "the one new idea"), Ask("long", "How long it plays", "in minutes")), refs=True,
             plan="A Level designer lays it out first (the path, the beats, where it gets hard), then builds it; then it is "
             "played through."),
    GoalType("character", "New character", "character", "A character drawn, picked from a few, then put in the game", ("art",),
             asks=(Ask("who", "Who it is", "in three words"),), refs=True,
             plan="An Artist draws four to pick from (a pick of 4 images); the picked one gets its frames and goes in the game."),
    GoalType("balance", "Balance pass", "balance", "The game's numbers changed so it plays better", ("gamedesign",),
             asks=(Ask("off", "What feels off", "where, and how"),),
             plan="Change numbers only, in the balance file; say each change and why; the tests stay green."),
    GoalType("sound", "New sound", "tune", "A sound or a tune, picked by ear", ("sound",),
             asks=(Ask("where", "Where it plays", "the moment, and how often"),), refs=True,
             plan="A Sound designer makes three to pick from (a pick of 3 sounds); the picked one is put in place."),
    GoalType("store", "Store listing", "store", "The store's page: keywords, texts, screenshots' words", ("aso",),
             asks=(Ask("for", "Who it is for"), Ask("stores", "The stores", "App Store, Google Play")), refs=True,
             plan="Keywords first (what people search for in the store), then the title, subtitle and description, then the "
             "screenshots' words; nothing is submitted without the person's yes."),
    GoalType("release", "A release", "release", "A version out: what is new, the build, the stores' list", ("aso", "code"),
             asks=(Ask("version", "Version", "1.4"), Ask("new", "What is new", "in the person's words")),
             plan="Bump the version, write what is new for the stores in the product's words, make the build, and write the "
             "stores' list the person goes through; nothing is submitted without the person's yes."),
)
BY_ID = {t.id: t for t in CATALOG}
# A type a goal kept by its leader's key before spec 59 ("<leader>/<id>"), read as the catalog's.
WAS = {"taskmaster/feature": "feature", "taskmaster/bug": "bug", "architect/bug": "bug", "taskmaster/tidy": "tidy",
       "architect/feature": "shaped-feature", "architect/restructure": "restructure", "product-designer/screen": "screen",
       "product-designer/icon": "icon", "product-designer/logo": "logo", "product-designer/feature": "flow-feature",
       "product-manager/pain": "pain", "product-manager/experiment": "experiment", "product-manager/launch": "launch",
       "analyst/metric": "metric", "analyst/report": "report", "analyst/abtest": "abtest", "growth/landing": "landing",
       "growth/post": "post", "growth/tagline": "tagline"}
GRUNT_OWN = library.get(roles.GRUNT).takes       # the Grunt's own kinds (code, tests): met by the Grunt itself
CODE = ("code", "tests")                         # a type that needs one is offered only when a member takes it itself


def get(type_key: object) -> GoalType | None:
    """The type a goal keeps: the catalog's id, or an old key `"<leader>/<id>"` as WAS reads it; None with none or anything else."""
    key = str(type_key or "")
    return BY_ID.get(WAS.get(key, key))


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
    week's runs, read when first asked. `Party.of` reads a leader and a team not saved."""

    def __init__(self, state_dir: Path, root: Path, slug: str) -> None:
        self.state_dir, self.root, self.slug = Path(state_dir), Path(root), slug
        self.leader = goal_team.leader_of(self.root, slug)
        self.team = goal_team.team_of(self.root, slug)
        self.craft = craft_of(self.leader)
        self.fresh: tuple[str, ...] = ()
        self._busy: set[str] | None = None
        self._week: dict | None = None

    @classmethod
    def of(cls, state_dir: Path, root: Path, leader: str, team: list[str]) -> Party:
        """A party not saved (the form's seats before the party is kept): the leader (the Taskmaster for "") and the team as given,
        with no slug, no goals and so no open work and no runs. A library agent the project does not have yet (saving the party
        makes it a role of the project) is read as the library has it: `fresh`."""
        p = cls(state_dir, root, "")             # no party has the empty slug: the reads of a saved party come back empty
        p.leader, p.team = leader or roles.TASKMASTER, list(team)
        p.craft = craft_of(p.leader)
        p.fresh = tuple(s for s in p.members if library.get(s) is not None and roles.role(p.state_dir, s) is None)
        p._busy, p._week = set(), {}
        return p

    @property
    def members(self) -> list[str]:
        return [*self.team, self.leader]

    def band(self, band: str) -> list[str]:
        return [s for s in self.team if goal_team.band_of(s) == band]

    def meets(self, kind: str) -> bool:
        """Whether someone of the party does `kind` (`met`); a member of the library not yet the project's, as the library takes it."""
        return met(self.state_dir, kind, self.members) or any(kind in library.get(s).takes for s in self.fresh)

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
            "free": len(p.band(a.band)) < library.seats_of(p.leader)[a.band]}


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
        if kind not in roles.TASK_KINDS or p.meets(kind) or not (agent := taker(kind, p.craft)):
            continue
        row = _row(p, kind, agent)
        band = p.band(row["band"])
        idle = [(n, s) for n, s in enumerate(band) if s not in p.busy()]
        row["out"] = [{"slug": s, "name": _name(state_dir, s), "runs": p.runs(s)}
                      for n, s in sorted(idle, key=lambda x: (p.runs(x[1]), -x[0]))]
        out.append(row)
    return out


def _takes(state_dir: Path, slug: str) -> set[str]:
    """The kinds a member takes itself: a library agent's, a role file's `takes`, the task types the project gives it."""
    a, r = library.get(slug), roles.role(state_dir, slug)
    return set(a.takes if a else ()) | (roles.takes_of(r, roles.kinds(state_dir)) if r else set())


def offered(state_dir: Path, root: Path, party_slug: str, *, read: Party | None = None) -> list[tuple[GoalType, list[dict]]]:
    """What a party can take on (spec 59 §4.3), in the catalog's order: `[(type, missing)]`. Code is someone's: a type that needs
    `code` or `tests` is offered only when a member takes it itself. A type with every need met is offered with nothing missing;
    one with exactly one need not met, that need having a taker, is offered with that one missing only when the leader itself
    takes another of its needs (work beside the leader's is another party's). One name once: a type with nothing missing hides
    the type it stands in for (`over`), and one with someone missing is not offered when that one is offered with nothing missing.
    Ideation (a party the Investor leads) is offered none: a pitch has no type, its decision names the type of the goal it becomes
    in the party it is sent to (spec 65 §1). In a project with a Release party (the Release manager leads it), *A release* is offered
    by that party alone (spec 68 §3.1)."""
    p = read or Party(state_dir, root, party_slug)
    if p.leader == library.INVESTOR:
        return []
    taken = {m: _takes(state_dir, m) for m in p.members}
    lead = taken.get(p.leader, set()) - set(CODE)
    found: list[tuple[GoalType, list[dict]]] = []
    for t in CATALOG:
        if any(k in CODE and not any(k in got for got in taken.values()) for k in t.needs):
            continue
        unmet = [k for k in t.needs if k not in CODE and not p.meets(k)]
        if not unmet:
            found.append((t, []))
        elif len(unmet) == 1 and lead & (set(t.needs) - set(unmet)):
            if rows := missing(state_dir, root, party_slug, unmet, read=p):
                found.append((t, rows))
    whole = {t.id for t, rows in found if not rows}
    hidden = {t.over for t in (t for t, _ in found) if t.over and t.id in whole}
    if p.leader != library.RELEASE_MANAGER and release_party(root):          # one place to release (spec 68 §3.1)
        found = [(t, rows) for t, rows in found if t.id != "release"]
    return [(t, rows) for t, rows in found if t.id not in hidden and not (rows and t.over in whole)]


def release_party(root: Path) -> str:
    """The slug of the project's Release party (the one the Release manager leads), "" with none (spec 68 §3.1)."""
    return next((t["slug"] for t in ideas.tracks(root, make=False) if t.get("leader") == library.RELEASE_MANAGER), "")


def lacking(state_dir: Path, p: Party, t: GoalType) -> str:
    """The first kind of a type's needs no one of the party does (code and tests: no member takes it itself), else its first."""
    taken = {m: _takes(state_dir, m) for m in p.members}
    return next((k for k in t.needs if not any(k in got for got in taken.values()) and (k in CODE or not p.meets(k))),
                t.needs[0])


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
            if not p.meets(kind):
                out.append(_row(p, kind, str(agent)))
    return out


def prompt_line(state_dir: Path, slug: str) -> str:
    """For the draft and the plan prompts (spec 52 §2.5): `Its type: <name>. <plan>` (the name alone when the type has no
    plan line), "" for a goal with no type."""
    t = get(ideas.state(state_dir, slug).get("type"))
    if t is None:
        return ""
    return f"Its type: {t.name}." + (f" {t.plan}" if t.plan else "") + "\n"
