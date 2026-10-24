"""Spec 70 part B on the desktop (docs/specs/70-orkmaster-and-the-project.md §2–§4, §5 "B"; decisions §85): Chromium at 1 440 × 900 against the route test's stub host (the Passkey party, Ideation, Website and a
Release party) with the host's `project` block (the Orkmaster and its deal), `ideas.party_for` and `ideas.shown` as spec §1 gives them. The Orkmaster's head in the project line and its press (the project's level: the
parties as columns, their goals as decks in groups, Flags folded, sticky heads, a column's press opens the party, a deck's press opens the goal, a sent goal's links on hover); the Orkmaster's deal (New party) and New
party's tiles in its order with the why; New goal on the level with its party suggested; `ideas.shown` to and from `@project`; a host without `project` keeps today's face. Screenshots to the directory
ORKCRAFT_SHOTS_DIR names when it is set."""
from __future__ import annotations

import copy

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.test_map_desktop_browser import node  # noqa: E402
from tests.test_route_desktop_browser import RELEASE_TYPE, RouteHost, shot  # noqa: E402
from tests.test_shell_browser import _calls, _new_party, _open, _parties, _show_goal  # noqa: E402

pytestmark = pytest.mark.browser

SHOP = "/work/shop"
ORK = {"id": "orkmaster", "name": "Orkmaster", "race": "peon", "tier": "elder"}
ARTIST = {"kind": "art", "words": "pixel art", "agent": "artist", "name": "Artist", "band": "build", "free": True, "out": []}
FIX = {"id": "fix", "name": "Fix a bug", "sign": "bug", "line": "Something is broken: find it, fix it, prove it", "lens": "code", "refs": False, "used": 2, "missing": [], "asks": []}
LOGO = {"id": "logo", "name": "New logo", "sign": "logo", "line": "A mark for the product, in sizes", "lens": "text", "refs": False, "used": 0, "missing": [], "asks": []}
LIBRARY = ["game", "mobile-app", "website", "ideation", "release", "engineering", "design", "data", "marketing", "product", "mixed"]
LACKING = [{"id": "release", "why": "flags_wait", "n": 3}, {"id": "ideation", "why": "no_pitches", "n": 0},
           *[{"id": i, "why": "", "n": 0} for i in LIBRARY if i not in ("release", "ideation")]]
HAVING = [*[{"id": i, "why": "", "n": 0} for i in LIBRARY if i not in ("release", "ideation")], {"id": "release", "why": "have", "n": 0}, {"id": "ideation", "why": "have", "n": 0}]


class ProjectHost(RouteHost):
    """The route test's world with four parties (Passkey, Ideation, Website, Release) and `ideas.map`'s `project` (`project=False`: a host from before spec 70). Passkey offers *Fix a bug* and *New logo* (and misses
    an Artist for it), Website offers *New logo* whole; `ideas.party_for` ranks them as realm/orkmaster.py does."""

    def __init__(self, project=True):
        super().__init__()
        self.project, self.deal = project, copy.deepcopy(HAVING)
        for slug in ("pricing", "weekly"):
            self.goals.pop(slug)
        self.nodes = [n for n in self.nodes if n["goal"] not in ("pricing", "weekly")]
        self.ideas.pop("prices", None)
        self.add(node("landing", "website", "Landing copy", "ready", 1), "dust")
        self.add(node("hero", "website", "Hero picture", "done", 1, stage="done", progress={"done": 1, "total": 1}, folded=True), "lava")

    def snapshot(self):
        snap = super().snapshot()
        snap["state"]["projects"] = {"current": SHOP, "recent": [], "open": [{"path": SHOP, "name": "shop", "working": 0, "needs_you": 0, "review": 0}]}      # the project line has its switcher
        return snap

    def map_doc(self):
        doc = super().map_doc()
        if not self.project:
            return doc
        types = {"passkey": [FIX, LOGO | {"missing": [ARTIST]}], "website": [LOGO], "release": [RELEASE_TYPE]}
        for g in doc["goals"]:
            g["types"] = copy.deepcopy(types.get(g["slug"], []))
        doc["project"] = {"orkmaster": dict(ORK), "deal": copy.deepcopy(self.deal)}
        return doc

    def handle(self, name, a):
        if name == "ideas.party_for":
            self.log.append((name, a))
            rows = [("passkey", "Passkey"), ("website", "Website"), ("release", "Release"), ("ideas", "Ideation")]
            if "type" not in a:
                parties = [{"party": s, "name": n, "fits": "pitch" if s == "ideas" else "", "missing": []} for s, n in rows]
                return {"parties": parties, "suggested": "passkey"}
            fit = {"passkey": ("missing", [{"agent": "artist", "name": "Artist"}]), "website": ("whole", [])}
            parties = [{"party": s, "name": n, "fits": fit.get(s, ("none", []))[0], "missing": fit.get(s, ("none", []))[1]} for s, n in rows]
            order = {"whole": 0, "missing": 1, "none": 2}
            parties.sort(key=lambda p: order[p["fits"]])
            return {"parties": parties, "suggested": parties[0]["party"]}
        return super().handle(name, a)


@pytest.fixture
def level(gui):
    pg, host, errors = _open(gui, host=ProjectHost(), ready=".arena[data-goal=passkey]")
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _project(pg):
    """The Orkmaster pressed: the project's level is on the field."""
    pg.get_by_role("button", name="The project").click()
    pg.locator(".arena-project").wait_for(timeout=WAIT_MS)
    pg.locator(".arena-pcol").first.wait_for(timeout=WAIT_MS)


def _col(pg, slug):
    return pg.locator(f'.arena-pcol[data-goal="{slug}"]')


def _groups(pg, slug):
    return [h.text_content().strip() for h in _col(pg, slug).locator(".arena-pgroup > .arena-sec").all()]


# -- the Orkmaster in the project's line ---------------------------------------------------------------------------------------------------------------------

def test_the_orkmasters_head_stands_at_the_left_of_the_project_line_and_its_press_shows_the_project_with_every_heading_closed(level):
    pg, host = level
    ork = pg.get_by_role("button", name="The project")
    assert ork.count() == 1 and ork.get_attribute("aria-pressed") == "false" and ork.get_attribute("title") == "The project"
    head = ork.locator(".ork-race__head")
    assert "peon-elder" in head.get_attribute("src") and head.bounding_box()["width"] == 24 and head.bounding_box()["height"] == 22      # orkUI's Head, an ork, the elder tier, 24 × 22
    line = pg.locator(".arena-left__proj")
    assert ork.bounding_box()["x"] < line.locator(".shell-proj").bounding_box()["x"]                                # at the line's left, then the switcher
    assert pg.locator(".arena-left__proj.is-open").count() == 0
    ork.click()
    pg.locator(".arena-project").wait_for(timeout=WAIT_MS)
    assert ork.get_attribute("aria-pressed") == "true" and pg.locator(".arena-left__proj.is-open").count() == 1      # the line marked as an open heading is
    assert pg.locator(".arena-phead[aria-expanded=true]").count() == 0 and pg.locator(".arena-phead[aria-current=true]").count() == 0
    assert pg.locator(".arena-phead").count() == 4 and pg.locator(".arena-pbody").count() == 0                       # every heading closed, no party's body
    assert pg.locator(".arena-pjtop h2").text_content() == "The project"
    _parties(pg).locator('.arena-phead[data-goal="website"]').click()                                                 # a heading shows its party again
    pg.locator('.arena[data-goal="website"]').wait_for(timeout=WAIT_MS)
    assert ork.get_attribute("aria-pressed") == "false" and pg.locator(".arena-project").count() == 0


def test_the_project_is_kept_per_device_as_a_party_is(level):
    pg, host = level
    _project(pg)
    pg.reload()
    pg.locator(".arena-project").wait_for(timeout=WAIT_MS)
    assert pg.get_by_role("button", name="The project").get_attribute("aria-pressed") == "true"


def test_a_host_without_project_keeps_todays_face_and_todays_tiles(gui):
    pg, host, errors = _open(gui, host=ProjectHost(project=False), ready=".arena[data-goal=passkey]")
    assert pg.get_by_role("button", name="The project").count() == 0 and pg.locator(".arena-ork").count() == 0
    assert not pg.locator(".arena-left__proj").get_attribute("class").count("has-ork")
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    assert [t.get_attribute("data-craft") for t in dlg.locator(".shell-craft-tile").all()][:5] == ["game", "mobile-app", "website", "ideation", "release"]      # the library's order
    assert dlg.locator(".shell-craft-tile__why").count() == 0
    pg.close()
    assert not errors, "\n".join(errors)


# -- the project's level ----------------------------------------------------------------------------------------------------------------------------------------

def test_the_level_is_a_column_for_each_party_with_its_goals_as_decks_in_groups_and_its_flags_folded(level):
    pg, host = level
    _project(pg)
    cols = pg.locator(".arena-pcol")
    assert [c.get_attribute("data-goal") for c in cols.all()] == ["passkey", "ideas", "website", "release"]            # the Board's order, no Operations
    head = _col(pg, "passkey").locator(".arena-pcol__head")
    assert head.locator(".ork-race__head").count() == 1 and head.locator(".arena-pcol__name").inner_text() == "Passkey" and "/" in head.locator(".arena-phead__count").inner_text()
    assert head.get_attribute("title") == "Open Passkey"
    assert _groups(pg, "passkey") == ["Planning", "At work"]
    decks = _col(pg, "passkey").locator(".arena-deck")
    assert decks.count() == 9                                                                                           # Flags (4) are folded
    one = _col(pg, "passkey").locator('.arena-deck[data-slug="register"]')
    box = one.bounding_box()
    assert box["width"] <= 132.5 and box["height"] <= 72.5
    assert one.locator(".ork-elem").count() == 1 and one.locator(".arena-deck__title").inner_text() == "WebAuthn register"
    assert one.locator(".arena-deck__line").inner_text().strip() == "0/6 in dev · implementation"                        # as the party's goal row says it
    assert _col(pg, "passkey").locator('.arena-pgroup[data-group="work"] .arena-deck').count() == 3
    fold = _col(pg, "passkey").get_by_role("button", name="Flags (4)")
    assert fold.get_attribute("aria-expanded") == "false"
    fold.click()
    assert fold.get_attribute("aria-expanded") == "true" and _col(pg, "passkey").locator('.arena-pgroup[data-group="flags"] .arena-deck').count() == 4
    assert _groups(pg, "website") == ["Planning", "Waits for main"] and _col(pg, "website").locator(".arena-deck").count() == 2
    assert _col(pg, "ideas").locator(".arena-deck").count() == 5 and _col(pg, "release").get_by_role("button", name="Flags (2)").count() == 1
    fold.click()
    assert _col(pg, "passkey").locator('.arena-pgroup[data-group="flags"] .arena-deck').count() == 0
    assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")


def test_an_empty_party_says_nothing_in_it_yet(level):
    pg, host = level
    host.nodes = [n for n in host.nodes if n["goal"] != "website"]
    host.bump({})
    _project(pg)
    assert _col(pg, "website").locator(".arena-pcol__empty").inner_text() == "Nothing in Website yet" and _col(pg, "website").locator(".arena-deck").count() == 0


def test_a_columns_press_opens_that_party_and_a_decks_press_opens_its_goal(level):
    pg, host = level
    _project(pg)
    _col(pg, "website").locator(".arena-pcol__head").click()
    pg.locator('.arena[data-goal="website"]').wait_for(timeout=WAIT_MS)
    assert pg.locator('.arena-phead[data-goal="website"][aria-current=true]').count() == 1
    _project(pg)
    _col(pg, "passkey").locator('.arena-deck[data-slug="signin"]').click()
    pg.locator(".board-ideaview").wait_for(timeout=WAIT_MS)
    assert any(a.get("slug") == "signin" for a in _calls(pg, host, "ideas.page"))
    assert pg.locator(".arena-project").count() == 1                                                                    # the level stays under the drawer


def test_the_heads_stay_while_the_columns_scroll_down_and_sideways(level):
    pg, host = level
    _project(pg)
    pg.set_viewport_size({"width": 800, "height": 900})                                                                 # narrower than the four columns: they scroll sideways
    body = pg.locator(".arena-project__body")
    assert body.evaluate("e => e.scrollWidth > e.clientWidth && getComputedStyle(e).overflowX !== 'hidden'")
    body.evaluate("e => { e.scrollLeft = 120; e.scrollTop = 300; }")
    pg.wait_for_timeout(100)
    top = body.bounding_box()["y"]
    heads = [h.bounding_box()["y"] for h in pg.locator(".arena-pcol__head").all()]
    assert all(abs(y - top) < 2 for y in heads)                                                                         # every head sticks to the top
    assert body.evaluate("e => e.scrollLeft") > 0


def test_hovering_a_sent_goals_deck_draws_its_links_to_its_pitch_and_its_release_and_nothing_at_rest(level):
    pg, host = level
    _project(pg)
    _col(pg, "release").get_by_role("button", name="Flags (2)").click()
    assert pg.locator(".arena-arrow").count() == 0                                                                      # nothing at rest
    pg.locator('.arena-deck[data-slug="register"]').hover()
    pg.locator('.arena-arrow[data-edge="dark>register"]').wait_for(timeout=WAIT_MS)                                     # the pitch it came from, in Ideation's column
    pg.locator('.arena-arrow[data-edge="register>r14"]').wait_for(timeout=WAIT_MS)                                      # the release it went into
    assert pg.locator(".arena-arrow").count() == 2
    shot(pg, "desk-project.png")
    pg.locator(".arena-pjtop").hover()
    pg.wait_for_function("() => !document.querySelector('.arena-arrow')", timeout=WAIT_MS)
    pg.locator('.arena-deck[data-slug="dark"]').focus()                                                                 # the keyboard's focus draws them too
    pg.locator('.arena-arrow[data-edge="dark>register"]').wait_for(timeout=WAIT_MS)


# -- the Orkmaster's deal: New party -------------------------------------------------------------------------------------------------------------------------

def _lacking(pg, host):
    host.deal = copy.deepcopy(LACKING)
    host.bump({})
    pg.wait_for_function("() => document.querySelector('.shell-main, .arena')", timeout=WAIT_MS)


def test_the_orkmaster_deals_release_first_when_flags_wait_then_ideation_and_a_press_opens_new_party_with_it_picked(level):
    pg, host = level
    _lacking(pg, host)
    _project(pg)
    pile = pg.locator(".arena-pjnew .arena-new__pile")
    assert pile.get_attribute("aria-label").startswith("New party") and pg.locator(".arena-pjnew").bounding_box()["y"] < pg.locator(".arena-project__body").bounding_box()["y"]      # under the field's head
    pile.click()
    deal = pg.get_by_role("dialog", name="New party")
    deal.locator(".arena-type--party").first.wait_for(timeout=WAIT_MS)
    cards = deal.locator(".arena-type--party")
    assert [c.get_attribute("data-preset") for c in cards.all()] == [e["id"] for e in LACKING]                          # the host's order
    first, second, plain = cards.nth(0), cards.nth(1), cards.nth(2)
    assert first.locator(".arena-type__why").inner_text() == "3 flags wait and no party releases them"
    assert second.locator(".arena-type__why").inner_text() == "No party judges small ideas yet" and plain.locator(".arena-type__why").count() == 0
    assert first.locator(".arena-type__name").inner_text() == "Release" and first.locator(".arena-type__heads .ork-race__head").count() >= 1 and first.locator(".arena-type__line").inner_text().strip()
    assert first.locator(".ork-race__head").first.get_attribute("src").count("skeleton") == 1                           # its leader's head
    pg.wait_for_timeout(900)                                                                                            # the deal is played
    shot(pg, "desk-deal.png")
    first.click()
    dlg = pg.get_by_role("dialog", name="New party")
    dlg.locator(".shell-craft-tile").first.wait_for(timeout=WAIT_MS)
    assert dlg.locator('.shell-craft-tile[data-craft="release"]').get_attribute("aria-pressed") == "true"
    assert dlg.locator(".arena-releasesfrom").count() == 1                                                              # Release picked: its Releases from is there


def test_a_party_the_project_has_is_dealt_last_and_says_you_have_one(level):
    pg, host = level
    _project(pg)
    pg.locator(".arena-pjnew .arena-new__pile").click()
    cards = pg.get_by_role("dialog", name="New party").locator(".arena-type--party")
    cards.first.wait_for(timeout=WAIT_MS)
    assert [c.get_attribute("data-preset") for c in cards.all()][-2:] == ["release", "ideation"]
    assert cards.last.locator(".arena-type__why").inner_text() == "You have one" and "is-have" in cards.last.get_attribute("class")
    pg.keyboard.press("Escape")
    pg.get_by_role("dialog", name="New party").wait_for(state="detached", timeout=WAIT_MS)


def test_new_partys_tiles_follow_the_deal_inside_each_group_with_the_why_under_the_line(level):
    pg, host = level
    _lacking(pg, host)
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    mixed = dlg.locator('.shell-library-group[aria-label="Mixed"] .shell-craft-tile')
    assert [t.get_attribute("data-craft") for t in mixed.all()] == ["release", "ideation", "game", "mobile-app", "website"]
    crafts = dlg.locator('.shell-library-group[aria-label="One craft"] .shell-craft-tile')
    assert [t.get_attribute("data-craft") for t in crafts.all()] == ["engineering", "design", "data", "marketing", "product"]      # the groups keep their headings
    why = dlg.locator('.shell-craft-tile[data-craft="release"] .shell-craft-tile__why')
    assert why.inner_text() == "3 flags wait and no party releases them"
    assert dlg.locator('.shell-craft-tile[data-craft="ideation"] .shell-craft-tile__why').inner_text() == "No party judges small ideas yet"
    assert dlg.locator('.shell-craft-tile[data-craft="game"] .shell-craft-tile__why').count() == 0
    assert dlg.locator('.shell-craft-tile[data-craft="release"] .shell-craft-tile__text small').all_inner_texts()[-1] == "3 flags wait and no party releases them"      # under its line
    pg.get_by_role("button", name="Cancel").click()
    host.deal = copy.deepcopy(HAVING)
    host.bump({})
    _new_party(pg)
    dlg = pg.get_by_role("dialog", name="New party")
    assert [t.get_attribute("data-craft") for t in dlg.locator('.shell-library-group[aria-label="Mixed"] .shell-craft-tile').all()] == ["game", "mobile-app", "website", "release", "ideation"]     # those it has, last
    assert dlg.locator('.shell-craft-tile[data-craft="ideation"] .shell-craft-tile__why').inner_text() == "You have one"


def test_the_columns_new_party_line_stays_and_opens_new_party_as_today(level):
    pg, host = level
    _project(pg)
    _new_party(pg)
    assert pg.get_by_role("dialog", name="New party").locator('.shell-craft-tile[aria-pressed="true"]').get_attribute("data-craft") == "engineering"


# -- New goal on the level: its party from the Orkmaster -------------------------------------------------------------------------------------------------

def _new_goal(pg):
    pg.locator(".arena-pjgoal .arena-new__pile").click()
    deal = pg.get_by_role("dialog", name="New goal for the project")
    deal.locator(".arena-type").first.wait_for(timeout=WAIT_MS)
    return deal


def test_new_goal_on_the_level_deals_every_type_of_the_parties_and_suggests_the_party_with_an_artist_for_a_logo(level):
    pg, host = level
    _project(pg)
    deal = _new_goal(pg)
    assert [c.get_attribute("data-type") for c in deal.locator(".arena-type").all()] == ["", "fix", "logo", "release"]  # Your own goal first, then the union
    deal.locator('.arena-type[data-type="logo"]').click()
    form = pg.get_by_role("dialog", name="New goal")
    form.locator('.arena-typed[data-type="logo"]').wait_for(timeout=WAIT_MS)
    its = form.get_by_role("group", name="Its party")
    its.locator(".arena-itsparty__chip").first.wait_for(timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.party_for")[-1] == {"type": "logo"}
    says = its.locator(".arena-itsparty__says")
    assert says.inner_text().strip() == "Orkmaster suggests Website · takes it whole"
    chips = its.locator(".arena-itsparty__chip")
    assert [c.get_attribute("data-party") for c in chips.all()] == ["website", "passkey", "release", "ideas"]           # Website (whole) first
    assert chips.nth(0).get_attribute("aria-checked") == "true" and chips.nth(1).locator("small").inner_text() == "needs Artist"
    assert chips.nth(2).locator("small").inner_text() == "no one there does it"
    form.get_by_label("Its title").fill("A new mark")
    shot(pg, "desk-goal-party.png")
    chips.nth(1).click()                                                                                                # another chip: Passkey, which misses an Artist
    assert chips.nth(1).get_attribute("aria-checked") == "true" and chips.nth(0).get_attribute("aria-checked") == "false"
    assert says.inner_text().strip() == "Orkmaster suggests Website · takes it whole"
    join = form.locator('.arena-join[data-agent="artist"]')
    join.wait_for(timeout=WAIT_MS)                                                                                       # the join line of the party picked
    form.get_by_role("button", name="Add the goal").click()
    sent = _calls(pg, host, "ideas.add")[-1]
    assert sent["track"] == "passkey" and sent["type"] == "logo" and sent["join"] == {"add": "artist"}
    form.wait_for(state="detached", timeout=WAIT_MS)


def test_the_suggested_party_is_picked_and_added_to_and_no_party_is_asked_for_before_the_answer(level):
    pg, host = level
    _project(pg)
    _new_goal(pg).locator('.arena-type[data-type="logo"]').click()
    form = pg.get_by_role("dialog", name="New goal")
    form.get_by_label("Its title").fill("A new mark")
    form.locator(".arena-itsparty__chip").first.wait_for(timeout=WAIT_MS)
    form.get_by_role("button", name="Add the goal").click()
    assert _calls(pg, host, "ideas.add")[-1]["track"] == "website"


def test_your_own_goal_on_the_level_says_any_party_with_ideation_last_and_a_pitch_goes_to_ideation(level):
    pg, host = level
    _project(pg)
    _new_goal(pg).locator('.arena-type[data-type=""]').click()
    form = pg.get_by_role("dialog", name="New goal")
    its = form.get_by_role("group", name="Its party")
    its.locator(".arena-itsparty__chip").first.wait_for(timeout=WAIT_MS)
    assert "type" not in _calls(pg, host, "ideas.party_for")[-1]
    assert its.locator(".arena-itsparty__says").inner_text().strip() == "Any party"
    chips = its.locator(".arena-itsparty__chip")
    assert [c.get_attribute("data-party") for c in chips.all()] == ["passkey", "website", "release", "ideas"] and chips.last.locator("small").inner_text() == "a pitch"
    form.get_by_label("Your goal").fill("Offline mode")
    form.get_by_role("button", name="Add the goal").click()
    sent = _calls(pg, host, "ideas.add")[-1]
    assert sent["track"] == "passkey" and sent["text"] == "Offline mode" and "type" not in sent
    pg.locator(".arena-pjgoal .arena-new__pile").click()
    pg.get_by_role("dialog", name="New goal for the project").locator('.arena-type[data-type=""]').click()
    form = pg.get_by_role("dialog", name="New goal")
    form.locator(".arena-itsparty__chip").first.wait_for(timeout=WAIT_MS)
    form.locator('.arena-itsparty__chip[data-party="ideas"]').click()                                                    # Ideation: a pitch
    form.get_by_label("What is the pitch?").fill("A pitch for dark mode")
    form.get_by_role("button", name="Judge now").click()
    sent = _calls(pg, host, "ideas.add", at_least=2)[-1]
    assert sent["track"] == "ideas" and sent["text"] == "A pitch for dark mode"


def test_a_partys_own_new_goal_is_unchanged(level):
    pg, host = level
    _show_goal(pg, "passkey")
    pg.locator(".arena-new__pile").click()
    dlg = pg.get_by_role("dialog", name="New goal")
    dlg.wait_for(timeout=WAIT_MS)
    assert dlg.get_by_role("group", name="Its party").count() == 0 and not [c for n, c in host.log if n == "ideas.party_for"]


# -- ideas.shown ------------------------------------------------------------------------------------------------------------------------------------------------

def test_the_project_is_counted_as_a_party_switch_to_and_from_it_fire_and_forget(level):
    pg, host = level
    assert not [1 for n, _ in host.log if n == "ideas.shown"]
    _project(pg)
    assert _calls(pg, host, "ideas.shown")[-1] == {"party": "@project", "from": "passkey"}
    _col(pg, "website").locator(".arena-pcol__head").click()
    pg.locator('.arena[data-goal="website"]').wait_for(timeout=WAIT_MS)
    assert _calls(pg, host, "ideas.shown", at_least=2)[-1] == {"party": "website", "from": "@project"}
    assert len([1 for n, _ in host.log if n == "ideas.shown"]) == 2
