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
- **New goal** in Ideation: one box (*What is the idea?*), the lens a tap away (today's), **Judge now**, **Tonight**,
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
