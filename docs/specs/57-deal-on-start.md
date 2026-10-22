# Spec 57 — The deal on Start: a plan started from the hand deals its tasks onto the field

The owner, 22 October (decisions §70). Pressing *Start the work* on a plan is the moment the party is set to work and
money starts to be spent, and today it says so quietly: the stop goes and the tasks rise into their columns (spec 49
§11.1) wherever the eye is not. Decisions §62.9 already says it in the realm's words: *you deal the work (a plan
started…), the party clears it*. So: **a plan started by a press in the hand deals its tasks from that stop's place onto
their columns** — the one motion that travels, kept to this one press (an exception to §62.8, never a precedent).
**Builds:** Claude · **Review:** full · P2.

**What it is, and is not:** one motion on both faces, played by the client from what it already reads. No host change
(`ideas.start` still answers `{ok}`), no new command, word, setting or storage. Every other start (autostart, the
drawer's plan screen, a plan passed while the page was hidden) keeps the rise of today. Nothing else flies.

Two parts (they share no file):

| part | builds | files (and their tests) |
|---|---|---|
| **B. Desktop** | §1–§3 | `js/arena/stops.js` (the plan's presses keep where they were pressed), `js/arena/arenastate.js` (the deal waiting), `js/arena/motion.js` (`useColumn`: a dealt card's entry), `js/arena/stacks.js` (its class), `js/arena/arena.css`; new `tests/test_deal_start_desktop_browser.py` |
| **C. Phone** | §1, §2, §4 | `pwa/shell-stops.js` (the plan's presses keep where), `pwa/shell-motion.js` (the deal), `pwa/shell-arena-field.js` (`observe`: a dealt stack's entry), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_deal_start_browser.py` |

## 1. What deals
1. **The presses**: on a plan's stop in the hand (desktop: its card's answers; phone: the raised card's), *Start the
   work*, *Add and start*, *Start without* and a night plan's *Start now*. Nothing else.
2. **When the call is answered `ok`**, the face keeps **a deal waiting**: `{goal: the plan's goal slug, from: the
   stop's box (its card's client rect at the press), at: now}`. One at a time (a newer press replaces it); it is dropped
   after **6 s**, at a refusal, or once played.
3. **The deal plays** in the first render where that goal's tasks are new on the field (the cards that would rise,
   spec 49 §11.1 / the phone's `is-drawn`): those cards, in the field's order, **travel from the stop's box to their
   places** instead of rising, then the deal is dropped. Cards of other goals new in that render rise as today.
4. **No deal** — the rise or nothing, as today — when motion does not play (`prefers-reduced-motion`, the page hidden),
   for a column held under the pointer or the focus (spec 49 §11.4: it waits, then its cards rise), or when the tasks
   come after the 6 s.

## 2. How it moves
- Each card from the stop's box (its centre, at the stop's size: scaled to the stop's width) to its own box, **steps(6),
  0.30 s, 35 ms apart** (spec 50 §4.1's deal), the field's order (left column first, the top of a column first).
- **At most six travel**; the rest of the goal's new cards rise as today, after the sixth starts.
- Over everything of the field while it moves (no scrim, nothing dims); a card takes the pointer only when it lands.
- Nothing bounces; nothing waits for it: the field is usable at once, the toast says what it says today.

## 3. The desktop (B)
- The stop's box is its `.arena-hc` (the hand's card), read at the press (it is raised then).
- `useColumn`'s fresh keys of the waiting deal's goal get `is-dealt` with the travel as inline variables (`--dx`, `--dy`,
  `--s`, `--delay`) in place of `is-drawn`; `DRAWN_MS` covers the last card's end.
- *Add and start*: the member joins first (the field's columns are the party's), so a new member's column is in place
  when its cards land.

## 4. The phone (C)
- The stop's box is the raised card's (`.raised`), read at the press, before it is lowered.
- Only the stage shown deals (the field draws one band, spec 52 §5): **the stage is not switched**; tasks that go to
  another stage are not dealt (its tab's faces say it, as today).
- A dealt stack (`.deck`) travels as one card: `is-dealt` with the travel's variables in place of `is-drawn`.
- `sw.js` `CACHE` one up; `tests/test_pwa.py`'s pin.

## 5. Tests
- **B** (1 440 × 900): a plan's *Start the work* pressed in the hand deals its new cards from the stop (the first card's
  start box near the stop's, its end its column's place; `is-dealt`, no `is-drawn`); at most six travel and the rest rise;
  a start from the drawer's plan screen and an autostart only rise; reduced motion: no `is-dealt`, no `is-drawn` motion;
  a refused start keeps nothing waiting; after 6 s a late render rises.
- **C** (390 × 844): the same from the raised card, the stage shown; a start whose tasks go to a stage not shown deals
  nothing and does not switch the stage; reduced motion.
- Browser tests wait for state, never read right after a press. Each part also runs the critical tests (`orkcraft.toml`
  `always`), `tests/test_gui_wording.py`, `tests/test_design_system.py`, and the phone `tests/test_pwa.py`.

## 6. Not in this spec
- An answered stop of any other kind travelling (decisions §65.8, §71 stand).
- Switching the phone's stage to where the work went; a sound.

## 7. As built

**B (desktop).** Built in `js/arena/stops.js` (`startPlan`), `arenastate.js` (`deal`, `dealWaits`, `dropDeal`), `motion.js` (`useColumn`'s `deals`, `claimDeal`, `dealOut`, `rises`), `stacks.js`
(`is-dealt`), `arena.css` (`arena-deal`, `.is-dealing`); new `tests/test_deal_start_desktop_browser.py`. What the spec left open, and the files beyond the row:
- **The deal waits from the press, not from the answer.** The host's `ideas.start` reply and its push of the new Board can arrive in either order, so the deal is kept at the press (its `at` is the press)
  and taken away if the call is refused (`act` answers null). A refused start never shows new cards, so nothing can be dealt by it. It is also dropped by `leaveParty()` (another party is shown).
- **Who takes the deal.** `useColumn(…, deals)` is asked by the field's columns only (`field.js`, two calls: `true`), so the review column (`waits.js`) never takes it. The first render with new keys of the
  deal's goal takes it in each column that has some; it is dropped on the next tick, once this flush's other columns have read it. A column held under the pointer settles later and finds no deal: its cards rise.
  A column that is new while the deal waits (*Add and start*: the member's column mounts with the Board's change) takes it from its first render.
- **The order and the six.** The cards are numbered in the layout pass after the redraw, over all the columns in the order of the page (left column first, a column's rows from the top), by `slots`. The seventh
  and the rest are turned into rises (`is-drawn`, delayed 210 ms, after the sixth starts); the choice is kept by `rises(key)` because a card redrawn by itself (a signal: the ring) is given its old props.
  A card that is not the front of a stack has no element, so it takes no number; the six are the six that are drawn.
- **Over the field.** The columns clip (`overflow-y: auto`); while its cards travel a column is `.is-dealing` (`overflow: visible`, for `DEALT_MS` = 620 ms) unless it is scrolled, and a dealt card has `z-index: 60`.
  The variables are `--dx`, `--dy`, `--s`, `--delay`, set inline from the stop's box (its centre; `--s` the stop's width over the card's); the keyframes switch `pointer-events` at their half, so a card takes the pointer
  at about the middle of its travel, not after the last one lands.
- **Beyond the row:** `field.js` (the two `useColumn` calls pass `true`), and `tests/test_design_system.py` (`--dx`, `--s`, `--delay` join the custom properties the sheets may use, as `--rot` and `--dy` do).
- Not done: the cards of the spread (spread.js) and the review column are not dealt; a stack's hidden cards (behind the front) take no number.

**C. Phone** (`orkcraft-app-v64`, shared with spec 58 C). Built to §1, §2, §4 as written; what the spec left open:
- **The deal waiting is `deal` in `shell-motion.js`** (`wait(goal, from)`, `live()`, `drop()`; 6 s), set by `shell-stops.js` `go(…, dealt)` after the host answers `ok`, from the raised card's rect read before it is lowered; only the party
  shown's plan deals (another party's tasks are not on this field), and not when `motionOn()` is false. `shell-arena-field.js` `observe` hands the stacks of that goal that are new in the stage shown (`s.dealt`) to `dealTo`; the
  deal is dropped in the first render where any stack of its goal is new (so tasks that go to a stage not shown, or into a column held under a finger, are never dealt and never wait on), and in any render under reduced motion or a hidden page.
- **What travels is a copy**, not the stack: the columns (`.stack`, `.arena-scroll`) clip, so a stack animated in place could not travel from the hand "over everything of the field". `dealTo` (`shell-motion.js`) measures each new stack in the page,
  gives it `is-dealt` with `--dx --dy --s --delay` (the stack lies `visibility: hidden` and lands, by an animation of 0 s delayed by `--delay` + 0.30 s, when the copy does: it takes the pointer only then), and puts a `.deal-fly` copy
  (`position: fixed`, `z-index: 60`, `pointer-events: none`, `deal 0.30s steps(6)`) on `body`, removed after it. A stack out of its column's view and every stack after the sixth get `is-drawn` instead (after the sixth: `animation-delay` 210 ms).
  `shell-decks.js` is unchanged. `test_design_system.py` allows the three new custom properties (`--dx`, `--s`, `--delay`; `--dy` was allowed already).
- The tests: `tests/test_pwa_deal_start_browser.py`, 11 tests (the four presses, the order and delays, from the raised card's centre at its width, the stage not switched, a stage not shown, six at most, reduced motion, refusal, after 6 s, another party's plan).
