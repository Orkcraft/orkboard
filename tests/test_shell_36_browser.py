"""Spec 36 part B on the desktop (docs/specs/36-agents-spend.md §5), in a real browser at 1 440 × 900 against the shell's stub
host with part A's new fields: Agents as a monitor (no Task types, a role's week, needs-you chips first), the agent's dialog
(the model list, the counter, Takes) and the result preview's idea line. Screenshots to docs/design/img/v1/ when
ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import os

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import SHOTS, StubHost, _open, box  # noqa: E402

pytestmark = pytest.mark.browser

MODELS = [{"id": "", "label": "By Target"}, {"id": "elder", "label": "Elder · opus"}, {"id": "warrior", "label": "Warrior · sonnet"},
          {"id": "laborer", "label": "Laborer · haiku"}]
WEEK = {"grunt": {"spent": 7.2, "merged": 8, "first_time": 6, "finished": 10, "usd_per_merged": 0.9},
        "taskmaster": {"spent": 1.1, "plans": 4, "first_time": 8, "finished": 10, "merged": 9},
        "scribe": {"spent": 0.3, "merged": 2, "first_time": 2, "finished": 2, "usd_per_merged": None}}
SPEND = {"usd": 3.1, "unpriced": 0, "tasks": {}, "stages": {"goal": {"usd": 0.4, "tokens": 1, "calls": 1}, "spec": {"usd": 0.5, "tokens": 1, "calls": 2},
         "plan": {"usd": 0.2, "tokens": 1, "calls": 1}, "work": {"usd": 1.5, "tokens": 1, "calls": 3}, "rework": {"usd": 0.5, "tokens": 1, "calls": 1},
         "dropped": {"usd": 0.0, "tokens": 0, "calls": 0}}}


class Stub36(StubHost):
    """Part A's shapes: roles with `week`, `kinds`, `hand_model`; the model list; `ideas.spend`; `kinds` on role_save."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.week = dict(WEEK)
        self.spend = SPEND
        self.roles["scribe"] = {"slug": "scribe", "name": "Scribe", "model": "opus", "max_parallel": 2, "instruction": "x" * 650, "builtin": False}
        self.kinds["docs"] = "scribe"

    def handle(self, name, a):
        if name == "ideas.roles":
            return {"roles": [r | {"spend_today": 0, "week": self.week.get(r["slug"]), "hand_model": r["model"] not in ("", "elder", "warrior", "laborer"), "record": self.record.get(r["slug"]),
                                   "kinds": [k for k, v in self.kinds.items() if v == r["slug"]],
                                   **({"check_week": self.check_week[r["slug"]]} if r["slug"] in self.check_week else {})} for r in self.roles.values()],
                    "kinds": self.kind_list(), "models": MODELS}
        if name == "ideas.agents":
            got = super().handle(name, a)
            got["roles"][1]["chips"] += [dict(idea="dark", idea_title="Dark mode", task="d2", title="Wire the toggle", state="testing", tier="warrior", note="", by="person", night=False),
                                         dict(idea="dark", idea_title="Dark mode", task="d3", title="Pick the palette", state="failed", tier="warrior", note="", by="person", night=False)]
            for b in got["roles"]:
                b["week"] = self.week.get(b["role"])
                if b["role"] in self.check_week:
                    b["check_week"] = self.check_week[b["role"]]
                if b["role"] != "taskmaster":
                    b["kinds"] = [k for k, v in self.kinds.items() if v == b["role"]]
            got["roles"] += [{"role": r["slug"], "name": r["name"], "model": r["model"], "max_parallel": r["max_parallel"], "builtin": False,
                              "spend_today": 0, "week": self.week.get(r["slug"]), "chips": [], "kinds": ["docs"]}
                             for r in self.roles.values() if r["slug"] == "scribe" and not any(b["role"] == "scribe" for b in got["roles"])]
            return got
        if name == "ideas.spend":
            self.log.append((name, a))
            return self.spend
        if name == "ideas.role_save":
            got = super().handle(name, a)
            slug = got["slug"]
            if "kinds" in a:
                self.kinds = {k: ("grunt" if v == slug and k not in a["kinds"] else v) for k, v in self.kinds.items()}
                self.kinds |= {k: slug for k in a["kinds"]}
            return got
        return super().handle(name, a)


@pytest.fixture
def shell36(gui):
    pg, host, errors = _open(gui, host=Stub36())
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def test_agents_has_no_task_types_and_a_role_is_one_line_with_what_a_task_costs(shell36):
    pg, host = shell36
    host.usd_task = {"grunt": 0.9}
    host.bump({})
    agents = pg.locator(".shell-agents")
    assert "task types" not in agents.inner_text().lower() and agents.get_by_label("Agent for Docs").count() == 0
    assert agents.get_by_role("button", name="+ Add agent").is_visible()
    line = agents.locator(".shell-role[data-slug='grunt'] .shell-role__head")
    pg.wait_for_function("() => document.querySelector(\".shell-role[data-slug='grunt'] .shell-role__head\")?.getAttribute('aria-label')?.includes('$0.90')", timeout=WAIT_MS)
    assert " ".join(line.inner_text().split()).startswith("Grunts ×8 ≈ $0.90 a task Edit")            # spec 41 §8: no model in words
    assert line.locator(".shell-role__week").inner_text() == "≈$1.25 today · ≈$0.90 a result · 6/10 the first time"   # its day and week, muted under the line
    assert line.locator("[title='At API prices, not your bill']").count() == 2
    scribe = agents.locator(".shell-role[data-slug='scribe']")
    assert "a result" not in scribe.inner_text() and "first time" not in scribe.inner_text()                # two merged: too few to say
    assert "Takes: docs" in scribe.inner_text() and "Does:" not in agents.inner_text()
    assert "Takes: code, tests" in agents.locator(".shell-role[data-slug='grunt']").inner_text()
    tm = agents.locator(".shell-role[data-role='taskmaster'] .shell-role__head").inner_text()          # its cost is its steps: its week stays
    assert "8/10 tasks the first time" in tm and "×" not in tm
    if os.environ.get("ORKCRAFT_SHOTS"):
        handle = box(pg, ".shell-split")
        pg.mouse.move(handle["x"] + 40, handle["y"] + 2)
        pg.mouse.down()
        pg.mouse.move(handle["x"] + 40, handle["y"] - 200, steps=5)
        pg.mouse.up()
        pg.screenshot(path=str(SHOTS / "desktop-agents-monitor-1440x900.png"))


def test_the_taskmaster_with_none_finished_says_no_week(shell36):
    pg, host = shell36
    pg.locator(".shell-role[data-role=taskmaster] .shell-role__week").wait_for(timeout=WAIT_MS)       # with tasks finished, it is there
    host.week = {"taskmaster": {"spent": 0, "plans": 0, "first_time": 0, "finished": 0, "merged": 0}}
    host.bump({})
    pg.wait_for_function("() => !document.querySelector('.shell-role[data-role=taskmaster] .shell-role__week')", timeout=WAIT_MS)
    assert "first time" not in pg.locator(".shell-agents").inner_text()


def test_needs_you_chips_come_first_then_working_testing_queued_held_at_review(shell36):
    pg, host = shell36
    chips = pg.locator(".shell-role[data-slug='grunt'] ul.shell-chips:not(details *) .shell-chip")
    pg.wait_for_function("() => document.querySelectorAll('.shell-role[data-slug=grunt] .shell-chip[data-state]').length >= 8", timeout=WAIT_MS)
    states = [chips.nth(i).get_attribute("data-state") for i in range(chips.count())]
    order = ["failed", "running", "testing", "ready", "held", "review"]
    assert states == sorted(states, key=order.index) and states[0] == "failed" and states[-1] == "review", states
    assert {"failed", "running", "testing", "ready", "held", "review"} <= set(states)
    assert "needs you" in chips.first.inner_text().lower()


def test_the_dialog_lists_by_target_and_the_tiers_counts_the_instruction_and_moves_a_type_from_grunt(shell36):
    pg, host = shell36
    pg.get_by_role("button", name="+ Add agent").click()
    pg.get_by_role("dialog", name="Add an agent").get_by_role("button", name="Your own").click()
    dlg = pg.get_by_role("dialog", name="Add agent")
    assert dlg.get_by_label("Model").input_value() == ""                                              # a new agent is By Target
    labels = dlg.get_by_label("Model").locator("option").all_inner_texts()
    assert labels == ["By Target", "Elder · opus", "Warrior · sonnet", "Laborer · haiku"]
    assert "By Target: the task's own tier, moved by the Target" in dlg.inner_text()
    assert dlg.get_by_test_id("instruction-count").inner_text() == "0 / 600"
    dlg.get_by_label("Instruction").fill("Write plainly.")
    assert dlg.get_by_test_id("instruction-count").inner_text() == "14 / 600"
    rows = dlg.locator(".shell-takes__row")
    assert rows.count() == 5 and "now Grunt" in rows.nth(0).inner_text()
    dlg.get_by_label("Name").fill("Reader")
    dlg.get_by_label("Research").check()
    dlg.get_by_role("button", name="Save agent").click()
    pg.locator(".shell-role[data-slug='reader']").wait_for(timeout=WAIT_MS)
    saved = next(a for n, a in host.log if n == "ideas.role_save")
    assert saved == {"name": "Reader", "model": "", "max_parallel": 2, "instruction": "Write plainly.", "kinds": ["research"], "craft": "engineering"}
    pg.get_by_role("button", name="Edit Grunts").click()                                              # Grunt's block no longer says research
    grunt = pg.get_by_role("dialog", name="Edit agent")
    grunt.get_by_label("Name").wait_for(timeout=WAIT_MS)
    assert grunt.get_by_label("Research").is_disabled() and not grunt.get_by_label("Research").is_checked()
    assert grunt.get_by_label("Code").is_checked() and "Grunt takes what no other agent takes" in grunt.inner_text()
    assert "now Reader" in grunt.locator(".shell-takes__row", has_text="Research").inner_text()
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.screenshot(path=str(SHOTS / "desktop-agent-dialog-grunt-1440x900.png"))


def test_an_instruction_over_600_says_so_and_cannot_be_saved_and_a_hand_set_model_stays_an_option_and_the_taskmaster_takes_nothing(shell36):
    pg, host = shell36
    pg.get_by_role("button", name="Edit Scribe").click()
    dlg = pg.get_by_role("dialog", name="Edit agent")
    dlg.get_by_label("Name").wait_for(timeout=WAIT_MS)
    assert dlg.get_by_test_id("instruction-count").inner_text() == "650 / 600"
    assert "Only the first 600 characters go to the ork: shorten it" in dlg.inner_text()
    assert dlg.get_by_role("button", name="Save agent").is_disabled()
    assert dlg.get_by_label("Model").input_value() == "opus"
    assert "opus (set by hand)" in dlg.get_by_label("Model").locator("option").all_inner_texts()
    assert dlg.get_by_label("Docs").is_checked()
    dlg.get_by_label("Instruction").fill("Short.")
    assert dlg.get_by_role("button", name="Save agent").is_enabled()
    dlg.get_by_role("button", name="Cancel").click()
    pg.get_by_role("button", name="Edit Taskmaster").click()
    tm = pg.get_by_role("dialog", name="Edit agent")
    tm.get_by_label("Name").wait_for(timeout=WAIT_MS)
    assert tm.locator(".shell-takes").count() == 0 and "By Target" not in tm.get_by_label("Model").locator("option").all_inner_texts()


def test_the_result_preview_says_what_the_idea_cost_so_far_and_dashes_when_nothing_is_priced(shell36):
    pg, host = shell36
    pg.locator(".shell-card", has_text="Add the queue").click()
    line = pg.locator(".shell-spend")
    line.wait_for(timeout=WAIT_MS)
    assert line.inner_text() == "This idea so far: ≈$3.10 — goal 0.40 · spec 0.50 · plan 0.20 · work 1.50 · rework 0.50"   # dropped at 0 left out
    assert any(n == "ideas.spend" and a == {"idea": "sync"} for n, a in host.log)
    if os.environ.get("ORKCRAFT_SHOTS"):
        pg.screenshot(path=str(SHOTS / "desktop-result-spend-1440x900.png"))
    pg.keyboard.press("Escape")
    host.spend = {"usd": None, "unpriced": 3, "tasks": {}, "stages": {k: {"usd": None, "tokens": 1, "calls": 1} for k in ("goal", "spec", "plan")}}
    pg.locator(".shell-card", has_text="Add the queue").click()
    pg.wait_for_function("() => document.querySelector('.shell-spend')?.textContent === 'This idea so far: —'", timeout=WAIT_MS)
