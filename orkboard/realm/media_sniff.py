"""What a file is, from its bytes, and what can be read of it cheaply (docs/specs/51-pick-one.md §2.1, §2.2): the media type of
a picture, a sound, a clip or a text, never from its name, and its size on screen or its length in seconds when the header says
so. No external tool, no model, no face.

    sniff(path)                  # "image/png" · "image/jpeg" · "image/gif" · "image/webp" · "image/svg+xml"
                                 # "audio/mpeg" · "audio/ogg" · "audio/wav" · "audio/mp4" · "video/mp4" · "video/webm"
                                 # "text/plain" (UTF-8 without control characters) · None for anything else
    measure(path, mime)          # {"w", "h", "seconds"}: each an int or float when the header gives it, else None

A text is `text/plain` here; that a text is Markdown is its name's to say (realm/idea_pick.py): the bytes cannot. An MP4 is a
sound or a clip by its tracks (`moov`), else by its brand (`M4A `, `M4B ` a sound). A WEBM is a clip, an OGG a sound.
Every read is bounded; a file that is cut or odd reads as null, never as an error.
"""
from __future__ import annotations

import codecs
import re
from pathlib import Path
from typing import IO

HEAD = 4096                      # what a signature, an SVG's root and a text's first characters are read from
MOOV_MAX = 16 * 1024 * 1024      # the largest `moov` box read
BOXES_MAX = 256                  # the most top-level boxes walked to find `moov`
NONE = {"w": None, "h": None, "seconds": None}

_SVG = re.compile(r"\A﻿?\s*(?:<\?xml[^>]*\?>\s*|<!--.*?-->\s*|<!DOCTYPE[^>\[]*(?:\[.*?\])?\s*>\s*)*<svg[\s>/]", re.S)
_SVG_TAG = re.compile(r"<svg\b([^>]*)>", re.S)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_NUMBER = re.compile(r"\s*([0-9]*\.?[0-9]+)\s*(?:px)?\s*\Z")
_MP3_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}     # by the version bits


def _mp3_header(b: bytes) -> bool:
    """Four bytes that open an MPEG audio frame: the sync, a known version and layer, a bitrate and a rate that exist."""
    return (len(b) >= 4 and b[0] == 0xFF and b[1] & 0xE0 == 0xE0 and (b[1] >> 3) & 3 != 1 and (b[1] >> 1) & 3 != 0
            and b[2] >> 4 != 0xF and (b[2] >> 2) & 3 != 3)


def _signature(head: bytes) -> str | None:
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    if head[:4] == b"OggS":
        return "audio/ogg"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "video/webm"
    if head[:3] == b"ID3" or _mp3_header(head[:4]):
        return "audio/mpeg"
    if head[4:8] == b"ftyp":
        return "video/mp4"                                  # a sound or a clip: `sniff` looks at its tracks
    return None


def _is_text(head: bytes, whole: bool) -> bool:
    """UTF-8 (a character cut by the end of a head that is not the whole file is not a fault) without a control character
    but tab and line breaks, and not empty."""
    if not head or b"\x00" in head:
        return False
    try:
        text = codecs.getincrementaldecoder("utf-8")().decode(head, final=whole)
    except UnicodeDecodeError:
        return False
    return bool(text) and not _CONTROL.search(text)


def sniff(path: Path) -> str | None:
    """The media type of the file at `path` from its bytes (the module's doc lists them); None for a type it does not know, a
    file it cannot read or an empty one."""
    try:
        with path.open("rb") as f:
            head = f.read(HEAD)
            size = path.stat().st_size
            mime = _signature(head)
            if mime == "video/mp4":
                return _mp4_mime(f, size, head[8:12])
            if mime is not None:
                return mime
    except OSError:
        return None
    if _SVG.match(head.decode("utf-8", "replace")):
        return "image/svg+xml"
    return "text/plain" if _is_text(head, size <= len(head)) else None


# -- measuring -----------------------------------------------------------------------------------------------

def measure(path: Path, mime: str) -> dict:
    """`{"w", "h", "seconds"}` of the file as its header gives them, null for what it cannot (a text has none). A picture has
    its size, a WAV, an MP3 with a Xing header and an MP4 their length, an MP4 clip its size too."""
    out = dict(NONE)
    try:
        with path.open("rb") as f:
            size = path.stat().st_size
            if mime == "image/svg+xml":
                out["w"], out["h"] = _svg_size(f.read(HEAD).decode("utf-8", "replace"))
            elif mime.startswith("image/"):
                out["w"], out["h"] = _image_size(f, mime)
            elif mime == "audio/wav":
                out["seconds"] = _wav_seconds(f, size)
            elif mime == "audio/mpeg":
                out["seconds"] = _mp3_seconds(f)
            elif mime in ("audio/mp4", "video/mp4"):
                info = _mp4(f, size)
                if info:
                    out["seconds"] = info["seconds"]
                    if mime == "video/mp4":
                        out["w"], out["h"] = info["w"], info["h"]
    except (OSError, ValueError, IndexError):
        return dict(NONE)
    return out


def _int(b: bytes, order: str = "big") -> int:
    return int.from_bytes(b, order)


def _image_size(f: IO[bytes], mime: str) -> tuple[int | None, int | None]:
    f.seek(0)
    head = f.read(32)
    if mime == "image/png" and len(head) >= 24:
        return _int(head[16:20]), _int(head[20:24])
    if mime == "image/gif" and len(head) >= 10:
        return _int(head[6:8], "little"), _int(head[8:10], "little")
    if mime == "image/webp":
        kind = head[12:16]
        if kind == b"VP8 " and len(head) >= 30 and head[23:26] == b"\x9d\x01\x2a":
            return _int(head[26:28], "little") & 0x3FFF, _int(head[28:30], "little") & 0x3FFF
        if kind == b"VP8L" and len(head) >= 25 and head[20] == 0x2F:
            bits = _int(head[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if kind == b"VP8X" and len(head) >= 30:
            return _int(head[24:27], "little") + 1, _int(head[27:30], "little") + 1
    if mime == "image/jpeg":
        return _jpeg_size(f)
    return None, None


def _jpeg_size(f: IO[bytes]) -> tuple[int | None, int | None]:
    f.seek(2)
    for _ in range(512):                                    # the segments before the frame header
        b = f.read(1)
        while b == b"\xff":                                 # fill bytes before a marker
            b = f.read(1)
        if not b:
            break
        marker = b[0]
        if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
            continue
        length = f.read(2)
        if len(length) < 2:
            break
        n = _int(length)
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            frame = f.read(5)
            return (_int(frame[3:5]), _int(frame[1:3])) if len(frame) == 5 else (None, None)
        if marker == 0xDA:                                  # the scan: no frame header came
            break
        f.seek(n - 2, 1)
    return None, None


def _length(value: str) -> float | None:
    m = _NUMBER.match(value or "")
    return float(m.group(1)) if m else None


def _svg_size(text: str) -> tuple[int | None, int | None]:
    """The root's `width` and `height` in pixels (a number, or a number of px), else its `viewBox`'s."""
    tag = _SVG_TAG.search(text)
    if not tag:
        return None, None
    attrs = dict(re.findall(r"""([\w:-]+)\s*=\s*["']([^"']*)["']""", tag.group(1)))
    w, h = _length(attrs.get("width", "")), _length(attrs.get("height", ""))
    if not (w and h):
        box = re.split(r"[\s,]+", (attrs.get("viewBox") or "").strip())
        if len(box) == 4:
            try:
                w, h = float(box[2]), float(box[3])
            except ValueError:
                w = h = None
    return (round(w), round(h)) if w and h and w > 0 and h > 0 else (None, None)


def _wav_seconds(f: IO[bytes], size: int) -> float | None:
    f.seek(12)
    rate = None
    for _ in range(64):
        head = f.read(8)
        if len(head) < 8:
            return None
        chunk, n = head[:4], _int(head[4:8], "little")
        if chunk == b"fmt ":
            body = f.read(min(n, 16))
            if len(body) >= 12:
                rate = _int(body[8:12], "little")
            f.seek(n - len(body) + (n & 1), 1)
        elif chunk == b"data":
            left = size - f.tell()
            return round(min(n, left) / rate, 1) if rate else None
        else:
            f.seek(n + (n & 1), 1)
    return None


def _mp3_seconds(f: IO[bytes]) -> float | None:
    """The length from a Xing (or Info) header's frame count; null for a file that has none (its length would be a guess)."""
    f.seek(0)
    head = f.read(10)
    skip = 0
    if head[:3] == b"ID3" and len(head) == 10:
        skip = 10 + ((head[6] & 0x7F) << 21 | (head[7] & 0x7F) << 14 | (head[8] & 0x7F) << 7 | (head[9] & 0x7F))
    f.seek(skip)
    buf = f.read(2048)
    at = next((i for i in range(len(buf) - 4) if _mp3_header(buf[i:i + 4])), -1)
    if at < 0 or (buf[at + 1] >> 1) & 3 != 1:               # Layer III only
        return None
    version, rate = (buf[at + 1] >> 3) & 3, _MP3_RATES[(buf[at + 1] >> 3) & 3][(buf[at + 2] >> 2) & 3]
    mono = (buf[at + 3] >> 6) & 3 == 3
    side = (17 if mono else 32) if version == 3 else (9 if mono else 17)
    x = at + 4 + (0 if buf[at + 1] & 1 else 2) + side       # the CRC bit is 0 when two bytes of CRC follow the header
    if buf[x:x + 4] not in (b"Xing", b"Info") or not _int(buf[x + 4:x + 8]) & 1:
        return None
    return round(_int(buf[x + 8:x + 12]) * (1152 if version == 3 else 576) / rate, 1)


# -- MP4 -----------------------------------------------------------------------------------------------------

def _mp4_boxes(data: bytes, start: int = 0, end: int | None = None):
    """(type, payload start, payload end) of the boxes in `data[start:end]`."""
    end = len(data) if end is None else end
    while start + 8 <= end:
        n, kind = _int(data[start:start + 4]), data[start + 4:start + 8]
        head = 8
        if n == 1:
            n, head = _int(data[start + 8:start + 16]), 16
        elif n == 0:
            n = end - start
        if n < head or start + n > end:
            return
        yield kind, start + head, start + n
        start += n


def _mp4_moov(f: IO[bytes], size: int) -> bytes | None:
    pos = 0
    for _ in range(BOXES_MAX):
        f.seek(pos)
        head = f.read(16)
        if len(head) < 8:
            return None
        n, kind, head_len = _int(head[:4]), head[4:8], 8
        if n == 1 and len(head) == 16:
            n, head_len = _int(head[8:16]), 16
        elif n == 0:
            n = size - pos
        if n < head_len:
            return None
        if kind == b"moov":
            f.seek(pos + head_len)
            return f.read(n - head_len) if n - head_len <= MOOV_MAX else None
        pos += n
        if pos >= size:
            return None
    return None


def _mp4(f: IO[bytes], size: int) -> dict | None:
    """{"handlers": the tracks' kinds ("vide", "soun"), "seconds", "w", "h": the first clip track's size} of an MP4 with a `moov`."""
    moov = _mp4_moov(f, size)
    if moov is None:
        return None
    out: dict = {"handlers": [], "seconds": None, "w": None, "h": None}
    for kind, a, b in _mp4_boxes(moov):
        if kind == b"mvhd" and b - a >= 32:
            v1 = moov[a] == 1
            scale = _int(moov[a + (20 if v1 else 12):a + (24 if v1 else 16)])
            span = _int(moov[a + (24 if v1 else 16):a + (32 if v1 else 20)])
            out["seconds"] = round(span / scale, 1) if scale and span != (1 << (64 if v1 else 32)) - 1 else None
        elif kind == b"trak":
            handler, w, h = _mp4_track(moov, a, b)
            if handler:
                out["handlers"].append(handler)
            if handler == "vide" and out["w"] is None:
                out["w"], out["h"] = w, h
    return out


def _mp4_track(moov: bytes, start: int, end: int) -> tuple[str, int | None, int | None]:
    handler, w, h = "", None, None
    for kind, a, b in _mp4_boxes(moov, start, end):
        if kind == b"tkhd":
            at = a + (88 if moov[a] == 1 else 76)
            if b - at >= 8:
                w, h = _int(moov[at:at + 2]) or None, _int(moov[at + 4:at + 6]) or None      # 16.16 fixed point: the whole part
        elif kind == b"mdia":
            for kind2, c, d in _mp4_boxes(moov, a, b):
                if kind2 == b"hdlr" and d - c >= 12:
                    handler = moov[c + 8:c + 12].decode("latin-1")
    return handler, w, h


def _mp4_mime(f: IO[bytes], size: int, brand: bytes) -> str:
    """`audio/mp4` for a file with a sound track and no clip track, or (with no `moov` to read) for the brands of a sound."""
    info = _mp4(f, size)
    if info and "vide" in info["handlers"]:
        return "video/mp4"
    if info and "soun" in info["handlers"]:
        return "audio/mp4"
    return "audio/mp4" if brand in (b"M4A ", b"M4B ") else "video/mp4"
