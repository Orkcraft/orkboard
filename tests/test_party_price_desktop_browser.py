"""Spec 43 C on the desktop (docs/specs/43-party-measured.md §3.3, Tests → C; docs/specs/50-parties-and-goals.md §3.7): the price line when the picker opens and
after a seat changes (one call for the changes of 300 ms), *a first guess* and *from this project's last N goals*, each check's *adds about … · about half of
them*, in New party and in Edit the party's *Change the party*."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import WAIT_MS, StubHost, _open, _show_goal  # noqa: E402

pytestmark = pytest.mark.browser


@pytest.fixture
def shell(gui):
    pg, host, errors = _open(gui, host=StubHost())
    _show_goal(pg)
    pg.wait_for_function("() => document.querySelector('.arena-ibar__goal')?.innerText.includes('a goal')", timeout=WAIT_MS)       # the party line has asked its own price
    host.price_base = len([1 for n, _a in host.log if n == "ideas.party_price"])
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def asked(host):
    """What the dialog asked (the party line asked its own price before it opened)."""
    return [a for n, a in host.log if n == "ideas.party_price"][host.price_base:]


def asks(pg, host, at_least):
    """`asked`, once the dialog has asked `at_least` times."""
    for _ in range(WAIT_MS // 50):
        if len(asked(host)) >= at_least:
            break
        pg.wait_for_timeout(50)
    return asked(host)


def test_new_party_asks_the_price_when_it_opens_and_after_a_seat_changes_and_says_it_under_the_bands(shell):
    pg, host = shell
    pg.get_by_role("button", name="New party", exact=True).click()
    dlg = pg.get_by_role("dialog", name="New party")
    price = dlg.locator(".shell-price")
    price.wait_for(timeout=WAIT_MS)
    assert asked(host) == [{"leader": "architect", "team": ["grunt", "tester", "reviewer"], "every": [], "craft": "engineering"}]       # the library's engineering party, asked at once
    dlg.locator('.shell-craft-tile[data-craft="design"]').click()
    got = asks(pg, host, 2)
    assert got[1] == {"leader": "product-designer", "team": ["ui-kit", "artist", "accessibility-reviewer"], "every": [], "craft": "design"}
    assert " ".join(price.inner_text().split()) == "This party: about $2–6 a goal from this project's last 12 goals"
    bands = dlg.get_by_role("region", name="Checks").bounding_box(), price.bounding_box()
    assert bands[1]["y"] > bands[0]["y"]                                                          # under the bands
    host.learned = False
    dlg.get_by_role("button", name="Take in: Analyst").click()
    dlg.get_by_role("button", name="Take in: Copywriter").click()
    dlg.get_by_role("button", name="Take out: Artist").click()                                    # three changes within 300 ms: one call
    pg.wait_for_function("() => document.querySelector('.shell-price')?.innerText.includes('a first guess')", timeout=WAIT_MS)
    got = asks(pg, host, 3)
    assert len(got) == 3 and got[2] == {"leader": "analyst", "team": ["ui-kit", "accessibility-reviewer", "copywriter"], "every": [], "craft": "design"}
    assert " ".join(price.inner_text().split()) == "This party: about $2–6 a goal a first guess: it learns from this project's goals"
    checks = dlg.get_by_role("group", name="Checks")                                              # the checks say what each adds to a goal
    text = " ".join(checks.inner_text().split())
    assert "adds about $0.35 to a goal it checks · about half of them" in text and "a goal they all apply to" not in text and "Checks on every goal" in " ".join(checks.text_content().split())
    checks.get_by_label("Every goal: Accessibility reviewer").check()
    pg.wait_for_function("() => document.querySelector('.shell-checks')?.innerText.includes('· every goal')", timeout=WAIT_MS)
    assert asked(host)[-1]["every"] == ["accessibility-reviewer"]
    dlg.get_by_label("What it is for").fill("A party that saves.")
    assert dlg.get_by_label("What it is for").count() == 1 and not dlg.get_by_role("button", name="Save party").is_hidden()   # never blocks Save


def test_below_a_dollar_the_price_is_said_in_cents(shell):
    pg, host = shell
    import tests.test_shell_browser as t
    original = t.party_price
    t.party_price = lambda a, learned=True, hints=(): {**original(a, learned, hints), "low": 0.4, "high": 1.2}
    try:
        pg.get_by_role("button", name="New party", exact=True).click()
        dlg = pg.get_by_role("dialog", name="New party")
        dlg.locator(".shell-price").wait_for(timeout=WAIT_MS)
        assert " ".join(dlg.locator(".shell-price").inner_text().split()).startswith("This party: about $0.40–1.20 a goal")
    finally:
        t.party_price = original


def test_edit_the_party_asks_when_the_party_is_changed_and_its_checks_say_what_they_add(shell):
    pg, host = shell
    pg.get_by_role("button", name="Edit the party").click()
    dlg = pg.get_by_role("dialog", name="Edit the party")
    n = len(asked(host))
    assert dlg.locator(".shell-price").count() == 0                                               # the party is not picked yet
    dlg.get_by_role("button", name="Change the party").click()
    dlg.locator(".shell-price").wait_for(timeout=WAIT_MS)
    assert len(asked(host)) == n + 1
    dlg.get_by_role("button", name="Take in: Reviewer").click()
    pg.wait_for_function("() => document.querySelector('.shell-checks')?.innerText.includes('adds about')", timeout=WAIT_MS)
    assert "adds about $0.35 to a goal it checks · about half of them" in " ".join(dlg.get_by_role("group", name="Checks").inner_text().split())


HINTS = ["Reviewer found nothing in its last 12 checks.", "No one in the party writes code: code tasks go to this project's agent for code (the Grunt when none)."]


def test_hints_are_quiet_lines_under_the_price_and_never_block_save(shell):
    """Spec 43 E: muted, one line each, no button; the price is asked with the party's craft when a party of the library is picked."""
    pg, host = shell
    host.hints = list(HINTS)
    pg.get_by_role("button", name="New party", exact=True).click()
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.locator(".shell-hint").first.wait_for(timeout=WAIT_MS)
    lines = dlg.locator(".shell-hint")
    assert lines.all_inner_texts() == HINTS and lines.first.evaluate("e => e.closest('.shell-price') === null")
    assert lines.first.evaluate("e => getComputedStyle(e).color") != dlg.locator(".shell-price").evaluate("e => getComputedStyle(e).color")     # muted
    assert dlg.locator(".shell-hint button, .shell-hint a").count() == 0
    assert asked(host)[0]["craft"] == "engineering"
    dlg.get_by_label("What it is for").fill("A party that saves with its hints.")
    assert dlg.get_by_role("button", name="Save party").is_enabled()                                    # a hint never blocks Save
