# Spec 38 — Operations: the person's everyday work by templates, across projects; a template checks with you until it may go by itself

The owner, 18 October (decisions §51). The Board takes a project's work from a goal to code at Review. The owner's
working day also holds small, frequent work that is no code and belongs to no repository: a Jira task to file with its
priority and epic, an email to answer. Today that is done by hand, or in a chat with a skill typed out each time: no
queue, no check before it goes, no memory of how the person wants it. This spec adds **Operations**: one list of the
person's, seen in every project, where such work is added from a **template** (a Claude skill and a short form),
prepared by one model call, checked by the person, and done by one more call allowed only the one tool that does it.
A template the person passed without a correction goes **by itself** from then on; a correction makes it propose
**rules**, and once the person takes them it goes by itself. **Builds:** Claude (A on the elder tier: outward actions
and the person's mail; B and C on the warrior tier) · **Review:** full · P1.

**When:** a new mechanic before the testers' numbers, the owner's named exception (decisions §51, as §45.8 and
§50.10). Not built at the same time as spec 37 D1 and D2 (all three change `gui/board_host.py` and the Board pane). It
is written for today's host of one project and holds with D: one Operations for all the open projects (§1).

Three parts, one branch each, in this order; **this file is the contract** (names, data, commands); the rest is the
builder's choice inside its files. Wording: CLAUDE.md (today's words: *Operations*, *operation*, *template*, *check*,
*by itself*, *rules*; §0). **Change nothing outside these files.**

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. Backend** | `spec/38-ops-backend` | §1–§9, §11 | new `realm/op_templates.py`, new `realm/op_runs.py`, new `core/op_runner.py`, new `gui/ops.py`, `realm/harnesses.py` (`call` gains effort, budget, one shot), `realm/jobs.py` (new `run_call`), `realm/idea_target.py` (the `op_*` steps), `settings.py` (`OPS`), `realm/lexicon.py`, `gui/board_host.py` (the host builds Operations; Stop all; the phone's `ops.*`; Needs you's rows), `gui/ideas_board.py` (`sort_needs` knows the `op` kinds), new `ops_templates/jira-task/` and `ops_templates/email-reply/` (each `SKILL.md` and `orkboard.toml`), `pyproject.toml` (their package data) |
| **B. Desktop** | `spec/38-ops-desktop` | §10 on the desktop | `gui/static/js/board/*` (new `ops.js`; `tracks.js`, `today.js`, `store.js`, `board.css`), `gui/static/js/shell/*` (new `opdialog.js`, `opcheck.js`; `boardpane.js`, `dialogs.js`, `shell.css`) |
| **C. Phone** | `spec/38-ops-phone` | §10 on the phone | `gui/static/pwa/shell-*.js` (new `shell-ops.js`; `shell-board.js`, `shell-needs.js`, `shell-forms.js`, `shell-words.js`), `pwa/board-app.js`, `pwa/app.css`, `pwa/sw.js` (cache version) with `tests/test_pwa.py`'s pinned version |

B and C branch from A once A is pushed (as in 35 and 37); they touch no file of each other's.

## 0. The words
- **Operations:** the person's list of everyday work, across projects (`TERMS` `operations`). Not a goal: no Summary,
  no ideas, no plan, no Review, no Target of a project's.
- **an operation:** one piece of that work, from one template: added, prepared, checked, done (`operation` ·
  `operations`).
- **a template:** a Claude skill with Orkboard's manifest beside it (§2): its form, the tools it may read with, its one
  action (`op_template`: *template · templates*).
- **the check:** the person's look at a prepared operation before its action, where they may correct it (`op_check`:
  *check · checks*). The steps' code names are `op_prepare`, `op_act`, `op_learn`.
- **by itself:** a template whose operations do their action with no check (§6), the words of spec 35 §11.5
  (`op_alone`).
- **rules:** what a template learned from the person's corrections, a line each, in Orkboard's own file for it (§7)
  (`op_rules`: *rules*).
- The project's **General** goal is not touched and not renamed: it stays the system's own place, unseen (spec 35 §2;
  decisions §50.4 sends External listeners to the goals they serve). Operations is a new thing beside the projects.

## 1. Operations is the person's
- **One list for the person, whatever project is open.** Its state lives in the person's folder, `ops/` beside the
  machine settings (`settings.path().parent / "ops"`: `~/.config/orkcraft/ops/`, under `$XDG_CONFIG_HOME` when set, and
  beside `$ORKCRAFT_SETTINGS_FILE` in the tests), never in a repository:

```
ops/
  runs/<id>.json                 one operation (§3), mode 600
  calls/                         its model calls, kept by call_log (their prompts hold the person's mail, §9)
  templates/<name>/rules.md      what the template learned (§7)
  templates/<name>/trust.json    its way to *by itself* (§6)
  templates/<name>/declined.jsonl  the rules the person turned down (§7)
  spend.jsonl                    the calls' ledger lines (idea_spend's `line`, §8)
  events.jsonl                   the events (event_log's rules, §11)
  work/                          the empty folder every call starts in
```

- **The host builds it once** (`gui/board_host.py` `Orkboard`: `self.ops = ops.Ops(self)` beside `self.ideas`), with
  its commands (§11), its tick and Stop all. With spec 37 D's several projects it stays one, beside them: showing
  another project changes nothing of it.
- **Its settings are the person's:** the machine settings gain `ops` (`settings.py` `OPS`, checked like `IDEAS`):

```python
OPS = {"target": "balance",      # thrift · balance · quality: the tier and effort of its calls (§4)
       "trust_after": 1,         # clean checks in a row before a template goes by itself (§6; the owner's choice)
       "daily_alone": 20,        # the most operations a template does by itself a day; then it checks again
       "keep_days": 14,          # a finished operation keeps its texts this long (§9)
       "servers": {}}            # a template's server key → the MCP server's name on this machine (§2)
```

- **The limits are the tool's**, shared with the projects. Before each call, as the keeper (spec 35 §6): in a spent
  window the call is not made, the operation waits (`held_until`, *waits for limits · after 18:00*) and runs when the
  window is back. Every operation in this spec is the person's own (they pressed **Add**), so only the `NEARLY` floor
  applies, never the reserve; an operation a source starts later (§12) will keep the reserve.
- **Its spend is the day's spend:** each call is charged as any run (`telemetry`, the top bar), and its ledger line
  goes to `ops/spend.jsonl`.
- At most **2** operations run their calls at once (`core/op_runner.py` `MAX_PARALLEL`); the rest wait in order.
- In v1 operations run on **Claude** only: `h.call` (an agent allowed only the MCP tools it is given) exists only for
  the claude harness. On a machine without it, Operations says so in plain words and adds nothing.

## 2. A template: a skill and its manifest
- **Where:** a template is a skill folder that holds an `orkboard.toml` beside its `SKILL.md`:
  - the person's: `<claude home>/skills/<name>/` (`$CLAUDE_HOME`, else `~/.claude`, as `sources/sessions.py` reads
    it);
  - the built-in two, shipped in the package: `orkboard/ops_templates/<name>/` (§5).
  A person's template with a built-in's name replaces it. A skill without `orkboard.toml` is not a template. The
  project's `.claude/skills/` (templates shared with a team) is not read in this spec (§12).
- **The skill stays a skill:** `SKILL.md` is the person's, written as for Claude Code, and goes on working there.
  Orkboard never writes it or the manifest. What Orkboard learns goes to its own `ops/templates/<name>/rules.md` (§7).
- **The manifest** (`realm/op_templates.py` reads it with `tomllib`; an unknown key is ignored; a broken one lists the
  template with its problem in words, and it cannot be added from):

```toml
# an excerpt of the built-in ops_templates/jira-task/orkboard.toml (all of it in §5)
title = "New Jira task"               # the New menu's item and the operation's heading
risk = "medium"                       # low · medium · high: high never goes by itself (§6)
servers = { jira = "Jira" }           # each {key} in a tool's name, and what it is for (the gear names the server)

[[fields]]                            # the form, asked when the person adds one, in this order
name = "what"
label = "What needs doing"
type = "long"                         # text · long · choice
required = true

[[fields]]
name = "priority"
label = "Priority"
type = "choice"
options = ["Highest", "High", "Medium", "Low", "Lowest"]
default = "Medium"
at = "additional_fields.priority.name"   # where its value goes in the action's arguments (below)

[[draft]]                             # what the prepare writes and the check lets the person correct
name = "summary"
label = "Title"
at = "summary"

[prepare]
tools = ["mcp__{jira}__searchJiraIssuesUsingJql", "mcp__{jira}__getJiraIssue"]   # what it may read with

[act]
tool = "mcp__{jira}__createJiraIssue"   # exactly one tool: the action
label = "Create in Jira"                # the check's button: what happens, said plainly
```

  - A field: `name`, `label`, `type`, and optionally `required`, `options` (a choice's), `default`, `hint`,
    `remember` (prefilled with the last value given), `at`. A draft part: `name`, `label`, optionally `type` (text ·
    long) and `at`. At most 8 fields and 4 draft parts; a value at most 4 000 characters.
  - `at` is a dotted path into the action's arguments. A field or draft part with `at` can be corrected on the check
    and code writes it there; a field without one is the prepare's to resolve (an epic's name into its key), so
    changing it on the check means **Prepare again** (§4).
  - `{key}` in a tool's name is the person's MCP server for that key, from `ops.servers`; the gear lists the servers
    `claude mcp list` prints (read when the gear opens) and the person picks one per key once. The tool's name is
    written as the CLI spells it, `mcp__<server>__<tool>`. A template whose key has no server says *Jira is not
    connected: add its MCP server to Claude Code, then pick it here*, and cannot be added from.
- **Its version** is the sha256 of its `SKILL.md` and `orkboard.toml` as read. A changed version sends it back to
  checks (§6). `rules.md` is not in it: it changes only through Orkboard, by the person (§7).

## 3. An operation's way
`preparing` → `check` → `acting` → `done`; or `preparing` → `acting` → `done` when its template goes by itself and
nothing stops it (§6). Besides: `held` (the limits, §1), `failed`, `dropped` (the person's **Drop**, from `check` or
`failed`).

- `ops/runs/<id>.json` (written whole, atomically, mode 600): `id, template, version, state, fields, found, draft,
  args, doubts, edited, alone, device, link, done_id, why, acted, at, done_at, cost`.
- **Add** (`ops.add`) checks the form (required fields, choices among their options), writes the run in `preparing`
  and starts the prepare at once.
- **Stop** on a running operation (and Stop all): its call is cancelled. Stopped in `preparing`: `failed`, *stopped*.
  Stopped in `acting`: `failed` with `acted: null`, *stopped while doing it: look in Jira before you add it again*.
- **Nothing is done twice by Orkboard.** A failed operation whose action may have run (`acted` true or null) offers
  only **Add again** (a new operation with the same fields, the person's knowing press) and **Drop**, never a retry. One
  that failed before its action (`acted: false`) offers **Try again**.

## 4. The calls: one job each, built by code, each with its cap
Every call is one shot, as the keeper's (spec 35 §0): a fresh `claude -p` in `ops/work/`, never resumed,
`--no-session-persistence`, `--effort` and `--max-budget-usd` when the CLI lists them, no built-in tool
(`harnesses.CLAUDE_NO_TOOLS`), only the MCP tools named. `realm/harnesses.py` `call` gains `effort`, `budget` and
`one_shot` as `read` has them; `realm/jobs.py` gains `run_call(harness, prompt, workdir, cancel, allow, model, env,
effort, budget)` → `(text, cost, tokens, events)`, `events` the stream-json lines it needs: the `init` event's tools,
each `tool_use` (name, input) and `tool_result` (is_error). Each run's calls are kept under `call_log.kept(ops/calls,
"ops")` (§9). Each call's tier and effort come from `ops.target` through `realm/idea_target.py`, the one table of steps:

| step | gets (cut by `CONTEXT`) | tools | thrift | balance | quality | cap $ (balance) | context |
|---|---|---|---|---|---|---|---|
| `op_prepare` | the skill's `SKILL.md` without its front matter (≤ 6 000), its rules (≤ 2 000), the fields, the draft parts with their `at`, the action's tool, today's date, the answer's shape | `[prepare] tools` | warrior · low | warrior · medium | elder · medium | 0.30 | 12 000 |
| `op_act` | the arguments, the tool | `[act] tool`, only | laborer | laborer | warrior · low | 0.10 | 6 000 |
| `op_learn` | the template's title, its rules, the fields, each corrected field and part before → after (≤ 2 000 each) or the *Not right* line, the last 10 declined rules | none | laborer | warrior · low | warrior · medium | 0.10 | 6 000 |

The budget is halved in thrift and doubled in quality (`BUDGET_SHARE`); no effort on the laborer tier (spec 35 §1).

- **The prepare** reads with its tools and changes nothing. The action's tool is in its tool list (it sees the
  tool's schema, to write its arguments) but not in `--allowedTools`, so in `-p` a call of it is refused. Before
  anything else the code checks the `init` event: a tool the template names that is not there stops the run, `failed`,
  *Jira's server has no createJiraIssue: check the server picked in Operations' gear*. Its answer, one JSON object:

```json
{"args": {"…": "the action tool's arguments"},
 "draft": {"summary": "…", "description": "…"},
 "found": [{"label": "Epic", "value": "ABC-12 · Checkout"}],
 "doubts": ["Maybe the same as ABC-140 · Checkout fails on Safari (open, 3 days old)"]}
```

  Code keeps only these keys: `args` an object; the draft parts the manifest names; `found` ≤ 6 rows, `doubts` ≤ 5
  lines (each ≤ 300 characters); then writes each field and draft part that has `at` into `args`, so the arguments
  say exactly what the check shows. No JSON: `failed` (`acted: false`), *the answer was not the JSON it was asked for*.
  The prompt says: *Use only the tools listed; change nothing; put into doubts whatever you are not sure of: a
  possible duplicate, a value you could not find, a guess.* Doubts are what stop a template that goes by itself (§6).
- **The action** is told: *Call `<tool>` once with exactly these arguments, then answer {"id", "link"} from what it
  returns.* Code reads its events: no `tool_use` → `failed`, `acted: false`, *nothing was done*; exactly one, of that
  tool, its input equal to `args` (as JSON), no error → `done` with `done_id` and `link` (http or https, else none);
  a `tool_result` error → `failed`, `acted: true`, its first line; another tool, other arguments, or more than one
  call → `failed`, `acted: true`, *it did not do exactly what was checked: look in Jira*.
- **Prepare again** (`ops.prepare`): on the check, with the fields as the person changed them, one more prepare; the
  draft parts the person corrected stay theirs.

## 5. The built-in templates
Two, in `orkboard/ops_templates/` (`pyproject.toml` package data `ops_templates/**/*`). Their tools are named as the
servers list them on the build day: the builder checks them against the owner's `claude mcp list` and one prepare's
`init` event, and the manifest is the one place they are written.

| | **New Jira task** (`jira-task`) | **Reply to an email** (`email-reply`) |
|---|---|---|
| risk | medium | medium (the action saves a draft; the person sends it from Gmail) |
| fields | `what` (long, required) · `project` (text, `remember`) · `priority` (choice Highest · High · Medium · Low · Lowest, default Medium, `at`) · `type` (choice Task · Bug · Story, default Task, `at`) · `epic` (text: a key or words of its name) | `find` (text, required: the sender or words of the subject) · `say` (long, required: what to answer) · `tone` (choice short · warm · formal, default short) |
| draft | `summary` (Title) · `description` (Description, long) | `subject` · `body` (long) |
| prepare reads | `{jira}`: `getAccessibleAtlassianResources`, `getVisibleJiraProjects`, `searchJiraIssuesUsingJql`, `getJiraIssue` | `{gmail}`: `search_threads`, `get_thread` |
| found | the project, the epic it resolved | the thread's subject, who writes, the last message's first line |
| doubts | an open issue in the project with a like summary from the last 90 days; an epic not found or more than one; a project not found | more than one thread matches; the last message is the person's own |
| action | `createJiraIssue` · *Create in Jira* | `create_draft` with `replyToMessageId`, `to`, `subject`, `body` · *Save as a draft in Gmail* |

Their `SKILL.md`s say how the person's work wants it: a Jira title as an action, the description's *Why* and *Done
when*, no invented facts; a reply in the person's language, in the tone asked, nothing promised the person did not
say.

## 6. By itself: a template earns it
Per template, `ops/templates/<name>/trust.json`: `{version, clean, alone, why, today: {date, alone_done}}`. The rules
are pure functions in `realm/op_runs.py`, so they are tested apart:

- **A clean check** (the person pressed the action with no field or draft part corrected; a Prepare again on changed
  fields is a correction): `clean += 1`; at `ops.trust_after` (default **1**) the template goes by itself
  (`alone: true`, `why: "clean"`). Its row says *goes by itself: creates in Jira without asking you*.
- **A corrected check:** the action is done as corrected; `clean = 0`, `alone: false` (`why: "edit"`); then the learn
  call (§7). When the person takes the rules it proposes, the template goes by itself (`why: "rules"`): the owner's
  rule, the rules being the correction made general and passed by the person. When the learn call finds nothing
  general (`rules: []`), the clean checks after it do it.
- **Not right** on a done operation (it went by itself and the person sees it wrong; a line why, optional):
  `alone: false`, `clean = 0` (`why: "not_right"`); the line goes to the learn call as the correction.
- **Its version changed** (the skill or the manifest edited on disk): `alone: false`, `clean = 0` (`why: "version"`).
- **Check again** on the template's row: `alone: false`, `clean = 0` (`why: "reset"`).
- **Even by itself, an operation stops at the check** (its row says why) when: its prepare wrote a doubt; its template's
  risk is `high` (*always checks with you*: such a template never goes by itself); the template did `ops.daily_alone`
  operations by itself today (*checks again today: 20 done by itself*). These stops change nothing of `trust.json`.
- A done operation shows *by itself* beside its link when it went so.

## 7. Rules: a correction made general
- **The learn call** (`op_learn`, no tools) runs after a corrected check is done, or after **Not right**. It answers
  `{"rules": ["…"], "why": "…"}`: at most 3 lines, each ≤ 200 characters, each a rule for every operation of this
  template (*A title starts with the component in brackets: [Checkout] …*), never a fact of this one operation. Code
  drops a line that repeats one in the rules or one declined.
- **The proposal:** in Operations and in Needs you (last, as spec 35's proposals: it blocks nothing), kind `op_rules`:
  the lines, the operation it came from, **Take** and **No** (with an optional one-line reason).
  - **Take** appends the lines to `ops/templates/<name>/rules.md` and sends the template by itself (§6).
  - **No** adds `{lines, reason, at}` to `declined.jsonl`; the template keeps checking. The next learn call reads the
    last 10.
  - At most one proposal waits per template: a new one replaces the old.
- **The rules are the person's to read and edit:** **Rules** on the template's row opens `rules.md` as plain text,
  saved by **Save** (`ops.rules_save`; ≤ 4 000 characters, a `#` heading made `###` as `ideas.clean_text` does). A save
  by the person leaves `trust.json` as it is. Every prepare gets the rules after the skill.

## 8. Needs you, the ledger
- The snapshot's `needs_you` gains, in every project, Operations' rows (`gui/ops.py`, merged by the host): `op` (an
  operation at its check: the template's title, the draft's first part, `blocks: false`, priority `normal`, its time),
  `op_failed` (a failed one) and `op_rules` (§7). `sort_needs` puts `op_rules` last with `proposal`; the snapshot's
  count leaves `op_rules` out, as it leaves proposals out.
- Each call's line in `ops/spend.jsonl` (idea_spend's `line`, its step, with `op` and `template`); `ops.list` gives
  each finished operation's cost.

## 9. What stays private
- **What an operation reads and writes stays in the person's folder:** its fields, its draft, what its prepare found
  (a mail's words, an issue's) and its arguments live only in `ops/runs/` (mode 600). Never in a repository, a Board
  page, the Board's commits (spec 35 §13), a project's event log or `.orkcraft/logs/`.
- **Its calls are kept apart:** `call_log` keeps every call's prompt and output (`.orkcraft/logs/<day>/` of the project
  once `keep_days` is set); an operation's calls run under `call_log.kept(ops/calls, "ops")`, so they are kept in the
  person's folder only. The project's `telemetry` ledger gets what it gets of any run: when, `ops`, the model, the cost,
  no text.
- **After `ops.keep_days` (14)** a finished operation (done, failed, dropped) keeps only `id, template, state, link,
  alone, cost, at, done_at`: its fields, found, draft, args and doubts are removed, and its calls from `ops/calls/`
  (`op_runs.forget_old`, at start and once a day).
- The events (§11) never carry a field's, a draft's, a mail's or an issue's words: names, counts, states.
- The phone: `ops.*` as `ideas.*` (`BoardPhone.allowed`), the device in the events.

## 10. Screens (B, C)
1. **The goal select** (spec 35 §11.1) gains **Operations**, last, after a divider, in every project. Chosen, the
   Board pane shows Operations in place of Needs you and the ideas; the Target chip and New idea give way to **New…**.
2. **New…** opens a menu: one item per usable template (its `title`), then a line for each that cannot be used and why
   (*Jira is not connected*). An item opens **its form** (`opdialog.js`): the fields as the manifest says (text, a
   box, a select), `remember`ed ones prefilled, `hint`s as placeholders, one button **Add**. Closing with typed text
   keeps it in the form for the next opening on that device (the browser's storage); closing it empty adds nothing.
3. **Operations' list**, top to bottom:
   - **At your check:** a row each (its template, its first draft part, its time; *at your check · a doubt* when a
     doubt stopped a template that goes by itself). A click opens **the check** (`opcheck.js`): what was found
     (`found`, read-only), the doubts as lines with a warning icon, the fields with `at` and the draft parts editable,
     the other fields editable behind **Prepare again**, and the action's button (`[act] label`), **Drop**. Changing
     a field without `at` turns the action's button into **Prepare again**.
   - **Running:** a spinner with *preparing* or *doing it*, and **Stop**; *waits for limits · after 18:00* when held.
   - **Failed:** its line why, then **Try again** (only with `acted: false`), **Add again**, **Drop**.
   - **Done (n)**, folded: each with its link (opens in the browser, `link.open`), *by itself* when so, and **Not right**
     on those that went by itself.
   - **Templates**, folded: each with its state in words (*checks with you* · *goes by itself* · *always checks with
     you*), **Check again** (when it goes by itself), **Rules**, and its rules proposal when one waits (Take · No).
4. **The gear** of Operations: its **Target** (the three, as spec 35's chip says them), *Goes by itself after N clean
   checks* (1–5), *By itself at most N a day* (1–100), and for each server key of the templates, its server (a select
   of `claude mcp list`'s names, *not connected* when none).
5. **Needs you** (every project): the `op`, `op_failed` and `op_rules` rows with their icons; a click opens the check,
   the failed row or the proposal.
- **The phone:** the same in the Board tab's select, the form, the check and the gear as sheets (34 §5); no horizontal
  scroll.
- Words on every button say what happens (CLAUDE.md): *Create in Jira*, *Save as a draft in Gmail*, never *OK*.

## 11. Commands and events (A)
| command | args | returns |
|---|---|---|
| `ops.list` | — | `{"templates": [{"name", "title", "risk", "fields", "draft", "act_label", "state", "clean", "unusable"?, "proposal"?}], "runs": [{"id", "template", "state", "title", "found", "draft", "fields", "doubts", "alone", "link", "why", "acted", "held_until", "cost", "at"}], "settings": {...}, "servers_needed": {"jira": "Jira"}}` |
| `ops.add` | `{"template", "fields": {...}}` | `{"id"}` or a refusal in words |
| `ops.prepare` | `{"id", "fields", "draft"}` (Prepare again) | `{"ok": true}` |
| `ops.act` | `{"id", "fields", "draft"}` (the check's action, as corrected) | `{"ok": true}` |
| `ops.drop` · `ops.stop` · `ops.retry` · `ops.again` | `{"id"}` (`retry` only with `acted: false`; `again` adds a new one with its fields) | `{"ok": true}` / `{"id"}` |
| `ops.not_right` | `{"id", "why"?}` | `{"ok": true}` |
| `ops.rules` · `ops.rules_save` | `{"template"}` · `{"template", "text"}` | `{"text"}` · `{"ok": true}` |
| `ops.rules_answer` | `{"template", "take": bool, "reason"?}` | `{"ok": true}` |
| `ops.trust_reset` | `{"template"}` (Check again) | `{"ok": true}` |
| `ops.servers` | — | `{"servers": ["…"]}` (`claude mcp list`'s names) |
| `ops.set` | `{"target"?, "trust_after"?, "daily_alone"?, "servers"?}` | the `ops` settings |

- The bus: `ops.changed` (`id` or `template`); the snapshot gains `ops_rev`. Stop all (`halt`) stops every operation's
  call.
- Events, in `ops/events.jsonl` by `event_log`'s rules (a closed list, plain data; `EVENTS` gains them):
  `op_added` (op, template, version, device) · `op_prepared` (op, doubts, step, tier, effort, prompt_chars, tokens,
  cost, seconds) · `op_checked` (op, edited: the names corrected, again: bool, device) · `op_done` (op, alone, step,
  tokens, cost, seconds) · `op_failed` (op, step, acted) · `op_dropped` (op, from) · `op_not_right` (op, has_reason) ·
  `op_learned` (template, lines, step, tokens, cost) · `op_rules_answered` (template, take, has_reason) · `op_trust`
  (template, alone, why).
- `TERMS` gains `operations`, `operation`, `op_template`, `op_check`, `op_alone`, `op_rules` (§0).

## 12. Not in this spec
- **Sources fill templates** (decisions §50.4): an External listener that adds an operation from a mail that came in.
  The template is the contract they will fill; what a source starts keeps the reserve (spec 35 §6).
- Templates shared with a team (`.claude/skills/` of a project, the rules beside them); the person's templates first.
- A field's options read from the tool (the epics of a project as a select): v1 takes words and the prepare resolves
  them.
- Chains (one operation starting another), conditions, schedules: a template is one form, one prepare, one action.
- Undoing an action: the tools have no undo; **Not right** teaches, the link opens the item.
- Operations in Agents' or Review's windows; an operation on another harness than Claude.
- An operation put into a project's goal, or an idea made from an operation.

## Tests
- **A:**
  - templates: the person's and the built-in found, the person's winning by name; a skill without `orkboard.toml`
    skipped; a broken manifest listed with its problem and refused by `ops.add`; an unknown key ignored; `{key}`
    resolved from `ops.servers`, a missing server makes it unusable with its words; the version moves with `SKILL.md`
    and with `orkboard.toml`, not with `rules.md`;
  - the form: a required field missing and a choice off its options refused; `remember` prefills the last value;
  - the prepare (a stub CLI printing stream-json): its command allows only `[prepare] tools`, disallows the built-in
    tools, never names the action's tool in `--allowedTools`, starts in `ops/work/`, carries `--effort`,
    `--max-budget-usd` and `--no-session-persistence` only when the fake `--help` lists them; its prompt holds the
    skill without front matter, the rules and the fields, and stays within `CONTEXT`; a tool missing from `init`
    fails it before any answer is read; its answer: unknown keys dropped, `found` and `doubts` cut, every `at` written
    into `args`; no JSON fails it with `acted: false`;
  - the action: its command allows only `[act] tool`; one `tool_use` with equal input → `done` with `id` and `link`;
    none → `failed`, `acted: false`, Try again allowed; other input, another tool, two calls → `failed`,
    `acted: true`, no retry; a tool error → `failed` with its first line; Stop while acting → `acted: null`;
  - the way to by itself (pure functions and through the runner): `trust_after` 1 and 3; a clean check makes it go by
    itself; a correction, Not right, a new version and Check again send it back; Take of rules sends it by itself; a
    doubt, `risk = "high"` and the daily cap stop it at the check without changing `trust.json`;
  - rules: the learn call gets the before → after of each corrected field and part (or the Not right line) and the last 10
    declined, has no tools; a repeated or declined line dropped; at most 3; Take appends them, No writes
    `declined.jsonl`; one proposal per template; `rules_save` cleans headings and keeps `trust.json`;
  - the limits: a spent window holds a prepare with `held_until` and it runs when the window is back; no reserve on the
    person's own; at most 2 at once;
  - privacy: an operation's files are mode 600 under the person's folder; nothing of it in the repository, its
    `.orkcraft/logs/` or its event log; its calls under `ops/calls/`; after `keep_days` its texts and calls are gone and
    its row stays; the events hold no field's or draft's text;
  - Needs you: `op`, `op_failed`, `op_rules` in every project's snapshot; `op_rules` last and out of the count;
  - the phone may send `ops.*`; Stop all stops a running operation;
  - the built-in two: their manifests read, their fields and tools as §5; `pyproject.toml` ships them (a built wheel
    holds `ops_templates/jira-task/orkboard.toml`);
  - `tests/test_architecture.py` (`core` and `realm` never import `gui`), and the critical tests (CLAUDE.md "Alpha").
- **B:** browser tests at 1 440 × 900 against a stub host: Operations in the goal select of a project; New… lists the
  two and a template that is not connected with its words; the Jira form adds one, *preparing*, then its check: found,
  a doubt, Priority changed in place, Epic changed turns the button into Prepare again; **Create in Jira** → done with
  its link; a template that goes by itself shows *by itself* and Not right; a rules proposal taken in its row; the gear
  sets the Target and a server; Needs you shows an `op` row in another project too.
- **C:** the same at 390 × 844 as sheets; no horizontal scroll.
- Each part: the critical tests, the touched modules' tests (`test_settings.py`, `test_gui_ideas.py`,
  `test_board_alone.py`, `test_pwa.py` and the new modules' own) and `tests/test_gui_wording.py`.
