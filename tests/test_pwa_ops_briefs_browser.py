"""Spec 66 part C on the phone (docs/specs/66-team-briefs.md §7, §8 "C"): Chromium at 390 × 844 against the stub of test_pwa_shell_browser.py with
the fake `ops.*` of test_pwa_ops38_browser.py and a brief's commands. Before a 1:1's form says what it reads (*Tell your team what it reads*) and
Prepare before… sets a standing brief (seven day toggles, a time, minutes before), listed under its template with Change and Stop; its check shows what
was found, the doubts, Last time and the page to correct, **Keep for the 1:1**, Prepare again and Drop, no action's button; a kept brief opens read-only,
a long one scrolls in its sheet, and Copy gives its Markdown; Forget… asks once in the spec's words and removes; the gear keeps the last 1:1 brief N
days. No horizontal scroll of the page. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import pytest

from orkboard.gui.board_host import BoardPhone
from tests.test_pwa_ops38_browser import OpsState, _template
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _called, _phone, _pick_goal, _pop, _shot  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

READS = "Jira: the issues they own or were on · GitHub: their pull requests and reviews in the repos you name · Slack: none"
DOES = "prepares a page, does nothing outside"
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
ONE_ON_ONE = {
    "name": "one-on-one", "title": "Before a 1:1", "risk": "medium", "brief": True, "people": True, "reads": READS, "follow": "who", "does": DOES,
    "forget": {"field": "who", "label": "Who"}, "act_label": "Keep for the 1:1", "state": "checks", "state_words": "checks with you", "clean": 0, "why": "",
    "fields": [{"name": "who", "label": "Who", "type": "text", "required": True, "hint": "Their name as Jira and GitHub know them"},
               {"name": "notes", "label": "Your notes", "type": "long"},
               {"name": "repos", "label": "Repositories", "type": "text"},
               {"name": "team", "label": "Team", "type": "text", "remember": True}],
    "draft": [{"name": "agenda", "label": "Agenda", "type": "long"}]}
DAILY = {
    "name": "daily-brief", "title": "Before the daily", "risk": "medium", "brief": True, "people": True, "follow": "", "does": DOES,
    "reads": "Jira: the project you name · GitHub: the repos you name · Slack: the channels you name, never direct messages",
    "act_label": "Keep for the daily", "state": "checks", "state_words": "checks with you", "clean": 0, "why": "",
    "fields": [{"name": "team", "label": "Team", "type": "text", "remember": True}, {"name": "channels", "label": "Channels", "type": "text"}],
    "draft": [{"name": "brief", "label": "Brief", "type": "long"}]}
AGENDA = "**Their work since the last 1:1**\n- ORK-12 done\n\n**Last time**\n- promised: the review guide\n\n**To ask**\n- What gets in the way?"


def _days_words(days):
    days = sorted(set(days))
    if days == list(range(7)):
        return "every day"
    if days == list(range(5)):
        return "weekdays"
    return ", ".join(DAY_NAMES[d] for d in days)


class BriefState(OpsState):
    """OpsState with Before a 1:1 and Before the daily, the kept briefs, the standing ones and Forget."""

    def __init__(self, stub: Stub) -> None:
        super().__init__(stub)
        self.templates = [dict(ONE_ON_ONE), dict(DAILY), _template("jira-task", "New Jira task")]
        self.settings = {**self.settings, "follow_days": 90}
        self.standing: list[dict] = []

    def brief_run(self, state="check", who="Anna", agenda=AGENDA, **more):
        return self.add_run("one-on-one", state, brief=True, fields={"who": who, "notes": "", "repos": "", "team": "ORK"}, draft={"agenda": agenda},
                            found=[{"label": "Jira", "value": "4 issues of theirs moved"}], **more)

    def commands(self):
        stub = self.stub

        def cmd(name):
            def call(a):
                assert a.pop("device") == "phone"
                a.pop("link", None)
                stub.calls.append((name, dict(a)))
                return getattr(self, name.split(".")[1])(a)
            return call
        more = ("keep", "forget", "standing_add", "standing_change", "standing_stop")
        return {**super().commands(), **{f"ops.{n}": cmd(f"ops.{n}") for n in more}}

    def list(self, a):
        return {**super().list(a), "standing": self.standing}

    def keep(self, a):
        run = self.run(a["id"])
        run.update(state="done", draft={**run["draft"], **a.get("draft", {})}, done_at="2026-10-23T09:00:00")
        self.changed()
        return {"ok": True}

    def forget(self, a):
        gone = [r for r in self.runs if r["template"] == a["template"] and r["fields"].get("who", "").strip().casefold() == a["value"].strip().casefold()]
        self.runs = [r for r in self.runs if r not in gone]
        self.changed()
        return {"removed": len(gone)}

    def _words(self, item):
        title = next(t["title"] for t in self.templates if t["name"] == item["template"])
        return {**item, "title": title, "words": f"{title}: {_days_words(item['days'])} {item['at']}"}

    def standing_add(self, a):
        item = self._words({"id": f"st-{len(self.standing) + 1}", "template": a["template"], "fields": a["fields"], "days": a["days"], "at": a["at"],
                            "before": a.get("before", 30), "last": "", "skipped": ""})
        self.standing.append(item)
        self.changed()
        return {"id": item["id"]}

    def standing_change(self, a):
        i = next(n for n, s in enumerate(self.standing) if s["id"] == a["id"])
        self.standing[i] = self._words({**self.standing[i], **{k: a[k] for k in ("fields", "days", "at", "before") if k in a}})
        self.changed()
        return {"ok": True}

    def standing_stop(self, a):
        self.standing = [s for s in self.standing if s["id"] != a["id"]]
        self.changed()
        return {"ok": True}


@pytest.fixture(autouse=True)
def _ops(monkeypatch):
    holder: dict = {}
    real = Stub.commands

    def commands(self):
        holder["ops"] = holder.get("ops") if holder.get("ops") and holder["ops"].stub is self else BriefState(self)
        return {**real(self), **holder["ops"].commands()}
    monkeypatch.setattr(Stub, "commands", commands)
    snap = BoardPhone.phone_snapshot

    def with_rev(host):
        return {**snap(host), "ops_rev": holder["ops"].rev if holder.get("ops") else 0}
    monkeypatch.setattr(BoardPhone, "phone_snapshot", staticmethod(with_rev))
    return holder


async def _templates(page):
    fold = page.locator(".ops-fold", has_text="Templates")
    await fold.locator("summary").click()
    return fold


@pytest.mark.asyncio
async def test_a_1_1s_form_says_what_it_reads_and_prepare_before_sets_a_standing_brief_changed_and_stopped(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await _pick_goal(page, "ops")
        await page.get_by_role("button", name="New…").click()
        await page.get_by_role("dialog", name="New…").get_by_role("button", name="Before a 1:1").click()
        form = page.get_by_role("dialog", name="Before a 1:1")
        await form.wait_for(timeout=WAIT_MS)
        text = await form.inner_text()
        assert f"Reads: {READS}" in text and "Tell your team what it reads" in text
        assert await form.get_by_role("button", name="Add", exact=True).is_visible()
        await form.get_by_label("Who").fill("Anna")
        await form.get_by_label("Team").fill("ORK")
        days = form.get_by_role("group", name="Days of the week")
        assert await days.is_hidden()                                                                   # Prepare before… opens them
        await form.get_by_role("button", name="Prepare before…").click()
        await days.wait_for(timeout=WAIT_MS)
        assert [await days.get_by_role("checkbox", name=d).is_checked() for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")] == \
            [True] * 5 + [False] * 2
        await days.get_by_role("checkbox", name="Friday").click()
        await form.get_by_label("The meeting's time").fill("10:00")
        await form.get_by_label("Minutes before").fill("45")
        box = await form.bounding_box()
        assert box["x"] == 0 and box["width"] == 390 and box["y"] + box["height"] == 844                 # a bottom sheet
        assert await page.evaluate(NO_SCROLL) and await form.evaluate("(d) => d.scrollWidth <= d.clientWidth")
        await _shot(page, "phone-ops-brief-form-390x844")
        await form.get_by_role("button", name="Prepare before each meeting").click()
        assert await _called(stub, "ops.standing_add", {"template": "one-on-one", "fields": {"who": "Anna", "notes": "", "repos": "", "team": "ORK"},
                                                        "days": [0, 1, 2, 3], "at": "10:00", "before": 45})
        await form.wait_for(state="hidden", timeout=WAIT_MS)
        fold = await _templates(page)
        row = fold.locator(".ops-template", has_text="Before a 1:1")
        standing = row.locator(".ops-standing")
        await standing.wait_for(timeout=WAIT_MS)
        assert "Before a 1:1: Mon, Tue, Wed, Thu 10:00" in await standing.inner_text()
        assert DOES in await row.inner_text() and f"Reads: {READS}" in await row.inner_text()
        await standing.get_by_role("button", name="Change: Before a 1:1: Mon, Tue, Wed, Thu 10:00").click()
        change = page.get_by_role("dialog", name="Change: Before a 1:1")
        await change.wait_for(timeout=WAIT_MS)
        assert await change.get_by_label("Who").input_value() == "Anna" and await change.get_by_label("The meeting's time").input_value() == "10:00"
        assert await change.get_by_role("checkbox", name="Thursday").is_checked() and not await change.get_by_role("checkbox", name="Friday").is_checked()
        assert await change.get_by_role("button", name="Add", exact=True).count() == 0
        await change.get_by_role("checkbox", name="Friday").click()
        await change.get_by_role("button", name="Save the change").click()
        assert await _called(stub, "ops.standing_change", {"id": "st-1", "fields": {"who": "Anna", "notes": "", "repos": "", "team": "ORK"},
                                                           "days": [0, 1, 2, 3, 4], "at": "10:00", "before": 45})
        await change.wait_for(state="hidden", timeout=WAIT_MS)
        await standing.get_by_text("Before a 1:1: weekdays 10:00").wait_for(timeout=WAIT_MS)
        assert await page.evaluate(NO_SCROLL)
        await standing.get_by_role("button", name="Stop: Before a 1:1: weekdays 10:00").click()
        assert await _called(stub, "ops.standing_stop", {"id": "st-1"})
        await standing.wait_for(state="detached", timeout=WAIT_MS)
        jira = fold.locator(".ops-template", has_text="New Jira task")                                 # an operation that acts says none of it
        assert DOES not in await jira.inner_text() and "Reads:" not in await jira.inner_text() and await jira.get_by_role("button", name="Forget…: New Jira task").count() == 0


@pytest.mark.asyncio
async def test_a_1_1s_check_shows_last_time_and_keeps_the_page_with_no_action(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        ops = _ops["ops"]
        ops.brief_run(state="done", done_at="2026-10-16T09:00:00")
        ops.brief_run(doubts=["Two people named Anna in GitHub"], follows="op1", agenda=AGENDA.replace("ORK-12", "ORK-15"))
        ops.changed()
        await _pick_goal(page, "ops")
        await (await _pop(page, "At your check: Before a 1:1")).get_by_role("button", name="Open…").click()
        check = page.get_by_role("dialog", name="Before a 1:1")
        await check.wait_for(timeout=WAIT_MS)
        body = await check.inner_text()
        assert "Before a 1:1 · Anna" in body and "Jira: 4 issues of theirs moved" in body and "Two people named Anna in GitHub" in body
        keep = check.get_by_role("button", name="Keep for the 1:1")
        await keep.wait_for(timeout=WAIT_MS)
        assert await check.get_by_role("button", name="Drop").is_visible() and await check.get_by_role("button", name="Create in Jira").count() == 0
        assert "ORK-15" in await check.get_by_label("Agenda").input_value()
        await check.get_by_role("button", name="Last time: kept 16 October").click()                    # the kept one it starts from, read-only
        last = page.get_by_role("dialog", name="Before a 1:1").filter(has=page.locator(".ops-kept"))
        await last.wait_for(timeout=WAIT_MS)
        assert "ORK-12 done" in await last.inner_text() and await last.locator("textarea, input").count() == 0
        await last.get_by_role("button", name="Close").click()
        await last.wait_for(state="hidden", timeout=WAIT_MS)
        await check.get_by_text("Change what was asked").click()
        await check.get_by_label("Who").fill("Bob")
        assert await check.get_by_role("button", name="Prepare again").is_visible() and await keep.count() == 0
        await check.get_by_label("Who").fill("Anna")
        await keep.wait_for(timeout=WAIT_MS)
        box = await check.bounding_box()
        assert box["x"] == 0 and box["width"] == 390 and await page.evaluate(NO_SCROLL)
        await _shot(page, "phone-ops-brief-check-390x844")
        await check.get_by_label("Agenda").fill("**To ask**\n- Put the stuck items first")
        await keep.click()
        assert await _called(stub, "ops.keep", {"id": "op2", "fields": {}, "draft": {"agenda": "**To ask**\n- Put the stuck items first"}})
        await check.wait_for(state="hidden", timeout=WAIT_MS)
        assert not any(c[0] == "ops.act" for c in stub.calls)


@pytest.mark.asyncio
async def test_a_kept_brief_opens_read_only_a_long_one_scrolls_in_its_sheet_and_copy_gives_its_markdown(fake_repo, monkeypatch, _ops):
    long = "\n".join([f"- ORK-{n} moved: the queue retries on a lost signal" for n in range(80)] + ["https://example.com/" + "x" * 300])
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        ops = _ops["ops"]
        ops.brief_run(state="done", who="Bob", agenda="", done_at="2026-10-09T09:00:00")                # replaced by a newer one: its row only
        ops.brief_run(state="done", agenda=long, done_at="2026-10-16T09:00:00", alone=True)
        ops.changed()
        await _pick_goal(page, "ops")
        await page.evaluate("""() => Object.defineProperty(navigator, "clipboard", { configurable: true,
            value: { writeText: (t) => { window.__copied = t; return Promise.resolve(); } } })""")
        fold = page.locator(".ops-fold", has_text="Done (2)")
        await fold.locator("summary").click()
        assert await fold.get_by_role("button", name="Open the kept brief: Before a 1:1 · Bob").count() == 0
        row = fold.locator(".ops-done", has_text="Anna")
        assert "kept 16 October" in await row.inner_text() and "by itself" in await row.inner_text()
        assert await row.get_by_role("button", name="Not right: Before a 1:1").is_visible()
        await row.get_by_role("button", name="Open the kept brief: Before a 1:1 · Anna").click()
        sheet = page.get_by_role("dialog", name="Before a 1:1")
        await sheet.wait_for(timeout=WAIT_MS)
        assert "Kept 16 October · Anna · by itself" in await sheet.inner_text()
        assert await sheet.locator("textarea, input").count() == 0 and "ORK-79 moved" in await sheet.locator(".ops-page").inner_text()
        assert await sheet.evaluate("(d) => d.scrollHeight > d.clientHeight + 200 && d.scrollWidth <= d.clientWidth")   # it scrolls down in its sheet, never sideways
        assert await page.evaluate(NO_SCROLL)
        copy = sheet.get_by_role("button", name="Copy")
        assert await copy.is_visible()
        top = (await copy.bounding_box())["y"]
        assert 0 < top < 844                                                                          # pinned at the sheet's foot
        await _shot(page, "phone-ops-brief-kept-390x844")
        await copy.click()
        await page.wait_for_function("() => window.__copied !== undefined", timeout=WAIT_MS)
        assert await page.evaluate("() => window.__copied") == long


@pytest.mark.asyncio
async def test_forget_asks_once_in_the_specs_words_and_removes_and_the_gear_keeps_the_last_brief(fake_repo, monkeypatch, _ops):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        ops = _ops["ops"]
        ops.brief_run(state="done", done_at="2026-10-09T09:00:00")
        ops.brief_run(state="done", who="Bob", done_at="2026-10-16T09:00:00")
        ops.add_run("daily-brief", "held", brief=True, standing="st-1", why="waits for limits: prepared when the window allows",
                    fields={"team": "ORK", "channels": "#team"}, draft={})
        ops.changed()
        await _pick_goal(page, "ops")
        held = page.locator(".ops-run-row", has_text="Before the daily")
        await held.wait_for(timeout=WAIT_MS)
        assert "waits for limits: prepared when the window allows" in await held.inner_text()
        fold = await _templates(page)
        assert await fold.get_by_role("button", name="Forget…: Before the daily").count() == 0           # it follows no one
        await fold.get_by_role("button", name="Forget…: Before a 1:1").click()
        sheet = page.get_by_role("dialog", name="Forget: Before a 1:1")
        await sheet.wait_for(timeout=WAIT_MS)
        await sheet.get_by_role("button", name="Forget…").click()
        await sheet.get_by_text("Say whose: Who").wait_for(timeout=WAIT_MS)
        await sheet.get_by_label("Who").fill("anna ")
        await sheet.get_by_role("button", name="Forget…").click()
        await sheet.get_by_text("Forget everything kept about anna in Before a 1:1? This cannot be undone.").wait_for(timeout=WAIT_MS)
        assert not any(c[0] == "ops.forget" for c in stub.calls)                                         # asked first
        assert await page.evaluate(NO_SCROLL)
        await _shot(page, "phone-ops-brief-forget-390x844")
        await sheet.get_by_role("button", name="Forget it all").click()
        assert await _called(stub, "ops.forget", {"template": "one-on-one", "value": "anna"})
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        await page.locator(".ops-fold", has_text="Done (1)").wait_for(timeout=WAIT_MS)
        assert [r["fields"]["who"] for r in ops.runs if r["template"] == "one-on-one"] == ["Bob"]
        await page.get_by_role("button", name="Operations settings").click()
        gear = page.get_by_role("dialog", name="Operations settings")
        days = gear.get_by_label("Keep the last 1:1 brief for N days")
        assert await days.input_value() == "90"
        await days.fill("120")
        await days.blur()
        assert await _called(stub, "ops.set", {"follow_days": 120})
        assert await page.evaluate(NO_SCROLL)
