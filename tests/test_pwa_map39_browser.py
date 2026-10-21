"""Spec 48 part C on the phone (docs/specs/48-map-ideas.md §3–§7, "Tests → C"): Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py with a fake `ideas.map`. The Map is one goal (the top bar's): its header, its party line, its ideas in trail
order, one open at a time (the idea's card, its waves rising bottom-up, its lanes, its stacks), the rest one line, Done (n) folded.
Yellow only on a stop; a merged task leaves once; the card merges, sends back and drops. No horizontal scroll."""
from __future__ import annotations

import json

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _phone, _pick_goal, _shot  # noqa: F401


async def _open_map(page):
    """The Map: it is the Board."""
    await page.locator(".board-tab-pane").wait_for(timeout=WAIT_MS)

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

HEAD = {"craft": "engineering", "race": "peon", "tier": "warrior"}
ELF = {"craft": "design", "race": "elf", "tier": "elder"}
GRUNT = {"slug": "grunt", "name": "Grunts"}
DESIGNER = {"slug": "product-designer", "name": "Product designer"}
REVIEWER = {"slug": "reviewer", "name": "Reviewer"}


def node(slug, title, tier, state, **more):
    return {"slug": slug, "goal": "ship", "title": title, "state": state, "queue": "", "held_until": "", "start_at": "", "priority": "normal",
            "size": "M", "risk": "", "tier": tier, "depends_on": [], "waits_on": [], "waits": None, "needs_you": "",
            "progress": {"done": 0, "total": 0}, "tasks": [], "estimate": None, "by_itself": False, "folded": False,
            "updated": "2026-10-01T10:00:00", "stage": "planning", "round": 1, "usd": None, "plan_estimate": None, "asked": [], "results": [], **more}


def task(tid, state, by=GRUNT, wave=1, band="build", after=(), **more):
    return {"id": tid, "title": f"Task {tid}", "state": state, "after": list(after), "tier": "warrior", "head": ELF if by is DESIGNER else HEAD,
            "by": by, "band": band, "wave": wave, **more}


def result(tid, **more):
    return {"idea": "sync", "idea_title": "Sync between phone and town", "task": tid, "title": f"Task {tid}", "round": 1,
            "tests": {"passed": 20, "failed": 0, "failing": [], "tail": ""}, "diff": {"files": 14, "added": 3, "removed": 1}, "cost": 0.42,
            "conflict": "", "finished": "2026-10-20T10:00:00", "estimate": None, "over": False, **more}


SYNC_TASKS = [task("k1", "review", GRUNT, 1), task("k2", "running", GRUNT, 1), task("k3", "waiting", DESIGNER, 2, after=["k1"]), task("k0", "merged", GRUNT, 1)]

# Ordered as the backend gives them: tiers, then the Board's order.
NODES = [
    node("plan-me", "Draft the pricing page", 1, "plan", needs_you="plan", waits={"kind": "you", "ref": "plan-me", "title": "", "until": ""},
         tasks=[task("p1", "waiting", GRUNT), task("p2", "waiting", REVIEWER, 2, "check")], estimate={"usd_low": 2.0, "usd_high": 4.0}, plan_estimate={"usd_low": 2.0, "usd_high": 4.0}),
    node("tables", "Build the tables", 1, "done", stage="done", progress={"done": 2, "total": 2}, tasks=[task("t1", "merged"), task("t2", "merged")]),
    node("night", "Write the changelog", 1, "raw", queue="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}),
    node("sync", "Sync between phone and town", 2, "working", stage="implementation", depends_on=["tables"],
         checks=[{"by": "reviewer", "name": "Reviewer", "applies": True, "why": "", "state": "passed"},
                 {"by": "accessibility-reviewer", "name": "Accessibility reviewer", "applies": True, "why": "", "state": "running"}],
         progress={"done": 1, "total": 4}, tasks=SYNC_TASKS, results=[result("k1")], usd=0.84, plan_estimate={"usd_low": 1.0, "usd_high": 2.0}),
    node("old", "Old cleanup", 1, "done", stage="done", folded=True),
]
PARTY = [{"slug": "taskmaster", "name": "Taskmaster", "head": HEAD, "band": "lead", "state": "needs", "why": "plan"},
         {"slug": "grunt", "name": "Grunts", "head": HEAD, "band": "build", "state": "work", "why": ""},
         {"slug": "product-designer", "name": "Product designer", "head": ELF, "band": "build", "state": "next", "why": ""},
         {"slug": "reviewer", "name": "Reviewer", "head": HEAD, "band": "check", "state": "free", "why": ""}]
LEADER = {"slug": "taskmaster", "name": "Taskmaster", "head": HEAD}
MAP = {"goals": [{"slug": "ship", "title": "Ship v1", "priority": "high", "state": "ready", "done_when": ["Tests pass", "Docs read"],
                  "ideas": 5, "done": 2, "usd": 12.4, "leader": LEADER, "party": PARTY, "today": {"merged": 1, "usd": 0.42},
                  "team": [{"slug": "product-designer", "name": "Product designer", "head": ELF, "checks": False, "every": False},
                           {"slug": "reviewer", "name": "Reviewer", "head": HEAD, "checks": True, "every": True}]},
                 {"slug": "docs", "title": "Docs", "priority": "normal", "state": "ready", "done_when": [], "ideas": 0, "done": 0, "usd": None,
                  "leader": LEADER, "party": [], "today": {"merged": 0, "usd": 0}, "verdict": {"met": True, "by": "Growth"}}],
       "nodes": NODES, "edges": [{"from": "tables", "to": "sync"}], "rev": "1"}


ANSWER: dict = {}                                    # what `ideas.map` answers in a test; the full Map by default


@pytest.fixture(autouse=True)
def _map(monkeypatch):
    ANSWER.clear()
    ANSWER.update(json.loads(json.dumps(MAP)))
    real, init = Stub.commands, Stub.__init__

    def commands(self):
        def fake(a):
            self.calls.append(("ideas.map", {}))
            return dict(ANSWER)

        def flags(a):
            self.calls.append(("ideas.flags", {}))
            return {"flags": [{"goal": g["slug"], "title": g["title"], "short": g["title"], "by": g["verdict"]["by"], "at": g["verdict"].get("at", ""),
                               "tally": g["verdict"].get("tally")} for g in ANSWER["goals"] if (g.get("verdict") or {}).get("met")]}

        def merge(a):                                  # the host merges: the task is merged, its result is gone
            a = {k: v for k, v in a.items() if k not in ("device", "link")}
            self.calls.append(("ideas.merge", a))
            sync = next(n for n in ANSWER["nodes"] if n["slug"] == "sync")
            for t in sync["tasks"]:
                if t["id"] == a["task"]:
                    t["state"] = "merged"
            sync["results"] = [r for r in sync["results"] if r["task"] != a["task"]]
            self.rev += 1
            return {"ok": True, "commit": "abc"}
        return {**real(self), "ideas.map": fake, "ideas.flags": flags, "ideas.merge": merge}

    def new_init(self):
        init(self)
        self.goals["ship"] = Stub.goal("ship", "Ship v1", "high", "ready")
        self.goals["docs"] = Stub.goal("docs", "Docs", "normal", "ready")
    monkeypatch.setattr(Stub, "commands", commands)
    monkeypatch.setattr(Stub, "__init__", new_init)


async def _open(page, slug):
    """Open an idea in place by a tap on its row (the accordion: the one open closes)."""
    await page.locator(f'.map-row[data-slug="{slug}"] .map-open').first.click()
    await page.locator(f'.map-idea[data-slug="{slug}"]').wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_a_goal_s_page_has_its_header_its_party_line_and_its_ideas_one_open_at_a_time(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        goal = page.locator(".map-goal")
        await goal.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "map", "device": "phone"})
        assert await page.get_by_role("tablist", name="Goals").count() == 0                       # one goal: the top bar's pick, no tabs
        assert await goal.get_attribute("aria-label") == "Ship v1"
        meta = await goal.locator(".map-goal-meta").inner_text()
        assert "≈$12 so far" in meta and "today 1 merged · ≈$0.42" in meta
        start = " ".join((await goal.locator(".trail-start").inner_text()).split())
        assert "45 %" in start and "2 of 5 ideas done" in start
        assert "Tests pass" in await goal.locator(".map-done-when summary").inner_text()
        party = goal.get_by_label("Party", exact=True)
        assert [" ".join(t.split()) for t in await party.locator("li").all_inner_texts()] == [
            "Taskmaster plan ready", "Grunts at work ↻", "Product designer next", "Reviewer free"]
        assert await party.locator(".map-member.is-stop").count() == 1 and await party.locator(".is-stop").get_attribute("data-member") == "taskmaster"
        # the first idea that waits for the person is open; the rest are one line each (stage · state words)
        assert await page.locator(".map-idea").count() == 1 and await page.locator(".map-idea").get_attribute("data-slug") == "plan-me"
        rows = page.locator(".map-ideas-list > .map-row")
        assert await rows.count() == 2                                                           # sync and the changelog; the done ones are folded
        said = await page.locator('.map-row[data-slug="sync"] .map-open').get_attribute("aria-label")
        assert said.startswith("Sync between phone and town: Implementation · working 1/4")
        assert "Planning · tonight" in await page.locator('.map-row[data-slug="night"] .map-open').get_attribute("aria-label")
        for btn in await page.locator(".map-ideas-list .map-open, .map-card-frame button").all():
            if await btn.is_visible():
                assert (await btn.bounding_box())["height"] >= 43
        done = goal.locator("details.done-ideas")
        await done.locator("summary").click()
        assert await done.locator("summary").inner_text() == "Done (2)"
        assert "in dev · waits for main" in await done.locator('.map-row[data-slug="old"]').inner_text()
        assert "3 of 3" not in await done.inner_text() and "2 of 2 tasks in dev" in await done.locator('.map-row[data-slug="tables"]').inner_text()
        assert await page.evaluate(NO_SCROLL)
        await _open(page, "sync")                                                                 # the accordion: sync opens, the plan's idea closes
        assert await page.locator(".map-idea").count() == 1 and await page.locator('.map-row[data-slug="plan-me"] .map-open').first.get_attribute("aria-expanded") == "false"
        await _shot(page, "phone-map-390x844")
        await page.locator('.map-idea[data-slug="sync"] .map-card-title').click()                 # a tap on its title closes it
        assert await page.locator(".map-idea").count() == 0
        await _open(page, "sync")
        await page.locator('.map-idea[data-slug="sync"] .map-view').click()
        await page.locator(".screen .sec").first.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "idea", "ref": "sync", "device": "phone", "via": "map"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await page.locator(".map-goal").wait_for(timeout=WAIT_MS)
        assert await page.locator(".board-tab-pane h2").count() == 0                              # no heading on the Board (spec 41 §2)


@pytest.mark.asyncio
async def test_a_plan_waiting_has_start_the_work_and_open_the_plan_on_its_card(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        idea = page.locator('.map-idea[data-slug="plan-me"]')
        await idea.wait_for(timeout=WAIT_MS)
        assert [await b.inner_text() for b in await idea.locator(".map-card-acts button").all()] == ["Start the work", "Open the plan"]
        assert await idea.locator('[data-act="start"]').get_attribute("aria-label") == "Start the work of “Draft the pricing page”: 2 tasks, about $2.00–4.00"
        track = idea.locator(".stage-track")
        assert await track.locator(".stage.is-now").text_content() == "Planning"
        assert "plan ≈$2.00–4.00" in await idea.locator(".map-pips-line").inner_text()
        plan_card = idea.locator(".map-field .map-tcard")                                         # the leader's lane, one column: the plan
        assert await plan_card.count() == 1 and "plan ready" in await plan_card.inner_text() and "is-stop" in await plan_card.get_attribute("class")
        assert await idea.locator(".map-members .map-member").count() == 1                        # only the leader is active in Planning
        await idea.locator('[data-act="start"]').click()
        assert await _called(stub, "ideas.start", {"slug": "plan-me", "via": "map"})
        await page.locator(".flash", has_text="Started.").wait_for(timeout=WAIT_MS)
        await idea.get_by_role("button", name="Open the plan").click()
        await page.locator(".screen").first.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.page", {"slug": "plan-me"})


@pytest.mark.asyncio
async def test_implementation_has_its_track_lanes_waves_rising_stacks_and_results_on_the_card(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await _open(page, "sync")
        idea = page.locator('.map-idea[data-slug="sync"]')
        stages = idea.locator(".stage-track .stage")
        assert [await s.get_attribute("class") for s in await stages.all()] == ["stage is-past", "stage is-now", "stage"]
        assert await idea.locator(".stage.is-now").get_attribute("aria-current") == "step"
        pips = " ".join((await idea.locator(".map-pips-line").inner_text()).split())
        assert "1 of 4 tasks in dev" in pips and "≈$0.84 so far" in pips and "plan ≈$1.00–2.00" in pips
        # the waves rise bottom-up: Wave 2 above Wave 1 above the members' row, the DOM in the same order
        labels = [await e.text_content() for e in await idea.locator(".map-wave-label").all()]
        assert labels == ["Wave 2", "Wave 1"]
        w2, w1, members = [await idea.locator(sel).first.bounding_box() for sel in ('[data-wave="Wave 2"]', '[data-wave="Wave 1"]', ".map-members")]
        assert w2["y"] < w1["y"] < members["y"]
        # lanes: the builders with tasks left, in the order they first appear
        names = [await e.inner_text() for e in await idea.locator(".map-members .map-member b").all()]
        assert names == ["Grunts", "Product designer"]
        # a merged task is not on the field; two tasks of Grunts in wave 1 are a stack with a count of 2
        assert await idea.locator('.map-tcard[data-task="k0"]').count() == 0
        stack = idea.locator('[data-wave="Wave 1"] .map-stack.is-stack')
        assert await stack.locator(".stack-count").inner_text() == "2" and "2 tasks of Grunts in wave 1" in await stack.locator(".map-tcard").get_attribute("aria-label")
        await stack.locator(".map-tcard").click()
        sheet = page.get_by_role("dialog", name="Grunts · wave 1 · 2")
        await sheet.wait_for(timeout=WAIT_MS)
        assert [await b.locator(".stack-title").inner_text() for b in await sheet.locator(".stack-row").all()] == ["Task k1", "Task k2"]
        assert (await sheet.locator(".stack-row").first.bounding_box())["height"] >= 43
        await sheet.locator(".stack-row").nth(1).click()
        assert await _called(stub, "ideas.task", {"slug": "sync", "task": "k2"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await page.locator('.map-idea[data-slug="sync"]').wait_for(timeout=WAIT_MS)
        # a waiting task is dashed with its words; a result in Review is muted ink, never yellow (decisions §54.1)
        wait = idea.locator('.map-tcard[data-task="k3"]')
        assert "is-wait" in await wait.get_attribute("class") and "waiting" in await wait.inner_text()
        assert await idea.locator(".is-stop").count() == 0 and await idea.locator(".map-tcard.is-fail").count() == 0
        looks = idea.locator(".map-looks")
        assert await looks.locator("h4").text_content() == "Waits for your look"
        assert "Task k1" in await looks.inner_text() and "20 / 20 passed" in await looks.inner_text() and "14 files" in await looks.inner_text()
        assert [await b.inner_text() for b in await looks.locator(".result-actions button").all()][:2] == ["Merge into dev", "Send back"] and \
            await looks.get_by_role("button", name="Drop…").count() == 1
        assert await page.evaluate(NO_SCROLL)
        await looks.get_by_role("button", name="Send back").click()
        await looks.locator("input.ork-field").fill("Cover the empty queue")
        await looks.locator("form.back-line button[type=submit]").click()
        assert await _called(stub, "ideas.back", {"slug": "sync", "task": "k1", "why": "Cover the empty queue"})
        await looks.get_by_role("button", name="Drop…").click()
        await page.get_by_role("dialog", name="Drop this result?").get_by_role("button", name="Drop it").click()
        assert await _called(stub, "ideas.drop_task", {"slug": "sync", "task": "k1"})


@pytest.mark.asyncio
async def test_a_merged_task_leaves_the_field_once_and_none_under_reduced_motion(fake_repo, monkeypatch):
    for reduced in (False, True):
        ANSWER.clear()
        ANSWER.update(json.loads(json.dumps(MAP)))
        async with _phone(fake_repo, monkeypatch) as (stub, page):
            if reduced:
                await page.emulate_media(reduced_motion="reduce")
            await _open_map(page)
            await _open(page, "sync")
            idea = page.locator('.map-idea[data-slug="sync"]')
            assert await idea.locator(".card-out").count() == 0                                   # none on the first read
            await idea.get_by_role("button", name="Merge into dev").click()
            assert await _called(stub, "ideas.merge", {"slug": "sync", "task": "k1"})
            await idea.locator('.map-looks').get_by_text("Nothing waits for your look.").wait_for(timeout=WAIT_MS)
            if reduced:
                await page.wait_for_timeout(300)
                assert await idea.locator(".card-out").count() == 0                              # nothing moves
            else:
                await idea.locator(".card-out").wait_for(timeout=WAIT_MS)                         # it leaves from where it was
                assert "in dev" in await idea.locator(".card-out").inner_text() and await idea.locator(".card-out").get_attribute("aria-hidden") == "true"
                await idea.locator(".card-out").wait_for(state="detached", timeout=6000)          # once
            assert await idea.locator('.map-tcard[data-task="k1"]:not(.is-out)').count() == 0
            assert "2 of 4 tasks in dev" in " ".join((await idea.locator(".map-pips-line").inner_text()).split())


@pytest.mark.asyncio
async def test_yellow_is_only_on_the_agent_the_work_stopped_on(fake_repo, monkeypatch):
    asked = node("asker", "Which store first", 1, "asks", needs_you="asks", waits={"kind": "you", "ref": "", "title": "", "until": ""},
                 asked=[{"ask": "iPhone or Android?", "choices": [], "by": {"slug": "product-designer", "name": "Product designer", "head": ELF}}])
    broken = node("broken", "Fails to build", 2, "working", stage="implementation", needs_you="failed", waits={"kind": "you", "ref": "", "title": "", "until": ""},
                  tasks=[task("f1", "failed", DESIGNER, 1), task("f2", "review", GRUNT, 1)], progress={"done": 0, "total": 2})
    ANSWER["nodes"] = [asked, broken]
    ANSWER["goals"][0]["party"] = [{**PARTY[0], "state": "needs", "why": "asks"}, PARTY[1], {**PARTY[2], "state": "needs", "why": "failed"}, PARTY[3]]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        q = page.locator('.map-idea[data-slug="asker"]')
        await q.wait_for(timeout=WAIT_MS)
        card = q.locator(".map-tcard.is-ask")
        assert "iPhone or Android?" in await card.inner_text() and "is-stop" in await card.get_attribute("class") and await card.locator("img").count() == 1   # the asker's head
        assert await q.locator(".map-members .is-stop").count() == 1                              # the leader, who holds the question
        await _open(page, "broken")
        b = page.locator('.map-idea[data-slug="broken"]')
        assert "is-fail" in await b.locator('.map-tcard[data-task="f1"]').get_attribute("class")
        stops = [await e.get_attribute("data-member") for e in await b.locator(".map-members .is-stop").all()]
        assert stops == ["product-designer"]                                                      # the agent of the failed task, not the one whose result waits
        review = b.locator('.map-tcard[data-task="f2"]')
        assert "is-review" in await review.get_attribute("class") and "in Review" in await review.inner_text()
        assert await review.evaluate("e => getComputedStyle(e.querySelector('.tcard-state')).color") != await b.locator(".map-members .is-stop").evaluate("e => getComputedStyle(e).color")


@pytest.mark.asyncio
async def test_checking_has_the_checkers_lanes_and_a_second_round(fake_repo, monkeypatch):
    chk = node("chk", "Checks of sync", 1, "working", stage="checking", round=2, progress={"done": 2, "total": 3},
               tasks=[task("c0", "merged"), task("c1", "running", REVIEWER, 1, "check"), task("c2", "waiting", REVIEWER, 2, "check")])
    ANSWER["nodes"] = [chk]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        idea = page.locator('.map-idea[data-slug="chk"]')
        await idea.wait_for(timeout=WAIT_MS)
        assert await idea.locator(".stage.is-now").text_content() == "Checking · round 2"
        assert [await s.get_attribute("class") for s in await idea.locator(".stage-track .stage").all()] == ["stage is-past", "stage is-past", "stage is-now"]
        assert [await e.inner_text() for e in await idea.locator(".map-members .map-member b").all()] == ["Reviewer"]
        assert await idea.locator('.map-tcard[data-task="c0"]').count() == 0
        assert await idea.get_by_label("Wave 2", exact=True).count() == 1


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


def _short(n, short):
    return {**n, "short": short}


@pytest.mark.asyncio
async def test_a_row_shows_the_short_name_on_two_lines_with_the_title_in_its_label(fake_repo, monkeypatch):
    ANSWER["nodes"] = [_short(NODES[2], "Changelog"), NODES[3]]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        chip = page.locator('.map-row[data-slug="night"] .map-open')
        await chip.wait_for(timeout=WAIT_MS)
        assert await chip.locator(".idea-title").inner_text() == "Changelog" and await chip.get_attribute("title") == "Write the changelog"
        assert "Write the changelog" in await chip.get_attribute("aria-label")                       # the title is its label
        assert await chip.locator(".idea-title").evaluate("e => getComputedStyle(e).webkitLineClamp") == "2"
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_row_that_waits_for_the_person_alone_has_one_button_beside_it(fake_repo, monkeypatch):
    ANSWER["nodes"] = [
        node("tonight", "Starts tonight", 1, "plan", start_at="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}, tasks=[task("w1", "waiting")]),
        node("raw", "A raw idea", 2, "raw", queue="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}),
        node("held", "Waits for limits", 3, "raw", queue="night", held_until="2026-10-18T18:00:00", waits={"kind": "limits", "ref": "", "title": "", "until": "18:00"})]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        acts = page.locator(".map-act")
        await acts.first.wait_for(timeout=WAIT_MS)
        assert await acts.count() == 2 and await page.locator('.map-row[data-slug="held"] .map-act').count() == 0   # it waits for something else
        now = page.locator('.map-row[data-slug="tonight"] .map-act')
        assert await now.inner_text() == "Start now" and (await now.bounding_box())["height"] >= 43
        chip = page.locator('.map-row[data-slug="tonight"] .map-open')
        a, b = await chip.bounding_box(), await now.bounding_box()
        assert abs((a["y"] + a["height"] / 2) - (b["y"] + b["height"] / 2)) < 4 and await now.evaluate("e => !e.closest('.map-open')")
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
    await _pick_goal(page, "docs")
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
        await _pick_goal(page, "ship")               # drawn again: not raised again
        await _docs(page)
        await page.wait_for_timeout(400)
        assert await page.locator(".is-raising").count() == 0
        assert len([c for c in stub.calls if c[0] == "ideas.log" and c[1].get("what") == "flag"]) == 1


FAR = "{ const sheet = new CSSStyleSheet(); sheet.replaceSync('.trail-end { margin-top: 3000px }'); document.adoptedStyleSheets = [sheet]; }"      # a constructed sheet: the phone's CSP has no inline style


@pytest.mark.asyncio
async def test_a_flag_whose_trail_is_out_of_sight_waits_and_is_raised_once_when_it_comes_into_view(fake_repo, monkeypatch):
    _met()
    flag_logs = lambda stub: [c for c in stub.calls if c[0] == "ideas.log" and c[1].get("what") == "flag"]      # noqa: E731
    async with _phone(fake_repo, monkeypatch, init=with_list(fake_repo, []) + FAR) as (stub, page):
        await _open_map(page)
        await _docs(page)
        for _ in range(3):                                                           # the section is drawn again, each time with its listener
            await _pick_goal(page, "ship")
            await _docs(page)
        await page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        await page.wait_for_timeout(400)
        assert await page.locator(".is-raising").count() == 0 and not flag_logs(stub)
        await page.locator(".trail-flag").scroll_into_view_if_needed()
        await page.locator(".trail-flag.is-raising").wait_for(timeout=WAIT_MS)
        await page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        await page.wait_for_timeout(400)
        assert len(flag_logs(stub)) == 1


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
async def test_a_met_goal_s_row_in_flags_has_what_the_party_did_closed_at_first(fake_repo, monkeypatch):
    """Spec 43 B: the same fold under a flag's row."""
    from tests.test_shell_browser import PARTY, PARTY_LINES
    _met()
    async with _phone(fake_repo, monkeypatch, init=with_list(fake_repo, ["docs"])) as (stub, page):
        stub.party = PARTY
        await _open_map(page)
        await _docs(page)
        await page.locator("details.map-flags summary").click()
        await page.locator(".map-flag").wait_for(timeout=WAIT_MS)
        fold = page.locator(".map-flags-list .party-work")
        assert await fold.get_attribute("open") is None and not any(c[0] == "ideas.party" for c in stub.calls)
        await fold.locator("summary").click()
        await page.wait_for_function("() => document.querySelectorAll('.map-flags-list .party-work li').length === 4", timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in await fold.locator("li").all_inner_texts()] == PARTY_LINES
        assert await _called(stub, "ideas.party", {"goal": "docs"})
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "party", "ref": "docs", "device": "phone"})
        assert await page.evaluate(NO_SCROLL)
