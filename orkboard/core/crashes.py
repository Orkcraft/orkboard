"""Crash reports (orkGet's docs/crashes.md): where in Orkboard's code something broke, never what was in it.

The code is orkGet's, `orkboard/orkget/crashes.py`, bound to Orkboard's profile (`orkboard/product.py`): reports go
to Orkboard's own Sentry project through the proxy, after the same yes as the usage stats; each crash's traceback is
also kept in `~/.orkcraft/crashes/crash-orkboard-….txt`. This module is the copy's itself:

    r = crashes.install(machine, face="gui", demo=demo)   # the hooks; a session starts
    crashes.capture(e, where="command")
    r.close()
"""
import sys

from orkboard.product import PRODUCT  # noqa: F401  (the copy knows its product before it works)
from orkboard.orkget import crashes as _copy

sys.modules[__name__] = _copy
