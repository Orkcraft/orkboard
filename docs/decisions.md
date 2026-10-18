# Decisions §45–§50: Orkboard's ground

Copied on 18 October 2026 from Orkline's `docs/design/decisions-2026-10.md` (Orkcraft/orkcraft, `main` at 163fea1f),
sections 45 to 50 as they stood when Orkboard moved to its own repository (docs/specs/37-board-and-line.md §9). They say
why the four windows — the Board with its goals, the preview, Agents and Review — became a tool of their own, and how
Orkline goes on from it. Orkline's file stays the record of the decisions before §45 and goes on after §50; the links
below that name `docs/design/…`, `docs/specs/…` (other than specs 33–37) or Orkline's code point into that repository.
A decision taken here from now on is added at the end of this file, numbered on from §50.

## 45. v1 is three buildings in plain windows; Camp waits, its art goes on (17 October, the owner)

Why: the AgentCraft study (§37) shows a game image brings views (320k at launch) but not a habit (~200 npm installs a
week, 309 in Discord eight months on). Without the core working, a fun UI does not get far. So the first version is
the core, drawn plainly, and the owner tests it before anything else is built. A simplification (§27).

1. **v1 is three buildings:** the **Task board**, the **Agent pool** and the **Review gate**, shown as plain windows
   (Office's calm look, no camp map, no road graph, no animation). The person's path: an idea → the keeper's questions
   → the spec → the plan, passed on the board → the orks' work → the result, judged at the gate before it goes.
   External listeners and the Wiki are **not shown** in v1 (the idea pages still live in the Wiki, as §43.4 says).
2. **The phone first: three tabs, Board · Agents · Review** (the owner's sketch,
   [img/v1/phone-sketch.jpg](img/v1/phone-sketch.jpg), drawn as Board / Agents / Check). **The desktop shows the
   three at once as panes on one screen, left to right, as an IDE does:** Board | Agents | Review.
3. **The top bar, on every tab and pane:** what is left of the AI tools' limits, **the smaller of the window and the
   week** for each tool (Claude, Antigravity); a tap or hover shows both and when they reset. Beside it today's
   spend and **Stop all** (money and safety always visible).
4. **Board:** the goal (§44) at the top, **New idea**, the ideas in order, the person's to-dos. An idea's state is
   said in words (*new · reading · asks you · plan ready · working 2/5 · needs you*), not a badge. **A click on an
   idea opens its spec; a click on a to-do opens the plan the model wrote, scrolled to that to-do**, with one line on
   what it unblocks. **The plan is passed here, on the board** (§43.6). A secret to-do is entered only over the
   paired link, else *At the computer* (§43.8).
5. **Agents:** the orks grouped by role, each role with its tasks as chips: working · needs you · queued · done, in
   words beside the icon. A chip opens its task (what it does, its log, its spend, **Stop**). A waiting ork says what
   it waits on and leads to that idea. Roles keep **orkish names** (CLAUDE.md): the keeper is the **Taskmaster**, a
   worker is a **Grunt**, an image maker the **Alchemist**; a role the person makes keeps the name they give it.
6. **Review: only the results of work, before they go** (the plan is not here). Each result shows what changed, its
   tests (passed / failed, how many), what it cost, and its tasks. **Merge into `<branch>`** (default `dev`, the
   branch on the button) only when tests are green and nothing conflicts; red tests offer **Fix** (back to its task
   with the failure) and **Drop**, never a merge (§42). ✗ means **send back with one line why**; dropping is a
   separate button. Images are judged one by one (§39). The tab shows how many results wait.
7. **The testers' defaults:** a result merges into `dev`, never `main`, and nothing is pushed by itself (spec 29a's
   runner today merges into `main` and pushes: that stays the owner's setting only). The first start opens the three
   windows after the trust screen and the repository; **Mission 1 is not offered** (its code stays).
8. **Kept for later, by the owner's answers (not built until the three are tested):**
   - **Roles, models and limits are fully editable** (add an agent, edit a role: its model or tier, its parallel limit,
     its instructions). A new mechanic, so **a named exception to §27**. Each role a small file in the repository (seen
     in git, undone for free); three lean roles by default (§40); the waybill shows spend by role, so every experiment
     is measured.
   - **Image generation in the product (the Alchemist):** the owner uses it to finish the full Orkline, the camp and
     its orks drawn by Orkline itself. Off for testers by default. Cut by CLAUDE.md "Art" (once from the source, never
     re-pixelated).
9. **The product backlog is paused** (the owner): only what the three windows need is built; the owner tests them,
   then the rest. Everything else in specs/README.md waits, written specs included.
10. **Camp is frozen, not dropped; its art goes on.** The camp, the look switch and Mission 1 stay in the code (the
    full town behind `focus = ""`) and get no work: specs 17b, 20, 22, 23, 16, 14, 02 and 03 wait. **agy keeps
    making the art now** (the five buildings' sheets, the room kit), so Camp can be put in quickly once the core holds.
    18 and 19 are merged if they come back green.
11. **Dates stay (§22)**; **Halloween is dropped** (no decor, no Halloween post). Because Mission 1 leaves the first
    day, §27's first measure becomes: **of 3–5 testers, at least 3 take an idea of their own through to a merged
    result**; the second stays (**at least 2 come back within 7 days** unasked). After a week each tester is shown a
    screenshot of Camp and asked whether they would want it to look so: **two or more saying yes on their own** brings
    Camp back as the look over the working core.

## 46. v1 round 2: goals and ideas by dialog, straight to the model; agents by task type (17 October, the owner)

From the owner's test of spec 33: (1) **a goal** is made in a dialog with metrics, a priority, links to documents and a
deadline, and **goes to the keeper at once** on saving; (2) **an idea** is a short text with **Process now** or
**Later**; closing the dialog with text saves it as Later; the keeper then fills its priority from the goal and the
rest; (3) **agents**: a role is a model and an instruction (and a limit), and each **task type** (code, tests, docs,
text for people, research) is assigned a role, or a new one is made from there; this brings §45.8's roles into v1 now;
(4) every dialog and menu opens on a dimmed backdrop; (5) a phone is paired from the shell (QR, Tailscale said
plainly). Spec 34. Improvements of v1's existing mechanics; the roles are §45.8's named exception to §27.

## 47. The Board does the writing; it starts what is safe; the Target picks the minds; the low work waits for the night (18 October, the owner and the PM)

Why: after 34 the person still types what the model could write (a goal's title, metrics, links), and every idea waits
on the person three times (the talk, Take it to work, passing the plan) even when it is small and safe. The person's
time and the window's daytime share are what is short; the night's window goes unused. So:
1. **A goal is a description and a priority.** The keeper writes its title, its Summary as the context every idea
   under it starts from (the files it touches, what exists, the constraints), 1–3 measurable *done when* lines, and its
   links. On the elder tier: a goal is rare and everything below reads it. No goal-to-goal dependencies. This replaces
   the dialog of 34 §1 (its data stays readable).
2. **An idea is a text, a goal and a priority** (the person's). No idea without a goal: General stays only for what the
   system files (External listeners, calendar meetings, Mission 1). High and Normal are drafted **at once** into a
   full spec and plan; Low waits for **the night**. The 30-minute batch on the laborer tier (§43.3) goes.
3. **The spec, simpler:** Gist · Why · Done when · Out · Risks (product, tech) · Depends on (ideas of any goal) ·
   Stages · Open questions · Decisions. *In* and *Estimate* go (the price stays on Take it to work). The tasks are
   seen only in Stages: name, order, complexity, what runs in parallel.
4. **Autostart, on by default.** A plan starts by itself by its risk and its idea's priority: low risk starts (Low
   priority at night), medium risk starts only for High, high risk always waits for the person; Open questions always
   wait. The risk is the model's, raised by rules no model can talk down (secrets, data, CI, outward actions). This
   reverses §41.3 and §43.6 for what is safe: the Review gate after the work is unchanged and nothing merges into
   `main` or is pushed by itself (§45.7), so a wrong start costs tokens, never the code. For the testers it is one step
   fewer to §45.11's first measure.
5. **The limits:** nothing starts in a spent window; what starts by itself leaves the person a reserve of the window
   (30 % by day, 10 % at night); High goes first.
6. **The Target moves from the building to the Board's whole route** (§44.3): thrift · balance · quality picks the tier
   and the reasoning of every step, the keeper's and the orks'. A model the person picked for a role wins.
7. **The night** drafts the low ideas, starts what may start at night, reads again a goal whose files changed, and
   proposes **ideas, not goals** (the owner): two in balance, three in quality, none in thrift, never more than three
   waiting; a proposal has no spec until the person takes it, and a declined one is not proposed again.
8. **To-dos** carry their steps whatever their kind, and a new kind takes a **file**, kept like a secret (never in the
   repository, a page or a prompt).
9. **The Board's order:** the goals as a select with New goal and the Target; **Needs you** as one list (questions,
   plans, to-dos, failures, proposals), what blocks work first, then by priority; the ideas as one line each, a
   drafting one with a spinner and Stop, a night one with Process now and Delete.
10. **One call, one job, above all** (the owner's pain: long talks on ideas eat the context and the money). No
    session per idea: every keeper call is one shot, never resumed, given only what its job needs under a cap, with
    a bounded number of files to read and a money cap per call; the page is the memory and the talk never goes back
    to a model. One round of questions, answered together; after it the keeper decides and writes its assumptions
    into Decisions. A talk turn is an edit of one section, not a chat. This replaces §43.5.
11. **The specs are committed at every change to the work branch** (the owner: parallel orks must see each
    other's specs), from a detached worktree of the Board's own, so the person's checkout is never in the way.
    Two branches in the concept: **dev**, where the work and the specs land, and **main**, moved only by the
    person; the owner's repository works on `main` for now. This replaces §43.4's "the keeper never commits".
Improvements of v1's existing mechanics (§27). Spec 35.

## 48. Agents shows what each ork costs and how often it gets it right; Review's decisions are the signal (18 October, the owner and the PM)

Why: the owner's ask (18 October). Agents is worth its place as the roles and what each does now; the money and the
quality of every step should be seen by goal, idea, task and ork; and the person's decisions at Review should tell the
product whether a result failed on quality or cost too much. Prioritised hard: the testers start on Friday 23, and spec
35 is being built on the same files.
1. **Agents is a monitor, not a settings page.** The roles and their live tasks, a task that needs the person first,
   leading to its Needs you item. The task types leave the window: an agent's dialog says which types it takes. A Grunt
   never asks in the middle of a task (§40, spec 35 §0's one round of questions): a task that cannot go on is a failure
   in Needs you, and the spec's quality is measured by how few there are.
2. **A role is who; the Target is how much thinking.** A role is a name, an instruction (at most 600 characters, as
   §40's personas), a limit and, if the person wants, a fixed tier; its model is *By Target* by default (the task's tier,
   shifted by the Target, as Grunt's). The effort always comes from the Target (spec 35 §1). No role gets an effort of
   its own: one dial moves the money, so the waybill can say what made a step dear, and the Target never says *Thrift*
   while an ork thinks at full effort. The raw model names leave the list (they repeat the tiers); a role file that
   names one still runs it.
3. **One currency: ≈$ at API prices**, said plainly (*not your bill*; `sources/pricing.py`), never $0 for what is
   unpriced. What is left of a window stays in the top bar. Harnesses are compared once a second one runs roles; the
   tool and model of every run are recorded from now on, so the data is there by then.
4. **What is measured, goal → idea → task → stage → ork.** The stages: the goal's read (and its night refresh), the
   spec (draft, answers, talk), the plan, the work (round 1), the rework (the rounds after a send back), and what was
   dropped. Two numbers decide: **$ a merged result** and **merged the first time** (round 1, never in Needs you). The
   Taskmaster's number is the spec's: of its plans' tasks, how many finished without Needs you (target 95 %). The
   plan's estimate learns from the board's own runs (a tier's mean over its last 20 tasks, as the pool's
   `plans.tier_costs` did), so *over the estimate* means something.
5. **Review's decisions are the signal.** Send back keeps its one line (quality); Merge gets an optional *Cost too much
   for this* (cost); the card shows its cost against the plan's estimate. Nothing changes by itself on a signal. After
   the testers, the night turns repeated signals into proposals in Needs you (a line for a role's instruction, a
   lighter tier for a type of work), taken or declined as spec 35 §8's.
6. **Tools later, and as tools.** Making images is a tool (an MCP server, e.g. an image API on the person's own key)
   given to a role, not a harness that can draw: running Antigravity inside Orkline is §5's ban risk. After the
   testers, with the Alchemist (§45.8).
7. **Before the testers, two lines, both in spec 35:** every keeper event carries its step, tokens and cost, and every
   task's run its tool and model (the testers' week cannot be measured again later); and an Agents chip says what
   started by itself or waits for the night, and why a task is held (the limits or the person's reserve), since spec 35
   starts plans without the person. The rest is spec 36, after 35 is merged.
Improvements of v1's existing mechanics (§27); the roles stay §45.8's named exception. Spec 36.

## 49. Two branches and the gate between them; orks never on the same files at once; checks by paths (18 October, the owner and the PM)

Why: the owner's flow (18 October). The person sees two branches only, **dev** and **main**: no pull requests, no
task branches. The orks' work lands in dev by itself when it holds; main moves only when the person passes it at the
Review gate. Prioritised hard, tokens above all: what paths and tests can decide, code decides; a model only writes
and fixes.
1. **Orks never work on the same files at once.** An idea claims its `touches` when its first task starts
   (`realm/claims.py`, written for the Agent pool and unused by the v1 runner); an idea whose paths meet an older
   one's waits for it. Conflicts are prevented, not merged: spec 35 §5 starts plans without the person, so two may
   run on the same files. In spec 35 part A (§5), before the testers.
2. **No messages into running sessions** about files that changed: a task is one `claude -p` run, a message would
   ride every later turn, and most changes do not concern it. A conflict is caught where it is today: at the rebase
   when the result lands, sent back with its files (`core/idea_runner.py`, `again["files"]`).
3. **No model looks for related specs.** The specs are on dev at every change (spec 35 §13); which ideas meet is a
   fact of their `touches` and `depends_on`, worked out by code (`claims.meets`): the draft gets the few ideas whose
   `touches` meet its own, a task gets the paths of at most three neighbouring specs. The Wiki stays for meaning
   (words, decisions), not for finding conflicts. After spec 35.
4. **Code lands in dev by itself** (`ideas.review` off): when its tests are green, it does not conflict, it touches
   no risk path its idea's risk left out (spec 35 §4) and it holds no media; else it waits in Needs you. No model
   reviews a task (§40: the tests are the review of code). After the testers, with item 5: their week keeps v1's
   result-by-result Review (§45.6).
5. **The Review gate is dev → main:** one card, *dev → main: N changes*, its report (the full suite, the browser
   tests, item 7's checks) and one press. Each result is a line of it with its cost against the plan, **Revert** (the
   quality signal, in place of Send back) and *Cost too much for this* (spec 36 §4's `dear`), so spec 36's two
   signals move with it. Spec 32's night gate (`core/night_gate.py` on `origin/dev`, written 17 October on a line that
   left main) is ported, not merged; its nightly model session that fixes dev waits for numbers on how often dev is
   red.
6. **Images, video and sound are judged one by one, before dev.** A result holding media does not land by itself: it
   waits in Review's **Look** row (Take · Another · Drop). The candidates live outside git
   (`<state_dir>/ideas/<slug>/candidates/`); only the one taken goes into the repository, cut once (CLAUDE.md "Art").
   No model looks at them; code checks size, format and alpha. The dev → main card says them in one line (*3 assets,
   taken 18 October*).
7. **Checks for what goes out are config, picked by paths, not by a model:** `.orkcraft/checks.toml` in the
   repository (`name`, `when` globs, `run`, `measure`, `compare = "main"`, `limit`). A short built-in catalogue
   (build size, bundle size, a benchmark, a document format lint) is offered once when a dev → main diff meets its
   paths; one click writes the line. Over a limit, *Pass to main* is off and says why. What goes to people (pages,
   mail, posts) stays §39's one-by-one look and waits for External listeners.
8. **Cut:** a model that orkestrates or reviews the orks' tasks; messages into running sessions; rebuilding the Wiki
   to find conflicts; a branch for assets; pull requests as the way (§42).
9. **Tokens, in spec 36 §6:** a task's prompt lists only the tasks it comes `after`, not every task before it in the
   plan (that list grows with the plan).
The order: spec 35 with item 1 → the testers → spec 36 A → **gate-kinds** (items 4–7, with spec 36's Review card) →
spec 36 B and C without the Review card. Item 3 rides gate-kinds or the Board's next round. Whether Orkline's own
repository moves to dev with item 4 or stays on main through the alpha is the owner's call. Improvements of v1's
existing mechanics (§27).

## 50. Orkboard and Orkline: one engine, three slices; the loop is the graph's unit; the game only reads (18 October, the owner)

Why: the owner's plan (18 October). With specs 35 and 36 the four windows (the Board with its goals, the preview,
Agents, Review) are a whole tool. The owner wants it every day, at work and at home, on other projects, and to go on
building Orkline from what that use shows. Today the four windows live inside the town's code: about 12 800 of the
90 000 lines of Python are theirs (15 100 with specs 35 and 36), and the rest comes along through nine imports (`realm/jobs.py` runs a tool through
`realm/roads.py`; `realm/harnesses.py` and `realm/tiers.py` read the machine through `realm/builders.py`;
`realm/worktrees.py` reads the town's scroll; `gui/ideas.py` finds its Wiki among the town's buildings). The town
also has its own Agent pool and Review gate (`core/workers/barracks*.py`, `realm/gate.py`, `realm/team.py`, the road
engine) beside the Board's runner and review (`core/idea_runner.py`, `core/idea_review.py`), and its own building
windows (`gui/views/*`, `js/buildings/*`) beside the v1 panes (`js/shell/*`). Two engines: what one proves says
nothing of the other. So:
1. **Three slices, two products.**
   - **Orkboard:** the engine and its base modules (goals, ideas and their specs, agents, review; the Wiki under
     them) in one fixed loop, drawn as the v1 panes in Office's look, the phone included. The owner's lab, used every
     day on other projects; not published (§37.2 stands: the public name is Orkline).
   - **Orkline, Office:** the same modules, assembled by the person into loops (item 3); no game.
   - **Orkline, Camp:** the same graph with the camp's art and its game layer (item 5), for the first audience's
     evening (audience.md §2a): a clear switch from the day's job to one's own project.
   Office and Camp stay one product with two looks, switched by the shift (portrait.md §3). The name stays Orkline.
2. **One engine.** What Orkboard proves must hold in Orkline, so Orkline's nodes are Orkboard's modules: the Agent
   pool runs on the Board's runner, the Review gate on its review. The town's own pipeline (`barracks*`, `gate.py`,
   `team.py`) retires once those nodes stand on Orkboard's modules; what only it does (External listeners' read and
   reply paths, the `doc` path) moves over as modes. Never two copies: Orkline imports Orkboard's modules, never the
   other way round.
3. **The loop is the graph's unit**, not a free graph: sources → a goal → its track (the stations: the draft, the
   plan, the orks' work) → review → rework back into the track, or out to dev. Editing the graph is adding a loop, a
   station to a track, a source to a goal. Orkboard is one loop whose source is the person. A free graph is what
   scares the first audience off n8n (audience.md §1). The road engine may stay as the transport; the loop is the rule.
4. **A source has the person's contract:** it puts an idea into a goal. External listeners become sources attached
   to a goal, so their cards reach the goal they serve, not General.
5. **The game layer only reads.** The score, Renown, the stages and the missions subscribe to events (`core/bus.py`,
   the event log) and draw; they never change what the work does: no mission opens a feature, no reward moves a
   queue, and a mission that starts work does it through the person's own commands. So Camp is Office with a look and
   a reader, and what holds in Office holds in Camp. CLAUDE.md "One vocabulary, two looks" says so. The one exception
   today is Mission 1 (`core/mission.py`): it raises buildings, lays roads, makes the pool run no model (`drill.json`)
   and passes its own cart at the gate. It is frozen with Camp (§45.10) and moves onto the person's commands when Camp
   comes back. The score (`realm/score.py`) already only reads, but counts the town's results, not the Board's.
6. **The building windows are the panes.** In Orkline a click on the Task board, the Agent pool or the Review gate
   opens the same pane as in Orkboard, so Orkboard tests the interface too. Their `gui/views/*` retire with the
   town's pipeline (item 2).
7. **The contract between modules is written down now**, while there are four: what passes along each edge (a goal,
   an idea with its spec, a plan, a task, a result, a merge or a send back) and where it lives (the pages,
   `plan.json`, the event log); spec 37 §6. A setting that takes a step out (`ideas.review: false`, §49.4) is a loop
   without that node: in Orkline it becomes the graph's, not an `if` in the runner.
8. **The order:** Orkboard holds (the owner's daily use, the testers) → Orkline Office (the loops) → Camp. Camp's art
   goes on in agy meanwhile (§45.10). No graph and no game mechanic is built before the testers' numbers (§27, §36).
9. **Stage 1 now, in this repository (spec 37):** the boundary as a list of Orkboard's modules and a test that they
   import nothing of Orkline's (today's edges listed; the list only shrinks); the edges cut and Orkboard started on
   its own; the gate run on another repository's tests (its first need at work: today's gate knows only pytest and
   this repository's critical tests, and passes a result when no test file is found), its settings in a tracked
   `orkcraft.toml` at the repository's root (`.orkcraft/` is git-ignored, so §49.7's checks go there too). Nothing moves files while specs 35 and 36 are open on them. **Stage 2, right
   after Orkboard runs on its own** (changed the same day by the owner; first planned after the testers' numbers):
   Orkboard moves with its history to `Orkcraft/orkboard`, package `orkboard`; the state keeps its names, so both read
   the same settings and Boards. Orkline's copy stays frozen through the testers' week (a change lands in orkboard
   first), then Orkline depends on the package. Item 10 is built there. Spec 37 §9.
10. **Orkboard is a project's IDE** (the owner, the same day). It opens a folder as an IDE does (git started when
    there is none), keeps several projects open at once, each with its own Board, and shows one; it shows the
    project's files and its git: Markdown and code read and edited in place, the status, a file's diff, a commit, a
    branch, pull and push on the press. The goals, the ideas, the specs, the plans and the Board's settings (the
    Target, `merge_into`, the night…) are the project's, no longer the machine's. The orks still write the code; the
    person reads it, fixes small things, writes the Markdown and commits. What may hold a secret is never shown, and
    a Board page is edited only through the Board. Spec 37 §8, after Orkboard runs on its own.
Architecture and order, and for Orkboard the owner's named exception to §27 (item 10, as §45.8's roles); no new
mechanic in Orkline before the testers. Spec 37.

## 51. Operations: the person's everyday work by templates, across projects; a template checks with you until it may go by itself (18 October, the owner)

Why: the owner wants Orkboard every day at work (§50), and most of a working day is small, frequent work that is no
code and belongs to no repository: a Jira task to file with its priority and epic, an email to answer. The Board's loop
(goal → spec → plan → orks in a worktree → the gate → Review) does not fit it: three or four calls where one is enough,
and the gate refuses a task that changes no file. Done by hand or in a chat with a skill, it has no queue, no check
before it goes and no memory of how the person wants it. So:
1. **Operations is the person's, one for all projects**, not a project's goal: its state in the person's folder
   (`~/.config/orkcraft/ops/`), never in a repository. The project's General is not renamed or touched: it stays the
   system's own place (spec 35 §2), and External listeners still go to the goals they serve (§50.4).
2. **A template is a Claude skill and a short form:** the skill's `SKILL.md` stays the person's and works in Claude
   Code as before; Orkboard's manifest beside it (`orkboard.toml`) names the fields asked at creation (a Jira task's
   priority and epic), the tools it may read with and the one tool that does its action. The person's own templates
   now (`~/.claude/skills/`); shared with a team later. Two built in: a Jira task, a reply to an email (saved as a
   draft).
3. **One job per call, as the keeper's (spec 35 §0):** a prepare that reads and changes nothing, the person's check,
   then an action allowed only its one tool, checked by code to have done exactly what was checked. Nothing outward is
   done twice by Orkboard.
4. **The way to by itself (the owner):** a template checks with you first; a check passed with no correction sends it
   by itself (after one, a setting); a correction makes it propose rules made general from it, and when the person
   takes them it goes by itself. A doubt of its prepare, a `high` risk or the day's cap still stops it at the check;
   **Not right** on what it did, a changed skill or **Check again** sends it back.
5. **What it reads stays the person's:** a mail's words and an issue's live only in the person's folder, its calls are
   kept there and not in a project's logs, and its texts go after 14 days.
6. **The template is the contract of a source:** when External listeners come (§50.4), a mail that came in fills the
   same form; what a source starts keeps the reserve (spec 35 §6).
A new mechanic before the testers' numbers: the owner's named exception to §27 (as §45.8 and §50.10). Spec 38.
