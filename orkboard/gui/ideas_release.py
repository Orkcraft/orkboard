"""A goal's route and a release (docs/specs/68-release-and-route.md §2–§5) as `gui/ideas.py`'s `Ideas` has them. Split from ideas.py to keep it
under ~600 lines.

    ideas.move {slug, track?, before?}       # another party only before the goal's work starts (realm/idea_route.py); `idea_moved`
    ideas.release_out {slug}                 # Mark it out: the release is out in the stores, said once, after its own flag; `release_out`
    ideas.release_candidates {party}         # what goes in: {since: {version, out} | None, releases_from, candidates: [...]} (realm/releases.py)
    ideas.shown {party, from?}               # the faces say a party switch, fire and forget; `party_shown` (never on a first read or a redraw)

A new goal of *A release* takes `goes_in` (the slugs ticked) with `ideas.add`: `release_args` checks it before the goal exists, `release_made`
writes its file after. Orkboard never submits, uploads or tags: out is the person's word.
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _device, _opt, _text
from orkboard.realm import event_log, idea_route, ideas, releases


class ReleaseMixin:
    def move(self, args: dict) -> dict:
        """`{slug, track?, before?}`: the goal to another party and/or before another goal. To another party it is refused once its
        work has started (*Its work has started in <party>: a goal moves only before its work starts. Add a new goal there.*) and
        recorded in its route otherwise; its element and its place are as before (spec 68 §2.2). `{ok}`."""
        slug = _text(args, "slug", 100)
        got = idea_route.move(self.root(), self.state_dir, slug, _opt(args, "track") or None, _opt(args, "before") or None, by="person")
        self._what[slug] = "moved"
        if got["moved"]:
            self._ev(event_log.IDEA_MOVED, args, goal=slug, **{"from": got["from"], "to": got["to"]})
        self.changed(slug)
        return {"ok": True}

    # -- A release (§3) ------------------------------------------------------------------------------------------

    def release_args(self, args: dict, track: str, typed: dict) -> dict | None:
        """Before `ideas.add` adds a goal: `{version, goals}` for *A release* (`asks.version`, `goes_in` checked against what goes in:
        a goal not listed, or one another open release holds, is refused), None for any other type; `goes_in` on another type is refused."""
        if typed["key"] != "release":
            if args.get("goes_in") not in (None, []):
                raise IdeasError("Only a release takes goals to go in")
            return None
        asks = args.get("asks") if isinstance(args.get("asks"), dict) else {}
        try:
            return {"version": releases.version_of(asks.get("version")), "goals": releases.check(self.root(), self.state_dir, track, args.get("goes_in"))}
        except ValueError as e:
            raise IdeasError(str(e)) from None

    def release_made(self, args: dict, slug: str, track: str, rel: dict) -> None:
        """The release's file, once its goal is added (§3.3), and `release_made`."""
        releases.make(self.state_dir, slug, rel["version"], rel["goals"])
        parties = {(ideas.idea_page(self.root(), g) or ideas.Page()).get("track") for g in rel["goals"]}
        self._ev(event_log.RELEASE_MADE, args, goal=slug, party=track, goals=len(rel["goals"]), parties=len(parties - {None}))

    def release_out(self, args: dict) -> dict:
        """`{slug}`: Mark it out (§3.5). Refused for a goal that is not a release, before its own flag (*Its flag is not raised yet: a
        release goes out once it is in main*) and when it is out already. `{ok, out: when}`."""
        slug = _text(args, "slug", 100)
        got = releases.out(self.root(), self.state_dir, slug)
        self._ev(event_log.RELEASE_OUT, args, goal=slug, goals=got["goals"], days=got["days"])
        self.changed(slug)
        return {"ok": True, "out": got["out"]}

    def release_candidates(self, args: dict) -> dict:
        """`{party}`: what goes into a release of that party (§3.2): `{since, releases_from, candidates}`. `since`: its last release that is
        out, `{version, out}`, None before the first; `releases_from`: the parties it was set to release from ([] = every party but
        Ideation); `candidates`: `[{goal, title, party, party_name, element, at, commit, held}]`, newest flag first, `held` the version of an
        open release that holds it ("" when free: ticked by default, not when held)."""
        party = _text(args, "party", 100)
        if ideas.track_page(self.root(False), party) is None:
            raise IdeasError("That party is gone")
        rows = releases.index(self.root(False), self.state_dir)
        return {"since": releases.since(self.root(False), self.state_dir, party, rows), "releases_from": releases.releases_from(self.root(False), party),
                "candidates": releases.candidates(self.root(False), self.state_dir, party, rows)}

    # -- measured (§4) -------------------------------------------------------------------------------------------

    def shown(self, args: dict) -> dict:
        """`{party, from?}`: the faces say the person switched party (not a first read, not a redraw): `party_shown` with where from, where to
        and the face. Nothing else changes; a switch to the same party, or from a party that is gone, is not counted."""
        to, was = _text(args, "party", 100), _opt(args, "from")
        known = {t["slug"] for t in ideas.tracks(self.root(False), make=False)}
        if to not in known:
            raise IdeasError("That party is gone")
        if was and was != to and was in known:
            self._ev(event_log.PARTY_SHOWN, None, face=_device(args), **{"from": was, "to": to})
        return {"ok": True}
