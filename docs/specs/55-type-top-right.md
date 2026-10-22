# Spec 55 — The type top right: a card's top right holds its goal's type, in its goal's colour; the state's sign leaves the top

The owner, 22 October (decisions §68), after the screenshots of spec 54: *"Where did the task type signs go on the cards?
I see only the element. Maybe then remove the exclamation mark or the error sign at the right of a task's card and put the
type there (but the type and the element in one colour)?"* They were not seen because a type's sign is drawn only for a
goal that has a type (`typeOf(n)`: `n.type.sign`) and the test scene's goals have none (nor do goals made before spec 52);
where it is drawn (spec 53 §3) it is 14 × 14 in muted ink before the goal's short name in the card's faint goal line, so
it is easily missed and it truncates the name. So: **a card's top right holds its goal's type's sign in its goal's
element's colour**; **the state's sign leaves the top** (the foot and the edge say it); **the goal line is the name
alone**. **Builds:** Claude · **Review:** full · P2.

**What it is, and is not:** one place moved and one colour rule, on both faces. No new command, no new setting, no
storage, no orkUI change (only its tokens `--ork-elem-<element>`, `--ork-ink-faint`, `--ork-ink-muted` and its signs).
The stops along the bottom, the top bars, the stack's ghost flash and New goal's form are not changed.

One part (phone and desktop share no file):

| part | builds | files (and their tests) |
|---|---|---|
| **Phone** | §1–§4 | `pwa/shell-decks.js` (`cardFace`), `pwa/shell-arena-words.js` (the card's `sign`/`signTip`, if nothing else reads them), `pwa/shell-goals.js` (the list's type sign coloured), `pwa/app.css`, `pwa/sw.js` (`CACHE` `orkcraft-app-v63`) with the pins of v62 in `tests/test_pwa.py`, `tests/test_pwa_board53_browser.py`, `tests/test_pwa_goal_types_browser.py`, `tests/test_pwa_one_hand_browser.py`; new `tests/test_type_top_right_browser.py` |
| **Desktop** | §1–§4 | `js/arena/stacks.js` (`CardBody`, `typeSign`), `js/arena/field.js` (a Planning goal's card), `js/arena/goals.js` (the list's type sign coloured), `js/arena/arena.css`; new `tests/test_type_top_right_desktop_browser.py` |

## 1. The type, top right, in its goal's colour
1. A card's top row: left the goal's **element**, then (phone, a spread's card) the phase word, right the goal's **type's
   sign** (14 × 14). Phone: `.tcard__top` holds `.ork-elem`, `.tcard__phase`, `.tcard__type`; desktop:
   `.arena-task__top` holds `.ork-elem`, `.arena-task__phase`, `.arena-task__type`.
2. **Its colour is its goal's element's**: orkUI's `--ork-elem-<element>`; `--ork-ink-faint` when the element is drawn
   `.dim` (a goal not read yet); `--ork-ink-muted` for a goal with no element. The sign is a mask filled with the text's
   colour, so the colour is set on the type's node by the element's class (`meadow`, `ice`, `dust`, `void`, `lava`, `dim`).
3. A goal with **no type**: no type node; the top right is empty.
4. The type's sign is `aria-hidden` with the type's name as its title. The interface never names an element.

## 2. The state's sign leaves the top
The card has no `.tcard__mark` / `.arena-task__mark`: ↻ at work, ✗ failed, the clock tonight and ! (asks you / asks you to
pick) are not drawn on a card's top. The state is said by the foot (*working 28 h*, *failed* in danger, *tonight*, *asks you
to pick*) and by the edge (`is-fail` danger, `is-stop` alert, dashed for what waits). The label (`aria-label`) and the
tooltip stay; the label already names the type after the goal.

## 3. The goal line is the name alone
`.tcard__idea` / `.arena-task__goal` holds the goal's short name, nothing before it: it gets its full width back. A
Planning goal's card keeps its words: the type's name (*Fix a bug*) or, with no type, *Goal* (phone) / *Planning*
(desktop); its type's sign is top right like any card's.

## 4. Where it applies
- **Every task card** of the field's stacks, the spread's cards (phone: the phase word stays between the element and the
  type) and a **Planning goal's card**, on both faces.
- **The goals' lists** (phone `pwa/shell-goals.js` `.dk__type`, desktop `js/arena/goals.js` `.arena-goal__type`) keep their
  place and their state signs (a row has no foot), but their type's sign wears its goal's element's colour too: a type's
  sign is drawn in its goal's colour wherever it is drawn.
- **Not changed**: the stops along the bottom (their cards are narrow: the element alone), the top bars, the stack's ghost
  flash (✓ merged, ✗ dropped), New goal's form.
- Reverses spec 53 §3's place of the type and spec 50 §3.4's mark top right.

## 5. Motion
None added (decisions §62.8 stands).

## 6. Tests
`tests/test_type_top_right_browser.py` (phone, 390 × 844) and `tests/test_type_top_right_desktop_browser.py` (1 440 × 900)
prove: a typed goal's card has the type's sign in the top row, right of the element (same row, larger x), 14 × 14; its
computed `background-color` equals the element's; a dim element's type is faint; no card anywhere has a state sign in its
top row; a failed card still has the danger edge and the danger *failed* foot; the goal line's text is the name alone with
no sign in it; a Planning card says *Fix a bug* (no sign in the line) or *Goal* / *Planning*; a goal with no type has no
type node; no stop along the bottom wears a type; the list's type sign has its element's colour; on the phone 44 px
targets and no sideways scroll stay. Browser tests wait for state, never read right after a tap. The tests that read the old
mark or the type before the name keep what they prove (a state sign becomes the foot's words and the edge's class).
Each part also runs the critical tests (`orkcraft.toml` `always`), `tests/test_gui_wording.py`,
`tests/test_design_system.py`, and the phone `tests/test_pwa.py` and the phone browser tests it changed.

## 7. As built
(written when built)
