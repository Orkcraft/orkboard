"""The gate (docs/specs/49-one-window.md §2.1) as `gui/ideas.py`'s `Ideas` has it: `ideas.gate`, what dev holds that main
lacks, and `ideas.gate_merge`, the one press that merges dev into main (realm/idea_gate.py). `dev` is the branch results
merge into (`ideas.into`), `main` the repository's default branch. Results still land in dev one by one; nothing reaches
main but through this press. Spec 50 §2.2: a goal raises its flag (realm/idea_flag.py) when this press takes it into main, or when it is done where there is
no gate. Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

from pathlib import Path

from orkboard import settings
from orkboard.gui.ideas_args import IdeasError
from orkboard.realm import event_log, idea_flag, idea_gate, ideas
from orkboard.realm.idea_git import IdeaGit


class GateMixin:
    def _gate_main(self, git: IdeaGit) -> str:
        """The repository's default branch; "" where there is no git yet (the gate is then off, as with no main)."""
        try:
            return git.default_branch()
        except Exception:                       # not a git folder yet
            return ""

    def _gate_ideas(self, shas: list[str]) -> list[dict]:
        """The ideas with a merged task whose commit is among `shas`, in the Board's order."""
        rows = []
        for i in ideas.ideas(self.root(False)):
            plan = ideas.plan(self.state_dir, i["slug"])
            if plan:
                rows.append((i["slug"], i["title"], i["track"], plan.get("tasks") or []))
        return idea_gate.ideas_in(shas, rows)

    def gate(self, args: dict) -> dict:
        """`{}`: `{into, main, same, commits, files, ideas: [{slug, title, goal, tasks}]}`. `same`: dev and main are one
        branch, or main does not exist: there is no gate (and nothing else is counted)."""
        into = self._into()
        git = IdeaGit(Path(self.host.repo_root))
        main = self._gate_main(git)
        out = {"into": into, "main": main, "same": idea_gate.same(into, main), "commits": 0, "files": 0, "ideas": []}
        if out["same"]:
            return out
        try:
            shas, files = idea_gate.waiting(git, into, main)
        except Exception:                       # a repository git cannot read: nothing waits that the Board can see
            return out
        return {**out, "commits": len(shas), "files": files, "ideas": self._gate_ideas(shas)}

    def gate_merge(self, args: dict) -> dict:
        """`{}`: merge dev into main (fast-forward, else a merge commit), pushed when the project pushes after merging.
        `{ok, commit, note}`: main's new head and the push's note ("" when pushed or there is no origin)."""
        into = self._into()
        git = IdeaGit(Path(self.host.repo_root))
        main = self._gate_main(git)
        push = bool(self.settings_now().get("push", settings.IDEAS["push"]))
        try:
            got = idea_gate.merge(git, into, main, push)
        except RuntimeError as e:               # a refusal (GateRefused) or git's own words
            raise IdeasError(" ".join(str(e).split())[:300] or "The merge failed") from None
        brought = self._gate_ideas(got["commits"])
        self._ev(event_log.GATE_MERGED, args, commits=len(got["commits"]), ideas=len(brought),
                 files=got["files"], how=got["how"], pushed=got["pushed"], into=into, main=main)
        self._flag_after_gate(brought, got["commit"], git, main)
        self.changed("")
        return {"ok": True, "commit": got["commit"], "note": got["note"]}

    # -- a goal's flag (spec 50 §2.2) ---------------------------------------------------------------------------

    def _raise_flag(self, slug: str, by: str, commit: str = "") -> bool:
        """The goal's flag, once: written, logged (`idea_flagged`) and published (`ideas.changed` with its slug). False when
        it had one already."""
        if idea_flag.flag_of(self.state_dir, slug) is not None:
            return False
        root = self.root(False)
        got = idea_flag.raise_flag(root, self.state_dir, slug, by, commit)
        party = (ideas.idea_page(root, slug) or ideas.Page()).get("track") or ""
        self._ev(event_log.IDEA_FLAGGED, None, idea=slug, goal=party, by=by, tasks=got["tasks"], first_time=got["first_time"],
                 usd=got["usd"], days=got["days"])
        self.changed(slug)
        return True

    def _flag_after_gate(self, brought: list[dict], commit: str, git: IdeaGit, main: str) -> None:
        """After the press: each done goal without a flag that this merge brought commits of, all of whose commits are in main
        now. (A goal done and in main before this spec has none of its commits among them: no backfill.) A flag never troubles
        the merge."""
        for row in brought:
            slug = row["slug"]
            try:
                if ideas.state(self.state_dir, slug)["state"] == "done" and idea_flag.flag_of(self.state_dir, slug) is None \
                        and idea_gate.all_in(git, idea_flag.commits_of(self.state_dir, slug), main):
                    self._raise_flag(slug, "gate", commit)
            except Exception:
                pass

    def _flag_when_done(self, slug: str) -> None:
        """A goal became done: where there is no gate (results merge into main itself), or when all its commits are in main
        already (its last task a clean check, after an earlier merge), its flag is raised. Done in dev, it waits for the gate."""
        try:
            git = IdeaGit(Path(self.host.repo_root))
            main, commits = self._gate_main(git), idea_flag.commits_of(self.state_dir, slug)
            if idea_gate.same(self._into(), main) or idea_gate.all_in(git, commits, main):
                self._raise_flag(slug, "done", commits[-1] if commits else "")
        except Exception:
            pass
