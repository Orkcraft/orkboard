"""Spec 68 part B on the desktop, a Release party (docs/specs/68-release-and-route.md §3, §7.3–§7.6, §8 "B"): Chromium at 1 440 × 900 against the world of tests/test_route_desktop_browser.py (the Passkey party, Ideation,
Website and a Release party whose leader is the Release manager, a skeleton). Release is the library's fifth mixed tile in New party and shows *Releases from* ticked (*Every party but Ideation*); Edit the party shows it
for a party that offers *A release*; New goal of *A release* asks **What goes in** after *Version* (a held flag greyed *In 1.4 already*, the empty line, *Add the goal* still adds); the Release party's Goals say *k flags
wait for a release* (a press opens New goal of *A release*), its Flags a release's version and *k goals*, **Mark it out** (asking first) and then *Out in 1.4*; another party's flags say *In Release 1.4*, *Out in 1.3* or
*Waits for a release* (only with a Release party). Screenshots to the scratchpad directory when ORKCRAFT_SHOTS_DIR is set."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_route_desktop_browser import RouteHost, shot  # noqa: E402
from tests.test_shell_browser import _calls, _new_party, _open, _parties, _show_goal  # noqa: E402

pytestmark = pytest.mark.browser

CANDIDATES = [
    {"goal": "badge", "title": "A badge on the icon", "party": "passkey", "party_name": "Passkey", "element": "ice", "at": "2026-10-20T09:00:00", "commit": "def5678", "held": ""},
    {"goal": "dark-ui", "title": "Dark sign-in page", "party": "passkey", "party_name": "Passkey", "element": "ice", "at": "2026-10-21T09:00:00", "commit": "abc1234", "held": ""},
    {"goal": "button", "title": "Passkey button on the page", "party": "passkey", "party_name": "Passkey", "element": "meadow", "at": "2026-10-14T10:00:00", "commit": "0a1b2c3", "held": "1.4"},
]
ASK = "Is 1.4 out in the stores? Orkboard submits nothing: say so once you have."


@pytest.fixture
def released(gui):
    pg, host, errors = _open(gui, host=RouteHost(), ready=".arena[data-goal=passkey]")
    host.candidates = [dict(c) for c in CANDIDATES]
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _flags(pg):
    """The Flags fold of the party shown, opened."""
    fold = pg.locator(".arena-flags .arena-fold")
    fold.wait_for(timeout=WAIT_MS)
    if fold.get_attribute("aria-expanded") != "true":
        fold.click()
    pg.locator(".arena-flags__list").wait_for(timeout=WAIT_MS)
    return pg.locator(".arena-flags__list")


def _release_form(pg):
    """The Release party's *k flags wait for a release*, pressed: New goal of A release."""
    _show_goal(pg, "release")
    pg.locator(".arena-waitrel").click()
    form = pg.get_by_role("dialog", name="New goal")
    form.locator('.arena-typed[data-type="release"]').wait_for(timeout=WAIT_MS)
    return form


# -- New party: Release is the fifth mixed tile ------------------------------------------------------------------------------------------------------------

def test_release_in_new_party_shows_releases_from_ticked_every_party_but_ideation_and_saves_the_default_unsent(released):
    pg, host = released
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    assert dlg.locator(".arena-releasesfrom").count() == 0                                                  # only a Release party takes goals from the others
    dlg.locator('.shell-craft-tile[data-craft="release"]').click()
    box = dlg.locator(".arena-releasesfrom")
    box.wait_for(timeout=WAIT_MS)
    names = [r.inner_text().strip() for r in box.locator(".arena-releasesfrom__row").all()]
    assert names == ["Passkey", "Pricing page", "Weekly report email", "Website", "Release"]                  # not Ideation, not General
    assert box.locator("input:checked").count() == 5 and "Every party but Ideation" in box.inner_text()
    dlg.locator('.shell-craft-tile[data-craft="game"]').click()
    box.wait_for(state="detached", timeout=WAIT_MS)
    dlg.locator('.shell-craft-tile[data-craft="release"]').click()
    box.wait_for(timeout=WAIT_MS)
    dlg.get_by_label("What it is for").fill("Our versions out.")
    dlg.get_by_role("button", name="Save party").click()
    sent = _calls(pg, host, "ideas.goal_save")[-1]
    assert sent["preset"] == "release" and sent["leader"] == "release-manager" and "releases_from" not in sent       # nothing changed: the default


def test_unticking_a_party_sends_the_parties_left_and_the_last_one_stays(released):
    pg, host = released
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.locator('.shell-craft-tile[data-craft="release"]').click()
    box = dlg.locator(".arena-releasesfrom")
    box.wait_for(timeout=WAIT_MS)
    for slug in ("pricing", "weekly", "website", "release"):
        box.locator(f'input[data-goal="{slug}"]').uncheck()
    assert "Only the ticked parties" in box.inner_text()
    box.locator('input[data-goal="passkey"]').click()                                                        # the last one stays: none would mean every party
    assert box.locator('input[data-goal="passkey"]').is_checked()
    dlg.get_by_label("What it is for").fill("Our versions out.")
    dlg.get_by_role("button", name="Save party").click()
    assert _calls(pg, host, "ideas.goal_save")[-1]["releases_from"] == ["passkey"]


# -- Edit the party --------------------------------------------------------------------------------------------------------------------------------------------

def _edit(pg, slug):
    close = pg.get_by_role("button", name="Close the drawer")
    if close.count():                                                                                        # the party's screen a save opens
        close.click()
        pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS) if pg.locator(".shell-drawer").count() else None
    _show_goal(pg, slug)
    pg.get_by_role("button", name="Edit the party").first.click()
    dlg = pg.get_by_role("dialog", name="Edit the party")
    dlg.wait_for(timeout=WAIT_MS)
    return dlg


def test_edit_the_party_of_a_release_party_shows_releases_from_as_saved_and_sends_only_what_changed(released):
    pg, host = released
    host.releases_from["release"] = ["passkey"]
    host.bump({})
    dlg = _edit(pg, "release")
    box = dlg.locator(".arena-releasesfrom")
    box.wait_for(timeout=WAIT_MS)
    assert [r.locator("input").is_checked() for r in box.locator(".arena-releasesfrom__row").all()] == [True, False, False, False]     # as saved; not itself
    assert "Only the ticked parties" in box.inner_text()
    dlg.get_by_label("What it is for").fill("Our versions out.")
    dlg.get_by_role("button", name="Save party").click()
    sent = _calls(pg, host, "ideas.goal_save")[-1]
    assert sent["slug"] == "release" and "releases_from" not in sent                                          # unchanged: not sent
    pg.wait_for_selector('.arena-phead[data-goal="release"][aria-current=true]', timeout=WAIT_MS)
    dlg = _edit(pg, "release")
    for slug in ("pricing", "weekly", "website"):
        dlg.locator(f'.arena-releasesfrom input[data-goal="{slug}"]').check()
    assert "Every party but Ideation" in dlg.locator(".arena-releasesfrom").inner_text()
    dlg.get_by_label("What it is for").fill("Our versions out.")
    dlg.get_by_role("button", name="Save party").click()
    assert _calls(pg, host, "ideas.goal_save", at_least=2)[-1]["releases_from"] == []                           # all ticked is the default: []


def test_edit_the_party_of_a_party_that_offers_a_release_starts_with_its_own_flags_and_one_that_does_not_has_none(released):
    pg, host = released
    host.offers = {"pricing"}
    host.bump({})
    dlg = _edit(pg, "passkey")
    assert dlg.locator(".arena-releasesfrom").count() == 0                                                   # Passkey does not offer A release
    dlg.get_by_role("button", name="Cancel").click()
    dlg = _edit(pg, "pricing")
    box = dlg.locator(".arena-releasesfrom")
    box.wait_for(timeout=WAIT_MS)
    assert box.locator("input:checked").count() == 0 and "Its own flags" in box.inner_text()
    box.locator('input[data-goal="passkey"]').check()
    assert "Its own flags and the ticked parties" in box.inner_text()
    dlg.get_by_label("What it is for").fill("Prices.")
    dlg.get_by_role("button", name="Save party").click()
    assert _calls(pg, host, "ideas.goal_save")[-1]["releases_from"] == ["passkey"]


# -- New goal of A release -----------------------------------------------------------------------------------------------------------------------------------

def test_k_flags_wait_for_a_release_opens_new_goal_of_a_release_with_what_goes_in_ticked_and_a_held_one_greyed(released):
    pg, host = released
    _show_goal(pg, "release")
    wait = pg.locator(".arena-waitrel")
    assert wait.inner_text().strip() == "2 flags wait for a release" and wait.locator(".ork-sign.flag").count() == 1
    assert pg.locator(".arena-goals").bounding_box()["y"] < wait.bounding_box()["y"] < pg.locator(".arena-deck").bounding_box()["y"]       # at the top of its Goals
    host.nodes = [n for n in host.nodes if n["slug"] != "dark-ui"]
    host.bump({})
    pg.wait_for_function("() => document.querySelector('.arena-waitrel')?.textContent.trim() === '1 flag waits for a release'", timeout=WAIT_MS)
    host.nodes.append(host.node_of("badge") | {"slug": "dark-ui", "title": "Dark sign-in page", "short": "Dark sign-in page"})
    host.bump({})
    pg.wait_for_function("() => document.querySelector('.arena-waitrel')?.textContent.trim() === '2 flags wait for a release'", timeout=WAIT_MS)
    wait.click()
    form = pg.get_by_role("dialog", name="New goal")
    form.locator('.arena-typed[data-type="release"]').wait_for(timeout=WAIT_MS)
    assert form.locator(".arena-typed__head b").text_content() == "A release" and "for Release" in form.locator(".arena-typed__for").inner_text()
    goes = form.get_by_role("group", name="What goes in")
    goes.locator("input").first.wait_for(timeout=WAIT_MS)
    labels = form.locator(".ok-font-label").all_text_contents()
    assert labels.index("Version") < labels.index("What goes in") < labels.index("What is new")               # after Version
    rows = goes.locator(".arena-goesin__row")
    assert [r.get_attribute("data-goal") for r in rows.all()] == ["badge", "dark-ui", "button"]
    assert [goes.locator(f'input[data-goal="{g}"]').is_checked() for g in ("badge", "dark-ui", "button")] == [True, True, False]       # the free ones ticked
    held = goes.locator('.arena-goesin__row[data-goal="button"]')
    assert held.locator("input").is_disabled() and "In 1.4 already" in held.inner_text() and "is-held" in held.get_attribute("class")
    assert held.evaluate("e => getComputedStyle(e).opacity") != "1" and "Passkey · 20 Oct" in rows.first.inner_text()
    assert rows.first.locator(".ork-elem.ice").count() == 1                                                  # its goal's element
    assert "Nothing has raised" not in goes.inner_text()
    shot(pg, "desk-whatgoesin.png")
    form.get_by_label("Its title").fill("Release 1.5")
    form.get_by_label("Version").fill("1.5")
    goes.locator('input[data-goal="dark-ui"]').uncheck()
    form.get_by_role("button", name="Add the goal").click()
    sent = _calls(pg, host, "ideas.add")[-1]
    assert sent["type"] == "release" and sent["asks"] == {"version": "1.5"} and sent["goes_in"] == ["badge"] and sent["track"] == "release"
    form.wait_for(state="detached", timeout=WAIT_MS)


def test_with_nothing_flagged_since_the_last_release_it_says_so_and_the_goal_can_still_be_added(released):
    pg, host = released
    host.candidates = []
    form = _release_form(pg)
    goes = form.get_by_role("group", name="What goes in")
    goes.get_by_text("Nothing has raised its flag since 1.3.").wait_for(timeout=WAIT_MS)
    form.get_by_label("Its title").fill("Fixes")
    form.get_by_role("button", name="Add the goal").click()
    assert _calls(pg, host, "ideas.add")[-1]["goes_in"] == []
    host.since = None                                                                                        # before the first release: since the start
    pg.locator(".arena-waitrel").click()
    pg.get_by_text("Nothing has raised its flag since the start.").wait_for(timeout=WAIT_MS)


def test_kept_for_tonight_a_release_goal_sends_no_goals(released):
    pg, host = released
    form = _release_form(pg)
    form.get_by_label("Its title").fill("Release 1.5")
    form.get_by_role("button", name="Put it back").click()
    sent = _calls(pg, host, "ideas.add")[-1]
    assert sent["night"] is True and "goes_in" not in sent


# -- the flags ------------------------------------------------------------------------------------------------------------------------------------------------

def test_a_releases_row_says_its_version_and_goals_mark_it_out_asks_first_and_then_every_flag_says_out(released):
    pg, host = released
    _show_goal(pg, "release")
    flags = _flags(pg)
    r14, r13 = flags.locator("li", has=pg.locator('.arena-flagrow[data-slug="r14"]')), flags.locator("li", has=pg.locator('.arena-flagrow[data-slug="r13"]'))
    assert "1.4 · 1 goal" in r14.inner_text() and r14.get_by_role("button", name="Mark it out").count() == 1
    assert "Out in 1.3" in r13.inner_text() and r13.get_by_role("button", name="Mark it out").count() == 0         # out already
    shot(pg, "desk-release.png")
    r14.get_by_role("button", name="Mark it out").click()
    ask = r14.get_by_role("alert")
    assert ask.inner_text().startswith(ASK) and ask.get_by_role("button").all_text_contents() == ["Out", "Not yet"]
    assert not _calls(pg, host, "ideas.release_out", at_least=1, ms=200)                                      # asked first, nothing sent
    ask.get_by_role("button", name="Not yet").click()
    assert r14.get_by_role("alert").count() == 0 and r14.get_by_role("button", name="Mark it out").count() == 1
    r14.get_by_role("button", name="Mark it out").click()
    host.refuse = "Its flag is not raised yet: a release goes out once it is in main"
    r14.get_by_role("button", name="Out", exact=True).click()
    pg.get_by_text(host.refuse).wait_for(timeout=WAIT_MS)                                                   # the host's words
    assert r14.get_by_role("alert").count() == 1                                                              # and the question stays
    host.refuse = ""
    r14.get_by_role("button", name="Out", exact=True).click()
    assert _calls(pg, host, "ideas.release_out", at_least=2)[-1] == {"slug": "r14"}
    pg.wait_for_function("() => document.querySelector('.arena-flagrow[data-slug=r14]')?.textContent.includes('Out in 1.4')", timeout=WAIT_MS)
    assert r14.get_by_role("button", name="Mark it out").count() == 0 and r14.get_by_role("alert").count() == 0
    _show_goal(pg, "passkey")                                                                                # the goal that went in says it too
    row = _flags(pg).locator('.arena-flagrow[data-slug="button"]')
    assert "Out in 1.4" in row.inner_text()


def test_another_partys_flags_say_their_release_or_that_they_wait_only_with_a_release_party(released):
    pg, host = released
    flags = _flags(pg)
    said = {s: flags.locator(f'.arena-flagrow[data-slug="{s}"] .arena-flagrow__rel').inner_text().strip() for s in ("button", "creds", "badge", "dark-ui")}
    assert said == {"button": "In Release 1.4", "creds": "Out in 1.3", "badge": "Waits for a release", "dark-ui": "Waits for a release"}
    assert flags.locator('.arena-flagrow[data-slug="badge"] .arena-flagrow__rel').get_attribute("data-rel") == "waits"


def test_without_a_release_party_no_flag_waits_for_a_release(gui):
    pg, host, errors = _open(gui, host=RouteHost(release=False), ready=".arena[data-goal=passkey]")
    try:
        flags = _flags(pg)
        assert flags.locator('.arena-flagrow[data-slug="badge"]').count() == 1 and flags.locator(".arena-flagrow__rel").count() == 0
        assert pg.locator(".arena-waitrel").count() == 0
        assert "Waits for a release" not in _parties(pg).page.locator("body").inner_text()
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_an_older_host_draws_the_release_party_as_any_party(gui):
    pg, host, errors = _open(gui, host=RouteHost(old=True), ready=".arena[data-goal=passkey]")
    try:
        _show_goal(pg, "release")
        assert pg.locator(".arena-waitrel").count() == 0 and pg.locator(".arena-release, .arena-flagrow__rel").count() == 0
        assert "/races/skeleton-" in pg.locator('.arena-phead[data-goal="release"] img.ork-race__head').get_attribute("src")
    finally:
        pg.close()
    assert not errors, "\n".join(errors)
