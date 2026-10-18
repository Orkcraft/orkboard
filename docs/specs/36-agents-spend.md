# Spec 36 — Agents: what each ork costs and how often it gets it right; Review's two signals; an agent takes its task types

The owner and the PM, 18 October (decisions §48). Agents (33, 34) shows the roles and their live tasks, and a settings
section (Task types). It does not show what an ork spends for a result, how often its result is merged the first time,
where an idea's money went, or whether the person's decision at Review was about quality or cost. This spec adds that,
takes the settings out of the window, and makes the task prompts cheaper. **Build after spec 35 is merged** (its §0
*Measured*, `ran_tier`, `effort`, `tool`, `model` and the Agents chips' words are this spec's ground). **Builds:**
Claude (A on the elder tier; B and C on the warrior tier) · **Review:** full · P1, after the testers' first days
(decisions §48.7: before them only spec 35's two lines).

Three parts, one branch each, in this order; **this file is the contract** (names, data, commands); the rest is the
builder's choice inside its files. Wording: CLAUDE.md (orks by orkish names: the Taskmaster, a Grunt; today's words:
*agent*, *task type*, *Target*, *goal*, *idea*). **Change nothing outside these files.**

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. Backend** | `spec/36-backend` | §1–§4, §6, §7 | new `realm/idea_spend.py`, `realm/roles.py`, `realm/ideas.py` (`drop` keeps the ledger's lines, §1), `realm/analytics.py` (the ledger in the zip), `realm/event_log.py`, `core/idea_keeper.py` (the ledger line in its one call wrapper; `core/idea_draft.py`, `core/idea_goals.py`, `core/idea_night.py` only if spec 35 left a model call there), `core/idea_runner.py`, `gui/ideas.py` (commands, `results()`), `gui/ideas_roles.py`, `gui/mobile.py` (allowlist) |
| **B. Desktop** | `spec/36-desktop` | §5 on the desktop | `gui/static/js/shell/agents.js`, `agentdialog.js`, `review.js`, `preview.js`, `store.js`, `shell.css` |
| **C. Phone** | `spec/36-phone` | §5 on the phone | `gui/static/pwa/shell-agents.js`, `shell-agent.js`, `shell-review.js`, `shell-preview.js`, `pwa/app.css`, `pwa/sw.js` (cache version) |

B and C branch from A once A is pushed; they touch no file of each other's.

## Why (facts, 18 October)
- A task's cost is the sum of its rounds (`core/idea_runner.py` `_session`): a send back's rework cannot be told from
  the first try. The keeper's cost is dropped (`core/idea_keeper.py`, `_cost`), and its calls are tagged by tier, so
  after spec 35 every step reads `plan` (`_claude`: `{"laborer": "sort", "elder": "plan"}`).
- `realm/call_log.py` has every call, but the day logs are cleared each morning (`gui/day_logs.py`): not a ledger.
- The plan's estimate comes from fixed defaults (`idea_keeper.estimate`, `plans.DEFAULT_COST`), so *over the estimate*
  means little.
- The model list of a role repeats the tiers (`roles.models()`: *Elder tier (opus)* and *opus*); a role's instruction
  may be 4 000 characters (`roles.INSTRUCTION_CHARS`), and it goes into every task (§40's personas: 600).
- The runner pastes the repository's CLAUDE.md (up to 12 000 characters, `CLAUDE_KEEP`) into every task's prompt,
  after the task's own text, while Claude Code most likely reads the same file by itself in the worktree (§6).

## 1. The ledger: what each call cost, kept with its idea
- After every model call of the board, one line is appended (A):
  - a keeper call on an idea → `<state_dir>/ideas/<slug>/spend.jsonl`; on a goal → `<state_dir>/goals/<slug>/spend.jsonl`;
    the night's proposals (no idea yet) → `<state_dir>/ideas/spend-board.jsonl`;
  - a task's turn → its idea's `spend.jsonl`.
- A line: `{"at", "step", "task"?, "round"?, "role", "tool", "model", "tier", "effort", "tokens": {"in", "out",
  "cache_read", "cache_write"}, "cost"}`. `step` is spec 35 §1's name (`goal`, `draft`, `answer`, `talk`, `plan`,
  `refresh`, `propose`), `task` for a task's turn in its `round`, `fix` for the gate's own retry inside a round. `role`
  is `taskmaster` for the keeper, else the task's role. `cost` is the tool's $ (API prices), `null` when unpriced:
  never 0.
- Written in two places only: the keeper's one call wrapper and the runner's turn (where its cost is added today).
  Appending never troubles the work: a disk that refuses is ignored, as `realm/event_log.py` does.
- `ideas.drop` appends the idea's lines to `<state_dir>/ideas/spend-gone.jsonl` before its folder goes, so the week's
  numbers (§2) keep what a deleted idea cost.
- The analytics zip (spec 33 §9, `realm/analytics.py`) carries each idea's `spend.jsonl` beside its `plan.json`.

## 2. The rollup: `realm/idea_spend.py` (code, no model)
- `STAGES = ("goal", "spec", "plan", "work", "rework", "dropped")`: **goal** ← `goal`, `refresh`; **spec** ← `draft`,
  `answer`, `talk`; **plan** ← `plan`; **work** ← `task` in round 1; **rework** ← `task` in round 2 and later, and
  `fix`; **dropped** ← every line of a task that ended `failed` (dropped by the person or failed), taken out of work and
  rework. `propose` is counted only in the Taskmaster's week.
- `of_idea(state_dir, slug)` → `{"usd", "unpriced", "stages": {stage: {"usd", "tokens", "calls"}}, "tasks": {tid:
  {"usd", "work", "rework"}}}`.
- `of_goal(state_dir, slug)` → its own lines (stage *goal*) and its ideas' stages summed, with `merged` (tasks merged)
  and `usd_per_merged`.
- `by_role(state_dir, days=7)` → `{role: {"spent", "merged", "first_time", "finished", "usd_per_merged"}}` over the
  tasks finished (merged or failed) in the last `days` and their lines; **first time** is merged in round 1;
  `usd_per_merged` is everything the role spent on those tasks, dropped ones included, over `merged`, and `null` while
  `merged < 3` (too few to say). The Taskmaster's row: `spent` (its lines by `at`), `plans` (made), `first_time` and
  `finished` over **all** the tasks of its plans, whoever did them: the spec's quality, decisions §48.4's 95 %.
- Money: `usd` sums the priced lines; `unpriced` counts the lines with `cost: null`; a sum of only unpriced lines is
  `null`, shown *—*. Read on request; `by_role` is cached for 60 s.

## 3. A role is who; the Target is how much thinking (decisions §48.2)
- `roles.models()`: `""` **By Target** first, then the three tiers with the harness's model small (*Elder · opus*,
  *Warrior · sonnet*, *Laborer · haiku*), and nothing else. A role file that names another model (written before, or by
  hand) keeps it and runs it; for that role the list shows it as one more option, *opus (set by hand)*, so saving the
  dialog never changes it silently.
- `""` is allowed for every role but the Taskmaster (today only Grunt): it runs as Grunt does, on the task's planned
  tier shifted by the Target (spec 35 §1). A new agent is `""` by default (today `warrior`). The Taskmaster picks a tier
  only (its default `elder`, spec 35's rule).
- No effort on a role: the Target gives it (spec 35 §1).
- **The instruction is at most 600 characters** (`INSTRUCTION_CHARS = 600`). `ideas.role_save` refuses a longer one:
  *An instruction is at most 600 characters*. One that is longer in its file (written before) goes into a prompt cut at
  its last sentence end within 600, its dialog says *Only the first 600 characters go to the ork: shorten it*, and the
  file is not rewritten until the person saves.
- **An agent takes its task types.** `ideas.role_save` gains `kinds` (the task types this agent takes), written with the
  role: a type another agent had moves here, a type unticked goes back to Grunt. Grunt takes what no other agent takes
  (not set on Grunt); the Taskmaster takes none (refused, as `set_kind` does). `ideas.kind_set` stays for old callers.

## 4. Review: the cost against the plan, and the cost signal (A)
- `results()` (and so `ideas.review_list`) gains per result: `work`, `rework` (§2's split of its `cost`), `estimate:
  {"low", "high"}` (the task's planned share: §6's learned cost of the tier it ran on, ±50 %) and `over`: `cost / high`
  rounded to one place when the cost is over `high`, else `null`.
- `ideas.merge` gains `"dear": bool` (default `false`): written on `result_decided` as `dear`. Nothing else happens on it
  (decisions §48.5: the night reads these after the testers, not this spec).
- **New command `ideas.spend`** `{"idea"}` or `{"goal"}` → `of_idea` / `of_goal`. Review's result preview uses it for its
  idea; the Board's goal and idea views use it in the Board's own next round, not here.

## 5. Screens (B, C)
**Agents, a monitor** (decisions §48.1):
- The **Task types** section goes, and with it *New agent…*; **+ Add agent** stays at the top.
- A role's head: its name · its model in words (*By Target*, *Elder · opus*) · *up to N* · today's *≈$0.42 today* (as
  today) · then its week, once it has three merged results: *≈$0.90 a result · 8/10 the first time*. The Taskmaster's
  head: *8/10 tasks the first time* (its plans' tasks). Every ≈$ has the hint *At API prices, not your bill*. *Takes:
  code, tests* under the head, as *Does:* is today.
- The chips in this order: *needs you* ⚠ first, then *working*, *testing*, *queued*, *held*, *at Review*; spec 35's words
  (*by itself*, *tonight*, the held reason) stay. A chip opens its task, as today.

**The agent's dialog:** Name · **Model** (§3's list; under it one line: *By Target: the task's own tier, moved by the
Target*) · At most at once · **Instruction** with a counter *412 / 600* · **Takes**: the five task types as checkboxes,
each with whose it is now, small (*now Grunt*). On Grunt the boxes are shown, not editable, with *Grunt takes what no
other agent takes*; the Taskmaster's dialog has no Takes. Deleting an agent says which types go back to Grunt, as today.

**Review card:** *Cost ≈$1.80 · planned $0.30–0.90*, and *2× over* in the warning role when `over` is set; in round 2
and later, *(rework $0.50)*. Beside **Merge into dev**, a checkbox **Cost too much for this**, never ticked by itself;
it goes with the press. Send back and Drop do not change.

**The result's preview:** one line under its title: *This idea so far: ≈$3.10 — goal 0.40 · spec 0.50 · plan 0.20 ·
work 1.50 · rework 0.50* (stages at 0 left out; *—* when all are unpriced).

**The phone** (C): the same; the checkbox sits in the pinned bar, above Merge; the dialog is a sheet (34 §5).

## 6. Cheaper task prompts and an estimate that learns (A)
- **CLAUDE.md once.** The builder checks the installed `claude` once: in a scratch git repository whose `CLAUDE.md` holds
  a marker line, `claude -p "Quote the marker line of your project instructions" --output-format json`. If the answer
  quotes it, Claude Code reads the repository's CLAUDE.md by itself in a task's worktree, and the runner's paste
  (`# The repository's rules (CLAUDE.md)`, `CLAUDE_KEEP`) goes. If not, the paste moves to the front of the prompt (the
  same for every task, so the prompt cache shares it). The report prints what the check answered; a test holds the
  choice.
- **Stable first** (spec 28 §1's rule, now for the runner): the role's instruction, then the finishing rules without
  the secrets' names; then what is the task's own: where it works (idea, branch), the path of its spec (spec 35 §13:
  the path, never the page), the task, the tasks before it, the secrets' names. The same words; only the order
  changes.
- **The estimate learns** (`idea_keeper.estimate`): a tier's cost is the mean cost of the board's last 20 finished tasks
  that ran on it (`ran_tier`, from the ideas' `plan.json`), else `plans.DEFAULT_COST`; ±50 % as today. Take it to work
  and §4's `estimate` use it.

## 7. Commands and events (A)
| command | args | returns |
|---|---|---|
| `ideas.spend` | `{"idea"}` or `{"goal"}` | §2's `of_idea` / `of_goal` |
| `ideas.roles` | — | as today; roles gain `kinds`, `week` (§2's row), `hand_model` (bool); `models` as §3 |
| `ideas.role_save` | as today, and `"kinds": [..]` | `{"slug"}` |
| `ideas.agents` | — | as today; each role block gains `week` |
| `ideas.review_list` | — | as today; results gain `work, rework, estimate, over` |
| `ideas.merge` | as today, and `"dear": bool` | as today |

All callable from the phone (`gui/mobile.py`). Events (spec 33 §9, the same log): `result_decided` gains `dear`;
`role_saved` gains `kinds` and `instruction_chars`. No new event.

## Not in this spec
The night's proposals from Review's signals (decisions §48.5, after the testers); tools, images and the Alchemist
(§48.6); task types as three routes (§44.3); an effort or a Target of a role's own; harnesses compared (§48.3); the
Board's goal and idea views showing their spend (the Board's next round, from `ideas.spend`); a list of reasons for a
send back (the line stays free text); a share of the window per task.

## Tests
- **A:**
  - the ledger: a keeper call (stubbed) and a task's two rounds and a gate retry write their lines with `step`,
    `round`, `role`, `tool`, `model`, `tier`, `effort`, `tokens`, `cost`; an unpriced stub writes `cost: null`;
    a deleted idea's lines land in `spend-gone.jsonl`; the analytics zip holds `spend.jsonl`;
  - the rollup: a fixture idea (goal, draft, answer, plan, task round 1, task round 2, a fix, a dropped task) gives
    each stage its sum; only unpriced lines give `null`, never 0; `by_role` over 7 days: merged, first time,
    `usd_per_merged` `null` under 3 merged; the Taskmaster's first time over all its plans' tasks;
  - roles: the model list (By Target, three tiers, a hand-set model only for the role that names it); `""` saved for a
    person's role, refused for the Taskmaster; an instruction over 600 refused on save, cut at a sentence end on load,
    its file untouched; `kinds` in `role_save` moves a type from another agent and an unticked one back to Grunt;
    Grunt's and the Taskmaster's kinds refused;
  - Review: `estimate` and `over`; `ideas.merge` with `dear` writes it on `result_decided`;
  - the prompt: the stable part is byte-identical for two tasks of one role and comes first; CLAUDE.md is not pasted
    (or is at the front, as the check chose); the estimate learns from the last 20 tasks of a tier;
  - `tests/test_architecture.py`.
- **B:** browser tests at 1 440 × 900 (stub host): no Task types section; a role's head with its week from the stub and
  without it under three merged; *needs you* chips first; the dialog's model list, its counter, Takes moving a type
  from Grunt (Grunt's block no longer says it); a Review card with *planned* and *2× over*; the checkbox unticked by
  default and sent with Merge; the result preview's idea line.
- **C:** the same at 390 × 844 as sheets; no horizontal scroll.
- Each part: the critical tests (CLAUDE.md "Alpha"), the touched modules' tests (`test_roles.py`,
  `test_idea_runner.py`, `test_idea_keeper.py`, `test_ideas.py`, `test_gui_ideas.py`, `test_shell_browser.py`,
  `test_pwa_shell_browser.py`, `test_board_loop.py`, and `idea_spend`'s own), `tests/test_gui_wording.py`, and the four
  checks of specs/README.md "Before you commit". The PM merges A, then B and C.
