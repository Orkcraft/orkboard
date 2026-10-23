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
5. The page (`ideas.page`) gains `changed` (the list, `[]` when none), `passed` (true when the plan is passed) and
   `change` (§2.4's summary while one waits, else `null`).

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
2. Its place in the hand: as a plan's (`sort_needs`), the party's. A goal has at most one.
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
