# Spec 48 — The Map shows one goal: its ideas by stage, its party in lanes, results merged on the idea's card

The owner, 21 October (decisions §61). The Map of spec 39 and 46 is a trail: every goal one under the other, an idea a
stop on it, its tasks small chips under the stop. It answers *how far is the goal*, but not *who is doing what on this
idea now, in which step, and what waits for my look*: for that the person leaves the Map for Agents and Review, and on
the desktop a whole column (Review) sits beside the Board for results that belong to ideas. This spec turns the Map
into the one place of a goal at work: **one goal at a time** (its header, its party on one line), **its ideas in trail
order**, each idea in one of three stages (Planning · Implementation · Checking), the working ones expanded with the
party's members in lanes and the plan's waves in columns, and **the idea's card** on its right, where its results are
merged. **Builds:** Claude · **Review:** full · P1.

**Superseded in part by spec 49** (docs/specs/49-one-window.md, decisions §62): the Map is no longer a tab of the preview but
the window itself (the goals are tabs, the party's columns, the stops along the bottom, the results in a column, the preview a
drawer); this spec's data (`ideas.map`) and its actions stand.

**What it is, and is not:** the Map is no longer only a view (this supersedes decisions §52.1 and spec 39's *Not in this
spec: acting from the Map*): it has the actions of §5, each one the Board's own (`ideas.start`, `ideas.merge`,
`ideas.back`, `ideas.drop_task`); the Map invents no action and no command. The gate between dev and main stays where
decisions §49.5 puts it, in Needs you. No branch per idea and no *merge into main* on an idea (decisions §49: the person
sees dev and main only). No new setting.

Three parts, one branch each: **A first**; B and C from A once A is pushed (they touch no file of each other's). **This
file is the contract**; the rest is the builder's choice inside its files. **Change nothing outside a part's files**
but those §9 names. The desktop is the more work (B: the Map's rewrite and the shell without Review); the phone (C) is
the same shape on one column. The mockup (an interactive Design artifact, `Ideas.dc.html` and `PhoneIdeas.dc.html`) is
the target for words and structure; the code is not copied from it: the page is Preact with orkUI's classes and tokens.

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. Backend** | `spec/48-map-backend` | §1, §2 | `realm/board_map.py` (`stage`, `round`, per task `by`, `wave`, `band`; per goal `party`, `today`; per node `usd`, `plan_estimate`, `asked`), new `realm/map_stage.py` (the stage and the waves, pure, so `board_map.py` stays under ~600 lines), `realm/roles.py` (`task_slug`, which `task_head` uses), `gui/ideas_map.py` (`results` of a node), `realm/lexicon.py` (`stage`, `wave`); `tests/test_board_map.py`, new `tests/test_map_stage.py` |
| **B. Desktop** | `spec/48-map-desktop` | §3, §4, §5, §6 | `js/board/map.js` (the goal's page: header, party line, ideas), new `js/board/mapidea.js` (an expanded idea: track, lanes, columns, stacks), new `js/board/mapcard.js` (the idea's card), `js/board/maplayout.js` (words: stages, a lane's, a column's; the pure functions), `js/shell/shell.js`, `js/shell/boardpane.js`, `js/shell/review.js` (the column goes; what Review's cards do moves into `mapcard.js`), `js/shell/store.js`, `js/shell/shell.css`, `js/board/board.css`; `tests/test_map_desktop_browser.py`, `tests/test_shell_browser.py` |
| **C. Phone** | `spec/48-map-phone` | §3, §4, §5, §7 | `pwa/shell-map.js`, new `pwa/shell-map-idea.js` (an expanded idea), `pwa/shell-review.js` (only if Review's rows are reused), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pinned version; `tests/test_pwa_map39_browser.py` |

## 0. The words
- **a stage** (`TERMS` `stage`, *stage / stages*): one of the three steps of an idea, **Planning**, **Implementation**,
  **Checking**, then *Done*. Not the spec's *Stages* section (`js/board/stages.js`, the plan's tasks in waves): that
  keeps its name on an idea's own screen.
- **a wave** (`TERMS` `wave`, *wave / waves*): the depth of a task in its plan by `after`: 1 for a task that waits for
  none, else one more than the deepest it waits for. The Stages section's lines are the same waves.
- **a lane**: one party member's row inside an expanded idea. **A column**: one wave. **A stack**: the tasks of one agent
  in one wave, drawn as one card with a count. **The idea's card**: the framed box on the right of an expanded idea.
  (No term: these are the page's, not the interface's words.)
- Today's words stay: *party*, *leader*, *Map*, *goal*, *idea*, *task*, *plan*, *check*, *Needs you*, *Review* (the
  state *in Review*, the card's *Waits for your look*), *Merge into dev*, *Send back*, *Drop*, *Start the work*, *Open the
  plan*, *dev*, *main*. A member's state: *at work*, *next*, *tonight*, *free*, or the Needs you words.
- **No *card*, *deck*, *boss* or *hand* in what a person reads** (decisions §56): the interface says *the plan*, *the
  idea*, *a task*, *Waits for your look*. Orks by their orkish names (the Taskmaster, Grunts), others by what they do.

## 1. The data: `ideas.map` (A)
`ideas.map` keeps its shape and gains fields; nothing is removed or renamed, so the Map of spec 39/46 keeps working
until B and C land.

**Each node gains**
- `stage`: `"planning"` · `"implementation"` · `"checking"` · `"done"`, worked out by `realm/map_stage.py` `stage_of`
  (§1.1), and `round`: 1, or the highest `round` of the idea's tasks (a task sent back runs again as round 2).
- `usd`: what the idea has cost so far (`idea_spend.of_idea`, `null` when unpriced; read only for an idea with a plan);
  `plan_estimate`: the plan's `{usd_low, usd_high}` also after it has started (`estimate` stays as it is: only before).
- `asked`: for an idea in `asks`, `[{ask, choices, by}]` with `by` the `{slug, name}` of who asks (the idea state's
  `asks_by` entry, else the goal's leader; spec 46 §1 writes it for a goal's questions, a draft's are the leader's).
- `results`: the results of the idea waiting at Review, each as `ideas.review_list` says it (`task, title, round, tests,
  diff, cost, estimate, over, conflict, check, findings, finished`), oldest first; `[]` for none. Added in
  `gui/ideas_map.py` from the host's `results()`, so `board_map.build` stays a pure read.

**Each task gains** `by`: `{slug, name}`, the role the task runs as (`roles.task_slug`: its `role`, else its kind's role,
else Grunt; `head` stays as it is); `band`: `"check"` when its `kind` is a checker's tag (`idea_checks.TAGS`), else
`"build"`; `wave`: its depth by `after` (a cycle, which a plan never has, reads as 1).

**Each goal gains**
- `party`: the leader, then the team, each `{slug, name, head, band: "lead" | "build" | "check", state, why}`. `state`
  is one of `"needs"` · `"work"` · `"next"` · `"tonight"` · `"free"`; `why` is the Needs you kind (`asks` · `plan` ·
  `proposal` · `failed`) when `state` is `needs`, else `""`. How it is worked out, the first that holds:
  - *the leader*: `needs` if an idea of the goal is in `asks`, has a plan waiting (`plan`) or is `proposed`; `work` while
    the goal's state is `reading` or an idea of it is `reading` or `planning`; `tonight` if one waits for the night in
    Planning; `next` if one is `raw` or `ready`; else `free`.
  - *a builder or a checker*: `needs` (`failed`) if a task it runs as has failed; `work` if one is `running` or
    `testing`; `tonight` if one is `held` for the night or its plan starts at night; `next` if one is `ready`, `waiting`
    or `held`; else `free`. A result `in review` is not `needs` (§6).
- `today`: `{merged, usd}`: the goal's tasks merged today (`finished` starts with today's date) and what they cost.

**1.1 The stage** (`stage_of(state, tasks)`, pure):
1. `done` when the idea's state is `done`.
2. `planning` while the idea has no passed plan: its state is `raw`, `reading`, `asks`, `ready`, `planning`, `plan` or
   `proposed` (the states before the person or autostart passes the plan).
3. `implementation` while a passed plan has a task that is not a check and not `merged` or `dropped`.
4. `checking` when what is left is checks: every build task is `merged` or `dropped`, and a check task is not `merged`
   or `dropped` (a check the person skipped is `dropped`).
5. A plan whose tasks are all `merged` or `dropped` with the idea not yet `done` reads as `checking` (it is closing).
A `failed` idea keeps the stage of its tasks (a failed task is a build task not merged: `implementation`). A check that
leaves findings does not move the stage: see §8.

## 2. The commands (A)
No new command. `ideas.map {goal?}` as before; the Map's page asks for the shown goal only (`goal`), which keeps the
read small. The actions are the Board's: `ideas.start {slug}` (the plan's pass, autostart stays as it is),
`ideas.review_list` (not needed by the Map: `results` carries it), `ideas.merge {slug, task, dear?}`,
`ideas.back {slug, task, why}`, `ideas.drop_task {slug, task}`; each with `via: "map"` in its log line where the
command takes `via`. A refused command says why in plain words, as on the Board.

## 3. The page of one goal (B, C)
1. **The header is the goal**: its title; the goal picker beside it on the desktop (a select of the goals, remembered
   per device; the phone picks the goal in its top bar); priority; state in words; a progress bar and its %;
   *n of m ideas done*; *done when …* (the first line, the rest behind *and n more*); *≈$ so far*; *today k merged ·
   ≈$* (§1 `today`).
2. **The party line** under it: the leader and each member as a head with its name and its state in words: *at work ↻*,
   *next*, *tonight*, *free*, or the Needs you words in the alert colour (*plan ready*, *asks you*, *proposed*, *failed*).
   A member is a button that opens its agent's screen (as a chip of Agents does).
3. **Below: the goal's ideas in trail order** (the order `ideas.map` gives, tiers then the Board's order):
   - an idea **at work** (stage `implementation` or `checking`) or **waiting for the person** (`needs_you` set, or a
     result in `results`, or a plan waiting) is **expanded** (§4); on the phone one at a time, the first of them open at
     first;
   - the rest are **one-line rows**: the head of who is on it (the running task's agent, else the next, else the
     leader), its title, *<stage> · <state words>* (the Board row's words, `rowOf`), a mark (↻ working, a clock for a
     timed wait, the alert mark for a stop on the person); a click expands it;
   - **Done (n)** folds the done ideas, each a row with a ✓ mark, its tasks *k of k in dev* and, while it is not in main,
     *in dev · waits for main* (the gate is in Needs you, §5.5).
4. **Empty** goal: *No ideas yet*; no goal: *No goals yet* with **New goal**, as today. The Flags fold, *Last week* and
   *While you were away* stay at the Map's foot as they are.

## 4. An expanded idea (B, C)
1. **The stage track**: *Planning — Implementation — Checking*; the current stage underlined, the past ones with ✓, the
   coming ones muted; with a `round` above 1, *Implementation · round 2*.
2. **Lanes**: only the party members active in the stage, one lane each, the member's head, name, state in words and
   *k of n* (their unmerged tasks of this idea): in Planning the leader; in Implementation the builders that have a
   task in the plan; in Checking the checkers. A task of an agent outside the party (Grunt, a role since dropped) gets
   a lane after the party's; the seats (1 leader, 3 builders, 2 checkers) cap the party, not the Map.
3. **Columns** are the plan's waves inside the stage, *Wave 1*, *Wave 2*, …; a task's card sits in its agent's lane,
   in its wave's column. In Planning there is one column, *Plan*: the plan's card (*2 tasks, 1 check*, *plan ready*) and
   the leader's questions (§4.6).
4. **A task's card**: its short name (two lines at most), its state in words (`TASK_STATE`); *in Review* in muted ink
   when its result waits (§6); a waiting task dashed, its words *after <task>*; a failed task in danger, with its error
   in its tooltip. A click opens the task's screen (the preview, `via: "map"`).
5. **Stacks**: several tasks of one agent in one wave are one card, the next one's edge offset behind it, with a count
   badge. **Desktop:** hover, focus or click opens a list of them (a dropdown: each row the task and its state, a click
   opens it, Esc closes it, the first row has the focus when it opens by key). **Phone:** a tap opens the list as a sheet
   above the stack.
6. **Members' questions** (state `asks`): cards in the leader's lane, each wearing the head of who asks (`asked[].by`, the
   leader's when it has none), its first words as its text, in the alert colour (the stop is on the person, §6); a
   click opens the idea where it is answered, as today. Nothing is answered on the Map.
7. **A merged task leaves the field**: it is not drawn once `merged`; when a refresh shows a task merged that the field
   had a moment ago, its card moves up and fades out once (≤1.1 s, in steps, `card-out`); **none under
   `prefers-reduced-motion`** (decisions §55.2) and none on the first read of a goal. Several merges in one refresh: one
   animation per card, the first three; the rest leave without one. The pips on the idea's card count them.
8. **On the phone** the idea's card is on top of the expanded block; below it the waves rise **bottom-up**, Wave 1
   nearest the members' row at the bottom; the lanes are the two- or three-column grid of the mockup (a column for each
   member, the members' row at its foot). The DOM follows the screen (highest wave first, the members last), so the
   focus order is the visual order.

## 5. The idea's card (B, C)
In orkUI's double frame (`.ork-frame` or the sheet's own: `3px double`), on the right of the expanded idea (desktop) or
on top of it (phone):
1. **It shows**: the idea's title; *<Stage> · round n* (the stage words, §4.1); pips, a filled one for each merged task,
   a ringed one for each at work, an empty one for the rest; *k of n tasks in dev*; *≈$ so far* and the plan's estimate
   (*plan ≈$1–2*, `plan_estimate`); and the wait in the Map's words if the idea waits (§6).
2. **In Planning with a plan waiting** (state `plan`, not passed): **Start the work** (`ideas.start`, which passes the
   plan as today's pass does; autostart stays as it is) and **Open the plan** (the preview's plan, `via: "map"`). With
   the plan held for the night: **Start now** (`ideas.start_now`), as spec 41 §4 has it. A Planning idea with no plan has
   no button: the leader is on it.
3. **In Implementation and Checking**: *Waits for your look* with a row for each of the idea's `results`: the task's
   title, its tests (*20/20 passed* in the success ink, red in danger), *14 files · $0.42*, and for a check its findings
   (*2 left of 5*); and three buttons — **Merge into dev** (`ideas.merge`; when the result is dearer than its estimate,
   the confirmation Review asks first), **Send back** (`ideas.back` with the reason typed in a small field, as Review
   does) and **Drop** (`ideas.drop_task`, after a confirmation). A result with a conflict says so and offers Send back
   and Drop only. When a result is merged its row folds out (the same animation, §4.7) and the card says *Nothing waits
   for your look. Next: <stage> by <agent>.*
4. **No branch per idea and no *merge into main*** on the card: the person sees dev and main only (decisions §49).
5. **The dev → main gate stays in Needs you**, untouched; Done ideas say *waits for main* and point there.
6. Several results: the card lists them oldest first, the first with its buttons visible; at most 3 rows and *and n more*.

## 6. Colour: the alert is the stop (B, C)
Yellow (orkUI's warning) goes only on the card of the agent the work **stopped on**:
- a **member who asks** (a question in Planning, §4.6);
- the **leader**, for a plan, a spec or a proposal that waits (`needs_you` `plan` · `proposal`, a spec to read);
- the **agent of a failed task**, with that task's card in danger.

A result waiting for review is **not** a signal (decisions §54.1): its card says *in Review* in muted ink, no yellow, no
mark. It still counts in Needs you and the shell's Review/Needs you count, as today. The same rule for the party line
(§3.2): only `needs` members are yellow. A waiting idea is not yellow for its waiting alone.
- **A wait** (limits, night, reserve, same files, another idea) is said by the idea's card in the Map's words
   (`maplayout.js` `waitsWords`: *waits for limits · after 18:00*, *keeps your reserve · after 18:00*, *tonight*, *same
   files as <idea>*, *waits for <idea>*, *stopped*), in muted ink; the tasks it holds are dashed with the same words in
   their tooltips; a clock mark when it is timed.

## 7. The phone (C)
The top bar picks the goal as today (nothing to add to it). The page is §3 on one column; an idea is a row (§3.3) that
expands in place, **one expanded at a time** (an accordion; the idea that needs the person first); §4.8 and §5 as said.
Touch targets 44 px high; the stack's list is a sheet (§4.5). The service worker's `CACHE` goes up by one.

## 8. Settled here (the open points)
- **Checking with findings.** A check task that ends with findings left never lands by itself (spec 43): its result
  waits in `results` with its findings count, on the idea's card. **Send back** runs the check again as round 2 and the
  stage stays *Checking*, shown as *Checking · round 2*. The idea returns to *Implementation* (round 2 too) when a build
  task is sent back or fails: it is then a build task not merged, and `stage_of` says so. No new runner step.
- **Members' questions** are the leader's lane in Planning (§4.6), asked by the head of the member; answered where they
  are today (Needs you, the idea's screen).
- **Waits** on the idea's card: §6; no new `waits` kind.
- **Keyboard and screen reader order**: the page is landmarks in this order: the header, the party line, then each idea in
  trail order; an expanded idea is a region named by its title: its stage track, its lanes (a lane a group named by the
  member, its tasks column by column, Wave 1 first on the desktop and as drawn on the phone), then its card. Stacks and
  the goal picker are reachable by Tab; Esc closes a list; the animations are `aria-hidden` and the task is gone from
  the tree when it merges.
- **The Agents pane** stays as it is: the pool by agent, the same chips. The Map's lanes are by idea; the pane is by agent.
- **Review, the desktop's column, goes** (B): results are merged on the idea cards. The shell's layout is two columns
  and the preview: Board | Map and preview | Needs you (the phone's three tabs are unchanged). Needs you keeps the dev →
  main gate, the questions and the failures; its count of results to look at points at the Map's idea (`showIdea`).
  Review's keyboard (↑ ↓) goes with the column.

## 9. Files a part may need beyond its row
`core/bus.py` consumers in `js/shell/store.js` for the refresh (B); `tests/test_shell_browser.py`'s `StubHost` and
`tests/test_pwa_shell_browser.py`'s `Stub` (the new fields). `docs/specs/39-map.md` and `46-goal-trail.md` get one line
each, pointing here, in B. Anything else: stop and write it in §10 first.

## 10. As built (notes, no change of the contract)
- **B (desktop).** The Map asks `ideas.map` for every goal, as before, and shows one: the Board's (`track`), else the one kept for the project, else
  the first. The Map's picker and the Board's select are the same choice (one signal, kept per device by `tracks.js` `keepGoal`), so the goal list
  needs no second read. The modules: `map.js` (header, party line, ideas, Done), `mapidea.js` (row, stage track, lanes, columns, stacks),
  `mapcard.js` (the idea's card), `mapstage.js` (the pure words and layout functions), `mapghost.js` (the one-time leave), `mapfoot.js` (flags,
  *Last week*, moved out of `map.js` unchanged); `maplayout.js` keeps its trail functions, now unused by the page except the shared words.
- **The shell** is two columns, Board and the centre; `ReviewPane` and its keys are gone. `review.js` keeps what the card and the result's
  preview use (`ResultActions`, `Found`, the tests' words, *Merge into* and Drop's dialogs). *Merge into ▾* sits in the Map's header, beside the
  goal, because it is the project's one setting for where results land. Below 1 024 px the tabs are Board · Agents; the Map is the Board's
  button, as before. A `dear` result (over its plan's price) sends `dear: true` with `ideas.merge`, which only logs it, as the backend says.
- **Rows.** An idea waiting on the person is expanded when it is in `plan`, has a `needs_you`, or has results at Review. The row of a done idea
  always says *in dev · waits for main*: the Map does not know whether main has the idea, and the gate is Needs you's.
- **The card's results** list three and a *and n more* button that lists the rest (the contract's limit, without losing a result). The result's
  title opens its result in the preview; a task's card in the lane does the same for a task `in Review`.
- **A leaving task** is drawn once from the tasks the field had a moment ago, only when the new read says it is merged; a result of the card
  folds out the same way. Both use `useLeaving` (three at most), and neither is drawn under `prefers-reduced-motion`.
- **Not done in B:** the *Others* lane label for an agent outside the party is only its name; the keyboard order is the DOM order of §8.

## 11. Tests
- **A**: `stage_of` for every state (planning states, a passed plan with a build task left, only checks left, a skipped
  check, all merged, done, failed); `round`; `wave` (none after, a chain, two roots, a cycle); `band`; `by`
  (a task's `role`, its kind's role, Grunt); the party's states for the leader and a builder and a checker (`needs` by
  each of its kinds, `work`, `tonight`, `next`, `free`) and that a result in review is not `needs`; `today`; `usd` and
  `plan_estimate`; `asked` with and without `asks_by`; `results` per node, oldest first; the old fields unchanged;
  the 200-idea timing still holds.
- **B** (browser, desktop): one goal shown, the picker switches it; the header's fields and the party line's words; an
  idea at work and one waiting expanded, the rest rows, Done (n) with *in dev · waits for main*; the track's underline
  and ✓; lanes by stage; columns by wave; a stack's count and its list (hover, focus, click, Esc); a merged task leaves
  with the class and none under reduced motion; questions in the leader's lane with the asker's head; the card's
  buttons and their commands' arguments (`ideas.start`, `ideas.merge` with `dear`, `ideas.back`, `ideas.drop_task`);
  yellow only on the three stops and never on *in Review*; no Review column; Needs you still holds the gate.
- **C** (browser, phone): the same on one column; the accordion; the waves rise bottom-up; a tap on a stack; the 44 px
  targets; the service worker's version.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_architecture.py`.

## 12. Not in this spec
- Answering a question, editing a plan or choosing a branch on the Map; a merge into main.
- A free graph or dragging an idea (decisions §50.3); the trail's lines between ideas (a row's order is the trail).
- The Agents pane's change; Camp's skin.

**Part C (phone), as built.**
- The goal shown is the top bar's (`st.track`, else the first goal of the Map); the goal tabs are gone. Another goal starts with its own first idea open.
- The party line is a list of the leader and the team (heads, names, state words); a member is not a button yet (the Agents tab is where an agent opens).
- One idea is open (`opened` in `shell-map.js`): until a tap picks one, the first at work or waiting for the person; a tap on an open idea's title closes it. A row's tap opens it in place; the idea's own screen opens from the card's *Open the idea* (`via: "map"`).
- A row keeps the Board row's words after the stage (*Implementation · working 1/4*) and its one button (*Start now*, *Process now*, spec 41 §4); *Start the work* and *Open the plan* live on the open card. A row that is `plan` with `needs_you` is always open, so it has the card's buttons.
- The card shows the results of the idea as Review's rows do (`resultActions` of `shell-review.js`: Merge into dev, Send back with its one line, Drop… with its confirmation), at most three and *and n more*; every row shows its buttons (the spec says the first). The `dear` confirmation (a result dearer than its estimate) is not on the phone, as in Review.
- A merged task's card leaves once (a ghost for 1.5 s, the first three of an idea in a refresh, none under reduced motion, none on the first read of a goal); the result's row on the card does not animate: it folds out at the redraw.
- A checker's task that has not run has a small × beside its card (*Skip the check*, as the trail had); a check the plan will hold, before the plan, is no longer drawn.
- Stacks open as a sheet titled *<agent> · wave n · k*; its rows open the task's screen.
- Tasks of agents outside the party get their own lane after the party's (`lanesOf` follows the tasks); the lane count is capped at three columns by CSS only for the grid, there is no cap in code.
