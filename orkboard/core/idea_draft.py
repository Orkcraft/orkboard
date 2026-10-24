"""The draft (docs/specs/35-goals-window.md §0, §3, §4): an idea straight to its spec, in one read-only call; its
questions answered at once in one more (`answer`, which asks nothing more); its Stages and its risk written by code. A
mixin of `IdeaKeeper`, as `idea_goals.py` is.

    keeper.draft(slug)              # in the background: Gist · Why · Done when · Out · Risks · Depends on · Open questions
    keeper.draft_one(slug)          # the same, on this thread (the night's way)
    keeper.answer(slug, answers)    # the person's answers, in the questions' order: the rest of the spec, then the plan
    keeper.write_stages(slug, plan) # Stages from plan.json, in waves by `after`, S / M / L from the planned tier
    keeper.assess(slug)             # the risk: the model's, raised by realm/idea_risk.py's triggers

Questions go to Needs you (`asks`); none, and the plan follows at once. `self` has the keeper's `ask`, `wiki_root`,
`state_dir`, `_start`, `_busy`, `_may_run`, `hold`, `refuse_spent`, `publish`, `plan_one`, `settings`.
"""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

from orkboard.realm import (event_log, goal_team, goal_types, idea_checks, idea_lens, idea_questions, idea_risk, idea_target,
                            ideas, pitches, releases, roles)
from orkboard.realm.idea_words import short_said

OTHERS = 40                        # of the other goals' ideas not done, the most the draft is given
MAX_DONE, MAX_OUT, MAX_TOUCHES, MAX_DEPENDS = 5, 3, 30, 8
COMPLEXITY = {"laborer": "S", "warrior": "M", "elder": "L"}


def _kw():
    from orkboard.core import idea_keeper
    return idea_keeper


def _json_list(text: str) -> list[str]:
    try:
        got = json.loads(text) if str(text or "").strip() else []
    except ValueError:
        return []
    return [str(x) for x in got if isinstance(x, str)] if isinstance(got, list) else []


def stages(plan: dict) -> str:
    """The tasks in waves by `after`: `1. k1 The table (S) ∥ k2 The form (M)` · `2. k3 The checks (L), after k1`."""
    tasks = [t for t in plan.get("tasks") or [] if isinstance(t, dict)]
    wave: dict[str, int] = {}
    for t in tasks:                                  # `after` names only earlier tasks (make_plan)
        wave[t["id"]] = 1 + max((wave.get(a, 0) for a in t.get("after") or []), default=0)
    lines = []
    for n in sorted(set(wave.values())):
        row = [f"{t['id']} {t.get('title', '')} ({COMPLEXITY.get(t.get('tier'), 'M')})"
               + (f", after {', '.join(t['after'])}" if t.get("after") else "") for t in tasks if wave[t["id"]] == n]
        lines.append(f"{n}. " + " ∥ ".join(row))
    return "\n".join(lines)


def depends_ok(root: Path, slug: str, wanted: list[str]) -> list[str]:
    """Of the slugs an idea would depend on, those that exist and do not close a cycle."""
    graph = {i["slug"]: _json_list((ideas.idea_page(root, i["slug"]) or ideas.Page()).get("depends_on"))
             for i in ideas.ideas(root)}
    out: list[str] = []

    def reaches(start: str, goal: str) -> bool:
        seen, todo = set(), [start]
        while todo:
            s = todo.pop()
            if s == goal:
                return True
            if s not in seen:
                seen.add(s)
                todo += graph.get(s, []) + (out if s == slug else [])
        return False

    for d in wanted:
        if d in graph and d != slug and d not in out and not reaches(d, slug):
            out.append(d)
    return out[:MAX_DEPENDS]


class DraftMixin:
    def draft(self, slug: str, person: bool = False) -> bool:
        """Draft a `raw` idea at once, in the background. In a spent window the person's ask (Process now) is refused;
        what drafts by itself (Add, the clock) waits with `held_until`. False when it was held. A pitch is judged instead
        (core/idea_judge.py)."""
        if ideas.idea_page(self.wiki_root(), slug) is None:
            raise _kw().KeeperError("That goal is gone")
        if self.is_pitch(slug):
            return self.judge(slug, person)
        if ideas.state(self.state_dir, slug)["state"] != "raw":
            raise _kw().KeeperError("The keeper has read this goal already")
        if why := self._may_run():
            raise _kw().KeeperError(why)
        if self.busy(slug):
            raise _kw().KeeperError("The keeper is busy with this goal: a moment")
        if person:
            self.refuse_spent()
        elif self.hold(slug):
            return False
        ideas.save_state(self.state_dir, slug, queue="now", held_until="", error="")
        self._start(slug, "drafting", lambda: self.draft_one(slug))
        return True

    def team_checks(self, root: Path, slug: str) -> list[dict]:
        """The checks of the idea's goal's team (realm/idea_checks.py): what the team holds the idea to."""
        return idea_checks.of_team(self.state_dir, goal_team.for_idea(root, slug), goal_team.every_for_idea(root, slug))

    def idea_checks(self, root: Path, slug: str) -> list[dict]:
        """What the idea's draft said of its team's checks (the page's `checks`); every check applies when it said none."""
        page = ideas.idea_page(root, slug)
        said = ideas._json_list(page.get("checks")) if page is not None else []
        return idea_checks.kept(said, self.team_checks(root, slug))

    def role_of(self, task: dict) -> dict:
        """The role a task runs as: the one its plan gave it from the goal's team, else its tag's in the project."""
        return (roles.role(self.state_dir, str(task.get("role") or "")) if task.get("role") else None) \
            or roles.role_for(self.state_dir, str(task.get("kind") or ""))

    def team_lines(self, team: list[str]) -> str:
        """The goal's team for the plan prompt: who does which tags (a task of a tag no one takes goes to Grunt)."""
        known = roles.kinds(self.state_dir)
        rows = [f"{r['name']} ({', '.join(sorted(roles.takes_of(r, known))) or 'code'})" for s in team if (r := roles.role(self.state_dir, s))]
        return ("\n- The goal's team, by the tags each does: " + "; ".join(rows) + ". Tag each task so one of them does it.") if rows else ""

    def draft_prompt(self, root: Path, slug: str) -> str:
        """§0's `draft` context: its goal's Summary and, when it has some, its Metrics, the goal's links as paths, the titles of the goal's other
        ideas and of the other goals' open ideas (≤ 40), the person's text."""
        page = ideas.idea_page(root, slug)
        track = page.get("track") or ideas.GENERAL
        g = next((t for t in ideas.tracks(root, make=False) if t["slug"] == track), None)
        mine, others = [], []
        for i in ideas.ideas(root):
            if i["slug"] == slug:
                continue
            st = ideas.state(self.state_dir, i["slug"])["state"]
            if i["track"] == track:
                mine.append(f"- {i['slug']}: {i['title']} ({st})")
            elif st != "done" and len(others) < OTHERS:
                others.append(f"- {i['slug']}: {i['title']} (goal {i['track']})")
        metrics = "\n".join(f"- {m['name']}" + (f" → {m['target']}" if m.get("target") else "")
                            + (f" (counted: {m['how']})" if m.get("how") else "") for m in (g or {}).get("metrics") or [])
        links = [x for x in (g or {}).get("links") or [] if "://" not in x]
        spared = {k["by"] for k in self.idea_checks(root, slug) if k.get("skipped")}          # a check the person skipped: not asked of
        checks = [c for c in self.team_checks(root, slug) if c["by"] not in spared]
        checks_json = ',\n "checks": [{"by": "<a check\'s id>", "applies": true, "why": "when it does not apply: why, in one line"}]' if checks else ""
        context = idea_target.cut([("The idea, in the person's words", page.section("Gist")),
                                   ("Its goal's summary", (g or {}).get("summary", "")),
                                   *([("Its goal's metrics", metrics)] if metrics else []),          # only when the party has some (spec 50 §2.5)
                                   ("Its goal's links (paths)", "\n".join(f"- {x}" for x in links)),
                                   ("The goal's other ideas", "\n".join(mine)),
                                   ("The other goals' open ideas", "\n".join(others))], idea_target.CONTEXT["draft"])
        why = "which of its goal's metrics it moves, and why it matters" if metrics else "why it matters"
        return f"""You are the keeper of this project's Task board. A person wrote an idea under the goal
{(g or {}).get('title', track)}: write its spec straight away. You may read the repository (read only).
{self.reads("draft", links)}
{idea_lens.attached(self.state_dir, slug)}{goal_types.prompt_line(self.state_dir, slug)}{releases.prompt_lines(root, self.state_dir, slug)}{idea_checks.draft_lines(checks)}{pitches.sent_lines(root, self.state_dir, slug)}
{context}Answer with one JSON object and nothing else:
{{"title": "a short title",
 "short": "its name in two or three words, 24 characters at most",
 "gist": "the idea rewritten clearly: its first line one sentence, the thesis; then a few lines if needed",
 "why": "{why}",
 "done_when": ["one to five lines, each one a check that proves it is done"],
 "out": ["zero to three things it does not do"],
 "risks": {{"product": ["…"], "tech": ["…"]}},
 "risk": "low, medium or high",
 "risk_why": "one line: why that risk",
 "touches": ["the repository paths or globs it changes"],
 "depends_on": ["the slugs of listed ideas, of any goal, that must be done first"],
 "size": "S, M or L",
 "before": "the slug of the goal's idea this one should stand before, or empty",
 "questions": [{{"ask": "zero to three questions the person must answer before it can be planned, all at once: only what changes the plan, never what the repository, the goal or the person's text already answers", "choices": ["two to four likely answers, each at most 40 characters"], "pick": "the index of the one you recommend", "why": "one line: why that one"}}]{checks_json}}}
"""

    def draft_one(self, slug: str) -> None:
        """One draft, one shot: the spec written; then `asks`, or `ready` and its plan at once (a pitch: judged instead)."""
        kw = _kw()
        root = self.wiki_root()
        if ideas.idea_page(root, slug) is None:
            return
        if self.is_pitch(slug):
            return self.judge_one(slug)
        began = time.monotonic()
        ideas.save_state(self.state_dir, slug, state="reading", error="", held_until="")
        self.publish(slug)
        try:
            text, *_rest = self.ask("draft", self.draft_prompt(root, slug))
            answer = self.parse(text)
        except Exception as e:                      # the idea stays new; stopped by the person: it waits for them
            stopped = isinstance(e, InterruptedError)
            ideas.save_state(self.state_dir, slug, state="raw", error="" if stopped else kw._why(e),
                             **({"queue": "hold"} if stopped else {}))
            return
        questions = self.write_draft(root, slug, answer)
        ideas.save_state(self.state_dir, slug, state="asks" if questions else "ready", error="", measure=self.measure(),
                         batch_at=dt.datetime.now().isoformat(timespec="seconds"))
        tier, effort = self.picked()
        page = ideas.idea_page(root, slug)
        self._ev(event_log.IDEA_DRAFTED, idea=slug, risk=idea_risk.level(page.get("risk")),
                 triggers=_json_list(page.get("risk_triggers")), questions=len(questions), tier=tier, effort=effort,
                 seconds=round(time.monotonic() - began, 1), **self.measure())
        self.publish(slug)
        if not questions:
            self.plan_now(slug)

    def plan_now(self, slug: str) -> None:
        """The plan that follows a spec by itself, on this thread (it waits with `held_until` in a spent window)."""
        if self.hold(slug):
            return
        was = self._busy.get(slug)
        self._busy[slug] = "planning"
        ideas.save_state(self.state_dir, slug, state="planning")
        self.publish(slug)
        try:
            self.plan_one(slug, "ready")
        finally:                                     # the run that holds the idea ends it; else it ends here
            if was is None:
                self._busy.pop(slug, None)
            else:
                self._busy[slug] = was

    # -- one round of questions (§0) -------------------------------------------------------------------------

    def answer(self, slug: str, answers: list[str], decide: bool = False) -> None:
        """The person answers the spec's questions together (in their order): one `answer` call, in the background.
        `decide` (Let the Taskmaster decide, spec 41 §9): each question answered with its recommended choice, one
        without with "(no answer: decide)"."""
        kw = _kw()
        page = ideas.idea_page(self.wiki_root(), slug)
        if page is None:
            raise kw.KeeperError("That goal is gone")
        if self.is_pitch(slug):
            raise kw.KeeperError(kw.PITCH_NOT_BUILT)
        questions = ideas.items(page.section("Open questions"))
        if ideas.state(self.state_dir, slug)["state"] != "asks" or not questions:
            raise kw.KeeperError("This goal asks nothing now")
        if decide:
            answers = idea_questions.picks(questions)
        answers = [" ".join(str(a or "").split())[:2000] for a in answers][:len(questions)]
        if not any(answers) and not decide:
            raise kw.KeeperError("Answer at least one question")
        if why := self._may_run():
            raise kw.KeeperError(why)
        if self.busy(slug):
            raise kw.KeeperError("The keeper is busy with this goal: a moment")
        self.refuse_spent()
        pairs = [(q, answers[n] if n < len(answers) else "") for n, q in enumerate(questions)]
        said = "\n".join(f"{idea_questions.parse(q)['ask']} — {a or '(no answer)'}" for q, a in pairs)
        ideas.add_turn(self.state_dir, slug, "you", f"Left to the Taskmaster:\n{said}" if decide else said,
                       "Open questions")
        self._start(slug, "drafting", lambda: self.answer_one(slug, pairs, decide))

    def answer_prompt(self, root: Path, slug: str, pairs: list[tuple[str, str]]) -> str:
        """§0's `answer` context: the spec's sections but Decisions and Stages, the questions with the answers."""
        page = ideas.idea_page(root, slug)
        names = [n for n in ideas.SECTIONS if n not in ("Decisions", "Stages", "Open questions")]
        parts = [("The questions and the person's answers", "\n".join(f"- {q}\n  {a or '(no answer: decide)'}" for q, a in pairs))]
        parts += [(n, page.section(n)) for n in names]
        context = idea_target.cut(parts, idea_target.CONTEXT["answer"])
        touches = _json_list(page.get("touches"))
        return f"""You are the keeper of this project's Task board. The person answered the questions of the spec
{page.title}. Write the rest of the spec from their answers. Ask nothing more: where you are unsure, decide, and say what
you assumed. {self.reads("answer", touches)} You may read the repository (read only).

{context}Answer with one JSON object and nothing else:
{{"sections": {{"<a section's name>": "its whole new text"}},
 "decisions": ["one line for each thing the answers decided"],
 "assumed": ["one line for each thing you assumed where you were unsure"]}}
Section names: {", ".join(names)}."""

    def answer_one(self, slug: str, pairs: list[tuple[str, str]], decided: bool = False) -> None:
        kw = _kw()
        root = self.wiki_root()
        ideas.save_state(self.state_dir, slug, state="reading", error="")
        self.publish(slug)
        try:
            text, *_rest = self.ask("answer", self.answer_prompt(root, slug, pairs))
            answer = self.parse(text)
        except Exception as e:
            ideas.save_state(self.state_dir, slug, state="asks", error="" if isinstance(e, InterruptedError) else kw._why(e))
            return
        got = answer.get("sections") if isinstance(answer.get("sections"), dict) else {}
        written = {n: kw._words(v, ideas.SECTION_CHARS) for n, v in got.items()
                   if n in ideas.SECTIONS and n not in ("Decisions", "Stages", "Open questions") and isinstance(v, str)}
        written["Open questions"] = ""               # one round: a question in its answer is dropped
        mark = " (the Taskmaster's pick)" if decided else ""
        decisions = [f"{idea_questions.parse(q)['ask']} — {a}{mark}" for q, a in pairs if a]
        decisions += kw._strings(answer.get("decisions"), 10)
        decisions += [f"Assumed: {x}" for x in kw._strings(answer.get("assumed"), 10)]
        ideas.update(root, slug, written, decisions)
        self.assess(slug)
        ideas.save_state(self.state_dir, slug, state="ready", error="", measure=self.measure())
        how = idea_questions.tally([q for q, _a in pairs], [a for _q, a in pairs])
        self._ev(event_log.IDEA_ANSWERED, idea=slug, answers=sum(1 for _q, a in pairs if a), decided=decided,
                 **({"picked": 0, "recommended": 0, "typed": 0} if decided else how), **self.measure())
        self.publish(slug)
        self.plan_now(slug)

    def write_draft(self, root: Path, slug: str, answer: dict) -> list[str]:
        """The draft's answer into the page, strictly (only known keys); its questions."""
        kw = _kw()
        w, ss = kw._words, kw._strings
        sections: dict[str, str] = {}
        if gist := w(answer.get("gist"), ideas.SECTION_CHARS):
            sections["Gist"] = gist
        if why := w(answer.get("why"), ideas.SECTION_CHARS):
            sections["Why"] = why
        checks = self.team_checks(root, slug)
        skipped = {k["by"] for k in self.idea_checks(root, slug) if k.get("skipped")}     # what the person skipped stays skipped
        said = [x | ({"skipped": True} if isinstance(x, dict) and x.get("by") in skipped else {}) for x in answer.get("checks") or [] if isinstance(x, dict)]
        said += [{"by": b, "skipped": True} for b in skipped if not any(x.get("by") == b for x in said)]
        kept_checks = idea_checks.kept(said, checks)
        done = ss(answer.get("done_when"), MAX_DONE)
        go = idea_checks.on(kept_checks)
        done += [c["done"] for c in checks if c["by"] in go and c["done"] not in done]
        if done:                                     # a check that applies: its line, whether the draft wrote it or not
            sections["Done when"] = kw._bullets(done)
        sections["Out"] = kw._bullets(ss(answer.get("out"), MAX_OUT))
        risks = answer.get("risks") if isinstance(answer.get("risks"), dict) else {}
        body = []
        for key, label in (("product", "Product"), ("tech", "Tech")):
            if got := ss(risks.get(key), 6):
                body.append(f"{label}:\n{kw._bullets(got)}")
        if line := w(answer.get("risk_why"), 300):
            body.insert(0, line)
        sections["Risks"] = "\n\n".join(body)
        depends = depends_ok(root, slug, ss(answer.get("depends_on"), MAX_DEPENDS, 60))
        titles = {i["slug"]: i["title"] for i in ideas.ideas(root)}
        sections["Depends on"] = kw._bullets([f"{d} — {titles.get(d, d)}" for d in depends])
        questions = [idea_questions.line(q) for q in idea_questions.all_of(answer.get("questions"), kw.MAX_QUESTIONS)]
        sections["Open questions"] = kw._bullets(questions)
        ideas.update(root, slug, sections)
        meta: dict[str, str] = {"risk_model": idea_risk.level(answer.get("risk")),
                                "touches": json.dumps(ss(answer.get("touches"), MAX_TOUCHES, 200), ensure_ascii=False),
                                "depends_on": json.dumps(depends, ensure_ascii=False),
                                "checks": json.dumps(kept_checks)}
        size = w(answer.get("size"), 2).upper()
        if size in ideas.SIZES:
            meta["size"] = size
        ideas.set_meta(root, slug, **meta)
        if title := " ".join(w(answer.get("title"), ideas.TITLE_CHARS).split()):
            with ideas.LOCK:
                page = ideas.idea_page(root, slug)
                page.title = title
                page.set("short", short_said(answer.get("short"), title))
                ideas._write(root / ideas.IDEAS / f"{slug}.md", page.text())
                ideas._reindex(root)
        self.assess(slug)
        self._place(root, slug, w(answer.get("before"), 60))
        return questions

    def write_stages(self, slug: str, plan: dict) -> None:
        ideas.update(self.wiki_root(), slug, {"Stages": stages(plan)})

    def assess(self, slug: str) -> str | None:
        """The idea's risk from its page and plan, written: front matter `risk`, `risk_triggers`, and the Risks
        section's first line. The risk it had when it changed, else None."""
        root = self.wiki_root()
        with ideas.LOCK:
            page = ideas.idea_page(root, slug)
            if page is None:
                return None
            plan = ideas.plan(self.state_dir, slug) or {}
            tasks = [t for t in plan.get("tasks") or [] if isinstance(t, dict)]
            rest = idea_risk.strip_line(page.section("Risks"))
            texts = [page.title, page.section("Out"), rest]
            texts += [f"{t.get('title', '')}\n{t.get('brief', '')}" for t in tasks]
            got = idea_risk.assess(_json_list(page.get("touches")), texts, len(tasks), page.get("risk_model") or "low",
                                   (self.settings() or {}).get("risk_paths") or [])
            was = page.get("risk")
            page.set("risk", got.risk)
            page.set("risk_triggers", json.dumps(got.triggers, ensure_ascii=False))
            page.set_section("Risks", got.line + (f"\n\n{rest.strip()}" if rest.strip() else ""))
            ideas._write(root / ideas.IDEAS / f"{slug}.md", page.text())
        return was if was and was != got.risk else None
