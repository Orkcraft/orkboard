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
from orkboard.realm import analytics, call_log, day_log, event_log, halt
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


class BoardLogs:
    """The Board's day logs (`/api/analytics`, `ideas.logs`): every model call of the last days and the Board's events
    and ideas, as one zip (realm/analytics.py). Orkline's are the town's (gui/day_logs.py), with its buildings."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        call_log.keep_days(self.root)

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
        call_log.keep_days(None)


class BoardPhone:
    """What a paired phone may do in Orkboard and what it sees (gui/phones.py reads it as the host's `phone_face`;
    Orkline's is gui/mobile.py): the Board's commands and Stop all, and the snapshot's Board, small."""

    COMMANDS = ("mobile.hello", "mobile.snapshot", "halt")

    @classmethod
    def allowed(cls, host, name: str, args: dict | None = None) -> bool:
        return name in cls.COMMANDS or (name.startswith("ideas.") and name in host.commands)

    @staticmethod
    def guard(name: str, args: dict, device: dict | None = None) -> dict:
        """As Orkline's (gui/mobile.py `guard`): the event log says the phone, and the link is the listener's to say."""
        args = dict(args)
        if name.startswith("ideas.") or name == "halt":
            args["device"] = "phone"
            args.pop("link", None)
            if (device or {}).get("id"):
                args["link"] = "paired"
        return args

    @staticmethod
    def phone_snapshot(host) -> dict[str, Any]:
        return host.phone_snapshot()


class Orkboard:
    """The Board's own host (spec 37 §4): the Board's commands (`ideas.*`), Stop all (`halt`), pairing a phone
    (`phones.*`, added by the server), updates, `link.open`, `crash.window` and the onboarding's first screen (trust,
    the AI tools found); no class, no Mission 1, no town. The page is `static/board.js`, the phone's `pwa/board-app.js`."""

    entry = "board.js"              # the desktop page's script (gui/server.py)
    phone_entry = "board-app.js"    # the phone's (gui/pwa.py)

    def __init__(self, repo_root: Path, demo: bool = False) -> None:
        from orkboard.gui import ideas, onboarding, updates
        self.repo_root = Path(repo_root).resolve()
        self.demo = demo
        self.machine = settings.load()
        self.bus = b.Bus()
        self._call: Callable[..., None] = lambda fn, *a: fn(*a)     # the server's loop, once it runs
        self.on_change: Callable[[], None] = lambda: None
        self.on_toast: Callable[[dict], None] = lambda data: None
        self.on_detail: Callable[[str], None] = lambda building_id: None
        self.sessions = None                                          # no terminal sessions in Orkboard
        self.run_id = telemetry.new_run_id()
        self.telemetry = telemetry.Telemetry(self.repo_root, self.run_id)
        telemetry.keep_ledger(self.repo_root)
        self.spend = telemetry.Snapshot()
        self._spend_at = float("-inf")
        self.limits = BoardLimits(self.repo_root, self.call, demo)
        self.day_logs = BoardLogs(self.repo_root)
        self.board = BoardHost(self.repo_root, self, bus=self.bus, toast=self.toast, call=self.call,
                               budget_ok=self.budget_ok, limits=lambda: self.limits(), day_logs=self.day_logs, demo=demo)
        self.town = self.board          # what gui/updates.py and gui/onboarding.py read as `host.town`: the machine,
        self.phone_face = BoardPhone    # demo, call and toast — the Board's own here, there is no town
        self.bus.subscribe(b.ANY, self._event)
        self.commands: dict[str, Callable[[dict], Any]] = {
            "halt": self._halt,
            "link.open": open_link,
            "crash.window": lambda a: None,           # the crash reporter is Orkline's (core/crashes.py)
            "mobile.hello": self._hello,
            "mobile.snapshot": self._mobile_snapshot,
        }
        self.updates = updates.Updates(self)
        self.commands.update(self.updates.commands())
        self.onboarding = onboarding.Onboarding(self)
        self.commands.update(self.onboarding.commands())
        self.ideas = ideas.Ideas(self.board)
        self.commands.update(self.ideas.commands())

    # -- the host's thread and its bus ---------------------------------------------------------------------

    def call(self, fn: Callable[..., None], *a: Any) -> None:
        self._call(fn, *a)

    def toast(self, message: str, title: str = "", severity: str = "information", timeout: float | None = None,
              kind: str = "") -> None:
        self.bus.publish(b.TOAST, message=message, title=title, severity=severity, timeout=timeout, kind=kind)

    def _event(self, event: b.Event) -> None:
        if event.topic == b.TOAST:
            self.on_toast({k: event.data.get(k) for k in ("message", "title", "severity", "timeout", "kind")})
            return
        self.on_change()

    def budget_ok(self) -> bool:
        return not self.demo and not treasury.over(self.spend.spent_usd, treasury.budget(self.repo_root)[0])

    # -- what the page sees ----------------------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """What the shell reads (spec 37 §4): the Board's counts and limits, the first screen, the top bar's spend,
        the repository and an update."""
        gold_usd, lumber_tokens = treasury.budget(self.repo_root)
        gold, _gold_level, lumber, _lumber_level = treasury.words(self.spend, gold_usd, lumber_tokens)
        _quota, _level, show_gold = treasury.quota(self.machine, self.limits())
        return {**self.ideas.snapshot(), "focus": "board", "onboarding": self.onboarding.snapshot(),
                "hud": {"show_gold": show_gold, "gold": gold, "lumber": lumber},
                "repo": str(self.repo_root), "update": self.updates.snapshot()}

    def phone_snapshot(self) -> dict[str, Any]:
        """The snapshot as a phone gets it; `rev` names its content (gui/phones.py sends it again only when it moved)."""
        s = self.snapshot()
        out = {"v": 1, "project": self.repo_root.name, "focus": "board", "look": "office",
               **{k: s[k] for k in ("ideas_rev", "needs_you", "idea_states", "review_count", "review_results", "limits")},
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
        if now - self._spend_at >= TELEMETRY_REFRESH_S:
            self._spend_at = now
            try:
                self.spend = self.telemetry.refresh()
            except OSError:
                pass
        self.limits.tick(now)
        self.updates.tick(now)
        self.ideas.tick(now)

    def close(self) -> None:
        self.ideas.stop_all()
        self.day_logs.close()

    # -- the page's commands ---------------------------------------------------------------------------------

    def command(self, name: str, args: dict | None = None) -> Any:
        from orkboard.gui import ideas, onboarding, updates
        fn = self.commands.get(name)
        if fn is None:
            raise CommandError(f"Unknown command: {name}")
        try:
            return fn(dict(args or {}))
        except (ideas.IdeasError, onboarding.OnboardingError, updates.UpdateError) as e:
            raise CommandError(str(e)) from None

    def _halt(self, args: dict) -> int:
        """🛑 Stop all: the Board's keeper and runner stop, every agent process is killed."""
        self.ideas.stop_all(device="phone" if args.get("device") == "phone" else "desktop")
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
         stop: Callable[[], None] = lambda: None) -> None:
    """The served page in a window of its own (pywebview), else the browser (`browser`, no toolkit, no pywebview);
    returns when it closed. `attach(window)`: what the window offers the page (Orkline's folder dialog)."""
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
    window = webview.create_window(title, server.url, width=SIZE[0], height=SIZE[1], min_size=(960, 600),
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


def run(repo_root: Path, browser: bool = False, port: int = 0, demo: bool = False) -> int:
    """Orkboard on `repo_root` until its window closes; `core.updates.RESTART` when it closed on an update it
    installed."""
    from orkboard.gui.server import Server
    host = Orkboard(repo_root, demo=demo)
    server = Server(host, port)
    thread = server.start_thread()
    show(host, server, thread, browser)
    return core_updates.RESTART if host.updates.restart_wanted else 0


def main(argv: list[str] | None = None) -> int:
    """`orkboard [board] [--repo DIR] [--browser] [--port N]`: Orkboard on the project it was started in
    (`config.find_project_root`); `board` is the old habit of `orkcraft board`, and changes nothing."""
    from orkboard.config import NOT_A_PROJECT_HINT, find_project_root
    parser = argparse.ArgumentParser(prog="orkboard", description="The Board on its own: goals, ideas, agents, review")
    parser.add_argument("command", nargs="?", choices=["board"], help=argparse.SUPPRESS)   # `orkboard board`: the same
    parser.add_argument("--version", action="version", version=f"Orkboard {__version__}")
    parser.add_argument("--repo", type=Path, default=None, help="Path to project root")
    parser.add_argument("--browser", action="store_true", help="Open it in the browser instead of a window")
    parser.add_argument("--port", type=int, default=0, help="Port on 127.0.0.1 (default: any free one)")
    args = parser.parse_args(argv)
    try:
        root = find_project_root(args.repo)
    except FileNotFoundError as e:
        sys.stderr.write(f"orkline error: {e}\n{NOT_A_PROJECT_HINT}\n")
        return 1
    code = run(root, browser=args.browser, port=args.port)
    if code == core_updates.RESTART:            # the window installed an update: it opens again on it
        core_updates.restart(["--repo", str(root), *(["--browser"] if args.browser else []),
                              *(["--port", str(args.port)] if args.port else [])])
    return code


if __name__ == "__main__":
    sys.exit(main())
