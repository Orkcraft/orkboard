"""Orkboard on its own (docs/specs/37-board-and-line.md §4, decisions §50): what the Board needs from its host, and the
host `orkboard` serves, built without the town.

    board = BoardHost(repo_root, owner, bus=…, toast=…, call=…, budget_ok=…, limits=…, day_logs=…, wiki_of=…)
    ideas = Ideas(board)                   # gui/ideas.py and its mixins use only what BoardHost has

    host = Orkboard(repo_root)             # the Board's own host: Ideas, Stop all, phones, updates, the first screen
    Server(host).start_thread()            # gui/server.py serves it as it serves Orkline's (gui/host.py)
    main([])                               # `orkboard` (and `orkboard board`): in a window, else the browser

Orkline's host (gui/host.py) builds the town and gives the Board a `BoardHost` made from it, `wiki_of` set (the town's
Wiki); Orkboard's has none (§3.5). Both read the same machine settings and the same `<repo>/.orkcraft/`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable

from orkboard import __version__, settings
from orkboard.core import bus as b
from orkboard.core import treasury, updates as core_updates
from orkboard.core.board_limits import BoardLimits
from orkboard.realm import analytics, call_log, day_log, event_log, halt, idea_target
from orkboard.sources import telemetry

TELEMETRY_REFRESH_S = 5.0       # as Orkline's host: this run's spend read again
SIZE = (1440, 900)


class CommandError(Exception):
    """A command the page sent that the host refuses; its text is shown to the person."""


def open_link(args: dict) -> bool:
    """`link.open`: a link of the page, in the person's browser (the app's window is a web view: it opens no tab)."""
    url = str(args.get("url", ""))
    if not url.lower().startswith(("http://", "https://")):
        raise CommandError("Only web links open in the browser")
    return webbrowser.open(url)


class BoardHost:
    """What the Board (gui/ideas.py and its mixins) needs from whoever runs it, and nothing of the town: the repository,
    the machine's settings (held by `owner.machine`, which a save may replace), the demo, the bus, a toast, a call on the
    host's thread, whether the budget lets work start, the AI tools' limits, the day logs, and the town's Wiki
    (`wiki_of`, None in Orkboard)."""

    def __init__(self, repo_root: Path, owner: Any, *, bus: Any, toast: Callable[..., None],
                 call: Callable[..., None], budget_ok: Callable[[], bool], limits: Callable[[], list],
                 day_logs: Any, demo: bool = False, wiki_of: Callable[[], Path | None] | None = None) -> None:
        self.repo_root = Path(repo_root)
        self._owner = owner
        self.bus = bus
        self.toast = toast
        self.call = call
        self.budget_ok = budget_ok
        self.limits = limits
        self.day_logs = day_logs
        self.demo = demo
        self.wiki_of = wiki_of

    @property
    def machine(self) -> settings.MachineSettings:
        return self._owner.machine

    @machine.setter
    def machine(self, value: settings.MachineSettings) -> None:
        self._owner.machine = value

    def publish(self, topic: str, **data: Any) -> None:
        self.bus.publish(topic, **data)

    def board_settings(self) -> dict:
        """The Board's settings of this project (spec 37 §8): its `.orkcraft/board.json` over the machine's `ideas`,
        `risk_paths` from its `orkcraft.toml`."""
        return settings.board_of(self.repo_root, self.machine.ideas)

    def save_board_settings(self, values: dict) -> dict:
        """The Board's settings written for this project only, never the machine's; what it now reads."""
        settings.save_board(self.repo_root, values)
        return self.board_settings()


class BoardLogs:
    """The Board's day logs (`/api/analytics`, `ideas.logs`): every model call of the last days and the Board's events
    and ideas, as one zip (realm/analytics.py). Orkline's are the town's (gui/day_logs.py), with its buildings. The
    project's keeper and runner keep their calls here themselves (`call_log.of_project`); a call no one placed goes to
    the shown project's (`Orkboard.shown`)."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def pack_period(self, days: int = 7, today: dt.date | None = None) -> tuple[str, bytes] | None:
        today = today or dt.date.today()
        days = max(1, min(int(days), day_log.KEEP_ANALYSIS))
        since = (today - dt.timedelta(days=days - 1)).isoformat()
        kept = [d for d in analytics.days_kept(self.root) if since <= d <= today.isoformat()]
        if not kept:
            if not event_log.read(self.root, since) and not analytics._board_files(self.root):
                return None
            kept = [(today - dt.timedelta(days=n)).isoformat() for n in range(days)]
        data = analytics.pack(self.root, kept, {call_log.TOWN: "The Board"}, lambda bid, day: [], lambda bid, day: [])
        return f"orkcraft-analytics-{kept[-1]}-to-{kept[0]}.zip", data

    def close(self) -> None:
        return None


class BoardPhone:
    """What a paired phone may do in Orkboard and what it sees (gui/phones.py reads it as the host's `phone_face`;
    Orkline's is gui/mobile.py): the Board's commands and Stop all, the project switcher, a Markdown file read-only
    (spec 37 §8: no edit and no git from the phone), and the snapshot's Board, small."""

    COMMANDS = ("mobile.hello", "mobile.snapshot", "halt", "projects.list", "projects.use", "mobile.push_key", "mobile.push_on",
                "mobile.push_off", "mobile.push_quiet")
    MARKDOWN = (".md", ".markdown")

    @classmethod
    def allowed(cls, host, name: str, args: dict | None = None) -> bool:
        if name == "files.read":
            path = (args or {}).get("path")
            return isinstance(path, str) and path.lower().endswith(cls.MARKDOWN)
        return name in cls.COMMANDS or (name.startswith(("ideas.", "ops.")) and name in host.commands)

    @staticmethod
    def guard(name: str, args: dict, device: dict | None = None) -> dict:
        """As Orkline's (gui/mobile.py `guard`): the event log says the phone, and the link is the listener's to say."""
        args = dict(args)
        if name.startswith("mobile.push_"):
            args.pop("device_id", None)                 # whose subscription it is: the listener's to say (gui/phone_push.py)
            if (device or {}).get("id"):
                args["device_id"] = device["id"]
        if name.startswith(("ideas.", "ops.", "projects.", "files.")) or name == "halt":
            args["device"] = "phone"
            args.pop("link", None)
            if (device or {}).get("id"):
                args["link"] = "paired"
        return args

    @staticmethod
    def phone_snapshot(host) -> dict[str, Any]:
        return host.phone_snapshot()


class _NoLogs:
    """The day logs with no project open: nothing to pack."""

    def pack_period(self, days: int = 7, today: dt.date | None = None) -> None:
        return None


class Orkboard:
    """The Board's own host (spec 37 §4, §8): the open projects (gui/board_projects.py, one Board each, one shown) and
    the Board's commands (`ideas.*`, to the shown one), the Files pane (`files.*`) and its Git section (`git.*`), Stop
    all (`halt`, every project's), pairing a phone (`phones.*`, added by the server), updates, `link.open`,
    `crash.window` and the onboarding's first screen (trust, the AI tools found); no class, no Mission 1, no town.
    The page is `static/board.js`, the phone's `pwa/board-app.js`.

    What is the host's is built once per host, beside the projects: the AI tools' limits, this run's spend, the
    phones, updates, the onboarding and Operations (gui/ops.py, spec 38: `ops.*`, its rows in the shown project's
    Needs you); what is a project's is its Board. With no project open it is the start screen: `ideas.*` say *Open a
    folder first*, Operations works as with one."""

    entry = "board.js"              # the desktop page's script (gui/server.py)
    phone_entry = "board-app.js"    # the phone's (gui/pwa.py)

    def __init__(self, repo_root: Path | None = None, demo: bool = False, restore: bool = False) -> None:
        """`repo_root`: the folder opened and shown (refused in words: `ideas.IdeasError`); `restore`: the projects
        open when Orkboard last closed are opened again too (`orkboard` does it; a test's host has only its own)."""
        from orkboard.gui import board_files, board_git, board_projects, folder_dialog, logs_save, onboarding, ops, phone_push, updates
        self.demo = demo
        self.machine = settings.load()
        self.bus = b.Bus()
        self.call: Callable[..., None] = lambda fn, *a: fn(*a)    # the server's loop, once it runs (gui/server.py)
        self.on_change: Callable[[], None] = lambda: None
        self.on_toast: Callable[[dict], None] = lambda data: None
        self.on_detail: Callable[[str], None] = lambda building_id: None
        self.sessions = None                                          # no terminal sessions in Orkboard
        self.run_id = telemetry.new_run_id()
        self.telemetry: telemetry.Telemetry | None = None             # this run's spend, in the shown project
        self.spend = telemetry.Snapshot()
        self._spend_at = float("-inf")
        self.limits = BoardLimits(Path.home(), lambda fn, *a: self.call(fn, *a), demo)
        self.town = self                # what gui/updates.py, gui/onboarding.py and gui/server.py read as `host.town`:
        self.phone_face = BoardPhone    # the machine, demo, call and toast — the host's own here, there is no town
        self.bus.subscribe(b.ANY, self._event)
        self.projects = board_projects.Projects(self)
        self.commands: dict[str, Callable[[dict], Any]] = {
            "halt": self._halt,
            "link.open": open_link,
            "crash.window": lambda a: None,           # the crash reporter is Orkline's (core/crashes.py)
            "mobile.hello": self._hello,
            "mobile.snapshot": self._mobile_snapshot,
        }
        self.pusher = phone_push.Pusher(self)          # notifications to a paired phone (spec 42 §3)
        self.commands.update(self.pusher.commands())
        self.updates = updates.Updates(self)
        self.commands.update(self.updates.commands())
        self.onboarding = onboarding.Onboarding(self)
        self.commands.update(self.onboarding.commands())
        self.commands.update(self.projects.commands())
        self.commands.update(board_files.Files(self.projects).commands())
        self.commands.update(board_git.Git(self.projects).commands())
        self.commands.update(folder_dialog.commands())   # Open folder's system dialog (desktop only: not BoardPhone's)
        self.commands.update(logs_save.commands(self))   # Save logs into the Downloads folder (desktop only, as well)
        self.ops = ops.Ops(self)                  # the person's, one per host: showing a project changes nothing of it
        self.commands.update(self.ops.commands())
        shown_board = self.commands["ideas.board"]
        self.commands["ideas.board"] = lambda a: self._with_ops(shown_board(a))
        if restore:
            self.projects.restore()
        if repo_root is not None:
            self.projects.open(repo_root)

    # -- the shown project -----------------------------------------------------------------------------------

    @property
    def project(self):
        return self.projects.current()

    @property
    def repo_root(self) -> Path | None:
        p = self.project
        return p.root if p is not None else None

    @property
    def board(self) -> BoardHost | None:
        p = self.project
        return p.board if p is not None else None

    @property
    def ideas(self):
        p = self.project
        return p.ideas if p is not None else None

    @property
    def day_logs(self) -> Any:
        p = self.project
        return p.logs if p is not None else _NoLogs()

    def shown(self, project: Any) -> None:
        """Another project is shown (gui/board_projects.py): this run's spend, the limits' reader, and the log and
        ledger of a call no one placed follow it (a Board's own calls and Operations' keep their own: realm/call_log.py
        `of_project`, `apart`)."""
        root = project.root if project is not None else None
        telemetry.keep_ledger(root)
        call_log.keep_days(root)
        self.telemetry = telemetry.Telemetry(root, self.run_id) if root is not None else None
        self._spend_at = float("-inf")
        self.limits.repo_root = root or Path.home()

    # -- the host's thread and its bus ---------------------------------------------------------------------

    def toast(self, message: str, title: str = "", severity: str = "information", timeout: float | None = None,
              kind: str = "") -> None:
        self.bus.publish(b.TOAST, message=message, title=title, severity=severity, timeout=timeout, kind=kind)

    def _event(self, event: b.Event) -> None:
        if event.topic == b.TOAST:
            self.on_toast({k: event.data.get(k) for k in ("message", "title", "severity", "timeout", "kind")})
            return
        self.on_change()

    def _with_ops(self, board: dict) -> dict:
        """The shown project's Board, Operations' rows in its Needs you (spec 38 §8)."""
        from orkboard.gui.ideas_board import sort_needs
        return {**board, "needs_you": sort_needs([*board.get("needs_you", []), *self.ops.needs()])}

    def budget_ok(self, root: Path | None = None) -> bool:
        """Whether work may start in a project (the shown one when none is named): this run's spend under its cap."""
        root = root or self.repo_root
        if self.demo or root is None:
            return False
        return not treasury.over(self.spend.spent_usd, treasury.budget(root)[0])

    def persons_cap(self, ops_ledger: Path) -> tuple[float, float]:
        """(the day's spend, the cap) Operations' calls are held by (spec 38 §1): across the open projects and
        Operations' own ledger, against the smallest cap among the open projects (the default with none open)."""
        return treasury.persons_cap([p.root for p in self.projects.open_ones], ops_ledger)

    # -- what the page sees ----------------------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """What the shell reads (spec 37 §4, §8): the shown Board's counts and limits, the first screen, the top
        bar's spend, the repository, the project switcher (`projects.list`) and an update."""
        root = self.repo_root
        gold_usd, lumber_tokens = treasury.budget(root) if root is not None else (treasury.GOLD_LIMIT_USD,
                                                                                   treasury.LUMBER_LIMIT_TOKENS)
        gold, _gold_level, lumber, _lumber_level = treasury.words(self.spend, gold_usd, lumber_tokens)
        _quota, _level, show_gold = treasury.quota(self.machine, self.limits())
        board = self.ideas.snapshot() if self.ideas is not None else {
            "focus": "board", "ideas_rev": 0, "needs_you": 0, "idea_states": [], "review_count": 0,
            "review_results": [], "limits": [], "reserve": {"share": idea_target.reserve({}, False), "night": False}}
        try:
            ops_needs = self.ops.count()
        except Exception:                      # Operations never breaks the snapshot
            ops_needs = 0
        board = {**board, "needs_you": int(board.get("needs_you") or 0) + ops_needs, "ops_rev": self.ops.rev}
        return {**board, "focus": "board", "onboarding": self.onboarding.snapshot(),
                "hud": {"show_gold": show_gold, "gold": gold, "lumber": lumber},
                "repo": str(root) if root is not None else "", "projects": self.projects.list(),
                "update": self.updates.snapshot()}

    def phone_snapshot(self) -> dict[str, Any]:
        """The snapshot as a phone gets it; `rev` names its content (gui/phones.py sends it again only when it moved), the
        reserve (spec 49 §2.3) among it."""
        s = self.snapshot()
        root = self.repo_root
        out = {"v": 1, "project": root.name if root is not None else "", "focus": "board", "look": "office",
               **{k: s[k] for k in ("ideas_rev", "ops_rev", "needs_you", "idea_states", "review_count", "review_results",
                                    "limits", "reserve")},
               "hud": dict(s["hud"])}
        out["rev"] = hashlib.sha256(json.dumps(out, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        return out

    def _hello(self, args: dict) -> dict[str, Any]:
        """The phone's handshake, as Orkline's (gui/mobile.py `hello`): what this host speaks, the mobile API's version
        among it, so a phone built for another version says so."""
        from orkboard.gui.phones import API          # phones imports this module
        return {"name": "orkcraft", "version": __version__, "api": API, "commands": sorted(self.commands)}

    def _mobile_snapshot(self, args: dict) -> dict[str, Any]:
        snap = self.phone_snapshot()
        if isinstance(args.get("since"), str) and args["since"] == snap["rev"]:
            return {"v": snap["v"], "rev": snap["rev"], "same": True}
        return snap

    def detail(self, building_id: str) -> None:
        """No building windows in Orkboard (gui/server.py asks only for a page that watches one)."""
        return None

    # -- the clock -------------------------------------------------------------------------------------------

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        if self.telemetry is not None and now - self._spend_at >= TELEMETRY_REFRESH_S:
            self._spend_at = now
            try:
                self.spend = self.telemetry.refresh()
            except OSError:
                pass
        self.limits.tick(now)
        self.updates.tick(now)
        self.projects.tick(now)           # every open project's Board: showing another stops nothing
        self.ops.tick(now)
        self.pusher.tick()

    def attach_phones(self, listener: Any) -> None:
        """The phone listener (gui/phones.py) made: the pusher reads its devices and its open sockets."""
        self.pusher.listener = listener

    def close(self) -> None:
        self.ops.close()
        self.projects.close_all()
        call_log.keep_days(None)

    # -- the page's commands ---------------------------------------------------------------------------------

    def command(self, name: str, args: dict | None = None) -> Any:
        from orkboard.core.op_commands import OpsError
        from orkboard.gui import ideas, onboarding, phone_push, updates
        fn = self.commands.get(name)
        if fn is None:
            raise CommandError(f"Unknown command: {name}")
        try:
            return fn(dict(args or {}))
        except (ideas.IdeasError, onboarding.OnboardingError, updates.UpdateError, OpsError, phone_push.PushRefused) as e:
            raise CommandError(str(e)) from None

    def _halt(self, args: dict) -> int:
        """🛑 Stop all: every open project's keeper and runner stop, every operation's call, every agent process is
        killed."""
        self.projects.stop_all(device="phone" if args.get("device") == "phone" else "desktop")
        self.ops.stop_all()
        stopped = halt.halt_all()
        self.toast(f"Stopped {stopped} run{'s' if stopped != 1 else ''}" if stopped else "Nothing was running",
                   title="Stop all")
        return stopped



# -- the window ------------------------------------------------------------------------------------------------

def toolkit() -> bool:
    """Whether pywebview has something to draw with: macOS and Windows always do; Linux needs GTK (gi) or Qt
    (qtpy), and without them pywebview prints its own tracebacks before it gives up."""
    if not sys.platform.startswith("linux"):
        return True
    from importlib.util import find_spec
    return any(find_spec(name) is not None for name in ("gi", "qtpy"))


def show(host: Any, server: Any, thread: Any, browser: bool, title: str = "Orkline",
         toolkit: Callable[[], bool] = toolkit, attach: Callable[[Any], None] | None = None,
         stop: Callable[[], None] = lambda: None, dress: Callable[[], None] | None = None) -> None:
    """The served page in a window of its own (pywebview), else the browser (`browser`, no toolkit, no pywebview);
    returns when it closed. `attach(window)`: what the window offers the page (a folder dialog); `dress()`: the app's
    name and icon, called only when a window opens (a Mac's menu bar and Dock: gui/mac_app.py)."""
    if not browser and not toolkit():
        sys.stderr.write("orkline: no window here (GTK or Qt for Python is not installed); opening the browser\n")
        browser = True
    if not browser:
        try:
            import webview
        except ImportError:
            sys.stderr.write("orkcraft: no window toolkit (pip install 'orkboard[gui]'); opening the browser\n")
            browser = True
    if browser:
        _in_browser(host, server, thread, stop)
        return
    if dress is not None:
        dress()
    url = server.url + ("&" if "?" in server.url else "?") + "app=1"      # the page knows it is the app's window
    window = webview.create_window(title, url, width=SIZE[0], height=SIZE[1], min_size=(960, 600),
                                   background_color="#141210")
    host.updates.quit = window.destroy
    if attach is not None:
        attach(window)
    try:
        webview.start()
    except Exception as e:                       # pywebview is there, a toolkit for it is not (Linux without GTK or Qt)
        sys.stderr.write(f"orkline: no window here ({e}); opening the browser\n")
        _in_browser(host, server, thread, stop)
        return
    except BaseException:
        _stop(server, thread, stop)
        raise
    _stop(server, thread, stop)


def _in_browser(host: Any, server: Any, thread: Any, stop: Callable[[], None]) -> None:
    host.updates.quit = server.stop
    print(f"Orkline is at {server.url} — Ctrl+C stops it")
    webbrowser.open(server.url)
    try:
        thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        _stop(server, thread, stop)


def _stop(server: Any, thread: Any, stop: Callable[[], None]) -> None:
    server.stop()
    thread.join(10)
    stop()


def run(repo_root: Path | None, browser: bool = False, port: int = 0, demo: bool = False) -> int:
    """Orkboard on `repo_root` (None: the start screen), the projects open when it last closed opened again, until
    its window closes; `core.updates.RESTART` when it closed on an update it installed."""
    from orkboard.gui import folder_dialog, mac_app
    from orkboard.gui.server import Server
    host = Orkboard(repo_root, demo=demo, restore=True)
    server = Server(host, port)
    thread = server.start_thread()
    show(host, server, thread, browser, attach=folder_dialog.attach, dress=mac_app.dress)
    return core_updates.RESTART if host.updates.restart_wanted else 0


def start_folder(folder: Path | None, machine: settings.MachineSettings) -> Path | None:
    """The project `orkboard` opens (spec 37 §8): the folder named; without one the last shown project, else the
    project it was started in (`config.find_project_root`); with none, None (the start screen)."""
    from orkboard.config import find_project_root
    if folder is not None:
        return Path(folder).expanduser().resolve()
    from orkboard.realm import project_folder
    last = next((r for r in machine.projects_recent if not project_folder.refusal(r)), None)
    if last is not None:
        return Path(last)
    try:
        return find_project_root(None)
    except FileNotFoundError:
        return None


def main(argv: list[str] | None = None) -> int:
    """`orkboard [board] [<folder>] [--repo DIR] [--browser] [--port N]`: Orkboard on that folder; without one the last
    shown project, else the one it was started in, else the start screen. `board` is the old habit of
    `orkcraft board`, and changes nothing. `orkboard --make-app`: Orkboard.app in ~/Applications (gui/mac_app.py)."""
    from orkboard.realm import project_folder
    parser = argparse.ArgumentParser(prog="orkboard", description="The Board on its own: goals, ideas, agents, review")
    parser.add_argument("words", nargs="*", metavar="folder", help="The project's folder to open")
    parser.add_argument("--version", action="version", version=f"Orkboard {__version__}")
    parser.add_argument("--repo", type=Path, default=None, help="Path to project root (as a folder named)")
    parser.add_argument("--browser", action="store_true", help="Open it in the browser instead of a window")
    parser.add_argument("--port", type=int, default=0, help="Port on 127.0.0.1 (default: any free one)")
    parser.add_argument("--make-app", action="store_true",
                        help="Put Orkboard.app in ~/Applications (a Mac): Orkboard from the Dock, Launchpad and Spotlight")
    args = parser.parse_args(argv)
    if args.make_app:
        from orkboard.gui import mac_app
        return mac_app.make_here()
    words = list(args.words)
    if words and words[0] == "board":                     # `orkboard board`: the same
        words.pop(0)
    if len(words) > 1:
        parser.error("one folder at most")
    folder = Path(words[0]) if words else args.repo
    root = start_folder(folder, settings.load())
    if root is not None:
        why = project_folder.refusal(root)
        if why:
            sys.stderr.write(f"orkline: {root}: {why}\n")
            return 1
    code = run(root, browser=args.browser, port=args.port)
    if code == core_updates.RESTART:            # the window installed an update: it opens again on it
        core_updates.restart([*(["--repo", str(root)] if root is not None else []),
                              *(["--browser"] if args.browser else []),
                              *(["--port", str(args.port)] if args.port else [])])
    return code


if __name__ == "__main__":
    sys.exit(main())
