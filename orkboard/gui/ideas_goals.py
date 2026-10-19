"""A goal by dialog (spec 34 §1, §4; spec 35 §2: a description and a priority, the keeper writes the rest), as
`gui/ideas.py`'s `Ideas` has it: `ideas.goal_save`, `ideas.goal`, `ideas.read_now`, `ideas.words` (New idea's completion).

Saving a goal sends it to the keeper at once (core/idea_goals.py); a goal's state (`reading` → `asks` | `ready`) lives
beside its page (`<state_dir>/goals/<slug>/`). Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from orkboard.core import idea_keeper
from orkboard.gui.ideas_args import IdeasError, _device, _opt, _text
from orkboard.hooks.warder import is_secret
from orkboard.realm import event_log, goal_team, idea_words, ideas, library, roles


DOC_CHARS = 100_000
NO_SECRETS = "That file may hold secrets: open it in your own editor"
HIDDEN_DIRS = (".git", ".orkcraft")           # git's own and the machine's own: never shown


def _kept_back(rel: Path) -> bool:
    """A path `ideas.doc` does not read: what the Warder keeps from the orks (`is_secret`), or under .git/ or .orkcraft/."""
    return is_secret(rel.as_posix()) or any(part in HIDDEN_DIRS for part in rel.parts)


class GoalsMixin:
    def goal_state(self, slug: str) -> dict:
        st = ideas.goal_state(self.state_dir, slug)
        if st["state"] == "reading" and not self.keeper.busy_goal(slug):
            st["state"] = "raw"                        # a reading the host lost (it closed)
        return st

    def _goal_row(self, g: dict) -> dict:
        """A goal as the board lists it: its fields, its state in the keeper's words."""
        st = self.goal_state(g["slug"])
        return {**g, "race": roles.RACES[g["craft"]], "state": st["state"], "state_error": st["error"], "ideas": g["count"]}

    def goal(self, args: dict) -> dict:
        slug = _text(args, "slug", 100)
        g = next((t for t in ideas.tracks(self.root(), make=False) if t["slug"] == slug), None)
        if g is None:
            raise IdeasError("That goal is gone")
        st = self.goal_state(slug)
        page = ideas.track_page(self.root(), slug)
        return {**self._goal_row(g), "description": g["about"],
                "sections": [{"name": n, "text": page.section(n)} for n in ideas.TRACK_SECTIONS],
                "talk": ideas.talk(self.state_dir, slug, goal=True),
                "busy": bool(self.keeper.busy_goal(slug)) or st["state"] == "reading"}

    def words(self, args: dict) -> dict:
        """`{"track"}`: the words New idea completes with (realm/idea_words.py): the goal's title and its ideas' titles,
        then the words of its description, summary, metrics, questions and its ideas' theses, the most used first."""
        root = self.root()
        track = _opt(args, "track")
        g = next((t for t in ideas.tracks(root, make=False) if t["slug"] == track), None)
        if g is None:
            raise IdeasError("That goal is gone")
        mine = ideas.ideas(root, track)
        texts = [g["title"], g["about"], g["summary"], *(m["name"] for m in g["metrics"]), *g["questions"],
                 *(f"{i['title']}\n{i.get('thesis') or ''}" for i in mine)]
        return {"track": track, "words": idea_words.words(texts, [g["title"], *(i["title"] for i in mine)])}

    def goal_save(self, args: dict) -> dict:
        """`{"slug"?, "about", "priority", "title"?, "craft"?, "team"?, "every"?}`: a team's agents of the library are made
        roles of the project (realm/library.py), the person's own agents taken as they are; `every`: the team's checkers
        whose check applies to every idea, not only where it applies (realm/idea_checks.py): a title typed is the person's (never rewritten); spec 34's
        metrics, links and deadline are still taken and kept when given."""
        slug = _opt(args, "slug") or None
        about = args.get("about", "")
        title = args.get("title", "")
        if not isinstance(about, str) or not isinstance(title, str):
            raise IdeasError("about is not text")
        metrics, links = args.get("metrics"), args.get("links")
        if metrics is not None and not isinstance(metrics, list) or links is not None and not isinstance(links, list):
            raise IdeasError("Metrics and links are lists")
        deadline = args.get("deadline") if isinstance(args.get("deadline"), str) else None
        team = None
        if args.get("team") is not None:
            try:
                team = goal_team.clean(args.get("team"))
            except ValueError as e:
                raise IdeasError(str(e)) from None
            if bad := [s for s in team if library.get(s) is None and roles.role(self.state_dir, s) is None]:
                raise IdeasError(f"No agent {bad[0]!r}")
        got, new = ideas.save_goal(self.root(), slug, title[:ideas.TITLE_CHARS], about[:ideas.SECTION_CHARS],
                                   metrics, _opt(args, "priority") or "normal", links, deadline, _opt(args, "craft") or None)
        if team is not None:
            library.install(self.state_dir, [s for s in team if library.get(s) is not None])
            every = args.get("every") if isinstance(args.get("every"), list) else []
            goal_team.set_team(self.root(), got, team, [s for s in every if isinstance(s, str)])
        g = next(t for t in ideas.tracks(self.root(), make=False) if t["slug"] == got)
        self._ev(event_log.GOAL_SAVED, args, goal=got, new=new, metrics=[m["name"] for m in g["metrics"]], links=g["links"],
                 priority=g["priority"], craft=g["craft"], team=g["team"], every=g["every"])
        self._read_goal(got)
        self.changed(f"goal:{got}")
        return {"slug": got}

    def _read_goal(self, slug: str, said: str = "") -> None:
        """The keeper reads the goal at once, in the background; a keeper that may not run (the demo, the spend limit)
        leaves it `raw` with the reason on it."""
        try:
            self.keeper.read_goal(slug, said)
        except idea_keeper.KeeperError as e:
            if said:
                raise IdeasError(str(e)) from None

    def read_now(self, args: dict) -> dict:
        slug = _text(args, "slug", 100)
        try:
            self.keeper.read_now(slug)
        except idea_keeper.KeeperError as e:
            raise IdeasError(str(e)) from None
        self.changed(slug)
        return {"ok": True}

    def doc(self, args: dict) -> dict:
        """A document a goal links, to show in the preview: a path in the repository or a page of the Wiki, read only,
        cut at DOC_CHARS; a Markdown one with its `html` too. Nothing outside those two folders; a URL is never fetched (the page opens it in the browser)."""
        link = _text(args, "path", 300).split("#")[0]
        if "://" in link:
            raise IdeasError("A web link opens in the browser")
        for base in (Path(self.host.repo_root), self.root()):
            path = (base / link.lstrip("/")).resolve()
            if path.is_file() and base.resolve() in path.parents:
                # the name asked for and the file it resolves to (a link to a `.env` is a `.env`)
                if _kept_back(Path(link.lstrip("/"))) or _kept_back(path.relative_to(base.resolve())):
                    raise IdeasError(NO_SECRETS)
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    raise IdeasError("That file cannot be read as text") from None
                out = {"path": link, "text": text[:DOC_CHARS], "truncated": len(text) > DOC_CHARS}
                if path.suffix.lower() in (".md", ".markdown"):      # rendered as the Files pane renders it (spec 37 §8)
                    from orkboard.gui import markdown
                    out["html"] = markdown.render(out["text"])
                return out
        raise IdeasError("That document is not in the repository or the Wiki")

    def goal_event(self, slug: str) -> None:
        """`goal_read` when a goal's reading ends (asks, ready, or raw: it could not)."""
        import time
        st = ideas.goal_state(self.state_dir, slug)["state"]
        now = time.monotonic()
        was, since = self._seen.get(f"goal:{slug}", ("", None))
        if st == was:
            return
        self._seen[f"goal:{slug}"] = (st, now)
        if st in ("asks", "ready", "raw") and was == "reading":
            got = ideas.goal_state(self.state_dir, slug)
            m = got["measure"] or {}
            self._ev(event_log.GOAL_READ, goal=slug, state=st, seconds=round(now - since, 1) if since else None,
                     tier=got["tier"], effort=got["effort"], step=m.get("step") or "goal", prompt_chars=m.get("prompt_chars"),
                     tokens=m.get("tokens"), cost=m.get("cost"))

    def goal_needs(self, goals: list[dict]) -> list[dict[str, Any]]:
        """A goal that asks is in Needs you (spec 35 §10: its own priority, oldest first)."""
        out = []
        for g in goals:
            if g["state"] == "asks":
                out.append({"idea": "", "goal": g["slug"], "kind": "goal", "title": g["title"],
                            "text": g["questions"][0] if g["questions"] else "The keeper asks you about this goal",
                            "questions": g["questions"][:5],
                            "priority": g["priority"], "blocks": False,
                            "at": ideas.goal_state(self.state_dir, g["slug"])["read_time"]})
        return out
