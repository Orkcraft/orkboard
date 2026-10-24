# Updates

Orkboard looks for a newer version of itself and installs it with orkGet's updater, which it carries as a copy
(`orkboard/orkget/`, [orkGet's docs/updates.md](https://github.com/orkWorks/orkGet/blob/main/docs/updates.md)):
the same code as Orkline's, with Orkboard's profile (`orkboard/product.py`).

## What a person sees

- **In the window**: when a newer version is out, Orkboard asks once per version, in a dialog with **Update and
  restart** (`js/shell/update.js`). A **critical** update (a fix for something that loses work or lets harm in) is
  asked loudly; a **major** one (a later line: 0.1 → 0.2, 1.x → 2.0, or a release marked `"major": true`) says that
  what is new may change how you work. *Later* hides it until the next version (a critical one, until the window
  opens again).
- **Settings → Updates**: the version, what is out with *Update…*, *Check now*, and which updates install by
  themselves when Orkboard opens: *Critical ones* (the default), *All*, or *None*.
- **The terminal**: `orkboard update` installs what is out, `orkboard update check` only says it,
  `orkboard update auto|critical|ask` sets what installs by itself. One setting per machine, shared with Orkline.

A critical update installs when Orkboard opens, before anything else loads, unless the setting is *None*; an install
that fails never stops Orkboard from opening and is tried again after a day.

## Releasing

One commit to `main` raises `__version__` in `orkboard/__init__.py` and adds the release at the top of
[`updates.json`](../updates.json) (`tests/test_updates.py` checks both). `"critical": true` only for a security fix or
a bug that loses work: it installs on every machine without asking, and its `notes` say plainly what it fixes.
`"major": true` only for a release that changes what people do when its number does not say so already.

Installed copies read the list from
`https://raw.githubusercontent.com/orkWorks/orkBoard/main/updates.json` (`PRODUCT.manifest`, pinned by the tests):
that address never changes, and it has to be readable without signing in, or no copy ever sees an update.

`ORKCRAFT_NO_UPDATE=1` (and CI) turns updates off; `ORKCRAFT_UPDATE_URL` reads the list from elsewhere (a fork, a
`file://` path).
