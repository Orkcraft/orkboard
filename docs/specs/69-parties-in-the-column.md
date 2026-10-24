# Spec 69 — On the desktop the left column is the parties: each a heading, the open one's goals under it; the project takes the top line

The owner, 24 October (decisions §84), on the window as built: the left column's top line (*Контент для … 0/5 ·
Parties ⌄*) cuts the party's name and keeps the other parties behind a deck, though a project has few and a goal's route
(spec 68) goes through them. So **the desktop's left column becomes the list of the parties**: a heading for each, the
one the board shows open with its leader, *Process now*, its goals and the New goal pile under it, and **the project
switcher takes the column's top line**. **Builds:** Claude · **Review:** full · P1.

**What it is, and is not:** the desktop's face only (no command, key, setting or storage changes; the host's answers as
today). Not: the phone (its deck and sheet stay, decisions §84); more than one party open; a goal moved by dragging it to
another party's heading; a new place for the Target, Agents, Files, Spend or Stop all.

One part, **B. Desktop**. Spec 68's B (the route, *k flags wait for a release*) is built **after** this one, in this
column. **This file is the contract**; the rest is the builder's choice inside its files. **Change nothing outside its
files** but those §6 names.

| part | builds | files (and their tests) |
|---|---|---|
| **B. Desktop** | §1–§5 | new `js/arena/partylist.js` (the list: the headings, the open party's body), `js/arena/goals.js` (`Left` becomes the open party's body; the pile at its foot), `js/arena/goaltabs.js` (the deck and the parties' spread go; `shownOf`, `othersStops`, the gather kept and pointed at the heading), `js/arena/arenastate.js` (only if the gather's target needs it), `js/arena/arena.js` (the column's wiring), `js/shell/topbar.js` (the project switcher leaves it), `js/shell/projects.js` (`ProjectSwitcher` at the column's width), `js/arena/arena.css`, `js/shell/shell.css`; new `tests/test_party_list_desktop_browser.py`, and the desktop browser tests that press *Parties ⌄*, read `.arena-ptop*` or `.arena-hero*`, or find the project switcher in the top bar (§5) |

## 0. The words
New strings: *Parties* (the list's name, for a screen reader), *Open <party>* (a closed heading's title), *<party> is
open* (the open heading's), *k of n goals done* (a heading's *k/n* tooltip, as today), *n wait in <party>* (a closed
heading's sign's title; *1 waits in <party>*). Every other word is today's: *+ New party*, *Operations*, *Process now*,
*Judge now*, *New goal*, *Goals*, *Pitches*, *Show all*. *deck*, *spread*, *pile* stay out of what a person reads.

## 1. The column (decisions §84.1, §84.3)
1. From the top: **the project switcher** (today's `ProjectSwitcher`, its button as wide as the column, the project's
   name in the pixel face, never cut under two lines; its menu as today: the open projects with what waits in each, the
   recent ones), then **the parties**, in the Board's order (`partiesOf()` as the deck had them), then **Operations**
   when the project has them, then **+ New party** (opens New party as the spread's card did).
2. The column's width is today's; it scrolls on its own when the open party's goals are longer than the window, the
   project's line staying at its top (sticky), the board never scrolling with it.
3. The top bar loses the project switcher: *Orkline*, the Target, the spacer, Agents, Files, Spend, Stop all, the gear.
   With no project (the start screen) the column is not drawn, as today.

## 2. A party's heading (decisions §84.1)
1. One button per party, `aria-expanded` (true for the open one), `aria-current="true"` on the open one, 40 px high at
   least (two lines of name: as high as it needs): **its leader's head** (orkUI's `Head`, 24 × 22, the race and tier as
   the leader's member row has them), **its whole name** (the text face; two lines, then cut with its title holding the
   whole), **k/n** (muted, its tooltip *k of n goals done*), and at its right **one sign** when something waits in it
   that cannot be seen (a closed party: its stops, `othersStops`' count for that party; ✗ in the danger colour when one
   failed, else !; its title *n wait in <party>*); the open party's heading has no sign (its stops are seen below).
   A party at work (a task running) shows the work sign before *k/n*, as the deck's top line did.
2. A press on a closed heading **shows that party** (the board switches as the deck's card did: `keepGoal`, the party
   kept per device, the picks of the party left behind as today) and opens it; the one open before closes. A press on
   the open heading does nothing (it is not a toggle) but for a screen reader's announcement.
3. Ideation's and Operations' headings are the same; Operations has no *k/n* and no leader's head (its icon as the
   deck's Operations card had).
4. Keyboard: the headings are in the Tab order; ↑ and ↓ move between headings when one has the focus; Enter or Space
   presses.

## 3. The open party's body (decisions §84.2, §84.4)
Under its heading, indented by the head's width:
1. **Its leader**: the member's row as `members.js` draws a member (its head with its three signs, its name, its two
   numbers; the peek on hover, solo on a press), in place of today's big leader card (`.arena-hero` and its deck edges
   go).
2. **Process now** (in Ideation **Judge now**), as today's button and words.
3. **Its goals**, as today's `Left`'s section: *Goals*/*Pitches* with its count and *Show all*, *At work*, *Planning*,
   *New (n)*, the Flags fold; a goal's row, its filter, its peek: unchanged.
4. **The New goal pile at its foot**, as today's (`NewGoal`: the types dealt from it, a blank goal last; Ideation's *a
   pitch to judge*).
5. Switching party **draws the new party's body in place** (no motion of its own: the board's own redraw as today);
   under `prefers-reduced-motion` as well.

## 4. The gather (spec 63 §3)
A new party saved from New party becomes the open party, and its seats' heads **gather onto its heading's head**
(`.arena-plist__head` of that party, its centre, at 0.4 as onto the deck), the rest of spec 63 §3 unchanged (6 s, at
most six, none under reduced motion, on a hidden page, after *Edit the party*'s save).

## 5. Tests
- New `tests/test_party_list_desktop_browser.py` (1 440 × 900, the stub host of the arena's tests): three parties and
  Operations listed in order with *+ New party* last; the project switcher at the column's top and not in the top bar;
  the open party's heading `aria-current`, its leader's member row, *Process now*, its goals and the pile at its foot;
  a long name on two lines, not cut, its title whole; a closed party with a stop shows ! with *1 waits in <party>*, a
  failed one ✗ in the danger colour; a press on a closed heading shows that party (the board's columns are its team's)
  and closes the other; a press on the open heading changes nothing; ↑/↓ and Enter; the column scrolls with the
  project's line staying; Ideation's body with *Judge now*; Operations shows Operations; New party's gather lands on
  the new heading's head (and none under reduced motion).
- The desktop browser tests that press *Parties ⌄*, read `.arena-ptop*`, `.arena-hero*` or the deck's edges, or find
  the project switcher in `.shell-top` are changed to the list (each keeps what it proves): among them
  `test_arena_decks_desktop_browser.py`, `test_arena_desktop_browser.py`, `test_goal_types_desktop_browser.py`,
  `test_party_gather_desktop_browser.py`, `test_ideation_desktop_browser.py`, `test_mixed_parties_desktop_browser.py`,
  `test_own_parties_desktop_browser.py`, `test_party_price_desktop_browser.py`, `test_party_proposals_desktop_browser.py`,
  `test_one_hand_desktop_browser.py`, `test_ops_desktop_browser.py`, `test_stop_link_desktop_browser.py`,
  `test_type_top_right_desktop_browser.py`, `test_map_desktop_browser.py`, `test_recap_desktop_browser.py`,
  `test_week_desktop_browser.py`, `test_races_browser.py`, `test_shell_browser.py`, `test_board_browser.py`
  (grep them; change only what reads what moved). The phone's tests are not touched.
- The critical tests (CLAUDE.md "Alpha"), `tests/test_gui_wording.py`, `tests/test_design_system.py`.

## 6. Outside the part's files
- `docs/decisions.md` §84 and this file are the contract. `js/arena/spread.js` keeps dealing a stack and the types; the
  parties' spread's code goes from `goaltabs.js` only.

## As built
Part B, on the desktop only; the files are §0's table's, no host, command or storage change.
- **`js/arena/partylist.js`** (new) draws the column: `.arena-left` is an `aside` named *Parties*; its top line `.arena-left__proj` holds `ProjectSwitcher`, under it `.arena-plist` (the part that
  scrolls, its scroll kept across the redraw a switch makes) with a `.arena-party` per party: the heading `.arena-phead` (`data-goal`, `aria-expanded`, `aria-current` on the open one; its head
  `.arena-plist__head` 24 × 22, `.arena-phead__name` two lines then cut with the whole name in its title, `.arena-phead__work`, `.arena-phead__count`, and on a closed party `.arena-phead__stop`: orkUI's
  `cross` sign in the danger colour when one failed, else `alert`; title *n wait in <party>*), the open party's body under it, then Operations and `.arena-pnew` (*+ New party*). A press on a closed heading
  does what the deck's card did (`leaveParty()`, `track`), on the open one nothing; ↑ and ↓ move between the headings and *+ New party*. The `track` and `keepGoal` effects and the gather moved here from `PartyTop`.
- **`goaltabs.js`** keeps `shownOf`, `partiesOf` (now exported), `othersStops` (kept as the spec says; nothing in the list calls it, a heading takes its own count) and `gatherInto` (exported, aimed at the
  heading's head, which is lit once). The deck, `PartiesSpread`, `PartyCard`, `deckEdges` and `partiesLabel` are gone. **`goals.js`** `Left` is the body (`.arena-pbody`: the leader's `Member` in `.arena-lead`,
  *Process now* / *Judge now*, the goals, the pile); `.arena-hero` and its edges are gone. **`arena.js`** wraps `Left` in `PartyList`; Operations and the no-party note are drawn beside the same list
  (`.arena-ops__main`). **`topbar.js`** no longer draws the switcher; `shell.css` makes it as wide as the column, its name on two lines at most.
- The column's own scroll is `.arena-plist`, under the project's line (the line is not `position: sticky`: it sits outside the scrolling part, so its menu, wider than the column, is not clipped).
- Tests: `tests/test_party_list_desktop_browser.py` (12); the helpers `_parties`, `_party_card`, `_new_party`, `_show_goal` in `tests/test_shell_browser.py` and the desktop tests that read the deck, `.arena-ptop*`,
  `.arena-hero*` or the top bar's switcher now read the list. Under reduced motion nothing gathers: `test_party_gather_desktop_browser.py` keeps that test.
- A goal row's peek (`goals.js` `GoalRow`) now follows a pointer *move* (`mousemove` with movement) instead of `mouseenter`: a switch draws the new body under the heading just pressed, and a pointer at rest
  under it peeked a row and left the board's column stuck mid-fade. A project with no party still draws the column (the project's line and *+ New party*), since the switcher lives there now.
