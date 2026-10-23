# Spec 65 — Ideation: a small idea read from four sides; the Investor invests in it, or passes, and says why

The owner, 23 October (decisions §78): *we drop small ideas and concepts, and they are judged from the product's,
marketing's, engineering's and design's side: either where to take the idea, or why it should not be done.* Today every
goal goes the one way of a party: draft → plan → tasks → Review → the gate. A small idea has nothing to merge yet, and a
party's builders and checkers would sit idle on it; and a goal the person drops is gone (`ideas.drop` removes its page),
with the reason it was not worth doing. So: **a party of the library, Ideation, whose goals are pitches: each is read by
four views and a skeptic, each alone; then its leader, the Investor, decides whether to invest in it — invest (in which
party, as what type of goal), reshape, or pass — with why; and a pitch passed is kept with its why, so the next one like
it is judged against it.** **Builds:** Claude · **Review:** full · P2.

**What it is, and is not:** a party preset, six agents of the library, a pitch's own short way (no plan, no tasks, no
Review, no gate, no flag), three read-only calls' steps and the faces of a pitch. Not: a web search (v1 judges against the
project, not the market, and says so), a pitch built in place, an Ideation party with code agents or fewer than four
views, a decision that moves or starts anything by itself.

Three parts, in this order; A first, B and C branch from it and share no file.

| part | builds | files (and their tests) |
|---|---|---|
| **A. Host** | §1–§7, §9 | `realm/library.py` (the agents, `PRESETS`, `STAGES`), `realm/goal_team.py` (Ideation's seats), `realm/ideas.py` (`STATES`), new `realm/pitches.py` (the answers, the kill reasons, the page's Decision section, the passed pitches), new `core/idea_judge.py` (the keeper's mixin: the views, the case against, the decision), `core/idea_keeper.py` (`ask` speaks as a given role; the mixin), `core/idea_night.py` (a pitch put off to the night), `realm/idea_target.py` (three steps), `realm/goal_types.py` (Ideation offers no type), `realm/event_log.py`, `realm/lexicon.py`, `gui/ideas.py`, `gui/ideas_board.py` and their neighbours in `gui/ideas_*.py` (the commands, the map's pitch rows, Needs you), `gui/board_host.py` (only if the phone's allowed list needs it); new `tests/test_ideation.py` |
| **B. Desktop** | §8 on the desktop | `js/shell/goalview.js` or a new `js/shell/pitchview.js` (a pitch's screen), `js/shell/goaldialog.js` / `goalwizard.js` (New goal in Ideation: one box), `js/arena/*` (Ideation's line on the field: the builder's choice of files), `js/shell/shell.css`, `js/arena/arena.css`; new `tests/test_ideation_desktop_browser.py` |
| **C. Phone** | §8 on the phone | `pwa/shell-goal.js` or a new `pwa/shell-pitch.js`, `pwa/shell-goal-new.js`, `pwa/shell-party.js`, `pwa/shell-goals-words.js`, `pwa/board-app.js` (only to load a new file), `pwa/app.css`, `pwa/sw.js` (`CACHE` one up) with `tests/test_pwa.py`'s pin; new `tests/test_pwa_ideation_browser.py` |

## 0. The words
`TERMS` gains (realm/lexicon.py), the code's names in brackets:
- **pitch** · *pitches* (`pitch`): a goal of an Ideation party: a small idea to judge, not to build.
- **view** · *views* (`pitch_view`): one side's read of a pitch: what speaks for it, what against, one question.
- **the case against** (`pitch_case`): the skeptic's strongest case not to do it.
- **decision** · *decisions* (`pitch_decision`): the Investor's answer: **Invest**, **Reshape** or **Pass**, with why.
  Not *verdict*: that word is a party's old verdict against its metrics (realm/goal_verdict.py).
- **passed** (`pitch_passed`): a pitch the person passed on, kept with its why.

## 1. The agents (`realm/library.py` `LIBRARY`)
Six, after the marketing ones, under a heading of their own (*ideation: the Investor and each side's view; a party of
their own*). Each `takes` a pitch kind only, so the Taskmaster never plans work for them, and each carries `pitch=True` (a
new field of `Agent`, default False).

| id | name | craft | tier | band | takes | line |
|---|---|---|---|---|---|---|
| `investor` | Investor | product | elder | lead | `pitch` | Decides whether to invest in an idea: where to take it, or why not |
| `product-view` | Product view | product | warrior | build | `pitch-product` | Who it is for, what it moves, what it leaves out |
| `market-view` | Market view | marketing | warrior | build | `pitch-market` | Who would want it, how they would hear of it, what it is like |
| `tech-view` | Engineering view | engineering | warrior | build | `pitch-tech` | What it touches, how big it is, what it risks |
| `design-view` | Design view | design | warrior | build | `pitch-design` | Where it lives on screen, the flow, what it costs people |
| `skeptic` | Skeptic | product | warrior | check | `pitch-against` | Makes the strongest case not to do it |

- **The Investor's head:** its craft's race, the undead's lich (`roles.RACES["product"]`), as the Product manager's. A
  mummy or a ghost of its own is drawn in orkUI first (CLAUDE.md: a head is orkUI's), then copied; not in this spec.
- **The Investor's instruction** (≤ `roles.INSTRUCTION_CHARS`, the builder words it): *You decide whether to invest the
  team's time in an idea. Invest only when someone it is for is named, it moves a metric the project has, and its cost is
  in proportion; else reshape it (say what would make it worth it) or pass (say why, plainly). Weigh the case against as
  seriously as the views for it. Name the cheapest way to know before building.*
- The views' and the skeptic's instructions hold: answer from the pitch and the project only; invent no number, no user,
  no competitor; say *I cannot tell from here* rather than guess. The skeptic's: *argue against it as well as it can be
  argued, whatever you think of it; never the same case twice in other words.*
- `STAGES["investor"] = Stages("Pitch", "Views", "Decision", 4, 1)`.
- **Ideation is always its four views and the skeptic** (the owner's call): `goal_team.seats` refuses a party led by the
  Investor whose team is not exactly the four views and the skeptic (*Ideation reads every pitch from all four sides: its
  views and the skeptic stay*), and a pitch agent in a party of another leader (*The views judge pitches: they are in
  Ideation only*). `library.listed()` gains `pitch`; the faces' agent pickers do not offer the pitch agents to other
  parties, and offer no seat change in Ideation.
- **The preset** (`PRESETS`, after Website): `("ideation", "Ideation", "Small ideas: invest, reshape or pass, and why",
  "product", "investor", ("product-view", "market-view", "tech-view", "design-view"), ("skeptic",))`.
- `goal_types.offered` answers no type for Ideation: a pitch has none. Its decision names the type the goal will have in
  the party it goes to (§3).

## 2. A pitch's way
`raw` → `judging` → `judged`; then the person's: **Send** (`sent`), **Pass** (`passed`), **Change and judge again** (back to
`judging`), or **Drop** (as today: the page goes). Besides: `failed` (a call failed: its line, **Try again**), held by the
limits as any goal's draft (`held_until`). `ideas.STATES` gains `judging`, `judged`, `sent`, `passed`.

- **Added** as a goal is today (`ideas.add` with the party), its words its pitch (one box, ≤ 2 000 characters, its lens
  as today: a screen, a pain, code). Its queue is today's: **Now**, **Tonight**, **Hold** (spec 35 §3); a pitch put off to
  the night is judged by the night (`core/idea_night.py`) before any draft, within the night's count.
- **No draft, no questions, no plan:** a pitch never reaches `reading`, `asks` or `planning`. `ideas.start`, the plan's
  commands and the gate refuse it in words (*A pitch is judged, not built: send it to a party first*).
- **Its page** (`pages/ideas/<slug>.md`) keeps the pitch as its Description and gains one section, **Decision**, written
  by code from §3's answer (the answer, why, where, the first step, the cheapest test, the kill reasons). The views and
  the case against are kept beside it, in `<state_dir>/ideas/<slug>/judge.json` (the faces read them; a hand edit of the
  page is read as it is).

## 3. The calls (`core/idea_judge.py`, a mixin of `IdeaKeeper`)
`keeper.judge(slug)`: in the background, as the goal's run (`ideas.judge`), three steps, each a one-shot read-only call
as the draft is, each measured. `ask` gains `as_role=` (a role's slug): the call speaks as that role (its voice and
instruction first), not as the goal's leader.

1. **The views**, one call per view (`pitch_view`), at most two at once, **each alone**: no view sees another. Each gets
   (cut by `CONTEXT`): the pitch and its lens; the project's parties (name, Description's first lines, metrics); the
   goals done and in work (titles, ≤ 40); the pitches passed (title and their why, ≤ 20, newest first). The Engineering
   view may read the repository with the draft's read-only tools; the others get no tools. Answer:
   `{"for": ["…"], "against": ["…"], "question": "…", "size": "S|M|L|"}`, ≤ 3 lines each (≤ 200 characters), `size` the
   Engineering view's only (the others' dropped).
2. **The case against** (`pitch_case`), as the skeptic: the pitch and the four views. Answer: `{"case": "…" (≤ 600),
   "kills": ["…"]}`.
3. **The decision** (`pitch_decide`), as the Investor: the pitch, the views, the case against, the project's parties with
   the goal types each is offered (`goal_types.offered`) and the presets of the library not in the project. Answer:

```json
{"answer": "invest",                             // invest · reshape · pass
 "why": ["…"],                                   // ≤ 3, ≤ 200 each
 "where": {"party": "ship", "type": "feature"},  // invest: a party of the project or a preset's id; its goal type or ""
 "first": "…",                                   // invest, reshape: the goal as the party would be given it (≤ 300)
 "test": "…",                                    // the cheapest way to know before building (≤ 300), or ""
 "kills": ["no_who"],                            // §4
 "like": "dark-mode"}                            // a goal or a passed pitch it repeats, or ""
```

- Code keeps only these keys and cuts them; a `where.party` that is neither a party of the project nor a preset, or a
  `type` that party is not offered, is emptied (the invest stands, the person picks); a `like` that names no goal is
  emptied. No JSON: `failed`, *the answer was not the JSON it was asked for*.
- **Always four:** a view that fails is retried once; a second failure fails the pitch (*Market view did not answer:
  try again*). The Investor never decides on fewer than the four views and the case against.

| step | thrift | balance | quality | cap $ (balance) | context |
|---|---|---|---|---|---|
| `pitch_view` | laborer | warrior · low | warrior · medium | 0.08 | 6 000 |
| `pitch_case` | laborer | warrior · low | warrior · medium | 0.06 | 6 000 |
| `pitch_decide` | warrior · medium | elder · low | elder · medium | 0.20 | 8 000 |

A pitch costs about $0.55 at balance at most (the caps); `party_price` (spec 43 §3) says it before the first pitch. A role
with its own model (Agents) keeps it, as today.

## 4. The kill reasons and the answers (`realm/pitches.py`, pure)
The kill reasons are code's, a closed list, each with its words:

| id | words |
|---|---|
| `no_who` | No one it is for is named |
| `no_move` | It moves none of the parties' metrics |
| `repeat` | It repeats a goal done, in work or passed |
| `costly` | It costs more than it is likely to bring |
| `off` | It is outside what the project is for |

- `kills` from the skeptic and the Investor are joined; an id not in the list is dropped.
- **An invest with a kill is a reshape:** code turns `invest` into `reshape` when `kills` holds `no_who`, `no_move` or
  `repeat` (the reason's own line says why). The Investor may still name where.
- `repeat` with `like` names the goal or passed pitch; without `like` it is dropped.

## 5. What the person does with it (`gui/ideas.py`)
- **Send to <party>** (`ideas.pitch_send {slug, party, type?}`; an invest's default the decision's `where`, any party of
  the project may be picked; a preset not in the project is refused with *Make the <name> party first*, and the faces
  open New party with that preset): a new goal in that party, added as `ideas.add` adds one (its type, its queue **Now**),
  its words the decision's `first` (else the pitch), its lens the pitch's, and a **From Ideation** line in its Description
  naming the pitch. The target party's draft gets the pitch's views and decision in its prompt (≤ 2 000 characters), so
  it does not ask again what the views said. The pitch is `sent`, its state names the goal. Nothing starts but the new
  goal's draft, as any new goal's.
- **Change and judge again** (`ideas.pitch_again {slug, text}`): the pitch's words changed by the person, judged anew;
  the old decision kept in `judge.json`'s `before` (the last two).
- **Pass** (`ideas.pitch_pass {slug, why?}`): `passed`, the person's line (optional, ≤ 300) beside the decision's why. A
  passed pitch is kept: read by every later pitch's views and Investor (§3), shown folded under the party's goals
  (*Passed (n)*), and can be **Judged again** (back to `judging`). At most 200 passed pitches are kept; the oldest is
  dropped as `ideas.drop` drops a goal.
- **Drop**, as today.
- Needs you gains `pitch` (a pitch `judged`, `blocks: false`, priority `low`), sorted after the goals' asks; the
  snapshot's count leaves it out (it waits for the person, it holds nothing).

## 6. Measured
Events (`EVENTS` gains them, no pitch's words): `pitch_judged` (goal, answer, kills, tokens, cost, seconds) ·
`pitch_sent` (goal, to party, type, as decided: bool) · `pitch_passed` (goal, as decided: bool, has_reason) ·
`pitch_again` (goal). From them the party's work (spec 43 §2) says, for Ideation: pitches judged, sent, passed, the share
where the person did what the Investor said, and of the goals sent, how many raised their flag. **That last number is how
the person learns whether the Investor is worth its cost.**

## 7. The night and the limits
A pitch is the person's own (they added it): only the `NEARLY` floor, never the reserve, as a draft. Put off to the night,
it is judged first among the night's work and counted in its `drafted`. Stop all stops a judging pitch: `failed`,
*stopped*, **Try again**.

## 8. Faces (B, C)
- **New goal** in Ideation: one box (*What is the pitch?*), the lens a tap away (today's), **Judge now**, **Tonight**,
  **Hold**. No type, no asks.
- **Ideation's line on the field / map:** its pitches by state: judging (the views' heads, lit one by one as each
  answers), judged (the answer's word: *Invest* · *Reshape* · *Pass*), sent (naming the goal), and *Passed (n)* folded. Its
  three stages are *Pitch*, *Views*, *Decision*.
- **A pitch's screen:** the pitch; the four views side by side (desktop) or one under another (phone), each with its
  head, *for*, *against*, its question; the case against; the decision: its answer large, why, the kill reasons in their
  words, where and as what type, the first step, the cheapest test, the goal it repeats. Buttons, saying what happens:
  **Send to <party>** (a party select beside it), **Change and judge again**, **Pass**, **Drop**.
- The pixel face for headings and buttons only; the views' and the Investor's words in the text face (CLAUDE.md).
- Phone: sheets, no horizontal scroll at 390 px.

## 9. Tests
- **A:** the six agents and the preset in `library` (`presets()` holds Ideation after Website; `stages()` the Investor's
  three words); `goal_team.seats` refuses Ideation without a view, with a code agent, and a view elsewhere;
  `goal_types.offered` answers none; a pitch refused by `ideas.start` and the plan's commands; the calls (a stub
  harness): four views each alone (no view's prompt holds another's answer), the Engineering view alone with tools, the
  passed pitches in each prompt, the skeptic gets the views, the Investor the parties' types; a view failing twice fails
  the pitch; the answer cut and cleaned (unknown party and type emptied, an unknown `like` emptied, unknown kills
  dropped); an invest with `no_who` made a reshape; `pitch_send` adds the goal in the party with its type and the From
  Ideation line, the target draft's prompt holds the views; `pitch_pass` keeps it, a later pitch's prompt holds its why;
  201 passed drops the oldest; the night judges a pitch put off; Stop all; the events hold no pitch's words; Needs you's
  `pitch` row out of the count.
- **B** (browser, 1 440 × 900, stub host): New party → Ideation; a pitch added, judging with the views lit one by one,
  its screen with four views, the case against and an invest; Send to the named party; a reshape changed and judged
  again; Pass folds it under *Passed (1)*.
- **C** (390 × 844): the same as sheets; no horizontal scroll.
- Each part: the critical tests (CLAUDE.md "Alpha"), its files' tests, `tests/test_gui_wording.py`,
  `tests/test_design_system.py`; C also `tests/test_pwa.py`.

## 10. Not in this spec
A web search for the Market view (the market as it is: a later spec, with its cost); a pitch from outside (a mail, a Slack
message: Operations' sources, spec 38 §12); pitches ranked against each other; an Investor that sends by itself; a
prototype built to test a pitch (its `test` is words; building it is a goal of a party); the Investor's own head (a mummy
or a ghost, drawn in orkUI first).

## 11. As built (notes, no change of the contract)

**A (host), 23 October.** Built in `realm/library.py` (`Agent.pitch`; the six agents after the marketing ones, `PITCH_RULE` the views' and
the skeptic's shared sentence; `INVESTOR`, `SKEPTIC`, `VIEWS`; the `ideation` preset after Website; `STAGES["investor"]`; `listed()`'s
`pitch`), `realm/goal_team.py` (`seats`: `IDEATION_WHOLE`, `PITCH_ONLY`), `realm/ideas.py` (`STATES` + `judging judged sent passed`;
`STATE_DEFAULT["from_pitch"]`), new `realm/pitches.py` (pure: the kill reasons, the answers cut and cleaned, `offers`, `judge.json`, the
Decision section, the passed pitches, what the faces read, `sent_lines`, `tally`, `stage_of`, `need_of`), new `core/idea_judge.py`
(`JudgeMixin`: `judge`, `judge_one`, `role_as`, `pick_as`, `speak_as`, the three prompts), `core/idea_keeper.py` (`ask(..., as_role=)`,
the mixin, `plan` refuses a pitch, `PITCH_NOT_BUILT`, the ledger's line names the role spoken as), `core/idea_draft.py` (`draft` and
`draft_one` judge a pitch instead; `answer` refuses one; the draft prompt carries `pitches.sent_lines`), `core/idea_night.py` (a pitch
first in the night's queue), `realm/idea_target.py` (`pitch_view`, `pitch_case`, `pitch_decide` in `STEPS`, `MATRIX`, `CONTEXT`, `READS`,
`CAPS`; `PITCH_STEPS`), `realm/idea_spend.py` (the three steps count in the *spec* stage), `realm/goal_types.py` (`offered` answers none for
a party the Investor leads), `realm/party_price.py` (`pitch_price`), `realm/party_work.py` (`pitches` for Ideation),
`realm/board_map.py` and `realm/map_party.py` (the `pitch` row and the node's `pitch`), `realm/event_log.py` (four events),
`realm/lexicon.py` (five words), new `gui/ideas_pitch.py` (`PitchMixin`: the four commands, `refuse_pitch`, `pitch_of`), `gui/ideas.py`
(the mixin and the table, `add`'s `hold` and `pitch`, `_state`, `page`'s `pitch`, the snapshot's count), `gui/ideas_board.py`
(`sort_needs`), `gui/ideas_party.py` (`party_price` of Ideation), `gui/ideas_types.py` (a type for a pitch refused). `gui/board_host.py`
is untouched: `BoardPhone.allowed` lets every `ideas.*` the host has through. Tests: new `tests/test_ideation.py` (22); the counts and
orders of the library, the presets and the board's commands brought up to date in `test_goal_team.py`, `test_library.py`,
`test_gui_roles.py`, `test_gui_ideas.py`, and the presets' order in `test_mixed_parties_desktop_browser.py` and
`test_pwa_mixed_parties_browser.py`.

**The shapes** (for B and C).
- **The library.** `ideas.roles`' `presets` holds `{"id": "ideation", "name": "Ideation", "line": "Small pitches: invest, reshape or pass, and
  why", "craft": "product", "race": "lich", "mixed": true, "lead": "investor", "build": ["product-view", "market-view", "tech-view",
  "design-view"], "check": ["skeptic"]}` after `website`; `stages.investor` is `{"lead": "Pitch", "build": "Views", "check": "Decision",
  "seats": {"lead": 1, "build": 4, "check": 1}}`; each `library` row has `pitch` (true for the six). A party is made as any with the
  preset: `ideas.goal_save {about, craft: "product", leader: "investor", team: [the four views, "skeptic"], preset: "ideation"}`. Any other
  team is refused with *Ideation reads every pitch from all four sides: its views and the skeptic stay*; a pitch agent in another party
  with *The views judge pitches: they are in Ideation only*. `ideas.party_price {leader: "investor", team}` answers `{"low": 0.29, "high":
  0.58, "learned": false, "ideas": 0, "checks": [], "pitch": true, "hints": [], "types": []}` at balance (learned: the mean of the
  project's judged pitches, ±50 %).
- **A pitch is added** with `ideas.add {text, track: <the Ideation party>, night?, hold?, lens?, photos?}` (its text cut to 2 000; a
  `type` is refused, *A pitch has no goal type: its decision names the one it will have*). `hold: true` is new for any goal: `queue: "hold"`,
  nothing drafts or judges it till the person does. It answers as today (`{slug, queue, element, type: "", joined: null}`).
- **The commands.** `ideas.judge {slug}` → `{ok: true}` (Judge now from Hold or Tonight, Try again after `failed`; refused in a spent
  window). `ideas.pitch_send {slug, party, type?}` → `{"slug": <the new goal>, "party", "type", "queue": "now"}` (`type` left out: the
  decision's when it named this party, else none; `"type": ""` sends none; a party of the library not in the project is refused with
  *Make the <name> party first*, an Ideation party or one that is gone with *That party is gone*). `ideas.pitch_again {slug, text?}` →
  `{ok: true}` (from `judged`, `failed` or `passed`; without `text` its words stay: *Judged again*). `ideas.pitch_pass {slug, why?}` →
  `{"ok": true, "dropped": [slugs of the oldest passed beyond 200]}`. While it is judging each answer is *The keeper is judging this pitch:
  a moment*; a sent one *This pitch is sent: its goal is in its party now*; a passed one asked to be sent or passed *This pitch is passed:
  judge it again first*. `ideas.plan`, `start`, `start_now`, `stop`, `revise`, `revise_answer`, `answer`, `say`, `todo`, `pick`,
  `check_skip` refuse a pitch with *A pitch is judged, not built: send it to a party first*.
- **States** (`ideas.board`'s `ideas[].state`, the snapshot's `idea_states`, the node's `state`): `raw` (with `queue` `now` · `night` ·
  `hold` and `held_until` as any goal) → `judging` → `judged` → `sent` | `passed`; `failed` with `state_error` (*stopped*, *Market view
  did not answer: try again*, *the answer was not the JSON it was asked for*). A `judging` whose run the host lost reads `failed`,
  *stopped*.
- **`pitch`** on `ideas.page` and on each Map node of an Ideation party (`null` for any other goal):
  `{"state": "judged", "views": [{"slug": "tech-view", "name": "Engineering view", "head": {"craft": "engineering", "race": "peon",
  "tier": "warrior"}, "answered": true, "for": ["…"], "against": ["…"], "question": "…", "size": "M"}, …four, in VIEWS' order],
  "skeptic": {"slug", "name", "head"}, "investor": {"slug", "name", "head"}, "case": {"case": "…", "kills": [{"id": "costly", "words":
  "It costs more than it is likely to bring"}]} | null, "decision": {"answer": "invest", "word": "Invest", "why": ["…"], "where":
  {"party": "ship", "name": "Ship", "preset": false, "type": "bug", "type_name": "Fix a bug"}, "first": "…", "test": "…", "kills": [{"id",
  "words"}], "like": {"slug", "title"} | null, "reshaped": false} | null, "sent": {"party", "type", "goal", "as_decided", "at", "name",
  "title"} | null, "passed": {"why", "at", "as_decided"} | null, "before": [decision + "at", newest first, at most two]}`. While judging,
  `answered` turns true view by view (each is kept and published as it answers), then `case`, then `decision`. `where.party` is ""
  when the Investor named none or none it may; `preset: true` names a party of the library the project lacks. `reshaped`: code made the
  invest a reshape (its kill reasons say why). A view's `size` is the Engineering view's only.
- **The Map.** An Ideation goal has `ideation: true` and `passed` (how many of its pitches are passed); others `false`, `0`. Its
  `types` is `[]`; its `stages` *Pitch*, *Views* (4), *Decision* (1). A pitch's node: `stage` `planning` (raw, failed), `implementation`
  (judging, views answering), `checking` (from the case on, and judged, sent, passed); a passed one is `folded: true`;
  `needs_you: "pitch"` when judged (`waits.kind: "you"`). The leader's party state is *needs* (`why: "pitch"`) while a pitch waits.
- **Needs you** (`ideas.board`'s `needs_you`, the phone's too): `{"idea", "goal", "title", "priority": "low", "blocks": false, "at",
  "kind": "pitch", "text": "Judged: Invest", "answer": "invest"}`, after the goals' own rows and before the proposals; the snapshot's
  `needs_you` count leaves it out.
- **The party's work.** `ideas.party {goal}` of an Ideation party adds `"pitches": {"judged", "sent", "passed", "as_decided": 0.5 | null,
  "flags"}` (`as_decided`: of the pitches sent or passed, the share where the person did what the Investor said; `flags`: the goals sent
  that raised their flag).
- **Events** (no pitch's words): `pitch_judged {goal, answer, kills, tokens, cost, seconds}`, `pitch_sent {goal, to, type, as_decided,
  device}`, `pitch_passed {goal, as_decided, has_reason, device}`, `pitch_again {goal, changed, device}`. `idea_added` is logged for a
  pitch as for any goal (its characters, never its text).
- **Files.** `<state_dir>/ideas/<slug>/judge.json`: `{views: {id: {for, against, question, size}}, case, decision, before, judged_at,
  passed, sent}`. The page keeps the pitch in its **Gist** (the section every goal's words are in; the faces call it the pitch) and
  gains **Decision**, e.g. `**Invest: the Ship party, as Fix a bug**`, the why as a list, *First step:*, *Cheapest test:*, *Kill
  reasons:*, *It repeats:*.

**What the spec left open, and what was chosen.**
1. *A role's own model.* A library agent is installed with its tier as its model, so "a role with its own model keeps it" is read as
   a model that is not its library tier (or a model by name): that one wins, else the Target's tier for the step (so thrift's *laborer*
   holds for the views). The effort is always the Target's.
2. *Tools.* The Engineering view alone has the draft's read-only tools (`READS["pitch_view"] = 4`); the case and the decision read no
   file, like the other views.
3. *Tried again.* The case against is tried once more as a view is; a second failure fails the pitch (*Skeptic did not answer: try
   again*). The decision is not tried again (a call whose answer is no JSON, or not one of the three answers, fails the pitch).
4. *At most two at once* is a thread pool of two; the run's own cancel is carried to its threads, so Stop all and the person's stop
   reach every view. A stop fails the pitch with *stopped* and puts it on Hold, as a stopped draft is.
5. *Where it may go* (`pitches.offers`): the project's parties but General and any Ideation party, with the types `goal_types.offered`
   gives each; then each party of the library (`library.presets()`, the crafts' and *Taskmaster alone* too, Ideation never) whose leader
   and team no party of the project has, with the types such a party would be offered. A party's slug wins over a preset's id.
6. *What every call reads.* The parties are listed by slug, title, the Description's first lines (≤ 300) and the metrics' names; the
   goals done and in work are the other parties' goals (any state but `proposed`), ≤ 40, `done` or `in work`; the passed pitches by slug,
   title, the decision's why and the person's line. The Investor reads the goals and the passed pitches too (for `like`), after the
   views, the case and where it may go.
7. *The night* judges a pitch put off before any draft, held only by the spent window (`hold`, the `NEARLY` floor), never by the reserve
   or the week's pace; it counts in `drafted`. The keeper's clock and Process now judge a pitch where they would draft a goal
   (`DraftMixin.draft` and `draft_one` hand it to `judge`/`judge_one`).
8. *Sent.* The new goal's words are the decision's first step (else the pitch) and a line `From Ideation: <pitch title> (<slug>)`; its
   queue is Now whatever its party's priority; its lens is the pitch's; its state keeps `from_pitch`, and its draft's prompt gets
   `pitches.sent_lines` (the views and the decision, ≤ 2 000). `as_decided` is the Investor's invest to the very party it was sent to.
   The pitch is claimed `sent` under the lock before the goal is added (a second press is refused), and back to `judged` if the add fails.
9. *Passed.* Kept by its `passed.at`; the 201st oldest is dropped with `ideas.drop` (page and state), never one being judged. A passed
   pitch's `as_decided` is the Investor's pass.
10. *Change and judge again* rewrites the Gist, and the title and short name from its first line; refused in a spent window, its words go
    back. The decision there was goes to `before` when the next judging starts (so a Try again after a failure keeps it too).
11. *Its price* (`party_price.pitch_price`): the six caps under the Target as the high end, half of them the low (about $0.29–$0.58 at
    balance), learned from three judged pitches with priced lines. The three steps' lines count in the ledger's *spec* stage, under the
    role that spoke.
12. *The gate* needs nothing: a pitch has no plan, so it has no task in dev and is never among the gate's goals.
13. *The words the page shows* say *pitch*, never *idea* (CLAUDE.md; `tests/test_arena_decks_desktop_browser.py` reads the New party
    dialog for the word): the preset's line is *Small pitches: invest, reshape or pass, and why* and the Investor's line *Decides
    whether to invest in a pitch: where to take it, or why not* (§1's table and preset said *idea*). The instructions, which go to the
    model, keep §1's words.
14. *Not done here.* The faces' pickers that must not offer the pitch agents to other parties, nor a seat change in Ideation, are B's and
    C's (`library[].pitch` says which). `gui/phone_push.py` `KIND_WORDS` (kept equal to `js/board/today.js`) does not name `pitch`, so a
    push never leads with a pitch; the snapshot's count leaves it out anyway. Saving an Ideation party is read by the keeper as any party
    is (the Investor's voice, the `goal` step). `realm/ideas.py` was over 600 lines before and grows by two; not split here.

**B (desktop).** Built in new `js/arena/pitchwords.js` (pure: `isIdeation`, a pitch's line by state `pitchWords`, `pitchMark`, `pitchLists`,
`pitchPlanning`, `judgePower`, `whereWords`, `sendTargets`), new `js/arena/pitches.js` (the left column's `PitchGoals`, the field's `PitchField`), new
`js/shell/pitchview.js` (a pitch's screen), `js/arena/arena.js` and `goals.js` (an Ideation party draws them in place of the tasks' columns, the goals'
lists and *Process now*), `js/shell/ideadialog.js` (`PitchGoal`), `js/shell/party.js`, `goalwizard.js`, `goaldialog.js` (the pickers), `js/arena/stops.js`
and `arenawords.js` (the `pitch` stop), `arena.css`, `shell.css`; new `tests/test_ideation_desktop_browser.py`, 11 tests. Outside §0's row, each a line or
two: `js/shell/preview.js` (a page with `pitch` opens `PitchView`), `js/arena/arenastate.js` (`sentOpen`), `partyline.js` and `goalwords.js` (*judging*
for *reading*, *a pitch* for *a goal* in the price), `js/board/maplayout.js` (`NEEDS_WORDS.pitch`, the leader's peek). What the spec left open:
- **The line on the field is the party row's columns.** Under the four views and the Skeptic, a framed row per pitch: its title and line, then under each
  view its head (dim until it answers, then lit, with `useLit`'s one flash as it comes), under the Skeptic what is next (*the case against*,
  *deciding*) and then the answer's word in the heading face. Sections *Judging*, *Judged*, *New*, *Sent*; the passed are only in the left column.
  A press opens the pitch's screen; a member's press (solo) dims the other columns' cells, nothing more.
- **The left column** says *Pitches (n)* (judging and judged), sections *Judging* (with the failed: ✗ and their error) and *Judged* (the alert sign,
  *judged: Invest*), then folds *New (n)*, *Sent (n)* and *Passed (n)* (`rawOpen`, `sentOpen`, `flagsOpen`, so leaving the party closes them). A row
  opens the screen: a pitch has no task to pick into the filter. **Judge now · n new pitches** sends `ideas.judge` for the first new one.
- **New goal** in Ideation is `BlankGoal`'s own text, party and lens drawn as `PitchGoal` (picking Ideation in its party select switches, and back):
  *What is the pitch?* (the template never says *idea*, tests/test_gui_wording.py), Hold · Tonight · Judge now; Judge now sends the party's priority
  but never `low` (a Low would put it to the night); closed with words in it, Tonight, as any goal. No priority field.
- **Send to <party>.** The select lists the project's parties but General and Ideation's, the decision's party first; a preset the decision names that
  the project lacks is listed last, *(make it first)*, and its Send opens New party with that preset (`openDialog("goal", {preset})`, `GoalWizard`'s
  new `preset`, its name filled in) without calling the host. `type` is never sent: the host's default (the decision's type when sent where it said).
- **The pickers.** `party.js` `pitchParty(leader)`: in Ideation `PartyBands` draws the seats and no list (the bands say what each does for a pitch, and
  *Ideation reads every pitch from all four sides: its views and the Skeptic stay*); elsewhere the lists leave out every `pitch` agent, the Investor
  too. New party leaves Ideation by another tile; Edit the party of Ideation has no *Change the party*. `PriceLine` says *a pitch*; `CanTake` and the
  checks block are not drawn (`types: []`, the Skeptic is no checker).
- **Needs you's `pitch`** is a stop of urgency 2 (*Pitch judged*, its text the host's *Judged: Invest*, no gem); its press and *Open the pitch* open
  the screen. It rings nothing on the field (`aboutOf` is unchanged).
- **Not done:** the drawer's tab still says *Goal* before a pitch's title (the tab strip reads no page); the views' heads are the library's, the
  Investor a lich (§1).

**C (phone)** (`orkcraft-app-v73`). Built to §8 on the phone as sheets, in new `pwa/shell-pitch.js` (`makePitchField`: Ideation's field; `makePitch`: a pitch's sheet; `isIdeation`, `pitchNode`),
`pwa/shell-goals-words.js` (`pitchLine`, `pitchStage`, `whereWords`, `pitchCount`, `answeredOf`; `goalsOf`, `barWords` and `doneWords` for Ideation), `pwa/shell-goal-new.js` (`IDEATION_WHOLE`; the
seats' folds offer no pitch agent; Ideation has no Change for its seats or its checks, its price is *a pitch*'s and it draws no *It can take*; `makeNewGoal.open(after, preset)`), `pwa/shell-ideas.js` (New goal in
Ideation), `pwa/shell-party.js` (About this party: no *Add to the party*, no *Its flags*, *about $… a pitch*), `pwa/shell-goal.js` (the party's screen: no Change in Ideation; `open(which, after, preset)`),
`pwa/app.css` (`.pitchfield`, `.pitchsec`, `.pitchrow`, `.pitch-passed`, `.pitch`, `.pitchview`, `.pitch__answer`, `.pitch__acts`, `.newgoal.is-pitch`), `pwa/sw.js` (`CACHE` v72 → v73, `shell-pitch.js` in
`SHELL`, with the pins of `tests/test_pwa.py` and the eight phone browser tests that pin it). Besides §0's row, for want of another place: `pwa/shell-arena.js` (Ideation's field takes the columns' place),
`pwa/shell-stops.js` and `pwa/shell-arena-words.js` (the `pitch` stop: `needsOf`, `URGENCY`), `pwa/board.js` (the pitch's sheet; `core.openPitch`, `core.newParty`; an `idea` opened that is a pitch opens its
sheet) and `pwa/shell-board.js` (`newParty`); `board-app.js` is untouched (`board.js` loads the new module). New `tests/test_pwa_ideation_browser.py`, 11 tests (390 × 844, over
`test_pwa_arena_browser.py`'s scene with an Ideation party beside). No host shape was missing. What the spec left open:
- **The field.** No stage switch and no columns (a pitch has no task): under the goals bar (*Ideation · 8 pitches · 1 passed*) three sections, one per stage, each headed by its band's heads, its word and its count:
  *Pitch* (raw: *queued*, *tonight*, *held: Judge now to have it read*, *waits for limits*; failed with its `state_error`), *Views* (a judging pitch whose views answer: its four small heads, unlit at 0.3, each lit as it
  answers and lit once when it turns, none under reduced motion), *Decision* (by the Map's `stage`: the case against or the Investor under way, then the judged with the answer's word at the row's end and where
  it would go or its first kill reason, then the sent naming their party and goal) and *Passed (n)* folded at its end (`<details>`, closed). The judged first in each. A row opens the pitch's sheet; the Goals
  sheet's filter holds. The Goals sheet lists the pitches but the passed under Planning, the judged first.
- **The sheet** is titled by the pitch (the text face: a person's words): its state and line; *The pitch* (its Gist); *Views · k of 4*, four cards one under another (head, name, *Size M* for the Engineering view,
  *For*, *Against*, *It asks:*; *Reading the pitch…* or *Not read yet.* before it answers); *The case against* (the Skeptic's head and name, the case, *Kill reasons*); *Decision* (the Investor's head and the answer
  in 28 px, why, *Kill reasons*, *Where:*, *First step:*, *Cheapest test:*, *It repeats:*, *Before: Reshape · …*); *Sent* or *Passed* when so. It reads `ideas.page` when opened and when the Board changes, and
  draws the Map's node's `pitch` in between; a box being typed in is not drawn over. Refusals are said in the sheet.
- **Its buttons.** Judged: the party select (the project's parties but General and Ideation, then the decision's party of the library when the project lacks it, *Website (a new party)*; *· as decided* on the
  decision's own) and **Send to <party>** pinned at its foot (`ideas.pitch_send {slug, party}`, no `type`: the host's default); **Change and judge again** (a box with the pitch's words, **Judge again**,
  `ideas.pitch_again {slug, text}`), **Pass** (an optional line, `ideas.pitch_pass {slug, why?}`) and **Drop** (asked once: *Its page goes and nothing keeps its why: Pass keeps it.*, `ideas.drop`) end the sheet.
  Failed: **Try again** (`ideas.judge`), Change and judge again, Drop. Passed: **Judge again** (`ideas.pitch_again {slug}`), Drop. Raw: **Judge now** (`ideas.judge`), Drop. Sent: **Open the goal**. Judging: none.
  A party of the library the project lacks is not sent: *Make the <name> party first* is said, the sheet closes and New party opens with that preset picked; once saved, the pitch's sheet opens again on it.
- **New goal** in Ideation (`ideas.add {text, track, hold?|night?, photos?, lens?}`, no priority, type or asks; the text cut to 2 000): the box is labelled *What is the idea?*, the party's lens and Photo stay,
  and the foot is **Hold** · **Tonight** · **Judge now**. Closing it with words keeps it for tonight, as any goal.
- **Needs you's `pitch`** is a stop of the fan (*Judged*, after the questions with the proposals; its text *Judged: Invest*, the Investor's head), whose one quick move is **Open the pitch**.
