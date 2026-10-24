"""Anonymous usage stats (docs/specs/41-orkget.md §7): orkGet's usage client (`orkboard/orkget/usage.py`, the copy)
bound to Orkboard's profile. Off until the operator says yes, one answer per machine for Orkline and Orkboard
(`machine.usage`, `machine.install_id`); then Orkboard sends only `app_opened` and `app_closed`, the events its schema
lists (`orkboard/orkget/schemas/orkboard.json`), never what is in a project.

    u = Usage(machine, face="gui", demo=demo)
    u.track("app_opened", face="gui", tools=["claude"])     # an unknown event or property is dropped, never sent
    u.tick(time.monotonic())
    u.close()                                                # app_closed, and what is left goes, briefly
"""
from __future__ import annotations

from orkboard.product import PRODUCT  # noqa: F401  (the copy knows its product before it works)
from orkboard.orkget.usage import *  # noqa: F401,F403
from orkboard.orkget.usage import (  # noqa: F401
    COUNTS, ENDPOINT, ID, MINUTES, SECONDS, Usage, blocked, clean, count, debug, endpoint, events, minutes, schema,
    sets, share, sharing)
