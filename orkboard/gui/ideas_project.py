"""The project's level (docs/specs/70-orkmaster-and-the-project.md §1.2) as `gui/ideas.py`'s `Ideas` has it. Split from ideas.py to keep it
under ~600 lines.

    ideas.party_for {type?}      # the Orkmaster's suggestion of a goal's party: {parties: [{party, name, fits, missing}], suggested: slug}

Reads the project's parties and their teams; writes nothing, asks no model (realm/orkmaster.py).
"""
from __future__ import annotations

from orkboard.gui.ideas_args import IdeasError, _opt
from orkboard.realm import orkmaster


class ProjectMixin:
    def party_for(self, args: dict) -> dict:
        """`{type?}`: the project's parties but General, how each fits a goal type (`whole`, `missing`, `none`; without a type "" and Ideation's
        `pitch`), and the one suggested. A type the catalog lacks is refused (*No goal type 'x'*)."""
        try:
            parties = orkmaster.party_for(self.state_dir, self.root(False), _opt(args, "type") or None)
        except ValueError as e:
            raise IdeasError(str(e)) from None
        return {"parties": parties, "suggested": orkmaster.suggested(parties)}
