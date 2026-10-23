"""Spec 62, the desktop (docs/specs/62-spec-after-start.md §5, §6; Tests → B): Chromium at 1 440 × 900 against the one window's stub host (tests/test_arena_desktop_browser.py)
whose goal *Export the passkeys* is at work and whose party is led by the Game designer. A goal's preview names the party's leader in its talk (*Ask or answer Game designer…*; *the
Taskmaster* for a party the Taskmaster leads); a spec whose plan-making sections changed says so under its sections (*Re-plan* before the start, *Re-plan what is left* after it);
the leader's plan change is a stop in the hand (*Plan change*: its gem, its text, its why; *Take the new plan* deals the tasks it adds, *Keep the plan*), and the plan screen shows
**The change** over the plan while it waits."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from orkboard.realm import idea_change  # noqa: E402
from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import ArenaHost, pip  # noqa: E402
from tests.test_deal_start_desktop_browser import RECORD, _centre, _ms, _seen  # noqa: E402
from tests.test_map_desktop_browser import node  # noqa: E402
from tests.test_shell_browser import _drawer, _sent, _stop  # noqa: E402

pytestmark = pytest.mark.browser

DESIGNER = {"slug": "game-designer", "name": "Game designer", "head": {"craft": "design", "race": "elf", "tier": "elder"}}
WHY = "The export is csv only: the streaming task goes, a progress screen and a check come."
ROWS = [{"op": "add", "id": "", "title": "Progress screen"}, {"op": "add", "id": "", "title": "Check the export"},
        {"op": "change", "id": "x2", "title": "Write csv"}, {"op": "drop", "id": "x3", "title": "Stream rows"}]


def _summary(**more) -> dict:
    """A plan change as `ideas.page` and the stop carry it (spec 62 §2.4): 2 added, 1 changed, 1 dropped, +$0.40–1.20."""
    return {"made_at": "2026-10-23T11:00:00", "why": WHY, "added": 2, "changed": 1, "dropped": 1, "usd_low": 0.4, "usd_high": 1.2, "rows": ROWS} | more


class ChangeHost(ArenaHost):
    """The passkey party with a goal at work (*Export the passkeys*: a task at work, one waiting, one that waits for it) whose spec changed, and the plan change of the leader.
    `leader`: who leads the party (the Game designer); `change`: the plan change that waits (its summary), else None."""

    def __init__(self, leader=DESIGNER):
        super().__init__()
        self.leader, self.change, self.revising, self.busy, self.done, self.refuse, self.left = leader, None, False, False, False, {}, []
        self.talk: list[dict] = []
        self.track = "passkey"                                                                       # the party the page says its goal is in
        self.state = {"export": {"changed": ["Gist", "Out"], "passed": True}, "recovery": {"changed": ["Gist", "Done when"], "passed": False}}
        tasks = [pip("x1", "Read the export code", "merged", by="backend"), pip("x2", "Write csv", "running", ["x1"], 2, "backend"),
                 pip("x3", "Stream rows", "waiting", ["x2"], 3, "backend")]
        self.nodes.append(node("export", "passkey", "Export the passkeys", "working", 1, stage="implementation", tasks=tasks, progress={"done": 1, "total": 3}, usd=0.5,
                               plan_estimate={"usd_low": 0.5, "usd_high": 1.0}, element="meadow", flag=None))
        self.ideas["export"] = self.idea("export", "Export the passkeys", "working", 20, track="passkey")
        self.added = [pip("k4", "Progress screen", "waiting", ["x2"], 3, "screens"), pip("k5", "Check the export", "waiting", ["k4"], 4, "reviewer", "check")]

    # -- the page and the Map ------------------------------------------------------------------------------------------------------------

    def page(self, slug):
        got = super().page(slug)
        if "error" in got or slug not in self.state:
            return got
        plan = {**self.plan, "idea": slug, "estimate": {"tasks": 3, "usd_low": 0.5, "usd_high": 1.0}, "todos": [], "missing": [],
                "tasks": list(self.node_of(slug)["tasks"]) if slug == "export" else self.plan["tasks"][:3]}
        got |= {"track": self.track, "state": "done" if self.done else "working" if slug == "export" else "plan", "plan": plan, "talk": self.talk, "busy": self.busy, "revising": self.revising,
                "change": self.change if slug == "export" else None, **self.state[slug]}
        return got

    def map_doc(self):
        doc = super().map_doc()
        for g in doc["goals"]:
            if g["slug"] == "passkey" and self.leader:
                g["leader"] = self.leader
                g["party"] = [{**self.leader, "band": "lead", "state": "free", "why": ""}, *g["party"][1:]]
        return doc

    def needs_you(self):
        rows = super().needs_you()
        if not self.change:
            return rows
        c = self.change
        return [*rows, {"kind": "change", "idea": "export", "goal": "passkey", "title": "Export the passkeys", "priority": "high", "blocks": False, "at": c["made_at"],
                        "text": idea_change.text_of(c), "why": c["why"], "added": c["added"], "changed": c["changed"], "dropped": c["dropped"],
                        "usd_low": c["usd_low"], "usd_high": c["usd_high"]}]

    def propose(self, change):
        """The leader has re-planned what is left: the change waits (the Map's node says so), the keeper is free."""
        self.change, self.revising, self.busy = change, False, False
        self.node_of("export")["needs_you"] = "change"
        self.bump({})

    # -- the commands --------------------------------------------------------------------------------------------------------------------

    def handle(self, name, a):
        if name in ("ideas.plan", "ideas.revise", "ideas.revise_answer", "ideas.say"):
            self.log.append((name, a))
            if name in self.refuse:
                return {"error": self.refuse[name]}
        if name == "ideas.revise":
            self.revising = self.busy = True
            return self.bump({"ok": True})
        if name == "ideas.revise_answer":
            c, self.change = self.change, None
            self.node_of("export")["needs_you"] = ""
            self.state["export"]["changed"] = []
            got = {"ok": True, "added": 0, "changed": 0, "dropped": 0, "left": []}
            if a["take"]:
                self.node_of("export")["tasks"] += self.added[:c["added"]]
                got |= {"added": c["added"], "changed": c["changed"], "dropped": c["dropped"], "left": self.left}
            return self.bump(got)
        if name in ("ideas.plan", "ideas.say"):
            return {"ok": True}
        return super().handle(name, a)


def _scene(gui, host, ready=".arena-hc[data-kind=plan]", **page):
    server, browser = gui
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, **page)
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    pg.wait_for_selector(ready, timeout=WAIT_MS)
    return pg, errors


@pytest.fixture
def changing(gui):
    """The party at work and a plan change that waits."""
    host = ChangeHost()
    host.propose(_summary())
    pg, errors = _scene(gui, host, ".arena-hc[data-kind=change]")
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


@pytest.fixture
def quiet(gui):
    """The party at work, its goal's spec changed, no plan change yet."""
    host = ChangeHost()
    pg, errors = _scene(gui, host)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _spec(pg, slug="export"):
    """A goal's spec in the drawer (the › on its row)."""
    pg.locator(f".arena-goal[data-slug={slug}] .arena-goal__open").click()
    pg.locator(".shell-preview .board-ideaview").wait_for(timeout=WAIT_MS)
    return pg.locator(".shell-preview")


def _line(pg):
    """The changed line under the sections: its words and its press."""
    line = pg.locator(".shell-preview .board-changed")
    line.wait_for(timeout=WAIT_MS)
    return line


def _toast(pg, text):
    pg.locator(".ok-toast", has_text=text).first.wait_for(timeout=WAIT_MS)


def _token(pg, name):
    """A colour token as the page computes it."""
    return pg.evaluate("(name) => { const d = document.createElement('span'); d.style.color = `var(${name})`; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; }", name)


# -- the talk names the leader (§5) -------------------------------------------------------------------------------------------------------

def test_the_talk_names_the_partys_leader(quiet):
    pg, host = quiet
    host.talk = [{"who": "you", "text": "Is csv enough?"}, {"who": "keeper", "text": "Yes: it is the only format asked for.", "section": "Out"}]
    host.bump({})
    spec = _spec(pg)
    ask = spec.get_by_role("textbox", name="Ask or answer Game designer")
    assert ask.get_attribute("placeholder") == "Ask or answer Game designer…"
    spec.get_by_role("button", name="Ask about Gist").click()
    assert ask.get_attribute("placeholder") == "About Gist…"                                          # a section keeps its own
    spec.get_by_role("button", name="Ask about the whole goal").click()
    talk = spec.get_by_role("list", name="The talk")
    assert talk.locator("li[data-who=keeper] .board-talk__who").inner_text() == "Game designer · Out" and talk.locator("li[data-who=you] .board-talk__who").inner_text() == "You"
    host.busy = True
    host.bump({})
    spec.get_by_text("Game designer is answering…").wait_for(timeout=WAIT_MS)
    ask.fill("Make it streaming")
    assert not spec.get_by_role("button", name="Ask", exact=True).is_enabled()                          # a talk is on: the press waits
    assert "the Taskmaster" not in spec.inner_text() and "The Taskmaster" not in spec.inner_text()


@pytest.mark.parametrize("leader, track", [(None, "passkey"), (DESIGNER, "ghost")])
def test_a_party_the_taskmaster_leads_or_the_map_does_not_know_says_the_taskmaster(gui, leader, track):
    host = ChangeHost(leader=leader)                                                                 # the Taskmaster leads the passkey party; or the page's party is not in the Map
    host.track = track
    host.talk = [{"who": "keeper", "text": "It is csv only.", "section": "Gist"}]
    pg, errors = _scene(gui, host)
    spec = _spec(pg)
    assert spec.get_by_role("textbox", name="Ask or answer the Taskmaster").get_attribute("placeholder") == "Ask or answer the Taskmaster…"
    assert spec.locator(".board-talk li[data-who=keeper] .board-talk__who").inner_text() == "The Taskmaster · Gist"
    host.busy = True
    host.bump({})
    spec.get_by_text("The Taskmaster is answering…").wait_for(timeout=WAIT_MS)                     # at a sentence's start: a capital
    host.state["export"]["changed"] = ["Gist"]
    host.revising = True
    host.bump({})
    spec.get_by_text("The Taskmaster re-plans what is left…").wait_for(timeout=WAIT_MS)
    pg.close()
    assert not errors, "\n".join(errors)


# -- the changed line (§6.1) --------------------------------------------------------------------------------------------------------------

def test_before_the_start_a_changed_spec_says_so_and_re_plan_sends_the_plan(quiet):
    pg, host = quiet
    pg.locator(".arena-goal[data-slug=recovery] .arena-goal__open").click()                           # its plan ready, not started: the plan screen, and from it the spec
    pg.get_by_role("button", name="Open the spec").click()
    pg.locator(".shell-preview .board-ideaview").wait_for(timeout=WAIT_MS)
    line = _line(pg)
    assert line.locator("p").inner_text() == "Gist and Done when changed since the plan."
    assert line.locator("button").inner_text() == "Re-plan" and line.get_attribute("data-passed") == "false"
    sections = pg.locator(".shell-preview .board-secs")                                              # under the sections, over the talk
    assert sections.bounding_box()["y"] < line.bounding_box()["y"] < pg.locator(".shell-preview .board-say").bounding_box()["y"]
    line.get_by_role("button", name="Re-plan").click()
    assert _sent(pg, host, ("ideas.plan", {"slug": "recovery"}))
    host.state["recovery"]["changed"] = ["Gist", "Done when", "Out"]                                  # three names: joined as the interface joins a list
    host.bump({})
    pg.get_by_text("Gist, Done when and Out changed since the plan.").wait_for(timeout=WAIT_MS)
    host.state["recovery"]["changed"] = []                                                           # a plan made again: nothing changed since it
    host.bump({})
    pg.locator(".shell-preview .board-changed").wait_for(state="detached", timeout=WAIT_MS)


def test_after_the_start_re_plan_what_is_left_asks_the_leader_then_waits_for_the_change(quiet):
    pg, host = quiet
    spec = _spec(pg)
    line = _line(pg)
    assert line.locator("p").inner_text() == "Gist and Out changed since the work started: the tasks not started may change."
    press = line.get_by_role("button", name="Re-plan what is left", exact=True)
    assert press.is_enabled() and line.get_attribute("data-passed") == "true"
    press.click()
    assert _sent(pg, host, ("ideas.revise", {"slug": "export"}))
    spec.get_by_text("Game designer re-plans what is left…").wait_for(timeout=WAIT_MS)             # the keeper works on it: the press is off
    assert not line.get_by_role("button", name="Re-plan what is left", exact=True).is_enabled()
    host.propose(_summary())
    spec.get_by_text("Game designer proposed a plan change: it waits for you below.").wait_for(timeout=WAIT_MS)
    again = line.get_by_role("button", name="Re-plan what is left again")
    assert again.is_enabled()
    again.click()
    assert [a for n, a in host.log if n == "ideas.revise"] == [{"slug": "export"}, {"slug": "export"}]


def test_a_refused_re_plan_is_shown_as_every_command_is_and_a_done_goal_says_nothing(quiet):
    pg, host = quiet
    host.refuse["ideas.revise"] = "The keeper is busy with this goal: a moment"
    spec = _spec(pg)
    _line(pg).get_by_role("button", name="Re-plan what is left").click()
    _toast(pg, "The keeper is busy with this goal: a moment")
    assert spec.get_by_text("re-plans what is left").count() == 0                                     # nothing was started
    host.done = True                                                                                 # a done goal: no line
    host.bump({})
    pg.locator(".shell-preview .board-changed").wait_for(state="detached", timeout=WAIT_MS)


def test_a_spec_that_has_not_changed_since_the_plan_has_no_line(quiet):
    pg, host = quiet
    host.state["export"]["changed"] = []
    spec = _spec(pg)
    assert spec.locator(".board-changed").count() == 0 and spec.get_by_role("button", name="Re-plan").count() == 0


# -- the stop in the hand (§6.2) ----------------------------------------------------------------------------------------------------------

def test_a_plan_change_is_a_stop_with_its_price_its_text_its_why_and_two_answers(changing):
    pg, host = changing
    stop = _stop(pg, "change")
    assert stop.locator(".arena-hc__kind").text_content() == "Plan change" and stop.locator(".ork-gem").inner_text() == "+$0.40–1.20"
    assert stop.locator(".ork-gem").get_attribute("title") == "What the change should cost, at API prices"
    assert stop.locator(".arena-hc__text").inner_text() == "The plan changes · +2 · 1 changed · −1"
    note = stop.locator(".arena-hc__note")
    assert note.inner_text() == WHY and note.evaluate("e => getComputedStyle(e).color") == _token(pg, "--ork-ink-muted")          # its why, under its text, muted
    assert stop.locator(".arena-banner").inner_text() == "Export the passkeys"
    buttons = stop.locator(".arena-hc__quick button")
    assert buttons.all_inner_texts() == ["Take the new plan", "Keep the plan"] and "primary" in buttons.first.get_attribute("class")
    card, top, quick, kind = stop.bounding_box(), stop.locator(".arena-hc__top").bounding_box(), stop.locator(".arena-hc__quick").bounding_box(), stop.locator(".arena-hc__kind")
    assert kind.evaluate("e => e.scrollWidth <= e.clientWidth")                                      # the kind's word is whole, not cut by the price
    assert stop.locator(".arena-hc__text").bounding_box()["y"] + stop.locator(".arena-hc__text").bounding_box()["height"] <= note.bounding_box()["y"]       # text, then why, then the answers
    assert note.bounding_box()["y"] + note.bounding_box()["height"] <= quick["y"] and top["y"] >= card["y"] and quick["y"] + quick["height"] <= card["y"] + card["height"]
    assert pg.locator(".arena-goal[data-slug=export] .arena-goal__mark").get_attribute("title") == "waits for you"      # its goal's row waits for the person too


def test_a_change_that_saves_says_so_with_the_real_minus_and_one_of_nothing_has_no_gem(gui):
    host = ChangeHost()
    host.propose(_summary(added=0, changed=0, dropped=1, usd_low=-0.13, usd_high=-0.38))
    pg, errors = _scene(gui, host, ".arena-hc[data-kind=change]")
    stop = _stop(pg, "change")
    assert stop.locator(".ork-gem").inner_text() == "−$0.13–0.38" and stop.locator(".arena-hc__text").inner_text() == "The plan changes · −1"
    assert stop.locator(".ork-gem").get_attribute("title") == "What the change should save, at API prices"
    host.propose(_summary(added=0, changed=0, dropped=0, usd_low=0.0, usd_high=0.0, rows=[], why="Nothing needs to change."))
    pg.wait_for_function("() => document.querySelector('.arena-hc[data-kind=change] .arena-hc__text')?.innerText === 'The plan stays as it is'", timeout=WAIT_MS)
    stop = _stop(pg, "change")
    assert stop.locator(".ork-gem").count() == 0 and stop.locator(".arena-hc__note").inner_text() == "Nothing needs to change."
    host.propose(_summary(usd_low=2.0, usd_high=6.0))                                               # whole dollars from $1 up, as a goal's price is said
    pg.wait_for_function("() => document.querySelector('.arena-hc[data-kind=change] .ork-gem')?.innerText === '+$2–6'", timeout=WAIT_MS)
    pg.close()
    assert not errors, "\n".join(errors)


def test_a_change_without_a_why_has_no_note_and_a_press_elsewhere_opens_the_plan_screen(gui):
    host = ChangeHost()
    host.propose(_summary(why=""))
    pg, errors = _scene(gui, host, ".arena-hc[data-kind=change]")
    stop = _stop(pg, "change")
    assert stop.locator(".arena-hc__note").count() == 0
    stop.locator(".arena-hc__open").click()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "plan", "ref": "export", "device": "desktop", "via": "hand"}))
    _drawer(pg).locator(".shell-change").wait_for(timeout=WAIT_MS)                                  # the plan screen, with The change over the plan
    pg.close()
    assert not errors, "\n".join(errors)


def test_while_a_plan_change_is_looked_at_its_goals_cards_are_ringed(changing):
    pg, host = changing
    _stop(pg, "change")                                                                              # raised by the focus: looked at (spec 58 §2)
    pg.wait_for_function("() => document.querySelector('.arena-stk.is-linked')", timeout=WAIT_MS)
    keys = pg.evaluate("() => [...document.querySelectorAll('.arena-stk.is-linked')].map((s) => s.querySelector('.arena-task').dataset.key)")
    assert keys and all(k.startswith("export/") for k in keys)                                       # the goal's cards and no other
    assert "its goal is ringed on the field" in pg.locator(".arena-hc[data-kind=change] [id^=link-]").text_content()


def test_keep_the_plan_sends_the_answer_from_the_hand_and_says_the_plan_stays(changing):
    pg, host = changing
    _stop(pg, "change").get_by_role("button", name="Keep the plan").click()
    assert _sent(pg, host, ("ideas.revise_answer", {"slug": "export", "take": False, "via": "hand"}))
    _toast(pg, "The plan stays as it was.")
    pg.locator(".arena-hc[data-kind=change]:not(.is-leaving)").wait_for(state="detached", timeout=WAIT_MS)       # the stop is gone
    assert pg.locator(".is-dealt").count() == 0 and pg.locator(".arena-task[data-key='export/k4']").count() == 0


def test_take_the_new_plan_sends_the_answer_says_what_changed_and_deals_the_added_tasks_from_the_stop(changing):
    pg, host = changing
    pg.evaluate(RECORD)
    stop = _stop(pg, "change")
    box = stop.bounding_box()                                                                        # the stop, raised, as it is at the press
    stop.get_by_role("button", name="Take the new plan").click()
    assert _sent(pg, host, ("ideas.revise_answer", {"slug": "export", "take": True, "via": "hand"}))
    _toast(pg, "The plan changed: 2 added, 1 changed, 1 dropped.")
    pg.wait_for_function("() => window.__seen.dealt.length === 2", timeout=WAIT_MS)                   # Progress screen (Screens) and Check the export (Reviewer)
    seen = _seen(pg)
    assert sorted(x["key"] for x in seen["dealt"]) == ["export/k4", "export/k5"] and seen["rose"] == []
    sx, sy = _centre(box)
    for x in seen["dealt"]:
        assert x["anim"] == "arena-deal" and x["agent"] in ("screens", "reviewer")
        assert abs(x["centre"][0] - sx) <= 3 and abs(x["centre"][1] - sy) <= 3 and abs(x["width"] - box["width"]) <= 3        # it starts at the stop's centre, at its width
    assert sorted(_ms(x) for x in seen["dealt"]) == [0, 35]
    pg.wait_for_function("() => !document.querySelector('.is-dealt, .is-drawn')", timeout=WAIT_MS)
    for x in seen["dealt"]:
        end = _centre(pg.locator(f".arena-task[data-key='{x['key']}']").bounding_box())
        assert abs(end[0] + float(x["dx"][:-2]) - sx) <= 3 and abs(end[1] + float(x["dy"][:-2]) - sy) <= 3                       # its end is its place
        assert pg.locator(f".arena-stack[data-agent={x['agent']}]").locator(f".arena-task[data-key='{x['key']}']").count() == 1


def test_what_started_meanwhile_is_said_after_what_changed_and_a_change_of_nothing_is_said_so(changing):
    pg, host = changing
    host.left = ["Stream rows", "Write csv"]
    _stop(pg, "change").get_by_role("button", name="Take the new plan").click()
    _toast(pg, "The plan changed: 2 added, 1 changed, 1 dropped. 2 left as they were: they started.")
    pg.locator(".arena-hc[data-kind=change]").wait_for(state="detached", timeout=WAIT_MS)             # the answered stop has gone
    host.propose(_summary(added=0, changed=0, dropped=0, usd_low=0.0, usd_high=0.0, rows=[]))
    host.left = ["Write csv"]
    _stop(pg, "change").get_by_role("button", name="Take the new plan").click()
    _toast(pg, "The plan stays as it was. 1 left as it was: it started.")


def test_a_take_that_adds_nothing_deals_nothing_and_a_refused_one_keeps_the_stop(gui):
    host = ChangeHost()
    host.propose(_summary(added=0, changed=1, dropped=1, rows=ROWS[2:]))
    pg, errors = _scene(gui, host, ".arena-hc[data-kind=change]")
    pg.evaluate(RECORD)
    host.refuse["ideas.revise_answer"] = "No plan change waits for this goal"
    _stop(pg, "change").get_by_role("button", name="Take the new plan").click()
    _toast(pg, "No plan change waits for this goal")
    assert pg.locator(".arena-hc[data-kind=change]:not(.is-leaving)").count() == 1                   # the stop stays: nothing was answered
    del host.refuse["ideas.revise_answer"]
    _stop(pg, "change").get_by_role("button", name="Take the new plan").click()
    _toast(pg, "The plan changed: 1 changed, 1 dropped.")
    host.node_of("export")["tasks"] += host.added[:1]                                                 # a card that comes later is not the change's: it rises
    host.bump({})
    pg.wait_for_function("() => window.__seen.rose.length === 1", timeout=WAIT_MS)
    assert _seen(pg)["dealt"] == []                                                                   # nothing waited for it
    pg.close()
    assert not errors, "\n".join(errors)


def test_under_reduced_motion_nothing_is_dealt_and_nothing_rises(gui):
    host = ChangeHost()
    host.propose(_summary())
    pg, errors = _scene(gui, host, ".arena-hc[data-kind=change]", reduced_motion="reduce")
    pg.evaluate(RECORD)
    _stop(pg, "change").get_by_role("button", name="Take the new plan").click()
    assert _sent(pg, host, ("ideas.revise_answer", {"slug": "export", "take": True, "via": "hand"}))
    pg.locator(".arena-task[data-key='export/k4']").wait_for(timeout=WAIT_MS)
    pg.locator(".arena-task[data-key='export/k5']").wait_for(timeout=WAIT_MS)
    seen = _seen(pg)
    assert seen["dealt"] == [] and seen["rose"] == [] and pg.locator(".is-dealt, .is-drawn").count() == 0
    pg.close()
    assert not errors, "\n".join(errors)


# -- the plan screen (§6.4) -----------------------------------------------------------------------------------------------------------------

def _plan_screen(pg):
    """The plan of *Export the passkeys* in the drawer, opened by a press on the change's stop outside its buttons: its block, The change."""
    _stop(pg, "change").locator(".arena-hc__open").click()
    block = _drawer(pg).locator(".shell-change")
    block.wait_for(timeout=WAIT_MS)
    return block


def test_the_plan_screen_shows_the_change_over_the_plan_with_its_why_its_rows_and_the_two_presses(changing):
    pg, host = changing
    block = _plan_screen(pg)
    heading = block.get_by_role("heading")
    assert heading.text_content().split("+")[0].strip() == "The change" and heading.locator("span").inner_text() == "+$0.40–1.20"      # what it adds
    assert block.locator(".shell-change__why").inner_text() == WHY
    rows = block.locator(".shell-change__rows li")
    assert [" ".join(t.split()) for t in rows.all_inner_texts()] == ["+ Progress screen", "+ Check the export", "~ Write csv", "− Stream rows"]
    assert rows.evaluate_all("els => els.map((e) => e.dataset.op)") == ["add", "add", "change", "drop"]
    assert rows.nth(0).locator("[role=img]").get_attribute("aria-label") == "added" and rows.nth(3).locator("[role=img]").get_attribute("aria-label") == "dropped"
    dropped = rows.nth(3).locator(".shell-change__title")
    assert dropped.evaluate("e => getComputedStyle(e).textDecorationLine") == "line-through" and rows.nth(0).locator(".shell-change__title").evaluate("e => getComputedStyle(e).textDecorationLine") == "none"
    assert dropped.evaluate("e => getComputedStyle(e).color") == _token(pg, "--ork-ink-muted")        # a dropped task is muted
    plan = _drawer(pg).locator(".board-plan:not(.shell-change)")
    assert block.bounding_box()["y"] + block.bounding_box()["height"] <= plan.bounding_box()["y"]    # over the plan
    assert block.get_by_role("button").all_inner_texts() == ["Take the new plan", "Keep the plan"]


def test_take_and_keep_on_the_plan_screen_answer_without_the_hand_and_deal_nothing(changing):
    pg, host = changing
    pg.evaluate(RECORD)
    block = _plan_screen(pg)
    block.get_by_role("button", name="Take the new plan").click()
    assert _sent(pg, host, ("ideas.revise_answer", {"slug": "export", "take": True}))
    _toast(pg, "The plan changed: 2 added, 1 changed, 1 dropped.")
    pg.locator(".shell-change").wait_for(state="detached", timeout=WAIT_MS)                           # answered: The change is gone from the plan
    pg.wait_for_function("() => window.__seen.rose.length === 2", timeout=WAIT_MS)
    assert _seen(pg)["dealt"] == []                                                                  # from the drawer the cards only rise, as a start from it does
    host.propose(_summary())                                                                         # the drawer stays on the plan: a newer change is over it
    block = _drawer(pg).locator(".shell-change")
    block.wait_for(timeout=WAIT_MS)
    block.get_by_role("button", name="Keep the plan").click()
    assert _sent(pg, host, ("ideas.revise_answer", {"slug": "export", "take": False}))
    _toast(pg, "The plan stays as it was.")
    pg.locator(".shell-change").wait_for(state="detached", timeout=WAIT_MS)


def test_a_plan_screen_without_a_change_has_no_block(quiet):
    pg, host = quiet
    pg.locator(".arena-goal[data-slug=recovery] .arena-goal__open").click()
    _drawer(pg).locator(".board-plan").first.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-change").count() == 0
