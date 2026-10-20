"""Operations on the host (docs/specs/38-operations.md §1, §8, §10, §11): one per host, not per project.

    ops = Ops(host)                       # gui/board_host.py `Orkboard` builds it once, beside the projects
    host.commands.update(ops.commands())  # ops.list, ops.add, ops.act, … (the phone may send them all)
    ops.needs()                           # its rows of Needs you, merged into whichever project is shown
    ops.count()                           # … how many count (op, op_failed: not op_rules, as proposals)
    ops.rev                               # the snapshot's `ops_rev`: moves on every `ops.changed`
    ops.tick(now) · ops.stop_all() · ops.close()

The state is the person's (`~/.config/orkcraft/ops/`, realm/op_runs.py), the engine `core/op_runner.py`; this face
checks what the page sends, publishes `ops.changed` on the host's bus, and never needs a project: with none open,
Operations works as with one. Its settings are the machine's `ops` (settings.OPS).
"""
from __future__ import annotations

import re
import subprocess
import time
from typing import Any, Callable

from orkboard import settings
from orkboard.core import op_runner
from orkboard.core.op_commands import OpsError
from orkboard.realm import halt, harnesses, op_runs, op_templates

CHANGED = "ops.changed"            # the bus's topic: id or template
RUNS_SHOWN = 200                   # the newest operations `ops.list` gives (dropped ones are not shown)
SERVERS_S = 60.0                   # `claude mcp list` is read again after this
SERVERS_TIMEOUT_S = 45
STATE_WORDS = {"checks": "checks with you", "alone": "goes by itself", "always": "always checks with you"}


def mcp_names(text: str) -> list[str]:
    """The servers `claude mcp list` prints: `<name>: <command or url> - <status>` a line."""
    out = []
    for line in (text or "").splitlines():
        m = re.match(r"^\s*([^:]{1,100}):\s+\S.*\s-\s", line)
        if m and m.group(1).strip() not in out:
            out.append(m.group(1).strip())
    return out


def _text(args: dict, key: str, most: int = 4000) -> str:
    value = args.get(key, "")
    if not isinstance(value, str):
        raise OpsError(f"{key} is a text")
    return value[:most]


def _device(args: dict) -> str:
    return "phone" if args.get("device") == "phone" else "desktop"


class Ops:
    def __init__(self, host: Any, base=None) -> None:
        self.host = host
        self.base = base or op_runs.root()
        self.rev = 0
        self._servers: tuple[float, list[str]] = (float("-inf"), [])
        self.runner = op_runner.OpRunner(self.base, settings=lambda: self.host.machine.ops,
                                         limits=lambda: self.host.limits(), publish=self._published,
                                         demo=bool(getattr(host, "demo", False)), cap=self._cap(host))
        if not self.runner.demo:
            self.runner.start()

    def _cap(self, host: Any) -> Callable[[], tuple[float, float]] | None:
        """The person's cap across the host's open projects (spec 38 §1); a host with none gives the runner's own."""
        persons_cap = getattr(host, "persons_cap", None)
        return (lambda: persons_cap(op_runs.ledger(self.base))) if callable(persons_cap) else None

    # -- the bus -------------------------------------------------------------------------------------------------

    def _published(self, op: str = "", template: str = "") -> None:
        """From any thread: the change is put on the host's bus on the host's thread."""
        self.host.call(self._changed, op, template)

    def _changed(self, op: str = "", template: str = "") -> None:
        self.rev += 1
        self.host.bus.publish(CHANGED, id=op, template=template)

    # -- what the page sees ----------------------------------------------------------------------------------------

    def _template_row(self, t: op_templates.Template, servers: dict, claude: bool) -> dict:
        row = op_templates.public(t)
        last = op_runs.last_values(self.base, t.name)
        for f in row["fields"]:
            if f.get("remember") and last.get(f["name"]):
                f["default"] = last[f["name"]]
        tr = self.runner.trust(t) if not t.problem else op_runs.fresh_trust()
        state = "always" if t.risk == "high" else ("alone" if tr["alone"] else "checks")
        row.update(state=state, state_words=STATE_WORDS[state], clean=tr["clean"], why=tr.get("why") or "",
                   trust_after=self.runner.ops()["trust_after"], alone_since=tr.get("alone_since") or "", done_alone=tr.get("done_alone") or 0)
        why = op_templates.unusable(t, servers, claude)
        if why:
            row["unusable"] = why
        got = op_runs.proposal(self.base, t.name)
        if got is not None:
            row["proposal"] = got
        return row

    @staticmethod
    def _run_row(run: dict, titles: dict) -> dict:
        return {"id": run["id"], "template": run.get("template", ""), "state": run.get("state", ""),
                "title": titles.get(run.get("template", ""), run.get("template", "")),
                "found": run.get("found") or [], "draft": run.get("draft") or {}, "fields": run.get("fields") or {},
                "doubts": run.get("doubts") or [], "alone": bool(run.get("alone")), "link": run.get("link") or "",
                "why": run.get("why") or "", "acted": run.get("acted", False), "held_until": run.get("held_until") or "",
                "cost": run.get("cost"), "at": run.get("at") or "", "done_at": run.get("done_at") or "",
                "step": run.get("step") or ""}

    def list(self, args: dict | None = None) -> dict:
        found = self.runner.templates()
        servers, claude = self.runner.ops()["servers"], self.runner.claude()
        templates = [self._template_row(t, servers, claude) for t in found.values()]
        titles = {t.name: t.title for t in found.values()}
        runs = [self._run_row(r, titles) for r in op_runs.runs(self.base) if r.get("state") != "dropped"]
        needed: dict[str, str] = {}
        for t in found.values():
            needed.update({k: v for k, v in t.servers.items() if k not in needed})
        return {"templates": templates, "runs": runs[-RUNS_SHOWN:], "settings": self.runner.ops(),
                "servers_needed": needed}

    def needs(self) -> list[dict]:
        """Operations' rows of Needs you (§8): at the check, failed, and a rules proposal (last: it blocks nothing)."""
        found = self.runner.templates()
        out = []
        for run in op_runs.runs(self.base):
            t = found.get(run.get("template", ""))
            title = t.title if t else run.get("template", "")
            base = {"op": run["id"], "template": run.get("template", ""), "title": title, "priority": "normal",
                    "blocks": False, "at": run.get("at") or ""}
            if run.get("state") == "check":
                draft = run.get("draft") or {}
                first = draft.get(t.draft[0]["name"], "") if t is not None and t.draft else next(iter(draft.values()), "")
                out.append({**base, "kind": "op", "text": " ".join(str(first).split())[:200] or title,
                            "why": run.get("why") or ""})
            elif run.get("state") == "failed":
                out.append({**base, "kind": "op_failed", "text": run.get("why") or "It failed",
                            "acted": run.get("acted", False)})
        for t in found.values():
            got = op_runs.proposal(self.base, t.name)
            if got is not None:
                out.append({"kind": "op_rules", "template": t.name, "title": t.title, "op": got.get("op", ""),
                            "text": got["lines"][0], "lines": list(got["lines"]), "priority": "normal",
                            "blocks": False, "at": got.get("at") or ""})
        return out

    def count(self) -> int:
        return sum(1 for n in self.needs() if n["kind"] != "op_rules")

    # -- the commands (§11) ----------------------------------------------------------------------------------------

    def commands(self) -> dict[str, Callable[[dict], Any]]:
        return {"ops.list": self.list, "ops.add": self._add, "ops.prepare": self._prepare, "ops.act": self._act,
                "ops.drop": self._drop, "ops.stop": self._stop, "ops.retry": self._retry, "ops.again": self._again,
                "ops.not_right": self._not_right, "ops.rules": self._rules, "ops.rules_save": self._rules_save,
                "ops.rules_answer": self._rules_answer, "ops.trust_reset": self._trust_reset,
                "ops.servers": self._servers_cmd, "ops.set": self._set}

    def _add(self, args: dict) -> dict:
        return {"id": self.runner.add(_text(args, "template", 80), args.get("fields") or {}, _device(args))}

    def _prepare(self, args: dict) -> dict:
        self.runner.prepare_again(_text(args, "id", 80), args.get("fields"), args.get("draft"), _device(args))
        return {"ok": True}

    def _act(self, args: dict) -> dict:
        self.runner.act(_text(args, "id", 80), args.get("fields"), args.get("draft"), _device(args))
        return {"ok": True}

    def _drop(self, args: dict) -> dict:
        self.runner.drop(_text(args, "id", 80))
        return {"ok": True}

    def _stop(self, args: dict) -> dict:
        self.runner.stop(_text(args, "id", 80))
        return {"ok": True}

    def _retry(self, args: dict) -> dict:
        self.runner.retry(_text(args, "id", 80))
        return {"ok": True}

    def _again(self, args: dict) -> dict:
        return {"id": self.runner.again(_text(args, "id", 80), _device(args))}

    def _not_right(self, args: dict) -> dict:
        self.runner.not_right(_text(args, "id", 80), _text(args, "why", 300) if "why" in args else "")
        return {"ok": True}

    def _rules(self, args: dict) -> dict:
        t = self.runner.template(_text(args, "template", 80))
        return {"text": op_runs.rules(self.base, t.name)}

    def _rules_save(self, args: dict) -> dict:
        t = self.runner.template(_text(args, "template", 80))
        text = args.get("text", "")
        if not isinstance(text, str):
            raise OpsError("The rules are a text")
        if len(text) > op_runs.RULES_CHARS:
            raise OpsError(f"The rules are longer than {op_runs.RULES_CHARS} characters")
        op_runs.save_rules(self.base, t.name, text)
        self._published(template=t.name)
        return {"ok": True}

    def _rules_answer(self, args: dict) -> dict:
        take = args.get("take")
        if not isinstance(take, bool):
            raise OpsError("take is true or false")
        self.runner.rules_answer(_text(args, "template", 80), take, _text(args, "reason", 300) if "reason" in args else "")
        return {"ok": True}

    def _trust_reset(self, args: dict) -> dict:
        self.runner.trust_reset(_text(args, "template", 80))
        return {"ok": True}

    def _servers_cmd(self, args: dict) -> dict:
        return {"servers": self.servers()}

    def servers(self) -> list[str]:
        """The MCP servers `claude mcp list` prints on this machine (read when the gear opens, kept a minute)."""
        at, names = self._servers
        if time.monotonic() - at < SERVERS_S:
            return list(names)
        h = harnesses.get(op_runner.HARNESS)
        if h is None or not self.runner.claude():
            return []
        try:
            proc = halt.run([h.bin, "mcp", "list"], timeout=SERVERS_TIMEOUT_S, who="claude mcp list",
                            cwd=str(op_runs._private_dir(self.base / "work")))
        except (OSError, subprocess.SubprocessError, halt.Halted):
            return list(names)
        names = mcp_names(proc.stdout)
        self._servers = (time.monotonic(), names)
        return list(names)

    def _set(self, args: dict) -> dict:
        mine = dict(self.host.machine.ops)
        for key in ("target", "trust_after", "daily_alone", "servers"):
            if key not in args:
                continue
            want = args[key]
            if key == "servers" and isinstance(want, dict):      # a key named with "" is forgotten
                want = {k: v for k, v in {**mine.get("servers", {}), **want}.items() if v != ""}
            got = settings.clean_ops({**mine, key: want})[key]
            if got != want:
                raise OpsError({"target": "The Target is thrift, balance or quality",
                                "trust_after": "Goes by itself after 1 to 5 clean checks",
                                "daily_alone": "By itself at most 1 to 100 a day",
                                "servers": "A server is a template's key and a server's name"}[key])
            mine[key] = got
        self.host.machine.ops = settings.clean_ops(mine)
        if not getattr(self.host, "demo", False):
            settings.save(self.host.machine)
        self._published()
        return self.runner.ops()

    # -- the clock ---------------------------------------------------------------------------------------------------

    def tick(self, now: float | None = None) -> None:
        if not self.runner.demo:
            self.runner.tick(now)

    def stop_all(self) -> int:
        return self.runner.stop_all()

    def close(self) -> None:
        self.runner.stop_all()
