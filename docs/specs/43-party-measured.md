# Spec 43 — A goal's party, measured: a check says what it found, what the party did, its price before it starts, what a check is worth, hints while picking, your parties across projects

The owner and the PM, 20 October (decisions §56). A goal's party is the deck Orkboard builds its work with (a library,
crafts, seats, a party of each craft to start from, a checker's check over every idea), but it is picked once and never
answered: nothing says afterwards whether it was a good party, and a check cannot even say "nothing found" (a check task
that changes no file fails at the gate). This spec makes a check say what it found, then shows what the party did, what
a party costs while it is picked, what a check is worth, with the night's first proposal from a signal, two quiet
hints, and the person's own parties, saved from a goal and picked again in any project. **Builds:** Claude · **Review:** full · P1.

**Built after spec 42** (all its parts merged; read its §13 "As built" first: this spec uses what 42 made — the flag's
tally and Flags (42 B), an agent's record (42 D), `board_recap` and `board_week` (42 A, F, G), the phone's cache at v44).
**What it is, and is not:** part A changes the engine (how a check task ends); B to E only read, but D's proposal, which
the person takes or keeps with their own press; F keeps the person's own parties in their folder and, when one is
picked, installs the agents of theirs it brings. Nothing in what a person reads says card, deck, mana, rarity or level
(CLAUDE.md: everything by what it does); no agent is unlocked, no tier is raised by use, no party is ranked against
another's.

Six parts, one branch each, **in this order, each from `main` once the one before is merged** (CLAUDE.md "Alpha", as
spec 42: the critical tests, the part's files' tests, `tests/test_gui_wording.py`, `tests/test_design_system.py`,
`tests/test_pwa.py` and its browser tests). **This file is the contract**; the rest is the builder's choice inside its
files. **Change nothing outside a part's files** but those §10 names.

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. A check says what it found** | `spec/43-findings` | §1 | `realm/idea_checks.py` (`TAGS`, `FINDINGS_FILE`, `parse_findings`, `status`), `core/idea_task.py` (the ask, the file read before the commit), `core/idea_runner.py` (how a check task ends), `core/idea_review.py` (*Leave them* with no commit, *Fix them*'s why), `gui/ideas_review.py` (`findings`, `check` on a result), `realm/event_log.py` (`check_done`; `task_state`'s `check`, `clean`), `realm/board_recap.py`, `realm/board_week.py` (a clean check is not a result), `realm/lexicon.py`, `js/shell/review.js`, `js/board/idea.js`, `js/shell/shell.css`, `pwa/shell-review.js`, `pwa/shell-preview.js`, `pwa/app.css`, `pwa/sw.js` (`orkcraft-app-v45`); `tests/test_idea_checks.py`, the runner's and Review's tests of today, `tests/test_board_recap.py`, `tests/test_board_week.py`, the Review browser tests of both faces, `tests/test_pwa.py` |
| **B. What the party did** | `spec/43-party-work` | §2 | new `realm/party_work.py`, new `gui/ideas_party.py` (a mixin, as `gui/ideas_recap.py`), `gui/ideas.py`, `realm/lexicon.py`, `js/shell/goalview.js`, `js/board/map.js` (the Flags row), `js/shell/shell.css`, `js/board/board.css`, `pwa/shell-goal.js`, `pwa/shell-map.js`, `pwa/app.css`, `pwa/sw.js` (v46); new `tests/test_party_work.py`, new `tests/test_gui_party.py`, the goal screen's browser tests of both faces, `tests/test_map_desktop_browser.py`, `tests/test_pwa_map39_browser.py`, `tests/test_pwa.py` |
| **C. A party's price** | `spec/43-party-price` | §3 | new `realm/party_price.py`, `gui/ideas_party.py` (`ideas.party_price`), `js/shell/party.js`, `js/shell/goalwizard.js`, `js/shell/goaldialog.js`, `js/shell/shell.css`, `pwa/shell-goal-new.js`, `pwa/shell-goal.js`, `pwa/app.css`, `pwa/sw.js` (v47); new `tests/test_party_price.py`, `tests/test_gui_party.py`, the party picker's browser tests of both faces (desktop New goal and Edit goal; `tests/test_pwa_goal_team_browser.py`), `tests/test_pwa.py` |
| **D. What a check is worth** | `spec/43-check-worth` | §4 | `realm/party_work.py` (`check_record`, `quiet_run`), new `realm/party_proposals.py`, `core/idea_night.py` (a step), `gui/ideas_party.py` (`ideas.party_answer`), `gui/ideas_board.py` or `gui/ideas_goals.py` (Needs you's `party` rows), `gui/ideas_roles.py` (`check_week`, `record.check`), `realm/event_log.py`, `realm/lexicon.py`, `js/board/today.js`, `js/shell/agents.js`, `js/shell/agentdialog.js`, `pwa/shell-needs.js`, `pwa/shell-agents.js`, `pwa/shell-agent.js`, `pwa/app.css`, `pwa/sw.js` (v48); `tests/test_party_work.py`, new `tests/test_party_proposals.py`, the night's tests of today, `tests/test_gui_party.py`, the Needs you and Agents browser tests of both faces, `tests/test_pwa.py` |
| **E. Hints while picking** | `spec/43-hints` | §5 | `realm/library.py` (`Check.fits`), new `realm/party_hints.py`, `gui/ideas_party.py` (`hints` in `ideas.party_price`), `js/shell/party.js`, `pwa/shell-goal-new.js`, `pwa/sw.js` (v49); new `tests/test_party_hints.py`, C's browser tests, `tests/test_pwa.py` |
| **F. Your parties** | `spec/43-own-parties` | §6 | new `realm/own_parties.py`, `realm/goal_team.py` (`party` on the goal's page), `realm/roles.py` (only if installing an own agent needs a sibling of `install`), `core/idea_lead.py` (a use marked met), `gui/ideas_party.py` (`ideas.parties`, `ideas.party_save`, `ideas.party_drop`), `gui/ideas_goals.py` (`ideas.goal_save`'s `party`), `realm/event_log.py`, `realm/lexicon.py`, `js/shell/party.js`, `js/shell/goalview.js`, `js/shell/goalwizard.js`, `js/shell/goaldialog.js`, `js/shell/shell.css`, `pwa/shell-goal-new.js`, `pwa/shell-goal.js`, `pwa/app.css`, `pwa/sw.js` (v50); new `tests/test_own_parties.py`, `tests/test_gui_party.py`, `tests/test_gui_goals.py`, C's browser tests, `tests/test_pwa.py` |

Each part that changes a phone file moves `pwa/sw.js`'s `CACHE` up by one (the versions above) with `tests/test_pwa.py`'s
pinned version; a new `.js` the app serves goes into `SHELL`. Each part writes its "as built" notes into §11, as spec 42.

## 0. The words
New `TERMS` (`realm/lexicon.py`), each with its part:
- **a finding** (`finding`, *finding* / *findings*, A): one thing a check found: where, what goes wrong, and whether it
  fixed it. A check with no finding is **clean**; one with a finding **caught** something; a finding not fixed is
  **left**. (A goal's *verdict* stays the goal's: a check has findings, never a verdict.)
- **a check task** (no term: code only): a task whose `kind` is a checker's tag (`idea_checks.TAGS`: the first `takes`
  of every library agent with a `check`: today `security`, `review`, `a11y`, `datacheck`, `edit`).
- **What the party did** (`party_work`, B): a goal's party's work, member by member, check by check.
- **a party's price** (`party_price`, C): about what an idea costs with this party, before it starts.
- **a party's proposal** (`party_proposal`, D): the night's proposal to take a checker out of a goal's party.
- **your parties** (`own_party`, *your party* / *your parties*, F): parties the person saved from a goal, kept in their
  own folder and picked for a goal in any project.
- Today's words stay: *party*, *leader*, *builder*, *checker*, *check*, *team*, *merged the first time*, *result*.

## 1. A check says what it found (A)

### 1.1 The ask
- `core/idea_task.py`'s prompt for a check task ends with `FINDINGS_ASK`:
  > When you are done, write what you found to `.orkcraft-findings.json` at the worktree's root, as JSON:
  > `{"findings": [{"where": "file:line, or the screen", "what": "one line: what goes wrong", "fixed": true}]}`, the worst
  > first, at most 20. Write `{"findings": []}` when you found nothing that blocks, and then change nothing else. Fix
  > only what is small and certain; leave the rest as findings with `"fixed": false`.
- The FIX prompt (the gate's one retry) for a check task adds the same ask.
- `realm/library.py`'s checkers' instructions and `Check.task` stay as they are.

### 1.2 Reading it (`realm/idea_checks.py`, `core/idea_task.py`)
- `FINDINGS_FILE = ".orkcraft-findings.json"`. Before `commit_left`, the gate's check of a check task reads it (at most
  64 KB) and **removes it**, so it is never committed.
- `parse_findings(text) -> list[dict] | None`: strictly, `{"findings": [...]}` with at most 20 items, each `{"where"
  (at most 200 characters), "what" (at most 300), "fixed": bool}`; `None` for a missing file, bad JSON or a bad shape.
- The task keeps `findings` (the list) in `plan.json`, replaced each round.

### 1.3 How a check task ends (`core/idea_runner.py`)
After its session (and its gate, when it changed files):
| what it left | what it found | the task |
|---|---|---|
| no change | `[]` | `merged`, `commit: ""`, `note: "clean"`; no gate run, no Review, nothing lands |
| no change | findings, none fixed | `review` (whatever `ideas.review` says), `note: "<n> left"` |
| changes | all `fixed` | today's path: the gate, then Review or landing |
| changes | some left | `review` (whatever `ideas.review` says) after a green gate; a red gate as today |
| anything | `None` | today's path (the FIX prompt asks for the file again); still nothing: `failed`, error *the check said nothing: no findings file* |

- `task_state` events of a check task carry `check: true`, and `clean: true` on the `merged` of a clean one.
- `check_done` (new event): `{idea, task, by (the checker's slug), found, fixed, left, round, cost}`, when a round of a
  check task ends with findings read.

### 1.4 Review
- A check's result in Review (`ideas.review_list`): its row gains `check` (the checker's name) and `findings`.
- **The card** (desktop `js/shell/review.js`, phone `pwa/shell-review.js`): under its title, *Found 3: 1 fixed, 2 left*
  and the findings left, each *where · what* (the text face: they are the checker's words); then:
  - **Fix them**: today's send back with its why filled: *Fix the findings left:* and one line each (*where: what*);
    the check runs again in round 2.
  - **Leave them**: today's merge; with no commit the task becomes `merged` with `note: "<n> left"` and nothing lands.
  - **Drop**: as today. A check result with no finding left has today's card.
- `realm/board_recap.py` and `realm/board_week.py` (spec 42): a `merged` event with `clean: true` is not a result (*in
  dev*), nor counted in `merged` or `first_time`.

### 1.5 The idea's checks
`idea_checks.status` gains `found`, `fixed`, `left` per check (from its task's `findings`; `null` before it ends). The
idea's Checks (desktop `js/board/idea.js`, phone `pwa/shell-preview.js`) say *clean*, or *found 2: 1 fixed, 1 left*.

## 2. What the party did (B)

### 2.1 The data: `realm/party_work.py`
No face, no model, writes nothing. `work(root, state_dir, goal) -> dict`, over the goal's ideas' plans:
```json
{"ideas": 9,
 "leader": {"slug", "name", "head", "usd": 4.1 | null},
 "members": [{"slug", "name", "head", "tasks": 14, "merged": 13, "first_time": 12, "usd": 9.2 | null}],
 "checks": [{"by", "name", "head", "applied": 6, "skipped": 1, "clean": 4, "caught": 2, "left": 1, "before": 0,
             "usd": 1.8 | null}]}
```
- `ideas`: the goal's ideas with a plan.
- `leader`: the goal's leader (`goal_team.leader_of`); `usd` the goal's `goal`, `spec` and `plan` stages
  (`idea_spend.of_goal`).
- `members`: every role that ran a task that is not a check task in those plans, the goal's builders first in the
  party's order, then the others (a task taken by the project's role for its type); `tasks` merged or failed, `merged`,
  `first_time` (`round` ≤ 1), `usd` their tasks' lines (`idea_spend.of_idea`'s `tasks`).
- `checks`: every checker of the goal's party, then any other whose check task ran: `applied` the ideas whose kept
  checks say it applies and it was not skipped; `skipped`; `clean` its check tasks that ended clean in round 1;
  `caught` those with a finding or sent back (`round` > 1); `left` the findings left over all; `before` its check tasks
  that ended without findings (before part A); `usd` its check tasks' lines.

### 2.2 The command
| command | args | returns |
|---|---|---|
| `ideas.party` | `{"goal"}` | §2.1's object |

### 2.3 Shown
- **The goal's screen** (desktop `js/shell/goalview.js`, under its Team; phone `pwa/shell-goal.js`, under `teamSec`): a
  fold **What the party did**, closed at first, read when opened. Its lines, the text face:
  - *Product manager (leads): ≈$4.10 for the goal, the drafts and the plans*;
  - *Grunt: 14 tasks, 12 merged the first time · ≈$9.20*;
  - *Accessibility reviewer: checked 6 ideas: 4 clean, caught 2 (1 left) · ≈$1.80* (*· skipped 1* when it was;
    *· 2 ended without findings* when `before` > 0);
  - *No work yet* while `ideas` is 0.
- **Flags** (spec 42 B): a met goal's row gains the same fold.
- Logged when opened: `opened` `{what: "party", ref: "<goal slug>"}` (`OPENED` gains `party`).

## 3. A party's price (C)

### 3.1 The data: `realm/party_price.py`
No face, no model, writes nothing. `price(root, state_dir, settings, leader, team, every) -> dict`:
```json
{"low": 1.9, "high": 5.7, "learned": true, "ideas": 12,
 "checks": [{"by", "name", "usd": 0.35, "share": 0.5, "every": false}]}
```
- **The basis**: the project's newest 20 ideas with a plan (by `plan.json`'s time); `learned` when there are at least
  `idea_spend.TOO_FEW` of them with priced lines; `ideas` how many.
- **The leader's steps**: learned, the mean of their `spec` and `plan` stages' $; else `plans.DEFAULT_COST` at the
  leader's tier (`roles.head_tier` under the Target) × 2.
- **The work**: the mean number of tasks that are not check tasks per idea (learned; else 3) × the mean cost of a task
  of the party's builders (each as `gui/ideas_roles.py` `_usd_task` says it; no builder: the Grunt's).
- **Each check**: `usd` its checker's cost of a task as above; `share` 1 with `every`, else learned, the share of the
  basis' ideas drafted with it in their goal's party where it applied and was not skipped (at least `TOO_FEW` such
  ideas), else 0.5.
- `low` and `high`: (steps + work + Σ usd × share) × 0.5 and × 1.5, as `idea_keeper.estimate` spreads a plan's.

### 3.2 The command
| command | args | returns |
|---|---|---|
| `ideas.party_price` | `{"leader", "team", "every"}` | §3.1's object, and (E) `hints` |

### 3.3 Shown
- Where a party is picked: the desktop's New goal (`goalwizard.js`) and Edit goal (`goaldialog.js`, *Change the
  party*), through `party.js`; the phone's New goal and a goal's Team (`pwa/shell-goal-new.js` `makeParty`). The faces
  ask `ideas.party_price` when the picker opens and 300 ms after a seat or *Every idea* changes.
- Under the bands, one line: *This party: about $2–6 an idea* (below $1: *about $0.40–1.20*), and muted after it
  *from this project's last 12 ideas*, or *a first guess: it learns from this project's ideas*.
- In the checks (desktop `ChecksBlock`, phone `drawChecks`), each check's line ends *adds about $0.35 to an idea it
  checks · about half of them* (*· every idea* with `every`); today's tier-cost sum (*≈ $X an idea they all apply to*)
  goes.
- The phone's band row gains the desktop's *checks* mark for a checker.

## 4. What a check is worth (D)

### 4.1 A check's record (`realm/party_work.py`)
- `check_record(root, state_dir, by, days) -> {"checks", "clean", "caught", "left", "usd_per_check"}`: the checker's
  check tasks that ended with findings in the last `days`, across the project's goals; `usd_per_check` from
  `TOO_FEW` checks, else `null`.
- `ideas.roles` and `ideas.agents`: a checker's role gains `check_week` (7 days); its `record` (spec 42 D) gains `check`
  (30 days).
- **Shown**: on the agent's muted line under its one line (the week the owner put back, `8369511`), a checker's ends
  *· its check: 6 ideas, caught 2* (from 1 check); in its dialog and sheet (spec 42 D's record), a line *Its check, the
  last 30 days: 14 ideas: 11 clean, caught 3 · ≈$0.35 a check* (*too few to say more* under `TOO_FEW`).

### 4.2 The night's proposal (`core/idea_night.py`, `realm/party_proposals.py`)
- **When**: a step of the night after its ideas' proposals; code decides, no model is called; not limited by the
  Target's proposals (it spares money) nor counted among the ideas' three waiting.
- **Which**: for each goal with a party and no met verdict, each checker of its party whose newest `QUIET_RUN = 8`
  check tasks in this goal's ideas all ended clean in round 1 (`party_work.quiet_run`), when the goal has no party's
  proposal waiting and the pair (goal, checker) has no decline after the newest of those eight.
- **Kept**: `<state_dir>/goals/<slug>/party-proposal.json` `{"by", "runs": 8, "usd": <usd_per_check>, "at"}` (one per
  goal); a decline in `<state_dir>/goals/<slug>/party-declined.jsonl` `{"by", "at", "reason"}`.
- **In Needs you**: a row `{"kind": "party", "goal", "by", "title": "Take Reviewer out of Billing's party?", "text": "It
  found nothing in the last 8 ideas; a check costs about $0.35.", "priority": <the goal's>, "blocks": false, "at"}`,
  sorted last with the proposals and, as they are, never counted in the signal (spec 41 §1).
- **Answered** (`ideas.party_answer {goal, take, reason?}`): take → the party without that checker (`goal_team.set_team`,
  `every` without it too; the goal is not read again), the file removed; keep → a decline row, the file removed.
  Desktop `js/board/today.js` and phone `pwa/shell-needs.js`: the row as a proposal's, its buttons **Take it out** and
  **Keep it** (with *Why not? (optional, one line)* as a proposal's No).
- **Logged**: `party_proposed {goal, by, runs}` (the night), `party_answered {goal, by, take, has_reason}`.

## 5. Hints while picking (E)
- `realm/library.py`: `Check` gains `fits` (the goal crafts its check usually applies to): `security-reviewer`
  engineering, product, data; `reviewer` engineering, product, data; `accessibility-reviewer` design, product,
  engineering; `data-reviewer` data, engineering, product; `editor` marketing, product, design.
- `realm/party_hints.py` `hints(root, state_dir, craft, leader, team, every) -> [str]`, at most two, in this order:
  1. a checker of the party whose `check_record` (30 days) has 8 checks or more and none caught: *Reviewer found
     nothing in its last 12 checks.*
  2. a checker whose `fits` leaves out the goal's craft: *Accessibility reviewer seldom checks a Data goal: it checks
     when the idea changes what people see or use.*
  3. an engineering or product goal whose party has no member that takes `code`: *No one in the party writes code: code
     tasks go to this project's agent for code (the Grunt when none).*
  4. a party with a leader other than the Taskmaster and no builder: *No builders: each task goes to this project's
     agent for its type (the Grunt when none).*
- `ideas.party_price` takes `craft` too and answers `hints`; the faces show them under the price line, muted, one line
  each. A hint never blocks Save and has no button.

## 6. Your parties (F)

### 6.1 Kept: `realm/own_parties.py`
The person's, one for every project, as Operations are (decisions §51.1): `parties.json` beside the machine's settings
(`~/.config/orkcraft/parties.json`), written whole and atomically, 0600 as `realm/op_runs.py` writes; never in a
repository. No face, no model.
```json
{"v": 1, "parties": [{"id": "p-1a2b3c4d", "name": "Lean web", "craft": "engineering",
  "leader": "architect", "team": ["grunt", "tester", "reviewer"], "every": ["reviewer"],
  "own": [{"slug": "docs-scribe", "name": "Docs scribe", "craft": "design", "model": "", "max_parallel": 2,
           "instruction": "…", "takes": ["docs"]}],
  "saved": "<iso>",
  "uses": [{"project": "<12 hex: sha1 of the project's path>", "name": "<the project folder's name>", "goal": "<slug>",
            "at": "<iso>", "met": null}]}]}
```
- `own`: every member (the leader too) that is neither a library agent nor built in, as its role file says it at the
  save (`roles.role`: name, craft, model, max_parallel, instruction, takes); the Taskmaster and the Grunt are never
  carried.
- At most `MAX = 12` parties; a name of 1 to 40 characters, unique whatever its case; at most 50 `uses` a party, the
  oldest dropped.
- `list()`, `save(name, craft, leader, team, every, own, replace=False)`, `drop(id)`, `used(id, project, name, goal)`,
  `mark(project, goal, met)`. A file of another shape reads as none and is not overwritten until a save.

### 6.2 Commands
| command | args | returns |
|---|---|---|
| `ideas.parties` | `{}` | `{"parties": [{"id", "name", "craft", "leader", "team", "every", "own": ["<names>"], "goals", "projects", "met", "saved"}]}` |
| `ideas.party_save` | `{"goal", "name", "replace"?}` | `{"id"}`: the goal's party as it is now; a taken name is refused (*You have a party named “Lean web”*) unless `replace` is true; a thirteenth is refused (*You have 12 parties: remove one first*) |
| `ideas.party_drop` | `{"id"}` | `{"ok": true}` |
| `ideas.goal_save` | gains `{"party"?: "<id>"}` | as today |

- `goals`: its uses; `projects`: the distinct projects among them; `met`: the uses whose goal was accepted as met.
- **Using one** (`ideas.goal_save` with `party`): the face sends the party's `leader`, `team` and `every`, as it filled
  them, and its `id`. The host installs the library agents as today and each `own` agent the project has not (a role
  file written as `roles.install` writes one, never over a role of that slug: the project's own stays, and the answer
  says *Docs scribe is this project's already: kept as it is*), checks the seats, saves the party, records the use and
  keeps `party: <id>` on the goal's page (`goal_team.set_team`'s `party`).
- **A goal's party changed afterwards** (a `goal_save` with `team`, `leader` or `every` and no `party`) clears the
  goal's `party`; a goal never changes a saved party.
- **Met**: when a goal's leader accepts it (`core/idea_lead.py`, after `goal_verdict.save`) and the goal has a `party`,
  `mark` sets that use's `met` (asked again, the last verdict).
- **Logged**: `party_saved {party, members, own, replaced, device}`, `party_dropped {party, device}`; `goal_saved` gains
  `party` (the id; `""` without one).

### 6.3 Shown
- **Save**: on the goal's screen, under its Team (desktop `goalview.js`, phone `pwa/shell-goal.js` `teamSec`), a quiet
  button **Save this party**. It asks a name (filled with *<Craft> party*, *Engineering party*) and saves; a taken name
  asks *Replace your party “Lean web”?* first. Said after: *Saved: pick it for a goal in any project.*
- **Pick**: where a party is picked (desktop `party.js`'s bands, in New goal and Change the party; phone `makeParty`),
  a row **Your parties** above the bands when there is one: each a chip with its members' small heads, its name and,
  muted, *3 goals in 2 projects · 2 met* (only once used). A tap fills the leader, the builders, the checkers and Every
  idea, sets the craft in New goal, and keeps its id for the save; a seat changed afterwards drops the id (the party is
  then the person's own picking). C's price and E's hints follow the seats as for any party.
- **Remove**: each chip's `close` mark (`aria-label` *Remove your party “Lean web”*), after *Remove your party “Lean
  web”? Goals that use it keep their agents.*
- Nowhere else: no list of parties of its own, nothing on the Map, no rank.

## 7. Tests
- **A**: `parse_findings` (the shape, 20 at most, the lengths, bad JSON and a bad shape give `None`); the prompt of a
  check task ends with the ask, another task's does not; with a fake session: clean and no change → `merged` with no
  commit, no gate run and no Review, the file never committed; findings left and no change → `review` with
  `ideas.review` off; all fixed with changes → today's path; changes with some left → `review` after a green gate; no
  file twice → `failed` with its words; `task_state`'s `check` and `clean`, `check_done`; *Fix them* sends back with the
  findings as its why and runs round 2; *Leave them* with no commit merges nothing and keeps the note; `board_recap`
  and `board_week` leave a clean check out of the results; `status`'s `found`, `fixed`, `left`. Browser (both faces):
  a check's card with *Found 3: 1 fixed, 2 left*, its lines, *Fix them* and *Leave them*; the idea's Checks say *clean*
  and *found 2: 1 fixed, 1 left*.
- **B**: `party_work.work` on a fixture goal (members in the party's order then the others, a check's `applied`,
  `skipped`, `clean`, `caught` by a finding and by a send back, `left`, `before`, `usd` `null` when unpriced, the
  leader's stages); `ideas.party`; browser: the fold on the goal's screen of both faces, closed at first, its lines when
  opened, *No work yet*; a met goal's row in Flags with the fold.
- **C**: `party_price.price`: a first guess with no basis (the defaults at the tiers the Target gives), learned from
  `TOO_FEW` priced ideas, `every` gives a share of 1, a check's learned share, a party with no builder takes the
  Grunt's cost, `low` and `high`; `ideas.party_price`; browser: the price line when the picker opens and after a seat
  changes (one call per 300 ms of changes), *a first guess* and *from this project's last N ideas*, each check's
  *adds about … · about half of them*, the phone's *checks* mark.
- **D**: `check_record` (30 and 7 days, `usd_per_check` under `TOO_FEW` is `null`); `quiet_run` and the night's step
  (eight clean in round 1 proposes; a catch, a send back or seven do not; a met goal does not; one waiting per goal; a
  decline holds until a newer run of eight); `ideas.party_answer` take and keep (the party saved without the checker
  and its `every`, no reading of the goal, the decline row, the events); Needs you's `party` row sorted last and not
  counted; browser: the row's *Take it out* and *Keep it* on both faces, the muted line's *its check*, the dialog's and
  the sheet's *Its check* line.
- **E**: `hints` (each of the four, their order, at most two, none for a party that fits); `ideas.party_price`'s
  `hints`; browser: the hints under the price line, muted, and Save still enabled.
- **F**: `own_parties` (save, the twelve, a taken name refused and replaced, drop, `uses` at most 50, a broken file
  read as none and kept, 0600); `ideas.party_save` from a goal with an agent of the person's own carries it;
  `ideas.goal_save` with `party` in another project (a second fixture repository) installs that agent, keeps a role of
  the same slug as it is and says so, records the use and keeps `party` on the page; a later party change clears it;
  accepting the goal marks `met`; `ideas.parties`' counts; the events. Browser: Save this party on both faces' goal
  screens (the name, the replace); Your parties' chips fill the seats and the craft in New goal; a seat changed drops
  the id (the save sends no `party`); Remove asks first.
- Every part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_pwa.py`.

## 8. Measured
- `opened` gains `what` `party` (B).
- New events: `check_done` (A), `party_proposed`, `party_answered` (D), `party_saved`, `party_dropped` (F); `task_state` gains `check`, `clean` (A).
- The owner reads after a week: how many checks ended clean, caught or said nothing (the failures part A ends); how
  often *Fix them* and *Leave them* are pressed; how often a party is changed from the craft's own (`goal_saved`'s
  `team` against `library.PARTIES`) with and without a price shown; party proposals taken and kept; how often a saved party is picked against a craft's own, and in how many projects.

## 9. Not in this spec
- An agent's instruction that learns from send-backs (decisions §48.5's other proposals); a library of the person's
  own agents across projects beyond what a saved party carries; parties shared with a team; a saved party's first-time
  share or $ across projects (its record is its goals, projects and flags). After the testers' numbers.
- A party's record across goals, a rank of parties, a score; any word of a card game.
- A check's findings in the recap or Last week (spec 42 stays as built, but a clean check is not a result, §1.4).
- A checker's craft limiting where it may sit (`fits` only hints).

## 10. Files a part may need beyond its row
`core/idea_keeper.py` (A: only if a check task's prompt is built there and not in `core/idea_task.py`),
`gui/ideas.py` (A, D: a command's arguments), `js/shell/store.js` and `pwa/board.js` (B, C: a fold or a call),
`tests/test_shell_browser.py`'s `StubHost` and `tests/test_pwa_shell_browser.py`'s `Stub` (the new commands). Anything
else: stop and write it in §11 first.

## 11. As built (notes, no change of the contract)

### A. A check says what it found
- The term is `check_finding` in `TERMS` (*finding* / *findings*): the key `finding` is the Mine's (Orkline's research, *Finding*), so the spec's `finding` is taken by it. The phone's cache is `orkcraft-app-v46` (the numbers of the table moved up by one, as the task said).
- `idea_checks` also has `counts(findings) -> {found, fixed, left}`, `is_checker(slug)` and `checker_of_tag(tag)`. `FINDINGS_ASK` is in `core/idea_task.py` (it is the prompt's), with `is_check(task)`, the findings round (`_findings_round`: the file read and removed, what the session left committed) and the words of a check that said nothing; the end of a check task is in `IdeaRunner._work` and the *Leave them* of a result with no commit in `ReviewMixin._leave`.
- A check that changed no file claims no fix: its findings are all kept as `fixed: false` (`found` and `left` are then equal). A check that changed files and said no findings (no file) goes the way of today; one that changed no file and said nothing fails after the retry with *the check said nothing: no findings file*, whatever `ideas.review` says.
- The retry (FIX) and a send back of a check task carry the ask again; a send back also lists the findings left of the round before, in full (the face's own *why*, which a send back keeps to 1,000 characters, names as many as fit and then *and N more*). The task's `findings` are cleared when a round begins and set when it ends.
- A clean check's task has `tests` with `ran: false` and a zero `diff`, and `note: "clean"`; a result of a check that changed no file reaches Review with the same and `note: "<n> left"`. *Leave them* with a diff of no file merges nothing (`ReviewMixin._leave`); with fixes it is today's merge.
- `ideas.review_list`'s rows gain `check` and `findings` only for a check task. A result with every finding fixed has today's card (no *Found*, *Merge into dev*, *Send back*); one with findings left has *Fix them*, *Leave them* and *Drop…*. *Fix them* sends the back at once (one press) with the why *Fix the findings left:* and a line each. The result's own screen on both faces shows the same lines.
- Not in the contract and left as it was: the goal's tally (`goal_flags`), the agents' record (`idea_spend.by_role`) and the roles' day count read the plan's tasks, so a clean check still counts as a merged task there; only the recap and the weeks leave it out (§1.4).
- `check_done` is written once per round of a check task that ends with a findings file read; `by` is the task's role when it is a library checker, else the library's checker of the task's tag.

### B. What the party did
- `party_work.work(root, state_dir, goal, target="balance")`: `root` is the Board's tree (where the goal's and the ideas' pages are, as `goal_team` and `goal_flags.tally` take it); `target` is the Board's Target, for the heads' gear (`ideas.party` passes it). The leader's `usd` is `null` while no call of the goal's `goal`, `spec` or `plan` stages was made. A `usd` is the priced lines' sum in cents, `null` when none was priced (a member's from its tasks' lines in the ideas' ledgers).
- A member is a role with a task that ended (`merged` or `failed`) which is not a check task; the party's builders come first in its order, then the others in the order the plans name them (the leader too, when it ran a task). A checker's tasks count once they said what they found (`merged`, or waiting at Review); a task sent back (round 2 and on) is a catch whatever its findings, a task at round 1 with `[]` is clean, one with no findings kept (before part A, or ended without a findings file) is counted in `before` only, said on both faces as *· N ended without findings*.
- The fold is in `js/shell/goalview.js` (`PartyWork`, `partyLines`; `map.js` imports it for the Flags row) and `pwa/shell-goal.js` (`partyFold`, `partyLines`; `shell-map.js` imports it). A member with no merge the first time says *none merged the first time*; a lead or a check with no price leaves the $ out. Each time the fold is opened it asks again and logs `opened` `party`.
- The phone's cache is `orkcraft-app-v47`.

### C. A party's price
- `party_price.price(root, state_dir, settings, leader, team, every)`: `root` is the Board's tree, `settings` the Board's (`ideas.party_price` passes `board_settings()`). The basis's time is the plan's `made_at` (the file's time when it has none); a priced idea is one with a priced line in its ledger; the leader's learned steps are the mean of their `spec` and `plan` stages over the priced ideas that have them. A check's learned share reads the ideas' kept `checks` (an idea whose draft said nothing of a checker does not count for it).
- A task of an agent is as `ideas.roles`' `usd_task` says it (`party_price.task_usd`, a copy of it in the realm, since the realm does not import `gui/`), with one difference: an agent's week counts only when it has a priced spend (a week of tasks that ended with no priced line is not $0.00 a task; it falls to the tier's cost).
- `ideas.party_price` takes the Taskmaster as the leader when none is sent, refuses an agent that is not the library's and a party that does not fit its seats (the same words as `ideas.goal_save`), and ignores an `every` that is not in the team. It saves nothing.
- Desktop: `usePartyPrice` (in `party.js`) asks when the picker opens (New goal's step 2, Edit goal's *Change the party*) and 300 ms after a seat or *Every idea* changes; the line is under the bands, each check's line in the Checks says what it adds. Phone: `makeParty` asks when it is set for a goal (the sheet opens), after a craft's preset and 300 ms after a seat or *Every idea*; its price line is under the team's line (and under the bands when they are open). Below $1 (the range's low end) the price is in cents (*about $0.40–1.20*); a range that rounds to one dollar is said once (*about $2*).
- The phone's band row already had the checkers' *checks* mark in its chips elsewhere; the seat rows gain it (`.check-badge`). The old line *≈ $X an idea they all apply to* is gone on both faces; `tests/test_pwa_goal_team_browser.py` says so (it asserts it is not there).
- The phone's cache is `orkcraft-app-v48`.

### D. What a check is worth
- `party_work.check_record(root, state_dir, by, days, now=None)` counts the checker's check tasks that have said what they found (`merged`, or waiting at Review, with a findings list) and finished in the last `days`; a task sent back (round 2 on) is a catch whatever its findings, a task at round 1 with `[]` is clean. It reads the plans once for every checker and keeps the answer for 30 s (`party_work.forget()` clears it; `now` given skips the cache). `usd_per_check` is the checks' priced lines over their number, from `TOO_FEW` checks.
- `party_work.quiet_run(root, state_dir, goal, by)` answers the time the newest of the eight finished (a string) when the newest `QUIET_RUN = 8` check tasks of that checker in the goal's ideas all ended clean in round 1, else `None`; a failed check, a send back or a finding ends the run. The decline holds while its time is after the *oldest* of the eight (`quiet_run(..., oldest=True)`, which `propose` uses): it holds until eight new clean checks come after it, so one more clean check does not bring the same proposal back.
- The night's step is `IdeaKeeper._night_parties` (the fifth step of `run_night`), `party_proposals.propose(root, state_dir)`: for each goal but General, with no met verdict and no proposal waiting, the first checker of its party that is quiet and has no decline after its newest eight. It writes `party-proposal.json`, logs `party_proposed` and publishes the goal; the night's counts (`night_run`) do not change.
- Needs you's row comes from `goal_needs` (`gui/ideas_goals.py`) through `party_proposals.rows`; it is sorted with the proposals, last, and `ideas.snapshot`'s `needs_you`, the desktop's counts, the phone's `needs.count()` leave it out. The row has `idea: ""`, `goal`, `by`; its title uses the goal's title (*Take Reviewer out of Billing's party?*) and its text leaves the price out while it is unknown. A row of a checker who has left the party since is not shown.
- `ideas.party_answer {goal, take, reason?}` answers (`take` is a boolean): take is `goal_team.set_team` without the checker and without it in `every`, the goal is not read again; keep is a row in `party-declined.jsonl` (`reason` cut to 300 characters). `party_answered` also carries the device.
- `ideas.roles` and `ideas.agents` gave a checker `check_week`; `record.check` (30 days) is in `ideas.roles` (a checker with no task has a record of its check alone). The check's line in the dialog and the sheet has `aria-label="Its check"` (not "…the last 30 days", which `get_by_label("The last 30 days")` of spec 42's tests would also match).
- `tests/test_gui_recap.py` used `party` as an example of a word `opened` refuses; it is `OPENED`'s since part B, so the example is `nothing` now (the refusal is as tested before).
- The phone's cache is `orkcraft-app-v49`.

### E. Hints while picking
- `Check.fits` is a tuple on the library's checks; `party_hints.hints(root, state_dir, craft, leader, team, every)` (`every` is not used by any of the four) answers at most two, in the spec's order. A checker's hint 1 counts its checks of the last 30 days (`check_record`, so the same 30 s cache), hint 2 is for a goal with a craft (a Mixed goal sends none, and gets no craft hint), hint 3 counts the party's builders and checkers and its leader when that is not the Taskmaster (a library agent by its `takes`, an own agent by its role's), hint 4 is any leader but the Taskmaster with no builder.
- `ideas.party_price` takes `craft` (anything but a craft is none) and answers `hints`; the faces send the goal's craft (New goal: the picked one, nothing for Mixed; Edit goal and a goal's Team: the goal's), ask again when it changes, and show the hints as muted lines under the price line.
- `tests/test_party_price.py` says the answer's keys now include `hints`; C's browser tests say the asked arguments include `craft`.
- The phone's cache is `orkcraft-app-v50`.

### F. Your parties
- `own_parties.list()` shadows the builtin in its module (the spec's name); the module uses `builtins.list` where it needs the type. `save` writes the party's `craft` as the goal's, and a replace keeps the party's id and its `uses`. A project is `own_parties.project_key(path)` (12 hex of the sha1 of the path, as the tabs' keys are) and its name the folder's.
- `roles.install_own(state_dir, own)` is the sibling of `install`: an agent of the person's own that a party carries, written once with its slug, its model kept only when it is a tier (else By Target), never over a role of that slug. `goal_team.set_team` has a `party` argument and **clears the goal's `party` whenever it is called without one** (so a party changed by hand, or by a proposal that takes a checker out, is no longer a saved party's); `goal_team.party_of(root, goal)` reads it; the goal's row (`ideas.goal`, `ideas.board`'s tracks) carries `party`.
- `ideas.goal_save` with `party` and neither `team` nor `leader` takes the party as it was saved; `party` is refused if it is gone (*That party is gone*). Its answer carries `notes` (a list) when an own agent was the project's already: *Docs scribe is this project's already: kept as it is*; both faces say each note as a toast.
- `core/idea_lead.py` marks a use `met` after the leader accepts a goal that has a `party`; the use is found by the project's key and the goal's slug.
- Desktop: `OwnParties`, `SaveParty`, `useOwnParties` in `party.js` (the save is inline in the goal's Team, not a dialog); New goal sets the craft to the party's; Edit goal's *Change the party* sends `party` when one was picked and no seat changed since. Phone: `makeParty(core, {onCraft})` has the row and the removal, and `get()` gives `party`; a goal's own Team sheet keeps the goal's `party` as the id until a seat changes, so saving it unchanged keeps it. Save this party's typed name survives a redraw (`naming` in `shell-goal.js`). The phone's cache is `orkcraft-app-v51`.

### Fix-ups after review
- A proposal whose checker has left the party is removed (`party_proposals.drop_left`), by the night's `propose` and when a goal's party is saved (`ideas.goal_save`), so that goal can be proposed again.
- Saving a goal with the `party` it already has (the phone's Team sheet resends it) installs nothing, says no note and does not call `used()`; it is not refused when the saved party is gone. `own_parties.used` keeps `met` of the same (project, goal, party) use.
- `own_parties.mark(project, goal, met, party_id)`: the leader's acceptance marks only the use of the party the goal has now (`core/idea_lead.py` passes it).
- A decline holds until eight new clean checks come after it (§4.2 above: the oldest of the eight is compared, not the newest).
- A night where only a clean check merged (`task_state` `merged`, `clean: true`) is not worked (§1.4).
- A check task that changed files and wrote no findings file stays in `before`, and both faces say *· N ended without findings*. The phone's cache is `orkcraft-app-v53`.
