"""A goal's element (docs/specs/50-parties-and-goals.md §2.3, decisions §63.4): the mark every card of the goal wears, one of orkUI's
five (`design-system/orkui/office/elements/`: a pixel symbol and a muted colour). Given once, to the goal that has none, as the one
used least among its party's open goals, and kept in its `state.json`; a goal moved to another party keeps its own. The faces draw it
and never name it.

    idea_element.pick(["ice", "ice", "dust"])                  # "meadow": the one used least, ties in ELEMENTS' order
    idea_element.of(state_dir, "dark-mode")                    # "" before one is given
    idea_element.give(root, state_dir, "dark-mode")            # the one it has, else the one it is given now (stored)

No face, no model.
"""
from __future__ import annotations

import os
from pathlib import Path

from orkboard.realm import ideas

ELEMENTS = ("meadow", "ice", "dust", "void", "lava")


def pick(used: list[str]) -> str:
    """The element used least in `used`, ties by `ELEMENTS`' order (a word that is no element counts for none)."""
    return min(ELEMENTS, key=lambda e: (list(used).count(e), ELEMENTS.index(e)))


def of(state_dir: Path, slug: str) -> str:
    """The goal's element; "" when it has none yet."""
    element = ideas.state(state_dir, slug).get("element")
    return element if element in ELEMENTS else ""


def open_elements(root: Path, state_dir: Path, party: str, besides: str = "") -> list[str]:
    """The elements of the party's open goals (not done; a dropped goal is gone), without `besides`."""
    out = []
    for i in ideas.ideas(root, party):
        if i["slug"] == besides:
            continue
        st = ideas.state(state_dir, i["slug"])
        if st["state"] != "done" and st.get("element") in ELEMENTS:
            out.append(st["element"])
    return out


def give(root: Path, state_dir: Path, slug: str, used: list[str] | None = None) -> str:
    """The goal's element: the one it has, else the one picked against its party's open goals and stored in its state (one write,
    ever). `used`: those elements when the caller has them already (a map that gives to many goals in a row). The write is not a
    change of the goal: its `state.json` keeps its modification time (`ideas.touched_at` says when the goal last changed)."""
    with ideas.LOCK:
        have = of(state_dir, slug)
        if have:
            return have
        if used is None:
            page = ideas.idea_page(root, slug)
            used = open_elements(root, state_dir, (page.get("track") if page is not None else "") or ideas.GENERAL, besides=slug)
        element = pick(used)
        path = ideas.state_folder(state_dir, slug) / "state.json"
        try:
            before = path.stat()
        except OSError:
            before = None
        ideas.save_state(state_dir, slug, element=element)
        if before is not None:
            try:
                os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
            except OSError:
                pass
        return element
