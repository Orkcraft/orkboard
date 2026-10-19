# Spec 40 — Orkforms: the design system, and `orkforms/office`, a denser, monochrome look with a pixel face for buttons and headings

The owner, 19 October (decisions §53). The audit of Orkboard's look (below) found the same product drawn two ways: the
desktop in a grey Office, the phone in a warm brown one; text at the browser's default 16 px beside buttons at 13 px;
a type scale in `tokens.json` that nothing reads. The owner wants the elements smaller, the look more minimal and
monochrome, and a reference to game interfaces through pixel type. This spec gives that look its own design system,
**Orkforms**, whose first member is **`orkforms/office`**: the default look of Office mode. A second member,
`orkforms/game`, follows later and is not designed here. **Builds:** Claude (A0 and A1 on the warrior tier; B and C
on the warrior tier) · **Review:** full · P1 · **Not before spec 39 B and C are merged** (they own `js/shell/*`, `js/board/*`,
`pwa/*`; this spec changes the same stylesheets).

**What it is, and is not:** a set of tokens and components, with the faces' stylesheets moved onto them. It changes
how things are drawn and sized, never what they say or cost: no label, no command, no data changes. The one new behaviour is
the letters on menu items (§8a.4). Camp's themes
(`camp`, `camp-ice`, `camp-void`) and Orkline's Office stay as they are; Orkline moves to Orkforms by its own spec.

Three parts, one branch each, in this order; **this file is the contract** (names, values, files); the rest is the
builder's choice inside its files. Wording: CLAUDE.md (labels say plainly what happens; Orks by their orkish names).
**Change nothing outside these files.**

| part | branch | builds | files (and their tests) |
|---|---|---|---|
| **A0. The system, in its own repository** | `spec/40-orkforms` in **`orkworks/orkforms`** (new, §1a) | §2–§6, §8a, §9 (A0) | in the new repository: `office/` (`ascii/*.txt` (five orks), `tokens.json`, generated `tokens.css`, `components.css`, `fonts/` with the OFL texts, `preview.html` the gallery, `README.md`), `tools/build_tokens.py` (the generator, standard library only), `tests/test_orkforms.py`, `NOTICE`, `CHANGELOG.md`, tag `v0.1.0` |
| **A1. Orkboard takes it** | `spec/40-submodule` | §1a, §6, §9 (A1) | `.gitmodules` and the submodule `design-system/orkforms` (pinned at `v0.1.0`), `pyproject.toml` (`package-data`: the wheel carries the files), `orkboard/design/tokens.py` (reads the form's tokens; it generates only Camp's), `orkboard/design/ui.py` (`RULES`), new `tests/test_orkforms_pin.py` |
| **B. Desktop** | `spec/40-desktop` | §7, §8a | `gui/static/index.html`, `gui/static/js/shell/shell.css`, `gui/static/js/board/board.css`, the inline sizes and colours in `js/shell/*`, `js/board/*`, `js/icons.js`; `gui/static/office.css` leaves Orkboard's page; `tests/test_board_browser.py` and the desktop browser tests |
| **C. Phone** | `spec/40-phone` | §8, §8a | `gui/static/pwa/app.css`, `pwa/index.html`, `pwa/shell-*.js` (the emoji, the header), `pwa/sw.js` (cache version) with `tests/test_pwa.py`'s pinned version, `gui/pwa.py` (what it serves), the phone browser tests |

B and C branch from A once A is pushed; they touch no file of each other's.

## 0. The audit (what is there, measured 19 October, 1 440 × 900 and 390 × 844, dark)
1. **Two Offices.** `office.css` (`data-look="office"`: greys, a gold accent) overrides the `office` theme of
   `design-system/tokens.css` (brown, a green accent) on the desktop; the phone reads the second and carries a light
   variant of its own (51 raw colours in `app.css`). An emoji (🎯) stands on the phone's goal rows, against the rule
   that Office has none.
2. **No base size on the desktop.** 67 % of the characters on the page are 16 px, the browser's default; the buttons and
   fields are 13 px, the labels 11–12 px; headings are `em` of that 16.
3. **The Office scale is unused.** `--type-office-*`, `--control-office`, `--chip-h` are read by nothing in
   `shell.css`, `board.css`, `app.css`; sizes there are `em`, `px` and `rem` mixed (70 inline sizes in the scripts).
4. **The same thing, sized differently:** a button 26 px on the desktop, 44 on the phone; a field 26 and 44; a radius 2
   and 4–6; a card's padding 8×12 and 12.
5. **Contrast:** `--ink-comment` is 3.4–3.8 : 1 on the panel (text needs 4.5). Body and muted text pass (6.5–17 : 1).
6. **Weight:** `index.html` loads 15 stylesheets, most of them Camp's and the town's, which Orkboard's page never draws (part B checks which).
7. The desktop shell today: top bar 43 px, a pane's head 40, a button 26, a Needs-you card 73–93; panes 300 · 800 · 340.

## 1. Orkforms: what the family is
- **Orkforms** is the design system of the product: tokens (colour, type, space, size, motion), components, fonts, rules.
  A **form** is one of its members: `orkforms/office` (this spec), `orkforms/game` (later: the game's look, Orkline
  Camp's successor, which then takes over the Camp themes and sprites).
- All forms **share the names**: the same token names (`--of-*`), the same component classes (`.of-btn`, …), the same
  scale's steps; a form changes their values, adds or removes a layer (the game has sprites; Office has none). So a face
  is written once and the look switches by one attribute.
- **The switch** is `data-forms="office"` on the root. Orkboard's page and phone always carry it. A form's stylesheets
  live in the `orkforms` repository (§1a), at `<form>/` in it, and in Orkboard at `design-system/orkforms/<form>/`, served as
  `/ds/orkforms/<form>/…` (the route `/ds/` exists).
- **Legacy roles keep working.** `tokens.css` of a form also sets the old role names (`--canvas`, `--panel`, `--ink`,
  `--frame`, `--action`, `--danger`, …) under `[data-forms="office"]`, so shared components and old rules that read a role
  take the new colours with no change; new code reads `--of-*`. A role the form does not use is set to the nearest
  one, never left to Camp's.
- Camp's tokens stay in `design-system/tokens.json` and `tokens.css`, untouched, for Orkline.

## 1a. Its own repository (decisions §53.9)
Orkforms is shared by Orkboard and Orkline, so it is a repository of its own, **`orkworks/orkforms`** (the owner's
organisation, renamed from `orkcraft`; Orkboard's own remote keeps working through GitHub's redirect and is not
renamed here). It holds, and only it holds: each form's tokens, stylesheets, fonts and gallery; the generator of
`tokens.css`; the tests of the system itself (§9 A0: contrast, steps, fonts, licences). It imports nothing of Orkboard or
Orkline and needs nothing of theirs to test.
- **A git submodule, pinned.** Orkboard mounts it at `design-system/orkforms`; a consumer names a tag (`v0.1.0`), moves it
  by its own commit, and so a change to the system reaches a face only when its owner takes it. Orkline does the same by
  its own spec; its frozen copy is not touched (decisions §50). A fix the testers need is made in `orkforms` first, tagged,
  and taken by each face the same day.
- **Orkboard keeps** the engine's side: `design/tokens.py` (reads the tokens), `design/ui.py` `RULES` (what a model is told,
  §6), and the faces' stylesheets that use the system. Camp's themes, sprites and logo stay in `design-system/` as they are;
  `orkforms/game` takes them over by its own spec.
- **Build and release:** `pip install` and the wheel need the submodule checked out (`pyproject.toml` `package-data` lists
  `design-system/orkforms/**`); CI and the cloud sessions clone with `--recurse-submodules`. A tag in `orkforms` is made
  only when its tests pass; `CHANGELOG.md` says what a face must do to take it.
- **Order:** A0 (the repository, its first form, `v0.1.0`) → A1 (Orkboard mounts it) → B and C. A0 collides with nothing in
  spec 39 and may start at once.

## 2. Colour (`orkforms/office`, dark only)
Monochrome: a grey scale, the ink as its highlight, and **one ork green for the primary action** (decisions §53.5). Apart
from that **colour means a signal** and nothing else: a question, an error, a success, a warning keep their hue. Light Office is not in this spec (§53.6).

| token | value | role |
|---|---|---|
| `--of-canvas` | `#0b0b0b` | the page, a pane's ground |
| `--of-panel` | `#111111` | a card, a dialog, a menu |
| `--of-raised` | `#1a1a1a` | a hovered row, a pressed control, a tab's ground |
| `--of-frame` | `#333333` | a hairline between things (not a control's edge) |
| `--of-edge` | `#8a8a8a` | a control's edge: a button, a field (≥ 3 : 1 on every ground) |
| `--of-ink` | `#e8e8e8` | text, the selected, the focus, the primary |
| `--of-ink-muted` | `#9a9a9a` | secondary text (≥ 6.5 : 1) |
| `--of-ink-faint` | `#858585` | placeholders, disabled, meta (≥ 4.5 : 1 on the panel; was `#7a7a7a`, 3.8) |
| `--of-on-ink` | `#0b0b0b` | text on an inked ground (the selected, the primary) |
| `--of-action` · `--of-action-hi` · `--of-action-press` | `#6aa84f` · `#7fbf5f` · `#58903f` | the primary button's ground at rest, hover, pressed (the ork green of today's phone; `--of-on-ink` on them 6.9 · 8.9 · 5.1 : 1; on the panel 6.6 · 8.6 · 4.9) |
| `--of-danger` · `--of-alert` · `--of-success` | `#f5806e` · `#f0d050` · `#86c062` | the signals; unchanged from today's Office (7.4 · 12.4 · 8.7 : 1 on the panel) |

- **`--of-warning`** is the alert hue (`#f0d050`, one yellow for a question and a warning, as today's Office has it).
  There is no `info` hue (ink) and no `hot` red (Camp's fire): a failing thing is `--of-danger`.
- **Green is two things, kept apart:** `--of-action` fills the primary button and nothing else (never text, never a
  mark, never a meter); `--of-success` is text, a ✓ and nothing filled (never a button's ground). So a green fill always
  means *press this*, and green text or a tick always means *this went well*.

**Button states** (the contract for `.of-btn`; edge 1 px; contrasts computed against the panel, text on a filled ground
against `--of-on-ink`; every pair ≥ 4.5 : 1, edges ≥ 3 : 1):

| variant | rest | hover | pressed | disabled |
|---|---|---|---|---|
| **default** | edge `--of-edge`, text `--of-ink`, no ground (15.4 : 1) | ground `--of-ink`, text `--of-on-ink` (16.1) | ground `--of-ink-muted`, text `--of-on-ink` (7.0) | dashed edge `--of-ink-faint`, text `--of-ink-faint` (5.1), no hover |
| **primary** (the action, ork green) | ground and edge `--of-action`, text `--of-on-ink` (6.9) | ground `--of-action-hi`, text `--of-on-ink` (8.9) | ground `--of-action-press`, text `--of-on-ink` (5.1) | as default's disabled (a primary that cannot act stops being filled) |
| **danger** (stops or deletes: *Stop all*, *Delete*) | edge and text `--of-danger` (7.4) | ground `--of-danger`, text `--of-on-ink` (7.7) | as hover, plus an inset 2 px `--of-on-ink` ring | as default's |
| **warning** (spends money or risks work: the ones that say so plainly) | edge and text `--of-warning` (12.4) | ground `--of-warning`, text `--of-on-ink` (13.0) | as hover, plus the ring | as default's |
| **quiet** | no edge, underlined pixel text `--of-ink-muted` (6.7) | text `--of-ink` | text `--of-ink-muted` | text `--of-ink-faint`, no underline |

Every variant, in every state, shows **focus** as the inset 2 px `--of-ink` ring (on a filled ground, `--of-on-ink`), over
the state's own look. **Success has no button:** it is a mark (✓) and text in `--of-success` (8.7 : 1) and the filled cells
of a meter that is fine. Outside buttons: a card that **asks** has a 1 px `--of-alert` edge, one that **fails** a
`--of-danger` edge; a limit's meter takes `--of-alert` past 80 % and `--of-danger` past 95 %.

- **Selected is raised, not white** (the owner found an inverted tab too bright): ground `--of-raised`, text `--of-ink`, and a
  **2 px `--of-ink` bar** on the edge that points at the content (the foot of a tab, the left edge of a row or a card):
  `box-shadow: inset 0 -2px 0 var(--of-ink)` (a row: `inset 2px 0 0`). Contrast of text on it 14.2 : 1. The primary button is
  green, so *selected* and *press this* never look alike. A button's hover and pressed (the table above) stay filled: they
  last a moment; a selection stays on screen.
- **Focus** is a 2 px ring drawn **inside** the control (`box-shadow: inset 0 0 0 2px var(--of-ink)`): the corners are
  notched with `clip-path` (§4), which clips an `outline`.
- Links are ink, underlined; there is no hue for them.
- A signal is never the only carrier of its meaning: a mark or a word goes with it (✓ ✗ ! in text, an icon in a row),
  as today (Office's rule: success ✓, warning ⚠, danger ✗).

## 3. Type
Two families, both OFL, both with Cyrillic, shipped in `fonts/` (≈ 59 kB, woff2, latin and cyrillic subsets):

| role | family | files | used for |
|---|---|---|---|
| **pixel** `--of-font-pixel` | Pixelify Sans 500 | as in `design-system/fonts/` (moved by copy) | **buttons and headings only** (§53.2) |
| **text** `--of-font-text` | IBM Plex Mono 400, 600 | `ibm-plex-mono-{latin,cyrillic}-{400,600}-normal.woff2` | **everything else**: what a person reads or wrote, and code, logs, diffs, paths |

One monospaced face for all text (the owner's choice, decisions §53.2): beside the pixel face it reads as one terminal-like
voice, and it has a real 600 for emphasis. It was picked from seven faces on a Russian and English sample (Plex Sans,
Inter, Onest, Golos Text, Commissioner, JetBrains Mono, Plex Mono); the shipped JetBrains Mono subset has no Cyrillic, Plex
Mono has. `--of-font-code` is an alias of `--of-font-text` in this form, so a form with a proportional text face (the
game's, later) changes the value, not the faces' code. The cost is width: Plex Mono is 0.6 em a character (7.2 px at 12 px)
against about 0.5 for a proportional face, so the same pane holds about 15 % fewer characters; the sizes below start from
that (body 12, not 13), and a block of prose is held to **90 characters** (`max-width: 90ch`) so a wide preview does not
make a line too long to read.

The scale (desktop; px are CSS px; the phone's in §8):

| token | font | size/line | use |
|---|---|---|---|
| `--of-type-title` | pixel | 16/20, caps, 0.04em | a dialog's and a window's title |
| `--of-type-heading` | pixel | 14/16, caps, 0.04em | a pane's head, a tab, the product's name |
| `--of-type-label` | pixel | 12/16, caps, 0.06em | a section's label, a role's name (Needs you, Taskmaster) |
| `--of-type-button` | pixel | 13/16 | a button, a chip's action |
| `--of-type-body` | text 400 | 12/18 | prose, a row's title (600 for the strong), code, logs, diffs, paths |
| `--of-type-caption` | text 400 | 11/16 | a row's second line, a hint, meta (a time, a count); never the only place a fact is |

Rules: the pixel face is **never below 12 px and always at whole pixels** (`font-size` an integer, no `em`/`%` of a
fractional size, no `transform: scale`); `font-synthesis: none` (Pixelify has one weight: emphasis is a mark, the 2 px bar,
the caps or the text face's 600, never a faux bold); `font-variant-ligatures: none` on the pixel face (its *fi* is drawn as
an *A*); the text face is monospaced, so its numbers already align. **Numbers and amounts are never set in the pixel face** (its *5* reads as an *S*: *Spend $5* looked like *Spend $S*): a button that carries one wraps it in the text face (`<span class="of-num">$5</span>`), and the words stay pixel. The body is set on the root
(`html { font: var(--of-type-body) }`): nothing is left to the browser's 16. A heading or a button never carries text a
person wrote (a goal's title is body text, not a heading), so a Cyrillic title is never set in Pixelify.

## 4. Shape, space, size
- **Edges** 1 px (`--of-line: 1px`); no radius (`--of-radius: 0`); no shadow but a dialog's hard 1 px frame on a dimmed
  backdrop. **Corners notched** by 2 px on controls, cards, chips and dialogs:
  `--of-notch: polygon(2px 0, calc(100% - 2px) 0, 100% 2px, 100% calc(100% - 2px), calc(100% - 2px) 100%, 2px 100%, 0 calc(100% - 2px), 0 2px)`
  (`clip-path`; the edge is the element's own 1 px border). Text fields and big panes stay square. **Nothing is round:** the pills and circles of today's faces (`border-radius: 999px` on the count badges, the Target
  and limit chips, the dots, the phone's sheets' 12 px top corners) become the same notched square, so a chip's outline is
  as pixel-made as a button's.
- **Space** on a 2 px step: `--of-1` 2 · `--of-2` 4 · `--of-3` 6 · `--of-4` 8 · `--of-5` 12 · `--of-6` 16 · `--of-8` 24.
  Gaps inside a card 2–4, between cards 6, a pane's padding 8, a dialog's 12. Nothing outside the steps.
- **Sizes** (desktop): `--of-control` 24 (a button, a field, a select) · `--of-chip` 20 · `--of-bar` 32 (the top bar, a
  pane's head, a tab) · `--of-row` 28 (a list row) · `--of-icon` 24 (§4 Icons). Every pointer target is at least 24 × 24 (WCAG
  2.2 AA 2.5.8). Panes keep spec 33's widths (300 · fluid · 340; 260 · fluid · 300 under 1 280).
- **Meters** are segmented: cells of 8 × 8 with a 2 px gap, filled cells ink, the rest `--of-frame`; a signal's cells take
  its hue only when the meter is a limit near its end (a limit past 80 %: alert; past 95 %: danger).
- **Motion:** none but a caret's blink (1 s, steps) in a focused field and the existing spin; all off under
  `prefers-reduced-motion`.
- **Icons: Pixelarticons** (MIT; 700 icons on a 24 px grid of whole pixels, so they match the pixel face and the notched
  corners; picked from Pixelarticons, Lucide, Phosphor and Tabler on the needed set). Rules: drawn at **24 px or 48 and
  never scaled to 16 or 12** (a cell would become 0.67 px and the lines uneven); `fill: currentColor`, so an icon takes its
  text's colour (ink, muted, or a signal's); no emoji anywhere in a face (Office's rule, now tested: §9). A button carries
  words, not an icon, except a **chevron** that says it opens something (a select, a menu, *Merge into dev*, *hide*); the
  24 px icons stand in rows, heads, tabs and the empty states, where a row is 28 and a bar 32.
- **Arrows are pixel marks, never typed.** Every arrow and chevron of the chrome (a select's, a menu's, a disclosure's, a
  row's *›*, Back, a step's →) is a pixel mark, never a typed glyph. The **chevrons** (`chevron-down` · `-up` · `-right` ·
  `-left`) are the form's own, in `office/icons/`: **5 × 3 cells of 2 × 2 px** (a down or up chevron is 10 × 6 px, a left or
  right one 6 × 10), one cell thick, `shape-rendering: crispEdges`, `currentColor`, with 4 px beside the word they follow
  (a 24 px Pixelarticons chevron was too large inside a 24 px control). The long **arrows** (`arrow-left` for Back,
  `arrow-right` for a step) are Pixelarticons at 24 px. The glyphs `▾ ▸ › → ⚙ ◎` are not used in a face's templates (the
  gear is `sliders`, the goal `flag`). A native `<select>` is `appearance: none` with the chevron over it, in the field's
  right 8 px. A test scans the faces' templates for those glyphs (§9). A subset is vendored in `office/icons/` as one sprite `icons.svg`
  (only the icons a face uses) with the MIT text; a face names an icon by its Pixelarticons name.
  The first set (`goal` → `flag`, `idea` → `lightbulb`, `task` → `checkbox`, `agent` → `robot`, `review` → `eye`,
  `stop` → `stop`, `settings` → `sliders`, `project` → `folder`, `file` → `file`, `add` → `plus`, `close` → `close`,
  `expand` → `chevron-down`, `warning` → `warning-diamond`, `error` → `square-alert`, `done` → `check`, `map` → `map`,
  `night` → `moon`, `cost` → `coins`, `phone` → `phone`, `edit` → `pencil`, `delete` → `trash`, `run` → `play`,
  `merge` → `git-merge`, `search` → `search`, `time` → `clock`, `link` → `link`, `more` → `more-horizontal`).
- **Key hints** `[K]` in the text face, 11 px, muted; **prefixes** `>` for the product's name and `▪` before a label.

## 5. Components (`components.css`, in this order)
`.of-btn` (variants default · primary · danger · warning · quiet, each in rest · hover · pressed · focus · disabled: the table in §2) ·
`.of-field` (input, select, textarea: 1 px `--of-edge`, `--of-canvas` ground, text face 12, focus inset ring and caret) ·
`.of-tabs` / `.of-tab` (pixel caps, the active one raised with its 2 px bar) · `.of-tabbar` (§8) · `.of-head` (a pane's head, 32 px, a hairline under) ·
`.of-row` / `.of-card` (a hairline edge; selected raised with its 2 px bar; **asks**: a 1 px `--of-alert` edge, **fails**: `--of-danger`)
· `.of-chip` and `.of-count` (20 px, pixel label, 1 px edge) · `.of-label` (a section's label with its `▪`) ·
`.of-meter` · `.of-dialog` (+ `.of-scrim`) · `.of-menu` · `.of-toast` · `.of-kbd` · `.of-split` (a pane divider: a 4 px
dotted line, ink on hover and focus) · `.of-icon`. Each has the states default · hover · pressed · focus · disabled, and
each is in the gallery `preview.html` in all five.
Orkboard's existing classes (`.ok-btn`, `.ok-input`, `.ok-tabs`, `.shell-*`, `.board-*`) are **kept as they are named**:
B and C restyle them through the legacy roles and `--of-*` rather than rename a hundred call sites; a class the new
look replaces whole becomes an alias in `components.css` (`.ok-btn` ↔ `.of-btn`) until no face uses the old name.

## 6. Rules for a UI document (`design/ui.py` `RULES`)
A model that writes a UI document is told, for a form: the roles of §3 (pixel for buttons and headings, text for
everything else, code for code); that colour is a signal only; the control and space steps of §4; that selected is
raised with a 2 px ink bar; that nothing is an emoji. The text is part A's, added next to the Camp rules, chosen by the form.

## 7. The desktop (B)
- `index.html`: `data-forms="office"` on the root (with `data-look="office"` kept: other code reads it); the
  stylesheets `orkforms/office/tokens.css`, `components.css` in place of `tokens.css`, `components.css`, `office.css`;
  every stylesheet no Orkboard page draws leaves the page (checked by a coverage run of the browser tests: a file with no
  matched rule in the Board, Review, Agents, the preview, the dialogs and the settings goes; the list is in the PR).
- `shell.css`, `board.css`: sizes and colours become `--of-*`; the `em` sizes go; the `data-look="camp"` blocks of
  `board.css` stay (Orkline's frozen copy reads them) and are marked as not Orkboard's.
- The result at 1 440 × 900, measured on the prototype: the top bar 43 → 32, a pane's head 40 → 32, a button 26 → 24, a
  Needs-you card 73 → ~68, the left pane's content about **13 % shorter**, all text one scale. (That prototype set the text in a proportional 13/18; in Plex Mono 12/18 the heights are the same and the lines wrap a little more, so B
  re-measures and the PR carries the real before/after.)
- Every inline size and colour in `js/shell/*`, `js/board/*` becomes a class or a token; the goal icon is an SVG
  (`js/icons.js`).

## 8. The phone (C)
The phone is the same form with a thumb's sizes; it follows the system's text size (`html { font: -apple-system-body }`,
sizes in `rem`).
- **Type:** body 16/22 (text; 9.6 px a character, about 38 on the 366 px a line has: the owner found 14 too small), caption 13/18, pixel heading 16/20, pixel button 16/20; a field's text 16
  (iOS zooms in on less); the pixel face still at whole pixels at the default size (it scales with the system's setting
  and the page is checked at 100 % and 130 %).
- **Targets:** a control is **40 px** drawn and **44 px** to hit: its hit area reaches 2 px beyond on each side
  (`position: relative`), and neighbours are at least 4 px apart so the hit areas never overlap. A list row is 44 px. A
  text link's target is its row, 44 px. Nothing smaller than 24 × 24 anywhere (WCAG 2.5.8), and the primary action of a
  screen is a full 44 px.
- **The notch must not cut the hit area.** `clip-path` also clips what a finger can hit, so a control's extension would
  be cut off. On the phone a control is therefore a 44 px-high box (a transparent 2 px frame in its own `padding`/`border`
  zone, the target being the box) with the 40 px look drawn inside it by `background-clip: content-box` and the notch cut
  by corner gradients or a `border-image`, not by `clip-path`; the desktop (controls ≥ 24 px, no extension) keeps `clip-path`.
  The browser test for §9 C asserts the hit area, not the look.
- **The tab bar** (`.of-tabbar`, Board · Agents · Review): three equal cells across the foot, each an icon over its word: the
  24 px icon (`board` → `list-box`, `agents` → `robot`, `review` → `eye`) and the word in the pixel face, 12/16 caps (the
  floor of the pixel face), 56 px high and the safe area under it, the whole cell the target, cells split by a hairline,
  a hairline over the bar. The active cell is raised (`--of-raised` ground, ink icon and word, a 2 px ink bar along its top edge); the others are
  `--of-ink-muted` (6.7 : 1). The icon never stands without its word. A count (Board's *3*) is a notched square, 16 px,
  on the icon's top right corner, in `--of-action`. The desktop's narrow shell (under 1 024 px) uses the same bar.
- **Space:** card padding 8 (was 12), gaps 6–8, the page's side padding 12, the tab bar 40 + the safe area.
- **The head** becomes one line (the product's name, the project, Stop all, the settings, the spend as a count beside
  them) in place of three; Stop all stays a full-size 44 px control (it is a safety control).
- The emoji on goal rows go; the Office light variant of `app.css` goes (the phone is dark, as §2 says); the 51 raw
  colours in `app.css` become roles; `sw.js` caches `orkforms/office` and its fonts; the cache version rises.
- Measured on the prototype: about 10 % less height before the head's rework, the head's two lines more after it.

## 8a. ASCII-game cues (the owner's choice, decisions §53.10)
A nod to NetHack, Dwarf Fortress and Brogue, in six small things; none of them changes what a screen says or does, and each
is drawn so it works without the font having the glyph (the shipped subsets of Plex Mono have no box-drawing, block or
shape characters), without a screen reader reading them out, and in the form's colours.
1. **Double frame on dialogs:** a dialog, a sheet and a menu take `border: 3px double var(--of-edge)` (a 1 px line, a gap,
   a 1 px line: the look of `╔═╗`), with the notch of §4. Cards and rows keep their 1 px edge.
2. **A block caret.** A focused text field shows `caret-shape: block` (Chrome 138+, Safari and Firefox keep their bar until
   they follow); a screen that waits for a model (the Taskmaster *thinking*, a Grunt *working*) shows a block `█` drawn by CSS
   after its word, blinking 1 s in steps. Under `prefers-reduced-motion` both are still.
3. **Blocks and hatching, drawn.** A limit, a spend and a plan's progress are the segmented meter of §4; a task's pips on the
   Map and in Agents are 8 × 8 cells in a row (done: ink; working: ink with a 2 px hole; waiting: `--of-frame`; failed:
   `--of-danger`; asks: `--of-alert`), `aria-label` saying the count in words. Empty and loading grounds are a hatch
   (`repeating-linear-gradient`, 2 px lines at 45°, `--of-frame`), never a spinner image. ✓ ✗ ! marks are the icons `check`,
   `close`, `warning-diamond`, not typed glyphs.
4. **The key line (desktop).** A 24 px line at the foot of the page, `--of-ink-muted`, lists the keys that work *here*, as
   `[Esc] close  [Ctrl+Enter] send  [↑↓] choose`, from the context (a dialog open, a field focused, a tab active, the Board).
   It shows only keys that exist. The keys of the existing code stay as they are (Esc, Enter, Ctrl or ⌘ + Enter, the arrows
   of Review); **new behaviour, the one in this spec:** the items of a menu get letters (`a) Add agent`, `e) Edit`), unique
   in the menu, shown in the pixel face and answered by that key (a menu is the project menu, the Merge menu, a row's
   *more*). The arrows in `[↑↓]` are the pixel chevrons, not typed. The line is hidden on the phone.
5. **Orks as characters.** Taskmaster `@`, Grunt `o`, idea `?`, goal `*`, task `+`: a one-character mark in the text face before a
   name in Agents, the Map's nodes and Review's lines. **A mark never stands alone:** its word is beside it or in its
   `aria-label`, and the glyph is `aria-hidden` (the word is the glossary's, `realm/lexicon.py`; no new word). The legend is
   in the form's README and in `RULES`.
6. **The ork, from the organisation's mark.** The art is the GitHub organisation's pixel ork (a crown of three points, stepped
   ears, two slits for eyes, two tusks), read from the mark's own 12 × 9 grid of cells, **each cell two characters wide and one
   line high** (so a cell stays square): crown `^^`, head and ears `##`, tusks `||`, the eyes left open or marked. ASCII
   only, 24 columns × 9 lines, monochrome, in the text face at 12/14 (`white-space: pre`, `aria-hidden`), `--of-ink-muted`;
   **on an empty screen it is centred, not left at the top:** the ork over the screen's own sentence (whose words stay as
   they are) is one block, centred on both axes in the free area of its pane (`display: grid; place-content: center;
   justify-items: center; text-align: center`; the `<pre>` is centred as a whole box and its lines stay left-aligned, so the
   art keeps its shape); a pane's head and its actions stay at the top and the block centres in what is left under them;
   on the phone it centres between the head and the tab bar. A block taller than the free area stops centring and scrolls from
   its top, so nothing is cut off. An ork that stands with other content (a list with one empty section: the Board's *Ideas*
   under *Needs you*) is not an empty screen: it is not drawn there, the section keeps its sentence. Five files in `office/ascii/`, one per state,
   all the same size so a screen's layout does not jump when its ork changes. Faces read the file by name; the art is not
   copied into a template.

   `ork.txt`, the default, for a screen with nothing to show (the Board with no idea, Review with nothing waiting, Agents
   with no task, a first start):
```
      ^^  ^^^^  ^^
      ^^^^^^^^^^^^
      ############
##  ################  ##
########################
  ####    ####    ####
    ################
    ##||########||##
    ##||########||##
```
   `ork-asleep.txt` (eyes `--`, a `z`): the work is held for the night, or an idea waits for its `start_at`.
```
      ^^  ^^^^  ^^    Z
      ^^^^^^^^^^^^  z
      ############
##  ################  ##
########################
  ####----####----####
    ################
    ##||########||##
    ##||########||##
```
   `ork-asks.txt` (eyes `oo`, `?`): the first thing on the list is a question to the person (the preview's empty text *First
   on your list: …*, a goal's question).
```
      ^^  ^^^^  ^^  ?
      ^^^^^^^^^^^^     ?
      ############
##  ################  ##
########################
  ####oooo####oooo####
    ################
    ##||########||##
    ##||########||##
```
   `ork-failed.txt` (eyes `xx`, `!`): a screen whose only content is a failure (a run that failed with nothing else open).
```
      ^^  ^^^^  ^^  !
      ^^^^^^^^^^^^
      ############
##  ################  ##
########################
  ####xxxx####xxxx####
    ################
    ##||########||##
    ##||########||##
```
   `ork-working.txt` (eyes `==`, `...`): a Grunt or the Taskmaster is working and there is nothing to read yet.
```
      ^^  ^^^^  ^^
      ^^^^^^^^^^^^  ...
      ############  ..
##  ################  ##
########################
  ####====####====####
    ################
    ##||########||##
    ##||########||##
```
   A state's ork never replaces its sentence or its colour: the signal is the screen's own (the alert edge, the danger text).
   The earlier set (a face with goggles and a cap) was drawn from the old logo and is dropped; no sprite, no image.

## 9. Tests (A, and the faces' B and C)
- **A0** `tests/test_orkforms.py` in `orkworks/orkforms` (its gate; Orkboard's critical tests add `test_orkforms_pin.py`):
  - `tokens.json` of a form has every token of §2–§4 under the names of this file; `tokens.css` is exactly what the
    generator makes of it (as `design-system/tokens.css` is);
  - **contrast, computed from the values:** `--of-ink`, `-muted`, `-faint` on canvas, panel and raised ≥ 4.5 : 1;
    `--of-edge` on each ground ≥ 3 : 1; each signal on the panel ≥ 4.5 : 1; every cell of the button-state table (§2) and the three action grounds in their own pairs ≥ 4.5 : 1 (edges ≥ 3 : 1); `--of-on-ink` on `--of-ink` ≥ 7 : 1;
  - no radius token above 0, no space or size outside the steps, no pixel size below 12 or fractional, the families
    named in `fonts/`, each font file present, `fonts.css` names only files that exist, the licences in `NOTICE` (Plex, Pixelify, Pixelarticons); every icon the sprite names exists in it and is drawn from the upstream file unchanged; the generator is deterministic (twice the same bytes);
  - the legacy roles of §1 are all defined, to colours of the form;
- **A1** `tests/test_orkforms_pin.py` (critical): the submodule is mounted at `design-system/orkforms` and `.gitmodules`
  names `orkworks/orkforms`; its commit is a tag (not a branch head); `tokens.css` there equals what the repository's
  generator makes of its `tokens.json`; `/ds/orkforms/office/tokens.css` is served by the host; the wheel's `package-data`
  lists the files; `RULES` names the form's roles; `tests/test_architecture.py` still holds (`orkboard/design` has no face,
  nothing of Orkboard is imported by the submodule's tools).
- **B** browser tests at 1 440 × 900 (`test_board_browser.py` and the others, kept green):
  - computed styles: a button, a tab and a pane's head are in the pixel face; a row, a card, a field, a paragraph, a log
    and a diff are in Plex Mono; `document.fonts` has both faces loaded, no request leaves the host for a font; a prose
    block is at most 90 characters wide;
  - `body` is 12/18; no visible text under 11 px, no pixel text under 12; every button, field and tab ≥ 24 px high; the
    top bar and a pane's head 32; panes keep their widths; no horizontal scroll;
  - in a button, a heading and a tab no digit is in the pixel face (the number sits in an `.of-num` span in the text face);
  a primary button's ground is `--of-action`, and nothing else on the page is filled with it;
  - no typed arrow or symbol glyph (`▾ ▸ › → ⚙ ◎`) in the faces' templates and rendered text; a select shows its chevron icon;
  - a selected tab, row and card is `--of-raised` with a 2 px `--of-ink` bar and is not an ink-filled box;
  - no visible element has a `border-radius` above 0 (a scan of every box, on the desktop and the phone);
  - a dialog and a menu have a double 3 px border; a focused field has `caret-shape: block`; a waiting screen's block is
    still under reduced motion; the key line lists only keys that work in the current context and each listed key does what
    it says; a menu's letters are unique and a letter activates its item (and does nothing while a field is focused);
  - each `office/ascii/*.txt` is ASCII only, exactly 9 lines, none longer than 24 columns, and the five are the same size;
    the empty states show their ork (`aria-hidden`, the same lines as the file) with their own sentence, the block's centre
    within 8 px of the free area's centre on both axes (desktop panes and the phone), and no ork inside a section of a pane that has
    other content; an `@ o ? * +` mark
    is `aria-hidden` and its word is present; no pip, meter or hatch is a typed glyph;
  - icons are 24 or 48 px (never another size) and take their text's colour;
  - no emoji in the page's text (a range check of the text nodes); a focused control shows its inset ring (a pixel of
    `--of-ink` inside the box); the selected row is raised with its bar; an asking card has the alert edge;
  - the old Office's files (`office.css`) and Camp's are not requested; a screenshot to `docs/design/img/v1/` when
    `ORKCRAFT_SHOTS` is set (before and after kept in the PR).
- **C** at 390 × 844, at the system text size 100 % and 130 %: the tab bar's three cells 56 px high, each with its icon (24 px) and word, one active; every control ≥ 40 px drawn, and its hit area (an
  `elementFromPoint` 2 px outside its box) is itself; no two hit areas overlap; rows ≥ 44; the head is one line; the
  pixel face at whole pixels at both sizes; no emoji; no horizontal scroll; the service worker caches the new files.
- All: `tests/test_gui_wording.py` (the labels are as they were), the critical tests (CLAUDE.md "Alpha").

## Not in this spec
- **`orkforms/game`:** the game's form (Camp's successor, with sprites and a richer palette), and Orkline's move to
  Orkforms (its Office to `orkforms/office`, its Camp to `orkforms/game`); each its own spec. Camp's themes stay as they
  are until then.
- A light Office (it returns as a second palette of this form if the testers ask).
- A pixel face for text a person wrote, or a Cyrillic pixel title (Pixelify's Cyrillic is weaker: *л* reads as *n*; the
  interface's words are English, §0 of CLAUDE.md, so it does not show; a different pixel face is a token).
- Renaming `.ok-*` and `.shell-*` call sites; moving the Map's or the tabs' layout (spec 39 owns them).
- Animations beyond §4, sound, a theme switcher in Orkboard's settings.
