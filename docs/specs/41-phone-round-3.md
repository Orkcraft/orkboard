# Spec 41 — the phone, round 3: what waits for you is the signal, a name fits its chip, a question comes with its answer picked

The owner, 20 October (decisions §54), after a day on the phone: the top bar's ! repeats the Needs you tab's count; the
project switcher, the gear and the Board's heading and Target row crowd the goal's name and the limits; names are cut on
the Map; starting a plan takes two screens; Speak sits on the Board unused; New goal is three screens; a goal's team
cannot be changed on the phone; Add agent only makes a new agent; an agent's line spells its model in words; the
questions' likely answers are seldom the ones taken. Most of it is the phone's; what the desktop shares (the signal,
short names, an agent's line, the questions) comes with it. **Builds:** Claude · **Review:** full · P1.

Wording: CLAUDE.md (today's words: *goal*, *idea*, *task*, *Taskmaster*, *Grunt*; the pixel face never for a person's
words). **This file is the contract** (names, data, commands); the rest is the builder's choice inside its files.
**Change nothing outside these files.**

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A0. orkUI** | orkUI's own | §1's warning count, §2's `menu`, §5's `mic` | orkUI: `office/components.css` (`.ork-count.warning`), `office/icons/src/menu.svg`, `office/icons/src/mic.svg` (Pixelarticons, its licence), `office/icons/icons.svg`, `tests/test_orkui.py`; then here `design-system/orkui/` by `python -m orkboard.design.orkui <orkUI>` (spec 40 §2), never by hand |
| **A. Backend** | `spec/41-backend` | §3, §4's event, §7's save, §8's data, §9's data, §10 | `realm/idea_words.py` (`short_of`), `realm/ideas.py` (`short` on pages and rows), `core/idea_draft.py` (`short`, questions, `decide`), `core/idea_goals.py` (`short`, questions), `core/idea_keeper.py` (a task's `short`), new `realm/idea_questions.py`, `realm/board_map.py` (`short`, `asks`), `gui/ideas.py`, `gui/ideas_board.py` (`ideas.answer`'s `decide`, `via`), `gui/ideas_goals.py` (a party's save), `gui/ideas_roles.py` (`ideas.role_add`, `usd_task`, `told`, `installed`), `realm/roles.py` (`TOLD`), `realm/lexicon.py`, `realm/event_log.py`; `tests/test_idea_words.py`, `tests/test_ideas.py`, `tests/test_idea_draft.py`, `tests/test_idea_keeper.py`, `tests/test_board_map.py`, `tests/test_gui_ideas.py`, `tests/test_gui_goals.py`, `tests/test_roles.py`, new `tests/test_idea_questions.py` |
| **B. Phone** | `spec/41-phone` | §1–§9 on the phone | `pwa/board.js`, `pwa/shell-top.js`, `pwa/shell-projects.js` (the drawer; its settings in a new `pwa/shell-drawer.js`), `pwa/shell-board.js`, `pwa/shell-map.js`, `pwa/shell-ideas.js`, `pwa/shell-idea-field.js`, `pwa/shell-goal-new.js`, `pwa/shell-goal.js`, `pwa/shell-agents.js`, `pwa/shell-agent.js`, `pwa/shell-needs.js`, `pwa/shell-preview.js` (`price` shared), `pwa/app.css`, `pwa/sw.js` (cache `orkcraft-app-v36`) with `tests/test_pwa.py`'s pinned version; `tests/test_pwa_shell_browser.py`, `tests/test_pwa_map39_browser.py`, `tests/test_pwa_goal_team_browser.py`, `tests/test_pwa_agents36_browser.py`, `tests/test_pwa_projects37_browser.py`, `tests/test_pwa_idea_field_browser.py` |
| **C. Desktop** | `spec/41-desktop` | §1, §3, §8, §9 on the desktop | `js/shell/shell.js` (the tab's signal), `js/board/map.js`, `js/board/maplayout.js`, `js/board/tracks.js` (short names), `js/shell/agents.js`, `js/shell/agentdialog.js`, `js/board/today.js`, `js/shell/askdialog.js`, `js/shell/shell.css`, `js/board/board.css`; `tests/test_shell_browser.py`, `tests/test_map_desktop_browser.py` |

A first (and A0's copy); B and C branch from A once it is pushed and touch no file of each other's.

## 0. The words
- **the signal**: Needs you's tab in orkUI's warning mark and colour while something waits for an answer (§1).
- **the drawer**: the phone's sheet from the left that the menu opens (§2); it was the projects' drawer.
- **a short name** (`TERMS` `short_name`): an idea's, a goal's or a task's name in 24 characters at most (§3).
- **a recommended answer** (`TERMS` `recommended_answer`): the choice the Taskmaster picks for one of its questions
  (§9).
- *Let the Taskmaster decide*: the button that answers every question of a card with its recommended answer (§9).

## 1. Needs you is the signal (A0, B, C)
- **What counts**: the snapshot's `needs_you` (the rows that wait for an answer — asks, a plan to start, a to-do, a
  failure, a goal's questions, an Operation's check; proposals never) and `review_count` (results waiting in Review).
  Both are there today: no backend change.
- **The phone**: the top bar's ! chip goes. The Needs you tab shows, while `needs_you` > 0, orkUI's `warning-diamond`
  in place of the eye and its count in orkUI's warning colour (`.ork-count.warning`, A0: as `.ork-btn.warning`); while
  only `review_count` > 0, the eye and a plain count; nothing when both are 0. Its label says which: *Needs you: 2
  wait for your answer, 3 results to check*.
- **The desktop**: the Board tab's count (its Needs you's) is `.ork-count.warning` when it is above 0; Review's stays
  plain.

## 2. The top bar and the drawer (A0, B)
- **The top bar**: the `menu` mark at its left (it opens the drawer) · the goal's head and its short name, one line (a
  tap picks another goal, Operations or the Map, as today) · the limits chip, only when a tool is low (as today). The
  project's name, the ! chip and the gear leave it.
- **The drawer**, in this order: **Stop all** (danger, as the gear's today); **Spend today**; **the projects** (as
  today, the project shown said in the drawer's head); **This project**: Target (Thrift, Balance, Quality, each with its
  line: `shell-words.js` `TARGETS`), Start plans by themselves, the night's hours, Push after merging (sends your code
  to origin), What is left (the limits' sheet); **This phone**: Pair a phone (the sheet that says it is done at the
  computer), Download the logs (Today, The last 7 days), Unpair this phone (from the Board's foot). Each setting writes
  with today's command (`ideas.board_set`, `ideas.into`), at once.
- **The Board** loses its heading and its Target row (the tab says *Board*; the Target is the project's setting).
- **A goal's settings** stay on its screen (Edit goal: its words, craft, priority; its team: §7). Nothing of a goal is
  in the drawer.

## 3. A short name (A, B, C)
- **Made by code** (`realm/idea_words.py` `short_of(text) -> str`, no model): the first sentence of `text`, the asking
  words at its start left out (`ASKING`, English and Russian: *let's, we should, I want, maybe, please; давай, давайте,
  нужно, надо, хочу, может, можно, пожалуйста*), its first letter in capital, cut at a word's end within 24 characters
  (no "…"); a code name (`sync_queue`, `docs/plan.md`) kept whole when it fits, dropped when it does not; never empty
  (else the first 24 characters at a word's end).
- **Written by the model where a call runs anyway**: the draft's JSON gains `"short": "two or three words"` beside
  `"title"` (`core/idea_draft.py`); the goal's reading the same (`core/idea_goals.py`); each task of the plan's JSON
  `"short"` beside `"title"` (`core/idea_keeper.py`). Parsed strictly: at most 24 characters and 4 words, else
  `short_of` of the title.
- **Kept**: an idea's and a goal's in their page's front matter (`short`), a task's in `plan.json`. An idea's is set by
  `ideas.add_idea` from the person's text, then by the draft; a goal's by `ideas.save_goal`, then by the reading.
- **Sent** beside every `title` a chip or a tab shows: `ideas.board`'s rows and goals, `ideas.map`'s goals, nodes and
  tasks, `ideas.agents`' chips (`idea_short` beside `idea_title`). Never empty: a page or a task written before has
  `short_of(title)`.
- **Shown**: a goal's tab, a Map node's chip, a task on the trail and an agent's chip show `short`, in the text face,
  on two lines at most (`-webkit-line-clamp: 2`), at the faces' small text step and never smaller; the title is the
  element's `title` and `aria-label`, and the screen it opens is headed by the title. Nothing else is renamed.

## 4. The Map's one action (A, B)
Beside the chip of a node that waits for the person alone, one button (a sibling of the chip's open button, never inside
it), in the same row; at most one per node:

| the node | its button | its command |
|---|---|---|
| `needs_you` `plan`, `waits_on` empty | `play` mark and the estimate's price (*~$2–4*, `shell-preview.js` `price`) | `ideas.start` |
| a plan passed to start at night (`start_at` `night`), not started | `play` mark, *Start now* | `ideas.start_now` |
| `state` `raw`, queue `night` or `hold`, no `held_until` | *Process now* | `ideas.queue` `{queue: "now"}` |

- Its `aria-label` says it whole: *Start “Offline mode”: 3 tasks, about $2–4*. The host's answer is said as the idea's
  screen says it (*Started.*, *The Taskmaster drafts it now.*, or its refusal); the Map reads again on `ideas.changed`.
- No button while the node waits for anything else (its chip says what, spec 39 §4.3). A check is skipped as spec 39
  says; an idea is put aside from its screen (*Tonight*); a task of code is never skipped. No long press, no swipe.
- **Measured** (A): `ideas.start`, `ideas.start_now` and `ideas.queue` take `via` (`"map"`, `"idea"`); `plan_passed`
  logs it, and the two that log nothing today log it in new events: `plan_started_now` (idea, via) and `idea_queued`
  (idea, queue, via).

## 5. New idea's button (A0, B)
- The Board keeps one button at the bottom right: `plus`, *New idea*. Speak leaves the Board.
- In New idea's sheet, Speak is the `mic` mark at the field's corner (`shell-idea-field.js`), where the browser has
  speech to text; its label *Speak the idea*. Where it has none, the hint says *Speak it with the keyboard's microphone*
  (as today).

## 6. New goal on one sheet (B)
One sheet, top to bottom, Save goal pinned at its foot (enabled once the description has words):
1. **What for**: the description (focused), the priority.
2. **Craft**: one row of six heads — the five crafts and Mixed —, each named in its label; under the row, the picked
   one's word and line (*Product: who it is for, what it moves, what it leaves out*). A tap picks it and sets the team
   to the craft's party (`ideas.roles` `parties`), as the first step does today.
3. **Team**, folded to one line — *Leads: Product manager · Builds: Product designer, Grunt · Checks: Reviewer* — with
   Change. Opened, three folds, one open at a time, each fold's head saying what is in it: Leads (one seat: a pick folds
   it and opens Builds), Builds (three at most) and Checks (two at most), each closed by Done; a fold's head opens it
   again.
4. **Checks**, folded to one line (*2 checks, where each applies*), opened as today's third step's.
5. What is left of the AI tools, as today.
The command is today's: `ideas.goal_save` with `craft`, `team`, `every`, `leader`. The desktop's New goal is not
changed.

## 7. A goal's team from its screen (A, B)
- **The phone**: the goal's screen shows its team in one line (the heads with their short names) with Change; Change
  opens §6's Team and Checks folds for this goal; Save sends `ideas.goal_save` `{slug, team, every, leader}`.
- **The host** (A): on a goal that exists, `about`, `title`, `craft` and `priority` that are not given are kept (none
  is ever emptied by a save that leaves it out); a save that changes only its party (`team`, `every`, `leader`) does not
  read the goal again (no model call). The desktop's Edit goal already sends the party; it gains the same.

## 8. Agents (A, B, C)
- **Add agent** opens two ways: **From the library** — the library's agents this project has not (`ideas.roles`
  `library` gains `installed: bool`), each its head, name, craft and what it takes; a tap adds it — and **Your own**
  (today's sheet). The command (A): `ideas.role_add` `{"id"}` makes a library agent a role of this project
  (`library.install`); refused for an id the library has not or the project has already; answers `{"slug"}`.
- **An agent in one line**: its head (the race says its craft, the gear its tier, spec 40 §6) · its name · *×2* (at most
  at once) · *≈ $0.40 a task*. `usd_task` on each role of `ideas.roles` and each block of `ideas.agents` (A): its week's
  `spent / finished` (`idea_spend.by_role`) when `finished` ≥ `idea_spend.TOO_FEW`, else `tier_costs()` at its head's
  tier; `null` for the Taskmaster (its cost is its steps: its week stays as it is said today) and while nothing is
  priced. The line's `aria-label` says it in words: *Docs scribe: an elf, Design, Seasoned; up to 2 at once; about $0.40
  a task*. No tool mark (decisions §54.8).
- **Edit agent**: the field is filled with the agent's instruction (as today). For the Taskmaster and the Grunt, whose
  instruction is Orkboard's own, the field is labelled *Added to what it is told* and above it, folded and read only,
  *What it is told already*: `told` on those two roles of `ideas.roles` (A: `realm/roles.py` `TOLD`, one or two lines
  each, written from the keeper's steps and a task's prompt as they are). The Taskmaster's instruction goes before each
  step it runs (A: `core/idea_keeper.py`; it was saved and reached none before).

## 9. A question comes with its answer picked (A, B, C)
- **The model's answer** (the draft's and the goal's reading's JSON): `"questions": [{"ask": "…?", "choices": ["…",
  "…"], "pick": 0, "why": "one line"}]`, 0 to 3, and the prompt adds: *ask only what changes the plan; never what the
  repository, the goal or the person's text already answers*. Parsed strictly (`realm/idea_questions.py`): 2 to 4
  choices of at most 40 characters, `pick` an index of them (else none), `why` at most 120 characters; a question
  without valid choices keeps its ask alone; a plain string is still read (pages and models of before).
- **In the page**, one line each, as today's plus the pick: `Which store first? (**App Store** / Google Play) — most
  of its users are on iPhone`: the recommended choice in bold, so the page says it too. `idea_questions.line(q)` writes
  it, `idea_questions.parse(line)` reads it back (today's `(one / other)` lines too).
- **Sent**: Needs you's rows of kind `asks` and `goal` gain `asked: [{"ask", "choices", "pick", "why"}]` beside
  `questions`; both faces drop their own `choicesOf`.
- **Shown** (B, C): each choice a button; the recommended one pressed at the start and marked *Recommended* in words
  (never by colour alone), its `why` under the question, muted; Send sends what is pressed, so one tap takes every
  recommendation; More opens the form with the recommended answers filled in.
- **Let the Taskmaster decide** (a quiet button in the card): `ideas.answer` `{"slug", "decide": true}` (with `"goal":
  true` for a goal's). Every question is answered with its recommended choice, a question without one with *(no
  answer: decide)*; the talk keeps *Left to the Taskmaster*; the answer call runs as today, and the Decisions lines
  code writes for the answers read `<ask> — <choice> (the Taskmaster's pick)` (every answer's line now says the ask
  alone, not its choices). `keeper.answer` takes an all-empty answer only with `decide`.

## 10. Measured (A)
- `idea_answered` gains `picked` (answers that are one of the choices), `recommended` (that are its pick), `typed`
  (the rest, not empty) and `decided` (bool: Let the Taskmaster decide); a goal's answer, which logs nothing today, logs
  `goal_answered` with the same.
- `plan_passed` gains `via`; `plan_started_now` and `idea_queued` are new (§4).
- The owner's question — *are the likely answers the ones taken?* — is read from these: the share of answers that are
  the recommended one, and of cards left to the Taskmaster, per week.

## 11. Tests
- **A0** (orkUI): `.ork-count.warning`; `menu` and `mic` in the subset, on the grid; here `tests/test_design_system.py`
  (the copy as stamped).
- **A**: `short_of` (both languages, the asking words, a code name, the 24-character cut at a word's end, never empty);
  the draft's, the reading's and the plan's `short` parsed strictly and kept, `short` sent beside every title of
  `ideas.board`, `ideas.map` and `ideas.agents`, a page of before given one; `idea_questions` (`parse` and `line` both
  ways, a bold pick, today's lines, a plain string, bad choices); Needs you's `asked`; `ideas.answer` `decide` (picks
  as answers, Decisions written by code, refused without questions); a party-only `ideas.goal_save` makes no call and
  keeps the goal's words; `ideas.role_add` (added, refused twice, refused for an unknown id); `usd_task` (the role's
  week, the tier's, `null`); `told` on the two; the events' new fields.
- **B** (browser): no ! chip; the tab's warning mark and warning count with answers waiting, the eye and a plain count
  with results only; the drawer's order and each setting's command; no heading or Target row on the Board; a chip's
  short name on two lines with the title in its label; the Map's button for each of §4's three nodes and none for a
  node that waits on an idea; one FAB and the `mic` in the sheet; New goal on one sheet (the folds, a lead's pick
  opening Builds, Save in sight); a goal's team changed from its screen; Add agent's two ways and `ideas.role_add`; an
  agent's line and its label; the built-in two's *What it is told already*; a card's recommended answers pressed, Send,
  and Let the Taskmaster decide.
- **C** (browser): the Board tab's warning count; short names on the Map and the goals' list; an agent's line;
  Recommended pressed in Needs you and the ask dialog; Let the Taskmaster decide.
