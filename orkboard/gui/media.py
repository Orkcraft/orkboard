"""The files of a pick, served (docs/specs/51-pick-one.md §3): `GET /media/<goal>/<pick-id>/<file>?s=<signature>` on the page's server
(gui/server.py) and on the phones' listener (gui/phones.py). An `<img>`, an `<audio>` or a `<video>` loads it without a header, so
the address carries its proof: an HMAC of the path with a secret this process makes for its life. The host signs every `url` it
sends (`url()`, gui/ideas_pick.py), and nothing but what the paired faces were given can be fetched. No signature, a wrong one, a name
with `/` or `..`, a file the pick does not list, or a path of another pick: 404.

    media.url("dark-mode", "k1-r1", "b.png")     # "/media/dark-mode/k1-r1/b.png?s=3fa9…"
    reply = media.serve("GET", target, range_header, media.state_dirs(host))     # status, headers, a slice of the file
    reply.read()                                  # the bytes of the slice (the page's server); `write` streams them (the listener)

The file is the pick's own (realm/idea_pick.py): from its folder only, with the media type its `pick.json` stored, **Range** requests
(206, so a sound or a clip seeks), `Cache-Control: private, max-age=31536000, immutable` (a round's files never change),
`X-Content-Type-Options: nosniff` and `Content-Security-Policy: sandbox; default-src 'none'` with `Content-Disposition: inline`: an SVG
opened on its own runs nothing. The phone's service worker never caches `/media/` (pwa/sw.js).
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlsplit

from orkboard.realm import idea_pick

PREFIX = "/media/"
CHUNK = 256 * 1024
_SECRET = secrets.token_bytes(32)                      # the host's, for its life: a pick's address from an earlier run is dead
_GOAL, _PICK, _FILE = re.compile(r"[a-z0-9-]{1,100}"), re.compile(r"[a-z0-9_-]{1,60}-r[0-9]{1,6}"), re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
HEADERS = [("Cache-Control", "private, max-age=31536000, immutable"), ("X-Content-Type-Options", "nosniff"),
           ("Content-Security-Policy", "sandbox; default-src 'none'")]


def sign(path: str) -> str:
    """The proof that the host gave this path out: a keyed hash of it."""
    return hmac.new(_SECRET, path.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def check(path: str, sig: str) -> bool:
    return bool(sig) and hmac.compare_digest(sign(path), sig)


def url(goal: str, pick: str, file: str) -> str:
    """The address of one file of a pick, signed: what the faces are given and put in an `<img>`, `<audio>` or `<video>`."""
    path = f"{PREFIX}{quote(goal, safe='')}/{quote(pick, safe='')}/{quote(file, safe='')}"
    return f"{path}?s={sign(path)}"


def parse(target: str) -> tuple[str, str, str, str] | None:
    """(the path as the host signs it, goal, pick id, file) of a request target; None when it is not a plain path to one file."""
    parts = urlsplit(target)
    if not parts.path.startswith(PREFIX):
        return None
    names = [unquote(p) for p in parts.path[len(PREFIX):].split("/")]
    if len(names) != 3 or not _GOAL.fullmatch(names[0]) or not _PICK.fullmatch(names[1]) or not _FILE.fullmatch(names[2]):
        return None
    return f"{PREFIX}{quote(names[0], safe='')}/{quote(names[1], safe='')}/{quote(names[2], safe='')}", *names


def state_dirs(host: Any) -> list[Path]:
    """The state folders of the projects the host has open, the shown one first (Orkline's host: its one Board's)."""
    found: list[Path] = []
    shown = getattr(host, "ideas", None)
    projects = getattr(getattr(host, "projects", None), "open_ones", None) or []
    for ideas in [shown, *(getattr(p, "ideas", None) for p in projects)]:
        folder = getattr(ideas, "state_dir", None)
        if folder is not None and Path(folder) not in found:
            found.append(Path(folder))
    return found


def find(dirs: list[Path], goal: str, pick: str, file: str) -> tuple[Path, str] | None:
    """(the file, its stored media type) of a pick's file in the first state folder that has it and lists it."""
    for state in dirs:
        try:
            data = idea_pick.load(state, goal, pick)
            folder = idea_pick.folder_of(state, goal, pick)
        except ValueError:
            continue
        mime = next((str(v.get("mime")) for v in (data or {}).get("variants") or [] if isinstance(v, dict) and v.get("file") == file), "")
        path = folder / file
        try:
            if mime and not path.is_symlink() and path.is_file() and path.resolve().parent == folder.resolve():
                return path, mime
        except OSError:
            continue
    return None


def span(header: str, size: int) -> tuple[int, int] | None | str:
    """The bytes a `Range` header asks for, `(first, last)`; None when there is none to serve (no header, another unit, several
    ranges, a bad one: the whole file); "unsatisfiable" when it starts past the end."""
    m = re.fullmatch(r"\s*bytes=(\d*)-(\d*)\s*", header or "")
    if not m or not (m.group(1) or m.group(2)):
        return None
    first, last = m.group(1), m.group(2)
    if not first:                                           # the last n bytes
        n = int(last)
        return "unsatisfiable" if n == 0 else (max(0, size - n), size - 1)
    a, b = int(first), int(last) if last else size - 1
    if last and b < a:
        return None
    return "unsatisfiable" if a >= size else (a, min(b, size - 1))


@dataclass
class Reply:
    status: int
    headers: list[tuple[str, str]] = field(default_factory=list)
    file: Path | None = None
    start: int = 0
    length: int = 0
    body: bytes = b""
    head_only: bool = False

    def read(self) -> bytes:
        """The bytes of the reply (the slice of the file, or the short text)."""
        if self.file is None or self.head_only:
            return b"" if self.head_only else self.body
        with self.file.open("rb") as f:
            f.seek(self.start)
            return f.read(self.length)


def _missing() -> Reply:
    body = b"Not found"
    return Reply(404, [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(body))), ("Cache-Control", "no-store"),
                       ("X-Content-Type-Options", "nosniff")], body=body)


def serve(method: str, target: str, range_header: str, dirs: list[Path]) -> Reply:
    """The reply to a request for a pick's file: 200, 206 for a range, 416 for one past the end, 404 for anything wrong (an unsigned
    address, a wrong signature, a name that is not a plain one, a file the pick does not list), 405 for a method but GET and HEAD."""
    if method not in ("GET", "HEAD"):
        return Reply(405, [("Allow", "GET, HEAD"), ("Content-Length", "0"), ("Cache-Control", "no-store")])
    got = parse(target)
    sig = (parse_qs(urlsplit(target).query).get("s") or [""])[0]
    if got is None or not check(got[0], sig):
        return _missing()
    found = find(dirs, got[1], got[2], got[3])
    if found is None:
        return _missing()
    path, mime = found
    try:
        size = path.stat().st_size
    except OSError:
        return _missing()
    kind = mime + ("; charset=utf-8" if mime.startswith("text/") else "")
    base = [("Content-Type", kind), ("Accept-Ranges", "bytes"), *HEADERS, ("Content-Disposition", f'inline; filename="{got[3]}"')]
    wanted = span(range_header, size)
    if wanted == "unsatisfiable":
        return Reply(416, [base[0], ("Content-Range", f"bytes */{size}"), ("Content-Length", "0"), ("Cache-Control", "no-store")])
    if wanted is None:
        return Reply(200, [*base, ("Content-Length", str(size))], path, 0, size, head_only=method == "HEAD")
    first, last = wanted
    return Reply(206, [*base, ("Content-Range", f"bytes {first}-{last}/{size}"), ("Content-Length", str(last - first + 1))],
                 path, first, last - first + 1, head_only=method == "HEAD")


async def write(writer: Any, reply: Reply, keep_alive: bool) -> None:
    """The reply on a phone's connection (gui/phone_http.py): its head, then the file in chunks, the writer drained between them."""
    phrase = HTTPStatus(reply.status).phrase
    head = "".join(f"{k}: {v}\r\n" for k, v in reply.headers)
    writer.write(f"HTTP/1.1 {reply.status} {phrase}\r\n{head}Connection: {'keep-alive' if keep_alive else 'close'}\r\n\r\n".encode("latin-1"))
    if reply.head_only:
        return
    if reply.file is None:
        writer.write(reply.body)
        return
    left = reply.length
    with reply.file.open("rb") as f:
        f.seek(reply.start)
        while left > 0:
            chunk = f.read(min(CHUNK, left))
            if not chunk:
                break
            left -= len(chunk)
            writer.write(chunk)
            await writer.drain()
