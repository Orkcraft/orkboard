"""Operations on the desktop, in a real browser (docs/specs/38-operations.md §10, Tests → B; 1 440 × 900), against a stub
host: Orkboard's real host and server with `ops.*` answered from memory by `StubOps` (the backend has its own tests). Operations
in the goal select; New… with a template that is not connected; the Jira form, its check (found, a doubt, Priority changed in
place, Epic changed turns the button into Prepare again) and **Create in Jira**; *by itself* and Not right; a rules proposal
taken in its row; the gear; Needs you's `op` row in another project; the start screen."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
expect = playwright.expect

from orkboard.core.op_commands import OpsError  # noqa: E402
from orkboard.gui.board_host import Orkboard  # noqa: E402
from orkboard.gui.server import Server  # noqa: E402
from tests.browser_kit import WAIT_MS, launch  # noqa: E402

pytestmark = pytest.mark.browser

JIRA = {"name": "jira-task", "title": "New Jira task", "risk": "medium", "act_label": "Create in Jira", "state": "checks",
        "state_words": "checks with you", "clean": 0, "why": "",
        "fields": [{"name": "what", "label": "What needs doing", "type": "long", "required": True, "hint": "What is wrong or wanted"},
                   {"name": "project", "label": "Project", "type": "text", "remember": True, "hint": "Its key or its name", "default": "SHOP"},
                   {"name": "priority", "label": "Priority", "type": "choice", "options": ["Highest", "High", "Medium", "Low", "Lowest"],
                    "default": "Medium", "at": "additional_fields.priority.name"},
                   {"name": "epic", "label": "Epic", "type": "text", "hint": "A key or words of its name"}],
        "draft": [{"name": "summary", "label": "Title", "type": "text", "at": "summary"},
                  {"name": "description", "label": "Description", "type": "long", "at": "description"}]}
MAIL = {"name": "email-reply", "title": "Email reply", "risk": "medium", "act_label": "Save as a draft in Gmail", "state": "alone",
        "state_words": "goes by itself", "clean": 3, "why": "",
        "fields": [{"name": "about", "label": "Which mail", "type": "text", "required": True}],
        "draft": [{"name": "body", "label": "Reply", "type": "long", "at": "body"}]}
CAL = {"name": "calendar-note", "title": "Calendar note", "risk": "low", "act_label": "Add to the calendar", "state": "checks",
       "state_words": "checks with you", "clean": 0, "why": "", "unusable": "Calendar is not connected", "fields": [], "draft": []}
GIT = ["git", "-c", "user.email=test@orkcraft.local", "-c", "user.name=Test Runner"]


class StubOps:
    """What `gui/ops.py` `Ops` is to the host, kept in memory; the test plays the model with `prepared`."""

    def __init__(self, host) -> None:
        self.host, self.rev, self.n = host, 0, 0
        self.templates = [dict(t) for t in (JIRA, MAIL, CAL)]
        self.runs: list[dict] = []
        self.settings = {"target": "balance", "trust_after": 3, "daily_alone": 20, "keep_days": 14, "servers": {}}
        self.sent: list[tuple[str, dict]] = []                                  # every command the page sent: (name, args)
        self.names = ["claude.ai Jira", "claude.ai Gmail"]

    # -- the host's side of Operations ------------------------------------------------------------------------------
    def commands(self):
        return {name: (lambda a, name=name: self.call(name, a)) for name in (
            "ops.list", "ops.add", "ops.prepare", "ops.act", "ops.drop", "ops.stop", "ops.retry", "ops.again", "ops.not_right",
            "ops.rules", "ops.rules_save", "ops.rules_answer", "ops.trust_reset", "ops.servers", "ops.set")}

    def needs(self):
        out = []
        for r in self.runs:
            base = {"op": r["id"], "template": r["template"], "title": r["title"], "priority": "normal", "blocks": False, "at": r["at"]}
            if r["state"] == "check":
                out.append({**base, "kind": "op", "text": r["draft"].get("summary", r["title"]), "why": r["why"]})
            elif r["state"] == "failed":
                out.append({**base, "kind": "op_failed", "text": r["why"], "acted": r["acted"]})
        for t in self.templates:
            if t.get("proposal"):
                out.append({"kind": "op_rules", "template": t["name"], "title": t["title"], "op": "", "text": t["proposal"]["lines"][0],
                            "lines": t["proposal"]["lines"], "priority": "normal", "blocks": False, "at": ""})
        return out

    def count(self):
        return sum(1 for n in self.needs() if n["kind"] != "op_rules")

    def tick(self, now=None): ...
    def stop_all(self): return 0
    def close(self): ...

    # -- the test plays the model -----------------------------------------------------------------------------------
    def changed(self):
        def go():
            self.rev += 1
            self.host.bus.publish("ops.changed", id="", template="")
        self.host.call(go)

    def run(self, id):
        return next(r for r in self.runs if r["id"] == id)

    def seed(self, template, state, **more) -> str:
        t = next(t for t in self.templates if t["name"] == template)
        self.n += 1
        self.runs.append({"id": f"op{self.n}", "template": template, "state": state, "title": t["title"], "found": [], "draft": {},
                          "fields": {}, "doubts": [], "alone": False, "link": "", "why": "", "acted": False, "held_until": "",
                          "cost": 0.01, "at": "2026-10-18T09:30:00", "done_at": "", "step": "", **more})
        self.changed()
        return f"op{self.n}"

    def prepared(self, id, **more):
        self.run(id).update(state="check", found=[{"label": "Epic", "value": "SHOP-12 Checkout"}], doubts=["Maybe a duplicate of SHOP-80"],
                            draft={"summary": "Checkout fails on a full cart", "description": "Pay is pressed and nothing happens."}, **more)
        self.changed()

    def done(self, id):
        self.run(id).update(state="done", link="https://jira.example/browse/SHOP-101", done_at="2026-10-18T09:40:00")
        self.changed()

    # -- the commands -----------------------------------------------------------------------------------------------
    def call(self, name, a):
        if name != "ops.list":
            self.sent.append((name, dict(a)))
        return getattr(self, "_" + name.split(".", 1)[1])(a)

    def _list(self, a):
        return {"templates": self.templates, "runs": self.runs, "settings": self.settings, "servers_needed": {"jira": "Jira"}}

    def _add(self, a):
        t = next(t for t in self.templates if t["name"] == a["template"])
        if t.get("unusable"):
            raise OpsError(t["unusable"])
        run = self.seed(a["template"], "preparing", fields=dict(a.get("fields") or {}))
        return {"id": run}

    def _prepare(self, a):
        self.run(a["id"]).update(state="preparing", fields={**self.run(a["id"])["fields"], **(a.get("fields") or {})}, doubts=[])
        self.changed()
        return {"ok": True}

    def _act(self, a):
        r = self.run(a["id"])
        t = next(t for t in self.templates if t["name"] == r["template"])
        for f in t["fields"]:
            if f["name"] in (a.get("fields") or {}) and not f.get("at"):
                raise OpsError(f"{f['label']} changed: Prepare again first")
        r.update(state="acting", fields={**r["fields"], **(a.get("fields") or {})}, draft={**r["draft"], **(a.get("draft") or {})})
        self.changed()
        return {"ok": True}

    def _drop(self, a):
        self.run(a["id"])["state"] = "dropped"
        self.runs[:] = [r for r in self.runs if r["state"] != "dropped"]
        self.changed()
        return {"ok": True}

    def _stop(self, a):
        self.run(a["id"]).update(state="failed", why="stopped", acted=False)
        self.changed()
        return {"ok": True}

    def _retry(self, a):
        self.run(a["id"]).update(state="preparing", why="")
        self.changed()
        return {"ok": True}

    def _again(self, a):
        return {"id": self.seed(self.run(a["id"])["template"], "preparing")}

    def _not_right(self, a):
        self.run(a["id"])["alone"] = False
        next(t for t in self.templates if t["name"] == self.run(a["id"])["template"]).update(state="checks", state_words="checks with you")
        self.changed()
        return {"ok": True}

    def _rules(self, a):
        return {"text": "Always name the epic."}

    def _rules_save(self, a):
        if len(a["text"]) > 4000:
            raise OpsError("The rules are longer than 4000 characters")
        return {"ok": True}

    def _rules_answer(self, a):
        next(t for t in self.templates if t["name"] == a["template"]).pop("proposal", None)
        self.changed()
        return {"ok": True}

    def _trust_reset(self, a):
        next(t for t in self.templates if t["name"] == a["template"]).update(state="checks", state_words="checks with you", clean=0)
        self.changed()
        return {"ok": True}

    def _servers(self, a):
        return {"servers": self.names}

    def _set(self, a):
        for key in ("target", "trust_after", "daily_alone"):
            if key in a:
                self.settings[key] = a[key]
        for key, name in (a.get("servers") or {}).items():
            if name:
                self.settings["servers"][key] = name
            else:
                self.settings["servers"].pop(key, None)
        self.changed()
        return self.settings


def _repo(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / "README.md").write_text("# " + path.name + "\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run([*GIT, "add", "-A"], cwd=path, check=True)
    subprocess.run([*GIT, "commit", "-qm", "init"], cwd=path, check=True)
    return path


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Orkboard on `shop` with a stub Operations: (host, stub, shop, blog)."""
    for key, value in {"ORKCRAFT_SETTINGS_FILE": tmp_path / "settings.json", "ORKCRAFT_ONBOARDING": "0",
                       "ORKCRAFT_LIMITS": "0", "ORKCRAFT_NO_UPDATE": "1", "XDG_CONFIG_HOME": tmp_path / "config"}.items():
        monkeypatch.setenv(key, str(value))
    shop, blog = _repo(tmp_path / "shop"), _repo(tmp_path / "blog")
    return _host(Orkboard(shop)), shop, blog


def _host(host):
    host.ops.close()
    stub = StubOps(host)
    host.ops = stub
    host.commands.update(stub.commands())
    return host


def _run(host, body, wait=".shell"):
    server = Server(host)
    thread = server.start_thread()
    with playwright.sync_playwright() as p:
        browser = launch(p)
        try:
            pg = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
            errors: list[str] = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(server.url)
            pg.locator(wait).wait_for(timeout=WAIT_MS)
            body(pg, host.ops)
            assert not errors, errors
        finally:
            browser.close()
            server.stop()
            thread.join(10)


def _sent(stub, want):
    """The page's last command to Operations is `want`: (name, args), waited for (a command goes by the socket)."""
    deadline = time.monotonic() + WAIT_MS / 1000
    while stub.sent[-1:] != [want] and time.monotonic() < deadline:
        time.sleep(0.05)
    assert stub.sent[-1:] == [want]


def _operations(pg):
    pg.get_by_label("Goal", exact=True).select_option("@operations")
    pg.locator(".board-ops").wait_for(timeout=WAIT_MS)


def _dialog(pg, name):
    dlg = pg.get_by_role("dialog", name=name)
    dlg.wait_for(timeout=WAIT_MS)
    return dlg


def test_a_held_run_says_why_the_limits_or_the_days_spend_cap(world):
    def body(pg, stub):
        _operations(pg)
        limits = stub.seed("jira-task", "held", held_until="2026-10-18T18:00:00")
        cap = stub.seed("email-reply", "held", held_until="2026-10-19T00:00:00", why="waits: the day's spend cap is reached")
        row = pg.locator(f".board-op[data-op={limits}]")
        row.wait_for(timeout=WAIT_MS)
        assert "waits for limits · after 18:00" in row.inner_text()
        assert "waits: the day's spend cap is reached" in pg.locator(f".board-op[data-op={cap}]").inner_text()
    _run(world[0], body)


def test_operations_is_in_the_goal_select_and_new_lists_the_templates(world):
    def body(pg, stub):
        select = pg.get_by_label("Goal", exact=True)
        assert select.locator("option").last.inner_text() == "Operations"           # last, after a divider
        assert pg.get_by_role("button", name="New idea").count() == 1 and pg.get_by_role("button", name="Target:", exact=False).count() == 1
        _operations(pg)
        assert pg.get_by_role("button", name="New idea").count() == 0               # New… takes the place of New idea and the Target
        assert pg.locator(".board-target__chip").count() == 0
        pg.get_by_role("button", name="New…").click()
        menu = pg.get_by_role("menu", name="New operation")
        assert [i.inner_text() for i in menu.get_by_role("menuitem").all()] == ["New Jira task", "Email reply"]
        off = menu.locator("[data-unusable]")
        assert "Calendar note" in off.inner_text() and "Calendar is not connected" in off.inner_text()
    _run(world[0], body)


def test_the_jira_form_adds_one_its_check_changes_and_create_in_jira_does_it(world):
    def body(pg, stub):
        _operations(pg)
        pg.get_by_role("button", name="New…").click()
        pg.get_by_role("menuitem", name="New Jira task").click()
        form = _dialog(pg, "New Jira task")
        assert form.get_by_label("Project").input_value() == "SHOP"                 # remembered, prefilled
        assert form.get_by_label("What needs doing").get_attribute("placeholder") == "What is wrong or wanted"
        add = form.get_by_role("button", name="Add")
        assert add.is_disabled()                                                    # a required field is empty
        form.get_by_label("What needs doing").fill("Checkout fails on a full cart")
        add.click()
        form.wait_for(state="detached", timeout=WAIT_MS)
        _sent(stub, ("ops.add", {"template": "jira-task", "fields": {"what": "Checkout fails on a full cart", "project": "SHOP", "priority": "Medium"}}))
        running = pg.get_by_role("region", name="Running")
        assert "preparing" in running.inner_text()
        op = stub.runs[0]["id"]
        stub.prepared(op)
        row = pg.locator(f".board-need[data-op={op}]")
        row.wait_for(timeout=WAIT_MS)
        assert "Checkout fails on a full cart" in row.inner_text() and "at your check" in row.inner_text()
        assert pg.get_by_role("region", name="Running").count() == 0
        row.click()
        check = _dialog(pg, "New Jira task")
        assert "SHOP-12 Checkout" in check.get_by_role("group", name="What was found").inner_text()
        assert "Maybe a duplicate of SHOP-80" in check.get_by_label("Doubts").inner_text()
        button = check.locator("[data-act]")
        assert button.inner_text() == "Create in Jira"
        check.get_by_label("Priority").select_option("High")                        # in place: the button stays
        assert button.inner_text() == "Create in Jira"
        check.get_by_label("Epic").fill("Payments")                                 # not in place: Prepare again
        assert button.inner_text() == "Prepare again"
        check.get_by_label("Epic").fill("")
        assert button.inner_text() == "Create in Jira"
        check.get_by_label("Title").fill("Checkout fails with a full cart")
        button.click()
        check.wait_for(state="detached", timeout=WAIT_MS)
        _sent(stub, ("ops.act", {"id": op, "fields": {"priority": "High"}, "draft": {"summary": "Checkout fails with a full cart"}}))
        pg.get_by_text("doing it").wait_for(timeout=WAIT_MS)
        stub.done(op)
        pg.get_by_text("Done (1)").click()
        link = pg.locator(f".board-op[data-op={op}] .board-link")
        link.wait_for(timeout=WAIT_MS)
        assert link.inner_text() == "jira.example/browse/SHOP-101"
    _run(world[0], body)


def test_prepare_again_sends_the_changed_field_and_the_form_keeps_what_was_typed(world):
    def body(pg, stub):
        _operations(pg)
        pg.get_by_role("button", name="New…").click()
        pg.get_by_role("menuitem", name="New Jira task").click()
        form = _dialog(pg, "New Jira task")
        form.get_by_label("What needs doing").fill("half typed")
        pg.keyboard.press("Escape")                                                 # closed with typed text: kept for the next opening
        form.wait_for(state="detached", timeout=WAIT_MS)
        assert not [s for s in stub.sent if s[0] == "ops.add"]
        pg.get_by_role("button", name="New…").click()
        pg.get_by_role("menuitem", name="New Jira task").click()
        form = _dialog(pg, "New Jira task")
        assert form.get_by_label("What needs doing").input_value() == "half typed"
        form.get_by_label("What needs doing").fill("")
        pg.keyboard.press("Escape")                                                 # closed empty: nothing kept
        pg.get_by_role("button", name="New…").click()
        pg.get_by_role("menuitem", name="New Jira task").click()
        assert _dialog(pg, "New Jira task").get_by_label("What needs doing").input_value() == ""
        pg.keyboard.press("Escape")
        op = stub.seed("jira-task", "check", fields={"what": "x", "epic": ""})
        stub.prepared(op)
        pg.locator(f".board-need[data-op={op}]").click()
        check = _dialog(pg, "New Jira task")
        check.get_by_label("Epic").fill("Payments")
        check.get_by_role("button", name="Prepare again").click()
        check.wait_for(state="detached", timeout=WAIT_MS)
        _sent(stub, ("ops.prepare", {"id": op, "fields": {"epic": "Payments"}, "draft": {}}))
    _run(world[0], body)


def test_a_failed_one_offers_what_may_be_done_and_a_stopped_one_stops(world):
    def body(pg, stub):
        _operations(pg)
        before = stub.seed("jira-task", "failed", why="Jira refused it: no such project", acted=False)
        after = stub.seed("jira-task", "failed", why="stopped while doing it: look in Jira before you add it again", acted=None)
        failed = pg.get_by_role("region", name="Failed")
        failed.wait_for(timeout=WAIT_MS)
        one, two = failed.locator(f"[data-op={before}]"), failed.locator(f"[data-op={after}]")
        assert "no such project" in one.inner_text()
        assert one.get_by_role("button", name="Try again").count() == 1 and two.get_by_role("button", name="Try again").count() == 0
        assert two.get_by_role("button", name="Add again").count() == 1 and two.get_by_role("button", name="Drop").count() == 1
        two.get_by_role("button", name="Drop").click()
        two.wait_for(state="detached", timeout=WAIT_MS)
        run = stub.seed("jira-task", "preparing")
        pg.locator(f"[data-op={run}]").get_by_role("button", name="Stop").click()
        pg.locator(f"[data-op={run}][data-state=failed]").wait_for(timeout=WAIT_MS)
    _run(world[0], body)


def test_by_itself_shows_and_not_right_teaches_and_check_again_resets(world):
    def body(pg, stub):
        _operations(pg)
        op = stub.seed("email-reply", "done", alone=True, link="https://mail.example/d/1", done_at="2026-10-18T09:41:00")
        pg.get_by_text("Done (1)").click()
        row = pg.locator(f".board-op[data-op={op}]")
        row.wait_for(timeout=WAIT_MS)
        assert row.locator("[data-by-itself]").inner_text() == "by itself"
        row.get_by_role("button", name="Not right").click()
        row.get_by_label("What was not right: Email reply").fill("Too long")
        row.get_by_role("button", name="Teach it").click()
        _sent(stub, ("ops.not_right", {"id": op, "why": "Too long"}))
        pg.locator(f".board-op[data-op={op}] [data-by-itself]").wait_for(state="detached", timeout=WAIT_MS)
        assert pg.locator(f".board-op[data-op={op}]").get_by_role("button", name="Not right").count() == 0
        stub.templates[1].update(state="alone", state_words="goes by itself")
        stub.changed()
        pg.get_by_text("Templates (3)").click()
        mail = pg.locator(".board-op--template[data-template=email-reply]")
        expect(mail).to_contain_text("goes by itself", timeout=WAIT_MS)                # after ops_rev moves, not before
        assert "save as a draft in gmail without asking you" in mail.inner_text()
        assert "checks with you" in pg.locator(".board-op--template[data-template=jira-task]").inner_text()
        assert pg.locator(".board-op--template[data-template=jira-task]").get_by_role("button", name="Check again").count() == 0
        mail.get_by_role("button", name="Check again").click()
        _sent(stub, ("ops.trust_reset", {"template": "email-reply"}))
        pg.locator(".board-op--template[data-template=email-reply] [data-template-state=checks]").wait_for(timeout=WAIT_MS)
    _run(world[0], body)


def test_a_rules_proposal_is_taken_in_its_row_in_needs_you_and_the_rules_are_saved(world):
    stub = world[0].ops
    stub.templates[1]["proposal"] = {"lines": ["Keep a reply under five lines"], "why": "you shortened two replies", "op": "op1", "at": ""}

    def body(pg, stub):
        row = pg.locator(".board-proposal[data-kind=op_rules]")
        row.wait_for(timeout=WAIT_MS)
        assert "Keep a reply under five lines" in row.inner_text()
        assert pg.locator(".shell-count").count() == 0                              # a proposal is no count
        row.get_by_role("button", name="Take").click()
        _sent(stub, ("ops.rules_answer", {"template": "email-reply", "take": True}))
        row.wait_for(state="detached", timeout=WAIT_MS)
        _operations(pg)
        pg.get_by_text("Templates (3)").click()
        pg.get_by_role("button", name="Rules: Email reply").click()
        rules = _dialog(pg, "Rules: Email reply")
        expect(rules.get_by_label("Rules")).to_have_value("Always name the epic.", timeout=WAIT_MS)   # read by ops.rules
        rules.get_by_label("Rules").fill("Be brief.")
        rules.get_by_role("button", name="Save the rules").click()
        rules.wait_for(state="detached", timeout=WAIT_MS)
        _sent(stub, ("ops.rules_save", {"template": "email-reply", "text": "Be brief."}))
    _run(world[0], body)


def test_a_proposal_can_be_declined_with_a_reason(world):
    stub = world[0].ops
    stub.templates[0]["proposal"] = {"lines": ["Always add a label"], "why": "", "op": "op1", "at": ""}

    def body(pg, stub):
        _operations(pg)
        pg.get_by_text("Templates (3)").click()
        row = pg.locator(".board-op--template[data-template=jira-task] .board-op-rules")
        row.get_by_role("button", name="No rules: New Jira task").click()
        row.get_by_label("Why not: New Jira task").fill("Not for bugs")
        row.get_by_role("button", name="Decline the rules: New Jira task").click()
        _sent(stub, ("ops.rules_answer", {"template": "jira-task", "take": False, "reason": "Not for bugs"}))
    _run(world[0], body)


def test_the_gear_sets_the_target_the_checks_and_a_server(world):
    def body(pg, stub):
        _operations(pg)
        pg.get_by_role("button", name="Operations settings").click()
        gear = _dialog(pg, "Operations settings")
        gear.get_by_text("Quality", exact=True).click()
        pg.wait_for_function("() => document.querySelector('.shell-seg__one.is-on')?.textContent.includes('Quality')")
        _sent(stub, ("ops.set", {"target": "quality"}))
        gear.get_by_label("Clean checks before it goes by itself").fill("2")
        gear.get_by_label("Clean checks before it goes by itself").blur()
        _sent(stub, ("ops.set", {"trust_after": 2}))
        select = gear.get_by_label("Jira server")
        expect(select.locator("option")).to_have_text(["not connected", "claude.ai Jira", "claude.ai Gmail"],
                                                      timeout=WAIT_MS)              # read by ops.servers
        select.select_option("claude.ai Jira")
        _sent(stub, ("ops.set", {"servers": {"jira": "claude.ai Jira"}}))
        select.select_option("")
        _sent(stub, ("ops.set", {"servers": {"jira": ""}}))
        assert stub.settings["target"] == "quality" and stub.settings["trust_after"] == 2
    _run(world[0], body)


def test_needs_you_shows_an_op_row_in_another_project_too(world):
    host, shop, blog = world
    stub = host.ops
    op = stub.seed("jira-task", "check", draft={"summary": "Checkout fails on a full cart"})
    failed = stub.seed("jira-task", "failed", why="Jira refused it", acted=False)

    def body(pg, stub):
        row = pg.locator(f".board-need[data-kind=op]")
        row.wait_for(timeout=WAIT_MS)
        assert "Checkout fails on a full cart" in row.inner_text()
        assert pg.locator(".board-need[data-kind=op_failed]").count() == 1
        pg.keyboard.press("Control+o")
        dlg = _dialog(pg, "Open folder")
        dlg.get_by_label("Folder").fill(str(blog))
        dlg.get_by_role("button", name="Open folder").click()
        dlg.wait_for(state="detached", timeout=WAIT_MS)
        pg.locator(".shell-proj__btn", has_text="blog").wait_for(timeout=WAIT_MS)
        row = pg.locator(".board-need[data-kind=op]")                               # the person's: seen in every project
        row.wait_for(timeout=WAIT_MS)
        row.click()
        check = _dialog(pg, "New Jira task")
        assert check.locator(f"[data-op={op}]").count() == 1
        pg.keyboard.press("Escape")
        pg.locator(".board-need[data-kind=op_failed]").click()
        assert "Jira refused it" in _dialog(pg, "Failed: New Jira task").inner_text()
    _run(world[0], body)


def test_the_start_screen_offers_operations(tmp_path, monkeypatch):
    for key, value in {"ORKCRAFT_SETTINGS_FILE": tmp_path / "settings.json", "ORKCRAFT_ONBOARDING": "0",
                       "ORKCRAFT_LIMITS": "0", "ORKCRAFT_NO_UPDATE": "1", "XDG_CONFIG_HOME": tmp_path / "config"}.items():
        monkeypatch.setenv(key, str(value))
    host = _host(Orkboard())

    def body(pg, stub):
        pg.locator(".shell-start .board-ops").wait_for(timeout=WAIT_MS)
        pg.get_by_role("button", name="New…").click()
        assert pg.get_by_role("menuitem", name="Email reply").count() == 1
    _run(host, body, wait=".shell-start")
