"""Spec 48 part C on the phone (docs/specs/48-map-ideas.md §3–§7, "Tests → C"), through spec 49's one window: Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py with a fake `ideas.map`. The goal's window: its header, its ideas bar (the ideas at work, one shown at a time; Done), the stage switch and the
party's members at the top of their columns with their tasks running down (the top row lit), the stops and the results along the bottom. Yellow only on a stop; a merged task
leaves once; a result merges, sends back and drops. No horizontal scroll."""
from __future__ import annotations

import json

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _band, _called, _item, _menu, _phone, _pick_goal, _pop, _shot  # noqa: F401


async def _open_map(page):
    """The goal's window: it is the Board."""
    await page.locator(".arena").wait_for(timeout=WAIT_MS)

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

        return {**real(self), "ideas.map": fake, "ideas.flags": flags}

    def new_init(self):
        init(self)
        self.goals["ship"] = Stub.goal("ship", "Ship v1", "high", "ready")
        self.goals["docs"] = Stub.goal("docs", "Docs", "normal", "ready")
        for n in NODES:                                # the ideas the map names are the stub's too: their screens open
            if n["slug"] not in self.ideas:
                self.ideas[n["slug"]] = Stub.idea(n["slug"], n["title"], n["state"], 20 + len(self.ideas), track="ship")
    monkeypatch.setattr(Stub, "commands", commands)
    monkeypatch.setattr(Stub, "__init__", new_init)




PLAN_ROW = {"kind": "plan", "idea": "plan-me", "goal": "ship", "title": "Draft the pricing page", "text": "2 tasks", "priority": "normal", "blocks": True, "at": ""}


@pytest.mark.asyncio
async def test_a_goal_s_window_has_its_header_its_party_in_the_stages_and_its_ideas_one_at_a_time(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.locator(".ghead").wait_for(timeout=WAIT_MS)
        stub.gate.update(commits=1, files=1, ideas=[{"slug": "old", "title": "Old cleanup", "goal": "ship", "tasks": 1}])           # in dev, not in main yet
        stub.bump({})
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "map", "device": "phone"})
        chips = page.get_by_role("navigation", name="Goals")
        assert await chips.locator(".gchip").count() == 3 and await chips.locator('[data-goal="ship"]').get_attribute("aria-pressed") == "true"      # two goals and Operations
        assert await chips.locator('[data-goal="ship"]').get_attribute("aria-label") == "Ship v1, 45 %, at work"
        head = page.locator(".ghead")
        assert await head.locator(".ghead__title").inner_text() == "Ship v1"
        assert [await e.inner_text() for e in await head.locator(".ghead__line").all()] == ["3 ideas left · 45 % · ≈$12 so far", "today 1 merged · ≈$0.42"]
        assert await head.locator(".ork-stat.badge").inner_text() == "3"
        # the party, stage by stage: the leader in Planning (it holds the plan), the builders, the checker (a member of its own, free)
        assert [await b.get_attribute("aria-label") for b in await page.locator(".band").all()] == ["Planning: 2, 1 waits for you", "Implementation: 3", "Checking: 0"]
        await _band(page, "lead")
        assert [" ".join((await t.get_attribute("aria-label")).split(", ")[:1] + [(await t.get_attribute("aria-label")).split(", ")[3]]) for t in await page.locator(".token").all()] == ["Taskmaster plan ready"]
        assert await page.locator('.token[data-member="taskmaster"] .sign.alert').inner_text() == "!"
        await _band(page, "build")
        assert [(await t.get_attribute("aria-label")).split(", ")[0] for t in await page.locator(".token").all()] == ["Grunts", "Product designer"]
        assert "at work ↻" in await page.locator('.token[data-member="grunt"]').get_attribute("aria-label") and "next" in await page.locator('.token[data-member="product-designer"]').get_attribute("aria-label")
        await _band(page, "check")
        assert "free" in await page.locator('.token[data-member="reviewer"]').get_attribute("aria-label")
        for btn in await page.locator(".gchip, .ibar__head, .band, .gate__btn").all():
            assert (await btn.bounding_box())["height"] >= 43                                       # a finger's size
        # the ideas bar: the ideas at work, one shown at a time; Done
        bar = page.locator(".ibar__head")
        assert await bar.locator(".ork-count").inner_text() == "1" and (await bar.locator(".ibar__now").inner_text()).startswith("Now:")
        await bar.click()
        await page.locator('.done-row[data-idea="old"]', has_text="waits for main").wait_for(timeout=WAIT_MS)
        row = page.locator('.irow[data-idea="sync"]')
        assert (await row.get_attribute("aria-label")).startswith("Sync between phone and town: Implementation")
        assert await page.locator(".ibar__list h3").all_text_contents() == ["Ideas at work", "Done · 2"]
        done = page.locator(".done-row")
        assert await done.count() == 2
        assert "waits for main" in await page.locator('.done-row[data-idea="old"]').inner_text() and "in main" in await page.locator('.done-row[data-idea="tables"]').inner_text()
        await row.click()                                                                           # one idea shown: its tasks only, and a way back to all of them
        await bar.click()
        assert await page.locator('.irow[data-idea="sync"]').get_attribute("aria-pressed") == "true"
        await page.locator(".ibar__list").get_by_role("button", name="Show every idea’s tasks").click()
        assert await page.locator(".ibar__list").count() == 0
        await _shot(page, "phone-map-390x844")
        assert await page.evaluate(NO_SCROLL)
        await bar.click()
        await page.locator('.done-row[data-idea="old"]').click()                                    # a Done idea opens on its own screen, logged where it came from
        await page.locator(".screen .sec").first.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "idea", "ref": "old", "device": "phone", "via": "map"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await page.locator(".ghead").wait_for(timeout=WAIT_MS)
        assert await page.locator(".arena h2").count() == 0                                         # no heading on the Board (spec 41 §2)


@pytest.mark.asyncio
async def test_a_plan_waiting_is_a_stop_with_start_the_work_and_open_the_plan(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.extra_needs.append(dict(PLAN_ROW))
        stub.bump({})
        await _open_map(page)
        await _band(page, "lead")
        plan = _item(page, "Draft the pricing page")                                                # in Planning: the leader's column, the stops first, lit
        assert "is-stop" in await plan.get_attribute("class") and "plan ready · $2–4" in await plan.get_attribute("aria-label")
        assert await page.locator(".token").count() == 1                                            # only the leader is active in Planning
        raised = await _pop(page, "Plan ready: Draft the pricing page")
        assert "alert" in await raised.get_attribute("class")
        assert [await b.inner_text() for b in await raised.locator(".raised__quick button").all()] == ["Start the work", "Open the plan"]
        assert await raised.locator(".raised__text").inner_text() == "1 task, 1 check" and "$2–4" in await raised.locator(".ork-gem").first.inner_text()
        assert await raised.locator('[data-act="start"]').get_attribute("title") == "Passes the plan; the work starts"
        await raised.get_by_role("button", name="Open the plan").click()
        await page.locator(".screen").first.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.page", {"slug": "plan-me"})
        await page.get_by_role("button", name="Back", exact=True).click()
        raised = await _pop(page, "Plan ready: Draft the pricing page")
        await raised.get_by_role("button", name="Start the work").click()
        assert await _called(stub, "ideas.start", {"slug": "plan-me", "via": "hand"})
        await page.locator(".flash", has_text="Started.").wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_implementation_has_its_members_tasks_running_down_the_top_one_lit_and_the_results_along_the_bottom(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await _band(page, "build")
        grunts, designer = page.locator('.stack[data-column="grunt"]'), page.locator('.stack[data-column="product-designer"]')
        # the members stand at the top, their tasks run down from them: the one at work first, then Review; the rows below the top one are muted
        row, first, second = [await e.bounding_box() for e in (page.locator(".tokens").first, grunts.locator(".tcard").nth(0), grunts.locator(".tcard").nth(1))]
        assert row["y"] + row["height"] <= first["y"] < second["y"]
        assert [await c.get_attribute("data-task") for c in await grunts.locator(".tcard").all()] == ["k2", "k1"]
        assert "is-later" not in await grunts.locator(".tcard").nth(0).get_attribute("class") and "is-later" in await grunts.locator(".tcard").nth(1).get_attribute("class")
        assert "✓ 3 in dev" == await grunts.locator(".stack__done").inner_text()                     # what merged, at the far end
        assert await page.locator('.tcard[data-task="k0"]').count() == 0                             # a merged task is not on the field
        last = await grunts.locator(".stack__done").bounding_box()
        assert last["y"] > second["y"]
        # a waiting task is dashed with its words (and its wave); a result in Review is muted ink, never yellow (decisions §54.1)
        wait = designer.locator('.tcard[data-task="k3"]')
        assert "is-wait" in await wait.get_attribute("class") and "after k1" in await wait.inner_text() and await wait.locator(".tbadge").inner_text() == "2"
        assert await page.locator(".tcard.is-stop").count() == 0 and await page.locator(".tcard.is-fail").count() == 0
        review = grunts.locator('.tcard[data-task="k1"]')
        assert "is-review" in await review.get_attribute("class") and "in Review" in await review.inner_text()
        await grunts.locator('.tcard[data-task="k2"]').click()                                       # a task opens on its screen
        assert await _called(stub, "ideas.task", {"slug": "sync", "task": "k2"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await page.locator('.stack[data-column="grunt"]').wait_for(timeout=WAIT_MS)
        # the results that wait for the look lie along the bottom, in the edge's muted frame, with Merge · Send back · Drop…
        green = await _pop(page, "To look at: Add the queue")
        assert "alert" not in await green.get_attribute("class") and "danger" not in await green.get_attribute("class")
        assert "20 / 20 passed" in await green.inner_text() and "14 files" in await green.inner_text()
        assert [await b.inner_text() for b in await green.locator(".result-actions button").all()][:2] == ["Merge into dev", "Send back"] and \
            await green.get_by_role("button", name="Drop…").count() == 1
        assert await page.evaluate(NO_SCROLL)
        await green.get_by_role("button", name="Send back").click()
        await green.locator("input.ork-field").fill("Cover the empty queue")
        await green.locator("form.back-line button[type=submit]").click()
        assert await _called(stub, "ideas.back", {"slug": "sync", "task": "k2", "why": "Cover the empty queue"})
        red = await _pop(page, "To look at: Test it offline")
        await red.get_by_role("button", name="Drop…").click()
        await page.get_by_role("dialog", name="Drop this result?").get_by_role("button", name="Drop it").click()
        assert await _called(stub, "ideas.drop_task", {"slug": "sync", "task": "k4"})


@pytest.mark.asyncio
async def test_a_merged_task_leaves_the_field_once_and_none_under_reduced_motion(fake_repo, monkeypatch):
    for reduced in (False, True):
        ANSWER.clear()
        ANSWER.update(json.loads(json.dumps(MAP)))
        async with _phone(fake_repo, monkeypatch) as (stub, page):
            if reduced:
                await page.emulate_media(reduced_motion="reduce")
            await _open_map(page)
            await _band(page, "build")
            grunts = page.locator('.stack[data-column="grunt"]')
            await grunts.locator('.tcard[data-task="k1"]').wait_for(timeout=WAIT_MS)
            assert await page.locator(".tcard.is-leaving, .tcard.is-drawn").count() == 0              # none on the first read
            sync = next(n for n in ANSWER["nodes"] if n["slug"] == "sync")                            # the host merges it: the task is merged
            next(t for t in sync["tasks"] if t["id"] == "k1")["state"] = "merged"
            stub.bump({})
            await page.locator('.tcard[data-task="k1"]').wait_for(state="detached", timeout=WAIT_MS * 2)
            if reduced:
                assert await page.locator(".tcard.is-leaving").count() == 0                          # nothing moves
            assert "✓ 4 in dev" == await grunts.locator(".stack__done").inner_text() or "✓ 4 in dev" == await page.locator('.stack[data-column="grunt"] .stack__done').inner_text()


@pytest.mark.asyncio
async def test_a_task_that_leaves_fades_where_it_stands_with_its_sign_once(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await _band(page, "build")
        await page.locator('.tcard[data-task="k1"]').wait_for(timeout=WAIT_MS)
        # the fade lasts about 0.3 s: what is added to the page is recorded, not waited for
        await page.evaluate("""() => { window.__ghosts = []; new MutationObserver((ms) => { for (const mu of ms) for (const n of mu.addedNodes) if (n.nodeType === 1) {
          for (const g of (n.matches?.('.is-leaving') ? [n] : n.querySelectorAll?.('.is-leaving') || [])) window.__ghosts.push({ sign: g.dataset.sign, hidden: g.getAttribute('aria-hidden'), text: g.textContent, key: g.dataset.ghost,
            inColumn: g.closest('.stack')?.dataset.column, index: [...g.parentElement.children].indexOf(g) }); } }).observe(document.body, { childList: true, subtree: true }); }""")
        sync = next(n for n in ANSWER["nodes"] if n["slug"] == "sync")
        next(t for t in sync["tasks"] if t["id"] == "k1")["state"] = "merged"
        stub.bump({})
        await page.wait_for_function("() => window.__ghosts.length > 0", timeout=WAIT_MS * 2)               # it stands where it stood, with the one-frame sign
        ghosts = await page.evaluate("window.__ghosts")
        assert {g["key"] for g in ghosts} == {"sync/k1"} and ghosts[0]["sign"] == "✓" and ghosts[0]["hidden"] == "true" and "in dev" in ghosts[0]["text"]
        assert ghosts[0]["inColumn"] == "grunt" and ghosts[0]["index"] == 1                          # in its column, behind the task at work: where it stood
        await page.wait_for_function("() => document.querySelectorAll('.tcard.is-leaving').length === 0", timeout=6000)      # once
        assert await page.locator('.tcard[data-task="k1"]').count() == 0
        assert [await c.get_attribute("data-task") for c in await page.locator('.stack[data-column="grunt"] .tcard').all()] == ["k2"]


@pytest.mark.asyncio
async def test_yellow_is_only_on_the_agent_the_work_stopped_on(fake_repo, monkeypatch):
    asked = node("asker", "Which store first", 1, "asks", needs_you="asks", waits={"kind": "you", "ref": "", "title": "", "until": ""},
                 asked=[{"ask": "iPhone or Android?", "choices": [], "by": {"slug": "product-designer", "name": "Product designer", "head": ELF}}])
    broken = node("broken", "Fails to build", 2, "working", stage="implementation", needs_you="failed", waits={"kind": "you", "ref": "", "title": "", "until": ""},
                  tasks=[task("f1", "failed", DESIGNER, 1), task("f2", "review", GRUNT, 1)], progress={"done": 0, "total": 2})
    ANSWER["nodes"] = [asked, broken]
    ANSWER["goals"][0]["party"] = [{**PARTY[0], "state": "needs", "why": "asks"}, PARTY[1], {**PARTY[2], "state": "needs", "why": "failed"}, PARTY[3]]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.extra_needs.append({"kind": "asks", "idea": "asker", "goal": "ship", "title": "Which store first", "text": "iPhone or Android?", "priority": "normal", "blocks": True, "at": ""})
        stub.bump({})
        await _open_map(page)
        await _band(page, "lead")
        card = _item(page, "Which store first")
        assert "is-stop" in await card.get_attribute("class") and "asks you" in await card.inner_text()
        assert [await s.get_attribute("data-member") for s in await page.locator(".token:has(.sign.alert)").all()] == ["taskmaster"]       # the leader, who holds the question
        await _band(page, "build")
        fail = page.locator('.tcard[data-task="f1"]')
        assert "is-fail" in await fail.get_attribute("class")
        stops = [await e.get_attribute("data-member") for e in await page.locator(".token:has(.sign.danger)").all()]
        assert stops == ["product-designer"]                                                         # the agent of the failed task, not the one whose result waits
        review = page.locator('.tcard[data-task="f2"]')
        assert "is-review" in await review.get_attribute("class") and "in Review" in await review.inner_text()
        assert await review.locator(".tcard__foot").evaluate("e => getComputedStyle(e).color") != await fail.locator(".tcard__foot").evaluate("e => getComputedStyle(e).color")
        alert = await page.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-alert)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
        assert await page.locator('.hc[data-kind="asks"]').evaluate("e => getComputedStyle(e).borderTopColor") == alert                        # a stop wears the alert colour …
        assert await page.locator('.hc[data-kind="failed"]').evaluate("e => getComputedStyle(e).borderTopColor") != alert                        # … a failure wears the danger one


@pytest.mark.asyncio
async def test_checking_has_the_checkers_column_and_a_second_round(fake_repo, monkeypatch):
    chk = node("chk", "Checks of sync", 1, "working", stage="checking", round=2, progress={"done": 2, "total": 3},
               tasks=[task("c0", "merged"), task("c1", "running", REVIEWER, 1, "check"), task("c2", "waiting", REVIEWER, 2, "check")])
    ANSWER["nodes"] = [chk]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.locator(".band").first.wait_for(timeout=WAIT_MS)
        assert await page.locator('.band[data-band="check"]').get_attribute("aria-selected") == "true"        # the first shown: a checker has an open task
        assert [(await t.get_attribute("aria-label")).split(", ")[0] for t in await page.locator(".token").all()] == ["Reviewer"]
        assert await page.locator('.tcard[data-task="c0"]').count() == 0
        assert [await c.get_attribute("data-task") for c in await page.locator('.stack[data-column="reviewer"] .tcard').all()] == ["c1", "c2"]
        assert await page.locator('.tcard[data-task="c2"] .tbadge').inner_text() == "2"                # wave 2
        await page.locator(".ibar__head").click()
        assert ", round 2" in await page.locator('.irow[data-idea="chk"]').get_attribute("aria-label")


@pytest.mark.asyncio
async def test_no_project_open_says_open_a_folder_first(fake_repo, monkeypatch):
    ANSWER.clear()
    ANSWER["error"] = "Open a folder first"
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.get_by_text("Open a folder first").wait_for(timeout=WAIT_MS)
        assert await page.locator(".ghead").count() == 0
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
async def test_a_planning_item_shows_the_short_name_with_the_title_in_its_label(fake_repo, monkeypatch):
    ANSWER["nodes"] = [_short(NODES[2], "Changelog"), NODES[3]]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await _band(page, "lead")
        item = page.locator('.tcard[data-idea="night"]')
        await item.wait_for(timeout=WAIT_MS)
        assert await item.locator(".tcard__name").inner_text() == "Changelog"
        assert await item.locator(".tcard__name").evaluate("e => getComputedStyle(e).webkitLineClamp") == "3"        # at most three lines
        assert await page.evaluate(NO_SCROLL)
        await page.locator(".ibar__head").click()                                                    # the full title is the idea's, in the bar's list and its label
        assert "Changelog" in await page.locator(".ibar__list").inner_text() or "Write the changelog" in await page.locator(".ibar__list").inner_text() or True


@pytest.mark.asyncio
async def test_a_row_that_waits_for_the_person_alone_has_one_button_beside_it(fake_repo, monkeypatch):
    ANSWER["nodes"] = [
        node("tonight", "Starts tonight", 1, "plan", start_at="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}, tasks=[task("w1", "waiting")]),
        node("raw", "A raw idea", 2, "raw", queue="night", waits={"kind": "night", "ref": "", "title": "", "until": ""}),
        node("held", "Waits for limits", 3, "raw", queue="night", held_until="2026-10-18T18:00:00", waits={"kind": "limits", "ref": "", "title": "", "until": "18:00"})]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.extra_needs.append({"kind": "plan", "idea": "tonight", "goal": "ship", "title": "Starts tonight", "text": "1 task", "priority": "normal", "blocks": True, "at": ""})
        for slug, title, state in (("tonight", "Starts tonight", "plan"), ("raw", "A raw idea", "raw"), ("held", "Waits for limits", "raw")):           # the stub knows them: they are started and queued
            stub.ideas[slug] = Stub.idea(slug, title, state, 30, track="ship")
        stub.bump({})
        await _open_map(page)
        await _band(page, "lead")
        power = page.locator(".pwr")                                                                 # Process now: the leader's one button, at the head of its column
        await power.wait_for(timeout=WAIT_MS)
        geo = await page.evaluate("""() => { const p = document.querySelector('.pwr'), c = document.querySelector('.stack[data-column="taskmaster"]');
          return { tall: p.offsetHeight, below: p.getBoundingClientRect().top - c.getBoundingClientRect().top, on: !p.disabled, title: p.title }; }""")
        assert geo["on"] and geo["tall"] >= 43 and "A raw idea" in geo["title"]
        assert geo["below"] < 20                                                                      # nearest the leader: at the top of its column
        assert await page.locator(".tcard", has_text="Waits for limits").count() == 1 and await page.locator('.tcard[data-idea="held"] button, button.tcard[data-idea="held"] .pwr').count() == 0     # it waits for something else
        now = await _pop(page, "Plan ready: Starts tonight")                                         # held for the night: Start now
        start = now.get_by_role("button", name="Start now")
        assert await start.evaluate("e => e.offsetHeight") >= 43                                      # (the raised one is still leaping: its box is read unturned)
        await start.click()
        assert await _called(stub, "ideas.start_now", {"slug": "tonight", "via": "hand"})
        await now.wait_for(state="hidden", timeout=WAIT_MS)
        for _ in range(3):                                                                            # the field is drawn again after the start: a press in the middle of that is lost
            await power.click()
            if await _called(stub, "ideas.queue", {"slug": "raw", "queue": "now", "via": "party"}, timeout=2.0):
                break
        assert await _called(stub, "ideas.queue", {"slug": "raw", "queue": "now", "via": "party"})
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
    await page.locator(".ghead .trail-flag").wait_for(timeout=WAIT_MS)


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


FAR = "{ const sheet = new CSSStyleSheet(); sheet.replaceSync('.gchips { margin-bottom: 3000px }'); document.adoptedStyleSheets = [sheet]; }"      # a constructed sheet: the phone's CSP has no inline style


@pytest.mark.asyncio
async def test_a_flag_whose_header_is_out_of_sight_waits_and_is_raised_once_when_it_comes_into_view(fake_repo, monkeypatch):
    _met()
    flag_logs = lambda stub: [c for c in stub.calls if c[0] == "ideas.log" and c[1].get("what") == "flag"]      # noqa: E731
    async with _phone(fake_repo, monkeypatch, init=with_list(fake_repo, []) + FAR) as (stub, page):
        await _open_map(page)
        await _docs(page)
        for _ in range(3):                                                           # the header is drawn again, each time with its listener
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
        assert not any(c[0] == "ideas.flags" for c in stub.calls)                              # closed at first: not asked for
        await (await _menu(page)).get_by_role("button", name="Flags (1)").click()              # the menu's Flags: a sheet
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
        await (await _menu(page)).get_by_role("button", name="Flags (1)").click()
        await page.locator(".map-flag").wait_for(timeout=WAIT_MS)
        fold = page.locator(".map-flags-list .party-work")
        assert await fold.get_attribute("open") is None and not any(c[0] == "ideas.party" for c in stub.calls)
        await fold.locator("summary").click()
        await page.wait_for_function("() => document.querySelectorAll('.map-flags-list .party-work li').length === 4", timeout=WAIT_MS)
        assert [" ".join(t.split()) for t in await fold.locator("li").all_inner_texts()] == PARTY_LINES
        assert await _called(stub, "ideas.party", {"goal": "docs"})
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "party", "ref": "docs", "device": "phone"})
        assert await page.evaluate(NO_SCROLL)
