# Spec 61 — Your own goal, first: the goal in the person's words leads the goal types, under its own name

The owner, 23 October (decisions §74): *a party's fixed set of goal types limits the person: leave room for a free goal,
its card filled in by the person.* It is there — the desktop's spread of types ends with *A blank goal*, the phone's row
with *No type* — but last, after up to ten types, and named as if it were empty. So: **it is called *Your own goal* and
stands first** on both faces; on the phone it is the one picked when the form opens. A type stays a shortcut (its asks,
its refs, its plan's hint), never a limit. **Builds:** Claude · **Review:** light · P2.

**What it is, and is not:** words and order on both faces. No host change (`ideas.add` without `type`, as today), no new
command, setting or storage. Measured as spec 52 §2.7 already measures it (`idea_added`'s `type`, `""` for one's own).
Not: a type suggested from the person's words; goal types of the person's own.

Two parts; they share no file.

| part | builds | files (and their tests) |
|---|---|---|
| **B. Desktop** | §0, §1 | `js/arena/types.js` (the card first, its words), `js/arena/goals.js` (the pile's label and title), `js/shell/ideadialog.js` (the form's head), `js/arena/arena.css` only if the order needs it; `tests/test_goal_types_desktop_browser.py`, `tests/test_arena_decks_desktop_browser.py`, `tests/test_lens_desktop_browser.py` (the pile's label), `tests/test_lexicon.py` (the label it reads) |
| **C. Phone** | §0, §2 | `pwa/shell-ideas.js` (the chip first, picked when the form opens, its words), `pwa/app.css` only if needed, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; `tests/test_pwa_new_goal53_browser.py`, `tests/test_pwa_goal_types_browser.py` |

## 0. The words
- **Your own goal** (was *A blank goal* on the desktop, *No type* on the phone). Its line on the phone: *In your words:
  the leader plans it like any other.* (was *A blank goal: only your words.*).
- The pile's label and title: *New goal: your own, or pick its type* (was *New goal: pick its type, or a blank one*).
- Code keeps its names: `is-blank`, `BlankGoal`, `data-type=""`, `typed = null`.

## 1. The desktop (B)
1. New goal's spread (`types.js`) deals **Your own goal first**, then the party's types in the map's order. Its card is
   today's blank card (the pile's back with its +, dashed), its name *Your own goal*, its aria-label *Your own goal: in
   your words*. The deal's order and timing as today (spec 50 §4.1): it is the first card dealt.
2. The pile's label and title (`goals.js`): §0.
3. Its form (`ideadialog.js` `BlankGoal`) is headed *Your own goal* in place of *A blank goal*; nothing else of the form
   changes.
4. A map with no `types` (an older host) opens the form at once, as today.

## 2. The phone (C)
1. The types' row (`shell-ideas.js`): **Your own goal first** (the dashed chip), then the party's types (the most used
   first, as today).
2. **It is the one picked when the form opens** (was the first type): the field's placeholder *What should become
   possible*, the lens switch as today with no type, its line §0. A tap on a type picks it as today.
3. A party with no types: the row is hidden as today (the goal is one's own).
4. `sw.js` `CACHE` one up from what `main` has, with `tests/test_pwa.py`'s pin.

## 3. Tests
- **B** (browser, 1 440 × 900): the spread's first card is *Your own goal* (`.arena-type.is-blank` first), the types
  after it in the map's order; a press opens the form headed *Your own goal*; the pile's label; an older host with no
  `types`.
- **C** (browser, 390 × 844): the row's first chip is *Your own goal* and is checked when the form opens, with its line;
  a type tapped is checked and the line is the type's; *Add the goal* with one's own sends no `type`.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`; C also `tests/test_pwa.py`.

## 4. Not in this spec
A type suggested from the person's words; a person's own goal types (spec 59: not in it).

## 5. As built (notes, no change of the contract)

### B. The desktop (23 October)
- **Built:** `js/arena/types.js` deals the blank card first (`<TypeCard t=${null} …/>` before the types' map), so it is the first card dealt (delay 0, the
  types after it each 35 ms later, as `dealCards` does for any spread); its name is *Your own goal*, its aria-label *Your own goal: in your words*. The pile's
  `aria-label` and `title` (`js/arena/goals.js`) are *New goal: your own, or pick its type*; the pile's two-line caption (*New goal* · *pick its type*) is
  unchanged, §0 names only the label and the title. `BlankGoal`'s head (`js/shell/ideadialog.js`) is *Your own goal*. No CSS change: the dashed card needs no
  rule of position. Code keeps `is-blank`, `BlankGoal`, `data-type=""`, `typed = null`.
- **Chosen:** the spread's focus starts, as for every deal (`Dealt`, `start = 0`), on its first card, which is now *Your own goal* (was the first type), so
  Enter on a fresh deal opens the person's own goal; ← and → still walk the cards, the focus going round from the first to the last type (the test names
  it). A press on *Your own goal* sends `ideas.add` with no `type`, as before (the test checks it).
- **Tests:** `tests/test_goal_types_desktop_browser.py` has the new test of §3 B (the first card, its words and dashed back, the types after it in the map's
  order, the focus, a press opening the form headed *Your own goal* and adding a goal with no `type`) beside the old one reordered, and the older host with no
  `types`; the pile's label is read in it, in `tests/test_lens_desktop_browser.py` and in `tests/test_lexicon.py`; `tests/test_arena_decks_desktop_browser.py`
  reads the new head. Spec 52 §4.1 and §4.2 still say *A blank goal* and *last*; this spec replaces them for the desktop.
- **Beside it:** `tests/test_lens_desktop_browser.py`'s `TypedHost` called `goal_types.of("architect")`, which spec 59 removed (the test failed on `main`); it
  now deals the catalog's `shaped-feature` and `restructure` (what `WAS` reads `architect/feature` and `architect/restructure` as).
