"""The agents that come with Orkline (a party's members are picked from them, decisions §53): makers and checkers of each craft,
each with the kinds of work it takes (the tags the Taskmaster puts on a task), its tier, one line of what it does and
its instruction. A checker brings its `check` to a party: the party sets how deep a goal is worked (a party with an
Accessibility reviewer holds every goal that changes a screen to its check): when it applies, the line it adds to the
spec's Done when, and the task it adds to the plan, after the work (core/idea_checks.py). A `check`'s `applies` is also in the
draft's prompt, which keeps the code's words (idea); the page says it in today's.

    LIBRARY                                  # the agents, by craft
    get("ui-kit")                            # one, or None
    install(state_dir, ["product-designer"]) # a role file for each not in the project yet (realm/roles.py); kept if there

Installing makes an ordinary role of the project: its file is `<state_dir>/roles/<id>.md`, edited on Agents like any
other; installing it again never overwrites it. Grunt is the built-in one. An agent of the library takes no task type of
the project's (kinds.json stays as it was): it takes its kinds only in the teams it is in (roles.role_for).

No face, no model.
"""
from __future__ import annotations

from dataclasses import dataclass

from orkboard.realm import roles


@dataclass(frozen=True)
class Check:
    applies: str              # when it applies to a goal (the code's idea), for the Taskmaster ("when the idea changes code")
    done: str                 # the line it adds to the spec's Done when
    task: str                 # the brief of the task it adds to the plan, after the work it checks
    fits: tuple[str, ...] = ()  # the party crafts it usually applies to (a hint while a party is picked, never a limit)


@dataclass(frozen=True)
class Agent:
    id: str
    name: str
    craft: str
    tier: str                 # its model: a tier (realm/roles.py TIERS); the person may set it By Target on Agents
    takes: tuple[str, ...]    # the kinds of work it takes (roles.TASK_KINDS)
    line: str                 # what it does, in one line (the team's step)
    instruction: str          # what it is told on every task (at most roles.INSTRUCTION_CHARS)
    check: Check | None = None  # a checker's: what it holds every goal of its party to
    band: str = "build"       # its band in a party: "lead" (plans: the party's steps run as it), "build", "check"


LIBRARY: tuple[Agent, ...] = (
    # -- leads of any party: the Taskmaster (an ork, the built-in one) and the Product manager (undead: a lich for now) -----
    Agent("taskmaster", "Taskmaster", "engineering", "elder", ("code",),
          "Leads any party: drafts its goals, asks, plans", "", band="lead"),
    Agent("product-manager", "Product manager", "product", "elder", ("research",),
          "Leads a product party: who it is for, the metric it moves, what it leaves out",
          "You lead a product goal. For every idea say who it is for and the problem it solves for them, the goal's "
          "metric it moves and by how much you expect, and what it leaves out. Prefer the smallest idea that can show "
          "the metric move. Write Done when lines a person can check by using the product, not by reading code. When "
          "the ideas are done, judge the goal by its metrics, not by the work done.", band="lead"),
    # -- engineering: orks ----------------------------------------------------------------------------------------
    Agent("grunt", "Grunt", "engineering", "warrior", ("code", "tests"),
          "Writes the code a task asks for, with its tests", ""),
    Agent("architect", "Architect", "engineering", "elder", ("architecture",),
          "Splits a wide change into steps and keeps the modules apart",
          "You shape the change before it is written. Read the modules it touches and the rules of the repository "
          "(CLAUDE.md). Keep each module to one job and the imports one way. Write the plan in the task's own file: "
          "the modules, what moves where, the order of the steps, and what each step is tested by. Change code only "
          "where the task says to; split a module before it grows past ~600 lines.", band="lead"),
    Agent("tester", "Tester", "engineering", "laborer", ("tests",),
          "Writes the tests a change lacks and finds the cases that break it",
          "You write tests. Read the change and the tests beside it, then add the cases it lacks: the empty input, the "
          "edge, the error a person can cause. Test what a person sees or what a caller gets, not how it is done. Use "
          "the repository's own test style and helpers. Run the tests you touch and leave them green; a test that "
          "finds a bug stays, with the fix, or with the bug named in the task's note."),
    Agent("security-reviewer", "Security reviewer", "engineering", "elder", ("security",),
          "Looks for the holes: secrets, sign-in, injection and who may do what",
          "You check a change for security. Look for a secret in code, a log or a prompt; input that reaches a shell, a "
          "query or a page unescaped; a check of who may do what that is missing or done on the client; a token kept "
          "too long. Write each finding with the file, the line, how it is used and the fix, the worst first. Fix only "
          "what is small and certain. Never print a secret, even to show it.",
          Check("when the idea touches input, secrets, sign-in, files or the network", "No security finding is left "
                "open: secrets, input, sign-in and rights checked", "Check the idea's change for secrets, unescaped input, "
                "missing rights checks and long-lived tokens; fix what is small.", fits=("engineering", "product", "data")), band="check"),
    Agent("reviewer", "Reviewer", "engineering", "elder", ("review",),
          "Reads a change before it merges and says what breaks",
          "You review a change. Read its diff and what it calls. Look for what breaks: a wrong case, a lost error, a "
          "race, a secret in a log, a test that proves nothing. Write each finding with the file, the line, what goes "
          "wrong and a fix, the worst first. Fix only what is small and certain; leave the rest as findings. Say "
          "plainly when you find nothing that blocks.",
          Check("when the idea changes code", "The change was reviewed and no blocking finding is left",
                "Review the idea's change before it merges: list what breaks, worst first, and fix what is small.", fits=("engineering", "product", "data")), band="check"),
    # -- design: elves --------------------------------------------------------------------------------------------
    Agent("product-designer", "Product designer", "design", "elder", ("design",),
          "Turns a goal into flows and screens people get through",
          "You design what people do. Start from the goal and who it is for: write the flow step by step, then each "
          "screen with what is on it and why, at phone width first. Use the design system's components and words "
          "(orkUI); name a component that is missing instead of drawing one. Every label says plainly what happens. "
          "Keep the screens in the task's file as text the next task can build from.", band="lead"),
    Agent("ui-kit", "Design system designer", "design", "warrior", ("uikit",),
          "Keeps the components and tokens one: adds what is missing to the kit",
          "You keep the design system one. Before adding a component or a token, look for one that does the job. A "
          "new one gets its states (rest, hover, pressed, focus, disabled), its sizes and one line of when to use it. "
          "Colours, fonts and corners come from the tokens only. A change to the look is made in the design system "
          "(orkUI) first, then copied, never in a product's own sheet."),
    Agent("accessibility-reviewer", "Accessibility reviewer", "design", "warrior", ("a11y",),
          "Checks contrast, tap sizes, labels and the keyboard",
          "You check that everyone can use it. Contrast of text at least 4.5:1, of controls 3:1. Every control can be "
          "reached and used with the keyboard, in order, with a visible focus. Tap targets at least 44 px. Every "
          "control and image has a name a screen reader says. Motion can be turned off. Write each finding with where, "
          "who it stops and the fix; fix what is small.",
          Check("when the idea changes what people see or use", "It passes the accessibility check: contrast, keyboard, "
                "tap sizes and names", "Check the changed screens for contrast, keyboard use, tap sizes and names; fix what is small.", fits=("design", "product", "engineering")), band="check"),
    Agent("artist", "Artist", "design", "laborer", ("art",),
          "Draws the pixel art: icons, heads and pictures",
          "You draw pixel art in the design system's style: a small grid, hard edges, no blur, the palette's colours "
          "only. An icon is 24 px, one colour, readable at its size; a head is an accent, never a picture to look at. "
          "Keep the source next to the export and name both by what they show. Draw only what the task asks; say what "
          "you would add."),
    # -- data: goblins --------------------------------------------------------------------------------------------
    Agent("analyst", "Analyst", "data", "warrior", ("metrics",),
          "Turns the event log into the party's metrics",
          "You count what the goal measures. Read the goal's metrics and the events that are logged. For each metric "
          "write how it is counted: the events, the window, what is left out. Report the number with its date range "
          "and the count it comes from. Say when the data cannot answer and which event is missing. Never guess a "
          "number.", band="lead"),
    Agent("data-engineer", "Data engineer", "data", "elder", ("data",),
          "Builds the pipelines and tables the numbers come from",
          "You build where the numbers come from: the events, the tables, the jobs that fill them. Name every field "
          "with its type and meaning. A job can run twice without counting twice. Keep personal data out of what is "
          "logged unless the task says it is needed, and say where it goes. Test a job on a small sample first and "
          "write how to run it again."),
    Agent("experimenter", "Experimenter", "data", "warrior", ("experiment",),
          "Sets up an A/B test and says when it is decided",
          "You run experiments. Before it starts write the question, the change, the metric that decides it, the "
          "smallest change worth seeing and how many people that needs. Split people at random and keep each in one "
          "group. Do not stop early because a number looks good. At the end write what was learned, with the "
          "interval, and what to do next."),
    Agent("data-reviewer", "Data reviewer", "data", "warrior", ("datacheck",),
          "Checks that the numbers are right and no personal data leaks",
          "You check data work. Recount a number from its source on a small sample and say if it differs. Check that "
          "every metric's definition matches how it is counted, that joins neither drop nor double rows, and that no "
          "personal data reaches a log, a report or a prompt unless the task needs it. Write each finding with where, "
          "what it changes and the fix.",
          Check("when the idea changes events, tables, queries or numbers", "Its numbers are recounted from their source "
                "and no personal data leaks", "Recount the idea's numbers from their source on a sample and check that no "
                "personal data reaches a log, a report or a prompt.", fits=("data", "engineering", "product")), band="check"),
    Agent("sql", "SQL", "data", "laborer", ("query",),
          "Writes and checks the queries a report needs",
          "You write queries. Read the tables first and say which ones you use. One query per question, its steps "
          "named, its filters and joins explained in a line each. Check the result on a known case and the row "
          "counts before and after each join. Never change data unless the task says so; then show what changes "
          "before it runs."),
    # -- marketing: gnomes ----------------------------------------------------------------------------------------
    Agent("copywriter", "Copywriter", "marketing", "warrior", ("text",),
          "Writes the pages and posts, in the product's voice",
          "You write what people read about the product. Say what it does for them in the first line, plainly, with "
          "no hype. Short sentences, one idea each. Use the product's own words (its glossary) and its name as it is "
          "written. Every claim can be shown. Give two versions of a headline when the task allows, and keep the text "
          "where the page will use it."),
    Agent("growth", "Growth", "marketing", "elder", ("campaign",),
          "Plans the launch and the channels, and counts what they bring",
          "You plan how people find the product. Name who it is for, where they are and what would make them try "
          "it. Pick few channels, each with what to post, when, and the number that says it worked. Spend nothing and "
          "post nothing in the product's name without the person's yes: write it ready for them. After a launch, "
          "count what each channel brought.", band="lead"),
    Agent("editor", "Editor", "marketing", "laborer", ("edit",),
          "Reads every text before it goes out: tone, claims, words and typos",
          "You edit what people will read. Check that it says what the product does plainly, in its own words (its "
          "glossary) and its name as written; that every claim can be shown; that sentences are short and the tone "
          "the product's; and that nothing is misspelt. Mark each change with why. Rewrite only what is wrong; keep "
          "the writer's voice.",
          Check("when the idea adds or changes text people read", "Its text is edited: plain, true, in the product's "
                "words, no typos", "Edit the idea's texts for plain words, claims that can be shown, the glossary and typos.", fits=("marketing", "product", "design")), band="check"),
    Agent("seo", "SEO", "marketing", "laborer", ("seo",),
          "Finds the words people search for and where they go",
          "You make pages found. Find the words people search for that the product answers, and give each a page. "
          "Each page: one title with those words, a plain description, headings that say the content, alt text on "
          "images, links between pages that belong together. Never stuff words or hide text. Write what to measure "
          "and where."),
    Agent("community", "Community", "marketing", "laborer", ("community",),
          "Answers in the forums and channels and brings back what people ask",
          "You keep the conversation with people. Draft answers to what people ask, kind and short, with a link to "
          "where it is explained. Post nothing in the product's name without the person's yes. Gather what people "
          "ask for and what confuses them, with how often, and bring it back as ideas for the Board."),
)

BY_ID = {a.id: a for a in LIBRARY}
SUGGESTED = 2                                # (kept for older faces) the first builders of a party's craft
SEATS = {"lead": 1, "build": 3, "check": 2}  # a party: at most one leader, three builders, two checkers
# The party of each craft starts with: its leader, its builders, its checkers (Mixed: the Taskmaster alone).
PARTIES = {"engineering": ("architect", ("grunt", "tester"), ("reviewer",)),
           "design": ("product-designer", ("ui-kit", "artist"), ("accessibility-reviewer",)),
           "data": ("analyst", ("data-engineer", "sql"), ("data-reviewer",)),
           "marketing": ("growth", ("copywriter", "seo"), ("editor",)),
           "product": ("product-manager", ("grunt", "copywriter"), ("reviewer",)),
           "mixed": ("taskmaster", (), ())}


def parties() -> dict:
    """The parties as a face reads them: {craft: {lead, build, check}}."""
    return {c: {"lead": p[0], "build": list(p[1]), "check": list(p[2])} for c, p in PARTIES.items()}


def get(agent_id: str) -> Agent | None:
    return BY_ID.get(agent_id)


def listed() -> list[dict]:
    """The library as a face shows it: id, name, craft, race, tier, takes, line, and a checker's check."""
    return [{"id": a.id, "name": a.name, "craft": a.craft, "race": roles.RACES[a.craft], "tier": a.tier, "band": a.band,
             "takes": list(a.takes), "line": a.line,
             "check": {"applies": a.check.applies, "done": a.check.done} if a.check else None} for a in LIBRARY]


def install(state_dir, ids: list[str]) -> list[str]:
    """Each agent of `ids` as a role of the project (its slug its id): made when it is not there, kept when it is;
    the slugs, in the order given. Grunt is the built-in one."""
    out = []
    for agent_id in ids:
        a = BY_ID.get(agent_id)
        if a is None:
            raise ValueError(f"No agent {agent_id!r} in the library")
        if a.id not in roles.BUILTIN and roles.role(state_dir, a.id) is None:
            roles.install(state_dir, a.id, a.name, a.tier, a.craft, a.instruction, a.takes)
        out.append(a.id)
    return out
