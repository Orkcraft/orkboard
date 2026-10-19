# Orkboard — notes for contributors and agents

Orkboard is Orkline's Board on its own (docs/specs/37-board-and-line.md, docs/decisions.md §50): the Board with its
goals, the preview, Agents and Review, on the desktop and on a paired phone. **Orkline imports Orkboard, never the
other way round**: nothing here imports Orkline's package (`orkcraft`).

## Wording

- In everything a person reads — the interface (labels, hints, toasts, errors), the docs, the README — write **ork** /
  **orks** / **Ork** and **orkestration** / **orkestrate**, never "orc" or "orchestration". The product's name in the
  interface stays **Orkline** (decisions §50.1: Orkboard is the owner's lab, not published).
- Code keeps its names: identifiers, module and file names (`orc_id`), CSS ids, dict keys, event ids and config values
  stay as they are. The state keeps Orkline's names, so Orkboard and Orkline read the same settings and the same Board
  of a project, and switching between them loses nothing: `~/.config/orkcraft/`, `<project>/.orkcraft/`,
  `.orkcraft.json`, `orkcraft.toml`, the `ORKCRAFT_*` variables, the keychain's `orkcraft-ideas`, the phone's
  `orkcraft.v1` and its `orkcraft-app-v*` cache. Only the package is `orkboard`.
- **One look, orkUI's office** (dark, monochrome, colour a signal; its only pictures the races' heads, small: an accent,
  never a picture): the page and the phone are always drawn in it (docs/specs/40-design-system.md). The pixel face is for
  headings and buttons, never for a person's words.
- **Orks by their orkish names, everything else by what it does**: the Taskmaster, a Grunt; the Board, Review, Agents,
  Stop all. Never the other way round: no ork gets a job title, no window a camp name.
  `orkboard/realm/lexicon.py` `TERMS` is the glossary: a new concept gets its one word there, and new code writes that
  word. A renamed concept keeps its old spelling in `was`, and the interface says an old spelling in today's word: the
  page through `say()` for attributes and data. A `html` template's own text is written in today's word at the source
  (`tests/test_gui_wording.py` checks). What people or agents wrote keeps its words; Markdown, inputs, logs and
  terminals keep theirs.
- Labels, settings and anything about money or safety say plainly what happens.
- Tests that check a visible string use the same wording.

## Where code goes

- **The page is the one face** (`orkboard/gui/`): the desktop's `static/board.js` with the shell (`js/shell/*`,
  `js/board/*`), the phone's `static/pwa/board-app.js` with `pwa/shell-*.js`. Nothing imports Textual or Rich, and
  `tests/test_architecture.py` keeps it so.
- `orkboard/core/`, `orkboard/realm/`, `orkboard/design/` have no face: they never import `gui/`
  (`tests/test_architecture.py` checks it). A service changes the Board and publishes on the bus (`core/bus.py`). It
  never shows a toast or a dialog itself.
- Split a module before it grows past ~600 lines.
- **Orkboard and Orkline** (decisions §50): Orkline imports Orkboard's modules, never the other way round. Every import
  of the package (a lazy one too) names one of its own modules, and Orkboard starts with no module of Orkline's
  (`tests/test_architecture.py`). New engine code (the Board, a tool's run, the gate) is written here. While Orkline
  keeps its frozen copy of these modules (the testers' week, spec 37 §9), a fix the testers need is made here first and
  in Orkline the same day, this repository's commit named in Orkline's.
- The rules a model gets for a UI document are `design/ui.py` `RULES`.
- **Installing, updating and reporting are orkGet's** (github.com/orkWorks/orkGet, its spec 41): `orkboard/orkget/` is
  its copy, stamped and never edited here; a change is made in orkGet, then copied (`python -m orkboard.orkget.stamp
  <orkGet>`, `tests/test_orkget_copy.py`). Orkboard's profile is `orkboard/product.py`; `core/updates.py`,
  `core/usage.py` and `core/crashes.py` are the copy's modules themselves. An event Orkboard sends is listed in
  orkGet's `schemas/orkboard.json` first.
- **The design system is orkUI** (github.com/orkWorks/orkUI): `design-system/orkui` is its copy, stamped and never edited
  here; a change to the look is made in orkUI, then copied (`python -m orkboard.design.orkui <orkUI>`). Orkboard's sheets
  read orkUI's tokens and carry no colour, font or corner of their own (`tests/test_design_system.py`).
- **An agent's craft is its race** (decisions §53): an ork engineers, an elf designs, a goblin minds the data, a gnome
  markets; its tier is the gear on its head. Taskmaster and the Grunts are orks.

## Alpha: merge fast, with the critical tests

- While Orkboard is in alpha, a change is merged into `main` as soon as the **critical tests** pass; the full suite and
  the browser tests are not waited for. A red full CI after the merge is fixed by the next commit to `main`.
- The critical tests: `tests/test_architecture.py`, `tests/test_board_alone.py`, `tests/test_updates.py` (the gate's
  `always` in `orkcraft.toml`), and the test files of the modules the change touches.
- This section is removed when the project leaves alpha.
