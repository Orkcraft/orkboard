"""Updates (orkGet's docs/updates.md): Orkboard looks for a newer version of itself and installs it.

The code is orkGet's, `orkboard/orkget/updates.py`, bound to Orkboard's profile (`orkboard/product.py`: its list of
releases, `updates.json` on Orkcraft/orkboard's `main`, read nowhere else; its cache, `orkboard-updates.json`). This
module is that one itself, so `from orkboard.core import updates` and a test's monkeypatch reach the same functions:

    s = updates.load_state()                  # what was read last, from the cache: no network
    offer = updates.offer(s.manifest)         # what is newer than this version
    way = updates.method()                    # how this copy was installed: git, pipx, uv, pip
    result = updates.install(way)             # its own tool upgrades it
"""
import sys

from orkboard.product import PRODUCT  # noqa: F401  (the copy knows its product before it works)
from orkboard.orkget import updates as _copy

sys.modules[__name__] = _copy
