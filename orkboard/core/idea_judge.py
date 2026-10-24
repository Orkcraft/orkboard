"""A pitch judged (docs/specs/65-ideation.md §3, §7): its four views, each alone, then the case against, then the Investor's decision;
three read-only steps, each call one shot and measured, each as its role (`ask(..., as_role=)`: the role's voice and instruction
first, its own model when the person set one on Agents). A mixin of `IdeaKeeper`, as `idea_draft.py` is.

    keeper.judge(slug)              # in the background, as the pitch's run: raw, failed, judged or passed → judging → judged
    keeper.judge_one(slug)          # the same, on this thread (the night's way)
    keeper.is_pitch(slug)           # its party is led by the Investor: it is judged, never drafted or planned

- **The views** (`pitch_view`), one call per view, at most two at once, each alone: no view's prompt holds another's answer. The
  Engineering view may read the repository with the draft's read-only tools; the others get none. A view that fails is tried once
  more; a second failure fails the pitch (*Market view did not answer: try again*). Each view is kept as it answers, so the faces
  light its head.
- **The case against** (`pitch_case`), as the Skeptic: the pitch and the four views (tried once more, as a view).
- **The decision** (`pitch_decide`), as the Investor: the pitch, the views, the case, the project's parties with the goal types each
  is offered and the library's parties not in the project, the goals done and in work and the pitches passed. Its answer is cut and
  cleaned by realm/pitches.py; the page's Decision section is written from it.

Stop all, or the person's stop, fails it with *stopped* (Try again). `self` has the keeper's `ask`, `wiki_root`, `state_dir`,
`_start`, `_tls`, `_may_run`, `hold`, `refuse_spent`, `busy`, `publish`, `_ev`, `measure`, `target`.
"""
from __future__ import annotations

import datetime as dt
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from orkboard.realm import event_log, idea_lens, idea_target, ideas, library, pitches, roles

AT_ONCE = 2                        # the views asked at once
GOALS = 40                         # the goals done and in work a call reads
TRIES = 2                          # a view (or the case) is tried once more before the pitch fails
JUDGE_FROM = ("raw", "failed", "judged", "passed", "judging")       # judging: a run the host lost (it is not busy)
NOT_JSON = "the answer was not the JSON it was asked for"


def _kw():
    from orkboard.core import idea_keeper
    return idea_keeper


def _sum(measures: list[dict]) -> dict:
    """The calls' measures as one: the step `pitch`, their prompts' characters, their tokens key by key, their cost."""
    tokens: dict[str, float] = {}
    for m in measures:
        for k, v in (m.get("tokens") or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                tokens[k] = tokens.get(k, 0) + v
    costs = [m["cost"] for m in measures if isinstance(m.get("cost"), (int, float))]
    return {"step": "pitch", "prompt_chars": sum(int(m.get("prompt_chars") or 0) for m in measures),
            "tokens": tokens or None, "cost": round(sum(costs), 4) if costs else None}


def _view_text(a: library.Agent, got: dict) -> str:
    return (f"{a.name}:\n  For: {'; '.join(got.get('for') or []) or '—'}\n  Against: {'; '.join(got.get('against') or []) or '—'}\n"
            f"  Its question: {got.get('question') or '—'}" + (f"\n  Size: {got['size']}" if got.get("size") else ""))


class JudgeMixin:
    def is_pitch(self, slug: str) -> bool:
        return pitches.is_pitch(self.wiki_root(), slug)

    # -- who speaks --------------------------------------------------------------------------------------------------

    def role_as(self, slug: str) -> dict:
        """The role a pitch's call speaks as: the project's (its name, model and instruction as the person left them on Agents),
        else the library's."""
        a = library.get(slug)
        return roles.role(self.state_dir, slug) or {"slug": slug, "name": a.name if a else slug, "model": a.tier if a else "",
                                                     "instruction": a.instruction if a else ""}

    def pick_as(self, step: str, slug: str) -> tuple[str, str] | None:
        """The (model or tier, effort) of a pitch's call: by the Target; a model the person set on Agents for that role (one that is
        not its library tier) wins, as a task's role does."""
        own = str(self.role_as(slug).get("model") or "")
        a = library.get(slug)
        return idea_target.keeper_pick(step, self.target(), "" if a is not None and own == a.tier else own)

    def speak_as(self, slug: str) -> str:
        """What a role is told before a pitch's call: who it is, and its instruction."""
        r = self.role_as(slug)
        return f"You are the {r['name']} of this project's Ideation party. {r.get('instruction') or ''}\n\n"

    # -- the run -------------------------------------------------------------------------------------------------------

    def judge(self, slug: str, person: bool = False) -> bool:
        """Judge a pitch, in the background. The person's ask is refused in a spent window; what judges by itself (Add, the clock)
        waits with `held_until`. False when it was held."""
        kw = _kw()
        root = self.wiki_root()
        if ideas.idea_page(root, slug) is None:
            raise kw.KeeperError("That goal is gone")
        if not pitches.is_pitch(root, slug):
            raise kw.KeeperError("Only a pitch is judged: a goal of another party is drafted")
        if why := self._may_run():
            raise kw.KeeperError(why)
        if self.busy(slug):
            raise kw.KeeperError("The keeper is busy with this pitch: a moment")
        if ideas.state(self.state_dir, slug)["state"] not in JUDGE_FROM:
            raise kw.KeeperError("This pitch is sent: its goal is in its party now")
        if person:
            self.refuse_spent()
        elif self.hold(slug):
            return False
        ideas.save_state(self.state_dir, slug, queue="now", held_until="", error="")
        self._start(slug, "judging", lambda: self.judge_one(slug))
        return True

    def judge_one(self, slug: str) -> None:
        """The three steps, on this thread: `judged` with its decision, or `failed` with why (*stopped* when it was stopped)."""
        kw = _kw()
        root = self.wiki_root()
        if ideas.idea_page(root, slug) is None:
            return
        began, measures = time.monotonic(), []
        pitches.begin(self.state_dir, slug)
        ideas.save_state(self.state_dir, slug, state="judging", error="", held_until="")
        self.publish(slug)
        try:
            views = self._views(root, slug, measures)
            case = self._tried(lambda: pitches.clean_case(kw.first_json(self.ask(
                "pitch_case", self.case_prompt(root, slug, views), tools=False, as_role=library.SKEPTIC)[0])), measures,
                self.role_as(library.SKEPTIC)["name"])
            pitches.save(self.state_dir, slug, case=case)
            self.publish(slug)
            offered = pitches.offers(root, self.state_dir)
            likes = {i["slug"]: i["title"] for i in ideas.ideas(root) if i["slug"] != slug}
            text = self.ask("pitch_decide", self.decide_prompt(root, slug, views, case, offered), tools=False, as_role=library.INVESTOR)[0]
            measures.append(self.measure())
            answer = kw.first_json(text)
            if answer is None:
                raise kw.KeeperError(kw.BUDGET_LINE if getattr(self._tls, "capped", False) else NOT_JSON)
            decision = pitches.clean_decision(answer, case["kills"], offered, likes)
        except Exception as e:
            stopped = isinstance(e, InterruptedError)
            ideas.save_state(self.state_dir, slug, state="failed", error="stopped" if stopped else kw._why(e), measure=_sum(measures),
                             **({"queue": "hold"} if stopped else {}))
            return
        pitches.save(self.state_dir, slug, decision=decision, judged_at=dt.datetime.now().isoformat(timespec="seconds"))
        pitches.write_decision(root, slug, pitches.decision_text(decision, offered, likes))
        total = _sum(measures)
        ideas.save_state(self.state_dir, slug, state="judged", error="", measure=total)
        self._ev(event_log.PITCH_JUDGED, goal=slug, answer=decision["answer"], kills=decision["kills"], tokens=total["tokens"],
                 cost=total["cost"], seconds=round(time.monotonic() - began, 1))
        self.publish(slug)

    def _tried(self, call, measures: list[dict], name: str):
        """`call()` (it asks one model call and cleans its answer, None when it is no object), tried once more when it fails; a
        second failure is the pitch's (*<name> did not answer: try again*). A stop is never tried again."""
        for n in range(TRIES):
            try:
                got = call()
            except InterruptedError:
                measures.append(self.measure())
                raise
            except Exception:
                got = None
            measures.append(self.measure())
            if got is not None:
                return got
        raise _kw().KeeperError(f"{name} did not answer: try again")

    def _views(self, root: Path, slug: str, measures: list[dict]) -> dict[str, dict]:
        """The four views, at most AT_ONCE at once, each alone, each kept as it answers; {view id: answer}."""
        kw = _kw()
        run = (self._tls.cancel, self._tls.slug, self._tls.key)

        def one(view: str) -> tuple[str, dict, list[dict]]:
            self._tls.cancel, self._tls.slug, self._tls.key = run          # the pitch's run, on this worker's thread
            mine: list[dict] = []
            got = self._tried(lambda: pitches.clean_view(kw.first_json(self.ask(
                "pitch_view", self.view_prompt(root, slug, view), tools=view == pitches.TECH, as_role=view)[0]), view), mine,
                self.role_as(view)["name"])
            pitches.save(self.state_dir, slug, view=(view, got))
            self.publish(slug)
            return view, got, mine

        out: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=AT_ONCE, thread_name_prefix="idea-view") as pool:
            futures = [pool.submit(one, v) for v in library.VIEWS]
            try:
                for f in futures:
                    view, got, mine = f.result()
                    out[view] = got
                    measures += mine
            except BaseException:
                for f in futures:
                    f.cancel()
                raise
        return {v: out[v] for v in library.VIEWS}

    # -- what each call is given ----------------------------------------------------------------------------------------

    def pitch_parts(self, root: Path, slug: str) -> list[tuple[str, str]]:
        """What every call of a pitch reads: the pitch, the project's parties (name, Description's first lines, metrics), the goals
        done and in work (≤ 40), the pitches passed (title and why, ≤ 20, newest first)."""
        page = ideas.idea_page(root, slug)
        parties, goals = [], []
        for t in ideas.tracks(root, make=False):
            if t["slug"] == ideas.GENERAL or (t.get("leader") or "") == library.INVESTOR:
                continue
            first = " ".join(" ".join(t["about"].splitlines()[:3]).split())[:300]
            metrics = ", ".join(m["name"] for m in t["metrics"])
            parties.append(f"- {t['slug']}: {t['title']}" + (f" — {first}" if first else "") + (f" (metrics: {metrics})" if metrics else ""))
        for i in ideas.ideas(root):
            st = ideas.state(self.state_dir, i["slug"])["state"]
            if len(goals) < GOALS and st not in ("proposed",) and not pitches.is_ideation(root, i["track"]):
                goals.append(f"- {i['slug']}: {i['title']} ({'done' if st == 'done' else 'in work'}, party {i['track']})")
        return [("The pitch, in the person's words", page.section("Gist") if page else ""),
                ("The project's parties", "\n".join(parties)), ("The goals done and in work", "\n".join(goals)),
                ("Pitches passed before, newest first (judge this one against them)", pitches.passed_lines(root, self.state_dir, slugs=True))]

    def view_prompt(self, root: Path, slug: str, view: str) -> str:
        a = library.get(view)
        context = idea_target.cut(self.pitch_parts(root, slug), idea_target.CONTEXT["pitch_view"])
        reads = self.reads("pitch_view", []) + " You may read the repository (read only)." if view == pitches.TECH \
            else "Read no file: answer from what is here."
        size = ',\n "size": "S, M or L: how big it is to build"' if view == pitches.TECH else ""
        return f"""Read this pitch alone, as its {a.name}: {a.line[0].lower() + a.line[1:]}. The other views read it apart from you;
you see none of them. {reads}
{idea_lens.attached(self.state_dir, slug)}
{context}Answer with one JSON object and nothing else:
{{"for": ["at most three lines, each at most 200 characters: what speaks for it"],
 "against": ["at most three lines: what speaks against it"],
 "question": "the one question whose answer would decide it"{size}}}
"""

    def case_prompt(self, root: Path, slug: str, views: dict[str, dict]) -> str:
        parts = [("The pitch, in the person's words", (ideas.idea_page(root, slug) or ideas.Page()).section("Gist")),
                 ("Its four views", "\n".join(_view_text(library.get(v), got) for v, got in views.items()))]
        context = idea_target.cut(parts, idea_target.CONTEXT["pitch_case"])
        kills = "; ".join(f'"{k}" ({w})' for k, w in pitches.KILLS.items())
        return f"""Make the case against this pitch: the strongest case not to do it, as well as it can be argued. Read no file.

{context}Kill reasons, by their ids: {kills}.
Answer with one JSON object and nothing else:
{{"case": "the case against, at most 600 characters",
 "kills": ["the ids of the kill reasons that hold, or none"]}}
"""

    def decide_prompt(self, root: Path, slug: str, views: dict[str, dict], case: dict, offered: dict[str, dict]) -> str:
        where = []
        for pid, o in offered.items():
            types = ", ".join(o["types"]) or "none"
            where.append(f"- {pid}: {o['name']}" + (" (a party of the library, not in the project yet)" if o["preset"] else "")
                         + f"; its goal types: {types}")
        base = self.pitch_parts(root, slug)
        parts = [base[0], ("Its four views", "\n".join(_view_text(library.get(v), got) for v, got in views.items())),
                 ("The case against", case.get("case") + (f"\nIts kill reasons: {', '.join(case['kills'])}" if case.get("kills") else "")),
                 ("Where it may go: the parties, with the goal types each is offered", "\n".join(where)), *base[1:]]
        context = idea_target.cut(parts, idea_target.CONTEXT["pitch_decide"])
        kills = "; ".join(f'"{k}" ({w})' for k, w in pitches.KILLS.items())
        return f"""Decide whether to invest the team's time in this pitch: invest (in which party, as what goal type), reshape (what
would make it worth it), or pass (why, plainly). Read no file.

{context}Kill reasons, by their ids: {kills}.
Answer with one JSON object and nothing else:
{{"answer": "invest, reshape or pass",
 "why": ["at most three lines, each at most 200 characters"],
 "where": {{"party": "the id of a party listed above, when it is invest", "type": "one of that party's goal types, or empty"}},
 "first": "for invest or reshape: the goal as that party would be given it, at most 300 characters",
 "test": "the cheapest way to know before building, or empty",
 "kills": ["the ids of the kill reasons that hold, or none"],
 "like": "the slug of a goal or a passed pitch listed above that it repeats, or empty"}}
"""
