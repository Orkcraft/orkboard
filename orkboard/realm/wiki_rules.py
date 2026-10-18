"""The rules and file templates of an LLM wiki, topic by topic (split from wiki.py).

`SECTIONS` names the sections of each topic (`general`, `codebase`, `team`, `design`) with a line on what each
holds; `SCHEMA_TEMPLATE` is the `WIKI.md` a wiki is scaffolded with, `TOPIC_ABOUT` the topic's one-line purpose, and
`INDEX_TEMPLATE`, `SECTION_INDEX`, `SECTION_RULES`, `POINTER` and `LOG_TEMPLATE` the other files `scaffold` writes.
Text only, filled in with `str.format`; the functions that write them are in realm/wiki.py, which re-exports every
name here. Pure module, no Textual.
"""
from __future__ import annotations

SECTIONS = {
    "general": [("concepts", "ideas, components and terms: what each is, why it exists, how it relates"),
                ("decisions", "what was decided, when, why, and what was rejected"),
                ("how-to", "the steps of tasks people repeat"),
                ("people", "one page per person: what they own, how to reach them (no private details), open items"),
                ("meetings", "one page per meeting: To discuss (kept by the Wiki from notes), background, outcome")],
    "codebase": [("architecture", "the big picture: layers, boundaries, how data moves"),
                 ("modules", "one page per module or package: purpose, entry points, key files, what it uses"),
                 ("flows", "processes that cross modules: a request, a build, a release, step by step"),
                 ("decisions", "why the code is the way it is (ADRs): context, decision, what was rejected"),
                 ("how-to", "developer tasks: set up, test, debug, release"),
                 ("glossary", "the project's terms and the code names they map to")],
    "team": [("teams", "teams and roles: who owns what and how to reach them (no private details)"),
             ("process", "how work is done: planning, reviews, incidents, releases"),
             ("product", "features, customers, goals and the reasons behind them"),
             ("decisions", "what was decided, by whom, when, why, and what was rejected"),
             ("onboarding", "what a newcomer needs in the first weeks"),
             ("glossary", "the team's terms and abbreviations"),
             ("people", "one page per person: what they own, how to reach them (no private details), open items"),
             ("meetings", "one page per meeting: To discuss (kept by the Wiki from notes), background, outcome")],
    "design": [("components", "one page per component: purpose, variants, states, props, where it is used, "
                              "its name in the code"),
               ("screens", "one page per screen or flow: what the user does there, the components on it, edge states"),
               ("decisions", "design decisions: the problem, the options, what was chosen and why"),
               ("tokens", "colours, type, spacing, radii, motion: each token's name, value, role and code name")],
}

SCHEMA_TEMPLATE = """# The wiki's rules — {topic}

This folder is an LLM wiki on one topic ({about}). The librarian orc of the 🗑️ Scroll Dump keeps
it from the sources; people may write it too. Edit these rules freely — the orc follows them.

## Sections

Pages live in `pages/<section>/`, one topic per page, named in kebab-case
(`pages/{first}/some-topic.md`). Every section has an `index.md` listing its pages and a
`CLAUDE.md` with the section's own rules (agents load it when they work there).

{sections}

Add a section only when a topic fits none of these: add it here, with its index and rules.

## Hierarchy

A wiki may grow to thousands of pages; keep every map short enough to read at a glance.
When a section passes ~40 pages, split it into subfolders (`pages/modules/payments/`), each
with its own `index.md` and, when its pages need rules of their own, its own `CLAUDE.md`.
Every index lists only its own level: pages and subfolders, one line each. An agent walks
`index.md` → section index → subfolder index → page, never the whole tree.

## A page

Every page starts with front matter, then a title, then the content:

    ---
    kind: <the section's kind, e.g. {first}>
    aliases: [<other names it goes by: code names, abbreviations, old names>]
    sources: [<the source paths it is drawn from>]
    updated: <YYYY-MM-DD>
    owner: orc            # or human: then the orc never edits it
    ---
    # Title

    One paragraph that answers "what is this and why does it matter" — agents decide from it
    whether to read on.

The aliases and the first paragraph are what searches hit: put every name people or the code
use for the thing there. Link other pages with relative links (`[release](../how-to/release.md)`); name a thing the
same way everywhere (the glossary wins). A page nothing links to is an orphan.

## Keeping it true

- Prefer updating a page to adding one; merge duplicates.
- When sources disagree, say so on the page (`> ⚠ Conflict: …`) instead of picking a side.
- When a source is gone, keep what is still true and mark the rest `> ⚠ Stale: …`.
- Never edit a page whose owner is human (or that carries `<!-- manual -->`): write what you
  would change in `proposals.md` (page, change, source) instead.
- Never copy secrets, tokens or personal data into the wiki.
- A meeting's page (`kind: meeting`, `calendar: meet:<id>`) has a **To discuss** list under a
  `<!-- to-discuss … -->` marker: the Wiki keeps it from people's notes and people tick it off — never
  edit that list. Write the page's Background from the pages its notes link; a person's page gets a
  line for each meeting with them.

## The maps

`index.md` lists the sections, one line each, and the few pages most people need. Each
`pages/<section>/index.md` lists its pages, one line each: what the page answers. `log.md`
gets one entry per ingest, newest first: the date, the sources taken in, the pages touched.
"""

TOPIC_ABOUT = {"general": "the project's knowledge", "codebase": "the code: how it is built and why",
               "team": "the team and the company: people, process, product",
               "design": "the design: components, screens, decisions and tokens"}

INDEX_TEMPLATE = """# Index — {topic}

The map of this wiki: read it first, then the index of the section you need, then the pages.

_Empty — the first ingest fills it._
"""

SECTION_INDEX = """# {title}

{what}

_Empty — pages land here as sources are taken in._
"""

SECTION_RULES = """# Rules of `{name}/`

This folder is the **{name}** section of an LLM wiki ({topic}): {what}.

- One page per topic, kebab-case names; front matter as `../../WIKI.md` says (`kind: {name}`).
- Keep `index.md` here current: one line per page or subfolder, what it answers.
- Past ~40 pages, group them in subfolders, each with its own `index.md`.
- Pages with `owner: human` are people's: suggest changes in `../../proposals.md`, never edit them.
"""

POINTER = """# LLM wiki

This folder is an LLM wiki ({topic}) kept by orkcraft's 🗑️ Scroll Dump. Start from `index.md`,
then a section's `index.md`, then the pages. The rules are in `WIKI.md`. Pages with
`owner: human` belong to people.
"""

LOG_TEMPLATE = """# Log

Newest first.
"""
