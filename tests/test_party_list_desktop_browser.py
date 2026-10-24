"""Spec 69 B on the desktop (docs/specs/69-parties-in-the-column.md §1–§5; decisions §84), in a real browser at 1 440 × 900 against the one window's stub host
(tests/test_arena_desktop_browser.py): the left column is the list of the parties — the project's line at its top (and not in the top bar), a heading for
each party in the Board's order, Operations, then + New party —; the open party (the one shown) has its leader as a member's row, Process now, its goals and the
New goal pile under its heading; a heading's head, name (two lines, then cut, the title whole), k/n and the sign of the stops that wait in a closed party;
a press on a closed heading shows that party, a press on the open one changes nothing; the keys; the column scrolls under the project's line; Ideation's
body; Operations; and the new party's heads gathering onto its heading's head. Screenshots to docs/design/img/v1/ when ORKCRAFT_SHOTS is set."""
from __future__ import annotations

import os

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import ArenaHost, _settle  # noqa: E402
from tests.test_ideation_desktop_browser import IdeationHost, PARTY as IDEAS  # noqa: E402
from tests.test_one_hand_desktop_browser import row, todo  # noqa: E402
from tests.test_party_gather_desktop_browser import RECORD, GatherHost, _centre, _fill, _gathered  # noqa: E402
from tests.test_shell_browser import SHOTS, _open, _parties, _show_goal, box  # noqa: E402

pytestmark = pytest.mark.browser

OPEN = ".arena-phead[aria-current=true]"
LONG = "Pricing page and the billing settings for every plan of the whole shop, with the yearly discounts and the receipts"
SHOP = "/work/shop"


class ListHost(ArenaHost):
    """The passkey party (a failed task and more), Pricing page with a long name and a to-do waiting, Weekly report email, and Operations with a failed run."""

    def __init__(self):
        super().__init__()
        self.ops = True
        self.goals["pricing"]["title"] = LONG
        self.extra_needs = [
            row("todo", goal="pricing", idea="prices", title="Prices from the billing settings", text="Reference picture", at="2026-10-16T09:00:00",
                todo=todo("t9", "Reference picture", "file", accept=["png"])),
            row("op_failed", goal="", op="r2", title="Nightly export", text="It failed", at="2026-10-19T09:00:00")]

    def snapshot(self):
        snap = super().snapshot()
        snap["state"]["projects"] = {"current": SHOP, "recent": [], "open": [{"path": SHOP, "name": "shop", "working": 0, "needs_you": 0, "review": 0}]}
        return snap


@pytest.fixture
def listed(gui):
    pg, host, errors = _open(gui, host=ListHost(), ready=".arena[data-goal=passkey]")
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _heads(pg):
    return _parties(pg).locator(".arena-phead")


def _shown(pg, slug):
    pg.locator(f'.arena[data-goal="{slug}"]').wait_for(timeout=WAIT_MS)
    _settle(pg)


def test_the_parties_are_listed_in_the_boards_order_then_operations_then_new_party(listed):
    pg, host = listed
    heads = _heads(pg)
    assert [h.get_attribute("data-goal") for h in heads.all()] == ["passkey", "pricing", "weekly", "@operations"]
    plus = pg.locator(".arena-pnew")
    assert plus.count() == 1 and plus.inner_text().strip() == "New party" and plus.get_attribute("title").startswith("One of yours")
    ys = [h.bounding_box()["y"] for h in heads.all()] + [plus.bounding_box()["y"]]
    assert ys == sorted(ys) and len(set(ys)) == 5                                                       # one under the other, + New party last
    assert pg.get_by_role("complementary", name="Parties").count() == 1 and box(pg, ".arena-left")["width"] == 248
    assert all(h.bounding_box()["height"] >= 40 for h in heads.all())
    assert pg.locator(".arena-ptop, .arena-hero, .arena-deck__card, .arena-spread").count() == 0       # the deck, the spread and the big card are gone
    plus.click()
    pg.get_by_role("dialog", name="New party").wait_for(timeout=WAIT_MS)


def test_the_project_switcher_heads_the_column_as_wide_as_it_and_is_not_in_the_top_bar(listed):
    pg, host = listed
    assert pg.locator(".shell-top .shell-proj").count() == 0 and pg.locator(".shell-top .arena-phead").count() == 0
    btn = pg.locator(".arena-left > .arena-left__proj .shell-proj__btn")
    assert btn.inner_text().strip() == "shop"
    col, b = box(pg, ".arena-left"), btn.bounding_box()
    assert b["y"] < _heads(pg).first.bounding_box()["y"] and b["y"] - col["y"] < 12                     # at the column's top, over the first heading
    assert col["width"] - b["width"] <= 24 and b["x"] >= col["x"]                                       # as wide as the column (its gutters)
    btn.click()
    menu = pg.get_by_role("menu", name="Projects")
    menu.wait_for(timeout=WAIT_MS)
    assert menu.get_by_role("menuitem").first.get_attribute("data-path") == SHOP and menu.bounding_box()["y"] > b["y"]
    pg.keyboard.press("Escape")
    menu.wait_for(state="detached", timeout=WAIT_MS)


def test_the_open_party_has_its_leader_process_now_its_goals_and_the_pile_under_its_heading(listed):
    pg, host = listed
    head = pg.locator(OPEN)
    assert head.get_attribute("data-goal") == "passkey" and head.get_attribute("aria-expanded") == "true" and head.get_attribute("title") == "Sign in with a passkey is open"
    assert _heads(pg).locator("xpath=self::*[@aria-current='true']").count() == 1                      # one open
    body = pg.locator(".arena-party.is-open .arena-pbody")
    assert body.count() == 1 and _parties(pg).locator(".arena-pbody").count() == 1                      # none under a closed heading
    assert head.locator(".ork-race__head").count() == 1 and head.locator(".arena-plist__head").bounding_box()["width"] == 24
    member = body.locator(".arena-lead .arena-member")                                                  # the leader as a member's row
    assert member.count() == 1 and member.locator(".ork-race__head.mid").count() == 1 and "Taskmaster" in member.inner_text()
    power = body.get_by_role("button", name="Process now", exact=False)
    assert power.count() == 1 and body.locator(".arena-hero, .arena-hero__edge").count() == 0
    ys = {k: body.locator(sel).first.bounding_box()["y"] for k, sel in (("head", ".arena-lead"), ("goals", ".arena-goals"), ("pile", ".arena-new"))}
    assert box(pg, OPEN)["y"] < ys["head"] < ys["goals"] < ys["pile"]
    assert body.locator(".arena-goals .arena-goal").count() >= 5 and body.locator(".arena-sec", has_text="Planning").count() == 1
    assert body.locator(".arena-new__pile").is_visible() and body.locator(".arena-new__words").text_content().startswith("New goal")     # the pile at its foot
    assert head.bounding_box()["y"] + head.bounding_box()["height"] <= ys["head"]
    assert not any(h.locator(".arena-phead__stop").count() for h in _heads(pg).all() if h.get_attribute("aria-current") == "true")      # the open heading has no sign


def test_a_long_name_stands_on_two_lines_cut_with_its_title_whole_and_a_short_one_is_not_cut(listed):
    pg, host = listed
    name = pg.locator('.arena-phead[data-goal="pricing"] .arena-phead__name')
    assert name.get_attribute("title") == LONG
    h = name.evaluate("e => ({client: e.clientHeight, scroll: e.scrollHeight, line: parseFloat(getComputedStyle(e).lineHeight)})")
    assert h["client"] == 2 * h["line"] and h["scroll"] > h["client"]                                   # two lines, then cut
    heading = pg.locator('.arena-phead[data-goal="pricing"]')
    assert heading.bounding_box()["height"] >= h["client"]                                              # the heading is as high as it needs
    short = pg.locator('.arena-phead[data-goal="weekly"] .arena-phead__name')
    assert short.evaluate("e => e.scrollHeight <= e.clientHeight") and short.inner_text() == "Weekly report email"
    assert name.evaluate("e => getComputedStyle(e).fontFamily") == short.evaluate("e => getComputedStyle(e).fontFamily")


def test_a_closed_party_with_a_stop_wears_one_sign_a_failed_one_in_the_danger_colour(listed):
    pg, host = listed
    sign = lambda goal: pg.locator(f'.arena-phead[data-goal="{goal}"] .arena-phead__stop')              # noqa: E731
    assert pg.locator(f"{OPEN} .arena-phead__stop").count() == 0
    assert sign("pricing").count() == 1 and sign("pricing").get_attribute("title") == "1 waits in Pricing page and the billing settings for every plan of the whole shop, with the yearly discounts and the receipts"
    assert sign("pricing").locator(".ork-sign.alert").count() == 1 and "is-danger" not in sign("pricing").get_attribute("class")
    assert sign("weekly").count() == 0                                                                  # nothing waits: no sign
    assert sign("@operations").count() == 1 and "is-danger" in sign("@operations").get_attribute("class") and sign("@operations").locator(".ork-sign.cross").count() == 1
    danger = pg.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-danger)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
    alert = pg.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-alert)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
    assert sign("@operations").evaluate("e => getComputedStyle(e).color") == danger and sign("pricing").evaluate("e => getComputedStyle(e).color") == alert
    pg.locator('.arena-phead[data-goal="pricing"]').click()                                             # shown: its stops are seen below, the sign goes; the passkey party's failure comes
    _shown(pg, "pricing")
    assert sign("pricing").count() == 0
    assert sign("passkey").count() == 1 and "is-danger" in sign("passkey").get_attribute("class") and sign("passkey").get_attribute("title").endswith("in Sign in with a passkey")


def test_a_press_on_a_closed_heading_shows_that_party_and_closes_the_other_a_press_on_the_open_one_does_nothing(listed):
    pg, host = listed
    assert pg.locator(".arena-team .arena-member").count() == 4                                         # the passkey party's team
    pg.locator(OPEN).click()                                                                            # the open heading: not a toggle
    pg.wait_for_timeout(200)
    assert pg.locator(OPEN).get_attribute("data-goal") == "passkey" and pg.locator(".arena-pbody").count() == 1 and pg.locator(".arena-team .arena-member").count() == 4
    pg.locator('.arena-phead[data-goal="weekly"]').click()
    _shown(pg, "weekly")
    assert pg.locator(OPEN).get_attribute("data-goal") == "weekly" and pg.locator(".arena-team .arena-member").count() == 0      # the board's columns are its team's
    old = pg.locator('.arena-phead[data-goal="passkey"]')
    assert old.get_attribute("aria-expanded") == "false" and old.get_attribute("aria-current") is None and old.get_attribute("title") == "Open Sign in with a passkey"
    assert pg.locator(".arena-pbody").count() == 1 and pg.locator(".arena-party.is-open").get_attribute("class").count("is-open") == 1
    pg.reload()                                                                                         # the party is kept per device
    _shown(pg, "weekly")
    assert pg.locator(OPEN).get_attribute("data-goal") == "weekly"


def test_the_headings_are_in_the_tab_order_the_arrows_move_between_them_and_enter_presses(listed):
    pg, host = listed
    pg.locator(OPEN).focus()
    pg.keyboard.press("ArrowDown")
    assert pg.evaluate("document.activeElement.dataset.goal") == "pricing"
    pg.keyboard.press("ArrowDown")
    pg.keyboard.press("ArrowDown")
    assert pg.evaluate("document.activeElement.dataset.goal") == "@operations"
    pg.keyboard.press("ArrowDown")
    assert pg.evaluate("document.activeElement.classList.contains('arena-pnew')")                       # + New party closes the list
    pg.keyboard.press("ArrowUp")
    pg.keyboard.press("ArrowUp")
    pg.keyboard.press("ArrowUp")
    assert pg.evaluate("document.activeElement.dataset.goal") == "pricing"
    pg.keyboard.press("Enter")
    _shown(pg, "pricing")
    assert pg.locator(OPEN).get_attribute("data-goal") == "pricing"
    assert all(h.evaluate("e => e.tabIndex") >= 0 for h in _heads(pg).all())                            # in the Tab order


def test_the_column_scrolls_on_its_own_under_the_projects_line_and_the_page_does_not(gui):
    pg, host, errors = _open(gui, host=ListHost(), viewport={"width": 1440, "height": 560}, ready=".arena[data-goal=passkey]")
    try:
        line = box(pg, ".arena-left__proj")
        list_ = pg.locator(".arena-plist")
        assert list_.evaluate("e => e.scrollHeight > e.clientHeight")                                  # the open party's goals are longer than the window
        assert list_.evaluate("e => getComputedStyle(e).overflowY") == "auto" and box(pg, ".arena-left")["y"] == 32
        list_.evaluate("e => { e.scrollTop = 10000; }")
        pg.wait_for_function("() => document.querySelector('.arena-plist').scrollTop > 0", timeout=WAIT_MS)
        assert box(pg, ".arena-left__proj") == line                                                    # the project's line stays at the column's top
        assert pg.locator(".arena-pnew").is_visible() and box(pg, ".arena-pnew")["y"] + 20 <= 560       # + New party is reachable at the foot
        assert not pg.evaluate("document.documentElement.scrollHeight > document.documentElement.clientHeight") and pg.evaluate("window.scrollY") == 0
        assert box(pg, ".arena-field")["y"] == 32                                                      # the board did not move with it
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_ideations_body_has_judge_now_and_its_pitches(gui):
    pg, host, errors = _open(gui, host=IdeationHost(), ready=".arena-phead")
    try:
        _show_goal(pg, IDEAS)
        body = pg.locator(".arena-party.is-open .arena-pbody")
        assert pg.locator(OPEN).get_attribute("data-goal") == IDEAS
        assert body.get_by_role("button", name="Judge now", exact=False).count() == 1 and body.get_by_role("button", name="Process now").count() == 0
        assert body.locator(".arena-lead .arena-member").count() == 1 and body.locator(".arena-goals h2").text_content() == "Pitches"
        assert "a pitch to judge" in body.locator(".arena-new__words").text_content()
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_operations_is_a_heading_with_its_icon_no_count_and_shows_operations(listed):
    pg, host = listed
    ops = pg.locator('.arena-phead[data-goal="@operations"]')
    assert ops.locator(".ork-icon").count() == 1 and ops.locator(".arena-phead__count, .ork-race__head").count() == 0 and ops.inner_text().strip() == "Operations"
    ops.click()
    pg.locator(".arena-ops").wait_for(timeout=WAIT_MS)
    assert pg.locator(OPEN).get_attribute("data-goal") == "@operations" and pg.locator(".arena-pbody").count() == 0
    assert pg.locator(".board-ops").is_visible() and pg.locator(".arena-left__proj .shell-proj__btn").is_visible() and _heads(pg).count() == 4     # the list stays
    pg.locator('.arena-phead[data-goal="passkey"]').click()
    _shown(pg, "passkey")


def test_a_new_partys_heads_gather_onto_its_headings_head(gui):
    pg, host, errors = _open(gui, host=GatherHost(), ready=".arena-phead")
    try:
        _show_goal(pg)
        dlg = _fill(pg)
        pg.evaluate(RECORD)
        dlg.get_by_role("button", name="Save party").click()
        got = _gathered(pg)
        pg.locator(".arena[data-goal=pixel-game]").wait_for(timeout=WAIT_MS)
        head = pg.locator(f"{OPEN} .arena-plist__head")
        assert pg.locator(OPEN).get_attribute("data-goal") == "pixel-game"                              # the new party is the open one
        target = _centre(head.bounding_box())
        first = _centre(got["first"]["deck"])
        assert abs(first[0] - target[0]) <= 2 and abs(first[1] - target[1]) <= 2                        # the heads landed on its heading's head …
        copy = got["copies"]["0ms"]
        cx, cy = _centre(copy["start"])
        assert abs(cx + float(copy["dx"][:-2]) - target[0]) <= 2 and abs(cy + float(copy["dy"][:-2]) - target[1]) <= 2 and copy["s"] == "0.4"      # … at 0.4 of their size
        assert any("arena-plist__head" in a["cls"] for a in got["lit"])                                  # and the head was lit once
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_the_column_in_the_offices_look(listed):
    pg, host = listed
    if os.environ.get("ORKCRAFT_SHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "desktop-party-list-1440x900.png"))
    assert pg.locator(f"{OPEN}").evaluate("e => getComputedStyle(e).backgroundColor") != pg.locator('.arena-phead[data-goal="weekly"]').evaluate("e => getComputedStyle(e).backgroundColor")
