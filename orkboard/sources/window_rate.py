"""What 1 % of Claude's five-hour window is worth at API prices (decisions §81): on a subscription the page says a spend as
a share of that window, never in dollars nobody pays.

    window_rate.learn(limits)        # after a read of the limits (core/board_limits.py), on its thread: one more sample
    window_rate.rate()               # {"tool": "claude", "window": "5h", "usd_per_pct": 0.31, "windows": 4}, or None
    window_rate.shown(machine)       # what the page gets: the rate while Claude is on a subscription, else None

A task's share can't be read off the window: Claude says its windows in whole percents, and every session on the machine,
the person's own too, spends the same window. So the share is estimated: the task's ≈$ at API prices over the rate, and
the rate is learnt from the window itself: the API-equivalent $ of every Claude Code session on the machine since the
window began, over the percent it shows used. One sample a window (its latest read, the most percents: the least
rounding), the median of the last WINDOWS. Use outside Claude Code (claude.ai, the desktop app) spends the window and
leaves no transcript here: the rate reads low, and a share high, never low.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import statistics
from pathlib import Path

from orkboard.env import getenv
from orkboard.sources import pricing

TOOL = "claude"
WINDOW_S = 5 * 3600              # Claude's session window: it comes back five hours after it began
MIN_USED_PCT = 5                 # fewer percents than this round too much to learn from
WINDOWS = 12                     # the samples kept: the last windows learnt from
MAX_BYTES = 20 * 1024 * 1024     # of a transcript read (its end: the window is its newest lines)


def file() -> Path:
    """Beside the machine's settings (`~/.config/orkcraft/`): Orkboard's and Orkline's."""
    from orkboard import settings
    return settings.path().parent / "window-rate.json"


def projects_dir() -> Path:
    base = getenv("CLAUDE_HOME") or os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return Path(base or Path.home() / ".claude") / "projects"


def _ts(value: object) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t.timestamp()


def spent_since(start: float, root: Path | None = None) -> float:
    """The API-equivalent $ of every Claude Code message on the machine timestamped at `start` or later (each message
    once: Claude Code repeats a message's usage on each of its lines). Unpriced models count nothing."""
    root = root or projects_dir()
    seen: set[str] = set()
    total = 0.0
    try:
        files = [p for p in root.rglob("*.jsonl") if p.stat().st_mtime >= start]
    except OSError:
        return 0.0
    for path in files:
        try:
            with path.open("rb") as f:
                size = f.seek(0, os.SEEK_END)
                f.seek(max(0, size - MAX_BYTES))
                raw = f.read()
        except OSError:
            continue
        for line in raw.decode("utf-8", "replace").splitlines():
            if '"usage"' not in line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            msg = row.get("message") if isinstance(row, dict) else None
            if not isinstance(msg, dict) or not isinstance(msg.get("usage"), dict):
                continue
            when = _ts(row.get("timestamp"))
            mid = str(msg.get("id") or "")
            if when is None or when < start or (mid and mid in seen):
                continue
            seen.add(mid)
            total += pricing.usage_cost(msg.get("model"), msg["usage"]) or 0.0
    return total


def _session(limits) -> tuple[float, float] | None:
    """(used percent, reset in epoch seconds) of Claude's five-hour window as last read, None when it was not read."""
    for lim in limits or ():
        if getattr(lim, "provider", "") != TOOL or getattr(lim, "window", "") != "session":
            continue
        left, reset = getattr(lim, "remaining", None), getattr(lim, "reset", None)
        if left is None or reset is None:
            continue
        return (1.0 - float(left)) * 100, reset.timestamp() if isinstance(reset, dt.datetime) else float(reset)
    return None


def _load(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = data.get("samples") if isinstance(data, dict) else None
    return [r for r in rows or [] if isinstance(r, dict) and isinstance(r.get("usd_per_pct"), (int, float))
            and r["usd_per_pct"] > 0 and isinstance(r.get("reset"), (int, float))]


def learn(limits, now: float | None = None, root: Path | None = None, path: Path | None = None) -> dict | None:
    """One more sample from the limits just read: the $ spent since the window began over its percent used; the
    window's earlier sample is replaced (more percents, less rounding). The sample, or None when nothing was learnt."""
    got = _session(limits)
    if got is None:
        return None
    used, reset = got
    now = dt.datetime.now().timestamp() if now is None else now
    start = reset - WINDOW_S
    if round(used) < MIN_USED_PCT or not start <= now < reset:
        return None
    usd = spent_since(start, root)
    if usd <= 0:
        return None
    sample = {"reset": round(reset), "used_pct": round(used, 1), "usd": round(usd, 4), "usd_per_pct": round(usd / used, 4)}
    path = path or file()
    kept = [r for r in _load(path) if abs(r["reset"] - reset) > 60] + [sample]
    kept = sorted(kept, key=lambda r: r["reset"])[-WINDOWS:]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"tool": TOOL, "window": "5h", "samples": kept}, indent=1), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        return None
    return sample


_CACHE: dict = {}


def rate(path: Path | None = None) -> dict | None:
    """The rate as learnt: the median $ a percent of the last windows; None before the first window is learnt."""
    path = path or file()
    try:
        key = (str(path), path.stat().st_mtime_ns)
    except OSError:
        return None
    if _CACHE.get("key") != key:
        rows = _load(path)
        _CACHE.update(key=key, rate=None if not rows else {
            "tool": TOOL, "window": "5h", "usd_per_pct": round(statistics.median(r["usd_per_pct"] for r in rows), 4),
            "windows": len(rows)})
    return _CACHE["rate"]


def shown(machine) -> dict | None:
    """The rate the page says spends in: only while Claude is on a subscription (an API key's $ is a bill)."""
    tool = (getattr(machine, "tools", None) or {}).get(TOOL)
    if tool is None or getattr(tool, "billing", "") != "subscription":
        return None
    return rate()
