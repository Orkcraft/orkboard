"""The gate (docs/specs/49-one-window.md §2.1) as `gui/ideas.py`'s `Ideas` has it: `ideas.gate`, what dev holds that main
lacks, and `ideas.gate_merge`, the one press that merges dev into main (realm/idea_gate.py). `dev` is the branch results
merge into (`ideas.into`), `main` the repository's default branch. Results still land in dev one by one; nothing reaches
main but through this press. Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

from pathlib import Path

from orkboard import settings
from orkboard.gui.ideas_args import IdeasError
from orkboard.realm import event_log, idea_gate, ideas
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
        self._ev(event_log.GATE_MERGED, args, commits=len(got["commits"]), ideas=len(self._gate_ideas(got["commits"])),
                 files=got["files"], how=got["how"], pushed=got["pushed"], into=into, main=main)
        self.changed("")
        return {"ok": True, "commit": got["commit"], "note": got["note"]}
