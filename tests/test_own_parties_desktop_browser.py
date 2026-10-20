"""Spec 43 F on the desktop (docs/specs/43-party-measured.md §6.3, Tests → F): *Save this party* on a goal's screen (the name, the replace);
*Your parties* in the picker fill the seats and the craft; a seat changed afterwards drops the id; Remove asks first."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import StubHost, _calls, _open, _sent, _show_goal  # noqa: E402

pytestmark = pytest.mark.browser

LEAN = {"id": "p-1a2b3c4d", "name": "Lean web", "craft": "engineering", "leader": "architect", "team": ["grunt", "tester", "reviewer"], "every": ["reviewer"],
        "own": [], "goals": 3, "projects": 2, "met": 2, "saved": "2026-10-20T10:00:00"}
FRESH = {**LEAN, "id": "p-5e6f7a8b", "name": "Fresh", "craft": "design", "leader": "product-designer", "team": ["ui-kit"], "every": [], "goals": 0, "projects": 0, "met": 0}


@pytest.fixture
def shell(gui):
    host = StubHost()
    host.own = [dict(LEAN), dict(FRESH)]
    pg, host, errors = _open(gui, host=host)
    _show_goal(pg)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def test_save_this_party_asks_a_name_asks_again_before_it_replaces_and_says_it_is_saved(shell):
    pg, host = shell
    host.goals["ship-sync"].update(team=["grunt", "reviewer"], every=["reviewer"], craft="design", leader=host.leader("architect"))
    host.bump({})
    pg.get_by_role("button", name="Open goal Ship sync").click()
    team = pg.locator(".shell-goal").get_by_role("region", name="Team")
    team.get_by_role("button", name="Save this party").click()
    name = team.get_by_label("Name of your party")
    assert name.input_value() == "Design party"                                                # filled with the goal's craft
    name.fill("Brand new")
    team.get_by_role("button", name="Save", exact=True).click()
    assert _sent(pg, host, ("ideas.party_save", {"goal": "ship-sync", "name": "Brand new"}))
    pg.get_by_text("Saved: pick it for a goal in any project.").wait_for(timeout=WAIT_MS)
    team.get_by_role("button", name="Save this party").click()
    team.get_by_label("Name of your party").fill("lean WEB")
    team.get_by_role("button", name="Save", exact=True).click()                                # a taken name: asked first
    team.get_by_text("Replace your party “Lean web”?").wait_for(timeout=WAIT_MS)
    team.get_by_role("button", name="Cancel").click()                                          # back to the name, still typed
    assert team.get_by_label("Name of your party").input_value() == "lean WEB"
    team.get_by_role("button", name="Save", exact=True).click()
    team.get_by_role("button", name="Replace it").click()
    assert _sent(pg, host, ("ideas.party_save", {"goal": "ship-sync", "name": "lean WEB", "replace": True}))


def _new_goal(pg):
    pg.get_by_role("button", name="New goal").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    dlg.locator('.shell-craft-tile[data-craft="design"]').click()
    return dlg


def test_your_parties_fill_the_seats_and_the_craft_and_a_seat_changed_afterwards_drops_the_id(shell):
    pg, host = shell
    dlg = _new_goal(pg)
    row = dlg.get_by_role("region", name="Your parties")
    chip = row.locator("[data-party=p-1a2b3c4d]")
    assert " ".join(chip.inner_text().split()) == "Lean web 3 goals in 2 projects · 2 met" and chip.locator("img").count() == 4         # its heads, name, use
    fresh = row.locator("[data-party=p-5e6f7a8b]")
    assert " ".join(fresh.inner_text().split()) == "Fresh"                                              # not used yet: nothing muted
    assert dlg.get_by_role("region", name="Leads").locator('.shell-team-row[aria-pressed="true"]').get_attribute("data-agent") == "product-designer"
    chip.get_by_role("button", name="Pick your party “Lean web”").click()                              # fills the leader, the builders, the checkers, Every idea, the craft
    assert dlg.get_by_role("region", name="Leads").locator('.shell-team-row[aria-pressed="true"]').get_attribute("data-agent") == "architect"
    assert [e.get_attribute("data-agent") for e in dlg.get_by_role("region", name="Builds").locator('.shell-team-row[aria-pressed="true"]').all()] == ["grunt", "tester"]
    assert [e.get_attribute("data-agent") for e in dlg.get_by_role("region", name="Checks").locator('.shell-team-row[aria-pressed="true"]').all()] == ["reviewer"]
    dlg.get_by_role("button", name="Next").click()
    assert "Engineering" in dlg.locator(".shell-party-line").inner_text() and "led by Architect" in dlg.locator(".shell-party-line").inner_text()
    assert dlg.get_by_label("Every idea: Reviewer").is_checked()
    dlg.get_by_label("Description").fill("A goal from your party.")
    dlg.get_by_role("button", name="Save goal").click()
    assert _calls(pg, host, "ideas.goal_save")[0] == {"about": "A goal from your party.", "craft": "engineering", "leader": "architect", "team": ["grunt", "tester", "reviewer"],
                                                      "every": ["reviewer"], "priority": "normal", "party": "p-1a2b3c4d"}
    dlg = _new_goal(pg)                                                                                # a seat changed afterwards: no id
    dlg.get_by_role("region", name="Your parties").get_by_role("button", name="Pick your party “Lean web”").click()
    dlg.get_by_role("button", name="Take out: Tester").click()
    dlg.get_by_role("button", name="Next").click()
    dlg.get_by_label("Description").fill("A changed party.")
    dlg.get_by_role("button", name="Save goal").click()
    assert "party" not in _calls(pg, host, "ideas.goal_save", 2)[1]


def test_remove_asks_first_and_the_goals_that_use_it_keep_their_agents(shell):
    pg, host = shell
    dlg = _new_goal(pg)
    row = dlg.get_by_role("region", name="Your parties")
    row.get_by_role("button", name="Remove your party “Lean web”").click()
    row.get_by_text("Remove your party “Lean web”? Goals that use it keep their agents.").wait_for(timeout=WAIT_MS)
    assert not [1 for n, _a in host.log if n == "ideas.party_drop"]                                    # asked, not dropped
    row.get_by_role("button", name="Keep it").click()
    assert row.locator("[data-party=p-1a2b3c4d]").count() == 1
    row.get_by_role("button", name="Remove your party “Lean web”").click()
    row.get_by_role("button", name="Remove it").click()
    assert _sent(pg, host, ("ideas.party_drop", {"id": "p-1a2b3c4d"}))
    pg.wait_for_function("() => !document.querySelector('[data-party=p-1a2b3c4d]')", timeout=WAIT_MS)


def test_edit_goal_picks_a_party_too_and_says_what_a_goal_keeps(shell):
    pg, host = shell
    host.goal_notes = ["Docs scribe is this project's already: kept as it is"]
    host.goals["ship-sync"]["about"] = "Sync is the first thing a second device needs."
    host.bump({})
    pg.get_by_role("button", name="Edit goal Ship sync").click()
    dlg = pg.get_by_role("dialog", name="Edit goal")
    dlg.get_by_role("button", name="Change the party").click()
    dlg.get_by_role("region", name="Your parties").get_by_role("button", name="Pick your party “Lean web”").click()
    dlg.get_by_role("button", name="Save goal").click()
    got = _calls(pg, host, "ideas.goal_save")[0]
    assert got["party"] == "p-1a2b3c4d" and got["leader"] == "architect" and got["team"] == ["grunt", "tester", "reviewer"] and got["slug"] == "ship-sync"
    pg.get_by_text("Docs scribe is this project's already: kept as it is").wait_for(timeout=WAIT_MS)
