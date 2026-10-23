# Spec 66 — Team briefs: Operations prepare the daily, the retro, the refinement and a 1:1, from the team's work

The owner, 23 October (decisions §79): *people management: following
Slack, git and Jira, finding team members' weak and strong sides, preparing 1:1s, dailies, retros and refinements.* It is
no project's goal: no code, no repository of its own, the same work whatever project is open, again every week. That is
Operations' (spec 38): the person's list, a template, a check, the person's folder. Two things Operations lacks: a
template that **prepares something to read** and does nothing outside (spec 38 has exactly one action), and one that comes
**on its own time** (spec 38 §12 leaves schedules out). So: **a template may be a brief — it reads, writes a page for the
person and stops; a brief may stand, prepared before the meeting; four built-in briefs (before the daily, the retro, the
refinement, a 1:1), read from the team's work: Jira, GitHub, the Slack channels the person names.** **Builds:** Claude ·
**Review:** full · P2.

**What it is, and is not — the line the owner asked about.** A brief is about **the work and the meeting**: what moved,
what is stuck, what was promised and what came of it, what to ask. It **never judges a person**: no strengths and
weaknesses, no score, no ranking, no comparison of people, no reading of a person's tone or mood, no counts of commits,
messages or hours as a measure of anyone, no direct messages, no private channels. Why, in one line each:
- **The law:** in the EU (and elsewhere) reading employees' messages to profile them needs a lawful basis, telling them,
  and often the works council; an automated judgement of people is a high-risk use. A tool for one manager cannot carry
  that.
- **The trust:** a team that learns a model reads their Slack for their weak sides stops writing in Slack.
- **The data:** commits and messages say little of how someone works; the number becomes the target.
- **Orkboard's own rule:** the Data reviewer holds every goal to *no personal data reaches a prompt unless the task needs
  it*; a brief needs the work, not a portrait.
The person's own view of their people stays theirs: their notes (a field, §4) go into the brief as they wrote them, and
nothing in Orkboard adds to them.

Three parts, in this order; B and C branch from A and share no file.

| part | builds | files (and their tests) |
|---|---|---|
| **A. Backend** | §1–§6, §8 | `realm/op_templates.py` (`[brief]`, `people`, `reads`, `follow`, `[[prepare.bound]]`), `realm/op_runs.py` (a brief's way, a follow kept, forget), `core/op_runner.py` (the brief's prepare and keep; the bound check; standing briefs on the tick), new `realm/op_standing.py`, `gui/ops.py` (the commands), `settings.py` (`OPS`), `realm/event_log.py`, `realm/lexicon.py`, new `ops_templates/daily-brief/`, `ops_templates/retro-brief/`, `ops_templates/refinement-brief/`, `ops_templates/one-on-one/` (each `SKILL.md` and `orkboard.toml`); new `tests/test_ops_briefs.py` |
| **B. Desktop** | §7 on the desktop | `js/shell/opdialog.js` (the form's *Reads* line, *Prepare before*), `js/shell/opcheck.js` (a brief's check: **Keep**), `js/board/ops.js` (a kept brief opened, standing briefs, Forget), `js/shell/shell.css`; new `tests/test_ops_briefs_desktop_browser.py` |
| **C. Phone** | §7 on the phone | `pwa/shell-ops.js`, `pwa/shell-forms.js`, `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_ops_briefs_browser.py` |

## 0. The words
`TERMS` gains: **brief** · *briefs* (`op_brief`: an operation that prepares a page to read and does nothing outside),
**standing brief** (`op_standing`: one prepared on its own time, before a meeting), **Keep** (the brief's check's
button), **Forget** (`op_forget`: removes everything kept of one person). The interface says *1:1*, *daily*, *retro*,
*refinement* as teams say them.

## 1. A brief (`realm/op_templates.py`)
- A manifest has **either** `[act]` (spec 38 §2) **or** `[brief]`, never both (*a template briefs or acts, not both*):

```toml
[brief]
label = "Keep for the 1:1"     # the check's button: what happens (≤ 60)
```

- A brief's way: `preparing` → `check` → `done` (**Keep**), or `preparing` → `done` when it goes by itself (§3). No
  `acting`, no `acted`, no link: its result is its draft. Its draft parts have no `at`; a field without `at` changed on
  the check is **Prepare again**, as today.
- **Keep** (`ops.keep {id, draft}`) saves the draft as corrected; a correction teaches as spec 38 §6–§7 (a clean keep
  counts, a corrected one asks the learn call), so a brief learns the person's way (*put the stuck items first*).
- A kept brief opens read-only, with **Copy** (Markdown). It is the person's alone: Orkboard never posts, sends or shows
  it to anyone (§9).
- `risk` stays: a brief does nothing outside, so its least is `low`; a `people` template (§2) is at least `medium`.

## 2. Templates about people (`people = true`)
A manifest key; the four built-in ones but `refinement-brief` carry it. For such a template, code — not only the skill —
holds the line of the header:
- **The prompt** of its prepare gains, after the rules, a fixed paragraph (`op_runner.PEOPLE_RULE`): *Write about the work
  and the meeting, never about a person: no strengths or weaknesses, no score, no ranking, no comparison of people, no
  reading of a person's tone or mood, no counts of commits, messages or time as a measure of anyone. Name people only as
  the owner or the author of an item, with its link. When the person's notes judge someone, keep them as written and add
  nothing.* The learn call (spec 38 §7) gets it too, and a proposed rule that asks for any of it is dropped by code when
  it holds one of `PEOPLE_WORDS` (*weak*, *strong side*, *rating*, *score*, *rank*, *performance*, *productive*,
  *lazy*, …: a short list in code, its tests the guard).
- **What it reads is said on its form:** `reads = "Jira: the project you name · GitHub: the repos you name · Slack: the
  channels you name, never direct messages"` (≤ 200), shown under the form's heading and in the template's row, with
  *Tell your team what it reads* beside it.
- **Bound reads** (`[[prepare.bound]]`): a read tool whose argument must be one the person named:

```toml
[[prepare.bound]]
tool = "mcp__{slack}__conversations_history"   # the builder pins the tool and its argument on the build day (spec 38 §5)
arg = "channel"
field = "channels"                              # the values named in this field, resolved by the prepare's own lookup
```

  The prepare's events (spec 38 §4: each `tool_use` and its input) are read: a bound tool called with an argument the
  field does not name (by id or name, as the lookup tool answered it) fails the brief before its answer is read,
  *it read a channel you did not name: nothing was kept*, and its call's kept output is removed. A `people` template
  with a Slack read tool and no bound on it is refused at load (*a brief about people reads only the channels named*).
- **Kept shorter:** its texts follow `ops.keep_days` (14) as any operation's, but a `follow` brief (§4) is kept until the
  next one for the same person replaces it, at most `ops.follow_days` (90).
- **Forget** (`ops.forget {template, value}` — the template's follow field's value, a person's name or handle): every
  operation of that template with that value, kept or not, its draft, fields and calls, removed now. The template's row
  has it; it asks once (*Forget everything kept about <value> in Before a 1:1? This cannot be undone.*).
- **Events** of a `people` template carry no field's value: never who, never a channel's name.

## 3. Standing briefs (`realm/op_standing.py`)
- **Prepare before…** on a brief's form (the form's own fields filled as for an add): the days of the week and a time
  (local), and *before* minutes (default 30). Kept as `ops/standing.json` (mode 600): `[{id, template, fields, days,
  at, before, last}]`, at most 12.
- On Operations' tick, at `at − before` of a listed day, the standing brief is added as `ops.add` adds one (its fields as
  saved), once a day (`last`). A brief added so is **not the person's own press**: it keeps the reserve (spec 35 §6, spec
  38 §1), held as any operation is, and said so on its row (*waits for limits: prepared when the window allows*).
- A machine asleep at that time adds it when it wakes, if the meeting's time has not passed; else it skips it (*skipped:
  the machine was off*), once.
- Its row in Templates: *Before the daily: weekdays 09:30*, **Change**, **Stop**.

## 4. Following a person or a team (`follow`)
`follow = "who"` in a manifest names a field: the prepare gets **the last kept brief of this template with the same value
of that field** (≤ 3 000 characters, after the rules: *Last time*), so a 1:1 starts from what was said and promised, a retro
from the last retro's actions. One kept per value (§2); the values compared as written, trimmed, ignoring case.

## 5. The four built-in briefs
Their tools are named as the servers list them on the build day (spec 38 §5): Atlassian's for `{jira}`, GitHub's for
`{github}`, Slack's for `{slack}`. Each prepare reads, changes nothing, answers spec 38 §4's JSON (`draft`, `found`,
`doubts`; no `args`).

| | **Before the daily** (`daily-brief`) | **Before the retro** (`retro-brief`) | **Before the refinement** (`refinement-brief`) | **Before a 1:1** (`one-on-one`) |
|---|---|---|---|---|
| people | yes | yes | no | yes |
| follow | — | `team` | — | `who` |
| fields | `team` (Jira project or board, `remember`) · `repos` (`remember`) · `channels` (`remember`) · `since` (choice *the last working day* · *yesterday*) | `team` (`remember`) · `sprint` (its name or dates, required) · `repos` · `channels` (`remember` each) | `team` (`remember`) · `which` (choice *the next sprint* · *the top of the backlog*) · `count` (choice 5 · 10 · 20) | `who` (required: their name as Jira and GitHub know them) · `notes` (long: your own, kept as you wrote them) · `repos` · `team` (`remember`) |
| draft | `brief` (long): **Moved** (done since, with links) · **Stuck** (an item not moved for 2 working days, a PR waiting for review over a day, a blocked ticket) · **Asked in the channels** (unanswered questions) · **To ask at the daily** (≤ 5) | `brief` (long): **The sprint in facts** (taken vs done, carried over, reopened, the median wait for a review) · **Last retro's actions** and what came of each · **What the channels said went wrong** (as items, with links, no names) · **Topics** (≤ 5, as questions to the team) | `brief` (long): per ticket: what it lacks (*Done when*, a size, a clear dependency), a likely duplicate, a question for the team; then the tickets ready as they are | `agenda` (long): **Their work since the last 1:1** (done, in work, reviews they gave; links) · **Where they got stuck** (items, not them) · **Last time** (what was said and promised, and what came of it) · **Your notes** (as written) · **To ask** (≤ 5 open questions about their work, their aims and what gets in their way) |
| reads | Jira: issues of the project changed since; GitHub: PRs and reviews of the repos; Slack: the channels' messages since | the same over the sprint, and the sprint's report | Jira: the sprint's or the backlog's first issues | Jira: issues they own or were on; GitHub: their PRs and reviews; Slack: none |
| doubts | the project or a repo not found; a channel not found | the sprint not found; no last retro to follow | a ticket in two sprints | the person not found in Jira or GitHub, or more than one |
| label | *Keep for the daily* | *Keep for the retro* | *Keep for the refinement* | *Keep for the 1:1* |

- **Before a 1:1 reads no Slack:** what someone writes in channels is not an agenda item about them; their work is in
  Jira and GitHub, and their own words are what they bring to the 1:1.
- The skills (`SKILL.md`) say the same as §2 in the person's way: facts with links, questions not conclusions, the
  person's language, nothing invented; *To ask* is about the work and what gets in its way.

## 6. Settings (`settings.py` `OPS`)
Gains `follow_days` (90; 14–365). `ops.set` takes it. The gear shows it as *Keep the last 1:1 brief for N days*.

## 7. Faces (B, C)
- **The form:** the *Reads* line and *Tell your team what it reads* under the heading of a `people` template; **Add**
  and, for a brief, **Prepare before…** (days as seven toggles, a time, *minutes before*).
- **A brief's check:** what was found, the doubts, the draft as an editable page (Markdown), **Keep** (`[brief] label`),
  **Prepare again**, **Drop**. No action's button.
- **Done:** a kept brief opens read-only with **Copy**; *by itself* when it went so; **Not right** as today.
- **Templates:** a brief's row says *prepares a page, does nothing outside*; standing briefs under it with **Change**,
  **Stop**; a `people` template's **Forget…** (a field for the value, the one question of §2).
- The phone: sheets; a long brief scrolls in its sheet; no horizontal scroll at 390 px.

## 8. Tests
- **A:** a manifest with both `[act]` and `[brief]` refused, with `[brief]` alone read; a brief's way without `acting`;
  Keep with and without a correction (clean counts, the learn call on a correction); a `people` template's prompt holds
  `PEOPLE_RULE`, its learn call's rule with *rating* dropped; `reads` shown in `ops.list`; a bound tool called with a
  channel not named fails the brief and removes its call's output; a `people` template with a Slack read and no bound
  refused at load; `follow` gives the last kept brief of the same value (case and spaces ignored) and keeps one per
  value, up to `follow_days`; Forget removes every operation and call of that value and no other; the events of a
  `people` template hold no field's value; a standing brief added at its time once a day, keeping the reserve, skipped
  when its meeting has passed; the four built-ins read, their fields, follow, bounds and tools as §5; the critical
  tests.
- **B** (1 440 × 900, stub host): Before a 1:1's form with its Reads line; its check with Last time and Keep; a kept
  brief opened and copied; Prepare before set and listed; Forget asks and removes.
- **C** (390 × 844): the same as sheets.
- Each part: the critical tests, the touched modules' tests (`test_settings.py`, the Operations' tests of spec 38),
  `tests/test_gui_wording.py`; C also `tests/test_pwa.py`.

## 9. Not in this spec
Strengths and weaknesses of people, a review of performance, a person's activity in numbers — never, by §2. A brief
shared with anyone: a brief is the manager's own, seen by them alone (the owner's call), never posted, sent or shown to the
teammate. Reading a calendar to find the meeting's time (needs the Calendar's server); a team's templates in a project's
`.claude/skills/` (spec 38 §12); other trackers (Linear, GitHub Issues) than Jira.

## 10. As built (notes, no change of the contract)

**A (backend).** Built in `realm/op_templates.py` (`[brief]`, `people`, `reads`, `follow`, `[[prepare.bound]]`, `bound`, `slack`, `same_value`), `realm/op_runs.py` (the run's `brief`, `standing`,
`follows`; `kept_briefs`, `last_kept`, `cut`, `remove`, `cut_calls`, `forget_value`; `forget_old` spares follow briefs; `new_rules(…, banned)`), new `realm/op_standing.py`, new `core/op_briefs.py` (`BriefsMixin`:
Keep, Forget, standing briefs, the bound check, `PEOPLE_RULE`, `PEOPLE_WORDS`; `core/op_runner.py` would have passed 600 lines, and re-exports them), `core/op_runner.py` (a brief's prepare, its prompt, the bound check, the
tick), `core/op_commands.py` (`add` takes `standing`; `act` refuses a brief), `realm/jobs.py` (`call_events` and `run_call` take `result_chars`, 2 000 as before), `gui/ops.py`, `settings.py`, `realm/event_log.py`,
`realm/lexicon.py`, the four `ops_templates/*/` (`pyproject.toml` already ships `ops_templates/**/*`; the wheel test now names all six); new `tests/test_ops_briefs.py`, 36 tests; `tests/test_op_templates.py` and
`tests/test_gui_ops.py` follow the six built-ins and the new commands. What the spec left open:
- **The manifest.** `[brief] label` (≤ 60) is the template's `act_label` too, so a face that shows `act_label` shows *Keep for the 1:1*. A brief's fields and draft parts with an `at` are refused (*a brief has no action*).
  A `people` template must say `reads` (≤ 200; refused without), and its `risk = "low"` is read as `medium` (raised, not refused). `follow` names one of a brief's fields. `[[prepare.bound]]`: `tool` and an optional
  `lookup`, each one of its `[prepare] tools`; `arg`; `field`, one of its fields; at most 6. **A Slack tool** is one whose `{key}` is `slack` or whose server is *for* Slack (`servers = { … = "Slack" }`): in a `people`
  template each must be a bound's `tool` or a bound's `lookup`, else *a brief about people reads only the channels named*.
- **The bound check.** A field's values are split on commas, semicolons and spaces, `#` and `@` left off, case ignored. A bound tool's argument passes when it is one of them, or an id the `lookup`'s answer pairs with
  one of them (each object with `id` and `name` in its JSON; read by pattern when the answer was cut). A call without the argument, or a list holding one value not named, fails it. It is read before the answer,
  also on a call that ended in an error. On a breach: every call of the operation keeps its line with `raw: ""`, `forgotten: true` and its file removed; draft, found, doubts and args emptied; `failed`,
  `acted: false` (Try again is offered: nothing was done outside). A prepare with bounds reads tool results up to 200 000 characters (`op_briefs.LOOKUP_CHARS`), as a channel list is long.
- **Keep** makes no call and is not refused at the cap. A kept brief: `state: "done"`, `acted: false`, `link: ""`, `done_at`; events `op_checked` then `op_kept`. By itself: `preparing` → `done`, `alone: true`,
  `op_kept` with `device: "alone"`; **Not right** works on it as on an action. `ops.act` on a brief: *A brief does nothing outside: Keep for the 1:1*.
- **The prompts.** A brief's prepare starts with `op_runner.BRIEF_LINE` and answers `BRIEF_SHAPE` (no `args`; an `args` it gives is not kept). Order: the skill, its rules, *About people* (`PEOPLE_RULE`), *Last time*,
  the fields, the draft parts, the tools, today, the shape. The learn call of a `people` template has `PEOPLE_RULE` after its rules; a proposed rule matching `PEOPLE_WORDS` (a word's start, case ignored:
  *weak*, *strength*, *rating*, *score*, *rank*, *performance*, *productive*, *lazy*, *mood*, *attitude*, …) is dropped.
- **Follow.** *Last time* is `Kept <date>.` and each draft part as `label:` + text, ≤ 3 000; *(none kept yet)* when there is none or the last is older than `ops.follow_days`. The run keeps `follows`: the id it
  started from. When a follow brief is kept (by the person or by itself), the older kept ones of the same value are cut at once to spec 38's kept row (one per value); `forget_old` spares the last kept one of
  each value until `follow_days`, every other brief following `keep_days`.
- **Forget** is offered for a template with `follow` (the row's `forget`): `daily-brief` follows no field, so it has none, and its texts go after `keep_days`. It removes the operations' files (kept or not) and
  their calls' files, the standing briefs of that value, the value remembered for the form, and a waiting learn call or rules proposal that came from one of them. Refused while one of them is queued or
  running (*A brief of theirs is being prepared: stop it, then Forget*). A brief already cut (replaced) holds no value and is not counted. Event `op_forgot` (template, runs, standing): never the value.
- **Standing briefs.** `days`: Monday 0 … Sunday 6; `at`: `HH:MM`, local; `before`: 0–240 minutes, 30 when not given; at most 12. Set or changed after today's meeting, `last` is today (no skip said).
  `runner.standing()` runs on each tick (20 s), before the window's check, with `runner.clock` (local now). Added with `device: "standing"` and the run's `standing` = its id; not refused at the cap
  (held instead); held while `idea_target.reserve_held` holds (the machine's `ideas` reserves), with `why` *waits for limits: prepared when the window allows*. A meeting passed: `skipped` = *skipped: the
  machine was off*, once; a template that cannot be used then: *skipped: <why>*. `skipped` is "" again at the next add. Events `op_standing` (standing, template, what: set · changed · stopped · added ·
  skipped, device).
- **The MCP tools** are named as their servers document them, and must be checked against `claude mcp list` and one prepare's `init` on the owner's machine (spec 38 §5); the manifests are the one place
  they are written. Jira: the Atlassian Rovo server (`getAccessibleAtlassianResources`, `getVisibleJiraProjects`, `searchJiraIssuesUsingJql`, `getJiraIssue`, `lookupJiraAccountId`). GitHub: GitHub's
  server, github/github-mcp-server (`list_pull_requests`, `search_pull_requests`, `pull_request_read`, `search_users`). Slack: the reference server, @modelcontextprotocol/server-slack
  (`slack_list_channels` as the lookup, `slack_get_channel_history` and `slack_get_thread_replies` bound by `channel_id`). With Slack's own newer server, the Slack names and the bound's `arg` change.

The shapes B and C read (spec 38 §11's table, continued):

| command | args | returns |
|---|---|---|
| `ops.keep` | `{"id", "fields"?, "draft"}` | `{"ok": true}`; a changed field: *<label> changed: Prepare again first* |
| `ops.forget` | `{"template", "value"}` | `{"removed": n}`; *<title> follows no one: nothing is kept by name* · *Say whose: <label>* |
| `ops.standing_add` | `{"template", "fields", "days": [0–6], "at": "HH:MM", "before"?: 0–240}` | `{"id"}` (`st-…`); *Pick the days of the week it is prepared on* · *The meeting's time is HH:MM* · *Minutes before is 0 to 240* · *At most 12 standing briefs: stop one first* · the form's own refusals |
| `ops.standing_change` | `{"id", "fields"?, "days"?, "at"?, "before"?}` | `{"ok": true}` |
| `ops.standing_stop` | `{"id"}` | `{"ok": true}` |
| `ops.set` | gains `"follow_days"` (14–365) | the `ops` settings; *Keep the last 1:1 brief for 14 to 365 days* |

- `ops.list`'s templates gain `brief`, `people`, `reads` ("" when none), `follow` (a field's name or ""), `does` (a brief only: *prepares a page, does nothing outside*), `forget` (only with `follow`:
  `{"field", "label"}`); `act_label` is the Keep label. Its runs gain `brief`, `standing` (the standing brief's id, or "") and `follows` (the id of the kept brief it started from, or ""); a held standing
  brief's `why` is the words above. It gains `standing`: `[{"id", "template", "fields", "days", "at", "before", "last", "skipped", "title", "words"}]`, `words` the row (*Before the daily: weekdays 09:30*;
  *every day*, *weekends*, else *Mon, Wed*). `settings` gains `follow_days`.
- A brief at its check is an `op` row of Needs you, as an operation's; the phone may send the five new commands (`ops.*`).

**C (phone)** (`orkcraft-app-v72`). Built to §7 on the phone as sheets, in `pwa/shell-ops.js` (`openForm(t, stand)`, `openKept`, `openForget`, `standingRow`, `readsLine`, `markdown`, `copyText`), `pwa/shell-forms.js`
(`daysSwitch`, `DAYS`), `pwa/app.css` (`.ops-reads`, `.ops-before`, `.pills.days`, `.ops-standing`, `.ops-kept`, `.ops-page`), `pwa/sw.js` (`CACHE` v71 → v72, with the pins of `tests/test_pwa.py` and the eight phone browser
tests that pin it); new `tests/test_pwa_ops_briefs_browser.py`, 4 tests (its state extends `test_pwa_ops38_browser.py`'s). No host shape was missing. What the spec left open:
- **The form.** A `people` template's `reads` stands under the form's heading as *Reads: …*, with *Tell your team what it reads* as a line under it (words, not a button); the template's row in Templates says the same, under `does`.
  A brief's form has **Prepare before…** above its foot: it opens the days (seven toggles, Mon–Fri on at first), *The meeting's time* (09:30 at first) and *Minutes before* (30), and their own button, **Prepare before each
  meeting** (`ops.standing_add` with the form's fields); **Add** stays in the foot. A refusal is said in the form, as `ops.add`'s.
- **A standing brief** is listed in its template's card with its `words` and its `skipped` line; **Change** opens the same form titled *Change: <title>*, its fields, days, time and minutes as saved, with **Save the change**
  (`ops.standing_change` with every field and the schedule) in place of Add; **Stop** stops it at once (`ops.standing_stop`; nothing to undo: it can be set again). A held run with no `held_until` says its `why` (a standing
  brief's *waits for limits: prepared when the window allows*), else *waits for limits*.
- **The check** of a brief: its title and the follow field's value (*Before a 1:1 · Anna*), a line *A page for you alone: Keep saves it, nothing is sent or done outside*, **Last time: kept 16 October** when `follows`
  names a kept brief still in the list (it opens that brief read-only over the check), found, doubts, the draft parts as 14-row boxes, the fields behind *Change what was asked*; the button is the `act_label` and sends
  `ops.keep {id, fields, draft}` with only what changed (as `ops.act` does), **Prepare again** when a field changed, **Drop**.
- **Done.** A kept brief's row says *<title> · <value>*, *kept <date>*, *by itself* when so, and **Open** (`Open the kept brief: …`) while its draft holds text (a brief cut to its row has none). Its sheet is read-only:
  *Kept <date> · <value> · by itself*, each part's text (its label as a heading when there are several), pre-wrapped and broken anywhere, the sheet scrolling down and never sideways, **Copy** pinned at its foot. Copy gives
  the one part as written, or `## <label>` and the text of each; the Clipboard API, else a hidden box and `execCommand("copy")` (the phone may be served without it).
- **Forget…** (only on a template with `forget`) opens *Forget: <title>*: a field labelled as the follow field, **Forget…** (empty: *Say whose: <label>*), then the spec's one question with **Forget it all** and **Cancel**;
  typing again takes the question back. The toast says *Forgotten: n briefs about <value>* or *Nothing was kept about <value>*.
- **The gear** shows *Keep the last 1:1 brief for N days* (14–365) when `settings` has `follow_days`.
