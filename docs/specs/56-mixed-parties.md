# Spec 56 — Mixed parties: the library's Game, Mobile app and Website first; the leader sets the stages and their seats; the goal types come from the team

The owner, 22 October (decisions §69): *"The parties used most will be mixed ones: a game's, its leader a game designer,
or a mobile app's, a product leader for now, and besides the code ASO and an Artist for the pictures — more often than
a party of pure engineering or pure design."* Spec 52 gave the goal types to the leader, so a party is offered its
leader's set whoever is in it (a mobile app's party led by the Product manager deals *Solve a pain* and never a store
listing), and every party has the same seats (one leader, three builders, two checkers), so a game's party (code, art,
levels, sound) does not fit. So: **the library gives mixed parties first** with the agents they need; **the leader sets
its stages' words and seats**, six at most with it; **a party's goal types are those its team can do**, from one catalog,
and those it misses one agent for. **Builds:** Claude · **Review:** full · P1.

**What it is, and is not:** new agents, kinds and parties in the library; a leader's stages; the goal types read from the
team. **Storage keeps its shape** (Orkline reads the same Board, CLAUDE.md): a party is its `leader`, `team` and
`team_every` as today (a member's stage is its band, as today); a goal's `type` is one key, now the catalog's id; the
person's own parties (`parties.json`) gain one optional key, `preset`. No new setting, no new command. **Not in it**: a
type's own steps (a skeleton its plan must keep: decisions §69, after the numbers), a stage that is not one of the three
bands, more than one stage of a band, a person's own goal types or stages.

Four parts. **A0 and A first, at once** (A0 is orkUI's repository, A touches no file of the page); **B and C from both**
once they are in (they touch no file of each other's). **This file is the contract**; the rest is the builder's choice
inside its files. **Change nothing outside a part's files** but those §9 names.

| part | builds | files (and their tests) |
|---|---|---|
| **A0. orkUI** (repository orkWorks/orkUI) | §1 | `office/signs/` gains five signs (§1) and their `.ork-sign` classes, the gallery's *Signs* section, the signs' README, `CHANGELOG.md` (**0.3.4**), the versions; `tests/test_orkui.py`. Then, in orkBoard, the copy: `python -m orkboard.design.orkui <orkUI>` (only `design-system/orkui/`, and `pwa/sw.js`'s `SHELL` and `CACHE` with `tests/test_pwa.py`'s count and pin, as spec 52 §10's A0 note) |
| **A. Backend** | §2–§5 | `realm/roles.py` (five kinds), `realm/library.py` (five agents, `STAGES`, `stages_of`, `seats_of`, `PRESETS`, `parties()`), `realm/goal_team.py` (`seats` by the leader's stages), `realm/goal_types.py` (the catalog, `offered`, `get` with the old keys, `missing` by the leader's seats), `realm/own_parties.py` (`preset`), `gui/ideas_roles.py` (`stages`, `presets`), `gui/ideas_map.py` (a party's `types` from `offered`; a party's `stages`), `gui/ideas_types.py` (`type` checked against `offered`, kept by its id), `gui/ideas_goals.py` (`goal_save`'s `preset`), `realm/event_log.py` (§5), `realm/lexicon.py` (`goal_type`'s line; `stage`'s line); `tests/test_goal_types.py`, `tests/test_library.py`, `tests/test_goal_team.py`, `tests/test_own_parties.py`, `tests/test_gui_ideas.py`, `tests/test_gui_roles.py`, `tests/test_event_log.py`, `tests/test_lexicon.py`, `tests/test_roles.py` |
| **B. Desktop** | §6, §8 | `js/shell/goalwizard.js` and `js/shell/party.js` (the library's parties, mixed first; the seats by the leader; the bands' words), `js/arena/field.js`, `js/arena/arenawords.js`, `js/arena/members.js` (a stage's word and seats from the party), `js/arena/arena.css`, `js/shell/shell.css`; `tests/test_shell_browser.py`'s New party helpers, new `tests/test_mixed_parties_desktop_browser.py` |
| **C. Phone** | §7, §8 | `pwa/shell-goal-new.js` (the library's parties, mixed first; the seats by the leader), `pwa/shell-party.js`, `pwa/shell-arena-words.js` (`BANDS`' words from the party), `pwa/shell-arena.js`, `pwa/shell-arena-field.js`, `pwa/shell-map-idea.js` (`STAGES`' words), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_mixed_parties_browser.py` |

## 0. The words
- **stage** (`TERMS` `stage`): a party's step a goal goes through, one per band: the leader's (*Planning*), the builders'
  (*Implementation*), the checkers' (*Checking*); **its leader words them** (a Game designer: *Concept*, *Build*,
  *Playtest*). Its line in `TERMS` says so.
- **goal type** (`TERMS` `goal_type`): its line becomes *what kind of goal a party's team can take on: New logo, Fix a
  bug; realm/goal_types.py, specs 52 and 56*.
- New strings, in these words: the agents' names and lines (§2.2), the kinds' labels (§2.1), the parties' names and lines
  (§2.4), the stages' words (§3), the new types' names, lines and asks (§4.2), *Mixed*, *One craft*, *<stage> has <n>
  seats with <leader>: take one out first.*, *A party led by <leader> has at most <n> <builders | checkers>*.
- spec 50 §0's rules hold: the interface says *party*, *goal*, *task*; no *preset*, *catalog*, *band*, *deck* in what a
  person reads (they are the code's words).

## 1. orkUI: five signs (A0)
As spec 52 §1 (`office/signs/<name>.svg`, 7 × 7, one `path`, `.ork-sign.<name>`, 14 × 14 and `.big` 28 × 28):

| dice | maze | store | box | scales |
|---|---|---|---|---|
| `#######` | `#######` | `..###..` | `.#####.` | `...#...` |
| `#.....#` | `#...#.#` | `.#...#.` | `#..#..#` | `#######` |
| `#.#.#.#` | `#.#.#.#` | `#######` | `#######` | `#..#..#` |
| `#.....#` | `#.#...#` | `#.....#` | `#..#..#` | `#..#..#` |
| `#.#.#.#` | `#.#####` | `#.#.#.#` | `#..#..#` | `##.#.##` |
| `#.....#` | `#.....#` | `#.....#` | `#..#..#` | `...#...` |
| `#######` | `#######` | `#######` | `#######` | `.#####.` |

*dice* a game's rule or mechanic, *maze* a level, *store* a store's page, *box* a release, *scales* a balance of numbers.
The README's lines, the gallery, the CHANGELOG (**0.3.4**), the versions; tests as spec 52 §1.

## 2. The library (A)
### 2.1 Five kinds (`realm/roles.py`)
`TASK_KINDS` gains, after `edit`, with their `KIND_LABELS` and `KIND_LINES`:

| kind | label | line (for the plan prompt) |
|---|---|---|
| `gamedesign` | Game design | the rules, the loop and the balance of a game |
| `level` | Levels | a level: its layout, its path and its pace |
| `sound` | Sound | sounds and music, picked by ear |
| `playtest` | Playtest | playing a change through and saying where it breaks or bores |
| `aso` | Store pages (ASO) | an app store's page: its keywords, texts and screenshots |

(A kind in a sentence, spec 52 §0: *game design*, *levels*, *sound*, *playtest*, *store pages (ASO)*.)

### 2.2 Five agents (`realm/library.py` `LIBRARY`)
In the library's order: the Game designer after the Product designer, the Level designer, the Sound designer and the
Playtester after the Artist, ASO after SEO. Each instruction at most 600 characters, in the library's voice (the builder
writes them; these say what each holds to):

| id | name | craft (race) | tier | takes | band | line | its instruction holds it to |
|---|---|---|---|---|---|---|---|
| `game-designer` | Game designer | design (elf) | elder | `gamedesign` | lead | Leads a game party: the rules, the loop, what makes it fun | every goal says what the player does, sees and gets, and why it is fun; the rule before the build; numbers in one balance file; Done when lines a player can check by playing |
| `level-designer` | Level designer | design (elf) | warrior | `level` | build | Lays out the levels: the path, the beats, where it gets hard | the layout on paper first (the path, the beats, the hard part, how long it plays), then built in the game's own format; one new idea a level |
| `sound-designer` | Sound designer | design (elf) | laborer | `sound` | build | Makes the sounds and the music, picked by ear | short, loopable where it loops, one loudness for all; a few to pick from when asked (a pick of sounds, spec 51); the source beside the export, named by what it is |
| `playtester` | Playtester | design (elf) | warrior | `playtest` | check | Plays a change through and says where it breaks or bores | plays the changed part through (the game's test build, or a headless run when it has one); each finding with where, what the player does and what goes wrong; fixes only what is small |
| `aso` | ASO | marketing (gnome) | laborer | `aso` | build | Writes the store pages: keywords, title, texts, screenshots' words | the words people search for in the store first; the title and subtitle within the store's limits; nothing submitted without the person's yes |

The Playtester's `Check`: applies *when the idea changes what a player does, sees or hears*; done *It was played through:
the changed part works and nothing near it broke*; task *Play the idea's change through and write where it breaks, bores
or confuses; fix what is small.*; fits `("design", "engineering")`.

### 2.3 The stages and their seats (`realm/library.py` `STAGES`)
A leader's stages: `Stages(lead, build, check, build_seats, check_seats)`, its three words and the seats of its builders
and checkers. **One leader and five more at most** (`goal_team.SEATS` stays 5): `build_seats + check_seats == 5`,
`build_seats` 2 to 4, `check_seats` 1 to 3.

| leader | lead | build | check | builders | checkers |
|---|---|---|---|---|---|
| (every leader not named here) | Planning | Implementation | Checking | 3 | 2 |
| `game-designer` | Concept | Build | Playtest | 4 | 1 |

- `stages_of(leader) -> Stages` (the default for any leader not in `STAGES`, the Taskmaster's and a person's own too);
  `seats_of(leader) -> {"lead": 1, "build": n, "check": m}`. `library.SEATS` stays the default's, for older faces.
- `goal_team.seats(team, leader)` counts against `seats_of(leader)`; its refusal names the leader: *A party led by
  <leader name> has at most <n> builders* (checkers). A party saved before keeps its seats: every leader of today keeps
  three and two.
- `goal_types.missing`' `free` reads `seats_of(the party's leader)`.

### 2.4 The library's parties (`realm/library.py` `PRESETS`)
`PRESETS`: the parties New party offers, **the mixed first**, each `(id, name, line, craft, lead, build, check)`:

| id | name | line | craft | leader | builders | checkers |
|---|---|---|---|---|---|---|
| `game` | Game | Rules, levels, art and sound, played through | design | `game-designer` | `grunt`, `artist`, `level-designer`, `sound-designer` | `playtester` |
| `mobile-app` | Mobile app | Screens, the store page and the pictures | product | `product-manager` | `grunt`, `artist`, `aso` | `reviewer`, `accessibility-reviewer` |
| `website` | Website | Pages that say what it does, and are found | marketing | `growth` | `grunt`, `copywriter`, `seo` | `reviewer`, `editor` |
| `engineering` … `product`, `mixed` | as today (`PARTIES`) | the craft's line of today | — | | | |

- `PARTIES` stays (by craft, as the faces read it today); `parties()` answers it with the three mixed ones added by their
  ids, so a face that reads `parties[<craft>]` is unchanged.
- `presets() -> [{id, name, line, craft, race, mixed, lead, build, check}]`, `mixed` true for the first three; the crafts'
  in today's order after them, their `name` the craft's label, their line the faces' line of today (*Code, tests and the
  build*, …), `mixed` false; *Mixed* (the Taskmaster alone) last, its name *Taskmaster alone*.
- `ideas.roles` answers `presets` and `stages` (`{leader id: {lead, build, check, seats}}` for every leader of the
  library, and `default`).

## 3. A party's stages on the map (A)
`ideas.map`: a party gains **`stages`**: `{lead: {word}, build: {word, seats}, check: {word, seats}}` by its leader
(`stages_of(goal_team.leader_of(...))`). Operations have none.

## 4. The goal types come from the team (A)
### 4.1 One catalog
`goal_types.CATALOG: tuple[GoalType, ...]`; `GoalType` gains **`over`** (the id of the more general type it stands in
for, or `""`). Every type keeps spec 52 §2.1's fields; its `needs` now say who can take it (every type needs at least one
kind). `TYPES`, `of` and `GENERAL` go.

### 4.2 The catalog
The types of spec 52 §2.1 keep their names, signs, lines, lenses, asks, refs and plans; their ids and needs:

| id | name | needs | over | was (`get` reads it as this) |
|---|---|---|---|---|
| `feature` | New feature | `code` | | `taskmaster/feature` |
| `bug` | Fix a bug | `code` | | `taskmaster/bug`, `architect/bug` |
| `tidy` | Clean up | `code` | | `taskmaster/tidy` |
| `shaped-feature` | New feature | `architecture` | `feature` | `architect/feature` |
| `restructure` | Restructure | `architecture` | | `architect/restructure` |
| `screen` | New screen | `uikit` | | `product-designer/screen` |
| `icon` | New icon | `art` | | `product-designer/icon` |
| `logo` | New logo | `art` | | `product-designer/logo` |
| `flow-feature` | New feature | `uikit` | `feature` | `product-designer/feature` |
| `pain` | Solve a pain | `research` | | `product-manager/pain` |
| `experiment` | Try an experiment | `research`, `experiment` | `abtest` | `product-manager/experiment` |
| `launch` | Write the launch | `research`, `text` | | `product-manager/launch` |
| `metric` | A new metric | `data` | | `analyst/metric` |
| `report` | A report | `query` | | `analyst/report` |
| `abtest` | An A/B test | `metrics`, `experiment` | | `analyst/abtest` |
| `landing` | A landing page | `text`, `seo` | | `growth/landing` |
| `post` | A launch post | `campaign`, `text` | | `growth/post` |
| `tagline` | A tagline | `text` | | `growth/tagline` |

And the new ones (asks as *label* (hint)):

| id | name | sign | line | needs | lens | asks | refs | plan |
|---|---|---|---|---|---|---|---|---|
| `mechanic` | New mechanic | dice | A rule the player plays by, tried before it is built in | `gamedesign` | text | *What the player does* (the verb, in one line) · *Why it is fun* (what they get from it) | no | Write the rule and its loop first (what the player does, sees and gets), then a playable prototype; its numbers in the balance file. |
| `level` | New level | maze | A level laid out, built and played through | `level` | text | *What it teaches* (the one new idea) · *How long it plays* (in minutes) | yes | A Level designer lays it out first (the path, the beats, where it gets hard), then builds it; then it is played through. |
| `character` | New character | picture | A character drawn, picked from a few, then put in the game | `art` | text | *Who it is* (in three words) | yes | An Artist draws four to pick from (a pick of 4 images); the picked one gets its frames and goes in the game. |
| `balance` | Balance pass | scales | The game's numbers changed so it plays better | `gamedesign` | text | *What feels off* (where, and how) | no | Change numbers only, in the balance file; say each change and why; the tests stay green. |
| `sound` | New sound | sound | A sound or a tune, picked by ear | `sound` | text | *Where it plays* (the moment, and how often) | yes | A Sound designer makes three to pick from (a pick of 3 sounds); the picked one is put in place. |
| `store` | Store listing | store | The store's page: keywords, texts, screenshots' words | `aso` | text | *Who it is for* · *The stores* (App Store, Google Play) | yes | Keywords first (what people search for in the store), then the title, subtitle and description, then the screenshots' words; nothing is submitted without the person's yes. |
| `release` | A release | box | A version out: what is new, the build, the stores' list | `aso`, `code` | text | *What is new* (in the person's words) | no | Bump the version, write what is new for the stores in the product's words, make the build, and write the stores' list the person goes through; nothing is submitted without the person's yes. |

### 4.3 What a party offers (`offered`)
**Fewer, and the leader's** (the owner: *better to show fewer goals than to distract the person; neighbouring goals are
another party's*). `offered(state_dir, root, party_slug, *, read=None) -> list[(GoalType, missing)]`, *party* its leader
and team (`Party.members`; a party with no team: its leader alone):
1. **Code is someone's**: a type that needs `code` or `tests` is offered only when a member takes that kind itself (the
   Grunt or the Tester in the team, the Taskmaster leading, an agent of the person's own that takes it). (`met` is
   unchanged: for a plan, the Grunt still fills in for any kind.)
2. A type whose every need is met (rule 1 for `code` and `tests`, `met` for the rest) is **offered**, `missing` `[]`.
3. A type with exactly **one** need not met, that need having a `taker`, is **offered with that one missing** (spec 52
   §2.1's row: `{kind, words, agent, name, band, free, out}`; `free` by the leader's seats) **only when the leader itself
   takes another of its needs** (the leader's `takes`, `code` and `tests` left out): the leader's own work, done with one
   more agent. Work beside the leader's is another party's.
4. Any other is not offered.
5. **One name once**: a type offered with nothing missing hides the type it stands in for (`over`); a type that would be
   offered with someone missing is not offered when the type it stands in for is offered with nothing missing.
6. In the catalog's order (the map then sorts by use, §4.5).

So the library's parties offer (with someone missing: *needs* and who):
- **Game**: New feature, Fix a bug, Clean up, New icon, New logo, New mechanic, New level, New character, Balance pass,
  New sound.
- **Mobile app**: New feature, Fix a bug, Clean up, New icon, New logo, Solve a pain, New character, Store listing, A
  release; *needs*: Try an experiment (Experimenter), Write the launch (Copywriter).
- **Website**: New feature, Fix a bug, Clean up, A landing page, A launch post, A tagline.
- **Engineering**: the Architect's New feature, Fix a bug, Clean up, Restructure. **Design**: New screen, New icon, New
  logo, its New feature. **Data**: A new metric, A report; *needs*: An A/B test (Experimenter). **Marketing**: A landing
  page, A launch post, A tagline. **Product**: New feature, Fix a bug, Clean up, Solve a pain, Write the launch; *needs*:
  Try an experiment (Experimenter). **Taskmaster alone**: New feature, Fix a bug, Clean up.
(`tests/test_goal_types.py` checks these lists; a row that differs when built is a note in §10, not a change.)
- Against spec 52: the parties of design, data and marketing no longer offer New feature, Fix a bug and Clean up (no one
  of them writes code); the Architect's *Fix a bug* opened the `code` lens first, the catalog's opens `text`.

### 4.4 A goal's type
- `ideas.add`'s `type` is the id of one of `offered` for the party; else refused *<party> cannot take “<id>”: no one of
  it does <words>* (a known type) or *No goal type “<id>”* (an unknown id). `join` as spec 52 §2.3, against that type's
  `missing` (one entry at most now).
- The goal keeps the **id** (`state.json` `type`). `get(key)` reads an id of the catalog, and an old key
  `"<leader>/<id>"` as the table's *was* says; anything else as none. (Orkline's frozen copy reads an id without a `/`
  as no type until its copy is updated: the goal works, its sign is not drawn there.)
- `prompt_line` unchanged.

### 4.5 A party's types (`ideas.map`)
A party's `types` (spec 52 §2.4) is `offered`, each with its `missing`; **the most used first** (`used`: the party's goals
with that type, an old key counted as its id), then those with nothing missing before those with someone missing, then
the catalog's order. The rows' shape is unchanged, so the faces draw it as today.

## 5. Measured (A)
- `goal_saved` gains `preset` (the library's party the seats started from, `""` when none or changed after) and
  `stages` (`"<builders>/<checkers>"`, the leader's seats).
- `idea_added`'s `type` is the id; it gains `offered` (how many types the party offered) and `near` (how many of them
  with someone missing).
- The owner reads: the share of new parties by preset, mixed against one craft; the types offered, picked and joined
  for, by preset; how often a party of four builders swaps against one of three.

## 6. The desktop (B)
1. **New party's library** (`js/shell/goalwizard.js`, `js/shell/party.js`): the party's choice lists **the mixed first**
   under *Mixed* (*Game*, *Mobile app*, *Website*: the leader's head, the name, the line, the members' small heads), then
   *One craft* (today's crafts), then *Taskmaster alone*. A pick fills the seats as a craft does today and keeps its id
   (sent as `preset` with `ideas.goal_save`; cleared when a seat changes, as `party` is).
2. **The seats by the leader**: the bands' heads say the leader's stage words (*Concept*, *Build* · *4 seats*,
   *Playtest*) and draw `seats_of(leader)` seats; a leader picked whose stage has fewer seats than the party fills shows
   the band's extra members in the alert colour with *<stage> has <n> seats with <leader>: take one out first.* and
   *Save party* stays off until it fits.
3. **The stages on the board** (`js/arena/field.js`, `arenawords.js`, `members.js`): every *Planning*, *Implementation*,
   *Checking* drawn for a party is its `stages`' word; a party with no `stages` (an older host) says today's words.
4. Nothing else changes: the types' spread reads `types` as today.

## 7. The phone (C)
1. **New party's library** (`pwa/shell-goal-new.js`, `pwa/shell-party.js`): as §6.1, one column; *Mixed* first.
2. **The seats by the leader**: as §6.2 (the folds' heads, the seats, the refusal line; *Save* off until it fits).
3. **The stages** (`pwa/shell-arena-words.js` `BANDS`, `pwa/shell-map-idea.js` `STAGES`, the stage switch): the
   party's `stages`' words; the switch shows up to four builders' heads (24 × 22, each 14 px after the one before: 66 px
   at four) and its words are never cut at 390 px (*Implementation* is the longest word of today's and stays the longest).
4. `sw.js`' `CACHE` one up after A0's, with `tests/test_pwa.py`'s pin. Touch targets 44 px.

## 8. Tests
- **A0**: §1.
- **A**: `tests/test_roles.py` (the five kinds, their labels and lines); `tests/test_library.py` (the five agents, each
  instruction ≤ 600, the Playtester's check, `STAGES`' sums, `stages_of`/`seats_of` for a leader in it and one not,
  `PRESETS`' members known and fitting their leader's seats, `presets()`' order, `parties()` keeps every craft);
  `tests/test_goal_team.py` (`seats` by the leader: four builders with the Game designer, three with the Architect, the
  refusal's words); `tests/test_goal_types.py` (every type needs a known kind; every id unique; every `over` a type of
  the catalog; every old key read; `offered`: code offered only with a member who takes it, all met, one missing with the leader taking another need,
  one missing without (not offered), one missing with no taker, two missing, `over` hiding and not hiding; the three presets' lists of §4.3; `missing`' `free` by the leader's seats);
  `tests/test_gui_ideas.py` (`ideas.add` with an id offered, not offered, unknown, with `join`; a goal of an old key
  mapped; `ideas.map`'s `types` order and `stages`); `tests/test_gui_roles.py` (`presets`, `stages`);
  `tests/test_own_parties.py` (`preset` kept, a file without it read); `tests/test_event_log.py` (§5's fields);
  `tests/test_lexicon.py`.
- **B** (browser, desktop): the library's parties (*Mixed* first, a pick fills the seats and sends `preset`, a seat
  changed clears it); the Game's four builders' seats and *Concept*/*Build*/*Playtest*; a leader with fewer seats (the
  alert line, *Save party* off); the board's stage words for a Game party and today's for another; an older host with no
  `stages`.
- **C** (browser, phone): as B's, at 390 px; four heads on the stage switch; the words not cut; the service worker's
  version.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_architecture.py`.

## 9. Files a part may need beyond its row
A: `core/idea_keeper.py` and `core/idea_draft.py` only if they call `goal_types.of` (they call `prompt_line`, unchanged);
`gui/ideas_board.py` if it reads `library.SEATS`. B: the desktop browser tests that read the bands' words or the craft
list of New party (`test_own_parties_desktop_browser`, `test_party_price_desktop_browser`, `test_goal_types_desktop_browser`).
C: the phone tests that read the stage switch's words or New party's crafts (`test_pwa_arena_browser`,
`test_pwa_goal_types_browser`, `test_pwa_party_proposals_browser`). A part that needs any other file: stop and write it
in *As built* first.

## 10. As built (notes, no change of the contract)
