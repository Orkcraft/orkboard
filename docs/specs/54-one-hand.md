# Spec 54 — One hand: every stop of the project in it, the most urgent in the middle, no count anywhere; every stop has a way out; a smaller Target; Agents from a member

The owner, 22 October (decisions §67), on the window as specs 52–53 built it. An Artist asked for a reference picture as
a plan's to-do: a file to-do is done only with a file, the plan does not start until it is, so the goal stood still with
no way on. The hand holds only the party shown's stops and counts the others on the party's deck, so what waits is
split between a hand and a number. So: **the hand holds every stop of the project** (every party's and Operations'),
**the most urgent in the middle**, and **no stop is counted anywhere** (a dot says where they are in the parties' list);
**every stop has a way out** that needs nothing from the person (*Let … decide*, *Describe it instead*, *Go without
it*); on the phone **the Target is one switch** and **Agents is reached from a member**. **Builds:** Claude ·
**Review:** full · P1.

**What it is, and is not:** a new place for what waits, two new answers to a to-do, one to a question, and two
settings made smaller. Storage keeps its shape (a to-do gains two keys in its plan). No new command, no new setting.

Three parts, **all at once** (they share no file): A the host, B the phone, C the desktop. B and C send what A takes;
until A is in `main` a *Go without it* or *Describe it instead* is refused by the host in its words, nothing else breaks.

| part | builds | files (and their tests) |
|---|---|---|
| **A. Host** | §1 | `gui/ideas.py` (`ideas.todo`'s `skip` and `words`), `core/idea_task.py` (the task prompt's lines for a to-do gone without or described), `realm/event_log.py` (`todo_done`'s fields); `tests/test_gui_ideas.py`, `tests/test_idea_runner.py`, `tests/test_event_log.py` |
| **B. Phone** | §2–§6 | `pwa/shell-stops.js` (one hand, its order, its party marks, the ways out on a raised stop), `pwa/shell-arena.js` and `pwa/shell-arena-words.js` (if the hand's items or a party's marks come from there), `pwa/shell-where.js` and `pwa/shell-goals.js` (the deck without a count, the parties' sheet's dots), `pwa/shell-needs.js` (the question sheet's and the to-do sheet's ways out), `pwa/shell-drawer.js` (the Target switch, Agents lower), `pwa/shell-ops.js` (its Target switch), `pwa/shell-arena-field.js` (*Edit* on a member's card), `pwa/board.js` (wiring), `pwa/app.css`, `pwa/sw.js` (`CACHE` `orkcraft-app-v62`) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_one_hand_browser.py`, and the phone tests that read the hand of one party, the deck's count, the Target's rows or the menu's Agents (§8) |
| **C. Desktop** | §2–§4 | `js/arena/arena.js` and `js/arena/arenawords.js` (one bottom row of every party's stops, its order), `js/arena/stops.js` (the party on a stop, the ways out on a raised stop), `js/arena/goaltabs.js` (Parties ⌄ without a count, the spread's dots), `js/shell/tododialog.js` (the to-do dialog's ways out), `js/arena/arena.css`; new `tests/test_one_hand_desktop_browser.py`, and the desktop tests that read the bottom row of one party or Parties ⌄'s count (§8) |

## 0. The words
New strings: *Let <name> decide* (the one who asks: *Let the Taskmaster decide*, *Let Reviewer decide*), *Describe it
instead*, *Go without it*, *Let <leader> choose* (a choice to-do), *What should it look like?* (the field of *Describe it
instead*), *Send*, *Nothing waits for you.*, *<party> · <goal>* (a stop's line of another party), *Agents of this
project*, *Edit*. Spec 50 §0's rules hold (no *card*, *hand*, *fan*, *deck* in what a person reads).

## 1. The host (A)
1. **`ideas.todo` gains `skip: true`** (any kind): the to-do is done (`done: true`) with `skipped: true` and no value; a
   secret's stored value, if any, stays; unticked (`done: false`) clears `skipped`. **`ideas.todo` gains `words`** for a
   `file` to-do: `{idea, id, done: true, words: "<text>"}` with no file: the to-do is done, its `value` the words (their
   edge spaces cut, at most 2 000 characters, refused when empty: *Say what it should look like*), `words: true`; a
   file sent later replaces them. Refusals in words; nothing else of the to-do changes.
2. **The task prompt** (`core/idea_task.py` `_prompt`), for each to-do the task is `for`, after the secrets' line:
   skipped — *The person went without “<title>”: do the task without it; if it cannot be done without it, say what it
   blocks and stop.*; a skipped `choice` — *The person left “<title>” to you: choose one of <choices>, and say which and
   why in your result.*; described — *Instead of the file “<title>”, the person described it: <words>*.
3. **`todo_done`** (`realm/event_log.py`) gains `skipped` (bool) and `words` (bool).
4. Questions need nothing new: `ideas.answer {slug, decide: true}` (spec 41 §9) answers each with its recommended choice,
   and `{…, goal: true, decide: true}` a party's.
5. Tests: a skipped to-do of each kind lets its tasks run and says so in their prompt; words for a file (kept, the
   prompt line, a file later replaces them, empty refused); unticking clears both; the event's fields.

## 2. One hand (B, C)
1. **The hand holds every stop of the project**: every party's Needs you rows, failed tasks and Pick one, and
   Operations' stops (phone: and every party's results to look at, as today's hand holds the party shown's; the
   desktop's results stay in their column, the party shown's). With the filter on (spec 50 §3.5) only the picked goals'
   stops and results, as today.
2. **A stop of another party** says its party: its raised card's goal line reads *<party> · <goal>* and its card wears
   the party's leader's small head (Operations': its `sliders` icon); its label names the party. A quick answer acts in
   place; *Open…*, *Open the plan*, *Open it on its own screen* first show that party (as a pick of it in the parties'
   list), then open.
3. **The order, by urgency**: red first (a failed task, a failed operation), then what holds work back (a plan, a
   question, a to-do, a Pick one, an operation at your check), then what does not (a proposal, a party's proposal, a
   template's rules), then the results to look at; in a group, the oldest first. **The most urgent lies in the
   middle**, the next to its right, the next to its left, and so outward (the fan's arc raises its middle); the order
   of the keys and of a screen reader is the urgency's.
4. **No count of stops anywhere** (reverses decisions §65.2's one count): the party's deck (phone) and *Parties ⌄*
   (desktop) lose theirs; their labels keep *n stops wait in the other parties* for a screen reader only. In the
   parties' list (the phone's sheet, the desktop's spread) a party with a stop wears **a dot** (8 × 8, danger when one
   of them failed, else alert) where its count was. The stage switch's signs are unchanged.
5. An empty hand says *Nothing waits for you.*

## 3. Every stop has a way out (B, C)
1. **A question** (Asks you, a party's question): its raised card and its sheet or dialog gain **Let <name> decide**
   (the asker: a member, the leader, the Taskmaster), last, quiet: `ideas.answer {slug, decide: true}` (`goal: true` for
   a party's). Its toast *Sent: <name> decides.*
2. **A to-do**: its raised card and its sheet or dialog gain, under its own input:
   - a `file` to-do: **Describe it instead** (a field *What should it look like?* and *Send*: `ideas.todo {idea, id,
     done: true, words}`) and **Go without it** (`ideas.todo {idea, id, skip: true}`);
   - a `choice` to-do: **Let <leader> choose** (`skip: true`);
   - a `secret`, `confirm` or `instructions` to-do: **Go without it** (`skip: true`), its title *Its tasks run without
     it, and say so if they cannot*.
   Each is quiet (not primary) and acts at once; its toast *Done: <leader>'s plan goes on without it.* / *Sent: the
   words go to <agent>.*
3. A Pick one keeps *None of them — make new ones*, a plan *Start without*, a proposal *No*, a failure *Drop*: each
   stop already has its way out but these two.

## 4. Motion (B, C)
Nothing flies (decisions §62.8). A stop that comes or goes moves in the hand as a card moves today; a new order is laid
at once, with no shuffle; none under `prefers-reduced-motion`.

## 5. The phone's Target (B)
The menu's **Target** is one switch: *Thrift* · *Balance* · *Quality* (a `radiogroup`, 44 px, the picked one raised as
the priority's is), under it one line, the picked one's words (*the usual models and reasoning, two proposals a
night*). Operations' gear the same. What it writes is today's.

## 6. Agents from a member (B)
1. The menu's head keeps *Stop all*, *Today* and *Spend today*; **Agents** moves into *This project*, as a row *Agents
   of this project ›* (the same screen).
2. **A member's card** (its solo, spec 53 §1.3) gains **Edit**: the agent's dialog of today (model, at once,
   instruction, Takes), for the leader and the Grunt too.

## 7. Tests
- **A**: §1.5.
- **B** (`tests/test_pwa_one_hand_browser.py`, 390 × 844): the hand holds two parties' and Operations' stops; another
  party's stop says its party and wears its leader's head; *Open…* on it shows that party; the order (failed in the
  middle, then a plan and a question beside it, a proposal, a result outward) and the keys' order; no count on the deck,
  a dot in the parties' sheet (danger with a failure); *Nothing waits for you.*; *Let Taskmaster decide* sends
  `decide: true`; a file to-do's *Describe it instead* sends `words`, *Go without it* sends `skip`; a choice's *Let …
  choose*; the Target switch writes `target`; *Agents of this project* opens Agents; *Edit* on a member's card opens
  its dialog; 44 px targets; `sw.js` v62.
- **C** (`tests/test_one_hand_desktop_browser.py`, 1 440 × 900): the bottom row of every party's and Operations' stops,
  their order and party marks; *Open…* shows the party; no count on *Parties ⌄*, the spread's dots; *Let … decide*;
  the to-do dialog's *Describe it instead* and *Go without it*.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_architecture.py`; B also `tests/test_pwa.py` and every
  `tests/test_pwa_*browser.py`; C the desktop browser tests of its files.

## 8. Files a part may need beyond its row
B: the phone browser tests that read one party's hand, the deck's count, the parties' sheet's counts, the Target's
rows or the menu's Agents (`test_pwa_arena_stops_browser`, `test_pwa_goal_types_browser`, `test_pwa_board53_browser`,
`test_pwa_decks_browser`, `test_pwa_ops38_browser`, `test_pwa_shell_browser`, `test_pwa_agents36_browser`,
`test_pwa_pick_browser`, `test_pwa_map39_browser` and any other the suite names). C: the desktop browser tests that
read one party's bottom row or *Parties ⌄*'s count (`test_arena_desktop_browser`, `test_goal_types_desktop_browser`,
`test_ops_desktop_browser`, `test_pick_desktop_browser`, `test_shell_browser` and any other). Each keeps what it proves.
A part that needs any other file: stop and write it in *As built* first.

## 9. Not in this spec
A readable log of what an agent does (the owner's next ask); the desktop's Target and Agents; a stop answered for
another party without opening it beyond its quick answers; a person's own order of the hand.

## 10. As built (notes, no change of the contract)
**A (host).** `ideas.todo` in `gui/ideas.py` takes `skip: true` (any kind: done, `skipped: true`, no value; a secret's stored
value stays) and `words` (a `file` to-do only: edge spaces cut, at most 2 000 characters, `WORDS_CHARS`; empty is refused
with *Say what it should look like*; another kind's `words` is not read, so its own refusal speaks). A file sent later
replaces the words; ticking a described to-do again with no file keeps them; unticking clears `skipped` and `words`.
`core/idea_task.py` `_without` writes the prompt lines after the secrets' line, for the to-dos the task is `for` only.
`todo_done` carries `skipped` and `words` (booleans, always set); the words themselves are never logged. A file a person
sent before going without stays on disk and in the task's environment (the to-do's value is cleared, not the file).
Only A's row was changed, plus `docs/specs/54-one-hand.md` for this note.

**B, the phone** (`orkcraft-app-v62`). Built to §2–§6 as written; what the spec left open, and the files it did not name:
- **The order is in the page, the place is in the CSS.** `shell-arena-words.js` `byUrgency` sorts the hand (a failed task or operation; then a plan, a question, a to-do, a Pick one, an operation at your check; then a proposal, a party's
  proposal, a template's rules; then the results; the oldest first by the row's `at` — a task's and a result's `finished` — and one without a time last) and `fanPlaces(n)` gives each rank its place in the row (the middle
  `⌊(n−1)/2⌋`, then its right, then its left, outward). The cards stay in the page in the urgency's order (so Tab and a screen reader read it) and `shell-stops.js` lays them out with `style.order`; the row's first and last
  card get their outer margin as an inline style by place, not by `:first-child`/`:last-child` (`test_design_system` allows no new custom property, so no `--place`). An even `n` has no card in the middle: the most urgent lies left of it.
- **A stop of another party** is built from every party of the Map in its order, then Operations': each party's own filter (`st.picks`) applies to its own stops and results. The party mark is `{slug, name, head}` (Operations:
  `{ops: true}`); `away()` in `shell-stops.js` shows it first (`core.pick(slug)` / `core.pickOps()`) for *Open…*, *Open the plan*, *Edit the party* and *Open it on its own screen*; a quick answer does not. The raised card's line is
  `.raised__goal` (*Tech · Log format*; a party's own question or Operations' stop: the party alone), its label *Asks you: Log format (Tech)*. A push's arrival still shows the party of the host's first row and pops the most urgent stop.
- **No count**: the deck keeps its label for a screen reader only; the parties' sheet rows lose their count, their labels say *something waits for you* (no number) and a dot (`.where-dot`, `data-dot` alert/danger, 8 × 8, orkUI's alert and
  danger tokens). The dot is for stops, not results, as the count was (`stopCount`, `stopFailed` in `shell-arena-words.js`). Operations' row wears one too.
- **Ways out** are in `shell-needs.js` (`decideButton`, `todoOuts`), used by the raised card and the sheet alike. The to-do row names no asking agent (`board_map.py` sends no `for`), so *Sent: the words go to …* and *Done: …'s plan goes on
  without it.* both name the party's leader (*the Taskmaster*, *Quill*); *Let … decide* names the first question's asker, else the leader.
- **The Target**: `targetSwitch` is in `shell-ops.js` (not `shell-forms.js`, which B's row does not name) and the drawer imports it; it reuses orkUI's `.pills`/`.pill` of the priority switch. Agents is a `data-act="agents"` row
  in *This project*, after *Merge into*.
- **Edit on a member's card** opens a second `makeAgentSheet` made in `board.js` (`core.editAgent(slug)`), because `shell-agents.js` keeps its sheet to itself and is not in B's row; the sheet is one more entry of `sheets`. A role the host
  does not list opens the dialog as *Add agent*, as it always has.
- **Tests changed beyond the new `tests/test_pwa_one_hand_browser.py`** (§8): `test_pwa_arena_stops_browser` (the order, the row's margins by place, a push pops the failure), `test_pwa_board35_browser` (the Target's one line, the dot, a question's
  and a goal's last button), `test_pwa_decks_browser`, `test_pwa_board53_browser`, `test_pwa_goal_types_browser` (no count, dots), `test_pwa_ops38_browser` (Operations' stops lie in every party's hand), `test_pwa_shell_browser` (*Nothing waits
  for you.*, the menu's order), and the `sw.js` pins in `test_pwa.py`, `test_pwa_goal_types_browser`, `test_pwa_board53_browser`.

**C, the desktop** (22 October):
- **One hand**: `arenawords.js` `handOf` gathers every party's `stopsOf` and Operations' `opStopsOf` (each stop gains `party` — slug, name, leader's head and
  name — `g` and `other`), the filter applied per party (the party shown: its picks and the goal peeked; another party: its picks), and below 1 024 px the party
  shown's results; `byUrgency` sorts them (red, holds work back, does not, results; the oldest first by the row's `at`, a failed task of a goal having none sorts last
  of the red; the host's order — the parties in the Board's order, Operations last — breaks a tie). `Stops` keeps them in that order in the page (the keys',
  a screen reader's) and lays them out from the middle with `laidOut` and CSS `order`; a long hand turns less (`fanOf`) and overlaps more (`--ov`, set from the row's
  width, the one overlap variable the design-system test already allowed).
- **A stop of another party** wears `.arena-hc__party` (its leader's small head; Operations': the `sliders` icon) at the card's top right, its banner reads
  *<party> · <goal>* and its label *<kind> in <party>*; *Open…*, *Open the plan*, *Edit the party*, *Pick, with a note…* and a press on the card show that party first
  (`track`, with `closeSpread` and `leaveParty`), the quick answers act in place. A project with Operations and no party still has the hand under *No parties yet*.
- **No count**: Parties ⌄ and the spread's cards lose it; the label keeps *n stops wait in the other parties* (Operations' rules now count in it, and wear the dot,
  as they lie in the hand). The dot (`.arena-deck__dot`, 8 × 8, `--ork-alert`, `--ork-danger` with a failure) is on every party but the one shown, and on Operations.
- **Ways out**: *Let <name> decide* is on the raised question (the first asker's name, the leader's for a party's, *the Taskmaster* for Taskmaster). `TodoWays` and
  `named` are in `shell/tododialog.js` (the dialog's, the stop's); the dialog's *Open…* passes the leader's name; a to-do's own `by.name`, if the host serves one,
  names the agent of *Sent: the words go to …*, else the leader.
- **Not done, outside C's files** (§8): the question's dialog (`shell/askdialog.js`) has no *Let … decide* yet — the raised stop has it; it is one more button there.
- Tests changed to keep what they prove (the count of others became a dot, the host's order became urgency's, one party's row became the project's):
  `test_arena_desktop_browser`, `test_goal_types_desktop_browser`, `test_ops_desktop_browser`, `test_pick_desktop_browser`, `test_shell_browser`.

## 11. Running A, B and C
Each a cloud session on orkWorks/orkBoard on Sonnet with the brief below; each **merges into `main` itself** when its
tests pass (CLAUDE.md, alpha): no pull request.

**A, the host:**

    Build part A (the host) of docs/specs/54-one-hand.md: §1 and A's lines of §7. That file is the contract; read
    decisions §67 (docs/decisions.md) and CLAUDE.md first. Change only the files of A's row. When the critical tests
    (orkcraft.toml `always`) and the tests of every file you changed pass: write A's note in §10 (As built), commit,
    merge into main ("Merge spec 54 A: …") and push main (git push origin HEAD:main). If the push is refused because main
    moved, fetch, merge origin/main in, run the tests again and push again. Never force-push. No pull request.

**B, the phone:**

    Build part B (the phone) of docs/specs/54-one-hand.md: §2–§6 and B's lines of §7. That file is the
    contract; read decisions §67 (docs/decisions.md), specs 52 §5 and 53 §1 and CLAUDE.md first. Change only the files
    of B's row and those §8 names for B. The browser tests need `uv sync --extra dev --extra browser`. When the critical
    tests (orkcraft.toml `always`), tests/test_gui_wording.py, tests/test_design_system.py, tests/test_pwa.py and every
    tests/test_pwa_*browser.py pass: write B's note in §10 (As built), commit, merge into main ("Merge spec 54 B: …")
    and push main (git push origin HEAD:main). If the push is refused because main moved, fetch, merge origin/main in,
    run the tests again and push again. Never force-push. No pull request.

**C, the desktop:**

    Build part C (the desktop) of docs/specs/54-one-hand.md: §2–§4 and C's lines of §7. That file is the contract;
    read decisions §67 (docs/decisions.md), spec 52 §3–§4 and CLAUDE.md first. Change only the files of C's row and
    those §8 names for C. The browser tests need `uv sync --extra dev --extra browser`. When the critical tests
    (orkcraft.toml `always`), tests/test_gui_wording.py, tests/test_design_system.py and the desktop browser tests of
    the files you changed pass: write C's note in §10 (As built), commit, merge into main ("Merge spec 54 C: …") and
    push main (git push origin HEAD:main). If the push is refused because main moved, fetch, merge origin/main in, run
    the tests again and push again. Never force-push. No pull request.
