"""Orkboard's profile for its copy of orkGet (docs/specs/41-orkget.md §2): the few values in which it differs from
Orkline. `orkboard/orkget/` is that copy, stamped and never edited here (`python -m orkboard.orkget.stamp <orkGet>`
takes it again); `core/updates.py`, `core/usage.py` and `core/crashes.py` bind it to this profile.

    from orkboard.product import PRODUCT        # the copy knows it from then on (`orkget.profile.current()`)
"""
from __future__ import annotations

from orkboard import __version__
from orkboard.orkget import profile

SOURCE = "git+https://github.com/orkWorks/orkBoard"

PRODUCT = profile.use(profile.Profile(
    product="orkboard", name="Orkboard", package="orkboard", version=__version__, agent="orkboard",
    manifest="https://raw.githubusercontent.com/orkWorks/orkBoard/main/updates.json",    # never changes
    source=SOURCE, names=("orkboard",),
    manual=f'uv tool install --force "orkboard[gui] @ {SOURCE}"',
    entry="orkboard.gui.board_host", state="orkboard-updates.json"))
