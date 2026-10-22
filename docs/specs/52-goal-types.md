# Spec 52 — Goal types: the leader deals what kind of goal, a type says who the party needs; the stages wear the party's faces; a stop is counted only where it cannot be seen; the party switch is a deck

The owner, 22 October (decisions §65). After spec 51 a new goal is always a blank card: the person writes it from
nothing, and the party works it with whoever is in it, so a logo asked of a party with no Artist is drawn by the Grunt.
What the person knows best is **what kind of goal** it is (a new logo, a bug, a landing page), and that kind already
says who must do it and what the leader needs to hear. So the **leader deals the goal types** of its party (a designer:
*New screen*, *New icon*, *New logo*, *New feature*; the Taskmaster a general set), each with **its sign**, the few
lines only the person can give, and **the kinds of work it needs**; a type whose work no one in the party does says so
in the form, and the agent who does it **joins** (a free seat) or **swaps** in (a full one). A plan that gives work to
no one in the party says so on its stop. The phone's stage switch, which was always **by band** (the leader's,
the builders', the checkers'), shows **the party's faces** with their words under them and **no counts**: what waits
for the person is counted once, by the hand, and marked once, by a sign where it comes from; only what waits **in
the other parties** is counted, on the **party switch**, which becomes a deck: over the leader on the desktop, at
the end of the stage switch on the phone. **Nothing flies** (decisions §62.8 stays). **Builds:** Claude ·
**Review:** full · P1.

**What it is, and is not:** a new start for a goal (its type), a new line on a plan's stop, and a new place for the
party switch and for the counts. On the host: the types (a new module, no model), a goal's `type`, `ideas.add`'s
`type`, `asks` and `join`, `ideas.start`'s `join`, a plan's `missing`, and a line in two prompts. **Storage keeps its
shape** (Orkline reads the same Board, CLAUDE.md): a goal's type is one more key in its `state.json`, a plan's
`missing` one more key in its plan; the party is changed the way *Edit the party* changes it. No new setting, no new
command. No mockup: **this file is the target** for words, structure and sizes.

Four parts. **A0 and A first, at once** (A0 is orkUI's repository, A touches no file of the page); **B and C from both**
once they are in (they touch no file of each other's). **This file is the contract**; the rest is the builder's choice
inside its files. **Change nothing outside a part's files** but those §9 names.

| part | builds | files (and their tests) |
|---|---|---|
| **A0. orkUI** (repository orkWorks/orkUI) | §1 | `office/signs/` gains eleven signs (§1) and their `.ork-sign` classes, the gallery's *Signs* section, the signs' README, `CHANGELOG.md` (**0.3.3**), the versions (`pyproject.toml`, `tokens.json`, `tokens.css`'s header); `tests/test_orkui.py`. Then, in orkBoard, the copy: `python -m orkboard.design.orkui <orkUI>` (only `design-system/orkui/` changes) |
| **A. Backend** | §2 | new `realm/goal_types.py` (the types, their needs, the agent who does a kind; no face, no model), `realm/ideas.py` (`STATE_DEFAULT` gains `type`), `gui/ideas.py` (`ideas.add`'s `type`, `asks`, `join`; `ideas.start`'s `join`; split into a new `gui/ideas_types.py` when it would pass ~600 lines), `gui/ideas_map.py` (a party's `types`), `realm/board_map.py` (a goal's `type`; a plan row's `missing`), `core/idea_keeper.py` (the plan prompt's type line; the plan's `missing`), `core/idea_draft.py` (the draft prompt's type line), `realm/event_log.py` (the fields of §2.7), `realm/lexicon.py` (`goal_type`); new `tests/test_goal_types.py`, `tests/test_gui_ideas.py`, `tests/test_board_map.py`, `tests/test_idea_keeper.py`, `tests/test_idea_draft.py`, `tests/test_event_log.py`, `tests/test_lexicon.py` |
| **B. Desktop** | §3, §4, §6 | `js/arena/goaltabs.js` (the party switch becomes the party's deck and the parties' spread), `js/shell/topbar.js` (the switch leaves the top bar), `js/arena/goals.js` (the left column's top line over the leader; the New goal pile deals the types; a goal row's type sign; a stop's row marked once), new `js/arena/types.js` (the types' cards, the join line's words), `js/arena/spread.js` (it deals parties and types as it deals a stack), `js/arena/stops.js` (a plan's missing line and its answers), `js/arena/stacks.js` (a card's alert edge goes), `js/shell/ideadialog.js` (New goal by its type), `js/shell/lens.js` (the type's lens first), `js/arena/arena.css`; `tests/test_arena_decks_desktop_browser.py`, `tests/test_arena_desktop_browser.py`, `tests/test_lens_desktop_browser.py`, new `tests/test_goal_types_desktop_browser.py`, and the desktop tests that press the old switch (§9) |
| **C. Phone** | §5, §6 | `pwa/shell-arena.js` and `pwa/shell-arena-words.js` (the stage switch: faces, signs, no counts; the party's deck at its end), `pwa/shell-arena-field.js` (a band with no one), `pwa/shell-where.js` (the project's button; the parties' sheet from the deck), `pwa/shell-top.js`, `pwa/shell-projects.js` (the projects' sheet), `pwa/shell-goals.js` and `pwa/shell-goals-words.js` (the goals bar says the party; a row's type sign), `pwa/shell-fab.js` (the deck deals the types), new `pwa/shell-types.js` (the types' strip, the join line's words), `pwa/shell-ideas.js` (New goal by its type), `pwa/shell-lens.js` (the type's lens first), `pwa/shell-stops.js` (a plan's missing line and its answers), `pwa/board.js` (the wiring), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up, `pwa/shell-types.js` in `SHELL`) with `tests/test_pwa.py`'s pinned version; `tests/test_pwa_decks_browser.py`, `tests/test_pwa_arena_browser.py`, `tests/test_pwa_arena_stops_browser.py`, `tests/test_pwa_lens_browser.py`, new `tests/test_pwa_goal_types_browser.py`, and the phone tests that tap the *where* button (§9) |

## 0. The words
- **goal type** (`TERMS` `goal_type`, *goal type / goal types*): what kind of goal a party's leader deals (*New logo*,
  *Fix a bug*). The interface seldom says the word: it says the type's own name.
- New strings, in these words: the types' names and lines (§2.1), *pick its type*, *New goal: pick its type, or a blank
  one*, *New goal for <party>*, *needs: <agent>*, *<agent> joins the party*, *≈$0.40 a run*, *Swap: <member> leaves,
  <agent> joins*, *Who leaves*, *<n> runs this week*, *Without <agent>, its <kind> goes to the Grunt.*, *The party's
  <builders | checkers> all have work open: <agent> can join from Edit the party when one is done. Till then its <kind>
  goes to the Grunt.*, *Refs*, *Links*, *Add a picture*, *Pictures you like*, *No one in the party does <kind>: <agent>
  would.*, *and <n> more*, *Add and start*, *Start without*, *<agent> joined the party; the work started.*, *Added:
  <agent> joined the party; <leader> drafts it now.*, *No builder in this party: the Grunt does its tasks.*, *No checker
  in this party: a goal is done when its own Done when lines are.*, *Parties ⌄* (the button: *Parties*), *Parties of
  <project>*, *shown*, *Projects*, *this one*, *k of n goals done* (the goals bar).
- **A kind of work in a sentence** is `roles.KIND_LABELS`' label with its first letter lowered unless its second letter
  is a capital: *pixel art*, *text for people*, *UI kit*, *experiments*.
- spec 50 §0's rules hold: the interface says *party*, *goal*, *task*; **no *card*, *deck*, *hand*, *spread*, *fan*,
  *type card*** in what a person reads (they are this spec's and the code's words); every symbol is orkUI's.
- **A type is told by its sign, never by a colour** (decisions §65.4): colour is the goal's element (spec 50 §1.2) and
  the signals (alert, danger, success).

## 1. orkUI: eleven signs (A0)
As spec 50 §1.6 (`office/signs/<name>.svg`, `viewBox="0 0 7 7"`, one `path` of unit squares, `.ork-sign.<name>`, 14 × 14
and `.big` 28 × 28, drawn in the colour of their text), a type's sign each:

| feature | bug | tidy | screen | picture | logo |
|---|---|---|---|---|---|
| `...#...` | `.#...#.` | `.....##` | `#######` | `#######` | `...#...` |
| `..###..` | `..###..` | `....##.` | `#.....#` | `#.....#` | `..#.#..` |
| `#######` | `.#####.` | `...##..` | `#.....#` | `#...#.#` | `.#.#.#.` |
| `.#####.` | `#.###.#` | `..##...` | `#.....#` | `#.....#` | `#.###.#` |
| `..###..` | `.#####.` | `.####..` | `#######` | `#..#..#` | `.#.#.#.` |
| `.##.##.` | `#.###.#` | `#####..` | `...#...` | `#.###.#` | `..#.#..` |
| `.#...#.` | `..#.#..` | `#.#.#..` | `..###..` | `#######` | `...#...` |

| target | flask | horn | chart | page |
|---|---|---|---|---|
| `.#####.` | `.#####.` | `.....#.` | `.......` | `.####..` |
| `#.....#` | `..#.#..` | `...###.` | `.....#.` | `.#..##.` |
| `#..#..#` | `..#.#..` | `###..#.` | `.....#.` | `.#...##` |
| `#.###.#` | `.#...#.` | `###..#.` | `...#.#.` | `.#....#` |
| `#..#..#` | `#.....#` | `...###.` | `.#.#.#.` | `.#....#` |
| `#.....#` | `#######` | `.....#.` | `.#.#.#.` | `.#....#` |
| `.#####.` | `.#####.` | `.......` | `#######` | `.######` |

*feature* a new thing people can do, *bug* a thing that goes wrong, *tidy* the same behaviour in simpler code, *screen*
a screen, *picture* a picture or an icon, *logo* a mark, *target* a pain of someone's, *flask* an experiment, *horn* a
launch or a post, *chart* a number, *page* a page or a report. A tagline uses spec 51's *text*. The gallery's *Signs*
section shows each at both sizes in ink, muted and on raised; the README's line; the CHANGELOG (**0.3.3**); the versions.
Tests as spec 50 §1.5 (the files, their pixels as in the tables, `NEW_PARTS`, the gallery).

## 2. The host (A)
### 2.1 The types (`realm/goal_types.py`)
A **type** is `GoalType(id, name, sign, line, needs, lens, asks, refs, plan)`:
- `id` (a slug, unique in its leader's set), `name` (the interface's: *New logo*), `sign` (orkUI's, §1), `line` (one
  line: what it makes, ≤ 60 characters);
- `needs`: the kinds of work (`roles.TASK_KINDS`) that someone of the party must take for it;
- `lens`: the lens New goal opens first (`text`, `code`, `screen`, `pain`; `realm/idea_lens.py`), when the party offers it;
- `asks`: at most three `Ask(id, label, hint)`: one-line fields only the person can fill (label ≤ 24 characters, hint ≤
  60); none is required;
- `refs`: whether the form asks for **Refs** (links and pictures the person likes);
- `plan`: one or two sentences for the draft and the plan prompts (§2.5), in the code's words; may be empty.

`TYPES: dict[str, tuple[GoalType, ...]]`, by the leader's id, in this order (the needs are kinds; the asks are *label*
(hint)):

| leader | id | name | sign | line | needs | lens | asks | refs | plan |
|---|---|---|---|---|---|---|---|---|---|
| `taskmaster` | `feature` | New feature | feature | Something people can do that they could not | — | text | — | no | — |
| | `bug` | Fix a bug | bug | Something that goes wrong, made right | — | text | *What you did* (the steps, in order) · *What happened* (what you saw) · *What should have* (what you expected) | no | Write a test that fails the way the person saw first, then the fix that makes it pass. |
| | `tidy` | Clean up | tidy | The same behaviour in simpler code | — | text | *What gets in the way* (what is hard to change today) | no | Change nothing a person or a caller sees; the tests stay green. |
| `architect` | `feature` | New feature | feature | A change across modules, shaped before it is written | — | code | *Must use or avoid* (a library, a pattern, a module not to touch) | no | Shape it first: the modules, the steps and what tests each, then the code. |
| | `bug` | Fix a bug | bug | Something that goes wrong, made right | — | code | as the Taskmaster's | no | as the Taskmaster's |
| | `restructure` | Restructure | tidy | Modules split or moved, one job each | — | code | *What gets in the way* (what is hard to change today) · *Your idea of the shape* (how you would split it) | no | Keep the behaviour; move in steps that each pass the tests; keep the imports one way. |
| `product-designer` | `screen` | New screen | screen | A screen people get through, phone width first | `uikit` | screen | *Who uses it* (and what they came to do) | yes | Write the flow step by step, then the screen: what is on it and why; the UI kit adds what is missing; then the build. |
| | `icon` | New icon | picture | An icon in the pixel style, picked from a few | `art` | text | *Where it shows* (its place and its size) | yes | An Artist draws four to pick from (a pick of 4 images) at the icon's size; the one picked is put in place. |
| | `logo` | New logo | logo | A mark for the product, picked from a few | `art` | text | *What it should say* (three words) | yes | An Artist draws four to pick from (a pick of 4 images); the one picked is put in place at every size the product uses. |
| | `feature` | New feature | feature | A flow and its screens, then the build | `uikit` | screen | *Who uses it* (and what they came to do) | yes | The flow first, then each screen of it, then the build. |
| `product-manager` | `pain` | Solve a pain | target | The smallest change that takes a pain away | — | pain | — | no | Say who it is for and the pain; plan the smallest change that shows it gone. |
| | `experiment` | Try an experiment | flask | A change shown to some people, then measured | `experiment` | pain | *What it should move* (the number, and by how much) | no | An Experimenter writes the question, the split and the number that decides before the change ships. |
| | `launch` | Write the launch | horn | The words people read when it ships | `text` | text | *Where it goes* (the page, the post, the store) | no | — |
| `analyst` | `metric` | A new metric | chart | A number counted from the events | `data` | text | *The question it answers* | no | Say how it is counted: the events, the window, what is left out; add the events that are not logged. |
| | `report` | A report | page | Numbers that answer a question, from the tables | `query` | text | *The question* · *Who reads it* | no | — |
| | `abtest` | An A/B test | flask | Two versions shown, one decided by a number | `experiment` | text | *What it should move* (the number, and by how much) | no | Write the question, the split and the number that decides before it starts; do not stop early. |
| `growth` | `landing` | A landing page | page | A page that says what the product does, and is found | `text`, `seo` | text | *Who it is for* · *Where they come from* | yes | — |
| | `post` | A launch post | horn | A post for one channel, ready for your yes | `text` | text | *The channel* | no | Nothing is posted without the person's yes: write it ready for them. |
| | `tagline` | A tagline | text | One line that says the product, picked from a few | `text` | text | — | no | A Copywriter writes three to pick from (a pick of 3 texts). |

- **The Taskmaster's set is the general one**: a leader with no set of its own (none today) deals it too.
- `of(leader) -> tuple[GoalType, ...]`; `get(key) -> GoalType | None` for a key `"<leader>/<id>"` (a goal keeps its
  type by that key, so a goal moved to another party keeps its own, §2.2).
- `taker(kind, craft) -> str`: the agent of the library who does `kind`: the first of `library.LIBRARY` whose `takes`
  holds it and whose band is `build` or `check`, the leader's craft first, then the others in the library's order;
  `""` when none (nothing is offered: the work goes as today). `art` → `artist`, `uikit` → `ui-kit`, `text` →
  `copywriter`, `seo` → `seo`, `experiment` → `experimenter`, `query` → `sql`, `data` → `data-engineer`.
- `met(state_dir, kind, party) -> bool`, *party* the leader and the team: `roles.role_for(state_dir, kind, party)` is
  someone other than the Grunt, or the Grunt's own kinds (`code`, `tests`) hold it. (The Grunt fills in for everything
  else: a kind it gets only by filling in is not met.)
- `missing(state_dir, root, party_slug, kinds) -> list[dict]`: for each kind not met whose `taker` is not `""`, once
  each, `{kind, words, agent, name, band, free, out}`: `words` the kind in a sentence (§0), `agent` its taker, `name`
  its library name, `band` the taker's band, `free` whether that band has a free seat (`library.SEATS`), `out` the
  members of that band **with no open task** (no task of theirs in the party's goals that is not merged, dropped or
  done) as `[{slug, name, runs}]` (`runs`: tasks finished this week, as `ideas.agents`' `week`), the fewest runs first,
  the band's later member first on a tie. A member with an open task never leaves this way.

### 2.2 A goal's type
- `STATE_DEFAULT` gains `"type": ""` (`realm/ideas.py`): the key `"<leader>/<id>"` of the type it was made from, given
  once by `ideas.add`, never changed (a goal moved by `ideas.move` keeps it).
- `ideas.map`: a node gains `type`: `{id, name, sign}` (`goal_types.get`; `null` with none or an unknown key).

### 2.3 New goal with a type, its asks and who joins (`ideas.add`)
`ideas.add` gains three optional arguments:
- **`type`**: an `id` of the party's leader's set (`goal_types.of(leader_of(party))`), stored as `"<leader>/<id>"`. Not
  one of them: refused *<party>'s leader has no goal type “<id>”*.
- **`asks`**: `{<ask id>: <text>}` of that type's asks, each ≤ 300 characters, its edge spaces cut, an empty one left
  out; an id the type has not, refused. The host writes each answered ask **after the goal's text** as a line `<label>:
  <text>`, in the type's order (`Refs: <links>` for `refs`, `refs` being the id of the Refs' links); the goal's page
  holds them as its words (Orkline reads the same), the draft reads them as any text.
- **`join`**: `{add, out?}`: `add` must be the `agent` of one of the type's `missing` (§2.1) for this party; `out`, when
  given, one of its `out`; when `free` is false `out` is required; refusals in words: *<name> is not what this goal
  misses*, *The party is full: pick who leaves*, *<name> has work open: it cannot leave*. The party changes **before
  the goal is added, under the same lock, the way `ideas.goal_save` changes a team**: the agent installed from the
  library (`library.install`), `out` taken out of the team (and out of `every`), the seats checked (`goal_team.seats`),
  `goal_team.set_team`; it logs `goal_saved` as *Edit the party* does, with `joined`, `out` and `via: "type"` (§2.7).
- The answer gains `type` (the key, or `""`) and `joined` (`{add, out}` or `null`). A goal kept for tonight (*Put it
  back* with words, a closed form) is sent with its `type` and `asks` but **never with `join`**: a party changes only on
  a press of *Add the goal*.
- `photos` (the phone's, spec 41) are taken from the desktop too (§4.3), with the same limits; Refs' pictures are photos.

### 2.4 A party's types (`ideas.map`)
A party (the map's goal) gains **`types`**: its leader's set (§2.1), **the most used first** (`used`: how many of the
party's goals, of any state, have that type), ties in the set's order; each `{id, name, sign, line, lens, asks: [{id,
label, hint}], refs, used, missing}` with `missing` as §2.1 says for the type's `needs` and this party. Computed in
`gui/ideas_map.py` (it reads roles and the week's runs; the pure `board_map.build` reads none), with the map's read,
not apart.

### 2.5 The type in the prompts
- The draft's prompt (`core/idea_draft.py`) and the plan's prompt (`core/idea_keeper.py` `plan_prompt`) gain, when the
  goal has a type, one line beside what its lens pointed at: `Its type: <name>. <plan>` (the name alone when `plan` is
  empty). Prompts keep the code's words; nothing else in them changes.

### 2.6 A plan that gives work to no one of the party (`missing`, `ideas.start`'s `join`)
- After `plan_one` gives each task its role (`core/idea_keeper.py`), the plan gains **`missing`**: the kinds of its
  tasks that are not `met` for the party (leader and team; a goal with no team has none), as `[{kind, agent}]` with
  `agent` its `taker`, once each, in the plan's order, those with no taker left out. A plan made before has none.
- Needs you's **plan row** (`realm/board_map.py` `idea_needs`, kind `plan`) gains `missing`: `[{kind, words, agent,
  name, band, free}]` read against the party **now** (a member added since drops out of it). `ideas.plan` answers the
  same.
- **`ideas.start`** gains `join: {add}`: `add` must be one of the row's `missing` whose `free` is true (refusals: *<name>
  is not what this plan misses*, *The party is full: change a member in Edit the party*). The party changes as §2.3 says
  (`goal_saved` with `via: "plan"`), then **the plan's tasks that have not started** (not running, merged, failed,
  dropped or in Review) are given their role again (`roles.role_for` with the new party), then the plan passes as
  today. Without `join`, `ideas.start` is unchanged (*Start without*).

### 2.7 Measured
- `idea_added` gains `type` (the key or `""`), `asks` (how many answered), `refs` (how many pictures were Refs'),
  `joined` (the agent or `""`), `out` (the member or `""`).
- `goal_saved` gains `joined`, `out` and `via` (`"type"`, `"plan"`; `""` for *Edit the party*).
- `plan_passed` gains `joined` (the agent or `""`) and `missing` (how many kinds the plan missed when it passed).
- The owner reads from them: the share of new goals with a type, by leader and type, against blank ones; how many asks
  are answered; the join line shown, kept, unticked or swapped; a plan's line shown and what was pressed; and, against
  the flags (spec 50 §2.2), whether a typed goal's plan passes at its first round and raises its flag sooner.

### 2.8 The words (`realm/lexicon.py`)
`TERMS` gains `goal_type` → *goal type / goal types* (*what kind of goal a party's leader deals: New logo, Fix a bug;
realm/goal_types.py, spec 52*).

### 2.9 Tests (A)
`tests/test_goal_types.py`: every leader of the library that leads has a set and the Taskmaster's is the general one;
ids unique in a set; every sign one of orkUI's; every need a known kind with a taker; `taker` (the craft first);
`met` (a member who takes it, the leader, the project's role, the Grunt's own kinds, the Grunt filling in);
`missing` (`free`, `out` without the members with open work, its order). `tests/test_gui_ideas.py`: `ideas.add` with a
`type` (stored as the key; refused for another leader's), `asks` (the lines after the text, in order; an unknown id
refused), `join` (a free seat; a swap; `out` required when full; a member with open work refused; the agent installed;
the seats; the party changed before the goal, both under the lock; no `join` with `night`); `ideas.start` with `join`
(the tasks not started given the new member; refusals); `ideas.map`'s `types` (the order by use, `missing`) and a node's
`type`. `tests/test_board_map.py`: the plan row's `missing` against the party now. `tests/test_idea_keeper.py`: the
plan's `missing`; the plan prompt's type line. `tests/test_idea_draft.py`: the draft prompt's type line.
`tests/test_event_log.py`: the fields. `tests/test_lexicon.py`: `goal_type`.

## 3. The desktop: the party's deck (B)
Decisions §65.3 reverses §63.11: the parties leave the top bar.
1. **The top bar** is spec 49 §3.1's again: the project switcher, *Orkline*, the spacer, Agents, Files, Spend, Stop all,
   the settings. `PartySwitch` goes; *results go into dev ⌄* stays under the gate.
2. **The left column's top line** (32 px, over the leader's row): the party's short name (pixel face, 13 px, ink, cut
   with an ellipsis), *k/n* (muted, its tooltip *k of n goals done*), the `work` sign while at work; at its right
   **Parties ⌄** (a quiet button 28 px high: a small deck — two edges behind a back, 14 × 18 —, the word, the chevron,
   and the warning count of the stops that wait in the project's **other** parties and in Operations, when there are
   any). Its label: *Parties: <party> shown[, n stops wait in the other parties]*.
3. **The leader's row stands on the deck**: one edge behind it (3 px up and right, as a goal's pile) when the project
   has one other party or Operations, two when it has more. Nothing else of the leader's row changes.
4. **A press on Parties ⌄ deals the parties** as a spread (spec 50 §3.6: the scrim, cards 120 × 168 dealt from the
   deck's place, ≈ 0.3 s, 35 ms apart, in steps; none under reduced motion) over the line *Parties of <project>*: a card
   per party in the Board's order — the leader's head (36 × 33), the party's name (pixel face, two lines at most), *k/n
   done*, its members' small heads in a row, its stops' count (warning) and the `work` sign at its top right; the party
   shown raised with a double ink frame and *shown* —, then **Operations** when the project has them (the `sliders`
   icon, its stops), then a blank card **+ New party** (*one of yours, or from the library*). A press picks the party
   (the spread gathers, the board shows it, kept per device as today), opens Operations, or opens New party; *Put them
   back*, Esc and a press on the scrim gather them. It is a `dialog` named *Parties*; the focus starts on the party
   shown; ←/→ move between the cards, Enter or Space presses; Esc gives the focus back to Parties ⌄.
5. The filter (spec 50 §3.5) is cleared by *Show all* and Esc, as before; the press on the shown party's tab that also
   cleared it goes with the tab.

## 4. The desktop: New goal by its type, a plan's missing line, a stop marked once (B)
1. **The New goal pile** (the left column's foot) says *New goal* · *pick its type* (its label *New goal: pick its
   type, or a blank one*). A press **deals the party's types** (`types` of §2.4) as a spread over the line *New goal for
   <party>*: a card each — the type's sign (`.big`) top left, its name (pixel face), its line (muted, three lines at
   most) and, when it misses someone, *needs: <name>* with that agent's small head at its foot (muted ink: it is not a
   stop) —, then the blank card (*A blank goal*, the pile's back with its +). A press on a card **turns it over** (the
   pile's turn of today, ≈ 0.42 s, in steps) and opens New goal with it; *Put them back*, Esc, the scrim gather them. No
   deal and no turn under reduced motion. A map with no `types` (an older host) opens the blank form as today.
2. **New goal with a type** (`js/shell/ideadialog.js`): its head is the type's sign (`.big`) and name in place of *A
   blank goal*, *for <party> · <leader> reads it next* under it; the party is **fixed** (said, not a select: a type is
   its leader's); then the element, *Its title*, *What it is for*, **the type's asks** (a one-line field each, its label
   over it, its hint as the placeholder; none required), **Refs** when the type has them (*Links*: one line; *Pictures
   you like*: *Add a picture*, which takes a file, a paste or a drop on the form, PNG, JPEG, WEBP or GIF, shown as small
   thumbnails with ×; sent as `photos`), the lens (the type's `lens` open first when the party offers it, else the
   leader's as today), **the join line** (§4.3), the priority, *Add the goal* · *Put it back*. *A blank goal* is the form
   of today. *Add the goal* sends `ideas.add` with `type`, `asks` and, when the join line is ticked, `join`; its toast,
   when someone joined: *Added: <agent> joined the party; <leader> drafts it now.* (*Kept for tonight.* as today for a
   Low goal).
3. **The join line**, one per entry of the type's `missing` (two at most):
   - a free seat: a checkbox, ticked at first: *<agent> joins the party*, the agent's small head, *≈$0.40 a run*
     (muted: its tier's price, `roles` `tier_costs`; its tooltip *at API prices, not your bill*); unticked, the line
     under it says *Without <agent>, its <kind> goes to the Grunt.*;
   - a full band with someone who can leave: a checkbox, ticked at first: *Swap: <member> leaves, <agent> joins* and
     *Who leaves ⌄* (a select of `out`: *<name> · <n> runs this week*, the first picked); unticked, as above;
   - a full band where no one can leave: no checkbox, a muted line: *The party's <builders | checkers> all have work
     open: <agent> can join from Edit the party when one is done. Till then its <kind> goes to the Grunt.*
4. **A plan's missing line** (`js/arena/stops.js`): a plan stop whose row has `missing` says under its text, muted, *No
   one in the party does <words>: <name> would.* (*and <n> more* when it misses more than one kind). Its quick answers:
   when the first entry is `free`: **Add and start** (primary; `ideas.start {slug, join: {add}, via: "hand"}`; its
   title *<name> joins the party, then the work starts*; its toast *<name> joined the party; the work started.*) and
   **Start without** (`ideas.start` as today); when it is not: **Start without** and **Edit the party**. A plan held for
   the night keeps *Start now* and *Open the plan* and says the line. The plan's screen in the drawer says the same line.
5. **A stop is marked once where it comes from** (decisions §65.2): a goal's row in the left column keeps its `!`
   (`alert`) sign and loses its 2-px alert edge and the alert colour of its words (spec 49 §4.3, spec 50 §3.3); a task's
   card on the field keeps its sign and loses its alert edge (a pick's, spec 51); a failure keeps its danger edge (a
   failure is a fact about the work). No count of the party shown's stops anywhere: the bottom row is their count. The
   only count of stops is Parties ⌄'s, for the other parties.
6. **A goal's row** (the left column's lists) shows its type's sign (14 × 14, muted ink) before its title when it has
   one; no other place draws it (a task's card keeps its element and its mark).

## 5. The phone (C)
1. **The top bar**: the menu, **the project's button** (*harbor ⌄*: the project's name, 12 px, 44 px high, its label
   *Project harbor. A tap shows your projects*), the limits. Its sheet, from the top, **Projects**: *this one* (the
   project shown, marked), then the other projects with what waits in each (`shell-projects.js` as today; a tap switches)
   and *Open on your computer: a tap switches this phone to one.* The party's name, head and counts leave the top bar.
2. **The goals bar says the party**: *⌄ <party short name> · k of n goals done* (the name cut at 14 characters with an
   ellipsis; with the filter on: the name, the picked goals' elements, *k of m goals*, *Show all*); the gate at its right
   as today; a tap opens the Goals sheet as today.
3. **The stage switch wears the party's faces** (decisions §65.1), 52 px high: three tabs (a `tablist` named *Stages*)
   and, at its right, outside the tablist, **the party's deck**.
   - Each tab: **the faces** of its band over **its word**: *Planning* the leader's head; *Implementation* the builders'
     heads in the party's order (three at most); *Checking* the checkers' (two at most). A head is orkUI's 24 × 22, each
     after the first 14 px after the one before (they overlap). Its word under them, 11 px, one line, never cut at 390
     px. A band with no one shows one empty head (a 24 × 22 outline, 1 px dashed `--ork-edge`).
   - **No number.** At the faces' top right (overlapping the last head by 4 px) one sign, 14 × 14: `cross` in danger ink
     when a task of that band failed, else `alert` in alert ink when a stop of that band waits (Planning: a plan, a
     question, a proposal; Implementation and Checking: a pick, a member's question), else none. The tab picked keeps its
     ink underline. Its label: *Implementation: Grunt, Tester. 1 failed* · *Planning: the Taskmaster. 2 wait for you* ·
     *Checking: no checker*.
   - **The party's deck**: a button 52 × 52 (a small deck: two edges behind a 22 × 30 back with the chevron down, orkUI's
     tokens), the warning count of the stops that wait in the project's other parties and in Operations at its top
     right (none when none: the one count of stops on the screen). Its label *Parties: <party> shown[, n stops wait in
     the other parties]. A tap shows the parties*. A tap opens **the parties' sheet** from the top: today's *where*
     sheet without its projects (*Parties*: the parties' rows, Operations' row, *+ New party*); a pick is kept
     (`orkcraft.goal`) and closes it.
   - The three tabs share what is left of the width (≈ 100 px each at 390).
4. **A band with no one** (the field, `shell-arena-field.js`): Implementation says *No builder in this party: the Grunt
   does its tasks.*, Checking *No checker in this party: a goal is done when its own Done when lines are.*, each with
   **Add to the party** (Edit the party, as About this party's). **No other place adds a member on the field** (decisions
   §65.7).
5. **New goal by its type**: a tap on the deck FAB lifts its top card (as today) and **deals the party's types** as a
   strip over the scrim, above the FAB: the line *New goal for <party>*, cards 132 × 185 in a sideways strip snapped to a
   card (two whole and a third showing at 390), each as §4.1's, the blank card last, *Put them back* (44 px); the scrim
   gathers them. A tap on a card turns it over and grows it into the full-screen form (today's 0.5 s, from that card's
   place). Under reduced motion the strip shows at once and the form opens at once. The FAB's label: *New goal: pick its
   type, or a blank one*. A map with no `types` opens the blank form as today.
6. **The form by its type** (`shell-ideas.js`): as §4.2, in one column: the type's sign and name, the party fixed, the
   element, *Its title*, *What it is for* (with Photo and the mic as today), the asks, **Refs** when the type has them
   (*Links*, one line; the pictures are the form's Photo, its hint *Pictures you like*), the lens (the type's first), the
   join line (§4.3's, its select a native one, 44 px), the priority, *Add the goal* · *Put it back*. The blank goal is
   today's form.
7. **A plan's missing line** (`shell-stops.js`): the fan's plan card and the raised one say §4.4's line; the raised
   one's answers are §4.4's as 44 px buttons (*Add and start* · *Start without*; *Start without* · *Edit the party*), and
   *Open it on its own screen*.
8. **A stop is marked once**: no count in the stage switch, none in the top bar; the field's cards and the Goals sheet's
   rows keep their signs and lose an alert edge (as §4.5); a failure keeps its danger edge; the parties' sheet keeps its
   rows' counts (it is where the other parties are seen). A goal's row in the Goals sheet shows its type's sign (§4.6).
9. `sw.js`' `CACHE` one up and `tests/test_pwa.py`'s pin; `pwa/shell-types.js` in `SHELL`. Touch targets 44 px.

## 6. Motion (B, C)
**Nothing flies** (decisions §62.8, §65.8): an answered stop leaves the bottom row as it does today, and nothing moves
from it to the task it answered. The deals of this spec are spec 50 §4's spread (a deal from the pile or the deck, and
back), and the turn of a card is New goal's of today; none under `prefers-reduced-motion`, none while the page is
hidden; nothing moves under the pointer or the focus (spec 49 §11.4).

## 7. Tests
- **A0**: §1.
- **A**: §2.9.
- **B** (browser, desktop): the top bar without the parties; the column's top line (the name, *k/n*, the work sign) and
  Parties ⌄ with the other parties' count (none when none); the leader's row's edges; the parties' spread (the cards,
  *shown*, Operations, *+ New party*, a pick, *Put them back*, Esc, the keys, the focus back; no deal under reduced
  motion); the New goal pile's types (the order, *needs:*, the blank last, the turn, a map with no `types`); New goal by
  a type (the head, the party fixed, the asks sent, Refs' links and a pasted picture sent as `photos`, the type's lens
  first; the join line's three shapes, its select, *Add the goal*'s `join` and toast; *Put it back* with words sends no
  `join`); a plan's missing line and its answers (`ideas.start` with `join`; *Start without*; full: *Edit the party*); a
  goal's row: `!` without the alert edge or words, its type's sign; a pick's card without the alert edge, a failure with
  its danger edge; no count of the shown party's stops; every template in today's words (`tests/test_gui_wording.py`).
- **C** (browser, phone): the top bar (the project's button and its Projects sheet; no party, no count); the goals bar
  with the party's name; the stage switch (the faces, the overlap, the words not cut at 390, the empty head; no number;
  ✗ over !; the labels); the party's deck (its count of the other parties, its sheet, a pick kept); a band with no one and
  *Add to the party*; the FAB's strip (the types, *needs:*, the snap, the blank last, *Put them back*, the turn, reduced
  motion); the form by a type (as B's, Photo as Refs' pictures); the plan's missing line on the fan's card and the raised
  one, its answers; the signs without the alert edges; 44 px targets; one tap does it (no retries); the service worker's
  version and `SHELL`.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_architecture.py`.

## 8. Not in this spec
- **A guest for one goal** (an agent who joins for a goal and leaves at its flag): the owner chose the swap.
- **A designer's spec first**: a builder's task that ends in questions to the person before the code waves (Pick one,
  spec 51, is the one such end today); a leader of the library as a builder.
- A person's own goal types; types for Operations (its templates, spec 38, stay its own *New…*); a type changed after
  the goal is made; types of more than one leader in one party.
- Moving a goal to the party whose leader deals its type; a quicker key for the parties than the spread.
- A played stop flying onto its task, or lighting it: turned down (decisions §65.8).

## 9. Files a part may need beyond its row
B: the desktop browser tests that press the party switch or read a string or a region this spec moves (the *Parties*
tablist → Parties ⌄ and its spread; a stop's alert edge; *draw a blank one* → *pick its type*):
`test_shell_browser`, `test_map_desktop_browser`, `test_board_browser`, `test_project_desktop_browser`,
`test_own_parties_desktop_browser`, `test_party_price_desktop_browser`, `test_party_proposals_desktop_browser`,
`test_recap_desktop_browser`, `test_week_desktop_browser`, `test_races_browser`, `test_check_review_desktop_browser`,
`test_gate_browser`, `test_ops_desktop_browser`, `test_pick_desktop_browser` and any other the full suite names: each
keeps what it proves. C: the phone browser tests that tap the *where* button or read the stage switch's counts
(`test_pwa_shell_browser` — only its helpers `_where`, `_band` and their strings —, `test_board_browser`'s phone half,
`test_pwa_map39_browser`, `test_pwa_board35_browser`, `test_pwa_party_proposals_browser`, `test_pwa_races_browser`,
`test_pwa_ops38_browser`, `test_pwa_pick_browser`, `test_pwa_goal*`). A part that needs any other file: stop and write
it in the spec's *As built* first.

## 10. As built (notes, no change of the contract)
- **A (the host).** Built as §2, with these choices. (1) *Where it lives.* The types, `taker`, `met`, `missing` and two more
  readers are `realm/goal_types.py`: `of_plan` (a plan's `missing` after its roles are given, which `core/idea_keeper.py`
  calls), `still_missing` (a plan's `missing` read against the party now, which `realm/board_map.py` `idea_needs` calls),
  `prompt_line` (the line of both prompts) and `Party` (a party read once: its leader, team and craft, who has work open
  and the week's runs, read when first asked, so the map reads each party once for all its types). The host's half is
  `gui/ideas_types.py` (`TypesMixin`: the type and its asks read, who joins checked and the party changed, `ideas.start`'s
  join, the events' fields), since `gui/ideas.py` would have passed ~600 lines (it is 560). (2) *The asks' ids* are
  `did`, `happened`, `expected` (Fix a bug), `in-the-way`, `avoid`, `shape`, `who`, `where`, `says`, `moves`, `question`,
  `reader`, `for`, `from`, `channel`; `refs` is Refs' links and no ask's id. An answer is one line: its spaces run together
  and cut at both ends, then cut at 300 characters. The lines stand after the text and a blank line, and the person's turn
  in the talk holds the same words. (3) *Refusals the contract had no words for*: an ask the type has not, *<type name>
  has no field “<id>”*; asks with no type, *A goal with no type has no fields of its own*; an `out` that is not of the
  taker's band, *<name> is not one of the party's builders* (checkers); a malformed `asks` or `join`, a line saying what
  they are. (4) *`join` with `night: true`* is left out, not refused: the goal is kept with its type and asks, the party is
  unchanged and `joined` is null, so a closed form's words are never lost. A Low goal from *Add the goal* may bring
  someone. (5) *A swap* puts the agent in the seat of the one who leaves (a free seat: last); the leaver leaves `every`;
  the saved party's id is cleared as any change of a party clears it (`goal_team.set_team`), and a proposal about a checker
  who left goes (`party_proposals.drop_left`), as `ideas.goal_save` does. (6) *§2.7's fields on events written in other
  files* (*Edit the party*'s `goal_saved` in `gui/ideas_goals.py`, `plan_passed` in `gui/ideas_board.py`, the person's
  pass and autostart's) are put by `Ideas._ev`, the one writer of the Board's events (`TypesMixin.type_fields`), so those
  files are unchanged. `plan_passed`'s `missing` is the plan's `missing` read against the party at the press, before a
  join: *Add and start* says `joined: "artist", missing: 1`, *Start without* `joined: "", missing: 1`, autostart's pass
  reads it then. `idea_added`'s `chars` stays the person's text alone; its `asks` counts the type's asks answered (Refs'
  links are not one); its `refs` counts the goal's photos when its type has Refs (the form's pictures are Refs'). (7)
  *"`ideas.plan` answers the same"* is read as `ideas.page`'s `plan` (the drawer's plan screen): its `missing` is the
  row's, read now; `ideas.plan` itself only starts a re-plan. (8) *A task open* is one not merged, not `dropped`, not
  failed as *dropped by you* (core/idea_review.py's drop) and of a goal not done (a failure waits: its member stays);
  whose it is: `roles.task_slug` (its role, else its kind's). (9) *`ideas.start` with `join`* checks the runner before the
  party changes; the tasks given their role again are those `waiting`, `ready` or `held`, by the team then the leader as
  `plan_one` gives them; the plan's own `missing` is kept as it was made (the row reads it now). (10) *The prompt line*
  with no `plan` is `Its type: <name>.`, right after the photos' and the lens' lines. A goal type's key is the leader's at
  the time (`<leader>/<id>`); `get` reads a library leader with no set of its own in the general set, any other unknown
  key as none. The map's `types` follow `goal_team.leader_of`, as `ideas.add` checks them. (11) *Tests*: the signs' test
  takes A0's eleven by name until orkUI 0.3.3's copy is in `design-system/orkui/signs/` (`tests/test_goal_types.py`
  `A0_SIGNS`). **Beyond A's row** (§9): `tests/test_idea_element.py`'s set of `ideas.add`'s answer gains `type` and
  `joined`.
