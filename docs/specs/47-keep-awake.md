# Spec 47 — Keep the computer awake: on power, while the orks work, while the Board has work for tonight, or while a phone should reach it

The owner, 20 October. Orkboard lets the computer sleep whatever the machine's *Keep the computer awake* says: holding
it is Orkline's (`orkcraft/gui/away.py`, `orkcraft/gui/awake.py`, decisions-2026-10 §18), and Orkboard's host has
neither (`tests/test_phones.py` `test_orkboard_offers_no_keeping_the_computer_awake`). What is left of it here does
nothing: the setting `keep_awake` (`"carts"` by default) and `awake_offered`, the old Town settings' `AwakeField`
(`js/settings.js`, a dialog Orkboard does not load) and `AwakeOffer` (`js/phones.js`, never shown: `phones.list`'s
`awake_offer` is always `""`). While the computer sleeps, a task stops where it is, the night's work (decisions §47,
spec 35 §7) never comes, and a paired phone cannot reach it. This spec gives Orkboard the hold: the system's own, on
power only, never the screen, for Orkboard's reasons. **Builds:** Claude · **Review:** full · P1.

**What it is, and is not:** the same setting as Orkline's, read and written as Orkline does (`~/.config/orkcraft/`:
`keep_awake` `off` | `carts` | `phone`, and `awake_offered`): no new value, so switching between the two loses
nothing. **Orkline is not changed**: it keeps its own `away.py` and `awake.py`; when both run, each holds by its own
rule and the computer sleeps only when neither holds. Not a wake from sleep, not the display, not a closed lid, never
on battery.

Two parts, one branch each, in this order, each from `main` once the one before is merged (CLAUDE.md "Alpha"). **This
file is the contract**; the rest is the builder's choice inside its files. **Change nothing outside a part's files**
but those §7 names. A touches `core/idea_night.py`, as spec 44 A does: whichever comes second merges `main` first.

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. The hold** | `spec/47-awake-backend` | §1–§4 | new `gui/awake.py` (the system's hold), new `gui/keep_awake.py` (when it holds; `awake.*`), `gui/board_host.py` (builds them; the clock; `run` starts and stops the hold; the phone's `sleep`), `gui/phones.py` (`awake_offer`), `core/idea_night.py` (the keeper's `at_work`, `tonight`), `core/op_runner.py` (`busy`), `gui/ideas.py` (`working`, `tonight`), `realm/lexicon.py`, `settings.py` (comments only); new `tests/test_awake.py`, new `tests/test_keep_awake.py`, `tests/test_phones.py`, `tests/test_board_alone.py`, `tests/test_idea_night.py`, `tests/test_op_runner.py` |
| **B. The words** | `spec/47-awake-faces` | §5 | `js/shell/settings.js` (the field), `js/shell/pair.js` and `js/phones.js` (the offer), `js/shell/shell.css`, `pwa/shell-drawer.js` (the line), `pwa/sw.js` (the cache one version up from `main`'s); `tests/test_shell_browser.py`, `tests/test_pwa_shell_browser.py`, `tests/test_pwa.py` |

## 0. The words
- **Keep the computer awake** (`keep_awake`, new in `TERMS`; already the setting's name in Orkline's Town settings):
  the computer does not go to sleep by itself. The screen may turn off; a sleep the person asks for (the menu, a closed
  lid) still happens.
- **the hold** (code only: `why`): what holds it now — `work` (an ork or an operation at work), `tonight` (the Board
  has work waiting for tonight), `phone` (a phone is paired and the mode says so), or `""`.
- **on power**: on mains power, or a machine that says nothing of a battery (a desktop). On battery nothing holds it,
  whatever the mode.
- The modes: `off` *Never*; `carts` *While the orks work*; `phone` *Stay reachable from your phone*. The value `carts`
  keeps Orkline's spelling (the state keeps Orkline's names, CLAUDE.md); the interface never says it.

## 1. The system's hold (`gui/awake.py`, A)
Orkline's `orkcraft/gui/awake.py` (`orkWorks/orkLine` `main` at `95ab38b`), copied: `Awake` (`apply(want)`, `stop()`,
`how`, `can()`, `running`) and `on_power()`, the same three ways, each only against idle sleep, each ending with this
process even when it is killed:
- macOS `caffeinate -i -w <pid>`; Linux `systemd-inhibit --what=sleep --mode=block` around `tail --pid=<pid>`;
  Windows `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` on a thread of its own.
- A hold refused (no logind, no right to inhibit, a container) ends at once: `how` stays `""`.
- Power: `pmset -g batt`, `/sys/class/power_supply`, `GetSystemPowerStatus`; unknown counts as on power.

Changed from Orkline's: only what names the town. `--who=Orkline` stays (the product's name in the interface, decisions
§50.1); `WHY` reads *Orkline: the orks keep working, and a paired phone reaches this computer, while the screen is off*;
the docstring points at `gui/keep_awake.py`. No module of Orkline's is imported (`tests/test_architecture.py`).

## 2. When it holds (`gui/keep_awake.py`, A)
`KeepAwake(host)`, the host's `keep_awake`, built in `Orkboard.__init__` beside `awake = awake.Awake()`.
- **Only while Orkboard is open.** `run()` sets `awake.running` once the server is up and holds at once if a reason
  holds; the window closing, Ctrl+C in the browser, or an update's restart let go (`show(..., stop=host.keep_awake.stop)`;
  today `run` hands `show` no `stop`). A host a test builds, the demo (`demo`), a host never run: nothing holds, no
  process starts, and `tick` reads nothing (no `pmset` either).
- **`reason(now) -> "work" | "tonight" | "phone" | ""`**, in this order:
  1. `""` when the mode is `off`, or the computer is on battery (`on_power()` read at most every `POWER_S = 60` s;
     `None` counts as on power).
  2. `"phone"` when the mode is `phone` and a phone is paired (`gui/pairing.py`, read again only when the settings
     file changed).
  3. `"work"` when, in any open project (`projects.open_ones`), the keeper is at work (a draft, a plan, a read, a
     check, the night's run: `IdeaKeeper.at_work()`) or the runner has a task running (`IdeaRunner.busy()`), or
     Operations has a call running or queued (`OpRunner.busy()`). A task waiting at Review, a plan held by the reserve
     or the limits, a question waiting for the person: none of them holds it.
  4. `"tonight"` when, in any open project, the Board has work waiting for tonight (`IdeaKeeper.tonight() > 0`: an
     idea `raw` in the `night` queue, or a passed plan with `start_at: "night"` still in state `plan` — the rows the
     night's steps 1 and 2 take, `core/idea_night.py`), read at most every `TONIGHT_S = 60` s per project. It holds
     until that work is done: inside the night window the night runs it and it holds as `"work"`; what the reserve
     kept for the next night holds until then. The night's refresh and proposals alone never hold it.
  5. else `""`.

  With mode `carts`, 1, 3 and 4 apply; with `phone`, 1 and 2, and 3–4 while no phone is paired.
- **`tick(now)`** (from `Orkboard.tick`, at most every `TICK_S = 30` s): `apply(now)`.
- **`apply(now)`** holds when `reason` is not `""`, and **lets go only after `LINGER_S = 300` s with no reason**: a task
  ending and the next starting, a draft becoming a plan, never leave a gap the computer sleeps in. A reason coming back
  inside the linger keeps the one hold (no second process). `why` is the reason while one holds (`""` while it lingers or
  nothing holds). A change of the mode applies at once; to `off` it lets go at once, with no linger.
- **`state() -> {"mode", "why", "holding", "battery", "can", "how", "machine", "paired"}`**: `mode` the setting; `why`
  as above; `holding` a hold is on now (`how` not `""`); `battery` true only when the computer says it is on battery;
  `can` (`Awake.can()`); `how` (`"caffeinate"` | `"systemd-inhibit"` | `"windows"` | `""`); `machine` `"Mac"` on macOS,
  else `"computer"`; `paired` a phone is paired.
- **`offer() -> "Mac" | "computer" | ""`**: the machine's word while "keep it awake for the phone" is to be asked — a
  phone paired, the mode not `phone`, `awake_offered` false, `can()` true, not the demo; else `""`.
- **`phone_line() -> str`**: what the phone says of this computer's sleep, one line or `""`: on battery *Your Mac is on
  battery and may sleep.*; mode `off` *Your Mac may sleep: keeping it awake is off in its Settings.* (*computer* for
  *Mac* on another system).

## 3. Commands and payloads (A)
- **`awake.state`** → `state()`.
- **`awake.set {mode}`**: `mode` through `settings.awake_mode` (an unknown value reads `carts`, as Orkline's does),
  saved in the machine's settings (`settings.save`), applied at once; → `state()`.
- **`awake.offer {yes}`**: `awake_offered` becomes true; with `yes` the mode becomes `phone`; saved, applied at once;
  → `state()`.
- Desktop only: none of them is in `BoardPhone.COMMANDS` (a phone does not keep the computer awake for itself).
- **`phones.list`**'s `awake_offer`: `host.keep_awake.offer()` (`gui/phones.py` reads `host.away` today, which
  Orkboard has not).
- **The phone's snapshot** (`Orkboard.phone_snapshot`) gains `sleep`: `phone_line()` (inside its `rev`). The desktop's
  snapshot does not change (`tests/test_board_alone.py`).
- **The new reads**: `IdeaKeeper.at_work() -> bool` and `IdeaKeeper.tonight() -> int` in `core/idea_night.py` (the
  keeper's mixin: `core/idea_keeper.py` is at the split limit); `Ideas.working() -> bool` and `Ideas.tonight() -> int`
  in `gui/ideas.py` (the keeper's and the runner's; a runner not built is not at work); `OpRunner.busy() -> bool`.
- No event, no toast: a hold is not news.

## 4. Settings (A)
`settings.py` changes only in its comments: `KEEP_AWAKE`, `keep_awake` and `awake_offered` name `gui/keep_awake.py`
(Orkboard's) beside Orkline's `gui/away.py`. The default stays `"carts"`: on a machine where Orkboard ran before, the
hold begins with the first work on power after this spec.

## 5. The words (B)
**Settings** (desktop, `js/shell/settings.js`), after *Your phone*: a group *Keep the computer awake*, read with
`awake.state` when the dialog opens and every 30 s while it is open; one of three, as the goal's Priority is drawn
(`shell-seg`): *Never* · *While the orks work* · *Stay reachable from your phone*, sent with `awake.set` at once. Under
it, muted lines:
- `off`: *The computer sleeps as its power settings say. While it sleeps the orks stop, the night's work waits, and a
  phone cannot reach it.*
- `carts`: *On power, it does not sleep by itself while an ork or an operation is at work, or while the Board has work
  waiting for tonight. With nothing to do, or on battery, it sleeps as its power settings say.*
- `phone`: *On power, it does not sleep by itself while Orkline is open and a phone is paired, work or not. On battery
  it sleeps as its power settings say, and the phone says so.* With no phone paired: *No phone is paired yet: Pair a
  phone, above.*
- What holds it now, the mode not `off`: *Holding now: an ork is at work.* (`work`) · *Holding now: the Board has work
  for tonight.* (`tonight`) · *Holding now: a phone is paired.* (`phone`) · *Not holding now: nothing to do.* (none) ·
  *On battery now, so it may sleep.* (`battery`, in place of the line before).
- The mode not `off`: *The screen still turns off. A laptop with its lid closed still sleeps unless a display is
  attached.*
- `can` false, the mode not `off`, in place of every line above: *This computer gives Orkline no way to keep it awake:
  set its power settings so it does not sleep while the orks work.*

**The offer** (desktop, `js/shell/pair.js`): after *Paired: <name>.*, while `awake_offer` is not `""` (`phones.list`,
as `usePairing` reads it): *Keep this Mac awake so your phone can reach it all day? Only on power.* with **Yes**
(primary) and **Not now**, sending `awake.offer`; gone once answered. `AwakeOffer` (`js/phones.js`) is exported and used
there; its words say *it* where they said *the town*.

**The phone** (`pwa/shell-drawer.js`): under This phone, one muted line, the snapshot's `sleep`, when it is not `""`.

Nothing else: no mark in the top bar, no colour (a battery is not a signal), no toast.

## 6. Tests
- **A, the system's hold** (`tests/test_awake.py`): the four tests of Orkline's `tests/test_awake.py` on `Awake` (each
  system's command and its end with this process; on, then let go; a refused hold says nothing holds; the setting's old
  `true` / `false` read as `carts` / `off`), with a fake `popen`, `which` and `platform`; `on_power` per system with a
  fake `pmset` output and a fake `/sys/class/power_supply`.
- **A, when it holds** (`tests/test_keep_awake.py`, a fake `Awake`, a fake clock, fake power): a host never run holds
  nothing and starts no process; `off` never holds; on battery nothing holds, in any mode; `carts` holds while a keeper
  is at work, a task runs, an operation runs or waits in the queue — not for a task at Review, a plan held by the
  reserve, a question; `tonight` holds for an idea in the night queue and for a plan to start at night, not for the
  night's proposals alone, and lets go after the night drafted and started them; `phone` holds with a phone paired, and
  with none falls back to `carts`'s reasons; it lets go only after `LINGER_S`, and a reason coming back inside it keeps
  one hold; `awake.set` saves and applies at once, `off` with no linger; `awake.offer` once, yes → `phone`; `offer()`
  is `""` with no phone, when asked before, with mode `phone`, with `can()` false, in the demo; `phone_line` on battery
  and with `off`; `run` hands `stop` to `show`, and it lets go when the window closes.
- `tests/test_phones.py`: `test_orkboard_offers_no_keeping_the_computer_awake` becomes *a paired phone is offered
  keeping the computer awake, once* (`awake_offer` `"Mac"` / `"computer"`, `""` after `awake.offer`).
  `tests/test_board_alone.py`: `awake.*` among the host's commands and not the phone's; the phone's snapshot has
  `sleep`; the desktop's snapshot keeps its keys. `tests/test_idea_night.py`: `at_work`, `tonight`.
  `tests/test_op_runner.py`: `busy`.
- **B** (browser): the field's three choices and their lines by `state` (held for each reason, not held, on battery,
  `can` false, no phone paired); a choice sends `awake.set`; the offer after pairing, once, Yes sends
  `awake.offer {yes: true}`, Not now `{yes: false}`; the phone's drawer line with `sleep`, none without.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`, `tests/test_pwa.py`.

## 7. Files a part may need beyond its row
`gui/pairing.py` (A: a read of the paired phones that does not read an unchanged file again, if it has none),
`tests/conftest.py` (A: a fixture that keeps every test's `Awake` fake, so no test starts `caffeinate` or
`systemd-inhibit`), `tests/test_shell_browser.py`'s `StubHost` and `tests/test_pwa_shell_browser.py`'s `Stub` (B:
`awake.*`, `sleep`). Anything else: stop and write it in §9 first.

## 8. Not in this spec
- Waking a sleeping computer for the night (`pmset schedule wake`, a Windows wake timer): it needs root or a task of
  the system's own.
- App Nap on a Mac (an `NSProcessInfo` activity): measured first — whether the host's clock slows while Orkboard.app's
  window is hidden — and a spec of its own if it does.
- A cap on the hold (Orkline's day away has one, 30 % of the window): the Board's reserve already stops what starts by
  itself, and with nothing at work the hold lets go.
- Orkline's `away.py` and `awake.py` replaced by Orkboard's: after the testers' week, with the rest (spec 37 §9).
- The old Town settings' `AwakeField` (`js/settings.js`): Orkboard does not load that dialog; it goes with that file.

## 9. As built (notes, no change of the contract)
- **A** (`spec/47-awake-backend`): `gui/awake.py` is written from §1's description, not copied: Orkline's file was not
  in reach. `Awake` takes `popen`, `which`, `platform`, `settle` and `windows` for the tests; `apply(True)` holds nothing
  while `running` is false, and a refused hold is not tried again (`can()` turns false). `KeepAwake.start()` (from `run`)
  sets `awake.running`; `stop()` clears it. `tests/conftest.py` swaps `awake.Awake` for a fake in every test.
  An idea `raw` with no queue counts for `tonight`, as the night takes it (`ideas.queue_of`).
