# Spec 35 — the Board: a goal from a description, an idea straight to its spec, the Target, autostart by risk, the night

The owner and the PM, 18 October (decisions §47). After 34 the Board asks too much and does too little by itself: a
goal needs a title, metrics and links typed in; an idea waits for a 30-minute batch, then for the person to talk it
through, then for **Take it to work**, then for the person to pass the plan; and the Board's models are fixed, whatever
the person wants to spend. This spec makes the person write only what only they know (a description and a
priority), lets the keeper write the rest, starts what is safe by itself, moves the low work to the night, and gives
the Board one **Target** (thrift · balance · quality) that picks every step's tier and reasoning. Build on `main` as
it is (33 and 34 merged). **Builds:** Claude (A on the elder tier; B and C on the warrior tier) · **Review:** full · P0.

Three parts, one branch each, in this order; **this file is the contract** (names, data, commands); the rest is the
builder's choice inside its files. Wording: CLAUDE.md (orks by orkish names: the Taskmaster is the keeper; today's
words: *goal*, *idea*, *Target*, *to-do*, *task*). **Change nothing outside these files.**

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. Backend** | `spec/35-backend` | §0–§10, §12 | new `realm/idea_target.py`, new `realm/idea_risk.py`, `realm/ideas.py`, `realm/idea_secrets.py` (the files beside the secrets), `realm/harnesses.py` and `realm/jobs.py` (effort, the budget cap, no session persistence), `core/idea_keeper.py`, `core/idea_goals.py`, new `core/idea_draft.py` (the draft, a mixin like `idea_goals.py`), new `core/idea_night.py`, `core/idea_runner.py`, `gui/ideas.py`, `gui/ideas_goals.py`, new `gui/ideas_board.py` (`board()` and Needs you move here: `gui/ideas.py` is at 571 lines), `gui/mobile.py` (allowlist), `realm/event_log.py`, `realm/lexicon.py`, `settings.py` |
| **B. Desktop** | `spec/35-desktop` | §11 on the desktop | `gui/static/js/shell/*`, `gui/static/js/board/*` |
| **C. Phone** | `spec/35-phone` | §11 on the phone | `gui/static/pwa/shell-*.js`, `pwa/app.css`, `pwa/sw.js` (cache version) |

B and C branch from A once A is pushed (as in 33 and 34); they touch no file of each other's and can be built at once.

## 0. The rule above all: one call, one job; no session, no long talk
The owner's pain (18 October): long talks on ideas eat the context and the money. A resumed session carries every
earlier turn and every file the model read into each new call. So, for every call of the keeper (`goal`, `draft`,
`answer`, `talk`, `plan`, `refresh`, `propose`):
- **One shot.** A fresh `claude -p`, never `--resume`, with `--no-session-persistence` when the installed CLI lists it
  (read once, as `--effort`). **The page is the memory**: its sections, its Decisions, its Open questions. The talk
  (`talk.jsonl`) is the person's archive and never goes to a model. The session per idea (decisions §43.5:
  `state.session`, `fresh`, the 60 % compaction) goes; `idle_hours` stays in the settings, unused.
- **Only what its job needs**, built by code and cut to a cap (`realm/idea_target.py` `CONTEXT`, characters of the
  prompt; the call's own instructions not counted):

| call | gets | cap |
|---|---|---|
| `goal` | its description, priority, links' paths, the person's answers (if any), the Wiki's index | 12 000 |
| `draft` | its goal's Summary and Metrics, the goal's links as paths (not their text), the titles of the goal's other ideas and of the other goals' open ideas (≤ 40), the person's text | 8 000 |
| `answer` | the spec's sections but Decisions and Stages, the questions with the person's answers | 8 000 |
| `talk` | the one section the person points at (Gist and Open questions when none), the last 10 lines of Decisions, the person's words | 6 000 |
| `plan` | Gist, Done when, Out, Risks, Depends on; the goal's Summary | 10 000 |
| `refresh` | as `goal`, and the names of the paths that changed | 12 000 |
| `propose` | each goal's title and the first line of its Summary, its ideas' titles and states, the declined titles, at most 50 commit subjects | 10 000 |

  The Wiki's index goes only to a goal's read: under a goal, its Summary is the map.
- **Bounded reading.** The prompt names the files to start from and how many it may read: `goal` 8, `draft` 6,
  `plan` 6, `refresh` 6 (the changed ones first), `talk` 2, `answer` 2, `propose` none (it runs with no tools). Every
  call runs with `--max-budget-usd` when the CLI lists it: `CAPS` per step in balance (goal 1.00 · draft 0.60 · answer
  0.40 · talk 0.20 · plan 0.60 · refresh 0.50 · propose 0.30), half in thrift, double in quality. A call that ends on
  its cap: its answer is used if it parses, else the idea stays as it was and says *the keeper ran out of its budget
  for this step*.
- **One round of questions.** The draft (and a goal's read) asks at most 3 questions, all at once. The person answers
  them together, one box each, one **Send** (`ideas.answer`). The `answer` call writes the rest of the spec and **asks
  nothing more**: where it is unsure it decides, and writes the assumption into Decisions (*Assumed: …*); a question in
  its answer is dropped by the code. A goal's answers the same way, on the `goal` step.
- **A talk turn is an edit, not a chat.** The person says what to change on a section, or asks about it; one call
  rewrites that section (and Decisions, if something was decided) and replies in at most three lines. No turn carries
  the turns before it.
- **Measured.** Every keeper event (`goal_read`, `idea_drafted`, `idea_answered`, `idea_said`, `plan_made`,
  `night_run`) carries `prompt_chars` and `tokens` (in, out, cache read), so the waybill shows what each step costs.

## 1. The Target: the Board's one setting
- `ideas.target`: `thrift` · `balance` · `quality` (default `balance`), shown as **Target** (`TERMS` `steward_goal`,
  spec 32). One per Board, and it is the target of the whole route board → pool → gate: in v1 neither Agents nor
  Review has its own (the direction of decisions §44.3).
- `realm/idea_target.py` `MATRIX`: each step of the Board → each target → `(tier, effort)`; `pick(step, target)`:

| step | thrift | balance | quality |
|---|---|---|---|
| `goal` (a goal read) | elder · medium | elder · high | elder · xhigh |
| `draft` (an idea → its spec, §3) | elder · low | elder · medium | elder · high |
| `talk` (an answer on the spec) | elder · low | elder · medium | elder · high |
| `plan` (the spec → its tasks, §4) | elder · low | elder · medium | elder · high |
| `refresh` (a goal read again at night, §7) | — (none) | elder · medium | elder · high |
| `propose` (the night's proposals, §8) | — (none) | elder · low | elder · medium |
| `task` (an ork's task) | its tier one lighter · low | its tier · medium | its tier one heavier · high |

- Why so: a goal is rare and everything below it reads it, so it is never cheap; the money goes on tasks (many, long),
  so the Target moves them most.
- *One lighter / heavier* is `realm/plans.py` `shift` (never past laborer or elder). A task's planned tier is its
  **complexity** and stays in plan.json (`tier`); the tier it runs on is worked out at launch and recorded on the task
  (`ran_tier`, `effort`). The plan's estimate (`estimate`, shown on Take it to work) counts the tiers they will run on.
- **The person's own pick wins.** A role with a model set (spec 34 §3) runs on it: the Taskmaster's model, when it is
  not its default `elder`, replaces the tier of every keeper step above; a role other than Grunt keeps its model for its
  tasks. The Target still gives the effort. Grunt (`""`) runs on the task's shifted tier.
- **Effort** reaches the model through `realm/jobs.py` → `realm/harnesses.py`'s claude commands as `--effort <level>`
  (the CLI's levels: low · medium · high · xhigh · max). It is passed only when the installed CLI lists `--effort` in
  its `--help` (read once, cached) and never on the laborer tier. Other harnesses ignore it (agy's reasoning is in its
  model's name). The keeper's `Call` gains `effort` and `budget`; it loses `resume` (§0).

## 2. A goal: a description and a priority; the keeper writes the rest
- **New goal**: **Description** (required, a few lines) and **Priority** (*High · Normal · Low*, default Normal).
  Nothing else. **Edit** on a goal: the same, and its **Title** (to correct the keeper's).
- Saving sends it to the keeper at once, as 34 does, on the `goal` step (§1). Besides today's Summary and questions it
  writes:
  - its **title** (≤ 60 characters), unless the person typed one: front matter `title_by: keeper | person`; a person's
    title is never rewritten;
  - **Summary**, now the goal's *context* for every idea under it, 5–12 lines: what the goal means for this repository,
    the modules and files it touches (as repository paths), what exists already, the constraints;
  - **Metrics**: 1–3 lines *done when …*, each measurable, with how it is counted, into today's `metrics` front
    matter (`{name, target, how}`), so the old readers stay;
  - **links**: at most 8 repository paths or Wiki pages it read and found relevant; the code keeps only paths that
    exist, never a URL; links a person gave before (34's goals) are kept;
  - 0–3 Open questions → `asks`, in Needs you, as today.
- The goal's state keeps `read_at`: the commit (`git rev-parse HEAD`) it was read at (§7's refresh).
- 34's deadline, metric targets and links stay in the data (old goals read as they are); the dialog no longer asks them.
  No goal-to-goal dependencies.
- **General** stays (decisions §43.1) for what the system files there itself: External listeners' cards, calendar
  meetings, Mission 1's drill. The person cannot choose it (§3); New goal never makes it.

## 3. An idea: a text, a goal and a priority; straight to its spec
- **New idea**: the **text** (required), the **goal** (required: the goal chosen in the Board's goal select, else the
  first by priority; General is not listed) and the **priority** (*High · Normal · Low*, default the goal's). One
  button: **Add**. Closing the dialog with text in it adds it to tonight's queue (never lost); closing it empty adds
  nothing. With no goal yet, New idea opens New goal first, then itself with that goal.
- `ideas.add` refuses a missing goal or General; `realm/ideas.py` `add_idea` still takes General for the system's own
  cards. The priority is the person's (front matter `priority`); the keeper no longer proposes one.
- **The queue** (`state.json` `queue`): High and Normal → `now` (drafted at once, in the background); Low → `night`
  (§7); `hold` when the person stopped it (§11). A `raw` idea from before this spec, with no queue, is `night`. The
  30-minute batch goes: `batch_minutes` stays in the settings, unused, so old settings keep loading.
- **The draft** (`core/idea_draft.py`): one call on the `draft` step, read-only, one shot, given §0's `draft` context
  (with *start from these files; search the repository only for what they don't cover*). It answers one JSON object:
  `{title, gist, why, done_when: [1–5], out: [0–3], risks: {product: [..], tech: [..]}, risk: low|medium|high,
  risk_why, touches: [repository paths or globs], depends_on: [idea slugs], size: S|M|L, before, questions: [0–3]}`.
- Written, strictly as today (only known keys): the sections **Gist · Why · Done when · Out · Risks · Depends on ·
  Open questions**; front matter `size, risk_model, touches, depends_on` and `title` (the person's words stay in the
  talk, as today). `depends_on` keeps only slugs that exist and do not close a cycle. `before` places it as 34 does
  (the person's drag wins).
- Then: questions → `asks` (Needs you); the person answers them together (`ideas.answer`), the `answer` call writes
  the rest (§0: one round), and the plan follows. No questions → **the plan at once** (§4). A plan not passed yet is
  made again by **Re-plan** (`ideas.plan`, as today).
- `realm/ideas.py` `SECTIONS` becomes **Gist · Why · Done when · Out · Risks · Depends on · Stages · Open questions ·
  Decisions**. *In* and *Estimate* are no longer written; a page that has them keeps them and shows them after the
  known sections (as `page()` does today with any other section). The price stays where it was used: on Take it to work
  and in the plan (`estimate`).

## 4. The plan, its Stages, its risk
- The plan as today (`plan_prompt`, `make_plan`), on the `plan` step, one shot with §0's `plan` context; each task's brief
  names the Done when lines it proves.
- **Stages** is written by the board from plan.json (code, no model) whenever a plan is made: the tasks in waves by
  `after`, e.g. `1. k1 The table (S) ∥ k2 The form (M)` · `2. k3 The checks (L), after k1`; the complexity from the
  planned tier: laborer **S** · warrior **M** · elder **L**. This is where the tasks are seen: nowhere else on the Board.
- **The risk** (`realm/idea_risk.py`, code, no model): `risk = max(risk_model, the triggers)`. The triggers read the
  idea's `touches` (as paths) and its spec and plan (titles, briefs, Out, Risks; as words, whole words, any case):

| trigger | at least | paths | words |
|---|---|---|---|
| secrets, sign-in, payments | medium | `auth`, `login`, `oauth` in a path | token, secret, password, credential, payment, billing, invoice, stripe, checkout |
| data: schema, migrations, deletion | medium | `migrations/`, `alembic/`, `*.sql`, `schema` | drop table, truncate, delete … data, wipe |
| CI and deploy | medium | `.github/workflows/`, `Dockerfile`, `docker-compose*`, `deploy`, `infra/`, `terraform/`, `k8s/`, `helm/` | deploy, release |
| a public API | medium | — | public API, breaking change |
| wide | medium | `touches` in more than 5 top-level folders | or more than 6 tasks |
| outward and irreversible | **high** | — | send an email, send a message, post to, publish, tweet, notify users, charge, refund, push to main, delete the branch |
| the repository's own | medium | `ideas.risk_paths` (globs; default none) | — |

- Front matter keeps `risk`, `risk_model` and `risk_triggers` (the names). The Risks section's first line says the
  risk and what raised it: *Risk: Medium — CI and deploy (`.github/workflows/`)*. A trigger matched by mistake only
  makes a plan wait for the person: that is the safe side.

## 5. Autostart: who passes the plan
- `ideas.autostart`, default **on** (the Board's gear: *Start plans by themselves*). Off: every plan waits for the
  person, as today.
- On: whenever a plan is made, and again when its idea's priority or risk changes, the board decides (code, no model):

| risk \ priority | High | Normal | Low |
|---|---|---|---|
| **low** | starts | starts | starts at night |
| **medium** | starts | waits for you | waits for you |
| **high** | waits for you | waits for you | waits for you |

- It never starts by itself: an idea with Open questions, or a plan the person stopped (from then on it waits for them).
- *Starts*: what `ideas.start` does, with `passed_by: "auto"` in plan.json (the person's press writes `"person"`).
  *Starts at night*: passed, with `start_at: "night"`: the runner starts its tasks only inside the night window (a task
  running at its end goes on); **Start now** on its row clears it. *Waits for you*: Needs you's *Plan ready*, as today.
- After the work nothing changes: the results wait at Review, merged into `dev`, nothing pushed (decisions §45.7).

## 6. The limits: never past the window; a reserve for the person
- The keeper checks the window as the runner does (`status.reset_of(limits, "claude", now, status.NEARLY)`) before a
  draft, a plan, a refresh or the proposals: in a spent window the call is not made, the idea stays where it was (`raw`, or
  `ready` before its plan) with `held_until` (the reset), its row says *waits for limits · after 18:00*, and it runs when the window is back. A
  call the person asks for (a talk, Process now, Re-plan) is refused the same way, in plain words.
- **The reserve.** What starts by itself (an autostarted plan's tasks, the night's run) does not start while the
  tool's `left` is at or below `ideas.reserve_day` (default **0.30**) by day or `ideas.reserve_night` (**0.10**)
  inside the night window: the rest of the window is the person's own work. It is held as the runner holds today
  (`held`, *after HH:MM*). What the person starts (passing a plan, a talk, Process now, Add) has only the `NEARLY`
  floor, as today. With no limits read for the tool, no reserve applies (as today).
- **High first:** when several wait, the runner and the night take ideas by priority, then by the person's order.

## 7. The night
- `ideas.night`, default `"01:00-07:00"` (the machine's local time), set in the Board's gear.
- Once a night, at its start (and again inside it when the limits held it), `core/idea_night.py` runs, in this order,
  each step stopping at the reserve (§6):
  1. the `night` queue: draft → plan → autostart (§3–§5), by priority, then the person's order;
  2. the plans that *start at night* (the runner);
  3. **refresh** (balance and quality): a goal whose linked paths, or paths named in its Summary, changed since its
     `read_at` (`git diff --name-only <read_at>..HEAD`) is read again on the `refresh` step; an unchanged goal costs
     nothing;
  4. **proposals** (§8).
- One event, `night_run`: `drafted, started, refreshed, proposed, held, seconds`.
- This is the Board's night. The camp's Night round (docs/design/night-round.md) is another thing and is not touched.

## 8. Proposals: up to 3 ideas a night, for the morning
- Balance: **2**, quality: **3**, thrift: **none**. One call on the `propose` step: the goals (Description, Summary,
  Metrics), each goal's ideas (title, state), the last 30 proposals turned down (title, goal, reason), the commits since
  the last night (`git log --oneline`, at most 50), the Wiki's index. It answers up to N `{goal, title, why}`.
- Each becomes an idea of that goal in a new state, **`proposed`** (`STATES` gains it): its Gist is the *why* (two
  lines); **no spec is written** until the person takes it. Never into General. Never more than **3** proposals waiting
  in all: a night with 3 unanswered makes none.
- In Needs you, last (they block nothing): **Take**, with a priority (default the goal's; the idea joins the queue as
  §3 says), and **No**, with an optional one-line reason. No removes the page and adds a line to
  `<state_dir>/ideas/declined.jsonl` (`title, goal, reason, at`), which the next night reads.
- `TERMS` gains `proposal` (*proposal / proposals*).

## 9. To-dos: steps on any, and a file
- **Steps on every kind** (today only `instructions` has them): the to-do's dialog shows its *why*, its steps (the plan
  of what to do), then its one input: a secret, a choice, a confirm, or a file. `instructions` stays (steps only).
- A new kind, **file**: `title` says what the file is (*the Firebase config, google-services.json*), `accept` an
  optional list of extensions. The person attaches one file, at most 5 MB, sent in `ideas.todo` as
  `file: {name, data}` (base64). It is kept at `<state_dir>/ideas/<slug>/files/<todo-id>-<name>` (mode 600): never in
  the repository, a page, plan.json (which says only `"value": "<name>"`) or a prompt's text. The task that waits for it
  gets its path in the environment, `ORKCRAFT_FILE_<TODO-ID>` (e.g. `ORKCRAFT_FILE_T2`), and one line in its prompt:
  *the file is at $ORKCRAFT_FILE_T2; copy it into the repository only if the task says so*. On the phone a file is
  given only over the paired link, as a secret is, else *At the computer*. Dropping the idea removes its files, as
  `idea_secrets.forget` removes its secrets.
- The plan prompt's to-do rules gain *file* and *steps on any kind, when the person has to do something first*.
  To-dos stay few (decisions §43.8, `MAX_TODOS`).

## 10. Needs you: one list
- `ideas.board`'s `today` becomes **`needs_you`**: one list of `{kind, idea | goal, title, text, priority, blocks, at}`.
  Kinds: `goal` (a goal asks), `asks` (a spec asks), `plan` (a plan waits for you), `todo` (a to-do of a plan),
  `failed` (a task or a run failed), `proposal`.
- Sorted by the backend: first what blocks work in progress (`blocks`: a to-do a ready task waits for, a failed task of
  a working idea), then the priority (the idea's; a goal's own), then the oldest first; proposals last.
- `held` leaves Needs you (the person cannot act on it): the idea's row says it (§11). The snapshot's `needs_you`
  count leaves proposals out.

## 11. Screens (B, C), top to bottom
1. **Goals.** A select (*All goals*, the default, then each goal: its title, its priority, its state in words:
   *reading · asks you · ready*) with **New goal** beside it, and the **Target** chip (*Target: Balance*). The chip opens
   the three with one line each: *Thrift: lighter models, less reasoning, no proposals at night* · *Balance* ·
   *Quality: heavier models, more reasoning, three proposals a night*. A chosen goal shows its Summary's first line,
   **Open** (the goal, as 34) and **Edit**. The choice filters Needs you and the ideas.
2. **Needs you.** §10's list, an icon per kind, its title and one line. A click opens what it is about: the questions of a spec or a goal as one
   form (a box per question, one **Send**: §0's one round), the plan (Take it to work), the to-do's dialog (§9), the goal. A proposal is answered in the row
   (Take with a priority · No with a reason).
3. **Ideas.** One row each, its title only, its priority as a mark, its state in words and its actions:

| the idea | its row says | actions |
|---|---|---|
| `raw`, queue `night` | *tonight* | Process now · Delete |
| `raw`, queue `hold` | *stopped* | Process now · Tonight · Delete |
| `raw` or `ready`, `held_until` | *waits for limits · after 18:00* | Delete |
| `reading` / `planning` | a spinner · *drafting* / *planning* | **Stop** |
| `plan`, `start_at: night` | *starts tonight* | Start now |
| `working` | *working 2/5* (· *waits for <idea>* while a dependency is not done) | Stop (as today) |
| `done` | in a folded *Done (n)* at the end | — |

   An idea in Needs you (`asks`, a plan waiting) is not listed here: each idea in one place. **New idea** heads the
   section.
4. **The spec** (the preview on the desktop, its own screen on the phone): its sections in §3's order; Stages shows
   each task's live state beside it from plan.json (*merged · working · held · failed*, in words beside the icon).
- The Board's gear: *Start plans by themselves* (on) and *Night* (from–to).
- The phone: the same order in one column, the Target chip in the Board's header, every dialog a sheet (34 §5).

## 12. Commands and events (A)
| command | args | returns |
|---|---|---|
| `ideas.goal_save` | `{"slug"?, "about", "priority", "title"?}` (`title` on Edit; 34's other fields still accepted and kept) | `{"slug"}` |
| `ideas.add` | `{"text", "track", "priority", "night"?: bool}` (`track` not `general`; `night`: the closed dialog's) | `{"slug", "queue"}` |
| `ideas.answer` | `{"slug", "answers": ["…"], "goal"?: bool}` (in the questions' order; §0's one round) | `{"ok": true}` |
| `ideas.queue` | `{"slug", "queue": "now" \| "night"}` (Process now, Tonight; `ideas.read_now` stays as `now`) | `{"ok": true}` |
| `ideas.read_stop` | `{"slug"}`: the keeper's run on this idea stops (its own cancel, not Stop all's); queue `hold` | `{"ok": true}` |
| `ideas.start_now` | `{"slug"}`: a plan that starts at night starts now | `{"ok": true}` |
| `ideas.proposal` | `{"slug", "take": bool, "priority"?, "reason"?}` | `{"ok": true}` |
| `ideas.board_set` | `{"target"?, "autostart"?, "night"?}` | `{"target", "autostart", "night"}` |
| `ideas.todo` | as today, and `file: {"name", "data"}` for a file to-do | `{"ok": true}` |

- `ideas.board`: `needs_you` in place of `today`; `target, autostart, night`; ideas gain `queue, held_until, risk,
  risk_triggers, depends_on, waits_on, start_at`; goals gain `title_by`. All callable from the phone (`gui/mobile.py`);
  a file to-do only over the paired link.
- Each keeper run has **its own cancel** (`read_stop`); Stop all cancels every one, as today.
- Settings, `IDEAS`: `target: "balance"`, `autostart: True`, `night: "01:00-07:00"`, `reserve_day: 0.3`,
  `reserve_night: 0.1`, `risk_paths: []`, checked in `settings.py` like the others.
- Events (spec 33 §9, the same log): `board_set` (target, autostart, night, device); `idea_added` gains `priority, queue`;
  `idea_drafted` (idea, risk, triggers, questions, tier, effort, seconds); `idea_answered` (idea, answers); `plan_passed` gains `by, risk, priority`;
  `keeper_stopped` (idea); `night_run` (§7); `proposal_made` (idea, goal); `proposal_answered` (idea, take,
  has_reason); `goal_read` gains `tier, effort`; `task_state` gains `ran_tier, effort`.

## Not in this spec
A model's review of results by the Target (the tests stay the review, decisions §40) and checking a done idea against
its Done when; goal-to-goal dependencies; goals proposed by the keeper (ideas only, the owner, 18 October); a Target on
Agents or Review, or per goal or idea; more than one input in a to-do; the camp's Night round; External listeners and
calendar meetings as Board screens (they go to General, unseen in v1).

## Tests
- **A:**
  - the matrix: every step × target gives its tier and effort; a role's own model wins and keeps the Target's effort;
    Grunt runs on the shifted tier; `--effort` is on the claude command only when the CLI's `--help` lists it (a fake
    `--help` both ways) and never on the laborer tier;
  - a goal saved with only a description and a priority is read at once on the `goal` step; the keeper's title is
    written and a person's never rewritten; Summary, 1–3 Metrics with *how*, links only to paths that exist; `read_at`
    kept;
  - `ideas.add` refuses no goal and General; High and Normal are drafted at once, Low and `night: true` wait for the
    night;
  - §0: no keeper call ever resumes a session; each call's prompt stays within its `CONTEXT` cap (the stub measures
    it) and holds only its listed parts (a talk's prompt has no earlier turn and no other section); `propose` runs with
    no tools; `--max-budget-usd` and `--no-session-persistence` are on the command only when the CLI lists them; a
    call ended on its cap leaves the idea as it was, with its line;
  - the draft writes its sections and front matter, drops an unknown or cycle-closing dependency; questions → `asks`;
    `ideas.answer` → one `answer` call, any question in its answer dropped and its assumptions in Decisions, then the
    plan; no questions → the plan at once;
  - Stages from plan.json, in waves, with S / M / L;
  - the risk: each trigger row raises it (a case each), whole words in any case, `risk_paths`, the max with the
    model's; the Risks section's first line;
  - autostart: the nine cells of the matrix; off → always waits; Open questions → waits; a stopped plan never starts by
    itself again; *starts at night* starts only in the window and **Start now** clears it; `passed_by`;
  - the limits: a keeper call in a spent window is not made and `held_until` is set, and it runs when the window is
    back; the reserve holds autostarted tasks and the night (day and night values) and never the person's own press;
    High before Normal;
  - the night: its order; a refresh only for a goal with a changed path (a fixture repository with a commit); N
    proposals by the Target (none in thrift); no new ones while 3 wait; a declined one is read back the next night;
    `night_run`;
  - `read_stop` stops one idea's run, not another's, and its queue is `hold`;
  - to-dos: steps on a secret; a file stored outside the repository, its path in the task's environment, never in
    plan.json or a prompt's text; refused from the phone off the paired link; removed with the idea;
  - Needs you: its kinds, the sort (blocks, priority, age), proposals last, `held` absent;
  - each event with its fields; `tests/test_architecture.py` (core and realm never import the GUI).
- **B:** browser tests at 1 440 × 900: New goal with only a description and a priority → *reading*, then its title
  and Summary; the goal select filters Needs you and the ideas; the Target chip sets and shows; New idea needs a goal;
  a High idea shows a spinner, its **Stop** leaves it *stopped*; a Low one shows *tonight* with Process now and
  Delete; Needs you is one list, a proposal answered in its row; the spec's Stages with live task states; a file
  to-do's dialog with its steps and an upload.
- **C:** the same at 390 × 844 as sheets; no horizontal scroll.
- Each part: the critical tests (CLAUDE.md "Alpha"), the touched modules' tests (`test_idea_keeper.py`,
  `test_idea_runner.py`, `test_ideas.py`, `test_gui_ideas.py`, `test_roles.py`, `test_board_loop.py`, and the new
  modules' own), `tests/test_gui_wording.py`, and the four checks of specs/README.md "Before you commit". The PM merges
  A, then B and C.
