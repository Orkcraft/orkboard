# Spec 56 — Fantasy signs: each goal type its own sign, drawn as a thing of the realm; orkUI keeps a library of them

The owner, 22 October (decisions §69). The goal types' signs (spec 52 §1) are office marks: a star, a display, bars. The
look's world is orks and their camp, and a type's sign now stands on every card, top right, in its goal's colour (spec 55),
so it is the most seen picture after the heads. So: **every goal type gets its own sign, drawn as a thing of the realm**
(a scroll, a potion, a war horn, a rune), **never a being** (a head says who works; a thing says what the work is), on the
same 7 × 7 grid. Many are drawn, **the owner picks**, and what is drawn beyond the types stays in orkUI as a library for
what comes next. **Builds:** Claude (candidates: Haiku) · **Review:** the owner's pick, then full · P2.

**What it is, and is not:** new pictures for the types and five new sign names; no new meaning, no new colour, no new
place on a face (spec 55's places stay), no element changed (the five stay as they are). No new command, setting or
storage. A type is still told by its sign, never a colour (§65.4); the sign still wears its goal's colour (§68).

Four parts, in this order: **G** (no file of the product), then **the owner's pick** (§3), then **A0** (orkUI's repository),
then **B** (the copy and the five new names here).

| part | builds | files (and their tests) |
|---|---|---|
| **G. Candidates** | §2 | new `docs/specs/56-signs/`: `candidates.json`, `sheet.py` (stdlib only: checks the grids, writes `sheet.html`), `sheet.html` |
| **A0. orkUI** (repository orkWorks/orkUI) | §4 | `office/signs/` (the eleven type signs' pixels redrawn, five new signs and their `.ork-sign` classes, the README), new `office/emblems/` (every picked drawing, `emblems.json`, a README), the gallery's *Signs* and new *Emblems* sections, `CHANGELOG.md` (**0.4.0**), the versions (`pyproject.toml`, `tokens.json`, `tokens.css`'s header); `tests/test_orkui.py`. Then, in orkBoard, the copy: `python -m orkboard.design.orkui <orkUI>` (only `design-system/orkui/` changes) |
| **B. orkBoard** | §5 | `realm/goal_types.py` (`SIGNS` and five types' `sign`), `pwa/sw.js` (`SHELL` gains the five, `CACHE` one up), `tests/test_pwa.py` (the masks' count and names, the pin), `tests/test_goal_types.py` (`A0_SIGNS`), the phone tests that pin the cache's version |

## 0. The words
- Nothing new in what a person reads: a type is still said by its name (*Fix a bug*); a sign is `aria-hidden` with the
  type's name as its title.
- **emblem** (this spec's and orkUI's word, never the interface's): a 7 × 7 drawing in orkUI's library (`office/emblems/`)
  that no face draws until it is made a sign.

## 1. The rules of a drawing
1. **A thing, never a being**: a tool, a vessel, a weapon, a scroll, a stone, a building's part. No head, no creature, no
   eye, no skull. (The `bug` stays an insect: it is the work's own word.)
2. **7 × 7 unit squares**, `.` and `#`, as spec 52 §1's tables; drawn at 14 px (2 px a cell) and 28 px (4 px a cell).
3. **Its silhouette says it at 14 px**: at most one empty row and one empty column at an edge; no lone pixel that is not
   part of the shape's outline or a deliberate spark.
4. **It takes no meaning that is taken**: not a flag or banner (`flag`, a goal in main), not a cross or crossed bones
   (`cross`, a failure), not an hourglass or clock (`night`), not `!` (`alert`), not a turning arrow (`work`), not ✓
   (`check`), not a moon (the `void` element), not a coin (money: Spend), not a chevron, ×, + (orkUI's icons).
5. **It differs from every other sign** by at least **8 cells** (of 49), and from the signs that share a face with it
   (the element marks, the state signs) by as much.
6. One drawing, one meaning: two types never share a sign (reverses spec 52 §1's shared `tidy`, `flask`, `horn`, `page`).

## 2. Candidates (G)
1. **`candidates.json`**: `[{"name", "for", "meaning", "grid"}]`, `name` a slug (`scroll`, `war-horn`), `for` the type
   id it is drawn for (§2.2) or `""` for the library, `meaning` one line, `grid` seven strings of seven `.`/`#`.
2. **At least three for each of the sixteen type ids** (spec 52 §2.1): `feature`, `bug`, `tidy`, `restructure`,
   `screen`, `icon`, `logo`, `pain`, `experiment`, `launch`, `metric`, `report`, `abtest`, `landing`, `post`,
   `tagline` (≥ 48), and **at least twelve for the library** (`for: ""`): things orkUI's faces are likely to need (a
   key, a chest, a map, a shield, a torch, a lantern, an anvil, a gate, a tower, a crown, a coin for money, a bell),
   ≥ 60 in all. What a type says decides its thing; a few to start from (not binding):

   | type id | says | things |
   |---|---|---|
   | `feature` | something people can do that they could not | a rune, a wand's spark, a key |
   | `bug` | something that goes wrong | a beetle, a scarab |
   | `tidy` | the same behaviour in simpler code | a broom, a whetstone |
   | `restructure` | modules split or moved | an anvil, building blocks, a split stone |
   | `screen` | a screen | a magic mirror, a crystal ball, an arched window |
   | `icon` | a picture or an icon | a gem, a ring, an amulet |
   | `logo` | a mark for the product | a shield with a device, a seal, a crown |
   | `pain` | a pain of someone's | an arrow in a target, a thorn |
   | `experiment` | a change shown to some, measured | a potion, a cauldron |
   | `launch` | the words people read when it ships | a war horn, a bell |
   | `metric` | a number counted from events | an abacus, a tally stone |
   | `report` | numbers that answer a question | a scroll, a tome |
   | `abtest` | two versions, one decided by a number | two potions, scales |
   | `landing` | a page that says the product | a signpost, a gate |
   | `post` | a post for one channel | a raven's letter (a sealed letter), a messenger's bell |
   | `tagline` | one line that says the product | a quill |

3. **`sheet.py`** (`python docs/specs/56-signs/sheet.py`): fails, naming the candidate, on a grid that is not 7 × 7 of
   `.`/`#`, a duplicate name, a `for` that is no type id, fewer than §2.2's counts, a candidate within 8 cells of a
   reserved sign (§1.4's: `check`, `cross`, `work`, `night`, `alert`, `flag`, `before`, `after`, `play`, `pause`,
   `sound`, `film`, `text`, and the five elements, read from `design-system/orkui/`) or of another candidate for another
   type; else writes **`sheet.html`**: a self-contained page on orkUI's dark surface, a row per type id (the current
   sign first, then its candidates), each drawing at 14 px and 28 px, in ink, in muted ink and in the five elements'
   colours (spec 55: a type wears its goal's colour), its name and meaning under it, then the library's; at the foot the
   reserved signs at 14 px for comparison.
4. G changes no file of the product; the sheet is the owner's to look at.

## 3. The owner's pick
The owner picks, from the sheet, **one for each of the sixteen types** and **the library** (four spares the types may
take later, and any other worth keeping: at least twenty in all), and may ask for another round of a row. The pick is
written in §6 (*Picked*) as spec 52 §1's tables (the name, then the seven rows), with each type's sign name: the eleven
of today keep their names (`feature`, `bug`, `tidy`, `screen`, `picture`, `logo`, `target`, `flask`, `horn`, `chart`,
`page`), five are new: **`restructure`**, **`abtest`**, **`landing`**, **`post`**, **`tagline`** (`text` stays the media
tile of spec 51). A0 and B build what §6 says.

## 4. orkUI (A0)
1. `office/signs/`: the eleven type signs' pixels as picked (their names, files and classes kept); five new signs as
   spec 50 §1.6 (`<name>.svg`, `viewBox="0 0 7 7"`, one `path` of unit squares, `.ork-sign.<name>`), the README's table
   of the goal types' marks: one line each.
2. **`office/emblems/`**: every picked drawing (the sixteen too) as `<name>.svg` in the signs' format, **`emblems.json`**
   (`[{"name", "meaning", "tags", "sign"}]`, `sign` the sign's name when a face draws it, else `""`) and a README: an
   emblem is not a mask of `components.css` and no face draws it; a face that needs one asks orkUI to make it a sign.
   (orkBoard's copy carries the folder; neither face serves it: `gui/pwa.py` serves `signs/`, not `emblems/`.)
3. The gallery: *Signs* shows the five new; a new *Emblems* section shows every emblem at 14 and 28 px in ink and muted.
4. `tests/test_orkui.py`: the sixteen type signs' pixels as §6's tables; every emblem's file in the format; `emblems.json`
   names every file and nothing else; an emblem with a `sign` has that sign's pixels; the gallery shows each.
5. `CHANGELOG.md` **0.4.0** (a new section of the look: minor), the versions.

## 5. orkBoard (B)
1. The copy of orkUI 0.4.0 (`python -m orkboard.design.orkui <orkUI>`).
2. `realm/goal_types.py`: `SIGNS` gains the five; Architect's `restructure` signs `restructure`, Analyst's `abtest`
   `abtest`, Growth's `landing` `landing`, `post` `post`, `tagline` `tagline` (the others keep theirs: a goal keeps its
   type by its key, so every goal made before shows its new sign at once).
3. `pwa/sw.js`: `SHELL` gains `signs/<the five>.svg`; `CACHE` one up. `tests/test_pwa.py`: the masks `34` (five elements,
   twenty-nine signs), the five named, the pin. `tests/test_goal_types.py`: `A0_SIGNS` holds the sixteen.
4. Nothing on a face changes: spec 55's places and colours draw the new pictures.

## 6. Picked
The owner's pick, 22 October: the model's favourites, `metric` and `restructure` drawn again. **The sixteen type signs** (`sign` (emblem); the type ids: feature → `feature`, bug → `bug`, tidy → `tidy`, restructure → `restructure`, screen → `screen`, icon → `picture`, logo → `logo`, pain → `target`, experiment → `flask`, launch → `horn`, metric → `chart`, report → `page`, abtest → `abtest`, landing → `landing`, post → `post`, tagline → `tagline`):

| `feature` (wand) | `bug` (beetle) | `tidy` (broom) | `restructure` (anvil) | `screen` (mirror) | `picture` (gem) |
|---|---|---|---|---|---|
| `...#...` | `...#...` | `......#` | `.......` | `..###..` | `..###..` |
| `..#.#..` | `..###..` | `.....#.` | `#######` | `.#...#.` | `.#####.` |
| `.#####.` | `#.###.#` | `....#..` | `.######` | `.#...#.` | `#######` |
| `..#.#..` | `.#####.` | `...##..` | `...###.` | `.#...#.` | `.#####.` |
| `...#...` | `#.###.#` | `..###..` | `...###.` | `..###..` | `..###..` |
| `...#...` | `..###..` | `.#####.` | `..#####` | `...#...` | `...#...` |
| `...#...` | `...#...` | `#.#.#..` | `.......` | `..###..` | `.......` |

| `logo` (seal) | `target` (arrow) | `flask` (beaker) | `horn` (bell) | `chart` (menhirs) | `page` (scroll) |
|---|---|---|---|---|---|
| `..###..` | `....###` | `..###..` | `...#...` | `.....##` | `#######` |
| `.#####.` | `.....##` | `...#...` | `..###..` | `.....##` | `.#####.` |
| `##...##` | `....#.#` | `...#...` | `.#####.` | `...#.##` | `..###..` |
| `##.#.##` | `...#...` | `..#.#..` | `.#####.` | `...#.##` | `..###..` |
| `##...##` | `..#....` | `.#...#.` | `.#####.` | `.#.#.##` | `..###..` |
| `.#####.` | `.#.....` | `#.....#` | `#######` | `.#.#.##` | `.#####.` |
| `..###..` | `#......` | `#######` | `...#...` | `#######` | `#######` |

| `abtest` (fork) | `landing` (signpost) | `post` (letter) | `tagline` (quill) |
|---|---|---|---|
| `##...##` | `...#...` | `#######` | `....##.` |
| `.#...#.` | `.#####.` | `##...##` | `...####` |
| `..#.#..` | `.#####.` | `#.#.#.#` | `..###..` |
| `...#...` | `...#...` | `#.....#` | `..##...` |
| `...#...` | `.#####.` | `#.....#` | `.##....` |
| `...#...` | `.#####.` | `#######` | `##.....` |
| `...#...` | `...#...` | `.......` | `#......` |

**The library** (emblems no face draws; twelve, with the sixteen above twenty-eight in all; the four spares for the types first: `chalice`, `hut`, `tome`, `hammer`):

| chalice | hut | tome | ring | scarab | hammer |
|---|---|---|---|---|---|
| `#.....#` | `...#...` | `#######` | `...#...` | `..###..` | `.##....` |
| `#.....#` | `..###..` | `#.#...#` | `..###..` | `.##.##.` | `####...` |
| `.#####.` | `.#####.` | `#.#.#.#` | `.#...#.` | `#######` | `.####..` |
| `..###..` | `#######` | `#.#...#` | `#.....#` | `#.###.#` | `....#..` |
| `...#...` | `.#...#.` | `#.#.#.#` | `#.....#` | `#######` | `.....#.` |
| `...#...` | `.#.#.#.` | `#.#...#` | `.#...#.` | `.##.##.` | `......#` |
| `..###..` | `.#.#.#.` | `#######` | `..###..` | `..###..` | `.......` |

| key | chest | shield | torch | crown | cairn |
|---|---|---|---|---|---|
| `###....` | `..###..` | `#######` | `..###..` | `#.#.#.#` | `...#...` |
| `#.#....` | `.#####.` | `#.....#` | `.#####.` | `#######` | `..###..` |
| `###....` | `#######` | `#.###.#` | `..###..` | `#######` | `..#.#..` |
| `...#...` | `#.....#` | `#.###.#` | `...#...` | `#.....#` | `.#####.` |
| `....#..` | `#..#..#` | `##.#.##` | `...#...` | `#.....#` | `.#.#.#.` |
| `.....##` | `#.....#` | `.##.##.` | `...#...` | `#######` | `#######` |
| `......#` | `#######` | `...#...` | `...#...` | `.......` | `#.#.#.#` |

Each emblem's meaning is its line in `docs/specs/56-signs/candidates.json`.

## 7. Tests
- **G**: `sheet.py` passes on `candidates.json` and fails on a broken one (a 6-row grid, a reserved shape).
- **A0**: §4.4.
- **B**: `tests/test_goal_types.py` (every type's sign one of orkUI's, no two types of one set sharing one, now no two
  types at all), `tests/test_pwa.py`, `tests/test_design_system.py` (the copy as stamped), the critical tests
  (`orkcraft.toml` `always`), `tests/test_type_top_right_browser.py` and `tests/test_type_top_right_desktop_browser.py`.

## 8. Not in this spec
- Beings of any kind as signs (decisions §69: a head says who works).
- The elements, the state signs, the media tiles: unchanged.
- A person's own sign for a goal; signs for Operations' templates.
- A second, larger grid (12 × 12) for the emblems: when a face needs one.

## 9. As built

**A0 and B** (22 October). Built to §4, §5 and §6 as written.
- **A0**: orkUI **0.4.0**, commit `b6bc7a5` (orkWorks/orkUI `main`; its own short spec `docs/specs/0.4.0-fantasy-signs.md`). The eleven type signs are redrawn to §6
  (names, files, classes kept), `restructure`, `abtest`, `landing`, `post`, `tagline` are new (29 signs); `office/emblems/` holds the 28 drawings, `emblems.json`
  (`sign` is the sign's name for the sixteen, `""` for the twelve; `meaning` is the line of `candidates.json`, `tags` the words of its first clause and the type id) and a
  README; the gallery's *Signs* shows the five and a new *Emblems* section draws every emblem at 14 and 28 px in ink and muted by a mask of the gallery's own
  (`.emb`, not a class of `components.css`). orkUI's 207 tests pass.
- **B**: the copy (`python -m orkboard.design.orkui`; `ORKUI.json` stamps 0.4.0 and `b6bc7a5`; only `design-system/orkui/` changed, with `emblems/` in it).
  `realm/goal_types.py`: `SIGNS` gains the five and Architect's `restructure`, Analyst's `abtest`, Growth's `landing`, `post`, `tagline` sign their own names.
  `pwa/sw.js`: `SHELL` gains the five, `CACHE` **`orkcraft-app-v65`** (main had v64, from specs 57 C and 58 C), pinned in `tests/test_pwa.py` and the four browser
  tests that pinned v64. `tests/test_pwa.py`: 34 masks, the five named. `tests/test_goal_types.py`: `A0_SIGNS` holds the sixteen; a new test says one type id has one sign and
  no two ids share one. Neither face serves `emblems/`; nothing on a face changed.
