"""The Board as `gui/ideas.py`'s `Ideas` shows it (docs/specs/35-goals-window.md §5, §10–§12): `ideas.board` with Needs
you as one list, who passes a plan (autostart by risk and priority), and the Board's own commands — `ideas.queue`,
`ideas.read_stop`, `ideas.start_now`, `ideas.proposal`, `ideas.board_set`, `ideas.answer`, and a file to-do's file.
Split from ideas.py (its size).
"""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

from orkboard import settings
from orkboard.core import idea_keeper, idea_night
from orkboard.gui.ideas_args import IdeasError, _device, _opt, _text
from orkboard.realm import event_log, idea_risk, idea_secrets, ideas
from orkboard.realm.idea_git import BoardTree

NEEDS_IDEA = ("asks", "plan", "failed", "proposed")


def _list(text: str) -> list[str]:
    try:
        got = json.loads(text) if str(text or "").strip() else []
    except ValueError:
        return []
    return [str(x) for x in got if isinstance(x, str)] if isinstance(got, list) else []


class BoardMixin:
    # -- the Board's own tree on the work branch (§13) ----------------------------------------------------------

    def _tree(self, wiki: Path):
        """The Board's tree for this Wiki and work branch; None where it cannot be (the demo, a Wiki outside the
        repository, a folder with no git history): the pages stay in the Wiki then, as before spec 35."""
        if self.host.demo or getattr(self, "_tree_off", False):
            return None
        repo = Path(self.host.repo_root).resolve()
        try:
            rel = Path(wiki).resolve().relative_to(repo).as_posix()
        except ValueError:
            return None
        got = getattr(self, "_board_tree", None)
        if got is None or got.wiki_rel != rel:
            got = self._board_tree = BoardTree(repo, self.state_dir, rel, lambda: self._into())
        return got

    def tree_root(self, wiki: Path, make: bool = True) -> Path:
        tree = self._tree(wiki)
        if tree is None:
            return wiki
        if tree.exists():
            return tree.root()
        if not make or not (Path(self.host.repo_root) / ".git").exists():
            return wiki
        try:
            tree.ensure()
            got = tree.move(wiki)
            if got and got["commit"]:
                self._ev(event_log.BOARD_COMMITTED, commit=got["commit"], pages=got["pages"], what="moved", seconds=None)
        except Exception as e:                  # a repository the tree cannot live in: the Wiki, as before
            self._tree_off = True
            self.host.toast(f"The Board keeps its pages in the Wiki: {' '.join(str(e).split())[:200]}", title="The Board",
                            severity="warning")
            return wiki
        return tree.root()

    def tree_note(self, slug: str, what: str = "") -> None:
        """A write of the Board's, for its next commit: the idea's or goal's title and what happened."""
        tree = getattr(self, "_board_tree", None)
        if tree is None or not tree.exists():
            return
        what = what or self._what.pop(slug, "") or "edited"
        key = slug[5:] if slug.startswith("goal:") else slug
        page = (ideas.track_page if slug.startswith("goal:") else ideas.idea_page)(tree.root(), key) if key else None
        tree.note((page.title if page else "") or key or "the Board", what, time.time())

    def tree_flush(self, force: bool = False) -> dict | None:
        """The Board's writes of the last 10 s as one commit, the work branch moved (or held: `board_held`)."""
        tree = getattr(self, "_board_tree", None)
        if tree is None:
            return None
        began = time.monotonic()
        try:
            got = tree.flush(time.time(), force)
        except Exception as e:                  # a commit that cannot be made never stops the board
            got = {"commit": "", "pages": 0, "what": "", "held": str(e)[:300]}
        if got and got["commit"]:
            self._ev(event_log.BOARD_COMMITTED, commit=got["commit"], pages=got["pages"], what=got["what"],
                     seconds=round(time.monotonic() - began, 2))
        if got and got["held"]:
            self._ev(event_log.BOARD_HELD, why=got["held"])
        return got

    # -- the Board's settings (§1, §5, §7) ---------------------------------------------------------------------

    def board_settings(self) -> dict:
        s = self.settings_now()
        return {"target": s.get("target", settings.IDEAS["target"]), "autostart": bool(s.get("autostart", True)),
                "night": s.get("night", settings.IDEAS["night"])}

    def board_set(self, args: dict) -> dict:
        mine = dict(self.settings_now())
        for key in ("target", "autostart", "night"):
            if key not in args:
                continue
            got = settings.clean_ideas({key: args[key]})[key]
            if got != args[key]:
                raise IdeasError({"target": "The Target is thrift, balance or quality",
                                  "autostart": "Start plans by themselves is on or off",
                                  "night": "The night is HH:MM-HH:MM"}[key])
            mine[key] = got
        self.save_settings(mine)
        out = self.board_settings()
        self._ev(event_log.BOARD_SET, args, **out)
        self.changed("")
        return out

    # -- the board ------------------------------------------------------------------------------------------

    def board(self, make: bool = True) -> dict[str, Any]:
        """`make`: General (and the Wiki) written when missing; the snapshot only reads."""
        root = self.root(make)
        goals = [self._goal_row(g) for g in ideas.tracks(root, make=make)]
        rows, needs = [], self.goal_needs(goals)
        found = ideas.ideas(root)
        states = {i["slug"]: self._state(i["slug"]) for i in found}
        for i in found:
            slug, st = i["slug"], states[i["slug"]]
            plan, page = ideas.plan(self.state_dir, slug), ideas.idea_page(root, slug)
            tasks = (plan or {}).get("tasks") or []
            asks = ideas.items(page.section("Open questions")) if page else []
            depends = _list(page.get("depends_on")) if page else []
            mine = self._idea_needs(i, st, plan, asks, root)
            needs += mine
            rows.append({"slug": slug, "title": i["title"], "track": i["track"], "order": i["order"],
                         "state": st["state"], "size": i["size"], "thesis": i["thesis"], "asks": len(asks),
                         "priority": i["priority"],
                         "progress": {"done": sum(1 for t in tasks if t.get("state") == "merged"), "total": len(tasks)},
                         "updated": ideas.touched_at(root, self.state_dir, slug),
                         "queue": ideas.queue_of(st), "held_until": st["held_until"],
                         "risk": idea_risk.level(page.get("risk")) if page and page.get("risk") else "",
                         "risk_triggers": _list(page.get("risk_triggers")) if page else [],
                         "depends_on": depends,
                         "waits_on": [d for d in depends if states.get(d, {}).get("state") != "done"],
                         "start_at": str((plan or {}).get("start_at") or ""),
                         "in_needs_you": any(n["kind"] in ("asks", "plan", "proposal") for n in mine)})
        return {"tracks": goals, "ideas": rows, "needs_you": sort_needs(needs), **self.board_settings(),
                "rev": self.rev, "demo": bool(self.host.demo)}

    def _idea_needs(self, i: dict, st: dict, plan: dict | None, asks: list[str], root) -> list[dict]:
        """What of one idea needs the person (§10): its questions, its plan waiting, its to-dos, a failure, a proposal."""
        slug, state = i["slug"], st["state"]
        base = {"idea": slug, "goal": i["track"], "title": i["title"], "priority": i["priority"], "blocks": False,
                "at": ideas.touched_at(root, self.state_dir, slug)}
        tasks = (plan or {}).get("tasks") or []
        out = []
        if state == "asks":
            out.append({**base, "kind": "asks", "text": asks[0] if asks else "The keeper asks you"})
        if state == "plan" and plan and not plan.get("passed_at"):
            out.append({**base, "kind": "plan", "text": "Plan ready" + (f" · {len(tasks)} tasks" if tasks else ""),
                        "at": str(plan.get("made_at") or base["at"])})
        if state == "proposed":
            out.append({**base, "kind": "proposal", "text": ideas.thesis(
                (ideas.idea_page(root, slug) or ideas.Page()).section("Gist")) or "The keeper proposes this"})
        if state == "failed":
            out.append({**base, "kind": "failed", "text": st.get("error") or "Something failed"})
        merged = {t.get("id") for t in tasks if t.get("state") == "merged"}
        if state == "working":
            for t in tasks:
                if t.get("state") == "failed":
                    out.append({**base, "kind": "failed", "blocks": True, "text": f"{t.get('title', '')}: {t.get('error') or 'failed'}",
                                "at": str(t.get("finished") or base["at"])})
        if plan and state in ("plan", "working", "failed"):
            for td in plan.get("todos") or []:
                if td.get("done"):
                    continue
                waits = [t for t in tasks if t.get("id") in (td.get("for") or []) and t.get("state") != "merged"
                         and set(t.get("after") or []) <= merged]
                out.append({**base, "kind": "todo", "text": td.get("title") or "", "blocks": state == "working" and bool(waits),
                            "at": str(plan.get("made_at") or base["at"]),
                            "todo": {k: td.get(k) for k in ("id", "title", "kind", "why", "choices", "steps", "accept", "done")}})
        return out

    # -- who passes the plan (§5) ----------------------------------------------------------------------------

    def rank(self, slug: str) -> tuple:
        """An idea's place: its priority, then the person's order (its goal's, then its own)."""
        root = self.root()
        page = ideas.idea_page(root, slug)
        if page is None:
            return (len(ideas.PRIORITIES), 0, 0)
        place = {t["slug"]: n for n, t in enumerate(ideas.tracks(root, make=False))}
        prio = page.get("priority") if page.get("priority") in ideas.PRIORITIES else "normal"
        return (ideas.PRIORITIES.index(prio), place.get(page.get("track") or ideas.GENERAL, len(place)), ideas._int(page.get("order")))

    def autostart(self, slug: str) -> str:
        """A plan made, or its idea's priority or risk changed: the board decides (code, no model) whether it starts,
        starts at night, or waits for the person. What it did ("" nothing to decide)."""
        if not bool(self.settings_now().get("autostart", True)):
            return "wait"
        plan, page = ideas.plan(self.state_dir, slug), ideas.idea_page(self.root(), slug)
        if plan is None or page is None or plan.get("passed_at") or plan.get("stopped") \
                or ideas.state(self.state_dir, slug)["state"] != "plan":
            return ""
        if ideas.items(page.section("Open questions")):
            return "wait"
        what = idea_risk.decide(page.get("risk"), page.get("priority"))
        if what != "wait":
            try:
                self.pass_plan(slug, "auto", night=what == "night")
            except IdeasError:
                return "wait"
        return what

    def _on_plan(self, slug: str) -> None:
        """From the keeper's thread: the plan's autostart (a refusal leaves it waiting for the person)."""
        try:
            self.autostart(slug)
        except Exception:                      # whether it starts never breaks the keeper
            pass
        self._publish(slug)

    def pass_plan(self, slug: str, by: str, night: bool = False, args: dict | None = None) -> None:
        """A plan passed: by the person's press ("person") or the board ("auto"); `night`: it starts inside the night
        window. From now on it is the runner's."""
        plan = ideas.plan(self.state_dir, slug)
        if plan is None:
            raise IdeasError("This idea has no plan yet: Take it to work first")
        runner = self.runner(need=True)
        if not plan.get("passed_at"):
            page = ideas.idea_page(self.root(), slug)

            def passing(p: dict) -> None:
                p.update(passed_at=time.strftime("%Y-%m-%dT%H:%M:%S"), passed_by=by)
                p["start_at"] = "night" if night else None
                p.pop("stopped", None)
            ideas.edit_plan(self.state_dir, slug, passing)
            self._ev(event_log.PLAN_PASSED, args, idea=slug, tasks=len(plan.get("tasks") or []), seconds=self._since(plan.get("made_at")),
                     by=by, risk=idea_risk.level(page.get("risk")) if page else "", priority=page.get("priority") if page else "")
        elif by == "person" and plan.get("start_at"):
            ideas.edit_plan(self.state_dir, slug, lambda p: p.update(start_at=None))
        if night:
            ideas.save_state(self.state_dir, slug, error="")
            self._publish(slug)
            return
        ideas.save_state(self.state_dir, slug, state="working", error="", queue="")
        runner.start(slug)
        self._publish(slug)

    def start_night(self, slug: str) -> bool:
        """The night's step 2: a plan passed to start at night goes to the runner (its tasks start inside the window)."""
        plan = ideas.plan(self.state_dir, slug)
        if not plan or plan.get("start_at") != "night" or ideas.state(self.state_dir, slug)["state"] != "plan":
            return False
        ideas.save_state(self.state_dir, slug, state="working", error="")
        self.runner(need=True).start(slug)
        self._publish(slug)
        return True

    def start_now(self, args: dict) -> dict:
        """Start now: a plan that starts at night starts now."""
        slug = _text(args, "slug", 100)
        plan = ideas.plan(self.state_dir, slug)
        if not plan or plan.get("start_at") != "night":
            raise IdeasError("This plan does not wait for the night")
        ideas.edit_plan(self.state_dir, slug, lambda p: p.update(start_at=None))
        runner = self.runner(need=True)
        if ideas.state(self.state_dir, slug)["state"] == "plan":
            ideas.save_state(self.state_dir, slug, state="working", error="")
            runner.start(slug)
        else:
            runner.tick()
        self.changed(slug)
        return {"ok": True}

    # -- the queue, the keeper's own stop (§3, §12) ------------------------------------------------------------

    def queue(self, args: dict) -> dict:
        """Process now (`now`: drafted at once; refused in plain words in a spent window) or Tonight (`night`)."""
        slug, q = _text(args, "slug", 100), _opt(args, "queue")
        if q not in ("now", "night"):
            raise IdeasError("The queue is now or night")
        if ideas.idea_page(self.root(), slug) is None:
            raise IdeasError("That idea is gone")
        if q == "now":
            try:
                self.keeper.read_now(slug)
            except idea_keeper.KeeperError as e:
                raise IdeasError(str(e)) from None
        else:
            if self._state(slug)["state"] != "raw":
                raise IdeasError("Only a new idea waits for the night")
            ideas.save_state(self.state_dir, slug, queue="night", held_until="", error="")
        self.changed(slug)
        return {"ok": True}

    def read_stop(self, args: dict) -> dict:
        slug = _text(args, "slug", 100)
        if ideas.idea_page(self.root(), slug) is None:
            raise IdeasError("That idea is gone")
        self.keeper.read_stop(slug)
        self.changed(slug)
        return {"ok": True}

    # -- one round of questions (§0), a file to-do's file (§9) ---------------------------------------------------

    def answer(self, args: dict) -> dict:
        """The questions of a spec (or of a goal, `goal: true`) answered together, in their order: one round (§0)."""
        slug = _text(args, "slug", 100)
        answers = args.get("answers")
        if not isinstance(answers, list) or not all(isinstance(a, str) for a in answers):
            raise IdeasError("answers are a list of text")
        if args.get("goal") is True:
            g = next((t for t in ideas.tracks(self.root(), make=False) if t["slug"] == slug), None)
            if g is None:
                raise IdeasError("That goal is gone")
            said = "\n".join(f"{q} — {a.strip() or '(no answer: decide)'}" for q, a in zip(g["questions"], answers))
            self.keeper.read_goal(slug, said, answered=True)
            self._what[f"goal:{slug}"] = "answered"
            self.changed(f"goal:{slug}")
            return {"ok": True}
        self.keeper.answer(slug, answers)
        self._what[slug] = "answered"
        self.changed(slug)
        return {"ok": True}

    def _todo_file(self, args: dict, slug: str, todo: dict) -> str:
        """A file to-do's file (spec 35 §9): base64, at most 5 MB, kept beside the secrets (mode 600); plan.json says
        only its name. From a phone only over the paired link, as a secret."""
        got = args.get("file")
        if _device(args) == "phone" and args.get("link") != "paired":
            raise IdeasError("A file is given at the computer, or over the paired link")
        if not isinstance(got, dict):
            if todo.get("value"):
                return todo["value"]
            raise IdeasError("A file to-do needs its file")
        data = got.get("data")
        if not isinstance(data, str) or len(data) > idea_secrets.FILE_MAX * 4 // 3 + 8:
            raise IdeasError("The file is larger than 5 MB")
        try:
            raw = base64.b64decode(data, validate=True)
        except ValueError:
            raise IdeasError("The file did not arrive whole") from None
        path = idea_secrets.put_file(self.state_dir, slug, str(todo.get("id")), str(got.get("name") or ""), raw,
                                     todo.get("accept") or [])
        return path.name.split("-", 1)[1]

    # -- proposals (§8) -----------------------------------------------------------------------------------------

    def proposal(self, args: dict) -> dict:
        """Take (with a priority: the idea joins the queue) or No (with an optional reason, read back the next night)."""
        slug = _text(args, "slug", 100)
        root = self.root()
        page = ideas.idea_page(root, slug)
        if page is None or self._state(slug)["state"] != "proposed":
            raise IdeasError("That proposal is gone")
        take = args.get("take") is True
        reason = args.get("reason") if isinstance(args.get("reason"), str) else ""
        if take:
            priority = _opt(args, "priority").lower() or next(
                (t["priority"] for t in ideas.tracks(root, make=False) if t["slug"] == page.get("track")), "normal")
            if priority not in ideas.PRIORITIES:
                raise IdeasError("Priority is High, Normal or Low")
            ideas.set_meta(root, slug, priority=priority)
            q = "night" if priority == "low" else "now"
            ideas.save_state(self.state_dir, slug, state="raw", queue=q, error="")
            if q == "now":
                try:
                    self.keeper.draft(slug)
                except idea_keeper.KeeperError as e:
                    ideas.save_state(self.state_dir, slug, error=str(e))
        else:
            idea_night.decline(self.state_dir, page.title or slug, page.get("track") or "", reason)
            ideas.drop(root, slug, self.state_dir)
            self._what[slug] = "declined"
        self._ev(event_log.PROPOSAL_ANSWERED, args, idea=slug, take=take, has_reason=bool(reason.strip()))
        self.changed(slug)
        return {"ok": True}


def sort_needs(needs: list[dict]) -> list[dict]:
    """What blocks work in progress first, then the priority, then the oldest; proposals last (§10)."""
    def key(n: dict) -> tuple:
        prio = n.get("priority") if n.get("priority") in ideas.PRIORITIES else "normal"
        return n["kind"] == "proposal", not n.get("blocks"), ideas.PRIORITIES.index(prio), str(n.get("at") or "")
    return sorted(needs, key=key)
