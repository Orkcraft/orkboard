"""Spec 38 part C on the phone (docs/specs/38-operations.md §10, "Tests → C"), through spec 49's window: Chromium at 390 × 844 against the stub of
test_pwa_shell_browser.py with fake `ops.*` commands. Operations among the parties' sheet's rows (taking the field's place); New… as a sheet listing the usable
template and the one that is not connected, in words; the form adds one (*preparing*), then its check: found, a doubt, Priority
changed in place, Epic changed turns the button into Prepare again; **Create in Jira** → done with its link; a template that goes
by itself shows *by itself* and Not right; a rules proposal taken on its stop; the gear sets the Target and a server; what waits in Operations is counted by the party's deck in
every goal and lies along the bottom in its own; with no project open Operations is still there; no horizontal scroll of the page. Screenshots to
docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import pytest

from orkboard.gui.board_host import BoardPhone
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _phone, _pick_goal, _pop, _shot, _where  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

FIELDS = [
    {"name": "what", "label": "What needs doing", "type": "long", "required": True},
    {"name": "priority", "label": "Priority", "type": "choice", "options": ["Highest", "High", "Medium", "Low", "Lowest"], "default": "Medium", "at": "p"},
    {"name": "epic", "label": "Epic", "type": "text", "hint": "a key or words of its name"},
]
DRAFT = [{"name": "summary", "label": "Title", "at": "summary"}, {"name": "description", "label": "Description", "type": "long", "at": "d"}]


def _template(name, title, **more):
    return {"name": name, "title": title, "risk": "medium", "fields": FIELDS, "draft": DRAFT, "act_label": "Create in Jira", "state": "checks",
            "state_words": "checks with you", "clean": 0, "why": "", **more}


class OpsState:
    """What the host's `ops.*` answer, in memory."""

    def __init__(self, stub: Stub) -> None:
        self.stub = stub
        self.templates = [_template("jira-task", "New Jira task"),
                          _template("email-reply", "Reply to an email", act_label="Save as a draft in Gmail", unusable="Gmail is not connected")]
        self.runs: list[dict] = []
        self.settings = {"target": "balance", "trust_after": 1, "daily_alone": 20, "keep_days": 14, "servers": {}}
        self.rev = 1

    def run(self, op_id):
        return next(r for r in self.runs if r["id"] == op_id)

    def changed(self):
        self.rev += 1
        self.stub.extra_needs = [n for n in self.stub.extra_needs if not n["kind"].startswith("op")]
        for r in self.runs:
            if r["state"] == "check":
                self.stub.extra_needs.append({"kind": "op", "op": r["id"], "template": r["template"], "title": r["title"], "text": r["draft"].get("summary", ""),
                                              "why": r["why"], "priority": "normal", "blocks": False, "at": r["at"]})
            if r["state"] == "failed":
                self.stub.extra_needs.append({"kind": "op_failed", "op": r["id"], "template": r["template"], "title": r["title"], "text": r["why"],
                                              "acted": r["acted"], "priority": "normal", "blocks": False, "at": r["at"]})
        for t in self.templates:
            if t.get("proposal"):
                self.stub.extra_needs.append({"kind": "op_rules", "template": t["name"], "title": t["title"], "op": "", "text": t["proposal"]["lines"][0],
                                              "lines": t["proposal"]["lines"], "priority": "normal", "blocks": False, "at": ""})
        self.stub.bump({})

    def add_run(self, template="jira-task", state="check", **more):
        n = len(self.runs) + 1
        t = next(x for x in self.templates if x["name"] == template)
        run = {"id": f"op{n}", "template": template, "state": state, "title": t["title"], "found": [{"label": "Project", "value": "ORK"}],
               "draft": {"summary": "Fix the lost signal", "description": "Why\nDone when"}, "fields": {"what": "fix the signal", "priority": "Medium", "epic": ""},
               "doubts": [], "alone": False, "link": "", "why": "", "acted": False, "held_until": "", "cost": 0.1, "at": "2026-10-18T09:30:00", "done_at": "", "step": ""}
        run.update(more)
        self.runs.append(run)
        return run

    def commands(self):
        stub = self.stub

        def cmd(name):
            def call(a):
                assert a.pop("device") == "phone"
                a.pop("link", None)
                stub.calls.append((name, dict(a)))
                return getattr(self, name.split(".")[1])(a)
            return call
        names = ("list", "add", "prepare", "act", "drop", "stop", "retry", "again", "not_right", "rules", "rules_save", "rules_answer", "trust_reset", "servers", "set")
        return {f"ops.{n}": cmd(f"ops.{n}") for n in names}

    def list(self, a):
        return {"templates": self.templates, "runs": self.runs, "settings": self.settings, "servers_needed": {"jira": "Jira"}}

    def add(self, a):
        run = self.add_run(a["template"], "preparing", fields=a["fields"], found=[], draft={})
        self.changed()
        return {"id": run["id"]}

    def prepare(self, a):
        self.run(a["id"]).update(state="preparing")
        self.changed()
        return {"ok": True}

    def act(self, a):
        run = self.run(a["id"])
        wrong = [f for f in FIELDS if f["name"] in a.get("fields", {}) and not f.get("at")]
        if wrong:
            return {"error": f"{wrong[0]['label']} changed: Prepare again first"}
        run.update(state="done", link="https://jira.example/ORK-7")
        self.changed()
        return {"ok": True}

    def drop(self, a):
        self.run(a["id"])["state"] = "dropped"
        self.runs = [r for r in self.runs if r["state"] != "dropped"]
        self.changed()
        return {"ok": True}

    def stop(self, a):
        self.run(a["id"]).update(state="failed", why="stopped by you", acted=None)
        self.changed()
        return {"ok": True}

    def retry(self, a):
        self.run(a["id"]).update(state="preparing", why="")
        self.changed()
        return {"ok": True}

    def again(self, a):
        run = self.add_run(state="preparing")
        self.changed()
        return {"id": run["id"]}

    def not_right(self, a):
        self.runs and self.run(a["id"]).update(alone=False)
        self.templates[0].update(state="checks", state_words="checks with you")
        self.changed()
        return {"ok": True}

    def rules(self, a):
        return {"text": "Titles start with a verb."}

    def rules_save(self, a):
        return {"ok": True}

    def rules_answer(self, a):
        for t in self.templates:
            if t["name"] == a["template"]:
                t.pop("proposal", None)
        self.changed()
        return {"ok": True}

    def trust_reset(self, a):
        self.templates[0].update(state="checks", state_words="checks with you")
        self.changed()
        return {"ok": True}

    def servers(self, a):
        return {"servers": ["atlassian", "gmail"]}

    def set(self, a):
        servers = {**self.settings["servers"], **a.pop("servers", {})}
        self.settings = {**self.settings, **a, "servers": {k: v for k, v in servers.items() if v}}
        self.changed()
        return self.settings


@pytest.fixture(autouse=True)
def _ops(monkeypatch):
    holder: dict = {}
    real = Stub.commands

    def commands(self):
        holder["ops"] = holder.get("ops") if holder.get("ops") and holder["ops"].stub is self else OpsState(self)
        return {**real(self), **holder["ops"].commands()}
    monkeypatch.setattr(Stub, "commands", commands)
    snap = BoardPhone.phone_snapshot

    def with_rev(host):
        return {**snap(host), "ops_rev": holder["ops"].rev if holder.get("ops") else 0}
    monkeypatch.setattr(BoardPhone, "phone_snapshot", staticmethod(with_rev))
    return holder


async def _ops_view(page):
    await _pick_goal(page, "ops")


@pytest.mark.asyncio
async def test_operations_is_among_the_goals_new_lists_the_templates_and_the_form_adds_one(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _where(page)
        rows = sheet.locator(".where-row")
        await rows.last.wait_for(timeout=WAIT_MS)
        assert (await rows.all_inner_texts())[-1:] == ["Operations"]                                    # the parties' sheet lists the parties and Operations
        await page.keyboard.press("Escape")
        await _pick_goal(page, "ops")
        assert await page.get_by_role("heading", name="Needs you").count() == 0 and await page.locator(".target-chip").count() == 0
        assert await page.locator(".gbar").count() == 0 and await page.locator(".ops-view .partydeck").get_attribute("data-goal") == "ops"         # Operations takes the field's place: no party's goals bar, the deck at its head
        await page.get_by_role("button", name="Operations settings").wait_for(timeout=WAIT_MS)
        await page.get_by_role("button", name="New…").click()
        menu = page.get_by_role("dialog", name="New…")
        await menu.wait_for(timeout=WAIT_MS)
        assert await menu.get_by_role("button", name="New Jira task").is_visible()
        text = await menu.inner_text()
        assert "Reply to an email" in text and "Gmail is not connected" in text and await menu.get_by_role("button", name="Reply to an email").count() == 0
        box = await menu.bounding_box()
        assert box["x"] == 0 and box["width"] == 390 and box["y"] + box["height"] == 844            # a bottom sheet
        await menu.get_by_role("button", name="New Jira task").click()
        form = page.get_by_role("dialog", name="New Jira task")
        await form.wait_for(timeout=WAIT_MS)
        assert await form.get_by_label("Epic").get_attribute("placeholder") == "a key or words of its name"
        assert await form.get_by_label("Priority").input_value() == "Medium"
        await _shot(page, "phone-ops-form-390x844")
        await form.get_by_label("What needs doing").fill("fix the lost signal")
        await form.get_by_role("button", name="Cancel").click()
        await page.get_by_role("button", name="New…").click()                                          # closed with text: kept for the next opening
        await menu.get_by_role("button", name="New Jira task").click()
        assert await form.get_by_label("What needs doing").input_value() == "fix the lost signal"
        await form.get_by_role("button", name="Add", exact=True).click()
        assert await _called(stub, "ops.add", {"template": "jira-task", "fields": {"what": "fix the lost signal", "priority": "Medium", "epic": ""}})
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        running = page.locator(".ops-run-row")
        await running.wait_for(timeout=WAIT_MS)
        assert "preparing" in await running.inner_text()
        assert await page.evaluate(NO_SCROLL)
        await running.get_by_role("button", name="Stop").click()
        assert await _called(stub, "ops.stop", {"id": "op1"})
        failed = page.locator(".ops-failed")
        await failed.wait_for(timeout=WAIT_MS)
        assert "stopped by you" in await failed.inner_text() and await failed.get_by_role("button", name="Try again").count() == 0   # it may have acted
        await failed.get_by_role("button", name="Drop").click()
        await failed.wait_for(state="detached", timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_the_check_edits_in_place_prepares_again_for_an_other_field_and_creates(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _ops["ops"].add_run(doubts=["A like task is open: ORK-3"])
        _ops["ops"].changed()
        await _ops_view(page)
        raised = await _pop(page, "At your check: New Jira task")                                      # the check waits along the bottom
        text = await raised.inner_text()
        assert "New Jira task" in text and "Fix the lost signal" in text and "at your check" in (await raised.locator(".raised__kind").text_content()).lower()
        await _shot(page, "phone-ops-list-390x844")
        await raised.get_by_role("button", name="Open…").click()
        check = page.get_by_role("dialog", name="New Jira task")
        await check.wait_for(timeout=WAIT_MS)
        body = await check.inner_text()
        assert "Project: ORK" in body and "A like task is open: ORK-3" in body
        create = check.get_by_role("button", name="Create in Jira")
        await create.wait_for(timeout=WAIT_MS)
        await check.get_by_label("Priority").select_option("High")
        assert await check.get_by_role("button", name="Create in Jira").is_visible()                 # a field with `at`: changed in place
        await check.get_by_label("Title").fill("Fix the signal loss")
        await _shot(page, "phone-ops-check-390x844")
        await check.get_by_text("Change what was asked").click()
        await check.get_by_label("Epic").fill("Mobile")
        assert await check.get_by_role("button", name="Prepare again").is_visible() and await create.count() == 0
        await check.get_by_label("Epic").fill("")
        await create.wait_for(timeout=WAIT_MS)
        box = await check.bounding_box()
        assert box["x"] == 0 and box["width"] == 390 and box["y"] + box["height"] == 844
        assert await page.evaluate(NO_SCROLL)
        await check.get_by_label("Epic").fill("Mobile")
        await check.get_by_role("button", name="Prepare again").click()
        assert await _called(stub, "ops.prepare", {"id": "op1", "fields": {"priority": "High", "epic": "Mobile"}, "draft": {"summary": "Fix the signal loss"}})
        await check.wait_for(state="hidden", timeout=WAIT_MS)
        listed = len([c for c in stub.calls if c[0] == "ops.list"])
        _ops["ops"].run("op1").update(state="check")
        _ops["ops"].changed()
        for _ in range(100):                                                                            # the phone reads Operations again when its revision moves
            if len([c for c in stub.calls if c[0] == "ops.list"]) > listed:
                break
            await page.wait_for_timeout(100)
        await (await _pop(page, "At your check: New Jira task")).get_by_role("button", name="Open…").click()
        await check.get_by_role("button", name="Create in Jira").click()
        assert await _called(stub, "ops.act", {"id": "op1", "fields": {}, "draft": {}})
        await check.wait_for(state="hidden", timeout=WAIT_MS)
        await page.locator(".ops-fold", has_text="Done (1)").locator("summary").click()
        link = page.get_by_role("link", name="Open the result of New Jira task")
        await link.wait_for(timeout=WAIT_MS)
        assert await link.get_attribute("href") == "https://jira.example/ORK-7"
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_template_that_goes_by_itself_says_so_not_right_and_check_again(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        ops = _ops["ops"]
        ops.templates[0].update(state="alone", state_words="goes by itself")
        ops.add_run(state="done", alone=True, link="https://jira.example/ORK-8")
        ops.add_run(state="check", alone=True, why="a doubt")
        ops.changed()
        await _ops_view(page)
        assert "a doubt" in await (await _pop(page, "At your check: New Jira task")).inner_text()
        await page.keyboard.press("Escape")
        await page.locator(".ops-fold", has_text="Done (1)").locator("summary").click()
        done = page.locator(".ops-done")
        assert "by itself" in await done.inner_text()
        await done.get_by_role("button", name="Not right: New Jira task").click()
        sheet = page.get_by_role("dialog", name="Not right")
        await sheet.get_by_label("What was not right").fill("wrong epic")
        await sheet.get_by_role("button", name="Send: not right").click()
        assert await _called(stub, "ops.not_right", {"id": "op1", "why": "wrong epic"})
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        ops.templates[0].update(state="alone", state_words="goes by itself")
        ops.changed()
        await page.locator(".ops-fold", has_text="Templates").locator("summary").click()
        tpl = page.locator(".ops-template", has_text="New Jira task")
        await tpl.get_by_text("goes by itself: create in jira without asking you").wait_for(timeout=WAIT_MS)
        await tpl.get_by_role("button", name="Check again: New Jira task").click()
        assert await _called(stub, "ops.trust_reset", {"template": "jira-task"})
        await tpl.get_by_role("button", name="Rules: New Jira task").click()
        rules = page.get_by_role("dialog", name="Rules: New Jira task")
        assert await rules.get_by_label("Rules").input_value() == "Titles start with a verb."
        await rules.get_by_role("button", name="Save rules").click()
        assert await _called(stub, "ops.rules_save", {"template": "jira-task", "text": "Titles start with a verb."})
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_what_waits_in_operations_is_counted_by_the_partys_deck_in_every_party_and_lies_along_the_bottom_in_its_own(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        stub.goals["ship"] = stub.goal("ship", "Ship v1", "high", "ready")
        ops = _ops["ops"]
        ops.add_run()
        ops.add_run(state="failed", why="Jira said no", acted=False)
        ops.templates[0]["proposal"] = {"lines": ["Titles start with a verb.", "Name the epic."], "why": "", "op": "op1", "at": ""}
        ops.changed()
        await _pick_goal(page, "ship")                                # another party: the party's deck counts Operations' stops all the same
        where = page.locator(".partydeck")
        await where.locator(".ork-count").wait_for(state="visible", timeout=WAIT_MS)
        assert await where.locator(".ork-count").inner_text() == "5" and "5 stops wait in the other parties" in await where.get_attribute("aria-label")      # Operations' 3 and General's 2
        sheet = await _where(page)
        assert await sheet.locator('.where-row[data-goal="ops"] .ork-count.warning').inner_text() == "3"           # and its row in the sheet
        await page.keyboard.press("Escape")
        assert await page.locator(".hc").count() == 0 or all("op" not in (await h.get_attribute("data-kind")) for h in await page.locator(".hc").all())          # not among that goal's stops
        await _pick_goal(page, "ops")
        assert sorted([await b.get_attribute("data-kind") for b in await page.locator(".hc").all()]) == ["op", "op_failed", "op_rules"]
        failed = await _pop(page, "Failed: ")
        assert "Jira said no" in await failed.inner_text() and "danger" in await failed.get_attribute("class")
        await failed.get_by_role("button", name="Open…").click()
        dialog = page.get_by_role("dialog", name="Failed")
        await dialog.get_by_role("button", name="Try again").click()
        assert await _called(stub, "ops.retry", {"id": "op2"})
        rules = await _pop(page, "Proposed: New Jira task")
        await rules.get_by_role("button", name="Open…").click()
        sheet = page.get_by_role("dialog", name="Rules: New Jira task")
        assert "Name the epic." in await sheet.inner_text()
        await sheet.get_by_label("Why not: jira-task").fill("too fussy")
        await sheet.get_by_role("button", name="No").click()
        assert await _called(stub, "ops.rules_answer", {"template": "jira-task", "take": False, "reason": "too fussy"})
        await page.locator('.hc[data-kind="op_rules"]').wait_for(state="detached", timeout=WAIT_MS)
        await (await _pop(page, "At your check: New Jira task")).get_by_role("button", name="Open…").click()          # a tap opens the check
        await page.get_by_role("dialog", name="New Jira task").get_by_role("button", name="Create in Jira").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_gear_sets_the_target_the_limits_and_a_server(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _ops_view(page)
        await page.get_by_role("button", name="Operations settings").click()
        gear = page.get_by_role("dialog", name="Operations settings")
        await gear.wait_for(timeout=WAIT_MS)
        assert await gear.get_by_role("radio", name="Balance").is_checked()
        await gear.get_by_role("radio", name="Quality").click()
        assert await _called(stub, "ops.set", {"target": "quality"})
        count = gear.get_by_label("Goes by itself after N clean checks")
        await count.fill("3")
        await count.blur()
        assert await _called(stub, "ops.set", {"trust_after": 3})
        server = gear.get_by_label("Server for Jira")
        await server.locator("option", has_text="atlassian").wait_for(state="attached", timeout=WAIT_MS)
        assert await server.input_value() == "" and "not connected" in await server.inner_text()
        await server.select_option("atlassian")
        assert await _called(stub, "ops.set", {"servers": {"jira": "atlassian"}})
        await _shot(page, "phone-ops-gear-390x844")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_a_held_run_says_why_the_limits_or_the_days_spend_cap(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        limits = _ops["ops"].add_run(state="held", held_until="2026-10-18T18:00:00")
        cap = _ops["ops"].add_run(template="email-reply", state="held", held_until="2026-10-19T00:00:00",
                                  why="waits: the day's spend cap is reached")
        _ops["ops"].changed()
        await _ops_view(page)
        row = page.locator(f".ops-run-row[data-op={limits['id']}]")
        await row.wait_for(timeout=WAIT_MS)
        assert "waits for limits · after 18:00" in await row.inner_text()
        assert "waits: the day's spend cap is reached" in await page.locator(f".ops-run-row[data-op={cap['id']}]").inner_text()
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_with_no_project_open_operations_is_still_offered(fake_repo, monkeypatch, _ops):
    real = Stub.run

    def run(self, name, a):
        if name == "ideas.board":
            return {"error": "Open a folder first"}
        return real(self, name, a)
    monkeypatch.setattr(Stub, "run", run)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        _ops["ops"].add_run()
        _ops["ops"].changed()
        pane = page.locator(".arena")
        await pane.get_by_text("Open a folder first").wait_for(timeout=WAIT_MS)
        await pane.get_by_role("heading", name="Operations").wait_for(timeout=WAIT_MS)
        await pane.locator(".need-op").wait_for(timeout=WAIT_MS)
        await pane.get_by_role("button", name="New…").click()
        await page.get_by_role("dialog", name="New…").get_by_role("button", name="New Jira task").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_the_phone_shows_the_way_to_by_itself_and_since_the_day_it_went_spec_42_e(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        ops = _ops["ops"]
        ops.templates[0].update(trust_after=3, clean=2)
        ops.templates[1].update(unusable="", state="alone", state_words="goes by itself", trust_after=3, alone_since="2026-10-18", done_alone=12)
        ops.templates.append(_template("wire", "Wire money", risk="high", state="always", state_words="always checks with you", trust_after=3))
        ops.changed()
        await _ops_view(page)
        await page.locator(".ops-fold", has_text="Templates").locator("summary").click()
        jira = page.locator(".ops-template", has_text="New Jira task")
        await jira.get_by_text("2 of 3 clean checks", exact=False).wait_for(timeout=WAIT_MS)      # drawn again once ops_rev moved
        assert " ".join((await jira.locator("[data-way]").inner_text()).split()) == "Checks with you: 2 of 3 clean checks, then it goes by itself"
        assert await jira.locator(".ork-pips > i").evaluate_all("els => els.map(e => e.className)") == ["d", "d", ""]
        mail = page.locator(".ops-template", has_text="Reply to an email")
        assert await mail.locator("[data-since]").inner_text() == "since 18 October · 12 done" and await mail.locator(".ork-pips").count() == 0
        wire = page.locator(".ops-template", has_text="Wire money")
        assert "always checks with you" in await wire.inner_text() and await wire.locator("[data-way]").count() == 0
        assert await page.evaluate(NO_SCROLL)
