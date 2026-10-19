# Spec 39 — the Map: a project's goals, ideas and tasks on one screen; the preview becomes tabs

The owner, 19 October (decisions §52). The Board shows a project's work as lists: Needs you, the ideas of the chosen
goal, and an idea's tasks only in its spec's Stages. Since spec 35 plans start by themselves and work goes on at night;
since spec 37 D several projects are open at once. What the Board lacks is one look that answers: *how far is each
goal, what waits for what, what moved since I last looked, and what needs my hand now.* This spec adds the **Map**:
every goal of the project as a tree of its ideas, an idea under the ideas it depends on, its tasks as pips, its state
in words. The Map is the preview's first tab, always there; whatever else the preview opens becomes a tab of its own
that closes. **Builds:** Claude (A, B and C on the warrior tier) · **Review:** full · P1.

**What it is, and is not:** a **view**, read from what the Board already holds (the pages, `plan.json`, the claims,
the ledger); it changes nothing and has no action of its own but *open*. It is not a graph editor (decisions §50.3:
a free graph scares the first audience off): its shape is the goals and the ideas' `depends_on`, as the keeper and the
person already write them. The RPG skill-tree look is Orkline Camp's skin over the same data (§52.3), not this spec.

Three parts, one branch each, in this order; **this file is the contract** (names, data, commands); the rest is the
builder's choice inside its files. Wording: CLAUDE.md (one look, Office; today's words: *Map*, *goal*, *idea*,
*task*; a screen named by what it does). **Change nothing outside these files.**

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. Backend** | `spec/39-map-backend` | §1, §2, §6 | new `realm/board_map.py` (the map, a pure function: no face, no model), new `gui/ideas_map.py` (the `ideas.map` command, a mixin like `ideas_goals.py`), `gui/ideas.py` (the mixin and the command), `realm/lexicon.py` (`board_map`), `realm/event_log.py` (`opened` gains `via`) |
| **B. Desktop** | `spec/39-map-desktop` | §3, §4 on the desktop | new `gui/static/js/board/map.js` (and `maplayout.js` if it grows past ~600 lines), new `gui/static/js/shell/tabs.js`, `gui/static/js/shell/preview.js`, `gui/static/js/shell/store.js`, `gui/static/js/shell/shell.js` (Esc), `gui/static/js/shell/projects.js` (a project's tabs on switching), `gui/static/js/shell/shell.css`, `gui/static/js/board/board.css` |
| **C. Phone** | `spec/39-map-phone` | §5 | new `gui/static/pwa/shell-map.js`, `gui/static/pwa/shell-board.js` (the Map button), `pwa/board-app.js`, `pwa/app.css`, `pwa/sw.js` (cache version) with `tests/test_pwa.py`'s pinned version |

B and C branch from A once A is pushed; they touch no file of each other's.

## 0. The words
- **the Map** (`TERMS` `board_map`: *Map*): the project's goals, ideas and tasks on one screen. Not the camp's *War
  Map* nor its *Map view* (the town from above, Orkline's): those stay as they are.
- **a tier**: an idea's row in its goal's tree: 1 for an idea that depends on none of its goal's ideas, else one more
  than the deepest idea it depends on.
- **a tab**: one thing the preview holds (§3). The Map's tab is **pinned**; the others close.

## 1. The map: `realm/board_map.py` (A)
`build(root, state_dir, settings, limits, now) -> dict`, pure (reads files, starts nothing, writes nothing), from what
`ideas.board` reads already plus each idea's `plan.json` tasks:

```json
{"goals": [{"slug", "title", "priority", "state", "done_when": ["…"], "ideas": 9, "done": 4, "usd": 12.4 | null}],
 "nodes": [{"slug", "goal", "title", "state", "queue", "held_until", "start_at", "priority", "size", "risk", "tier",
            "depends_on": ["…"], "waits_on": ["…"], "waits": {"kind", "ref", "title", "until"} | null, "needs_you": "asks" | "plan" | "todo" | "failed" | "proposal" | "",
            "progress": {"done": 2, "total": 5},
            "tasks": [{"id", "title", "state", "after": ["…"], "tier"}],
            "estimate": {"usd_low", "usd_high"} | null, "by_itself": false, "folded": false, "updated": "<iso>"}],
 "edges": [{"from": "<the idea depended on>", "to": "<the idea that depends>"}],
 "rev": "<the board's rev>"}
```

- **goals** in the Board's order (priority, then the person's order); General is never in the Map. `done_when` is the
  goal's Metrics as lines (`metrics` front matter, *done when …*); `usd` is `idea_spend.of_goal`'s sum (`null` when
  unpriced, never 0).
- **nodes**: every idea of those goals, with the fields of its `ideas.board` row that word its state (`state`,
  `queue`, `held_until`, `start_at`, `progress`, `waits_on`), so each face words a node with the function that words
  the Board's row today (the desktop's `js/board/tracks.js` `rowOf`, the phone's `pwa/shell-ideas.js` `rowState`):
  the Map and the Board never word a state twice. The backend writes no words.
- **tier**: by `depends_on` inside the goal (an idea it depends on in another goal draws no edge and gives no tier;
  `depends_on` closes no cycle, spec 35 §3). Inside a tier, nodes go in the Board's order.
- **waits**: why a node that is not done does not move, the first that holds, in this order:
  `{"kind": "you"}` (it is in Needs you: asks, a plan waiting for the person, a to-do, a failure), `"idea"` (`ref` and
  `title` of the first idea of `waits_on`), `"files"` (a task held by the claims: `ref`, `title` of that idea, spec 35
  §5), `"limits"` (`until`: `held_until`, or a held task's reset), `"reserve"` (`until`), `"night"` (queue `night` or
  `start_at: night`), `"stopped"` (queue `hold`), else `null`. `needs_you` names the Needs you kind when it is `"you"`.
- **tasks**: the plan's, with their state (`waiting · ready · running · testing · review · merged · failed · held ·
  dropped`) and `after`; none before a plan is made. `progress` counts merged of all, as the Board's row does.
- **estimate**: the plan's (`plan.json` `estimate`) only while no task of it has started; else `null`.
- **by_itself**: the plan was passed by autostart (`passed_by: "auto"`).
- **folded**: a done idea that no idea still open depends on. The Map shows folded nodes only in its *Done (n)*; a done
  idea that an open one depends on stays in its tier, so every edge has both ends.
- **updated**: `ideas.touched_at`, as the Board's row has it (§3.5 marks what moved since the person last looked).
- Built for a project of 200 ideas in under 200 ms on the fixture (it reads each `plan.json` once; no git call).

## 2. The command (A)
| command | args | returns |
|---|---|---|
| `ideas.map` | `{"goal"?}` (one goal's slug; none: every goal) | §1's object |

- Callable from the phone (`BoardPhone` allows `ideas.*`). With no project open: *Open a folder first*, as the other
  `ideas.*` (spec 37 D).
- `ideas.log` `{"event": "opened", "what": "map"}` is how the page says the Map was looked at; an idea opened from the
  Map is logged `{"what": "idea", "ref": "<slug>", "via": "map"}` (`opened` gains `via`, plain data: `map`, `board`,
  `needs`, `agents`, `review`; old lines read `""`).

## 3. The preview becomes tabs (B)
Today the preview holds one thing at a time, so opening a file loses the spec being read, and the Esc that closes it
loses where one was. From now on it holds **tabs**, as an IDE does (decisions §50.10).

1. **The Map's tab is first and pinned:** always there, no ×, never closed by Esc. It is what the preview shows when
   nothing else is open: it takes the place of today's empty text (*Open an idea, a task or a result*).
2. **Every other thing opens in a tab** (`kind` and its ref, as today's `preview` value: `idea`, `plan`, `task`,
   `result`, `goal`, `doc`, `file`, `gitdiff`). Opening what already has a tab shows that tab (a plan scrolls to the
   to-do asked).
3. **One passing tab:** a thing opened by a click goes into the *passing* tab (its title in italics), replacing the one
   there, so clicking through Needs you or the Map does not pile up tabs. The passing tab is **kept** (upright, stays)
   when the person double-clicks its title, edits in it (a file editor with changes), or presses **Keep** on it. Keep
   follows VS Code's preview tabs, which people already know.
4. **Closing:** × on a tab, a middle click, or **Esc** on the active tab (not the Map; not while typing; not under a
   dialog, as today). A tab with unsaved changes asks first (today's *leave* dialog). Closing shows the tab to its
   left, the Map at the end. `closePreview()` closes the active tab, so every caller that closes the preview after an
   action (a merge, a drop) goes on working.
5. **At most 12 tabs:** a 13th closes the oldest kept tab with no unsaved changes, and says so (*closed the oldest
   tab: <title>*).
6. **A tab's title** is today's head: its kind (*Spec*, *Plan*, *Task*, *Code*, *Goal*, *Document*, *File*,
   *Changes*) and its title, cut with an ellipsis, the whole in its tooltip. The tab strip takes the place of the
   pane's head on the desktop; a result's actions stay pinned at its foot, as today.
7. **Each project has its own tabs**, kept per device (browser storage, `orkboard.tabs.<sha1 of the project's path,
   12 chars>`; read and written in try/catch, and the page works without it): which tabs, which is active, which is
   passing. Switching project shows that project's tabs (`resetForProject` keeps the Map and swaps the rest). Only the
   refs are kept: every tab reads its thing again when shown. A tab whose thing is gone says so (*This idea is gone*)
   with **Close**.
8. **The tab strip** is a `tablist` (arrow keys move between tabs, Enter shows one), so it is reached by keyboard.
9. **Narrow** (below 1 024 px, the phone's layout): no tab strip. The active tab (not the Map) is the full-screen
   preview, as today, and **Back** closes it; the Map is reached by the Board's **Map** button (§5).

## 4. The Map on the desktop (B)
In the Map's tab, in Office's look (monochrome, no art; the camp's War Map is not this):

1. **A section per goal**, in the Board's order (the goal select's *All goals*; a chosen goal shows only its own
   section). Its head: the title, its priority as a mark, its state in words, *4 of 9 done*, *≈$12 so far* (or *—*), and
   its *done when* lines, folded to the first. **Fold** per goal, remembered per device.
2. **The tree:** tiers from top to bottom, nodes left to right in the Board's order; a line from each idea to each idea
   that depends on it (SVG, drawn under the nodes, no arrowheads: the lower one waits for the upper). A goal wider than
   the pane scrolls sideways inside its section; the page itself never does.
3. **A node** (a card about 220 × 72 px): the title (two lines at most, the rest in its tooltip), its words (`rowOf`,
   as the Board's row), its tasks
   as pips (filled merged, ringed working, empty the rest), and its marks:
   - **needs your hand** (the node's frame heavier, a ● and the Needs you words: *asks you*, *plan ready*, *a to-do
     waits*, *failed*, *proposed*). These are the nodes that move only when the person acts; the rest move by
     themselves (spec 35 §5), so these are the ones the eye should find first;
   - **working**: a spinner beside its words;
   - **waits**: dashed, and why in words from `waits` (*waits for <idea>*, *same files as <idea>*, *waits for limits ·
     after 18:00*, *keeps your reserve · after 18:00*, *tonight*, *stopped*): these words are the Map's own, in
     `map.js` (the phone's in `shell-map.js`), the same as the Agents chips' (spec 35 §11.5);
   - **done**: filled, its words *done*;
   - **proposed**: dotted;
   - **by itself**: the words *by itself* (spec 35 §11.5);
   - **cost**: *≈$0.40–1.20* while its plan has not started (§1 `estimate`).
4. **Tasks** show on the node as pips only; **Tasks** on a node (or its keyboard focus and Enter on the pips) unfolds
   them under its card as small rows in their waves (as the spec's Stages: *k1 The table · merged*), so a task's state
   is seen without leaving the Map.
5. **What moved since you last looked:** a node whose `updated` is after the time this device last showed the Map for
   this project carries *new*, until the Map is shown again (the time kept with the tabs, §3.7).
6. **Done (n)** at each goal's foot holds its folded nodes (§1 `folded`), unfolded by a click.
7. **A click on a node** opens its idea in the passing tab (§3.3) and logs `via: "map"`; the Map keeps its scroll and
   what is unfolded when the person comes back to its tab.
8. The Map re-reads `ideas.map` when the board's rev moves (the shell's refresh, as the Board does), not on a clock of
   its own.
9. **Empty:** a project with no goal says *No goals yet* with **New goal** (the Board's dialog).

## 5. The Map on the phone (C)
A tree does not fit 390 px; the phone shows the same data as a list.
- The Board tab's head gains **Map** (beside the goal select). It opens the Map screen: each goal a section (its head
  as §4.1, without the *done when* lines unless unfolded), its ideas in tier order, each a row with its tier as dots
  (●○○), its title, its words (`rowState`, as the Board's row), its pips, its marks (§4.3) and, when it has some, *after <idea>, <idea>*.
- Rows that need the person's hand come first within their tier.
- *Done (n)* folded at each goal's foot; *new* as §4.5 (kept on the phone for itself).
- A tap opens the idea (the phone's idea screen, as from the Board), logged `via: "map"`. No horizontal scroll.

## 6. Events (A)
- `opened` gains `via` (§2). No new event: the Map's use is `opened` with `what: "map"`, counted per day; its use for
  the person's work is the ideas opened `via: "map"` against `via: "board"` and `via: "needs"`.
- The owner reads after a week: how many days the Map was opened, the first screen opened each morning, and the share
  of ideas opened from the Map.

## Not in this spec
- **The skill-tree look** (Orkline Camp, decisions §52.3): Camp's art over the same `ideas.map`, its *learn* being the
  person's own Start; after the testers' numbers, or as §45.11's screenshot.
- Acting from the Map (Start, Process now, Delete): the actions stay in the idea's tab and Needs you, one place each;
  the Map's use (§6) says whether they are wanted there.
- Drawing or editing `depends_on` on the Map; dependencies between goals (spec 35 §2).
- Operations on the Map (it is the person's, not a project's: spec 38 §1).
- Tabs on the phone; a tab dragged out to a window of its own; splitting the preview.

## Tests
- **A:**
  - `build` on a fixture board: two goals; ideas in tiers by `depends_on` (a chain of three is tiers 1–2–3; a node with
    two parents takes the deeper one); a dependency on another goal's idea draws no edge; General left out;
  - each `waits` kind, in its order (a node in Needs you is `you` before `idea`); a held task's claim gives `files`
    with that idea's title; `until` for limits and reserve;
  - `estimate` only before a task starts; `by_itself` from `passed_by`; `folded` only for a done idea no open one
    depends on, and every edge's two ends are in `nodes` and not folded;
  - a node's state fields equal its `ideas.board` row's for every state, so the faces' row words apply as they are;
  - a goal's `done_when`, counts and `usd` (`null` when nothing is priced);
  - 200 ideas build in under 200 ms; `build` writes nothing and starts no process;
  - `ideas.map` from the desktop and the phone; with no project open, *Open a folder first*; `{"goal"}` gives one goal;
  - `opened` with `via` is written, an old line reads `via: ""`;
  - the critical tests (CLAUDE.md "Alpha"), `tests/test_gui_wording.py`, `tests/test_architecture.py`.
- **B:** browser tests at 1 440 × 900 against a stub host:
  - the Map's tab is first, has no ×, is shown at start in place of the empty text, and Esc does not close it;
  - two goals as sections; an idea that depends on another sits a tier below it with a line between their nodes; a
    waiting node says why; a node with a plan waiting is marked as needing the person; a done idea nothing depends on
    is in *Done (n)*;
  - *Tasks* unfolds a node's tasks in waves; *new* on a node changed since the Map was last shown, gone after;
  - a click on a node opens a passing tab (italic); a click on another replaces it; a double-click keeps it; editing a
    file keeps its tab; Esc closes the active tab; a tab with unsaved changes asks first;
  - opening what already has a tab shows it; a 13th tab closes the oldest kept one with its words;
  - tabs come back after a reload; switching project shows the other project's tabs and the Map stays;
  - at 1 000 px wide: no strip, the preview full screen, Back closes it, the Map from the Board's Map button;
  - the existing desktop browser tests stay green (`test_shell_browser.py`, `test_board_browser.py`,
    `test_project_desktop_browser.py`, `test_ops_desktop_browser.py`).
- **C:** at 390 × 844: the Map button opens the Map; a goal's ideas in tier order with their dots, words, pips and
  *after …*; a row needing the person first in its tier; a tap opens the idea; no horizontal scroll; `tests/test_pwa.py`
  with the new cache version.
- Each part: the critical tests, the touched modules' tests and `tests/test_gui_wording.py`.
