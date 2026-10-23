"""Spec 63 B on the desktop (docs/specs/63-party-gathered.md §3, Tests → B; decisions §76): Chromium at 1 440 × 900 against the one window's stub host (tests/test_shell_browser.py).
*Save party* in New party gathers the seats' heads into the party's deck once the dialog has closed and the new party is shown: a copy of each head (six at most, the leader's first)
travels from its seat's box to the deck's centre, `steps(6)`, 0.30 s, 35 ms apart, over everything and taking no press, and is gone on landing; then the deck is lit once. None after
*Edit the party*'s save, for a New goal made through its party first (`then: "idea"`), under reduced motion or after a refused save; a head whose seat is scrolled out of the dialog
starts from *Save party*'s box."""
from __future__ import annotations

import re

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_shell_browser import StubHost, _calls, _new_party, _open, _show_goal  # noqa: E402

pytestmark = pytest.mark.browser

ABOUT, SLUG = "Pixel game.", "pixel-game"                  # what the stub makes a party's slug of: the first two words of *What it is for*

RECORD = """() => {
  const g = window.__g = {copies: {}, lit: [], first: null};
  const animate = Element.prototype.animate;
  Element.prototype.animate = function (...a) {
    g.lit.push({cls: String(this.className), kf: JSON.stringify(a[0]), opts: a[1], left: document.querySelectorAll('.arena-gather').length});
    return animate.apply(this, a);
  };
  const tick = () => {
    const all = [...document.querySelectorAll('.arena-gather')];
    if (all.length && !g.first) {                                    // the first frame in which a head is there: what else is on the page
      g.first = {dialogs: document.querySelectorAll('[role=dialog]').length, scrims: document.querySelectorAll('.arena-spread, [data-modal-backdrop]').length,
                 shown: !!document.querySelector('.arena[data-goal="pixel-game"]'), deck: document.querySelector('.arena-ptop__deck').getBoundingClientRect().toJSON()};
    }
    all.forEach((e) => {
      const r = e.getBoundingClientRect(), key = e.style.getPropertyValue('--delay'), cs = getComputedStyle(e);
      const c = g.copies[key] ||= {start: {x: e.offsetLeft, y: e.offsetTop, width: e.offsetWidth, height: e.offsetHeight}, src: e.getAttribute('src'), dx: e.style.getPropertyValue('--dx'), dy: e.style.getPropertyValue('--dy'), s: e.style.getPropertyValue('--s'),
        delay: cs.animationDelay, duration: cs.animationDuration, easing: cs.animationTimingFunction, name: cs.animationName, position: cs.position, events: cs.pointerEvents, z: cs.zIndex, n: 0};
      c.last = r.toJSON();
      c.n += 1;
    });
    requestAnimationFrame(tick);
  };
  tick();
}"""


class GatherHost(StubHost):
    """The stub, which refuses a party's save while `refuse` is set."""

    def __init__(self):
        super().__init__()
        self.refuse = False

    def handle(self, name, a):
        if name == "ideas.goal_save" and self.refuse:
            self.log.append((name, a))
            return {"error": "The party cannot be saved now."}
        return super().handle(name, a)


@pytest.fixture
def shell(gui):
    pg, host, errors = _open(gui, host=GatherHost())
    _show_goal(pg)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _fill(pg, craft="game"):
    """New party, its seats from the library's `craft` (the Game: six heads), what it is for."""
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.locator(f'.shell-craft-tile[data-craft="{craft}"]').click()
    dlg.get_by_label("What it is for").fill(ABOUT)
    heads = {"game": 6, "engineering": 4}[craft]
    pg.wait_for_function("(n) => document.querySelectorAll('.shell-team-seat .ork-race__head').length === n", arg=heads, timeout=WAIT_MS)
    pg.wait_for_function("() => [...document.querySelectorAll('.shell-team-seat .ork-race__head')].every((e) => e.complete)", timeout=WAIT_MS)
    dlg.locator(".shell-price").wait_for(timeout=WAIT_MS)                                               # the dialog has taken its height
    return dlg


def _seats(pg, dlg, scroll=0):
    """The seats' heads as the dialog shows them with its body scrolled to `scroll` (it is 2 500 px high in a 760 px window: only some seats are in view): each head's box and image,
    and where its copy starts: its own box when it is in the body's visible part, else its size at the centre of *Save party*'s box."""
    body = dlg.locator(".shell-modal__body")
    at = body.evaluate("(e, y) => { e.scrollTop = y; return e.scrollTop; }", scroll)                     # as far as it goes
    pg.wait_for_function("(y) => Math.abs(document.querySelector('.shell-modal__body').scrollTop - y) < 1", arg=at, timeout=WAIT_MS)
    view, save = body.bounding_box(), dlg.get_by_role("button", name="Save party").bounding_box()
    heads = [{**h.bounding_box(), "src": h.get_attribute("src")} for h in dlg.locator(".shell-team-seat .ork-race__head").all()]
    for h in heads:
        h["on"] = h["y"] + h["height"] > view["y"] and h["y"] < view["y"] + view["height"]
        h["from"] = h if h["on"] else {"x": save["x"] + (save["width"] - h["width"]) / 2, "y": save["y"] + (save["height"] - h["height"]) / 2, "width": h["width"], "height": h["height"]}
    return heads


def _centre(b):
    return b["x"] + b["width"] / 2 if "x" in b else b["left"] + b["width"] / 2, b["y"] + b["height"] / 2 if "y" in b else b["top"] + b["height"] / 2


def _gathered(pg):
    """Once the deck is lit (the gather is over): what the recorder saw."""
    pg.wait_for_function("() => window.__g.lit.some((a) => a.cls.includes('arena-ptop__deck'))", timeout=WAIT_MS)
    return pg.evaluate("window.__g")


def _quiet(pg):
    """The party is shown and the dialog gone: and then some time for a gather to have started, had there been one."""
    pg.locator(f'.arena[data-goal="{SLUG}"]').wait_for(timeout=WAIT_MS)
    pg.get_by_role("dialog").wait_for(state="detached", timeout=WAIT_MS)
    pg.wait_for_timeout(900)


def test_save_party_gathers_the_heads_from_their_seats_into_the_deck_and_lights_it(shell):
    pg, host = shell
    dlg = _fill(pg)
    seats = _seats(pg, dlg, 500)                                                                       # the leader's seat and the four builders' in view, the checker's below
    assert [s["on"] for s in seats] == [True] * 5 + [False]
    pg.evaluate(RECORD)
    dlg.get_by_role("button", name="Save party").click()
    got = _gathered(pg)
    assert _calls(pg, host, "ideas.goal_save")[0]["leader"] == "game-designer"
    copies = [got["copies"][f"{i * 35}ms"] for i in range(6)]                                         # six, 35 ms apart, the leader's first
    assert sorted(got["copies"]) == sorted(f"{i * 35}ms" for i in range(6))
    deck = _centre(got["first"]["deck"])
    for i, (c, seat) in enumerate(zip(copies, seats)):
        assert c["src"] == seat["src"].replace(".png", "@2x.png") and re.search(r"/races/\w+-\w+@2x\.png$", c["src"])    # the head's own image
        assert all(abs(c["start"][k] - seat["from"][k]) <= 2 for k in ("x", "y", "width", "height"))       # it starts in its seat's box (the one out of view: at *Save party*)
        x, y = _centre(c["start"])
        assert abs(x + float(c["dx"][:-2]) - deck[0]) <= 2 and abs(y + float(c["dy"][:-2]) - deck[1]) <= 2         # its travel ends at the deck's centre …
        assert c["s"] == "0.4"                                                                         # … at 0.4 of its size
        near = lambda b: ((_centre(b)[0] - deck[0]) ** 2 + (_centre(b)[1] - deck[1]) ** 2) ** 0.5       # noqa: E731
        assert c["n"] >= 3 and near(c["last"]) < near(c["start"]) * 0.8                               # it was seen moving toward the deck
        assert 0.4 <= c["last"]["width"] / c["start"]["width"] < 0.95                                   # … and getting smaller
        assert (c["name"], c["duration"], c["easing"], c["position"], c["events"]) == ("arena-gather", "0.3s", "steps(6)", "fixed", "none")
        assert float(c["delay"][:-1]) == pytest.approx(i * 0.035) and int(c["z"]) > 120                # 35 ms apart; over the dialogs' layers
    assert "elf-elder" in copies[0]["src"]                                                             # the Game designer first
    assert got["first"]["dialogs"] == 0 and got["first"]["scrims"] == 0 and got["first"]["shown"]      # the dialog is closed, nothing dims, the party is shown
    lit = [a for a in got["lit"] if "arena-ptop__deck" in a["cls"]]
    assert len(lit) == 1 and "var(--ork-ink)" in lit[0]["kf"] and lit[0]["opts"] == {"duration": 600, "easing": "steps(4, end)"}      # the deck lit once, as the quiet reward
    assert lit[0]["left"] == 0 and pg.locator(".arena-gather").count() == 0                           # when the last had landed; the copies are gone
    assert pg.locator(".shell-goal").count() == 1                                                      # About this party opens in the drawer as today


def test_a_party_of_four_gathers_four_heads_the_leader_first(shell):
    pg, host = shell
    dlg = _fill(pg, "engineering")
    seats = _seats(pg, dlg)
    pg.evaluate(RECORD)
    dlg.get_by_role("button", name="Save party").click()
    got = _gathered(pg)
    assert sorted(got["copies"]) == ["0ms", "105ms", "35ms", "70ms"]
    assert [got["copies"][f"{i * 35}ms"]["src"] for i in range(4)] == [s["src"].replace(".png", "@2x.png") for s in seats]
    assert "peon-elder" in got["copies"]["0ms"]["src"]                                                 # the Architect leads


def test_the_party_is_usable_while_the_heads_travel(shell):
    pg, host = shell
    dlg = _fill(pg)
    pg.evaluate(RECORD)
    dlg.get_by_role("button", name="Save party").click()
    pg.wait_for_function("() => Object.keys(window.__g.copies).length > 0", timeout=WAIT_MS)            # the heads have started (read from the record: they may be gone by now)
    assert pg.locator(f'.arena[data-goal="{SLUG}"]').count() == 1 and pg.locator(".arena-ptop__deck").is_enabled()      # nothing waits for the heads
    got = _gathered(pg)
    assert {c["events"] for c in got["copies"].values()} == {"none"}                                    # they take no press
    assert got["lit"]                                                                                   # and they land


def test_a_head_whose_seat_is_scrolled_out_of_the_dialog_starts_from_save_partys_box(shell):
    pg, host = shell
    dlg = _fill(pg)
    seats = _seats(pg, dlg, 100000)                                                                    # the dialog scrolled to its end: only the checker's seat is in view
    assert [s["on"] for s in seats] == [False] * 5 + [True]
    save = dlg.get_by_role("button", name="Save party").bounding_box()
    pg.evaluate(RECORD)
    dlg.get_by_role("button", name="Save party").click()
    got = _gathered(pg)
    assert len(got["copies"]) == 6
    for i, seat in enumerate(seats):
        start = got["copies"][f"{i * 35}ms"]["start"]
        assert all(abs(start[k] - seat["from"][k]) <= 2 for k in ("x", "y", "width", "height"))
        if not seat["on"]:                                                                              # the head is its own size, at the middle of *Save party*
            assert abs(start["x"] + start["width"] / 2 - (save["x"] + save["width"] / 2)) <= 2 and abs(start["y"] + start["height"] / 2 - (save["y"] + save["height"] / 2)) <= 2
            assert (start["width"], start["height"]) == (24, 22)


def test_edit_the_partys_save_gathers_nothing(shell):
    pg, host = shell
    pg.get_by_role("button", name="Edit the party").click()
    dlg = pg.get_by_role("dialog", name="Edit the party")
    dlg.get_by_label("What it is for").fill("More people try Orkline, and stay.")
    pg.evaluate(RECORD)
    dlg.get_by_role("button", name="Save party").click()
    assert _calls(pg, host, "ideas.goal_save")[0]["slug"] == "ship-sync"
    pg.get_by_role("dialog").wait_for(state="detached", timeout=WAIT_MS)
    pg.wait_for_timeout(900)
    got = pg.evaluate("window.__g")
    assert got["copies"] == {} and got["lit"] == [] and pg.locator(".arena-gather").count() == 0


def test_a_refused_save_gathers_nothing_and_the_one_that_follows_gathers_once(shell):
    pg, host = shell
    dlg = _fill(pg)
    host.refuse = True
    pg.evaluate(RECORD)
    dlg.get_by_role("button", name="Save party").click()
    pg.get_by_text("The party cannot be saved now.").first.wait_for(timeout=WAIT_MS)
    pg.wait_for_timeout(900)
    assert dlg.is_visible() and pg.evaluate("window.__g.copies") == {} and pg.evaluate("window.__g.lit") == []     # the dialog stays; nothing waits
    host.refuse = False
    dlg.get_by_role("button", name="Save party").click()
    got = _gathered(pg)
    assert len(got["copies"]) == 6 and len(_calls(pg, host, "ideas.goal_save", 2)) == 2                 # one gather, of the second press


def test_a_goal_made_through_its_party_first_gathers_nothing_the_goal_form_is_what_is_looked_at(gui):
    host = StubHost()
    host.goals, host.ideas = {}, {}                                                                     # a project with no party yet
    pg, host, errors = _open(gui, host=host, ready=".arena-note")
    pg.get_by_role("button", name="New goal").click()
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.get_by_label("What it is for").fill(ABOUT)
    pg.evaluate(RECORD)
    dlg.get_by_role("button", name="Save party").click()
    pg.get_by_role("dialog", name="New goal").wait_for(timeout=WAIT_MS)                                  # New goal opens right after
    pg.get_by_role("dialog", name="New goal").get_by_role("button", name="Put it back").click()
    pg.locator(f'.arena[data-goal="{SLUG}"]').wait_for(timeout=WAIT_MS)
    pg.wait_for_timeout(900)
    got = pg.evaluate("window.__g")
    assert got["copies"] == {} and got["lit"] == [] and pg.locator(".arena-gather").count() == 0
    pg.close()
    assert not errors, "\n".join(errors)


def test_under_reduced_motion_nothing_gathers(gui):
    host = GatherHost()
    server, browser = gui
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.wait_for_selector(".arena-ptop", timeout=WAIT_MS)
    _show_goal(pg)
    dlg = _fill(pg)
    pg.evaluate(RECORD)
    dlg.get_by_role("button", name="Save party").click()
    _quiet(pg)
    got = pg.evaluate("window.__g")
    assert got["copies"] == {} and got["lit"] == [] and pg.locator(".arena-gather").count() == 0
    pg.close()
    assert not errors, "\n".join(errors)
