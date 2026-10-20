# Spec 42 — Coming back: what the orks did while you were away, the flag, notifications, a record, the way to by itself, this week, last week, nights in a row

The owner and the PM, 20 October (decisions §55). The Board says loudly what it costs, what waits and what failed, and
quietly what it did; the only reason to open it is Needs you, and that reaches the phone only while its page is alive.
This spec adds eight readers of what the Board already holds, each said once, in one place, closed by one press, and
the push that brings a waiting question and the morning to the phone. **Builds:** Claude · **Review:** full · P1.

**What it is, and is not** (§50.5, §55): every piece **reads** (the event log, the ledgers, the plans, the verdicts,
the trust files); none starts, holds, moves or opens work, and none has a setting of its own but C's. It rewards
**results and thrift** (merged, merged the first time, $ a merged result, a flag, a template that goes by itself),
never volume or spend. **No** points, levels, badges, leaderboards, sounds, confetti, a mascot that speaks, or a run of
the person's own: a day away costs nothing.

Eight parts, one branch each, **built in this order, each from `main` once the one before is merged** (CLAUDE.md
"Alpha": a part is merged when the critical tests, its files' tests, `tests/test_gui_wording.py`,
`tests/test_design_system.py`, `tests/test_pwa.py` and its browser tests pass). **This file is the contract** (names,
data, commands, words); the rest is the builder's choice inside its files. Wording: CLAUDE.md (today's words; the
product is *Orkline* in the interface; the pixel face never for a person's words; colour only for a signal). **Change
nothing outside a part's files**; a file this table does not name but a part cannot be built without is named in §12.

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. While you were away** | `spec/42-recap` | §1 | new `realm/board_recap.py`, `realm/idea_spend.py` (`between`), new `gui/ideas_recap.py` (a mixin), `gui/ideas.py` (the mixin, the command, `OPENED`, `VIA`), `realm/lexicon.py`, new `gui/static/js/shell/look.js`, new `gui/static/js/board/cards.js`, `js/board/map.js` (the card's place), `js/board/board.css`, new `pwa/shell-cards.js`, `pwa/shell-board.js`, `pwa/board.js` (the last look), `pwa/app.css`, `pwa/sw.js` (`SHELL`, cache `orkcraft-app-v37`); new `tests/test_board_recap.py`, new `tests/test_gui_recap.py`, new `tests/test_recap_desktop_browser.py`, new `tests/test_pwa_recap_browser.py`, `tests/test_pwa.py` |
| **B. The flag** | `spec/42-flag` | §2 | new `realm/goal_flags.py`, `realm/board_map.py` (a goal's `verdict.at`, `tally`), `gui/ideas_recap.py` (`ideas.flags`), `realm/lexicon.py`, `js/board/map.js`, `js/board/maplayout.js`, `js/board/board.css`, `pwa/shell-map.js`, `pwa/app.css`, `pwa/sw.js` (v38); new `tests/test_goal_flags.py`, `tests/test_board_map.py`, `tests/test_map_desktop_browser.py`, `tests/test_pwa_map39_browser.py`, `tests/test_pwa.py` |
| **C. Notifications** | `spec/42-push` | §3 | new `gui/web_push.py`, new `gui/phone_push.py`, `settings.py` (`clean_phones` keeps `push`), `gui/board_host.py` (`BoardPhone.COMMANDS`, the `mobile.push_*` commands, the pusher's tick), `gui/phones.py` (which devices have a socket open), `realm/event_log.py`, `realm/lexicon.py`, new `pwa/shell-push.js`, `pwa/shell-drawer.js`, `pwa/board-app.js`, `pwa/sw.js` (`push`, `notificationclick`, v39); new `tests/test_web_push.py`, new `tests/test_phone_push.py`, `tests/test_phones.py`, `tests/test_mobile.py`, new `tests/test_pwa_push_browser.py`, `tests/test_pwa.py` |
| **D. An agent's record** | `spec/42-record` | §4 | `gui/ideas_roles.py` (`record`), `realm/lexicon.py`, `js/shell/agentdialog.js`, `js/shell/shell.css`, `pwa/shell-agent.js`, `pwa/app.css`, `pwa/sw.js` (v40); `tests/test_gui_ideas.py` (or the file that tests `ideas.roles` today), `tests/test_shell_browser.py` or a new `tests/test_record_desktop_browser.py`, `tests/test_pwa_agents36_browser.py`, `tests/test_pwa.py` |
| **E. The way to by itself** | `spec/42-trust` | §5 | `realm/op_runs.py` (`alone_since`, `done_alone`), `gui/ops.py` (a template's row), `js/board/ops.js`, `js/board/board.css`, `pwa/shell-ops.js`, `pwa/app.css`, `pwa/sw.js` (v41); the tests of `op_runs` and `gui/ops.py` today, `tests/test_ops_desktop_browser.py`, the phone's Operations browser test, `tests/test_pwa.py` |
| **F. This week** | `spec/42-this-week` | §6 | new `realm/board_week.py` (`nights`, `this_week`), `realm/idea_spend.py` only if `between` needs a sibling, `gui/ideas_recap.py` (`ideas.week_work`), `realm/lexicon.py`, `js/shell/topbar.js`, `js/shell/dialogs.js`, `js/board/cards.js`, `js/shell/shell.css`, `pwa/shell-drawer.js`, `pwa/shell-cards.js`, `pwa/app.css`, `pwa/sw.js` (v42); new `tests/test_board_week.py`, new `tests/test_week_desktop_browser.py`, new `tests/test_pwa_week_browser.py`, `tests/test_pwa.py` |
| **G. Last week** | `spec/42-last-week` | §7 | `realm/board_week.py` (`last_week`), `gui/ideas_recap.py` (`ideas.week`), `realm/lexicon.py`, `js/board/cards.js`, `js/shell/look.js`, `js/board/map.js` (the foot's link), `pwa/shell-cards.js`, `pwa/shell-board.js`, `pwa/shell-drawer.js`, `pwa/sw.js` (v43); `tests/test_board_week.py`, `tests/test_week_desktop_browser.py`, `tests/test_pwa_week_browser.py`, `tests/test_pwa.py` |
| **H. Nights in a row** | `spec/42-nights` | §8 | `realm/board_week.py` (`streak`), `gui/ideas_recap.py` (`nights` on three payloads), `realm/lexicon.py`, `js/board/cards.js`, `pwa/shell-cards.js`, `pwa/sw.js` (v44); `tests/test_board_week.py`, `tests/test_gui_recap.py`, the A, F and G browser tests, `tests/test_pwa.py` |

Each part that changes a file of the phone's app moves `pwa/sw.js`'s `CACHE` up by one (the versions above) with
`tests/test_pwa.py`'s pinned version, and a new `.js` the app serves goes into `sw.js`'s `SHELL` (`tests/test_pwa.py`
checks both). Each part writes its "as built" notes into §13 when it differs from this file in a way a reader would
notice, as spec 41 §12.

## 0. The words
New `TERMS` (`realm/lexicon.py`), each with the part that adds it; the interface says them as written here, the
Markdown and the tests too.
- **While you were away** (`recap`, A): the card of what the Board did since this device's last look.
- **the last look** (no term: code only): when the person last pressed, typed or had the page in front of them, kept
  per device and per project (§1.3).
- **a flag** (`flag`, *flag* / *flags*, B): a goal accepted by its leader against its metrics (`realm/goal_verdict.py`,
  `met`); **Flags** the list of a project's flags. *Not met yet* is a verdict, not a flag.
- **a tally** (no term: code only): a goal's numbers under its flag (§2.1).
- **a notification** (`notification`, *notification* / *notifications*, C): a push to a paired phone.
- **a record** (`record`, *record*, D): what an agent did in the last 30 days.
- **This week** (`this_week`, F): the work of the last seven days, at API prices, beside today's spend.
- **Last week** (`last_week`, G): the card of the week before this one, Monday to Sunday.
- **nights in a row** (`nights_in_a_row`, H): the Board's nights with work done, one after another, up to last night.
- **merged the first time** (today's words, spec 36): a task merged in round 1, not sent back by the person; the gate's
  own retry inside the round still counts as the first time.
- **a result** (today's word): a task's work that reached Review; *in dev* is said with the Board's own merge branch
  (`merge_into`, default `dev`): *in main* on a Board that merges into `main`.

## 1. While you were away (A)

### 1.1 The data: `realm/board_recap.py`
No face, no model, writes nothing. `build(root, state_dir, since, now, rows) -> dict`:
- `since`, `now`: aware datetimes. `rows`: the current `ideas.board` rows (`ideas`) and `tracks`, for titles and short
  names (a deleted idea or goal is left out of every list).
- It reads `event_log.read(root, since=<since in the log's own format>)` (local ISO with offset, `event_log.line`) and
  the ledgers through `idea_spend.between(state_dir, since, now)` (new: the $ of every ledger line whose `at` is in
  `[since, now)`; `None` when every such line is unpriced, `0.0` when there is none; the ledgers' `at` is local and
  naive: read as local time). A helper `when(text) -> datetime | None` reads both forms; the module never compares
  times as text.

```json
{"since": "<iso>", "hours": 9, "into": "dev",
 "merged": {"tasks": 5, "first_time": 4,
            "ideas": [{"slug", "short", "title", "goal", "done": true}]},
 "flags": [{"goal", "short", "title", "met": true, "by": "Product manager"}],
 "night": {"drafted": 2, "started": 1, "refreshed": 0, "proposed": 2} | null,
 "proposed": [{"slug", "short", "title", "goal"}],
 "failed": [{"slug", "short", "title", "task": "<the task's short name>"}],
 "usd": 4.2 | null,
 "nights": 0,
 "waits": {"you": 1, "review": 3},
 "empty": false}
```
- **merged**: `task_state` events with `state: "merged"` in the period (both the person's merge and a result that lands
  by itself write one); `first_time` those with `round` ≤ 1; `ideas` the distinct ideas of those tasks, in the order of
  their first merge, `done` when the idea's state is `done` now.
- **flags**: `goal_accepted` events in the period, the last per goal; `met` and `by` as written.
- **night**: the sum of the period's `night_run` events' `drafted`, `started`, `refreshed`, `proposed`; `null` when
  there is none or all four are 0.
- **proposed**: `proposal_made` events in the period whose idea is still `proposed` now.
- **failed**: `task_state` events with `state: "failed"` in the period whose task is still `failed` now (a task fixed
  since is not said).
- **usd**: `idea_spend.between`, rounded to cents.
- **nights**: 0 here; H fills it (§8).
- **waits**: `you` the snapshot's `needs_you` (the rows that wait for an answer, Operations' included; proposals never),
  `review` its `review_count`; the command fills both from the host.
- **into**: the Board's merge branch (`merge_into`).
- **empty**: true when `merged.tasks`, `flags`, `proposed` and `failed` are all empty or 0 and `night` is `null`.
  `waits` and `usd` alone never make a card.

### 1.2 The command (A)
| command | args | returns |
|---|---|---|
| `ideas.recap` | `{"since": <ms since the epoch>}` | §1.1's object |

- `since` is required, a number; one older than 30 days is taken as 30 days ago; one ahead of now is refused (*`since`
  is ahead of now*). Callable from the phone (`ideas.*`). With no project open: *Open a folder first*, as the other
  `ideas.*`.
- `gui/ideas_recap.py` is a mixin as `gui/ideas_map.py`; B, F, G and H add their commands to it.
- `ideas.log`'s `opened` (`gui/ideas.py` `OPENED`, `VIA`): `what` gains `recap`, `flag`, `week`, `push`; `via` gains
  `recap`, `week`, `flags`, `push`. No other event is logged from a face.

### 1.3 The last look (A)
- **The desktop** (`js/shell/look.js`): per project, `orkboard.look.<the same 12 characters as orkboard.tabs.*>` holds
  the time in ms. It is written: on a press or a key in the page while it is visible, at most once a minute; on
  `visibilitychange` to hidden and on `pagehide`. Read and written in try/catch; the page works without it.
- **The phone** (`pwa/board.js`): the same, as `orkboard.look.<the snapshot's project>`.
- **Away**: `AWAY_H = 6`. When the page becomes visible, when it starts, when the project shown changes, or on the first
  press or key after a quiet spell, and the last look is 6 hours ago or more, the face calls `ideas.recap {since: the
  last look}` and then writes the last look as now. **A device that has no last look** writes it and shows nothing.
- The card shows when the answer is not `empty`; it is not shown again for the same period (the last look moved).

### 1.4 The card (A)
- **Where**: the desktop, at the top of the Map (`MapView`, above the goals; on a narrow window too); the phone, at the
  top of the Board tab, above the Map's section. One card at a time (G's comes first, §7.3). It never covers the work:
  no backdrop, no dialog, nothing moves.
- **Look**: an `.ork-card` with `aria-label="While you were away"`; its head in the pixel face, *While you were away ·
  9 h* (*· 2 days* from 48 hours); its lines in the text face, in this order, each only when it has something:
  1. *5 results in dev, 4 the first time* (*1 result in dev, the first time*; *1 result in dev*), and under it the
     ideas by their short names, each a link, *· done* after one that is done; at most 5, then *and 3 more*.
  2. *Flag raised: Offline mode, met, says Product manager* for a met goal; *Offline mode: not met yet, says Product
     manager* for one that is not. A link to the goal.
  3. *The night: drafted 2 ideas, started 1 plan, read 1 goal again, proposed 2 ideas* (only the parts above 0).
  4. *Proposed for you: Retry queue, Export CSV*, a link to Needs you.
  5. *Failed: Retry queue · The table* (the failure's words stay where they are: in Needs you and the idea), in the
     error tone (a signal).
  6. *≈$4.20 of work at API prices, not your bill.*
  7. (H) *5 nights in a row with work done.*
  8. *Waits for you: 1 answer, 3 results to check*, a link to Needs you; *Nothing waits for you* when both are 0.
- **Close**: one quiet button, *Close* (`.ork-btn quiet`), and Esc while the focus is in the card. Closing writes
  nothing (the last look already moved).
- **A click** on an idea opens it (desktop: the passing tab, spec 39 §3.3; phone: the idea's screen) and logs `opened`
  `{what: "idea", ref, via: "recap"}`; on a flag, the goal; on *Waits for you* or *Proposed*, Needs you (the desktop's
  Needs you tab, the phone's).
- **Logged** when shown: `opened` `{what: "recap", ref: "<hours>h"}`.

## 2. The flag (B)

### 2.1 The data: `realm/goal_flags.py`
No face, no model, writes nothing.
- `tally(root, state_dir, goal) -> {"ideas", "results", "first_time", "usd", "days"}`: the goal's ideas that are
  `done`; the tasks of their plans that are `merged`; of those, `round` ≤ 1; `idea_spend.of_goal(...)["usd"]` (`null`
  when unpriced, never 0); whole days from the goal's start to its verdict's `at` (at least 1), where the start is the
  oldest of: the goal's first `goal_saved` event with `new: true`, the first line of its ledger
  (`goals/<slug>/spend.jsonl`), the first line of its ideas' ledgers; `null` when none is known.
- `flags(root, state_dir) -> [{"goal", "title", "short", "by", "at", "tally"}]`: every goal (General never) whose
  verdict is `met`, newest `at` first.
- `realm/board_map.py`: a goal's `verdict` gains `at` (as kept), and a goal whose verdict is `met` gains `tally`.

### 2.2 The command (B)
| command | args | returns |
|---|---|---|
| `ideas.flags` | `{}` | `{"flags": §2.1's list}` |

### 2.3 The flag raised (B)
- **Once per device**: the desktop keeps `orkboard.flags.<12 characters>` (a list of goal slugs whose flag it raised),
  the phone `orkboard.flags.<project>`. When the Map draws a goal whose `verdict.met` is true and its slug is not in the
  list, its trail's flag is **raised**: the flag mark moves up from the foot of its box to its place in six steps over
  0.6 s (`steps(6)`, a transform; a keyframe of `board.css` / `app.css`, named `map-flag-raise`), then the slug is
  added. **Under `prefers-reduced-motion: reduce`** nothing moves; the slug is added all the same.
- Only while the trail is on screen (the Map's tab shown and the page visible; on the phone, the goal chosen); a goal
  accepted while its section is folded is raised when it is unfolded.
- **A device with no list** (the first start after this part) adds every met goal without raising any.
- **The tally** stays under a met goal's flag words, in the text face, muted: *7 ideas · 23 results · 19 the first time
  · ≈$38 · 9 days* (a part that is `null` is left out). Not met: no tally.
- **Logged** when raised: `opened` `{what: "flag", ref: "<goal slug>"}`.

### 2.4 Flags (B)
- At the foot of the Map, after the goals, a fold **Flags (3)** when there is at least one (closed at first, remembered
  per device with the Map's folds). Each row: the flag mark, the goal's title (text face), *met, says Product manager ·
  18 October*, the tally. A click opens the goal and logs `opened` `{what: "idea", ref: "goal:<slug>", via: "flags"}`.
- The phone: the same fold at the foot of the Map's section.
- The data: `ideas.flags` when the fold is opened, not with every Map read.

## 3. Notifications (C)

### 3.1 What goes, and when (`gui/phone_push.py`)
A pusher ticked by the host's clock (at most every 30 s), off the event loop (a worker thread for every send). It
sends to each paired phone that has a subscription (§3.3):
1. **An answer waits** (tag `needs`): when the number of rows waiting for an answer — the snapshot's `needs_you` of
   every open project (Operations' counted once), proposals and results to check never — is above the number this
   device was last told, and **the device has no socket open** (an open page says it itself). Body: one row, the first
   of the current project's Needs you that waits for an answer: its kind's words (*A spec asks*, *A plan waits for
   you*, *A to-do*, *Failed*, *A goal asks*, *At your check*: the words of `js/board/today.js` `KIND_WORDS`, kept in
   one Python table) and its short name (`idea_words.short_of(title)`): *A spec asks · Offline mode*; with more,
   *3 wait for your answer · A spec asks · Offline mode*. `badge` the number, `url` `./#needs`. At most one per device
   every `PUSH_GAP_S = 900` seconds; the tag replaces the one before on the phone. When the device opens a socket, its
   told number becomes the current one.
2. **The morning** (tag `recap`): once a day per device, at the first tick after the quiet hours end, when the device
   was not seen (its pairing record's `seen`) since the quiet hours began, and §1.1's `build` since its `seen`, summed
   over the open projects, is not `empty`: *While you were away: 3 results in dev, 1 flag raised, 2 ideas proposed ·
   1 waits for your answer* (only the parts above 0; *and nothing waits for you* when nothing does). `url` `./`. The
   day it was sent is kept in the device's subscription (`morning`, a date), so a restart does not send it twice.
3. **Never**: in the quiet hours (`schedule.quiet_now`), under Do not disturb (`dnd_until` `on` or a time ahead), for a
   proposal, a result to check, a merge, a spend or a limit; to a device whose socket is open; more than one push per
   tag per device every `PUSH_GAP_S`.
- **The quiet hours** are the machine's `quiet` (`MachineSettings.quiet`, `schedule.py`); a phone that turns
  notifications on while `quiet` is `None` sets it to `DEFAULT_QUIET` (23:00–09:00) and says so (§3.4).
- **The words** of a push are the Board's (kinds, short names, counts); never a question's text, a spec's, a mail's or a
  template's field.
- **Gone**: a send answered 404 or 410 drops that device's subscription (`push_sent`'s `gone`).

### 3.2 Sending (`gui/web_push.py`)
No new dependency: `cryptography` (the `[gui]` extra that pairing a phone already needs), imported lazily as
`gui/phone_tls.py` does; without it every `mobile.push_*` answers *Notifications need the cryptography package: pip
install 'orkboard[gui]'*.
- **The key**: a P-256 key made once, `push.key` beside `phone.key` (`settings.path().parent`), 0600, written as
  `phone_tls._write_private` writes; `public_key() -> str` its uncompressed point, base64url without padding.
- **The message**: RFC 8291 (`aes128gcm`, RFC 8188, one record) of the JSON `{"title": "Orkline", "body", "tag",
  "badge", "url"}`, at most 1 KB before it is sealed. `seal(payload, p256dh, auth, salt=None, key=None) -> bytes`
  takes a salt and a sender key only for the tests.
- **VAPID** (RFC 8292): `Authorization: vapid t=<JWT>, k=<public key>`, the JWT ES256 with `aud` the endpoint's origin,
  `exp` 12 hours ahead, `sub` `https://github.com/orkWorks/orkBoard`.
- **The request**: `urllib.request` POST to the endpoint with `Content-Encoding: aes128gcm`, `Content-Type:
  application/octet-stream`, `TTL: 43200`, `Urgency: normal` (`high` for `needs`), `Topic: <tag>`; timeout 10 s; the
  environment's proxy as `core/updates.py` has it. `send(sub, message) -> int` gives the HTTP status (0 when it never
  got one); it never raises into the host.

### 3.3 The subscription (C)
- A device's record (`settings.clean_phones`) keeps `push`: `{"endpoint": "https://…" (at most 1 024 characters),
  "p256dh": "<base64url>", "auth": "<base64url>", "at": "<iso>", "morning": "<YYYY-MM-DD>" | ""}`; anything else in it is
  dropped, a bad one drops `push`. Written with `settings.save_phones`. Forgetting a phone forgets its subscription with
  it.
- **Commands** (`BoardPhone.COMMANDS`; a phone only, its device's id given by `guard`; refused to the page):

| command | args | returns |
|---|---|---|
| `mobile.push_key` | `{}` | `{"key": "<base64url>", "quiet": "23:00-09:00" \| ""}` |
| `mobile.push_on` | `{"endpoint", "p256dh", "auth"}` | `{"ok": true, "quiet": "23:00-09:00"}` (sets `DEFAULT_QUIET` when `quiet` is `None`) |
| `mobile.push_off` | `{}` | `{"ok": true}` |
| `mobile.push_quiet` | `{"quiet": "HH:MM-HH:MM"}` | `{"ok": true}` (the machine's `quiet`) |

- **Logged** (the project's log, when a project is open; else nothing): `push_set` `{on, device: "phone"}`;
  `push_sent` `{tag, devices, gone}`.

### 3.4 The phone (C)
- **The drawer**, *This phone*, a row **Notifications** (`pwa/shell-push.js`), its state in words and at most one button:
  - no `PushManager` on an iPhone or iPad outside the Home Screen app: *Add Orkline to the Home Screen to get
    notifications here*; elsewhere without it: *This browser cannot show notifications from Orkline*;
  - off: **Notify this phone** and *When an answer waits, and once in the morning. Never in the quiet hours.* The tap
    asks `Notification.requestPermission()` (from the tap itself), then `mobile.push_key`, then
    `pushManager.subscribe({userVisibleOnly: true, applicationServerKey})`, then `mobile.push_on`;
  - on: *On · quiet 23:00–09:00*, the quiet hours as two time fields (as the night's) that write `mobile.push_quiet`,
    and **Turn off** (`subscription.unsubscribe()`, then `mobile.push_off`);
  - refused by the phone: *Notifications are off for Orkline in this phone's settings*;
  - the computer's refusal (no `cryptography`): its words.
- **On every connect** while on, the page sends its subscription again with `mobile.push_on` (an endpoint the browser
  renewed reaches the computer this way; no `pushsubscriptionchange` handler).
- **Unpair this phone** unsubscribes first (`unpairHere`).
- **The badge**: on every render the page sets `navigator.setAppBadge(needs_you)`, `clearAppBadge()` at 0, where the
  browser has it, in try/catch.
- **`sw.js`**: a `push` handler that shows `showNotification(title, {body, tag, icon: "icon-192.png", data: {url}})`
  for every push (a push always shows: iOS revokes one that does not) and sets the badge from `badge`;
  `notificationclick` focuses the app's window or opens `data.url`, with `#from=push-<tag>` so the page logs `opened`
  `{what: "push", ref: "<tag>"}` once and removes it from its address.

### 3.5 Not here
The desktop's own notifications; actions on a notification (an iPhone shows none); the working hours (`work`) holding
a push; any server of ours (each computer sends its own, with its own key).

## 4. An agent's record (D)
- `ideas.roles`: each role gains `record`: `idea_spend.by_role(state_dir, days=30)`'s row as
  `{"days": 30, "finished", "merged", "first_time", "usd_per_merged"}` (the Taskmaster's: `{"days", "plans",
  "finished", "first_time"}`); `null` for a role with no row.
- **Shown** in the agent's dialog (desktop `agentdialog.js`) and sheet (phone `shell-agent.js`), under its head and
  name, read only, in the text face:
  - with `finished` ≥ `idea_spend.TOO_FEW`: *The last 30 days: 41 tasks, 36 merged the first time · ≈$0.60 a merged
    result* (the price only when `usd_per_merged` is not `null`);
  - with fewer: *The last 30 days: 2 tasks: too few to say more*;
  - with none, or `null`: *No tasks in the last 30 days*;
  - the Taskmaster: *The last 30 days: 12 plans; of their 41 tasks, 36 merged the first time*.
- **Not on the agent's line** (decisions §54.6, spec 41 §12): the line and the muted week under it stay exactly as they
  are (the owner put the week back on 20 October, commit `8369511`: today's spend, from three merged a result's cost and
  the first-time share); the record is the dialog's and the sheet's only.

## 5. The way to by itself (E)
- **Kept** (`realm/op_runs.py`, the template's `trust.json`): `alone_since` (the date it went by itself; `""` while it
  checks with you) and `done_alone` (how many it did by itself since; 0 while it checks with you). `after_check` that
  reaches `alone` and `after_rules` set `alone_since` to today and `done_alone` to 0; `after_alone` adds 1 to
  `done_alone`; every move back to checking (`after_check` with an edit, `after_not_right`, `after_reset`,
  `after_version`) sets `""` and 0. A file of before reads them as `""` and 0.
- **Sent** (`gui/ops.py`, a template's row): `trust_after` (the setting), `alone_since`, `done_alone`.
- **Shown** on both faces' template rows:
  - checking: *Checks with you: 2 of 3 clean checks, then it goes by itself* with orkUI's `.ork-pips` (`trust_after`
    pips, `clean` of them filled); with `trust_after` 1: *Checks with you: one clean check and it goes by itself*;
  - by itself: today's line (*goes by itself: create the issue without asking you*) and *since 18 October · 12 done*
    (*since today* the day it went; nothing more while `done_alone` is 0), and Check again as today;
  - a high risk: as today (*always checks with you*), no pips.
- The phone shows `clean` too (today it does not).

## 6. This week (F)

### 6.1 The nights: `realm/board_week.py`
`nights(root, settings, now, n=7) -> [{"date": "YYYY-MM-DD", "kind": "worked" | "idle" | "off"}]`, the last `n`
nights that have ended, newest first, each the Board's night window (`night`, machine time; a window that crosses
midnight starts the evening before `date`):
- **worked**: a `task_state` event with `state` `review` or `merged` falls in the window, or a `night_run` event in the
  window has `drafted`, `started`, `refreshed` or `proposed` above 0;
- **idle**: a `night_run` event falls in the window and nothing worked;
- **off**: no `night_run` event in the window (Orkline was not running, or the night was turned off).

### 6.2 The data and the command
`this_week(root, state_dir, settings, now, rows) -> dict`, over the last 7 days:
```json
{"usd": 46.1 | null, "ops_usd": 3.2 | null, "merged": 12, "first_time": 10, "usd_per_merged": 3.84 | null,
 "nights": {"worked": 4, "idle": 2, "off": 1}, "tonight": 0, "night_on": true, "into": "dev"}
```
- `usd`: `idea_spend.between` over the 7 days; `ops_usd`: the same over Operations' ledger (`ops/spend.jsonl`), the
  person's, all projects; `merged`, `first_time`: as §1.1 over the 7 days; `usd_per_merged`: `usd / merged` when
  `merged` ≥ `idea_spend.TOO_FEW` and `usd` is not `null`.
- `tonight`: the ideas whose queue is `night` and the plans whose `start_at` is `night`, not started; `night_on`: the
  Board has a night window.

| command | args | returns |
|---|---|---|
| `ideas.week_work` | `{}` | §6.2's object |

### 6.3 Shown
- **The desktop**: today's spend in the top bar becomes a button (`aria-label` *Spend today: $1.20. This week's work*)
  that opens a dialog **This week** (a `Modal`, `KINDS` `this_week`).
- **The phone**: the drawer's *Spend today* row opens a sheet **This week**.
- **Lines**, in this order:
  1. *≈$46 of work at API prices in this project, ≈$3 in Operations: not your bill* (a `null` part left out);
  2. *12 results in dev, 10 the first time · ≈$3.84 a result*;
  3. *The last 7 nights: 4 with work done, 2 with none, 1 Orkline was not running* (parts at 0 left out);
  4. (H) *5 nights in a row*;
  5. with `night_on`: *Tonight: 2 wait* — or *Nothing waits for tonight* with a quiet link **New idea** (it opens New
     idea; a Low idea goes to the night). This is the only nudge in this spec.
- **Logged** when opened: `opened` `{what: "week", ref: "this"}`.

## 7. Last week (G)

### 7.1 The data and the command
`last_week(root, state_dir, settings, now, rows, week="") -> dict`, Monday to Sunday, machine time; `week` an ISO week
(`2026-W42`), default the last full one:
```json
{"week": "2026-W42", "from": "2026-10-12", "to": "2026-10-18",
 "merged": 23, "first_time": 19, "usd": 61.2 | null, "usd_per_merged": 2.66 | null,
 "before": {"merged", "first_time", "usd_per_merged"} | null,
 "goals": [{"goal", "short", "title", "done": 3}],
 "flags": [{"goal", "short", "title", "met", "by"}],
 "dearest": {"slug", "short", "title", "usd"} | null,
 "fastest": {"slug", "short", "title", "minutes"} | null,
 "answers": {"answers": 12, "recommended": 9, "decided": 2} | null,
 "nights": {"worked", "idle", "off"}, "streak": 0, "empty": false}
```
- `merged`, `first_time`, `usd`, `usd_per_merged`: as §6.2 over the week; `before` the same for the week before
  (`null` when it had no merged result).
- `goals`: per goal, its ideas that became `done` in the week (`keeper_state` `state: "done"`), goals with none left
  out.
- `flags`: `goal_accepted` in the week, the last per goal.
- `dearest`: the idea whose ledger lines in the week cost the most (at least $0.01).
- `fastest`: of the ideas whose first `task_state` `merged` falls in the week, the least time from its `idea_added` to
  that merge, in whole minutes.
- `answers`: the week's `idea_answered` and `goal_answered`: `answers` the sum of `answers`, `recommended` the sum of
  `recommended`, `decided` how many have `decided` true; `null` when there are none.
- `nights`: §6.1's seven nights of the week; `streak`: 0 here, H fills it.
- `empty`: no merged result, no flag and no idea done.

| command | args | returns |
|---|---|---|
| `ideas.week` | `{"week"?}` | §7.1's object |

### 7.2 The card
- In the place of §1.4 and in its look, `aria-label="Last week"`: its head *Last week · 12–18 October*; its lines:
  1. *23 results in dev, 19 the first time (83 %; the week before 71 %)*;
  2. *≈$2.66 a result (the week before ≈$3.10)*;
  3. *Goals: Offline mode, 3 ideas done · Billing, 1*;
  4. *Flags: Offline mode, met* (as §1.4's 2);
  5. *Cost the most: Offline mode, ≈$12 · Fastest from idea to dev: Export CSV, 42 min* (*3 h* from 120 minutes,
     *2 days* from 48 hours);
  6. *Questions: 9 of 12 answers were the recommended one; 2 cards left to the Taskmaster*;
  7. *Nights: 5 with work done, 2 with none* and (H) *· 5 in a row*;
  and *Close*. Links as §1.4 (an idea, a goal), `via: "week"`.

### 7.3 When it shows
- On the **first look of a new ISO week** on this device: the desktop keeps `orkboard.week.<12 characters>`, the phone
  `orkboard.week.<project>` (the last week shown). When the key is not last week and `ideas.week` is not `empty`, the
  card shows and the key becomes last week. **A device with no key** writes it and shows nothing.
- **With the recap**: when both are due, the week's card shows first; closing it shows the recap's (whose last look has
  not moved yet).
- **Any time**: the desktop's Map has a quiet link **Last week** at its foot (beside Flags); the phone's drawer a row
  **Last week**; both show the card at the top of the Map / the Board tab.
- **Logged** when shown: `opened` `{what: "week", ref: "2026-W42", via: "map"}` from the link, without `via` on the
  week's first look.

## 8. Nights in a row (H)
- `streak(root, settings, now) -> int`: §6.1's nights, from the last one that ended backwards, while each is `worked`
  (an `idle` or `off` night ends the run); at most 365.
- **Said only where the Board already speaks of its nights**, with no mark and no colour: the recap's line 7 (when it is
  2 or more), This week's line 4 (2 or more), Last week's line 7 (2 or more). Nothing is said when a run ends.
- `ideas.recap`'s `nights`, `ideas.week`'s `streak` and `ideas.week_work` (a new `streak` field) carry it.

## 9. Measured
- `opened` gains `what` `recap`, `flag`, `week`, `push` and `via` `recap`, `week`, `flags`, `push` (§1.2).
- New events (`realm/event_log.py` `EVENTS`): `push_set` `{on, device}`, `push_sent` `{tag, devices, gone}` (C).
- The owner reads after a week: the days the recap was shown and what was opened from it (`via: "recap"`); the first
  screen of each morning (decisions §52.4) on days with and without a morning push; the share of `push_sent` followed
  by an `opened` `what: "push"` within the hour; the flags raised; how often This week and Last week were opened.

## 10. Not in this spec
- Points, levels, badges, leaderboards, sounds, confetti, a mascot that speaks; a run of the person's own; any reward
  that opens, starts or moves work (§50.5).
- The record on an agent's line (§54.6); a record for an Operation's template beyond §5.
- The Camp skin (decisions §52.3).
- Notifications on the desktop; acting from a notification; a server that sends them.
- History beyond what the logs and ledgers already keep (`limits_read` stays as it is; no limits history is added).

## 11. Tests
- **A**: `board_recap.build` on a fixture log and ledgers: each list from its events, `first_time` by `round`, a
  deleted idea left out, a failure fixed since left out, a proposal taken since left out, `night` `null` when all 0,
  `usd` `null` when unpriced and 0.0 when none, `empty` (waits and usd alone are empty), times with and without an
  offset; `idea_spend.between`; `ideas.recap` from the desktop and the phone, *Open a folder first*, `since` clamped and
  refused; `opened` takes the new `what` and `via`. Browser (desktop, the stub host; phone, `_phone`): a device with a
  last look 9 hours ago gets the card at the top of the Map with its lines in order; 2 hours ago, none; no last look,
  none and the key written; Close removes it; a click on an idea opens it with `via: "recap"`; *Waits for you* opens
  Needs you; no horizontal scroll at 390 px.
- **B**: `tally` (ideas, results, first time, usd `null`, days from each start and `null`), `flags` (met only, newest
  first, General never); the Map's goal has `verdict.at` and `tally`; `ideas.flags`. Browser: a met goal not in the
  list is raised (`.is-raising`) once and its slug kept; under reduced motion (`page.emulate_media(reduced_motion=
  "reduce")`) no animation runs; a device with no list raises nothing; the tally's words; Flags (n) opens with its rows
  and a row opens the goal.
- **C**: `web_push.seal` against RFC 8291's Appendix A (the example's keys, salt and message give its body byte for
  byte; its values copied from the RFC, and only when they cannot be had, the round trip alone, said in §13) and a
  round trip with a receiver key made in the test; the VAPID JWT (header, claims, a signature the public key
  verifies); `send` with a stubbed opener (headers, 201, 410 gives `gone`); `clean_phones` keeps a good `push` and drops
  a bad one; the four commands (a phone only, `quiet` set when `None`); the pusher with a fake clock: a new answer to a
  device without a socket sends once, none to one with a socket, none in the quiet hours or under Do not disturb, none
  within `PUSH_GAP_S`, the morning once a day and not after the device was seen, a 410 drops the subscription; the
  words never hold a question's text. Browser (phone, `Notification` and `pushManager.subscribe` stubbed by an init
  script): Notify this phone sends `mobile.push_on` with the endpoint and keys; on, the quiet hours and Turn off; the
  Home Screen line without `PushManager`; the badge set. `tests/test_pwa.py`: `sw.js` has a `push` handler that always
  shows, `notificationclick` opens `data.url`.
- **D**: `record` on every role of `ideas.roles` (30 days, the Taskmaster's shape, `null`); browser: each of the four
  wordings in the dialog and the sheet; the agent's line and its muted week unchanged (`8369511`).
- **E**: the trust moves set and clear `alone_since` and `done_alone`; a file of before; the row's new fields; browser:
  the pips and their words, *since … · N done*, a high risk without pips, the phone's `clean`.
- **F**: `nights` (worked by a task or by a night run, idle, off, a window across midnight), `this_week` (`ops_usd`,
  `usd_per_merged` under `TOO_FEW` is `null`, `tonight`); browser: today's spend opens This week with its lines; *Nothing
  waits for tonight* and New idea; the phone's sheet from the drawer.
- **G**: `last_week` (the default week, `before`, `goals`, `dearest`, `fastest`, `answers`, `empty`); browser: the
  card on the first look of a week and not twice, after it the recap; the link and the drawer's row; a device with no
  key writes it.
- **H**: `streak` (a run, an idle night ends it, an off night ends it, today's night not counted until it ends); the
  three payloads carry it; browser: the line at 2 and not at 1.
- Every part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py` (no colour, font or corner of its own; a keyframe is allowed), `tests/test_pwa.py`.

## 12. Files a part may need beyond its row
Named here so a builder does not stop on them: `gui/static/js/shell/store.js` (A: the Needs you tab and the passing tab
from a card; B: the folds), `gui/static/js/shell/preview.js` (A: only if `MapView`'s place needs it),
`gui/static/js/board/today.js` (C: `KIND_WORDS`, read only, to keep the Python table in step), `gui/server.py` (C:
only if the pusher's tick cannot ride the host's), `gui/static/pwa/util.js` (A, G: a `localStorage` helper),
`tests/test_shell_browser.py` (its `StubHost` answering the new `ideas.*` commands), `tests/test_pwa_shell_browser.py`
(its `Stub` the same). Anything else: stop and write it in §13 first.

## 13. As built (notes, no change of the contract)

### A. While you were away
- `board_recap.build(root, state_dir, since, now, rows, into="dev")`: `root` is the project's folder (where `.orkcraft/usage/events.jsonl` is, as `ideas._ev` writes it), `rows` the `ideas.board` object (`ideas` and `tracks`), and `into` the Board's merge branch (`ideas.recap` passes `_into()`); the contract's five arguments stay as they are.
- `merged.tasks` counts every `merged` event of the period, a deleted idea's too; only the lists leave a deleted idea out. `failed` names each idea once per failed task.
- The desktop's `look.js` keeps the cards to show in a signal (`cards`), so Last week (G) can go ahead of the recap; the project's key is the tabs' (`store.js` `lookKey`), and a failed `ideas.recap` does not move the last look (it asks again at the next press).

### B. The flag
- `goal_flags.tally(root, state_dir, goal)`: `root` is the Board's tree (where the pages are); the event log it reads for a goal's first `goal_saved` is the project's, `state_dir`'s parent. The log is read again only when it changed.
- A flag is raised when its trail is on screen: an `IntersectionObserver` on the trail's end, with the page visible, so a trail scrolled out of sight (or on a tab not shown, or folded) waits. The desktop's Flags fold is remembered as `@flags:open` among the Map's folds kept with the tabs; the phone's is a `<details>` kept as `orkboard.map.flags.<project>`.
- The phone's Flags fold asks `ideas.flags` through `core.call`, and a raise logs `opened` through it too (no change to `board.js`).

### C. Notifications
- `schedule.DEFAULT_QUIET` is 23:00–08:00 (its own comment says so; the spec's 09:00 was a slip), so a phone that turns notifications on says *On · quiet 23:00–08:00*.
- **The morning** is sent at the first tick within 3 hours after the quiet hours end (`phone_push.MORNING_H`), so a computer that wakes at noon does not say "morning". Its line has a fourth part when something failed (*2 failed*) and says *the night's work* when only the night ran.
- **The pusher** lives on the Orkboard host (`host.pusher`, ticked by `host.tick`); the listener tells it about itself in `Listener.__init__` (`host.attach_phones`). A phone's `device_id` is added by `BoardPhone.guard` to `mobile.push_*` only; the page has none, so the page is refused (*Only a paired phone can do this*). A device met for the first time is told the current count, so a restart pushes nothing old.
- **RFC 8291 Appendix A**: `seal` gives the Appendix's body byte for byte from its keys, salt and message (`tests/test_web_push.py`; the values are the RFC's, written from memory of it and checked by this very match, since the RFC could not be fetched from this environment).
- A notification tap focuses the open window and tells it (`postMessage` `push-open`), or opens `data.url` with `from=push-<tag>` added to its fragment; `needs` in the fragment shows the Needs you tab. The phone's Notifications row, a renewal on connect, the unsubscribe on unpairing and the badge are in `shell-push.js` and `board-app.js` (the row is made in the drawer, `board.js` untouched).

### D. An agent's record
- The Taskmaster's `record` is `null` only without a row; a Taskmaster that made no plan in 30 days shows *No tasks in the last 30 days*, as an agent with none. The `TOO_FEW` of the dialog and the sheet is a constant (3) kept in step with `idea_spend.TOO_FEW` by hand.

### E. The way to by itself
- `after_check` and `after_rules` take an optional `today` (default: the machine's date), as `after_alone` does. A template that is already by itself keeps its day when a check it stopped at passes (`after_check` sets `alone_since` and `done_alone` only on the check that makes it go by itself). `op_runs.trust` reads `""` and 0 for a template that checks with you, whatever the file says.
- Two existing assertions of `tests/test_op_runs.py` that compared a whole trust dict gained the two new keys; nothing else of them changed.

### F. This week
- `board_week.nights(root, settings, now, n)` and `this_week(...)` take the **project's folder** as `root` (where the event log is), as `board_recap.build` does; `this_week` also takes `ops_base` (Operations' folder, whose `spend.jsonl` is its ledger; `ideas.week_work` passes `op_runs.root()`) and `into`. `idea_spend` gained `between_file` for it.
- `ops_usd` is `0.0` when Operations spent nothing and the face leaves a zero out as it leaves a null; with nothing priced in either, line 1 is not said. With no result in the week, line 2 says *No results in dev in the last 7 days*.
- On the phone *New idea* presses the Board's own button (`.fab`) after the sheet closes, so New idea opens with the goal the Board shows.
