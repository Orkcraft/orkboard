"""The commands of `orkboard` that open no window (gui/board_host.py `main` hands them over), as Orkline's:

    orkboard usage on|off|status [--id HEX]     # the one answer to usage stats and crash reports (core/usage.py)
    orkboard update [check|auto|critical|ask]   # install the latest version, see what is out, or say what installs
                                                # by itself (core/updates.py)

The answer is the machine's, for every product on it (orkGet's docs/usage.md): `usage on` here is Orkline's answer
too. `on --id` keeps the id the installer drew (orkboard/orkget/install.sh), so the install and the first days are one
install. A folder named `usage` or `update` opens as `orkboard ./usage`.
"""
from __future__ import annotations

import argparse
import sys

from orkboard import __version__, settings

WORDS = ("usage", "update")


def main(argv: list[str]) -> int:
    """`argv` starts with one of `WORDS`."""
    parser = argparse.ArgumentParser(prog="orkboard")
    sub = parser.add_subparsers(dest="word", required=True)
    usage_p = sub.add_parser("usage", help="Anonymous usage stats and crash reports: share them, stop, or see what is set")
    usage_p.add_argument("action", choices=("on", "off", "status"))
    usage_p.add_argument("--id", dest="install_id", default=None, metavar="HEX",
                         help="With on: the install id the installer drew (32 hex digits)")
    up_p = sub.add_parser("update", help="Install the latest version, see what is out, or say what installs by itself")
    up_p.add_argument("action", nargs="?", choices=("check", "auto", "critical", "ask"), default=None,
                      help="check: only say what is out · auto | critical | ask: which updates install by "
                           "themselves (default: critical)")
    args = parser.parse_args(argv)
    if args.word == "usage":
        return usage(args.action, args.install_id)
    return update(args.action)


def usage(action: str, install_id: str | None = None) -> int:
    from orkboard.core import usage as stats
    machine = settings.load()
    if install_id is not None and not stats.ID.fullmatch(install_id):
        print("orkboard usage: --id must be 32 hex digits", file=sys.stderr)
        return 2
    if action != "status":
        stats.share(machine, action == "on", install_id)
        settings.save(machine)
    said = {True: "on", False: "off", None: "not asked yet (off)"}[machine.usage]
    print(f"usage stats and crash reports: {said} (one answer for every product on this computer)")
    if machine.usage and machine.install_id:
        print(f"install id: {machine.install_id}")
    if stats.blocked():
        print(f"nothing is collected here: {stats.blocked()}")
    elif not stats.endpoint():
        print("nothing is sent: this build has no usage proxy")
    print("what is collected: https://github.com/orkWorks/orkGet/blob/main/docs/usage.md")
    return 0


def update(action: str | None) -> int:
    from orkboard.core import updates
    machine = settings.load()
    if action in updates.POLICIES:
        machine.updates = action
        settings.save(machine)
    if action not in (None, "check"):
        print(f"updates: {machine.updates} — " + {
            "auto": "every update installs when Orkboard opens",
            "critical": "critical updates install when Orkboard opens; the others wait for `orkboard update`",
            "ask": "nothing installs by itself; `orkboard update` installs"}[machine.updates])
        return 0
    if updates.blocked():
        print(f"updates are off here: {updates.blocked()}")
        return 0
    try:
        found = updates.offer(updates.check(force=True, timeout=15.0).manifest)
    except Exception as e:
        sys.stderr.write(f"orkboard error: the list of updates cannot be read ({e})\n")
        return 1
    way = updates.method()
    if found is None:
        print(f"Orkboard {__version__} is the latest")
        return 0
    print(f"Orkboard {found.version} is out{' — a critical update' if found.critical else ''} "
          f"(you have {__version__})")
    for line in found.notes:
        print(f"  {line}")
    if action == "check":
        print(f"install it: orkboard update ({way.describe()})" if way.can else way.why)
        return 0
    if not way.can:
        sys.stderr.write(f"orkboard error: {way.why}\n")
        return 1
    print(f"installing ({way.describe()})…")
    result = updates.install(way)
    updates.remember(result, found.version)
    if not result.ok:
        sys.stderr.write(f"orkboard error: the update did not install:\n{result.output}\n")
        return 1
    print(f"installed Orkboard {result.version or found.version}; open Orkboard again to run it")
    return 0
