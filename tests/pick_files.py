"""Small real files for the pick tests (docs/specs/51-pick-one.md §8): a PNG, a JPEG, a GIF, a WEBP, an SVG, a WAV, an MP3 with a Xing
header, an OGG, an MP4 (a clip and a sound), a WEBM and a text, each a few hundred bytes, made from their formats' own layouts."""
from __future__ import annotations

import io
import json
import struct
import wave
import zlib
from pathlib import Path


def png(w: int = 3, h: int = 2) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = b"".join(b"\x00" + b"\x20\x40\x80" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def jpeg(w: int = 40, h: int = 30) -> bytes:
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = b"\xff\xc0\x00\x11\x08" + struct.pack(">HH", h, w) + b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01"
    return b"\xff\xd8" + app0 + sof + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00" + b"\xff\xd9"


def gif(w: int = 7, h: int = 5) -> bytes:
    return b"GIF89a" + struct.pack("<HH", w, h) + b"\x00\x00\x00;"


def webp(w: int = 16, h: int = 12, kind: str = "VP8L") -> bytes:
    if kind == "VP8L":
        bits = (w - 1) | ((h - 1) << 14)
        body = b"VP8L" + struct.pack("<I", 5) + b"\x2f" + struct.pack("<I", bits) + b"\x00"
    elif kind == "VP8 ":
        body = b"VP8 " + struct.pack("<I", 10) + b"\x00\x00\x00\x9d\x01\x2a" + struct.pack("<HH", w, h)
    else:
        body = b"VP8X" + struct.pack("<I", 10) + b"\x00\x00\x00\x00" + (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little")
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WEBP" + body


def svg(w: int | None = 24, h: int | None = 12) -> bytes:
    size = f' width="{w}" height="{h}"' if w else ' viewBox="0 0 48 36"'
    return f'<?xml version="1.0"?>\n<!-- a mark -->\n<svg xmlns="http://www.w3.org/2000/svg"{size}><rect width="4" height="4"/></svg>'.encode()


def wav(seconds: float = 0.5, rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


def mp3(frames: int = 1000, xing: bool = True) -> bytes:
    """An MPEG 1 Layer III frame (44.1 kHz, stereo) with a Xing header that counts `frames` frames: frames * 1152 / 44100 s."""
    frame = bytearray(b"\xff\xfb\x90\x00" + bytes(32))
    if xing:
        frame += b"Xing" + struct.pack(">II", 1, frames)
    return bytes(frame.ljust(417, b"\x00")) * 2


def ogg() -> bytes:
    return b"OggS\x00\x02" + bytes(20) + b"\x01\x1eOpusHead" + bytes(10)


def webm() -> bytes:
    return b"\x1a\x45\xdf\xa3\x93\x42\x82\x88webm" + bytes(30)


def box(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + kind + payload


def mp4(handler: bytes | None = b"vide", seconds: int = 5, w: int = 320, h: int = 240, brand: bytes = b"isom", moov: bool = True) -> bytes:
    """An MP4 with an `ftyp` box and, unless `moov` is off, a `moov` of one track (`vide` a clip, `soun` a sound) of `seconds`."""
    out = box(b"ftyp", brand + b"\x00\x00\x02\x00" + brand + b"mp42")
    if not moov:
        return out
    mvhd = box(b"mvhd", b"\x00\x00\x00\x00" + bytes(8) + struct.pack(">II", 1000, seconds * 1000) + bytes(80))
    tkhd = box(b"tkhd", b"\x00\x00\x00\x07" + bytes(72) + struct.pack(">II", w << 16, h << 16))
    hdlr = box(b"hdlr", bytes(8) + handler + bytes(12) + b"\x00")
    trak = box(b"trak", tkhd + box(b"mdia", hdlr)) if handler else b""
    return out + box(b"free", bytes(16)) + box(b"moov", mvhd + trak) + box(b"mdat", bytes(32))


def text(words: str = "Orkboard: the Board, on its own.") -> bytes:
    return words.encode("utf-8")


def write(folder: Path, name: str, data: bytes) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(data)
    return path


def ask(n: int = 3, kind: str = "image", target: str = "assets/logo.png", text: str = "A logo for the app") -> dict:
    """A plan's task `pick`."""
    return {"n": n, "kind": kind, "ask": text, "target": target}


def task(n: int = 3, kind: str = "image", **more) -> dict:
    """A task of the plan that makes variants."""
    return {"id": "k1", "title": "Draw the logo", "short": "Logo", "state": "running", "round": 1, "pick": ask(n, kind), **more}


def leave(tree: Path, files: dict[str, bytes], names: dict[str, str] | None = None, rows: list | None = None) -> None:
    """What a task leaves: each file into `.orkcraft-pick/` and a manifest of them (`rows` instead when given)."""
    for name, data in files.items():
        write(tree / ".orkcraft-pick", name, data)
    tree.mkdir(parents=True, exist_ok=True)
    rows = rows if rows is not None else [{"name": (names or {}).get(f, f.split(".")[0]), "file": f, "why": f"why {f}"} for f in files]
    (tree / ".orkcraft-pick.json").write_text(json.dumps({"variants": rows}), encoding="utf-8")


def make_pick(state_dir: Path, scratch: Path, files: dict[str, bytes], slug: str = "dark-mode", tid: str = "k1", rnd: int = 1,
              kind: str = "image", by: str = "grunt") -> dict:
    """A pick as the runner leaves it in the goal's state folder (`<state>/ideas/<slug>/picks/<task>-r<round>/`), made from `files`."""
    from orkboard.realm import idea_pick
    t = task(len(files), kind, id=tid, round=rnd)
    leave(scratch, files)
    variants, why = idea_pick.read(scratch, t)
    assert why == "", why
    pick = idea_pick.store(state_dir, slug, t, rnd, variants, by=by)
    idea_pick.discard(scratch)
    return pick
