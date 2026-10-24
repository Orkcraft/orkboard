# Spec 71 — The Orkmaster keeps the parties from colliding: an overlap before the work, a spec changed under another party, a goal that waits for another party's

The owner, 24 October (decisions §86): *the Orkmaster coordinates the parties' work and the changes in their specs, so
they do not collide.* Each party's leader sees its own goals; two parties' goals that change the same thing meet only at
the gate. So the Orkmaster (spec 70) **finds** what two open goals of different parties both touch, **asks** the person
what goes first, **tells** a party when another party's spec changed under it, and lets a goal **wait** for another
party's flag. Code finds, a model of the cheaper tier judges, the person decides. **Builds:** Claude · **Review:** full ·
P2. **Written, not built**: after spec 70 is seen at work (the owner's call).

**What it is, and is not:** one finder (code), one judge (a model call, cheap tier, only when the finder found
something), one kind of stop in the hand (`collide`), a goal's `depends_on` that may name another party's goal, and its
lines on the project's level. Not: the Orkmaster editing another party's spec or plan; anything held, merged or re-planned
without the person's answer; a model call on every event; reading the stores, the web or another project.

Three parts. **A first**; B and C from `main` once A is in (they share no file).

| part | builds | files (and their tests) |
|---|---|---|
| **A. Host** | §1–§5 | new `realm/collide.py` (what a goal touches, the overlaps, the kept answers), new `core/idea_collide.py` (the judge: the prompt, the call, the answer read), `realm/orkmaster.py` (its role: `orkmaster` installed as a role of the project, `warrior`, takes no task), `realm/board_map.py` (Needs you's `collide`; a node's `waits_for` across parties), `realm/ideas` readers of `depends_on` (a goal of another party held until its flag), `gui/ideas_project.py` (`ideas.collide_answer`), the hooks at a plan made and at a spec changed after the start (`core/idea_change.py`'s caller), `realm/event_log.py`, `realm/lexicon.py`; new `tests/test_collide.py`, `tests/test_idea_collide.py` |
| **B. Desktop** | §6 on the desktop | the hand's `collide` stop (its two goals, its answers), the project level's links (spec 70 §2.3) drawn for a collision and a wait, a goal row's *waits for <party> · <goal>*; new `tests/test_collide_desktop_browser.py` |
| **C. Phone** | §6 on the phone | the same as the phone's hand and goal rows draw a stop and a wait; `pwa/sw.js` `CACHE` one up; new `tests/test_pwa_collide_browser.py` |

## 0. The words
`TERMS` gains `collide` (*collision*: two goals of different parties that change the same thing). New strings: *<party>
«<goal>» and <party> «<goal>» change the same thing*, *<one> first*, *One goal*, *Leave it*, *<party> changed «<goal>»:
«<goal>» in <party> rests on what it was*, *Re-plan it*, *waits for <party> · <goal>*, *Orkmaster asks*.

## 1. What a goal touches (A, code)
`collide.touches(root, state_dir, slug)`: the paths and modules its page's `touches` names (as `core/idea_keeper.py`
reads it), its plan's tasks' files when they name some, and the files its merged tasks changed; normalised (a module
`orkboard/realm/x.py` and its folder `orkboard/realm/` overlap; `tests/` and docs are left out unless both goals are only
docs). Read, never written.

## 2. The overlap, before the work (A)
1. When a plan is made (the event `plan_made`), `collide.overlaps(…, slug)` compares the goal's touches with every open
   goal (not done, not dropped, not a pitch, not a release) **of another party**; none: nothing more (no model).
2. One or more: **the judge** (`core/idea_collide.py`, the Orkmaster's role, the cheaper tier) gets the two goals' titles,
   *Done when* and touches (≤ 3 000 characters) and answers `{"collide": bool, "why": "…" (≤ 200), "first": slug|""}`;
   `collide: false` drops it (kept as answered, never asked again for that pair); `true` is a stop.
3. **The stop** (`collide`, Needs you, `blocks: false`, priority `normal`): the two goals, the why, the suggested first;
   answers **<one> first** (the other's `depends_on` gains it: held until its flag, §4), **One goal** (the later goal's
   text joins the earlier's as a change, spec 62's way; the later is dropped with *joined into «…»*), **Leave it**. Kept
   by the pair (`<state_dir>/collide.json`, the last 200 answers): a pair answered is never asked again.

## 3. A spec changed after the start (A)
When a goal's spec changes after its plan (spec 62's change), its touches are compared with the open goals of other
parties as in §2.1, judged as in §2.2 with the change's words; a collision is a stop *<party> changed «<goal>»: «<goal>»
in <party> rests on what it was*, with **Re-plan it** (that goal's leader re-plans what is left, spec 62's way, the change
told to it) and **Leave it**.

## 4. A goal waits for another party's (A)
A goal's `depends_on` may name a goal of another party; its start is held (as `depends_on` holds today within a party)
until that goal's flag (spec 50 §2.2), and the map's node says `waits_for: [{goal, party}]`. Set by *<one> first* or by
the person (the goal's screen).

## 5. Measured and priced (A)
Events: `collide_found` (pair, by: plan|change, judged: bool, collide: bool, tokens, cost) · `collide_answered` (pair,
answer). The party's work for the project says the Orkmaster's stops answered, taken (not *Leave it*) and its cost a
week. A finder that finds nothing costs nothing; the judge runs only on what it finds.

## 6. Faces (B, C)
- The hand's `collide` stop: the Orkmaster's head, *Orkmaster asks*, the two goals (each with its party, a press opens
  it), the why, its answers as buttons saying what happens.
- The project's level (spec 70): a collision is a link between the two decks in the signal's colour while the stop is
  open; a wait a link with the arrow of *waits for*.
- A goal's row in its party: *waits for <party> · <goal>* with orkUI's ← sign; a press opens that goal.

## 7. Tests
- **A**: touches read and normalised; no overlap no call; an overlap judged (a stub harness), `false` kept and not asked
  again, `true` a stop; each answer (first: the wait held until the flag; one goal: joined and dropped; leave it); a spec
  change judged and *Re-plan it*; a goal of another party in `depends_on` held and then started at the flag; events hold
  no goal's words.
- **B**, **C**: the stop and its answers; the link on the project's level; the wait's line.
