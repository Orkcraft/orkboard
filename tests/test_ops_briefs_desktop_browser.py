"""Team briefs on the desktop, in a real browser (docs/specs/66-team-briefs.md §7, Tests → B; 1 440 × 900), against a stub host:
Orkboard's real host and server with `ops.*` answered from memory (spec 38's `StubOps`, taught a brief's commands; the backend has
its own tests). Before a 1:1's form with its Reads line; its check with Last time and Keep; a kept brief opened and copied;
Prepare before set, listed, changed and stopped; Forget asks once and removes; the gear's *Keep the last 1:1 brief for N days*."""
from __future__ import annotations

import pytest

playwright = pytest.importorskip("playwright.sync_api")
expect = playwright.expect

from orkboard.core.op_commands import OpsError  # noqa: E402
from orkboard.gui.board_host import Orkboard  # noqa: E402
from tests.browser_kit import WAIT_MS  # noqa: E402
from tests.test_ops_desktop_browser import JIRA, StubOps, _dialog, _operations, _repo, _row, _run, _sent  # noqa: E402

pytestmark = pytest.mark.browser

DOES = "prepares a page, does nothing outside"
ONE = {"name": "one-on-one", "title": "Before a 1:1", "risk": "medium", "act_label": "Keep for the 1:1", "state": "checks",
       "state_words": "checks with you", "clean": 0, "why": "", "brief": True, "people": True, "follow": "who", "does": DOES,
       "reads": "Jira: the issues they own or were on · GitHub: their pull requests and reviews in the repos you name · Slack: none",
       "forget": {"field": "who", "label": "Who"},
       "fields": [{"name": "who", "label": "Who", "type": "text", "required": True, "hint": "Their name as Jira and GitHub know them"},
                  {"name": "notes", "label": "Your notes", "type": "long", "hint": "Your own: kept as you wrote them, seen by you alone"},
                  {"name": "repos", "label": "Repositories", "type": "text", "hint": "owner/repo, a comma between them"},
                  {"name": "team", "label": "Team", "type": "text", "remember": True, "default": "SHOP"}],
       "draft": [{"name": "agenda", "label": "Agenda", "type": "long", "at": ""}]}
DAILY = {"name": "daily-brief", "title": "Before the daily", "risk": "medium", "act_label": "Keep for the daily", "state": "checks",
         "state_words": "checks with you", "clean": 0, "why": "", "brief": True, "people": True, "follow": "", "does": DOES,
         "reads": "Jira: the project you name · GitHub: the repos you name · Slack: the channels you name, never direct messages",
         "fields": [{"name": "team", "label": "Team", "type": "text", "remember": True, "default": "SHOP"},
                    {"name": "channels", "label": "Slack channels", "type": "text", "remember": True, "default": "#shop"},
                    {"name": "since", "label": "Since", "type": "choice", "options": ["the last working day", "yesterday"],
                     "default": "the last working day"}],
         "draft": [{"name": "brief", "label": "Brief", "type": "long", "at": ""}]}
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
AGENDA = "## Their work since the last 1:1\n- SHOP-101 done\n\n## To ask\n- What gets in the way of the review?"


class BriefStub(StubOps):
    """Spec 38's stub with the four commands of a brief (spec 66 §10) and its standing briefs."""

    def __init__(self, host) -> None:
        super().__init__(host)
        self.templates = [dict(t) for t in (JIRA, ONE, DAILY)]
        self.settings["follow_days"] = 90
        self.standing: list[dict] = []

    def commands(self):
        out = super().commands()
        out.update({name: (lambda a, name=name: self.call(name, a)) for name in (
            "ops.keep", "ops.forget", "ops.standing_add", "ops.standing_change", "ops.standing_stop")})
        return out

    def seed(self, template, state, **more) -> str:
        brief = next(t for t in self.templates if t["name"] == template).get("brief", False)
        return super().seed(template, state, **{"brief": brief, "standing": "", "follows": "", **more})

    def _list(self, a):
        return {**super()._list(a), "standing": self.standing}

    def _set(self, a):
        if "follow_days" in a:
            self.settings["follow_days"] = a["follow_days"]
        return super()._set(a)

    def _keep(self, a):
        self.run(a["id"]).update(state="done", draft={**self.run(a["id"])["draft"], **(a.get("draft") or {})}, done_at="2026-10-23T09:40:00")
        self.changed()
        return {"ok": True}

    def _forget(self, a):
        value = a["value"].strip().lower()
        gone = [r for r in self.runs if r["template"] == a["template"] and r["fields"].get("who", "").strip().lower() == value]
        self.runs[:] = [r for r in self.runs if r not in gone]
        self.changed()
        return {"removed": len(gone)}

    @staticmethod
    def _words(item):
        days = "weekdays" if item["days"] == [0, 1, 2, 3, 4] else ", ".join(DAYS[d] for d in item["days"])
        return f"Before the daily: {days} {item['at']}"

    def _standing_add(self, a):
        if not a.get("days"):
            raise OpsError("Pick the days of the week it is prepared on")
        item = {"id": f"st-{len(self.standing) + 1}", "template": a["template"], "fields": dict(a["fields"]), "days": a["days"],
                "at": a["at"], "before": a.get("before", 30), "last": "", "skipped": "", "title": "Before the daily"}
        self.standing.append({**item, "words": self._words(item)})
        self.changed()
        return {"id": item["id"]}

    def _standing_change(self, a):
        item = next(s for s in self.standing if s["id"] == a["id"])
        item.update({k: a[k] for k in ("fields", "days", "at", "before") if k in a})
        item["words"] = self._words(item)
        self.changed()
        return {"ok": True}

    def _standing_stop(self, a):
        self.standing[:] = [s for s in self.standing if s["id"] != a["id"]]
        self.changed()
        return {"ok": True}


@pytest.fixture
def host(tmp_path, monkeypatch):
    for key, value in {"ORKCRAFT_SETTINGS_FILE": tmp_path / "settings.json", "ORKCRAFT_ONBOARDING": "0",
                       "ORKCRAFT_LIMITS": "0", "ORKCRAFT_NO_UPDATE": "1", "XDG_CONFIG_HOME": tmp_path / "config"}.items():
        monkeypatch.setenv(key, str(value))
    host = Orkboard(_repo(tmp_path / "shop"))
    host.ops.close()
    host.ops = BriefStub(host)
    host.commands.update(host.ops.commands())
    return host


def _new(pg, title):
    pg.get_by_role("button", name="New…").click()
    pg.get_by_role("menuitem", name=title).click()
    return _dialog(pg, title)


def _templates(pg):
    pg.get_by_text("Templates (3)").click()


def test_before_a_1_1s_form_says_what_it_reads_and_adds_one(host):
    def body(pg, stub):
        _operations(pg)
        form = _new(pg, "Before a 1:1")
        reads = form.get_by_role("note", name="What it reads")
        assert "Slack: none" in reads.inner_text() and "Tell your team what it reads." in reads.inner_text()
        assert "nothing is posted, sent or changed anywhere" in form.inner_text()
        assert form.get_by_role("button", name="Prepare before…").count() == 1          # a brief may stand
        form.get_by_label("Who").fill("Alex")
        form.get_by_role("button", name="Add").click()
        form.wait_for(state="detached", timeout=WAIT_MS)
        _sent(stub, ("ops.add", {"template": "one-on-one", "fields": {"who": "Alex", "team": "SHOP"}}))
        jira = _new(pg, "New Jira task")                                               # an action: no Reads, no Prepare before
        assert jira.get_by_role("note", name="What it reads").count() == 0 and jira.get_by_role("button", name="Prepare before…").count() == 0
        pg.keyboard.press("Escape")
        _templates(pg)
        one = pg.locator(".board-op--template[data-template=one-on-one]")
        assert DOES in one.inner_text() and "Tell your team what it reads." in one.inner_text()
        assert "Slack: none" in one.get_by_role("note", name="What it reads").inner_text()
        assert DOES not in pg.locator(".board-op--template[data-template=jira-task]").inner_text()
    _run(host, body)


def test_its_check_shows_last_time_and_keep_keeps_the_page_as_corrected(host):
    stub = host.ops
    last = stub.seed("one-on-one", "done", fields={"who": "Alex"}, draft={"agenda": "Promised: a review buddy for Alex's PRs"},
                     done_at="2026-10-16T10:00:00")
    op = stub.seed("one-on-one", "check", fields={"who": "Alex", "team": "SHOP"}, follows=last, draft={"agenda": AGENDA},
                   found=[{"label": "Jira", "value": "alex@shop (1 account)"}], doubts=["Two GitHub users are named Alex"])

    def body(pg, stub):
        _operations(pg)
        _row(pg, "op", op).locator(".arena-hc__open").click()
        check = _dialog(pg, "Before a 1:1 · Alex")
        assert "alex@shop" in check.get_by_role("group", name="What was found").inner_text()
        assert "Two GitHub users are named Alex" in check.get_by_label("Doubts").inner_text()
        lasttime = check.locator("[data-last-time]")
        assert lasttime.get_attribute("data-last-time") == last and "Last time · kept 16 October" in lasttime.inner_text()
        lasttime.locator("summary").click()
        expect(lasttime.locator(".shell-brief")).to_have_text("Promised: a review buddy for Alex's PRs")
        assert check.get_by_label("Agenda", exact=True).input_value() == AGENDA                    # the page, editable
        assert check.locator("[data-act=act]").count() == 0                            # no action's button
        keep = check.get_by_role("button", name="Keep for the 1:1")
        assert check.get_by_role("button", name="Prepare again").count() == 1 and check.get_by_role("button", name="Drop").count() == 1
        check.get_by_label("Who").fill("Sam")                                          # the form changed: Prepare again first
        assert keep.is_disabled()
        check.get_by_label("Who").fill("Alex")
        assert keep.is_enabled()
        check.get_by_label("Agenda", exact=True).fill(AGENDA + "\n- Ask about the on-call week")
        keep.click()
        check.wait_for(state="detached", timeout=WAIT_MS)
        _sent(stub, ("ops.keep", {"id": op, "draft": {"agenda": AGENDA + "\n- Ask about the on-call week"}}))
        assert stub.run(op)["state"] == "done"
    _run(host, body)


def test_a_kept_brief_opens_read_only_and_copy_puts_its_markdown_on_the_clipboard(host):
    stub = host.ops
    op = stub.seed("one-on-one", "done", fields={"who": "Alex"}, draft={"agenda": AGENDA}, alone=True, done_at="2026-10-23T09:40:00")

    def body(pg, stub):
        _operations(pg)
        pg.evaluate("""() => { window.copied = [];
          Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: (t) => { window.copied.push(t); return Promise.resolve(); } } }); }""")
        pg.get_by_text("Done (1)").click()
        row = pg.locator(f".board-op[data-op={op}]")
        assert row.locator("[data-by-itself]").inner_text() == "by itself" and "kept 23 October" in row.inner_text()
        row.get_by_role("button", name="Open: Before a 1:1 · Alex").click()
        kept = _dialog(pg, "Before a 1:1 · Alex")
        assert kept.locator("textarea, input").count() == 0                              # read-only
        assert kept.locator(".shell-brief").inner_text().startswith("## Their work since the last 1:1")
        assert "never posts, sends or shows it to anyone" in kept.inner_text() and kept.locator("[data-by-itself]").count() == 1
        kept.get_by_role("button", name="Copy").click()
        pg.wait_for_function("() => window.copied.length === 1", timeout=WAIT_MS)
        assert pg.evaluate("() => window.copied[0]") == AGENDA + "\n"
        assert not [s for s in stub.sent if s[0] != "ops.list"]                           # opening and copying send nothing
    _run(host, body)


def test_prepare_before_is_set_listed_changed_and_stopped(host):
    def body(pg, stub):
        _operations(pg)
        form = _new(pg, "Before the daily")
        assert form.get_by_role("button", name="Prepare before each meeting").count() == 0
        form.get_by_role("button", name="Prepare before…").click()
        days = form.get_by_role("group", name="Days of the week")
        assert [d.inner_text() for d in days.locator(".shell-seg__one.is-on").all()] == ["Mon", "Tue", "Wed", "Thu", "Fri"]
        go = form.get_by_role("button", name="Prepare before each meeting")
        assert go.is_disabled()                                                          # no time yet
        days.get_by_text("Fri", exact=True).click()
        form.get_by_label("The meeting's time").fill("09:30")
        form.get_by_label("Minutes before").fill("20")
        go.click()
        form.wait_for(state="detached", timeout=WAIT_MS)
        fields = {"team": "SHOP", "channels": "#shop", "since": "the last working day"}
        _sent(stub, ("ops.standing_add", {"template": "daily-brief", "days": [0, 1, 2, 3], "at": "09:30", "before": 20, "fields": fields}))
        _templates(pg)
        row = pg.locator(".board-op--template[data-template=daily-brief] [data-standing=st-1]")
        row.wait_for(timeout=WAIT_MS)
        assert "Before the daily: Mon, Tue, Wed, Thu 09:30" in row.inner_text()
        assert pg.locator(".board-op--template[data-template=daily-brief]").get_by_role("button", name="Forget: Before the daily").count() == 0
        row.get_by_role("button", name="Change").click()
        change = _dialog(pg, "Before the daily")
        assert change.get_by_label("The meeting's time").input_value() == "09:30" and change.get_by_label("Minutes before").input_value() == "20"
        change.get_by_role("group", name="Days of the week").get_by_text("Fri", exact=True).click()
        change.get_by_label("The meeting's time").fill("10:00")
        change.get_by_role("button", name="Save the changes").click()
        change.wait_for(state="detached", timeout=WAIT_MS)
        _sent(stub, ("ops.standing_change", {"id": "st-1", "days": [0, 1, 2, 3, 4], "at": "10:00", "before": 20, "fields": fields}))
        expect(row).to_contain_text("Before the daily: weekdays 10:00", timeout=WAIT_MS)
        row.get_by_role("button", name="Stop").click()
        _sent(stub, ("ops.standing_stop", {"id": "st-1"}))
        row.wait_for(state="detached", timeout=WAIT_MS)
    _run(host, body)


def test_forget_asks_once_and_removes_everything_kept_of_that_value(host):
    stub = host.ops
    alex = stub.seed("one-on-one", "done", fields={"who": "Alex"}, draft={"agenda": AGENDA})
    sam = stub.seed("one-on-one", "done", fields={"who": "Sam"}, draft={"agenda": "Sam's"})

    def body(pg, stub):
        _operations(pg)
        _templates(pg)
        pg.get_by_role("button", name="Forget: Before a 1:1").click()
        dlg = _dialog(pg, "Forget: Before a 1:1")
        ask = dlg.get_by_role("button", name="Forget…")
        assert ask.is_disabled()
        dlg.get_by_label("Who").fill(" alex ")
        ask.click()
        question = dlg.get_by_role("alert")
        assert " ".join(question.inner_text().split()) == "Forget everything kept about alex in Before a 1:1? This cannot be undone."
        assert not [s for s in stub.sent if s[0] == "ops.forget"]                     # nothing yet: it asks first
        dlg.get_by_role("button", name="Forget everything").click()
        dlg.wait_for(state="detached", timeout=WAIT_MS)
        _sent(stub, ("ops.forget", {"template": "one-on-one", "value": "alex"}))
        pg.get_by_text("Forgot alex: 1 removed from Before a 1:1").wait_for(timeout=WAIT_MS)
        pg.get_by_text("Done (1)").click()
        assert pg.locator(f".board-op[data-op={alex}]").count() == 0 and pg.locator(f".board-op[data-op={sam}]").count() == 1
    _run(host, body)


def test_the_gear_keeps_the_last_1_1_brief_n_days(host):
    def body(pg, stub):
        _operations(pg)
        pg.get_by_role("button", name="Operations settings").click()
        gear = _dialog(pg, "Operations settings")
        days = gear.get_by_label("Days the last 1:1 brief is kept")
        assert days.input_value() == "90"
        assert " ".join(gear.locator("[data-setting=follow_days]").inner_text().split()) == "Keep the last 1:1 brief for days"
        days.fill("400")                                                                 # past 365: not sent
        days.blur()
        days.fill("60")
        days.blur()
        _sent(stub, ("ops.set", {"follow_days": 60}))
        assert stub.settings["follow_days"] == 60 and not [s for s in stub.sent if s == ("ops.set", {"follow_days": 400})]
    _run(host, body)
