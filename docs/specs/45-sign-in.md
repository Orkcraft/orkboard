# Spec 45 — Sign-in: a tool that is not signed in opens its own sign-in at once, and the work that needs it waits for it

The owner, 20 October (decisions §58). Today a refused sign-in is a line: *Claude Code is not signed in, or its sign-in
has expired. … Sign in again in a terminal: claude, then /login* (`realm/tool_errors.py` `LINES`, `what_to_do`,
`claude_sign_in`), on the first screen's Check and on the idea, task or run that failed; the task is **failed**, and
nothing opens. This spec opens the tool's **own** sign-in **at once** — in the browser for a tool that signs in there by
itself (Claude Code, Codex), in a terminal window opened with the tool for one that signs in only inside its own session
(pi) — and keeps the work that hit it **waiting** for the sign-in instead of failed: it goes on by itself once the tool
is signed in. **Builds:** Claude · **Review:** full · P1.

**Independent of specs 43 and 44** (written, not built): it shares only `core/idea_runner.py`, `core/idea_keeper.py`,
`realm/board_map.py`, `realm/event_log.py` and the phone's cache with them; whichever is merged second takes both.
**What it is, and is not:** Orkline starts the tool's own sign-in (`claude auth login`, `codex login`…) with its own
environment, so the sign-in lands where Orkline's runs look for it (a terminal's `claude` may use another config folder:
`claude_sign_in`'s first case); it never sees a password, a code or a token, and keeps none. It never opens when a
sign-in cannot help (§3), never on a phone, and never while no one is at the computer's page: then it opens the moment
someone comes back to it (§5). In Orkboard the Board and Operations run on Claude (`HARNESS` of `core/idea_runner.py`,
`core/idea_keeper.py`, `core/op_runner.py`); every tool is run by the first screen's Check. Orkline's buildings run
every tool and take this with spec 37's next copy (§11).

Two parts, one branch each, in this order, each from `main` once the one before is merged (CLAUDE.md "Alpha", as specs
42–44). **This file is the contract**; the rest is the builder's choice inside its files. **Change nothing outside a
part's files** but those §10 names.

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. The sign-in** | `spec/45-sign-in-backend` | §1–§7 | `realm/harnesses.py` (each tool's `sign_in`), `tools.py` (`signed_in`), `realm/sign_in.py` (new: a sign-in run), `realm/tool_errors.py` (`watch`, `helps`, `what_to_do`), `realm/tool_run.py` (`ran`), `core/sign_ins.py` (new: the service), `core/bus.py` (`SIGN_IN`, `SIGNED_IN`), `core/idea_runner.py`, `core/idea_keeper.py`, `core/idea_draft.py`, `core/op_runner.py` (the holds), `realm/board_map.py` (`waits` and the need), `realm/event_log.py`, `realm/lexicon.py`, `gui/board_host.py` (the service, its commands, the snapshot's `sign_in`), `gui/onboarding.py` (a Check row's `sign_in`); the tests of those modules today (`tests/test_harnesses.py`, `tests/test_tools.py`, `tests/test_idea_runner.py`, `tests/test_idea_keeper.py`, `tests/test_op_runner.py`, `tests/test_board_map.py`, `tests/test_event_log.py`, `tests/test_lexicon.py`, `tests/test_board_alone.py`), new `tests/test_sign_in.py` |
| **B. The faces** | `spec/45-sign-in-faces` | §8 | `js/shell/signin.js` (new: opens at once, the toasts), `js/shell/shell.js` (mounts it), `js/onboarding.js` (the Check row), `js/board/today.js` (the need), `js/board/tracks.js` (`rowOf`), `js/board/maplayout.js` and `js/board/map.js` (a stop's wait), `js/shell/errors.js` (`ErrorLine`'s *Sign in*), `pwa/shell-needs.js`, `pwa/shell-ideas.js`, `pwa/shell-map.js`, `pwa/sw.js` (the cache +1); `tests/test_shell_browser.py`, `tests/test_pwa_shell_browser.py`, new `tests/test_sign_in_browser.py`, `tests/test_pwa.py` |

## 0. The words
- **sign-in** (`sign_in`, a new term in `realm/lexicon.py`: *Sign-in*, *Sign-ins*): a tool's own way to sign in to its
  account, run by the tool; **Sign in** the button. Not *Login* (the lexicon's `logins`: tokens Orkline keeps).
  The first screen's *logged in* / *not logged in* become *signed in* / *not signed in* (B).
- **by browser** / **in a terminal** (`by`: `"browser"` | `"terminal"`, code only): a tool that signs in by itself in the
  browser it opens and takes the answer back; one that signs in only inside its own session, which needs a terminal.
- **needs a sign-in** (`needed`): a tool one of whose runs failed for its sign-in (§3), until it is signed in again.
- **held for the sign-in** (`held_for: "sign_in"`, code only): work that waits for its tool's sign-in (§6).
- Today's words stay: *not signed in, or its sign-in has expired* (`LINES`), *Retry*, *Details*, *Save logs*.

## 1. How each tool signs in (`realm/harnesses.py`, `tools.py`)
`Harness` gains `sign_in: tuple[str, ...]` (what follows its `bin`; `()` its session alone), `sign_in_by` (`"browser"` |
`"terminal"`) and `sign_in_type: str` (what the person types in its session, `""` when nothing). `login`, the words
shown, reads as today for each tool.

| tool | `sign_in` | by | type | `tools.signed_in` tells it by | checked |
|---|---|---|---|---|---|
| Claude Code | `auth login` | browser | — | `claude auth status`'s `loggedIn` (2.1.41 on; `_claude_login`) | 2.1.304, 20 October: stdin closed, no terminal; it opens the browser itself (`open` / `xdg-open` / `BROWSER`) on claude.com's sign-in, whose answer comes back to `localhost:<port>/callback`; prints *Paste code here if prompted* only for a browser that did not open |
| Codex | `login` | browser | — | `auth.json`, else `codex login status` (`_codex_login`) | 0.163.0, 20 October: a local server on `127.0.0.1:1455` (one port: one Codex sign-in at a time on the computer), opens the browser itself, no terminal; `--device-auth` is its headless way (not used) |
| Cursor | `login` | terminal until checked | — | its login file (`_cursor_login`; on macOS `None`, the Keychain) | not yet: §12 |
| Antigravity | `login` | terminal until checked | — | `None` (cannot be told) | not yet: §12 |
| pi | `()` | terminal | `/login` | `auth.json` (`_pi_login`) | 1.3.0, 20 October: no sign-in outside its session (`pi auth` only checks and prints) |
| Hermes Agent | `setup` | terminal | — (its setup asks) | `auth.json` / `.env` (`_hermes_login`) | not yet: §12 |

- `tools.signed_in(harness_id, env=None, run=subprocess.run, home=None) -> bool | None`: one tool's sign-in as `detect`
  tells it (`True`, `False`, or `None`: cannot be told), no model call; Claude's `auth status` is asked only of a
  version that has it (the version `detect` read, else one `--version`).
- A tool the builder finds to sign in by browser on the owner's Mac (it opens the browser itself and ends 0 once signed
  in, with stdin closed) moves to `browser`, with a line in §12; one that asks on its terminal stays `terminal`.

## 2. A sign-in run (`realm/sign_in.py`, new; no face)
`start(harness_id, env, state_dir, platform=sys.platform, which=shutil.which, popen=subprocess.Popen) -> Run`;
`Run.poll() -> None | Outcome`, `Run.cancel()`.
- **The environment**: Orkline's own, as a run of the tool gets it (`realm/tool_run.py`'s base): the same `PATH`,
  `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `PI_CODING_AGENT_DIR`, `HERMES_HOME`. In the home folder, never a project's.
- **By browser**: `[bin, *sign_in]`, stdin closed, its output to `<state>/sign-in/<tool>.log` with every URL cut to its
  host (a sign-in link carries a one-time state: it is not kept). It ends: exit 0 → **told** (below); another code →
  `failed`, `why` its last line; still running after `WAIT_S = 600` seconds → stopped, `timeout`. Its words asking to
  paste a code (`paste code`, `device code`) end it at once as `failed` (`why: "no_browser"`): the face offers the
  terminal (§8).
- **In a terminal**: a script `<state>/sign-in/<tool>.command` (mode 0700: `cd ~`, the environment's `PATH` and the
  tool's config variables above exported, then `exec <bin> <sign_in…>`), opened in a terminal window:
  - macOS: `open -a Terminal <file>` (a `.command` file, so no Apple Events and no Automation prompt);
  - Linux: the first found of `x-terminal-emulator -e`, `gnome-terminal --`, `konsole -e`, `xfce4-terminal -x`, `xterm -e`;
  - Windows: `cmd /c start "" cmd /k <file>.cmd`;
  - none found → `none`, with `command`: the words to type (`login`).

  The window is the person's: Orkline never closes it. It ends when `signed_in` says `True` (asked every `POLL_S = 5`
  seconds) → `done`; after `WAIT_S` → `timeout`; for a tool that cannot be told (`None`) only by the person's *Done*
  (§5), then **told**.
- **Told**: `signed_in` → `True` done; `False` failed (`why: "refused"`); `None` → onboarding's check (a short ask on the
  tool's cheapest tier, `gui/onboarding.py` `CHECK_PROMPT`, moved to `realm/sign_in.py` so core may call it) → done, or
  failed with the check's words.
- `cancel()`: stops the process (a terminal's window stays), `cancelled`.
- Nothing here reads, keeps or logs a code, a token or a password; the tool keeps its sign-in where it always does (the
  Keychain, its folder).

## 3. When a sign-in helps (`realm/tool_errors.py`)
- `watch(fn)`: `fn(err)` is called for every `ToolError` of kind `login` made (where `_LAST` is set); `watch_ok(fn)`:
  `fn(harness)` is called by `ran(harness)`, which `realm/tool_run.py` calls when a run of a tool ends without a failure.
  Nothing is watched until a host watches: tests and Orkline's runs see no change. A watcher's own error is swallowed.
- `helps(err, env=None, signed_in=tools.signed_in) -> bool`: `err.kind == "login"`, unless
  - a key the tool takes before its sign-in is set where Orkline runs (Claude: `ANTHROPIC_AUTH_TOKEN`,
    `ANTHROPIC_API_KEY`; Codex: `CODEX_API_KEY`; Cursor: `CURSOR_API_KEY`): `claude_sign_in`'s first case, its step as
    today;
  - another Claude Code was renewing the sign-in (*Retry in a minute*, as today);
  - only the weak words matched (`oauth`, `sign in`, `authenticat`: the work's own words can hold them) and
    `signed_in` says `True`.
- `what_to_do` for `login`, when `helps`: *Sign in opens Claude Code's sign-in. In a terminal: claude, then /login.*
  (`h.login` for the others); else as today. `plainly` keeps its cap.

## 4. Sign-ins (`core/sign_ins.py`, new: the host's service)
`SignIns(bus, env, state_dir, clock=time.time)`, watching `tool_errors` (`watch`, `watch_ok`), holds per tool:
`{harness, tool, mark, state, by, auto, since, where, why, command, waiting}`.
- **`state`**: `needed` (a failure that a sign-in `helps`) → `open` (a run started) → `done` | `failed` (`why`: `timeout`,
  `cancelled`, `refused`, `no_browser`, the check's words) | `none` (no terminal: `command`). A failure that does not
  help is never kept here: its line says its step.
- **An episode** begins with a failure that helps while the tool is not `needed` or `open`, and ends at `done`: by its
  run, or by a run of the tool that ended well (`ran`: the person signed in elsewhere). `where`: what failed first
  (`task`, `draft`, `plan`, `op`, `check`, `ask`); `waiting`: how much is held for it now (§6).
- **`auto`**: `true` from the episode's start until its first `start(auto=True)`, `false` for the rest of the episode:
  a second page, a reload, a second failure open nothing more by themselves. After `failed`, `timeout`, `cancelled` or
  `none` the episode goes on: the faces offer *Sign in* again, and `auto` stays `false`.
- **`start(harness, auto=False)`**: one run per tool; `open` returns its run, never a second; a second Codex sign-in on
  the computer waits for the first's port. **`cancel(harness)`**. **Stop all** cancels an open run. Quitting Orkline
  stops its runs. The service polls its open runs on the host's clock (at most every `POLL_S`).
- Each change publishes **`bus.SIGN_IN`** (`{harness, tool, state, by, auto, why, command, waiting}`); `done` also
  **`bus.SIGNED_IN`** (`{harness}`). Never a toast or a dialog (CLAUDE.md: the face shows them).
- The snapshot's **`sign_in`**: the tools not `done`, in the registry's order (`[]` when none).

## 5. Opening at once (`gui/board_host.py`; the page in B)
- **Commands, desktop only** (not in `BoardPhone`'s): `tools.sign_in {harness, auto}` → the tool's entry;
  `tools.sign_in_cancel {harness}`; `tools.sign_in_done {harness}` (a terminal sign-in of a tool that cannot be told:
  **told**, §2). An unknown tool, or one not found on the computer, is refused with a line.
- **The page opens it**: when the snapshot's `sign_in` holds a tool `needed` with `auto: true`, the desktop page sends
  `tools.sign_in {harness, auto: true}` for the first, **when the person is at the page** — it is visible
  (`document.visibilityState`) and has the focus (`document.hasFocus()`) — at once if so, else on its next `focus`,
  `pointerdown` or `keydown`. One tool at a time: the next once the first is no longer `open`.
  So a failure while the person uses Orkline opens its sign-in at once; one in the night opens when they come back to
  Orkline, not at 3 a.m. into a browser no one answers.
- The server takes `auto: true` once per episode (§4): the first page wins; the others get the entry as it is.
- The first screen is the same page: a Check that fails for the sign-in opens it at once (the person just pressed it).

## 6. The work waits for it (A)
A failure that a sign-in helps (§3) no longer fails what ran by itself: it is held for the sign-in, as a spent window
holds it today, and goes on when its tool is signed in (`bus.SIGNED_IN` of its `harness`).

| what | today | with this spec |
|---|---|---|
| a plan's task (`core/idea_runner.py`) | `failed`, `error` the line | `held`, `held_for: "sign_in"`, `harness`; runs again on `SIGNED_IN`, as a limit's hold does at its reset |
| what the Board runs by itself: a draft, a plan, the night's (`core/idea_keeper.py`, `core/idea_draft.py`) | the idea's `error` | `held_until` as a spent window has it, `held_for: "sign_in"`; the keeper's clock runs it again once signed in |
| an operation's run (`core/op_runner.py`) | `failed` | `held`, `held: <step>`, `held_for: "sign_in"` |
| what the person waits on (an answer in a dialog, a goal's lead, Check) | its error line | as today: the line, with *Sign in* beside it (B) |

- At most **`HOLD_H = 24`** hours held: then it fails as today, with the line.
- A sign-in that ends `failed` or `cancelled` leaves what is held held (the person may still sign in) until `HOLD_H`.
- Stop all and Stop on a held task stop it as they stop a limit's hold.

## 7. Data, events (A)
- `ideas.map` / `ideas.board`: `waits` kind `sign_in` (`tool`: its title, `until`: `HOLD_H` from the hold) on a held task
  or idea; the needs (`realm/board_map.py`) gain one per tool that needs a sign-in and holds work:
  `{kind: "sign_in", harness, tool, text: the line, waiting}`; a Check's failure adds no need.
- A Check row (`onboarding.check`'s `check`) gains `sign_in: true` when its failure helps.
- Events (`realm/event_log.py`, the project shown; none open: not written): `sign_in_needed {harness, where}`,
  `signed_in {harness, by, s}` (`by`: `browser` | `terminal` | `elsewhere`; `s`: seconds from the episode's start),
  `sign_in_failed {harness, why}`. How often and how fast, nothing more.

## 8. The faces (B)
- **Desktop** (`js/shell/signin.js`, new, mounted by the shell):
  - it opens at once (§5);
  - **by browser**, while `open` (a toast that stays while open): *Sign in to Claude Code* — *Its sign-in opened in your
    browser. Sign in there: the work that waits for it goes on by itself.* — **Cancel**;
  - **in a terminal**: *Sign in to pi* — *pi signs in in its own window: a terminal opened with pi. Type /login there.* —
    **Copy** (the command), **Done** (a tool that cannot be told), **Cancel**; `none`: *No terminal was found. Open one
    and run: pi, then /login* — **Copy**;
  - `done`: *Claude Code is signed in.*, and with `waiting`: *3 tasks go on.*; `failed`: *Claude Code's sign-in did not
    finish.* with its `why` in words — **Sign in again**, **Details**; `no_browser`: *The browser did not open.* —
    **Sign in in a terminal** (the terminal way of §2 for this run);
  - **Sign in** beside every line of a failure that a sign-in helps: the first screen's Check row (`js/onboarding.js`:
    *⚠ not signed in* · **Sign in**, in place of *⚠ not logged in: …*), every error line (`ErrorLine`: an idea's, a
    task's, a goal's) that says a tool of the snapshot's `sign_in` is not signed in (its `LINES` words), the need on
    Today (`js/board/today.js` `KIND_WORDS.sign_in`: *Sign-in*);
  - a row or a stop held by it (`rowOf`, the Map): *waits: Claude Code's sign-in*.
- **Phone** (`pwa/shell-needs.js`, `pwa/shell-ideas.js`, `pwa/shell-map.js`): the need *Sign in to Claude Code on the
  computer*, with no button (a phone opens nothing on the computer: `BoardPhone`); a held row *waits: Claude Code's
  sign-in*; the cache +1 (`pwa/sw.js`). No push.
- Nothing else: no badge, no colour of its own (the toast's severity is `warning` while it waits, `information` when
  done).

## 9. Tests
- **A**: each tool's `sign_in`, `sign_in_by`, `sign_in_type` and `login` unchanged; `tools.signed_in` per tool with fake
  runs and homes (Claude's `auth status` only from 2.1.41; Codex's `login status`; `None` where it cannot be told);
  `realm/sign_in.py` with a fake `popen` and clock: the browser way's argv, environment (`CLAUDE_CONFIG_DIR` kept), stdin
  closed, ends 0 → told, another code → failed, `WAIT_S` → stopped `timeout`, *paste code* → `no_browser`; the log holds
  no URL past its host; the terminal way's script (0700, the variables, `exec`) and its opener per platform (darwin,
  linux with each emulator missing in turn, win32), none → `none`; told by `signed_in` `True`/`False`/`None` → the
  check; `helps` (each key, the renewing words, weak words with `signed_in` `True`, `False` and `None`); `watch` and
  `watch_ok` called once per failure and run, nothing without a watcher; `SignIns`: an episode, `auto` once, one run per
  tool, Codex's one port, `ran` ends it (`by: "elsewhere"`), Stop all cancels, `SIGN_IN` and `SIGNED_IN` published;
  the commands refused on the phone's face; a task, a draft, a night's plan and an operation's run held for the sign-in
  and run again on `SIGNED_IN`, failed at `HOLD_H`, a key's failure failed as today; `waits` kind `sign_in`, the need,
  the Check row's `sign_in`; the three events.
- **A, by hand** (the owner's Mac, noted in §12): Claude Code and Codex signed out, a task run: the browser opens on its
  sign-in, the task waits, the sign-in done, the task goes on; Cursor, Antigravity and Hermes Agent checked by §1's rule.
- **B** (browser, both faces, a stub host): `needed` with `auto` → `tools.sign_in {auto: true}` sent once when the page
  is visible and focused, not while it is hidden or unfocused, sent on its next focus or press; two tools → one at a
  time; the toasts of `open` (browser, terminal, `none`), `done` with `waiting`, `failed`, `no_browser`; **Sign in** on
  the Check row, an error line and the need; *waits: Claude Code's sign-in* on a row and a stop; the phone's need with
  no button and no `tools.sign_in` ever sent.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_architecture.py` (`realm/sign_in.py` and `core/sign_ins.py` import no
  `gui/`), B also `tests/test_pwa.py`.

## 10. Files a part may need beyond its row
`gui/server.py` (A: only if Stop all's cancel cannot reach the service through the host), `realm/status.py` (A: a hold's
words), `realm/halt.py` (A: Stop all's cancel), `tests/test_shell_browser.py`'s `StubHost` and
`tests/test_pwa_shell_browser.py`'s `Stub` (B: `sign_in` and the commands). Anything else: stop and write it in §12
first.

## 11. Not in this spec
- **Orkline's buildings**: their *<Tool> hit an error* toast (`Town.tool_failed`, `bus.TOOL_ERROR`) takes `SignIns` with
  spec 37's next copy of these modules; until then the line, as today.
- Signing in with a key (`--with-api-key`, `ANTHROPIC_API_KEY`): Orkline keeps no key of a tool.
- Choosing the account or its kind (`--console`, `--sso`, `--email`): the tool's own page asks.
- A sign-in from the phone; a push for it.
- Switching to another tool when one is not signed in (Orkline's toast's Switch stays where it is).

## 12. As built (notes, no change of the contract)

**Part A, built.** Where it differs from the text above:
- **Files beyond §10, each one line or a mixin**: `realm/ideas.py` (`held_for` in `STATE_DEFAULT`, so `ideas.state` keeps it),
  `realm/op_runs.py` (`held_for` in `RUN_KEYS`), `gui/ideas.py` and `gui/ops.py` (the keeper, the runner and Operations are
  given the host's `sign_ins`), `core/idea_sign_in.py` (new: the keeper's holds, as a mixin, so `idea_keeper.py` does not grow
  further past ~600 lines), `tests/conftest.py` (an autouse fixture drops every `tool_errors` watcher after a test: a host
  watches for the life of its process), `tests/test_gui_ideas.py` (that test sets a key so a sign-in cannot help: it is about
  the line).
- **`tool_errors`**: besides `watch`, `watch_ok`, `helps` and `ran`, `doing(where)` / `where_now()` name what a thread does
  (`task`, `draft`, `plan`, `op`, `check`, else `ask`) for the episode's `where`; `helped(err)` asks `helps` once for an error
  (`err.helped`). `what_to_do` says *Sign in opens …* only for an error a host's watcher judged `helps` (`err.helped is True`),
  so Orkline's runs and the tests keep today's words. `ran` is called by `tool_run.result_of` (every `jobs` run that ended
  without a failure reads its result there) and by `tool_run.ask`.
- **`realm/sign_in.py`**: `Outcome.state` is `done` | `failed` | `none`; `timeout` and `cancelled` are `failed` with that
  `why`. The process is registered in `realm/halt.py` (so Stop all also kills it, and `tests/test_architecture.py` needs no
  exception); `Run.told()` is *Done*. A script on Windows is `<tool>.cmd`.
- **`core/sign_ins.py`**: a failure within 60 s after a `done`, of a tool that says it is signed in, begins no episode (a run
  that began before the sign-in is held and let go at once). A tool that needs its sign-in with no run open is asked
  `signed_in` every 30 s: `True` after a `False` ends the episode as `elsewhere` (nothing runs to tell it while the work is
  held). A Codex sign-in whose port is busy stays `open` and starts when the port is free (or fails `timeout`).
  `SignIns(…, threaded=False)` runs polls and *Done* on the caller's thread (tests).
- **Holds**: a task keeps `held_for`, `harness`, `held_until` (ISO, `HOLD_H` from the hold) and `held_line` (the line it fails
  with); an idea `held_for` + `held_until` in its state; an operation `held_for` + `held_until`. A task, an idea or an
  operation that would start by itself while the tool is not signed in is held at once, without a call. The draft and the
  plan are held whoever asked for them (*Process now*, *Re-plan* too); an answer in a dialog, a talk and a goal's read fail
  with the line.
- **The need** is `board_map.sign_in_needs(entries)`; the host adds it to `ideas.board`'s `needs_you` and to the snapshot's
  `needs_you` count, with the snapshot's `sign_in`. The phone's snapshot carries neither `sign_in` nor a command for it; B
  reads the need from `ideas.board`. `waits` kind `sign_in` is `{kind, ref: harness, title: tool, tool, until: ISO}`.
- **Events** go to the shown project's log only (`root()` of the host); none in the demo, where nothing is watched.

**Part B, built.** Where it differs from the text above:
- **`js/shell/signin.js`** is mounted by the shell and by the first screen (`js/onboarding.js`), the two pages never being drawn together.
  It reads only the snapshot's `sign_in`: a tool that leaves it after being `open`, `failed` or `none` (or with work waiting) is
  *signed in*; the `done` toast's *N tasks go on* is the `waiting` it last saw. A cancelled sign-in and a `failed` one found at the
  page's first snapshot (a reload) say nothing. The toast stays 10 minutes (`WAIT_S`) while open.
- **Open terminal sign-in**: the snapshot's entry holds no `command` while a terminal is `open` and no `sign_in_type`, so the page
  knows pi's `/login` itself (`TYPED` in `signin.js`), and *Done* is offered for every tool signed in in a terminal (a tool that can be
  told is told at once; a *Done* is then only early).
- **Sign in in a terminal** (after `no_browser`) sends `tools.sign_in {harness, by: "terminal"}`; part A's `start` reads no `by` yet, so
  until it does the host opens the browser way again. A one-line follow-up in `core/sign_ins.py` / `gui/board_host.py`.
- **The Check row**: *Sign in* sits beside the failed Check's line (`CheckFailed`), not in the status cell, which reads *⚠ not signed in*
  (with the tool's `login` words when no sign-in helps).
- **Needs you**: the `sign_in` row is not a button that opens something; it has *Sign in* and *Later*. The phone's row has neither.
- No change in `js/board/map.js`: `nodeView` already says the wait `waitsWords` gives, now `waits: Claude Code's sign-in` (before
  *waits for limits*, since a hold sets `held_until` for both).
