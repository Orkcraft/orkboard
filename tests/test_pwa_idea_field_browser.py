"""New idea's field on the phone (shell-idea-field.js): the goal's words to complete with, Photo and Speak, in Chromium at
390 x 844. The Board is the stub's (tests/test_pwa_shell_browser.py); the browser's speech to text is stood in."""
from __future__ import annotations

import base64
import struct
import zlib

import pytest

from tests.test_pwa_shell_browser import NO_SCROLL, WAIT_MS, _called, _dial, _phone, _pick_goal, _shot  # noqa: F401

pytestmark = pytest.mark.browser

# The browser's speech to text, stood in: start() hears two phrases, the second one final, then it ends.
SPEECH = """
window.SpeechRecognition = class {
  start() {
    window.__heard = this;
    const said = (parts, final) => ({ results: parts.map((t) => Object.assign([{ transcript: t }], { isFinal: final })) });
    setTimeout(() => this.onresult?.(said(["fix the"], false)), 20);
    setTimeout(() => this.onresult?.(said(["fix the", " sync queue"], true)), 60);
  }
  stop() { setTimeout(() => this.onend?.(), 10); }
};
"""


def _png(w: int = 40, h: int = 30) -> bytes:
    rows = b"".join(b"\x00" + b"\x80\x40\x20" * w for _ in range(h))
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))   # noqa: E731
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


async def _new_idea(stub, page):
    stub.goals["ship"] = stub.goal("ship", "Ship v1", "normal", "ready")
    stub.bump({})
    await _pick_goal(page, "ship")                                                                      # the goal is on the phone and shown
    await _dial(page, "New idea")                                                                       # the create button's first item
    sheet = page.get_by_role("dialog", name="New idea")
    await sheet.wait_for(timeout=WAIT_MS)
    assert await _called(stub, "ideas.words", {"track": "ship"})
    return sheet


@pytest.mark.asyncio
async def test_the_goal_s_words_complete_the_one_being_typed_and_a_tap_puts_it_in_with_a_space(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _new_idea(stub, page)
        text = sheet.get_by_label("The idea", exact=True)
        words = sheet.locator(".idea-words")
        await text.press_sequentially("Make o")
        assert await words.is_hidden()                                                                  # one letter: nothing yet
        await text.press_sequentially("f")
        await words.get_by_role("button").first.wait_for(timeout=WAIT_MS)
        assert await words.get_by_role("button").all_inner_texts() == ["Offline mode", "offline"]       # the titles first, case aside
        await words.get_by_role("button", name="Complete with Offline mode").click()
        assert await text.input_value() == "Make Offline mode "
        assert await page.evaluate("document.activeElement.getAttribute('aria-label')") == "The idea"   # the keyboard stays up
        assert await words.is_hidden()
        await text.press_sequentially("use sync")
        await words.get_by_role("button", name="Complete with sync_queue.py").click()
        assert await text.input_value() == "Make Offline mode use sync_queue.py "
        await _shot(page, "phone-idea-words-390x844")
        assert await page.evaluate(NO_SCROLL)


@pytest.mark.asyncio
async def test_photo_attaches_a_shrunk_jpeg_that_goes_with_the_idea_and_one_can_be_removed(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch) as (stub, page):
        sheet = await _new_idea(stub, page)
        await sheet.get_by_label("The idea", exact=True).fill("The login screen is cut off")
        assert await sheet.get_by_role("button", name="Photo").is_visible()
        await sheet.get_by_label("Photos to attach").set_input_files([
            {"name": "a.png", "mimeType": "image/png", "buffer": _png()}, {"name": "b.png", "mimeType": "image/png", "buffer": _png(20, 20)}])
        await sheet.locator(".idea-photo img").nth(1).wait_for(timeout=WAIT_MS)
        await sheet.get_by_role("button", name="Remove photo 2").click()
        assert await sheet.locator(".idea-photo").count() == 1
        await _shot(page, "phone-idea-photo-390x844")
        await sheet.get_by_role("button", name="Add").click()
        await sheet.wait_for(state="hidden", timeout=WAIT_MS)
        added = [a for n, a in stub.calls if n == "ideas.add"][-1]
        assert added["text"] == "The login screen is cut off" and len(added["photos"]) == 1
        assert base64.b64decode(added["photos"][0]["data"])[:3] == b"\xff\xd8\xff"                     # made a JPEG on the phone
        await _dial(page, "New idea")
        assert await sheet.locator(".idea-photo").count() == 0                                          # a new idea starts with none


@pytest.mark.asyncio
async def test_speak_puts_the_words_heard_in_at_the_caret_and_stops(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init=SPEECH) as (stub, page):
        sheet = await _new_idea(stub, page)
        text = sheet.get_by_label("The idea", exact=True)
        await text.fill("Please")
        speak = sheet.get_by_role("button", name="Speak the idea")
        assert "keyboard’s microphone" not in await sheet.locator(".hint").inner_text()                 # Speak is here: no need to say it
        assert await speak.locator("use").get_attribute("href") == "icons/icons.svg#mic"                # the mic mark, in the field's corner
        mic, field = await speak.bounding_box(), await text.bounding_box()
        assert field["x"] + field["width"] - mic["x"] - mic["width"] < 4 and field["y"] + field["height"] - mic["y"] - mic["height"] < 4
        await speak.click()
        stop = sheet.get_by_role("button", name="Stop speaking")
        assert await stop.get_attribute("aria-pressed") == "true"
        for _ in range(100):
            if await text.input_value() == "Please fix the sync queue":
                break
            await page.wait_for_timeout(20)
        assert await text.input_value() == "Please fix the sync queue"
        await stop.click()
        await speak.wait_for(timeout=WAIT_MS)
        assert await speak.get_attribute("aria-pressed") == "false"


@pytest.mark.asyncio
async def test_without_speech_to_text_the_mic_is_not_there_and_the_hint_says_the_keyboard_s(fake_repo, monkeypatch):
    async with _phone(fake_repo, monkeypatch, init="delete window.SpeechRecognition; delete window.webkitSpeechRecognition;") as (stub, page):
        sheet = await _new_idea(stub, page)
        assert await sheet.locator(".idea-mic").is_hidden() and "Speak it with the keyboard’s microphone" in await sheet.locator(".hint").inner_text()
        assert await page.get_by_role("button", name="Speak a new idea").count() == 0                   # Speak left the Board (spec 41 §5)
