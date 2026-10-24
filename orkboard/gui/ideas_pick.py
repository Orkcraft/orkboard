"""Pick one (docs/specs/51-pick-one.md §2.3, §2.4) as `gui/ideas.py`'s `Ideas` has it: `ideas.pick`, the person's answer to a task that
made variants, and the Needs you row such a task puts on the Board. Split from ideas.py to keep it under ~600 lines.

    ideas.pick {slug, task, key, note, via}    # key: a variant's letter, or null for none of them (then a note is required)

The row (kind `pick`) carries the variants with their signed addresses (gui/media.py); a text's words come inline. Its tasks are
the runner's (core/idea_picking.py): the Board only reads them and says what the person answered.
"""
from __future__ import annotations

from orkboard.gui import media
from orkboard.gui.ideas_args import VIA, IdeasError, _device, _text
from orkboard.realm import idea_pick, ideas, roles
from orkboard.realm.board_map import task_short

PICK_VIA = ("hand", "front", "drawer", "screen")           # where a pick was answered: the stops along the bottom, the drawer, the phone's own screen
TEXT_INLINE = idea_pick.KINDS["text"].limit       # a text variant's words, inline in the row, at most this many bytes


class PickMixin:

    def pick(self, args: dict) -> dict:
        """`{"slug", "task", "key", "note"?, "via"?}`: the person's answer to a task that waits for a pick. `key`: the variant's letter,
        or null for none of them, which asks for new ones and needs a `note` (at most 2 000 characters). `via`: `hand` (the stop's card),
        `drawer` or `screen` (the phone's own screen); another is read as the idea's screen."""
        slug, tid = _text(args, "slug", 100), _text(args, "task", 40)
        key, note = args.get("key"), args.get("note", "")
        if key is not None and not isinstance(key, str):
            raise IdeasError("key is a variant's letter, or null for none of them")
        if not isinstance(note, str):
            raise IdeasError("note is not text")
        via = args.get("via")
        via = via if isinstance(via, str) and via in (*VIA, *PICK_VIA) else "idea"
        self.runner(need=True).pick(slug, tid, key, note[:idea_pick.NOTE_MAX], device=_device(args), via=via)
        self.changed(slug)
        return {"ok": True}

    def _variant_row(self, slug: str, pick: dict, v: dict) -> dict:
        """One variant as a face reads it: `{key, name, why, url, mime, w, h, seconds, text?}`."""
        row = {"key": v["key"], "name": v["name"], "why": v.get("why") or "", "url": media.url(slug, str(pick["id"]), str(v["file"])),
               "mime": v["mime"], "w": v.get("w"), "h": v.get("h"), "seconds": v.get("seconds")}
        if str(v["mime"]).startswith("text/"):
            try:
                raw = (idea_pick.folder_of(self.state_dir, slug, str(pick["id"])) / str(v["file"])).read_bytes()[:TEXT_INLINE]
                row["text"] = raw.decode("utf-8", "replace")
            except OSError:
                row["text"] = ""
        return row

    def pick_rows(self, i: dict, plan: dict | None) -> list[dict]:
        """The Needs you rows of a goal's tasks that wait for a pick, in the plan's order (realm/idea_pick.py `current`): kind `pick`,
        `slug` (the goal) and `task`, `title` (the task's), the member it ran as, the ask, the variants, the round and when it was asked.
        It blocks the goal's work in progress, so it sorts first."""
        out, slug = [], i["slug"]
        waiting = [t for t in (plan or {}).get("tasks") or [] if isinstance(t, dict) and t.get("state") == "picking"]
        if not waiting:
            return out
        read, target = roles.known(self.state_dir), self._target()
        for t in waiting:
            pick = idea_pick.current(self.state_dir, slug, t)
            if pick is None or idea_pick.answered(pick):
                continue
            who = read[0].get(roles.task_slug(t, read)) or read[0].get(roles.GRUNT) or {}
            out.append({"kind": "pick", "slug": slug, "idea": slug, "goal": i["track"], "task": t.get("id"), "title": t.get("title") or "",
                        "short": task_short(t), "idea_title": i["title"], "priority": i["priority"], "blocks": True,
                        "by": {"slug": who.get("slug") or "", "name": who.get("name") or "", "head": roles.task_head(self.state_dir, t, target, read)},
                        "ask": pick.get("ask") or "", "n": len(pick["variants"]), "media": pick.get("kind"),
                        "variants": [self._variant_row(slug, pick, v) for v in pick["variants"] if isinstance(v, dict)],
                        "round": int(pick.get("round") or 1), "at": str(pick.get("at") or t.get("finished") or "")})
        return out
