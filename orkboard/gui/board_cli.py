"""`orkboard usage …` and `orkboard update …` (docs/specs/41-orkget.md §7): the machine's answer about usage stats and
crash reports, and the updates, from the terminal, as Orkline's `orkcraft usage` and `orkcraft update`. `main` in
gui/board_host.py hands them over; a folder named `usage` or `update` opens as `orkboard ./usage`.

    run(["usage", "on", "--id", "<32 hex>"])     # the installer's yes, with the id it drew (install.sh)
    run(["update", "check"])                     # what is out, nothing installed
"""
from __future__ import annotations

import argparse
import sys

from orkboard import __version__, settings
from orkboard.core import updates, usage

WORDS = ("usage", "update")

POLICY_WHAT = {
    "auto": "every update installs when Orkboard opens",
    "critical": "critical updates install when Orkboard opens; the others wait for `orkboard update` or the window",
    "ask": "nothing installs by itself; `orkboard update` or the window installs",
}


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="orkboard")
    sub = parser.add_subparsers(dest="word", required=True)
    usage_p = sub.add_parser("usage", help="Anonymous usage stats and crash reports: share them, stop, or see what is set")
    usage_p.add_argument("action", choices=("on", "off", "status"))
    usage_p.add_argument("--id", dest="install_id", default=None, metavar="HEX",
                         help="With on: the install id the installer drew (32 hex digits)")
    up_p = sub.add_parser("update", help="Install the latest version, see what is out, or say what installs by itself")
    up_p.add_argument("action", nargs="?", choices=("check", *updates.POLICIES), default=None,
                      help="check: only say what is out · auto | critical | ask: which updates install by themselves "
                           "when Orkboard opens (default: critical)")
    args = parser.parse_args(argv)
    if args.word == "usage":
        return _usage(args.action, args.install_id)
    return _update(args.action)


def _usage(action: str, install_id: str | None = None) -> int:
    """One answer for this computer, for Orkline and Orkboard alike (`machine.usage`); `on --id` keeps the id the
    installer drew, so the install and the app's events are one install."""
    machine = settings.load()
    if install_id is not None and not usage.ID.fullmatch(install_id):
        print("orkboard usage: --id must be 32 hex digits", file=sys.stderr)
        return 2
    if action != "status":
        usage.share(machine, action == "on", install_id)
        settings.save(machine)
    said = {True: "on", False: "off", None: "not asked yet (off)"}[machine.usage]
    print(f"usage stats and crash reports: {said} (one answer for this computer)")
    if machine.usage and machine.install_id:
        print(f"install id: {machine.install_id}")
    if usage.blocked():
        print(f"nothing is collected here: {usage.blocked()}")
    print("what Orkboard sends: that it opened (with the AI tools on) and closed (how long, in buckets), and where in "
          "its own code something broke; never your code, prompts, paths or project names")
    return 0


def _update(action: str | None) -> int:
    machine = settings.load()
    if action in updates.POLICIES:
        machine.updates = action
        settings.save(machine)
    if action not in (None, "check"):
        print(f"updates: {machine.updates} — {POLICY_WHAT[machine.updates]}")
        return 0
    if updates.blocked():
        print(f"updates are off here: {updates.blocked()}")
        return 0
    try:
        found = updates.offer(updates.check(force=True, timeout=15.0).manifest)
    except Exception as e:
        sys.stderr.write(f"orkboard error: the list of updates cannot be read ({e})\n")
        return 1
    if found is None:
        print(f"Orkboard {__version__} is the latest")
        return 0
    kind = " — a critical update" if found.critical else " — a major update" if found.major else ""
    print(f"Orkboard {found.version} is out{kind} (you have {__version__})")
    for line in found.notes:
        print(f"  {line}")
    way = updates.method()
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
