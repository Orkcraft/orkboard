"""Pick one on the desktop (docs/specs/51-pick-one.md §5, §6, Tests → B), in a real browser at 1 440 × 900 against the one window's stub host
(tests/test_arena_desktop_browser.py) with a pick that waits (tests/pick_desktop_host.py): the raised stop in the bottom row (the count, the member's head, the tiles two
by two, *Take B*, *Pick, with a note…*), the drawer's Pick one (the ask, the tiles four across, ← →, the note, *Take B*, *None of them: make new ones*), the tile of
each kind (a picture, a clip's first frame, a sound, a text), picking by the label strip and never by *Play*, one media at a time on the page, nothing playing by itself,
the map's *asks you to pick*, today's rows, and reduced motion. The files are real: the page plays a WAV and a tiny WEBM the stub serves it. Screenshots to the folder
ORKCRAFT_SHOTS names (docs/design/img/v1/ when it is just set)."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.browser_kit import WAIT_MS, gui  # noqa: E402,F401  (fixture)
from tests.pick_desktop_host import ANSWER, ASK, NAMES, PickHost, open_pick  # noqa: E402
from tests.test_shell_browser import SHOTS, _drawer, _sent, _stop, box  # noqa: E402

pytestmark = pytest.mark.browser


@pytest.fixture
def picking(gui):
    """A pick of four pictures; the page, the host."""
    pg, host, errors = open_pick(gui, PickHost())
    yield pg, host
    pg.close()
    assert not errors, "\n".join(errors)


def _page_with(gui, request, **more):
    pg, host, errors = open_pick(gui, PickHost(**more))
    request.addfinalizer(lambda: (pg.close(), None))
    request.addfinalizer(lambda: errors and pytest.fail("\n".join(errors)))
    return pg, host


def _text(loc) -> str:
    return " ".join(loc.inner_text().split())


def _card(pg):
    """The pick's stop, raised: its tiles are in reach."""
    return _stop(pg, "pick")


def _tiles(scope):
    return scope.locator(".pick-tile")


def _radio(scope, key):
    return scope.locator(f"[role=radio][data-variant={key}]")


def _picked(scope) -> list[str]:
    """The keys of the tiles that are picked."""
    return scope.locator("[role=radio][aria-checked=true]").evaluate_all("els => els.map((e) => e.dataset.variant)")


def _drawer_of(pg):
    """The drawer's Pick one, once its tiles are there."""
    drawer = _drawer(pg)
    drawer.locator(".shell-pickone").wait_for(timeout=WAIT_MS)
    return drawer


def _playing(pg) -> list[str]:
    """The media on the page that play now: [<where>/<key>]."""
    return pg.evaluate("""() => [...document.querySelectorAll('.pick-tile audio, .pick-tile video')].filter((m) => !m.paused)
        .map((m) => (m.closest('.shell-drawer') ? 'drawer' : 'card') + '/' + m.closest('.pick-tile').dataset.variant)""")


def _shot(pg, name: str) -> None:
    """A screenshot when ORKCRAFT_SHOTS is set: to the folder it names, else docs/design/img/v1/."""
    want = os.environ.get("ORKCRAFT_SHOTS")
    if want:
        folder = Path(want) if "/" in want else SHOTS
        folder.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(folder / name))


# -- the stop in the bottom row (§6) -------------------------------------------------------------------------------------------------------------

def test_the_stop_is_pick_one_its_gem_the_count_with_the_members_head_and_the_tiles_two_by_two(picking):
    pg, host = picking
    assert pg.locator(".arena-hc").count() == 5 and pg.locator(".arena-hc").first.get_attribute("data-kind") == "pick"       # it blocks work in progress: the host puts it first
    card = _card(pg)
    assert box(pg, ".arena-hc[data-kind=pick]")["width"] == 156 and box(pg, ".arena-hc[data-kind=pick]")["height"] == 246       # the card of the fan, as every stop
    assert card.locator(".arena-hc__kind").text_content() == "Pick one" and card.locator(".ork-gem").text_content() == "4"        # the gem is the count
    assert card.locator(".ork-gem").get_attribute("title") == "4 pictures"
    assert card.get_by_role("button", name="Pick one: Draw the mark").count() == 1 and "elf-warrior" in card.locator(".arena-hc__who img.ork-race__head").get_attribute("src")   # its member's head
    assert card.locator(".arena-hc__who").get_attribute("title") == "made by Screens"
    group = card.get_by_role("radiogroup", name="The pictures")
    assert group.count() == 1 and [t.text_content() for t in group.get_by_role("radio").all()] == ["A · anchor", "B · monogram", "C · lighthouse", "D · compass"]
    boxes = [t.bounding_box() for t in _tiles(card).all()]
    assert boxes[0]["y"] == boxes[1]["y"] and boxes[2]["y"] == boxes[3]["y"] and boxes[0]["x"] == boxes[2]["x"] and boxes[1]["x"] > boxes[0]["x"] + 60      # two by two
    assert boxes[2]["y"] > boxes[0]["y"] + 60 and all(60 <= b["width"] <= 72 for b in boxes)
    assert [b.text_content() for b in card.locator(".arena-hc__quick button").all()] == ["Pick, with a note…"]                        # nothing is picked: no Take
    assert not pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth") and card.locator(".arena-banner, .arena-hc__text").count() == 0


def test_picking_on_the_card_makes_take_b_and_add_a_note_and_taking_sends_via_hand(picking):
    pg, host = picking
    card = _card(pg)
    _radio(card, "B").click()
    assert _picked(card) == ["B"] and [b.text_content() for b in card.locator(".arena-hc__quick button").all()] == ["Take B", "Add a note…"]
    take = card.get_by_role("button", name="Take B")
    assert "primary" in take.get_attribute("class") and take.get_attribute("aria-label") == "Take B: Draw the mark"
    tile = _tiles(card).nth(1)
    assert tile.evaluate("e => getComputedStyle(e).borderTopStyle") == "double" and tile.locator(".pick-tile__on .ork-sign.check").count() == 1      # a double ink line and the check sign
    assert tile.evaluate("e => getComputedStyle(e).borderTopColor") == pg.evaluate("getComputedStyle(document.body).color") and _tiles(card).locator(".ork-sign.check").count() == 1
    _radio(card, "D").click()                                                                                    # another: the one picked moves
    assert _picked(card) == ["D"] and card.get_by_role("button", name="Take D").is_visible()
    card.get_by_role("button", name="Take D").click()
    assert _sent(pg, host, ("ideas.pick", {"slug": "logo", "task": "p1", "key": "D", "via": "hand"}))                 # no note from the card
    pg.locator(".arena-hc[data-kind=pick]").wait_for(state="detached", timeout=WAIT_MS)                              # the stop is answered: it goes
    assert not pg.locator(".arena-task.is-pick").count() and pg.locator(".arena-task[data-task=p1]").get_attribute("data-state") == "running"


def test_a_press_on_the_picture_picks_it_too_but_the_strip_is_the_radio(picking):
    pg, host = picking
    card = _card(pg)
    _tiles(card).nth(2).locator(".pick-tile__media").click(position={"x": 30, "y": 20})
    assert _picked(card) == ["C"]
    assert _radio(card, "C").get_attribute("aria-checked") == "true" and _radio(card, "A").get_attribute("aria-checked") == "false"           # a radio of the group
    assert card.locator("[role=radio]").count() == 4 and card.locator("[role=radiogroup]").count() == 1


@pytest.mark.parametrize("n", [2, 3, 5, 6])
def test_from_two_to_six_variants_fit_the_card_and_the_drawer(gui, request, n):
    pg, host = _page_with(gui, request, n=n)
    card = _card(pg)
    frame = card.bounding_box()
    tiles = [t.bounding_box() for t in _tiles(card).all()]
    assert len(tiles) == n and card.locator(".ork-gem").text_content() == str(n) and card.locator(".ork-gem").get_attribute("title") == f"{n} pictures"
    assert all(frame["x"] <= t["x"] and t["x"] + t["width"] <= frame["x"] + frame["width"] and t["y"] + t["height"] <= card.locator(".arena-hc__quick").bounding_box()["y"] + 0.5 for t in tiles)
    assert len({round(t["x"]) for t in tiles}) == (3 if n > 4 else 1 if n == 2 else 2) and all(t["height"] > 50 for t in tiles)       # two across, three for five or six, one over the other for two
    _shot(pg, f"pick-card-{n}-variants.png")
    card.get_by_role("button", name="Pick, with a note").click()
    drawer = _drawer_of(pg)
    big = [t.bounding_box() for t in _tiles(drawer).all()]
    assert len(big) == n and big[0]["x"] < big[1]["x"] and f"{n} pictures" in _text(drawer.locator(".shell-pickone__by")) and all(b["width"] >= 190 for b in big)
    assert not pg.evaluate("document.querySelector('.shell-result__body').scrollWidth > document.querySelector('.shell-result__body').clientWidth")


# -- each kind's tile (§5) -----------------------------------------------------------------------------------------------------------------

def test_a_picture_is_contained_never_cropped_never_drawn_past_twice_its_size_and_crisp_only_when_small(gui, request):
    sizes = [(16, 16), (64, 64), (65, 40), (128, 96), (400, 300), (0, 0)]                                         # the last is an SVG: no size to keep, never crisp
    pg, host = _page_with(gui, request, n=6, sizes=sizes)
    card = _card(pg)
    card.get_by_role("button", name="Pick, with a note").click()
    drawer = _drawer_of(pg)
    pg.wait_for_function("() => [...document.querySelectorAll('.shell-pickone img')].every((i) => i.complete && i.naturalWidth > 0)", timeout=WAIT_MS)
    crisp = [True, True, False, False, False, False]
    for place in (drawer, card):                                                                                 # large in the drawer, small on the card
        for i, (w, h) in enumerate(sizes):
            tile = _tiles(place).nth(i)
            img, media = tile.locator("img"), tile.locator(".pick-tile__media").bounding_box()
            assert img.get_attribute("alt") == f"{'ABCDEF'[i]} · {NAMES[i]}"                                  # its alt is the variant's label
            assert img.evaluate("e => getComputedStyle(e).objectFit") == "contain", sizes[i]                    # contained, never cropped
            assert (img.evaluate("e => getComputedStyle(e).imageRendering") == "pixelated") is crisp[i], sizes[i]
            at = img.bounding_box()
            assert media["x"] - 0.5 <= at["x"] and at["x"] + at["width"] <= media["x"] + media["width"] + 0.5 and media["y"] - 0.5 <= at["y"] and at["y"] + at["height"] <= media["y"] + media["height"] + 0.5
            if w:                                                                                                  # a picture: at most twice its size, painted whole
                nat = img.evaluate("e => [e.naturalWidth, e.naturalHeight]")
                assert nat == [w, h]
                assert at["width"] <= 2 * w + 0.5 and at["height"] <= 2 * h + 0.5, (place, sizes[i], at)
                assert min(at["width"] / w, at["height"] / h) <= 2.001
            else:
                assert at["width"] >= media["width"] - 1                                                         # a vector fills its tile
        if place is drawer:
            small = [(w, h) for w, h in sizes[:2]]
            big = _tiles(drawer).nth(0).locator("img").bounding_box()
            assert (big["width"], big["height"]) == (small[0][0] * 2, small[0][1] * 2)                           # a 16 px mark is 32 px, not the tile
    assert _tiles(drawer).locator("img").first.get_attribute("src").startswith("/media/logo/p1-r1/a.png?s=")      # the address as the host gave it


def test_a_clip_shows_its_first_frame_the_film_sign_and_its_length_and_plays_in_its_tile_with_the_sound_off(gui, request):
    pg, host = _page_with(gui, request, media="video")
    card = _card(pg)
    first, second = _tiles(card).nth(0), _tiles(card).nth(1)
    video = second.locator("video")
    assert video.get_attribute("preload") == "metadata" and video.get_attribute("playsinline") is not None and video.evaluate("e => e.muted")      # a frame, not the file; muted
    assert video.get_attribute("autoplay") is None and video.get_attribute("controls") is None
    pg.wait_for_function("(e) => e.readyState >= 2 && e.videoWidth === 32", arg=video.element_handle(), timeout=WAIT_MS)                              # the first frame is there
    assert video.evaluate("e => e.paused && e.currentTime < 0.05")
    assert second.locator(".pick-badge .ork-sign.film").count() == 1 and second.locator(".pick-len").text_content() == "0:03"                         # the film sign and its length
    pg.wait_for_function("(e) => e.textContent === '0:03'", arg=first.locator(".pick-len").element_handle(), timeout=WAIT_MS)                          # the host had none: the clip's own
    play = second.get_by_role("button", name="Play")
    assert play.get_attribute("aria-label") == "Play B · monogram" and play.locator(".ork-sign.play").count() == 1
    play.click()
    pg.wait_for_function("(e) => !e.paused && e.currentTime > 0.1", arg=video.element_handle(), timeout=WAIT_MS)                                       # it plays in its tile
    assert video.evaluate("e => e.muted") and second.get_by_role("button", name="Pause").locator(".ork-sign.pause").count() == 1
    assert second.locator(".pick-bar").get_attribute("aria-valuenow") is not None and second.locator(".pick-bar i").evaluate("e => parseFloat(e.style.width)") > 0
    sound = second.get_by_role("button", name="Turn the sound on")
    sound.click()                                                                                                 # the sound is on only when the person turns it on
    assert not video.evaluate("e => e.muted") and second.get_by_role("button", name="Turn the sound off").get_attribute("aria-pressed") == "true"
    assert _picked(card) == []                                                                                    # playing never picks
    second.get_by_role("button", name="Pause").click()
    pg.wait_for_function("(e) => e.paused", arg=video.element_handle(), timeout=WAIT_MS)
    assert second.get_by_role("button", name="Play").count() == 1 and _picked(card) == []


def test_a_sound_has_its_sign_its_length_play_and_pause_and_a_thin_bar_of_where_it_is(gui, request):
    pg, host = _page_with(gui, request, media="audio")
    card = _card(pg)
    tile = _tiles(card).nth(0)
    audio = tile.locator("audio")
    assert audio.get_attribute("preload") == "metadata" and audio.get_attribute("autoplay") is None and tile.locator(".ork-sign.sound").count() == 1
    assert tile.locator(".pick-len").text_content() == "0:02"
    bar = tile.locator(".pick-bar")
    assert bar.get_attribute("role") == "progressbar" and bar.evaluate("e => e.getBoundingClientRect().height") <= 4                              # thin
    tile.get_by_role("button", name="Play").click()
    pg.wait_for_function("(e) => !e.paused && e.currentTime > 0.15", arg=audio.element_handle(), timeout=WAIT_MS)
    assert tile.get_by_role("button", name="Pause").get_attribute("aria-label") == "Pause A · anchor" and tile.locator(".ork-sign.pause").count() == 1
    pg.wait_for_function("(e) => parseFloat(e.style.width) > 5", arg=bar.locator("i").element_handle(), timeout=WAIT_MS)                             # the bar says where it is
    assert _picked(card) == []
    tile.get_by_role("button", name="Pause").click()
    pg.wait_for_function("(e) => e.paused", arg=audio.element_handle(), timeout=WAIT_MS)
    assert tile.get_by_role("button", name="Play").count() == 1 and _picked(card) == []


def test_a_text_shows_its_words_and_the_text_sign_the_first_lines_on_the_card_all_of_it_in_the_drawer(gui, request):
    pg, host = _page_with(gui, request, media="text")
    card = _card(pg)
    first = _tiles(card).nth(0)
    assert "Passkeys, without the password." in _text(first.locator(".pick-words")) and first.locator(".pick-words .ork-sign.text").count() == 1
    assert first.locator("audio, video, img").count() == 0 and first.locator("button").count() == 1               # the strip is its only button: a text has nothing to play
    card.get_by_role("button", name="Pick, with a note").click()
    drawer = _drawer_of(pg)
    words = _tiles(drawer).nth(1).locator(".pick-words")
    assert words.inner_text().split("\n") == ["Your face is the key.", "Your phone is the door."]                 # its own lines, whole
    assert words.get_attribute("tabindex") == "0" and words.get_attribute("role") == "group" and words.get_attribute("aria-label") == "B · monogram"
    assert words.evaluate("e => getComputedStyle(e).fontFamily").startswith('"IBM Plex Mono"')                    # a person's words: the text face, never the pixel face


# -- playing never picks; one at a time; nothing by itself (§5) -------------------------------------------------------------------------------

@pytest.mark.parametrize("media", ["audio", "video"])
def test_playing_never_picks_one_plays_at_a_time_on_the_whole_page_and_nothing_plays_by_itself(gui, request, media):
    pg, host = _page_with(gui, request, media=media)
    card = _card(pg)
    pg.wait_for_timeout(700)
    assert _playing(pg) == [] and pg.evaluate("[...document.querySelectorAll('audio, video')].every((m) => m.paused && m.currentTime < 0.05 && !m.autoplay && !m.hasAttribute('autoplay'))")
    card.locator(".pick-tile[data-variant=A] .pick-play").click()
    pg.wait_for_function("() => document.querySelector('.pick-tile[data-variant=A] audio, .pick-tile[data-variant=A] video').currentTime > 0.1", timeout=WAIT_MS)
    assert _playing(pg) == ["card/A"] and _picked(card) == []                                                     # Play does not pick
    card.locator(".pick-tile[data-variant=B] .pick-play").click()
    pg.wait_for_function("() => document.querySelector('.pick-tile[data-variant=B] audio, .pick-tile[data-variant=B] video').currentTime > 0.1", timeout=WAIT_MS)
    assert _playing(pg) == ["card/B"] and _picked(card) == []                                                     # one at a time: A paused when B began
    assert card.locator(".pick-tile[data-variant=A]").get_by_role("button", name="Play").count() == 1
    _radio(card, "C").click()                                                                                     # picking another does not stop what plays
    assert _picked(card) == ["C"] and _playing(pg) == ["card/B"]
    card.get_by_role("button", name="Add a note").click()                                                         # the drawer's tiles do not start by themselves either
    drawer = _drawer_of(pg)
    pg.wait_for_timeout(500)
    assert _playing(pg) == ["card/B"] and drawer.locator("audio[autoplay], video[autoplay]").count() == 0
    drawer.locator(".pick-tile[data-variant=D] .pick-play").click()
    pg.wait_for_function("() => document.querySelector('.shell-drawer .pick-tile[data-variant=D] audio, .shell-drawer .pick-tile[data-variant=D] video').currentTime > 0.1", timeout=WAIT_MS)
    assert _playing(pg) == ["drawer/D"] and _picked(drawer) == ["C"]                                              # across the card and the drawer: one
    pg.get_by_role("button", name="Close the drawer").click()                                                     # the drawer goes: what played there stops
    pg.wait_for_function("() => document.querySelectorAll('.pick-tile audio, .pick-tile video').length > 0 && ![...document.querySelectorAll('.pick-tile audio, .pick-tile video')].some((m) => !m.paused)", timeout=WAIT_MS)


# -- the drawer's Pick one (§6) ----------------------------------------------------------------------------------------------------------

def test_the_drawer_has_the_ask_four_tiles_across_the_note_and_take_with_none_of_them(picking):
    pg, host = picking
    card = _card(pg)
    card.get_by_role("button", name="Pick, with a note").click()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "pick", "ref": "logo/p1", "device": "desktop", "via": "hand"}))              # the drawer's own tab
    drawer = _drawer_of(pg)
    tab = drawer.get_by_role("tab", name=re.compile("Pick one"))
    assert tab.count() == 1 and "Draw the mark" in tab.text_content()
    view = drawer.locator(".shell-pickone")
    assert view.locator(".arena-lbl").text_content() == "Pick one" and view.locator("h2").text_content() == "Draw the mark"
    assert _text(view.locator(".shell-pickone__by")) == "made by Screens · 4 pictures" and view.locator(".shell-pickone__by img.ork-race__head.small").count() == 1
    assert view.locator(".shell-pickone__ask").text_content() == f"“{ASK}”"
    tiles = [t.bounding_box() for t in _tiles(drawer).all()]
    assert len(tiles) == 4 and len({t["y"] for t in tiles}) == 1 and all(b["x"] > a["x"] for a, b in zip(tiles, tiles[1:])) and all(t["width"] >= 190 for t in tiles)    # four across at 1 440
    note = drawer.get_by_role("textbox", name="Note")
    assert note.get_attribute("placeholder") == "Say why, or what to change (it goes to Screens)" and note.evaluate("e => e.tagName") == "TEXTAREA"
    foot = drawer.locator(".shell-result__foot")
    take, none = foot.get_by_role("button").nth(0), foot.get_by_role("button").nth(1)
    assert take.text_content() == "Take the one you pick" and take.is_disabled() and none.text_content() == "None of them: make new ones" and none.is_enabled()
    _radio(drawer, "B").click()
    assert take.text_content() == "Take B" and take.is_enabled() and "primary" in take.get_attribute("class")
    pg.reload()                                                                                                    # the tab is kept, as every tab is
    _drawer_of(pg)
    assert _picked(pg.locator(".shell-drawer")) == []                                                              # what was picked is a draft of this page
    assert pg.get_by_role("tab", name=re.compile("Pick one")).count() == 1


def test_arrow_keys_move_between_the_tiles_and_pick_as_a_radio_group_does_and_a_key_in_the_note_is_the_notes(picking):
    pg, host = picking
    _card(pg).get_by_role("button", name="Pick, with a note").click()
    drawer = _drawer_of(pg)
    _radio(drawer, "A").focus()
    assert _picked(drawer) == [] and pg.evaluate("document.activeElement.dataset.variant") == "A"                     # the first is the group's way in
    pg.keyboard.press("ArrowRight")
    assert _picked(drawer) == ["B"] and pg.evaluate("document.activeElement.dataset.variant") == "B" and pg.evaluate("document.activeElement.getAttribute('role')") == "radio"
    pg.keyboard.press("ArrowRight")
    pg.keyboard.press("ArrowRight")
    assert _picked(drawer) == ["D"]
    pg.keyboard.press("ArrowRight")
    assert _picked(drawer) == ["A"] and pg.evaluate("document.activeElement.dataset.variant") == "A"                  # round the group
    pg.keyboard.press("ArrowLeft")
    assert _picked(drawer) == ["D"] and pg.evaluate("document.activeElement.dataset.variant") == "D"
    pg.keyboard.press("ArrowLeft")
    assert _picked(drawer) == ["C"]
    assert [r.get_attribute("tabindex") for r in drawer.get_by_role("radio").all()] == ["-1", "-1", "0", "-1"]      # one stop for the Tab key: the picked one
    note = drawer.get_by_role("textbox", name="Note")
    note.focus()
    pg.keyboard.type("ab")
    pg.keyboard.press("ArrowLeft")
    assert _picked(drawer) == ["C"] and pg.evaluate("document.activeElement.tagName") == "TEXTAREA"               # the caret moves, the pick does not
    assert drawer.get_by_role("button", name="Take C").is_enabled()


def test_taking_in_the_drawer_sends_the_pick_with_its_note_and_via_drawer_and_the_tab_closes(picking):
    pg, host = picking
    _card(pg).get_by_role("button", name="Pick, with a note").click()
    drawer = _drawer_of(pg)
    _radio(drawer, "C").click()
    drawer.get_by_role("textbox", name="Note").fill("  Bolder, and on the left  ")
    drawer.get_by_role("button", name="Take C").click()
    assert _sent(pg, host, ("ideas.pick", {"slug": "logo", "task": "p1", "key": "C", "note": "Bolder, and on the left", "via": "drawer"}))
    pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)                                       # answered: the tab goes
    pg.mouse.move(5, 5)                                                                                             # (the fan keeps still while the pointer is on one of its cards)
    pg.locator(".arena-hc[data-kind=pick]").wait_for(state="detached", timeout=WAIT_MS)


def test_none_of_them_asks_for_a_note_first_then_sends_null_and_the_next_round_is_asked_for(picking):
    pg, host = picking
    _card(pg).get_by_role("button", name="Pick, with a note").click()
    drawer = _drawer_of(pg)
    none = drawer.get_by_role("button", name="None of them: make new ones")
    none.click()
    pg.wait_for_timeout(300)
    assert not [1 for n, _ in host.log if n == "ideas.pick"]                                                       # nothing is sent without a note
    refused = drawer.get_by_role("alert")
    assert refused.text_content() == ANSWER and pg.evaluate("document.activeElement.getAttribute('aria-label')") == "Note"       # it says why, and the note is in reach
    drawer.get_by_role("textbox", name="Note").fill("Less round, more anchor")
    assert drawer.get_by_role("alert").count() == 0
    none.click()
    assert _sent(pg, host, ("ideas.pick", {"slug": "logo", "task": "p1", "key": None, "note": "Less round, more anchor", "via": "drawer"}))
    pg.locator(".shell-drawer").wait_for(state="detached", timeout=WAIT_MS)
    pg.mouse.move(5, 5)
    card = _card(pg)                                                                                              # the next round: new ones to pick from, none picked
    assert card.locator(".pick-tile img").first.get_attribute("src").startswith("/media/logo/p1-r2/a.png") and _picked(card) == []
    card.get_by_role("button", name="Pick, with a note").click()
    assert "round 2" in _text(_drawer_of(pg).locator(".shell-pickone__by"))


def test_the_host_s_refusal_stays_in_the_drawer_in_the_host_s_words(picking):
    pg, host = picking
    _card(pg).get_by_role("button", name="Pick, with a note").click()
    drawer = _drawer_of(pg)
    _radio(drawer, "A").click()
    host.waits = False                                                                                              # answered elsewhere (the phone): the host's refusal, in its words
    host.handle_refusal = "That pick is answered already"
    original = host.handle

    def refuse(name, a):
        if name == "ideas.pick":
            host.log.append((name, a))
            return {"error": host.handle_refusal}
        return original(name, a)
    host.handle = refuse
    drawer.get_by_role("button", name="Take A").click()
    pg.get_by_text("That pick is answered already").first.wait_for(timeout=WAIT_MS)
    assert pg.locator(".shell-drawer").count() == 1                                                                 # the drawer stays: nothing was taken


def test_what_is_picked_and_written_is_one_state_of_the_card_and_the_drawer(picking):
    pg, host = picking
    card = _card(pg)
    _radio(card, "B").click()
    card.get_by_role("button", name="Add a note").click()                                                           # picked on the card: picked in the drawer
    drawer = _drawer_of(pg)
    assert _picked(drawer) == ["B"] and drawer.get_by_role("button", name="Take B").is_enabled()
    _radio(drawer, "D").click()                                                                                      # and the other way round
    drawer.get_by_role("textbox", name="Note").fill("a draft")
    assert _picked(card) == ["D"]
    pg.get_by_role("button", name="Close the drawer").click()
    card = _card(pg)
    assert card.get_by_role("button", name="Take D").is_visible()
    card.get_by_role("button", name="Add a note").click()
    assert _drawer_of(pg).get_by_role("textbox", name="Note").input_value() == "a draft"                          # the draft is kept while the page is


# -- the map, the member, today ----------------------------------------------------------------------------------------------------------

def test_a_task_that_asks_you_to_pick_says_so_with_the_alert_sign_on_its_card_its_member_and_its_goal(picking):
    pg, host = picking
    task = pg.locator(".arena-task[data-task=p1]")
    assert task.get_attribute("data-state") == "picking" and "is-pick" in task.get_attribute("class")
    foot = task.locator(".arena-task__foot")
    assert _text(foot) == "asks you to pick" and foot.locator(".ork-sign.alert").count() == 1 and "!" not in foot.text_content()               # the alert sign, drawn
    alert = pg.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-alert)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
    assert foot.evaluate("e => getComputedStyle(e).color") == alert
    member = pg.locator(".arena-member[data-agent=screens]")
    assert "asks you to pick" in member.get_attribute("aria-label") and member.locator(".arena-sign .ork-sign.alert").count() == 1             # the member that waits for the person
    row = pg.locator(".arena-goal[data-slug=logo]")
    assert row.locator(".arena-goal__mark .ork-sign.alert").count() == 1 and row.locator(".arena-goal__mark").get_attribute("title") == "waits for you"
    assert pg.locator(".arena-gtab.is-on .ork-count").text_content() == "5"                                                                     # the pick is one of the stops
    task.click()                                                                                                    # a press on it opens the pick, not its log
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "pick", "ref": "logo/p1", "device": "desktop", "via": "map"}))
    assert "Draw the mark" in _drawer_of(pg).locator(".shell-pickone").inner_text()


def test_todays_strip_takes_the_alert_tone_and_the_pick_kind_and_an_answered_pick_says_so(picking):
    pg, host = picking
    host.today_events[:0] = [{"at": "13:20", "mark": "✓", "tone": "ok", "words": "Picked B", "title": "Draw an icon", "goal": "passkey", "idea": "logo", "task": "p0",
                              "open": {"kind": "pick", "slug": "logo", "task": "p0"}},
                             {"at": "13:10", "mark": "↺", "tone": "muted", "words": "New ones asked", "title": "Draw a banner", "goal": "passkey", "idea": "logo", "task": "p9",
                              "open": {"kind": "pick", "slug": "logo", "task": "p9"}}]
    host.bump({})
    asked = pg.locator(".arena-today .arena-hitem[data-open=pick]").last
    asked.wait_for(timeout=WAIT_MS)
    items = pg.locator(".arena-today .arena-hitem[data-open=pick]")
    assert items.count() == 3
    asked = pg.locator(".arena-hitem", has=pg.locator(".ork-sign.alert"))
    assert asked.get_attribute("aria-label") == "13:05 · Draw the mark · Pick one" and "is-alert" in asked.get_attribute("class") and asked.text_content() == ""   # a sign, not a typed mark
    assert asked.evaluate("e => getComputedStyle(e).color") == pg.evaluate("(() => { const d = document.createElement('span'); d.style.color = 'var(--ork-alert)'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
    picked = pg.locator(".arena-hitem[aria-label^='13:20']")
    assert picked.get_attribute("aria-label") == "13:20 · Draw an icon · Picked B" and picked.locator(".ork-sign.check").count() == 1 and "is-ok" in picked.get_attribute("class")
    assert pg.locator(".arena-hitem[aria-label^='13:10']").get_attribute("aria-label") == "13:10 · Draw a banner · New ones asked"
    asked.click()
    assert _sent(pg, host, ("ideas.log", {"event": "opened", "what": "pick", "ref": "logo/p1", "device": "desktop", "via": "today"}))
    assert "Draw the mark" in _drawer_of(pg).locator(".shell-pickone").inner_text()
    picked.click()                                                                                                  # a pick answered long ago: its tab says so
    gone = pg.locator(".shell-drawer .shell-empty")
    gone.wait_for(timeout=WAIT_MS)
    assert _text(gone).startswith("That pick is answered already") and gone.get_by_role("button", name="Close").is_visible()


# -- reduced motion (§11 of spec 49 holds) -----------------------------------------------------------------------------------------------

def test_under_reduced_motion_nothing_about_a_pick_animates(gui):
    pg, host, errors = open_pick(gui, PickHost(media="audio"), reduced=True)
    try:
        assert pg.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
        card = _card(pg)
        _radio(card, "B").click()
        card.locator(".pick-tile[data-variant=B] .pick-play").click()
        card.get_by_role("button", name="Add a note").click()
        drawer = _drawer_of(pg)
        _radio(drawer, "C").click()
        pg.wait_for_timeout(400)
        for scope in (card, drawer):
            moving = scope.locator(".pick-tiles, .pick-tiles *").evaluate_all(
                "els => els.filter((e) => { const c = getComputedStyle(e); return c.transitionDuration.split(',').some((d) => parseFloat(d) > 0) || c.animationName !== 'none'; }).length")
            assert moving == 0
        assert card.evaluate("e => getComputedStyle(e).transitionDuration") == "0s"                              # the raised card does not slide either
        assert pg.evaluate("document.getAnimations().length") == 0
    finally:
        pg.close()
    assert not errors, "\n".join(errors)


def test_the_sheets_give_a_pick_no_transition_and_no_animation_to_begin_with():
    from orkboard.gui import server
    css = (server.STATIC / "js" / "arena" / "arena.css").read_text(encoding="utf-8")
    start, end = css.index("/* -- Pick one"), css.index("/* -- what is left of your AI tools")
    mine = css[start:end]
    assert "transition" not in mine and "animation" not in mine and "@keyframes" not in mine
    assert "image-rendering: pixelated" in mine and "object-fit: contain" in mine                                  # the picture's two rules of §5


# -- looking at it ----------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("media", ["image", "audio", "video", "text"])
def test_screenshots_of_the_card_and_the_drawer_of_each_kind(gui, media):
    pg, host, errors = open_pick(gui, PickHost(media=media, n=4))
    try:
        card = _card(pg)
        _radio(card, "C").click()
        pg.mouse.move(700, 120)
        _radio(card, "C").focus()
        _shot(pg, f"pick-card-{media}.png")
        card.get_by_role("button", name="Add a note").click()
        drawer = _drawer_of(pg)
        drawer.get_by_role("textbox", name="Note").fill("Closer to the first one, and a little bolder.")
        pg.mouse.move(700, 800)
        _shot(pg, f"pick-drawer-{media}.png")
        assert _picked(drawer) == ["C"]
    finally:
        pg.close()
    assert not errors, "\n".join(errors)
