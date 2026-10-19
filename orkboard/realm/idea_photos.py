"""The photos a person attached to an idea (the phone's New idea): kept beside its state, read by the Taskmaster.

    put(state_dir, "dark-mode", raw)        # ".orkcraft/ideas/dark-mode/photos/1.jpg", the path the keeper reads
    listed(state_dir, "dark-mode")          # those paths, in the order they came
    decode([{"data": "<base64>"}, ...])     # the bytes of each, checked: an image, at most MAX_BYTES, at most MAX_PHOTOS

The phone makes each one a JPEG of at most 1600 px before it sends it; a PNG or a WebP is taken as it is. They live
in `<state_dir>/ideas/<slug>/photos/`, so deleting the idea deletes them. The keeper runs in the repository with
Read, and `.orkcraft/` is in it: the paths are given to it relative to the repository.

No face, no model.
"""
from __future__ import annotations

import base64
import binascii
from pathlib import Path

MAX_PHOTOS = 4
MAX_BYTES = 3 * 2**20
KINDS = ((b"\xff\xd8\xff", "jpg"), (b"\x89PNG\r\n\x1a\n", "png"))      # and WebP: RIFF....WEBP


def _kind(raw: bytes) -> str:
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    return next((ext for magic, ext in KINDS if raw.startswith(magic)), "")


def decode(photos: object) -> list[bytes]:
    """The photos of a request, checked; ValueError says plainly what is wrong."""
    if photos is None:
        return []
    if not isinstance(photos, list):
        raise ValueError("Photos are a list")
    if len(photos) > MAX_PHOTOS:
        raise ValueError(f"At most {MAX_PHOTOS} photos go with an idea")
    out = []
    for p in photos:
        data = p.get("data") if isinstance(p, dict) else None
        if not isinstance(data, str) or len(data) > MAX_BYTES * 4 // 3 + 8:
            raise ValueError(f"A photo is larger than {MAX_BYTES // 2**20} MB")
        try:
            raw = base64.b64decode(data, validate=True)
        except (ValueError, binascii.Error):
            raise ValueError("A photo did not arrive whole") from None
        if not _kind(raw):
            raise ValueError("A photo is a JPEG, a PNG or a WebP")
        out.append(raw)
    return out


def folder(state_dir: Path, slug: str) -> Path:
    return Path(state_dir) / "ideas" / slug / "photos"


def put(state_dir: Path, slug: str, raw: bytes) -> str:
    """One photo kept; its path relative to the repository (the state dir's parent)."""
    where = folder(state_dir, slug)
    where.mkdir(parents=True, exist_ok=True)
    n = 1 + max((int(p.stem) for p in where.iterdir() if p.stem.isdigit()), default=0)
    path = where / f"{n}.{_kind(raw)}"
    path.write_bytes(raw)
    return path.relative_to(Path(state_dir).parent).as_posix()


def listed(state_dir: Path, slug: str) -> list[str]:
    where = folder(state_dir, slug)
    if not where.is_dir():
        return []
    found = sorted((p for p in where.iterdir() if p.stem.isdigit() and p.suffix[1:] in ("jpg", "png", "webp")), key=lambda p: int(p.stem))
    return [p.relative_to(Path(state_dir).parent).as_posix() for p in found]


def prompt_lines(state_dir: Path, slug: str) -> str:
    """For a keeper's prompt: the photos to read first, beyond its count of files ("" with none)."""
    got = listed(state_dir, slug)
    if not got:
        return ""
    return "The person attached photos to the idea: read each one first (they are not counted in the files).\n" + \
        "\n".join(f"- {p}" for p in got) + "\n"
