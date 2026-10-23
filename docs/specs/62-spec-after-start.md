# Spec 62 — The spec after the start: talked over with the party's leader by name, and a change re-plans what is left

The owner, 23 October (decisions §75): *I want to edit and discuss the spec with the leader, before the work starts and
after it, ideally each point on its own, and it should change the work in progress.* Half of it is there: a goal's
preview asks about one section at a time (`ideas.say` with `section`: the leader rewrites that section and writes what
was decided), a section can be written by hand (`ideas.edit`), and a plan not passed is made again by **Re-plan**. But
the talk is signed *the Taskmaster* whoever leads the party, and **once the plan is passed the spec is cut off from the
work**: a talk or an edit still rewrites a section, and nothing reaches the tasks (`plan()` refuses: *Its plan is passed
already*). So: **the talk names the party's leader**; **a goal whose plan-making sections changed says so in its
preview**, with *Re-plan* before the start and **Re-plan what is left** after it; the leader then proposes **a plan
change**: the tasks not started changed, dropped or added, the tasks at work and the merged ones left as they are, and
**it comes to the hand as one stop** — what changes and what it costs — answered *Take the new plan* or *Keep the plan*.
**Builds:** Claude · **Review:** full · P1.

**What it is, and is not:** the person presses for a re-plan (a model call each, so never by itself on every edit); the
leader never stops or rewrites a task that has started; nothing is applied without the person's *Take*. Storage keeps
its shape: `plan.json` as today (new tasks are tasks of today's shape), one new file beside it while a change waits
(`plan_change.json`), one new key in `state.json` (`changed`). Not: a party's description changing its goals (a party
has no plan: decisions §75.4), a link from each Done when line to its tasks (the briefs name them, as today), a talk on
one line of a section.

Three parts. **A first; B and C once A is in `main`** (they touch no file of each other's). **This file is the
contract**; the rest is the builder's choice inside its files. Change nothing outside a part's files but those §8 names.

| part | builds | files (and their tests) |
|---|---|---|
| **A. Host** | §1–§4 | new `core/idea_revise.py` (the keeper's side: `revise`, its prompt, `revise_one`; a mixin as `core/idea_draft.py` is), `core/idea_keeper.py` (the mixin; `talk_one` and `plan_one` keep `changed`), `core/idea_review.py` (the runner's side: `revise_tasks`, beside `skip_task`, under the runner's lock), new `realm/idea_change.py` (`plan_change.json`: read, write, drop; the sections that make a plan), `realm/ideas.py` (`STATE_DEFAULT` gains `changed`), new `gui/ideas_revise.py` (`ideas.revise`, `ideas.revise_answer`: a mixin as `gui/ideas_party.py` is), `gui/ideas.py` (the mixin, its two commands in the table, `edit` keeps `changed`, the page's `changed`, `passed` and `change`), `realm/board_map.py` (the stop `change`), `gui/ideas_board.py` (its place in the hand's order), `gui/mobile.py` (the allowlist), `realm/event_log.py`, `realm/lexicon.py`; new `tests/test_idea_revise.py`, `tests/test_gui_ideas.py`, `tests/test_board_map.py`, `tests/test_event_log.py`, `tests/test_lexicon.py` |
| **B. Desktop** | §5, §6 | `js/board/idea.js` (the leader's name in the talk; the changed line), `js/shell/preview.js` (the plan screen's *The change*), `js/arena/arenawords.js` (`stopsOf`: the stop `change`), `js/arena/stops.js` (its answers; *Take the new plan* deals), `js/shell/shell.css`, `js/arena/arena.css`; new `tests/test_plan_change_desktop_browser.py` |
| **C. Phone** | §5, §7 | `pwa/shell-preview.js` (the leader's name; the changed line; the plan's *The change*), `pwa/shell-stops.js` (the stop `change` and its answers; *Take the new plan* deals), `pwa/shell-arena-words.js` (the hand's item, if it is made there), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_plan_change_browser.py` |

## 0. The words
- A new concept, one word in the glossary (`realm/lexicon.py`): **plan change** / *plan changes* — the leader's re-plan of
  what is left after a goal's spec changed (spec 62). The code says `change` (`plan_change.json`, the stop's kind).
- New strings, in these words: *Re-plan what is left*, *<sections> changed since the plan*, *<sections> changed since the
  work started: the tasks not started may change*, *<leader> re-plans what is left…*, *The plan changes*, *Take the new
  plan*, *Keep the plan*, *The change*, *added*, *changed*, *dropped*, *left as it is: it started*, the refusals of §2.
- *<leader>* is the party's leader's name (`ideas.map`'s `goals[].leader.name`), *the Taskmaster* when it leads or is
  not known (*The Taskmaster* at a sentence's start).

## 1. What changed since the plan (A)
1. **The sections that make a plan**: those `plan_prompt` reads — *Gist*, *Done when*, *Out*, *Risks*, *Depends on*
   (`idea_change.PLAN_SECTIONS`; a test keeps it equal to what `plan_prompt` reads).
2. `state.json` **`changed`**: the names of those sections written since the plan was made, in `PLAN_SECTIONS`' order,
   each once. A section is *written* when `talk_one` writes it (its `sections` answer) or `ideas.edit` sets it, and its
   text differs from what it was. Other sections (*Why*, *Open questions*, *Decisions*, *Stages*) never count.
3. Kept only for a goal with a plan: no plan, nothing is kept (the draft and the answer write the spec before any plan).
4. Cleared when a plan is made (`plan_one` saves one), and when a plan change is answered (taken or kept, §3).
5. The page (`ideas.page`) gains `changed` (the list, `[]` when none), `passed` (true when the plan is passed),
   `change` (§2.4's summary while one waits, else `null`) and `revising` (true while the leader re-plans what is left:
   `busy` alone is a talk too).

## 2. Re-plan what is left (A)
1. **`ideas.revise {slug}`**: refused, in words, when the goal has no plan (*This goal has no plan yet*), its plan is not
   passed (*Its plan is not started: Re-plan it*), it is done (*This goal is done*), the keeper is busy with it (*The
   keeper is busy with this goal: a moment*), or as `plan()` refuses (the demo, the budget, a spent window). Otherwise it
   answers `{ok}` and the keeper runs **`revise_one`** in the background (busy *planning*, as Re-plan); the goal's
   state does not change.
2. **`revise_one`**: one call on the `plan` step, one shot, read-only, with `plan_prompt`'s context (the sections, the
   party's summary, the team's lines, the checks) and three more parts, cut to the `plan` context's size:
   - *What changed*: the names in `changed` (none: *the person asked to look again*) and the last 10 lines of Decisions;
   - *Done*: the merged tasks, `id title` each; *At work*: the tasks running, testing, in Review or picking, `id title`
     and their brief — **these stay as they are**;
   - *Not started*: the tasks waiting, ready or held, as the plan wrote them (`id, title, short, brief, kind, tier,
     after`).

   It answers one JSON object: `{"why": "one line to the person", "change": [{id, title, short, brief, kind, tier,
   after}], "drop": [id], "add": [{key, title, short, brief, kind, tier, after}]}`: `change` and `drop` name only tasks
   not started; `add`'s `key` is `n1`, `n2`…; any `after` names a task of the plan or an added one's `key`; a not-started
   task named in neither `change` nor `drop` stays. Unknown ids, a `change` or `drop` of a started task, an `after` that
   names nothing or closes a cycle: left out (the rest is kept). An empty answer (nothing changes) is kept as a change of
   nothing: its stop says so (§4.2).
3. **Saved as a plan change** (`plan_change.json`, `realm/idea_change.py`): `{made_at, why, changed: [the sections it was
   made for], change, drop, add, estimate: {usd_low, usd_high}}`. The added tasks get their `role` as `plan_one` gives it;
   their ids are given only when it is taken (§3.2). `estimate` is what it adds or saves: the estimate (`idea_plan.
   estimate`, as `plan_one` prices a plan, with the Target and each role's model) of the added and changed tasks less
   that of the dropped and of the changed tasks as they were; negative when it saves. A newer one replaces it. Logs
   `plan_revised` (§4.4).
4. **The summary** (the page's `change` and the stop's): `{made_at, why, added: n, changed: n, dropped: n, usd_low,
   usd_high, rows: [{op: "add"|"change"|"drop", id, title}]}` (`id` `""` for an added task).
5. On failure the keeper's error is the goal's `error` as a Re-plan's is (*No plan change: …*), and nothing is saved.

## 3. Take the new plan, or keep the plan (A)
1. **`ideas.revise_answer {slug, take, via?}`**: refused when no plan change waits (*No plan change waits for this
   goal*). `take: false` drops the file and clears `changed`. `take: true` applies it (§3.2), then drops the file and
   clears `changed`, writes the goal's *Stages* again (as `plan_one` does), and answers `{ok, added, changed, dropped,
   left}` (counts; `left`: the titles of the tasks it named that had started meanwhile).
2. **Applied by the runner, under its lock** (`IdeaRunner.revise_tasks(slug, change)` in `core/idea_review.py`, under
   `self._lock` as `tick` and `skip_task` are, the plan read fresh inside it):
   - **drop**: each task still waiting, ready or held is taken out as `skip_task` takes one (out of the others' `after`);
   - **change**: each task still waiting, ready or held takes the new `title`, `short`, `brief`, `kind`, `tier`, `after`
     and `role`; its `id`, state and the rest are kept;
   - **add**: each added task is appended in `state: "waiting"`, its id the next free one (`k<n>`, after the highest
     `k` of the plan, never one used before), its `after` mapped from the keys to those ids;
   - a check task (`realm/idea_checks.py`: it waits for every other task) gains the added ids in its `after`;
   - a task it names that started meanwhile is left as it is and named in `left`;
   - the plan's `estimate` is made again from its tasks; `passed_at` and the rest are kept.
   Then the runner settles the goal (`_settle_idea`), publishes and ticks: the new tasks are taken up as any waiting
   task (`_advance`). A goal that is failed or stopped keeps its state: its new tasks wait for its work to start again.
3. A plan change waiting is **dropped by itself** when the goal is done or its plan is made again (Re-plan before the
   start), and when every task it would change or drop has started and it adds nothing.
4. **The talk and the edit while a change waits** keep `changed`; the stop stays; *Re-plan what is left* again makes a
   newer one.

## 4. The stop and the events (A)
1. **The stop** (`realm/board_map.py`, beside the plan's): while `plan_change.json` exists, `{idea, goal, title,
   priority, blocks: false, at: made_at, kind: "change", text, why, added, changed, dropped, usd_low, usd_high}`; `text`
   says it: *The plan changes · +2 · 1 changed · −1* (only the parts that are not zero; *The plan stays as it is* for a
   change of nothing).
2. Its place in the hand: as a plan's (`sort_needs`), the party's. A goal has at most one. The Map's node names it
   (`needs_you` `change`, `board_map.NEEDS`), so its goal's row is marked as one that waits for the person, and the
   leader stops on it (`map_party` `_LEAD_NEEDS`); a push names it *A plan change waits for you* (`phone_push.KIND_WORDS`,
   with the desktop's `js/board/today.js` `KIND_WORDS`).
3. `gui/mobile.py` lets the phone call `ideas.revise` and `ideas.revise_answer`.
4. **Events** (`realm/event_log.py`, the same log): `plan_revised {idea, changed, added, changed_n, dropped, usd_low,
   usd_high}` and the keeper's measure (`step`, `prompt_chars`, `tokens`, `cost`) as `plan_made` has; `plan_change_answered
   {idea, take, added, changed_n, dropped, left, via}`; `idea_edited {idea, section, chars, passed}` for a section written
   by hand (there is none today).
5. **Measured** (the owner reads): how many goals change their spec after the start; how many plan changes are asked,
   taken and kept; what they add; how long after the start.

## 5. The talk names the leader (B, C)
- In a goal's preview, the talk's speaker, its placeholder (*Ask or answer <leader>…*), *<leader> is answering…* and every
  other *the Taskmaster* of the preview's talk and plan say the party's leader (§0), read from the map (the goal whose
  slug is the page's `track`). The phone's *Sent: <leader> answers in a moment.*

## 6. The desktop (B)
1. **The changed line** (`js/board/idea.js`), under the sections, when the page's `changed` is not empty:
   - before the start (`passed` false): *<Gist and Done when> changed since the plan.* and **Re-plan** (`ideas.plan`);
   - after it: *<…> changed since the work started: the tasks not started may change.* and **Re-plan what is left**
     (`ideas.revise`); while the keeper works on it: *<leader> re-plans what is left…*, the press off; while a change waits
     (`change` not null): *<leader> proposed a plan change: it waits for you below.* and the press says *Re-plan what is
     left again*.
   - The names are joined as the interface joins a list (*Gist, Done when and Out*). A done goal says nothing.
2. **The stop in the hand** (`arenawords.js` `stopsOf`, `stops.js`): kind words *Plan change*; its gem the price it adds
   (*+$0.40–1.20*; *−$…* when it saves; no gem for a change of nothing); its text the stop's `text`, its `why` under it,
   muted. Its quick answers: **Take the new plan** (primary: `ideas.revise_answer {slug, take: true, via: "hand"}`; its
   toast *The plan changed: 2 added, 1 dropped.*, with *k left as they were: they started.* when `left`) and **Keep the
   plan** (`take: false`; toast *The plan stays as it was.*); a press elsewhere on it opens the plan screen.
3. **Take the new plan deals** its added tasks from the stop's box onto their columns, as *Start the work* does (spec 57,
   its rules and timing; the same moment of decisions §76.3: the work dealt).
4. **The plan screen** (`js/shell/preview.js`) shows **The change** over the plan while one waits: its `why`, then its
   rows — *+ <title>* added, *~ <title>* changed, *− <title>* dropped (muted, struck) — and the two presses of §6.2.

## 7. The phone (C)
1. **The changed line** in the preview (`shell-preview.js`): as §6.1, its press 44 px.
2. **The stop in the hand** (`shell-stops.js`): as §6.2 on the raised card (its kind word, the gem, the text and `why`);
   the quick answers *Take the new plan* and *Keep the plan*; the raised card's way out as every stop's (spec 54).
3. **Take the new plan deals** its added tasks as *Start the work* does on the phone (spec 57 §4: only into the stage
   shown, the stage not switched).
4. The plan's screen shows **The change** as §6.4.
5. `sw.js` `CACHE` one up from what `main` has, with `tests/test_pwa.py`'s pin.

## 8. Files a part may need beyond its row
A: `core/idea_plan.py` if `estimate` needs a helper; `core/idea_runner.py` only to call the new method or to settle (no
new code there: it is at 593 lines); `realm/idea_checks.py` if a check task's `after` needs a helper. B: the desktop tests
that read the preview's talk words (*the Taskmaster*) or the hand's kinds. C: the phone tests that read the preview's
talk words or the hand's kinds. A part that needs any other file: stop and write it in §10 first.

## 9. Tests
- **A** (`tests/test_idea_revise.py` with a fake keeper call, `tests/test_gui_ideas.py`): `changed` kept by a talk and by
  an edit of a plan section, not by *Why* or *Open questions*, not for a goal with no plan, not when the text is the
  same; cleared by a plan made and by an answer; `PLAN_SECTIONS` equals what `plan_prompt` reads; `ideas.revise`'s
  refusals; the prompt holds the not-started tasks and names the started ones as staying; an answer that changes a
  started task, names an unknown id or closes a cycle is cut; the estimate's sign; `revise_answer` take: a dropped task
  gone from the plan and from the others' `after`, a changed one's fields and its kept id and state, an added one's
  fresh id (never a used one, after a skip too), its `after` mapped, the check task's `after`, a task that started
  meanwhile in `left`; keep: the plan as it was; the stop's fields and words; the dropping by itself; the events'
  fields; the glossary's word; the runner picks an added task up (`_advance`) on its next tick.
- **B** (browser, 1 440 × 900): the talk says the Game party's leader (*Ask or answer Game designer…*) and *the
  Taskmaster* for a Taskmaster party; the changed line before the start (*Re-plan*) and after it (*Re-plan what is left*
  sends `ideas.revise`); the stop with its gem, text and why; *Take the new plan* sends the answer and deals the added
  tasks (`is-dealt`); *Keep the plan*; the plan screen's *The change*; reduced motion: no deal.
- **C** (browser, 390 × 844): the same on the phone; the deal only into the stage shown.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_architecture.py`; C also `tests/test_pwa.py`.

## 10. As built (notes, no change of the contract)

### Part A (the host), 23 October

**Where.** New `realm/idea_change.py` (`PLAN_SECTIONS`; `changed` kept by `update` and `set_section`, which wrap `ideas.update` and `ideas.set_section`
under `ideas.LOCK` and keep a plan-making section whose text differs; `plan_change.json`: `read`, `write`, `drop`; `live`, `stale`, `settle`; `summary`,
`text_of`; `safe_after`, `in_order`), `core/idea_revise.py` (the keeper's mixin: `revise`, `revise_prompt`, `clean_change`, `change_price`, `revise_one`),
`gui/ideas_revise.py` (`ideas.revise`, `ideas.revise_answer`, the page's three keys, `edited`, `settle_change`). `core/idea_review.py` gains
`revise_tasks` (and `_highest_id`) beside `skip_task`; `core/idea_keeper.py` mixes the keeper's side in, `talk_one` writes through `idea_change.update`, `plan_one`
clears `changed` and drops a waiting change once its plan is saved; `gui/ideas.py` has the mixin, the two commands, the page's keys, `edit` through
`edited`, and calls `settle_change` on every change of a goal; `realm/board_map.py` makes the stop; `realm/ideas.py` `STATE_DEFAULT` has `changed`;
`realm/event_log.py` the three events; `realm/lexicon.py` `plan_change`. `core/idea_runner.py` is untouched. Tests: `tests/test_idea_revise.py` and the A rows
of `test_gui_ideas.py`, `test_board_map.py`, `test_event_log.py`, `test_lexicon.py`.

**The shapes** (for B and C).
- The page: `changed` (`["Gist", "Out"]`, `[]` when none), `passed` (bool), `change` (`null`, or the summary):
  `{"made_at": "2026-10-23T11:00:00", "why": "The export is csv only.", "added": 1, "changed": 1, "dropped": 1, "usd_low": -0.13, "usd_high": -0.38,
  "rows": [{"op": "add", "id": "", "title": "Stream rows"}, {"op": "change", "id": "k2", "title": "Write csv"}, {"op": "drop", "id": "k3", "title": "Task k3"}]}`.
  The rows run added, changed, dropped. A *changed* row's title is the new one, a *dropped* row's the plan's. `usd_low`/`usd_high` are what it adds, negative
  when it saves (then `usd_low` is the smaller saving: −0.13 against −0.38).
- The stop, in `ideas.board`'s `needs_you` (and so the snapshot and the phone's): `{"idea": "cache-the-table", "goal": "speed", "title": "Cache the table",
  "priority": "normal", "blocks": false, "at": "2026-10-23T11:00:00", "kind": "change", "text": "The plan changes · +1 · 1 changed · −1", "why": "The export
  is csv only.", "added": 1, "changed": 1, "dropped": 1, "usd_low": -0.13, "usd_high": -0.38}`; the text is *The plan stays as it is* for a change of nothing.
- `ideas.revise {slug}` answers `{ok: true}`. `ideas.revise_answer {slug, take, via?}` answers `{ok: true, added: 1, changed: 0, dropped: 1, left: ["Task k2"]}`
  (counts of what was applied; `left` the titles of the tasks it named that had started meanwhile). Kept (`take: false`) it answers the same keys, all zero and
  `left: []`. A refusal is a `CommandError` with the sentence of §2.1 or §3.1; also *take is true or false*, and *The keeper is busy with this goal: a moment*
  for an answer while the leader works on a newer change.
- The change file: `{made_at, why, changed, change: [{id, title, short, brief, kind, tier, after, role}], drop: [id], add: [{key, title, short, brief, kind,
  tier, after, role}], estimate: {usd_low, usd_high}}`.

**What the spec left open, and what was chosen.**
1. *The phone's allowlist.* Orkboard has no `gui/mobile.py` (it is Orkline's). The phone's commands are `BoardPhone.allowed` in `gui/board_host.py`, which lets
   through every `ideas.*` command the host has: nothing to change, and `tests/test_gui_ideas.py` `BOARD_COMMANDS` now names the two.
2. *Not started* is waiting, ready or held **and never run** (`started` empty). A task stopped on its own (waits as `ready`, *stopped by you*) or a failed one that
   was started again (`waiting`) has run and keeps its branch: the leader is not shown it as changeable and the runner leaves it (`left`). `idea_change.open_task`.
3. *Check tasks* (kind a checker's tag) are shown to the leader marked `"check": true` and stay: `change` and `drop` of one are left out, no task may wait for one
   (it waits for all), and a check not started gains the added tasks in its `after` (a check that has started does not). The kinds offered to the leader leave out
   the checks' tags, and an added or changed task gets no such tag.
4. *`after`.* A model's `after` is cleaned against a graph that holds the plan's tasks (the dropped ones out), the added tasks by key and the check tasks' implied
   waiting for the added ones; the changes are taken in the answer's order, then the adds, and a dependency that would close a cycle is left out (the rest kept).
   The runner does the same at the take, so two tasks that wait for each other cannot come out of the file.
5. *Ids.* The next id is one past the highest `k<n>` among the plan's tasks, the to-dos' `for` and the `k<n>.log` files beside the plan. A gap is never filled. A
   skipped (or dropped) task that was the highest, and left none of those, can give its id again: nothing of it ever ran. plan.json keeps its shape.
6. *The summary counts what taking it now would do.* A task the change names that has started since (or is gone) is not in the counts or the rows; `left` at the
   take is then for a task that started between the last look and the press. A change whose named tasks have all started and that adds nothing is dropped by itself;
   a change of nothing (the leader named none) is not.
7. *Dropped by itself* is done on the bus (`Ideas._changed` → `settle_change`, on every change of a goal), and every read (`ideas.page`, the stop, the take) ignores
   a stale file meanwhile, so `build` and `board` still write nothing. `changed` stays when it goes by itself (the sections did change since the plan); it is cleared
   when a plan is made or the change answered.
8. *`estimate`* is the difference of two `idea_plan.estimate` results (the added and changed tasks as they will be, less the dropped and the changed as they were),
   so each end is rounded before the subtraction (a cent from the difference of the bases). Priced with the Target, the roles' models and the board's learned costs as
   `plan_one` does.
9. *Roles* are given as `plan_one` gives them (the goal's team and its leader; none: `""`); the plan's `missing` is not made again. A changed task keeps its state,
   except that a `ready` one that now waits for a task not merged waits.
10. *Limits.* At most 8 tasks added by one change; no cap on the plan's total. The prompt's spec takes at most half of the `plan` context, the tasks' part the
    rest (each brief of the tasks not started cut to 4 000 characters shared among them, at least 300; a task at work 300); a *Failed* part names the tasks that failed.
11. *The answer.* A press on *Take* or *Keep* claims the change under `ideas.LOCK` (a second press finds none), puts it back if the runner refuses, and is refused
    while the keeper works on a newer one. *Stages* are written again from the tasks put in order (`idea_change.in_order`: the added tasks come last in the plan).
12. *Events.* `plan_change_answered`'s `left` is a count; for *Keep* its counts are those of the change proposed (so *what they add* can be read from kept ones too);
    `idea_edited` is logged for every section by hand, not only the plan's. `plan_revised` is written by the keeper (no `device`).
13. *`error`.* A failed call sets the goal's `error` to *No plan change: …* (it replaces a failed goal's reason until the runner writes one again); a later success
    clears it only when it is that one.
14. *Not done here (files outside A's row).* `gui/phone_push.py` words only the kinds in its `KIND_WORDS`, so a `change` stop counts in *N wait for your answer* but is
    not named in a push's first line; the Map's `needs_you` (`board_map.NEEDS`, `map_party._LEAD_NEEDS`) is as it was, so a node whose only stop is a plan change
    says nothing of it.

**Review of A (the session that wrote this spec), 23 October.** Added on top of A, as §1.5 and §4.2 now say: the page's
`revising` (`gui/ideas_revise.py` `after_start`: the plan is passed and the keeper is busy *planning*); `change` in
`board_map.NEEDS` (after `plan`) and in `map_party._LEAD_NEEDS`; *A plan change waits for you* in `gui/phone_push.py`
`KIND_WORDS` and `js/board/today.js` `KIND_WORDS` (`tests/test_phone_push.py` keeps the two equal). Tests:
`tests/test_board_map.py` (the node's `needs_you`, the leader's state), `tests/test_gui_ideas.py` (`revising`).

### Part C (the phone), 23 October (`orkcraft-app-v69`)

**Where.** `pwa/shell-preview.js` (the leader's name, the changed line, the plan screen's *The change* and its two presses), `pwa/shell-stops.js` (the stop `change`, its answers, the toast from the host's answer),
`pwa/shell-arena-words.js` (`needsOf` and `URGENCY` take `change`; `changePrice`, `changeWords`), `pwa/shell-goals-words.js` (`STOPS` takes `change`: one word, §8), `pwa/app.css`, `pwa/sw.js` v69 with the pin
in `tests/test_pwa.py` and in the five phone browser tests that pin the cache (`test_pwa_deal_start`, `_one_hand`, `_board53`, `_goal_types`, `_mixed_parties`); new `tests/test_pwa_plan_change_browser.py`
(21 tests: the talk's words for a Game party and a Taskmaster party, the changed line in its four states and for a done goal, the stop and its answers, the deal, the plan screen, v69).

**What the spec left open, and what was chosen.**
1. *The leader* is `leadOf(p)` in the preview: the Map's goal whose slug is the page's `track`, `leaderName` of `shell-goal.js`; `the()` / `The()` (local to `shell-preview.js`) give *the Taskmaster* inside a sentence,
   *The Taskmaster* at its start, any other leader by its name. It names the speaker of the talk, the box's placeholder and label, the toast *Sent: <leader> answers in a moment.* and the other lines of the spec's screen that
   named the Taskmaster (*… drafts it now.*, *… is planning.*). The phone's ask box had no *is answering…* line: it has one now, shown while the keeper is busy and not re-planning and the goal is not reading or planning
   (those say their own).
2. *The changed line* sits under the sections, before the plan. Its press is off while the keeper is busy (a talk too) and while the leader re-plans; its toasts are *<leader> is planning.* (*Re-plan*) and *<leader> re-plans what
   is left.* The waiting words are *<leader> proposed a plan change: it waits for you.* **without "below"**: on the phone the spec's screen covers the hand, so nothing is below it (the desktop's line says it).
3. *The stop.* The gem is `changePrice` (two decimals, the real minus sign for a saving, none when both ends are 0: a change of nothing); the `why` is a muted line under the text (`.raised__why`); `gemOf` and the card take no
   gem. `go()` takes a toast that is a function of the host's answer: *The plan changed: 2 added, 1 dropped.* is read from the answer (`added`, `changed`, `dropped`), not from the stop, so a task that started meanwhile is not
   promised. Nothing applied: *The plan stays as it was.*; `left` adds *2 left as they were: they started.* (**singular: *1 left as it was: it started.***, the spec's plural is ungrammatical for one). *Keep the plan* says *The
   plan stays as it was.* A press elsewhere on the stop is the raised card's *Open it on its own screen* (the plan screen); its way out is the card's *Put it back*, as every stop's.
4. *The deal* is `deal.wait` as *Start the work*'s, set only when the stop's `added` is above 0 (a change that adds nothing leaves no deal waiting to take a task that comes by itself), from the raised card's box, the party
   shown's stop only, the stage shown only, never switched, none under reduced motion (all spec 57's). The plan's screen deals nothing.
5. *The plan screen's presses* are the screen's bar (pinned, 44 px, *Take the new plan* primary, *Keep the plan*), not in the block, so they stay in reach under a long plan; they send no `via`. The block shows the why, the rows
   (*+* added, *~* changed, *−* dropped muted and struck, each mark with its word for a screen reader), the price as the gem has it (*At API prices, not your bill*) and, for a change of nothing, *The plan stays as it is.*
6. *Not done, outside C's row.* `shell-goals-words.js` `asking` (what `STOPS` feeds) is read by nothing on the phone, so a goal at work with a plan change waiting has no mark on its row of the Goals sheet; the leader's member
   state `needs`/`change` reads *needs you* (`shell-map-idea.js` `memberWords` has no word for it) and the stage tab's faces count Planning's stops only (`shell-arena-words.js` `modelOf`), so the Planning tab shows no sign for a
   change; `shell-board.js`'s `STATE_WORDS` still says *the Taskmaster is planning* for a goal whose leader is another.

**Merge of C.** C was built at `orkcraft-app-v69`; specs 60/61 C and 63 C took v69 and v70 first, so the merge made it **`orkcraft-app-v71`** (sw.js and every pin).
