"""Spec 43 C on the desktop (docs/specs/43-party-measured.md §3.3, Tests → C): the price line when the picker opens and after a seat changes (one
call for the changes of 300 ms), *a first guess* and *from this project's last N ideas*, each check's *adds about … · about half of them*, in
New goal and in Edit goal's *Change the party*."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import WAIT_MS, StubHost, _calls, _open, _show_goal  # noqa: E402

pytestmark = pytest.mark.browser


@pytest.fixture
def shell(gui):
    pg, host, errors = _open(gui, host=StubHost())
    _show_goal(pg)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def asked(host):
    return [a for n, a in host.log if n == "ideas.party_price"]


def test_new_goal_asks_the_price_when_the_party_is_picked_and_says_it_under_the_bands(shell):
    pg, host = shell
    pg.get_by_role("button", name="New goal").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    assert not asked(host)                                                                        # step 1: no party yet
    dlg.locator('.shell-craft-tile[data-craft="design"]').click()
    price = dlg.locator(".shell-price")
    price.wait_for(timeout=WAIT_MS)
    assert " ".join(price.inner_text().split()) == "This party: about $2–6 an idea from this project's last 12 ideas"
    assert asked(host) == [{"leader": "product-designer", "team": ["ui-kit", "artist", "accessibility-reviewer"], "every": []}]
    bands = dlg.get_by_role("region", name="Checks").bounding_box(), price.bounding_box()
    assert bands[1]["y"] > bands[0]["y"]                                                          # under the bands
    host.learned = False
    dlg.get_by_role("button", name="Take in: Analyst").click()
    dlg.get_by_role("button", name="Take in: Copywriter").click()
    dlg.get_by_role("button", name="Take out: Artist").click()                                    # three changes within 300 ms: one call
    pg.wait_for_function("() => document.querySelector('.shell-price')?.innerText.includes('a first guess')", timeout=WAIT_MS)
    got = _calls(pg, host, "ideas.party_price", 2)
    assert len(got) == 2 and got[1] == {"leader": "analyst", "team": ["ui-kit", "accessibility-reviewer", "copywriter"], "every": []}
    assert " ".join(price.inner_text().split()) == "This party: about $2–6 an idea a first guess: it learns from this project's ideas"
    dlg.get_by_role("button", name="Next").click()                                                # 3. the checks say what each adds
    checks = dlg.get_by_role("group", name="Checks")
    text = " ".join(checks.inner_text().split())
    assert "adds about $0.35 to an idea it checks · about half of them" in text and "an idea they all apply to" not in text
    checks.get_by_label("Every idea: Accessibility reviewer").check()
    pg.wait_for_function("() => document.querySelector('.shell-checks')?.innerText.includes('· every idea')", timeout=WAIT_MS)
    assert asked(host)[-1]["every"] == ["accessibility-reviewer"]
    assert dlg.get_by_label("Description").count() == 1 and not dlg.get_by_role("button", name="Save goal").is_hidden()   # never blocks Save


def test_below_a_dollar_the_price_is_said_in_cents(shell):
    pg, host = shell
    import tests.test_shell_browser as t
    original = t.party_price
    t.party_price = lambda a, learned=True: {**original(a, learned), "low": 0.4, "high": 1.2}
    try:
        pg.get_by_role("button", name="New goal").click()
        dlg = pg.get_by_role("dialog", name="New goal")
        dlg.locator('.shell-craft-tile[data-craft="engineering"]').click()
        dlg.locator(".shell-price").wait_for(timeout=WAIT_MS)
        assert " ".join(dlg.locator(".shell-price").inner_text().split()).startswith("This party: about $0.40–1.20 an idea")
    finally:
        t.party_price = original


def test_edit_goal_asks_when_the_party_is_changed_and_its_checks_say_what_they_add(shell):
    pg, host = shell
    pg.get_by_role("button", name="Edit goal Ship sync").click()
    dlg = pg.get_by_role("dialog", name="Edit goal")
    assert not asked(host)                                                                        # the party is not picked yet
    dlg.get_by_role("button", name="Change the party").click()
    dlg.locator(".shell-price").wait_for(timeout=WAIT_MS)
    assert len(asked(host)) == 1
    dlg.get_by_role("button", name="Take in: Reviewer").click()
    pg.wait_for_function("() => document.querySelector('.shell-checks')?.innerText.includes('adds about')", timeout=WAIT_MS)
    assert "adds about $0.35 to an idea it checks · about half of them" in " ".join(dlg.get_by_role("group", name="Checks").inner_text().split())
