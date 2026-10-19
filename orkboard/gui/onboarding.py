"""The onboarding's first screen (docs/design/gui-onboarding.md; spec 37 §4): your AI tools, found on this machine,
each with a Check, the warning of an experimental one, and a request for one the orks cannot run on yet. Orkboard's:
it opens on a machine never set up and closes on Open the board (`onboarding.skip`), the tools found kept on; no
class, no Mission 1 and no town.

Orkline's onboarding (gui/onboarding_town.py) is this screen and its own steps after it: who you are, the MCP
servers, your first town and the town going up while you watch.

    ob = Onboarding(host)                 # active on a machine never set up, unless ORKCRAFT_ONBOARDING=0
    host.commands.update(ob.commands())   # onboarding.tools · .check · .detect · .request · .skip · .close · .cancel
    ob.snapshot()                         # the snapshot's `onboarding`, None when there is none
    ob.tick(now)                          # from the host's clock (the town's raising, in Orkline)

The host is read as `host.town` (its machine, demo, call and toast: Orkline's town, Orkboard's `BoardHost`) and
`host.on_change`.
"""
from __future__ import annotations

import threading
import time
from dataclasses import replace
from typing import Any, Callable
from urllib.parse import urlencode

from orkboard import settings, tools
from orkboard.env import getenv
from orkboard.realm import harnesses, tool_errors, tool_run

TOOLS, WHO, MCP, TOWN, SURVEY, RAISING = "tools", "who", "mcp", "town", "survey", "raising"
RAISE_STEP_S = 0.8          # between two raising steps of the town (gui/onboarding_town.py): each building seen going up
ISSUES = "https://github.com/Orkcraft/orkcraft/issues/new"
RECOMMENDED = ("claude", "codex", "cursor")    # what the step offers to install when no AI tool is here
CHECK_PROMPT = "Reply with the one word: ok"   # Check: a short real request, on the tool's cheapest tier


class OnboardingError(Exception):
    """A step the page sent that cannot be taken; its text is shown to the person."""


def off() -> bool:
    return getenv("ONBOARDING").lower() in ("0", "false", "no", "off")


class Onboarding:
    def __init__(self, host, detect: Callable[[], list[tools.ToolStatus]] | None = None,
                 detect_others: Callable[[], list[tools.Other]] | None = None,
                 ask: Callable[..., Any] | None = None) -> None:
        self.host = host
        self.again = False              # opened from the map's menu on a town that stands (Orkline's Set up again)
        self.step = TOOLS
        self.statuses: list[tools.ToolStatus] | None = None
        self.checks: dict[str, dict] = {}       # Check: a tool's answer to a short request, or why it gave none
        self._ask = ask or (lambda tool, prompt, model=None: tool_run.ask(tool, prompt, model))
        self.others: list[tools.Other] = []
        self.picked: dict[str, settings.ToolChoice] = {}
        self.warder = True
        self._detectors = (detect or (lambda: tools.detect()), detect_others or (lambda: tools.detect_others()))
        self.active = self.wanted()
        if self.active:
            self._look()

    def wanted(self) -> bool:
        """Orkboard opens on it on a machine never set up (Orkline: on a project with no town yet)."""
        town = self.host.town
        return not town.machine.onboarded and not town.demo and not off()

    def _look(self) -> None:
        """The AI tools on a thread (`--version` runs for each)."""
        self._scan()

    def _scan(self) -> None:
        self.statuses = None
        self.checks = {}
        self._finder = threading.Thread(target=self._detect, args=self._detectors, daemon=True)
        self._finder.start()

    # -- what the page sees ------------------------------------------------------------------------

    def _detect(self, detect, detect_others) -> None:
        """The AI tools, on a thread: `--version` runs for each. The page shows them when they are in."""
        try:
            found, others = detect(), detect_others()
        except Exception:                           # a broken tool never stops the onboarding
            found, others = [], []
        self.host.town.call(self._detected, found, others)

    def detect(self, args: dict) -> dict | None:
        """Check again: look for the AI tools once more (one was just installed)."""
        self._live()
        self._scan()
        self.host.on_change()

    def check(self, args: dict) -> dict | None:
        """Check: a short request to one tool found (`harnesses` `ask`, on its cheapest tier), on a thread.
        The row shows ✓ and how long the answer took, or what kind of failure it was (realm/tool_errors.py)."""
        self._live()
        tid = str(args.get("tool") or "")
        if not any(st.id == tid and st.found for st in self.statuses or []):
            raise OnboardingError("That AI tool is not found here")
        if (self.checks.get(tid) or {}).get("state") == "running":
            return self.snapshot()
        self.checks[tid] = {"state": "running"}
        threading.Thread(target=self._check_run, args=(tid,), daemon=True).start()
        self.host.on_change()
        return self.snapshot()

    def _check_run(self, tid: str) -> None:
        start = time.monotonic()
        try:
            self._ask(tid, CHECK_PROMPT, "laborer")
            out = {"state": "ok", "ms": round((time.monotonic() - start) * 1000)}
        except Exception as e:                      # a timeout or 🛑 Halt All is a failure like any other
            err = e if isinstance(e, tool_errors.ToolError) else tool_errors.ToolError(tid, str(e))
            title = harnesses.title(tid)
            out = {"state": "failed", "kind": err.kind, "line": tool_errors.LINES[err.kind].format(tool=title),
                   "action": tool_errors.what_to_do(err), "detail": err.detail or str(err)}
        self.host.town.call(self._checked, tid, out)

    def _checked(self, tid: str, out: dict) -> None:
        if tid in self.checks:                      # not when Check again began a new look meanwhile
            self.checks[tid] = out
            self.host.on_change()

    def _detected(self, found: list[tools.ToolStatus], others: list[tools.Other]) -> None:
        self.statuses, self.others = found, others
        kept = self.host.town.machine.tools if self.again else {}    # set up again: what was chosen stays
        # an experimental tool (agy) is never on by default: the person turns it on after its warning
        self.picked = {st.id: kept.get(st.id) or settings.ToolChoice(
                           enabled=st.found and st.tool.available and not harnesses.risky(st.id), billing=st.billing)
                       for st in found}
        self.host.on_change()

    def steps(self) -> list[str]:
        """The steps of this run, from what is known so far: the first screen alone in Orkboard."""
        return [TOOLS]

    def _tools_rows(self) -> list[dict]:
        rows = []
        for st in self.statuses or []:
            if not st.found:
                continue
            choice = self.picked.get(st.id, settings.ToolChoice())
            h = harnesses.get(st.id)
            rows.append({"id": st.id, "title": st.tool.title, "mark": h.mark if h else "", "version": st.version,
                         "logged_in": st.logged_in, "login": st.tool.login, "enabled": choice.enabled, "billing": choice.billing,
                         "check": self.checks.get(st.id), "risk": harnesses.risky(st.id)})
        return rows

    @staticmethod
    def _recommended() -> list[dict]:
        """What the step offers when no AI tool is here: how to install each and sign in (harnesses.REGISTRY)."""
        out = []
        for tid in RECOMMENDED:
            h = harnesses.get(tid)
            if h is not None:
                out.append({"id": h.id, "title": h.title, "mark": h.mark, "install": h.install, "login": h.login})
        return out

    def _not_run_on(self) -> dict:
        """The tools the orks don't run on here: `missing` (not found), `others` (found, but no harness) and `cli`
        (an app here whose CLI the orks run on is not: Cursor's editor without cursor-agent). A tool found
        is never named again below the table."""
        statuses = self.statuses or []
        found = {st.id for st in statuses if st.found}
        others = [o for o in self.others if o.id not in found]
        cli = {o.id: h for o in others if (h := harnesses.get(o.id))}
        return {"missing": [st.tool.title for st in statuses if not st.found and st.id not in cli],
                "others": [{"id": o.id, "title": o.title} for o in others if o.id not in cli],
                "cli": [{"id": o.id, "title": o.title, "bin": cli[o.id].bin} for o in others if o.id in cli]}

    def snapshot(self) -> dict[str, Any] | None:
        if not self.active:
            return None
        steps = self.steps()
        return {
            "step": self.step, "steps": steps,
            "n": steps.index(self.step) if self.step in steps else len(steps) - 1,
            "tools": {"ready": self.statuses is not None, "rows": self._tools_rows(), **self._not_run_on(),
                      "warder": self.warder, "warder_agy": self._warder_agy(), "recommended": self._recommended()},
            "tool_titles": {t.id: t.title for t in tools.TOOLS},
            "again": self.again,
            "raising": None,
        }

    # -- the page's commands -----------------------------------------------------------------------

    def commands(self) -> dict[str, Callable[[dict], Any]]:
        return {"onboarding.tools": self.set_tools, "onboarding.request": self.request,
                "onboarding.check": self.check, "onboarding.detect": self.detect,
                "onboarding.skip": self.skip, "onboarding.close": self.close, "onboarding.cancel": self.cancel}

    def _warder_agy(self) -> str:
        """What the guard step says about agy when agy is chosen (Orkline's: the Security reviewer guards its town)."""
        return ""

    def _enabled(self) -> list[str]:
        machine = self.host.town.machine
        return [t for t, c in {**machine.tools, **self.picked}.items() if c.enabled]

    def cancel(self, args: dict) -> None:
        """Set up again, left without saving (a first run has no way out but Skip)."""
        if self.again:
            self.active = self.again = False
            self.host.on_change()

    def _live(self) -> None:
        if not self.active or self.step == RAISING:
            raise OnboardingError("The onboarding is not open")

    def _go(self, after: str) -> dict | None:
        """The first screen answered: the tools are saved and the board opens."""
        self._save_machine()
        self.active = False
        self.host.on_change()
        return None

    def set_tools(self, args: dict) -> dict | None:
        """Which tools the orks run on and how each is paid for; whether the Security reviewer guards the project."""
        self._live()
        for tid, c in (args.get("tools") or {}).items():
            if tid in self.picked and isinstance(c, dict):
                billing = c.get("billing") if c.get("billing") in ("subscription", "api") else self.picked[tid].billing
                on = bool(c.get("enabled"))
                if on and harnesses.risky(tid) and not self.picked[tid].enabled and c.get("risk_read") is not True:
                    raise OnboardingError(f"{harnesses.title(tid)} is experimental: read its warning first")
                self.picked[tid] = settings.ToolChoice(enabled=on, billing=billing)
        if isinstance(args.get("warder"), bool):
            self.warder = args["warder"]
        if args.get("next"):
            return self._go(TOOLS)
        self.host.on_change()             # the page draws its rows from the state pushed, not from this reply
        return self.snapshot()

    def request(self, args: dict) -> dict:
        """A tool the orks cannot run on yet: a filled-in GitHub issue for the browser. Nothing is sent from here."""
        name = str(args.get("name") or "").strip()[:80]
        if not name:
            raise OnboardingError("Name the tool")
        link = str(args.get("link") or "").strip()[:300]
        note = str(args.get("note") or "").strip()[:1000]
        body = "\n\n".join(x for x in (f"Tool: {name}", f"Link: {link}" if link else "",
                                       f"What orks would do with it: {note}" if note else "") if x)
        return {"url": f"{ISSUES}?{urlencode({'title': f'Support {name}', 'body': body, 'labels': 'tool request'})}"}

    def skip(self, args: dict) -> dict | None:
        """Open the board: the tools found kept on, saved; nothing else is set up."""
        self._live()
        return self._go(TOOLS)

    def close(self, args: dict) -> None:
        """The first screen leaves the page (Orkline's: once its town stands)."""
        self.active = False
        self.host.on_change()

    def _save_machine(self) -> None:
        town = self.host.town
        m = town.machine
        tools_ = dict(m.tools)
        tools_.update(self.picked)
        town.machine = replace(m, tools=tools_, onboarded=True)
        settings.save(town.machine)

    def tick(self, now: float | None = None) -> None:
        """Nothing goes up in Orkboard (Orkline's raises its town, one step a tick)."""
