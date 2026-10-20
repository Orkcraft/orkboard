# Spec 44 — The week's pace: Low work spends the week's room, by day when the week is ahead, at night when it is not behind

The owner and the PM, 20 October (decisions §57). What the Board itself puts off to the night (a Low idea's draft, a
Low plan's start) waits for the night whatever the week says, and at night it may spend the week down to the night's
reserve. This spec reads the Claude week's **pace** — its share left against the share of the week still to come — and
lets that work go by day when the week is ahead, holds it at night when the week is behind, eases the day's reserve in
the hour before the five-hour window comes back, and keeps how much of each week was left unused. **Builds:** Claude ·
**Review:** full · P1.

**Built after spec 43** (all its parts merged; read specs 42 §13 and 43 §11 "As built" first: this spec adds to 42 F's
This week, `realm/board_week.py` and `ideas.week_work`, and to the Map's `waits`; the phone's cache is at v50).
**What it is, and is not:** it changes **when** work the Board put off may start, never **whether** work may start
without the person (`realm/idea_risk.py` `AUTOSTART` is not changed: medium and high risk wait for the person; High and
Normal of low risk start at once, as today). No new setting: it is part of *Start plans by themselves* (`autostart`).
No forecast of a burn rate. What the person put off (*Tonight*) is not moved.

Two parts, one branch each, in this order, each from `main` once the one before is merged (CLAUDE.md "Alpha", as
specs 42 and 43). **This file is the contract**; the rest is the builder's choice inside its files. **Change nothing
outside a part's files** but those §7 names.

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. The pace** | `spec/44-pace-backend` | §1–§4 | `realm/idea_target.py` (`week`, `pace`, the reserve per window, `gate`), `realm/ideas.py` (a state's `night_by`), `gui/ideas.py` (`ideas.add_idea` writes `night_by`), `gui/ideas_board.py` (`ideas.queue` and `pass_plan` write who put it off), `core/idea_night.py` (`pace_tick`; the night holds the Board's Low work when the week is behind), `core/idea_keeper.py` (its clock calls `pace_tick`), `core/idea_runner.py` (a hold of kind `week`; `by_pace` on a plan that started by day), `core/board_limits.py` (`week_reset`), `realm/event_log.py`, `realm/board_map.py` (`waits` kind `week`, `night_by`, `by_pace`), `realm/board_week.py` (This week's `week` and `last_unused`), `gui/ideas_roles.py` (a chip's `pace`), `realm/lexicon.py`; the tests of those modules today (`tests/test_idea_target.py`, the night's, the runner's, `tests/test_board_map.py`, `tests/test_board_week.py`, `tests/test_gui_ideas.py`), new `tests/test_week_pace.py` |
| **B. The words** | `spec/44-pace-faces` | §5 | `js/board/tracks.js` (`rowOf`), `js/board/maplayout.js` and `js/board/map.js` (a stop's wait), `js/shell/agents.js` (a chip), `js/board/cards.js` (This week), `pwa/shell-ideas.js` (`rowState`), `pwa/shell-map.js`, `pwa/shell-agents.js`, `pwa/shell-cards.js`, `pwa/sw.js` (`orkcraft-app-v51`); `tests/test_map_desktop_browser.py`, `tests/test_week_desktop_browser.py`, `tests/test_pwa_map39_browser.py`, `tests/test_pwa_week_browser.py`, the Agents browser tests of both faces, `tests/test_pwa.py` |

## 0. The words
- **the week** (no new term): the Claude tool's weekly window as `claude /usage` says it (`sources/limits.py` `Limit`
  with `provider` `claude` and `window` `weekly`): its share left and when it comes back.
- **the pace** (`pace`, *the week's pace*, A): the week's share left against the share of the week still to come:
  **ahead** (at least `MARGIN = 0.10` above it), **behind** (below it), else **even**.
- **put off by the Board** / **by the person** (no term: code only): who sent work to the night — the Board, for a Low
  idea's draft and a Low plan's start; the person, with *Tonight* or New idea's night.
- Today's words stay: *tonight*, *by itself*, *reserve*, *limits*, *Start plans by themselves*.

## 1. The pace (`realm/idea_target.py`)
No face, no model.
- `week(limits, now, provider="claude") -> {"left", "rest", "reset"} | None`: from the tool's `weekly` limit with a
  share and a reset read: `left` its `remaining`; `rest` the share of the week still to come, `(reset − now) / 7 days`,
  between 0 and 1; `reset` epoch seconds. `None` when there is no such limit (not read, an error, another tool, an API
  key): then every rule below is today's.
- `pace(limits, now) -> "ahead" | "even" | "behind" | None`: `ahead` when `left − rest ≥ MARGIN`, `behind` when
  `left < rest`, else `even`; `None` with no `week`.
- **The reserve, per window** (`reserve_held`): what starts by itself is held while **any** of the tool's windows has
  its share or less left — the day's (`reserve_day`) or the night's (`reserve_night`), as today — except that **by day,
  within `SOON_S = 3600` seconds of the five-hour window's (`session`) reset, and while the pace is not `behind`**, that
  window's share is the night's. With no window near its reset this is today's rule exactly (the smallest window
  against one share).

## 2. Who put it off (A)
- **An idea's draft**: `ideas.add_idea` queues a Low idea for the night as today and keeps `night_by: "board"` in its
  state; with `night: true` (the person's) `night_by: "person"`. `ideas.queue {queue: "night"}` (*Tonight*) keeps
  `"person"`. A state of before reads `"person"` (nothing written before this spec is moved).
- **A plan's start**: `pass_plan` with `night` keeps `start_at_by` on the plan: `"board"` when the Board passed it
  (autostart's Low), `"person"` when the person did. A plan of before reads `"person"`.
- Only what has `"board"` is moved by the pace (§3).

## 3. When it goes (A)
| when | the week's pace | the Board's Low draft (`queue: "night"`, `night_by: "board"`) | the Board's Low plan (`start_at: "night"`, `start_at_by: "board"`) |
|---|---|---|---|
| by day | `ahead` | drafted by `pace_tick`, one at a time per project, while the reserve holds | starts (the `gate` does not hold it for the night), the reserve as for any autostart; `by_pace: true` |
| by day | `even`, `behind`, `None` | waits for the night (as today) | waits for the night (as today) |
| at night | `ahead`, `even`, `None` | the night drafts it (as today) | starts (as today) |
| at night | `behind` | stays queued; the night drafts the rest | held: the `gate` answers the week's reset (a hold of kind `week`) |

- **`pace_tick(now)`** (`core/idea_night.py`, from the keeper's clock beside `night_tick`, at most every `PACE_S = 600`
  seconds, never inside the night window, never while a draft of the Board's Low is running in this project): when the
  pace is `ahead`, `autostart` is on and the reserve does not hold, it drafts the first Board's Low idea in the Board's order of the
  project (as the night's queue step does one). A Low idea it drafts keeps its plan's start as autostart decides: low
  risk passes it with `start_at: "night"` and `start_at_by: "board"`, which the `gate` then lets start by day while the
  pace is `ahead`.
- **At most one Board's Low plan running by day per project**: a second waits (for the night, or for the first to end).
- **The night when the week is behind**: its queue step leaves the Board's Low ideas queued; the person's are drafted as
  today. `night_run` gains `paced` (how many it left for the week).
- **Never moved**: what the person put off; a plan held for the person (medium or high risk, open questions); anything
  while `autostart` is off; High and Normal (they start at once, as today).

## 4. Data, events, payloads (A)
- `ideas.map`'s nodes: `waits` gains kind `week` (`until`: the week's reset) for the Board's Low plan or draft held at
  night by the pace; `night_by` (`"board"` | `"person"`) on a queued idea and a plan to start at night; `by_pace: true`
  on a plan that started by day by the pace. `ideas.board`'s rows carry `night_by` beside `queue` and `start_at`.
- `ideas.agents`' chips: `pace: true` on a task of a plan with `by_pace`.
- **`week_reset`** (new event, `core/board_limits.py`): when a read shows the weekly reset moved later than the one
  read before (the week came back), `{left: <the last share left read before it>, provider: "claude"}`, written once to
  the log of the project shown (none open: not written).
- **`task_state`** `running` of a task of a plan that started by day by the pace gains `by_pace: true` (`plan_passed` says nothing of the pace: a plan is passed before it starts, and may start at night).
- **This week** (`ideas.week_work`, spec 42 §6.2) gains `week`: `{"left", "rest", "pace", "reset"} | null` and
  `last_unused`: the newest `week_reset`'s `left` (`null` with none).

## 5. The words (B)
- **A row and a stop** (desktop `rowOf`, phone `rowState`, the Map's stops): a Board's Low idea or plan waiting for the
  night: *tonight, or sooner if the week has room* (*starts tonight, or sooner if the week has room* for a plan); the
  person's: *tonight* / *starts tonight*, as today. Held by the week (kind `week`): *waits: the week is behind · until
  Mon 09:00* (the reset in the faces' own words for a time, as the limits' resets are said).
- **An Agents chip** of a task started by the pace: *by itself: the week has room* (in place of *by itself*).
- **This week** (spec 42 §6.3), a line after the nights', when `week` is not `null`:
  - *The week: 55 % left with 2 days to go: Low work starts by day* (`ahead`);
  - *… : Low work waits for the night* (`even`);
  - *… : Low work waits until the week comes back* (`behind`);
  and, with `last_unused`, *Last week ended with 30 % unused*.
- Nothing else: no meter, no colour (a pace is not a signal), no toast when work starts by the pace.

## 6. Tests
- **A**: `week` and `pace` (ahead, even, behind at their edges; `rest` at a reset passed or a week away; `None` with no
  weekly limit, an error or another provider); the reserve per window equals today's rule with no window near its
  reset, and eases the five-hour window within `SOON_S` only while the pace is not `behind`; `night_by` and
  `start_at_by` written by each path and read as `"person"` from a state or plan of before; with a fake clock and fake
  limits: by day and `ahead`, `pace_tick` drafts the first Board's Low idea in the Board's order once, one at a time, not while the reserve
  holds, not with `autostart` off, not the person's; the `gate` lets the Board's Low plan start by day only `ahead`, one
  per project, and sets `by_pace`; at night and `behind`, the Board's Low plan is held with kind `week` until the reset
  and its draft stays queued while the person's are drafted; `night_run`'s `paced`; `week_reset` once when the reset
  moves; `ideas.map`'s `waits` `week`, `night_by`, `by_pace`; This week's `week` and `last_unused`; the Map's 200-idea
  timing still holds.
- **B** (browser, both faces): the two *tonight* wordings by `night_by`; *waits: the week is behind · until …*; the
  chip's *by itself: the week has room*; This week's three pace lines and *Last week ended with … unused*; no line
  without `week`.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_pwa.py`.

## 7. Files a part may need beyond its row
`gui/board_host.py` (A: only if the keeper's clock does not reach `pace_tick`), `realm/status.py` (A: a reset's helper),
`tests/test_shell_browser.py`'s `StubHost` and `tests/test_pwa_shell_browser.py`'s `Stub` (B: the new fields). Anything
else: stop and write it in §9 first.

## 8. Not in this spec
- A forecast of the week's burn; a pace for another tool (only Claude runs the Board's tasks, `core/idea_runner.py`
  `HARNESS`); moving High, Normal or the person's own night; a setting of its own; a pace for Operations (their own
  Target and day's cap stand).
- Holding High or Normal work when the week is behind (the reserve does what it does today).

## 9. As built (notes, no change of the contract)

### A. The pace
- `idea_target.week(limits, now, provider)` takes the tightest weekly window when a tool has several; `rest` is clamped to 0–1. `reserve_held` is the per-window rule (a copy of the old one is the oracle of `tests/test_week_pace.py`, which compares them on a grid); `pace` is `ahead` from `MARGIN` above the share to come (inclusive), `behind` below it, else `even`. `WeekHold` is a float (the week's reset): what `gate` answers for a hold of kind `week`. `board_low(plan, board)` and `by_pace(plan, limits, board, now)` are its helpers.
- The state keeps `night_by` (in `STATE_DEFAULT`, `""` before; `ideas.night_by_of` reads `""` as `"person"`); a plan keeps `start_at_by`. `ideas.add` sets `"board"` for a Low idea and `"person"` for any `night: true`; `ideas.queue` night sets `"person"`; `pass_plan` sets `start_at_by` (`"board"` for `by == "auto"`). `plan_passed` says nothing of the pace; the `running` lines of a `by_pace` plan's tasks carry `by_pace: true` (`IdeaRunner._note`).
- `pace_tick` (`core/idea_night.py`, from the keeper's `tick`) runs `run_pace` on a thread: it starts the Board's first Low plan waiting for the night (`start_night`) and drafts the first Board's Low idea, unless one is being drafted. *First* is the Board's order (`_rank`: the priority, then the person's order), not age. The gate does the rest: it lets the plan's tasks start by day and the runner marks the plan `by_pace` when it launches a task; a second Board's Low plan waits (`gate` = `"night"`) while another plan with `by_pace` is not finished. A held task of kind `week` (note *week · after HH:MM*) is let go as soon as the gate no longer answers a `WeekHold` (the pace changed), not only at the reset.
- The night leaves the Board's Low ideas when the week is behind and `autostart` is on; `night_run` carries `paced` (also `0`), the returned counts do not (they stay as they were). The Board's Low plan is started by the night as today, and held by the gate at night while the week is behind.
- `ideas.map`'s nodes carry `night_by` (only for a new idea waiting for the night and a plan to start at night; `""` otherwise), `by_pace`, and `waits` kind `week` with `until` as `YYYY-MM-DDTHH:MM` (the week's reset, local time) for work held at night by the pace; `ideas.board`'s rows carry `night_by`. `gui/ideas_map.py` now passes the host's limits (`Limit` rows) to `board_map.build` (it passed the page's own dicts, which `build` did not read) — outside A's file list, written here.
- `week_reset` is written by `BoardLimits._read` when the weekly reset read is more than a day later than the one before and a project is shown (the rows are read for the home folder when none is). This week's `week` carries `reset` in epoch seconds; `ideas.week_work` passes the host's limits.

### B. The words
- Rows: `night_by === "board"` reads *tonight, or sooner if the week has room* (idea) / *starts tonight, or sooner if the week has room* (plan), on the desktop (`rowOf`) and the phone (`rowState`); an empty `night_by` stays *tonight*, as the person's.
- Stops: `waitsWords` on both faces answers *waits: the week is behind · until Mon 09:00* for kind `week` (`dayAt`: short weekday and the time of the local `until`); `week` is a timed wait, so its chip carries the clock like the others.
- Agents: a chip with `pace: true` reads *by itself: the week has room* (desktop `shell-chip__tag`, phone `chip-why`).
- This week: `weekPace(w)` (in `cards.js` and `shell-cards.js`) gives *The week: 55 % left with 2 days to go: Low work starts by day / waits for the night / waits until the week comes back*, placed after the nights' lines; the days to go are `rest` × 7 rounded up (at least 1, *1 day*). *Last week ended with 30 % unused* follows when `last_unused` is set. No line when `week` is null. No meter, colour or toast.
- `sw.js` is `orkcraft-app-v52`. Tests: `test_week_desktop_browser`, `test_pwa_week_browser` (the lines, the row and wait words through the modules).
- `core/idea_task.py` has `_paced_elsewhere(slug)` (another plan of the project with `by_pace` is not finished: the runner holds a second Board's Low plan with `gate` = `"night"`) and `_mark_pace(slug)` (the plan says `by_pace` and, running, no longer `start_at: "night"`).

### Fix-ups after review
- `run_pace` skips an idea whose state has an `error` (as the keeper's own tick does) and tries the next; it starts a Board's Low plan only when no plan of the project with `by_pace` is unfinished (`NightMixin._paced_running`).
- A plan the pace starts is `by_pace: true` with `start_at` cleared (`run_pace` after `start_night`, and `_mark_pace` for a plan that starts through the runner's tick): the Map shows it as any working plan, and the one-at-a-time rule goes through `by_pace`.
- Only what is still Low is the Board's: `idea_target.board_low`, `by_pace` and `gate` take `low` (the runner asks its `rank`), `board_low_idea` in `core/idea_night.py` is the night's and the pace's test, and `board_map` reads `night_by` as `"person"` for a raised idea or plan. A raised one goes back to today's behaviour exactly.
- A night proposal taken as Low is queued with `night_by: "board"`.
- `plan_passed` no longer carries `pace`; the `task_state` `running` events of a `by_pace` plan's tasks carry `by_pace: true`.
- A draft left by the pace at night counts as `held` for the night's retry (`night.json` `held` is true when `paced` > 0).
- With no week read, a `week` wait has `until: ""` and both faces say *waits: the week is behind* alone.
- Browser tests: the chip's *by itself: the week has room* and the wait without a time, on both faces (`tests/test_week_desktop_browser.py`, `tests/test_pwa_week_browser.py`).
- A plan the pace started and the person stopped (`stopped`) holds no other: `_paced_running` leaves it out, as the runner does (it is no longer active), so the next Board's Low plan may go by day.
