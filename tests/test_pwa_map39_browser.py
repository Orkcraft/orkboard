"""Spec 39 part C on the phone (docs/specs/39-map.md §5, "Tests → C"): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py with a fake `ideas.map`. The Board's Map button opens the Map; a goal's ideas in tier order with their
dots, words, pips and *after …*; a row that needs the person first in its tier; a tap opens the idea, logged `via: "map"`;
no horizontal scroll."""
from __future__ import annotations

import json

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _phone, _pick_goal, _shot  # noqa: F401


async def _open_map(page):
    """The Map: it is the Board."""
    await page.locator(".board-tab-pane").wait_for(timeout=WAIT_MS)

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser


def node(slug, title, tier, state, **more):
    return {"slug": slug, "goal": "ship", "title": title, "state": state, "queue": "", "held_until": "", "start_at": "", "priority": "normal",
            "size": "M", "risk": "", "tier": tier, "depends_on": [], "waits_on": [], "waits": None, "needs_you": "",
            "progress": {"done": 0, "total": 0}, "tasks": [], "estimate": None, "by_itself": False, "folded": False,
            "updated": "2026-10-01T10:00:00", **more}


def _tasks(*states):
    return [{"id": f"k{i}", "title": f"Task {i}", "state": s, "after": [], "tier": "warrior",
             "head": {"craft": "engineering", "race": "peon", "tier": "warrior"}} for i, s in enumerate(states, 1)]


# Ordered as the backend gives them: by goal, then tier, then the ones that need the person first.
NODES = [
    node("plan-me", "Draft the pricing page", 1, "plan", needs_you="plan", waits={"kind": "you", "ref": "plan-me", "title": "", "until": ""}),
    node("tables", "Build the tables", 1, "done", progress={"done": 2, "total": 2}, tasks=_tasks("merged", "merged")),
    node("night", "Write the changelog", 1, "raw", queue="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}),
    node("sync", "Sync between phone and town", 2, "working", depends_on=["tables"], checks=[{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "passed"},
                            {"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": True, "why": "", "state": "running"}], progress={"done": 1, "total": 3},
         tasks=_tasks("merged", "running", "waiting")),
    node("old", "Old cleanup", 1, "done", folded=True),
]
MAP = {"goals": [{"slug": "ship", "title": "Ship v1", "priority": "high", "state": "ready", "done_when": ["Tests pass", "Docs read"],
                  "ideas": 5, "done": 2, "usd": 12.4, "team": [{"slug": "product-designer", "name": "Product designer", "head": {"craft": "design", "race": "elf", "tier": "elder"}, "checks": False, "every": False},
                  {"slug": "reviewer", "name": "Reviewer", "head": {"craft": "engineering", "race": "peon", "tier": "elder"}, "checks": True, "every": True}]},
                 {"slug": "docs", "title": "Docs", "priority": "normal", "state": "ready", "done_when": [], "ideas": 0, "done": 0, "usd": None,
                  "verdict": {"met": True, "by": "Growth"}}],
       "nodes": NODES, "edges": [{"from": "tables", "to": "sync"}], "rev": "1"}


ANSWER: dict = {}                                    # what `ideas.map` answers in a test; the full Map by default


@pytest.fixture(autouse=True)
def _map(monkeypatch):
    ANSWER.clear()
    ANSWER.update(MAP)
    real = Stub.commands

    def commands(self):
        def fake(a):
            self.calls.append(("ideas.map", {}))
            return dict(ANSWER)

        def flags(a):
            self.calls.append(("ideas.flags", {}))
            return {"flags": [{"goal": g["slug"], "title": g["title"], "short": g["title"], "by": g["verdict"]["by"], "at": g["verdict"].get("at", ""),
                               "tally": g["verdict"].get("tally")} for g in ANSWER["goals"] if (g.get("verdict") or {}).get("met")]}
        return {**real(self), "ideas.map": fake, "ideas.flags": flags}
    monkeypatch.setattr(Stub, "commands", commands)


@pytest.mark.asyncio
async def test_the_goals_are_tabs_with_how_far_each_is_and_a_goal_is_a_trail_down_to_its_flag(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        goal = page.locator(".map-goal")
        await goal.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "map", "device": "phone"})
        tabs = page.get_by_role("tablist", name="Goals")
        assert [" ".join(t.split()) for t in await tabs.get_by_role("tab").all_inner_texts()] == ["Ship v1 47 %", "Docs met"]   # 2 done of 5 and a third of sync; Docs accepted
        assert await tabs.get_by_role("tab", name="Ship v1").get_attribute("aria-selected") == "true"
        assert await goal.get_attribute("aria-label") == "Ship v1" and "≈$12 so far" in await goal.locator(".map-goal-meta").inner_text()
        start = goal.locator(".trail-start")
        assert "47 %" in await start.inner_text() and "2 of 5 ideas" in await start.inner_text()
        steps = goal.locator(".trail-step")
        assert await steps.count() == 2
        first = [await t.inner_text() for t in await steps.nth(0).locator(".idea-title").all()]
        assert first == ["Draft the pricing page", "Write the changelog"]                      # side by side; the hand first; done not on the trail
        gate = steps.nth(0).locator(".map-row").first
        assert await gate.locator(".trail-mark.is-gate").count() == 1 and "plan ready" in await gate.locator(".map-open").get_attribute("aria-label")   # a gate: ! on its chip
        sync = steps.nth(1).locator('.map-row[data-slug="sync"]')
        assert "working 1/3" in await sync.locator(".map-open").get_attribute("aria-label")
        assert (await sync.locator(".map-open").bounding_box())["height"] <= 48                        # a chip: one line
        tasks = sync.get_by_label("Tasks of Sync between phone and town")
        assert [await t.locator(".map-task-title").inner_text() for t in await tasks.locator(".map-task").all()] == ["Task 2", "Task 3"]
        assert await tasks.locator(".map-task").first.locator("img").count() == 1                      # the head of who does it
        assert "1 done" in await tasks.inner_text()
        assert "The goal" in await goal.locator(".trail-end").inner_text()
        for row in await goal.locator(".trail-step .map-open").all():                         # tap targets of at least 44 px
            assert (await row.bounding_box())["height"] >= 44
        await goal.get_by_text("Done (2)").click()
        await goal.get_by_text("Old cleanup").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)
        await _shot(page, "phone-map-390x844")
        await tabs.get_by_role("tab", name="Docs").click()                                    # another goal: its trail, and the Board's goal
        await page.locator('.map-goal[data-goal="docs"]').wait_for(timeout=WAIT_MS)
        assert "Met · Growth" in await page.locator(".trail-end").inner_text()
        await tabs.get_by_role("tab", name="Ship v1").click()
        await page.locator('.map-goal[data-goal="ship"] .map-row[data-slug="sync"] .map-open').click()
        await page.locator(".screen .sec").first.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "idea", "ref": "sync", "device": "phone", "via": "map"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await page.locator(".map-goal").wait_for(timeout=WAIT_MS)                            # back on the Board: its trails
        assert await page.locator(".board-tab-pane h2").count() == 0                       # no heading on the Board (spec 41 §2)


@pytest.mark.asyncio
async def test_no_project_open_says_open_a_folder_first(fake_repo, monkeypatch):
    ANSWER.clear()
    ANSWER["error"] = "Open a folder first"
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.get_by_text("Open a folder first").wait_for(timeout=WAIT_MS)
        assert await page.locator(".map-goal").count() == 0
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_project_with_no_goal_says_no_goals_yet_with_new_goal(fake_repo, monkeypatch):
    ANSWER.update(goals=[], nodes=[], edges=[])
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.get_by_text("No goals yet.").wait_for(timeout=WAIT_MS)
        await page.locator(".pane").get_by_role("button", name="New goal").last.click()
        await page.get_by_role("dialog", name="New goal").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_phone_map_says_a_goal_s_team_and_an_idea_s_checks(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        team = page.locator('.map-goal[data-goal="ship"] .map-team')
        await team.wait_for(timeout=WAIT_MS)
        assert "Team: Product designer, Reviewer (checks every idea)" in await team.inner_text()
        said = await page.locator('.map-row[data-slug="sync"] .map-open').get_attribute("aria-label")
        assert "checks 1/2" in said
        await _shot(page, "phone-map-team-390x844")
        assert await page.evaluate(NO_SCROLL)


def _short(n, short):
    return {**n, "short": short}


@pytest.mark.asyncio
async def test_a_chip_and_a_tab_show_the_short_name_on_two_lines_with_the_title_in_their_label(fake_repo, monkeypatch):
    ANSWER["goals"] = [{**ANSWER["goals"][0], "short": "Ship"}, *ANSWER["goals"][1:]]
    ANSWER["nodes"] = [_short(NODES[0], "Pricing page"), *NODES[1:3],
                       {**_short(NODES[3], "Sync"), "tasks": [{**t, "short": f"T{t['id']}"} for t in NODES[3]["tasks"]]}, NODES[4]]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        tab = page.get_by_role("tablist", name="Goals").get_by_role("tab").first
        await tab.wait_for(timeout=WAIT_MS)
        assert "Ship" in await tab.inner_text() and "Ship v1" not in await tab.inner_text() and await tab.get_attribute("title") == "Ship v1"
        chip = page.locator('.map-row[data-slug="plan-me"] .map-open')
        assert await chip.locator(".idea-title").inner_text() == "Pricing page" and await chip.get_attribute("title") == "Draft the pricing page"
        assert "Draft the pricing page" in await chip.get_attribute("aria-label")                  # the title is its label
        assert await chip.locator(".idea-title").evaluate("e => getComputedStyle(e).webkitLineClamp") == "2"
        sync = page.locator('.map-row[data-slug="sync"]')
        assert [await t.locator(".map-task-title").inner_text() for t in await sync.locator(".map-task").all()] == ["Tk2", "Tk3"]   # a task on the trail
        assert await sync.locator(".map-task").first.get_attribute("title") == "Task 2 · working"
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_node_that_waits_for_the_person_alone_has_one_button_beside_its_chip(fake_repo, monkeypatch):
    est = {"usd_low": 2.0, "usd_high": 4.0}
    ANSWER["nodes"] = [
        node("start-me", "Offline mode", 1, "plan", needs_you="plan", waits={"kind": "you", "ref": "", "title": "", "until": ""}, estimate=est, tasks=_tasks("waiting", "waiting", "waiting")),
        node("blocked", "Needs the first", 1, "plan", needs_you="plan", waits_on=["start-me"], waits={"kind": "idea", "ref": "start-me", "title": "Offline mode", "until": ""},
             estimate=est, tasks=_tasks("waiting")),
        node("tonight", "Starts tonight", 2, "plan", start_at="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}, tasks=_tasks("waiting")),
        node("raw", "A raw idea", 2, "raw", queue="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}),
        node("held", "Waits for limits", 3, "raw", queue="night", held_until="2026-10-18T18:00:00", waits={"kind": "limits", "ref": "", "title": "", "until": "18:00"}),
        node("asks", "Asks you", 3, "asks", needs_you="asks", waits={"kind": "you", "ref": "", "title": "", "until": ""}),
        node("going", "Going", 4, "working", progress={"done": 1, "total": 2}, tasks=_tasks("merged", "running"))]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        acts = page.locator(".map-act")
        await acts.first.wait_for(timeout=WAIT_MS)
        assert await acts.count() == 3                                                              # the three nodes of the table; none for the rest
        for slug in ("blocked", "held", "asks", "going"):
            assert await page.locator(f'.map-row[data-slug="{slug}"] .map-act').count() == 0, slug  # it waits for something else: its chip says what
        start = page.locator('.map-row[data-slug="start-me"] .map-act')
        assert await start.get_attribute("aria-label") == "Start “Offline mode”: 3 tasks, about $2.0–4.0"
        assert "$2.0–4.0" in await start.inner_text() and await start.locator("use").get_attribute("href") == "icons/icons.svg#play"
        chip = page.locator('.map-row[data-slug="start-me"] .map-open')
        a, b = await chip.bounding_box(), await start.bounding_box()
        assert abs((a["y"] + a["height"] / 2) - (b["y"] + b["height"] / 2)) < 4 and b["x"] > a["x"]       # the same row; a sibling, not inside the chip
        assert await start.evaluate("e => !e.closest('.map-open')") and (await start.bounding_box())["height"] >= 44
        await _shot(page, "phone-map-actions-390x844")
        await start.click()
        assert await _called(stub, "ideas.start", {"slug": "start-me", "via": "map"})
        await page.locator(".flash", has_text="Started.").wait_for(timeout=WAIT_MS)
        now = page.locator('.map-row[data-slug="tonight"] .map-act')
        assert await now.inner_text() == "Start now"
        await now.click()
        assert await _called(stub, "ideas.start_now", {"slug": "tonight", "via": "map"})
        proc = page.locator('.map-row[data-slug="raw"] .map-act')
        assert await proc.inner_text() == "Process now"
        await proc.click()
        assert await _called(stub, "ideas.queue", {"slug": "raw", "queue": "now", "via": "map"})
        assert await page.evaluate(NO_SCROLL)


# -- spec 42 B: the flag raised once, its tally and Flags -------------------------------------------------------------

TALLY = {"ideas": 7, "results": 23, "first_time": 19, "usd": 38.4, "days": 9}


def _met():
    ANSWER["goals"] = [dict(MAP["goals"][0]), {**MAP["goals"][1], "verdict": {"met": True, "by": "Product manager", "at": "2026-10-18T10:00:00", "tally": TALLY}}]


def with_list(repo, slugs):
    key = json.dumps(f"orkboard.flags.{repo.name}")
    return f"if (!localStorage.getItem({key})) localStorage.setItem({key}, {json.dumps(json.dumps(slugs))});"


async def _docs(page):
    await page.get_by_role("tablist", name="Goals").get_by_role("tab", name="Docs").click()
    await page.locator('.map-goal[data-goal="docs"]').wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_a_met_goal_not_in_the_list_is_raised_once_and_its_slug_kept(fake_repo, monkeypatch):
    _met()
    async with _phone(fake_repo, monkeypatch, init=with_list(fake_repo, [])) as (stub, page):
        await _open_map(page)
        await _docs(page)
        await page.locator(".trail-flag.is-raising").wait_for(timeout=WAIT_MS)
        assert await page.locator(".is-raising").count() == 1
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "flag", "ref": "docs", "device": "phone"})
        assert json.loads(await page.evaluate(f"localStorage.getItem({json.dumps('orkboard.flags.' + fake_repo.name)})")) == ["docs"]
        await page.locator(".is-raising").wait_for(state="detached", timeout=WAIT_MS)                            # it moved once
        await page.get_by_role("tablist", name="Goals").get_by_role("tab", name="Ship v1").click()               # drawn again: not raised again
        await _docs(page)
        await page.wait_for_timeout(400)
        assert await page.locator(".is-raising").count() == 0
        assert len([c for c in stub.calls if c[0] == "ideas.log" and c[1].get("what") == "flag"]) == 1


@pytest.mark.asyncio
async def test_under_reduced_motion_nothing_moves_and_a_phone_with_no_list_raises_nothing(fake_repo, monkeypatch):
    _met()
    async with _phone(fake_repo, monkeypatch, init=with_list(fake_repo, [])) as (stub, page):
        await page.emulate_media(reduced_motion="reduce")
        await _open_map(page)
        await _docs(page)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "flag", "ref": "docs", "device": "phone"})
        assert await page.locator(".is-raising").count() == 0
        assert json.loads(await page.evaluate(f"localStorage.getItem({json.dumps('orkboard.flags.' + fake_repo.name)})")) == ["docs"]
    async with _phone(fake_repo, monkeypatch) as (stub, page):                       # no list at all: every met goal is added, none raised
        await _open_map(page)
        await _docs(page)
        await page.wait_for_timeout(400)
        assert await page.locator(".is-raising").count() == 0
        assert json.loads(await page.evaluate(f"localStorage.getItem({json.dumps('orkboard.flags.' + fake_repo.name)})")) == ["docs"]
        assert not [c for c in stub.calls if c[0] == "ideas.log" and c[1].get("what") == "flag"]


@pytest.mark.asyncio
async def test_the_tally_stays_under_the_flag_and_flags_opens_with_its_rows(fake_repo, monkeypatch):
    _met()
    async with _phone(fake_repo, monkeypatch, init=with_list(fake_repo, ["docs"])) as (stub, page):
        await _open_map(page)
        await _docs(page)
        assert " ".join((await page.locator(".trail-tally").inner_text()).split()) == "7 ideas · 23 results · 19 the first time · ≈$38 · 9 days"
        fold = page.locator("details.map-flags")
        assert await fold.locator("summary").inner_text() == "Flags (1)" and await fold.get_attribute("open") is None
        assert not any(c[0] == "ideas.flags" for c in stub.calls)                              # closed at first: not asked for
        await fold.locator("summary").click()
        row = page.locator(".map-flag")
        await row.wait_for(timeout=WAIT_MS)
        assert " ".join((await row.inner_text()).split()) == "Docs met, says Product manager · 18 October 7 ideas · 23 results · 19 the first time · ≈$38 · 9 days"
        assert await page.evaluate(NO_SCROLL)
        await row.click()
        await page.locator(".screen").first.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "idea", "ref": "goal:docs", "device": "phone", "via": "flags"})


@pytest.mark.asyncio
async def test_a_met_goals_row_in_flags_has_the_fold_for_what_its_party_did(fake_repo, monkeypatch):
    from tests.test_pwa_goal_team_browser import PARTY, PARTY_LINES
    _met()
    async with _phone(fake_repo, monkeypatch, init=with_list(fake_repo, ["docs"])) as (stub, page):
        stub.party = PARTY
        await _open_map(page)
        await _docs(page)
        await page.locator("details.map-flags summary").click()
        await page.locator(".map-flag").wait_for(timeout=WAIT_MS)
        fold = page.locator("details.map-flags details.party-work")
        assert await fold.get_attribute("open") is None and not any(c[0] == "ideas.party" for c in stub.calls)
        await fold.locator("summary").click()
        await fold.locator("li").first.wait_for(timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in await fold.locator("li").all_inner_texts()] == PARTY_LINES
        assert await _called(stub, "ideas.party", {"goal": "docs"})
        assert " ".join((await page.locator(".map-flag").inner_text()).split()).startswith("Docs met, says Product manager")
        assert await page.evaluate(NO_SCROLL)
