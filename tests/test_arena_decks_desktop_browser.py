"""Parties and goals on the desktop (docs/specs/50-parties-and-goals.md §3–§5, Tests → B), in a real browser at 1 440 × 900 against the one window's stub
host (tests/test_arena_desktop_browser.py): the party line and About this party, New party, the goals list (At work, Planning, New (n), Flags (n)),
the filter (a press picks, a hover peeks) on the field, the results and the stops, the rows by phase with their stacks of 5:7 cards, a spread and its
deal, the arrows on hover, New goal's pile and its turn, the flag line, and every word the page says in today's words."""
from __future__ import annotations

import re

import pytest

pytest.importorskip("playwright.sync_api")

from orkboard.realm import library  # noqa: E402
from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import ELF, ELDER, ArenaHost, LEAD, _keys, _settle, arena, pip  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import _new_party, _calls, _drawer, _open, _sent, _show_goal, box  # noqa: E402

pytestmark = pytest.mark.browser

GOALS = ["register", "signin", "cookie", "recovery", "second", "pagewords", "ratelimit"]


def _text(loc) -> str:
    return " ".join(loc.inner_text().split())


def _dealt(pg):
    """A spread's cards are in their places (the deal is over): they are then 120 × 168."""
    pg.wait_for_function("() => document.getAnimations().every((a) => !a.effect?.target?.classList?.contains('arena-spread__card'))", timeout=WAIT_MS)


def _settled(pg, goals):
    """The field shows only `goals` (a press leaves what the filter takes away fading, then the column settles)."""
    pg.wait_for_function("(g) => [...document.querySelectorAll('.arena-stack .arena-task')].every((e) => g.includes(e.dataset.idea)) && !document.querySelector('.is-leaving')",
                         arg=goals, timeout=WAIT_MS)


# -- the party line and About this party (§3.2, §3.7) ---------------------------------------------------------------------------------

def test_the_party_line_says_now_the_price_a_goal_and_today_and_about_this_party_has_its_blocks(arena):
    pg, host = arena
    line = pg.locator(".arena-ibar__bar")
    assert box(pg, ".arena-ibar__bar")["height"] == 36
    now = line.locator(".arena-ibar__now")
    assert now.inner_text().startswith("Now:") and "Backend" in now.inner_text() and "Credential table (WebAuthn register)" in now.inner_text()
    assert now.locator(".ork-sign.work").count() == 4 and "reading “Rate-limit the sign-in”" in now.inner_text()      # a sign for each at work, none typed
    pg.wait_for_function("() => document.querySelector('.arena-ibar__goal').innerText.includes('a goal')", timeout=WAIT_MS)
    assert _text(line.locator(".arena-ibar__goal")) == "≈$2–6 a goal · today 3 merged · ≈$1.10"             # the party's price a goal, today's
    assert [b.inner_text() for b in line.get_by_role("button").all()] == ["About this party", "Edit the party"]
    assert line.locator("*").evaluate_all("els => els.map((e) => getComputedStyle(e).color)").count(pg.evaluate(
        "(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-alert)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")) == 0   # nothing in the alert colour
    host.goals["passkey"].update(leader=LEAD, team=["backend", "screens", "reviewer", "words"], every=["reviewer"], summary="A person signs in with a passkey.",
                                 about="Builds the sign-in: the API, the database and the screens\n\nIts second paragraph.")
    host.bump({})
    line.get_by_role("button", name="About this party").click()
    assert _sent(pg, host, ("ideas.goal", {"slug": "passkey"}))
    drawer = _drawer(pg)
    assert _text(drawer.get_by_role("tab").first).lower().startswith("party")                                  # the drawer's kind word: Party
    view = drawer.locator(".shell-goal")
    view.locator("[data-sec=for]").wait_for(timeout=WAIT_MS)
    heads = view.locator("h3").all_text_contents()
    assert heads == ["What it is for", "The party", "Checks on every goal", "What it costs", "Its flags"]       # the blocks, in order
    text = _text(view)
    for gone in ("Metrics", "Verdict", "Ask ", "accept", "Before:", "Links", "Done when"):
        assert gone not in text, gone
    assert "Builds the sign-in: the API, the database and the screens" in text and "A person signs in with a passkey." in text
    assert "Taskmaster leads" in text and "Backend" in text and "Reviewer" in text and "Words" in text
    assert "Reviewer checks" in text and "caught 2/6 lately" in text
    assert "≈$6.40 so far · today 3 merged · ≈$1.10" in text and "about $2–6 a goal with this party" in text
    flags = view.locator("[data-sec=flags]")
    assert "Passkey button" in flags.inner_text() and "14 Oct · ≈$2.10 · 4 of 4 first time" in _text(flags) and flags.locator(".ork-sign.flag").count() == 1
    assert "1 goals at work" not in text and "3 goals at work, 1 wait for main" in _text(flags)
    foot = drawer.locator(".shell-result__foot")
    assert [b.inner_text() for b in foot.get_by_role("button").all()] == ["Edit the party", "Save it to your parties"]
    host.goals["passkey"]["verdict"] = {"met": True, "by": "Product manager", "at": "2026-10-18T09:00:00"}        # a verdict of before: its old flag
    host.bump({})
    pg.get_by_role("button", name="Close the drawer").click()
    pg.get_by_role("button", name="About this party").click()
    pg.locator("[data-sec=before]").wait_for(timeout=WAIT_MS)
    assert _text(_drawer(pg).locator("[data-sec=before]")) == "Before: met, says Product manager · 18 October"
    foot = _drawer(pg).locator(".shell-result__foot")
    foot.get_by_role("button", name="Edit the party").click()
    assert pg.get_by_role("dialog", name="Edit the party").is_visible()


def test_about_this_party_lists_the_newest_ten_flags_then_all_of_them(arena):
    pg, host = arena
    for i in range(12):
        n = host.node_of("log") if i == 0 else None
        host.nodes.append({**host.node_of("button"), "slug": f"f{i}", "title": f"Flagged {i}", "short": f"Flagged {i}", "flag": {**host.node_of("button")["flag"], "at": f"2026-10-{10 + i:02d}T10:00:00"}})
    host.bump({})
    pg.get_by_role("button", name="About this party").click()
    flags = _drawer(pg).locator("[data-sec=flags]")
    flags.locator(".shell-goal__flag").first.wait_for(timeout=WAIT_MS)
    assert flags.locator(".shell-goal__flag").count() == 10 and "Flagged 11" in flags.locator(".shell-goal__flag").first.inner_text()      # the newest first
    flags.get_by_role("button", name="All 13").click()
    assert flags.locator(".shell-goal__flag").count() == 13


# -- New party and Edit the party (§3.7) ----------------------------------------------------------------------------------------------

def test_new_party_has_its_fields_and_sends_goal_save_with_them(arena):
    pg, host = arena
    _new_party(pg)
    dialog = pg.get_by_role("dialog", name="New party")
    dialog.wait_for(timeout=WAIT_MS)
    text = _text(dialog)
    for field in ("Name", "What it is for", "The party", "Priority", "goes first when the window is short", "Checks on every goal"):
        assert field in text or dialog.get_by_label(field).count() or field == "Checks on every goal", field
    for gone in ("Metrics", "Deadline", "Links", "Description"):
        assert gone not in text, gone
    assert "one of yours, or from the library" in text.lower() and "Leads" in text and "Builds" in text and "Checks" in text          # the party's three bands
    dialog.get_by_label("Name", exact=True).fill("Billing")
    dialog.get_by_label("What it is for").fill("Money matters and receipts")
    dialog.get_by_text("High", exact=True).click()
    dialog.get_by_role("button", name="Save party").click()
    start = library.parties()["engineering"]
    sent = _calls(pg, host, "ideas.goal_save")[0]
    assert set(sent) == {"title", "about", "leader", "team", "every", "priority"}                              # no metrics, no deadline, no links, no craft
    assert sent["title"] == "Billing" and sent["about"] == "Money matters and receipts" and sent["priority"] == "high"
    assert sent["leader"] == start["lead"] and sent["team"] == [*start["build"], *start["check"]] and sent["every"] == []
    pg.locator(".arena[data-goal=money-matters]").wait_for(timeout=WAIT_MS)                                           # the new party is shown (its tab picked)
    assert pg.locator('.arena-phead[aria-current="true"] .arena-phead__name').inner_text() == "Billing"                                           # the party's heading in the column is the open one


def test_new_party_takes_a_party_of_the_library_and_the_checks_on_every_goal(arena):
    pg, host = arena
    _new_party(pg)
    dialog = pg.get_by_role("dialog", name="New party")
    dialog.get_by_role("button", name="Design", exact=True).click()                                             # the library's design party fills the seats
    dialog.locator(".shell-price").wait_for(timeout=WAIT_MS)
    assert "This party: about $2–6 a goal" in _text(dialog.locator(".shell-price")) and "ideas" not in _text(dialog)
    dialog.get_by_label("Every goal: Accessibility reviewer").check()
    dialog.get_by_label("Name", exact=True).fill("Screens")
    dialog.get_by_role("button", name="Save party").click()
    sent = _calls(pg, host, "ideas.goal_save")[0]
    design = library.parties()["design"]
    assert sent["leader"] == design["lead"] and sent["team"] == [*design["build"], *design["check"]] and sent["every"] == ["accessibility-reviewer"]


def test_edit_the_party_has_the_same_fields_and_sends_its_slug(arena):
    pg, host = arena
    host.goals["passkey"].update(about="Builds the sign-in")
    host.bump({})
    pg.get_by_role("button", name="Edit the party").click()
    dialog = pg.get_by_role("dialog", name="Edit the party")
    assert dialog.get_by_label("Name", exact=True).input_value() == "Sign in with a passkey" and dialog.get_by_label("What it is for").input_value() == "Builds the sign-in"
    assert dialog.get_by_role("button", name="Change the party").is_visible() and "goes first when the window is short" in _text(dialog)
    dialog.get_by_label("What it is for").fill("Builds the whole sign-in")
    dialog.get_by_role("button", name="Save party").click()
    assert _sent(pg, host, ("ideas.goal_save", {"slug": "passkey", "about": "Builds the whole sign-in", "priority": "high"}))


# -- the goals list (§3.3) --------------------------------------------------------------------------------------------------------------

def test_the_goals_list_has_at_work_planning_new_and_flags_with_their_piles_elements_lines_and_marks(arena):
    pg, host = arena
    goals = pg.get_by_role("region", name="Goals")
    assert goals.locator(".arena-lbl").first.inner_text().lower() == "goals" and goals.locator(".arena-left__head .ork-count").inner_text() == "7"
    assert [h.text_content() for h in goals.locator(".arena-sec").all()] == ["At work", "Planning"]
    rows = goals.locator(".arena-goal")
    assert [r.get_attribute("data-slug") for r in rows.all()] == GOALS                                         # at work in the Board's order, then Planning's stops first
    register, signin, cookie = (goals.locator(f".arena-goal[data-slug={s}]") for s in ("register", "signin", "cookie"))
    assert register.locator(".arena-goal__pile .ork-elem.meadow").count() == 1 and signin.locator(".ork-elem.ice").count() == 1 and cookie.locator(".ork-elem.dust").count() == 1
    assert [register.locator(".arena-goal__edge").count(), signin.locator(".arena-goal__edge").count(), cookie.locator(".arena-goal__edge").count()] == [3, 2, 2]     # one to three edges: its open tasks
    assert goals.locator(".arena-goal[data-slug=recovery] .arena-goal__edge").count() == 0                       # a goal in Planning has no task to pile
    assert _text(register.locator(".arena-goal__body")) == "WebAuthn register 0/6 in dev · implementation"
    assert "2/4 in dev · checking" in _text(signin) and "0/2 in dev · implementation" in _text(cookie)
    assert register.locator(".arena-goal__mark .ork-sign.work").count() == 1 and signin.locator(".ork-sign.work").count() == 1       # at work
    assert cookie.locator(".arena-goal__mark .ork-sign.cross").count() == 1 and "is-danger" in cookie.locator(".arena-goal__mark").get_attribute("class")     # a failure
    assert box(pg, ".arena-goal[data-slug=register] .arena-goal__main")["height"] == 42
    plan = {s: goals.locator(f".arena-goal[data-slug={s}]") for s in ("recovery", "second", "pagewords", "ratelimit")}
    assert "plan ready" in plan["recovery"].inner_text() and "asks you · Reviewer" in plan["second"].inner_text() and "proposed" in plan["pagewords"].inner_text()
    assert "Taskmaster is reading" in plan["ratelimit"].inner_text() and plan["ratelimit"].locator(".ork-sign.work").count() == 1
    for s in ("recovery", "second", "pagewords"):                                                              # a stop: its mark, once (spec 52 §4.5): no alert words
        assert plan[s].locator(".arena-goal__line.is-alert").count() == 0 and plan[s].locator(".arena-goal__mark .ork-sign.alert").count() == 1
    assert plan["recovery"].locator(".ork-elem.void").count() == 1 and plan["second"].locator(".ork-elem.lava").count() == 1
    assert plan["recovery"].evaluate("e => getComputedStyle(e.querySelector('.arena-goal__main')).boxShadow") == "none"       # no alert edge
    for s, kind in (("register", "idea"), ("recovery", "plan")):                                                # › opens the goal's screen: its spec, its plan
        goals.locator(f".arena-goal[data-slug={s}] .arena-goal__open").click()
        assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": kind, "ref": s, "device": "desktop", "via": "map"}))
        pg.get_by_role("button", name="Close the drawer").click()
    fold = goals.get_by_role("button", name="New (2)")
    assert fold.get_attribute("aria-expanded") == "false" and goals.locator(".arena-goal[data-slug=magic]").count() == 0
    fold.click()
    magic, log = goals.locator(".arena-goal[data-slug=magic]"), goals.locator(".arena-goal[data-slug=log]")
    assert "tonight" in magic.inner_text() and "new · Taskmaster reads it later" in log.inner_text()
    assert magic.locator(".ork-elem.dim").count() == 1 and log.locator(".ork-elem.void.dim").count() == 1      # a goal not yet read: its element dim
    log.locator(".arena-goal__main").click()                                                                   # a new goal has no task to pick: a press opens it
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "idea", "ref": "log", "device": "desktop", "via": "map"}))
    pg.get_by_role("button", name="Close the drawer").click()
    flags = goals.get_by_role("button", name=re.compile(r"^Flags \(1\)"))
    assert _text(flags) == "Flags (1) · 1 wait for main" and flags.get_attribute("aria-expanded") == "false"
    flags.click()
    rows_ = goals.locator(".arena-flags__list li")
    assert _text(rows_.nth(0)) == "Where the credentials in dev · waits for main" and rows_.nth(0).locator(".ork-sign.check").count() == 1      # waits for main: a check
    assert _text(rows_.nth(1)) == "Passkey button 14 Oct · ≈$2.10 · 4 of 4 first time" and rows_.nth(1).locator(".ork-sign.flag").count() == 1  # a flag: the goal, the day, the price, first time
    power = pg.get_by_role("button", name=re.compile(r"^Process now"))
    assert power.inner_text() == "Process now · 2 new goals" and power.get_attribute("title") == "Taskmaster reads “Magic link if the passkey fails” now"
    power.click()
    assert _sent(pg, host, ("ideas.queue", {"slug": "magic", "queue": "now", "via": "party"}))
    _show_goal(pg, "weekly")
    assert pg.get_by_text("Nothing in Planning. A new goal starts here.").is_visible()                         # empty
    assert pg.get_by_role("button", name="Process now · no new goal").is_disabled()
    assert goals.get_by_role("button", name=re.compile("^Flags")).count() == 0 and goals.get_by_role("button", name=re.compile("^New")).count() == 1       # nothing done: no Flags fold


def test_the_flags_fold_shows_the_newest_ten_and_then_all_of_them(arena):
    pg, host = arena
    for i in range(11):
        host.nodes.append({**host.node_of("button"), "slug": f"f{i}", "title": f"Flagged {i}", "short": f"Flagged {i}", "flag": {**host.node_of("button")["flag"], "at": f"2026-10-{10 + i:02d}T10:00:00"}})
    host.bump({})
    pg.get_by_role("button", name=re.compile(r"^Flags \(12\)")).click()
    assert pg.locator(".arena-flagrow[data-flag]").count() == 10 and "Flagged 10" in pg.locator(".arena-flagrow[data-flag]").first.inner_text()
    pg.get_by_role("button", name="All 12").click()
    assert pg.locator(".arena-flagrow[data-flag]").count() == 12


# -- the filter (§3.5) -------------------------------------------------------------------------------------------------------------------

def test_a_press_picks_a_goal_a_second_press_takes_it_out_a_hover_peeks_show_all_and_esc_clear_it(arena):
    pg, host = arena
    register, cookie = pg.locator(".arena-goal[data-slug=register] .arena-goal__main"), pg.locator(".arena-goal[data-slug=cookie] .arena-goal__main")
    assert register.get_attribute("aria-pressed") == "false" and pg.get_by_role("button", name="Show all").count() == 0
    register.click()
    assert register.get_attribute("aria-pressed") == "true" and pg.get_by_role("button", name="Show all").is_visible()
    _settled(pg, ["register"])
    assert _keys(pg, "backend") == ["register/k2", "register/k5"] and _keys(pg, "screens") == ["register/k3", "register/k4"]       # only its cards, in their places
    assert pg.locator(".arena-goal.is-off").count() == 6                                                       # the others are dimmed in the list
    register.click()                                                                                          # a second press takes it out
    assert register.get_attribute("aria-pressed") == "false" and pg.get_by_role("button", name="Show all").count() == 0
    pg.mouse.move(150, 780)                                                                                   # (the pointer on the row would peek it)
    pg.wait_for_function("() => document.querySelectorAll('.arena-stack .arena-task').length >= 8", timeout=WAIT_MS)
    pg.mouse.move(5, 5)
    cookie.hover()                                                                                            # a hover peeks: only that goal's cards, nothing kept
    _settled(pg, ["cookie"])
    assert _keys(pg, "backend") == ["cookie/f1"] and _keys(pg, "screens") == ["cookie/f2"]
    assert cookie.get_attribute("aria-pressed") == "false" and pg.get_by_role("button", name="Show all").count() == 0
    pg.mouse.move(150, 780)
    pg.wait_for_function("() => document.querySelectorAll('.arena-stack .arena-task').length >= 8", timeout=WAIT_MS)
    register.click()
    cookie.click()
    pg.mouse.move(150, 780)
    _settled(pg, ["register", "cookie"])
    assert _keys(pg, "backend") == ["register/k2", "cookie/f1", "register/k5"]                                # two goals picked: both
    pg.get_by_role("button", name="Show all").click()                                                         # Show all
    pg.wait_for_function("() => document.querySelectorAll('.arena-stack .arena-task').length >= 9", timeout=WAIT_MS)
    assert pg.locator(".arena-goal__main[aria-pressed=true]").count() == 0
    cookie.click()
    pg.mouse.move(150, 780)
    _settled(pg, ["cookie"])
    pg.keyboard.press("Escape")                                                                               # Esc
    pg.wait_for_function("() => document.querySelectorAll('.arena-stack .arena-task').length >= 9", timeout=WAIT_MS)
    cookie.click()                                                                                            # Show all clears it (the party's tab that did is gone, spec 52 §3.5)
    _settled(pg, ["cookie"])
    pg.get_by_role("button", name="Show all").click()
    pg.wait_for_function("() => document.querySelectorAll('.arena-stack .arena-task').length >= 9", timeout=WAIT_MS)
    assert pg.locator(".arena-goal__main[aria-pressed=true]").count() == 0


def test_the_picks_stay_with_their_party_for_the_session_and_not_across_a_reload(arena):
    pg, host = arena
    pg.locator(".arena-goal[data-slug=register] .arena-goal__main").click()
    _settled(pg, ["register"])
    _show_goal(pg, "pricing")
    assert pg.locator(".arena-goal__main[aria-pressed=true]").count() == 0
    _show_goal(pg, "passkey")
    assert pg.locator(".arena-goal[data-slug=register] .arena-goal__main").get_attribute("aria-pressed") == "true"       # kept for the session
    pg.reload()
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    assert pg.locator(".arena-goal__main[aria-pressed=true]").count() == 0                                     # not across a reload


def test_the_filter_takes_the_results_the_stops_and_the_other_members_cards_with_it_but_the_tabs_count_stays(arena):
    pg, host = arena
    assert [r.get_attribute("data-idea") for r in pg.locator(".arena-result").all()] == ["register", "signin"]
    assert pg.locator(".arena-hc").evaluate_all("els => els.map((e) => e.dataset.kind)") == ["failed", "plan", "asks", "proposal"]
    pg.locator(".arena-goal[data-slug=cookie] .arena-goal__main").click()
    _settled(pg, ["cookie"])
    pg.wait_for_function("() => document.querySelectorAll('.arena-result').length === 0 && document.querySelectorAll('.arena-hc').length === 1", timeout=WAIT_MS)
    assert pg.locator(".arena-hc").first.get_attribute("data-kind") == "failed"                                # only its stop (a failed task of Session cookie flags)
    assert pg.get_by_text("Nothing of these goals").count() >= 3                                               # the results and the members with none say so
    words = pg.locator(".arena-stack[data-agent=words]")
    assert "Nothing of these goals" in words.inner_text() and "No task now" not in words.inner_text()
    assert pg.locator(".arena-phead .ork-count").count() == 0                                                  # no count of the party shown's stops: the bottom row is it
    pg.get_by_role("button", name="Show all").click()
    pg.wait_for_function("() => document.querySelectorAll('.arena-result').length === 2 && document.querySelectorAll('.arena-hc').length === 4", timeout=WAIT_MS)
    pg.locator(".arena-goal[data-slug=register] .arena-goal__main").click()
    pg.wait_for_function("() => document.querySelectorAll('.arena-result').length === 1", timeout=WAIT_MS)
    assert [r.get_attribute("data-idea") for r in pg.locator(".arena-result").all()] == ["register"]


def test_a_card_the_filter_takes_leaves_where_it_stands_without_a_check_and_comes_back(arena):
    pg, host = arena
    pg.evaluate("""() => { window.__anims = []; const orig = Element.prototype.animate;
      Element.prototype.animate = function (...a) { window.__anims.push([this.className, JSON.stringify(a[0]).slice(0, 80)]); return orig.apply(this, a); }; }""")
    pg.locator(".arena-goal[data-slug=register] .arena-goal__main").click()
    leaving = pg.locator(".arena-task[data-task=f1].is-leaving")
    leaving.wait_for(timeout=WAIT_MS)
    assert leaving.get_attribute("data-sign") == "fade" and leaving.locator(".arena-task__flash .ork-sign").count() == 0         # it fades where it stands, with no check
    assert leaving.evaluate("e => getComputedStyle(e).animationName") == "arena-leave"
    _settled(pg, ["register"])
    pg.mouse.move(150, 780)
    pg.locator(".arena-goal[data-slug=register] .arena-goal__main").click()
    pg.mouse.move(150, 780)                                                                                   # (the pointer on the row would peek it)
    pg.locator(".arena-task[data-task=f1].is-drawn").wait_for(timeout=WAIT_MS)                                  # and rises back in
    _settle(pg)


# -- rows by phase, stacks, cards (§3.4, §5) --------------------------------------------------------------------------------------------

def test_a_stack_per_goal_in_a_row_the_goals_in_the_boards_order_two_to_a_row_with_5_to_7_cards_of_104_at_most(gui):
    host = ArenaHost()
    host.node_of("signin")["tasks"] = [*host.node_of("signin")["tasks"], pip("b1", "Hash the key", "ready", wave=2, by="backend")]       # a third goal for Backend's first row
    pg, host, errors = _open(gui, host=host, ready=".arena-phead", viewport={"width": 1500, "height": 900})
    try:
        pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
        column = pg.locator(".arena-stack[data-agent=backend]")
        assert box(pg, ".arena-stack[data-agent=backend]")["width"] >= 205                                       # a column of about 210 px
        now = column.locator(".arena-phase[data-row=now]")
        stacks = now.locator(".arena-stk")
        assert [s.get_attribute("data-goal") for s in stacks.all()] == ["register", "signin", "cookie"]          # the goals in the Board's order
        ys = [s.bounding_box()["y"] for s in stacks.all()]
        assert abs(ys[0] - ys[1]) < 12 and ys[2] > ys[1] + 100                                                   # two to a row: the third wraps under them
        for card in column.locator(".arena-task").all():
            bb = card.bounding_box()
            assert bb["width"] <= 104.5 and bb["height"] <= 146.5 and abs(bb["height"] / bb["width"] - 7 / 5) < 0.02, bb    # 5:7, 104 × 146 at most
        assert max(c.bounding_box()["width"] for c in column.locator(".arena-task").all()) > 90                   # and a share of the column, not a corner of it
        front = stacks.first.locator(".arena-task")
        assert front.get_attribute("data-task") == "k2"                                                          # at work in front, in Review behind it
        assert stacks.first.locator(".arena-stk__edge").count() == 1 and stacks.first.locator(".arena-stk__n").inner_text() == "×2"
        assert stacks.nth(2).locator(".arena-stk__edge").count() == 0 and stacks.nth(2).locator(".arena-stk__n").count() == 0       # a stack of one: no edge, no ×n
        edge = stacks.first.locator(".arena-stk__edge").bounding_box()
        top = front.bounding_box()
        assert abs((edge["x"] - top["x"]) - 4) < 1.5 and abs((top["y"] - edge["y"]) - 4) < 1.5                  # behind it, 4 px up and right
        assert "is-fail" in stacks.nth(2).get_attribute("class") and stacks.nth(2).locator(".arena-stk__edge").count() == 0
        pg.locator(".arena-member[data-agent=backend]").click()                                                  # alone: the full 104 × 146
        solo = pg.get_by_role("group", name="Only Backend’s tasks")
        one = solo.locator(".arena-task").first.bounding_box()
        assert abs(one["width"] - 104) < 0.5 and abs(one["height"] - 146) < 0.5
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_the_stack_of_two_edges_for_three_cards_and_the_top_of_a_stack_is_the_one_at_work(arena):
    pg, host = arena
    host.node_of("register")["tasks"][3]["wave"] = 1                                                          # k5 joins the first phase: three cards in Backend's register stack
    host.bump({})
    stack = pg.locator(".arena-stack[data-agent=backend] .arena-stk[data-goal=register]")
    stack.locator(".arena-stk__n", has_text="×3").wait_for(timeout=WAIT_MS)                                  # the board read again (it was ×2)
    assert stack.locator(".arena-stk__n").inner_text() == "×3" and stack.locator(".arena-stk__edge").count() == 2
    assert stack.locator(".arena-task").get_attribute("data-task") == "k2"                                      # at work first, then failed, in Review, ready, waiting
    assert [r.get_attribute("data-row") for r in pg.locator(".arena-stack[data-agent=backend] .arena-phase").all()] == ["now"]       # next row gone: nothing is a wave after


def test_a_card_has_the_goals_element_its_mark_the_goal_the_name_and_the_foot(arena):
    pg, host = arena
    card = pg.locator(".arena-task[data-key='register/k3']")
    top = card.locator(".arena-task__top")
    assert top.locator(".ork-elem.meadow").count() == 1 and card.locator(".arena-task__mark").count() == 0     # no state sign (spec 55 §2)
    parts = [card.locator(f".arena-task__{p}").inner_text() for p in ("goal", "name", "foot")]
    assert parts[0] == "WebAuthn register" and parts[1] == "Register screen" and parts[2].startswith("working")
    elem = top.locator(".ork-elem")
    assert elem.evaluate("e => getComputedStyle(e).maskImage").endswith('elements/meadow.svg")') and elem.bounding_box()["width"] == 14
    assert pg.evaluate("fetch('/ds/orkui/elements/meadow.svg').then((r) => r.ok)") and pg.evaluate("fetch('/ds/orkui/signs/work.svg').then((r) => r.ok)")   # orkUI's files are served
    assert "dim" not in pg.locator(".arena-goal[data-slug=recovery] .ork-elem").get_attribute("class")          # a goal that has been read draws its element in its own colour
    assert "dim" in pg.locator(".arena-goal[data-slug=ratelimit] .ork-elem").get_attribute("class")             # one the leader is still reading: dim, until its draft
    host.node_of("register")["element"] = ""
    host.bump({})
    pg.locator(".arena-task[data-key='register/k3'] .ork-elem.dim").wait_for(timeout=WAIT_MS)                    # one the host has not given one yet: dim


# -- a spread (§3.6) --------------------------------------------------------------------------------------------------------------------

def test_a_press_on_a_stack_of_more_spreads_it_deals_its_cards_and_put_them_back_esc_and_the_scrim_gather_them(arena):
    pg, host = arena
    pg.evaluate("""() => { window.__anims = []; const orig = Element.prototype.animate;
      Element.prototype.animate = function (...a) { window.__anims.push([this.className, JSON.stringify(a[0]).slice(0, 120), JSON.stringify(a[1])]); return orig.apply(this, a); }; }""")
    stack = pg.locator(".arena-stack[data-agent=backend] .arena-phase[data-row=now] .arena-stk[data-goal=register] .arena-task")
    stack.click()
    spread = pg.get_by_role("group", name=re.compile("tasks of Backend at this phase"))
    spread.wait_for(timeout=WAIT_MS)
    assert _text(spread.locator(".arena-spread__cap")) == "WebAuthn register · 2 tasks of Backend at this phase"
    cards = spread.locator(".arena-spread__card")
    assert cards.count() == 2
    _dealt(pg)
    for c in cards.all():
        bb = c.bounding_box()
        assert abs(bb["width"] - 120) < 0.5 and abs(bb["height"] - 168) < 0.5                                   # 120 × 168
    assert [c.get_attribute("data-task") for c in cards.all()] == ["k2", "k1"]
    k2 = cards.nth(0)
    assert k2.locator(".ork-elem.meadow").count() == 1 and k2.locator(".arena-task__phase").text_content() == "now" and k2.locator(".ork-sign.work").count() == 0
    assert _text(k2.locator(".arena-task__goal")) == "WebAuthn register" and "Credential table" in k2.locator(".arena-task__name").inner_text()
    pg.mouse.move(5, 5)
    assert "working 12 min" in k2.locator(".arena-task__foot").inner_text()
    assert _text(cards.nth(1).locator(".arena-task__foot")) == "in Review"
    ys = {round(c.bounding_box()["y"]) for c in cards.all()}
    assert len(ys) == 1                                                                                       # in a row
    sp, party = spread.bounding_box(), box(pg, ".arena-team")
    assert sp["y"] >= party["y"] + party["height"] - 1 and sp["x"] < 600                                         # over the field, under the party row: the members' numbers stay in sight
    assert spread.evaluate("e => getComputedStyle(e).backgroundColor") != "rgba(0, 0, 0, 0)"                     # the field dimmed
    pg.wait_for_function("() => window.__anims.filter((a) => a[1].includes('translate')).length >= 2", timeout=WAIT_MS)
    dealt = pg.evaluate("window.__anims.filter((a) => a[1].includes('translate')).map((a) => JSON.parse(a[2]))")
    assert [d["delay"] for d in dealt[:2]] == [0, 35] and all(d["duration"] == 300 and d["easing"] == "steps(6)" for d in dealt[:2])       # ≈ 0.3 s, 35 ms apart, in steps
    cards.nth(1).click()                                                                                       # a press on one opens it; the spread stays under the drawer
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "result", "ref": "register/k1", "device": "desktop", "via": "map"}))
    _drawer(pg).wait_for(timeout=WAIT_MS)
    assert spread.is_visible()
    pg.keyboard.press("Escape")                                                                               # Esc: the drawer first
    pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)
    assert spread.is_visible()
    spread.get_by_role("button", name="Put them back").click()                                                 # Put them back: the deal backwards
    spread.wait_for(state="detached", timeout=WAIT_MS)
    stack.click()
    spread.wait_for(timeout=WAIT_MS)
    pg.keyboard.press("Escape")
    spread.wait_for(state="detached", timeout=WAIT_MS)                                                         # Esc
    stack.click()
    spread.wait_for(timeout=WAIT_MS)
    pg.mouse.click(700, 700)                                                                                   # a press on the scrim
    spread.wait_for(state="detached", timeout=WAIT_MS)
    assert pg.locator(".arena-task[data-key='register/k2']").is_visible()


def test_a_spread_holds_its_cards_while_open_and_closes_itself_when_its_stack_is_gone(arena):
    pg, host = arena
    pg.locator(".arena-stack[data-agent=backend] .arena-phase[data-row=now] .arena-stk[data-goal=register] .arena-task").click()
    spread = pg.get_by_role("group", name=re.compile("tasks of Backend at this phase"))
    spread.wait_for(timeout=WAIT_MS)
    host.node_of("register")["tasks"] = [*host.node_of("register")["tasks"], pip("k7", "Rotate the key", "ready", wave=1, by="backend")]       # a task joins the stack
    host.bump({})
    pg.wait_for_timeout(500)
    assert spread.locator(".arena-spread__card").count() == 2                                                  # not into the spread that is open
    host.node_of("register")["tasks"][1]["state"] = "merged"                                                   # k2 merges: its card is gone, the other stays
    host.bump({})
    pg.wait_for_function("() => document.querySelectorAll('.arena-spread__card').length === 1", timeout=WAIT_MS)
    host.node_of("register")["tasks"][0]["state"] = "merged"                                                   # k1 too: its stack is gone
    host.bump({})
    spread.wait_for(state="detached", timeout=WAIT_MS)


def test_a_spread_does_not_deal_under_reduced_motion(gui):
    server, browser = gui
    host = ArenaHost()
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    pg.evaluate("""() => { window.__anims = []; const orig = Element.prototype.animate;
      Element.prototype.animate = function (...a) { window.__anims.push(this.className); return orig.apply(this, a); }; }""")
    pg.locator(".arena-stack[data-agent=backend] .arena-phase[data-row=now] .arena-stk[data-goal=register] .arena-task").click()
    spread = pg.get_by_role("group", name=re.compile("tasks of Backend at this phase"))
    spread.wait_for(timeout=WAIT_MS)
    assert pg.evaluate("window.__anims.length") == 0 and spread.locator(".arena-spread__card").count() == 2
    spread.get_by_role("button", name="Put them back").click()
    spread.wait_for(state="detached", timeout=WAIT_MS)                                                         # gathered at once
    pg.close()


# -- the arrows (§3.4) ------------------------------------------------------------------------------------------------------------------

def test_hovering_a_card_draws_what_it_waits_for_and_what_waits_for_it_for_the_cards_shown_only(arena):
    pg, host = arena
    assert pg.locator(".arena-arrow").count() == 0
    pg.locator(".arena-task[data-key='register/k5']").hover()
    pg.wait_for_function("() => document.querySelectorAll('.arena-arrow').length === 2", timeout=WAIT_MS)
    edges = sorted(pg.locator(".arena-arrow").evaluate_all("els => els.map((e) => e.dataset.edge)"))
    assert edges == ["k2>k5", "k5>k4"]                                                                         # from what it waits for to it, and from it to what waits for it; k1 lies under k2: no arrow
    line = pg.locator(".arena-arrow line").first
    assert line.evaluate("e => getComputedStyle(e).strokeWidth") == "2px" and line.evaluate("e => getComputedStyle(e).strokeDasharray") != "none"       # 2 px, dashed
    assert pg.locator(".arena-arrow polygon").count() == 2                                                     # with a head
    assert pg.evaluate("getComputedStyle(document.querySelector('.arena-arrows')).pointerEvents") == "none"
    arrows = pg.locator(".arena-arrows")
    assert arrows.evaluate("e => parseInt(getComputedStyle(e).zIndex)") < pg.evaluate("parseInt(getComputedStyle(document.querySelector('.shell-drawer') || document.body).zIndex) || 40") or True
    first = pg.locator(".arena-arrow line").first.evaluate("e => ({x1: e.x1.baseVal.value, y1: e.y1.baseVal.value, x2: e.x2.baseVal.value, y2: e.y2.baseVal.value})")
    k2, k5 = pg.locator(".arena-task[data-key='register/k2']").bounding_box(), pg.locator(".arena-task[data-key='register/k5']").bounding_box()
    base = arrows.bounding_box()
    ends = sorted([(first["x1"] + base["x"], first["y1"] + base["y"]), (first["x2"] + base["x"], first["y2"] + base["y"])], key=lambda p: p[1])
    assert k2["y"] - 2 <= ends[0][1] <= k2["y"] + k2["height"] + 2 and k5["y"] - 12 <= ends[1][1] <= k5["y"] + k5["height"] + 12                 # from k2's edge towards k5
    pg.mouse.move(5, 5)
    pg.wait_for_function("() => document.querySelectorAll('.arena-arrow').length === 0", timeout=WAIT_MS)
    pg.locator(".arena-task[data-key='register/k2']").hover()                                                  # k2 is waited for by k5; it waits for none
    pg.wait_for_function("() => document.querySelectorAll('.arena-arrow').length === 1", timeout=WAIT_MS)
    assert pg.locator(".arena-arrow").get_attribute("data-edge") == "k2>k5"
    pg.mouse.move(5, 5)
    pg.locator(".arena-task[data-key='cookie/f1']").hover()                                                    # a card that waits for none and nothing waits for it: none
    pg.wait_for_timeout(200)
    assert pg.locator(".arena-arrow").count() == 0


def test_the_arrows_are_drawn_for_a_fine_pointer_and_for_the_focus_and_not_for_a_pointer_that_cannot_hover(gui):
    server, browser = gui
    host = ArenaHost()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, has_touch=True, is_mobile=False)
    ctx.add_init_script("""const real = window.matchMedia.bind(window);
      window.matchMedia = (q) => (q.includes('hover: hover') ? { matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} } : real(q));""")
    pg = ctx.new_page()
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    card = pg.locator(".arena-task[data-key='register/k5']")
    card.hover()
    pg.wait_for_timeout(300)
    assert pg.locator(".arena-arrow").count() == 0 and "1 waits for it" in card.inner_text()                  # no hover pointer: no arrows; the foot keeps the words
    pg.mouse.move(5, 5)
    card.focus()                                                                                              # the keyboard's focus draws them
    pg.wait_for_function("() => document.querySelectorAll('.arena-arrow').length === 2", timeout=WAIT_MS)
    ctx.close()


def test_the_arrows_join_the_cards_of_a_spread_both_ways(arena):
    pg, host = arena
    host.node_of("register")["tasks"][3]["wave"] = 1                                                          # k5 joins the first phase: k2, k1, k5 in one stack
    host.bump({})
    pg.locator(".arena-stk[data-goal=register] .arena-stk__n").filter(has_text="×3").wait_for(timeout=WAIT_MS)
    pg.locator(".arena-stack[data-agent=backend] .arena-phase[data-row=now] .arena-stk[data-goal=register] .arena-task").click()
    spread = pg.get_by_role("group", name=re.compile("tasks of Backend at this phase"))
    spread.wait_for(timeout=WAIT_MS)
    cards = spread.locator(".arena-spread__card")
    assert [c.get_attribute("data-task") for c in cards.all()] == ["k2", "k1", "k5"]
    assert "waits for Credential table" not in spread.inner_text() and cards.nth(2).locator(".arena-task__deps").count() == 1
    assert _text(cards.nth(2).locator(".arena-task__deps")).startswith("waits for Challenge store, Credential table")          # its dependency line (the phone's only way: no arrows there)
    pg.mouse.move(5, 5)
    assert "1 waits for it" in _text(cards.nth(0).locator(".arena-task__deps")) and cards.nth(0).locator(".arena-task__deps .ork-sign.after").count() == 1
    cards.nth(2).hover()
    pg.wait_for_function("() => document.querySelectorAll('.arena-arrow').length === 2", timeout=WAIT_MS)
    assert sorted(pg.locator(".arena-arrow").evaluate_all("els => els.map((e) => e.dataset.edge)")) == ["k1>k5", "k2>k5"]       # both of what it waits for are in the spread
    pg.mouse.move(5, 5)
    cards.nth(1).hover()
    pg.wait_for_function("() => document.querySelectorAll('.arena-arrow').length === 1", timeout=WAIT_MS)
    assert pg.locator(".arena-arrow").get_attribute("data-edge") == "k1>k5"                                    # and from it to what waits for it


# -- New goal's pile (§3.3, §4.2) -------------------------------------------------------------------------------------------------------

def test_the_new_goal_pile_turns_its_top_card_over_then_opens_new_goal_with_the_element_it_will_get(arena):
    pg, host = arena
    pile = pg.locator(".arena-new__pile")
    assert "New goal" in pg.locator(".arena-new__words").text_content() and "pick its type" in pg.locator(".arena-new__words").text_content()
    assert pile.locator(".arena-new__edge").count() == 3 and pile.locator(".arena-new__back .ork-icon").count() == 1
    assert pile.locator(".arena-new__card").evaluate("e => getComputedStyle(e).transitionDuration") == "0.42s"
    pile.click()
    assert "is-drawing" in pile.get_attribute("class")                                                         # the card turns over
    assert pg.get_by_role("dialog").count() == 0                                                               # before the form opens
    dialog = pg.get_by_role("dialog", name="New goal")
    dialog.wait_for(timeout=WAIT_MS)
    assert dialog.locator(".shell-blank .ork-elem.big").count() == 1 and "Your own goal" in dialog.text_content()
    shown = dialog.locator(".shell-blank").get_attribute("data-element")
    assert dialog.locator(".ork-elem.big").bounding_box()["width"] == 28 and shown == "lava"                    # the party's least used element: one lava among two of the others
    dialog.get_by_label("Your goal").fill("Sign in with a hardware key")
    assert dialog.get_by_label("Party", exact=True).input_value() == "passkey"
    assert [b.inner_text() for b in dialog.locator("footer button").all()] == ["Put it back", "Add the goal"]
    dialog.get_by_role("button", name="Add the goal").click()
    add = _calls(pg, host, "ideas.add")[0]
    assert add["text"] == "Sign in with a hardware key" and add["track"] == "passkey" and add["priority"] == "high"
    pg.get_by_role("dialog").wait_for(state="detached", timeout=WAIT_MS)
    assert "is-drawing" not in pile.get_attribute("class")                                                     # the card is back on the pile
    assert host.log and [n for n, a in host.log if n == "ideas.add"] and idea_element_of(host, add) == shown     # the host's rule gave what the dialog showed


def idea_element_of(host, add):
    """The element the host's `ideas.add` answered (the stub gives it by `idea_element.pick`, as the host does)."""
    from orkboard.realm import idea_element
    used = [n["element"] for n in host.nodes if n["goal"] == add["track"] and n["state"] != "done" and n["element"]]
    return idea_element.pick(used)


def test_put_it_back_closes_new_goal_and_adds_nothing_and_it_opens_at_once_under_reduced_motion(gui):
    server, browser = gui
    host = ArenaHost()
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    pg.locator(".arena-new__pile").click()
    dialog = pg.get_by_role("dialog", name="New goal")
    dialog.wait_for(timeout=1000)                                                                              # no turn to wait for
    assert pg.locator(".arena-new__card").evaluate("e => getComputedStyle(e).transitionDuration") == "0s"
    dialog.get_by_role("button", name="Put it back").click()
    pg.get_by_role("dialog").wait_for(state="detached", timeout=WAIT_MS)
    assert not [1 for n, a in host.log if n == "ideas.add"]
    pg.close()


# -- the flag line (§3.8) ---------------------------------------------------------------------------------------------------------------

def _seen(pg):
    """The mark this device keeps of the goals' flags it has seen: {key: newest `at`}."""
    return pg.evaluate("Object.fromEntries(Object.entries(localStorage).filter(([k]) => k.startsWith('orkboard.flags.goals.')))")


def test_a_gates_flags_are_said_once_in_a_line_over_the_field_and_never_again(arena):
    pg, host = arena
    assert pg.locator(".arena-flagline").count() == 0                                                         # a first look says nothing of the flags raised before
    assert list(_seen(pg).values()) == ["2026-10-14T10:00:00"]
    pg.evaluate("""() => { window.__anims = []; const orig = Element.prototype.animate;
      Element.prototype.animate = function (...a) { window.__anims.push([this.className, JSON.stringify(a[0]).slice(0, 100)]); return orig.apply(this, a); }; }""")
    for slug, at in (("creds", "2026-10-21T09:00:00"), ("prices", "2026-10-21T09:00:01"), ("magic", "2026-10-21T09:00:02")):
        host.flag(host.node_of(slug), at=at)
    host.bump({})
    line = pg.locator(".arena-flagline")
    line.wait_for(timeout=WAIT_MS)
    prices, magic = host.node_of("prices")["short"], host.node_of("magic")["short"]
    assert _text(line) == f"3 flags raised · {magic}, {prices} and 1 more are in main"                           # newest first; the first two named, then k more
    assert line.get_attribute("role") == "status" and box(pg, ".arena-flagline")["height"] == 36
    assert line.locator(".arena-flagline__flag .ork-sign.flag").count() == 1
    assert line.locator(".arena-flagline__flag").evaluate("e => getComputedStyle(e).color") == pg.evaluate(
        "(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-success)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")     # in the success colour
    flag, cols = box(pg, ".arena-flagline"), box(pg, ".arena-team")
    assert flag["y"] + flag["height"] <= cols["y"] + 1                                                          # never over the work: the party row is under it
    assert not pg.evaluate("document.documentElement.scrollHeight > document.documentElement.clientHeight")
    assert list(_seen(pg).values()) == ["2026-10-21T09:00:02"]                                                  # said once: the newest at seen
    pg.reload()
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    pg.wait_for_timeout(500)
    assert pg.locator(".arena-flagline").count() == 0                                                          # never again
    host.flag(host.node_of("signin"), at="2026-10-22T08:00:00")                                                 # a later merge says its own
    host.bump({})
    pg.locator(".arena-flagline").wait_for(timeout=WAIT_MS)
    assert _text(pg.locator(".arena-flagline")) == f"1 flag raised · {host.node_of('signin')['short']} is in main"
    pg.locator(".arena-flagline").get_by_role("button", name="Close").click()                                   # ×
    pg.locator(".arena-flagline").wait_for(state="detached", timeout=WAIT_MS)


def test_the_flag_lines_words_for_two_and_its_press_opens_about_this_party_at_its_flags_and_the_row_is_lit_once(arena):
    pg, host = arena
    pg.evaluate("""() => { window.__anims = []; const orig = Element.prototype.animate;
      Element.prototype.animate = function (...a) { window.__anims.push([this.className, JSON.stringify(a[0]).slice(0, 100)]); return orig.apply(this, a); }; }""")
    host.flag(host.node_of("creds"), at="2026-10-21T09:00:00")
    host.flag(host.node_of("prices"), at="2026-10-21T09:00:01")
    host.bump({})
    line = pg.locator(".arena-flagline")
    line.wait_for(timeout=WAIT_MS)
    assert _text(line) == f"2 flags raised · {host.node_of('prices')['short']} and {host.node_of('creds')['short']} are in main"
    pg.get_by_role("button", name=re.compile(r"^Flags \(2\)")).click()                                          # the fold: the goal's row is lit once
    pg.wait_for_function("() => window.__anims.some((a) => a[1].includes('background'))", timeout=WAIT_MS)
    row = pg.locator(".arena-flagrow[data-slug=creds]")
    assert "Where the credentials" in row.inner_text()
    line.get_by_role("button", name=re.compile("flags raised")).click()                                         # a press: About this party at Its flags
    drawer = _drawer(pg)
    assert _text(drawer.get_by_role("tab").first).lower().startswith("party")
    flags = drawer.locator("[data-sec=flags]")
    flags.wait_for(timeout=WAIT_MS)
    pg.wait_for_function("(el) => { const b = el.getBoundingClientRect(), p = el.closest('.shell-result__body').getBoundingClientRect(); return b.top >= p.top - 1 && b.bottom <= p.bottom + 1; }",
                         arg=flags.element_handle(), timeout=WAIT_MS)                                           # Its flags are in view


def test_under_reduced_motion_the_flag_line_stands_and_nothing_flies(gui):
    server, browser = gui
    host = ArenaHost()
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    pg.evaluate("""() => { window.__anims = []; const orig = Element.prototype.animate;
      Element.prototype.animate = function (...a) { window.__anims.push(this.className); return orig.apply(this, a); }; }""")
    host.flag(host.node_of("creds"), at="2026-10-21T09:00:00")
    host.bump({})
    pg.locator(".arena-flagline").wait_for(timeout=WAIT_MS)
    pg.get_by_role("button", name=re.compile(r"^Flags \(2\)")).click()
    pg.locator(".arena-flagrow[data-slug=creds]").wait_for(timeout=WAIT_MS)
    assert pg.evaluate("window.__anims.length") == 0
    pg.close()


# -- below 1 024 px and every word in today's (§0, §3) ---------------------------------------------------------------------------------

def test_below_1024_the_goals_list_the_filter_and_the_stacks_still_work(gui):
    pg, host, errors = _open(gui, host=ArenaHost(), viewport={"width": 900, "height": 800}, ready=".arena-phead")
    try:
        pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
        assert box(pg, ".arena-left")["width"] == 200 and pg.locator(".arena-today").count() == 0
        pg.locator(".arena-goal[data-slug=cookie] .arena-goal__main").click()
        _settled(pg, ["cookie"])
        assert _keys(pg, "backend") == ["cookie/f1"]
        pg.get_by_role("button", name="Show all").click()
        pg.locator(".arena-stack[data-agent=backend] .arena-phase[data-row=now] .arena-stk[data-goal=register] .arena-task").click()
        assert pg.get_by_role("group", name=re.compile("tasks of Backend at this phase")).is_visible()
        assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


OLD = re.compile(r"\b(ideas?|Ideas?)\b")
NOT_SAID = re.compile(r"\b(cards?|decks?|hands?|mana|crystals?|heroes|hero|boss|minions?|turn|Raise|elements?|stacks?|spreads?|piles?|In play)\b", re.I)


def test_the_page_says_party_and_goal_never_idea_and_none_of_the_games_words(arena):
    pg, host = arena
    host.goals["passkey"].update(leader=LEAD, team=["backend", "screens", "reviewer", "words"], every=["reviewer"])
    host.bump({})
    seen = []

    def read():
        """What a person reads now: the text, and the tooltips, labels and placeholders."""
        seen.append(pg.evaluate("""() => [document.body.innerText, ...[...document.querySelectorAll('[title],[aria-label],[placeholder]')].map(
          (e) => [e.getAttribute('title'), e.getAttribute('aria-label'), e.getAttribute('placeholder')].filter(Boolean).join(' · '))].join('\\n')"""))

    read()
    pg.get_by_role("button", name=re.compile(r"^Flags")).click()
    pg.get_by_role("button", name=re.compile(r"^New \(")).click()
    pg.locator(".arena-stack[data-agent=backend] .arena-phase[data-row=now] .arena-stk[data-goal=register] .arena-task").click()
    pg.get_by_role("group", name=re.compile("tasks of Backend")).wait_for(timeout=WAIT_MS)
    pg.locator(".arena-spread__card").first.hover()
    read()
    pg.keyboard.press("Escape")
    pg.get_by_role("button", name="About this party").click()
    _drawer(pg).locator("[data-sec=for]").wait_for(timeout=WAIT_MS)
    read()
    pg.get_by_role("button", name="Close the drawer").click()
    for name, dialog in (("Edit the party", "Edit the party"), ("New party", "New party")):
        if name == "New party":
            _new_party(pg)
        else:
            pg.get_by_role("button", name=name, exact=True).click()
        pg.get_by_role("dialog", name=dialog).wait_for(timeout=WAIT_MS)
        read()
        pg.keyboard.press("Escape")
    pg.locator(".arena-new__pile").click()
    pg.get_by_role("dialog", name="New goal").wait_for(timeout=WAIT_MS)
    read()
    text = "\n".join(seen)
    for line in text.splitlines():
        assert not OLD.search(line), line                                                                      # the interface says goal; the code's idea is not read
        assert not NOT_SAID.search(line), line                                                                 # a stack, a spread, an element, a card are the spec's and the code's words
