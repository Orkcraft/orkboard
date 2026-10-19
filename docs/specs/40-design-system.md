# Spec 40 — Orkboard in orkUI: the office look, and an agent's craft and tier as the head of its race

The owner, 19 October (decisions §53): rebuild Orkboard on the new design system, orkUI (github.com/orkWorks/orkUI), and
show an agent's role and tier with the mascots: **orks the engineers, elves design, goblins data, gnomes marketing**. Two
things: the page and the phone drawn in orkUI's *office* look in place of the old design system and Orkline's Camp sheets;
and on Agents (and wherever a task is shown) the head of the race of who does it, wearing its tier's gear.
**Built:** Claude · **Review:** full · P1.

Wording: CLAUDE.md (today's words; *craft*, *race*: `TERMS`). **This file is the contract**; the rest is the builder's
choice inside its files.

| part | builds | files (and their tests) |
|---|---|---|
| **A0. orkUI** | §1–§5, §6's heads | orkUI's own repository: `office/` (tokens, components, fonts, icons, races), `races/races.json`, `tools/`, `tests/test_orkui.py` |
| **A. The look** | §2, §7, §8 | `design-system/orkui/` (the copy), new `design/orkui.py`, `design/tokens.py`, `design/tokens.json` (`gui`), `gui/pwa.py`, `gui/static/index.html`, new `gui/static/page.css`, `js/shell/shell.css`, `js/board/board.css`, new `js/orkui.js`, the shell's markup (`.ork-btn`, `.ork-field`, `.ork-dialog`, the tab bar, the pixel marks), `pwa/app.css`, `pwa/util.js`, `pwa/board.js`, `pwa/sw.js`; the twelve Camp sheets deleted; new `tests/test_design_system.py` |
| **B. The races** | §6 | `realm/roles.py` (`craft`, `RACES`, `head`, `task_head`), `realm/lexicon.py`, `realm/board_map.py`, `gui/ideas_roles.py`, `gui/ideas.py`, `gui/ideas_review.py`, `js/orkui.js`, `js/shell/agents.js`, `js/shell/agentdialog.js`, `js/shell/preview.js`, `js/board/idea.js`, `js/board/stages.js`, `js/board/map.js`, new `pwa/shell-who.js`, `pwa/shell-agents.js`, `pwa/shell-agent.js`, `pwa/shell-preview.js`; new `tests/test_races_browser.py`, `tests/test_pwa_races_browser.py` |

## 0. The words
- **orkUI**: the design system; **office** its look (dark, monochrome); **a look** changes values, never names.
- **a craft** (`TERMS` `craft`): what an agent's work is: *Engineering*, *Design*, *Data*, *Marketing*.
- **a race** (`TERMS` `race`): orkUI's head that says a craft: an *ork* (orkUI's id `peon`), an *elf*, a *goblin*, a *gnome*.
- **a head**: a race at a tier, a 12 × 11 grid of pixels: a *novice* bare, a *seasoned* in iron, a *veteran* hooded.

## 1. orkUI (A0)
Its own repository, Apache-2.0, standard library only. `office/tokens.json` is the source of `tokens.css` (`--ork-*`, and
the old role names Orkboard's older rules read); `components.css` the components (`.ork-*`); `fonts.css` IBM Plex Mono and
Pixelify Sans (OFL); `icons/icons.svg` a Pixelarticons subset with the look's own chevrons; `ascii/` five ASCII orks;
`races/` the six races in three tiers (generated from `races/races.json`); `preview.html` the gallery. Pinned in a product
as a copy (§2).

## 2. The copy (A)
`design-system/orkui/` is orkUI's `office/`, its `LICENSE` and `NOTICE`, and `ORKUI.json`: `{"from", "look", "version",
"commit", "files": {path: sha256}}`. `python -m orkboard.design.orkui <a checkout of orkUI>` replaces it and stamps it;
`orkui.problems()` names a file missing, added or changed by hand (the tests run it). It is served at `/ds/orkui/` on the
desktop and beside the app's files on the phone. Never edited here.

## 3. Type
The pixel face (Pixelify Sans 500) for titles, headings, labels, buttons and tabs, never below 12 px and never for a
number or **a person's words** (a goal's, an idea's, a file's name, an agent's name, a Markdown heading); IBM Plex Mono for
everything else, 12/18 on the desktop and 16/22 on the phone. Orkboard's roles (`.ok-font-*`, `/roles.css`) map onto
orkUI's type tokens (`design/tokens.json` `gui.fonts`).

## 4. Colour, space, shape
Colour means a signal (danger, alert, success), except the one ork green of the primary action and the muted heads of
the races (decisions §53.5). Spaces from orkUI's steps; nothing round; a control's corners notched by 2 px; a dialog
framed `3px double`; selected is raised with a 2 px ink bar, never a white box. Orkboard's own sheets carry no colour, no
font and no corner of their own (`tests/test_design_system.py`).

## 5. Components
orkUI's: `.ork-btn` (`primary`, `danger`, `warning`, `quiet`), `.ork-field` (a select without orkUI's wrapper gets the
look's chevron in five pixels, `page.css`), `.ork-tab`, `.ork-head`, `.ork-row`, `.ork-card`, `.ork-chip`, `.ork-count`,
`.ork-label`, `.ork-meter`, `.ork-pips`, `.ork-dialog`, `.ork-menu`, `.ork-toast`, `.ork-tabbar` (the phone's tabs and the
desktop's below 1 024 px), `.ork-icon`, `.ork-chev`, `.ork-race` (§6). The reset is weightless (`:where()`), so a button
and a tab wear the pixel face. Every arrow and icon is a pixel mark: a chevron for a menu or a fold, `close`, `sliders`
for a gear; Needs you's kinds as icons, **a goal a flag**.

## 6. The races (B)
- **A role's craft** is its file's `craft` (`realm/roles.py` `CRAFTS`): engineering (a file without one, every role
  written before), design, data, marketing; `RACES` maps it to orkUI's race: `peon`, `elf`, `goblin`, `gnome`. Taskmaster
  and Grunt are orks: engineering, never another (`ideas.role_save` refuses).
- **The tier a head wears** (`head_tier`): a role on a tier, that tier; a model set by hand, its tier; By Target, the
  tier the Target gives a task (a middle task's for a role: thrift novice, balance seasoned, quality veteran). A task's
  head (`task_head`): the role it ran as (its type's role before), at `ran_tier` once it ran, else its planned tier
  shifted by the Target, a role's own model winning.
- **What the host sends**: `head` = `{"craft", "race", "tier"}` on every role and chip of `ideas.agents` and every role of
  `ideas.roles`, every task of `ideas.page`'s plan, `ideas.task` and `ideas.map`'s tasks; `ideas.roles` adds `crafts`:
  `[{"craft", "label", "race", "heads": {model id: tier}}]` for the dialog's head; `ideas.role_save` takes `craft`.
- **A head is an accent, never a picture**: 24 × 22 (its @2x for a sharp screen) beside an agent's name; 12 × 11, a pixel
  a cell (`.small`), in a chip, a plan's task, Stages, the Map's tasks and a task's Tier line. Its words are beside it
  (the craft and model: *Data · By Target, now Seasoned*; a task's tier: *Seasoned* with *elf · Design* muted) or in its
  title (*Seasoned elf · Design*). The tiers are said as the lexicon says them, the model list too (*Veteran · opus*).
- **The agent's dialog and sheet** pick the craft (*Engineering: an ork*, *Design: an elf*, *Data: a goblin*,
  *Marketing: a gnome*; disabled for the built-in two) and show the head the agent will wear with the model picked.
- **The Agents tab** is an ork's head (the peon, a novice) in the tab bar, as the other tabs' icons.

## 7. The page (A)
`index.html` loads orkUI's `fonts.css`, `tokens.css`, `components.css`, `/roles.css`, xterm's sheet and `page.css` (the
toasts, the first screen, `js/dialog.js`'s dialog, a checkbox, the paired phones); `shell.js` adds `board.css` and
`shell.css`. No Camp sheet, no `data-theme`; `data-look="office"`.

## 8. The phone (A)
The app is served orkUI's `fonts.css`, `tokens.css`, `components.css`, `fonts/*.woff2`, `races/*.png` and
`icons/icons.svg` beside its own files (same CSP); `app.css` is the shell's layout alone on orkUI's tokens; the worker's
cache is `orkcraft-app-v25` (the faces precached, the heads cache-first).

## 9. Tests
- **A0** (orkUI, `tests/test_orkui.py`): the tokens and their contrast, the steps, the faces and their licences, the
  icons, the orks, the races (a tier never moves the face; no office head more colourful than a signal; every edge pixel
  3:1 on the grounds), the reset's weight, `.ork-race`'s sizes.
- **A** (`tests/test_design_system.py`): the copy as stamped, a hand edit caught, the roles' map onto orkUI, the page's
  sheets, no colour, font, corner or Camp rule of Orkboard's own; the phone's (`tests/test_pwa.py`): its styles are the
  copy's, its faces, heads and icons served, the cache's version.
- **B**: `tests/test_roles.py` (crafts, heads, a task's head), `tests/test_gui_ideas.py` (the payloads, `craft` saved),
  `tests/test_board_map.py` (the Map's tasks), `tests/test_design_system.py` (every head in the copy, the page's words the
  lexicon's), `tests/test_races_browser.py` and `tests/test_pwa_races_browser.py` (the heads drawn, their sizes, the
  dialog and the sheet, the Agents tab).
