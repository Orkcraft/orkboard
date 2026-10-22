# Spec 53 — The phone, simpler: the deck beside the party's name, the faces are the members, New goal at once with the party first, a goal's two marks on every card

The owner, 22 October (decisions §66), on the phone as spec 52 built it: four bands before the first card (the top bar,
the goals bar, the stage switch with the party's faces, the members' strip with the same faces again: ≈ 230 px of 844),
New goal behind two motions (the deck's card lifted and the types dealt, ≈ 0.7 s, then the card turned and grown,
0.5 s) and a form longer than the screen (*Fix a bug* 1107 px) that names the party twice. So: **the party's deck moves
to the goals bar**, beside the party's name; **the faces in the stage switch are the members** (a face in the stage
shown is pressed to show only its tasks, a stage's sign stands on the face it comes from) and the members' strip goes,
its names left over the columns; **New goal opens at once** (the form slides up) and **picks the party first**, then
the priority, then the type, then one field for the goal; **a goal's two marks are on every card**: its element (which
goal) at the corner, its type's sign (what kind) before its name. The mockup is the canvas *Orkboard: телефон как есть*,
section *Макет: телефон проще* (boards A–E); **this file is the contract** where they differ. **Builds:** Claude ·
**Review:** full · P1.

**What it is, and is not:** the phone's faces (A and B) and one line of the desktop's cards (C). No host change, no new
command, no new setting, no change to storage: every field this spec reads is in `ideas.map` already (a party's
`leader`, its `types`; a node's `type` and `element`). Change nothing outside a part's files but those §8 names.

Three parts, **all at once** (they share no file but `pwa/app.css` and `pwa/sw.js` between A and B, §7):

| part | builds | files (and their tests) |
|---|---|---|
| **A. Phone: the board** | §1, §3 (phone) | `pwa/shell-goals.js` (the deck at the bar's left), `pwa/shell-where.js` (the deck's size there), `pwa/shell-arena.js` (the stage switch: no deck, faces pressed, signs on faces), `pwa/shell-arena-words.js` (which face a sign stands on; a card's item carries its goal's type), `pwa/shell-arena-field.js` (no members' strip; the names over the columns), `pwa/shell-decks.js` (the type's sign on a card), `pwa/app.css`, `pwa/sw.js` (`CACHE` `orkcraft-app-v60`) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_board53_browser.py`, and the phone tests that read the members' strip, the deck or the stage switch's place (§8) |
| **B. Phone: New goal** | §2 | `pwa/shell-fab.js` (the form slides up; no lift, no deal, no turn), `pwa/shell-types.js` (no strip: the types' chips and the join line), `pwa/shell-ideas.js` (the form), `pwa/shell-lens.js` (no switch for a typed goal), `pwa/shell-forms.js` (if the priority's words need it), `pwa/board.js` (the wiring, if it changes), `pwa/app.css`, `pwa/sw.js` (`CACHE` `orkcraft-app-v61`) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_new_goal53_browser.py`, and the phone tests that open New goal or read its form (§8) |
| **C. Desktop: the type's sign on a card** | §3 (desktop) | `js/arena/stacks.js` (`CardBody`), `js/arena/field.js` (a Planning goal's card), `js/arena/arena.css`; `tests/test_goal_types_desktop_browser.py` (its own new test), and the desktop tests that read a card's goal line exactly (§8) |

## 0. The words
- New strings, in these words: *The goal*, *its first line is its title*, *In a line or a few*, *Goal type*, *No type*,
  *Keep for tonight*, *Waits for the night: the leader reads it then.*, *<leader> leads · k of n goals done*,
  *<leader> · k of n goals done*, *Only <member>’s tasks* (a face's label, as the solo's title says it today).
- Spec 50 §0's rules hold: the interface says *party*, *goal*, *task*; no *card*, *deck*, *strip*, *chip*, *element*
  in what a person reads; every symbol is orkUI's. A type is told by its sign, never a colour (decisions §65.4).

## 1. The board (A)
1. **The goals bar** (44 px): at its left **the party's deck** (spec 52 §5.3's button, its count of the stops in the
   project's other parties and in Operations, its label and its sheet unchanged; here a 44 × 44 target round a back of
   16 × 22 with two edges behind it), then today's *⌄ Passkey · 2 of 9 goals done* (the Goals sheet, the filter, as
   today), the gate at the right as today. Operations' head keeps its deck as spec 52 C put it.
2. **The stage switch** (60 px): the three tabs share the whole width (no deck at its end). Each tab: its band's faces
   over its word, as spec 52 §5.3, but **side by side** (4 px apart, not overlapping) and **the sign on the face it
   comes from**: ✗ (danger) on the member whose task failed, else ! (alert) on the member a stop waits on (Planning's on
   the leader; a pick or a member's question on that member); 12 × 12, at the head's top right, over it by 5 px. ✗ over !
   on one face as today on a tab. No number.
3. **The faces are the members.** In the tab shown, each face is its own button (a 44 × 44 target round its 24 × 22
   head; `aria-pressed`; its label *Only <member>’s tasks*): a tap shows only that member's tasks (today's tap on a
   member, `st.focus`, its solo with *Everyone* and the member's card: head, kit, price, runs, as today); a tap on the
   face pressed shows everyone again. A tab not shown is one button, as today. The tab's own label stays spec 52's
   (*Implementation: Backend, Screens. 1 failed*).
4. **The members' strip goes.** Over each column, its member's **name** only (28 px; pixel face 11 px, capitals,
   muted, centred over the column; not a button). Planning's column says its leader's name. A band with no one keeps
   spec 52 §5.4's line and *Add to the party*. The stacks, the phases, the spread, the motion and the filter are as today.
5. From the top bar's foot to the first phase row: 48 + 44 + 60 + 28 px; nothing else moves.

## 2. New goal (B)
1. **The create button** (*New goal*, its label): a tap opens the New goal form at once; the form **slides up** from the
   bottom, 180 ms, ease-out (a transform; no lift, no deal, no turn); *Put it back*, *Close* and Esc slide it down, 180
   ms. None under `prefers-reduced-motion` (it shows and goes at once). The types' strip of spec 52 §5.5 is no longer
   drawn; a map with no `types` (an older host) opens the form with no *Goal type* row.
2. **The form, from the top**: its head *New goal* and *Close*; then
   1. **Party** (first): a button 52 px high: the party's leader's head (24 × 22), the party's name (600, 13 px), under
      it *<leader> leads · k of n goals done* (11 px, muted), ⌄. A tap opens a list under it (`listbox`, named
      *Parties*): each party of the project in the Board's order — its leader's head, its name, *<leader> · k of n goals
      done*, ✓ on the one picked — then *+ New party* · *one of yours, or from the library* (opens New party as the
      parties' sheet does). Operations is not listed. A pick closes the list and deals that party's types below. The
      party picked first is the one shown.
   2. **Priority**: *High* · *Normal* · *Low* (44 px), picked first as today (the party's own until the person picks).
      Under it, only when *Low* is picked: *Waits for the night: the leader reads it then.* Spec 50's three-line hint goes.
   3. **Goal type**: a row of the party's `types` in their order (the most used first), then **No type** (a dashed
      edge: a blank goal); each 44 px high, its sign (14 × 14) and its name (pixel face 13 px), one picked
      (`radiogroup` named *Goal type*). The first is picked when the form opens and when the party changes. The row
      scrolls sideways when it is wider than the screen (16 px at each end). Under it, the picked type's `line` (11 px,
      muted); *No type*'s: *A blank goal: only your words.*
   4. **The goal**: one field (three lines, its foot holding *Photo* and the mic as today's) labelled *The goal*, with
      *its first line is its title* at the label's right (11 px, faint); its placeholder *In a line or a few* (*What
      should become possible* with *No type*). It is `ideas.add`'s `text` as it is; *Its title* and *What it is for* go.
   5. The type's **asks**, **Refs** and **the join line**: spec 52 §5.6 as built (Refs' pictures are the field's Photo).
   6. **The lens**: a typed goal opens its type's `lens` with **no switch** (a `screen` lens shows its *Add a screen*, a
      `code` or `pain` lens its own fields, under the asks; `text` shows nothing); *No type* keeps today's switch.
   7. At the foot, pinned: *Put it back* · **Add the goal**, which says **Keep for tonight** while *Low* is picked.
3. **Gone from the form**: the element's line (*Its element marks every task of it.*: the host gives it), *for <party>
   · <leader> reads it next* (the Party field says it), the type's sign and name as the form's head (the row says it).
4. What *Add the goal* sends is spec 52's (`text`, `track`, `priority`, `type`, `asks`, `join`, `photos`, `lens`);
   *Put it back* with words keeps the goal for tonight as today, never with `join`.
5. The form fits one screen at 390 × 844 for a type with three asks and no Refs (*Fix a bug*): no scroll.

## 3. A goal's two marks on every card (A: phone, C: desktop)
A goal has two marks and each has its place: its **element** (which goal: shape and colour) at a card's top left, as
today; its **type's sign** (what kind: muted ink, 14 × 14) **before the goal's name wherever the name is written** — as
the Goals sheet's row and the desktop's goal row do since spec 52 (reverses spec 52 §4.6's *no other place draws it*).
- **A task's card** (the field's stacks, a spread's cards): the line with its goal's short name gains the sign before
  the name (phone: `.tcard__idea`; desktop: `.arena-task__goal`). A goal with no type: the name alone.
- **A goal's card in Planning**: in place of the word *Goal* (phone) / *Planning* (desktop), its type's sign and name
  (*Fix a bug*); with no type, the word as today.
- Not on the stops along the bottom (their cards are 104 px wide: the element alone), nor in the top bars.
- The card's label (`aria-label`, the tooltip) names the type after the goal: *… Sign in with a passkey, Fix a bug, …*.

## 4. Motion
Nothing flies (decisions §62.8). The form's slide (§2.1) is the only new motion; spec 52 C's deal and turn of the
create button go. The desktop's deals are unchanged.

## 5. Tests
- **A** (`tests/test_pwa_board53_browser.py`, 390 × 844): the deck at the goals bar's left (44 px, its count of the
  other parties, its sheet), none at the stage switch's end; the tabs' faces side by side; ✗ on the failed member's
  face and ! on the leader's, none on a face with nothing; a face pressed shows the solo and `aria-pressed`, pressed again
  everyone; no `.token` strip; a name over each column; the first phase row at 180 px under the top bar's foot; a task's
  card with its type's sign before its goal's name and none for a goal with no type; a Planning goal's card says its
  type; no stop card wears it; 44 px targets; no horizontal scroll.
- **B** (`tests/test_pwa_new_goal53_browser.py`): the create button opens the form with one animation of 180 ms and
  none of the lift, deal or turn (and none under reduced motion); the Party field first with the leader's head, its
  list (every party, ✓, *+ New party*, no Operations), a pick that deals the new party's types and picks its first;
  the priority (*Low*'s line and *Keep for tonight*); the types' row (order, *No type* last, one picked, its line);
  one field *The goal* (no *Its title*, no *What it is for*, no element line, no *for … reads it next*); asks, Refs and
  the join line as spec 52; a typed goal has no lens switch; what *Add the goal* sends (`text` the field's words,
  `track` the party picked, `type`, `asks`); *Put it back* with words never sends `join`; *Fix a bug* fits 844 px.
- **C** (`tests/test_goal_types_desktop_browser.py`): a task's card shows its goal's type's sign before the goal's
  name; a Planning goal's card says *Fix a bug* with its sign; none for a goal with no type.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_architecture.py`; A and B also `tests/test_pwa.py` and every
  `tests/test_pwa_*browser.py`; C every desktop browser test its files touch.

## 6. Not in this spec
- The desktop's New goal (its pile still deals the types and turns a card, spec 52 B §4.1) and its party's deck.
- One sheet for the parties and the goals; a member's runs or price on the board (they stay in its solo).
- A colour for a type; a type's sign on the stops along the bottom.

## 7. A and B share two files
`pwa/app.css`: each adds or changes only its own rules (A: the goals bar's deck, the stage switch, the columns' names,
the card's sign; B: the form and its slide). `pwa/sw.js` and `tests/test_pwa.py`'s pin: A sets `orkcraft-app-v60`, B
`orkcraft-app-v61`; the part that merges second keeps **v61** and both parts' `SHELL` entries. A conflict anywhere else
keeps both sides' changes.

## 8. Files a part may need beyond its row
A: the phone browser tests that read the members' strip (`.token`), the deck at the stage switch's end
(`.stagebar > .partydeck`) or the stage switch's faces: `test_pwa_arena_browser`, `test_pwa_arena_motion_browser`,
`test_pwa_arena_stops_browser`, `test_pwa_map39_browser`, `test_pwa_decks_browser`, `test_pwa_goal_team_browser`,
`test_pwa_pick_browser`, `test_pwa_goal_types_browser` (its top bar, goals bar, stage switch and deck tests only),
`test_pwa_shell_browser` (only its helpers `_where`, `_band` and their strings). B: the phone browser tests that open
New goal or read its form: `test_pwa_goal_types_browser` (its strip and form tests only), `test_pwa_shell_browser`
(only `_new_goal` and its strings), `test_pwa_idea_field_browser`, `test_pwa_lens_browser`, `test_pwa_decks_browser`
(its create button tests only), `test_pwa_own_parties_browser`, `test_pwa_party_browser`, `test_pwa_goal_team_browser`
(its form's strings only). C: the desktop browser tests that read a card's goal line exactly. Each keeps what it proves.
A part that needs any other file: stop and write it in *As built* first.

## 9. As built (notes, no change of the contract)

**A, the phone's board** (built; `sw.js` `CACHE` `orkcraft-app-v60`, which B's merge, first on `main`, left at v61 as §7 says):
- **The deck** moved to the goals bar's left (`shell-goals.js` `bar(m, gate, deck)`, the deck made by `shell-where.js` as before): 44 × 44, a back of 16 × 22, two edges, its count at the corner; the stage switch has none. Operations' head and the empty board keep theirs (the same 44 px).
- **The faces.** `shell-arena-words.js` `facesOf` now gives each face `{head, slug, name, lead, sign}`; the sign is the member's own: ✗ when a task of it failed, else ! when a stop waits on it (a plan, a proposal or the leader's question: the leader; a pick: its maker; a member's question: that member). A band's own `sign` and label stay as spec 52 (`data-sign`, *Implementation: Backend, Screens. 1 failed*). A face beyond the tab's shown ones (a fourth builder) wears no sign; the label still counts it. A question asked by a builder or a checker is on that member's face, so Planning's tab shows none for it.
- **The tab shown is a `div role="tab"`** (its faces are buttons, and a button does not nest in one); a tab not shown is one button, as today. A face's label is *Only <member>’s tasks* (the leader's: *Only <leader>’s work*, as its solo's title says it). A face's 44 × 44 box overlaps its neighbours' (margins give the room back: the heads stand 4 px apart, 24 × 22); the sign is 12 × 12, 5 px over the head's corner. A press on the tab shown's centre is a face's: a test moves to another tab by its word (`_band` in `tests/test_pwa_shell_browser.py`, which does nothing for the tab already shown).
- **No members' strip**: `memberCard` is gone with its `.token`, `.tport`, `.tnum`, `.sign` and mark rules; over each column a `.colname` (28 px, the pixel face 11 px, capitals by CSS, muted, centred, not a button), `data-member` on it. Its runs, price, kit and marks (level, tool) are in the solo only (the solo's card shows the kit and the numbers; the marks are no longer drawn on the phone's board). A member's first number is no more lit on a merge; the column's *✓ k in dev* is. The solo now covers the columns from the stage switch's foot.
- **The first phase row** stands 189 px under the page's top at 390 × 844 (48 + 44 + 60 + 28 of §1.5, and the bars' 1 px lines and the column's 6 px padding and 1 px edge); the test takes 180 to 190.
- **The type's sign on a card** (`.tcard__type`, 14 × 14, muted): task items carry `type` (`typeOf(n)`, `{id, name, sign}` or none), the card's line is *[sign] Goal name*; a Planning goal's card says *[sign] Fix a bug*, else *Goal*. The label of a task's card is *Task (Goal, Fix a bug): …*, a Planning card's *Goal, Fix a bug: …* (its tooltip too), and a stack of more says the type after its goal. The spread's cards wear it (they use the same card); stops along the bottom do not.
- **Tests.** New `tests/test_pwa_board53_browser.py`. Changed for the new places (each keeps what it proves): `test_pwa_arena_browser` (the member test is now the faces' and the solo's), `test_pwa_arena_motion_browser` (a merge lights the column's count only), `test_pwa_arena_stops_browser`, `test_pwa_map39_browser`, `test_pwa_decks_browser`, `test_pwa_goal_team_browser`, `test_pwa_pick_browser`, `test_pwa_goal_types_browser` (its stage switch, deck and service worker pin tests), `test_pwa_shell_browser` (`_where`, `_band`), `test_pwa.py`'s pin. B's tests (the create button, New goal's form) are untouched here.

**B, the phone's New goal** (`pwa/shell-fab.js`, `shell-types.js`, `shell-ideas.js`, `shell-lens.js`, `board.js`, `app.css`, `sw.js` v61):
- The create button's label is *New goal*; its tap calls `core.newIdea()` and nothing else. `shell-types.js` lost the strip (`makeTypes`, `typeCard`) and keeps
  the agents' heads and prices and the join line; the strip's and the turn's CSS (`.typedeal`, `.typecard`, `.drawlayer`, `.drawcard`) went.
- The form slides up as a `transform` on the dialog itself (one `animate`, 180 ms, ease-out) and slides down for *Put it back*, *Close*, Esc, the backdrop and after
  *Add the goal*; the close buttons are caught on the way down (capture) so they slide first and `close()` runs when the slide ends. Words in it are still kept for tonight
  when it closes. None under `prefers-reduced-motion` or a hidden page (`motionOn()`).
- The party is a button (`.newgoal__party`, `data-goal` the party's slug) and a `listbox` of the Board's parties (the Board's order: priority, then order; no Operations);
  Esc puts the list away before the form. *+ New party* opens New party (`goalSheet.open`) and, once it is saved and the Board read, picks that party.
  A party's name is its title; *<leader> leads · k of n goals done* reads the map's `leader.name` and the goals bar's `barWords`.
- The type row reads the map's `types` of the party picked; the first is picked when the form opens and on a party change; a map with no `types` (or an empty list) draws no row
  and sends no `type`. The priority follows the party until the person picks (as before); *Low* shows its line and *Keep for tonight* sends what *Add the goal* sent (`priority: "low"`).
- `shell-lens.js`: `track(slug, first, alone)` — a typed goal passes `alone`, so its lens shows with no switch (`text` hides the lens), and `value()` sends only that lens; a second
  call for the same party redraws for the type picked instead of returning at once. *No type* passes nothing: today's switch.
- The words the speaker's hint says (*Speak it with the keyboard’s microphone.*) are shown only where the browser has no speech to text.
- Tests: new `tests/test_pwa_new_goal53_browser.py`; the spec 52 strip tests in `test_pwa_goal_types_browser.py` went (their form tests stay, opening the form with `_form`);
  the other phone tests that opened New goal read *The goal*, the party button's `data-goal` and *Keep for tonight*; `test_pwa_shell_browser` waits for the slide before it measures.

## 10. Running A, B and C
Each a cloud session on orkWorks/orkBoard with the brief below; each **merges into `main` itself** when its tests pass
(CLAUDE.md, alpha): no pull request. A and B on Sonnet, C on Haiku.

**A, the phone's board:**

    Build part A (the phone's board) of docs/specs/53-phone-simpler.md: §1, §3 (the phone's cards), §4 and A's lines of
    §5. That file is the contract; read decisions §66 (docs/decisions.md), spec 52 §5 and CLAUDE.md first. Change only
    the files of A's row and those §8 names for A; §7 says how A and B share pwa/app.css and pwa/sw.js (A sets v60).
    The browser tests need `uv sync --extra dev --extra browser`. When the critical tests (orkcraft.toml `always`),
    tests/test_gui_wording.py, tests/test_design_system.py, tests/test_pwa.py and every tests/test_pwa_*browser.py pass:
    write A's note in §9 (As built), commit, merge into main ("Merge spec 53 A: …") and push main. If main moved
    meanwhile (B or C merged), merge it in (§7 for sw.js), run the tests again, then push. No pull request.

**B, the phone's New goal:**

    Build part B (the phone's New goal) of docs/specs/53-phone-simpler.md: §2, §4 and B's lines of §5. That file is the
    contract; read decisions §66 (docs/decisions.md), spec 52 §5.5–§5.6 and CLAUDE.md first. Change only the files of
    B's row and those §8 names for B; §7 says how A and B share pwa/app.css and pwa/sw.js (B sets v61). The browser
    tests need `uv sync --extra dev --extra browser`. When the critical tests (orkcraft.toml `always`),
    tests/test_gui_wording.py, tests/test_design_system.py, tests/test_pwa.py and every tests/test_pwa_*browser.py pass:
    write B's note in §9 (As built), commit, merge into main ("Merge spec 53 B: …") and push main. If main moved
    meanwhile (A or C merged), merge it in (§7 for sw.js), run the tests again, then push. No pull request.

**C, the desktop's cards:**

    Build part C (the desktop's cards) of docs/specs/53-phone-simpler.md: §3 (the desktop) and C's lines of §5. That
    file is the contract; read decisions §66 (docs/decisions.md) and CLAUDE.md first. Change only the files of C's row
    and those §8 names for C. The browser tests need `uv sync --extra dev --extra browser`. When the critical tests
    (orkcraft.toml `always`), tests/test_gui_wording.py, tests/test_design_system.py and the desktop browser tests of
    the files you changed pass: write C's note in §9 (As built), commit, merge into main ("Merge spec 53 C: …") and
    push main. If main moved meanwhile, merge it in, run the tests again, then push. No pull request.
