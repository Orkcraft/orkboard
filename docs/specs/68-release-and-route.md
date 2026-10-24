# Spec 68 — A goal's route across parties, and a Release party that gathers the flags

The owner, 23 October (decisions §83): *what if parties changed often: ideation → a new mobile feature → ideation → a new
feature → testing → release?* Read as parties, that chain is one thing's way, not a change of team: the features are the
Mobile app party's goals, testing is its checkers and the gate. So parties stay teams and stay few (§63.11), and a goal
gets **a route**: where it came from, where it is, and where it went. And the one step that is truly another team's, a
version out in the stores, becomes **a party of the library, Release**: its leader the **Release manager** (a skeleton),
its builders on the cheaper models, its goal *A release* gathering **the flags raised since the last release** in the
parties it releases from. **Builds:** Claude · **Review:** full · P2.

**What it is, and is not:** a route read from what the Board already keeps (the pitch a goal was sent from, its flag)
and two small files beside a goal's state (`route.json`, a release's `release.json`); four agents and a preset of the
library; a type's list of what goes in; one press, *Mark it out*; a race of orkUI's for one agent. Not: a goal moved
once its work has started; a store submission, a tag pushed or a build uploaded by Orkboard (§3.5); a view of every
party at once; a release that spans projects.

Four parts. **A0 and A at once** (A0 is orkUI's repository; A reads the skeleton's head only when orkUI's copy has it,
§1.3); **B and C from `main` once A is in** (they touch no file of each other's). **This file is the contract**; the rest
is the builder's choice inside its files. **Change nothing outside a part's files** but those §9 names.

| part | builds | files (and their tests) |
|---|---|---|
| **A0. orkUI** (repository orkWorks/orkUI) | §1.3 | `office/races/skeleton-{elder,warrior,laborer}.png` and `@2x` (24 × 22, the races' grid and gear), `office/preview.html` (the races' row), the version (**0.5.0**), `CHANGELOG.md`, `README.md`; `tests/test_orkui.py`. Then, in orkBoard, the copy: `python -m orkboard.design.orkui <orkUI>` (only `design-system/orkui/` changes) |
| **A. Host** | §1–§6 | `realm/library.py` (the four agents, `Agent.race`, the preset, `STAGES`), `realm/roles.py` (`head` and `install` keep an agent's own race), `realm/goal_types.py` (*A release*'s asks; not offered beside a Release party), new `realm/idea_route.py` (a goal's route; the move's rule and record), new `realm/releases.py` (what goes in, a release's file, out, the prompt's lines), `realm/board_map.py` (a goal's `route`; a party's `releases_from`, `wait_release`; a flag's `release`), `realm/event_log.py`, `realm/lexicon.py`, `gui/ideas.py` (`ideas.move` through the route; `ideas.release_out`, `ideas.shown`; `ideas.add`'s `goes_in` for a release), `gui/ideas_pitch.py` (the pitch's element; a sent pitch's goal state), `gui/ideas_party.py` (`releases_from` saved with the party), `core/idea_draft.py`, `core/idea_keeper.py` (the release's lines in the draft and plan prompts, beside `goal_types.prompt_line`); new `tests/test_idea_route.py`, new `tests/test_releases.py`, `tests/test_goal_types.py`, `tests/test_library.py`, `tests/test_board_map.py`, `tests/test_lexicon.py`, `tests/test_event_log.py`, `tests/test_ideation.py` |
| **B. Desktop** | §7 on the desktop | `js/board/idea.js` (the goal's screen: its route), new `js/arena/route.js` (the route's line, shared by the goal's and the pitch's screens), `js/shell/pitchview.js` (a sent pitch's goal), `js/shell/ideadialog.js` (*A release*: What goes in), `js/shell/goaldialog.js` and `js/shell/goalwizard.js` (*Releases from*), `js/arena/goals.js` and `js/arena/flags.js` (a flag's release; *k flags wait for a release*; *Mark it out*), `js/arena/goaltabs.js` (a switch says `ideas.shown`), `js/arena/arena.css`, `js/shell/shell.css`; new `tests/test_route_desktop_browser.py`, new `tests/test_release_desktop_browser.py`, and the desktop tests that read the Mobile app party's types (§8) |
| **C. Phone** | §7 on the phone | new `pwa/shell-route.js` (the route's line), the goal's screen (from `pwa/shell-goals.js`'s ›), `pwa/shell-pitch.js` (a sent pitch's goal), `pwa/shell-ideas.js` (*A release*: What goes in), `pwa/shell-goal-new.js` and `pwa/shell-party.js` (*Releases from*), `pwa/shell-goals.js` and `pwa/shell-goals-words.js` (a flag's release; *k flags wait for a release*; *Mark it out*), `pwa/shell-where.js` (a switch says `ideas.shown`), `pwa/shell-who.js` and the craft-to-race maps of the files above (the host's `race` first), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up, `shell-route.js` in `SHELL`) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_route_browser.py`, new `tests/test_pwa_release_browser.py`, and the phone tests that read the Mobile app party's types (§8) |

## 0. The words
`TERMS` gains (realm/lexicon.py), the code's names in brackets:
- **route** · *routes* (`idea_route`): a goal's way across parties: where it came from, where it is, where it went.
- **release** · *releases* (`release`): a goal of *A release*: a version, the goals that go in, its notes and the stores'
  list.
- **out** (`release_out`): a release the person said is out in the stores.
- `race.skeleton`: *skeleton*, *skeletons*.

New strings, in these words: *Route*, *From Ideation: <answer>, <date>* (*From Ideation: Invest, 22 Oct*), *Moved from
<party>*, *At work in <party>* (while it works; else *In <party>*), *In main*, *In <party> <version>* (*In Release 1.4*), *Out in <version>*, *Waits for a
release*, *k flags wait for a release* (*1 flag waits for a release*), *What goes in*, *Nothing has raised its flag since
<version>.* (*… since the start.* before the first), *In <version> already* (a flag another open release holds),
*Releases from*, *Every party but Ideation*, *Version*, *Mark it out*, *Is <version> out in the stores? Orkboard submits
nothing: say so once you have.*, *Out*, *Its work has started in <party>: a goal moves only before its work starts. Add a
new goal there.*, *Release*, *Release manager*, *Release engineer*, *Release notes*, *Release checker*.

## 1. The agents and the party (A, A0)
1. **`realm/library.py` `LIBRARY`** gains four, after Ideation's, under *-- release: the Release manager (a skeleton)
   and its cheaper hands; a party of their own (spec 68 §1) --*:

| id | name | craft | tier | band | takes | race | line |
|---|---|---|---|---|---|---|---|
| `release-manager` | Release manager | product | warrior | lead | `research` | `skeleton` | Gathers what goes into a version and gets it out, step by step |
| `release-engineer` | Release engineer | engineering | laborer | build | `code` | | Bumps the version, the changelog and the build's config |
| `release-notes` | Release notes | marketing | laborer | build | `text` | | Writes what is new, for the stores and the changelog |
| `release-checker` | Release checker | product | warrior | check | `review` | `skeleton` | Checks that the version, its notes and the list agree |

   ASO (`aso`, laborer, today's) is the fourth hand. The instructions (≤ `roles.INSTRUCTION_CHARS`, the builder words
   them) hold: the **Release manager** plans only from the goals that go in (their titles, *Done when* and flags), never
   new work, names each step a person must do (submit, answer the store's review) as a step for the person, not a task;
   the **Release engineer** changes the version, the changelog and the build's config only, and never a feature;
   **Release notes** says what is new for the person who uses it, one line a goal, in the product's words, nothing that
   did not go in; the **Release checker**'s `Check`: applies *when the goal is a release*, done *Its version, what is
   new and the stores' list name exactly the goals that go in, and nothing was submitted*, its task *Check that the
   version, what is new and the stores' list name exactly the goals that go in, that the build's config carries the
   version, and that nothing was submitted.*, `fits=("product", "engineering", "marketing")`.
2. **The preset** (`PRESETS`, after Ideation): `("release", "Release", "A version out: what goes in, its notes, the
   stores' list", "product", "release-manager", ("release-engineer", "release-notes", "aso"), ("release-checker",))`.
   `STAGES["release-manager"] = Stages("Gather", "Prepare", "Check", 3, 1)`. The tiers are the library's defaults: the
   person may set any of them on Agents as today.
3. **An agent's own race** (decisions §83.5): `Agent` gains `race: str = ""` (its craft's, `roles.RACES`, when empty);
   `listed()` says it; `install` writes it to the role's file; `roles.head` reads a role's `race` when it is one of
   orkUI's and its file is in the copy (`design-system/orkui/races/<race>-<tier>.png`), else its craft's. So before A0's
   copy the Release manager and the Release checker wear the lich's head, after it the skeleton's. **A0** draws the
   skeleton on the races' grid, the three tiers' gear as the others wear it, and adds it to the preview's races row.

## 2. The route (A)
1. **`realm/idea_route.py`** answers a goal's route, oldest first, each step `{step, party, goal, at, …}`:
   - `pitch`: the goal was sent from a pitch (`state.json`'s `from_pitch`): its party (Ideation's slug), the pitch's
     slug, the decision's `answer` and its date;
   - `moved`: the goal was moved from another party (`route.json`'s `moved`, §2.2): from, to, at;
   - `party`: where it is now: the party, the goal's state (`raw`… `done`), its tasks *k of n*;
   - `main`: its flag (`idea_flag.flag_of`): at, by;
   - `release`: the release that holds it (§3): the release goal's slug, its party, its version, `out` (the date, or `""`).
   A goal with only its `party` step has no route to show (the faces draw nothing).
2. **A move** (`ideas.move` with another `track`) goes through `idea_route.move(root, state_dir, slug, to, by)`: refused
   once a task of the goal has run (any task past `waiting`/`ready`, or a plan started), with *Its work has started in
   <party>: a goal moves only before its work starts. Add a new goal there.*; else it records `{from, to, at, by}` in
   `<state_dir>/ideas/<slug>/route.json` (`moved`, the last 20) and moves as today. A move within the party (its order)
   is not recorded. A goal keeps its element (`realm/idea_element.py`, as today).
3. **A sent pitch's goal keeps the pitch's element** where the target party's open goals do not wear it; else the one
   used least, as today (`gui/ideas_pitch.py`, at `ideas.add`).
4. **A sent pitch follows its goal**: the pitch's map row (`board_map`) gains `goal_state`: the sent goal's party, its
   state, *k of n* tasks, its flag's date, its release's version and `out` (the same fields as its route's last steps);
   a goal dropped since says `dropped`.
5. `realm/board_map.py`: each goal gains `route` (§2.1, `[]` when only its party); nothing is read but the goal's
   own files and the releases of its project (§3.2).

## 3. A release (A)
1. **The type *A release*** (`goal_types.py`) keeps its needs (`aso`, `code`) and gains an ask *Version* (`version`,
   *1.4*). It is **not offered beside a Release party**: in a project with a party whose leader is `release-manager`,
   only that party offers it (one place to release); without one, a party offers it as today.
2. **What goes in** (`realm/releases.py`): `candidates(root, state_dir, party)`: the goals with a flag in the parties the
   release's party **releases from**, raised after the last release of that party that is out (all of them before the
   first), newest first; a flag that an open release (not out) holds is listed with `held: <version>` and cannot be
   ticked. *Releases from* is a party's `releases_from` (its page's front matter, a list of party slugs): for the Release
   party, every party of the project but Ideation's and Release's own by default (`[]` means that), set in *Edit the
   party*; for any other party, itself.
3. `ideas.add` of *A release* takes `goes_in` (the slugs ticked; refused with a flag not listed or held); the release's
   file `<state_dir>/ideas/<slug>/release.json` keeps `{version, goals, out: ""}`. The goals that go in are never
   written: their route reads the releases (§2.1).
4. **The draft's and the plan's prompts** get `releases.prompt_lines(root, state_dir, slug)` beside the type's line: the
   version and, for each goal that goes in, its title, its *Done when* and its flag's commit, at most 3 000 characters
   (the goals cut last first, *and k more* said). Nothing else of the parties is read.
5. **Out**: `ideas.release_out {slug}` sets `out` (now), only after the release's own flag (it is in main), once; the
   faces ask first (*Is 1.4 out in the stores? Orkboard submits nothing: say so once you have.*). Orkboard never
   submits, uploads or pushes a tag; the stores' list is the person's to go through.
6. A release goal dropped before *Out* frees its goals (they are candidates again).

## 4. Measured (A)
Events (`EVENTS`, no goal's words): `idea_moved` (goal, from, to) · `release_made` (goal, party, goals: n, parties: n) ·
`release_out` (goal, goals: n, days: from its first goal's flag to out) · `party_shown` (from, to, face), from
`ideas.shown {party, from}`, which the faces send on a party switch (not on a project's first read, not on a redraw).
The party's work (spec 43 §2) for a Release party says releases out, goals a release, the days from a flag to out.
`party_shown`'s count a day and its pairs are read by the owner, not shown (decisions §83.7).

## 5. Refusals and old hosts (A)
- `ideas.move` of a goal whose work started: refused (§2.2); the faces show the refusal's words.
- `ideas.release_out` before the release's flag, twice, or of a goal that is not a release: refused.
- A face of before this spec reads no `route`, `goal_state`, `wait_release` or `race` and draws as today.

## 6. The host's answers (A)
- `board_map`: a goal's `route`; a pitch's `goal_state`; a party's `releases_from` and `wait_release` (the count of its
  candidates not held, for a party that offers *A release*); a flag row's `release` (`{goal, version, out}`).
- `library.listed()`'s `race`; a role's `head` with its own race (§1.3).
- `ideas.party_price`'s and the presets' answers carry Release as any preset.

## 7. The faces (B, C)
1. **The route's line**, on the goal's screen under its title (desktop: `js/board/idea.js` in the drawer; phone: the
   goal's screen): the steps in order, joined by orkUI's ›, each one line: the party's leader's head (small), then its
   words: *From Ideation: Invest, 22 Oct* · *Moved from Mobile app* · *At work in Mobile app · 3 of 7* · *In main* ·
   *In Release 1.4* · *Out in 1.4*. Each step is a button (44 px high on the phone) that opens what it names: the
   pitch's screen, that party with the goal picked into the filter (spec 50 §3.5), or the release goal's screen. No
   route (only its party): no line. On the phone a route longer than the width wraps; never a sideways scroll at 390 px.
2. **A sent pitch** (desktop `pitchview.js`, phone `shell-pitch.js`): under its decision, the goal's line as §2.4 says
   it (*At work in Mobile app · 3 of 7*, *In main*, *Out in 1.4*, *Dropped*), a press opening the goal; in Ideation's
   list a sent pitch's row says the same, short.
3. **New goal of *A release*** (desktop `ideadialog.js`, phone `shell-ideas.js`): after *Version*, **What goes in**:
   the candidates (§3.2), each a row with its goal's element, its title, its party and its flag's date, ticked; a held
   one greyed with *In 1.4 already*; none: *Nothing has raised its flag since 1.3.* and *Add the goal* still adds it
   (a release of fixes not yet flagged is the person's call).
4. **The Release party's goals** (desktop `goals.js`, phone `shell-goals.js`): in its Flags group, a release's row says
   its version and *k goals*, and once in main **Mark it out** (asks first, §3.5); out, it says *Out in 1.4*. At the top
   of its Goals, **k flags wait for a release** (`wait_release`), a press opening New goal of *A release*.
5. **Another party's flags** (its Flags group): a flag in a release says *In Release 1.4*, or *Out in 1.4*; a flag
   waiting says *Waits for a release* only in a project with a Release party.
6. ***Releases from*** in *Edit the party* of a party that offers *A release*: the project's parties to tick, *Every
   party but Ideation* the default; New party of the Release preset shows it ticked so.
7. **A move refused** shows the host's words as the move's toast or line, and the goal stays where it was.
8. **The skeleton's head** is drawn from the host's `race` (the library's, a role's `head`); the faces' craft-to-race
   maps are a fallback for an older host only (C: `shell-who.js` and the maps in the files it touches).
9. **A party switch says `ideas.shown`** (desktop `goaltabs.js`, phone `shell-where.js`), fire and forget, never waited
   for.
10. The pixel face for headings and buttons only; the goals' titles and the notes in the text face (CLAUDE.md). Every
    sign orkUI's (*›*, ⚑, the element, the `release` sign of the type).

## 8. Tests
- **A:** the four agents and the preset (`presets()` holds Release after Ideation; `stages()` the Release manager's
  three words; the tiers); `head` with a race whose file is missing is the craft's, with it the skeleton's; *A
  release* offered by the Release party and not by Mobile app beside it, by Mobile app without it (spec 59 §4.3's list
  otherwise unchanged); a route from a pitch (its answer, its date), a move recorded, a flag, a release, out, in that
  order; a move refused once a task has run, allowed before, not recorded within the party; a sent pitch keeps its
  element when free, not when taken; `goal_state` through each state and *dropped*; candidates since the last release
  out, *Releases from* by default and as set, a held one refused at `ideas.add`, a dropped release freeing its goals;
  the prompt's lines cut at 3 000 with *and k more*; `release_out` refused before the flag and twice; the events hold no
  goal's words; `party_shown` from `ideas.shown`.
- **B** (browser, 1 440 × 900, stub host): a goal sent from Ideation shows its route, each step opening what it names;
  a pitch shows its goal *In main*; New party → Release; *k flags wait for a release* opens *A release* with What goes
  in ticked and a held one greyed; *Mark it out* asks, then the flags say *Out in 1.4*; a refused move's words.
- **C** (390 × 844): the same as sheets; the route wraps, no horizontal scroll; the skeleton's head from `race`; the
  service worker's version.
- B and C: the browser tests that read the Mobile app party's types or the presets' tiles (Release is the fifth tile).
- Each part: the critical tests (CLAUDE.md "Alpha"), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`; C also `tests/test_pwa.py`.

## 9. Outside the parts' files
- `docs/decisions.md` §83 and this file are the contract.
- `realm/ideas.py` (past the size to split at) is not changed: the route and the releases keep their own files.

## 10. As built (A, notes, no change of the contract)

**A (host), 24 October.** Built in `realm/library.py` (`Agent.race`; the four agents after Ideation's; `RELEASE_MANAGER`; the `release` preset
after `ideation`; `STAGES["release-manager"]`; `race_of`; `listed()` and `presets()` say the agent's own race only when orkUI's copy has its
head), `realm/roles.py` (`RACE_FILES`, `own_race`, a role's `race` read, written and kept by `save`, `install(..., race)`, `head`), new
`realm/idea_route.py` (`route`, `steps`, `move`, `moves`, `started`, `goal_state`), new `realm/releases.py` (`read`, `index`, `holding`,
`releases_from`, `set_releases_from`, `sources`, `since`, `candidates`, `offers`, `wait`, `check`, `make`, `out`, `tally`, `prompt_lines`),
`realm/goal_types.py` (*Version*; `release_party`; `offered` drops *A release* beside a Release party), `realm/board_map.py` (node `route`,
`goal_state`, `release`; flag `release`; party `releases_from`, `wait_release`), `realm/goal_flags.py` (a flag row's `release`),
`realm/party_work.py` (`releases` for a Release party), `realm/event_log.py` (four events), `realm/lexicon.py` (four words),
`realm/idea_checks.py` (`TAGS` once each: the Release checker takes `review` like the Reviewer), new `gui/ideas_release.py` (`ReleaseMixin`:
`move`, `release_args`, `release_made`, `release_out`, `release_candidates`, `shown`), `gui/ideas.py` (the mixin, `add`'s release and
element, `page`'s `route`; `move` is now in the mixin), `gui/ideas_pitch.py` (`element_for`; `pitch_of` carries `goal_state`),
`gui/ideas_party.py` (`save_releases_from`), `gui/ideas_goals.py` (`goal_save` calls it when `releases_from` is sent), the three prompts
(`core/idea_draft.py`, `core/idea_keeper.py`, `core/idea_revise.py`). `realm/ideas.py` is untouched. Tests: new `tests/test_idea_route.py`
(9) and `tests/test_releases.py` (20); the counts and orders brought up to date in `test_library.py`, `test_goal_types.py`,
`test_board_map.py`, `test_lexicon.py`, `test_event_log.py`, `test_ideation.py`, `test_goal_team.py`, `test_gui_ideas.py`,
`test_gui_roles.py`, `test_goal_flags.py`, `test_party_hints.py`.

**Deviations and additions** (none changes a contract answer).
- `ideas.move` lives in `gui/ideas_release.py`, not `gui/ideas.py` (which is at its size); `ideas.add` does the same as the spec says.
- `release.json` also keeps `at` (when the release was made): `{version, goals, out, at}`; its route step needs it.
- Added beyond the spec, for the faces: `ideas.release_candidates {party}` (the dialog's *What goes in*: `since`, `releases_from`,
  `candidates`), a release goal's node `release` (`{version, goals, out}`), `ideas.page`'s `route` and `pitch.goal_state`, `ideas.flags`'
  `goals[].release` (a flag row), and a Release party's `ideas.party` key `releases` (`{made, out, goals, days}`, spec §4).
- `race` of a role's file is read for library roles only (`Taskmaster` and `Grunt` have none). The skeleton's files are looked up in
  `orkboard/design/system/orkui/races/` (orkUI's copy), so `head` and `listed()` say `lich` until A0 is copied.
- The Release preset's own `race` is its leader's (`lich` now, `skeleton` after A0).

**The shapes** (for B and C).
- **A route step** (`node.route`, `ideas.page.route`; oldest first; `[]` when only its party step): every step has `step`, `party`,
  `goal` (the slug a press opens), `at`.
  `pitch`: `{party: Ideation's slug, goal: the pitch's slug, at: the decision's date, answer: invest|reshape|pass, word: Invest…, title}`;
  `moved`: `{party: the party it was moved from, from, to, goal: the goal itself, at}`;
  `party`: `{party: where it is, goal: itself, at: the last move's date or "", state, done, total}` (done = merged tasks);
  `main`: `{party, goal: itself, at: the flag's date, by: gate|done}`;
  `release`: `{goal: the release goal's slug, party: its party, version, out: the date or "", at: out, else when it was made}`.
- **A sent pitch's goal** (`node.goal_state` on the pitch's node, `ideas.page(pitch).pitch.goal_state`; None for a pitch not sent):
  `{goal, party, state, done, total, flag: the flag's date or "", release: {goal, party, version, out} | None}`; a goal dropped since:
  `{goal, party: "", state: "dropped", done: 0, total: 0, flag: "", release: None}`.
- **A flag** (`node.flag.release`, `ideas.flags.goals[].release`): `{goal, party, version, out}` of the last release that holds it, else None.
  A flag waits when `release` is None (and the project has a party whose `leader.slug` is `release-manager`).
- **A party** (`ideas.map` goals): `releases_from` (the slugs as saved; `[]` = every party but Ideation), `wait_release` (the candidates
  not held, for a party that offers *A release*, else 0).
- **A release goal** (`node.release`): `{version, goals: [slugs], out}`; None for any other goal.
- **`library.listed()[].race`** and `ideas.roles` presets' `race`: the agent's own when orkUI has it, else its craft's.
- **`ideas.move {slug, track?, before?}`**: refused with *Its work has started in <party>: a goal moves only before its work starts. Add a
  new goal there.* (the party it is in); a move within the party is its order only.
- **`ideas.add {…, type: "release", asks: {version}, goes_in: [slugs]}`**: refused with *That goal has not raised its flag in a party
  this release takes from*, *“<title>” is in <version> already*, *goes_in is a list of goals*; `goes_in` on another type: *Only a release
  takes goals to go in*. `ideas.goal_save {…, releases_from: [slugs]}` (a list of the project's parties but itself, Ideation and General;
  *No party 'x' to release from*, *Releases from is a list of parties*).
- **`ideas.release_candidates {party}`** → `{since: {version, out} | None, releases_from, candidates: [{goal, title, party, party_name,
  element, at, commit, held}]}`, newest flag first; `held` is the open release's version ("a release" when it has none), "" when free.
- **`ideas.release_out {slug}`** → `{ok, out}`; refused with *That goal is not a release*, *Its flag is not raised yet: a release goes out
  once it is in main*, *<version> is out already*. **`ideas.shown {party, from?}`** → `{ok}` (counted only with a `from` that is another
  party of the project; *That party is gone* for an unknown `party`); the event's `face` is the caller's device.

## 11. As built (C, the phone, notes, no change of the contract)

**C (phone), 24 October.** Built in new `pwa/shell-route.js` (`routeLine`, `openStep`: the route's line under a goal's title, the goal's screen is `shell-preview.js` `ideaScreen`, opened from the Goals sheet's ›) and new
`pwa/shell-release.js` (`makeGoesIn`: *What goes in*; `makeReleasesFrom`: *Releases from*), `shell-goals-words.js` (`routeWords`, `goalStateWords`, `flagRelease`, `releaseLine`, `waitWords`, `partyNameOf`, `hasReleaseParty`;
`flagsOf` carries `own`, a release goal's own file; `pitchLine` says a sent pitch's goal), `shell-goals.js` (*k flags wait for a release*, a flag's release, a release's row with **Mark it out**), `shell-party.js` (*Its flags*
say the same), `shell-pitch.js` (a sent pitch's goal under its decision and in Ideation's list), `shell-ideas.js` (*A release*: *What goes in* after *Version*; `goes_in` sent; `open(slug, type)`), `board.js`
(`core.newIdea(type, slug)`), `shell-goal-new.js` (New party: *Releases from* for the Release party; `raceOf`), `shell-goal.js` (Edit the party: *Releases from*; `raceOf`), `shell-where.js` (`ideas.shown`),
`shell-who.js` (`skeleton` in `RACE_WORDS`, `RACE_OF`, `raceOf`: the host's `race` first, the craft's for an older host; used in `shell-goal-new.js`, `shell-goal.js` and `shell-agents.js`), `app.css`, `sw.js` (`CACHE`
v76; the two new modules in `SHELL`). Tests: new `tests/test_pwa_route_browser.py` (6) and `tests/test_pwa_release_browser.py` (13); `sw.js`' version pin moved to v76 in every phone test that pins it, and
`test_pwa_mixed_parties_browser.py`' tiles say *Release* fifth.

**Deviations and additions** (none changes a contract answer).
- `shell-release.js` is a second new file (the spec names only `shell-route.js`): `shell-ideas.js` and `shell-goal-new.js` are near the size to split at. *Releases from* sits in `shell-goal.js` (Edit the party's form is there,
  not in `shell-party.js`, which is the About sheet) and, for New party, in `shell-goal-new.js`.
- **Route steps**: a step's words are `routeWords` (*At work in <party>* for every `party` step, with *k of n* when the goal has tasks); a `pitch` or `release` step opens the pitch's sheet or the release goal's screen
  (`core.open`); a `party` or `main` step closes the screen and shows that party with the goal picked into the filter (`st.picks`); a `moved` step shows the party the goal came from, whole (it no longer holds the goal).
  The current (last) step is `aria-current="step"`.
- **A sent pitch's goal** is a 44 px button *Its goal · <words>* at the end of the sheet's Decision, disabled for *Dropped*; Ideation's row line and the Goals sheet's row say the same words from `goal_state` (the
  *sent to Passkey: …* of before for an older host).
- **Releases from**: shown in Edit the party when the party's Map `types` hold *A release*, and in New party for the Release preset (every party but Ideation, General and the party itself, all ticked). A Release party
  keeps at least one ticked (none would mean every party: all ticked is sent as `[]`); another party that offers *A release* starts with none ticked (its own flags). It is sent as `releases_from` only when changed.
- **A refused move**: the phone has no gesture that moves a goal to another party (nothing in `pwa/` sends `ideas.move`), so there is nothing to show a refusal for yet; a refusal of any command is the toast `core.call`
  already says in the host's words. **Mark it out** says its refusal (*Its flag is not raised yet: …*) in the ask and keeps asking.
- **`ideas.shown`** is sent from the parties' sheet only (`shell-where.js`), with `from` the party shown, not for the party already shown, not for Operations as `from`; never awaited, never a toast.
- **Tests run with** `--with cryptography --with segno --with websockets` (the phone's listener needs `cryptography`): all 356 phone tests of `tests/test_pwa*.py` passed before the two new files, which pass too.

## 12. As built (B, the desktop, notes, no change of the contract)

**B (desktop), 24 October.** Built on spec 69's column (the left column is the list of the parties; the open party's body is `goals.js` `Left`). New `js/arena/releasewords.js` (the phone's words, ported: `routeWords`, `goalStateWords`, `flagRelease`,
`releaseLine`, `waitWords`, `outAsk`, `partyName`, `partyOf`, `hasReleaseParty`; the desktop cannot import from `pwa/`), new `js/arena/route.js` (`RouteLine`, `openStep`), new `js/shell/release.js` (`GoesIn`: *What goes in*;
`useReleasesFrom` and `ReleasesFrom`: *Releases from*; the spec names `ideadialog.js`, `goaldialog.js` and `goalwizard.js` only, which are near the size to split at), `board/idea.js` (the route at the top of the goal's screen),
`shell/pitchview.js` (a sent pitch's goal under its decision), `arena/pitchwords.js` (`pitchWords` of a sent pitch says `goal_state`, else *sent to <party> · <goal>* as before: Ideation's row, the bar of a pitch's screen),
`shell/ideadialog.js` (*A release*: `GoesIn` after the *Version* ask; `goes_in` sent), `shell/goaldialog.js` and `shell/goalwizard.js` (*Releases from*; sent as `releases_from` only when changed), `arena/goals.js` (*k flags wait for a
release*, a flag's release, a release's row with **Mark it out**), `arena/partylist.js` (`ideas.shown`), `shell/party.js`, `shell/goalwizard.js` and `shell/agentdialog.js` (an agent's head from the host's `race`, the craft's for an older
host: `raceOfAgent`), `arena/arena.css`. `shell/shell.css` is unchanged. Tests: new `tests/test_route_desktop_browser.py` (8) and `tests/test_release_desktop_browser.py` (11); no desktop test of before changed.

**Deviations and additions** (none changes a contract answer).
- **The route** stands at the top of `IdeaView` (the drawer's tab strip is the goal's title), `nav[aria-label=Route]` with a `Route` label, a `.arena-route__step` button for each step (the party's leader's small head from the Map's `leader.head`, then the words; the
  last is `aria-current="step"`), orkUI's › between. A `pitch` or `release` step opens that goal's screen (`showIdea`, no `via`: the host refuses a `via` that is not in its list); a `party` or `main` step shows that party (`track`) with the goal
  picked into its filter (`picks`); a `moved` step shows the party it came from, whole. The drawer stays open: the board changes behind it. A step is *At work in <party> · k of n* only while its goal is `working`, else *In <party>*, as the phone.
- **A sent pitch's goal** is *Its goal · <words>* under the decision (`data-after="goal"`), the words a button that opens the goal, plain text for *Dropped*. Ideation's row and the bar of a pitch's screen say the words themselves (not a shorter form:
  the line of a row is cut with an ellipsis in the narrow column).
- **Flags**: a flag row says its release words in their own line (`data-rel`: `in`, `out`, `waits`; a release's own row `own`, *1.4 · 3 goals*). **Mark it out** is a button under the row; a press asks in place (*Is 1.4 out in the stores? Orkboard submits
  nothing: say so once you have.* with **Out** and **Not yet**, as the phone), a refusal is the host's words as the toast the command already gives and the question stays; then the row and the goals that went in say *Out in 1.4*.
  *k flags wait for a release* is `.arena-waitrel`, a quiet button at the top of the open party's Goals, shown when the Map's party has the `release` type and `wait_release > 0`; a press opens New goal of *A release* (`openDialog("idea", {goal, type})`).
  The closed Release heading does not show the count (the spec says it may): the heading's *k/n* and stop sign stay as spec 69 has them.
- **What goes in** is read when the dialog opens (`ideas.release_candidates {party}`) and ticks the free flags; a goal kept for tonight (*Put it back* with words) sends no `goes_in`, as it brings no one.
- **Releases from**: New party shows it when the leader is the Release manager (the preset or a seat picked so), ticked: all (sent only when changed; all ticked is `[]`), one always stays. Edit the party shows it when the Map's party holds the `release` type, from its
  `releases_from` (a Release party: all ticked when `[]`; another party: none).
- **A refused move**: the desktop has no gesture that moves a goal to another party (nothing in `js/` sends `ideas.move`), so there is nothing to show a refusal for yet; a refusal of any command is the toast `command` already says in the host's words.
- **`ideas.shown`** is sent from `partylist.js` `show()` (a press on a closed heading), `{party, from}`, not awaited, not for Operations on either side, not for the open heading; the first read sends none.
- **Tests run with** `--with cryptography --with segno --with websockets`: 338 desktop browser tests (`tests/test_*desktop_browser.py`, `test_board_browser.py`, `test_shell_browser.py`, `test_races_browser.py`) ran: 335 passed, 3 failed under load, of which
  `test_shell_browser.py::test_a_file_todo_shows_its_steps_and_uploads_the_file_and_a_secret_shows_its_steps_too` also fails on `main` and the other two (`test_type_top_right_desktop_browser.py`, `test_board_browser.py`'s phone test) pass when re-run alone.

