# Spec 58 — A stop and its task: the link is shown before the answer; the stop leaves with its task's change

The owner, 22 October (decisions §71). A stop in the hand is about something on the field (a task that asks to pick, a
goal whose plan waits, a task that failed), but nothing shows which until it is answered, and then the stop just
vanishes while the card changes somewhere else. The owner first asked for the answered card to fly onto its task; that
was turned down (§65.8: it would distract, every answer). So: **the link is shown while the person looks at the stop** —
its task's cards are ringed on the desktop, its raised card names them on the phone — and **an answered stop leaves
where it stands in the same frame its task changes**, so the two are read as one. Nothing flies, nothing is lit after.
**Builds:** Claude · **Review:** full · P2.

**What it is, and is not:** a ring and a line before, a fade after. No host change, no new command, setting or storage;
one new line of words on the phone (§3). Spec 57's deal is the only travel and is not this spec's.

Two parts (they share no file):

| part | builds | files (and their tests) |
|---|---|---|
| **B. Desktop** | §1, §2, §4 | `js/arena/stops.js` (a stop looked at; the answered stop's leave), `js/arena/arenastate.js` (`stopLook`), `js/arena/stacks.js` and `js/arena/field.js` (a linked card's ring), `js/arena/motion.js` (the hand's leave), `js/arena/arena.css`; new `tests/test_stop_link_desktop_browser.py` |
| **C. Phone** | §1, §3, §4 | `pwa/shell-stops.js` (the raised card's line; the fan's leave), `pwa/shell-arena-words.js` (the line's words, if it is theirs), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_stop_link_browser.py` |

## 1. What a stop is about (its targets)
- `failed`, `pick`, `result`: **its task** (`<goal>/<task>`).
- `plan`, `asks`, `proposal`, `todo`, `goal`: **its goal's cards on the field** (every card of that goal; in Planning or
  Solo, the goal's Planning card).
- A stop of **another party**, Operations' stops, `party`: none (they are not on this field).
- A target not drawn now (scrolled out of its column, another stage on the phone, inside a stack not spread): the stack
  that holds it when that is drawn, else none.

## 2. The desktop: the ring while a stop is looked at (B)
1. A stop is **looked at** while it is raised: the pointer over its `.arena-hc`, or the focus in it (the same moments
   its card rises, `arena.css`'s `:hover, :focus-within`). `arenastate.js` gains `stopLook` (the stop's key or `""`),
   set on `pointerenter`/`focusin`, cleared on `pointerleave`/`focusout`.
2. Its targets wear **`is-linked`**: a **2-px ink outline, 2 px outside** the card (`--ork-ink`; no colour: a link is
   not a signal), drawn and taken away at once (no transition). Nothing moves, nothing else dims.
3. With a target, the stop's card says it in its label's end: *, its task is ringed on the field* (only in
   `aria-describedby`'s text, not drawn). With none, nothing.
4. The dependency arrows (spec 50) are not drawn for it.

## 3. The phone: the raised card names its task (C)
1. The raised card's goal line (`.raised__goal`) is **always drawn** when the stop has a target (§1), not only for
   another party's: *<goal's short name> · <task's title>* for a task's stop, *<goal's short name>* for a goal's, with
   the task's member after a middle dot when it has one (*· Artist*). Another party's stop keeps *<party> · <goal>*.
2. One line, cut with an ellipsis, muted ink, under the banner (where it stands today).

## 4. The answered stop leaves with its task's change (B, C)
1. Today the answered stop is gone in the render that rereads the Board, the same render that changes its task's
   card (`refreshShell` / `refresh`). Keep it so: **no optimistic removal**, no change before that render.
2. In that render the stop **leaves where it stands**: a ghost of its card fades in place (opacity 1 → 0, **steps(4),
   0.30 s**, spec 49 §11.2's fade without its ✓), then the hand closes the gap as it does today. Its task's card
   changes in the same frame (its foot, its edge, or it leaves its column), so the eye reads one change.
3. The raised stop on the phone is lowered at the press as today; the fan's ghost fades in its place in the fan.
4. No fade under `prefers-reduced-motion` or while the page is hidden: the stop is simply gone, as today. A stop that
   leaves for another reason (answered elsewhere, withdrawn) leaves the same way.

## 5. Tests
- **B** (1 440 × 900): hovering a pick's stop rings its task's card (`is-linked`, an outline of 2 px, no transition) and
  no other; a plan's stop rings its goal's Planning card; another party's stop rings nothing; focus by keys rings the
  same; leaving the stop takes the ring away; an answered stop leaves a fading ghost in the render where its card
  changes, none under reduced motion.
- **C** (390 × 844): a stop of the party shown names its goal and task in its raised card (and the member); another
  party's keeps *<party> · <goal>*; an answered stop's ghost fades in the fan; reduced motion.
- Browser tests wait for state. Each part also runs the critical tests (`orkcraft.toml` `always`),
  `tests/test_gui_wording.py`, `tests/test_design_system.py`, and the phone `tests/test_pwa.py`.

## 6. Not in this spec
- A stop flying onto its task, its task lit after the answer, a stamp on it (decisions §65.8, §71).
- Arrows from the hand to the field.

## 7. As built
