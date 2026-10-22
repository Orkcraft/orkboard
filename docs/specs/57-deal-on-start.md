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
