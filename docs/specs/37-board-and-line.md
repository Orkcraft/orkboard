# Spec 37 — Orkboard and Orkline, stage 1: the boundary, Orkboard on its own, the gate on any repository, the project as in an IDE

The owner, 18 October (decisions §50). After specs 35 and 36 the four windows (the Board with its goals, the
preview, Agents, Review) are a whole tool, and the owner wants it every day, at work and at home, on other projects:
**Orkboard**. Orkline goes on from what that use shows, on the same modules. Today the four windows live inside the
town: `focus = "board"` only changes what is drawn. The host still builds the whole town (`gui/host.py:47-170`), the
Board reaches into it at run time (its Wiki among the town's buildings, the limits from the Town Hall's worker, the
budget from the Treasury), nine imports pull the town's modules in, the desktop and phone pages load the camp's
scripts, and the gate passes a result when it finds no test file to run. This spec draws the line, cuts it, starts
Orkboard on its own, lets the gate test another repository, and opens a project as an IDE does (§8). Nothing moves
to another repository here (stage 2, §7). **Builds:** Claude (A, C, D2, D3 on the warrior tier; B and D1 on the
elder tier) · **Review:** full · P1.

**When.** A now: it touches no file of specs 35 or 36. C after 35 and 36 are merged: it is what Orkboard needs
first at work. B after C (both change `realm/jobs.py`). gate-kinds (decisions §49.4–7) comes after C and puts its
`[[check]]` rows into C's file; B and gate-kinds are not built at the same time (both change `gui/ideas.py`). D
(§8, its own three branches) after B.

Four parts, one branch each (D in three, in §8); **this file is the contract** (names, data, commands); the rest is the builder's
choice inside its files. Wording: CLAUDE.md. **Change nothing outside these files.**

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. The boundary** | `spec/37-boundary` | §1, §2 | new `orkcraft/layers.py`, `tests/test_architecture.py` (new tests only), `CLAUDE.md` ("Where code goes": one bullet, §2) |
| **C. The gate on any repository** | `spec/37-gate` | §5 | new `realm/gate_config.py`, `realm/idea_git.py`, `core/idea_runner.py` and `core/idea_review.py` (*no tests ran* never lands by itself), `realm/forge.py` and `realm/jobs.py` (`test_argv` imported from `gate_config`, one line each), new `orkcraft.toml` (this repository's), `gui/ideas_goals.py` (`ideas.doc` reads no secret), `orkcraft/layers.py` (`hooks.warder`, `gui.markdown` join `BOARD`), `tests/test_architecture.py` (only `KNOWN` loses `jobs → forge`), `gui/static/js/shell/review.js` and `gui/static/pwa/shell-review.js` (the tests' line only), `pwa/sw.js` (cache version) with `tests/test_pwa.py`'s pinned version |
| **B. Orkboard on its own** | `spec/37-alone` | §3, §4 | new `realm/tool_run.py`, `realm/jobs.py`, `realm/road_agents.py`, `realm/roads.py`, `realm/harnesses.py`, `realm/tiers.py`, `realm/looks.py`, `realm/builders.py`, `realm/worktrees.py` and a new line module for its town part, `settings.py` (`ideas.wiki`, `MachineSettings` read cached), new `core/board_limits.py`, `core/treasury.py`, `gui/ideas.py`, `gui/ideas_limits.py`, new `gui/board_host.py`, `gui/host.py`, `gui/state.py`, `gui/onboarding.py`, `gui/static/js/onboarding.js`, `gui/launch.py`, `gui/server.py`, `gui/pwa.py`, `gui/phone_http.py`, `gui/mobile.py`, `gui/phones.py`, `cli.py`, `pyproject.toml` (`[project.scripts]`), new `gui/static/board.js`, `gui/static/index.html` only if the entry needs it, new `gui/static/pwa/board-app.js`, `gui/static/pwa/index.html`, `pwa/sw.js`, `orkcraft/layers.py` (`SPLIT` emptied), `tests/test_architecture.py` (only `KNOWN` emptied, and §4's new test), new `<name>_town.py` modules beside the split ones (§4) |

## 0. The words
- **Orkboard:** the engine and its base modules (goals, ideas and their specs, agents, review; the Wiki under them)
  in one fixed loop, drawn as the v1 panes in Office's look, the phone included. The owner's lab, not published: the
  interface says *Orkline* as today (§37.2 of the decisions). Nothing a person reads changes in this spec, but the
  command `orkcraft board` (§4).
- **The line:** every module that is not Orkboard's: the town, its buildings and workers, the road engine, the camp,
  the missions, the game layer.
- An **Orkboard module** imports only Orkboard modules, the standard library and the third-party packages
  `pyproject.toml` lists. Orkline imports Orkboard, never the other way round (decisions §50.2).

## 1. The list: `orkcraft/layers.py` (A)
- `BOARD`: a tuple of module patterns (`fnmatch` on dotted names), today:

```python
BOARD = (
    # the engine: the keeper, the runner, review, the git of a task, the pages, the claims
    "orkcraft", "orkcraft.core", "orkcraft.core.idea_*", "orkcraft.realm.idea_*", "orkcraft.realm.ideas",
    "orkcraft.realm.claims",
    # running a tool: harnesses, models, tiers, roles, plans, limits, prices, sessions, the log of calls
    "orkcraft.realm.harnesses", "orkcraft.realm.jobs", "orkcraft.realm.model_families", "orkcraft.realm.tiers",
    "orkcraft.realm.roles", "orkcraft.realm.plans", "orkcraft.realm.status", "orkcraft.realm.halt",
    "orkcraft.realm.tool_errors", "orkcraft.realm.call_log", "orkcraft.realm.worktrees", "orkcraft.realm.event_log",
    "orkcraft.realm.lexicon", "orkcraft.realm.analytics", "orkcraft.realm.day_log",
    "orkcraft.realm.wiki", "orkcraft.realm.shelves",
    "orkcraft.quota", "orkcraft.quota.*", "orkcraft.sources", "orkcraft.sources.pricing",
    "orkcraft.sources.telemetry", "orkcraft.sources.sessions", "orkcraft.sources.transcripts",
    "orkcraft.sources.limits", "orkcraft.hooks", "orkcraft.hooks.pi_extension", "orkcraft.tools",
    "orkcraft.settings", "orkcraft.env", "orkcraft.schedule", "orkcraft.autonomy", "orkcraft.config",
    "orkcraft.design", "orkcraft.design.*",
    # the face: the Board's commands, the phone's link
    "orkcraft.gui", "orkcraft.gui.ideas*", "orkcraft.gui.pairing", "orkcraft.gui.phone_http",
    "orkcraft.gui.phone_tls", "orkcraft.gui.tailnet",
)
```

  Measured 18 October: 62 modules, about 12 800 lines on `main`; 68 and 15 100 with specs 35 and 36 merged.
- `SPLIT`: the modules that hold both today; B splits each (§4) and empties the tuple: `orkcraft.cli`,
  `orkcraft.gui.host`, `orkcraft.gui.state`, `orkcraft.gui.server`, `orkcraft.gui.launch`, `orkcraft.gui.mobile`,
  `orkcraft.gui.pwa`, `orkcraft.gui.phones`, `orkcraft.gui.onboarding`, `orkcraft.core.treasury`.
- `python -m orkcraft.layers` prints the report: Orkboard's modules and lines, `SPLIT`, and every edge out of
  `BOARD` with its file and line. The PM reads it after each merge.
- A module joins `BOARD` when all its imports are Orkboard's already (as `day_log`, `tools` and `shelves` did).

## 2. The rule and its test (A)
- `tests/test_architecture.py` gains, beside the existing tests and in their way (every import counts, a lazy one
  inside a function too):
  - **`test_orkboard_imports_only_orkboard`:** for every module matching `BOARD`, each `orkcraft` import resolves
    to a module matching `BOARD`, or is listed in `KNOWN`. Names are resolved as `_starts_and_names` already does
    (`from orkcraft.realm import catalog` is `orkcraft.realm.catalog`, not `orkcraft.realm`), relative imports too. A
    new edge fails, saying the file, the line and both modules, and *cut it, or add the module to BOARD when all its
    own imports are Orkboard's*.
  - **`test_known_edges_still_exist`:** every `KNOWN` edge is still in the code; one that is gone fails with *remove
    it from KNOWN*. So the list only shrinks.
  - **`test_every_board_pattern_matches`:** each `BOARD` and `SPLIT` pattern matches at least one module.
- `KNOWN` (in the test, `importer → imported`, no line numbers), today's nine, the same after 35 and 36 (checked on a
  trial merge, 18 October):

| importer | imported | why it is there | cut by |
|---|---|---|---|
| `gui.ideas` | `realm.catalog` | finds the Board's Wiki among the town's buildings (`catalog.migrate`) | B, §3.5 |
| `gui.phone_http` | `gui.pwa` | the phone's files, the camp's with the shell's | B, §4 |
| `realm.harnesses` | `realm.builders` | `tier_choices()` reads the machine's `tier_models` through `builders._machine()` | B, §3.3 |
| `realm.tiers` | `realm.builders` | `builders.main_tool()` | B, §3.3 |
| `realm.jobs` | `realm.roads` | `resolve`, `harness_stdin`, `failure`, `result_of`, `codex_thread_usage` (defined in `road_agents`, re-exported) | B, §3.1 |
| `realm.jobs` | `realm.road_agents` | `run_proc` | B, §3.1 |
| `realm.jobs` | `realm.forge` | `test_argv` | C, §5 |
| `realm.worktrees` | `scroll` | `link`, `unlink`, `cwd_for` (an orkspace's worktree; the Board never calls them) | B, §3.4 |
| `realm.worktrees` | `realm.projects` | `root_of` | B, §3.4 |

- `CLAUDE.md` "Where code goes" gains one bullet: *Orkboard and Orkline (decisions §50): Orkboard's modules
  (`orkcraft/layers.py` `BOARD`) never import the line's; `tests/test_architecture.py` checks it, and its `KNOWN`
  edges only shrink. New engine code (the Board, a tool's run, the gate) goes into an Orkboard module.*

## 3. The edges cut (B)
Each move keeps the old name working where the line uses it (a re-export in the old module), so no line module
changes more than an import.
1. **A tool's run** (`realm/jobs.py` → `roads`, `road_agents`): `resolve`, `harness_stdin`, `failure`, `result_of`,
   `codex_thread_usage` and `run_proc` move to a new Orkboard module, `realm/tool_run.py`; `road_agents` and `roads`
   import them from there.
2. **The test command** (`realm/jobs.py` → `forge`): done by C (§5).
3. **The machine's tools and tiers** (`harnesses` and `tiers` → `builders`): `settings` gains a cached read of the
   machine's settings (by the file's mtime, as `builders._machine()` does today); `harnesses.tier_choices()`,
   `tiers` and `looks` read `tier_models` and the main tool there. `builders._machine()` and `builders.main_tool()`
   stay as wrappers for the line.
4. **The worktrees** (`worktrees` → `scroll`, `projects`): `link`, `unlink`, `cwd_for` and whatever reads an orkspace
   move to a line module beside it (`realm/orkspace_trees.py`); `worktrees` keeps the git part the Board and the
   pool share.
5. **The Board's Wiki** (`gui/ideas.py` → `catalog`, and `town.custom_specs`, `town.scroll`, `town.worker` at run
   time): Orkboard's Wiki is `ideas.wiki` (a folder in the repository; default `""`) else `llm-wiki/general/`
   (`wiki.root_of(repo, None, "general")`, as today when the camp has no Wiki). The town's lookup (the Task board's
   `wiki`, else the camp's first Wiki) moves to the line's host, which hands it to the Board as `wiki_of` (§4). The
   pages found do not change for a town that has a Wiki.

## 4. Orkboard on its own (B)
- **What the Board needs from its host** is one small object, `gui/board_host.py` `BoardHost`, built without the
  town: `repo_root`, `machine` (the machine's settings), `demo`, `bus` (`subscribe`, `publish`), `toast`, `call`
  (to the host's thread), `budget_ok`, `limits`, `day_logs`, `wiki_of` (`None` in Orkboard: §3.5). `gui/ideas.py`
  and its mixins use only these. Today they reach thirteen names on `host.town` and `host`: `repo_root`, `machine`,
  `demo`, `toast`, `publish`, `call`, `bus`, `budget_ok`, `worker`, `scroll`, `custom_specs` (the last three only to
  find the Wiki), `limits`, `day_logs`.
- **The limits** (today the Town Hall worker reads them every 10 minutes, `host.limits()`): a new Orkboard service,
  `core/board_limits.py`, reads them on the same clock with the same `quota` modules; the Town Hall's worker uses it
  in Orkline. **The day's budget** (`core/treasury.py`, built on the town): its check on the day's spend against the
  cap takes no town; Treasury keeps it for the line.
- **Orkline's host** (`gui/host.py`) builds the town as today and gives the Board a `BoardHost` made from it, with
  `wiki_of` set. Nothing changes for `focus = ""` or `focus = "board"` inside Orkline.
- **The split modules.** Each module of `SPLIT` either becomes Orkboard's or keeps its Orkboard part and moves the
  town's to a line module beside it, named `<name>_town.py` (`gui/state_town.py`, `gui/pwa_town.py`, …). After B,
  `SPLIT` and `KNOWN` are empty.
- **The command.** `orkcraft board` (a `cli.py` subcommand) and the script `orkboard` (`pyproject.toml`) start
  Orkboard: `BoardHost` and the server with the Board's commands (`ideas.*`), Stop all (`halt`), pairing a phone
  (`phones.*`, `phones.tailnet`), updates, `link.open`, `crash.window`, and the onboarding's first screen (trust, the
  AI tools found): no class, no Mission 1, no town raised behind it (today `js/onboarding.js:545-559` raises one).
  The folder is the one `orkcraft board` was started in (`config.find_project_root`, as `orkcraft gui` does); D
  (§8) adds opening another. The same machine settings and state folder as Orkline's: switching between the two loses nothing.
- **The snapshot** in Orkboard holds only what the shell reads: `focus` (`"board"`), `onboarding`, `ideas_rev`,
  `needs_you`, `idea_states`, `review_count`, `review_results`, `limits`, `hud` with `show_gold`, `gold`, `lumber`
  only (the top bar's spend), `repo`, `update`.
- **The pages.** The desktop page in Orkboard loads `static/board.js`: the shell, the onboarding's first screen
  and the toasts, and no camp module (`app.js:4-35` imports them all today). The phone loads
  `pwa/board-app.js`: `board.js`, `util.js` and the `shell-*.js`; no `precacheCamp`, no camp file in its cache
  (`sw.js`'s list for Orkboard is the shell's; the cache version goes up). In Orkline, `app.js` and `pwa/app.js` keep
  drawing the shell when `focus = "board"`, as today.

## 5. The gate on any repository (C)
- **The file:** `orkcraft.toml` at the repository's root, **tracked** (`.orkcraft/` is git-ignored and the machine's
  own, so a task's worktree and another machine would never see a file there). This replaces the path of decisions
  §49.7: gate-kinds' `[[check]]` rows go into the same file. Read by `realm/gate_config.py` `read(repo_root)` with
  `tomllib`; an unknown key is ignored, a bad file is said plainly on the Review card and the gate runs as with no
  file.
- **`[gate]`:**

```toml
[gate]
run = "npm test -- {files}"        # the command; {files} = always + the touched files' tests, quoted; without {files}, run as is
always = ["tests/test_architecture.py"]   # always among {files}
map = ["tests/test_{stem}.py"]     # a touched file → its tests: {stem}, {name}, {dir}; only those that exist
timeout_min = 20
```

- **No file, or no `[gate]`:** today's gate exactly (pytest on the critical tests that exist and
  `tests/test_<stem>.py`), so a repository that worked keeps working. This repository gets its `orkcraft.toml` with
  today's three critical tests in `always`; `idea_git.CRITICAL_TESTS` stays only as that default.
- **Nothing ran is never green.** Today `IdeaGit.gate_run` returns `(True, "no test files to run")` when no test file
  maps (`realm/idea_git.py:160-161`): on a repository without pytest every result passes untested, and with §49.4 it
  would land in dev by itself. From now on the gate answers `ran: false`; the task goes to `review` with *no tests
  ran*; it never lands by itself; its Review card says so (spec 33 §2's words), and **Merge** stays the person's
  press.
- **What it shows:** a pytest summary line gives the counts as today; any other command: its exit code decides, the
  counts are `null`, the card says *passed (exit 0)* or *failed (exit 1)* with the output's tail. Today the card's
  line (`review.js` `testsLine`, `shell-review.js`) adds `passed + failed` and reads `passed === 0` as *no tests ran*:
  it reads `ran` first (*no tests ran*), then `null` counts (the exit code's words), then the counts as today. The run goes
  through `test_argv` (words, or `sh -c` when it needs a shell), which moves from `realm/forge.py` to
  `realm/gate_config.py`; `forge` and `jobs` import it from there (`KNOWN` loses `jobs → forge`).
- `plan.json` task `tests` gains `ran` (bool) and `command` (the command as run); old tasks read `ran: true`.
- **`ideas.doc` reads no secret** (found 18 October, closed here because C comes first). Today it reads any path
  under the repository, `.env`, `.orkcraft/secrets.json` and `.git/config` included, on the desktop and on the phone
  (`gui/ideas_goals.py:83-97`; its tests check only `../`, `/etc/passwd`, a missing file and a URL), and since spec 35
  §2 the keeper writes a goal's links itself. From C on, `ideas.doc` refuses, in words (*may hold secrets: open it in
  your own editor*), what `hooks/warder.py` `is_secret` names (the list the Warder already keeps from the orks: what
  an ork may not read, the preview does not show) and anything under `.git/` or `.orkcraft/`. `hooks.warder` and
  `gui.markdown` join `BOARD` (they import nothing of `orkcraft`).

## 6. The contract between the modules (written now; no code in this spec)
What passes along each edge of Orkboard's loop and where it lives. Orkline's graph (decisions §50.3) joins the same
modules by these hand-offs and no others; a new module speaks them. A setting that takes a step out
(`ideas.review: false`, §49.4) is the loop without that node.

| edge | what passes | where it lives | written by | read by | events |
|---|---|---|---|---|---|
| source → goal | an idea: text, goal, priority | `pages/ideas/<slug>.md` front matter, `state.json` `queue` | the person (`ideas.add`); later a source (decisions §50.4) | the keeper | `idea_added` |
| goal → its context | Summary, Metrics, links | `pages/tracks/<slug>.md` | the keeper (`goal`, `refresh`) | `draft`, `plan` | `goal_saved`, `goal_read` |
| draft → spec | Gist · Why · Done when · Out · Risks · Depends on · Open questions; `touches`, `risk` | the idea's page | the keeper (`draft`, `answer`, `talk`) | `plan`, the claims | `idea_drafted`, `idea_answered`, `idea_said`, `keeper_state` |
| spec → plan | tasks (tier, `after`, `touches`, brief), to-dos, `estimate` | `plan.json`; Stages on the page | the keeper (`plan`) | the runner | `plan_made`, `plan_passed` |
| plan → work | a task launched: worktree, branch, tier, effort, tool, model | `plan.json` task; `<task>.log` | the runner | Agents | `task_state` |
| work → review | a result: tests (`ran`, counts, tail), diff, cost, `round` | `plan.json` task (`state: review`) | the runner and the gate | Review, Needs you | `result_ready` |
| review → out | merged into `ideas.merge_into` | git; `plan.json` `merged` | the person, or §49.4's landing | the runner (the next tasks), the idea's state | `result_decided` |
| review → rework | sent back with one line why; or dropped | `plan.json` `round`, `why`; `failed` | the person | the runner | `result_decided`, `task_state` |

## 7. Not in this spec
- **Stage 2, the move** (decisions §50.9), after the testers' numbers and when: `SPLIT` and `KNOWN` are empty;
  `orkcraft board` has run the owner's work on another repository for two weeks; the testers' numbers are in. Then
  Orkboard's files and their tests leave with their history (`git filter-repo` on `BOARD`'s paths) for a repository
  of their own, and Orkline depends on it as a package. A spec of its own.
- Orkline's graph of loops, sources on goals, the panes as the buildings' windows, the town's pipeline retired
  (decisions §50.2–6): after the testers.
- Mission 1 on the person's commands, the score counting the Board's results (§50.5): when Camp comes back.
- A Wiki pane in Orkboard: when the owner's use asks for it.

## 8. The project, as in an IDE (D)
The owner (18 October, decisions §50.10): Orkboard opens a folder as an IDE does and works on its git, its code and
its Markdown; the goals, the ideas and everything of the Board belong to that project. Today the folder is fixed when
the host starts (the town's repository), the Board's settings are the machine's (`settings.py` `IDEAS`: one Target,
one `merge_into` for every repository), and nothing shows the project's files or its git but a result's diff at
Review. The orks still write the code; the person reads it, fixes small things, writes the Markdown, and commits.

**A project is a repository's folder.**
- **Open folder…** (the shell's project menu, the start screen, Ctrl+O / ⌘O) picks a folder. What must not be a
  project is refused in plain words (today's `realm/projects.py` `refusal`: the home folder, the system's, Orkline's
  own…); a folder without git offers **Start git here** (`start_git`, as today: a first commit, unless it would be too
  large). Both move to an Orkboard module, `realm/project_folder.py`; `realm/projects.py` keeps the orkspaces and
  imports them.
- **The list:** the machine's settings gain `projects_open` (paths, in the switcher's order) and `projects_recent`
  (at most 10). The **project switcher** heads the top bar: the current project's name; its menu lists the open
  projects, each with its counts (*working 2 · needs you 1 · review 3*), then Recent, **Open folder…**, **Close
  project**. `orkcraft board <folder>` opens that folder; without one, the last current project; with no project, the
  start screen (Open folder…, Recent).
- **Several at once, one shown.** Each open project has its own Board: its keeper, runner, claims and night (one
  `BoardHost` each, §4). Showing another project stops nothing: its tasks go on, the switcher counts what it needs, a
  push names its project. The limits are the tool's, so spec 35's reserve and *High first* hold across the open
  projects (each runner reads the same window, as today). **Stop all** stops every project's work. **Close project**
  stops its keeper and runner; with tasks running it asks first (*2 tasks are running in shop: Stop them and close ·
  Keep it open*).

**Everything of the Board is the project's.**
- Its pages, `plan.json`, the to-dos' secrets and files, the claims, the event log and the Board's tree are already
  under the project (`<repo>/.orkcraft/`, its Wiki): nothing of one project is seen in another.
- **The Board's settings move from the machine to the project:** `target`, `autostart`, `night`, `merge_into`,
  `push`, `review`, `wiki`, `max_parallel`, `reserve_day`, `reserve_night` are read from
  `<repo>/.orkcraft/board.json` (machine-local, git-ignored), the machine's `ideas` being the defaults a new project
  starts from; `risk_paths` from the tracked `orkcraft.toml` `[board]` (a fact of the repository, shared with whoever
  clones it). The gear says *for this project*. Roles (`.orkcraft/roles/`) are already the project's.

**Files.**
- A **Files** pane, a tab of the left column beside the Board (*Board · Files*), so the shell keeps its three
  columns: the project's tree, one level at a time, folders folded; `.git/` and `.orkcraft/` never shown;
  git-ignored files hidden behind a toggle. A click opens the file in the preview:
  - **Markdown** rendered by `gui/markdown.py` (markdown-it, raw HTML off; `files.read` returns its `html`), with
    **Edit**; a goal's linked document (`ideas.doc`, a `<pre>` today) is rendered the same way;
  - **code and any text** with line numbers (highlighted only if a highlighter is already vendored in
    `gui/static/vendor/`; no new library in this spec), with **Edit**;
  - a **binary** file or one over 1 MB: its size and **Open in the system** (`files.reveal`: the system's app for it,
    desktop only; `link.open` opens only http and https).
- **Edit** is a plain monospace editor: Ctrl+S saves, leaving with changes asks. A save is refused, in words, when the
  file changed on disk since it was read (*changed on disk: reload*), when the path leaves the project (`..`, a link
  out), and for a Board page (`pages/ideas/`, `pages/tracks/` of the Board's Wiki): those open in the Board, which
  commits them (spec 35 §13).
- **What may hold a secret is never read or written** by these commands: what `hooks/warder.py` `is_secret` names
  (`.env*`, keys, certificates, credentials: the Warder's list, as `ideas.doc` from C, §5) and the to-dos' secret
  store. The tree lists them greyed, *may hold secrets: open it in your own editor*.
- **The to-dos' secrets are the project's too.** The keychain's account is `<slug>/<todo id>` today
  (`realm/idea_secrets.py`), with no project in it: two projects with the same idea and to-do would share a secret.
  The account gains the project (`<project id>/<slug>/<todo id>`, the id a hash of the repository's path); a secret
  under the old account is read once and moved.

**Git.**
- A **Git** section of the Files pane: the branch, and whether it is the work branch (`merge_into`) or `main`;
  ahead / behind its upstream; the changed files with their + / −. A click shows the file's diff in the preview, in
  Review's diff view.
- **Commit** (the person ticks the files and writes the message; a secret-looking file is never offered), **Switch
  branch** (refused with uncommitted changes, said plainly), **Pull** (fast-forward only) and **Push** (on the press
  only, said plainly: *sends your code to origin*).
- Every call: fixed arguments, no shell, under the repository's lock (`idea_git.lock_of`); never in a task's worktree
  or the Board's tree. No rebase, reset, force or stash in this spec.

**The phone:** the project switcher, and a Markdown file read-only when the Board links it (a spec, a goal's
document). No edit and no git from the phone: `gui/mobile.py` allows `projects.list`, `projects.use` and
`files.read` (Markdown only), nothing else of this section.

| command | args | returns |
|---|---|---|
| `projects.list` | — | `{"current", "open": [{"path", "name", "working", "needs_you", "review"}], "recent": [{"path", "name"}]}` |
| `projects.open` | `{"path"}` | `{"ok": true, "git": bool}` or `{"error"}` (the refusal, in words) |
| `projects.start_git` | `{"path"}` | `{"ok": true, "said"}` or `{"error"}` |
| `projects.use` | `{"path"}` | `{"ok": true}` (an open project becomes the shown one) |
| `projects.close` | `{"path", "stop"?: bool}` | `{"ok": true}`, or `{"running": n}` when tasks run and `stop` is not set |
| `files.tree` | `{"dir"?, "ignored"?: bool}` | `{"entries": [{"name", "path", "dir", "size", "secret"}]}` (one level) |
| `files.read` | `{"path"}` | `{"path", "kind": "markdown" \| "text" \| "binary" \| "large" \| "secret", "text"?, "size", "mtime"}` |
| `files.write` | `{"path", "text", "mtime"}` | `{"ok": true, "mtime"}` or `{"error"}` |
| `files.reveal` | `{"path"}` | `{"ok": true}` (desktop only) |
| `git.status` | — | `{"branch", "work_branch", "upstream", "ahead", "behind", "files": [{"path", "status", "added", "removed"}]}` |
| `git.diff` | `{"path"}` | one file in `ideas.diff`'s shape |
| `git.commit` | `{"paths", "message"}` | `{"ok": true, "commit"}` or `{"error"}` |
| `git.switch` | `{"branch"}` | `{"ok": true}` or `{"error"}` |
| `git.pull`, `git.push` | — | `{"ok": true, "said"}` or `{"error"}` |

- Events (the same log, the project's): `project_opened` (new, git, device), `project_closed` (stopped),
  `file_saved` (kind, bytes: never the path's text), `git_committed` (files, device), `git_pushed` (branch, device).
- All of it is Orkboard's: its modules join `BOARD`, and Orkline gets it through the same panes (decisions §50.6).

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **D1. Backend** | `spec/37-project-backend` | §8 but the screens | new `realm/project_folder.py`, `realm/projects.py` (imports it), new `realm/repo_git.py`, new `gui/board_projects.py` (the open projects, a `BoardHost` each), new `gui/board_files.py`, new `gui/board_git.py`, `gui/board_host.py`, `gui/ideas.py` and its mixins (the settings from the project), `settings.py` (`projects_open`, `projects_recent`), `realm/event_log.py`, `gui/mobile.py` (allowlist), `cli.py` (`orkcraft board <folder>`), `realm/idea_secrets.py` (the account per project), `orkcraft/layers.py` (the new modules in `BOARD`) |
| **D2. Desktop** | `spec/37-project-desktop` | §8's screens on the desktop | `gui/static/js/shell/*` (new `files.js`, `gitpane.js`, `projects.js`, `editor.js`; `shell.js`, `preview.js`, `topbar.js`, `settings.js`, `shell.css`), `gui/static/board.js` |
| **D3. Phone** | `spec/37-project-phone` | the switcher and a Markdown file read-only | `gui/static/pwa/shell-*.js` (new `shell-projects.js`), `pwa/board-app.js`, `pwa/app.css`, `pwa/sw.js` (cache version, and `tests/test_pwa.py`'s pinned version with it) |

D comes after B (it needs `BoardHost`); D1 on the elder tier (paths, secrets, git: security and data that can be
lost), D2 and D3 on the warrior tier, branched from D1 once it is pushed.

## Tests
- **A:**
  - `test_orkboard_imports_only_orkboard`, `test_known_edges_still_exist`, `test_every_board_pattern_matches`;
  - each can fail: a fixture module under `BOARD` importing a line module (written in `tmp_path`, checked by the
    same function) fails the first; an edge added to `KNOWN` that the code does not have fails the second; a
    pattern that matches nothing fails the third;
  - `python -m orkcraft.layers` prints the nine edges with their files and lines;
  - the critical tests (CLAUDE.md "Alpha").
- **C:**
  - on a fixture repository with no tests, a task's result is `review` with `ran: false`, and with
    `ideas.review: false` it does not land;
  - `[gate]` with `run = "sh -c 'exit 0'"`: passed by the exit code, counts `null`; `exit 1`: failed with the tail;
  - `{files}` holds `always` and the mapped tests that exist, quoted; `map` with `{stem}` and `{dir}`;
  - no `orkcraft.toml`: the same command and files as today on this repository; a broken file: the card's line and
    today's gate;
  - `test_argv` from `gate_config`: words, and `sh -c` for `&&`;
  - `ideas.doc` refuses `.env`, `.orkcraft/secrets.json`, `.git/config` and an `id_ed25519`, from the desktop and
    the phone, and still reads a Markdown file and a `.env.example` (the Warder's `ENV_OK`);
  - browser at 1 440 × 900 and 390 × 844 (a stub host's results): `ran: false` reads *no tests ran*, `null` counts
    with a green exit *passed (exit 0)*, a red exit *failed (exit 1)* with Fix, pytest counts as today;
  - `test_idea_git.py`, `test_idea_runner.py`, `test_gui_ideas.py`, `test_gui_goals.py`, the critical tests.
- **B:**
  - `test_orkboard_starts_alone`: in a fresh interpreter, building Orkboard's host and its server on a fixture
    repository (no port opened) leaves only `BOARD` modules in `sys.modules` (as `test_loading_the_core_loads_no_face`
    does);
  - `KNOWN` and `SPLIT` empty;
  - the Board's commands on `BoardHost` give the same answers as on Orkline's host (`test_gui_ideas.py` and
    `test_gui_goals.py` run against both);
  - the Wiki: Orkboard on `ideas.wiki` and on the default; Orkline with a Wiki building finds the same folder as today;
  - browser at 1 440 × 900 (`orkcraft board`): the four panes, a goal saved, Needs you; the page requests no file
    under `js/camp/`, `js/buildings/`, `sprites/`, `v3/` (the network log); at 390 × 844 the phone shell, the same,
    no horizontal scroll;
  - Orkline with `focus = "board"` and `focus = ""` as today (`test_shell_browser.py`, `test_pwa_shell_browser.py`);
  - the critical tests, the touched modules' tests, `tests/test_gui_wording.py`, and the four checks of
    specs/README.md "Before you commit".
- **D1:**
  - on two fixture repositories: open both; a goal and an idea in one are not seen in the other; each runs its own
    runner; switching the shown one stops nothing; Stop all stops both; Close with a running task answers `running`
    and stops only with `stop`;
  - the Board's settings: a project's `board.json` wins over the machine's; a new project starts from the machine's;
    `risk_paths` from `orkcraft.toml`;
  - Open folder: the refusal's words for the home folder; a folder without git answers `git: false`, then
    `start_git` makes the first commit;
  - two projects with the same idea slug and to-do id keep two secrets; one stored under the old account is read
    and moved;
  - files: the tree hides `.git/` and `.orkcraft/`, the ignored files only behind the toggle; `files.read` of
    Markdown, text, binary, over 1 MB; a `.env` and an `id_ed25519` read as `secret` with no text; `files.write`
    refused outside the project (`../x`, a symlink out), on a Board page, on a secret-looking path, and when the
    file changed since `mtime`; a save that passes writes the file and records `file_saved` without its text;
  - git on a fixture with an upstream: status with ahead/behind and + / −; a file's diff; a commit of the ticked
    files only; switch refused with uncommitted changes; pull fast-forward only (a diverged one refused); push only
    on its command; every call under the lock and with no shell;
  - the phone: `projects.list`, `projects.use` and a Markdown `files.read` allowed; `files.write`, `git.*` and a
    code file refused;
  - `test_orkboard_imports_only_orkboard` with the new modules in `BOARD`; the critical tests.
- **D2:** browser at 1 440 × 900: Open folder on a fixture, the switcher with two projects and their counts; the
  Files pane: a Markdown file rendered, edited and saved; a code file with line numbers; a `.env` greyed; the Git
  section: a changed file's diff, a commit; *changed on disk: reload* after the file changes underneath.
- **D3:** at 390 × 844: the switcher as a sheet; a spec opened read-only; no edit or git control; no horizontal
  scroll.
