"""The keeper's reading of a goal (spec 34 §1, spec 35 §2): a goal saved is sent to the keeper at once, read-only, on
the Target's `goal` step — it writes the title (unless the person typed one), the Summary every idea under the goal
starts from, 1–3 measurable Metrics with how each is counted, at most 8 links that exist, and 0–3 questions; `read_at`
is the commit it read (the night's refresh, core/idea_night.py). Split from `idea_keeper.py` (the module's size).

    keeper.read_goal(slug)             # in the background; the goal is `reading`, then `asks` or `ready`
    keeper.read_goal(slug, "answer")   # the person answers its questions: the talk of an idea's, on a goal

A mixin of `IdeaKeeper`; `self` has its `ask`, `wiki_root`, `state_dir`, `_start`, `_busy`, `_may_run`, `publish`.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from orkboard.realm import idea_target, ideas

REPLY_CHARS, MAX_QUESTIONS = 4000, 3


def _kw():
    from orkboard.core import idea_keeper
    return idea_keeper


class GoalMixin:
    def goal_prompt(self, root: Path, slug: str, said: str = "", changed: list[str] | None = None, step: str = "goal") -> str:
        """§0's `goal` context: its description, priority, its links' paths (never their text: it reads them itself,
        within its bound), the person's answers, the Wiki's index; a refresh adds the paths that changed."""
        g = next(t for t in ideas.tracks(root) if t["slug"] == slug)
        try:
            index = (Path(self.index_root()) / "index.md").read_text(encoding="utf-8")
        except OSError:
            index = "(no index yet)"
        links = [f"- {x} (a web link: not fetched)" if re.match(r"^[a-z][a-z0-9+.-]*://", x, re.I) else f"- {x}" for x in g["links"]]
        paths = [x for x in g["links"] if "://" not in x]
        parts = [("Its description", g["about"])]
        if g["metrics"] and g.get("metrics_by") == "person":
            parts.append(("The metrics the person set", "\n".join(f"- {m['name']} → target {m['target'] or 'not set'}" for m in g["metrics"])))
        if changed is not None:
            parts.append(("The paths that changed since it was read", "\n".join(f"- {c}" for c in changed)))
            paths = [c for c in changed if c in paths or any(c.startswith(p.rstrip("/") + "/") for p in paths)] + paths
        parts += [("Its links (paths)", "\n".join(links)), ("The person says", said), ("The project's Wiki, its map (index.md)", index)]
        context = idea_target.cut([p for p in parts if p[0] != "The person says" or said], idea_target.CONTEXT[step])
        title = (f"Its title is the person's (keep it): {g['title']}" if g["title_by"] == "person"
                 else f"Its title so far (yours to write): {g['title']}")
        return f"""You are the keeper of this project's Task board. A person saved a goal: a description and a priority
(priority {g['priority']}{', deadline ' + g['deadline'] if g['deadline'] else ''}). Write the rest: it is the context
every idea under this goal starts from. {title}. You may read the repository (read only); web links are named, never
fetched. {self.reads(step, list(dict.fromkeys(paths)))}

{context}""" + """Answer with one JSON object and nothing else:
{"title": "a title of at most 60 characters",
 "summary": "5 to 12 lines: what the goal means for this repository, the modules and files it touches (as repository paths), what exists already, the constraints",
 "metrics": [{"name": "done when …: one to three, each measurable", "target": "the number or state", "how": "how it is counted, and where"}],
 "links": ["at most 8 repository paths or Wiki pages you read and found relevant"],
 "questions": ["zero to three questions the person must answer to make the goal clear, all at once"],
 "reply": "one short line to the person (only when they said something)"}
"""

    def read_goal(self, slug: str, said: str = "", step: str = "goal", answered: bool = False) -> None:
        """Send a goal to the keeper at once (read-only, on the Target's `goal` step), or its answer to the person's words;
        `answered`: the person answered its questions (§0's one round: it asks nothing more)."""
        if not any(t["slug"] == slug for t in ideas.tracks(self.wiki_root())):
            raise _kw().KeeperError("That goal is gone")
        said = str(said or "").strip()[:ideas.SECTION_CHARS]
        if why := self._may_run():
            ideas.save_goal_state(self.state_dir, slug, state="raw", error=why)
            raise _kw().KeeperError(why)
        key = f"goal:{slug}"
        if said:
            ideas.add_turn(self.state_dir, slug, "you", said, goal=True)
        if self.busy(key):                         # saved again while it reads: it reads once more after this
            self._again.add(key)
            return
        ideas.save_goal_state(self.state_dir, slug, state="reading", error="")
        self._start(slug, "goal", lambda: self._goal_loop(slug, said, step, answered), key)

    def _goal_loop(self, slug: str, said: str, step: str = "goal", answered: bool = False) -> None:
        key = f"goal:{slug}"
        self.read_goal_one(slug, said, step, answered=answered)
        while key in self._again:
            self._again.discard(key)
            self.read_goal_one(slug, "", step)

    def _links_found(self, root: Path, links: list[str]) -> list[str]:
        """Of the links the keeper names, the repository paths and Wiki pages that exist; never a URL."""
        out = []
        for link in links:
            link = link.split("#")[0].strip().lstrip("/")
            if not link or "://" in link or link.startswith("~"):
                continue
            for base in (self.repo_root, root):
                path = (Path(base) / link).resolve()
                if path.exists() and (Path(base).resolve() in path.parents or path == Path(base).resolve()):
                    out.append(link)
                    break
        return list(dict.fromkeys(out))[:ideas.KEEPER_LINKS]

    def head(self) -> str:
        """The repository's commit now (`git rev-parse HEAD`), "" when it has none."""
        from orkboard.realm.idea_git import _git
        try:
            proc = _git(self.repo_root, "rev-parse", "HEAD")
        except Exception:
            return ""
        return proc.stdout.strip() if proc.returncode == 0 else ""

    def read_goal_one(self, slug: str, said: str = "", step: str = "goal", changed: list[str] | None = None,
                      answered: bool = False) -> None:
        kw = _kw()
        root = self.wiki_root()
        ideas.save_goal_state(self.state_dir, slug, state="reading", error="")
        self.publish(f"goal:{slug}")
        try:
            text, *_rest = self.ask(step, self.goal_prompt(root, slug, said, changed, step))
            answer = self.parse(text)
        except Exception as e:
            ideas.save_goal_state(self.state_dir, slug, state="raw", error=kw._why(e), measure=self.measure())
            return
        how: dict[str, str] = {}
        metrics = []
        for i, m in enumerate(answer.get("metrics") if isinstance(answer.get("metrics"), list) else []):
            if not isinstance(m, dict):
                continue
            if kw._words(m.get("how"), 300):
                how[kw._words(m.get("name"), 300) or str(i)] = kw._words(m.get("how"), 300)
            if kw._words(m.get("name"), 300):
                metrics.append({k: kw._words(m.get(k), 300) for k in ("name", "target", "how")})
        questions = [] if answered else kw._strings(answer.get("questions"), MAX_QUESTIONS)
        links = self._links_found(root, kw._strings(answer.get("links"), 20, 300)) if "links" in answer else None
        ideas.write_goal_reading(root, slug, kw._words(answer.get("summary"), 3000), how, questions,
                                 title=kw._words(answer.get("title"), ideas.TITLE_KEEPER), metrics=metrics, links=links)
        if said and (reply := kw._words(answer.get("reply"), REPLY_CHARS)):
            ideas.add_turn(self.state_dir, slug, "keeper", reply, goal=True)
        tier, effort = self.picked()
        ideas.save_goal_state(self.state_dir, slug, state="asks" if questions else "ready", error="", read_at=self.head(),
                              read_time=dt.datetime.now().isoformat(timespec="seconds"), tier=tier, effort=effort,
                              measure=self.measure())
