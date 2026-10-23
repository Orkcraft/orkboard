"""The rate of Claude's five-hour window (decisions §81): what 1 % of it costs at API prices, learnt from the machine's
transcripts and the window's own reads; the page says a subscription's spend in it."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from types import SimpleNamespace

from orkboard.sources import pricing, window_rate
from orkboard.sources.limits import Limit

NOW = dt.datetime(2026, 10, 23, 12, 0).timestamp()
USAGE = {"input_tokens": 1000, "output_tokens": 2000}
ONE = pricing.usage_cost("claude-opus-5-5", USAGE)


def _iso(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _msg(t: float, mid: str) -> str:
    return json.dumps({"type": "assistant", "timestamp": _iso(t),
                       "message": {"id": mid, "model": "claude-opus-5-5", "usage": USAGE}})


def _transcripts(root: Path, *lines: str) -> Path:
    folder = root / "projects" / "-home-me-app"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "s1.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.utime(folder / "s1.jsonl", (NOW, NOW))       # written now, on the tests' clock
    return root / "projects"


def _session(left: float, reset: float) -> list[Limit]:
    return [Limit("claude", "", "session", left, dt.datetime.fromtimestamp(reset)),
            Limit("claude", "", "weekly", 0.5, dt.datetime.fromtimestamp(reset + 3 * 86400))]


def test_spent_since_counts_each_message_once_and_only_inside_the_window(tmp_path):
    root = _transcripts(tmp_path, _msg(NOW - 600, "a"), _msg(NOW - 600, "a"), _msg(NOW - 300, "b"),
                        _msg(NOW - 6 * 3600, "old"), "not json", json.dumps({"type": "user", "timestamp": _iso(NOW)}))
    assert window_rate.spent_since(NOW - 3600, root) == 2 * ONE


def test_learn_divides_the_windows_spend_by_its_percent_and_keeps_one_sample_a_window(tmp_path):
    root = _transcripts(tmp_path, *[_msg(NOW - 60 * i, f"m{i}") for i in range(10)])
    path = tmp_path / "rate.json"
    reset = NOW + 2 * 3600                       # began three hours ago
    got = window_rate.learn(_session(0.8, reset), NOW, root, path)
    assert got["used_pct"] == 20.0 and abs(got["usd_per_pct"] - 10 * ONE / 20) < 1e-4
    window_rate.learn(_session(0.75, reset), NOW, root, path)       # the same window read later: replaced
    samples = json.loads(path.read_text())["samples"]
    assert len(samples) == 1 and samples[0]["used_pct"] == 25.0
    assert window_rate.rate(path)["usd_per_pct"] == round(10 * ONE / 25, 4)


def test_learn_waits_for_enough_percents_and_for_a_spend(tmp_path):
    root = _transcripts(tmp_path, _msg(NOW - 60, "a"))
    path = tmp_path / "rate.json"
    assert window_rate.learn(_session(0.97, NOW + 3600), NOW, root, path) is None          # 3 %: rounds too much
    assert window_rate.learn(_session(0.5, NOW + 3600), NOW, tmp_path / "none", path) is None   # no transcript
    assert window_rate.learn([Limit("limits", "—", "—", None, None, "disabled")], NOW, root, path) is None
    assert window_rate.rate(path) is None


def test_the_rate_is_the_median_of_the_last_windows(tmp_path):
    path = tmp_path / "rate.json"
    rows = [{"reset": 1000 * i, "used_pct": 10, "usd": 1, "usd_per_pct": v} for i, v in enumerate([0.1, 0.5, 0.3])]
    path.write_text(json.dumps({"samples": rows}))
    assert window_rate.rate(path) == {"tool": "claude", "window": "5h", "usd_per_pct": 0.3, "windows": 3}


def test_the_page_gets_the_rate_only_on_a_subscription(tmp_path, monkeypatch):
    path = tmp_path / "rate.json"
    path.write_text(json.dumps({"samples": [{"reset": 1, "usd_per_pct": 0.4}]}))
    monkeypatch.setattr(window_rate, "file", lambda: path)
    sub = SimpleNamespace(tools={"claude": SimpleNamespace(billing="subscription")})
    api = SimpleNamespace(tools={"claude": SimpleNamespace(billing="api")})
    assert window_rate.shown(sub)["usd_per_pct"] == 0.4
    assert window_rate.shown(api) is None and window_rate.shown(SimpleNamespace(tools={})) is None
