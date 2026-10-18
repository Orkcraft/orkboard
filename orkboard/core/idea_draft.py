"""The draft (docs/specs/35-goals-window.md §3, §4): an idea straight to its spec, in one read-only call that starts the
idea's session; its Stages and its risk written by code. A mixin of `IdeaKeeper`, as `idea_goals.py` is.

    keeper.draft(slug)              # in the background: Gist · Why · Done when · Out · Risks · Depends on · Open questions
    keeper.draft_one(slug)          # the same, on this thread (the night's way)
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

from orkcraft.realm import event_log, idea_risk, ideas

INDEX_CHARS, PAGE_CHARS, GOAL_CHARS = 6000, 20_000, 3000
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
        page = ideas.idea_page(root, slug)
        track = page.get("track") or ideas.GENERAL
        goals = {t["slug"]: t for t in ideas.tracks(root, make=False)}
        g = goals.get(track)
        try:
            index = (root / "index.md").read_text(encoding="utf-8")[:INDEX_CHARS]
        except OSError:
            index = "(no index yet)"
        goal = "(no goal)"
        if g is not None:
            metrics = "\n".join(f"- {m['name']}" + (f" → {m['target']}" if m.get("target") else "")
                                + (f" (counted: {m['how']})" if m.get("how") else "") for m in g["metrics"]) or "(none yet)"
            links = "\n".join(f"- {x}" for x in g["links"]) or "(none)"
            goal = (f"{g['title']} (priority {g['priority']})\nDescription:\n{g['about'][:GOAL_CHARS]}\n\n"
                    f"Summary:\n{g['summary'][:GOAL_CHARS]}\n\nMetrics:\n{metrics}\n\n"
                    f"Its links (start from these files; search the repository only for what they don't cover):\n{links}")
        mine, others = [], []
        for i in ideas.ideas(root):
            if i["slug"] == slug:
                continue
            st = ideas.state(self.state_dir, i["slug"])["state"]
            if i["track"] == track:
                mine.append(f"- {i['slug']}: {i['title']} ({st})")
            elif st != "done" and len(others) < OTHERS:
                others.append(f"- {i['slug']}: {i['title']} (goal {i['track']})")
        return f"""You are the keeper of this project's Task board. A person wrote an idea under a goal: write its spec
straight away. You may read the repository (read only).

The goal:
{goal}

The goal's other ideas:
{chr(10).join(mine) or "(none)"}

The other goals' ideas not done:
{chr(10).join(others) or "(none)"}

The project's Wiki, its map (index.md):
{index}

The idea, in the person's words:
{page.section("Gist")[:PAGE_CHARS]}

Answer with one JSON object and nothing else:
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
 "questions": ["zero to three questions the person must answer before it can be planned"]}}
"""

    def draft_one(self, slug: str) -> None:
        """One draft: the spec written, the idea's session kept; then `asks`, or `ready` and its plan at once."""
        kw = _kw()
        root = self.wiki_root()
        if ideas.idea_page(root, slug) is None:
            return
        began = time.monotonic()
        ideas.save_state(self.state_dir, slug, state="reading", error="", held_until="")
        self.publish(slug)
        try:
            text, _cost, tokens, session = self.ask("draft", self.draft_prompt(root, slug))
            answer = kw.first_json(text)
            if answer is None:
                raise kw.KeeperError("the keeper's answer was not the JSON it was asked for")
        except Exception as e:                      # the idea stays new; stopped by the person: it waits for them
            stopped = isinstance(e, InterruptedError)
            ideas.save_state(self.state_dir, slug, state="raw", error="" if stopped else kw._why(e),
                             **({"queue": "hold"} if stopped else {}))
            return
        questions = self.write_draft(root, slug, answer)
        risk = idea_risk.level(ideas.idea_page(root, slug).get("risk"))
        ideas.save_state(self.state_dir, slug, state="asks" if questions else "ready", error="", session=session or "",
                         session_at=dt.datetime.now().isoformat(timespec="seconds"),
                         context=self._context(session, tokens) if session else 0,
                         batch_at=dt.datetime.now().isoformat(timespec="seconds"))
        tier, effort = self.picked()
        page = ideas.idea_page(root, slug)
        self._ev(event_log.IDEA_DRAFTED, idea=slug, risk=risk, triggers=_json_list(page.get("risk_triggers")),
                 questions=len(questions), tier=tier, effort=effort, seconds=round(time.monotonic() - began, 1))
        self.publish(slug)
        if not questions and not self.hold(slug):
            self._busy[slug] = "planning"
            ideas.save_state(self.state_dir, slug, state="planning")
            self.publish(slug)
            self.plan_one(slug, "ready")

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
