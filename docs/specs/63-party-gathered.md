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
