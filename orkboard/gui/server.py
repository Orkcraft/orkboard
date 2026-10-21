"""The GUI's server: the page, the design system and one WebSocket, on 127.0.0.1 only.

One asyncio loop runs it and the host (`gui/host.py`): the town lives on this loop's thread. The
page gets a snapshot of the town whenever it changes (at most every `FLUSH_S`, and only when it
differs from the last one), toasts as they come, and sends commands back:

    → {"t": "cmd", "id": 7, "name": "hut.move", "args": {"id": "lake", "x": 0.4, "y": 0.2}}
    ← {"t": "reply", "id": 7, "ok": true, "result": null}      (or "ok": false, "error": "...")
    ← {"t": "state", "state": {...}}                             (gui/state.py)
    ← {"t": "toast", "message": "...", "title": "...", "severity": "information", "timeout": null}
    → {"t": "cmd", "id": 8, "name": "watch", "args": {"ids": ["lake"]}}   (the buildings open in the page)
    ← {"t": "detail", "detail": {"id": "lake", "type": "lake", "ui": {...}, "data": {...}}}

A building's own state (`detail`, gui/views/) goes only to the pages that have it open, when its
worker says it changed.

A session's bytes go as binary frames, only to the pages that show it (`term.attach`):

    → {"t": "cmd", "id": 9, "name": "term.attach", "args": {"keys": ["new:claude:1"]}}   (all it shows)
    → {"t": "cmd", "id": 10, "name": "term.replay", "args": {"key": "new:claude:1"}}      (a terminal opened)
    ← [kind: 1 byte][key length: 1 byte][key, UTF-8][bytes]    kind 0: output, 1: all of it again (replay)

The socket takes only the page this server gave out: a random token in its address and an Origin
of this server, so another page open in a browser cannot drive the town.

`GET /api/version` (the same token, as `?t=` or `Authorization: Bearer`) is the handshake a client
other than the page makes first (docs/design/mobile.md): what this server speaks, as JSON.

    ← {"name": "orkcraft", "version": "0.1.0", "protocol": 1, "api": 1}

`GET /media/<goal>/<pick-id>/<file>?s=<signature>` is a pick's file (gui/media.py, spec 51 §3): the address is signed by the host
and is the proof, so it needs no token and an `<img>`, `<audio>` or `<video>` loads it; Range is served (206).

`GET /api/analytics?days=7` (the same token) is the day logs of the last days, with what each day added up to, as one
zip (realm/analytics.py, the host's `day_logs`).

Orkboard's (spec 37 §4): it serves whichever host it is given, Orkboard's own (gui/board_host.py) or Orkline's
(gui/host.py). A host may name the page's script (`entry`) and hand the server its own part (`serve(server)`):
Orkline's adds the town's routes (an Audio briefing's episode, a building's day log, a Test bench's runs, the last
check), its terminals' bytes, its building windows' preview and the phones' news (gui/server_town.py).
"""
from __future__ import annotations

import asyncio
import json
import mimetypes
import secrets
import threading
from http import HTTPStatus
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, quote, urlsplit

from websockets.asyncio.server import ServerConnection, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

from orkboard import __version__
from orkboard.design import tokens
from orkboard.gui import media, phones, pwa
from orkboard.gui.board_host import CommandError

STATIC = Path(__file__).with_name("static")
TICK_S = 1.0
FLUSH_S = 0.05
ROUTES = {"/static/": STATIC, "/ds/": tokens.SYSTEM}
PROTOCOL = 1            # the socket's messages above: a change that breaks a client raises it
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("image/webp", ".webp")


def _response(status: HTTPStatus, body: bytes, content_type: str = "text/plain; charset=utf-8") -> Response:
    headers = Headers([("Content-Type", content_type), ("Content-Length", str(len(body))),
                       ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")])
    return Response(status.value, status.phrase, headers, body)


def resolve(path: str, preview: Path | None = None) -> Path | None:
    """The file a static path names, never one outside its folder; a design-system picture this machine has its own
    of (a UX bench applied it, design/tokens.py `assets_dir`) is that one; with a fix's page in preview (gui/fixes.py),
    its copy's file first."""
    if preview is not None and path.startswith("/static/"):
        page = preview.resolve()
        mine = (page / path[len("/static/"):]).resolve()
        if mine.is_file() and mine.is_relative_to(page):
            return mine
    if path.startswith("/ds/sprites/"):
        own = tokens.assets_dir().resolve()
        mine = (own / path[len("/ds/"):]).resolve()
        if mine.is_file() and mine.is_relative_to(own):
            return mine
    for prefix, root in ROUTES.items():
        if path.startswith(prefix):
            root = root.resolve()
            target = (root / path[len(prefix):]).resolve()
            if target.is_file() and target.is_relative_to(root):
                return target
    return None


class Server:
    def __init__(self, host, port: int = 0) -> None:
        self.host = host
        self.port = port
        self.token = secrets.token_urlsafe(24)
        self.clients: set[ServerConnection] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.ready = threading.Event()
        self._stop: asyncio.Event | None = None
        self._last = ""
        self._dirty = False
        self.watching: dict[ServerConnection, set[str]] = {}
        self._details: set[str] = set()             # buildings whose detail waits to be sent
        self._sent: dict[tuple[int, str], str] = {}  # (page, building) → the detail it has
        self.attached: dict[ServerConnection, set[str]] = {}
        # What a host adds (gui/server_town.py): routes by path (a prefix ends in "/"), and the page of a fix in preview
        self.routes: dict[str, Callable[[Request, str], Response]] = {}
        self.preview: Callable[[], Path | None] = lambda: None
        host.on_change = self._changed
        host.on_detail = self._detail_changed
        host.on_toast = lambda data: self._send_all({"t": "toast", **data})
        # The listener for phones (gui/phones.py): on the LAN, TLS, a device token; only while one is paired.
        self.phones = phones.Listener(host)
        host.commands.update(self.phones.commands())
        self.tail_watch = pwa.TailWatch(self.phones)   # Tailscale that came after the town (gui/pwa.py)
        host.commands.update(pwa.commands(self.phones))   # the app in a phone's browser: Tailscale's state
        serve = getattr(host, "serve", None)
        if serve is not None:
            serve(self)

    def _preview(self) -> Path | None:
        """The page of the fix shown in preview (gui/fixes.py, through the host's `serve`), or None."""
        try:
            return self.preview()
        except Exception:
            return None

    def capture(self, e: BaseException, where: str, **kw) -> None:
        """An error the server caught, to the host's crash reports (Orkline's, core/crashes.py), when it keeps them."""
        capture = getattr(self.host, "capture", None)
        if capture is not None:
            capture(e, where, **kw)

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def url(self) -> str:
        return f"{self.origin}/?t={self.token}"

    # -- HTTP ----------------------------------------------------------------------------------

    def _token_ok(self, request: Request) -> bool:
        """The server's token, from the address (`?t=`) or an `Authorization: Bearer` header."""
        token = parse_qs(urlsplit(request.path).query).get("t", [""])[0]
        auth = request.headers.get("Authorization", "")
        if not token and auth.startswith("Bearer "):
            token = auth.removeprefix("Bearer ").strip()
        return bool(token) and secrets.compare_digest(token, self.token)

    def version(self) -> dict:
        return {"name": "orkcraft", "version": __version__, "protocol": PROTOCOL, "api": phones.API}

    def _http(self, connection: ServerConnection, request: Request) -> Response | None:
        parts = urlsplit(request.path)
        if parts.path == "/ws":
            token = parse_qs(parts.query).get("t", [""])[0]
            origin = request.headers.get("Origin", "")
            if not secrets.compare_digest(token, self.token) or origin != self.origin:
                return _response(HTTPStatus.FORBIDDEN, b"Forbidden")
            return None                                   # go on with the WebSocket handshake
        if parts.path == "/api/version":
            if not self._token_ok(request):
                return _response(HTTPStatus.FORBIDDEN, b"Forbidden")
            return _response(HTTPStatus.OK, json.dumps(self.version()).encode(), "application/json")
        if parts.path.startswith(media.PREFIX):                  # a pick's files, by a signed address (spec 51 §3): no token, the address is the proof
            return self._media(request)
        if parts.path == "/api/analytics":
            if not self._token_ok(request):
                return _response(HTTPStatus.FORBIDDEN, b"Forbidden")
            days = parse_qs(parts.query).get("days", ["7"])[0]
            return self._zip(self.host.day_logs.pack_period(int(days) if days.isdigit() else 7))
        for route, answer in self.routes.items():
            if parts.path == route or (route.endswith("/") and parts.path.startswith(route)):
                return answer(request, parts.path.removeprefix(route) if route.endswith("/") else "")
        preview = self._preview()
        if parts.path in ("/", "/index.html"):
            page = preview / "index.html" if preview is not None and (preview / "index.html").is_file() else None
            return _response(HTTPStatus.OK, page.read_bytes() if page else self.page(), "text/html; charset=utf-8")
        if parts.path == "/favicon.ico":                  # the ork mark (design-system/logo)
            return _response(HTTPStatus.OK, (tokens.SYSTEM / "logo" / "favicon.ico").read_bytes(), "image/x-icon")
        if parts.path == "/roles.css":
            return _response(HTTPStatus.OK, tokens.roles_css().encode(), "text/css; charset=utf-8")
        target = resolve(parts.path, preview)
        if target is None:
            return _response(HTTPStatus.NOT_FOUND, b"Not found")
        kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if kind.startswith("text/") or kind.endswith(("javascript", "json")):
            kind += "; charset=utf-8"
        return _response(HTTPStatus.OK, target.read_bytes(), kind)

    def _media(self, request: Request) -> Response:
        """A file of a pick (gui/media.py): 200, 206 for a range, 416, or 404 for anything wrong."""
        reply = media.serve("GET", request.path, request.headers.get("Range", ""), media.state_dirs(self.host))
        return Response(reply.status, HTTPStatus(reply.status).phrase, Headers(reply.headers), reply.read())

    @staticmethod
    def _zip(packed: tuple[str, bytes] | None) -> Response:
        """A zip to download (a day log, a Test bench's runs); 404 when there is nothing of that name."""
        if packed is None:
            return _response(HTTPStatus.NOT_FOUND, b"Not found")
        name, data = packed
        resp = _response(HTTPStatus.OK, data, "application/zip")
        resp.headers["Content-Disposition"] = f'attachment; filename="{quote(name)}"'
        return resp

    def page(self) -> bytes:
        """The page: `static/index.html`, its script the host's `entry` when it names one (Orkboard's `board.js`, in
        Office's look from the first paint: no camp file is asked for before the script runs)."""
        html = (STATIC / "index.html").read_bytes()
        entry = getattr(self.host, "entry", "")
        if entry:
            html = html.replace(b'src="/static/app.js"', f'src="/static/{entry}"'.encode()) \
                       .replace(b'data-theme="camp" data-look="camp"', b'data-theme="office" data-look="office"')
        return html

    # -- the socket ----------------------------------------------------------------------------

    async def _client(self, ws: ServerConnection) -> None:
        self.clients.add(ws)
        try:
            await ws.send(json.dumps({"t": "state", "state": self.host.snapshot()}, ensure_ascii=False))
            async for raw in ws:
                await ws.send(json.dumps(self._handle(raw, ws), ensure_ascii=False))
        except ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)
            self.watching.pop(ws, None)
            self.attached.pop(ws, None)
            self._sent = {k: v for k, v in self._sent.items() if k[0] != id(ws)}

    def _watch(self, ws: ServerConnection | None, args: dict) -> list[str]:
        """The buildings this page has open: each one's detail now, and again when it changes."""
        ids = [str(x) for x in (args.get("ids") or [])][:50]
        if ws is not None:
            self.watching[ws] = set(ids)
            for bid in ids:
                self._send_detail(ws, bid, force=True)
        return ids

    @staticmethod
    def frame(kind: int, key: str, data: bytes) -> bytes:
        k = key.encode("utf-8")[:255]
        return bytes([kind, len(k)]) + k + data

    def _attach(self, ws: ServerConnection | None, args: dict) -> list[str]:
        """The sessions this page shows: their bytes as they come."""
        keys = [str(x) for x in (args.get("keys") or [])][:20]
        if ws is not None:
            self.attached[ws] = set(keys)
        return keys

    def _replay(self, ws: ServerConnection | None, args: dict) -> bool:
        """A terminal opened on the page: the session as it stands now, then its bytes as they come."""
        key = str(args.get("key") or "")
        sessions = getattr(self.host, "sessions", None)
        s = sessions.get(key) if sessions is not None else None
        if ws is None or s is None:
            return False
        self.attached.setdefault(ws, set()).add(key)
        asyncio.ensure_future(self._send(ws, self.frame(1, key, s.replay())))
        return True

    def _output(self, key: str, data: bytes) -> None:
        frame = None
        for ws, keys in list(self.attached.items()):
            if key in keys:
                frame = frame or self.frame(0, key, data)
                asyncio.ensure_future(self._send(ws, frame))

    def _send_detail(self, ws: ServerConnection, bid: str, force: bool = False) -> None:
        detail = self.host.detail(bid)
        if detail is None:
            return
        text = json.dumps({"t": "detail", "detail": detail}, ensure_ascii=False)
        key = (id(ws), bid)
        if force or self._sent.get(key) != text:
            self._sent[key] = text
            asyncio.ensure_future(self._send(ws, text))

    def _detail_changed(self, bid: str) -> None:
        if self.loop is None or not any(bid in ids for ids in self.watching.values()):
            return
        if not self._details:
            self.loop.call_later(FLUSH_S, self._flush_details)
        self._details.add(bid)

    def _flush_details(self) -> None:
        bids, self._details = self._details, set()
        for ws, ids in list(self.watching.items()):
            for bid in bids & ids:
                self._send_detail(ws, bid)

    def _handle(self, raw: str | bytes, ws: ServerConnection | None = None) -> dict:
        try:
            msg = json.loads(raw)
            cid = msg.get("id")
        except (ValueError, AttributeError):
            return {"t": "reply", "id": None, "ok": False, "error": "Not a command"}
        if msg.get("t") != "cmd":
            return {"t": "reply", "id": cid, "ok": False, "error": "Not a command"}
        try:
            name, args = str(msg.get("name", "")), msg.get("args") or {}
            if not isinstance(args, dict):
                raise CommandError("Arguments are an object")
            if name == "watch":
                result = self._watch(ws, args)
            elif name == "term.attach":
                result = self._attach(ws, args)
            elif name == "term.replay":
                result = self._replay(ws, args)
            else:
                args.pop("device_id", None)                 # a paired phone's to say (`BoardPhone.guard`), never the page's
                if name.startswith(("ideas.", "ops.", "projects.", "files.")) or name == "halt":
                    args.pop("link", None)                  # (the onboarding's `link` is a person's own words)
                result = self.host.command(name, args)
            return {"t": "reply", "id": cid, "ok": True, "result": result}
        except CommandError as e:
            return {"t": "reply", "id": cid, "ok": False, "error": str(e)}
        except Exception as e:                            # a broken command never closes the page
            known = str(msg.get("name", ""))
            self.capture(e, "command", command=known if known in self.host.commands else "")
            return {"t": "reply", "id": cid, "ok": False, "error": f"{type(e).__name__}: {e}"}

    def _send_all(self, msg: dict) -> None:
        text = json.dumps(msg, ensure_ascii=False)
        for ws in list(self.clients):
            asyncio.ensure_future(self._send(ws, text))

    @staticmethod
    async def _send(ws: ServerConnection, text: str | bytes) -> None:
        try:
            await ws.send(text)
        except ConnectionClosed:
            pass

    def _changed(self) -> None:
        """The town changed: flush a snapshot soon (many changes in one moment make one send)."""
        if self._dirty or self.loop is None:
            return
        self._dirty = True
        self.loop.call_later(FLUSH_S, self._flush)

    def _flush(self) -> None:
        self._dirty = False
        if not self.clients:
            return
        text = json.dumps({"t": "state", "state": self.host.snapshot()}, ensure_ascii=False)
        if text != self._last:
            self._last = text
            for ws in list(self.clients):
                asyncio.ensure_future(self._send(ws, text))

    # -- its life ------------------------------------------------------------------------------

    async def _ticker(self) -> None:
        while True:
            await asyncio.sleep(TICK_S)
            try:
                self.host.tick()
                self.phones.tick()
                self.tail_watch.tick()
            except Exception as e:
                self.capture(e, "clock")
                self.host.town.toast(f"{type(e).__name__}: {e}", title="Town clock", severity="error")

    async def run(self) -> None:
        self.loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        self.host.town.call = lambda fn, *a: self.loop.call_soon_threadsafe(fn, *a)
        reporter = getattr(self.host, "crashes", None)
        if reporter is not None:
            self.loop.set_exception_handler(reporter.asyncio_handler)   # a task's error nobody awaited
        async with serve(self._client, "127.0.0.1", self.port, process_request=self._http,
                         max_size=8 * 2**20) as server:
            self.port = server.sockets[0].getsockname()[1]
            ticker = asyncio.create_task(self._ticker())
            self._phones_start()
            self.ready.set()
            await self._stop.wait()
            ticker.cancel()
            self.phones.stop()
        self.host.close()

    def _phones_start(self) -> None:
        """A machine with a paired phone listens for it from the start."""
        try:
            if self.phones.wanted():
                self.phones.start()
        except phones.PhoneError as e:
            self.host.town.toast(str(e), title="Phones", severity="warning")

    def stop(self) -> None:
        """Ask the server to stop; once it has, asking again does nothing (its loop is closed by then)."""
        if self.loop is not None and self._stop is not None and not self.loop.is_closed():
            try:
                self.loop.call_soon_threadsafe(self._stop.set)
            except RuntimeError:                 # it closed between the look and the call
                pass

    def start_thread(self) -> threading.Thread:
        """Serve on a thread of its own (the window takes the main thread); returns once it listens."""
        t = threading.Thread(target=lambda: asyncio.run(self.run()), name="orkcraft-gui", daemon=True)
        t.start()
        self.ready.wait(10)
        return t
