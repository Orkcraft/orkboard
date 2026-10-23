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

**C (the phone), 23 October.** §1–§3 built as written, with the two findings below. What the builder chose or found:
- `pwa/shell-arena-field.js` `colName(m)` draws, from `m.marks` (`marksOf`, unchanged: it is not in C's row), `mark("harness-<id>", tip)`, the name in `span.colname__name` and
  `mark("rank-<n>", tip)`; a mark that is `null` is not drawn. `.colname` (`pwa/app.css`) gains `gap: var(--ork-2)` and loses its `text-overflow` (the ellipsis moves to the name);
  the name span takes `min-width: 0; overflow: hidden; text-overflow: ellipsis` and the marks stay `flex: none` (orkUI's `.ork-mark`, 16 × 16). Padding, the 28 px row and the
  centring are as they were. The leader's column and the checkers' columns wear theirs through the same function.
- `aria-label` is `<name> · runs on <tool> · <level>`: the tool is `role.harness.name`, the level the tier's word from `shell-who.js` `TIER_WORDS` (*Seasoned*, *Veteran*, *Novice*); a
  part not known is left out, and a member with neither has the label of its name. The marks' titles are `marksOf`'s own (*Runs on Claude*, *Seasoned: its level*), their `alt` empty.
  The label stands on a role-less `span` as the spec words it (no `role` added), so only some screen readers say it.
- **The tool's name is the host's:** `ideas_roles._harness` sends the first word of the tool's title, so the words are *Claude* and *Codex*, not *Claude Code*: the card reads
  *Seasoned elf · Design · Claude* and the title *Runs on Claude* (the spec's examples are the long form). Not changed: the host and `marksOf` are not in C's row.
- The card's kit line (§2) is `[m.kit, role.harness.name]` joined with ` · `, the tool left out when the host sends none; the leader's and the Grunt's card use the same line.
- **Finding, §1's last bullet (three columns):** the field's `FEW` is 2 (spec 50 §6.5), so `.strip.is-few` is one or two columns (about 180 px each with two) and **three columns are
  148 px, scrolled**, the third peeking: there is no three-column `.is-few` of about 120 px. Built and tested on what the code draws: with three columns a long name
  (*Design system designer*) is cut with an ellipsis and both marks keep 16 × 16 inside the column; with two, *Level designer* is whole.
- **Finding, §1's last sentence (148 px):** *today's library's names are not cut* does not hold. At 148 px the name has 100 px (4 + 16 + 4 + name + 4 + 16 + 4), measured in Chromium at
  11 px: *Design system designer* 141 px, *Accessibility reviewer* 142, *Security reviewer* 111, *Product designer* 105 and *Product manager* 102 are cut; the other six fit
  (*Sound designer* 91, *Level designer* 91, *Data engineer* 83, *Taskmaster* 70, *Architect* 60, *Grunt* 34). Without marks (140 px) the first two would already be 1–2 px over.
  Left as specified (marks never shrink, only the name is cut); if the owner wants these whole, the room is the column's side padding (+8 px takes the two nearest) or its width.
- Tests: new `tests/test_pwa_member_marks_browser.py` (eight tests: the three marks in order with titles, labels, 16 × 16, the gap and the centring; the leader's and the checkers'
  columns; no mark for a tool orkUI draws none for, no level for a head with no tier, neither for a role with no tool; the cut with three columns and the whole name with two; the card's
  line; the stage switch with no `.ork-mark`; the cache). The tests that read `.colname` (`test_pwa_board53_browser`, `test_pwa_arena_browser`, `test_pwa_map39_browser` and the others)
  needed no change: the text is the name alone.
- `sw.js` `CACHE` is **`orkcraft-app-v68`** (main had v67), one bump for this part and spec 61 C: the second to merge keeps v68. Pinned in `tests/test_pwa.py` and in the five browser
  tests that pin the version (`test_pwa_board53_browser`, `test_pwa_deal_start_browser`, `test_pwa_goal_types_browser`, `test_pwa_mixed_parties_browser`, `test_pwa_one_hand_browser`),
  which would be red on v67 otherwise.
- **Merged** after spec 64 C, which had taken v68 first: the merge made it **`orkcraft-app-v69`** (sw.js and the same pins), so a phone that cached v68 takes this part too.
