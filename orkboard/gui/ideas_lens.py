"""The lens a new idea is written with (realm/idea_lens.py), as `gui/ideas.py`'s `Ideas` has it: `ideas.lens` (the lenses
a goal's party offers, the one open first, the project's segments and screens), `ideas.lens_code` (the repository's
parts and how they depend on one another: realm/code_map.py), `ideas.lens_screen` (a kept screen's picture). What an idea
points at comes with `ideas.add` (`lens`) and is shown with its page. Split from ideas.py to keep it under ~600 lines.
"""
from __future__ import annotations

from pathlib import Path

from orkboard.gui.ideas_args import IdeasError, _opt, _text
from orkboard.realm import code_map, idea_lens, ideas


class LensMixin:
    def lens(self, args: dict) -> dict:
        """`{"track"}`: the lenses of the goal's party, the one open first, the segments and screens the project keeps."""
        track = _opt(args, "track")
        if track and not any(t["slug"] == track for t in ideas.tracks(self.root(), make=False)):
            raise IdeasError("That goal is gone")
        return {**idea_lens.lenses(self.state_dir, self.root(), track), "segments": idea_lens.segments(self.state_dir),
                "screens": [{"id": s["id"], "name": s["name"]} for s in idea_lens.screens(self.state_dir)]}

    def lens_code(self, args: dict) -> dict:
        """The repository's parts: each folder of source files, its files, what it uses and what uses it."""
        return {"parts": code_map.parts(Path(self.host.repo_root))}

    def lens_screen(self, args: dict) -> dict:
        got = idea_lens.screen_data(self.state_dir, _text(args, "id", 40))
        if got is None:
            raise IdeasError("That screen is gone")
        return got

    def _lens_args(self, args: dict) -> list[dict]:
        """What `ideas.add` brings in `lens`, checked (a new screen kept)."""
        try:
            return idea_lens.clean(self.state_dir, args.get("lens"), Path(self.host.repo_root))
        except ValueError as e:
            raise IdeasError(str(e)) from None
