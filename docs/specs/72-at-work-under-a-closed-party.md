# Spec 72 — A closed party says what it is at work on, in one line

The owner, 24 October (decisions §87): the left column (spec 69) shows only the open party's goals; a closed party says
*k/n* and one sign. So **under a closed party's heading, one quiet line of its goals at work**, a press on one opening that
party with that goal picked; the phone's parties' sheet gets the same line. **Builds:** Claude · **Review:** light · P2.

**What it is, and is not:** a line on each face from what `ideas.map` already answers (a node's `goal`, `state`,
`short`, `element`). No host change, no new command, setting or word in the glossary. Not: a closed party's other goals;
the open party's heading (its goals are below it); the project's level (spec 70 has its own).

Two parts, **built at once, in parallel**; they share no file.

| part | builds | files (and their tests) |
|---|---|---|
| **B. Desktop** | §1, §2 | `js/arena/partylist.js` (the line under a closed heading), `js/arena/arenastate.js` (only if picking a goal into a party not shown needs it), `js/arena/arena.css`; new `tests/test_at_work_line_desktop_browser.py`, and `tests/test_party_list_desktop_browser.py` if a heading's height is asserted |
| **C. Phone** | §1, §3 | `pwa/shell-where.js` (the line under a party of the parties' sheet), `pwa/shell-goals.js` (only if picking a goal into the filter of a party not shown needs it), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin and the phone tests that pin it; new `tests/test_pwa_at_work_line_browser.py` |

## 0. The words
New strings: *and k more* (*and 1 more*), *At work: <goal>, <goal>* (the line's accessible name and title, the goals'
whole titles). The work sign is orkUI's `work` (`.ork-sign`), never a Unicode ↻.

## 1. The line (B, C)
1. **What it holds**: the party's goals whose node `state` is `working`, in the map's order; each **its element**
   (`.ork-elem`, small) and **its short name** (`short`, else the title), joined by *·*; what does not fit on one line ends
   with *and k more* (no cut word, no ellipsis in the middle of a name). Before them the work sign (muted). No goal at
   work: **no line** (the heading keeps its height).
2. **Quiet**: the text face, the muted ink, one line, the heading's indent; never the alert or danger colour (a stop is
   the heading's sign, §65.2). It is not drawn under the open party (B) or the party shown (C), nor under Operations.
3. **A press on a goal** (each is a button, 32 px high at least on the desktop, 44 px on the phone) **opens that party
   with that goal picked into the filter** (the picks of spec 50 §3.5: that party's picks become that goal alone), as a
   press on its heading would switch, then picks. *and k more* is a button that opens the party with no pick.
4. Its accessible name: *At work: <goal>, <goal>* (whole titles); each goal's button its whole title.

## 2. The desktop (B)
Under the heading's name, inside the heading's box (the heading grows by the line's height, 20 px), indented by the
head's width. The goals' buttons are not inside the heading's own button (no nested buttons): the heading is a box with
the heading's button and the line's buttons side by side in it. ↑/↓ still move between headings.

## 3. The phone (C)
Under each party's row of the parties' sheet but the one shown: the line as §1, its goals 44 px tap targets (one row
that wraps to two at most, then *and k more*); a tap closes the sheet and switches. No sideways scroll at 390 px.

## 4. Tests
- **B** (1 440 × 900, stub host): a closed party with two goals at work shows the line (elements, short names, the work
  sign) and the open one shows none; a party with none has no line; five at work end with *and k more*; a press on a goal
  shows that party with only that goal picked; *and k more* shows it with no pick; no nested buttons; the line's colour is
  the muted ink.
- **C** (390 × 844): the same in the parties' sheet; a tap closes the sheet and switches with the pick; no sideways
  scroll; the service worker's version.
- Each part: the critical tests (CLAUDE.md "Alpha"), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`; C also `tests/test_pwa.py`.
