"""Crash reports (docs/specs/41-orkget.md §7): orkGet's reporter (`orkboard/orkget/crashes.py`, the copy) bound to
Orkboard's profile. One answer with the usage stats: off until the operator says yes. Then where in Orkboard's own code
something broke — the error's type, its message scrubbed, file, function and line — goes to Orkboard's own Sentry
project as `orkboard@<version>`; never a project's code, a prompt or a path of the person's. Whatever was answered,
each crash is also written to `~/.orkcraft/crashes/`, its file named with the product.

    r = crashes.install(machine, face="gui", demo=demo)    # the hooks; a session starts
    r.capture_window(message, stack)                        # an error of the page (js/crashes.js)
    r.close()                                               # the session ends; the hooks go
"""
from __future__ import annotations

from orkboard.product import PRODUCT  # noqa: F401  (the copy knows its product before it works)
from orkboard.orkget.crashes import *  # noqa: F401,F403
from orkboard.orkget.crashes import (  # noqa: F401
    Reporter, capture, endpoint, install, js_frames, log_dir, scrub)
