# Spec 49 — One window: the goals as tabs, Planning over its leader, the party at the foot, what waits for you along the bottom

The owner, 21 October (decisions §62). After spec 48 the desktop is still three regions the person moves between (the
Board's column with its goal select and Needs you, the Map and its tab strip in the centre, Agents under it) and the phone
is three tabs. The person's day is one question asked many times, *where is my goal, and what waits for me*, and the
answer is spread over all of them. This spec makes it **one window**: the goals are **tabs** across the top with their
progress; under the tab, **Planning** runs down the left above the goal's **leader**; the goal's **party** stands along
the foot, each member's open tasks rising **bottom-up** from it; the results that wait for a look are a column on the
right; **what waits for you** (plans, questions, proposals, failures) lies along the bottom edge, each with its quick
answers; anything opened slides in as a **drawer** from the right. The phone is the same window on one column, with no
tab bar. **Builds:** Claude · **Review:** full · P1.

**What it is, and is not:** a new face over the Board's own data and commands. Its shape borrows from a collectible
card game (decisions §62.2) for what a person already reads at a glance there (a cost before a move, two numbers on a
member, a hand of things to answer, the end of a turn); the words stay the Board's (§0). New on the host: the **dev →
main gate** that decisions §49.5 decided and nothing built (§2.1), **today's events** (§2.2), the **reserve** in the
snapshot (§2.3), a few fields on `ideas.map` and `ideas.agents` (§2.4–2.5). No new setting. The runner, the keeper and
the night are not changed.

Four parts. **A0 and A first, at once** (A0 is orkUI's repository, A touches no file of the page); **B and C from both**
once they are in (they touch no file of each other's). **This file is the contract**; the rest is the builder's choice
inside its files. **Change nothing outside a part's files** but those §12 names. The mockup is the Design artifact
*Orkboard: one window* (`Agents.dc.html` is the desktop, `Phone.dc.html` the phone; `Concept.dc.html` lists what was
taken from the game and what was not); it is the target for words, structure and sizes; its code is not copied: the
page is Preact with orkUI's classes and tokens, the phone is the PWA's plain modules.

| part | builds | files (and their tests) |
|---|---|---|
| **A0. orkUI** (repository orkWorks/orkUI) | §1 | `office/components.css` (`.ork-gem`, `.ork-stat`, `.ork-crystals`, `.ork-frame`, `.ork-race__head.mid`, `.ork-mark`), new `office/marks/` (the tools' marks and the level's chevrons, from Orkline, with a README), `office/preview.html` (a section each), `office/tokens.json` and `pyproject.toml` (version 0.2.0; `tokens.css` rebuilt by `tools/build_tokens.py`), `CHANGELOG.md`, `README.md` (the components line); `tests/test_orkui.py`. Then, in orkBoard, the copy: `python -m orkboard.design.orkui <orkUI>` (only `design-system/orkui/` changes) |
| **A. Backend** | §2 | new `realm/idea_gate.py` (what dev holds that main lacks; the merge), new `gui/ideas_gate.py` (`ideas.gate`, `ideas.gate_merge`), new `realm/board_today.py` (today's events as rows, pure), `gui/ideas_recap.py` (`ideas.today`), `gui/ideas.py` (the registry; the snapshot's `reserve`; `OPENED`, `VIA`), `gui/ideas_args.py` (`_via`), `gui/board_host.py` (the phone's snapshot carries `reserve`), `realm/board_map.py` (a task's `error`, `note`, `round`, `cost`, `started`; a node's `asked[].pick`, `why`), `gui/ideas_roles.py` (each role's `harness`), `realm/event_log.py` (`GATE_MERGED`), `realm/lexicon.py` (`gate`); new `tests/test_idea_gate.py`, new `tests/test_board_today.py`, `tests/test_board_map.py`, `tests/test_gui_ideas.py`, `tests/test_event_log.py` |
| **B. Desktop** | §3–§9, §11 | new `js/arena/` (`arena.js`, `goaltabs.js`, `planning.js`, `ideabar.js`, `field.js`, `waits.js`, `members.js`, `stops.js`, `limits.js`, `todaystrip.js`, `gate.js`, `arenawords.js` (the pure words and lists), `arena.css`), `js/shell/shell.js`, `js/shell/store.js`, `js/shell/tabs.js`, `js/shell/preview.js`, `js/shell/topbar.js`, `js/shell/shell.css`, `js/board/board.css` (only what the Map's removal frees); new `tests/test_arena_desktop_browser.py`, `tests/test_shell_browser.py`, `tests/test_map_desktop_browser.py`, `tests/test_board_browser.py`, `tests/test_design_system.py` (`SHEETS` gains `arena.css`), and the desktop browser tests that use the old helpers (§12) |
| **C. Phone** | §10, §11 | `pwa/board.js` (no tab bar), new `pwa/shell-arena.js` (the goal's window), new `pwa/shell-stops.js` (what waits for you, the raised one), new `pwa/shell-today.js` (the Today and the tools sheets), `pwa/shell-top.js`, `pwa/shell-board.js`, `pwa/shell-map.js` and `pwa/shell-map-idea.js` (kept only for what the arena reuses), `pwa/shell-needs.js` (its rows' actions reused), `pwa/shell-drawer.js` (the menu gains Agents), `pwa/board-app.js` (`#needs` arrival), `gui/pwa.py` (serves orkUI's `marks/*.png` as it serves `races/`), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up, the new modules in `SHELL`) with `tests/test_pwa.py`'s pinned version; new `tests/test_pwa_arena_browser.py`, `tests/test_pwa_shell_browser.py` and the phone browser tests that click a tab (§12) |

## 0. The words
- Today's words stay: *goal*, *idea*, *task*, *plan*, *check*, *party*, *leader*, *Planning*, *Implementation*,
  *Checking* (spec 48's stages), *wave*, *Waits for your look*, *Merge into dev*, *Send back*, *Drop*, *Start the work*,
  *Open the plan*, *Start again*, *Process now*, *Stop all*, *Spend*, *dev*, *main*. A member's state: *at work ↻*,
  *next*, *tonight*, *free*, or the Needs you words (*plan ready*, *asks you*, *proposed*, *failed*).
- **the gate** (`TERMS` `gate`, *gate / gates*): the one press that merges dev into main (decisions §49.5). The button
  says **Merge dev into main**; its screen's kind word is *The gate*.
- New strings, in these words: *Ideas at work*, *Now:*, *nothing at work right now*, *About this goal*, *Edit the
  party*, *A free seat*, *Show everyone's work*, *Only <name>'s tasks*, *No task now*, *✓ k in dev*, *Nothing in
  Planning. A new idea starts here.*, *New (n)*, *+ New idea*, *+ New goal*, *Nothing waits for you on this goal.*,
  *Nothing waits for your look. Results come here as their tasks finish.*, *Merge dev into main*, *main is up to date*,
  *n ideas in dev wait for main*, *hatched: kept for tonight* (inside the night window: *kept for the morning*), *Today*,
  *What is left of your AI tools*, *Open it on its own screen*, *runs/sent back*, *checks/caught*, *plans/made again*,
  *a run*.
- **No *card*, *deck*, *hand*, *mana*, *crystal*, *hero*, *boss*, *minion*, *turn* or *Raise* in what a person
  reads** (decisions §56): those are this spec's and the code's words for the parts (§3), never the interface's. Orks
  by their orkish names (the Taskmaster, a Grunt), the rest by what it does. A `html` template's own text is checked by
  `tests/test_gui_wording.py`: no old spelling (for example a capitalised *Goal* on its own, *track*, *gold*).

## 1. orkUI: the new parts of the look (A0)
Each a class in `office/components.css`, tokens only (no raw colour, no radius, spacing on the steps), shown in the
gallery, listed in the README and the CHANGELOG (**0.2.0**):
1. **`.ork-gem`**: a price or a mark before a move: an inverted chip (`--ork-ink` ground, `--ork-on-ink` text, 600
   12/16), 22 px high and at least 22 wide, its corners cut by `--ork-notch`; `.alert` (the alert ground), `.danger`,
   `.dim` (the edge ground). On the phone (`max-width:1023px`) 24 px.
2. **`.ork-stat`**: a measured number on a member: `--ork-canvas` ground, a line of `--ork-edge`, notched, 600 12/16,
   20 px high, at least 30 wide.
3. **`.ork-crystals`**: a row of `<i>` diamonds (10 × 10, clipped to a diamond, a gap of `--ork-1`): an `i` is
   `--ork-frame`, `i.on` `--ork-ink`, `i.kept` hatched with `--ork-edge` lines (a `repeating-linear-gradient` of the
   token, the only gradient in orkUI); it says what is left of a tool, and the reserve inside it.
4. **`.ork-frame`**: the double frame of a raised thing (3 px double `--ork-edge`, `--ork-panel` ground, notched; spec 48
   named it and it was never written): `.alert`, `.danger` its edge in those colours.
5. **`.ork-race__head.mid`**: a head at 36 × 33 from the @2x image (`image-rendering: pixelated`), between the small (12
   × 11) and the big (48 × 44).
6. **The marks** (`office/marks/`, the owner's call: small accents beside a name, like the heads): each AI tool's mark
   (`harness-claude`, `-codex`, `-agy`, `-cursor`, `-hermes`, `-pi`, `-pipeline`) and the level's chevrons (`rank-1`,
   `-2`, `-3`: Novice, Seasoned, Veteran), 16 × 16 and @2x 32 × 32, copied byte for byte from Orkline
   (`design-system/sprites/icons/`, drawn by its `tools/icon_sprites.py`; its README names the commit); **`.ork-mark`**
   draws one at 16 × 16 from the @2x (`.big` 32 × 32), pixelated. A change to a mark is made in Orkline and copied whole.
Tests: each class exists with its states; no raw colour; the gallery has a section for each. Version 0.2.0 in
`pyproject.toml` and `tokens.json`; `tokens.css` built again. Then orkBoard's copy is made with
`python -m orkboard.design.orkui <path of orkUI>` once orkUI's commit is pushed (the stamp names it).

## 2. The host (A)
### 2.1 The gate: dev → main
- **`ideas.gate {}`** → `{into, main, same, commits, files, ideas: [{slug, title, goal, tasks}]}`: `into` is the
  merge target (`merge_into`, `dev` by default), `main` the repository's default branch (`IdeaGit.default_branch()`);
  `same: true` (and nothing else counted) when they are one branch or `main` does not exist: there is then no gate.
  `commits` is the count of `git rev-list main..dev`, `files` the count of files `git diff --name-only main...dev`
  changes; `ideas` are the ideas with a merged task whose `commit` is among those commits (one read of `rev-list`, not a
  call per task), with the count of such tasks, in the Board's order. Pure where it can be: the git reads in
  `realm/idea_git.py`'s helpers or `realm/idea_gate.py`, the command in `gui/ideas_gate.py`.
- **`ideas.gate_merge {}`** → `{ok, commit, note}`. Under the repository's lock (`idea_git.lock_of`): when `main` is an
  ancestor of `dev`, `main` is fast-forwarded to `dev` the way a result lands (`_fast_forward`: a root checkout on
  `main` moves with `merge --ff-only`, refused with its files when they are changed; else `update-ref`); otherwise a merge
  commit *Merge dev into main* is made in a worktree of its own, detached at `main` (`realm/worktrees`), and `main` is
  fast-forwarded to it; a conflict aborts the merge, removes the worktree and is refused *dev and main conflict in
  <files>: merge main into dev first*. After it, `main` is pushed when the project pushes after merging (`ideas.into`
  `push`), its note as `land`'s. Refusals in plain words: *main is dev here: there is no gate*, *Nothing in dev waits
  for main*. Logs **`gate_merged`** `{commits, ideas, files, how: "fast-forward" | "merge", pushed, device}`
  (`realm/event_log.py`), and moves `ideas_rev` so every face reads again.
- Nothing else changes: results still land in `dev` one by one (spec 48 §5); the gate's report of decisions §49.5
  (the full suite, the browser tests, `.orkcraft/checks.toml`) and its *Revert* are not in this spec.

### 2.2 Today's events
**`ideas.today {}`** → `{events: [{at, mark, tone, words, title, goal, idea, task, open}]}`: the event log since local
midnight (`event_log.read(root, since=…)`), newest first, at most 40, built by the pure `realm/board_today.py`
`rows(lines, titles)` with the titles joined from the Board (ideas by slug, a plan's tasks by id; a title the Board no
longer has reads as the slug). `at` is `HH:MM`; `open` is what a click opens: `{kind: "result" | "task" | "idea",
slug, task?}`. The rows, one per line of these events:

| event | mark · tone | words | title |
|---|---|---|---|
| `task_state` `merged` | ✓ · ok | *merged into <into>* | the task's |
| `task_state` `failed` | ✗ · danger | *failed* | the task's |
| `result_decided` `back` / `fix` | ↺ · muted | *sent back* | the task's |
| `result_decided` `drop` | ✗ · muted | *dropped* | the task's |
| `plan_passed` | ▸ · ink | *the work started* | the idea's |
| `idea_answered`, `goal_answered` | · · muted | *you answered* | the idea's or goal's |
| `proposal_answered` | + / · · muted | *taken* / *left out* | the idea's |
| `gate_merged` | ✓ · ok | *dev merged into main* | *dev → main* |

`goal` is the row's goal (its idea's) so a face can show one goal's day; the gate's row has `goal: ""` and is shown on
every goal. Lines of other events are skipped.

### 2.3 The reserve in the snapshot
The desktop's and the phone's snapshot gain **`reserve: {share, night}`**: `share` is the part of a tool's window the
Board keeps from work that starts by itself right now (`idea_target.reserve(settings, night)`), `night` whether the
night window holds now (`idea_target.in_night`). It applies to Claude, the runner's tool (`idea_runner.HARNESS`). The
phone's `rev` includes it.

### 2.4 `ideas.map` gains
- Each **task**: `error` (its failure, as the runner wrote it, ≤ 300 chars), `note` (a hold's or a stop's: *reserve ·
  after 18:00*, *stopped by you*), `round`, `cost` (usd, `null` before it ran), `started` (ISO, `""`). Nothing renamed.
- Each node's **`asked[]`** gains `pick` (the recommended choice's index, `null` without one) and `why`, as Needs you's
  rows have them (`idea_questions.parse`).

### 2.5 `ideas.agents` and `ideas.roles` gain
Each role's block: **`harness: {id, name}`**, the tool it runs on (`idea_runner.HARNESS`; the Taskmaster the keeper's,
`idea_keeper.HARNESS`), its name as `realm/harnesses.py` says it (*Claude*). The page shows it with the head's tier
(§5.3); a role that runs on another tool one day says that tool's name with no change to the page.

### 2.6 The small things
- `ideas.log`'s `VIA` gains `"hand"` (the stops along the bottom, §6), `"party"` (a member, §5), `"today"` (the
  strip, §7), `"gate"`; `OPENED` gains `"gate"`, `"today"`. `_via` keeps a start's and a queue's `via` when it is one
  of `VIA` (else `"idea"`), so `plan_passed`, `plan_started_now`, `idea_queued` say where the press was.
- `tests/test_gui_ideas.py`'s list of the Board's commands gains `ideas.gate`, `ideas.gate_merge`, `ideas.today`; the
  phone's allowlist needs nothing (every `ideas.*`).

## 3. The window (B; the phone in §10)
From the top, at 1 440 × 900 (the mockup's size), nothing scrolling but the regions named:
1. **The top bar** (32 px, as today): the project switcher, *Orkline*, then the spacer, **Agents** (the drawer's Agents,
   §9), **Files** (only with projects, the drawer's Files), **Spend ≈$…** (this week's work, as today), **Stop all**,
   the settings. The limits leave the bar for the bottom right (§8).
2. **The goal tabs** (40 px, §4).
3. **The main row**: the **today strip** (40 px, §7), the **left column** (248 px: Planning over the leader, §4.3–4.4),
   and the **goal's field** (the rest): the **ideas bar** (36 px, §4.5), the **party's columns** with the right column
   **Waits for your look** (312 px, §5.4) beside them, the **party row** (64 px: the members, and the gate in the right
   312 px, §5.1, §5.5), and the **bottom row** (64 px: what waits for you, §6, and the limits in the right 312 px, §8).
4. **The drawer** (§9) over the field from the right.
Below 1 024 px: the today strip is hidden, the left column is 200 px, the results join the bottom row (as on the phone,
§10.6), the drawer takes the window's width and the party's columns scroll sideways. The page's names: the parts are
`arena-*` classes; the regions are landmarks in this order: the goal tabs (a `tablist` named *Goals*), *Today*,
*Planning*, the field (*The goal at work*), *Waits for your look*, the party, *Waits for you*, the limits.

## 4. The goal: its tabs, Planning, its leader, its ideas (B)
1. **A tab per goal** (`ideas.map`'s goals, the Board's order), each: the flag mark, the goal's short title, a meter
   of 5 cells and its % (`progressOf`), the count of its **stops** (§6: what waits for the person on it) in the warning
   count when there is one (*n stops wait for you* in its label), ↻ while its party is at work. Its tooltip: the title,
   *% of the way*, *done when …*. The tab picked is the goal shown, kept per device as today (`keepGoal`); arrows,
   Home, End move between tabs. After the goals: **Operations** when the project has them (`ops_rev`): the field is
   then today's Operations view and the bottom row its rows (op, op_failed, op_rules); **+ New goal**; at the row's end
   **Merge into dev ▾** (`IntoDialog`, as the Map's header has it).
2. **The ideas bar** is the goal's one line (decisions §62.6 keeps it to one): **▾ Ideas at work n · Now:** *who ↻ which
   task (which idea)* for every running task, the leader reading, or *nothing at work right now*; then the goal's
   numbers *k ideas left of n · ≈$ so far · today m merged · ≈$*; **About this goal** (the goal's screen in the
   drawer: priority, state, leader, done when, how far, what it costs, the party's price, its checks on every idea);
   **Edit the party** (`openDialog("goal", {slug})`). Open, it lists the ideas at work (stage `implementation` or
   `checking`): title, *≈$ so far · plan ≈$*, the stage track (spec 48 §4.1, *round n*), pips, *k of n tasks in dev*,
   and a note (*✗ <task> failed*, *<who> ↻ <task>*, *tonight: <task>*, else spec 48 §5.3's *Nothing waits for your look.
   Next: …*); a click on an idea shows only its tasks in the field and its results on the right (pressed; a second
   click shows all); hovering it lights its tasks. **Done (n)** folds the done ideas, each *in dev · waits for main*, or
   *in main* when `ideas.gate` no longer lists it.
3. **Planning** (the left column's top): *Planning n* and **+ New idea** (`openDialog("idea", {goal})`); the goal's
   ideas in stage `planning` that are not `raw`, the stops first: each a plain row (no frame, no head): a mark (**!** in
   the alert colour for a stop: `asks`, `plan`, `proposed`; ↻ while the leader reads or plans; none else), its title, its
   state in words (*asks you · <who>* for a member's question), the plan's price (*$1–2*, `plan_estimate`) for a plan; a
   stop has the alert edge on its left (2 px). A click opens it in the drawer (the plan's screen for a plan, else the
   idea's). Under them **New (n)** folds the `raw` ideas (*new · <leader> reads it later*, or *tonight*). Empty:
   *Nothing in Planning. A new idea starts here.*
4. **The leader** (the left column's foot): the leader as a member (§5.2, the same small row), and **Process
   now · n new ideas** (`ideas.queue {slug, queue: "now", via: "party"}` for the goal's first `raw` idea; off with *no
   new idea*; its tooltip *<leader> reads “<title>” now*). A click on the leader shows only the leader's work (§5.3).

## 5. The party (B)
1. **The party row**: the goal's builders, then its checkers, then its **free seats** (the seats the party leaves,
   decisions §56: 3 builders, 2 checkers), each over its column (§5.4). A free seat is narrow (88 px), dashed, *+* and
   *A free seat* with its band (*builds* / *checks*); a click opens **Edit the party**. The row is 64 px high.
2. **A member** is a small framed row, about 55 px high, filling its column's width (on the desktop at most 200 px; three
   across a phone, 118 px each) (1 px `--ork-frame`, notched, `--ork-panel`; a member that is on: `--ork-raised` with an
   ink edge): **its head** (36 × 33, `.ork-race__head.mid`, the leader's too) **wearing three signs on its corners** (16
   × 16, over the head's edge, none reaching into the text: 10–12 px clear between the head and its lines): its
   **level's chevrons** top left (the head's tier: `rank-1` Novice, `rank-2` Seasoned, `rank-3` Veteran; tooltip
   *Seasoned: its level*), its **harness's mark** bottom left (§1.6, §2.5: `marks/harness-<id>.png`, tooltip *Runs on
   Claude*) and **its state** top right: ✗ on the
   danger ground for a failure, ! on the alert ground for any other stop (*plan ready*, *asks you*, *proposed*), ↻ while
   at work, ☾ tonight, none when next or free (tooltip: the state in words). Beside the head, three short lines: its
   **name**, **its runs and redos** (*5/1*: tasks finished this week and of them sent back; a checker's *6/2*, checks and
   of them caught something; the leader's *6/1*, plans and of them made again) and **its price for a run** (*$0.38*: the
   week's average once 3 have finished, `usd_task`; before, *≈$0.40*, its level's price), each number with a tooltip that
   says which (*the average of its 5 runs this week* · *about: too few runs yet, the price of its level*, both *at API
   prices, not your bill*). No line of words for the state, the harness or the level: the peek (§5.3) and the member's
   label for a screen reader say all of it in words. Numbers come from `ideas.agents` joined by slug (`week`,
   `check_week`, `usd_task`, `max_parallel`, the chips); the Taskmaster's price is the plans' (*—* when it has none). A
   free seat is a dashed square with *+* in its narrow column (tooltip *A free seat: pick an agent from the library*).
3. **Its peek**: hovering or focusing a member shows its whole face beside it (a larger framed card, `aria-hidden`,
   nothing in it pressable): the price in a gem with *a run*, its band, the head, the name, *race · harness · level ·
   model · k of n at once*, its state, now and next, *Takes: …* (*Checks: …*, *Leads: …*), and the two numbers in
   `.ork-stat`s with their words. A click on a member shows **only its work** (solo): **nothing is reordered**: the
   other members' tasks leave the field, and its own, in its column's order, lie **across the field's whole width**,
   still rising bottom-up (six to a row on the desktop instead of two; the bottom row lit, the rows above muted); *Only
   <name>'s tasks n* over them; the right column only its results (*· only <name>'s*); **Show everyone's work** (and a
   second click, and Esc) shows all again. The leader's solo lays Planning's items out the same way.
4. **The columns**: one per member of the row, the label *Implementation* over the first builder and *Checking* over the
   first checker. A column holds its member's open tasks of the goal's ideas at work, **rising bottom-up** from the
   member, two to a row: the one at work nearest the member, then failed, *in Review*, ready, waiting, held. **The
   bottom row is lit; the rows above are muted** (`--ork-canvas` ground, muted ink; hover and focus light one again):
   what is taken next is what is bright. A column scrolls inside itself; its top says *✓ k in dev* for its merged
   tasks; empty, *No task now*. **A task** is a small framed item 112 px high: its wave (a badge and *wave*), a mark (↻,
   ✗, the clock for a hold), its idea's title (one faint line), its name (three lines at most), its state in words (spec
   48's: *working 4 min*, *in Review* in muted ink, *after k1*, *tonight · after 01:00*, *failed* with the error in its
   tooltip). A click opens it in the drawer (*in Review*: its result; else the task's screen; `via: "map"`). **Hovering
   a task lights what waits for it** (its tasks `after` it, in the same idea): the task *→ n wait for it*, each of them
   *← waits for <id>*, outlined in ink.
5. **Waits for your look** (the right column): *Waits for your look n*; a result per row, oldest first: its idea's
   title (one line), its title (a link: the result in the drawer), *<agent>* (*· its check* for a check), its tests (in
   success or danger ink) or a check's findings, *14 files · $0.42*, and **Merge into dev** · **Send back** · **Drop**
   (`ResultActions`, unchanged: `ideas.merge` with `dear`, `ideas.back` with its line, `ideas.drop_task` after its
   confirmation). Empty: *Nothing waits for your look. Results come here as their tasks finish.* A result is not a
   signal (decisions §54.1): no alert colour here. At the column's top, *While you were away* and *Last week* (`Cards`,
   as the Map's top had them); at its foot the Flags fold and *Last week* (`MapFoot`).
6. **The gate** (§2.1), beside the party row: **Merge dev into main** (the primary button) and *n ideas in dev wait for
   main*; *main is up to date* (off) when nothing waits; not drawn when `same`. A press opens the gate's screen in the
   drawer: *dev → main*, *n ideas in dev wait for main*, the ideas listed under *In dev, not in main* with their goals,
   the commits and files counts, **Merge dev into main** (`ideas.gate_merge`), and *Nothing reaches main without you.*
   After the merge the drawer says *main has every idea of dev* and the button is off.

## 6. What waits for you: the bottom row (B; the phone in §10.5)
1. **The stops of the goal shown**, from its Needs you rows (`ideas.board` `needs_you` of the goal, in the host's
   order) and its failed tasks: each a framed item (`.ork-frame`, the alert edge; a failure the danger edge) standing
   in a **fan** along the bottom edge (each turned a little from the middle, the middle ones higher, overlapping), only
   their tops showing (64 px); hover or focus **raises** one whole (246 px tall, 156 wide) above the others, with no
   motion under `prefers-reduced-motion`. Empty: *Nothing waits for you on this goal.*
2. **Each shows**: a gem with what it costs (a plan's price *$1–2*; *?* for a question; *—* for a proposal; ✗ for a
   failure; · for a to-do), its kind (*Plan ready* · *Asks you* · *Proposed* · *A to-do* · *Failed*), the head of who
   it is from (24 × 22 at the right of its top for a question or a failure; a plan and a proposal the leader's 36 × 33
   in its middle), its title, its text (three lines: the plan's *2 tasks, 1 check*, the question in quotes, the
   proposal's why, the failure's error), and **its quick answers**:
   - a plan: **Start the work** (`ideas.start {slug, via: "hand"}`, the plan's pass) and **Open the plan**; held for the
     night: **Start now** (`ideas.start_now`);
   - a question with choices (an idea's or a goal's, the first of its questions): each choice a button, the recommended
     one marked (●) and primary; a press answers it (`ideas.answer {slug, answers: [<choice>], goal?}`); with more than
     one question: **Send the picks** (each question's recommended choice) and **Open…** (`AskDialog`); with no choices:
     **Open…** only;
   - a proposal: **Take** (`ideas.proposal {take: true}` at the goal's priority) and **No** (its *Why not?* line, as
     Needs you); a party proposal: **Take it out** / **Keep it** (`ideas.party_answer`);
   - a to-do: **Open…** (`openDialog("todo")`);
   - a failure: **Start again** (`ideas.start {slug, via: "hand"}`: its idea's tasks that are not merged or in Review run
     again; its tooltip says so) and **Open…** (the task's screen: its log, *Drop* there with its confirmation).
   A press shows its toast as Needs you does (*Sent: the Taskmaster answers in a moment.*). A click on the item outside
   its buttons opens it in the drawer.
3. A stop is the alert colour's one place with the members' states and Planning's marks (spec 48 §6, unchanged).

## 7. Today: the strip (B; the phone's sheet in §10.4)
The strip on the left is the day of the goal shown (§2.2, `goal` the shown one or the gate's): a mark per event, newest at
the top (✓ in the success ink, ✗ in danger, ↺ and · muted, ▸ ink), a clock mark over them; each a button whose label and
tooltip say *HH:MM · <title> · <words>*; a click opens its `open` in the drawer (`via: "today"`). It reads `ideas.today`
with the shell's refresh.

## 8. The limits (B; the phone's sheet in §10.4)
At the bottom right, a line per tool of the snapshot's `limits`: its mark and name, ten `.ork-crystals` diamonds for
what is left (`left` × 10, rounded), the last of them **hatched** for the reserve (`reserve.share` × 10, Claude only),
and its %; under them *hatched: kept for tonight* (*kept for the morning* inside the night window) and *<tool> resets
at HH:MM* for the tightest window. A tool whose limits were not read says *not read* and has no diamonds. The tooltip:
*<tool>: n % left, m % of it kept for tonight · resets at HH:MM*.

## 9. The drawer (B)
The preview of today becomes a drawer: it opens from the right over the field (62 % of the window's width, at least 560
px), 3 px double edge on its left; its tabs at its top (spec 41's: kind and title, the passing one in italics, kept on
a double click, × each, at most 12, kept per project; **no pinned Map tab**), **Close the drawer** (×) at their right;
its body is today's preview bodies unchanged (an idea, a plan, a task, a result with its pinned actions, a goal, a
document, a file, a diff; the gate's screen, §5.6; **Agents**: today's Agents pane, the pool by agent with *+ Add
agent*; **Files**: today's Files pane). Anything opened opens the drawer on its tab; **Esc** closes the drawer (not
while typing, not over a modal) and keeps its tabs: opening anything brings it back. An action that ends the thing
(merge, drop) closes its tab as today (`closePreview`). The field is never behind a tab: `ideas.map` is always read
(the shell's refresh), and *opened map* is logged once per page load.

## 10. The phone (C)
The phone (390 × 844) is the same window on one column, **with no tab bar** (Board, Agents, Needs you go):
1. **The top bar** (44 px): the menu (the drawer of today: Stop all, Spend, the project, its settings, the phone's; it
   gains **Agents**, today's Agents tab as a screen), the project's name, **Today** (a clock and the count of today's
   events: the Today sheet), and the **limits chip** (the worst tool's diamonds: the tools sheet). It slides away as
   the page scrolls, as today.
2. **The goals** as a row of chips under it (scrolling sideways): the short title, its %, its stops' count, ↻; an
   *Operations* chip when the project has them, and **+ New goal** last (dashed). The goal's header under them: its title, *k ideas left · n % · ≈$ so
   far*, and the gate's button (*dev → main*, off when main is up to date; its screen full-screen).
3. **The ideas bar**: *▾ n · Now: …*; open, the ideas at work (title, pips, stage track, note; a tap shows only that
   idea's tasks) and *Done · n*.
4. **The sheets**: **Today** lists §2.2's events of the goal (*mark · title · HH:MM · words*; a tap opens it) and the
   Done ideas; **What is left of your AI tools** lists §8's lines with their resets. Both are bottom sheets
   (`util.js` `sheet`).
5. **The stage switch** over the field: **Planning n** · **Implementation n** · **Checking n** (a `tablist`, 44 px; a
   count in the warning count when a stop is in that stage; *Implementation* is the wider): it shows **only the
   columns of that stage**: Planning the leader's column (its Planning items as task items, the stops first, **Process
   now** in it), Implementation the builders' and their free seats, Checking the checkers' and theirs.
   The first shown is Implementation when a builder has an open task, else Checking when a checker has, else Planning;
   another goal starts at its own first. With up to three members the columns share the width (no sideways scroll);
   more scroll sideways. The members stand at the foot of their columns (§5.2's row, a 60 px row: three fit across), the
   free seats after them; a tap on a member shows only its work over the field (§5.3: the same order, three to a row
   across the width, bottom-up; its price and numbers in a line on top; *Everyone*).
6. **What waits for you** lies along the bottom (56 px, **no line over it**): the stops of §6 and, after them, the
   results to look at (*To look at*, the edge's muted frame), fanned and only their tops showing; **New idea** is the
   FAB in its right corner (as the phone's FAB of before, `ideas.fab`: a 48 px square in the action colour with *+*, the
   new idea for the goal shown), the fan keeping clear of it. A tap **pops** one out:
   it leaps from its place in the fan to a raised sheet above the scrim (≈ 0.34 s in steps, from its turn to upright;
   none under `prefers-reduced-motion`; its place in the fan stays empty while it is up): its gem, kind, head, title,
   text, its quick answers as 44 px buttons (§6.2's; a result's *Merge into dev* · *Send back* · *Drop…*) and **Open it
   on its own screen**. A tap on the scrim lays it back.
7. **The screens** are today's full-screen preview with **‹ Back** (and the system back), unchanged.
8. A push's `#needs` arrival opens the goal of the first stop and pops it. Touch targets 44 px; the service worker's
   `CACHE` goes up by one and its `SHELL` lists the new modules.

## 11. Motion (B, C)
Motion says what changed, never decorates (decisions §62.8). Each in steps (the pixel look), none under
`prefers-reduced-motion` (decisions §55.2), none on the first read of a goal, none for what changed while the page was
hidden (`document.hidden`: *While you were away* tells it). Ticking words (*working 4 min*) and counts never move.
1. **A task appears**: a task the field did not have a moment ago rises into its column (≤ 0.36 s).
2. **A task leaves** (merged or dropped): its item fades where it stands with a one-frame ✓ (✗ for a drop), ≈ 0.3 s;
   then **its column settles**: the items it held up slide down into the gap (≈ 0.25 s, ease-out, no bounce). Several
   in one refresh move together; the first three animate, the rest simply go (spec 48 §4.7's `useLeaving`, whose
   ghost rising up is replaced by this).
3. **A task moves in its column** (its state changed its place: finished → *in Review*, sent back, failed): it and the
   items it passes slide to their new places (FLIP: each item's old box measured before the redraw, its new one after,
   the difference played back, ≈ 0.25 s); nothing else moves.
4. **Nothing moves under the pointer or the focus**: while the pointer is over a column or the focus is inside it, that
   column's settle and moves wait (the gap stays empty) until the pointer leaves or the focus goes, at most 10 s; a stop
   in the bottom row does not shift while it is raised or popped.
5. **The quiet reward**: when a task merges, its member's first number (*5/1 → 6/1*) and its column's *✓ k in dev* show
   their new value with a one-time highlight (≈ 0.6 s); nothing flies to them.
6. **A stop rises** (the desktop's hover, the phone's pop, §10.6).

## 12. Files a part may need beyond its row
B: `js/board/map.js`, `mapidea.js`, `mapcard.js`, `mapfoot.js`, `today.js` (their pieces are reused: `ResultActions`,
`Cards`, `MapFoot`, `AskDialog`, `Proposal`, `PartyProposal`; what the arena no longer draws may stay or go, but
`today.js` keeps `KIND_WORDS`, which `tests/test_phone_push.py` reads); `js/orkui.js` (a `mid` head); the desktop browser
tests that import `tests/test_shell_browser.py`'s or `tests/test_map_desktop_browser.py`'s helpers (`_open`, `_needs`,
`_show_goal`) or assert the old layout: `test_check_review_desktop_browser`, `test_gate_browser`,
`test_lens_desktop_browser`, `test_own_parties_desktop_browser`, `test_party_price_desktop_browser`,
`test_party_proposals_desktop_browser`, `test_record_desktop_browser`, `test_week_desktop_browser`, `test_races_browser`,
`test_shell_36_browser`, `test_recap_desktop_browser`, `test_project_desktop_browser`, `test_ops_desktop_browser`: each
keeps what it proves, through the new window. `tests/test_shell_browser.py` keeps the names the phone's tests import
(`GREEN`, `task`, `PARTY`, `PARTY_LINES`, `party_price`). C: the phone browser tests that click a tab or wait for one
(`test_pwa_map39_browser`, `test_pwa_agents36_browser`, `test_pwa_board35_browser`, `test_pwa_check_review_browser`,
`test_pwa_party_proposals_browser`, `test_pwa_races_browser`, `test_pwa_week_browser`, `test_gate_phone_browser`,
`test_pwa_recap_browser`, `test_pwa_push_browser`, `test_pwa_ops38_browser`), the same way; C does not edit
`tests/test_shell_browser.py`. Both: `docs/specs/48-map-ideas.md` gets one line pointing here (B). The variables
Orkboard's sheets may set of their own (`tests/test_design_system.py`) gain, with this spec, `--rot`, `--dy`, `--z`,
`--ov` (a fan's turn, rise, order and overlap) and `--cols` (the columns' template); a part uses no other. Anything
else: stop and write it in §14 (as built) first.

## 13. Tests
- **A0**: the classes and their states; tokens only; the gallery's sections; the marks' files, sizes and bytes; the version.
- **A**: `ideas.gate` on a fixture repository (dev ahead of main by a merged task, `same` when `into` is main, an idea
  listed by its task's commit, one `rev-list` read); `ideas.gate_merge` fast-forward, a merge commit when main moved, a
  conflict refused with main as it was and no worktree left, the push note, the log line, the refusals; `board_today.rows`
  for each event of §2.2, the order, the limit, a lost title, other events skipped, midnight; the snapshot's `reserve` by
  day and inside the night; the map task's new fields and `asked`'s `pick` and `why`; each role's `harness`; `VIA`,
  `OPENED`, `_via`; the old fields unchanged.
- **B** (browser, desktop): the regions in their order and sizes at 1 440 × 900 with no page scroll; the tabs (title,
  %, the stops' count, the picked one kept after a reload, arrows; Operations); Planning's rows and marks, *New (n)*,
  Process now's command; the ideas bar's line, open list, a press filtering the field, *About this goal* in the
  drawer, Done's words with `ideas.gate`; a member's row (≈ 45 px high) with its two numbers and their tooltips (the
  average and the *≈* before), its three signs on the head (harness, level, the state: ✗ for a failure) and their tooltips, the peek on hover, solo and back (the same order, across the width,
  others gone; the button, Esc); the columns bottom-up with the bottom row lit
  and the rows above muted, *✓ k in dev*, the hover's *waits for it*; Waits for your look's buttons and their commands;
  the gate's button, screen and `ideas.gate_merge`; the stops in the fan, a raise on hover and focus, each kind's quick
  answers and their commands' arguments (`via: "hand"`); the strip's marks and a click; the limits' diamonds and the
  hatched reserve; the drawer (opens on a click, tabs, Esc keeps them, Agents and Files in it); below 1 024 px;
  reduced motion; no alert colour on a result.
- **C** (browser, phone): no tab bar; the top bar's Today and limits sheets; the goal chips and header; the stage
  switch (the first shown, a press, the counts, the columns shown, no sideways scroll with three); the members' cards
  (three across at 390 px, their signs; `marks/*.png` served); a member's solo (the column's order, three to a row);
  + New goal last among the chips; the New idea FAB in the bottom row's corner, clear of the fan;
  the stops and results along the bottom with no line over them, a tap pops one (the class, none under reduced
  motion), its quick answers' commands, *Open it on its own screen*; `#needs`; 44 px targets; the service worker's
  version and `SHELL`.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_architecture.py`.

## 14. As built (notes, no change of the contract)
- **A (the host).** `ideas.today`'s `open.kind` is also `"gate"` (`{kind: "gate", slug: ""}`, the gate's row) and `"goal"`
  (`{kind: "goal", slug: <goal>}`, a goal answered): the faces open the gate's screen and the goal's. A check that found
  nothing (`task_state` merged with `clean`) landed nothing and has no row, as the recap counts it. `gate_merged` also
  logs `into` and `main`; the gate's row says *<into> merged into <main>* with the title *<into> → <main>*. The *no gate*
  refusals name the branches (*Results merge into main itself: there is no gate*, *This folder has no main branch:
  there is no gate*); a failed push does not undo the merge (its note says *push failed: …*). `VIA` lives in
  `gui/ideas_args.py` beside `_via` (`gui/ideas.py` imports it). The merge commit's author is the Board's own, as a
  task's commit (`Orkline`). The snapshot's `reserve` is read at each snapshot (the clock moves it).

## 15. Not in this spec
- The gate's report of §49.5 (the full suite, the browser tests, `checks.toml`), *Revert* on it, and the media look.
- A retry of one failed task (*Start again* runs the idea's unmerged tasks, as today); dragging a stop or a task.
- From the game, turned down (`Concept.dc.html`): packs and golden members, quests and streaks, a turn's timer, emotes
  and sounds, the opponent's hand (a forecast of *done when*: no data for it).
- Camp's skin; the phone in landscape; picking an agent from a free seat (it opens *Edit the party*, as today).
