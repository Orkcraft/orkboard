# Spec 70 — The Orkmaster and the project's level: the parties as columns, their goals as decks; the Orkmaster deals the parties and a goal's party

The owner, 24 October (decisions §85): *one Orkmaster on the project; pressing it, the field shows one level more: the
goals in the parties' columns; creating or picking a party goes through it.* The Board has a party, its goals and their
tasks; a goal's route (spec 68) crosses parties and is seen only from inside one goal. So: **the Orkmaster**, the
project's ork, stands in the project's line; **a press shows the project's level** (the parties as columns, their goals
as decks, their routes as links); **its deck is New party** (the parties the project lacks first); **a goal written on
that level gets its party from it** (by its type and the parties' teams). No model in this spec (the coordination is
spec 71, decisions §86). **Builds:** Claude · **Review:** full · P1.

**What it is, and is not:** one block in `ideas.map`'s answer, one command, one face on each side. Not: a model call; a
goal moved by the Orkmaster; a party made without the person's press; switching party through the project's level
(§84's heading stays the one press); a role file for the Orkmaster (spec 71 decides it).

Three parts, **built at once, in parallel**: B and C build against their tests' stub hosts with the shapes of §1, and
are merged after A. **This file is the contract**; the rest is the builder's choice inside its files. **Change nothing
outside a part's files** but those §7 names. A, B and C share no file.

| part | builds | files (and their tests) |
|---|---|---|
| **A. Host** | §1 | new `realm/orkmaster.py` (the Orkmaster, the deal, a goal's party), `gui/ideas_map.py` (`project` in `ideas.map`), `gui/ideas_release.py` (`ideas.shown` takes `@project`), a new `gui/ideas_project.py` mixin (`ideas.party_for`) registered as the others are in `gui/ideas.py`, `realm/lexicon.py`; new `tests/test_orkmaster.py`, `tests/test_lexicon.py`, `tests/test_gui_ideas.py` (the command list), `tests/test_releases.py` (`@project` shown) |
| **B. Desktop** | §2, §3, §4 on the desktop | `js/arena/partylist.js` (the Orkmaster in the project's line; the line open), new `js/arena/project.js` (the project's level on the field), new `js/arena/projectwords.js`, `js/arena/arena.js` (`@project` shown), `js/board/store.js` (`PROJECT = "@project"` beside `OPS`), `js/arena/goaltabs.js` (`shownOf` keeps `@project`), `js/shell/goalwizard.js` (the tiles in the deal's order with their why), `js/shell/ideadialog.js` (New goal on the project's level: its party suggested), `js/arena/arena.css`; new `tests/test_project_desktop_browser.py` (or `test_orkmaster_desktop_browser.py` if the first name is taken), and the desktop tests that count the column's headings or New party's tiles' order |
| **C. Phone** | §2, §3, §4 on the phone | `pwa/shell-where.js` (*The project* at the parties' sheet's top), new `pwa/shell-project.js` (the project's sheet), `pwa/shell-goal-new.js` (the tiles in the deal's order), `pwa/shell-ideas.js` (New goal from the project's sheet: its party suggested), `pwa/board.js` (only to wire it), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up, `shell-project.js` in `SHELL`) with `tests/test_pwa.py`'s pin and the phone tests that pin it; new `tests/test_pwa_project_browser.py` |

## 0. The words
`TERMS` gains `orkmaster` (*Orkmaster*: the project's ork: it deals the parties and a goal's party, spec 70; it plans
nothing) and `project_level` (*The project*: the project's level, its parties as columns). New strings: *The project*,
*Orkmaster*, *The parties, their goals*, *Open <party>*, *New party*, *n flags wait and no party releases them*
(*1 flag waits …*), *No party judges small ideas yet*, *You have one*, *New goal*, *Its party*, *Orkmaster suggests
<party>*, *takes it whole*, *needs <agent>*, *no one there does it*, *Any party*, *Nothing in <party> yet*, *Planning*,
*At work*, *Waits for main*, *Flags (n)*. A deck is a goal; *deck*, *card*, *spread* stay out of what a person reads.

## 1. The host (A)
1. **`ideas.map`'s answer gains `project`**:
   ```
   "project": {
     "orkmaster": {"id": "orkmaster", "name": "Orkmaster", "race": "peon", "tier": "elder"},
     "deal": [{"id": "release", "why": "flags_wait", "n": 3}, {"id": "ideation", "why": "no_pitches", "n": 0},
              {"id": "game", "why": "", "n": 0}, …, {"id": "mixed", "why": "", "n": 0}]
   }
   ```
   `deal` is every preset of `library.presets()` once, in this order: **Release** first with `why: "flags_wait"` when the
   project has no party the Release manager leads and `n` > 0 goals of its parties (Ideation's left out) have a flag;
   **Ideation** next with `why: "no_pitches"` when no party the Investor leads; then every other preset in the library's
   order, `why: ""`; **last**, Release and Ideation when the project has one, `why: "have"`. `n` is the flags' count
   for `flags_wait`, else 0. `realm/orkmaster.py` `deal(root, state_dir)`; `ORKMASTER` the dict above.
2. **`ideas.party_for {type?}`** (`realm/orkmaster.py` `party_for(state_dir, root, type_id)`): the project's parties but
   General, in the Board's order, each `{"party": slug, "name": title, "fits": …, "missing": [{"agent", "name"}]}`:
   - with a `type` (a catalog id, `goal_types.get`): `fits: "whole"` the parties `goal_types.offered` offers it with
     nothing missing, then `"missing"` those that offer it with someone missing (`missing` their rows' agent and name),
     then `"none"` the rest; Ideation's party is always `"none"` for a type;
   - with none: every party `fits: ""`, Ideation's last with `fits: "pitch"`.
   The first `whole` (else the first `missing`, else the first) is `suggested: <slug>` beside `parties` in the answer.
   An unknown `type`: refused, *No goal type 'x'*. No write, no model.
3. **`ideas.shown {party: "@project", from}`** is taken as a party's switch (`party_shown`, `to: "@project"`), and from
   `@project` to a party as well.
4. `tests/test_orkmaster.py`: the deal with no parties (Ideation, then the library's, Release not first: no flags);
   flags and no Release party (Release first, `n`); a Release and an Ideation party (both last, `have`); `party_for` of
   *New logo* with a party that has an Artist (`whole` first, suggested), one that misses one (`missing` with the agent),
   Ideation `none`; without a type (Ideation last, `pitch`); an unknown type refused; `ideas.map` carries `project`;
   `ideas.shown` to and from `@project`.

## 2. The Orkmaster and the project's level (B, C)
1. **The Orkmaster's place** (B): in the left column's project line (spec 69 §1.1), at its left: the Orkmaster's head
   (orkUI's `Head`, `peon`, `elder`, 24 × 22), a button titled *The project* (`aria-pressed` while the project's level is
   shown), then the project switcher as today. A press shows the project's level (`track` `@project`, kept per device as
   a party is); every party heading is then closed and the project line marked as the open heading is. (C): at the top
   of the parties' sheet, a row: the Orkmaster's head, *The project*, *The parties, their goals*; a tap opens the
   project's sheet.
2. **The project's level** (B, the field in place of the party's members): one column per party in the Board's order,
   Operations not among them. A column's head: its leader's head, its name (two lines), *k/n*; a press on it **opens
   that party** (title *Open <party>*). Under it its goals as **decks**: a deck is 132 × 72 at most, a goal's element
   (`.ork-elem`), its type's sign in its goal's colour, its title (two lines), its state's words as the party's goal row
   says them; grouped *Planning*, *At work*, *Waits for main*, then *Flags (n)* folded (a press unfolds). A press on a
   deck opens the goal's screen (the drawer, as a goal row's ›). Empty: *Nothing in <party> yet*. Wider than the field:
   the columns scroll sideways, the heads stay (sticky).
3. **The routes as links** (B): hovering or focusing a deck draws, with `arrows.js`, a link to each deck its route names
   in another column (the pitch it came from, the release it went into: `node.route`'s `pitch` and `release` steps);
   nothing else is drawn on hover, nothing at rest.
4. **The phone's project sheet** (C): a full sheet, *The project* its title; a section per party: its leader's head, its
   name, *k/n*, *Open <party>* (a tap switches the board to it and closes the sheet); under it its goals as rows (the
   element, the type's sign, the title, the state's words), *Planning* and *At work* first, *Waits for main* and *Flags (n)*
   folded; a row's tap opens the goal's screen. No sideways scroll at 390 px. The routes are not drawn (the goal's screen
   has its route line, spec 68).

## 3. The Orkmaster's deck: New party (B, C)
1. On the project's level the Orkmaster's head (B: in the project line; C: at the project sheet's top) is also a pile:
   a press beside it, **New party** (B: a small pile under the field's head at its left; C: a button *New party* at the
   sheet's top), deals the presets as cards in `project.deal`'s order (B: `spread.js` `Dealt`, as New goal deals types;
   C: a horizontal strip of tiles, as New party's library), each card its name, its heads, its line, and its why:
   `flags_wait` *n flags wait and no party releases them*, `no_pitches` *No party judges small ideas yet*, `have` *You
   have one* (muted); a press opens New party with that preset picked (as its tile's press does today).
2. **New party's tiles follow the deal** (B `goalwizard.js`, C `shell-goal-new.js`): the mixed and the craft groups
   keep their headings; inside each, the deal's order; a tile with a why says it under its line. An older host with no
   `project`: today's order.
3. *+ New party* at the column's foot (spec 69) stays and opens New party as today.

## 4. A goal's party from the Orkmaster (B, C)
1. On the project's level: **New goal** (B: a pile at the field's foot, as a party's; C: a button at the project sheet's
   foot) opens New goal **without a party**: its type (*Your own goal* first, then every type of the catalog the
   project's parties are offered: the union of the map's parties' `types`), its text and asks as today, and **Its party**:
   asked with `ideas.party_for` (again when the type changes): the suggested party picked, a line *Orkmaster suggests
   <party>* with its fit (*takes it whole*, *needs <agent>*, *no one there does it*), and the other parties to pick
   (chips; C: a select-like list). *Add the goal* adds it to the party picked (`ideas.add` as today, its `track`). With
   the join line of spec 52 as today when the picked party misses someone.
2. Without a type: *Any party*, the parties as `party_for` answers them (Ideation last: a pitch there).
3. A party's own New goal is unchanged.

## 5. Tests
- **A**: §1.4.
- **B** (browser, 1 440 × 900, stub host): the Orkmaster's head in the project line, its press shows the project's
  level (`aria-pressed`, no party heading open, the line marked); three parties' columns with their decks in groups and
  Flags folded; a column's press opens that party; a deck's press opens its goal; hovering a sent goal's deck draws a
  link to its pitch's deck in Ideation's column; the deal: Release first with *3 flags wait and no party releases them*,
  then Ideation, a press opens New party with Release picked; New party's tiles in the deal's order with the why; New goal
  on the level: *New logo* picks the party with an Artist, *Orkmaster suggests …* · *takes it whole*, another chip picked,
  *Add the goal* sends `ideas.add` with that `track`; `ideas.shown` to `@project`; an older host (no `project`): no head,
  today's tiles.
- **C** (390 × 844): *The project* at the parties' sheet's top; the project's sheet with sections and rows, *Open <party>*
  switches; the deal's strip; New goal with its party suggested; no sideways scroll; the service worker's version.
- Each part: the critical tests (CLAUDE.md "Alpha"), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`; C also `tests/test_pwa.py`.

## 6. Measured
`party_shown` with `to: "@project"` (A §1.3): how often the project's level is opened, and from where. No new event.

## 7. Outside the parts' files
`docs/decisions.md` §85 and this file are the contract.

## As built (B)
Part B, on the desktop only; no host, phone or Python file.
- **`board/store.js`** `PROJECT = "@project"` beside `OPS`; **`goaltabs.js`** `shownOf` keeps it (only when `ideas.map` carries `project`: `projectOn()`) and falls back to the kept one, which may be the project, as a party is; **`arena.js`** draws `ProjectField` in place of the party when it is shown, as Operations' field.
- **`partylist.js`**: `show()` exported; the project line gains `.arena-ork` (orkUI `Head` of `project.orkmaster`, `aria-pressed`, title and label *The project*) before the switcher; while the level is shown every heading is closed and the line has `.is-open`. A press says `ideas.shown` (to and from `@project`, fire and forget).
- **`project.js`** (new): the level. `.arena-pjtop` (head, *The project*, *The parties, their goals*), the New party pile, `.arena-project__body` (scrolls both ways) with a `.arena-pcol` per party (sticky `.arena-pcol__head`: head, name, *k/n*, *Open <party>*), `.arena-deck`s (132 × 72) in `.arena-pgroup`s *Planning*, *At work*, *Waits for main*, then *Flags (n)* folded; *Nothing in <party> yet*; the New goal pile. Links on hover or focus: `projectwords.js` `linksOf` (the `pitch` and `release` steps of `node.route`, and a pitch's `goal_state`), drawn with `arrows.js`, which now exports `segment` and `ArrowLines`. Ideation's pitches: to judge and being judged are Planning, a sent one is At work, a passed one is not drawn.
- **`projectwords.js`** (new): groups, links, the deal's why words, the fit words, the union of goal types. **`projectdeal.js`** (new): *New party* (`Dealt` of the deal's cards in `project.deal` order; a card opens New party with that preset) and *New goal* (`TypesSpread` of the union of the parties' types, then New goal on `PROJECT`). **`projectparty.js`** (new): `usePartyFor` (`ideas.party_for`, again when the type changes; an older host gives the Map's parties) and *Its party* (*Orkmaster suggests <party>* · fit, every party a chip; *Any party* without a type).
- **`ideadialog.js`**: with `goal === PROJECT` New goal has no party at first, picks the suggested one, and sends `ideas.add` with the picked `track`; a typed goal's join line is the picked party's own type entry (asked again on a pick); a pitch in Ideation keeps its form.
- **New party's tiles** (`goalwizard.js`, and `LibraryTiles` in `shell/party.js`, one optional `deal` argument, outside the table's list): each group in the deal's order, the why in `.shell-craft-tile__why`; no `project`: as before.
- Tests: `tests/test_project_desktop_browser.py` (17). Known: `test_shell_browser.py::test_a_file_todo_…` fails on main; `test_own_parties_desktop_browser.py::test_edit_the_party_…` and the phone test of `test_board_browser.py` failed once under load and pass alone.
