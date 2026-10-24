# Spec 67 — The hand first: on the phone the field is a board of tokens, the room goes to the hand

The owner, 23 October (decisions §81): *the person will not read the task cards much; what matters on the phone are the
cards in the hand. The target device is an iPhone: use its screen as productively as we can, and no sideways scroll.*
On a 390 × 844 screen today the field takes almost all of it — a task card is 132 × 185 always (spec 50 §6.5, decisions
§63.13), a member's column 148 px, three or more members a sideways strip (the third peeking, the fourth off the
screen) — while the hand is a strip of 56 px whose words are cut (*ASK*, *PRO*) and every answer takes a tap to raise
its card first. Drawn with the owner on the Design canvas *Orkboard — after the cleanup* (row *The hand first*, mockup
B). **Builds:** Claude · **Review:** full · P1.

**What it is, and is not:** the phone's field and the phone's hand, drawn again from what they read today. No new
command, setting or storage; the host's one change is a new `via` value, `front` (`gui/ideas_args.py` `VIA`,
`gui/ideas_pick.py` `PICK_VIA`). The desktop is unchanged, but for the words of what a
task waits for (§3), which both faces share. Not: a swipe through the hand (§6), a change of the hand's order or its
count (none, decisions §67.3), the stage switch, the top bar or the goals bar.

One part.

| part | builds | files (and their tests) |
|---|---|---|
| **C. Phone** | §1–§5 | `pwa/shell-arena-field.js` (the strip: the columns share the width, no sideways scroll), `pwa/shell-decks.js` (a task's token), `pwa/shell-arena-words.js` (a token's value; what a task waits for, by name), `pwa/shell-stops.js` (the hand: the front card, the fan), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; `gui/ideas_args.py`, `gui/ideas_pick.py` (`front`); `js/arena/arenawords.js` and `js/arena/stacks.js` (§3 on the desktop); new `tests/test_pwa_hand_first_browser.py`; the phone and desktop tests that read what this changes (the card's size, the strip, the hand's height, the words *after k1*) |

## 1. The field: every member on the screen
1. **The members share the width.** The strip is the screen's width less 6 px each side, its columns 4 px apart and
   equal (`flex: 1 1 0`); **no sideways scroll** with one to four members (four is a stage's most: decisions §72.2).
   Replaces spec 50 §6.5's 148-px columns, the snap and the third peeking, and decisions §63.13's *the members scroll
   instead*.
2. **A card is a token, 74 px wide, 5:7** (≈ 74 × 104), in every stage. A member's stacks lie in rows that wrap and are
   centred in its column: one to a row with four members, two with two, four in the Planning's one column. A stack's
   edges and ×n stay (spec 50 §3.4), drawn to the token's size.
3. **The column's name** stays over it (11 px); a name longer than the column is cut, its tool mark and chevrons
   (spec 60) are never cut: they go to a second line under the name when the name and they do not fit one.
4. The phases' words (*now*, *next*, *later*) stay where they are; the rows' gaps are 6 px; a column's foot (*✓ 2 in
   dev*) stays.

## 2. A token: what kind of work, which goal, its name, one value
1. **Its top row is unchanged** (decisions §68): the goal's element at the left, its type's sign at the right in the
   element's colour (a goal with no type: the right is empty).
2. **The goal's line goes** on the phone's tokens (reverses spec 55 §3 on the phone; the element and the type say it), in
   every stage: a Planning card's *Goal* or type name goes too (the type's sign says it).
3. **Its name**: the task's (a Planning card: the goal's) `short`, the text face 600, 11 px / 14 px, at most three lines,
   broken between words only (`overflow-wrap: normal`; a word longer than the token is cut with *…*).
4. **One value at its foot**, the text face 600, 11 px, tabular numbers, ink:
   - at work or testing: the time it has run (*42 h*, *7 min*: today's `sinceWords`);
   - held for tonight or for the reserve: the hour it may start (*18:00*);
   - anything else (waiting, ready, failed, in Review, asks you to pick, done): **nothing** — the token's edge and fill
     say it (§2.5).
5. **The edge and the fill say the state**: at work, testing, in Review or asking to pick, the token lies **raised**
   (`--ork-raised`) with today's edge (`--ork-edge`; a pick's alert sign stays); failed, raised with the danger edge;
   waiting, ready or held, dashed on the canvas (today's). The phases' rows below *now* stay muted (decisions §62.1).
6. **Its words are all still said**: the token's `aria-label` and `title` keep today's full words (its goal, its
   state, what it waits for by name, §3); a tap opens what it opens today.

## 3. What a task waits for, by name (both faces)
Today a waiting task says *after k1, k2*: the plan's ids, which the person never sees anywhere else. So:
1. `afterWords` (desktop, `js/arena/arenawords.js`) and its phone twin (`pwa/shell-arena-words.js`) name the tasks by
   their `short` (else `title`): *after Challenge store, Credential table*; *after the build* stays; an id with no task
   found is left out (none left: *waiting*).
2. **The desktop's card foot** says *waits for 2* (one: *waits for Challenge store*), its sign the *before* sign; the
   arrows on hover name them (spec 50 §3.4, unchanged). The tooltip (`cardTip`) and the phone's labels say the names.

## 4. The hand: the most urgent stop stands in front, answered where it stands
1. **The hand's zone is 250 px** (`--tabs`) while one stop or more waits (56 px when none: *Nothing waits for you.*,
   today's). The create button stands over it (it reads `--tabs` today), the news and the raised stop too.
2. **The front card**: the most urgent stop (`byUrgency`'s first, the fan's middle: spec 54 §2) stands **upright in
   front**, 150 × 236, not turned: its gem, its kind, its element, its party's head when another party's (today's
   `card` top), then its **banner** (its title, 600, centred, two lines), then its **text** (four lines, muted), then
   **its quick answers** — the same buttons its raised card has (`it.quick()`), 36 px at least, at most **two**; a stop
   with more (a question's choices) shows its recommended choice (pressed, as decisions §54.7) and *More…*, which
   raises it.
3. **The rest fan around it** as today (`fanPlaces`), 104 × 150, turned 4° a place outward and lowered by
   `3·d² + 8` px (d: the places from the front), their gem, element and banner showing; their kind's word is not drawn
   (its gem and its fill say it; the label keeps it). **A card right of the front draws its corner mirrored**: its gem
   at the top right, its element at the left, its banner aligned right, so what its left neighbour covers is not what
   it says (a playing card's index in both corners).
4. **A tap on a fanned card brings it to the front** (no motion but its new place, steps(3), 0.12 s; none under reduced
   motion); it stays in front until it is answered or the hand changes. **A tap on the front card's body raises it**
   (today's raised sheet, its *Open it on its own screen*); its buttons answer at once.
5. **An answer from the front** is the same command as from the raised card, with `via: "front"` (today `"hand"`);
   decisions §62.7's measure counts both as the hand. An answered stop fades where it stands (spec 58 §4); the next most
   urgent comes to the front; a plan started deals from the front's place (spec 57).
6. **One stop**: it stands alone in front, centred. Keys and a screen reader read the stops in the urgency's order, the
   front first (today's).

## 5. Tests (browser, 390 × 844)
- A stage of **four builders** (the scene's Backend and Screens, with an Artist and a Sound designer added, two tasks
  each): no sideways scroll (`scrollWidth` of the page and of `.arena-scroll` = their `clientWidth`); four `.pair`
  columns of equal width; every token 74 px wide and 5:7; the tokens of one member wrap in its column; with two members
  a member's two *now* tokens lie on one row; Planning lays its goals four to a row.
- A token: no `.tcard__idea`; the type's sign at the top right in the element's colour for a typed goal; a running
  task's foot is its time; a held one's its hour; a waiting one's foot empty, its `aria-label` names what it waits for
  (*after Challenge store, Credential table*) and never an id; a failed one has the danger edge and the raised fill.
- The hand: its zone 250 px with stops, 56 px with none; the front card is the most urgent (the failure), upright,
  150 × 236, with *Start again* and *Open…* as buttons; a question in front shows its recommended choice and *More…*;
  a right-hand card's gem lies right of its element; a tap on a fanned card brings it to the front; a tap on the front
  card's body opens the raised sheet; an answer from the front sends `via: "front"`; the create button's bottom is
  above the zone's top.
- The desktop: a waiting card's foot says *waits for 2*; its tooltip names the tasks; no card or tooltip says an id.
- The critical tests (`orkcraft.toml` `always`), the files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_pwa.py`.

## 6. Not in this spec
A swipe through the hand; the hand's zone growing with the number of stops; the desktop's field and hand (the desktop's
cleanup drawn on the same canvas is its own spec); the field as a table of dots.

## 7. As built (notes, no change of the contract)

- **A word longer than the token** (§2.3) is clipped at the token's edge, not ended with *…*: a line clamp cannot end a single unbroken word with an ellipsis. Its full words are in its label.
- **A card of a spread is not a token** (§2): it keeps its goal's line and its state in words (*after Challenge store, Credential table*, §3 applies), at 172 × 240.
- **The hand's zone has a 1 px line over it** (`--ork-frame`), as the approved mockup draws it; spec 49 §10.6's *no line over them* is reversed.
- **The fan's overlap** (§4.3) is computed so that the row fits (`ov` in `shell-stops.js` `fan()`, 8 px at the least, the two ends keeping no outer overlap): with more stops the cards lie further over each other, each still showing its top. With an even count the cards right of the front turn further out than the left ones, so the fan's extent is centred within 6 px, not 2.
- **The front card** (§4.2): a stop whose raised card holds more than its buttons (a plan that misses a kind of work) shows its *missing* line under a two-line text; a Pick one stop shows *More…* only (its tiles are on the raised card); a result shows its *Merge into dev* (or *Fix them*) and *More…*. The buttons are drawn 36 px and hit 44 px (a pseudo-element), 8 px apart.
- **A tap's front stays** until the stop is answered or a new stop arrives (a stop answered elsewhere leaves the front as it is). While the answered front card fades where it stood, the next one waits fanned beside it, then takes the front.
- **A column's head** (§1.3): when the name does not fit beside its marks they go to a second line (`.colname.is-two`, set by `fitNames` in `shell-arena-field.js`), and every head of the strip is then 42 px high so the columns' tops stay level.
- **Motion**: the field's slide (`shell-motion.js` `play`) moves a token only vertically; a token that wraps up into the row of one that left does not slide sideways. The module is unchanged here (spec 63/64's).
