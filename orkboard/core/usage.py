"""Anonymous usage stats (orkGet's docs/usage.md): which features are used, never what is in them.

The code is orkGet's, `orkboard/orkget/usage.py`, bound to Orkboard's profile (`orkboard/product.py`); its events are
`orkboard/orkget/schemas/` (Orkboard's own: when it opens and closes). Off until the operator says yes, one answer
for every product on this machine (`usage.share`, `orkboard usage on|off`). This module is the copy's itself:

    u = usage.Usage(machine, face="gui", demo=demo)
    u.track("app_opened", face="gui", tools=[…])
    u.close()
"""
import sys

from orkboard.product import PRODUCT  # noqa: F401  (the copy knows its product before it works)
from orkboard.orkget import usage as _copy

sys.modules[__name__] = _copy
