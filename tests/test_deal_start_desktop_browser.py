"""Spec 57, the desktop (docs/specs/57-deal-on-start.md §1–§3; Tests → B): Chromium at 1 440 × 900 against the one window's stub host (tests/test_arena_desktop_browser.py) whose plan
(*Recovery codes*) starts when the hand's *Start the work* is pressed. A plan started by a press in the hand deals its new cards from the stop's box to their places (`is-dealt`, the
travel in inline variables, at most six; the rest rise); a start nobody pressed in the hand, a refused one, one that comes after 6 s and one under reduced motion deal nothing."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_arena_desktop_browser import HEAD, ArenaHost, member, pip  # noqa: E402,F401
from tests.test_shell_browser import _sent, _stop  # noqa: E402

pytestmark = pytest.mark.browser

ARTIST = {"kind": "art", "words": "pixel art", "agent": "artist", "name": "Artist", "band": "build", "free": True}

RECORD ="""() => {
  window.__seen = {dealt: [], rose: []};
  const note = () => {
    document.querySelectorAll('.arena-task.is-dealt').forEach((e) => {
      if (window.__seen.dealt.some((x) => x.key === e.dataset.key)) return;
      const r = e.getBoundingClientRect(), s = e.style;
      window.__seen.dealt.push({key: e.dataset.key, dx: s.getPropertyValue('--dx'), dy: s.getPropertyValue('--dy'), s: s.getPropertyValue('--s'), delay: s.getPropertyValue('--delay'),
        agent: e.closest('.arena-stack')?.dataset.agent, col: [...document.querySelectorAll('.arena-stack')].indexOf(e.closest('.arena-stack')),
        anim: getComputedStyle(e).animationName, centre: [r.left + r.width / 2, r.top + r.height / 2], width: r.width});
    });
    document.querySelectorAll('.arena-task.is-drawn').forEach((e) => { if (!window.__seen.rose.includes(e.dataset.key)) window.__seen.rose.push(e.dataset.key); });
  };
  new MutationObserver(note).observe(document.body, {subtree: true, childList: true, attributes: true, attributeFilter: ['class', 'style']});
}"""


class DealHost(ArenaHost):
    """The plan of *Recovery codes* starts when it is told to: its goal is at work then, its tasks are on the field, its stop is gone."""

    def __init__(self, many=False):
        super().__init__()
        self.started, self.refuse, self.hold, self.missing = False, False, False, False
        if many:                                        # eight stacks: three rows of Backend's and of Screens', one each of the other two
            self.node_of("recovery")["tasks"] = [pip(f"m{i}", f"Step {i}", "ready" if wave == 1 else "waiting", wave=wave, by=by)
                                                 for i, (by, wave) in enumerate([("backend", 1), ("backend", 2), ("backend", 3), ("screens", 1), ("screens", 2), ("screens", 3),
                                                                                 ("reviewer", 1), ("words", 1)])]

    def needs_you(self):
        rows = [r for r in super().needs_you() if not (self.started and r["idea"] == "recovery")]
        return [r | {"missing": [ARTIST]} if self.missing and r["kind"] == "plan" else r for r in rows]

    def page(self, slug):
        """The plan of *Recovery codes* as the drawer's plan screen has it: waiting, with its estimate."""
        got = super().page(slug)
        if slug == "recovery" and "error" not in got:
            got["state"] = "working" if self.started else "plan"
            got["plan"] = {**self.plan, "estimate": {"tasks": 3, "usd_low": 1.0, "usd_high": 2.0}, "missing": []}
        return got

    def begin(self):
        self.started = True
        self.node_of("recovery").update(stage="implementation", state="working", needs_you="")
        self.ideas["recovery"].update(state="working")
        self.bump({})

    def handle(self, name, a):
        if name in ("ideas.start", "ideas.start_now") and a.get("slug") == "recovery":
            self.log.append((name, a))
            if self.refuse:
                return {"error": "The plan cannot start now."}
            if a.get("join"):                           # the member joins first: its column is in place when its cards land
                self.party["passkey"].append(member("artist", "Artist", HEAD, "build", "next"))
                self.node_of("recovery")["tasks"].append(pip("a1", "Draw the code sheet", "ready", by="artist"))
            if not self.hold:
                self.begin()
            return {"ok": True}
        return super().handle(name, a)


def _scene(gui, host, **page):
    server, browser = gui
    pg = browser.new_page(viewport={"width": 1440, "height": 900}, **page)
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.goto(server.url)
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    pg.wait_for_selector(".arena-hc[data-kind=plan]", timeout=WAIT_MS)
    return pg, errors


@pytest.fixture
def dealing(gui):
    host = DealHost()
    pg, errors = _scene(gui, host)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


@pytest.fixture
def dealing_many(gui):
    host = DealHost(many=True)
    pg, errors = _scene(gui, host)
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _press_start(pg, host):
    stop = _stop(pg, "plan")
    pg.evaluate(RECORD)
    box = stop.bounding_box()                                                                        # the stop, raised, as it is at the press
    stop.get_by_role("button", name="Start the work").click()
    assert _sent(pg, host, ("ideas.start", {"slug": "recovery", "via": "hand"}))
    return box


def _seen(pg):
    return pg.evaluate("window.__seen")


def _centre(b):
    return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2


def _ms(x):
    return int(x["delay"][:-2])


# -- the deal (§1–§3) ---------------------------------------------------------------------------------------------------------------

def test_a_plan_started_in_the_hand_deals_its_cards_from_the_stop_to_their_columns(dealing):
    pg, host = dealing
    box = _press_start(pg, host)
    pg.wait_for_function("() => window.__seen.dealt.length === 3", timeout=WAIT_MS)                   # r1 Backend, r2 Screens, r3 Reviewer
    seen = _seen(pg)
    assert sorted(x["key"] for x in seen["dealt"]) == ["recovery/r1", "recovery/r2", "recovery/r3"] and seen["rose"] == []     # dealt, none rose
    sx, sy = _centre(box)
    for x in seen["dealt"]:
        assert x["anim"] == "arena-deal" and x["agent"] in ("backend", "screens", "reviewer")
        assert abs(x["centre"][0] - sx) <= 3 and abs(x["centre"][1] - sy) <= 3                         # it starts at the stop's centre …
        assert abs(x["width"] - box["width"]) <= 3                                                     # … at the stop's width
    assert sorted(_ms(x) for x in seen["dealt"]) == [0, 35, 70]                                         # 35 ms apart
    assert [x["col"] for x in sorted(seen["dealt"], key=_ms)] == sorted(x["col"] for x in seen["dealt"])        # the left column first
    pg.wait_for_function("() => !document.querySelector('.is-dealt, .is-drawn')", timeout=WAIT_MS)       # then they are cards like any
    for x in seen["dealt"]:
        card = pg.locator(f".arena-task[data-key='{x['key']}']")
        end = _centre(card.bounding_box())
        assert abs(end[0] + float(x["dx"][:-2]) - sx) <= 3 and abs(end[1] + float(x["dy"][:-2]) - sy) <= 3        # its end is its place: the travel leads back to the stop
        assert pg.locator(f".arena-stack[data-agent={x['agent']}]").locator(f".arena-task[data-key='{x['key']}']").count() == 1    # in its member's column


def test_at_most_six_travel_and_the_rest_rise_after_the_sixth_starts(dealing_many):
    pg, host = dealing_many
    _press_start(pg, host)
    pg.wait_for_function("() => window.__seen.dealt.length + window.__seen.rose.length === 8", timeout=WAIT_MS)
    seen = _seen(pg)
    assert len(seen["dealt"]) == 6 and len(seen["rose"]) == 2
    assert sorted(_ms(x) for x in seen["dealt"]) == [0, 35, 70, 105, 140, 175]
    assert [x["col"] for x in sorted(seen["dealt"], key=_ms)] == sorted(x["col"] for x in seen["dealt"])        # the field's order
    assert all(k.startswith("recovery/") for k in seen["rose"])
    pg.wait_for_function("() => !document.querySelector('.is-dealt, .is-drawn')", timeout=WAIT_MS)
    assert pg.locator(".arena-task[data-idea=recovery]").count() == 8                                    # all eight are there


def test_the_cards_travel_over_the_field_and_nothing_dims(dealing):
    pg, host = dealing
    _press_start(pg, host)
    pg.wait_for_function("() => window.__seen.dealt.length === 3", timeout=WAIT_MS)
    assert pg.locator(".arena-spread").count() == 0                                                       # no scrim: nothing dims
    assert pg.locator(".arena-task.is-dealt").first.evaluate("e => getComputedStyle(e).zIndex") == "60"      # over everything of the field
    pg.wait_for_function("() => !document.querySelector('.is-dealt')", timeout=WAIT_MS)
    assert pg.locator(".arena-stack.is-dealing").count() == 0                                             # the columns clip again


def test_add_and_start_deals_into_the_new_members_column_too(gui):
    host = DealHost()
    host.missing = True
    pg, errors = _scene(gui, host)
    stop = _stop(pg, "plan")
    pg.evaluate(RECORD)
    stop.get_by_role("button", name="Add and start").click()
    assert _sent(pg, host, ("ideas.start", {"slug": "recovery", "join": {"add": "artist"}, "via": "hand"}))
    pg.wait_for_function("() => window.__seen.dealt.length === 4", timeout=WAIT_MS)                    # the three of the party and the new member's
    seen = _seen(pg)
    assert "artist" in [x["agent"] for x in seen["dealt"]] and seen["rose"] == []
    pg.wait_for_function("() => !document.querySelector('.is-dealt')", timeout=WAIT_MS)
    assert pg.locator(".arena-stack[data-agent=artist] .arena-task[data-key='recovery/a1']").count() == 1
    pg.close()
    assert not errors, "\n".join(errors)


# -- what does not deal ---------------------------------------------------------------------------------------------------------------

def test_a_start_nobody_pressed_in_the_hand_only_rises(dealing):
    pg, host = dealing
    pg.evaluate(RECORD)
    host.begin()                                                                                          # an autostart: no press in the hand
    pg.wait_for_function("() => window.__seen.rose.length === 3", timeout=WAIT_MS)
    assert _seen(pg)["dealt"] == [] and pg.locator(".is-dealt").count() == 0


def test_a_start_from_the_drawers_plan_screen_only_rises(dealing):
    pg, host = dealing
    _stop(pg, "plan").get_by_role("button", name="Open the plan").click()
    start = pg.get_by_role("button").filter(has_text="Start ·")
    start.first.wait_for(timeout=WAIT_MS)
    pg.evaluate(RECORD)
    start.first.click()
    pg.wait_for_function("() => window.__seen.rose.length === 3", timeout=WAIT_MS)
    assert _seen(pg)["dealt"] == []


def test_a_refused_start_keeps_nothing_waiting(dealing):
    pg, host = dealing
    host.refuse = True
    pg.evaluate(RECORD)
    _stop(pg, "plan").get_by_role("button", name="Start the work").click()
    assert _sent(pg, host, ("ideas.start", {"slug": "recovery", "via": "hand"}))
    pg.get_by_text("The plan cannot start now.").first.wait_for(timeout=WAIT_MS)
    host.refuse = False
    host.begin()                                                                                          # it starts later, by itself
    pg.wait_for_function("() => window.__seen.rose.length === 3", timeout=WAIT_MS)
    assert _seen(pg)["dealt"] == []                                                                       # nothing waited: the cards rise


def test_after_six_seconds_a_late_render_rises(dealing):
    pg, host = dealing
    host.hold = True                                                                                      # the call is answered, the Board does not change yet
    _press_start(pg, host)
    pg.wait_for_timeout(6300)
    host.begin()
    pg.wait_for_function("() => window.__seen.rose.length === 3", timeout=WAIT_MS)
    assert _seen(pg)["dealt"] == []


def test_under_reduced_motion_nothing_is_dealt_and_nothing_rises(gui):
    host = DealHost()
    pg, errors = _scene(gui, host, reduced_motion="reduce")
    _press_start(pg, host)
    pg.locator(".arena-task[data-key='recovery/r1']").wait_for(timeout=WAIT_MS)
    pg.locator(".arena-task[data-key='recovery/r3']").wait_for(timeout=WAIT_MS)
    seen = _seen(pg)
    assert seen["dealt"] == [] and seen["rose"] == [] and pg.locator(".is-dealt, .is-drawn").count() == 0
    pg.close()
    assert not errors, "\n".join(errors)
