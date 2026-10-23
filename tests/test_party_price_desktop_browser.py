"""Spec 43 C on the desktop (docs/specs/43-party-measured.md §3.3, Tests → C; docs/specs/50-parties-and-goals.md §3.7): the price line when the picker opens and
after a seat changes (one call for the changes of 300 ms), *a first guess* and *from this project's last N goals*, each check's *adds about … · about half of
them*, in New party and in Edit the party's *Change the party*. And spec 63 B (docs/specs/63-party-gathered.md §2, Tests → B): under the price the line *It can take:* with the
goal types the party would be offered (`types` of the price's answer), *with one more:* the ones that miss someone, *and k more* past two lines, a type the last seat change
opened lit once, nothing for an older host that sends no `types`."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from orkboard.realm import goal_types  # noqa: E402
from tests.browser_kit import gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import _new_party, WAIT_MS, StubHost, _open, _show_goal  # noqa: E402

pytestmark = pytest.mark.browser

GAME = ("feature", "bug", "tidy", "icon", "logo", "mechanic", "level", "character", "balance", "sound")        # spec 59 §4.3's lists
MOBILE = ("feature", "bug", "tidy", "screen", "icon", "logo", "pain", "experiment", "launch", "character", "store", "release")
NEEDS = {"screen": ("ui-kit", "Design system designer"), "experiment": ("experimenter", "Experimenter"), "launch": ("copywriter", "Copywriter")}


def types(ids, team=()):
    """`ideas.party_price`'s `types` (spec 63 §1): the catalog's rows for `ids` in that order; a type that needs an agent the team has not says its name in `missing`."""
    by = {t.id: t for t in goal_types.CATALOG}
    need = lambda i: NEEDS[i][1] if i in NEEDS and NEEDS[i][0] not in team else ""       # noqa: E731
    return [{"id": i, "name": by[i].name, "sign": by[i].sign, "missing": need(i)} for i in ids]


class TypesHost(StubHost):
    """A host that answers `types` for the leader and the team it is asked about: spec 59 §4.3's lists of the Game and the Mobile app, the Taskmaster's for any other leader.
    `offered` is a function of the call (None: an older host, no `types`)."""

    def __init__(self):
        super().__init__()
        self.offered = lambda a: types({"game-designer": GAME, "product-manager": MOBILE}.get(a["leader"], ("feature", "bug", "tidy")), a["team"])

    def handle(self, name, a):
        got = super().handle(name, a)
        if name == "ideas.party_price" and self.offered:
            got["types"] = self.offered(a)
        return got


RECORD = """() => {
  window.__lit = [];
  const animate = Element.prototype.animate;
  Element.prototype.animate = function (...a) { window.__lit.push({cls: String(this.className), type: this.dataset.type || '', kf: JSON.stringify(a[0]), opts: a[1]}); return animate.apply(this, a); };
}"""


@pytest.fixture
def shell(gui):
    pg, host, errors = _open(gui, host=TypesHost())
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
    _new_party(pg)
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
        _new_party(pg)
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
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.locator(".shell-hint").first.wait_for(timeout=WAIT_MS)
    lines = dlg.locator(".shell-hint")
    assert lines.all_inner_texts() == HINTS and lines.first.evaluate("e => e.closest('.shell-price') === null")
    assert lines.first.evaluate("e => getComputedStyle(e).color") != dlg.locator(".shell-price").evaluate("e => getComputedStyle(e).color")     # muted
    assert dlg.locator(".shell-hint button, .shell-hint a").count() == 0
    assert asked(host)[0]["craft"] == "engineering"
    dlg.get_by_label("What it is for").fill("A party that saves with its hints.")
    assert dlg.get_by_role("button", name="Save party").is_enabled()                                    # a hint never blocks Save


# -- It can take (spec 63 §2) ---------------------------------------------------------------------------------------------------------------

def _line(dlg):
    """The line *It can take:* as it reads."""
    return " ".join(dlg.locator(".shell-cantake").inner_text().split())


def _lit(pg):
    """The types lit so far (a type's `data-type`), each as the quiet reward: ink to its background, 0.6 s, in four steps."""
    got = pg.evaluate("window.__lit.filter((a) => a.cls === 'shell-cantake__one')")
    assert all("var(--ork-ink)" in a["kf"] and a["opts"] == {"duration": 600, "easing": "steps(4, end)"} for a in got)
    return [a["type"] for a in got]


def test_it_can_take_lists_the_types_of_the_party_with_their_signs_under_the_price_and_lights_the_new_ones_once(shell):
    pg, host = shell
    pg.evaluate(RECORD)                                                                           # before New party opens: the first answer is recorded too
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.locator(".shell-cantake").wait_for(timeout=WAIT_MS)
    assert _line(dlg) == "It can take: New feature · Fix a bug · Clean up"
    dlg.locator('.shell-craft-tile[data-craft="game"]').click()
    pg.wait_for_function("() => document.querySelector('.shell-cantake')?.innerText.includes('New sound')", timeout=WAIT_MS)
    line = dlg.locator(".shell-cantake")
    assert _line(dlg) == "It can take: New feature · Fix a bug · Clean up · New icon · New logo · New mechanic · New level · New character · Balance pass · New sound"
    assert [s.get_attribute("class") for s in line.locator(".ork-sign").all()] == [f"ork-sign {x}" for x in
                                                                                    ("feature", "bug", "tidy", "picture", "logo", "mechanic", "level", "character", "balance", "tune")]
    assert line.locator(".ork-sign").first.evaluate("e => getComputedStyle(e).color") != line.locator(".shell-cantake__one").first.evaluate("e => getComputedStyle(e).color")     # muted
    price, box = dlg.locator(".shell-price").bounding_box(), line.bounding_box()
    assert box["y"] > price["y"] + price["height"] - 1                                            # under the price line
    assert box["height"] <= 2 * float(line.evaluate("e => parseFloat(getComputedStyle(e).lineHeight)")) + 1          # two lines at most
    assert "with one more" not in _line(dlg) and not line.get_attribute("title")              # ten types fit: no "and k more"
    pg.wait_for_function("() => window.__lit.length >= 7", timeout=WAIT_MS)
    assert _lit(pg) == ["icon", "logo", "mechanic", "level", "character", "balance", "sound"]     # the seven the Game opened; nothing at the first answer, nothing for the three it had


def test_the_taskmaster_alone_the_party_that_takes_nothing_and_an_older_host(shell):
    pg, host = shell
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.locator('.shell-craft-tile[data-craft="game"]').click()
    pg.wait_for_function("() => document.querySelector('.shell-cantake')?.innerText.includes('New sound')", timeout=WAIT_MS)
    dlg.locator('.shell-craft-tile[data-craft="mixed"]').click()
    pg.wait_for_function("() => document.querySelectorAll('.shell-cantake .ork-sign').length === 3", timeout=WAIT_MS)
    assert _line(dlg) == "It can take: New feature · Fix a bug · Clean up"
    host.offered = lambda a: []
    dlg.locator('.shell-craft-tile[data-craft="data"]').click()
    pg.wait_for_function("() => document.querySelector('.shell-cantake')?.innerText.includes('nothing')", timeout=WAIT_MS)
    assert _line(dlg) == "It can take: nothing of its own yet: add a builder."
    host.offered = None                                                                           # an older host: the answer has no `types`
    dlg.locator('.shell-craft-tile[data-craft="design"]').click()
    pg.wait_for_function("() => !document.querySelector('.shell-cantake')", timeout=WAIT_MS)
    assert dlg.locator(".shell-price").count() == 1                                               # the price is still said


def test_the_types_that_miss_someone_follow_with_one_more_and_a_seat_that_opens_one_lights_it_once(shell):
    pg, host = shell
    host.offered = lambda a: types(("feature", "bug", "tidy", "screen", "pain", "launch"), a["team"])
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.locator('.shell-craft-tile[data-craft="product"]').click()                                # the Product manager, the Grunt, the Copywriter, the Reviewer
    pg.wait_for_function("() => document.querySelector('.shell-cantake')?.innerText.includes('Write the launch with one more')", timeout=WAIT_MS)       # the Copywriter is in this team
    assert _line(dlg) == "It can take: New feature · Fix a bug · Clean up · Solve a pain · Write the launch with one more: New screen (needs Design system designer)"
    assert dlg.locator('.shell-cantake [data-type="screen"] .ork-sign.screen').count() == 1          # drawn with its sign too
    pg.evaluate(RECORD)
    dlg.get_by_role("button", name="Take in: Design system designer").click()                    # the third builder opens New screen
    pg.wait_for_function("() => !document.querySelector('.shell-cantake').innerText.includes('with one more')", timeout=WAIT_MS)
    assert _line(dlg) == "It can take: New feature · Fix a bug · Clean up · New screen · Solve a pain · Write the launch"          # in the catalog's order
    pg.wait_for_function("() => window.__lit.length >= 1", timeout=WAIT_MS)
    assert _lit(pg) == ["screen"]
    dlg.get_by_role("button", name="Take out: Copywriter").click()                               # a type that goes is not lit: it is said to need the Copywriter
    pg.wait_for_function("() => document.querySelector('.shell-cantake')?.innerText.includes('Write the launch (needs Copywriter)')", timeout=WAIT_MS)
    assert _line(dlg).endswith("Solve a pain with one more: Write the launch (needs Copywriter)")
    dlg.get_by_role("button", name="Take in: Copywriter").click()                                # … and lit when it is back
    pg.wait_for_function("() => window.__lit.length >= 2", timeout=WAIT_MS)
    assert _lit(pg) == ["screen", "launch"]


def test_what_does_not_fit_in_two_lines_ends_with_and_k_more_and_its_title_lists_them_all(shell):
    pg, host = shell
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.locator('.shell-craft-tile[data-craft="mobile-app"]').click()                             # nine types, and three that miss someone
    pg.wait_for_function("() => document.querySelector('.shell-cantake')?.title", timeout=WAIT_MS)
    line = dlg.locator(".shell-cantake")
    said = line.get_attribute("title").split(", ")
    assert said[:3] == ["New feature", "Fix a bug", "Clean up"] and len(said) == 12             # as the line reads: the nine that miss no one, then the three that do
    assert said[9:] == ["New screen (needs Design system designer)", "Try an experiment (needs Experimenter)", "Write the launch (needs Copywriter)"]
    k = int(_line(dlg).rsplit("and ", 1)[1].split(" more")[0])
    assert 1 <= k < 12 and _line(dlg).endswith(f"and {k} more") and line.locator(".shell-cantake__one").count() == 12 - k
    assert line.bounding_box()["height"] <= 2 * float(line.evaluate("e => parseFloat(getComputedStyle(e).lineHeight)")) + 1
    assert line.evaluate("e => e.scrollHeight <= e.clientHeight + 1")                              # nothing is cut off by the box: what did not fit was left out whole
    dlg.locator('.shell-craft-tile[data-craft="mixed"]').click()                                  # three types fit: no title, no "and k more"
    pg.wait_for_function("() => document.querySelectorAll('.shell-cantake .ork-sign').length === 3", timeout=WAIT_MS)
    assert not line.get_attribute("title") and "more" not in _line(dlg)


def test_edit_the_party_has_the_line_and_a_new_leader_lights_what_it_opens(shell):
    pg, host = shell
    pg.get_by_role("button", name="Edit the party").click()
    dlg = pg.get_by_role("dialog", name="Edit the party")
    assert dlg.locator(".shell-cantake").count() == 0                                             # the party is not picked yet
    pg.evaluate(RECORD)
    dlg.get_by_role("button", name="Change the party").click()
    dlg.locator(".shell-cantake").wait_for(timeout=WAIT_MS)
    assert _line(dlg) == "It can take: New feature · Fix a bug · Clean up"
    dlg.get_by_role("region", name="Leads").get_by_role("button", name="Take in: Game designer").click()
    pg.wait_for_function("() => document.querySelector('.shell-cantake')?.innerText.includes('New sound')", timeout=WAIT_MS)
    assert _line(dlg).startswith("It can take: New feature · Fix a bug · Clean up · New icon · New logo · New mechanic")
    price, box = dlg.locator(".shell-price").bounding_box(), dlg.locator(".shell-cantake").bounding_box()
    assert box["y"] > price["y"]
    pg.wait_for_function("() => window.__lit.length >= 7", timeout=WAIT_MS)
    assert _lit(pg) == ["icon", "logo", "mechanic", "level", "character", "balance", "sound"]


def test_under_reduced_motion_nothing_is_lit(gui):
    server, browser = gui
    host = TypesHost()
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.wait_for_selector(".arena-ptop", timeout=WAIT_MS)
    _show_goal(pg)
    pg.evaluate(RECORD)
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.locator('.shell-craft-tile[data-craft="game"]').click()
    pg.wait_for_function("() => document.querySelector('.shell-cantake')?.innerText.includes('New sound')", timeout=WAIT_MS)
    assert _lit(pg) == [] and pg.evaluate("window.__lit.length") == 0                              # the line changes, nothing animates
    pg.close()
    assert not errors, "\n".join(errors)
