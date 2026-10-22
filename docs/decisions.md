# Decisions §45–§50: Orkboard's ground

Copied on 18 October 2026 from Orkline's `docs/design/decisions-2026-10.md` (orkWorks/orkLine, `main` at 163fea1f),
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
   Orkboard moves with its history to `orkWorks/orkBoard`, package `orkboard`; the state keeps its names, so both read
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

## 52. The Map: a project's work on one screen; the preview becomes tabs; the skill tree is Camp's skin (19 October, the owner)

Why: since spec 35 plans start by themselves and work goes on at night, and since spec 37 D several projects are open at
once; the Board still shows work as lists (Needs you, a goal's ideas, an idea's Stages). The owner wants to see a
project's goals, ideas and tasks and their links on one screen, as an RPG's skill tree (Diablo). The metaphor fits
the data, not only the look: a goal is a tree, an idea a skill, `depends_on` its prerequisite, a plan's tasks its
ranks (*working 2/5*), a plan's estimate its cost, the night's proposals the skills offered. So:
1. **The Map is a view, not a mechanic.** Read from what the Board holds (the pages, `plan.json`, the claims, the
   ledger) by `realm/board_map.py`; it changes nothing; its one action is *open*. Not a graph editor (§50.3): its shape
   is the goals and the ideas' `depends_on` as they are written. Named by what it does: *Map* (`TERMS` `board_map`).
2. **The preview becomes tabs**, as an IDE's (§50.10): the Map's tab first and pinned, every other thing in a tab that
   closes; one passing tab that a click replaces and an edit or a double-click keeps (VS Code's preview tabs); at most
   12; each project's tabs kept per device.
3. **The skill tree is Orkline Camp's skin over the same `ideas.map`** (§50.1, §50.5, §50.6): Camp's art, its *learn*
   the person's own Start, no points that open or move work. After the testers' numbers, or as §45.11's screenshot in
   place of the town's: cheaper art, and it shows the core.
4. **Measured:** the Map's opens per day, the first screen opened each morning, the share of ideas opened from it
   (`opened` gains `via`).
A view of existing data: an improvement of v1's existing mechanics (§27); the Camp skin waits as §50.8 says. Spec 39.

## 53. Orkboard is drawn in orkUI; an agent's craft is its race, its tier the gear on its head (19 October, the owner)

Why: the page and the phone were drawn in the old design system's Office theme on top of Orkline's twelve Camp sheets
(the town, the yards, the kit), with its warm browns, a gold accent and four faces; orkUI (github.com/orkWorks/orkUI) is
now the design system of orkWorks' products, its first look *office*. And Agents said who works only in words: a role's
name and a model, never what kind of work it does. The owner: rebuild Orkboard on the new design system, and show an
agent's role and tier with the mascots, **orks the engineers, elves design, goblins data, gnomes marketing**. So:
1. **One look, orkUI's office**: dark, monochrome, dense; IBM Plex Mono for text, Pixelify Sans for headings and
   buttons; nothing round; selected raised with a 2 px ink bar; every arrow and icon a pixel mark. orkUI owns its tokens
   (`--ork-*`) and components (`.ork-*`); Orkboard's sheets read them and carry no colour, font or corner of their own.
2. **A copy, never edited here**: `design-system/orkui` is orkUI's `office/` with its licence, stamped in `ORKUI.json`
   (orkUI's version, commit, every file's hash) and refreshed by `python -m orkboard.design.orkui <orkUI>`. A copy, not
   a git submodule: the wheel, `uv tool install` and CI need nothing more than this repository. A change to the look is
   made in orkUI first.
3. **What leaves**: the old tokens, components and kit with their four faces; the twelve Camp sheets the page loaded;
   the phone's light Office (office is dark only), its fence, tiles and dock. The Camp skin stays Orkline's (§50.5).
4. **The pixel face never for a person's words**: a goal's or an idea's title, an agent's name, a Markdown heading, a
   file's name stay in the text face; headings, labels, buttons and tabs are the pixel face's.
5. **Colour means a signal** (danger, alert, success), except the one ork green of the primary action and the muted
   heads of the races; waiting is not a signal (`wait` reads as muted ink).
6. **An agent's craft is its race**: a role is engineering, design, data or marketing (`craft` in its file), drawn as
   orkUI's head of an ork, an elf, a goblin or a gnome. Taskmaster and the Grunts are orks, always (CLAUDE.md: orks by
   their orkish names); a role written before crafts is engineering. orkUI's knight and lich wait for a craft of their own.
7. **Its tier is the gear on its head**: a novice bare, a seasoned in iron, a veteran hooded. A role wears its own tier
   (or its hand-set model's); By Target, the tier the Target gives it now; a task, the tier it ran at (before it ran, the
   tier it will run at). The tiers are said in today's words everywhere, the model list too (*Veteran · opus*).
8. **A head is an accent, never a picture** (the owner): 24 × 22 beside an agent's name, 12 × 11 (a pixel a cell) in a
   chip, a plan's task, the Map's tasks, a task's Tier line; its words beside it or in its title. The Agents tab is an
   ork's head; a goal's mark is a flag.
An improvement of v1's existing mechanics (§27): the look and the words of what is there, one new field (`craft`).
Spec 40.

## 54. The phone, round 3: what waits for you is the signal, a name fits its chip, a question comes with its answer picked (20 October, the owner)

Why: the owner's notes after a day on the phone. The top bar's ! repeats the Needs you tab's count and never says
whether work stands still; the project switcher, the gear and the Board's heading and Target row take the room the goal's
name and the limits need; goals' and ideas' names are cut on the Map; starting a plan takes two screens; Speak sits on
the Board unused; New goal is three screens for what is mostly a default, and a goal's team cannot be changed on the phone
once it is made; Add agent only makes a new agent; an agent's line spells its model in words; the questions' likely
answers are seldom the ones taken. So:
1. **Needs you is the signal**: orkUI's warning mark and colour while something waits for an answer — a
   question, a plan to start, a to-do, a failure, an Operation's check —; a plain count while only results wait in
   Review. The top bar's ! goes. Colour means a signal (§53.5): a result waiting for a look is not one.
2. **The top bar holds the goal and the limits**: the menu at its left opens the drawer (Stop all, today's spend, the
   projects, this project's settings with the Target, this phone's); the gear and the Board's heading and Target row go.
   A setting sits with what it sets: the phone's and the project's in the drawer, a goal's in Edit goal on its screen.
3. **A short name**: an idea, a goal and a task carry `short` (24 characters at most), written by code when it is made,
   then by the call that writes its title anyway (the draft, the plan, the goal's reading): no model call more. A chip
   or a tab shows it on two lines; the title stays on its screen.
4. **The Map gets one action beside open** (amends §52.1): a node that waits for the person alone — a plan whose ideas
   it depends on are done, a plan held for the night, an idea held for the night — has one button, with what it costs.
   Nothing is skipped from the trail but a check (spec 39); a task of code never, the next ones build on it.
5. **New goal on one sheet**: what it is for, the craft as a row of heads, the team folded to one line with Change (its
   bands in folds, one open at a time), the checks, Save always in sight. A goal's team changes from its screen.
6. **Agents**: Add agent takes one from the library or makes your own; an agent is one line — its head (the race its
   craft, the gear its tier), its name, how many at once, about what a task costs —; the Taskmaster and the Grunt say
   what they are told already beside the field that adds to it.
7. **A question comes with its answer picked**: the Taskmaster gives each question its choices, the one it recommends
   and why; the recommended ones are pressed, so one Send takes them, and *Let the Taskmaster decide* takes them unread,
   written in the spec's Decisions as its pick. Measured: how many answers are a choice, the recommended one, typed, or
   left to it — the research the owner asked for, before the next change to how it asks.
8. **Not done, and why.** *A goal stays a goal*: it has metrics, a flag and a verdict, and the Map's trail runs to that
   flag; a line of work by kind is the goal's craft, so goals may be grouped by craft, never renamed back to tracks
   (`track` is the word `goal` replaced, `TERMS`). *No sideways scroll of ideas*: it hides what is past the edge and
   breaks the trail's order; the trail packs tighter instead. *No token multiplier on an agent*: a person has nothing to
   hold it against and a token's price differs by model; dollars a task say it. *No new leader for delivery*: spreading
   the work across goals is the Taskmaster's (priority, autostart, how many at once, the limits); a release is an
   Operation's template (spec 38), a spec of its own when wanted. *No tool mark on an agent* while every agent of the
   Board runs on Claude Code (`core/idea_runner.py` `HARNESS`).
An improvement of v1's existing mechanics (§27): the look, the words and the order of what is there; two fields
(`short`, a question's `pick`), one command (`ideas.role_add`), one flag (`ideas.answer`'s `decide`). Spec 41.

## 55. Coming back: the Board says what it did, not only what it costs; the game only reads, and rewards results and thrift (20 October, the owner and the PM)

Why: a product manager's review (20 October). The Board says loudly what it costs, what waits and what failed (the
spend, the limits, Stop all, Needs you's warning) and quietly what it did: a merged result goes into *Done (n)*, the
night's work is said nowhere (`night_run` and `night.json` are read by no face), an accepted goal is a flag of another
colour. The only reason to open it is Needs you, a duty, and that reaches the phone only while its page is alive (no
`push` handler in `pwa/sw.js`, no producer of the phone's `news`) and the desktop never. AgentCraft (§37, §45) showed
that a game's picture brings views, not a habit; what brings a person back is their own work, seen. So, a game layer
that only reads (§50.5):
1. **It rewards results and thrift, never volume or spend:** merged, merged the first time, $ a merged result, a
   goal's flag, a template that goes by itself. No points, levels, badges, leaderboards, sounds or confetti, and no
   streak of the person's: a day away costs nothing. The one run it counts is the Board's own (nights in a row with
   work done), kept by adding ideas, which is what the Board needs.
2. **Said once, in one place, closed by one press:** a card shows when it has something to say and not again; nothing
   pops over the work; a mark that moves moves once, and never under `prefers-reduced-motion`.
3. **Eight pieces, built in this order:** (A) *While you were away*, the card of what the Board did since this device's
   last look; (B) the flag raised once when a goal is accepted, with its tally, and *Flags*, the goals met; (C)
   notifications on the paired phone (Web Push from the desktop, no server of ours and no app store) for an answer that
   waits and the morning's summary, and Needs you's count on the app's icon; (D) an agent's record in its dialog (its
   line stays §54.6's); (E) a template's way to by itself as progress (*2 of 3 clean checks*); (F) this week's work
   beside the limits (≈$ at API prices, the results, what the nights did, *Nothing waits for tonight*); (G) *Last week*,
   a card on the first look of a week; (H) nights in a row, said only where A, F and G already speak.
4. **Measured:** each piece logs when it is seen and what was opened from it (`via`), read against §45.11's second
   measure (two come back within seven days unasked) and §52.4's first screen of the morning.
The owner's call: all eight now, before the testers' numbers: a named exception to §27 and §50.8 (as §45.8, §50.10 and
§51). Views of existing data, but C, which is how a question reaches the person, and two counters (`done_alone`,
`alone_since`) in a template's trust. Spec 42.

## 56. A goal's party is measured: a check says what it found, the party's work is shown, its price is seen before it starts (20 October, the owner and the PM)

Why: a product manager's review (20 October). A goal's party is a deck-builder at heart — a library to pick from, a
craft, seats (one leader, three builders, two checkers), a party of each craft to start from, a checker's check that
holds every idea of the goal to it — and that is the right game for Orkboard, because the choice is the work's own:
what a goal costs against how carefully it is done. But it is half a loop: a party is picked once, and nothing says
afterwards whether it was a good one. Worse, a check cannot say "nothing found": a check task that changes no file
fails at the gate (`core/idea_task.py`: *You changed no file*), so a clean check is a failure in Needs you or a file
made to pass. So:
1. **A check says what it found** (`findings`, in a file the runner reads and never commits): none is clean and passes
   without a change; what it fixed goes through the gate as any work; what it left goes to Review, whatever
   `ideas.review` says, with *Fix them* and *Leave them*. The engine's one change here; the rest only reads.
2. **What the party did**, on the goal's screen and under its flag: each member's tasks, merged the first time and $;
   each checker's ideas checked, clean, caught, left and $.
3. **A party's price before it starts**, while it is picked: *about $2–4 an idea*, and what each check adds, from the
   project's own ideas once there are enough, a first guess before.
4. **What a check is worth**, in its agent's record (spec 42 D), and the night's one proposal from it: a checker that
   found nothing in the last eight ideas of a goal is proposed to leave that party, taken or kept by the person (as
   §48.5 means the night to turn signals into proposals; the first of them).
5. **Hints while picking**: at most two quiet lines (a check that seldom applies to the goal's craft, no builder for its
   code, a check that has found nothing lately); never a block.
6. **Your parties** (the owner, the same day): a party saved from a goal's screen and picked again for a goal in any
   project, kept in the person's folder as Operations are (§51.1), never in a repository; an agent of the person's own
   travels inside it and is installed where it is missing, never over a project's; a saved party's record is its
   goals, its projects and its flags.
Not a game's words: no cards, decks, mana or rarity in what a person reads (CLAUDE.md: everything by what it does); no
agent unlocked, no tier raised by use, no party ranked against another's. Built after spec 42, before the testers'
numbers: the owner's named exception to §27 (as §55). Spec 43.

## 57. Low work spends the week's room: by day when the week is ahead of its pace, at night when it is not behind (20 October, the owner and the PM)

Why: the owner's idea (20 October): start waiting work while a window has room that would otherwise be lost. Today Low
work waits for the night whatever the week says (`realm/idea_risk.py` `AUTOSTART`: low risk, Low priority → night), and
at night it may spend down to 10 % of the smaller window (`idea_target.reserve`), the week's too: a tight week is spent
at night on Low work and High work finds nothing the next day; a loose one ends with its room unused. Normal work of
low risk starts at once already, and work of medium or high risk waits for the person on purpose. The week is the
budget; the five hours are a rate that comes back. So:
1. **One rule in place of "Low at night":** what the Board itself put off to the night (a Low idea's draft, a Low plan's
   start) goes **by day when the week is ahead of its pace** (its share left at least 10 points above the share of the
   week still to come) and **at night when the week is not behind** (its share left at least the share to come). What
   the person put off (*Tonight*) stays the person's: the night, as today.
2. **The five hours only ease the reserve:** within the hour before the five-hour window comes back, and while the week
   is not behind, the day's reserve on that window is the night's.
3. **Only "when", never "whether":** risk still decides what may start without the person; no forecast of a burn rate
   (whole percents read every ten minutes, and the person's own use in the same window, make it noise): a straight
   line from the week's reset is the pace.
4. **Measured first among it:** the week's share left when it resets (`week_reset`), said in This week (spec 42 F) as
   *Last week ended with 30 % unused*; if weeks end spent, the rule mostly holds Low work at night, which is its other
   use.
Improvements of v1's existing mechanics (§27): the same autostart, the same reserve, read against the week. Spec 44.

## 58. A tool that is not signed in opens its own sign-in at once; the work that needs it waits for it (20 October, the owner)

Why: the owner (20 October): when Claude Code's sign-in fails, Orkline only says so (*Sign in again in a terminal:
claude, then /login*), and the task that hit it is failed. The person has to find a terminal, sign in, maybe in another
config folder than the one Orkline's runs use (`tool_errors.claude_sign_in`), and then start the work again by hand.
Every tool Orkline runs has its own sign-in; Claude Code (`claude auth login`) and Codex (`codex login`) open the
browser by themselves and take the answer back without a terminal (checked on 20 October: 2.1.304, 0.163.0). So:
1. **The sign-in opens at once**, for every tool: in the browser for a tool that signs in there by itself, in a terminal
   window opened with the tool for one that signs in only inside its own session (pi's `/login`). Orkline starts the
   tool's own sign-in with its own environment, so the sign-in lands where its runs look; it never sees a password, a
   code or a token.
2. **Only when someone is at the computer's page**: at once while the person uses Orkline, else the moment they come
   back to it; never on a phone, and never into a browser no one answers at night. At most once by itself for each
   time a tool needs it; *Sign in* opens it again any time.
3. **Never when a sign-in cannot help**: a key in the environment the tool takes first, another Claude Code renewing
   the sign-in; the line says what to do, as today.
4. **The work waits for it instead of failing**: what ran by itself (a task, a draft, an operation's run) is held for the
   sign-in, as a spent window holds it, and goes on by itself once the tool is signed in; at most a day.
Improvements of v1's existing mechanics (§27): the same failure, the same hold, with the tool's own sign-in. Spec 45.

## 59. A goal's trail: its party asks with its leader, its leader lays out its ideas as proposals, the desktop catches up with the phone (20 October, the owner)

Why: the owner, after the phone's round 3 and a look at the desktop. A goal is read and asks its questions, then its
Map is a flag with nothing on the way to it: its ideas come one by one from the person, or two a night (balance) from
the proposals, never more than three waiting. Its party (§56) is picked for the goal and says nothing until the work:
the goal is read by its leader alone, whatever its designer or its reviewer would have asked. And the desktop is behind
the phone: New goal is a plain button under the goal's select (the owner could not find it), three steps where the
phone has one sheet; what waits for an answer hides in a tab behind the Board while Review, not a signal (§54.1), keeps
a column of its own; the Map has no button. So:
1. **The party asks with its leader, in the one round** (spec 35 §0 stands): in balance each member's view is in the
   leader's read (no call more); in quality each member asks first, by itself, without tools, cheaply; the leader keeps
   at most three questions (five in quality), each with the head of who asks. Not every agent asking its own: up to six
   reads of the repository a goal and eighteen questions, which the person would answer with *Let the Taskmaster
   decide*; a trail is as good as the person's answers, not as the number of askers.
2. **The leader lays out the goal's trail** once its questions are answered: up to 3 · 5 · 7 ideas by the Target, in
   their order with what each waits for, as **proposals**: no spec, no draft, no money until the person takes them;
   *Take all* drafts them one at a time. A checker's check is an idea of its own only where the work it checks needs
   one. By itself only for a goal with at most two ideas; *Lay out ideas* on the goal's screen any time after.
3. **An idea the person adds joins the trail**: its draft says which of the goal's ideas not drafted yet wait for it, and
   which proposal does the same thing; nothing is removed on a model's guess.
4. **The desktop catches up**: New goal on the Map's head and in the goal's select, on one sheet; Needs you, with Review
   under it, is the right column (Board · Files on the left; below 1 024 px the phone's three tabs); the Map's one
   action. Not the phone's top bar and drawer: the desktop has the room.
5. **Measured**: the trail's ideas taken, turned down (and why) and merged within 14 days; the members' questions
   against the leader's, by how they are answered (§54.7's research); what a goal costs to read and lay out, by Target.
Improvements of v1's existing mechanics (§27): the goal's read, the night's proposals, the draft, the Map, and the
phone's look on the desktop; two keeper steps (`ask`, in quality only; `trail`), no new setting. Spec 46.

## 60. One product and its labs: Orkboard, OrkWiki and OrkWatch crystallise Orkline's buildings; a building's mechanic is the shape of its work (21 October, the owner and the PM)

Why: the owner (21 October), on the studio's positioning: a line of products on Orkline's engine, each joining a game's
mechanic to a problem of orkestrating agents. Orkboard, a card game: planning and following the work of several agents.
OrkTower, now **OrkWatch**, an idle game: mail sorted, replies drafted, events made in the calendar. OrkWiki, the links
of Mini Metro and Mini Motorways and their quality: an LLM wiki kept true, fresh, linked, placed by its rules and free
of contradictions. Orkline, Factorio: loops built and tuned for every kind of request, the person in them as little as
possible, the others in one line. The PM's review the same day: a strong thesis where the game's loop is the work's own
(as §52 and §56 found); a weak plan if it is four launches (four audiences for one person, and a skin is copied in a
weekend, as AgentCraft took its image first, §37); and parts of it against §37.1, §50.1, §55 and §56. The owner: not
four launches, one product and its labs. So:
1. **Orkline is the product; Orkboard, OrkWiki and OrkWatch are its labs.** Each crystallises one of Orkline's buildings
   on its own and checks that it is needed: the owner uses it every day, its shape and its words settle, its contract
   with the other modules is written (§50.7); then it enters Orkline ready, as that building, never a second copy (one
   engine, §50.2). A lab is not published (§50.1, for each), and the public name stays Orkline (§37.2). A lab may end in
   *not needed*: a building no one turns out to need does not enter Orkline.
2. **The labs and their buildings:**
   - **Orkboard:** the Board with its goals, Agents and Review, which are Orkline's Task board, Agent pool and Review
     gate (§50.6).
   - **OrkWiki:** the Wiki (Camp's Scroll Dump) with its librarian, its Quality checks and its Rules for AI tools
     (Orkline's `docs/design/wiki-librarian.md`, `docs/design/wiki-folders-rules.md`; here `realm/wiki.py`,
     `realm/wiki_rules.py`): a wiki that people and models write and agents read stays true, fresh, linked, placed by
     its rules and free of contradictions.
   - **OrkWatch:** External listeners (Camp's Watchtower, `TERMS` `watchtower`) with Operations' reply to an email
     (§51): mail sorted, replies saved as drafts, events proposed for the calendar; nothing sent until its template may
     go by itself (§51.4).
   - **Orkline:** the factory that lays them into loops (§50.3), the person in them less and less (item 6).
3. **The order: Orkboard, then OrkWiki; OrkWatch is decided after.** Orkboard holds first (§50.8: the owner's daily use,
   the testers). OrkWiki is the next lab: its mechanic fits its work best (item 4), it is the owner's own daily need
   (the decisions, the specs and the rules every agent reads), and the other buildings' agents read it. Whether OrkWatch
   is needed is decided after OrkWiki, from Operations' email template in use; until then it is Operations' templates
   and no lab. What weighs against it: mail is the most crowded market (the mail clients' own assistants) and the most
   private data, and Gmail's scopes for a published app are restricted and need Google's verification. §50.8 stands for
   Orkline itself: its loops, then Camp.
4. **A building's mechanic is the shape of its work** (§52, §56): a game is picked because its loop is the work's, and
   the line's games go down a ladder of how much of each move is the person's, as a template earns going by itself
   (§51.4):
   - **Orkboard, a deck-builder** (Slay the Spire, Balatro), as §56 has it: a library to pick from, a party for a goal,
     its price against its care. Not a collectible card game: nothing collected, no packs, no rarity; an agent is set
     up, never won (§56).
   - **OrkWatch, an idle tower defense** (the owner, the same day): mail comes in waves, its rules and templates are the
     towers, what got through wrongly is the damage, and a tower grows when its template goes by itself (§51.4); it
     works while the person is away, and coming back is seeing what it held (§55.3 A). Not an idle clicker: a click is
     the work it saves, and *numbers go up* rewards volume (§55.1).
   - **OrkWiki, Mini Metro:** pages are the stations, links the lines, agents' questions the passengers, a crowded
     station a contradiction or a stale page, the trains the week's budget for checks. Its calm and its colour that only
     signals are orkUI's office already (§53.5).
   - **Orkline, Factorio** as the image its first audience knows (audience.md §1), shapez as the mechanic: loops, not a
     free graph (§50.3).
5. **In a lab the mechanic is a shape, never a skin.** A lab is drawn in orkUI's office (§53) and says everything by
   what it does (§56: no cards, decks, mana or rarity in what a person reads): the mechanic is the view's shape and the
   person's choices (the Map, §52; a party, §56). The art and a game's words are Orkline Camp's skin (§50.1, §52.3). In
   every product of the line the game only reads (§50.5) and rewards results and thrift, never volume, spend or a
   person's streak (§55.1). **A mechanic earns its place by the work** (the owner, the same day): no boosters, no fear
   of missing out, nothing that only spends a person's energy, strength or attention; each mechanic is tied to what the
   product does and is of use every day, never there for its looks.
6. **"The person as little as possible" is the ladder of trust:** the person decides what goes by itself (§51.4), and
   what leaves to people stops at the gate until then (§39). §37.1's line stands, *nothing passes without you*, and the
   line is never advertised as agents round the clock (audience.md §2a.5).
7. **What sells is the engine's result; the mechanic is how it feels.** A skin is copied in a weekend; the one engine
   (the loop, the gate, the ladder of trust) is not.
8. **The PM's proposals, settled the same day (the owner):** OrkWatch is an idle tower defense (item 4); OrkWiki is
   shown, for now, over an Obsidian vault (*a graph view that does something*), still open to change. Not taken: the
   PM's line for the studio (*games taught millions to run systems that work without them*); the site says what the
   studio makes in the owner's words, *game mechanics that help you work* (item 9).
9. **The studio's site shows the line** (the owner, the same day; orkWorks/orkPage `ff9e157`). Its first screen keeps
   its look and changes its lines (*Game mechanics that help you work*; nothing a game uses to hook you); Work vs Humans
   stays as it is. *Orks can build for you* gains the studio's three rules for a game (the game is the job; nothing to
   hook you; less of you, by trust), the line as a road of Orkcraft 0.2's buildings in the order the tools come (the
   Task Fields for Orkboard, the Scroll Dump for OrkWiki, the Watchtower for OrkWatch, the Forge for Orkline), and a
   card for each: the game it plays like, its job, how the game is the job, and its install or where it stands (a tool
   not out yet offers the letter when it ships). The dates are approximate, the owner's to move: Orkboard now, OrkWiki
   and OrkWatch autumn 2026, the whole line December 2026 (moved by the owner the same day; first winter 2026, spring
   2027, summer 2027; moved again in item 10). The site names a game by its kind alone (a deck-builder, a routing
   puzzle, idle tower defense, a factory game), never another studio's title; a tool's card opens from its building on
   the line (orkPage `8081bc3`).
10. **OrkMine, the third lab** (the owner and the PM, the same day): the Mine, Orkline's research building (Orkline's
    `docs/design/mine.md`, built 8 October), on its own: deep research by every AI tool that can search the web, each on
    its own, its findings checked against the others' and marked confirmed (two tools, two sites), one source or
    disputed, the disputes the person's, the report into the Wiki's inbox. It plays like an ASCII roguelike, taking from
    NetHack only what is the work: a claim is an unidentified item until it is identified (the altar's blessed,
    uncursed, cursed are the Mine's three marks), the fog is the question not yet searched, the stairs down a
    sub-question, the food the run's budget, the heroes the tools; never death, loot, levels or a grind (item 5). ASCII
    is the one game drawn in orkUI's office without art. Its line to OrkWiki: the Mine finds and checks what is new
    outside, its links the evidence of one question; the Wiki keeps what is known, its links the knowledge's shape over
    time; the Mine's report is the Wiki's first source, Orkline's first loop. What sells: research that shows what each
    line stands on, on the subscriptions a developer already has; against it, a crowded market (the vendors' research
    modes) and the cost of several tools (its price seen before it starts, as a party's, §56.3). The order becomes
    Orkboard, OrkWiki, OrkMine, OrkWatch; on the site OrkMine is third, its stop the Mine from orkUI's `game/buildings`,
    autumn 2026, OrkWatch December 2026 and the whole line February 2027; the line's names in small letters, their ork
    in the ork's green (orkPage `e43a915`).
The line's frame and its page: no product's code and no spec. §27 and §50.8 stand (no new mechanic before the testers'
numbers); a lab starts with a spec of its own, OrkWiki's first.

## 61. The Map shows one goal: its ideas by stage, its party in lanes; results are merged on the idea; Review's column goes (21 October, the owner)

Why: the owner's notes on the trail Map (decisions §59, spec 46). It shows every goal at once and tells how far each is,
but not who is on an idea now, in which step, and what waits for the person's look: for that the person leaves for
Agents and Review, and on the desktop a column of results sits beside the Board for work that belongs to ideas. The
owner and the PM worked out a Map of one goal, drawn as an interactive mockup (Ideas and Phone Ideas; the older variants
Main, States, Lanes and Phone were turned down). So:
1. **The Map shows one goal.** Its header is the goal: title, priority, state, progress and %, *n of m ideas done*, *done
   when*, *≈$ so far*, today's merged and $; under it one line with the whole party and each member's state (*at work*,
   *next*, *tonight*, *free*, or the Needs you words in alert). The desktop picks the goal in its header; the phone's top
   bar already does.
2. **Below it, the goal's ideas in trail order.** An idea at work or waiting for the person is expanded; the rest are one
   line (the head of who is on it, the title, *<stage> · <state>*, a mark); the done ones fold into *Done (n)*, with *in
   dev · waits for main* while they are not in main.
3. **Every idea is in one of three stages**, worked out from its state and its plan, never written by hand: **Planning**
   (raw, reading, asks, ready, planning, plan, proposed), **Implementation** (a passed plan whose build tasks are not
   all merged), **Checking** (only check tasks left: their kind is a checker's tag), then Done. A word for the step, not
   a new state: the keeper's and the runner's states do not change.
4. **An expanded idea** is a stage track (the current one underlined, the past ones ✓), **lanes** of the party members
   active in the stage (the leader in Planning, the builders with tasks in Implementation, the checkers in Checking:
   at most 3 by the party's seats), **columns** that are the plan's waves, a task's card in its agent's lane and wave;
   tasks of one agent in one wave **stack** with a count. A merged task leaves the field with one animation, none
   under `prefers-reduced-motion` (§55.2). Members' questions in Planning are in the leader's lane, wearing the asker's
   head (spec 46 `by`).
5. **The idea's card**, in orkUI's double frame, on the right: title, stage, pips, *k of n tasks in dev*, ≈$ so far and
   the plan's estimate. In Planning with a plan waiting: **Start the work** (the plan's pass, autostart stays) and **Open
   the plan**. In Implementation and Checking: *Waits for your look* for that idea's results with **Merge into dev**,
   **Send back** and **Drop**, which are Review's actions, unchanged. On the phone the card is on top of the block, the
   waves rise bottom-up and one idea is expanded at a time.
6. **Yellow goes only on the agent the work stopped on**: a member who asks, the leader for a plan, a spec or a proposal,
   the agent of a failed task (its task in danger). A result waiting for a look is not a signal (§54.1): *in Review* in
   muted ink; it still counts in Needs you.
7. **The desktop's Review column goes.** Results are merged on the idea's card, one place each. The dev → main gate stays
   where §49.5 has it, in Needs you. No branch per idea and no *merge into main* on an idea: the person sees dev and
   main only (§49).
8. **The Map is no longer only a view.** This supersedes §52.1 (its one action *open*) and §54.4's single button, and
   spec 39's *Not in this spec: acting from the Map*: it has the actions of item 5, which are the Board's own commands;
   it invents no command and no setting.
9. **A check with findings** stays in Checking: its result waits for the person with its findings, *Send back* runs it
   again as round 2 (*Checking · round 2*); an idea is back in Implementation when a build task is sent back or fails.
   The runner is not changed.
10. **Measured:** the share of results merged from the Map against Review (`opened` `via: "map"`), the Map's opens per day
    (§52.4).
An improvement of v1's existing mechanics (§27) and a view's rewrite: the owner's call, before the testers' numbers, as
§55 and §59. Spec 48.

## 62. One window: the goals as tabs, Planning over the leader, the party at the foot, what waits for you along the bottom; the gate is built (21 October, the owner and the PM)

Why: the owner's call to simplify the desktop radically, to one window (and the phone to one screen with no tabs). After
spec 48 the person still moves between three regions (the Board's column with Needs you, the Map with its tab strip,
Agents) to answer one question asked all day: *where is my goal, and what waits for me*. The owner and the PM drew it as
an interactive mockup (Design artifact *Orkboard: one window*: B, the desktop, and D, the phone; A, waves as columns,
was turned down; C lists what was taken from the game). So:
1. **One window.** The goals are tabs with their progress and their stops' count; under the tab, the leader heads
   the left column over its Planning; the party stands along the top of the field, each member's open tasks running
   down from it, the top row lit and the rows below muted (what a member is on is what is bright; item 9); the
   results that wait for a look are a column on the right; what waits for the person lies along the bottom with its
   quick answers; anything opened slides in as a drawer from the right, its tabs kept. The Agents pane, the Board's column and Needs you's list go as
   regions (the pool by agent and the files open in the drawer). The phone is the same on one column with no tab bar: a
   stage switch (Planning · Implementation · Checking) shows one stage's columns at a time, and a tap pops a stop out
   of the bottom row.
2. **The shape of a collectible card game, the words of the Board.** What a person reads there at a glance is taken
   where it means the same: a price before a move (a gem), two measured numbers on a member, the things to answer as a
   hand at the bottom with their answers on them, the end of a turn as the gate, what is left of a tool as diamonds with
   its reserve hatched, the day as a strip of marks, a peek at a member's whole face on hover, what waits for a task lit
   on hover. Taken with care: the checks stay in the party; a task appears with one motion. Not taken: packs, golden
   members, quests and streaks, a timer, emotes and sounds, dragging to play, a forecast of *done when* (no data). It is
   also the product's picture for marketing. The interface never says card, deck, hand, mana, hero or boss (§56).
3. **A member says two numbers and its kit**: its runs and redos this week (a checker's checks and catches, the
   leader's plans and plans made again) and its average price for a run (an estimate, by its level, until three have
   finished), beside its head; the head wears its harness's mark, its level's chevrons (Orkline's, now in orkUI) and
   its state as a sign (✗ a failure, ! a stop, ↻ at work). No octagon frame: the head is the picture (§53), small; the
   member is a small row, three of them across a phone. Showing one member's work reorders nothing: the others' tasks leave the field and its own lie across it.
4. **The gate is built** (§49.5's item 5, its one press): *Merge dev into main*, beside the party, with its count of
   ideas in dev not in main, its screen in the drawer, a fast-forward or a merge commit made in a worktree of its own, a
   conflict refused with main as it was. Its report (the full suite, the browser tests, `checks.toml`) and *Revert* stay
   §49.5's next round.
5. **Today's events** become a command and the strip on the left (the phone's *Today* sheet); the reserve is in the
   snapshot so the limits can show it.
6. **Quiet by default** (the owner, on the mockup): the goal's numbers are one line in the ideas bar, its details
   behind *About this goal*; Planning's rows are plain lines with a mark only for a stop; the alert colour stays where
   §61.6 puts it.
7. **Measured:** the share of answers given from the bottom row (`via: "hand"`) against the drawer and Needs you of
   before; opens from the strip (`via: "today"`) and from a member (`via: "party"`); the gate's presses a week.
8. **Motion says what changed, never decorates**: a task that leaves fades where it stands and its column settles
   into the gap, a task whose state moves it slides to its place, nothing moves under the pointer or the focus, a merge
   lights its member's number once; nothing flies, nothing bounces, none for what changed while the page was hidden.
9. **The party on top, the work running down to you** (the owner, on the flipped mockup): the members stand along the
   top of the field, each one's tasks queue down from it, what waits for the person lies along the bottom. You deal the
   work (a plan started, a question answered, a new idea), the party clears it (the front task is the one a member is
   on, a merged one fades and the queue steps up), and what it brings comes down to you. Read top-down, as the eye
   does: what is happening now first. The game's look stays in the hand, the prices, the gate and the diamonds; the
   words stay plain (§56).
A new face over v1's mechanics and the gate decided in §49.5: the owner's call, before the testers' numbers, as §55,
§59 and §61. Spec 49.

## 63. Parties and goals: what was a goal is a party, what was an idea is a goal; a goal raises its flag in main; a party's goals are decks of one element (21 October, the owner)

Why: the owner, on the one window's mockup. The goal on a tab is a container the person never really chooses: what they
pick every day is **who works on it** (a leader, builders and checkers, the checks they hold the work to, what it
costs), while a goal's metrics, its *done when* and its verdict are written for them by the keeper and steer nothing;
and an idea, the thing that does have an end, has none the Board celebrates. A product team works the same way: a team
for the product, one for the platform, one for the whole flow, each with its own line of goals. So:
1. **The words move one step**: what the code calls a goal (a track, `pages/tracks/`) is a **party** in what a person
   reads; what the code calls an idea is a **goal**; a task stays a task. The code, the files, the commands, the keys,
   the events and the classes keep their names (CLAUDE.md), so Orkline reads the same Board. This reverses §54.8
   (*a goal stays a goal*) and §47.2's *no idea without a goal* (now: no goal without a party).
2. **A party has no end**: a team you picked and what it is for (its brief), its checks, its price; no metrics, no *done
   when*, no progress, no verdict: only a count, its done goals of all its goals (*5/12*). Nothing accepts it by itself any more; a party's reading no longer asks metrics.
   Parties are the tabs; a new one is one of yours (§56.6) or made from the library.
3. **A goal raises its flag when the gate takes it into main** (the person's press, §62.4), or when it is done where
   there is no gate. Done in dev, it waits for main. The flags of its goals are a party's record; a party's old flag
   (a verdict met, §55.3 B) stays as history. No backfill.
4. **A goal is a deck of one element**: a pixel symbol and a muted colour (orkUI's, five: meadow, ice, dust, void,
   lava) on every card of it, given once, the least used among its party's open goals. Never named in the interface.
5. **A member's work lies in stacks by phase**: its tasks of one goal at one phase (now, next, later: against the
   goal's current wave) are one stack of 5:7 cards that spreads on a press; what a task waits for is an arrow on
   hover (the desktop) or a line on the card (the phone): a card that does not go up shows why.
6. **The goals list filters the board**: one press shows only that goal's cards, more add to it, *Show all* clears;
   a goal stays in the list until its flag.
7. **Quiet at the top**: the party is one line, its goals one line; the details behind a press (*About this party*,
   the goals' sheet). The phone's project is a sheet of its own from the top bar.
8. **A tap is never lost to a redraw** (the phone): a redraw waits while a pointer is down, and the holds redraw only
   what they held back; the tests' retries go.
9. **New goal draws a blank card**: a face-down pile on the desktop, the FAB's dial on the phone; the card turns over
   and is filled in.
10. **Every symbol the window draws is orkUI's** (the owner): the elements and eight signs (done, failed, at work,
   tonight, a stop, a flag, what a task waits for and what waits for it) are pixel symbols of the look, drawn on a 7 × 7
   grid; no Unicode symbol stands in for one.
11. **The parties are a switch in the top bar, not a row of tabs** (the owner): a project has a few, three at most as a
   rule, and they change seldom; the switch says where you are (*project › party*) and the board gains the tab row's
   height. The phone keeps its chips.
12. **On the phone the party is in the top bar too** (the owner): one *where* button, *project › party ⌄*, with a count of
   what waits in the other parties; its sheet lists the parties, a new one and the other projects. The chips row goes.
13. **A card keeps its size; the members scroll instead** (the owner): a member's column is as wide as its card, and
   three or more members are a sideways strip with the third peeking; the cards never shrink to fit (this replaces
   spec 49's *no sideways scroll with three*).
14. **No Today button on the phone's top bar** (the owner): *Today* is an item of the menu; the bar holds the menu, where
   you are and the limits.
15. **One row for the goals and the gate on the phone** (the owner): the party's bar goes; *k at work* and *j ask you*
   were the stage switch's counts said twice; the party's details are behind the Goals sheet's *About … ›*.
16. **The phone's FAB is the desktop's New goal deck** (the owner): a small face-down deck that draws a blank goal; the
   dial goes (a new party is in the *where* sheet, a member in About this party).
A new face and new words over v1's mechanics, two small additions to the host (a goal's flag, its element), and the
end of a model call (a party's acceptance): the owner's call, before the testers' numbers, as §55, §59, §61 and §62.
Mockups E and F of *Orkboard: one window*. Spec 50.

## 64. Pick one: a task may make a few variants of one kind (pictures, sounds, clips, texts) and the person picks one with a note (21 October, the owner)

Why: the owner. Some work is chosen by eye or by ear (an artist's logos, an icon, a jingle, a clip, a tagline), not
reviewed as a change; one variant a round makes the person wait a round for each look. So:
1. **A task may end with variants instead of a change**: two to six of one kind, which the plan asks for when the goal's
   spec asks to choose by eye or by ear; never code. The task leaves them as files and a manifest the runner reads and
   never commits (as a check's findings, §56.1); they live in the goal's state folder, not in the repository.
2. **The kinds are one mechanism**: pictures, sounds, clips and texts are files with a media type sniffed from their
   bytes, limits by kind, served by one signed route (Range for sound and video, a sandbox for anything that could run);
   the faces draw each kind as a tile. A new kind is a new tile and a line in `KINDS`, not a new flow.
3. **The person picks one, with a note, or none**: *Take B* commits the one picked to where the plan said and the work
   goes on (the note told to the tasks after); *None of them* asks for a note and runs the task again. It is a stop of the
   bottom row (*Pick one*), answered on the card or with a note in the drawer, on the phone in its raised card or on its
   own screen.
4. **Measured**: picks a week, taken at the first round or asked again, the time to pick, where, with a note or not.
A new end for a task over v1's runner and the faces of §62–§63, the owner's call. Spec 51.

## 65. The leader deals the goal types; a type says who the party needs; the stages wear the party's faces; a stop is counted only where it cannot be seen; the party switch is a deck (22 October, the owner)

Why: the owner, on the one window as built. A new goal is a blank card, so the person writes from nothing what they
already know (it is a logo, a bug, a landing page), and the party works it with whoever is in it: a logo asked of a party
with no Artist goes to the Grunt. The phone's stage switch says *Planning 6 · Implementation 7 · Checking 3* in the
alert colour, read as *seven wait for you* when one does; and the tabs were always by band (the leader's, the builders',
the checkers'), not phases in order. So:
1. **The stages wear the party's faces**: the phone's switch shows the heads of each band over its word (*Planning*,
   *Implementation*, *Checking*: the words stay, a head never stands alone) and **no number**: a sign (✗ a failure, else
   ! a stop) on the faces of the band it comes from.
2. **A stop is counted only where it cannot be seen**: the bottom row is the count of the party shown; where a stop
   comes from has its sign, once (no alert edge, no alert words beside it); the only count of stops is that of the
   project's other parties, on the party switch. A failure keeps its danger edge.
3. **The party switch is a deck** (reverses §63.11 and the party half of §63.12): on the desktop over the leader at the
   left column's top, a press dealing the parties as cards; on the phone at the end of the stage switch, its sheet the
   parties. The top bar keeps the project; the phone's goals bar says the party.
4. **The leader deals the goal types**: each leader of the library has a few (a designer *New screen*, *New icon*, *New
   logo*, *New feature*; an architect *New feature*, *Fix a bug*, *Restructure*), the Taskmaster a general set (*New
   feature*, *Fix a bug*, *Clean up*), and a blank goal is always the last. A type is told by **its sign** (orkUI's),
   never a colour: colour is the goal's element and the signals. A type brings the few lines only the person can give,
   Refs where looks matter, the lens it opens first, and a line for the leader's draft and plan.
5. **A type says what kinds of work the party needs**; when no one of the party does one, the form says who would: a
   free seat, it joins; a full band, **a swap** (the owner: a swap, not a guest for one goal); a member with work open
   never leaves this way. A goal kept for tonight never changes the party.
6. **A plan that gives work to no one of the party says so on its stop**: *No one in the party does pixel art: Artist
   would*, with *Add and start* when a seat is free, else *Edit the party*; *Start without* keeps today's way.
7. **Members are not added in the stage switch**: the tabs show who works; the team is changed where the need shows
   (the type's form, a plan's stop, About this party) and, for a band with no one, from its empty line.
8. **Nothing flies** (§62.8 stays): the owner turned down an answered stop flying onto, or lighting, the task it answered;
   it would distract.
9. **Measured**: the share of new goals with a type, by leader and type; the asks answered; the join line kept, unticked
   or swapped; a plan's line and what was pressed; whether a typed goal's plan passes at its first round and raises its
   flag sooner.
A new start for a goal and a new place for the party switch and the counts over v1's mechanics, the owner's call before
the testers' numbers, as §62–§64. Spec 52.

## 66. The phone, simpler: the deck beside the party's name, the faces are the members, New goal at once with the party first, a goal's two marks on every card (22 October, the owner)

Why: the owner, on the phone as spec 52 built it: four bands before the first card, the party's faces twice (on the
stage switch and in the members' strip under it), New goal behind two motions (≈ 1.2 s) and a form longer than the
screen that names the party twice. So:
1. **The party's deck stands at the goals bar's left**, beside the party's name and its *k of n goals done* (moves the
   phone's half of §65.3 from the stage switch's end); its count and its sheet are §65's.
2. **The faces are the members**: in the stage shown, a tap on a face shows only that member's tasks, again everyone;
   a stage's sign (✗, else !) stands on the face it comes from (refines §65.1). The members' strip goes: over each
   column its member's name; a member's runs and price stay in its solo.
3. **New goal opens at once**: the form slides up (180 ms; none under reduced motion); the lift, the deal and the turn
   of the create button go on the phone. The desktop's New goal is unchanged for now.
4. **The party first**: the form starts with the party (its leader's head, a list of the project's parties), then the
   priority, then the goal type (the party's leader's types, *No type* last), then **one field for the goal** (its
   first line its title), then the type's fields. A type belongs to its party's leader, so a change of party deals its
   types again. The form says no element, names the party once, has no lens switch for a typed goal, and *Low* says
   *Keep for tonight*.
5. **A goal's two marks, each in its place**: its element (which goal: shape and colour) at a card's corner; its type's
   sign (what kind: muted ink) before the goal's name wherever the name is written, task cards too (reverses spec 52
   §4.6's *no other place*). A type is still never a colour (§65.4).
6. **Nothing flies** (§62.8 stays).
The owner's call on the phone as built, before the testers' numbers, as §62–§65. Spec 53.

## 67. One hand: every stop of the project in it, the most urgent in the middle, no count anywhere; every stop has a way out (22 October, the owner)

Why: the owner, on the window as specs 52–53 built it. An Artist asked for a reference picture as a plan's to-do; a file
to-do was done only with a file, so the goal stood still. And what waits was split: the party shown's in the hand, the
others' as a number on the party's deck. So:
1. **One hand for the project**: every party's stops and Operations' lie in it; a stop of another party says its party
   and opens there. What waits for the person is their inbox, not a party's.
2. **The most urgent in the middle**: red (a failure) first, then what holds work back, then what does not, then the
   results; the oldest first in each. The keys and a screen reader read them in that order.
3. **No count of stops anywhere** (reverses §65.2's one count and the count of §65.3's deck): nothing waits out of
   sight. The parties' list marks a party with a stop by a dot (red when one failed).
4. **Every stop has a way out that needs nothing from the person**: a question *Let <asker> decide*; a file to-do
   *Describe it instead* or *Go without it*; a choice *Let <leader> choose*; any other to-do *Go without it* (its tasks
   run without it and say so if they cannot). How often each is pressed, by agent and kind, says who asks too much.
5. On the phone, **the Target is one switch**, and **Agents is reached from a member** (*Edit* on its card); the menu
   keeps Stop all, Today and Spend at its head.
The owner's call on the window as built, before the testers' numbers, as §62–§66. Spec 54.

## 68. The type top right: a card's top right holds its goal's type, in its goal's colour; the state's sign leaves the top (22 October, the owner)

Why: the owner, on the screenshots of spec 54: *where did the task type signs go on the cards? I see only the element;
maybe remove the exclamation mark or the error sign at the right of a card and put the type there, the type and the
element in one colour?* The sign was not seen because a goal made before spec 52 (and every goal of the test scene) has no
type, and where it is drawn (spec 53 §3) it is 14 × 14 in muted ink before the goal's short name, easily missed, and it
truncates the name. So:
1. **A card's top right holds its goal's type's sign**, 14 × 14, **in its goal's element's colour** (faint while the
   element is drawn dim, muted for a goal with no element). The top row reads as the goal's mark: left *which goal*, right
   *what kind of work*. Two goals of one type in a party still differ by colour. A goal with no type: the top right is
   empty.
2. **The state's sign leaves the card's top** (↻ at work, ✗ failed, the clock tonight, ! asks you / asks you to pick): the
   foot's words (*working 28 h*, *failed*, *tonight*, *asks you to pick*) and the card's edge (danger for a failure,
   alert for a stop, dashed for what waits) say it already. Edges, foot, label and tooltip stay.
3. **The goal line is the goal's short name alone**, its full width back; a Planning goal's card keeps the type's name
   (*Fix a bug*) or *Goal* (phone) / *Planning* (desktop), without a sign in the line.
4. **Everywhere a type's sign is drawn it wears its goal's colour**, the goals' lists too (one rule); the stops along the
   bottom (the element alone), the top bars, the stack's ghost flash and New goal's form are unchanged.
5. Reverses spec 53 §3's place of the type (before the goal's name, muted) and spec 50 §3.4's mark top right. A type is
   still never a colour of its own (§65.4): it takes its goal's. No orkUI change; the interface never names an element.
The owner's call on the cards as built, before the testers' numbers, as §62–§67. Spec 55.

## 69. Parties of mixed crafts first; the leader sets the stages and their seats; the goal types come from the team, not the leader (22 October, the owner)

Why: the owner, going through the library's parties and their goal types: *the parties used most will be mixed ones, a
game's (its leader a game designer) or a mobile app's (a product leader, and besides the code ASO and an Artist for the
pictures), more often than a party of one craft.* Spec 52 gave the goal types to the leader (§65.4), so a mobile app's
party led by the Product manager dealt *Solve a pain*, *Try an experiment*, *Write the launch* and never a store listing,
whoever was in it; and every party had the same seats (one leader, three builders, two checkers), so a game's party
(code, art, levels, sound) did not fit. So:
1. **The library gives parties of mixed crafts, first**: *Game*, *Mobile app*, *Website*, then the parties of one craft
   as today. New agents for them: a Game designer (an elf, a leader), a Level designer and a Sound designer (elves), a
   Playtester (an elf, a checker), ASO (a gnome).
2. **The leader sets the stages**: their words and how many seats each has, one leader and five more at most (the party
   stays six). A Game designer's: *Concept* (it), *Build* (four), *Playtest* (one). A stage is still one of the three
   bands (plans, builds, checks), so who plans, who takes a task by its kind and whose check joins a goal stay as they are.
   The leaders of today keep *Planning*, *Implementation*, *Checking* and three and two seats.
3. **The goal types come from the team** (reverses §65.4's dealer): one catalog of types, each with the kinds of work it
   needs; a party offers the types its members (the leader with them) can do, **and few others**: one it misses one agent
   for only when the leader itself does another part of it (§65.5's *needs:*, its join or swap), never work beside the
   leader's (*better fewer goals than a distracted person; neighbouring goals are another party's*); the general types
   (*New feature*, *Fix a bug*, *Clean up*) only when someone of the party writes code. A type that stands in for a
   general one (a designer's *New feature*) hides it when the party can do it. A type is still told by its sign (§65.4).
   The Product manager takes screens too (an app's leader writes its flows), so its parties are offered *New screen*
   with the Design system designer to join.
4. A goal keeps its type by the catalog's id; a type kept before by its leader (`architect/feature`) is read as the one
   the catalog gives it.
5. **Measured**: the share of new parties from each of the library's, mixed and of one craft; the types offered, picked and
   joined for, by party; whether a party with four builders swaps less than one with three.
Steps of a type's own (a skeleton the plan must keep) wait for the numbers: first see where a typed goal's plans differ.
The owner's call on the library before the testers' numbers, as §62–§68. Spec 56.
