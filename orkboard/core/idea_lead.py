"""A goal's leader (decisions §53; realm/goal_team.py): the goal's steps run as the leader of its party — its reading, its
ideas' drafts, answers, talk and plans — on the leader's model, the leader's voice and instruction before the step's own
prompt; the Taskmaster when the goal has no leader picked (and for what is no goal's: the night's proposals). When the
goal's ideas are done, its leader accepts it against its metrics (`accept_goal`: realm/goal_verdict.py).

    keeper.leader()                  # the role the running step leads as, None for the Taskmaster
    keeper.accept_goal("ship")       # in the background, as the goal's run (`goal:<slug>`)

A mixin of `IdeaKeeper`; `self` has its `ask`, `parse`, `wiki_root`, `state_dir`, `_start`, `_tls`, `publish`, `_ev`.
"""
from __future__ import annotations

from pathlib import Path

from orkboard.realm import event_log, goal_team, goal_verdict, idea_target, ideas, own_parties, roles


def _kw():
    from orkboard.core import idea_keeper
    return idea_keeper


class LeadMixin:
    def goal_of_key(self, key: str) -> str:
        """The goal a run is on: a goal's own (`goal:<slug>`), an idea's goal; "" for what is no goal's."""
        key = str(key or "")
        if key.startswith("goal:"):
            return key[5:]
        page = ideas.idea_page(self.wiki_root(), key) if key and key != "night-proposals" else None
        return (page.get("track") or "") if page is not None else ""

    def leader(self) -> dict | None:
        """The role the running step leads as: its goal's leader; None for the Taskmaster (no leader, or no goal). A
        member's `ask` call (core/idea_goals.py, spec 46 §2) runs as that member."""
        if member := getattr(self._tls, "member", None):
            return member
        goal = self.goal_of_key(getattr(self._tls, "key", "") or getattr(self._tls, "slug", "") or "")
        slug = goal_team.leader_of(self.wiki_root(), goal) if goal else roles.TASKMASTER
        return None if slug == roles.TASKMASTER else roles.role(self.state_dir, slug)

    @staticmethod
    def voice(lead: dict) -> str:
        """What a leader is told before a step's own prompt: who it is, and its instruction; a member (builder or checker)
        asked about the goal, who it is the same way."""
        if lead.get("member"):
            return f"You are {lead['name']}, a member of this goal's party. {lead.get('instruction') or ''}\n\n"
        return (f"You are {lead['name']}, the leader of this goal's party: you plan its ideas and accept the goal. "
                f"{lead.get('instruction') or ''}\nIn what follows, \"the keeper\" is you.\n\n")

    def leader_name(self, goal: str) -> str:
        slug = goal_team.leader_of(self.wiki_root(), goal)
        return (roles.role(self.state_dir, slug) or {}).get("name") or "Taskmaster"

    # -- accepting a goal ----------------------------------------------------------------------------------------

    def accept_goal(self, slug: str) -> None:
        """The goal's leader accepts it against its metrics, in the background (the goal's run)."""
        kw = _kw()
        if not any(t["slug"] == slug for t in ideas.tracks(self.wiki_root(), make=False)):
            raise kw.KeeperError("That goal is gone")
        if why := self._may_run():
            raise kw.KeeperError(why)
        key = f"goal:{slug}"
        if self.busy(key):
            raise kw.KeeperError("The goal's leader is busy with it: a moment")
        self._start(slug, "accept", lambda: self.accept_one(slug), key)

    def accept_prompt(self, root: Path, slug: str) -> str:
        g = next(t for t in ideas.tracks(root, make=False) if t["slug"] == slug)
        mine = ideas.ideas(root, slug)
        done = [i for i in mine if ideas.state(self.state_dir, i["slug"])["state"] == "done"]
        metrics = "\n".join(f"- {m['name']}" + (f" → {m['target']}" if m.get("target") else "")
                            + (f" (counted: {m['how']})" if m.get("how") else "") for m in g["metrics"])
        shipped = "\n\n".join(f"{i['title']}\n" + (ideas.idea_page(root, i["slug"]) or ideas.Page()).section("Done when")
                              for i in done)
        context = idea_target.cut([("The goal", f"{g['title']}\n{g['about']}"), ("Its summary", g["summary"]),
                                   ("Its metrics", metrics), ("Its ideas done, with their Done when", shipped),
                                   ("Its ideas not done", "\n".join(f"- {i['title']}" for i in mine if i not in done))],
                                  idea_target.CONTEXT["accept"])
        return f"""You are the keeper of this project's Task board. The ideas of the goal {g['title']} are done: accept the goal or
not, against its metrics, not against the work done. You may read the repository (read only) to see what shipped.
{self.reads("accept", [])}

{context}Answer with one JSON object and nothing else:
{{"met": true or false,
 "verdict": "two or three lines: whether the goal is reached, and why",
 "metrics": [{{"name": "a metric as named", "status": "met, not met or unknown", "why": "one line: the number, or what is missing to count it"}}],
 "next": ["zero to three next ideas, one line each, when the goal is not reached"]}}
"""

    def _mark_party(self, slug: str, met: bool) -> None:
        """The goal has a saved party of the person's: its use says whether the goal was met (realm/own_parties.py)."""
        if party := goal_team.party_of(self.wiki_root(), slug):
            try:
                own_parties.mark(own_parties.project_id(self.repo_root), slug, met, party)
            except OSError:
                pass                                  # the person's folder cannot be written: the verdict stands

    def accept_one(self, slug: str) -> None:
        root = self.wiki_root()
        try:
            text, *_rest = self.ask("accept", self.accept_prompt(root, slug))
            got = goal_verdict.save(self.state_dir, slug, self.parse(text), by=self.leader_name(slug))
            self._mark_party(slug, got["met"])
        except Exception as e:
            if not isinstance(e, InterruptedError):
                ideas.save_goal_state(self.state_dir, slug, error=f"Not accepted: {_kw()._why(e)}")
            return
        self._ev(event_log.GOAL_ACCEPTED, goal=slug, met=got["met"], by=got["by"], **self.measure())
        if goal_team.party_of(root, slug):                    # a goal that picked a saved party: its use is marked (spec 43 §6.2)
            own_parties.mark(own_parties.project_key(self.repo_root), slug, got["met"])
        self.publish(f"goal:{slug}")
