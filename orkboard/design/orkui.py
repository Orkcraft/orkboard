"""orkUI, the design system Orkboard is drawn in (https://github.com/orkWorks/orkUI; docs/specs/40-design-system.md): a
copy of its `office` look in `design-system/orkui/`, with orkUI's licence and notice, served at `/ds/orkui/` to the
desktop (gui/server.py) and beside the app's own files to the phone (gui/pwa.py). Never edited here: a change is made in
orkUI, then copied over, and `ORKUI.json` stamps which orkUI it is and every file's hash.

    python -m orkboard.design.orkui ../orkUI    # copy orkUI's office/ (and LICENSE, NOTICE) here, stamp ORKUI.json
    orkui.problems()                            # what in the copy is not what its stamp says (the tests run it)
    orkui.race_png("elf", "elder")              # "races/elf-elder.png": a race's head, under ROOT

No face.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from orkboard.design import tokens

ROOT = tokens.ORKUI
STAMP = ROOT / "ORKUI.json"
SOURCE = "https://github.com/orkWorks/orkUI"
LOOK = "office"
OWN = ("LICENSE", "NOTICE")           # orkUI's own, beside the look's files


def _files(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and p.name != STAMP.name}


def stamp() -> dict:
    """ORKUI.json: where the copy came from (`from`, `version`, `commit`) and every file's sha256 (`files`)."""
    return json.loads(STAMP.read_text(encoding="utf-8"))


def problems() -> list[str]:
    """What in the copy is not orkUI's as stamped: a file missing, one added or one changed by hand."""
    try:
        want = stamp()["files"]
    except (OSError, ValueError, KeyError):
        return ["design-system/orkui/ORKUI.json is missing: copy orkUI with python -m orkboard.design.orkui <orkUI>"]
    have = _files(ROOT)
    out = [f"{n}: missing" for n in sorted(set(want) - set(have))]
    out += [f"{n}: not orkUI's (copy orkUI again, never edit here)" for n in sorted(set(have) - set(want))]
    out += [f"{n}: changed by hand" for n in sorted(set(want) & set(have)) if want[n] != have[n]]
    return out


def race_png(race: str, tier: str, big: bool = False) -> str:
    """A race's head at a tier, as a path under ROOT (orkUI races/: 24 x 22, @2x 48 x 44)."""
    return f"races/{race}-{tier}{'@2x' if big else ''}.png"


def copy(source: Path) -> dict:
    """orkUI's `office/` (from a checkout of orkUI at `source`) here, in place of the copy there was; then the stamp."""
    source = Path(source).resolve()
    office = source / LOOK
    if not (office / "tokens.css").is_file() or not (office / "components.css").is_file():
        raise ValueError(f"{source} is not a checkout of orkUI (no {LOOK}/tokens.css)")
    if ROOT.exists():
        shutil.rmtree(ROOT)
    shutil.copytree(office, ROOT)
    for name in OWN:
        shutil.copy2(source / name, ROOT / name)
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source, capture_output=True, text=True,
                                check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = ""
    found = re.search(r'^version\s*=\s*"([^"]+)"', (source / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    data = {"from": SOURCE, "look": LOOK, "version": found.group(1) if found else "", "commit": commit,
            "files": _files(ROOT)}
    STAMP.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m orkboard.design.orkui <a checkout of orkUI>")
    got = copy(Path(sys.argv[1]))
    print(f"orkUI {got['version']} ({got['commit'][:7] or 'no commit'}): {len(got['files'])} files in {ROOT}")
