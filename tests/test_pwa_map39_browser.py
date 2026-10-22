"""Spec 48 part C on the phone (docs/specs/48-map-ideas.md §3–§7, "Tests → C"), through spec 49's one window and spec 50's: Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py with a fake `ideas.map`. The party's window: its goals bar (and the Goals sheet: the goals at work, one shown at a time; Done in Today), the stage switch and the
party's members at the top of their columns with their tasks running down in rows by phase, the stops and the results along the bottom. Yellow only on a stop; a stack leaves once when its last task
merges; a result merges, sends back and drops. No horizontal scroll."""
from __future__ import annotations

import json

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _band, _called, _item, _menu, _open_task, _phone, _pick_goal, _pop, _shot, _today, _where  # noqa: F401


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
async def test_a_party_s_window_has_its_goals_bar_its_members_in_the_stages_and_its_goals_one_at_a_time(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        stub.gate.update(commits=1, files=1, ideas=[{"slug": "old", "title": "Old cleanup", "goal": "ship", "tasks": 1}])           # in dev, not in main yet
        stub.bump({})
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "map", "device": "phone"})
        where = page.locator(".partydeck")
        assert await where.get_attribute("data-goal") == "ship"
        sheet = await _where(page)                                                                   # two parties and Operations
        assert await sheet.locator(".where-row").count() == 3 and await sheet.locator('.where-row[data-goal="ship"]').get_attribute("aria-current") == "true"
        assert await sheet.locator('.where-row[data-goal="ship"]').get_attribute("aria-label") == "Ship v1, 2/5 done, at work"      # the count of done goals, no %
        await page.keyboard.press("Escape")
        assert " ".join((await page.locator(".gbar__head").inner_text()).split()) == "Ship v1 · 2 of 5 goals done"
        # the party, stage by stage: the leader in Planning (it holds the plan), the builders, the checker (a member of its own, free)
        assert [await b.get_attribute("aria-label") for b in await page.locator(".band").all()] == ["Planning: the Taskmaster. 1 waits for you", "Implementation: Grunts, Product designer", "Checking: Reviewer"]
        await _band(page, "lead")
        assert [" ".join((await t.get_attribute("aria-label")).split(", ")[:1] + [(await t.get_attribute("aria-label")).split(", ")[3]]) for t in await page.locator(".token").all()] == ["Taskmaster plan ready"]
        assert await page.locator('.token[data-member="taskmaster"] .sign.alert .ork-sign.alert').count() == 1       # ! on the alert ground: orkUI's sign
        await _band(page, "build")
        assert [(await t.get_attribute("aria-label")).split(", ")[0] for t in await page.locator(".token").all()] == ["Grunts", "Product designer"]
        assert "at work" in await page.locator('.token[data-member="grunt"]').get_attribute("aria-label") and "next" in await page.locator('.token[data-member="product-designer"]').get_attribute("aria-label")
        await _band(page, "check")
        assert "free" in await page.locator('.token[data-member="reviewer"]').get_attribute("aria-label")
        await page.locator(".gbar__gate").wait_for(timeout=WAIT_MS * 2)                              # (the gate was read again, the bar drawn with it)
        await page.wait_for_timeout(700)
        for sel in (".board-bar .projbtn", ".partydeck", ".gbar__head", ".band", ".gbar__gate"):
            heights = await page.evaluate("(sel) => [...document.querySelectorAll(sel)].map((e) => e.getBoundingClientRect().height)", sel)   # read at once: a redraw in between is not a 0
            assert heights and min(heights) >= 43, sel                                                                                       # a finger's size
        # the Goals sheet: the goals at work, one shown at a time
        await page.locator(".gbar__head").click()
        goals = page.get_by_role("dialog", name="Goals")
        row = goals.locator('.dk__main[data-idea="sync"]')
        await row.wait_for(timeout=WAIT_MS)
        assert (await row.get_attribute("title")).startswith("Sync between phone and town · ")
        await goals.locator("h3", has_text="Waits for main").wait_for(timeout=WAIT_MS * 2)                    # (the gate was read again)
        assert [await h.text_content() for h in await goals.locator("h3").all()] == ["At work", "Planning", "Waits for main · 1", "Flags · 0"]       # (drawn in capitals)
        assert "Old cleanup · in dev" in await goals.locator(".goals__line").first.inner_text()      # a done goal waits for main
        await row.click()                                                                            # one goal shown: its tasks only, and a way back to all of them
        await goals.locator('.dk__main[data-idea="sync"][aria-pressed="true"]').wait_for(timeout=WAIT_MS)      # (the sheet is drawn again just after the tap)
        await goals.get_by_role("button", name="Show all").click()
        await goals.locator('.dk__main[data-idea="sync"][aria-pressed="false"]').wait_for(timeout=WAIT_MS)
        await page.keyboard.press("Escape")
        await _shot(page, "phone-map-390x844")
        assert await page.evaluate(NO_SCROLL)
        await _today(page)                                                                           # Done goals are Today's
        done = page.locator('.done-row[data-idea="old"]')
        await done.wait_for(timeout=WAIT_MS)
        assert "waits for main" in await done.inner_text() and "in main" in await page.locator('.done-row[data-idea="tables"]').inner_text()
        await done.click()                                                                           # a Done goal opens on its own screen, logged where it came from
        await page.locator(".screen .sec").first.wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "idea", "ref": "old", "device": "phone", "via": "today"})
        await page.get_by_role("button", name="Back", exact=True).click()
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
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
async def test_implementation_has_its_members_tasks_running_down_in_rows_by_phase_and_the_results_along_the_bottom(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await _band(page, "build")
        grunts, designer = page.locator('.stack[data-column="grunt"]'), page.locator('.stack[data-column="product-designer"]')
        # the members stand at the top, their tasks run down from them in rows by phase: a goal's tasks of one phase are one stack (the one at work in front)
        token, column = await page.locator('.token[data-member="grunt"]').bounding_box(), await grunts.bounding_box()
        stacks = grunts.locator(".deck:not(.is-leaving)")
        first = await stacks.first.bounding_box()
        assert token["y"] + token["height"] <= column["y"] <= first["y"]
        assert [await c.get_attribute("data-key") for c in await stacks.all()] == ["sync|now"] and await stacks.first.get_attribute("data-n") == "2"      # k2 and k1: one stack of two
        assert await stacks.first.get_attribute("data-task") is None and "Task k2" in await stacks.first.locator(".tcard__name").inner_text() and "is-run" in await stacks.first.locator(".tcard").get_attribute("class")
        assert (await grunts.locator(".stack__done").inner_text()).strip() == "3 in dev" and await grunts.locator(".stack__done .ork-sign.check").count() == 1       # what merged, at the far end
        assert await page.locator('.deck[data-task="k0"]').count() == 0                              # a merged task is not on the field
        last = await grunts.locator(".stack__done").bounding_box()
        assert last["y"] > first["y"]
        # a waiting task is dashed with its words, in the next row; a result in Review is muted ink, never yellow (decisions §54.1)
        wait = designer.locator('.deck[data-task="k3"]')
        assert "is-wait" in await wait.locator(".tcard").get_attribute("class") and "after k1" in await wait.inner_text() and await wait.locator("xpath=ancestor::*[contains(@class, 'phase')][1]").get_attribute("data-phase") == "next"
        assert await page.locator(".tcard.is-stop").count() == 0 and await page.locator(".tcard.is-fail").count() == 0
        await stacks.first.click()                                                                   # a stack of more lays its cards out in a row: k2 at work, k1 in Review
        await page.locator(".spread").wait_for(timeout=WAIT_MS)
        review = page.locator('.spread__card[data-key="sync/k1"], .spread__card').filter(has_text="in Review").first
        assert "is-review" in await review.locator(".tcard").get_attribute("class") and "in Review" in await review.inner_text()
        await page.locator(".spread__card").filter(has_text="Task k2").first.click()                 # a task opens on its screen
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


def _merge_sync(*ids):
    sync = next(n for n in ANSWER["nodes"] if n["slug"] == "sync")                                   # the host merges them: the tasks are merged
    for t in sync["tasks"]:
        if t["id"] in ids:
            t["state"] = "merged"


@pytest.mark.asyncio
async def test_a_stack_whose_last_task_merged_leaves_the_field_once_and_none_under_reduced_motion(fake_repo, monkeypatch):
    for reduced in (False, True):
        ANSWER.clear()
        ANSWER.update(json.loads(json.dumps(MAP)))
        async with _phone(fake_repo, monkeypatch) as (stub, page):
            if reduced:
                await page.emulate_media(reduced_motion="reduce")
            await _open_map(page)
            await _band(page, "build")
            grunts = page.locator('.stack[data-column="grunt"]')
            await grunts.locator('.deck[data-key="sync|now"]').wait_for(timeout=WAIT_MS)
            assert await page.locator(".deck.is-leaving, .deck.is-drawn").count() == 0                # none on the first read
            _merge_sync("k1")                                                                         # one of the two merges: the stack stays, its front card is the one left
            stub.bump({})
            await page.wait_for_function("() => document.querySelector('.stack[data-column=\"grunt\"] .deck[data-key=\"sync|now\"]')?.dataset.n === '1'", timeout=WAIT_MS * 2)
            assert (await grunts.locator(".stack__done").inner_text()).strip() == "4 in dev"
            _merge_sync("k2")                                                                         # the last: the stack leaves
            stub.bump({})
            await grunts.locator('.deck[data-key="sync|now"]').wait_for(state="detached", timeout=WAIT_MS * 2)
            if reduced:
                assert await page.locator(".deck.is-leaving").count() == 0                           # nothing moves
            assert (await grunts.locator(".stack__done").inner_text()).strip() == "5 in dev"


@pytest.mark.asyncio
async def test_a_stack_that_leaves_fades_where_it_stands_with_its_sign_once(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await _band(page, "build")
        await page.locator('.deck[data-key="sync|now"]').first.wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(2300)                                                             # the first read of a party is not a change
        # the fade lasts about 0.3 s: what is added to the page is recorded, not waited for
        await page.evaluate("""() => { window.__ghosts = []; new MutationObserver((ms) => { for (const mu of ms) for (const n of mu.addedNodes) if (n.nodeType === 1) {
          for (const g of (n.matches?.('.is-leaving') ? [n] : n.querySelectorAll?.('.is-leaving') || [])) window.__ghosts.push({ sign: g.dataset.sign, hidden: g.getAttribute('aria-hidden'), key: g.dataset.ghost,
            inColumn: g.closest('.stack')?.dataset.column }); } }).observe(document.body, { childList: true, subtree: true }); }""")
        _merge_sync("k1", "k2")
        stub.bump({})
        await page.wait_for_function("() => window.__ghosts.length > 0", timeout=WAIT_MS * 2)               # it stands where it stood, with the one-frame sign
        ghosts = await page.evaluate("window.__ghosts")
        assert {g["key"] for g in ghosts} == {"sync|now"} and ghosts[0]["sign"] == "check" and ghosts[0]["hidden"] == "true"      # orkUI's check, not a typed one
        assert ghosts[0]["inColumn"] == "grunt"
        await page.wait_for_function("() => document.querySelectorAll('.deck.is-leaving').length === 0", timeout=6000)      # once
        assert await page.locator('.stack[data-column="grunt"] .deck').count() == 0


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
        fail = page.locator('.stack[data-column="product-designer"] .deck[data-task="f1"]')
        assert "is-fail" in await fail.get_attribute("class") and "is-fail" in await fail.locator(".tcard").get_attribute("class")
        stops = [await e.get_attribute("data-member") for e in await page.locator(".token:has(.sign.danger)").all()]
        assert stops == ["product-designer"]                                                         # the agent of the failed task, not the one whose result waits
        review = page.locator('.stack[data-column="grunt"] .deck[data-task="f2"]')
        assert "is-review" in await review.locator(".tcard").get_attribute("class") and "in Review" in await review.inner_text()
        assert await review.locator(".tcard__foot").evaluate("e => getComputedStyle(e).color") != await fail.locator(".tcard__foot").evaluate("e => getComputedStyle(e).color")
        alert = await page.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-alert)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
        assert await page.locator('.hc[data-kind="asks"]').evaluate("e => getComputedStyle(e).borderTopColor") == alert                        # a stop wears the alert colour …
        assert await page.locator('.hc[data-kind="failed"]').evaluate("e => getComputedStyle(e).borderTopColor") != alert                        # … a failure wears the danger one


@pytest.mark.asyncio
async def test_checking_has_the_checkers_column_and_its_goal_in_the_goals_sheet(fake_repo, monkeypatch):
    chk = node("chk", "Checks of sync", 1, "working", stage="checking", round=2, progress={"done": 2, "total": 3},
               tasks=[task("c0", "merged"), task("c1", "running", REVIEWER, 1, "check"), task("c2", "waiting", REVIEWER, 2, "check")])
    ANSWER["nodes"] = [chk]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.locator(".band").first.wait_for(timeout=WAIT_MS)
        assert await page.locator('.band[data-band="check"]').get_attribute("aria-selected") == "true"        # the first shown: a checker has an open task
        assert [(await t.get_attribute("aria-label")).split(", ")[0] for t in await page.locator(".token").all()] == ["Reviewer"]
        assert await page.locator('.deck[data-task="c0"]').count() == 0
        assert [await c.get_attribute("data-task") for c in await page.locator('.stack[data-column="reviewer"] .deck').all()] == ["c1", "c2"]
        assert await page.locator('.deck[data-task="c2"]').locator("xpath=ancestor::*[contains(@class, 'phase')][1]").get_attribute("data-phase") == "next"      # wave 2: the next row
        await page.locator(".gbar__head").click()
        assert "1/3 in dev · checking" in await page.get_by_role("dialog", name="Goals").locator('.dk[data-idea="chk"] .dk__line').inner_text()


@pytest.mark.asyncio
async def test_no_project_open_says_open_a_folder_first(fake_repo, monkeypatch):
    ANSWER.clear()
    ANSWER["error"] = "Open a folder first"
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.get_by_text("Open a folder first").wait_for(timeout=WAIT_MS)
        assert await page.locator(".gbar").count() == 0
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_project_with_no_party_says_no_parties_yet_with_new_party(fake_repo, monkeypatch):
    ANSWER.update(goals=[], nodes=[], edges=[])
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await page.get_by_text("No parties yet.").wait_for(timeout=WAIT_MS)
        await page.locator(".pane").get_by_role("button", name="New party").last.click()
        await page.get_by_role("dialog", name="New party").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


def _short(n, short):
    return {**n, "short": short}


@pytest.mark.asyncio
async def test_a_planning_card_shows_the_short_name_with_the_title_in_its_label(fake_repo, monkeypatch):
    ANSWER["nodes"] = [_short(NODES[2], "Changelog"), NODES[3]]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _open_map(page)
        await _band(page, "lead")
        item = page.locator('.deck[data-idea="night"]')
        await item.wait_for(timeout=WAIT_MS)
        assert await item.locator(".tcard__name").inner_text() == "Changelog"
        assert await item.locator(".tcard__name").evaluate("e => getComputedStyle(e).webkitLineClamp") == "4"        # at most four lines
        assert "Write the changelog" in await item.get_attribute("aria-label") or "Write the changelog" in await item.get_attribute("title")      # the full title is in its label
        assert await page.evaluate(NO_SCROLL)


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
        await power.click()                                                                           # one tap does it: the field is drawn again after the start, never between a press's down and up
        assert await _called(stub, "ideas.queue", {"slug": "raw", "queue": "now", "via": "party"})
        assert await page.evaluate(NO_SCROLL)
