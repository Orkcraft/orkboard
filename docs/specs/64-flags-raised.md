# Spec 64 — The flags raised: a goal's end travels from the gate to the flag line

The owner, 23 October (decisions §77): *is there a motion when a goal is done, and should there be one? Then three big
motions: the party picked, the work started, the work done.* A merged task fades where it stands with a one-frame ✓ and
its member's number lights once (decisions §62.8's quiet reward); a goal's end — **its flag raised** when the gate takes it
into main (§63.3) — only makes the flag line stand (spec 50 §3.8, §6.8), still. So: **when the flag line first stands, its
goals' elements travel from the gate to the line, the line's flag is raised and the line lit once** — the third of the
three moments that travel (decisions §76.3). **Builds:** Claude · **Review:** full · P2.

**What it is, and is not:** one motion on each face, played by the client from what it already reads (`ideas.flags`' goals
on the desktop, the map's flags on the phone, each goal's `element` from the map); the flag line gains a row of its goals'
elements. No host change, no new command, word, setting or storage. Not: a sound, confetti, a colour outside the office's,
a motion for a task merged (the quiet reward stays) or for a goal done in dev (it waits for main).

Two parts; they share no file.

| part | builds | files (and their tests) |
|---|---|---|
| **B. Desktop** | §1–§3 | `js/arena/flags.js` (the raise waiting: the line's goals and the gate's box), `js/arena/partyline.js` (`FlagLine`: the row of elements, the raise, the light), `js/arena/gate.js` (the box of the merge's press), `js/arena/motion.js` (a line for the raise in the header's list), `js/arena/arena.css`; new `tests/test_flags_raised_desktop_browser.py`, and the desktop tests that read the flag line (only if they need it) |
| **C. Phone** | §1, §2, §4 | `pwa/shell-party.js` (`flagNode`: the row, the raise, the light; the gate's box), `pwa/shell-gate.js` (the box of the merge's press), `pwa/shell-motion.js` (the travel), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_flags_raised_browser.py`, and the phone tests that read the flag line (only if they need it) |

## 1. What travels
1. **The moment**: the flag line stands for the first time on this device for these flags (the once that exists today:
   spec 50 §3.8 on the desktop, §6.8 on the phone). Never at a later draw, never after a reload (the mark is written when
   the line first stands).
2. **What**: up to **six** of the line's goals (in the line's order, the newest first), each as its goal's **element**
   (`.ork-elem`, small: the goal's `element` from the map, shape and colour), a copy over everything (no scrim,
   `pointer-events: none`).
3. **From the gate**: the box of the merge's press in the gate's screen, read at that press and kept **10 s** (the person
   merged a moment ago); else the gate's button (desktop `.arena-gate__btn`, phone `.gbar__gate`) when it is on screen
   and not under the drawer or a sheet (the element at its centre is it); else **nothing travels** (§2.3 still plays).
4. **To the flag line**: each element lands in a row of small elements after the line's flag sign, in the line's order.
   That row is the line's from now on: drawn still when the line is drawn again, and under reduced motion.

## 2. How it moves
1. Each element from the source box's centre to its place in the row: **steps(6), 0.30 s, 35 ms apart** (spec 57 §2's
   deal), scaled from the source box's height to its own.
2. More than six flags: the seventh and the rest have no element in the row; the words say them (*and k more*, today's).
3. When the last element lands (at once when nothing travels): the line's flag sign is **raised** — it steps up from 6 px
   lower to its place, steps(3), 0.18 s — and the line is **lit once**: ink → its background, 0.6 s, steps(4) (the quiet
   reward's look).
4. None of it under `prefers-reduced-motion` or on a hidden page (the line stands with its row, still). Nothing else on
   the page moves; the line and its close are usable at once.

## 3. The desktop (B)
- `flags.js` keeps **a raise waiting** when it makes `flagLine` stand: `{goals: [{slug, element}], from: box | null, at}`;
  `gate.js` keeps the merge's press box for 10 s.
- `FlagLine` draws the row and plays the raise once (dropped once played, or after 6 s).
- `motion.js`'s header gains a line for the raise (*the flags raised: one of the three moments that travel, decisions
  §76.3*), after the gather's line when spec 63's B is in (else after the deal's).

## 4. The phone (C)
- `shell-party.js` `flagNode`: the row, the raise and the light, once; its source the box `shell-gate.js` kept at the
  merge's press (the gate's sheet closes after the merge, so the box is read at the press), else `.gbar__gate`.
- `sw.js` `CACHE` one up from what `main` has, with `tests/test_pwa.py`'s pin.

## 5. Tests
- **B** (browser, 1 440 × 900): a merge from the gate's screen that raises two flags: two copies of the elements travel
  (their first box near the merge's press, their last in the line), the flag sign raised and the line lit (animations on
  them), then the copies gone and the line's row has the two elements; a reload: the line does not stand again (as
  today); eight flags: six in the row and *and 2 more* in the words; no gate on screen: no copy, the flag still raised;
  reduced motion: no copy, no animation, the row drawn.
- **C** (browser, 390 × 844): the same from the phone's gate.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`; C also `tests/test_pwa.py`.

## 6. Not in this spec
A motion for a goal done in dev; a task's merge (the quiet reward stays); a sound.

## 7. As built (notes, no change of the contract)
