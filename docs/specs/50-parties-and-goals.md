# Spec 50 — Parties and goals: a tab is a party, its goals are decks of one element, the work lies in stacks by phase, a goal raises its flag in main

The owner, 21 October (decisions §63). After spec 49 the window answers *where is my goal, and what waits for me*, but
the goal it shows is a container the person never really chooses: what they pick every day is **who works on it** (a
party: its leader, builders and checkers, the checks it holds the work to, its price), while the goal's metrics, its
*done when* and its verdict are written for them and steer nothing. So the words move one step: **what was a goal is a
party** (a team you picked and what it is for, with no end), **what was an idea is a goal** (it has a *done when*, an
end, and it **raises its flag when the gate takes it into main**), a task stays a task. On the board a party's goals are
**decks of one element** (a pixel symbol and a muted colour on every card of it), a member's tasks of one goal at one
phase lie in a **stack** of 5:7 cards that **spreads** on a press, what a task waits for is drawn as an **arrow** on
hover, and the goals list **filters** the board. The phone gets the same with a quiet top: one line for the party, one
for its goals, the details behind a press; and a tap is never lost to a redraw. **Builds:** Claude · **Review:** full ·
P1.

**What it is, and is not:** a new face and new words over the Board's own data, and three small things on the host: a
goal's **flag** (§2.2), a goal's **element** (§2.3) and the words (§2.1, §2.6). **Storage keeps its shape** (Orkline
reads the same Board, CLAUDE.md): a party is a goal page (`pages/tracks/<slug>.md`), a goal is an idea page, and the
commands, keys, events, files and classes keep their names; two things are added beside them (a goal's `flag.json`, an
`element` in its `state.json`). No new setting. The runner and the night are not changed, but for the end of accepting
(§2.2) and of asking metrics (§2.5).

Four parts. **A0 and A first, at once** (A0 is orkUI's repository, A touches no file of the page); **B and C from both**
once they are in (they touch no file of each other's). **This file is the contract**; the rest is the builder's choice
inside its files. **Change nothing outside a part's files** but those §8 names. The mockup is the Design artifact
*Orkboard: one window*: **E** (`Decks.dc.html`) is the desktop and **F** (`PhoneDecks.dc.html`) the phone; they are the
target for words, structure and sizes, their code is not copied (the page is Preact with orkUI's classes and tokens, the
phone is the PWA's plain modules). Where the mockup and this file differ, this file wins (§0: *At work*, not *In play*;
§9: no *Its code*).

| part | builds | files (and their tests) |
|---|---|---|
| **A0. orkUI** (repository orkWorks/orkUI) | §1 | new `office/elements/` (five 7 × 7 symbols and a README), new `office/signs/` (eight, §1.6; **0.3.1**), `office/tokens.json` (five element colours; `tokens.css` rebuilt by `tools/build_tokens.py`), `office/components.css` (`.ork-elem`), `office/preview.html` (an *Elements* section), `pyproject.toml` and the versions (**0.3.0**), `CHANGELOG.md`, `README.md`; `tests/test_orkui.py`. Then, in orkBoard, the copy: `python -m orkboard.design.orkui <orkUI>` (only `design-system/orkui/` changes) |
| **A. Backend** | §2 | `realm/lexicon.py`, new `realm/idea_flag.py`, new `realm/idea_element.py`, `realm/ideas.py` (`STATE_DEFAULT` gains `element`), `realm/idea_gate.py` (what is in main), `gui/ideas_gate.py` (the flags after a merge), `gui/ideas.py` (the end of `_accept_when_done`; a done goal's flag; `ideas.add` gives the element), `realm/board_map.py` (a goal's `element`, `flag`; a party's `flags`, `waits_main`, `brief`), `realm/goal_flags.py` and the command that serves `ideas.flags` (its `goals`), `realm/event_log.py` (`IDEA_FLAGGED`), `realm/board_today.py`, `realm/board_recap.py`, `realm/board_week.py`, `gui/phone_push.py`, `core/idea_goals.py` and `core/idea_draft.py` (no metrics asked), `core/idea_lead.py` (its preamble), and every Python string a person reads (§2.6); new `tests/test_idea_flag.py`, new `tests/test_idea_element.py`, `tests/test_lexicon.py`, `tests/test_idea_gate.py`, `tests/test_board_map.py`, `tests/test_gui_ideas.py`, `tests/test_board_today.py`, `tests/test_event_log.py` and the tests of the strings it changes |
| **B. Desktop** | §3–§5 | `realm/lexicon.py` (only `idea`'s `was`, §2.1) with `tests/test_lexicon.py`'s two lines, `js/arena/*` (new `goals.js` (the left list and its filter), `stacks.js` (a member's rows and stacks), `spread.js`, `arrows.js`; `arena.css`; the rest as needed), `js/shell/*` (`goalwizard.js` → New party, `goaldialog.js` → Edit the party, `goalview.js` → About this party, `store.js`'s kind words, `preview.js`), `js/board/*` (only words and the pieces the arena reuses), and every desktop template in today's words (§0); `tests/test_arena_desktop_browser.py`, `tests/test_arena_motion_desktop_browser.py`, new `tests/test_arena_decks_desktop_browser.py`, and the desktop tests that read a string it changes (§11) |
| **C. Phone** | §6 | `pwa/shell-arena.js`, `pwa/shell-arena-field.js`, `pwa/shell-arena-words.js`, `pwa/shell-stops.js`, `pwa/shell-dial.js`, `pwa/shell-motion.js`, `pwa/shell-today.js`, `pwa/shell-top.js` (the project's sheet), `pwa/shell-projects.js` and `pwa/shell-drawer.js` (the projects leave the menu), `pwa/shell-goal.js` and `pwa/shell-goal-new.js` (About this party, New party), new `pwa/shell-goals.js` (the goals sheet), new `pwa/shell-spread.js`, `pwa/board.js`, `pwa/app.css`, `gui/pwa.py` (serves `elements/*.svg`), `pwa/sw.js` (`CACHE` one up, the new modules in `SHELL`) with `tests/test_pwa.py`'s pinned version, and every phone string in today's words (§0); `tests/test_pwa_arena_browser.py`, `tests/test_pwa_arena_stops_browser.py`, `tests/test_pwa_arena_motion_browser.py`, new `tests/test_pwa_decks_browser.py`, and the phone tests that retry a tap or read a string it changes (§11) |

## 0. The words
**The step** (decisions §63.1). The interface says:

| the interface says | the code, its files, commands, keys, events and classes say (unchanged) |
|---|---|
| **party**, parties (`TERMS` `track`) | goal, track: `pages/tracks/<slug>.md`, an idea's `track`, `ideas.goal_save`, `ideas.goal`, `goal` in keys, `.arena[data-goal]`, `goal_accepted` |
| **goal**, goals (`TERMS` `idea`) | idea: the idea pages, `ideas.add`, `ideas.page`, `slug`, `idea` in keys, `data-idea`, `idea_flagged` |
| the party's members (`TERMS` `party`, unchanged) | a goal's team and leader (`team`, `leader`, `party` keys) |
| task | task |
| a goal's **flag** | an idea's `flag.json` (§2.2) |
| a party's old flag | a goal's verdict that was met (`verdict.json`), kept as history |

- A **party** is a team you picked and what it is for: its leader, its builders and checkers, the checks it holds every
  goal to, its brief. It has **no end**: no metrics, no *done when*, no progress %, no verdict, no flag of its own. What
  it shows is a count: **k/n**, its done goals of all its goals (decisions §63.2). Its record is its goals' flags.
- A **goal** has a *done when* (its spec's), a plan of tasks, and an end: done in dev, it **waits for main**; when the
  gate takes it into main it **raises its flag** (§2.2).
- New strings, in these words: *Parties* (the tablist), *+ New party*, *New party*, *Edit the party*, *About this
  party*, *Save it to your parties*, *What it is for*, *The party*, *Checks on every goal*, *What it costs*, *Its flags*,
  *Before: <its old flag>*, *Goals*, *At work*, *Planning*, *New (n)*, *Waits for main*, *Flags*, *Flags (n)*, *k wait
  for main*, *Show all*, *k of n goals*, *Nothing of these goals*, *now*, *next*, *later*, *Put them back*, *← waits for
  <short>*, *→ n wait for it* (*→ 1 waits for it*), *← waits for the build*, *New goal*, *A blank goal*, *Add the goal*,
  *Put it back*, *k/n*, *k/n done*, *k of n goals done* (a tooltip), *n flags raised* (*1 flag raised*), *<goal> is in main*, *<a>, <b> and k more are in main*, *⚑ n*,
  *≈$2–4 a goal*, *Projects*, *this one*, *Open on your computer: a tap switches this phone to one.*, *one of yours, or
  from the library*.
- Every string a person reads that said *idea* says *goal*, and every one that said *goal* (the container) says
  *party*: *New idea* → *New goal*, *Process now · 2 new ideas* → *… 2 new goals*, *about $2–4 an idea* → *… a goal*,
  *Nothing waits for you on this goal.* → *… in this party.*, *An idea needs a goal* → *A goal needs a party*, *Checks
  on every idea* → *… goal*, *Ideas at work* → *Goals at work*. Mind the order when rewriting a string by hand (a
  string with both: *idea* first to *goal*, the container's *goal* to *party*; never a blind replace).
- **Not in what a person reads:** *card*, *deck*, *hand*, *mana*, *crystal*, *hero*, *boss*, *minion*, *turn*,
  *Raise* (decisions §56, spec 49 §0), and with this spec *element*, *stack*, *spread*, *pile*, *In play*: they are this
  spec's and the code's words. A goal's element is shown, never named; a stack is a goal's tasks; *At work*, not *In
  play*.
- **What does not change:** prompts to a model (the models keep the code's words), what people or agents wrote (specs,
  plans, answers, Markdown), logs and terminals, keys, command names, event ids, file and class names, `localStorage`
  keys, `data-*` attributes.
- **Every symbol is orkUI's** (§1.6): what the window and its sheets draw as a sign is `.ork-sign` (✓ ✗ ↻ the clock !
  ⚑ ← →), an element `.ork-elem`, and ×, +, ›, ⌄ orkUI's icons; no Unicode symbol drawn as a sign in B's and C's
  files (*×n*, *≈*, *$* and *·* are text, and stay). A sign keeps its words for the reader: its `title` or the text
  beside it (*failed*, *at work*, *tonight*), and `aria-hidden` on the sign.
- `tests/test_gui_wording.py` catches a desktop template that says *idea* (it becomes an old spelling, §2.1); the phone's
  strings and the JavaScript strings outside templates are not scanned: B and C grep their files (`idea`, `Idea`,
  `goal`, `Goal`) and leave only code.

## 1. orkUI: the elements (A0)
1. **Five elements**, a goal's mark (decisions §63.4): *meadow* (a leaf), *ice* (a flake), *dust* (stones), *void* (a
   crescent), *lava* (a flame). Each is a 7 × 7 grid, drawn row by row from the top (`#` a pixel):

   | meadow | ice | dust | void | lava |
   |---|---|---|---|---|
   | `....###` | `...#...` | `..###..` | `..###..` | `...#...` |
   | `..#####` | `.#.#.#.` | `..###..` | `.##....` | `..##...` |
   | `.####.#` | `..###..` | `.......` | `##.....` | `..###.#` |
   | `.###..#` | `#######` | `.......` | `##.....` | `.#####.` |
   | `.##..#.` | `..###..` | `###.###` | `##.....` | `#######` |
   | `.#.##..` | `.#.#.#.` | `###.###` | `.##....` | `#######` |
   | `#......` | `...#...` | `.......` | `..###..` | `.#####.` |

   Each is `office/elements/<name>.svg`: `viewBox="0 0 7 7"`, one `path` of unit squares, `fill="#000"`,
   `shape-rendering="crispEdges"`; `office/elements/README.md` says what they are and that they are a goal's mark.
2. **Their colours**, tokens in `office/tokens.json` (so `--ork-elem-<name>` in `tokens.css`): meadow `#7fbf9a`, ice
   `#82aaff`, dust `#d4b77a`, void `#8e88a8`, lava `#a49a96`: muted, none the success green (the forest biome is left
   out for it), none the alert or danger hue; each at least 3:1 on `--ork-panel` and on `--ork-raised` (a graphic,
   not text).
3. **`.ork-elem`**: an inline block 14 × 14 drawn by `mask-image: url(elements/<name>.svg)` (`mask-size: 100%`,
   `mask-repeat: no-repeat`) on `background: var(--ork-elem-<name>)`; a class per element (`.ork-elem.meadow` …);
   `.big` 28 × 28; `.dim` draws it in `--ork-ink-faint` (a goal not yet given one). No size between: 14 or 28, whole
   pixels.
4. A gallery section *Elements* (each, both sizes, on panel and raised), the README's components line, the CHANGELOG
   (**0.3.0**), the versions (`pyproject.toml`, `tokens.json`, `tokens.css`'s header).
5. Tests: the five files, their 7 × 7 pixels as in the table, the tokens and their contrast, `.ork-elem`'s rules read
   only defined tokens (`NEW_PARTS`), the gallery's section, the version.
6. **The signs** (the owner: every symbol the window draws is orkUI's, decisions §63.10): eight 7 × 7 signs drawn in
   the colour of their text (`background: currentColor`), `office/signs/<name>.svg` as the elements are made, and
   `.ork-sign.<name>` (14 × 14, `.big` 28 × 28, `vertical-align: -3px` so it sits on a 16 px line), with a README:

   | check | cross | work | night | alert | flag | before | after |
   |---|---|---|---|---|---|---|---|
   | `.......` | `.......` | `..###.#` | `..###..` | `...#...` | `.#.....` | `.......` | `.......` |
   | `......#` | `.#...#.` | `.#...##` | `.#.#.#.` | `...#...` | `.#####.` | `..#....` | `....#..` |
   | `.....#.` | `..#.#..` | `#...###` | `#..#..#` | `...#...` | `.####..` | `.#.....` | `.....#.` |
   | `#...#..` | `...#...` | `#......` | `#..##.#` | `...#...` | `.#####.` | `#######` | `#######` |
   | `.#.#...` | `..#.#..` | `#.....#` | `#.....#` | `.......` | `.#.....` | `.#.....` | `.....#.` |
   | `..#....` | `.#...#.` | `.#...#.` | `.#...#.` | `...#...` | `.#.....` | `..#....` | `....#..` |
   | `.......` | `.......` | `..###..` | `..###..` | `.......` | `.#.....` | `.......` | `.......` |

   *check* a done thing (✓), *cross* a failure (✗), *work* at work (↻), *night* held for tonight (a clock; ☾ is
   dropped: a crescent is the *void* element), *alert* a stop that asks (!), *flag* a goal in main (⚑), *before* what a
   task waits for (←), *after* what waits for it (→). A gallery section *Signs* (each at both sizes, in ink, muted,
   success, danger and alert), the README's line, the CHANGELOG (**0.3.1**), the versions; tests as §1.5 (the files,
   the pixels, `NEW_PARTS`, the gallery). The close (×), the plus (+) and the chevrons (›, ⌄) are orkUI's icons
   already (`icons/icons.svg`).

## 2. The host (A)
### 2.1 The words in the glossary
- `TERMS`: `track` → *party / parties*, was *track / tracks* (its comment: *a team you picked and the goals dealt to
  it; decisions §63*); `idea` → *goal / goals* (*a goal: a page with its spec and plan, done in dev, its flag raised in
  main*), its `was` *idea / ideas* added by **B** with its templates (it makes every desktop template that says *idea*
  fail `tests/test_gui_wording.py`, so it lands with their rewrite); `steward_goal` loses its `was` (*Goal* is today's word for a goal); `party`'s comment *a
  party's leader, builders and checkers*; `flag`'s *a goal the gate took into main (spec 50 §2.2); a party's old flag
  is its verdict met (spec 42 §2)*; the other comments that say *idea* or *goal* in today's words.
- `words("the goal") == "the goal"`, `words("Goal") == "Goal"`, `term("track") == "party"`, `term("idea", many=True) ==
  "goals"` (A); `words("New idea") == "New goal"`, `words("3 ideas") == "3 goals"` (B, with the `was`). *goal* is never an old
  spelling (it is today's word): `track` keeps only *track* as its `was`.
- If `docs/reference.md` or any test renders the glossary, it follows.

### 2.2 A goal's flag
1. New `realm/idea_flag.py` (no face, no model):
   - `FLAG = "flag.json"`, in the goal's state folder (beside its `state.json`).
   - `tally(root, state_dir, slug) -> {"tasks", "first_time", "usd", "days"}`: its merged tasks (code and checks), of them
     those merged in their first round (never sent back), its $ (its spend; `None` when unpriced, never 0), whole days
     from its first state to now (at least 1; `None` when unknown) — `realm/goal_flags.tally`'s rules, for one goal.
   - `raise_flag(root, state_dir, slug, by, commit="") -> dict`: writes `{"at", "by", "commit", **tally}` once (`by`:
     `"gate"` or `"done"`); a goal that has a flag keeps it (returns the one it has).
   - `flag_of(state_dir, slug) -> dict | None`.
2. `realm/idea_gate.py` gains `all_in(git, shas, main) -> bool`: every sha is in main (an ancestor of it); no sha is
   `False`. One git call per goal at most.
3. **When a goal raises its flag** (once, never undone):
   - **at the gate**: after `ideas.gate_merge` merged, every **done** goal (its state `done`) with no flag whose merged
     tasks' commits are all in main now (`by: "gate"`, `commit`: the merge's);
   - **when it is done**, where `gui/ideas.py` calls `_accept_when_done` today: when there is no gate
     (`idea_gate.same`: results merge into main itself) or its commits are all in main already (its last task a clean
     check, after an earlier merge) (`by: "done"`).
   - Each raise logs `idea_flagged` (`realm/event_log.py` `IDEA_FLAGGED`: `idea`, `goal` (its party), `by`, `tasks`,
     `first_time`, `usd`, `days`) and publishes `ideas.changed` with the goal's slug.
   - No backfill: a goal done and in main before this spec has no flag.
4. **A party is never accepted by itself**: `_accept_when_done` goes (no model call when a party's goals are all
   done). `ideas.goal_accept` stays, for a party with metrics written before (its verdict kept as history); the faces
   no longer offer it.

### 2.3 A goal's element
- New `realm/idea_element.py` (no face): `ELEMENTS = ("meadow", "ice", "dust", "void", "lava")`;
  `pick(used: list[str]) -> str` (pure): the element used least in `used`, ties by `ELEMENTS`' order;
  `of(state_dir, slug) -> str` (`""` when none); `give(root, state_dir, slug) -> str`: when the goal has none, picks
  against the elements of its party's **open** goals (not done, not dropped) and stores it in the goal's state, then
  returns it; a given element never changes (a goal moved to another party keeps its own).
- `STATE_DEFAULT` gains `"element": ""` (`realm/ideas.py`); `save_state` keeps it.
- Given by `ideas.add` (the new goal; its answer gains `element`), and for a goal of before the first time `ideas.map`
  reads it (one write per goal, ever; it must not change `ideas_rev` in a loop).
- A raw goal (*New (n)*, not yet read) has one too: the faces draw it `.dim` until its draft (§3.3).

### 2.4 What the faces read
- `ideas.map`: a node gains `element` and `flag` (the dict or `null`); a goal of the map (a party) gains `flags` (how
  many of its goals have a flag), `waits_main` (its done goals with none) and `brief` (its Description's first
  paragraph, else its Summary's first line; at most 140 characters). Its count (§0) is the map's `ideas` (all its
  goals) and `done` (the done ones), as today: no new field.
- `ideas.flags {}` gains `goals`: `[{slug, title, short, goal, element, at, tasks, first_time, usd, days}]`, newest
  first, every party's (the faces filter by `goal`); what it returns today stays as it is (the parties' old flags).
- `ideas.today`: `idea_flagged` is a row: *⚑ <short> is in main*, its `open` `{kind: "idea", slug}`.
- *While you were away* and *Last week* (`realm/board_recap.py`, `realm/board_week.py`): a goal's flag reads *⚑ <goal>
  is in main* (from `idea_flagged`), counted as the flags; a party's old flag (`goal_accepted` of before) keeps its line.
- The morning's push (`gui/phone_push.py`): *n flags raised* counts `idea_flagged`.

### 2.5 No metrics asked
- A party's reading (`core/idea_goals.py`, the keeper and the night's refresh) no longer asks for metrics and no longer
  reads them from the answer; a party's metrics of before stay on its page and are passed on as written.
- A goal's draft (`core/idea_draft.py`) mentions its party's metrics only when the party has some (no *which metric it
  moves* question without them).
- The leader's preamble (`core/idea_lead.py`) no longer says it accepts the goal.
- Prompts keep the code's words (*idea*, *goal*); nothing else in the keeper changes.

### 2.6 Every Python string a person reads
- A message, an error, a toast, a Needs you row, a today row, a card of the recap or the week, a push, a dialog's hint
  that the host sends a face: in today's words (§0). Find them by grep in `gui/`, `realm/` and `core/` (errors raised to
  a face: `KeeperError`, `ValueError` texts shown in toasts); for example *An idea needs a goal* (`gui/ideas.py`) → *A
  goal needs a party*.
- Not changed: keys, command names, event ids, log lines, prompts, file names.
- The tests that check one of these strings change with it (CLAUDE.md); a browser test that reads one is B's or C's to
  follow (they build on A).

### 2.7 Tests (A)
`tests/test_lexicon.py` (§2.1's lines); `tests/test_idea_flag.py`: the tally, once only, the gate's path on a fixture
repository (dev ahead of main by a done goal's merged tasks: flagged after `ideas.gate_merge`; a goal not done: not
flagged; a done goal whose commits were merged before and whose last task is a clean check: flagged when it is done;
no gate: flagged when done), the log line and the publish; `tests/test_idea_element.py`: `pick`, `give` stores and
keeps, the least used in its party, a raw goal; `tests/test_board_map.py`: the new fields; `tests/test_gui_ideas.py`:
`ideas.add`'s `element`, `ideas.flags`' `goals`, no accept when a party's goals are done; `tests/test_board_today.py`:
the flag's row; the recap, the week and the push lines; the old fields unchanged.

## 3. The window (B)
As spec 49 §3 (the regions, their sizes at 1 440 × 900, no page scroll; below 1 024 px), with: the tablist named
*Parties*, the field's landmark *The party at work*, and the left column's *Planning* region replaced by *Goals*
(§3.3). The mockup E is the target.

### 3.1 The party tabs
Each tab (40 px): the leader's head (orkUI's small head), the party's short name, **k/n** (muted: its done goals of
all its goals, the map's `done` and `ideas`; its tooltip *k of n goals done*), the stops' count (warning) and ↻ while at
work; **no meter and no %** (a party has no end, only a count), no verdict's flag. *+ New party*
(outlined) after the tabs opens New party (§3.7); *Merge into …* and Operations as today. The picked party is kept
(`localStorage`, as the goal was).

### 3.2 The party line (the ideas bar's place, 36 px)
*Now: <member> ↻ <task> (<goal>) · …* muted, then quiet: *≈$2–4 a goal · today 3 merged · ≈$1.10* (the party's price a
goal, today's), *About this party* (the drawer, §3.7) and *Edit the party*. Nothing else; nothing in alert colour.

### 3.3 The left column: the leader, then the goals
- The leader (its member row) and *Process now · n new goals* on top, as spec 49 §4.3.
- **Goals n** (a heading with the party's goals that are not done), and *Show all* while the filter is on. Then:
  - **At work**: its goals in implementation or checking, in the Board's order;
  - **Planning**: its goals in Planning that have been read (the questions and plans first, as spec 49's Planning);
  - *New (n)* (a fold: the raw goals, as today);
  - *Flags (n) · k wait for main* (a fold: the done goals that wait for main with ✓, then its flags with ⚑: the goal,
    the date, ≈$, *k of n first time*; the newest ten, then *All n*).
- **A goal's row** (42 px): its **pile** (a back with the element on it, `.ork-elem`, and one to three edges behind for
  its open tasks), its title (one line, cut), its line (*k/n in dev · implementation* or *checking*; in Planning its
  words, the alert colour only for a question or a plan to start), its mark (✗ a failure, ↻ at work, ☾ tonight, ! a
  stop), and **›** (opens the goal's screen, as a Planning row opens today). A press on the row (not on ›) **picks** the
  goal into the filter (§3.5): `aria-pressed`, a second press takes it out; a hover **peeks** (the board shows only
  that goal's cards while the pointer is on the row, nothing is kept).
- **New goal**, at the foot of the column: a small **face-down pile** (three edges and a back with *+*, 44 × 60) with
  *New goal* (pixel face) and *draw a blank one*. A press turns its top card over (≈ 0.42 s, in steps) and opens the
  New goal dialog (the old New idea dialog, its words, §3.7); under reduced motion it opens at once.

### 3.4 The field: the members' rows by phase, a goal's tasks as a stack
- The party row is spec 49 §5 (the members, their two numbers, the signs, the peek, solo). Under each member, its
  open tasks lie in **rows by phase**: **now** (a task at its goal's current wave: the lowest wave among the goal's open
  tasks), **next** (one wave after), **later** (two or more); a row that has nothing is not drawn; each row has its
  word (*now*, *next*, *later*, 10 px, faint) over its left edge. The rows after *now* are muted (spec 49's rows below
  the top). The checkers' columns the same (a check's phase is its own wave against its goal's).
- In a row, **one stack per goal** (the goals in the Board's order): the member's open tasks of that goal at that
  phase. The top card is the front one (spec 49's order: at work, failed, in Review, ready, waiting, tonight); behind
  it one or two **edges** (offset 4 px up and right) when there are more, and **×n** on its corner.
- **A card is 5:7** (the width of its share of the column, at most 104 px, × 146; two stacks to a row in a column of
  210 px): the goal's **element** top left (`.ork-elem`), the mark top right (↻, ✗, ☾), the goal's short name (one
  line, muted), the task's name (two whole lines at most, spec 49 §5.4), the foot (*working 12 min*, *failed*, *in
  Review*, *tonight*, *after k1, k2*). A failed stack has the danger edge.
- **A press**: a stack of one opens its task (or its result), as today; a stack of more **spreads** (§3.6).
- **Arrows**: hovering a card (or a spread card) draws an arrow **from each task it waits for** to it and **from it
  to each task that waits for it**, for the cards shown (a dashed ink line with a head, over the field, under the
  drawer); a hidden end draws none. Only with a fine pointer (`(hover: hover)`); keyboard focus draws them too. The
  card's foot keeps the words (*← waits for <short>*, *→ n wait for it*).
- Solo (one member): its rows across the width, as spec 49 (the same order, the others gone).
- *✓ k in dev* under a column, *No task now*, Waits for your look, the gate, the bottom row and the limits: as spec 49.

### 3.5 The filter
While goals are picked (or one is peeked), the field, *Waits for your look* and the bottom row show only their cards,
results and stops (the rest leave, in the motion of spec 49 §11.2, without a ✓); a member with none says *Nothing of
these goals*. The tab's count still counts every stop. *Show all*, Esc, or a press on the party's tab clears it. The
picks are kept per party for the session (not across a reload).

### 3.6 A spread
A press on a stack of more dims the field (the scrim) and **deals** its cards in a row over it (120 × 168, centred,
wrapped if they do not fit), each from the stack's place to its own (≈ 0.3 s, 35 ms apart, in steps), over the line
*<goal> · n tasks of <member> at this phase*; each card has the element, its phase word, its mark, the goal's short
name, its name, its dependency line (*← waits for …* / *→ n wait for it*) and its foot; a press on one opens it (the
spread stays under the drawer); **Put them back**, Esc or a press on the scrim gathers them (the deal backwards). No
deal under reduced motion. A spread never covers the party row's members' numbers' update (it closes itself when its
stack is gone).

### 3.7 The dialogs and the drawer (`js/shell/`)
- **New party** (`goalwizard.js`): its name, *What it is for* (one line), the party (*one of yours, or from the
  library*: the leader, builders and checkers as today, with the price a goal, spec 43 §3), the checks on every goal,
  its priority (*goes first when the window is short*); no metrics, no deadline, no links. It sends `ideas.goal_save`
  with `title`, `about`, `team`, `every`, `leader`, `party`, `priority`.
- **Edit the party** (`goaldialog.js`): the same fields.
- **About this party** (`goalview.js`, in the drawer): *What it is for* (its brief and Summary), *The party* (the
  leader, each member with what it does and costs), *Checks on every goal*, *What it costs* (so far, today, the price a
  goal), *Its flags* (⚑ the goal · date · ≈$ · *k of n first time*; the newest ten, then *All n*), and only for a party
  with a verdict of before, *Before: <its old flag's words>*; *Edit the party* and *Save it to your parties*. No
  Metrics, no Verdict, no *Ask … to accept*.
- **New goal** (the New idea dialog): its words, and the element it will get (`.ork-elem.big`: `idea_element.pick`'s
  rule over the party's open goals' elements in the map, the same as the host's). *Add the goal* sends `ideas.add` as
  today.
- The drawer's kind words (`store.js`): *Party*, *Goal*; `preview.js`'s way back says *party*.
- Every desktop template in today's words (§0).

### 3.8 The flag line
After a gate's merge that raised flags (`ideas.flags`' `goals` newer than this device saw), one line over the field
(36 px, the party line's place, until closed): *⚑ n flags raised · <a>, <b> and k more are in main* and ×; the ⚑ in the
success colour; said once per device (`localStorage` `orkboard.flags.goals.<project>`: the newest `at` seen), never over
the work, never again; a goal's row in *Flags (n)* is lit once (spec 49 §11.5's highlight). Its press opens *About this
party* at *Its flags*.

## 4. Motion (B, C)
As spec 49 §11, plus, each in steps, none under `prefers-reduced-motion`, none on a first read or for what changed while
the page was hidden:
1. **A spread deals** its cards from the stack (≈ 0.3 s, 35 ms apart) and gathers them back the same way.
2. **New goal turns** its top card (the desktop's pile, ≈ 0.42 s; the phone's card from the FAB to the middle, ≈ 0.5 s)
   before the form opens.
3. **A flag is raised once**: the flag line appears (no fly), its goal's row lit once.
4. **The filter** moves cards out and in with spec 49 §11.2–11.3's leave and settle, without a ✓.
5. Nothing moves under the pointer or the focus (spec 49 §11.4): a stack under the pointer does not change while it is
   hovered; a spread holds its cards while open.

## 5. Sizes (B)
At 1 440 × 900: the tabs 40, the party line 36, the party row 64, the bottom row 64; the left column 248 (a goal's row
42, the New goal pile 60 + 12 of padding); a card 104 × 146 at most (5:7) with two stacks to a row in a 210-px column;
the spread's cards 120 × 168; the arrows 2 px. No page scroll; the left column's list scrolls.

## 6. The phone (C)
The mockup F is the target. As spec 49 §10 with:
1. **The top bar**: the project's name is a button (*harbor ⌄*) that opens the **Projects** sheet (from the top): the
   projects as rows (the name; *this one*; what waits), *Open on your computer: a tap switches this phone to one.*; a tap
   switches as the drawer's projects do today (`projects.use`). The menu keeps Stop all, Spend, Agents and the settings;
   its aria-label *Menu: Stop all, Spend, Agents and settings*; the projects leave it.
2. **The party chips** (56 px row): the leader's head (20 px), the party's short name, the stops' count, ↻; no %.
3. **The party bar** (44 px, one line, quiet: faint 12 px text, no title, no second line): *k/n done* (the count,
   §0), the party's price a goal (*≈$2–4 a goal*), and **›**; a tap opens **About this party** (a sheet: §3.7's blocks, *Edit the party*, *Save it to
   your parties*). At its right the gate, quiet (no green): *dev → main* with its count (ink), its screen as spec 49;
   *main ✓* (disabled) when up to date.
4. **The goals bar** (44 px, one line, quiet): *⌄ Goals n · k at work · j ask you*; while the filter is on: the picked
   goals' elements, *k of n goals* and *Show all*. A tap opens the **Goals** sheet (from the bottom): a line *A tap shows
   only that goal’s tasks; tap more to add them. › opens one.*, *At work*, *Planning*, *Waits for main · n* (✓),
   *Flags · n* (⚑); a goal's row 52 px (the pile with its element, the title, its line, its mark, ✓ when picked) and ›
   (44 px). A tap picks or unpicks (the filter as §3.5: the columns, the results and the stops).
5. **The stage switch** stays (Planning · Implementation · Checking). Under the members, the **rows by phase** with
   their stacks (§3.4's rules): a card **132 × 185** (5:7), two columns at 390 px; the leader's Planning (a goal per
   card, the element top left, its words at the foot) and a member's solo: two cards to a row, centred, 16 px apart.
   A raw goal's card is dashed with its element dim.
6. **A spread** is a strip over the field: the line *<goal> · n tasks of <member> at this phase*, the cards (172 × 240)
   in a row that scrolls sideways (snap to a card), dealt; each card with its **dependency line** (no arrows on the
   phone); *Put them back*. A tap on a card opens it.
7. **The create dial**: **New goal** (a blank card turns over from the FAB to the middle, ≈ 0.5 s, then the full-screen
   New goal form: its element, *Its title*, *What it is for*, *Add the goal*, *Put it back*), **New party** (*one of yours,
   or from the library*: the New party sheet), **Add to the party**. The FAB's aria-label *Create: a new goal, a new party
   or a member of this one*.
8. **Elements** on every card, stack, stop and result; the **flag line** under the party bar after a gate's merge (§3.8's
   words, once per device: `localStorage` `orkcraft.flags.goals`), its × 44 px.
9. **No lost tap** (decisions §63.8). Today a tap can be lost: a press moves the focus, `focusout` releases the holds
   (`shell-motion.js` `makeHolds`), whose 0 ms timer bumps `st.tick` and redraws the whole pane between the mouse's down
   and up, so the click lands on a node that is gone (the tests retry their taps for it). So:
   - `makeHolds` redraws on a release **only when a redraw was held back** (a `deferred` flag set when `held()` said
     yes, cleared by the redraw);
   - **a pointer guard** on the arena's and the stops' roots: a `pointerdown` (capture) sets `down`; while it is set, a
     draw (`arena.draw`, `stops.draw`, the snapshot's, the refresh's, the poll's) is **postponed** (`pending`, its
     signature not used up) and runs after `pointerup`/`pointercancel` in a 0 ms timeout (the click lands first);
   - the tests' retries go (`tests/test_pwa_shell_browser.py` `_band`, `_tap`, `_open_idea`, `_pop`'s wait loop,
     `tests/test_pwa_map39_browser.py`'s Process now): one tap must do it; a new test presses down, forces a redraw
     (a snapshot), releases, and sees the click done.
10. `sw.js`' `CACHE` one up (`orkcraft-app-v56`) and `tests/test_pwa.py`'s pin; the new modules in `SHELL`; `gui/pwa.py`
    serves orkUI's `elements/*.svg` as it serves `marks/` (the masks of `.ork-elem` resolve beside `components.css`;
    a mask needs the page's origin, so they are never read from elsewhere).
11. Every phone string in today's words (§0): `shell-goal.js`, `shell-goal-new.js`, `shell-preview.js`, `board-app.js`
    and the arena's files say *party* and *goal* as the table says.

## 7. Tests
- **A0**: §1.5.
- **A**: §2.7.
- **B** (browser, desktop): the tabs (*Parties*: head, name, *k/n*, the stops' count, ↻; no meter, no %); the party line and
  About this party's blocks (no Metrics, no Verdict; *Before:* only with a verdict of before); New party's fields and
  `ideas.goal_save`'s arguments; the goals list (At work, Planning, New (n), Flags (n) · k wait for main; a row's pile,
  element, line, mark; a press picks, a second unpicks, hover peeks, *Show all*, Esc); the filter (the field, the
  results and the stops show only the picked goals' cards; *Nothing of these goals*); the rows by phase (*now*, *next*,
  *later* from the goals' waves; the order of the stacks; ×n; a card 5:7 at most 104 wide; the element; two stacks to a
  row in a 210-px column); a spread (the cards, the line, a press opens one, Put them back, Esc; none moving under
  reduced motion); the arrows on hover (both ways, none for a hidden end; the foot's words); New goal's pile (the turn,
  the dialog, the element it shows); the flag line (once, its words, ×, its press); every template in today's words
  (`tests/test_gui_wording.py`); no page scroll at 1 440 × 900; below 1 024 px.
- **C** (browser, phone): the Projects sheet from the top bar and the menu without the projects; the chips (head, no %);
  the party bar's one line (*k/n done*) and About this party's sheet; the gate's quiet button; the goals bar and its sheet (picks,
  *k of n goals*, *Show all*, the filter on the columns, results and stops); the rows by phase, the cards 132 × 185, two
  to a row in Planning and solo; a spread's strip (snap, the dependency lines, Put them back); the dial's three ways and
  New goal's turn (none under reduced motion); the flag line once; **one tap opens** (no retries left in the phone tests;
  the down–redraw–up test); 44 px targets; the service worker's version and `SHELL`.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_architecture.py`.

## 8. Files a part may need beyond its row
B: the desktop browser tests that read a string or a region this spec renames (*Goals* → *Parties*, *The goal at work*
→ *The party at work*, *+ New goal* → *+ New party*, *About this goal* → *About this party*, *Edit goal* → *Edit the
party*, *New idea* → *New goal*, *Planning* region → *Goals*): `test_shell_browser`, `test_map_desktop_browser`,
`test_board_browser`, `test_project_desktop_browser`, `test_own_parties_desktop_browser`,
`test_party_price_desktop_browser`, `test_party_proposals_desktop_browser`, `test_recap_desktop_browser`,
`test_week_desktop_browser`, `test_races_browser`, `test_lens_desktop_browser`, `test_check_review_desktop_browser`,
`test_gate_browser`, `test_shell_36_browser`, `test_ops_desktop_browser` and any other the full suite names: each keeps
what it proves. `tests/test_shell_browser.py` keeps the names the phone's tests import (`GREEN`, `task`, `PARTY`,
`PARTY_LINES`, `party_price`) and its helpers' names. C: the phone browser tests that retry a tap (§6.9) or read a
string this spec renames (`test_pwa_shell_browser` — only its retry helpers and strings; it is shared with B: C edits
only the helpers `_band`, `_tap`, `_open_idea`, `_pop`, B edits nothing else there in the same lines —,
`test_pwa_map39_browser`, `test_pwa_board35_browser`, `test_pwa_agents36_browser`, `test_pwa_check_review_browser`,
`test_pwa_party_proposals_browser`, `test_pwa_races_browser`, `test_pwa_week_browser`, `test_gate_phone_browser`,
`test_pwa_recap_browser`, `test_pwa_push_browser`, `test_pwa_ops38_browser`, `test_pwa_goal*`). Both: `README.md`'s
first line is the owner's (already written with this spec). A part that needs any other file: stop and write it in §10
(as built) first.

## 9. Not in this spec
- Moving a goal to another party from the faces (`ideas.move` exists; a later spec), and offering a new goal to the
  party whose code it touches (*Its code* in the mockup).
- More than five elements (a sixth goal at work in one party repeats the least used one; its title tells them apart).
- A backfill of flags for goals in main before this spec; a party's end, metrics or verdict of its own.
- *Let the Taskmaster decide* and *Later* among the phone's quick answers; dragging a card or a stack; Camp's skin.

## 10. As built (notes, no change of the contract)
