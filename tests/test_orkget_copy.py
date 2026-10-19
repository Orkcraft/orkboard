"""orkGet's copy (orkboard/orkget/, orkWorks/orkGet docs/specs/41-orkget.md §2): stamped and never edited here, and
bound to Orkboard's profile before anything of it works. A change to it is made in orkGet, then copied:
`python -m orkboard.orkget.stamp <a checkout of orkGet>`."""
from __future__ import annotations

import ast
from pathlib import Path

from orkboard import __version__, product
from orkboard.orkget import profile, stamp

COPY = Path(stamp.__file__).resolve().parent


def test_the_copy_is_as_orkget_stamped_it():
    assert stamp.problems() == [], "orkboard/orkget/ is orkGet's: change it there, then take the copy again"


def test_the_copy_imports_only_the_standard_library_and_itself():
    for path in COPY.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                assert node.module.split(".")[0] not in ("orkboard", "orkcraft"), (path.name, node.module)
            if isinstance(node, ast.Import):
                assert all(a.name.split(".")[0] not in ("orkboard", "orkcraft") for a in node.names), path.name


def test_orkboards_profile_is_the_one_the_copy_works_with():
    p = product.PRODUCT
    assert profile.current() is p
    assert (p.product, p.name, p.package, p.agent, p.version) == ("orkboard", "Orkboard", "orkboard", "orkboard",
                                                                    __version__)
    assert p.manifest == "https://raw.githubusercontent.com/Orkcraft/orkboard/main/updates.json"   # never changes
    assert p.entry == "orkboard.gui.board_host" and p.state == "orkboard-updates.json"
    assert p.pypi == "" and p.brew == "" and p.in_app == ("orkboard",) and not p.legacy_files


def test_the_installer_and_the_schemas_come_with_the_copy():
    assert (COPY / "install.sh").is_file() and (COPY / "schemas" / "orkboard.json").is_file()
    assert 'orkboard)\n    PRODUCT=orkboard' in (COPY / "install.sh").read_text(encoding="utf-8")
