"""The keeper's reading of a goal (spec 34 §1, spec 35 §2): a goal saved is sent to the keeper at once, read-only, on
the Target's `goal` step — it writes the title (unless the person typed one), the Summary every idea under the goal
starts from, 1–3 measurable Metrics with how each is counted, at most 8 links that exist, and 0–3 questions; `read_at`
is the commit it read (the night's refresh, core/idea_night.py). Split from `idea_keeper.py` (the module's size).

    keeper.read_goal(slug)             # in the background; the goal is `reading`, then `asks` or `ready`
    keeper.read_goal(slug, "answer")   # the person answers its questions: the talk of an idea's, on a goal

A goal's party is in its read (spec 46 §1, §2): by the Target, the leader alone (thrift), with each member's view in its
context (balance), or after each member asked its own questions, all at once (quality, on a goal's first read only).

A mixin of `IdeaKeeper`; `self` has its `ask`, `wiki_root`, `state_dir`, `_start`, `_busy`, `_may_run`, `publish`.
"""
from __future__ import annotations

import datetime as dt
import re
import threading
from pathlib import Path

from orkboard.realm import event_log, goal_team, idea_checks, idea_questions, idea_target, ideas, library, roles, tool_errors
from orkboard.realm.idea_words import short_said

REPLY_CHARS, MAX_QUESTIONS = 4000, 3
MEMBER_QUESTIONS, LINE_CHARS = 2, 200      # what a member asks at most (spec 46 §2); a member's line in the leader's context
NUMBERS = ("zero", "one", "two", "three", "four", "five")


def _kw():
    from orkboard.core import idea_keeper
    return idea_keeper


class GoalMixin:
    # -- the party (spec 46 §1, §2) -----------------------------------------------------------------------------------

    def members(self, root: Path, slug: str) -> list[dict]:
        """A goal's members, in the team's order: the roles of the project that are its builders or checkers; never the
        Grunt, the Taskmaster, its leader, or a slug that is no role."""
        lead = goal_team.leader_of(root, slug)
        got = (roles.role(self.state_dir, s) for s in goal_team.team_of(root, slug) if s not in (roles.GRUNT, roles.TASKMASTER, lead))
        return [r for r in got if r is not None]

    def party_view(self, root: Path, slug: str, members: list[dict]) -> str:
        """Each member's view for the leader's context: name, craft, band, its line, and a checker's check."""
        checks = {c["by"]: c for c in idea_checks.of_team(self.state_dir, [m["slug"] for m in members], goal_team.every_of(root, slug))}
        rows = []
        for m in members:
            agent = library.get(m["slug"])
            line = agent.line if agent is not None else " ".join(str(m.get("instruction") or "").split())[:LINE_CHARS]
            band = "checks" if goal_team.band_of(m["slug"]) == "check" else "builds"
            row = f"- {m['name']} ({m['slug']}; {m.get('craft') or 'engineering'}; {band}): {line}"
            if c := checks.get(m["slug"]):
                row += f"\n  its check applies {c['applies']}; done when: {c['done']}"
            rows.append(row)
        return "\n".join(rows)

    def party_names(self, root: Path, slug: str, members: list[dict]) -> str:
        lead = roles.role(self.state_dir, goal_team.leader_of(root, slug)) or roles.role(self.state_dir, roles.TASKMASTER)
        return "\n".join([f"- {lead['name']} (leads)", *(f"- {m['name']} ({'checks' if goal_team.band_of(m['slug']) == 'check' else 'builds'})"
                                                      for m in members)])

    def ask_prompt(self, root: Path, slug: str, members: list[dict]) -> str:
        """A member's `ask` call (spec 46 §2): the goal, its party, what it needs to know. No tools."""
        g = next(t for t in ideas.tracks(root) if t["slug"] == slug)
        context = idea_target.cut([("The goal", g["about"]), ("Its priority and craft", f"{g['priority']}, {g['craft']}"),
                                   ("The party", self.party_names(root, slug, members))], idea_target.CONTEXT["ask"])
        return f"""A person wrote a goal. Its leader will read the repository and write the goal down; before that, you say what you
need to know from the person, in your own craft. Ask only what changes the goal and what your craft needs: never what
the description already says. {self.reads("ask", [])}

{context}Answer with one JSON object and nothing else; no question is a good answer:
{{"questions": [{{"ask": "a question for the person (at most {MEMBER_QUESTIONS})", "choices": ["two to four likely answers, each at most 40 characters"], "pick": "the index of the one you recommend", "why": "one line: why that one"}}]}}
"""

    def ask_members(self, root: Path, slug: str, members: list[dict]) -> dict[str, list[dict]]:
        """Each member asked once, all at the same time (one thread each, SEATS at most), without tools: its questions by
        its slug. One whose call fails, runs out of its budget or answers nothing adds nothing; a spent window asks none."""
        if not members or self.window_until() is not None:
            return {}
        got: dict[str, list[dict]] = {}
        parent = {k: getattr(self._tls, k, None) for k in ("cancel", "slug", "key")}
        prompt = self.ask_prompt(root, slug, members)

        def one(member: dict) -> None:
            for k, v in parent.items():
                setattr(self._tls, k, v)                           # the goal's own run: its stop stops this call
            self._tls.member = {**member, "member": True}
            try:
                with tool_errors.doing("ask"):
                    text, *_rest = self.ask("ask", prompt, tools=False)
            except Exception:
                return
            try:
                asked = idea_questions.all_of(self.parse(text).get("questions"), MEMBER_QUESTIONS)
            except Exception:
                asked = []
            m = self.measure()
            self._ev(event_log.PARTY_ASKED, goal=slug, by=member["slug"], questions=len(asked), step="ask",
                     prompt_chars=m.get("prompt_chars"), tokens=m.get("tokens"), cost=m.get("cost"))
            if asked:
                got[member["slug"]] = asked

        threads = [threading.Thread(target=one, args=(m,), daemon=True, name="idea-ask") for m in members[:goal_team.SEATS]]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return {m["slug"]: got[m["slug"]] for m in members if m["slug"] in got}

    # -- the read ----------------------------------------------------------------------------------------------------

    def goal_prompt(self, root: Path, slug: str, said: str = "", changed: list[str] | None = None, step: str = "goal",
                    asks: dict[str, list[dict]] | None = None) -> str:
        """§0's `goal` context: its description, its party's views (balance, quality) and what the members asked, priority,
        its links' paths (never their text: it reads them itself, within its bound), the person's answers, the Wiki's
        index; a refresh adds the paths that changed."""
        g = next(t for t in ideas.tracks(root) if t["slug"] == slug)
        try:
            index = (Path(self.index_root()) / "index.md").read_text(encoding="utf-8")
        except OSError:
            index = "(no index yet)"
        links = [f"- {x} (a web link: not fetched)" if re.match(r"^[a-z][a-z0-9+.-]*://", x, re.I) else f"- {x}" for x in g["links"]]
        paths = [x for x in g["links"] if "://" not in x]
        target = self.target()
        members = self.members(root, slug) if target != "thrift" else []
        parts = [("Its description", g["about"])]
        if members:
            parts.append(("Your party", self.party_view(root, slug, members)))
        if asks:
            names = {m["slug"]: m["name"] for m in members}
            parts.append(("What your party asks", "\n".join(f"{names.get(by, by)}:\n" + "\n".join(f"- {idea_questions.line(q)}" for q in qs)
                                                          for by, qs in asks.items())))
        if g["metrics"] and g.get("metrics_by") == "person":
            parts.append(("The metrics the person set", "\n".join(f"- {m['name']} → target {m['target'] or 'not set'}" for m in g["metrics"])))
        if changed is not None:
            parts.append(("The paths that changed since it was read", "\n".join(f"- {c}" for c in changed)))
            paths = [c for c in changed if c in paths or any(c.startswith(p.rstrip("/") + "/") for p in paths)] + paths
        parts += [("Its links (paths)", "\n".join(links)), ("The person says", said), ("The project's Wiki, its map (index.md)", index)]
        context = idea_target.cut([p for p in parts if p[0] != "The person says" or said], idea_target.CONTEXT[step])
        n = idea_target.GOAL_QUESTIONS[target]
        by = ', "by": "the slug of the member whose view the question answers, else empty"' if members else ""
        rule = (" Ask what the party needs to know before the work can be laid out; a member's question only when its answer "
                "changes the goal; never two questions on one thing." if members else "")
        ask_json = ('"questions": [{"ask": "' + f"zero to {NUMBERS[n]} questions" + ' the person must answer to make the goal clear, all at once: '
                    'only what changes it, never what the repository already answers", "choices": ["two to four likely answers, each at most 40 '
                    'characters"], "pick": "the index of the one you recommend", "why": "one line: why that one"' + by + '}],')
        title = (f"Its title is the person's (keep it): {g['title']}" if g["title_by"] == "person"
                 else f"Its title so far (yours to write): {g['title']}")
        return f"""You are the keeper of this project's Task board. A person saved a goal: a description and a priority
(priority {g['priority']}{', deadline ' + g['deadline'] if g['deadline'] else ''}). Write the rest: it is the context
every idea under this goal starts from. {title}.{rule} You may read the repository (read only); web links are named, never
fetched. {self.reads(step, list(dict.fromkeys(paths)))}

{context}""" + """Answer with one JSON object and nothing else:
{"title": "a title of at most 60 characters",
 "short": "its name in two or three words, 24 characters at most",
 "summary": "5 to 12 lines: what the goal means for this repository, the modules and files it touches (as repository paths), what exists already, the constraints",
 "metrics": [{"name": "done when …: one to three, each measurable", "target": "the number or state", "how": "how it is counted, and where"}],
 "links": ["at most 8 repository paths or Wiki pages you read and found relevant"],
 """ + ask_json + """
 "reply": "one short line to the person (only when they said something)"}
"""

    def read_goal(self, slug: str, said: str = "", step: str = "goal", answered: bool = False, party: bool = False) -> None:
        """Send a goal to the keeper at once (read-only, on the Target's `goal` step), or its answer to the person's words;
        `answered`: the person answered its questions (§0's one round: it asks nothing more); `party`: a goal's first read,
        which asks its members first in quality (spec 46 §2), not an Edit's or an answer's."""
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
        self._start(slug, "goal", lambda: self._goal_loop(slug, said, step, answered, party), key)

    def _goal_loop(self, slug: str, said: str, step: str = "goal", answered: bool = False, party: bool = False) -> None:
        key = f"goal:{slug}"
        self.read_goal_one(slug, said, step, answered=answered, party=party)
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
                      answered: bool = False, party: bool = False) -> None:
        kw = _kw()
        root = self.wiki_root()
        ideas.save_goal_state(self.state_dir, slug, state="reading", error="")
        self.publish(f"goal:{slug}")
        asks: dict[str, list[dict]] = {}
        if party and step == "goal" and not answered and not said and self.target() == "quality":
            asks = self.ask_members(root, slug, self.members(root, slug))            # before the leader's call (spec 46 §2)
        try:
            text, *_rest = self.ask(step, self.goal_prompt(root, slug, said, changed, step, asks))
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
        members = self.members(root, slug) if self.target() != "thrift" else []
        asked = [] if answered else idea_questions.all_of(answer.get("questions"), idea_target.GOAL_QUESTIONS[self.target()])
        questions = [idea_questions.line(q) for q in asked]
        links = self._links_found(root, kw._strings(answer.get("links"), 20, 300)) if "links" in answer else None
        title = kw._words(answer.get("title"), ideas.TITLE_KEEPER)
        ideas.write_goal_reading(root, slug, kw._words(answer.get("summary"), 3000), how, questions, title=title,
                                 metrics=metrics, links=links,
                                 short=short_said(answer.get("short"), title) if title else "")
        if said and (reply := kw._words(answer.get("reply"), REPLY_CHARS)):
            ideas.add_turn(self.state_dir, slug, "keeper", reply, goal=True)
        tier, effort = self.picked()
        lead = goal_team.leader_of(root, slug)
        by = idea_questions.asked_by(asked, [m["slug"] for m in members], lead)        # who asks each Open question (spec 46 §1)
        ideas.save_goal_state(self.state_dir, slug, state="asks" if questions else "ready", error="", read_at=self.head(),
                              read_time=dt.datetime.now().isoformat(timespec="seconds"), tier=tier, effort=effort,
                              measure=self.measure(), asks_by=by, party=len(members), by_party=sum(1 for b in by if b != lead))
