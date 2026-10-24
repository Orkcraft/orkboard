"""Ideation's pitches (docs/specs/65-ideation.md §2, §5) as `gui/ideas.py`'s `Ideas` has them: a goal of a party the Investor leads
is a pitch, judged by the keeper (core/idea_judge.py) and never built. Split from ideas.py to keep it under ~600 lines.

    ideas.judge {slug}                      # judge it now: a new pitch put on Hold or Tonight, Try again after a failure
    ideas.pitch_send {slug, party, type?}   # Send to <party>: a new goal there, Now; the pitch is `sent`
    ideas.pitch_again {slug, text?}         # Change and judge again (Judged again, for a passed one)
    ideas.pitch_pass {slug, why?}           # Pass: kept with its why, read by every later pitch; the 201st oldest goes

A pitch is added with `ideas.add` in its party (one box, its lens, Now · Tonight · `hold`), dropped with `ideas.drop`. The plan's
commands refuse it in words (`refuse_pitch`). What the faces read of it is `pitch` on its page and on its Map node
(realm/pitches.py `face`).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from orkboard.core import idea_keeper
from orkboard.gui.ideas_args import IdeasError, _opt, _text
from orkboard.realm import event_log, ideas, pitches

# The commands of a plan, of its tasks and of the talk: a pitch has none of them (spec 65 §2).
PLAN_COMMANDS = ("ideas.plan", "ideas.start", "ideas.start_now", "ideas.stop", "ideas.revise", "ideas.revise_answer", "ideas.answer",
                 "ideas.say", "ideas.todo", "ideas.pick", "ideas.check_skip")


class PitchMixin:
    def refuse_pitch(self, name: str, args: dict) -> None:
        """The plan's commands (and the talk) refuse a pitch: *A pitch is judged, not built: send it to a party first*."""
        if name not in PLAN_COMMANDS or args.get("goal") is True:
            return
        slug = args.get("slug") if isinstance(args.get("slug"), str) else args.get("idea")
        if isinstance(slug, str) and pitches.is_pitch(self.root(False), slug.strip()):
            raise IdeasError(idea_keeper.PITCH_NOT_BUILT)

    def pitch_of(self, root: Path, slug: str, state: str) -> dict | None:
        """A pitch's views, case against, decision and what became of it (realm/pitches.py `face`); None for any other goal."""
        return pitches.face(root, self.state_dir, slug, state, self._target()) if pitches.is_pitch(root, slug) else None

    def _pitch(self, args: dict, *states: str) -> tuple[Path, str, ideas.Page]:
        """The pitch an answer is about, in one of `states` (its state as the host reads it)."""
        slug, root = _text(args, "slug", 100), self.root()
        page = ideas.idea_page(root, slug)
        if page is None or not pitches.is_pitch(root, slug):
            raise IdeasError("That pitch is gone")
        st = self._state(slug)["state"]
        if self.keeper.busy(slug) or st == "judging":
            raise IdeasError("The keeper is judging this pitch: a moment")
        if st not in states:
            raise IdeasError({"sent": "This pitch is sent: its goal is in its party now",
                              "passed": "This pitch is passed: judge it again first"}.get(st, "This pitch is not judged yet"))
        return root, slug, page

    # -- the commands ----------------------------------------------------------------------------------------------

    def judge(self, args: dict) -> dict:
        """`{slug}`: judge it now (a pitch kept for tonight or on hold, or one that failed: Try again); refused in a spent window."""
        slug = _text(args, "slug", 100)
        if ideas.idea_page(self.root(), slug) is None:
            raise IdeasError("That pitch is gone")
        self.keeper.judge(slug, person=True)
        self.changed(slug)
        return {"ok": True}

    def pitch_send(self, args: dict) -> dict:
        """`{slug, party, type?}`: Send to <party> (spec 65 §5). A new goal in that party, added as `ideas.add` adds one: its type (the
        decision's when it named this party and none is given; "" for none), its queue Now, its words the decision's first step (else the
        pitch) with a *From Ideation* line naming the pitch, its lens the pitch's; its draft reads the pitch's views and decision. A party
        of the library not in the project is refused (*Make the <name> party first*). `{slug: the new goal, party, type, queue}`."""
        root, slug, page = self._pitch(args, "judged")
        party = _text(args, "party", 100)
        to = pitches.offers(root, self.state_dir).get(party)
        if to is None:
            raise IdeasError("That party is gone")
        if to["preset"]:
            raise IdeasError(f"Make the {to['name']} party first")
        d = pitches.read(self.state_dir, slug)["decision"] or {}
        where = d.get("where") or {}
        kind = _opt(args, "type") if "type" in args else ((where.get("type") or "") if where.get("party") == party else "")
        text = f"{d.get('first') or page.section('Gist')}\n\nFrom Ideation: {page.title or slug} ({slug})"
        with ideas.LOCK:                                  # claimed: a second press finds it sent
            if ideas.state(self.state_dir, slug)["state"] != "judged":
                raise IdeasError("This pitch is sent: its goal is in its party now")
            ideas.save_state(self.state_dir, slug, state="sent")
        try:
            got = self.add({"text": text, "track": party, "type": kind, **{k: args[k] for k in ("device", "link") if k in args}}, pitch=slug)
        except Exception:
            ideas.save_state(self.state_dir, slug, state="judged")
            raise
        decided = d.get("answer") == "invest" and where.get("party") == party
        pitches.save(self.state_dir, slug, sent={"party": party, "type": got["type"], "goal": got["slug"], "as_decided": decided,
                                                 "at": dt.datetime.now().isoformat(timespec="seconds")})
        self._ev(event_log.PITCH_SENT, args, goal=slug, to=party, type=got["type"], as_decided=decided)
        self.changed(slug)
        return {"slug": got["slug"], "party": party, "type": got["type"], "queue": got["queue"], **({"error": got["error"]} if got.get("error") else {})}

    def pitch_again(self, args: dict) -> dict:
        """`{slug, text?}`: Change and judge again (a judged or failed pitch), or Judged again (a passed one): its words changed when
        `text` is given (at most 2 000 characters), judged anew; the decision there was kept in `before` (the last two)."""
        root, slug, page = self._pitch(args, "judged", "failed", "passed")
        text = args.get("text")
        if text is not None and not isinstance(text, str):
            raise IdeasError("text is not text")
        text, old = (text or "").strip()[:pitches.PITCH_CHARS], page.section("Gist")
        changed = bool(text) and text != old.strip()
        if changed:
            pitches.rewrite(root, slug, text)
            ideas.add_turn(self.state_dir, slug, "you", text, "Gist")
        try:
            self.keeper.judge(slug, person=True)
        except idea_keeper.KeeperError:
            if changed:
                pitches.rewrite(root, slug, old)          # refused (a spent window): its words as they were
            raise
        self._ev(event_log.PITCH_AGAIN, args, goal=slug, changed=changed)
        self.changed(slug)
        return {"ok": True}

    def pitch_pass(self, args: dict) -> dict:
        """`{slug, why?}`: Pass. The pitch is kept, `passed`, with the person's line (at most 300) beside the decision's why; read by
        every later pitch's views and Investor. At most 200 are kept: the oldest beyond is dropped as `ideas.drop` drops a goal.
        `{ok, dropped: [slugs]}`."""
        root, slug, _page = self._pitch(args, "judged")
        why = args.get("why")
        if why is not None and not isinstance(why, str):
            raise IdeasError("why is not text")
        why = " ".join((why or "").split())[:pitches.WHY_CHARS]
        decided = (pitches.read(self.state_dir, slug)["decision"] or {}).get("answer") == "pass"
        pitches.save(self.state_dir, slug, passed={"why": why, "at": dt.datetime.now().isoformat(timespec="seconds"), "as_decided": decided})
        ideas.save_state(self.state_dir, slug, state="passed", error="")
        self._ev(event_log.PITCH_PASSED, args, goal=slug, as_decided=decided, has_reason=bool(why))
        dropped = []
        for old in pitches.over_cap(root, self.state_dir):
            if not self.keeper.busy(old):
                ideas.drop(root, old, self.state_dir)
                dropped.append(old)
                self.changed(old)
        self.changed(slug)
        return {"ok": True, "dropped": dropped}
