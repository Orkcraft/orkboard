# Spec 46 — A goal's trail: its party asks with its leader, its leader lays out its ideas, yours join them; the desktop catches up with the phone

The owner, 20 October (decisions §59). A goal is read and asks its questions, then stands empty: its ideas come one by
one from the person, or two a night (balance) from the proposals, never more than three waiting, and the Map of a new
goal is a flag with nothing on the way to it. Its party (spec 43) says nothing until the work: the goal is read by its
leader alone, whatever its designer or its reviewer would have asked. And the desktop is behind the phone: New goal is a
plain button under the goal's select (the owner could not find it) and on the Map only while there is no goal; it is
three steps where the phone has one sheet; what waits for an answer hides in a tab behind the Board while Review, which
is not a signal (decisions §54.1), keeps a column of its own; the Map has no button. This spec lets the party ask with
its leader (§1–§2), has the leader lay out the goal's ideas as proposals once its questions are answered (§3–§4), lets an
idea the person adds join that trail (§5), and gives the desktop the phone's New goal, its Needs you with Review and the
Map's one action (§6). **Builds:** Claude · **Review:** full · P1.

**Independent of specs 44 and 45** (written, not built): it shares `realm/idea_target.py`, `realm/board_map.py`,
`realm/event_log.py`, `realm/lexicon.py`, `core/idea_keeper.py` (one base class) and the phone's cache with them;
whichever is merged second takes both. Read specs 41 §12 and 43 §11 "As built" first.
**What it is, and is not:** a trail is proposals (spec 35 §8): no spec is written, nothing is drafted and nothing is spent
on an idea of it until the person takes it. One round of questions stays (spec 35 §0): the party's questions are that
round's, not a round of their own. The Map stays a view (decisions §52.1): its one button is one its node's own screen
has. No new setting.

Four parts, one branch each. A first; B from `main` once A is merged; C from `main` at once (it touches no file of A's
or B's); D from `main` once B and C are merged (CLAUDE.md "Alpha"). **This file is the contract**; the rest is the
builder's choice inside its files. **Change nothing outside a part's files** but those §10 names. `realm/ideas.py` (609
lines) and `core/idea_keeper.py` (604) are past the size to split at: nothing is added to them but `idea_keeper.py`'s one
base class; what a part needs of them goes beside them.

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A. The party asks** | `spec/46-party-asks` | §1, §2 | `realm/idea_target.py` (the `ask` step, `GOAL_QUESTIONS`), `core/idea_goals.py` (the party in the goal's read; the members' calls), `realm/idea_questions.py` (a question's `by`), `gui/ideas_goals.py` (`goal_needs`: who asks; `goal_read`'s and `goal_answered`'s new fields), `gui/ideas_board.py` (`ideas.answer` on a goal: `by_party`), `realm/event_log.py` (`party_asked`), `realm/lexicon.py` (`member`); `tests/test_idea_target.py`, `tests/test_idea_keeper.py`, `tests/test_idea_questions.py`, `tests/test_gui_goals.py`, new `tests/test_party_asks.py` |
| **B. The trail** | `spec/46-trail` | §3–§5 | new `core/idea_trail.py` (the `trail` step and Take all, a mixin as `idea_goals.py` is), `core/idea_keeper.py` (its base), `core/idea_goals.py` (a read that ends `ready` lays out the trail), `core/idea_draft.py` (`needed_by`, `same_as`), `realm/idea_target.py` (`trail`, `TRAIL`), `gui/ideas.py` (two commands in its table), `gui/ideas_goals.py` (`ideas.trail`, `ideas.trail_take`, the `trail` row, a goal's `trail`), `gui/ideas_board.py` (`ideas.proposal`'s `via`), `realm/board_map.py` (a trail proposal is not a row of its own; nodes' `proposed_by`, `trail_by`, `same_as`; goals' `trail`), `realm/event_log.py`, `realm/lexicon.py` (`trail`); `tests/test_idea_target.py`, `tests/test_idea_draft.py`, `tests/test_gui_goals.py`, `tests/test_board_map.py`, `tests/test_idea_night.py`, new `tests/test_goal_trail.py` |
| **C. The desktop catches up** | `spec/46-desktop` | §6 | `js/board/map.js`, `js/board/maplayout.js`, `js/board/tracks.js` (the select's *New goal…*), `js/shell/goalwizard.js`, `js/shell/party.js`, `js/shell/shell.js`, `js/shell/boardpane.js`, `js/shell/review.js`, `js/board/today.js`, `js/shell/store.js` (`leftTab`, `showNeeds`), `js/shell/shell.css`, `js/board/board.css`; `tests/test_shell_browser.py`, `tests/test_map_desktop_browser.py` |
| **D. The trail's faces** | `spec/46-trail-faces` | §7 | desktop: `js/board/today.js`, `js/board/tracks.js`, `js/board/map.js`, `js/board/maplayout.js`, `js/board/store.js` (a state's words), `js/shell/goalview.js`; phone: `pwa/shell-needs.js`, `pwa/shell-map.js`, `pwa/shell-goal.js`, `pwa/shell-ideas.js`, `pwa/app.css`, `pwa/sw.js` (the next `CACHE`); `tests/test_shell_browser.py`, `tests/test_map_desktop_browser.py`, `tests/test_pwa_shell_browser.py`, `tests/test_pwa_map39_browser.py`, `tests/test_pwa.py` |

## 0. The words
- **the trail** (`TERMS` `trail`, *trail / trails*): a goal's ideas in their order, from where it stands to its flag, as
  the Map draws it (spec 39); what its leader lays out (§3).
- **to lay out** (no term: the button's words, *Lay out ideas*): the `trail` step, the leader writing the goal's missing
  ideas as proposals.
- **a trail proposal** (no term: code only, `proposed_by: "trail"`): a proposal (`TERMS` `proposal`) the trail made; the
  night's stay *proposals*, as today.
- **a member** (`TERMS` `member`, *member / members*): one of a goal's party who is not its leader — a builder or a
  checker (`goal_team.team_of`) that is a role of the project, never Grunt or the Taskmaster.
- Today's words stay: *party*, *leader*, *check*, *proposal*, *Take*, *No*, *Needs you*, *Review*, *recommended
  answer*, *Let the Taskmaster decide*.

## 1. The party in the goal's read (A)
No face.
- **By the Target**, the goal's read (`core/idea_goals.py`, step `goal`):

| Target | the read | questions at most (`GOAL_QUESTIONS`) |
|---|---|---|
| thrift | the leader alone, as today | 3 |
| balance | the leader, each member's view in its context | 3 |
| quality | each member asked first (§2), then the leader, their views and their questions in its context | 5 |

  A goal with no member reads as today, whatever the Target. An idea's draft keeps `MAX_QUESTIONS` (3).
- **A member's view** (balance, quality): a part of the `goal` context, *Your party*, after the description: each
  member's name, craft, band (*builds* / *checks*), its library `line` (else the first 200 characters of its
  instruction) and, for a checker, its check's `applies` and `done`. Cut with the rest (`idea_target.cut`), before the
  links and the Wiki's index.
- **Who asks**: the `goal` answer's questions gain `by`: the slug of the member whose view the question answers, else
  empty (the leader's own). The prompt says: ask what the party needs to know before the work can be laid out; a
  member's question only when its answer changes the goal; never two questions on one thing.
- **Kept**: the goal's state gains `asks_by`, one slug per Open question in their order: the member's, or the leader's
  (`taskmaster` with none) for its own and for a `by` that is no member. The page's lines are not changed
  (`idea_questions.line`): the page keeps what is asked, the state who asks it.
- **Needs you** (`gui/ideas_goals.py` `goal_needs`): each of a `goal` row's `asked` gains `by`: `{slug, name, head}`
  (`roles.head` at the Target), the leader's for its own.
- **The other reads** — with the person's answers (`answered`), an Edit's, a night's refresh — have the members' views in
  their context (balance, quality) and ask no member (§2).
- **Measured**: `goal_read` gains `party` (how many members' views it had) and `by_party` (how many of its questions are
  a member's); `goal_answered` gains `by_party` (how many of the questions answered were a member's) beside its tally
  (spec 41 §10).

## 2. A member asks (A; quality only)
No face.
- On a goal's read with no answers (step `goal`, not `answered`), before the leader's call, each member is asked once,
  all at the same time (one thread each, at most `goal_team.SEATS`); the goal is `reading` meanwhile.
- **Step `ask`** (`STEPS`, `MATRIX`): thrift none, balance none, quality `("warrior", "low")`; a member with a model of
  its own runs on it, the Target still giving the effort (as a role's task, `task_pick`). `CONTEXT["ask"] = 4_000`,
  `READS["ask"] = 0` (no tools, as `propose`), `CAPS["ask"] = 0.10`.
- **Its prompt**: who it is (its name and its instruction, as `core/idea_lead.py` `voice` says a leader's), the goal's
  description, priority and craft, the party's names and bands. It answers `{"questions": [at most 2 of {ask, choices,
  pick, why}]}`, taken by `idea_questions.all_of`.
- **The leader's call** gets them as a part, *What your party asks* (each under its member's name), and keeps at most
  `GOAL_QUESTIONS` of its own and theirs, each with its `by` (§1).
- A member whose call fails, runs out of its budget or answers nothing adds nothing, and the read goes on. Stop all and
  the goal's own stop stop the members' calls as they stop the read. The window (spec 35 §6): a member is not asked in a
  spent window; the leader reads alone.
- **Measured**: `party_asked`, one per member's call: `goal, by, questions, step: "ask", prompt_chars, tokens, cost`.

## 3. The trail (B)
No face.
- **When**: a goal's read (step `goal`) that ends `ready` lays out its trail at once, in the same run (the goal's key,
  `goal:<slug>`), when the goal has no `trail_at` and at most 2 ideas: a goal whose ideas the person wrote already is
  the person's to lay out (*Lay out ideas*, §4). A refresh never lays out; nor does a read that ends `asks` or `raw`.
- **Step `trail`** (`STEPS`, `MATRIX`): thrift `("elder", "low")`, balance `("elder", "medium")`, quality `("elder",
  "high")`, run as the goal's leader (decisions §53: its steps run as it). `CONTEXT["trail"] = 10_000`,
  `READS["trail"] = 4` (its links first), `CAPS["trail"] = 0.60`. `TRAIL = {"thrift": 3, "balance": 5, "quality": 7}`:
  at most that many new ideas a lay out.
- **Its context**, cut in this order: the goal (title, description); its Summary; its Metrics, with how each is counted;
  its ideas (slug, title, state, `depends_on`); its links (paths); its party (who builds which tags, `team_lines`; each
  checker's check, its `applies` and `done`); the proposals of this goal turned down (`declined`: title, reason); the
  other goals' open ideas (titles, at most 40, as the draft's).
- **It answers**:
  `{"ideas": [{"key": "t1", "title": "…", "short": "24 characters at most", "why": "two lines: what it does and which
  metric it moves", "after": ["keys of this list, or slugs of the goal's ideas, that must be done first"], "by": "a
  member's slug when the idea answers that member's view or check, else empty"}]}`.
  The prompt says: the ideas that take the goal from where the repository is to its metrics, in the order they should be
  done; each one spec's worth (one to eight tasks); nothing an idea of the goal covers already; a checker's check is held
  by every idea it applies to (spec 43), so it is an idea of its own only when the work it checks needs one (*a test
  suite for the sync*).
- **Written, strictly**, in the answer's order, after the goal's ideas, at most `TRAIL`: each an idea of the goal (its
  Gist the `why`; its `title` and `short`) in the state `proposed` with `proposed_by: "trail"` and `trail_by` (the
  member's slug; none for the leader's or an unknown one); front matter `depends_on` from `after` (keys turned into the
  new slugs; only ideas that exist; no cycle: `idea_draft.depends_ok`). A title the person turned down for this goal, or
  an idea's of the goal, is dropped (case aside). No priority is written: it is the goal's until taken, as a proposal's.
- **The goal's state** gains `trail_at` (the time) and `trail` (the slugs written). Event **`trail_laid`**: `goal, ideas,
  dropped, via ("read" | "person"), step: "trail", prompt_chars, tokens, cost`.
- A call that fails or runs out of its budget writes nothing; the goal stays `ready`, its state says the error (as a
  read's), and *Lay out ideas* tries again.
- **The night is unchanged**: a trail proposal counts among the proposals waiting (`MAX_WAITING`), so the night proposes
  nothing while three or more wait; the trail is not held by `MAX_WAITING` (a lay out writes up to `TRAIL` whatever
  waits). A proposal without `proposed_by` is the night's.

## 4. Taking it (B)
No face.
- **`ideas.trail {goal, via}`** (*Lay out ideas*): lays out the goal's trail now, in the background, as the goal's run
  (`via: "person"` on `trail_laid`). Refused in plain words: a goal not `ready` (*The goal is being read, or waits for
  your answers*), a goal with trail proposals waiting (*Its laid-out ideas wait for you: take them or say No first*), the
  leader busy with it, the window and the reserve (as a read is).
- **`ideas.trail_take {goal, via}`** (*Take all*): every trail proposal of the goal that waits is taken as
  `ideas.proposal` takes one, at the goal's priority; those of the queue `now` are drafted **one at a time, in the
  trail's order**, in the goal's run (the night's way, `draft_one`), never all at once; Low ones go to the night (spec 44
  says when). Event **`trail_taken`**: `goal, ideas, via`.
- **`ideas.proposal`** (one, Take or No) is unchanged but for `via` (`"needs"`, `"map"`, `"board"`, `"idea"`);
  `proposal_answered` gains `via` and `proposed_by`.
- **Needs you**: a goal's trail proposals that wait are one row, kind **`trail`** (`goal_needs`): `{kind: "trail",
  goal, title (the goal's), short (the goal's), text: "5 ideas laid out", ideas: [{slug, title, short}], priority (the
  goal's), blocks: false, at: trail_at}`, among the proposals (last; they block nothing; out of the count). A trail
  proposal is not a `proposal` row of its own (`realm/board_map.py` `idea_needs`); the night's are, as today.
- **Payloads**: `ideas.board`'s goal rows and `ideas.map`'s goals gain `trail`: `{at, waiting, busy}` (`waiting`: how
  many of its proposals wait; `busy`: the leader is laying it out now); `ideas.map`'s nodes gain `proposed_by`,
  `trail_by` (`{slug, name, head}` or `null`) and `same_as` (`{slug, short}` or `null`, §5).

## 5. An idea the person adds joins the trail (B)
No face.
- The draft (`core/idea_draft.py`) reads the goal's ideas with their states already, and writes `depends_on` and
  `before`. Its answer gains two fields:
  - **`needed_by`**: the slugs of the goal's ideas not drafted yet (`proposed` or `raw`) that should wait for this one;
    the code adds this idea to each one's `depends_on` (no cycle, at most `MAX_DEPENDS`). An idea drafted already is
    never changed by another's draft.
  - **`same_as`**: the slug of a proposal of the goal (the trail's or the night's) that does the same thing, or empty;
    kept on that proposal's state (`same_as: <this idea's slug>`). The proposal is not removed: the person says No or
    Take (§7).
- **Measured**: `idea_drafted` gains `needed_by` (how many) and `same_as` (true when it named one).

## 6. The desktop catches up with the phone (C)
Desktop only; no backend change; the phone is not touched.

### 6.1 New goal, found
- **The Map's head**: *New goal* (`.ork-btn`) above its cards, always; the empty Map keeps its primary one.
- **The goal's select** on the Board: its last option *New goal…* (after Operations); picking it opens New goal and the
  select keeps the goal shown.
- The Board's *New goal* beside the select stays.

### 6.2 New goal on one sheet
Spec 41 §6 on the desktop (`goalwizard.js`; spec 41 §12: *Engineering* is picked at the start, so Save goal needs only
the description): one modal, top to bottom — **What for** (the description, focused; the priority), **Craft** (one row
of six heads, the five crafts and Mixed, the picked one's word and line under it; a pick sets the team to the craft's
party), **Team** folded to one line with Change (three folds, Leads · Builds · Checks, one open at a time, each closed by
Done), **Checks** folded to one line, what is left of the AI tools; **Save goal** in the modal's foot, enabled once the
description has words. The command is today's (`ideas.goal_save` with `craft`, `team`, `every`, `leader`). Edit goal
(`goaldialog.js`) is not changed.

### 6.3 Needs you, with Review, on the right
- **The right column is Needs you** (it was Review): its head *Needs you* with the signal (spec 41 §1:
  `.ork-count.warning` while an answer waits); then the rows that wait for an answer, as the left column's tab has them
  today (`today.js`: the questions answered in their rows, Later, the proposals last); then **Review**, a section of its
  own with its count, *Merge into* ▾ and its cards as today (↑ ↓ as today, no shortcut merges). Nothing in either:
  *Nothing waits for you.*
- **The left column is Board · Files** (Files with projects, as today); the Needs you tab goes. A `leftTab` of
  `"needs"` kept from before reads `"board"`. `showNeeds()` (a card's link to Needs you) scrolls the right column to its
  top and moves the focus there.
- **Below 1 024 px** the shell's tabs are **Board · Agents · Needs you** (the phone's order and marks), Needs you the
  signal as the phone's: the warning mark and colour while an answer waits, the eye and a plain count while only results
  wait; its label says both (*Needs you: 2 wait for your answer, 3 results to check*).
- `opened` logs `tab: "needs"` where it logged `"review"`.

### 6.4 The Map's one action
Spec 41 §4 on the desktop: its table (a plan to start, *Start now*, *Process now*), its words and labels, `via: "map"`; a
sibling button beside the stop's chip, never inside it; at most one per node; none while the node waits for anything
else.

## 7. The trail's faces (D, both faces)
- **A goal's questions** (Needs you's `goal` row and its form): each with the head of who asks (12 × 11, decisions
  §53.8) and its name in its label, *Reviewer asks: …*; the leader's own with the leader's head.
- **Needs you's `trail` row**: the goal's flag mark, *<goal's short name>: 5 ideas laid out*, the first three titles and
  *and 2 more*; **Take all** (primary, `ideas.trail_take`) · **Look** (the Map at that goal: on the desktop the Map's
  tab, scrolled to it; on the phone the Board tab's Map).
- **A trail proposal**: on the Map, a fog stop as a proposal is today, its one action (§6.4, spec 41 §4) **Take**
  (`ideas.proposal {take: true, via: "map"}`, at the goal's priority); its words say *proposed by <name>* when it has
  `trail_by`, *the same as your <short>?* when it has `same_as`. On the desktop's Board, the goal's ideas list shows its
  trail proposals in their order (proposals are left out of it today), each row *proposed* with **Take** and **No** (an
  optional reason, as Needs you's proposal row; filled with *the same as <title>* when it has `same_as`).
- **Lay out ideas**: on the goal's screen (desktop `goalview.js`, phone `shell-goal.js`) while the goal is `ready` and
  no trail proposal of it waits. While it runs, the goal's card, its screen and the Map's goal head say *<leader> is
  laying out its ideas…*. The host's answer is said as a read's is.
- Nothing pops; no toast but the host's answer; no colour (a proposal is not a signal, decisions §53.5).

## 8. Tests
- **A**: `pick("ask", t)`: none in thrift and balance, `("warrior", "low")` in quality; `budget("ask", "quality")`
  0.20; `GOAL_QUESTIONS`. With a fake `ask`: in thrift the goal prompt has no *Your party*; in balance it has each
  member's name, band and line and a checker's check, and no member is called; in quality each member (not Grunt, not the
  leader, not a slug that is no role) is called once, all before the leader, whose prompt has *What your party asks*; a
  member's failure, empty answer or spent budget and the read goes on; Stop all stops them; no member is called on the
  read with answers, an Edit's or a refresh. `by` kept as `asks_by` in the questions' order (a member's, the leader's,
  an unknown one as the leader's); at most 3 questions in thrift and balance, 5 in quality; `goal_needs`' `asked[].by`;
  `party_asked`; `goal_read`'s `party` and `by_party`; `goal_answered`'s `by_party`.
- **B**: a read that ends `ready` on a goal with at most 2 ideas and no `trail_at` lays out once — not with 3 ideas, not
  on a refresh, not twice; at most 3 · 5 · 7 by the Target. Written strictly: `proposed`, `proposed_by`, `trail_by`, the
  Gist, `title`, `short`, `depends_on` from keys and slugs, a cycle cut, an unknown key dropped, a turned-down title and
  an idea's title dropped, the order after the goal's ideas. A failed call writes nothing and the goal stays `ready` with
  its error. `ideas.trail`'s refusals; `ideas.trail_take`: each taken at the goal's priority, the `now` ones drafted one
  at a time in the trail's order (a fake draft records the order and that no two overlap), Low ones to the night;
  `trail_taken`. Needs you: one `trail` row per goal, none of its proposals a `proposal` row, the night's still one each,
  all out of the count. The night counts trail proposals as waiting; a proposal without `proposed_by` is the night's. The
  draft's `needed_by` (only the goal's `proposed` and `raw`, no cycle, at most `MAX_DEPENDS`, a drafted idea untouched)
  and `same_as` (on the proposal's state; nothing removed). `ideas.map` and `ideas.board`: goals' `trail`, nodes'
  `proposed_by`, `trail_by`, `same_as`; the Map's 200-idea timing still holds. `proposal_answered`'s `via` and
  `proposed_by`; `trail_laid`.
- **C** (browser, desktop): *New goal* on the Map's head with goals; the select's *New goal…* opens it and the select
  keeps the goal; the Board's stays. New goal on one sheet: Save goal disabled until the description has words; the
  craft's row sets the party; the folds one open at a time; the command's arguments as the three steps' were. The right
  column is Needs you: its signal, its rows, Review's section with its count and cards, *Nothing waits for you.*; the
  left column's tabs Board · Files; a kept `"needs"` reads `"board"`; a card's link to Needs you focuses the right
  column; below 1 024 px Board · Agents · Needs you with the phone's signal and label. The Map's one action: the three
  buttons, their labels, `via: "map"`, none on a node that waits for anything else.
- **D** (browser, both faces): a goal's question with its asker's head and *<name> asks*; the `trail` row's words,
  *Take all* sends `ideas.trail_take`, *Look* shows the goal on the Map; a trail proposal's stop: *Take* on the Map,
  *proposed by …*, *the same as your …?*; the desktop's ideas list rows with *Take* and *No* (No's reason filled from
  `same_as`); *Lay out ideas* shown only while the goal is `ready` and no trail waits; *… is laying out its ideas…*
  while it runs.
- Each part: the critical tests (`orkcraft.toml` `always`), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`; D also `tests/test_pwa.py`.

## 9. Measured
What the owner reads after a week, from the events above (decisions §59.5):
- Of the trail's ideas: taken (Take, Take all), turned down (No, and its reasons), still waiting; of those taken, merged
  within 14 days; laid out by the read against by the person (`trail_laid` `via`).
- Of a goal's questions: the members' share, and how the person answered them (a choice, the recommended one, typed,
  left to the Taskmaster) against the leader's own (spec 41 §10's tally, split by `by_party`).
- What a goal costs to read and lay out, by Target (`goal_read`, `party_asked`, `trail_laid`).

## 10. Files a part may need beyond its row
`core/idea_lead.py` (A: a member's voice beside the leader's), `core/idea_night.py` (B: only a helper that writes a
proposal, shared with the trail), `tests/test_shell_browser.py`'s `StubHost` and `tests/test_pwa_shell_browser.py`'s
`Stub` (C, D: the new fields). Anything else: stop and write it in §12 first.

## 11. Not in this spec
- The party asked on an idea's draft (only on a goal's read); a second round of questions; members asked on a refresh
  or after the answers.
- A trail taken by itself, or a proposal drafted before it is taken; a setting to turn the trail off (measured first,
  §9).
- Changing the trail on the Map (decisions §52.1: a view; its one action is its node's own).
- The phone's top bar and drawer on the desktop (spec 41 §2: the desktop has the room); Edit goal on one sheet.
- A trail for Operations.

## 12. As built (notes, no change of the contract)

### A. The party asks
- **Where.** The members' calls, the views and `asks_by` are in `core/idea_goals.py` (`members`, `party_view`, `ask_members`); a member's voice is `idea_lead.py` `voice` (a member is a role dict with `member: True`, which `leader()` returns on the member's thread, so `keeper.ask` picks its model and writes its ledger line as it does a leader's). `idea_target.py` has no new function: a member with a model of its own runs on it through `keeper_pick`, like a leader.
- **First read only.** Members are asked on a goal's *first* read, which is `ideas.goal_save` of a new goal (`read_goal(..., party=True)`); an Edit's save, `ideas.say`, the answers, a read run again while busy and the night's refresh ask none. In balance and quality those reads still carry the views.
- **What is kept.** `asks_by`, `party` and `by_party` are kept in the goal's `state.json` (not read by `ideas.goal_state`, which is in a module past its size); `GoalsMixin._goal_extra` reads them. `goal_answered`'s `by_party` counts the member's questions with a non-empty answer.
- **`by` is a question's own key**, kept by `idea_questions.of` only when the model wrote one (an idea's questions have none); `idea_questions.asked_by` makes `asks_by`.

### B. The trail
- **Where.** `core/idea_trail.py` (`TrailMixin`: `lay_out`, `lay_out_goal`, `write_trail`, `draft_trail`, `trailing`, `trail_waiting`); the night's proposal is written by `idea_night.write_proposal`, which the trail shares. `idea_draft.py` `join_trail` applies `needed_by` and `same_as` after `write_draft`; the draft prompt asks for both.
- **What a proposal keeps.** `proposed_by`, `trail_by` and `same_as` are kept in the idea's `state.json` beside the Board's keys (`ideas.state` reads only its own, in a module past its size): `realm/board_map.py` `proposal_state` reads them, `is_trail` and `trail_of` build on it.
- **A read that ends `ready` lays out in its own run** (the goal's key stays busy), not in a run of its own; `keeper.trailing(goal)` says it, which is the goal's `trail.busy`. It lays out after an `answered` read and after a first read with no questions; not in a spent window or when the keeper may not run (Lay out ideas then says why). An answer with no usable idea still sets `trail_at`, so it is not laid out twice by itself; Lay out ideas tries again. Stop all during a lay out writes nothing and leaves no error.
- **`after` and cycles.** Every idea is written first, then each one's `depends_on` is set in the answer's order (`depends_ok`): a forward reference is kept unless it closes a cycle with the ones set before it. `dropped` counts the entries of the answer not written (no title, a title taken or turned down, a duplicate, past `TRAIL`).
- **Take all** is `GoalsMixin.trail_take` + `BoardMixin.take_proposal` (the one the single Take uses) + `keeper.draft_trail`: the `now` ideas are marked busy so the clock leaves them to the run, drafted in the trail's order with their own spend; Stop all leaves the rest in the queue `hold`; a spent window leaves one with `held_until`. `trail_taken.ideas` counts the ideas taken (also the Low ones).
- **Needs you.** `GoalsMixin.trail_rows` makes both the goal rows' `trail` on `ideas.board` and the `trail` rows (kind `trail`, sorted with the proposals, out of the `needs_you` count). `ideas.goal` carries `trail` too.
- **Events.** `proposal_answered.proposed_by` is `trail` or `night`; `via` is one of needs · map · board · idea (else `idea`). `trail_laid`, `trail_taken`, `idea_drafted.needed_by` (how many ideas were made to wait) and `.same_as` (true) as the contract says.
- **Tests that changed.** A first read that ends `ready` now makes a second call, the trail: the stubs of `tests/test_board_35.py`, `tests/test_gui_goals.py` and `tests/test_party_asks.py` answer it (empty) apart from the reads they count.
