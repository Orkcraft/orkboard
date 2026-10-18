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

from orkcraft.realm import event_log, idea_risk, idea_target, ideas

OTHERS = 40                        # of the other goals' ideas not done, the most the draft is given
MAX_DONE, MAX_OUT, MAX_TOUCHES, MAX_DEPENDS = 5, 3, 30, 8
COMPLEXITY = {"laborer": "S", "warrior": "M", "elder": "L"}


def _kw():
    from orkcraft.core import idea_keeper
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
        what drafts by itself (Add, the clock) waits with `held_until`. False when it was held."""
        if ideas.idea_page(self.wiki_root(), slug) is None:
            raise _kw().KeeperError("That idea is gone")
        if ideas.state(self.state_dir, slug)["state"] != "raw":
            raise _kw().KeeperError("The keeper has read this idea already")
        if why := self._may_run():
            raise _kw().KeeperError(why)
        if self.busy(slug):
            raise _kw().KeeperError("The keeper is busy with this idea: a moment")
        if person:
            self.refuse_spent()
        elif self.hold(slug):
            return False
        ideas.save_state(self.state_dir, slug, queue="now", held_until="", error="")
        self._start(slug, "drafting", lambda: self.draft_one(slug))
        return True

    def draft_prompt(self, root: Path, slug: str) -> str:
        """§0's `draft` context: its goal's Summary and Metrics, the goal's links as paths, the titles of the goal's other
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
        context = idea_target.cut([("The idea, in the person's words", page.section("Gist")),
                                   ("Its goal's summary", (g or {}).get("summary", "")), ("Its goal's metrics", metrics),
                                   ("Its goal's links (paths)", "\n".join(f"- {x}" for x in links)),
                                   ("The goal's other ideas", "\n".join(mine)),
                                   ("The other goals' open ideas", "\n".join(others))], idea_target.CONTEXT["draft"])
        return f"""You are the keeper of this project's Task board. A person wrote an idea under the goal
{(g or {}).get('title', track)}: write its spec straight away. You may read the repository (read only).
{self.reads("draft", links)}

{context}Answer with one JSON object and nothing else:
{{"title": "a short title",
 "gist": "the idea rewritten clearly: its first line one sentence, the thesis; then a few lines if needed",
 "why": "which of its goal's metrics it moves, and why it matters",
 "done_when": ["one to five lines, each one a check that proves it is done"],
 "out": ["zero to three things it does not do"],
 "risks": {{"product": ["…"], "tech": ["…"]}},
 "risk": "low, medium or high",
 "risk_why": "one line: why that risk",
 "touches": ["the repository paths or globs it changes"],
 "depends_on": ["the slugs of listed ideas, of any goal, that must be done first"],
 "size": "S, M or L",
 "before": "the slug of the goal's idea this one should stand before, or empty",
 "questions": ["zero to three questions the person must answer before it can be planned, all at once"]}}
"""

    def draft_one(self, slug: str) -> None:
        """One draft, one shot: the spec written; then `asks`, or `ready` and its plan at once."""
        kw = _kw()
        root = self.wiki_root()
        if ideas.idea_page(root, slug) is None:
            return
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
        self._busy[slug] = "planning"
        ideas.save_state(self.state_dir, slug, state="planning")
        self.publish(slug)
        self.plan_one(slug, "ready")

    # -- one round of questions (§0) -------------------------------------------------------------------------

    def answer(self, slug: str, answers: list[str]) -> None:
        """The person answers the spec's questions together (in their order): one `answer` call, in the background."""
        kw = _kw()
        page = ideas.idea_page(self.wiki_root(), slug)
        if page is None:
            raise kw.KeeperError("That idea is gone")
        questions = ideas.items(page.section("Open questions"))
        if ideas.state(self.state_dir, slug)["state"] != "asks" or not questions:
            raise kw.KeeperError("This idea asks nothing now")
        answers = [" ".join(str(a or "").split())[:2000] for a in answers][:len(questions)]
        if not any(answers):
            raise kw.KeeperError("Answer at least one question")
        if why := self._may_run():
            raise kw.KeeperError(why)
        if self.busy(slug):
            raise kw.KeeperError("The keeper is busy with this idea: a moment")
        self.refuse_spent()
        pairs = [(q, answers[n] if n < len(answers) else "") for n, q in enumerate(questions)]
        ideas.add_turn(self.state_dir, slug, "you", "\n".join(f"{q} — {a or '(no answer)'}" for q, a in pairs), "Open questions")
        self._start(slug, "drafting", lambda: self.answer_one(slug, pairs))

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

    def answer_one(self, slug: str, pairs: list[tuple[str, str]]) -> None:
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
        decisions = [f"{q} — {a}" for q, a in pairs if a] + kw._strings(answer.get("decisions"), 10)
        decisions += [f"Assumed: {x}" for x in kw._strings(answer.get("assumed"), 10)]
        ideas.update(root, slug, written, decisions)
        self.assess(slug)
        ideas.save_state(self.state_dir, slug, state="ready", error="", measure=self.measure())
        self._ev(event_log.IDEA_ANSWERED, idea=slug, answers=sum(1 for _q, a in pairs if a), **self.measure())
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
        if done := ss(answer.get("done_when"), MAX_DONE):
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
        questions = ss(answer.get("questions"), kw.MAX_QUESTIONS)
        sections["Open questions"] = kw._bullets(questions)
        ideas.update(root, slug, sections)
        meta: dict[str, str] = {"risk_model": idea_risk.level(answer.get("risk")),
                                "touches": json.dumps(ss(answer.get("touches"), MAX_TOUCHES, 200), ensure_ascii=False),
                                "depends_on": json.dumps(depends, ensure_ascii=False)}
        size = w(answer.get("size"), 2).upper()
        if size in ideas.SIZES:
            meta["size"] = size
        ideas.set_meta(root, slug, **meta)
        if title := " ".join(w(answer.get("title"), ideas.TITLE_CHARS).split()):
            with ideas.LOCK:
                page = ideas.idea_page(root, slug)
                page.title = title
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
