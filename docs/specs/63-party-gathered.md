# Spec 63 — The party gathered: what it can take, shown as its seats are picked; a new party's heads gather into the deck

The owner, 23 October (decisions §76): *put the accent on gathering the party; maybe a motion too, like folding into a
deck, as the start of a goal's work has.* Picking a party is the person's first and largest choice (who plans, who
builds, who checks; what a goal costs), and New party says what it costs (spec 43 §3) but not **what it opens**: the goal
types the party will be offered (spec 59 §4.3) are seen only after it is saved, in New goal's spread. And its saving is a
dialog that closes. So: **New party and Edit the party say what the party can take, as its seats change** (a type a seat
has just opened lit once); **a new party saved gathers its heads into the party's deck** — spec 57's deal the other way
round, one of the three moments that travel (decisions §76.3). **Builds:** Claude · **Review:** full · P2.

**What it is, and is not:** one more field in `ideas.party_price`'s answer (the goal types of a leader and a team not
saved), one line in the party's forms on each face, one motion on New party's save. No new command, setting, storage or
word in the glossary. Not: picking a type from New party; a sound; a motion on *Edit the party*'s save.

Three parts. **A first; B and C once A is in `main`** (a host without `types` draws no line, so B and C can be built
against their tests' fake host at once, and are merged after A). B and C touch no file of each other's.

| part | builds | files (and their tests) |
|---|---|---|
| **A. Host** | §1 | `gui/ideas_party.py` (`party_price`'s `types`), `realm/goal_types.py` (a `Party` read from a leader and a team not saved; `offered` and `missing` answer as today); `tests/test_party_price.py`, `tests/test_goal_types.py` |
| **B. Desktop** | §2, §3 | `js/shell/party.js` (the line *It can take*), `js/shell/goalwizard.js` (the line; the gather's boxes at the save), `js/shell/goaldialog.js` (the line), `js/arena/arenastate.js` (the gather waiting), `js/arena/goaltabs.js` (`PartyTop`: it plays onto the deck), `js/arena/motion.js` (the header's list of what moves), `js/shell/shell.css`, `js/arena/arena.css`; `tests/test_party_price_desktop_browser.py`, new `tests/test_party_gather_desktop_browser.py` |
| **C. Phone** | §2, §4 | `pwa/shell-goal-new.js` (the line; the gather's boxes at the save), `pwa/shell-where.js` (the deck it lands on), `pwa/shell-motion.js` (the gather), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; `tests/test_pwa_party_browser.py`, new `tests/test_pwa_party_gather_browser.py` |

## 0. The words
New strings, in these words: *It can take*, *with one more*, *needs <agent>*, *nothing of its own yet: add a builder*.
A type is said by its name and drawn with its sign, as New goal's spread draws it.

## 1. The host (A)
1. `ideas.party_price`'s answer gains **`types`**: what a party of this leader and this team would be offered (spec 59
   §4.3's `offered`, unchanged), each `{id, name, sign, missing}` with `missing` the name of the agent it needs (`""` when
   nothing is missing), in `offered`'s order (the catalog's: a party not saved has no goals to sort by use).
2. The party is read from the call's `leader` and `team`, not from a saved party: `goal_types.Party` gains a way to be
   made from a leader and a team (`Party.of(state_dir, root, leader, team)`, or a builder's equal), with no slug, no open
   work (`busy()` empty) and no runs; `offered(..., read=that)` and `missing(..., read=that)` answer from it. Edit the
   party's call (the seats as edited) is read the same way.
3. A refusal of today (an unknown leader, seats that do not fit) refuses as today; `types` is never asked of a refused
   party.
4. `tests/test_party_price.py`: the Game preset's leader and team answer spec 59 §4.3's Game list; the Taskmaster alone
   answers New feature, Fix a bug, Clean up; a Mobile app team without the Design system designer answers *New screen*
   with `missing` *Design system designer*; an agent added to the team that opens a type adds it.

## 2. *It can take* (B, C)
1. Under the price line of **New party** and **Edit the party** (the desktop's `PriceLine`, the phone's price box): a
   line **It can take:** then the types with nothing missing — each its sign (small, muted ink) and name, joined by
   *·* — and, when there are some, **with one more:** then the types that miss someone, each *<name> (needs <agent>)*.
   No type: *It can take: nothing of its own yet: add a builder.* Never more than two lines on the desktop (three on the
   phone); what does not fit ends with *and k more* (its title lists them all).
2. It follows the seats: it is redrawn from each answer of `ideas.party_price` (asked as today: at once, then 300 ms after
   a seat or *Every goal* changes). **A type that the last change opened is lit once** (the quiet reward's look: ink →
   its background, 0.6 s, steps(4)); a type that went is simply not drawn. Nothing is lit at the first answer.
3. An older host with no `types`: no line.

## 3. The desktop: the gather (B)
1. **At *Save party*'s press in New party** (`goalwizard.js`), the gather keeps the boxes of the seats' heads
   (`.shell-team-seat` with a head: the leader first, then the builders, then the checkers; **six at most**) and each
   head's race and tier. When `ideas.goal_save` answers a slug, **a gather waits** (`arenastate.js`, as spec 57's deal
   waits): `{party: slug, from: [{race, tier, box}], at}`; dropped after **6 s**, at a refusal, or once played. None when
   New goal opens right after the save (`then: "idea"`: the form is what the person looks at).
2. **It plays in the first render of `PartyTop` that shows that party**, once the dialog has closed: each head, a copy
   over everything (no scrim, `pointer-events: none`), travels from its seat's box to the deck (`.arena-ptop__deck`),
   **steps(6), 0.30 s, 35 ms apart**, the leader first; each ends at the deck's centre at 0.4 of its size and is gone on
   landing. When the last lands, the deck is **lit once** (0.6 s, steps(4), as the quiet reward). The copies are then
   removed.
3. Nothing waits for it: the party is shown and usable at once, About this party opens in the drawer as today.
4. **No gather** under `prefers-reduced-motion`, on a hidden page, after *Edit the party*'s save, or for a party saved on
   the phone. A head whose seat was not on screen at the press (the dialog scrolled) starts from *Save party*'s box.
5. `motion.js`'s header lists what moves: the deal's line says *one of the three moments that travel (decisions §76.3)*
   in place of *the one motion that travels*, and a line is added for the gather.

## 4. The phone: the gather (C)
1. At *Save party*'s press (`shell-goal-new.js`), the boxes of the party's heads as the sheet shows them (the folded
   party line's heads, or the open fold's taken seats; the leader first, six at most; a head not on screen starts from
   *Save party*'s box), kept after the host answers a slug: `{party, from, at}` in `shell-motion.js`, beside the deal;
   dropped after 6 s, at a refusal, or once played.
2. It plays in the first draw after the sheet has closed where the goals bar's deck (`.partydeck`, `shell-where.js`)
   shows that party (`data-goal`): the heads travel to the deck as §3.2 (the same timing), the deck lit once (`.is-reward`).
3. No gather as §3.4 (reduced motion, a hidden page, a party's team changed from its own screen).
4. `sw.js` `CACHE` one up from what `main` has, with `tests/test_pwa.py`'s pin.

## 5. Tests
- **A**: §1.4.
- **B** (browser, 1 440 × 900): *It can take* in New party for the Game preset (its types, no *with one more*), a Mobile
  app's *with one more: New screen (needs Design system designer)*, a seat taken in that opens a type (the line has it,
  lit once: an animation on it), the Taskmaster alone, an older host (no line); Edit the party has the line; *Save party*
  in New party: copies of the heads travel (their first box near a seat's, their last near the deck's), six at most, the
  deck lit, the copies gone after; Edit the party's save: no copy; reduced motion: no copy.
- **C** (browser, 390 × 844): the line on New party's sheet; the gather onto `.partydeck`; reduced motion; the service
  worker's version.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`; C also `tests/test_pwa.py`.

## 6. Not in this spec
Picking a goal type from New party; a gather on Edit the party; a sound; the library's tiles moving.

## 7. As built (notes, no change of the contract)

**A (the host), 23 October.** §1 built as written. What the builder chose or found:
- `goal_types.Party.of(state_dir, root, leader, team)` is the party not saved: slug `""`, the leader (the Taskmaster for `""`) and
  the team as given (copied), the leader's craft, and `_busy` and `_week` set empty so `busy()` is empty and `runs()` is 0 without
  a read (`ideas.ideas(root, "")` is never asked). `offered(state_dir, root, "", read=Party.of(...))` answers from it; so does
  `missing(..., read=...)`, whose `out` then lists every member of the band, none holding, none with runs.
- **What the spec did not say, and the answer needed: a library agent the project does not have yet.** `met` reads the project's
  role files, and a library agent becomes a role only when the party is saved (`ideas_goals.py` installs it). Read as `met` has it,
  the Game preset in a project that has none of its agents answered *New feature, Fix a bug, Clean up* only. So `Party` gains
  **`fresh`** (the members that are the library's and not yet the project's, set by `Party.of`; `()` for a saved party) and
  **`meets(kind)`** (`met`, or a `fresh` member's library `takes`), as `party_price._who` reads a library agent not installed yet.
  `missing`, `offered`, `lacking` and `still_missing` ask `p.meets(kind)`; for a saved party `fresh` is empty, so they answer as
  before. Nothing is installed or saved by the call (`tests/test_party_price.py` checks it).
- `ideas.party_price` builds the `Party` and asks `offered` after the refusals, so a refused party never reaches `types`.
  `types` is `[{id, name, sign, missing}]` in `offered`'s order (the catalog's: *New screen* of a Mobile app sits after *Clean up*,
  not last); `missing` is the `name` of the first (the only) row of the type's `missing`, `""` with none. A type whose name two
  catalog entries share (*New feature*) is told by its `id`.
- A leader of the person's own is refused as today (`library.get` does not know it); a member of the team of the person's own is
  read through its role file (its `takes`), as a saved party's.
- Tests: `tests/test_party_price.py` (§1.4: the Game preset, the Taskmaster alone, a Mobile app, an agent added; also nothing saved
  or installed, and a refused party never asks `Party.of` or `offered`; the answer's keys now include `types`) and
  `tests/test_goal_types.py` (`Party.of`; a party not saved offers what the same party saved does, in a project that has its agents
  and in one that has none).

**C (the phone), 23 October (`orkcraft-app-v68`).** §2 and §4 built as written. What the builder chose or found:
- **The line is `makeParty`'s**, so New party's sheet and *The party*'s (a party's team changed from its own screen) draw it from the one place, under `priceLine()`: `takesLine()` in
  `shell-goal-new.js`. The types with nothing missing each as `.take` (`.ork-sign.<sign>` at 12 × 12 in the muted ink, then the name), joined by *·*; then `, with one more:` and those that miss
  someone as *<name> (needs <agent>)*; none at all, *nothing of its own yet: add a builder.* (with only missing types: *…add a builder, with one more: …*); an older host (no `types`): no line.
  The missing types also have their sign. **Three lines** are measured, not counted: `fitTakes()` runs once the line is in the page (its sheet open) and takes types off its end until the line
  is three lines high, the rest said *and k more* (its title lists all, with their *(needs …)*). So a long list falls from the end: at 390 px the Mobile app's *with one more: New screen (needs Design
  system designer)* is behind *and 5 more*, and the Data party's *A new metric · A report, with one more: An A/B test (needs Experimenter)* fits whole.
- **Lit once** is `pulse()` (the quiet reward, `.is-reward`), on the `.take` nodes whose ids the answer has and the answer before did not. *Nothing lit at the first answer* needed care: the
  sheet asks twice as it opens (`set()` for the Taskmaster alone, then `preset(craft)` 300 ms later), so `askPrice(now, lights)` takes **`lights`**: both are `false` (`preset(craft, false)` from
  `open()`), their answers are the baseline; a seat, a craft tile, a party picked, *Every goal* ask with `lights` true. The light is drawn once (it is used up by the draw that shows it: a fold
  opened or a redraw does not light it again); none when `motionOn()` is false.
- **The folded party line has no heads** (spec §4.1 says *the folded party line's heads*; it is text: *Leads: … · Builds: …*). What the sheet shows of the party's heads at the press is: the
  **open fold's taken seats** (`.team-seat`), else the **tile of the library party picked** (`.preset-tile` heads, 24 × 22) or the **chip of your own party picked** (`.own-chip` heads, 12 × 11).
  Those heads carry `data-agent` (`tag()`), and `gatherFrom()` looks each member up by it, in that order, taking the first whose box lies inside the sheet's view above the pinned foot; any other
  head — a member whose fold is shut and whose tile is not on screen, the row of crafts (an older host: it draws one head a craft, not the party's) — starts from the middle of *Save party*'s box, at
  24 × 22. The party is `makeParty.heads()`: the leader first, then the team in its order, six at most, each `{race, tier}` as the seats draw it.
- **The gather is `gather` in `shell-motion.js`** beside `deal` (`wait(party, from)`, `live()`, `drop()`; 6 s) and **`gatherTo(waiting)`**, played by `shell-where.js` `deck()`: in the first draw that
  builds a deck whose `data-goal` is the waiting party, the gather is dropped and (not under reduced motion or a hidden page) played on the next animation frame, when the deck is in the page. A
  copy is an `img.gather-fly` (`races/<race>-<tier>@2x.png`, `position: fixed`, `z-index: 60`, `pointer-events: none`, `animation: gather 0.30s steps(6) var(--delay)`) at its head's box with
  `--dx --dy` to the deck's centre and `--s: 0.4`; it is removed at `animationend` (and by a timeout); the deck is `pulse`d when the last has landed (found again by its `data-goal`: a draw in
  between replaces the node). `test_design_system.py` needed nothing new (`--dx --dy --s --delay` are allowed already).
- **Kept waiting only for a party the person is shown**: not when New party was opened by New goal (`then`, as §3.1's `then: "idea"`: the form is what the person looks at), not at a refusal
  (`gather.drop()`), not when the press had motion off (no boxes read).
- **Found: the party's own screen covers the deck.** After *Save party* the phone opens the party's screen (`core.open`, `.screen`, fixed, over the whole Board) at once, so the deck is under it:
  the heads fly over that screen (`z-index: 60`) to where the deck is and are gone there, and the deck's light is lit under it, not seen until *Back*. Built as the spec says; showing the deck
  would take one of: opening the party's screen only after the gather (about 0.5 s), or not opening it after a save from the parties' sheet. Not done: the spec did not ask for either.
- **`sw.js` `CACHE`** is `orkcraft-app-v68`; its pin is also in the five browser tests that pinned v67 (`test_pwa_mixed_parties_browser`, `test_pwa_deal_start_browser`,
  `test_pwa_goal_types_browser`, `test_pwa_one_hand_browser`, `test_pwa_board53_browser`), beyond `test_pwa.py`.
- Tests: `tests/test_pwa_party_browser.py` (8 more: the line under the price for the Game preset, three lines and *and k more* with the title, signs; *with one more* and *(needs …)*; the
  Taskmaster alone; no type; an older host; a seat taken out and in lights the one type once (`window.__lit`), nothing lit by the opening, nothing under reduced motion; the party's own
  sheet) and new `tests/test_pwa_party_gather_browser.py` (the Game's six heads from the tile's boxes, the order, delays, `steps(6)`, 0.30 s, `fixed`, over the screen, to the deck's centre at 0.4,
  gone, the deck lit once after the last; heads out of sight from *Save party*; an open fold's seats and the shut folds' members from the button; the row of crafts; your own party's chip;
  reduced motion; a refusal; a gather of 1 s that plays and one of 6.4 s that does not; New goal taking the party; a team changed from the party's own screen; the service worker's version).
  The fake host answers `types` as `gui/ideas_party.py` does, from the realm (`goal_types.Party.of` and `offered`): `typed()` in the party test file.
