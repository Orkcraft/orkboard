"""Spec 64, the desktop (docs/specs/64-flags-raised.md §1–§3; Tests → B): Chromium at 1 440 × 900 against the one window's stub host (tests/test_arena_desktop_browser.py) whose gate's merge raises
the flags of two goals. When the flag line first stands, its goals' elements travel from the merge's press (else the gate's button) to a row after its flag, six at most, then the flag is raised
and the line lit once; with no gate on screen nothing travels and the flag is still raised; under reduced motion and on a hidden page the row is drawn still."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import ArenaHost  # noqa: E402
from tests.test_map_desktop_browser import node  # noqa: E402
from tests.test_shell_browser import _drawer, _sent  # noqa: E402

pytestmark = pytest.mark.browser

RECORD = """() => {
  window.__fly = {copies: [], starts: [], close: false};
  const seen = new WeakSet();
  const note = () => {
    document.querySelectorAll('.arena-flagfly').forEach((e) => {
      if (seen.has(e)) return;
      seen.add(e);
      const r = e.getBoundingClientRect(), s = e.style, c = getComputedStyle(e);
      window.__fly.copies.push({element: ['meadow', 'ice', 'dust', 'void', 'lava'].find((x) => e.classList.contains(x)), dx: s.getPropertyValue('--dx'), dy: s.getPropertyValue('--dy'),
        s: s.getPropertyValue('--s'), delay: s.getPropertyValue('--delay'), left: parseFloat(s.left), top: parseFloat(s.top), centre: [r.left + r.width / 2, r.top + r.height / 2], width: r.width,
        z: c.zIndex, pointer: c.pointerEvents, position: c.position, anim: c.animationName,
        places: [...document.querySelectorAll('.arena-flagline__el')].map((x) => getComputedStyle(x).visibility)});
      if (window.__fly.close) document.querySelector('.arena-flagline__x').click();
    });
  };
  new MutationObserver(note).observe(document.body, {childList: true});
  document.addEventListener('animationstart', (e) => window.__fly.starts.push([e.animationName, e.target.className]), true);
}"""

ELEMENTS = ["meadow", "ice", "dust", "void", "lava"]


class RaiseHost(ArenaHost):
    """The gate's merge raises the flags of *Where the credentials are kept* and *Prices from the billing settings* (and of `more` goals besides), newest last."""

    def __init__(self, more=0):
        super().__init__()
        self.hold = False                                 # the merge raises nothing yet
        self.raises = ["creds", "prices"]
        for i in range(1, more + 1):
            slug = f"x{i}"
            n = node(slug, "passkey", f"Extra goal {i}", "done", 1, stage="done", progress={"done": 1, "total": 1}, folded=True)
            n.update(element=ELEMENTS[i % 5], flag=None)
            self.nodes.append(n)
            self.ideas[slug] = self.idea(slug, n["title"], "done", 50 + i, track="passkey")
            self.raises.append(slug)

    def raise_flags(self):
        for i, slug in enumerate(self.raises):
            self.flag(self.node_of(slug), at=f"2026-10-21T09:00:{i:02d}")

    def handle(self, name, a):
        if name == "ideas.gate_merge" and not self.hold:
            self.raise_flags()
        return super().handle(name, a)

    def newest(self, k=2):
        """The shorts of the goals raised, newest first, as the line names them."""
        return [self.node_of(s)["short"] for s in reversed(self.raises)][:k]


def _scene(gui, host, **page):
    server, browser = gui
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, **page)
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    pg.locator(".arena-gate__btn").wait_for(timeout=WAIT_MS)
    pg.wait_for_function("() => Object.keys(localStorage).some((k) => k.startsWith('orkboard.flags.goals.'))", timeout=WAIT_MS)       # this device has looked: what comes now is new
    return pg, errors


@pytest.fixture
def raising(gui):
    host = RaiseHost()
    pg, errors = _scene(gui, host)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


@pytest.fixture
def raising_many(gui):
    host = RaiseHost(more=6)
    pg, errors = _scene(gui, host)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _merge(pg, host):
    """The gate's screen is opened and its one press is made: returns the box of the press, as it is then."""
    pg.locator(".arena-gate__btn").click()
    view = _drawer(pg).locator(".arena-gateview")
    view.wait_for(timeout=WAIT_MS)
    button = view.get_by_role("button", name="Merge dev into main")
    box = button.bounding_box()
    pg.evaluate(RECORD)
    button.click()
    assert _sent(pg, host, ("ideas.gate_merge", {}))
    return box


def _fly(pg):
    return pg.evaluate("window.__fly")


def _centre(b):
    return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2


def _ms(x):
    return int(x["delay"][:-2])


def _over(pg):
    """The line has stood and the raise is over: the copies are gone, nothing waits to land, nothing is lit."""
    pg.wait_for_function("() => !document.querySelector('.arena-flagfly, .is-raising, .is-coming')", timeout=WAIT_MS)


def _elements(pg):
    return pg.locator(".arena-flagline__row .ork-elem").evaluate_all("els => els.map((e) => e.className.split(' ').filter((c) => c !== 'ork-elem'))")


def _starts(pg):
    return pg.evaluate("window.__fly.starts.map(([n, c]) => n + ' ' + c)")


# -- the raise (§1–§3) -------------------------------------------------------------------------------------------------------------------

def test_a_merge_from_the_gates_screen_travels_the_goals_elements_to_the_flag_line_then_the_flag_is_raised_and_the_line_lit(raising):
    pg, host = raising
    press = _merge(pg, host)
    pg.wait_for_function("() => window.__fly.copies.length === 2", timeout=WAIT_MS)
    fly = _fly(pg)
    px, py = _centre(press)
    assert [c["element"] for c in fly["copies"]] == ["meadow", "ice"]                                   # the line's order: the newest first, each its goal's element
    for c in fly["copies"]:
        assert abs(c["centre"][0] - px) <= 3 and abs(c["centre"][1] - py) <= 3                          # it starts at the merge's press …
        assert abs(c["width"] - press["height"]) <= 2 and abs(float(c["s"]) * 14 - press["height"]) <= 1  # … at the press's height
        assert c["position"] == "fixed" and c["z"] == "60" and c["pointer"] == "none" and c["anim"] == "arena-fly"     # over everything, taking no press
        assert c["places"] == ["hidden", "hidden"]                                                      # its place in the row is empty until it lands
    assert [_ms(c) for c in fly["copies"]] == [0, 35]                                                   # 35 ms apart
    pg.wait_for_function("() => window.__fly.starts.some(([n]) => n === 'arena-raise') && window.__fly.starts.some(([n]) => n === 'arena-lit')", timeout=WAIT_MS)
    starts = _starts(pg)
    assert "arena-raise arena-flagline__flag" in starts and "arena-lit arena-flagline is-raising" in starts       # the flag sign raised, the line lit
    assert [s for s in starts if s.startswith("arena-fly")] == ["arena-fly ork-elem meadow arena-flagfly", "arena-fly ork-elem ice arena-flagfly"]
    _over(pg)                                                                                           # the copies are gone, the line is as it was
    assert _elements(pg) == [["meadow"], ["ice"]]                                                       # … and its row has the two elements
    assert pg.locator(".arena-flagline__el").evaluate_all("els => els.map((e) => getComputedStyle(e).visibility)") == ["visible", "visible"]
    line = pg.locator(".arena-flagline")
    assert " ".join(line.inner_text().split()) == "2 flags raised · {} and {} are in main".format(*host.newest())     # the words are today's
    assert pg.locator(".arena-flagline").bounding_box()["height"] == 36
    for c, slot in zip(fly["copies"], pg.locator(".arena-flagline__el").all()):                          # each landed in its own place in the line, after the flag sign
        b = slot.bounding_box()
        assert abs(c["left"] - b["x"]) <= 1 and abs(c["top"] - b["y"]) <= 1
    flag, first = pg.locator(".arena-flagline__flag").bounding_box(), pg.locator(".arena-flagline__el").first.bounding_box()
    assert first["x"] >= flag["x"] + flag["width"]


def test_the_travel_leads_from_each_place_back_to_the_press(raising):
    pg, host = raising
    press = _merge(pg, host)
    pg.wait_for_function("() => window.__fly.copies.length === 2", timeout=WAIT_MS)
    _over(pg)
    px, py = _centre(press)
    for c, slot in zip(_fly(pg)["copies"], pg.locator(".arena-flagline__el").all()):
        end = _centre(slot.bounding_box())
        assert abs(end[0] + float(c["dx"][:-2]) - px) <= 1 and abs(end[1] + float(c["dy"][:-2]) - py) <= 1


def test_a_reload_does_not_raise_the_flags_again(raising):
    pg, host = raising
    _merge(pg, host)
    pg.locator(".arena-flagline").wait_for(timeout=WAIT_MS)
    _over(pg)
    pg.reload()
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    pg.evaluate(RECORD)
    pg.wait_for_timeout(700)
    assert pg.locator(".arena-flagline").count() == 0 and pg.locator(".arena-flagfly").count() == 0       # as today: said once
    assert _fly(pg)["copies"] == [] and _starts(pg) == []


def test_eight_flags_six_elements_travel_and_stay_in_the_row_and_the_words_say_the_rest(raising_many):
    pg, host = raising_many
    _merge(pg, host)
    pg.wait_for_function("() => window.__fly.copies.length === 6", timeout=WAIT_MS)
    _over(pg)
    fly = _fly(pg)
    assert len(fly["copies"]) == 6 and [_ms(c) for c in fly["copies"]] == [0, 35, 70, 105, 140, 175]
    assert len(_elements(pg)) == 6                                                                       # six in the row, in the line's order (the newest first)
    assert _elements(pg) == [[c["element"]] for c in fly["copies"]]
    a, b = host.newest()
    assert " ".join(pg.locator(".arena-flagline").inner_text().split()) == f"8 flags raised · {a}, {b} and 6 more are in main"      # the rest, in today's words (k = n − 2)


def test_the_gates_button_is_where_they_travel_from_when_nothing_was_pressed(raising):
    pg, host = raising
    pg.evaluate(RECORD)
    host.raise_flags()                                                                                    # raised from another device: no press here
    host.bump({})
    pg.wait_for_function("() => window.__fly.copies.length === 2", timeout=WAIT_MS)
    button = pg.locator(".arena-gate__btn").bounding_box()                                                # (the line has pushed the field down: it is read where it stands now)
    bx, by = _centre(button)
    for c in _fly(pg)["copies"]:
        assert abs(c["centre"][0] - bx) <= 3 and abs(c["centre"][1] - by) <= 3 and abs(c["width"] - button["height"]) <= 2
    _over(pg)
    assert _elements(pg) == [["meadow"], ["ice"]]


def test_a_merge_pressed_more_than_ten_seconds_ago_is_not_where_they_travel_from(raising):
    pg, host = raising
    host.hold = True                                                                                      # the merge is made, the Board raises nothing yet
    press = _merge(pg, host)
    pg.get_by_role("button", name="Close the drawer").click()
    pg.wait_for_timeout(10_400)
    host.hold = False
    host.raise_flags()
    host.bump({})
    pg.wait_for_function("() => window.__fly.copies.length === 2", timeout=WAIT_MS)
    button = pg.locator(".arena-gate__btn").bounding_box()
    c = _fly(pg)["copies"][0]
    assert abs(c["centre"][0] - _centre(button)[0]) <= 3 and abs(c["centre"][1] - _centre(button)[1]) <= 3       # the gate's button, not the press
    assert abs(c["centre"][0] - _centre(press)[0]) > 20 or abs(c["centre"][1] - _centre(press)[1]) > 20
    _over(pg)


def test_a_gate_under_the_drawer_is_not_a_place_to_travel_from_but_the_flag_is_still_raised(raising):
    pg, host = raising
    pg.get_by_role("button", name="About this party").click()                                             # the drawer lies over the gate's button
    _drawer(pg).wait_for(timeout=WAIT_MS)
    button = pg.locator(".arena-gate__btn").bounding_box()
    assert pg.evaluate("([x, y]) => document.elementFromPoint(x, y).closest('.arena-gate__btn') === null", list(_centre(button)))
    pg.evaluate(RECORD)
    host.raise_flags()
    host.bump({})
    pg.locator(".arena-flagline").wait_for(timeout=WAIT_MS)
    pg.wait_for_function("() => window.__fly.starts.some(([n]) => n === 'arena-raise') && window.__fly.starts.some(([n]) => n === 'arena-lit')", timeout=WAIT_MS)
    _over(pg)
    assert _fly(pg)["copies"] == [] and not [s for s in _starts(pg) if s.startswith("arena-fly")]        # nothing travelled
    assert _elements(pg) == [["meadow"], ["ice"]]                                                       # the row is drawn


def test_with_no_gate_on_screen_nothing_travels_and_the_flag_is_still_raised(raising):
    pg, host = raising
    host.gate_doc.update(same=True)                                                                       # one branch: no gate to draw
    host.bump({})
    pg.wait_for_function("() => !document.querySelector('.arena-gate__btn')", timeout=WAIT_MS)
    pg.evaluate(RECORD)
    host.raise_flags()
    host.bump({})
    pg.locator(".arena-flagline").wait_for(timeout=WAIT_MS)
    assert pg.locator(".arena-flagline__el").evaluate_all("els => els.map((e) => getComputedStyle(e).visibility)") == ["visible", "visible"]     # the row is there at once
    pg.wait_for_function("() => window.__fly.starts.some(([n]) => n === 'arena-raise') && window.__fly.starts.some(([n]) => n === 'arena-lit')", timeout=WAIT_MS)
    _over(pg)
    assert _fly(pg)["copies"] == [] and not [s for s in _starts(pg) if s.startswith("arena-fly")]
    assert _elements(pg) == [["meadow"], ["ice"]]


def test_closing_the_line_while_they_travel_takes_the_copies_away(raising):
    pg, host = raising
    pg.locator(".arena-gate__btn").click()
    view = _drawer(pg).locator(".arena-gateview")
    view.wait_for(timeout=WAIT_MS)
    pg.evaluate(RECORD)
    pg.evaluate("window.__fly.close = true")                                                              # the line is closed in the frame the first copy is drawn
    view.get_by_role("button", name="Merge dev into main").click()
    pg.wait_for_function("() => window.__fly.copies.length >= 1", timeout=WAIT_MS)
    pg.locator(".arena-flagline").wait_for(state="detached", timeout=WAIT_MS)
    _over(pg)
    assert pg.locator(".arena-flagfly").count() == 0


# -- none of it ---------------------------------------------------------------------------------------------------------------------------

def test_under_reduced_motion_no_copy_no_animation_and_the_row_is_drawn(gui):
    host = RaiseHost()
    pg, errors = _scene(gui, host, reduced_motion="reduce")
    _merge(pg, host)
    pg.locator(".arena-flagline").wait_for(timeout=WAIT_MS)
    pg.wait_for_timeout(700)
    assert _fly(pg)["copies"] == [] and _starts(pg) == [] and pg.evaluate("document.getAnimations().length") == 0
    assert pg.locator(".arena-flagfly, .is-raising, .is-coming").count() == 0
    assert _elements(pg) == [["meadow"], ["ice"]]
    assert pg.locator(".arena-flagline__el").evaluate_all("els => els.map((e) => getComputedStyle(e).visibility)") == ["visible", "visible"]
    pg.close()
    assert not errors, "\n".join(errors)


def test_on_a_hidden_page_nothing_plays_and_the_row_is_drawn(gui):
    host = RaiseHost()
    pg, errors = _scene(gui, host)
    pg.evaluate("Object.defineProperty(document, 'hidden', {configurable: true, get: () => true})")
    _merge(pg, host)
    pg.locator(".arena-flagline").wait_for(timeout=WAIT_MS)
    pg.wait_for_timeout(700)
    assert _fly(pg)["copies"] == [] and _starts(pg) == []
    assert pg.locator(".arena-flagfly, .is-raising, .is-coming").count() == 0 and _elements(pg) == [["meadow"], ["ice"]]
    pg.close()
    assert not errors, "\n".join(errors)
