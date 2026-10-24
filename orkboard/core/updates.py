"""Updates (docs/updates.md): Orkboard looks for a newer version of itself and installs it — orkGet's updater
(`orkboard/orkget/updates.py`, the copy) bound to Orkboard's profile (`orkboard/product.py`).

The list of releases is `updates.json` at the root of Orkboard's repository (orkWorks/orkBoard), read from its `main`
branch; while it has none, nothing is offered. Orkline's list is Orkline's: Orkboard never reads it, and keeps what it
read in a cache file of its own.

    s = updates.load_state()                  # what was read last, from the cache: no network
    offer = updates.offer(s.manifest)         # what is newer than this version
    offer.version, offer.critical, offer.major, offer.notes
    way = updates.method()                    # how this copy was installed: git, brew, pipx, uv, pip
    result = updates.install(way)             # its own tool upgrades it; result.ok, result.output
    updates.check(force=True)                 # read the list again now (a few seconds at most)

A critical release installs by itself when Orkboard opens (`at_launch`), unless the policy says otherwise
(`settings.updates`: auto · critical · ask); any other is offered in the window and installs with one click.
A major one (a later line, 0.2 → 0.3) is offered louder. `ORKCRAFT_NO_UPDATE` and CI turn it all off.
"""
from __future__ import annotations

from orkboard.product import PRODUCT
from orkboard.orkget.updates import *  # noqa: F401,F403  (the updater's names, as before orkGet)
from orkboard.orkget.updates import (  # noqa: F401  (the names `*` leaves out, read by the window and the tests)
    BRANCHES, CHECK_EVERY_S, FETCH_TIMEOUT_S, INSTALL_TIMEOUT_S, MAX_BYTES, POLICIES, RESTART, RETRY_FAILED_S,
    UPDATED_ENV, Method, Offer, Release, Result, State, at_launch, blocked, check, check_later, due, fetch, install,
    installed_version, load_state, major, method, newer, offer, releases, remember, restart, save_state, series,
    state_path, url, version_key)

MANIFEST_URL = PRODUCT.manifest
SOURCE = PRODUCT.source
MANUAL = PRODUCT.manual
PYPI = PRODUCT.pypi                        # Orkboard is not on PyPI: it installs from git
NAMES = PRODUCT.names
