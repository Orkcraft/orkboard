"""Spec 59 B on the desktop (docs/specs/59-mixed-parties.md §6, Tests → B): New party's library (the mixed first, a pick fills the seats and sends `preset`, a
seat changed clears it), the seats and the stage words by the leader (a Game's four builders and *Concept*, *Build*, *Playtest*; a leader with fewer seats:
the alert line, *Save party* off), and the board's stage words from the party's `stages` (today's from an older host that sends none)."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import ArenaHost  # noqa: E402
from tests.test_shell_browser import StubHost, _calls, _new_party, _open, _show_goal  # noqa: E402

pytestmark = pytest.mark.browser

GAME_STAGES = {"lead": {"word": "Concept"}, "build": {"word": "Build", "seats": 4}, "check": {"word": "Playtest", "seats": 1}}


@pytest.fixture
def party(gui):
    pg, host, errors = _open(gui, host=StubHost())
    _show_goal(pg)
    _new_party(pg)
    yield pg, host, pg.get_by_role("dialog", name="New party")
    pg.close()
    assert not errors, "\n".join(errors)


def _on(band):
    return [e.get_attribute("data-agent") for e in band.locator('.shell-team-row[aria-pressed="true"]').all()]


def test_the_library_lists_the_mixed_parties_first_then_one_craft_then_the_taskmaster_alone(party):
    pg, host, dlg = party
    assert [h.text_content() for h in dlg.locator(".shell-library-group h3").all()] == ["Mixed", "One craft"]
    assert [t.get_attribute("data-craft") for t in dlg.locator(".shell-craft-tile").all()] == [
        "game", "mobile-app", "website", "ideation", "engineering", "design", "data", "marketing", "product", "mixed"]
    game = dlg.locator('.shell-craft-tile[data-craft="game"]')
    assert "Game" in game.text_content() and "Rules, levels, art and sound, played through" in game.inner_text()
    assert game.locator(".ork-race__head").count() == 1 + 5                                       # the leader's head and its five members'
    assert dlg.locator('.shell-craft-tile[data-craft="engineering"]').get_attribute("aria-pressed") == "true"        # the party it starts from


def test_a_pick_fills_the_seats_and_is_sent_as_the_preset_until_a_seat_changes(party):
    pg, host, dlg = party
    dlg.locator('.shell-craft-tile[data-craft="mobile-app"]').click()
    assert dlg.locator('.shell-craft-tile[data-craft="mobile-app"]').get_attribute("aria-pressed") == "true"
    assert _on(dlg.get_by_role("region", name="Leads")) == ["product-manager"]
    assert _on(dlg.get_by_role("region", name="Builds")) == ["grunt", "artist", "aso"]
    assert _on(dlg.get_by_role("region", name="Checks")) == ["reviewer", "accessibility-reviewer"]
    dlg.get_by_label("Name", exact=True).fill("Pocket notes")
    dlg.get_by_role("button", name="Save party").click()
    got = _calls(pg, host, "ideas.goal_save")[0]
    assert got["preset"] == "mobile-app" and got["leader"] == "product-manager" and got["team"] == ["grunt", "artist", "aso", "reviewer", "accessibility-reviewer"]


def test_a_seat_changed_afterwards_clears_the_preset(party):
    pg, host, dlg = party
    dlg.locator('.shell-craft-tile[data-craft="website"]').click()
    dlg.get_by_role("button", name="Take out: SEO").click()
    assert all(t.get_attribute("aria-pressed") == "false" for t in dlg.locator(".shell-craft-tile").all())
    dlg.get_by_label("Name", exact=True).fill("Pages")
    dlg.get_by_role("button", name="Save party").click()
    assert "preset" not in _calls(pg, host, "ideas.goal_save")[0]


def test_a_game_has_four_builder_seats_and_the_stage_words_of_its_leader(party):
    pg, host, dlg = party
    dlg.locator('.shell-craft-tile[data-craft="game"]').click()
    leads, builds, checks = (dlg.get_by_role("region", name=n) for n in ("Leads", "Builds", "Checks"))
    assert [b.locator("h3").text_content() for b in (leads, builds, checks)] == ["Concept", "Build", "Playtest"]
    assert "4 of 4 seats" in builds.inner_text() and "1 of 1 seats" in checks.inner_text()
    assert builds.locator(".shell-team-seat").count() == 4 and builds.locator(".shell-team-seat:not(.is-empty)").count() == 4
    assert checks.locator(".shell-team-seat").count() == 1
    builds.get_by_role("button", name="Take in: Copywriter").click()                              # a fifth: no seat, and it says so with the leader
    pg.get_by_text("Build has 4 seats with Game designer: take one out first.").wait_for(timeout=WAIT_MS)
    dlg.locator('.shell-craft-tile[data-craft="engineering"]').click()                            # another leader: today's words and seats
    assert [b.locator("h3").text_content() for b in (leads, builds, checks)] == ["Planning", "Implementation", "Checking"]
    assert builds.locator(".shell-team-seat").count() == 3 and checks.locator(".shell-team-seat").count() == 2


def test_a_leader_with_fewer_seats_shows_the_extra_members_in_the_alert_colour_and_keeps_save_off_until_it_fits(party):
    pg, host, dlg = party
    dlg.locator('.shell-craft-tile[data-craft="game"]').click()
    dlg.get_by_label("Name", exact=True).fill("Pixels")
    save = dlg.get_by_role("button", name="Save party")
    assert save.is_enabled()
    dlg.get_by_role("region", name="Leads").get_by_role("button", name="Take in: Architect").click()
    builds = dlg.get_by_role("region", name="Builds")
    line = builds.get_by_role("alert")
    assert line.inner_text() == "Implementation has 3 seats with Architect: take one out first."
    assert builds.locator(".shell-team-seat.is-over").count() == 1 and builds.locator(".shell-team-seat").count() == 4
    assert builds.locator(".shell-team-seat.is-over").evaluate("e => getComputedStyle(e).borderTopColor") != builds.locator(".shell-team-seat:not(.is-over)").first.evaluate("e => getComputedStyle(e).borderTopColor")
    assert save.is_disabled()
    builds.get_by_role("button", name="Take out: Sound designer").click()
    assert builds.get_by_role("alert").count() == 0 and builds.locator(".shell-team-seat.is-over").count() == 0
    assert save.is_enabled()


class StagesHost(ArenaHost):
    """The map of a host that sends `stages` for the party shown (a Game designer's) and none for the other."""

    def map_doc(self):
        got = super().map_doc()
        for g in got["goals"]:
            if g["slug"] == "passkey":
                g["stages"] = GAME_STAGES
        return got


def _labels(pg):
    return [h.text_content() for h in pg.locator(".arena-cols__head .arena-lbl:not(.is-blank)").all()]


def test_the_board_says_the_stage_words_of_the_party_and_todays_without_stages(gui):
    pg, host, errors = _open(gui, host=StagesHost(), ready=".arena-phead")
    try:
        pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
        assert _labels(pg) == ["Build", "Playtest"]                                               # over the first builder, the first checker
        assert pg.locator(".arena-cols__head .arena-lbl", has_text="Build").get_attribute("title") == "4 seats"
        pg.locator(".arena-member.is-lead").click()                                               # the leader alone: its stage
        pg.locator(".arena-solo-wrap").wait_for(timeout=WAIT_MS)
        assert "Planning" not in pg.locator(".arena-solo-wrap").inner_text()
    finally:
        pg.close()
    assert not errors, "\n".join(errors)
    pg, host, errors = _open(gui, host=ArenaHost(), ready=".arena-phead")                          # an older host: no `stages`
    try:
        pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
        assert _labels(pg) == ["Implementation", "Checking"]
    finally:
        pg.close()
    assert not errors, "\n".join(errors)
