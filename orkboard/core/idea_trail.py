"""A goal's trail (docs/specs/46-goal-trail.md §3, §4): once a goal's questions are answered its leader lays out the goal's
ideas as proposals, in the order they should be done; the person takes them one by one or all (Take all). A trail is
proposals (spec 35 §8): no spec is written, nothing is drafted and nothing is spent on an idea of it until the person takes
it. A mixin of `IdeaKeeper`, as `idea_goals.py` is.

    keeper.lay_out(slug, "read")        # on this thread, the goal's run: the `trail` step; the proposals are written
    keeper.lay_out_goal(slug)           # Lay out ideas: in the background, as the goal's run (`goal:<slug>`), via "person"
    keeper.draft_trail(slug, slugs)     # Take all: the ideas taken for `now` drafted one at a time, in the trail's order
    keeper.trailing(slug)               # the goal's leader is laying out its trail now
    keeper.trail_waiting(slug)          # the trail proposals of the goal that wait, in the trail's order

`self` has the keeper's `ask`, `parse`, `wiki_root`, `state_dir`, `_start`, `_may_run`, `refuse_spent`, `window_until`,
`members`, `draft_one`, `hold`, `publish`, `_ev`, `_tls`.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from orkboard.core.idea_draft import depends_ok
from orkboard.core.idea_night import declined, write_proposal
from orkboard.realm import board_map, event_log, goal_team, idea_checks, idea_target, ideas, roles

MAX_AFTER = 8                      # the keys and slugs an idea of the trail may wait for
MAX_IDEAS_SHOWN = 40               # of the other goals' open ideas, the most the trail is given (as the draft's)


def _kw():
    from orkboard.core import idea_keeper
    return idea_keeper


def _title(text: str) -> str:
    return " ".join(str(text or "").split())


class TrailMixin:
    # -- what waits ------------------------------------------------------------------------------------------

    def _trail_busy(self) -> set[str]:
        return self.__dict__.setdefault("_trail_busy_set", set())

    def trailing(self, slug: str) -> bool:
        """The goal's leader is laying out its trail now (a read's, or Lay out ideas)."""
        return slug in self._trail_busy()

    def trail_waiting(self, slug: str) -> list[dict]:
        """The goal's trail proposals that wait, in the trail's order (the goal's ideas by their order)."""
        return [i for i in ideas.ideas(self.wiki_root(), slug)
                if ideas.state(self.state_dir, i["slug"])["state"] == "proposed" and board_map.is_trail(self.state_dir, i["slug"])]

    def trail_due(self, slug: str) -> bool:
        """A goal's read that ends `ready` lays out its trail when it has no `trail_at` and at most 2 ideas (§3): a goal
        whose ideas the person wrote already is the person's to lay out (Lay out ideas)."""
        root = self.wiki_root()
        if slug == ideas.GENERAL or not any(t["slug"] == slug for t in ideas.tracks(root, make=False)):
            return False
        kept = ideas._json(ideas.goal_folder(self.state_dir, slug) / "state.json") or {}
        return ideas.goal_state(self.state_dir, slug)["state"] == "ready" and not kept.get("trail_at") \
            and len(ideas.ideas(root, slug)) <= 2

    # -- the context -----------------------------------------------------------------------------------------

    def team_view(self, root: Path, slug: str) -> str:
        """Who builds which tags, and each checker's check with its `applies` and `done` (the goal's party, §3)."""
        team = goal_team.team_of(root, slug)
        known = roles.kinds(self.state_dir)
        rows = [f"- {r['name']} ({r['slug']}) builds {', '.join(sorted(roles.takes_of(r, known))) or 'code'}"
                for s in team if (r := roles.role(self.state_dir, s)) and goal_team.band_of(s) != "check"]
        for c in idea_checks.of_team(self.state_dir, team, goal_team.every_of(root, slug)):
            rows.append(f"- {c['name']} ({c['by']}) checks: applies {'to every idea' if c['every'] else c['applies']}; done when: {c['done']}")
        return "\n".join(rows)

    def trail_prompt(self, root: Path, slug: str) -> str:
        """§3's `trail` context, cut in this order: the goal, its Summary, its Metrics with how each is counted, its ideas,
        its links (paths), its party, the proposals of this goal turned down, the other goals' open ideas."""
        g = next(t for t in ideas.tracks(root, make=False) if t["slug"] == slug)
        mine, others = [], []
        for i in ideas.ideas(root):
            st = ideas.state(self.state_dir, i["slug"])["state"]
            if i["track"] == slug:
                page = ideas.idea_page(root, i["slug"])
                after = board_map.list_of(page.get("depends_on")) if page else []
                mine.append(f"- {i['slug']}: {i['title']} ({st})" + (f", after {', '.join(after)}" if after else ""))
            elif st != "done" and len(others) < MAX_IDEAS_SHOWN:
                others.append(f"- {i['title']} (goal {i['track']})")
        metrics = "\n".join(f"- {m['name']}" + (f" → {m['target']}" if m.get("target") else "")
                            + (f" (counted: {m['how']})" if m.get("how") else "") for m in g["metrics"])
        no = "\n".join(f"- {d['title']}" + (f": {d['reason']}" if d["reason"] else "") for d in declined(self.state_dir, 1000) if d["goal"] == slug)
        paths = [x for x in g["links"] if "://" not in x]
        n = idea_target.TRAIL[self.target()]
        context = idea_target.cut([("The goal", f"{g['title']}\n{g['about']}"), ("Its summary", g["summary"]), ("Its metrics", metrics),
                                   ("Its ideas", "\n".join(mine)), ("Its links (paths)", "\n".join(f"- {x}" for x in g["links"])),
                                   ("Its party", self.team_view(root, slug)),
                                   ("Proposals of this goal the person turned down (never lay these out again)", no),
                                   ("The other goals' open ideas", "\n".join(others))], idea_target.CONTEXT["trail"])
        return f"""You are the keeper of this project's Task board. The goal {g['title']} is read and its questions are answered:
lay out its ideas. Write the ideas that take the goal from where the repository is to its metrics, in the order they should
be done, at most {n}; each one is one spec's worth (one to eight tasks); nothing an idea of the goal covers already. A
checker's check is held by every idea it applies to, so it is an idea of its own only when the work it checks needs one
(a test suite for the sync). You may read the repository (read only). {self.reads("trail", paths)}

{context}Answer with one JSON object and nothing else:
{{"ideas": [{{"key": "t1", "title": "a short title", "short": "its name in two or three words, 24 characters at most",
 "why": "two lines: what it does and which metric it moves",
 "after": ["keys of this list, or slugs of the goal's ideas, that must be done first"],
 "by": "a member's slug when the idea answers that member's view or check, else empty"}}]}}
"""

    # -- laying out ------------------------------------------------------------------------------------------

    def lay_out_goal(self, slug: str) -> None:
        """Lay out ideas (`ideas.trail`): the goal's trail now, in the background, as the goal's run (§4). Refused in plain
        words: a goal not `ready`, a trail that waits, its leader busy with it, the window and the reserve."""
        kw = _kw()
        if slug == ideas.GENERAL or not any(t["slug"] == slug for t in ideas.tracks(self.wiki_root(), make=False)):
            raise kw.KeeperError("That goal is gone")
        if ideas.goal_state(self.state_dir, slug)["state"] != "ready" or self.busy_goal(slug):
            raise kw.KeeperError("The goal is being read, or waits for your answers")
        if self.trail_waiting(slug):
            raise kw.KeeperError("Its laid-out ideas wait for you: take them or say No first")
        if why := self._may_run():
            raise kw.KeeperError(why)
        self.refuse_spent()
        self._start(slug, "trail", lambda: self.lay_out(slug, "person"), f"goal:{slug}")

    def lay_out(self, slug: str, via: str = "read") -> None:
        """The `trail` step on this thread (the goal's run): the leader writes the goal's missing ideas as proposals. A call
        that fails or runs out of its budget writes nothing: the goal stays `ready` with the error."""
        kw = _kw()
        root = self.wiki_root()
        self._trail_busy().add(slug)
        ideas.save_goal_state(self.state_dir, slug, error="")
        self.publish(f"goal:{slug}")
        try:
            try:
                text, *_rest = self.ask("trail", self.trail_prompt(root, slug))
                answer = self.parse(text)
            except Exception as e:
                if not isinstance(e, InterruptedError):
                    ideas.save_goal_state(self.state_dir, slug, error=kw._why(e))
                return
            measure = self.measure()
            wrote, dropped = self.write_trail(root, slug, answer)
            ideas.save_goal_state(self.state_dir, slug, error="", trail_at=dt.datetime.now().isoformat(timespec="seconds"), trail=wrote)
            self._ev(event_log.TRAIL_LAID, goal=slug, ideas=len(wrote), dropped=dropped, via=via, **measure)
            for s in wrote:
                self.publish(s)
        finally:
            self._trail_busy().discard(slug)

    def write_trail(self, root: Path, slug: str, answer: dict) -> tuple[list[str], int]:
        """The answer's ideas, strictly, in its order after the goal's ideas, at most `TRAIL`: each a proposal of the goal
        (`proposed_by: "trail"`, `trail_by` a member's slug), its `depends_on` from `after`. A title the person turned down
        for this goal, an idea's of the goal or one already written is dropped (case aside). The slugs written and how many
        were dropped."""
        kw = _kw()
        limit = idea_target.TRAIL[self.target()]
        members = {m["slug"] for m in self.members(root, slug)}
        taken = {_title(i["title"]).lower() for i in ideas.ideas(root, slug)}
        taken |= {_title(d["title"]).lower() for d in declined(self.state_dir, 1000) if d["goal"] == slug}
        mine = {i["slug"] for i in ideas.ideas(root, slug)}
        asked = [x for x in (answer.get("ideas") if isinstance(answer.get("ideas"), list) else []) if isinstance(x, dict)]
        written: list[tuple[str, str, list[str]]] = []                 # (key, slug, its `after`)
        dropped = 0
        for n, raw in enumerate(asked):
            title, why = _title(kw._words(raw.get("title"), ideas.TITLE_CHARS)), kw._words(raw.get("why"), 600)
            if not title or title.lower() in taken or len(written) >= limit:
                dropped += 1
                continue
            taken.add(title.lower())
            by = _title(kw._words(raw.get("by"), 60))
            new = write_proposal(root, self.state_dir, slug, title, why or title, kw._words(raw.get("short"), 60),
                                 proposed_by=board_map.TRAIL, trail_by=by if by in members else "")
            key = _title(kw._words(raw.get("key"), 40)) or f"t{n + 1}"
            written.append((key, new, kw._strings(raw.get("after"), MAX_AFTER, 100)))
        keys = {k: s for k, s, _a in written}
        for _k, new, after in written:                                     # the keys are slugs now: no cycle, only the goal's ideas
            wanted = [keys.get(a) or (a if a in mine else "") for a in after]
            ok = depends_ok(root, new, [w for w in wanted if w])
            if ok:
                ideas.set_meta(root, new, depends_on=json.dumps(ok, ensure_ascii=False))
        return [s for _k, s, _a in written], dropped

    # -- taking all ------------------------------------------------------------------------------------------

    def draft_trail(self, goal: str, slugs: list[str]) -> None:
        """Take all (§4): the trail's ideas taken for the queue `now`, drafted one at a time in the trail's order, in the
        goal's run (the night's way, `draft_one`), never all at once. Each is `raw` already; none is drafted by the clock
        meanwhile. Refused (nothing started) while the goal's run is busy or the keeper may not run."""
        kw = _kw()
        if self.busy_goal(goal):
            raise kw.KeeperError("The goal's leader is busy with it: a moment")
        if why := self._may_run():
            raise kw.KeeperError(why)
        if not slugs:
            return
        with self._lock:                                  # the clock leaves them to this run
            for s in slugs:
                self._busy.setdefault(s, "drafting")
        try:
            self._start(goal, "drafting", lambda: self.draft_each(goal, slugs), f"goal:{goal}")
        except Exception:
            for s in slugs:
                self._busy.pop(s, None)
            raise

    def draft_each(self, goal: str, slugs: list[str]) -> None:
        cancel, key, slug = getattr(self._tls, "cancel", None), getattr(self._tls, "key", None), getattr(self._tls, "slug", None)
        try:
            for n, s in enumerate(slugs):
                if self.cancel.is_set() or (cancel is not None and cancel.is_set()):
                    for rest in slugs[n:]:                # stopped: what is left waits for the person, as a read's stop does
                        ideas.save_state(self.state_dir, rest, queue="hold")
                        self.publish(rest)
                    return
                if self.hold(s):                          # a spent window or a sign-in: it waits with `held_until`
                    continue
                self._tls.key = self._tls.slug = s        # its spend is the idea's; its leader is still the goal's
                try:
                    self.draft_one(s)
                finally:
                    self._tls.key, self._tls.slug = key, slug
                    self._busy.pop(s, None)
        finally:
            for s in slugs:
                self._busy.pop(s, None)
