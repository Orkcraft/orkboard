# Spec 60 — The phone's members wear their tool and level: the marks beside each column's name, the tool in words on a member's card

The owner, 23 October (decisions §73): *on the phone, while the party works, you cannot see each member's tool and level:
only the heads on top and the names below; the desktop has them.* On the desktop a member's head wears its level's
chevrons and its tool's mark (spec 49 §5.2) and the peek says both in words. On the phone spec 53 took the members' strip
away and the marks with it (§66.2): `marksOf` (`pwa/shell-arena-words.js`) still computes them for every member and
nothing draws them. So the phone never says on what tool, or at what level, a member runs: the two things that make its
price and its pace. So: **over each column, the member's tool mark before its name and its level's chevrons after it**;
**on a member's card (its solo), its tool in words**. **Builds:** Claude · **Review:** light · P2.

**What it is, and is not:** the phone only, from what the snapshot already gives (`role.harness`, `head.tier`). No host
change, no new command, word, setting or storage. Not on the stage switch's faces: a 24 × 22 head takes no two 16-px
marks beside its state sign, and the faces are the switch's buttons. The desktop is unchanged.

| part | builds | files (and their tests) |
|---|---|---|
| **C. Phone** | §1–§3 | `pwa/shell-arena-field.js` (`colName`, the solo's card), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_member_marks_browser.py`; the phone tests that read `.colname` (`test_pwa_board53_browser`, `test_pwa_arena_browser`) only if they need it |

## 1. Over each column
- `.colname` holds three things in a row, centred: **the tool's mark** (`marks/harness-<id>.png`, 16 × 16 from its @2x,
  as `shell-who.js` `mark()` draws it), **the name** (a span of its own: the only part cut with an ellipsis), **the
  level's chevrons** (`marks/rank-<n>.png`, 16 × 16). The gap is `--ork-2`; the row stays 28 px high.
- From `marksOf(m)`: a mark that is `null` (a tool orkUI draws no mark for, a head with no tier) is not drawn, and the
  name stands with what is left.
- Each mark's `title` is its words (*Runs on Claude Code*, *Seasoned: its level*), its `alt` empty. `.colname`'s
  `aria-label` says it once: *<name> · runs on <tool> · <level>* (the parts known). Its text (`text_content()`) stays the
  name alone: the tests read it.
- The leader's column (the first stage) too.
- At 390 px with three columns (`.strip.is-few`, about 120 px each) a long name (*Level designer*) is cut, the marks
  never; with four or more (148 px each, scrolled) today's library's names are not cut.

## 2. On a member's card (the solo)
The kit line says the tool after the head's words: *Seasoned elf · Design · Claude Code* (`role.harness.name`; nothing
added when it is not known). The leader's and the Grunt's too.

## 3. The service worker
`sw.js` `CACHE` one up from what `main` has, with `tests/test_pwa.py`'s pin.

## 4. Tests
- **C** (browser, 390 × 844): a party of a leader and three builders on two tools and three levels: each `.colname` has
  its member's tool mark and level mark (`img[src*="harness-<id>"]`, `img[src*="rank-<n>"]`), its text is the name, its
  `aria-label` says both; a member on a tool with no mark: the chevrons only; a long name is cut and both marks keep
  16 × 16 inside the column; the solo's kit line ends with the tool's name; the stage switch is as it was (no `.ork-mark`
  in `.bands`); the service worker's version.
- The critical tests (`orkcraft.toml` `always`), `tests/test_pwa.py`, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`.

## 5. Not in this spec
The price for a run over each column (it is on the card); the marks on the stage switch; the desktop.

## 6. As built (notes, no change of the contract)
