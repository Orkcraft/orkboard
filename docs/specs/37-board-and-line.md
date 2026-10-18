# Spec 37 — Orkboard and Orkline, stage 1: the boundary, Orkboard on its own, the gate on any repository

The owner, 18 October (decisions §50). After specs 35 and 36 the four windows (the Board with its goals, the
preview, Agents, Review) are a whole tool, and the owner wants it every day, at work and at home, on other projects:
**Orkboard**. Orkline goes on from what that use shows, on the same modules. Today the four windows live inside the
town: `focus = "board"` only changes what is drawn. The host still builds the whole town (`gui/host.py:47-170`), the
Board reaches into it at run time (its Wiki among the town's buildings, the limits from the Town Hall's worker, the
budget from the Treasury), nine imports pull the town's modules in, the desktop and phone pages load the camp's
scripts, and the gate passes a result when it finds no test file to run. This spec draws the line, cuts it, starts
Orkboard on its own, and lets the gate test another repository. Nothing moves to another repository here (stage 2,
§7). **Builds:** Claude (A and C on the warrior tier; B on the elder tier) · **Review:** full · P1.

**When.** A now: it touches no file of specs 35 or 36. C after 35 and 36 are merged: it is what Orkboard needs
first at work. B after C (both change `realm/jobs.py`). gate-kinds (decisions §49.4–7) comes after C and puts its
`[[check]]` rows into C's file; B and gate-kinds are not built at the same time (both change `gui/ideas.py`).

Three parts, one branch each; **this file is the contract** (names, data, commands); the rest is the builder's
choice inside its files. Wording: CLAUDE.md. **Change nothing outside these files.**

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. The boundary** | `spec/37-boundary` | §1, §2 | new `orkcraft/layers.py`, `tests/test_architecture.py` (new tests only), `CLAUDE.md` ("Where code goes": one bullet, §2) |
| **C. The gate on any repository** | `spec/37-gate` | §5 | new `realm/gate_config.py`, `realm/idea_git.py`, `core/idea_runner.py` and `core/idea_review.py` (*no tests ran* never lands by itself), `realm/forge.py` and `realm/jobs.py` (`test_argv` imported from `gate_config`, one line each), new `orkcraft.toml` (this repository's), `orkcraft/layers.py` (`KNOWN` loses `jobs → forge`) |
| **B. Orkboard on its own** | `spec/37-alone` | §3, §4 | new `realm/tool_run.py`, `realm/jobs.py`, `realm/road_agents.py`, `realm/roads.py`, `realm/harnesses.py`, `realm/tiers.py`, `realm/looks.py`, `realm/builders.py`, `realm/worktrees.py` and a new line module for its town part, `settings.py` (`ideas.wiki`, `MachineSettings` read cached), new `core/board_limits.py`, `core/treasury.py`, `gui/ideas.py`, `gui/ideas_limits.py`, new `gui/board_host.py`, `gui/host.py`, `gui/state.py`, `gui/onboarding.py`, `gui/static/js/onboarding.js`, `gui/launch.py`, `gui/server.py`, `gui/pwa.py`, `gui/phone_http.py`, `gui/mobile.py`, `gui/phones.py`, `cli.py`, `pyproject.toml` (`[project.scripts]`), new `gui/static/board.js`, `gui/static/index.html` only if the entry needs it, new `gui/static/pwa/board-app.js`, `gui/static/pwa/index.html`, `pwa/sw.js`, `orkcraft/layers.py` (`SPLIT` and `KNOWN` emptied), new `<name>_town.py` modules beside the split ones (§4) |

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
  AI tools found, the repository): no class, no Mission 1, no town raised behind it (today `js/onboarding.js:545-559`
  raises one). The same machine settings and state folder as Orkline's: switching between the two loses nothing.
- **The snapshot** in Orkboard holds only what the shell reads: `focus` (`"board"`), `onboarding`, `ideas_rev`,
  `needs_you`, `idea_states`, `review_count`, `review_results`, `limits`, `hud` with `show_gold`, `gold`, `lumber`
  only (the top bar's spend), `repo`, `projects`, `orkspaces` (the repository picker), `update`.
- **The pages.** The desktop page in Orkboard loads `static/board.js`: the shell, the onboarding's first screen,
  the repository picker and the toasts, and no camp module (`app.js:4-35` imports them all today). The phone loads
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
  counts are `null`, the card says *passed (exit 0)* or *failed (exit 1)* with the output's tail. The run goes
  through `test_argv` (words, or `sh -c` when it needs a shell), which moves from `realm/forge.py` to
  `realm/gate_config.py`; `forge` and `jobs` import it from there (`KNOWN` loses `jobs → forge`).
- `plan.json` task `tests` gains `ran` (bool) and `command` (the command as run); old tasks read `ran: true`.

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
  - `test_idea_git.py`, `test_idea_runner.py`, `test_gui_ideas.py`, the critical tests.
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
