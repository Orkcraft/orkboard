"""Spec 51 part C, the phone (docs/specs/51-pick-one.md §5, §7, §8 "B / C"): Chromium at 390 × 844 against the scene of tests/test_pwa_arena_browser.py with a goal whose task left variants to
pick from. The files are real ones (tests/pick_files.py, a tiny WebM clip beside them) put in the host's state folder and served by the phones' listener at their signed addresses, so a picture,
a sound and a clip load as they do on a phone. Each kind's tile (a picture contained and never cropped, a clip's frame with its length and *Play*, a sound's *Play* / *Pause* and bar, a text);
picking by the label strip and never by *Play*; one playing at a time and nothing playing by itself; *Take B*'s command with the `via` of where it was answered; *None of them* asking for the
note first; the pick's own screen (one tile to a screen, swiped with a snap, the note and the two answers under them); a redraw that does not stop a sound or lose a press; reduced motion; the
44 px targets; the stop in the fan, the field's *asks you to pick*, Today's rows; the service worker that never keeps `/media/`."""
from __future__ import annotations

import copy
import os
import struct
import zlib
from pathlib import Path

import pytest

from orkboard.gui import media
from orkboard.gui.board_host import Orkboard
from orkboard.realm import idea_pick
from tests import pick_files as pf
from tests.test_pwa_arena_browser import ELF, SCENE, SCREENS, STAMP, _redrawn, _scene, node, task  # noqa: F401
from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, Stub, _band, _called, _phone, _pop, _today  # noqa: F401

pytest.importorskip("playwright.async_api")
pytestmark = pytest.mark.browser

SHOTS = os.environ.get("PICK_SHOTS", "")                                  # a folder: screenshots of the window are kept there
CLIP = (Path(__file__).parent / "fixtures" / "pick_clip.webm").read_bytes()      # a real 3-second VP8 clip, 64 × 48
ANSWERS: dict = {}                                                         # what the stub says to `ideas.pick`: {"error": "…"} refuses


def art(w: int, h: int, ink=(0x6A, 0xA8, 0x4F), ground=(0x1A, 0x1A, 0x1A), edge=True) -> bytes:
    """A PNG of `w` × `h`: a ground, an ink square in the middle and, with `edge`, a ring of ink along the very border (a picture that is cropped loses it)."""
    def px(x: int, y: int) -> tuple:
        if edge and (x in (0, w - 1) or y in (0, h - 1)):
            return ink
        return ink if w // 3 <= x < w - w // 3 and h // 3 <= y < h - h // 3 else ground

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = b"".join(b"\x00" + b"".join(bytes(px(x, y)) for x in range(w)) for y in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def svg_art(w: int = 48, h: int = 36, ink: str = "#d4b77a") -> bytes:
    """A vector mark in ink that shows on the dark ground (tests/pick_files.py's is black)."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect x="2" y="2" width="{w - 4}" height="{h - 4}" fill="none" stroke="{ink}" stroke-width="2"/>'
            f'<path d="M{w // 2} 6 L{w - 8} {h - 6} L8 {h - 6} Z" fill="{ink}"/></svg>').encode()


def files_of(media_kind: str) -> tuple[dict[str, bytes], str]:
    """The files a task of this kind left, named by their variants (the stem is the name), and its ask."""
    if media_kind == "image":
        return ({"anchor.png": art(16, 16), "monogram.png": art(120, 90, ink=(0xD4, 0xB7, 0x7A)), "lighthouse.svg": svg_art(), "compass.png": art(300, 200, ink=(0x82, 0xAA, 0xFF))},
                "Four marks for the passkey button. Which one goes on the sign-in page?")
    if media_kind == "audio":
        return {"chime.wav": pf.wav(4.0), "pluck.wav": pf.wav(5.0), "drone.wav": pf.wav(6.0)}, "Three sounds for a passkey that signed in. Which one?"
    if media_kind == "video":
        return {"fade.webm": CLIP, "slide.webm": CLIP, "pop.webm": CLIP}, "Three clips for the empty state. Which one?"
    return ({"short.txt": pf.text("Sign in without a password."), "warm.txt": pf.text("Your passkey is your face, your finger, or a quiet tap on your phone. No password to forget.\n\nWelcome back."),
             "plain.md": pf.text("# Sign in\n\nUse your passkey.")}, "Three taglines for the sign-in page. Which one?")


def add_pick(repo: Path, tmp: Path, media_kind: str = "image", slug: str = "logo", tid: str = "l1", title: str = "Draw the logo", rnd: int = 1) -> dict:
    """A pick of this kind put in the host's state folder as the runner leaves it, a goal *Logo* with its task `picking` on the Map, and its Needs you row. Returns the row."""
    host = Orkboard(repo)
    try:
        state = host.ideas.state_dir
    finally:
        host.close()
    files, ask = files_of(media_kind)
    pick = pf.make_pick(state, tmp / "scratch", files, slug=slug, tid=tid, rnd=rnd, kind=media_kind, by="screens")
    variants = []
    for v in pick["variants"]:
        row = {"key": v["key"], "name": v["name"], "why": v["why"], "url": media.url(slug, pick["id"], v["file"]), "mime": v["mime"], "w": v["w"], "h": v["h"], "seconds": v["seconds"]}
        if v["mime"].startswith("text/"):
            row["text"] = (idea_pick.folder_of(state, slug, pick["id"]) / v["file"]).read_text(encoding="utf-8")
        variants.append(row)
    n = len(variants)
    row = {"kind": "pick", "slug": slug, "idea": slug, "goal": "passkey", "task": tid, "title": title, "short": "Logo", "idea_title": "A mark for the sign-in button", "priority": "high", "blocks": True,
           "by": {"slug": "screens", "name": "Screens", "head": ELF}, "ask": ask, "n": n, "media": media_kind, "round": rnd, "at": STAMP, "variants": variants}
    SCENE["needs"].append(row)
    SCENE["map"]["nodes"].append(node(slug, "A mark for the sign-in button", "working", "implementation", progress={"done": 0, "total": 1}, waits={"kind": "you", "ref": "", "title": "", "until": ""},
                                      tasks=[task(tid, title, "picking", SCREENS, 1, pick={"n": n, "media": media_kind, "round": rnd})]))
    SCENE["map"]["goals"][0]["ideas"] += 1
    for m in SCENE["map"]["goals"][0]["party"]:
        if m["slug"] == "screens":
            m.update(state="needs", why="pick")                                                                         # as the host says a member that has a task waiting for a pick
    return row


@pytest.fixture(autouse=True)
def _pick_stub(_scene, monkeypatch):
    """The stub answers `ideas.pick` as the host does (an answered pick leaves Needs you), or with the error the test sets."""
    ANSWERS.clear()
    real = Stub.commands

    def commands(self):
        def pick(a):
            a = {k: v for k, v in a.items() if k not in ("link", "device")}
            self.calls.append(("ideas.pick", dict(a)))
            if ANSWERS.get("error"):
                return {"error": ANSWERS["error"]}
            SCENE["needs"] = [n for n in SCENE["needs"] if not (n["kind"] == "pick" and n["task"] == a["task"])]
            for n in SCENE["map"]["nodes"]:
                for t in n["tasks"]:
                    if t["id"] == a["task"] and t["state"] == "picking":
                        t.update(state="review" if a["key"] else "running", pick=None)
            return self.bump({"ok": True})
        def task_of(a):
            if a["task"] != "l1":
                return real(self)["ideas.task"](a)
            state = next(t["state"] for n in SCENE["map"]["nodes"] for t in n["tasks"] if t["id"] == "l1")
            return {"id": "l1", "title": "Draw the logo", "brief": "Brief of Draw the logo", "tier": "warrior", "after": [], "state": state, "branch": "idea/logo/l1", "commit": "", "session": "s", "cost": 0.4,
                    "tokens": 10, "started": "", "finished": "", "error": "", "note": "", "round": 1, "tests": None, "diff": None, "conflict": "", "why": "", "idea": a["slug"],
                    "idea_title": "A mark for the sign-in button", "log": "== round 1\nmaking marks\n", "head": ELF, "by": SCREENS}
        return {**real(self), "ideas.pick": pick, "ideas.task": task_of}
    monkeypatch.setattr(Stub, "commands", commands)


async def _shot_to(page, name: str) -> None:
    if SHOTS:
        Path(SHOTS).mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(Path(SHOTS) / f"{name}.png"))


async def _raise(page, title: str = "Draw the logo"):
    """The stop popped out of the fan; its tiles loaded (a picture decoded, a sound's or a clip's length read)."""
    raised = await _pop(page, f"Pick one: {title}")
    await raised.locator(".pk").first.wait_for(timeout=WAIT_MS)
    await page.wait_for_function("() => [...document.querySelectorAll('.raised img')].every((i) => i.complete) && [...document.querySelectorAll('.raised audio, .raised video')].every((m) => m.readyState >= 1)",
                                 timeout=WAIT_MS)
    return raised


async def _swipe(page, x: float, y: float, dx: float, steps: int = 10) -> None:
    """A finger put down at (x, y) and dragged `dx` sideways in `steps` moves, then lifted: real touch events, so the scrolling and its snap are the browser's."""
    cdp = await page.context.new_cdp_session(page)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    for i in range(1, steps + 1):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x + dx * i / steps, "y": y}]})
        await page.wait_for_timeout(16)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


async def _playing(page) -> list[str]:
    """The keys of the tiles whose media plays now."""
    return await page.evaluate("() => [...document.querySelectorAll('.pk')].filter((t) => { const m = t.querySelector('audio, video'); return m && !m.paused; }).map((t) => t.dataset.key)")


# -- each kind's tile ------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_pictures_tile_is_contained_on_its_ground_never_cropped_and_pixelated_only_when_it_is_64_px_or_less(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "image")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        tiles = raised.locator(".pk")
        assert await tiles.count() == 4 and await raised.locator(".pks").get_attribute("role") == "radiogroup"
        assert [await t.get_attribute("data-kind") for t in await tiles.all()] == ["image"] * 4
        got = await page.evaluate("""() => [...document.querySelectorAll('.raised .pk')].map((t) => { const i = t.querySelector('img'), v = t.querySelector('.pk__view').getBoundingClientRect(), r = i.getBoundingClientRect(), s = getComputedStyle(i);
            return { alt: i.alt, fit: s.objectFit, pixel: s.imageRendering, nw: i.naturalWidth, nh: i.naturalHeight, w: r.width, h: r.height, inside: r.left >= v.left - 0.5 && r.right <= v.right + 0.5 && r.top >= v.top - 0.5 && r.bottom <= v.bottom + 0.5 }; })""")
        assert [g["alt"] for g in got] == ["A · anchor", "B · monogram", "C · lighthouse", "D · compass"]          # its alt is the variant's label
        assert all(g["fit"] == "contain" and g["inside"] for g in got)                                              # contained on the ground, never cropped, never spilling out of the tile
        assert [g["pixel"] for g in got] == ["pixelated", "auto", "auto", "auto"]                                  # the 16 px one only
        anchor, monogram, _, compass = got
        assert round(anchor["w"]) == 32 and round(anchor["h"]) == 32                                               # 16 px, up to twice its size, not to the tile
        assert round(monogram["w"]) <= 2 * monogram["nw"] and round(monogram["h"]) <= 2 * monogram["nh"] and monogram["w"] > monogram["nw"]      # 120 × 90 drawn up to the tile's width, at most 2×
        assert compass["w"] < compass["nw"] and compass["w"] <= 150                                               # 300 px wide, drawn smaller: fit into the tile
        await _shot_to(page, "pick-images")


@pytest.mark.asyncio
async def test_a_clips_tile_shows_its_first_frame_its_length_and_play_with_its_sound_off(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "video")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        tile = raised.locator('.pk[data-key="A"]')
        video = tile.locator("video")
        assert await video.get_attribute("preload") == "metadata" and await video.get_attribute("playsinline") is not None
        await page.wait_for_function("() => { const v = document.querySelector('.raised .pk[data-key=\"A\"] video'); return v.readyState >= 2; }", timeout=WAIT_MS)       # its first frame is drawn
        assert await video.evaluate("v => v.muted && v.paused && v.currentTime < 0.1")                                  # muted, not playing
        assert await tile.locator(".pk__meta .ork-sign.film").count() == 1 and await tile.locator(".pk__len").inner_text() == "0:03"      # the film sign and its length, in a corner
        play = tile.get_by_role("button", name="Play")
        assert await play.locator(".ork-sign.play").count() == 1 and (await play.bounding_box())["height"] >= 43
        sound = tile.get_by_role("button", name="Sound")
        assert await sound.get_attribute("aria-pressed") == "false"                                                  # off until it is turned on
        await play.click()
        await page.wait_for_function("() => document.querySelector('.raised .pk[data-key=\"A\"] video') && !document.querySelector('.raised .pk[data-key=\"A\"] video').paused", timeout=WAIT_MS)
        assert await video.evaluate("v => v.muted") and await tile.get_by_role("button", name="Pause").locator(".ork-sign.pause").count() == 1
        await sound.click()
        assert await video.evaluate("v => !v.muted") and await sound.get_attribute("aria-pressed") == "true"         # turned on by the person
        assert await tile.get_attribute("aria-checked") is None and await tile.locator(".pk__label").get_attribute("aria-checked") == "false"   # playing never picks
        await _shot_to(page, "pick-clips")


@pytest.mark.asyncio
async def test_a_sounds_tile_has_its_sign_its_length_play_pause_and_a_thin_bar_that_follows_it_and_seeks(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "audio")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        tile = raised.locator('.pk[data-key="A"]')
        assert await tile.locator(".pk__meta .ork-sign.sound").count() == 1 and await tile.locator(".pk__len").inner_text() == "0:04"
        bar = tile.locator(".pk__bar")
        assert await bar.get_attribute("type") == "range" and await bar.evaluate("e => e.value") == "0" and await bar.evaluate("e => getComputedStyle(e).height") == "44px"
        await tile.get_by_role("button", name="Play").click()
        await page.wait_for_function("() => document.querySelector('.raised .pk[data-key=\"A\"] audio').currentTime > 0.3", timeout=WAIT_MS)
        await page.wait_for_function("() => Number(document.querySelector('.raised .pk[data-key=\"A\"] .pk__bar').value) > 20", timeout=WAIT_MS)   # the bar follows the sound
        await tile.get_by_role("button", name="Pause").click()
        await tile.get_by_role("button", name="Play").wait_for(timeout=WAIT_MS)                                     # (named again when the sound says it paused)
        box = await bar.bounding_box()
        await page.mouse.click(box["x"] + box["width"] * 0.75, box["y"] + box["height"] / 2)                          # a press on the bar seeks
        await page.wait_for_function("() => document.querySelector('.raised .pk[data-key=\"A\"] audio').currentTime > 2.4", timeout=WAIT_MS)
        assert await tile.locator(".pk__label").get_attribute("aria-checked") == "false"                             # and picks nothing
        await _shot_to(page, "pick-sounds")


@pytest.mark.asyncio
async def test_a_texts_tile_shows_its_words_the_first_lines_in_the_tile_and_all_of_them_on_its_own_screen(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "text")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        tiles = raised.locator(".pk")
        assert await tiles.count() == 3 and await tiles.first.locator(".ork-sign.text").count() == 1
        assert await tiles.first.locator(".pk__words").inner_text() == "Sign in without a password."
        warm = raised.locator('.pk[data-key="B"] .pk__words')
        assert "Welcome back." in await warm.inner_text()
        assert await raised.locator('.pk[data-key="C"] .pk__words').inner_text() == "# Sign in\n\nUse your passkey."      # Markdown keeps its marks: what is written keeps its words
        assert await warm.evaluate("e => getComputedStyle(e).fontFamily.includes('Plex') && !getComputedStyle(e).fontFamily.includes('Pixelify')")     # never the pixel face
        await _shot_to(page, "pick-texts")
        await raised.locator('[data-act="open-screen"]').click()
        screen = page.locator(".screen .pks.is-swipe")
        await screen.wait_for(timeout=WAIT_MS)
        long = screen.locator('.pk[data-key="B"] .pk__words')
        assert await long.evaluate("e => e.scrollHeight <= e.clientHeight + 1") and "quiet tap on your phone" in await long.inner_text()        # all of it, no clamp


# -- picking: the label strip, not Play ------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_label_strip_picks_as_a_radio_and_play_never_does(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "audio")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        take = raised.locator('[data-act="take"]')
        assert (await take.inner_text()) == "Take the one you pick" and await take.is_disabled()                       # nothing is picked yet
        strips = raised.locator(".pk__label")
        assert [await s.get_attribute("role") for s in await strips.all()] == ["radio"] * 3 and [await s.get_attribute("aria-checked") for s in await strips.all()] == ["false"] * 3
        assert [await s.inner_text() for s in await strips.all()] == ["A · chime", "B · pluck", "C · drone"]            # the label: the letter, a dot, the task's name for it
        await raised.locator('.pk[data-key="B"]').get_by_role("button", name="Play").click()                           # Play: plays, picks nothing
        await page.wait_for_function("() => document.querySelector('.raised .pk[data-key=\"B\"] audio') && !document.querySelector('.raised .pk[data-key=\"B\"] audio').paused", timeout=WAIT_MS)
        assert [await s.get_attribute("aria-checked") for s in await strips.all()] == ["false"] * 3 and await take.is_disabled()
        assert await raised.locator(".pk.is-on").count() == 0 and await raised.locator(".pk__on").evaluate_all("els => els.every((e) => getComputedStyle(e).display === 'none')")
        await strips.nth(1).click()                                                                                      # the strip: picks it (one tap)
        assert await strips.nth(1).get_attribute("aria-checked") == "true" and await raised.locator(".pk.is-on").count() == 1
        assert await take.inner_text() == "Take B" and await take.is_enabled()
        tile = raised.locator('.pk[data-key="B"]')
        assert await tile.evaluate("e => getComputedStyle(e).borderStyle") == "double" and await tile.locator(".pk__on .ork-sign.check").is_visible()      # a double line and the check sign
        assert await _playing(page) == ["B"]                                                                             # picking did not stop the sound
        await strips.nth(2).click()                                                                                      # radios: another pick takes it over
        assert await take.inner_text() == "Take C" and [await s.get_attribute("aria-checked") for s in await strips.all()] == ["false", "false", "true"]
        await raised.locator('.pk[data-key="A"] .pk__view').click(position={"x": 8, "y": 8})                            # a tap on the picture picks it too (not on Play, the bar or the sound switch)
        assert await take.inner_text() == "Take A"
        await _shot_to(page, "pick-picked")


@pytest.mark.asyncio
async def test_the_strips_are_one_stop_of_the_tab_and_the_arrows_move_the_pick(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "image")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        strips = raised.locator(".pk__label")
        assert [await s.get_attribute("tabindex") for s in await strips.all()] == ["0", "-1", "-1", "-1"]
        await strips.first.focus()
        await page.keyboard.press("ArrowRight")
        assert await strips.nth(1).get_attribute("aria-checked") == "true" and await strips.nth(1).evaluate("e => document.activeElement === e")
        assert [await s.get_attribute("tabindex") for s in await strips.all()] == ["-1", "0", "-1", "-1"]
        await page.keyboard.press("ArrowLeft")
        await page.keyboard.press("ArrowLeft")
        assert await strips.nth(3).get_attribute("aria-checked") == "true"                                              # round the group


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["audio", "video"])
async def test_one_plays_at_a_time_and_nothing_plays_by_itself(fake_repo, monkeypatch, tmp_path, kind):
    add_pick(fake_repo, tmp_path, kind)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        await page.wait_for_timeout(700)
        assert await _playing(page) == [] and await page.evaluate("() => [...document.querySelectorAll('audio, video')].every((m) => m.paused && !m.autoplay && m.currentTime < 0.2)")      # nothing by itself
        await raised.locator('.pk[data-key="A"]').get_by_role("button", name="Play").click()
        await page.wait_for_function("() => document.querySelector('.raised .pk[data-key=\"A\"]').querySelector('audio, video').currentTime > 0.1", timeout=WAIT_MS)
        assert await _playing(page) == ["A"]
        await raised.locator('.pk[data-key="C"]').get_by_role("button", name="Play").click()                           # another starts: the first stops
        await page.wait_for_function("() => document.querySelector('.raised .pk[data-key=\"A\"]').querySelector('audio, video').paused", timeout=WAIT_MS)
        assert await _playing(page) == ["C"]
        assert await raised.locator('.pk[data-key="A"]').get_by_role("button", name="Play").count() == 1 and await raised.locator('.pk[data-key="C"]').get_by_role("button", name="Pause").count() == 1
        await raised.locator('.pk[data-key="C"]').get_by_role("button", name="Pause").click()
        await page.wait_for_function("() => document.querySelector('.raised .pk[data-key=\"C\"]').querySelector('audio, video').paused", timeout=WAIT_MS)
        assert await _playing(page) == []
        await raised.locator('.pk[data-key="B"]').get_by_role("button", name="Play").click()                           # and a card put back stops what plays
        await page.wait_for_function("() => document.querySelector('.raised .pk[data-key=\"B\"]').querySelector('audio, video').currentTime > 0.1", timeout=WAIT_MS)
        await page.keyboard.press("Escape")
        await page.locator("dialog.raised-dlg").wait_for(state="hidden", timeout=WAIT_MS)
        await page.wait_for_function("() => [...document.querySelectorAll('audio, video')].every((m) => m.paused)", timeout=WAIT_MS)      # (stopped as the dialog closes)
        assert await _playing(page) == []


# -- the answers -----------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_take_b_sends_ideas_pick_with_its_letter_the_note_and_via_hand_and_puts_the_card_back(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "image")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        await raised.locator('.pk__label[data-key="B"]').click()
        note = raised.get_by_label("Note")
        assert await note.get_attribute("placeholder") == "Say why, or what to change (it goes to Screens)"
        await note.fill("  The monogram reads at 16 px.  ")
        await raised.get_by_role("button", name="Take B").click()
        assert await _called(stub, "ideas.pick", {"slug": "logo", "task": "l1", "key": "B", "note": "The monogram reads at 16 px.", "via": "hand"})
        await page.locator("dialog.raised-dlg").wait_for(state="hidden", timeout=WAIT_MS)
        await page.locator(".flash", has_text="Picked B").wait_for(timeout=WAIT_MS)
        await page.wait_for_function("() => !document.querySelector('.hc[data-kind=\"pick\"]')", timeout=WAIT_MS)       # the Board read again: it left Needs you
        assert len([c for c in stub.calls if c[0] == "ideas.pick"]) == 1                                                # one tap, one command


@pytest.mark.asyncio
async def test_take_sends_no_note_when_there_is_none(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "text")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        await raised.locator('.pk__label[data-key="C"]').click()
        await raised.get_by_role("button", name="Take C").click()
        assert await _called(stub, "ideas.pick", {"slug": "logo", "task": "l1", "key": "C", "via": "hand"})


@pytest.mark.asyncio
async def test_none_of_them_needs_a_note_first_then_asks_for_new_ones(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "image")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        none = raised.get_by_role("button", name="None of them: make new ones")
        await none.click()                                                                                              # no note: nothing is sent, the card says what is missing and the note takes the focus
        say = raised.locator(".pk__say")
        await say.wait_for(timeout=WAIT_MS)
        assert (await say.inner_text()) == "A note says what to change: write one first" and await say.get_attribute("role") == "alert"
        assert await raised.get_by_label("Note").evaluate("e => document.activeElement === e") and await raised.get_by_label("Note").get_attribute("aria-invalid") == "true"
        await page.wait_for_timeout(300)
        assert not [c for c in stub.calls if c[0] == "ideas.pick"] and await page.locator("dialog.raised-dlg[open]").count() == 1
        await raised.get_by_label("Note").fill("Draw them heavier.")
        assert await say.is_hidden()
        await none.click()
        assert await _called(stub, "ideas.pick", {"slug": "logo", "task": "l1", "key": None, "note": "Draw them heavier.", "via": "hand"})
        await page.locator(".flash", has_text="New ones asked").wait_for(timeout=WAIT_MS)


@pytest.mark.asyncio
async def test_a_refusal_of_the_host_is_said_on_the_card_where_it_can_be_seen_and_the_card_stays(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "image")
    ANSWERS["error"] = "That pick is answered already"
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        await raised.locator('.pk__label[data-key="D"]').click()
        await raised.get_by_role("button", name="Take D").click()
        await raised.locator(".pk__say", has_text="That pick is answered already").wait_for(timeout=WAIT_MS)            # not a toast under the card
        assert await page.locator("dialog.raised-dlg[open]").count() == 1 and await raised.get_by_role("button", name="Take D").is_enabled()


@pytest.mark.asyncio
async def test_the_pick_and_the_note_of_the_card_are_there_on_its_own_screen_and_the_answer_there_says_screen(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "image")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        await raised.locator('.pk__label[data-key="C"]').click()
        await raised.get_by_label("Note").fill("The lighthouse.")
        await raised.get_by_role("button", name="Open it on its own screen").click()
        screen = page.locator(".screen")
        await screen.locator(".pks.is-swipe").wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "pick", "ref": "logo/l1", "device": "phone", "via": "hand"})
        assert await screen.locator(".screen-title").inner_text() == "Pick one Draw the logo"
        assert await screen.locator('.pk__label[data-key="C"]').get_attribute("aria-checked") == "true" and await screen.get_by_label("Note").input_value() == "The lighthouse."
        assert await screen.get_by_role("button", name="Take C").is_enabled()
        await screen.get_by_role("button", name="Take C").click()
        assert await _called(stub, "ideas.pick", {"slug": "logo", "task": "l1", "key": "C", "note": "The lighthouse.", "via": "screen"})
        await page.locator(".screen").wait_for(state="hidden", timeout=WAIT_MS)                                         # answered: the screen is left
        await page.locator(".flash", has_text="Picked C").wait_for(timeout=WAIT_MS)


# -- the pick's own screen: one tile to a screen, swiped ----------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_own_screen_lays_the_tiles_one_to_a_screen_swiped_with_a_snap_and_the_note_and_the_two_answers_under_them(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "image")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        await raised.get_by_role("button", name="Open it on its own screen").click()
        screen = page.locator(".screen")
        strip = screen.locator(".pks.is-swipe")
        await strip.wait_for(timeout=WAIT_MS)
        await page.wait_for_function("() => [...document.querySelectorAll('.screen img')].every((i) => i.complete)", timeout=WAIT_MS)
        await page.wait_for_timeout(300)
        assert await strip.evaluate("e => { const s = getComputedStyle(e); return [s.scrollSnapType, s.overflowX]; }") == ["x mandatory", "auto"]
        sizes = await strip.evaluate("e => { const r = e.getBoundingClientRect(); return [...e.children].map((c) => [Math.round(c.getBoundingClientRect().width), Math.round(r.width), getComputedStyle(c).scrollSnapAlign]); }")
        assert all(w == full and align.startswith("start") for w, full, align in sizes) and len(sizes) == 4               # each tile is the width of the screen
        assert await strip.evaluate("e => e.scrollLeft") == 0 and await screen.locator(".pk-pips i.d").count() == 1
        box = await strip.bounding_box()
        await _swipe(page, box["x"] + 300, box["y"] + 120, -240)                                                          # a finger drags the tile away: the browser's own scroll and snap
        await page.wait_for_timeout(900)
        pitch = await strip.evaluate("e => e.children[1].offsetLeft - e.children[0].offsetLeft")
        assert await strip.evaluate("e => e.scrollLeft") == pitch                                                       # it snapped to the second tile
        assert await screen.locator(".pk-pips i").evaluate_all("els => els.map((e) => e.classList.contains('d'))") == [False, True, False, False]      # the dots follow
        # under the tiles: the note, then the two answers, in this order, all inside the screen
        ys = [(await screen.locator(s).bounding_box())["y"] for s in (".pks.is-swipe", ".pk-pips", ".pk__note", '[data-act="take"]', '[data-act="none"]')]
        assert ys == sorted(ys) and len(set(ys)) == 5 and (await screen.locator('[data-act="none"]').bounding_box())["y"] + 44 <= 844
        assert await page.evaluate(NO_SCROLL)
        await screen.locator('.pk__label[data-key="B"]').click()                                                        # a pick on the second tile, by its strip
        assert await screen.get_by_role("button", name="Take B").is_enabled()
        await _shot_to(page, "pick-own-screen")


@pytest.mark.asyncio
async def test_a_clip_plays_in_its_tile_on_the_own_screen_and_leaving_the_screen_stops_it(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "video")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        await raised.get_by_role("button", name="Open it on its own screen").click()
        screen = page.locator(".screen")
        await screen.locator(".pks.is-swipe").wait_for(timeout=WAIT_MS)
        tile = screen.locator('.pk[data-key="A"]')
        assert (await tile.get_by_role("button", name="Play").inner_text()).strip() == "Play"                           # the word shows on a screen of its own
        await tile.get_by_role("button", name="Play").click()
        await page.wait_for_function("() => document.querySelector('.screen video').currentTime > 0.1", timeout=WAIT_MS)
        assert await _playing(page) == ["A"]
        await _shot_to(page, "pick-own-screen-clip")
        await page.get_by_role("button", name="Back", exact=True).click()
        await screen.wait_for(state="hidden", timeout=WAIT_MS)
        assert await _playing(page) == []


# -- a redraw loses neither a sound, nor a drag, nor a press ------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_redraw_while_a_sound_plays_or_a_bar_is_dragged_or_a_tile_is_pressed_loses_none_of_them(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "audio")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        await page.evaluate("() => { window.__card = document.querySelector('.raised'); window.__audio = document.querySelector('.raised .pk[data-key=\"A\"] audio'); }")
        await raised.locator('.pk[data-key="A"]').get_by_role("button", name="Play").click()
        await page.wait_for_function("() => window.__audio.currentTime > 0.2", timeout=WAIT_MS)
        SCENE["map"]["nodes"][6]["tasks"][1]["state"] = "review"                                                       # the Board changes under the card: a stop's text, another result
        SCENE["needs"][0]["text"] = "Plan ready · 4 tasks"
        SCENE["needs"][-1]["at"] = "2026-10-21T11:00:00"                                                                # when it was asked is not what it shows
        await _redrawn(stub, page)
        assert await page.evaluate("() => window.__card.isConnected && window.__audio.isConnected && !window.__audio.paused")      # the same card, still playing
        # a bar dragged: the press is down while the Board changes, and the drag goes on
        bar = raised.locator('.pk[data-key="B"] .pk__bar')
        await page.wait_for_function("() => !document.querySelector('.raised .pk[data-key=\"B\"] .pk__bar').disabled", timeout=WAIT_MS)
        box = await bar.bounding_box()
        y = box["y"] + box["height"] / 2
        await page.mouse.move(box["x"] + box["width"] * 0.2, y)
        await page.mouse.down()
        SCENE["needs"][0]["text"] = "Plan ready · 5 tasks"
        SCENE["map"]["nodes"][6]["tasks"][1]["state"] = "running"
        await _redrawn(stub, page)
        assert await page.evaluate("() => window.__card.isConnected")                                                  # nothing is drawn again under the pointer
        await page.mouse.move(box["x"] + box["width"] * 0.8, y, steps=5)
        await page.mouse.up()
        await page.wait_for_function("() => document.querySelector('.raised .pk[data-key=\"B\"] audio').currentTime > 3", timeout=WAIT_MS)       # the drag sought (80 % of 5 s)
        # a press on a strip: down, the Board changes, up: the pick lands (one tap)
        strip = raised.locator('.pk__label[data-key="C"]')
        sb = await strip.bounding_box()
        await page.mouse.move(sb["x"] + 20, sb["y"] + 20)
        await page.mouse.down()
        await page.evaluate("() => { window.__strip = document.querySelector('.raised .pk__label[data-key=\"C\"]'); }")
        SCENE["map"]["nodes"][6]["tasks"][1]["state"] = "review"
        await _redrawn(stub, page)
        assert await page.evaluate("() => window.__strip.isConnected")
        await page.mouse.up()
        assert await strip.get_attribute("aria-checked") == "true" and await raised.locator('[data-act="take"]').inner_text() == "Take C"


# -- reduced motion, targets ---------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_under_reduced_motion_the_card_does_not_leap_and_nothing_plays_or_moves(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "video")
    async with _phone(fake_repo, monkeypatch, init="") as (stub, page):
        await page.emulate_media(reduced_motion="reduce")
        card = page.locator('.hc[data-kind="pick"]')
        await card.wait_for(timeout=WAIT_MS)
        raised = await _pop(page, "Pick one: Draw the logo")
        assert "is-pop" not in (await raised.get_attribute("class")) and await raised.evaluate("e => getComputedStyle(e).animationName") == "none"
        await page.wait_for_timeout(600)
        assert await _playing(page) == [] and await raised.evaluate("e => e.getAnimations({subtree: true}).length") == 0
        await raised.get_by_role("button", name="Open it on its own screen").click()
        strip = page.locator(".screen .pks.is-swipe")
        await strip.wait_for(timeout=WAIT_MS)
        assert await strip.evaluate("e => getComputedStyle(e).scrollBehavior") == "auto" and await page.evaluate("() => document.getAnimations().length") == 0


SMALL = """([root, left]) => [...root.querySelectorAll('button, input, textarea')].filter((b) => (b.offsetParent || getComputedStyle(b).position === 'fixed') && !b.closest(left))
    .map((b) => [b.className + ' ' + (b.getAttribute('aria-label') || b.textContent).slice(0, 24), Math.round(b.getBoundingClientRect().height), Math.round(b.getBoundingClientRect().width)]).filter(([, h, w]) => h < 43 || w < 43)"""


async def _small(page, root, left="[hidden]"):
    """The controls of `root` that are under 44 px on a side (what is in `left` is not asked)."""
    return await page.evaluate(SMALL, [await root.element_handle(), left])


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["image", "video", "audio", "text"])
async def test_every_target_is_44_px_and_a_tiles_strip_and_its_play_are_apart(fake_repo, monkeypatch, tmp_path, kind):
    add_pick(fake_repo, tmp_path, kind)
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        await page.wait_for_timeout(300)
        assert await _small(page, raised, "[hidden], .raised__top") == []                                                # the strips, Play, the bar, the sound switch, the note, Take, None, Open: 44 px at least
        play = raised.locator(".pk__play")
        if kind in ("audio", "video"):
            for tile in await raised.locator(".pk").all():
                strip, play = await tile.locator(".pk__label").bounding_box(), await tile.locator(".pk__play").bounding_box()
                assert await tile.locator(".pk__label .pk__play").count() == 0 and (play["y"] + play["height"] <= strip["y"] + 1)      # Play is not in the strip and does not overlap it
        else:
            assert await play.count() == 0
        box = await raised.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 390 and await page.evaluate(NO_SCROLL)
        await raised.get_by_role("button", name="Open it on its own screen").click()
        screen = page.locator(".screen")
        await screen.locator(".pks.is-swipe").wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(300)
        assert await _small(page, screen, "[hidden], .screen-head") == []


# -- the stop in the fan, the field, Today -----------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_stop_in_the_fan_wears_its_count_its_kind_and_small_tiles_and_the_raised_one_its_head_title_and_ask(fake_repo, monkeypatch, tmp_path):
    row = add_pick(fake_repo, tmp_path, "image")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        card = page.locator('.hc[data-kind="pick"]')
        await card.wait_for(timeout=WAIT_MS)
        assert await card.get_attribute("aria-label") == "Pick one: Draw the logo" and await card.locator(".ork-gem").inner_text() == "4"      # gem: the count
        assert await card.locator(".hc__kind").count() == 0 and await card.locator(".hc__thumb").count() == 0                              # a fanned card draws gem, element and banner only (spec 65 §4.3): its kind is in its label, its tiles on the raised one
        raised = await _raise(page)
        assert await raised.get_attribute("data-kind") == "pick" and await raised.locator(".raised__kind").text_content() == "Pick one"
        assert await raised.locator(".raised__top .ork-gem").inner_text() == "4" and await raised.locator(".raised__top img.ork-race__head").get_attribute("src") == "races/elf-warrior.png"
        assert await raised.locator(".banner").inner_text() == "Draw the logo" and await raised.locator(".raised__text").inner_text() == f"“{row['ask']}”"
        boxes = [await t.bounding_box() for t in await raised.locator(".pk").all()]
        assert len({round(b["x"]) for b in boxes}) == 2 and len({round(b["y"]) for b in boxes}) == 2                                      # 2 × 2
        assert [await b.inner_text() for b in await raised.locator('.raised__quick .ork-btn').all()] == ["Take the one you pick", "None of them: make new ones"]
        assert await raised.locator('[data-act="open-screen"]').inner_text() == "Open it on its own screen"
        await _shot_to(page, "pick-raised-images")


@pytest.mark.asyncio
async def test_the_raised_card_of_six_variants_scrolls_inside_the_screen_and_a_pick_that_is_gone_puts_the_card_back(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "image")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        box = await raised.bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= 844 - 56                                                   # inside the screen, over the bottom row
        SCENE["needs"] = [n for n in SCENE["needs"] if n["kind"] != "pick"]                                              # answered elsewhere (the desktop)
        stub.bump({})
        await page.locator("dialog.raised-dlg").wait_for(state="hidden", timeout=WAIT_MS * 2)
        assert await page.locator('.hc[data-kind="pick"]').count() == 0


@pytest.mark.asyncio
async def test_a_task_that_waits_for_a_pick_says_so_on_the_field_with_the_alert_sign_and_opens_the_pick(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "image")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".bands").wait_for(timeout=WAIT_MS)
        await _band(page, "build")
        deck = page.locator('.deck[data-state="picking"]')
        await deck.wait_for(timeout=WAIT_MS)
        face = deck.locator(".tcard")
        assert await face.locator(".tcard__foot").count() == 0 and await face.locator(".tcard__mark").count() == 0        # spec 65 §2.4: a token asking to pick has no value at its foot; its edge, its fill and its label say it
        assert "asks you to pick" in await deck.get_attribute("aria-label")
        alert = await face.evaluate("e => { const i = document.createElement('i'); i.style.color = 'var(--ork-alert)'; e.append(i); const c = getComputedStyle(i).color; i.remove(); return c; }")
        assert await face.evaluate("e => getComputedStyle(e).borderTopColor") != alert                                  # its sign, no alert edge (spec 52 §5.8)
        member = page.locator('button.band__face[data-member="screens"]')
        assert await member.locator(".band__sign.alert .ork-sign.alert").count() == 1                                    # its member's face: the alert sign too (spec 53 §1.2)
        await _shot_to(page, "pick-field")
        await page.locator(".gbar__head").click()                                                                        # the Goals sheet: the goal says it too
        goals = page.get_by_role("dialog", name="Goals")
        row = goals.locator('.dk[data-idea="logo"]')
        await row.wait_for(timeout=WAIT_MS)
        assert "asks you to pick" in await row.locator(".dk__line").inner_text() and await row.locator(".dk__mark .ork-sign.alert").count() == 1 and "asks" not in await row.get_attribute("class")
        await page.keyboard.press("Escape")
        await goals.wait_for(state="hidden", timeout=WAIT_MS)
        await deck.click()                                                                                              # a tap opens the pick on its own screen
        await page.locator(".screen .pks.is-swipe").wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "pick", "ref": "logo/l1", "device": "phone", "via": "map"})


@pytest.mark.asyncio
async def test_todays_rows_for_a_pick_show_an_alert_mark_and_open_it_or_its_task_once_answered(fake_repo, monkeypatch, tmp_path):
    add_pick(fake_repo, tmp_path, "image")
    open_ = {"kind": "pick", "slug": "logo", "task": "l1"}
    base = {"goal": "passkey", "idea": "logo", "task": "l1", "title": "Draw the logo", "open": open_}
    SCENE["events"] = [{**base, "at": "12:50", "mark": "!", "tone": "alert", "words": "Pick one"}, {**base, "at": "12:20", "mark": "✓", "tone": "ok", "words": "Picked B"},
                       {**base, "at": "11:30", "mark": "↺", "tone": "muted", "words": "New ones asked"}]
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        await page.locator(".gbar").wait_for(timeout=WAIT_MS)
        await page.wait_for_timeout(500)
        await _today(page)
        sheet = page.get_by_role("dialog", name="Today")
        rows = sheet.locator(".today-list .hrow")
        assert [" ".join((await r.inner_text()).split()) for r in await rows.all()] == ["Draw the logo 12:50 · Pick one", "Draw the logo 12:20 · Picked B", "↺ Draw the logo 11:30 · New ones asked"]
        assert [await r.get_attribute("data-open") for r in await rows.all()] == ["pick"] * 3
        asked = rows.first.locator(".hrow__mark")
        assert await asked.locator(".ork-sign.alert").count() == 1 and "alert" in await asked.get_attribute("class")
        alert = await page.evaluate("() => { const s = document.createElement('span'); s.style.color = 'var(--ork-alert)'; document.body.append(s); const c = getComputedStyle(s).color; s.remove(); return c; }")
        assert await asked.evaluate("e => getComputedStyle(e).color") == alert and await rows.nth(1).locator(".hrow__mark").evaluate("e => getComputedStyle(e).color") != alert      # the alert tone, a signal
        assert await rows.nth(1).locator(".ork-sign.check").count() == 1
        await _shot_to(page, "pick-today")
        await rows.first.click()                                                                                        # still waiting: its own screen
        await page.locator(".screen .pks.is-swipe").wait_for(timeout=WAIT_MS)
        assert await _called(stub, "ideas.log", {"event": "opened", "what": "pick", "ref": "logo/l1", "device": "phone", "via": "today"})
        await page.get_by_role("button", name="Back", exact=True).click()
        SCENE["needs"] = [n for n in SCENE["needs"] if n["kind"] != "pick"]                                              # answered: the row opens the task it was about
        SCENE["map"]["nodes"][-1]["tasks"][0].update(state="review", pick=None)
        stub.bump({})
        await page.wait_for_function("() => !document.querySelector('.hc[data-kind=\"pick\"]')", timeout=WAIT_MS * 2)
        await _today(page)
        await rows.nth(1).click()
        screen = page.locator(".screen")
        await screen.get_by_text("Brief of Draw the logo").wait_for(timeout=WAIT_MS)
        assert await screen.locator(".pks").count() == 0 and "at Review" in await screen.locator("dd[data-state='review']").inner_text()


# -- the service worker ---------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_service_worker_does_not_answer_for_media_and_never_keeps_it(fake_repo, monkeypatch, tmp_path):
    """The worker's own file run with a stand-in for its scope: a fetch of `/media/…` is let go (the browser asks the town, with its Range), one of the app's files is answered; nothing of
    a pick is in its cache after the tiles loaded."""
    row = add_pick(fake_repo, tmp_path, "audio")
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        raised = await _raise(page)
        source = await page.evaluate("async () => (await (await fetch('sw.js', { cache: 'no-store' })).text())")
        got = await page.evaluate("""(src) => {
            const listeners = {}, box = { location: { origin: location.origin, href: location.origin + '/app/sw.js' }, addEventListener: (t, f) => { listeners[t] = f; }, clients: {}, registration: {} };
            new Function('self', 'caches', 'fetch', 'Response', 'Headers', src)(box, { open: async () => ({ match: async () => undefined, put: async () => {} }), keys: async () => [], match: async () => undefined }, async () => new Response('x'), Response, Headers);
            const ask = (path, method = 'GET') => { let answered = false; listeners.fetch({ request: { url: location.origin + path, method }, respondWith: () => { answered = true; } }); return answered; };
            return { media: ask('/media/logo/l1-r1/a.wav?s=0123456789abcdef0123456789abcdef'), range: ask('/media/logo/l1-r1/a.wav'), app: ask('/app/util.js'), elsewhere: ask('/other') };
        }""", source)
        assert got == {"media": False, "range": False, "app": True, "elsewhere": False}
        url = row["variants"][0]["url"]
        assert await page.evaluate("async (u) => { const r = await fetch(u, { headers: { Range: 'bytes=0-9' } }); return [r.status, (await r.arrayBuffer()).byteLength]; }", url) == [206, 10]     # the town's own Range answer
        kept = await page.evaluate("async () => { const out = []; if (typeof caches === 'undefined') return out; for (const k of await caches.keys()) for (const r of await (await caches.open(k)).keys()) out.push(new URL(r.url).pathname); return out; }")
        assert not [p for p in kept if p.startswith("/media/")], kept
        assert await page.evaluate("() => { const e = document.querySelector('.raised audio'); return e && e.getAttribute('src').startsWith('/media/'); }")
