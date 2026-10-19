"""Orkboard as orkGet knows it (orkWorks/orkGet, docs/specs/41-orkget.md §2): the profile its copy works with.

`orkboard/orkget/` is orkGet's copy, stamped and never edited here (`python -m orkboard.orkget.stamp <orkGet>` takes
it again). It installs, updates and reports for Orkline and Orkboard alike; what differs is this profile, handed to
it once, here, before anything of it works. `core/updates.py`, `core/usage.py` and `core/crashes.py` import this
module first and are the copy's modules themselves.

The values are what Orkboard's updater had before orkGet; `manifest` never changes (every installed copy reads it).
"""
from __future__ import annotations

from orkboard import __version__
from orkboard.orkget import profile

PRODUCT = profile.use(profile.Profile(
    product="orkboard", name="Orkboard", package="orkboard", version=__version__, agent="orkboard",
    manifest="https://raw.githubusercontent.com/Orkcraft/orkboard/main/updates.json",
    source="git+https://github.com/Orkcraft/orkboard",
    manual='uv tool install --force "orkboard[gui] @ git+https://github.com/Orkcraft/orkboard"',
    entry="orkboard.gui.board_host", state="orkboard-updates.json"))
