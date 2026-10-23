"""What the board's commands share (gui/ideas.py and its mixins): the refusal and the readers of a command's args."""
from __future__ import annotations

# Where an opened idea was reached from, and where a start's or a queue's press was (spec 39 §2, spec 42 §1.2, spec 49 §2.6):
# the Map, the Board, Needs you, Agents, Review, the recap, the week, the flags, a push; the stops along the bottom (hand),
# a member of the party (party), the strip of today's events (today), the gate (gate).
VIA = ("map", "board", "needs", "agents", "review", "recap", "week", "flags", "push", "hand", "front", "party", "today", "gate")


class IdeasError(Exception):
    """A board command the host refuses, in plain words."""


def _device(args: dict) -> str:
    """"phone" when the listener says so (gui/mobile.py `guard`), else the computer's own window."""
    return "phone" if args.get("device") == "phone" else "desktop"


def _via(args: dict) -> str:
    """Where the person pressed it (spec 41 §4, spec 49 §2.6): the `via` the face says when it is one of `VIA` ("map", the
    stops along the bottom's "hand", …), else "idea" (the idea's screen)."""
    via = args.get("via")
    return via if isinstance(via, str) and via in VIA else "idea"


def _str(args: dict, key: str, limit: int) -> str:
    value = args.get(key, "")
    if not isinstance(value, str):
        raise IdeasError(f"{key} is not text")
    return value[:limit]


def _text(args: dict, key: str, limit: int) -> str:
    value = _str(args, key, limit).strip()
    if not value:
        raise IdeasError(f"{key} is missing")
    return value


def _opt(args: dict, key: str) -> str:
    value = args.get(key)
    return value.strip()[:100] if isinstance(value, str) else ""
