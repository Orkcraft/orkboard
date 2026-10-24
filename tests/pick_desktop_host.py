"""The stub host of the Pick one tests on the desktop (tests/test_pick_desktop_browser.py): the one window's stub (tests/test_arena_desktop_browser.py) with a task
that made variants and waits for a pick (docs/specs/51-pick-one.md §2.4: the Needs you row of kind `pick`, the map's task `picking`, today's rows, `ideas.pick`),
and the files of the variants it serves to the page: a PNG, an SVG, a WAV, a tiny WEBM and texts, by `page.route` on `/media/` (`Range` answered as the host does)."""
from __future__ import annotations

import base64
import re
import struct
import zlib

from tests import pick_files as pf
from tests.browser_kit import WAIT_MS
from tests.test_arena_desktop_browser import ELF, ArenaHost, member, pip
from tests.test_map_desktop_browser import node

ASK = "Four marks for the passkey button. Which one goes on the sign-in page?"
NAMES = ["anchor", "monogram", "lighthouse", "compass", "wave", "star"]
ANSWER = "A note says what to change: write one first"
# a clip of 32 × 24 px and 3 s (a solid colour, VP8; ffmpeg made it once, 725 bytes): the page plays it for real
CLIP = base64.b64decode(
    "GkXfo59ChoEBQveBAULygQRC84EIQoKEd2VibUKHgQJChYECGFOAZwEAAAAAAAKlEU2bdLpNu4tTq4QVSalmU6yBoU27i1OrhBZU"
    "rmtTrIHYTbuMU6uEElTDZ1OsggEeTbuMU6uEHFO7a1OsggKP7AEAAAAAAABZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVSalmsirXsYMPQkBNgI1M"
    "YXZmNjAuMTYuMTAwV0GNTGF2ZjYwLjE2LjEwMESJiECncAAAAAAAFlSua8GuAQAAAAAAADjXgQFzxYhkpB3uHtcuKZyBACK1nIN1"
    "bmSIgQCGhVZfVlA4g4EBI+ODhB3NZQDgibCBILqBGJqBAhJUw2f8c3OgY8CAZ8iaRaOHRU5DT0RFUkSHjUxhdmY2MC4xNi4xMDBz"
    "c9ZjwItjxYhkpB3uHtcuKWfIoUWjh0VOQ09ERVJEh5RMYXZjNjAuMzEuMTAyIGxpYnZweGfIoUWjiERVUkFUSU9ORIeTMDA6MDA6"
    "MDMuMDAwMDAwMDAwAB9DtnVA6ueBAKO5gQAAgNACAJ0BKiAAGAAAxwiFhYiFhIgEggJ1qgP4AgghKZ5w/vnnA/9QZ8gz5Bn6qX/y"
    "C5YXXEYAo6KBAfQAEQIACxFgABgHb/A/8uaZgIviAP7guUrDkK4whdugo6CBA+gA0QEACxFgABgAHlf0DABBDgD+4LlKw5CuMIXb"
    "oKOggQXcANEBAAsRYAAYAB5X9AwAQQ4A/uC5SsOQrjCF26CjoIEH0ADRAQALEWAAGAAeV/QMAEEOAP7guUrDkK4whdugo6CBCcQA"
    "0QEACxFgABgAHlf0DABBDgD+4LlKw5CuMIXboBxTu2uRu4+zgQC3iveBAfGCAZ/wgQM=")


def _png(w: int, h: int, paint) -> bytes:
    """A PNG of w × h pixels, `paint(x, y)` its colour."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = b"".join(b"\x00" + b"".join(bytes(paint(x, y)) for x in range(w)) for y in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def _mark(shape: int, ink: tuple[int, int, int]):
    """A 16 × 16 mark in one colour on a dark ground: a diamond, a ring, a square or a plus."""
    def paint(x: int, y: int):
        dx, dy = abs(x - 7.5), abs(y - 7.5)
        on = [dx + dy <= 6, 4 <= max(dx, dy) <= 6.5, max(dx, dy) <= 5, min(dx, dy) <= 1.5 and max(dx, dy) <= 6.5][shape % 4]
        return ink if on else (16, 24, 40)
    return paint


INKS = [(106, 150, 255), (127, 191, 154), (212, 183, 122), (190, 130, 240), (240, 208, 80), (245, 128, 110)]
SVG = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 36"><rect width="48" height="36" fill="#8e88a8"/></svg>'


class PickHost(ArenaHost):
    """The passkey party with a task that made variants and waits for a pick: a goal at work whose task is `picking`, the Needs you row of kind `pick` (the shape
    of docs/specs/51-pick-one.md §2.4 as part A sends it), today's rows of it, and `ideas.pick` as the host answers it."""

    def __init__(self, media: str = "image", n: int = 4, sizes: list[tuple[int, int]] | None = None):
        super().__init__()
        self.media, self.n, self.sizes, self.round, self.waits = media, n, sizes or [], 1, True
        task = pip("p1", "Draw the mark", "picking", by="screens") | {"short": "Mark", "pick": {"n": n, "media": media, "round": 1}}
        self.nodes.append(node("logo", "passkey", "A mark for the passkey button", "working", 1, stage="implementation", tasks=[task], progress={"done": 0, "total": 1}, usd=0.4,
                               waits={"kind": "you", "ref": "", "title": "", "until": ""}, element="void", flag=None, plan_estimate={"usd_low": 0.2, "usd_high": 0.5}))
        self.ideas["logo"] = self.idea("logo", "A mark for the passkey button", "working", 9, track="passkey")
        self.party["passkey"] = [(member("screens", "Screens", ELF, "build", "needs", "pick") if m["slug"] == "screens" else m) for m in self.party["passkey"]]
        self.files = {}
        self.today_events.insert(0, {"at": "13:05", "mark": "!", "tone": "alert", "words": "Pick one", "title": "Draw the mark", "goal": "passkey", "idea": "logo", "task": "p1",
                                     "open": {"kind": "pick", "slug": "logo", "task": "p1"}})

    # -- the pick ------------------------------------------------------------------------------------------------------------------------

    def variants(self) -> list[dict]:
        out = []
        for i in range(self.n):
            key, name = "ABCDEF"[i], NAMES[i]
            v = {"key": key, "name": name, "why": f"{name}, because it is simple", "w": None, "h": None, "seconds": None}
            path = f"/media/logo/p1-r{self.round}/{key.lower()}"
            if self.media == "image":
                w, h = self.sizes[i] if i < len(self.sizes) else (16, 16)
                svg = (w, h) == (0, 0)
                ext, mime, data = ("svg", "image/svg+xml", SVG) if svg else ("png", "image/png", _png(w, h, _mark(i, INKS[i])))
                v |= {"w": None if svg else w, "h": None if svg else h}
            elif self.media == "audio":
                ext, mime, data = "wav", "audio/wav", pf.wav(2.0)
                v |= {"seconds": 2.0}
            elif self.media == "video":
                ext, mime, data = "webm", "video/webm", CLIP
                v |= {"w": 32, "h": 24, "seconds": None if i == 0 else 3.0}
            else:
                ext, mime = "txt", "text/plain"
                text = ["Passkeys, without the password.", "Your face is the key.\nYour phone is the door.", "Sign in, and nothing else.", "No more passwords: a touch and you are in."][i % 4]
                data = text.encode()
                v |= {"text": text}
            self.files[f"{key.lower()}.{ext}"] = (data, mime)
            out.append(v | {"url": f"{path}.{ext}?s={'0' * 31}{i}", "mime": mime})
        return out

    def row(self) -> dict:
        return {"kind": "pick", "slug": "logo", "idea": "logo", "goal": "passkey", "task": "p1", "title": "Draw the mark", "short": "Mark", "idea_title": "A mark for the passkey button",
                "priority": "high", "blocks": True, "by": {"slug": "screens", "name": "Screens", "head": ELF}, "ask": ASK, "n": self.n, "media": self.media, "round": self.round,
                "at": "2026-10-21T13:05:00", "variants": self.variants()}

    def needs_you(self):
        return [*([self.row()] if self.waits else []), *super().needs_you()]

    def handle(self, name, a):
        if name == "ideas.pick":
            self.log.append((name, a))
            if a.get("key") is None and not str(a.get("note", "")).strip():
                return {"error": ANSWER}
            task = next(n for n in self.nodes if n["slug"] == "logo")["tasks"][0]
            if a.get("key") is None:                                       # none of them: the task goes again as its next round
                self.round += 1
                task["pick"]["round"] = self.round
            else:
                self.waits, task["state"], task["pick"] = False, "running", None
            return self.bump({"ok": True})
        return super().handle(name, a)

    def serve(self, route):
        """The files of the pick, by their address's last name (a real `Range` answered as the host does: 206)."""
        name = route.request.url.split("?")[0].rsplit("/", 1)[1]
        if name not in self.files:
            route.fulfill(status=404, body="")
            return
        body, mime = self.files[name]
        got = route.request.headers.get("range")
        head = {"Content-Type": mime, "Accept-Ranges": "bytes", "Cache-Control": "private, max-age=31536000, immutable"}
        span = re.fullmatch(r"bytes=(\d+)-(\d*)", got or "")
        if span:
            start, end = int(span[1]), min(int(span[2] or len(body) - 1), len(body) - 1)
            route.fulfill(status=206, body=body[start:end + 1], headers=head | {"Content-Range": f"bytes {start}-{end}/{len(body)}"})
        else:
            route.fulfill(status=200, body=body, headers=head)


def open_pick(gui, host, viewport=None, reduced=False):
    """The window against the stub, its media served from the stub; the party with the pick shown. (pg, host, errors)"""
    server, browser = gui
    pg = browser.new_page(viewport=viewport or {"width": 1440, "height": 900}, reduced_motion="reduce" if reduced else "no-preference")
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
    pg.route_web_socket("**/ws*", host.on_socket)
    pg.route("**/media/**", host.serve)
    pg.goto(server.url)
    pg.wait_for_selector(".arena-phead", timeout=WAIT_MS)
    pg.locator(".arena[data-goal=passkey]").wait_for(timeout=WAIT_MS)
    pg.locator(".arena-hc[data-kind=pick]").wait_for(timeout=WAIT_MS)
    return pg, host, errors
