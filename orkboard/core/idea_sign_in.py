"""The keeper's part of spec 45 (docs/specs/45-sign-in.md §6): what it starts by itself waits while Claude Code needs its
sign-in, instead of failing (`held_for` "sign_in", `held_until` a day from the hold), and goes on once it is signed in.
`IdeaKeeper` has these through `SignInMixin`; it needs `sign_ins`, `state_dir`, `wiki_root`, `publish`.
"""
from __future__ import annotations

import datetime as dt
import time

from orkboard.core.sign_ins import HOLD_H
from orkboard.realm import harnesses, ideas, tool_errors

HARNESS = "claude"


def _iso(at: float) -> str:
    return dt.datetime.fromtimestamp(at).isoformat(timespec="seconds")


class SignInMixin:
    def signed_out(self) -> bool:
        """Whether the host says Claude Code needs its sign-in: what runs by itself waits for it (spec 45 §6)."""
        return self.sign_ins is not None and bool(self.sign_ins.blocked(HARNESS))

    def hold_sign_in(self, slug: str) -> bool:
        """The idea waits for Claude Code's sign-in, at most `HOLD_H` hours from the first hold. False when it needs none."""
        if not self.signed_out():
            return False
        st = ideas.state(self.state_dir, slug)
        if st["held_for"] != "sign_in" or not st["held_until"]:
            ideas.save_state(self.state_dir, slug, held_for="sign_in", held_until=_iso(time.time() + HOLD_H * 3600))
            self.publish(slug)
        return True

    def held_for(self, harness: str) -> int:
        """How many ideas wait for this tool's sign-in now (the Board runs on Claude)."""
        if harness != HARNESS:
            return 0
        return sum(1 for i in ideas.ideas(self.wiki_root())
                   if ideas.state(self.state_dir, i["slug"])["held_for"] == "sign_in")

    def _release(self, slug: str, st: dict, now: float) -> bool:
        """An idea held for the sign-in, on the clock: False while it waits; True when Claude Code is signed in (the hold
        is lifted and it goes on). After a day it fails as it did, with the line."""
        if not self.signed_out():
            ideas.save_state(self.state_dir, slug, held_for="", held_until="")
            return True
        try:
            due = dt.datetime.fromisoformat(st["held_until"]).timestamp()
        except ValueError:
            due = now
        if now >= due:
            line = tool_errors.LINES[tool_errors.LOGIN].format(tool=harnesses.title(HARNESS))
            ideas.save_state(self.state_dir, slug, held_for="", held_until="", error=line)
            self.publish(slug)
        return False

    def sign_in_held(self, slug: str, e: Exception, back: str) -> bool:
        """A call by itself failed for its sign-in (it helps): the idea goes `back` to where it was and waits for it,
        instead of failing. False when the failure is not one."""
        if self.sign_ins is None or not self.sign_ins.holds(e):
            return False
        ideas.save_state(self.state_dir, slug, state=back, error="", held_for="sign_in",
                         held_until=_iso(time.time() + HOLD_H * 3600))
        return True
