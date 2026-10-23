"""A plan change (docs/specs/62-spec-after-start.md): what the leader proposes for the tasks not started, after a goal's spec
changed, kept beside its plan until the person answers; and which of the spec's sections changed since the plan.

    PLAN_SECTIONS                              # the sections that make a plan: those the plan prompt reads
    update(root, state_dir, slug, {"Out": …})  # the keeper's turn: ideas.update, and `changed` kept
    set_section(root, state_dir, slug, "Out", "…")   # a section by hand: ideas.set_section, and `changed` kept
    changed_of(state)                          # the sections written since the plan, in PLAN_SECTIONS' order
    clear(state_dir, slug)                     # a plan was made, a change was answered: nothing changed since
    read / write / drop (state_dir, slug)      # <state_dir>/ideas/<slug>/plan_change.json
    live(state_dir, slug, plan, goal_state)    # the change, while it can still be taken (a read: nothing is dropped)
    settle(state_dir, slug)                    # …and the one that cannot, dropped by itself
    summary(change, plan) / text_of(summary)   # what the page, the stop and the answer say of it
    safe_after(graph, node, wanted)            # `after` that closes no cycle
    in_order(tasks)                            # the tasks, each after the ones it waits for

A plan change is `{made_at, why, changed, change, drop, add, estimate}`: `change` the tasks not started that take new fields
(`id, title, short, brief, kind, tier, after, role`), `drop` their ids, `add` new tasks (`key` n1, n2…, the same fields), `estimate`
what it adds to the plan's price or, when it saves, takes from it (`usd_low`, `usd_high`). The runner applies it
(core/idea_review.py `revise_tasks`); the keeper makes it (core/idea_revise.py). No face, no model.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from orkboard.realm import ideas

PLAN_SECTIONS = ("Gist", "Done when", "Out", "Risks", "Depends on")     # what core/idea_keeper.py `plan_prompt` reads of the spec
NOT_STARTED = ("waiting", "ready", "held")                              # a task that has not run: the leader may change it
FILE = "plan_change.json"


def open_task(task: dict | None) -> bool:
    """A task the leader may still change or drop: not started, and never run (a task stopped on its own waits as `ready`, a failed
    one that is started again as `waiting`: both ran, and keep their branch)."""
    return task is not None and task.get("state") in NOT_STARTED and not task.get("started")


# -- the sections that changed since the plan -------------------------------------------------------------

def changed_of(state: dict) -> list[str]:
    """The plan-making sections written since the plan was made, each once, in `PLAN_SECTIONS`' order."""
    kept = state.get("changed")
    return [n for n in PLAN_SECTIONS if isinstance(kept, list) and n in kept]


def mark(state_dir: Path, slug: str, names: list[str]) -> None:
    """These sections were written: those that make a plan are kept in `changed`, for a goal with a plan only."""
    names = [n for n in PLAN_SECTIONS if n in names]
    if not names:
        return
    with ideas.LOCK:
        if ideas.plan(state_dir, slug) is None:
            return
        was = changed_of(ideas.state(state_dir, slug))
        now = [n for n in PLAN_SECTIONS if n in was or n in names]
        if now != was:
            ideas.save_state(state_dir, slug, changed=now)


def clear(state_dir: Path, slug: str) -> None:
    """A plan was made, or a plan change was answered: no section changed since."""
    with ideas.LOCK:
        if changed_of(ideas.state(state_dir, slug)):
            ideas.save_state(state_dir, slug, changed=[])


def update(root: Path, state_dir: Path, slug: str, sections: dict[str, str], decisions: list[str] = ()) -> list[str]:
    """`ideas.update` (the keeper's turn), and the plan-making sections whose text differs from what it was kept in `changed`."""
    with ideas.LOCK:
        page = ideas.idea_page(root, slug)
        names = [n for n, text in sections.items() if _differs(page, n, text)]
        done = ideas.update(root, slug, sections, decisions)
        mark(state_dir, slug, [n for n in names if n in done])
    return done


def set_section(root: Path, state_dir: Path, slug: str, name: str, text: str) -> None:
    """`ideas.set_section` (a section by hand), and `changed` kept as `update` keeps it."""
    with ideas.LOCK:
        differs = _differs(ideas.idea_page(root, slug), name, text)
        ideas.set_section(root, slug, name, text)
        if differs:
            mark(state_dir, slug, [name])


def _differs(page: ideas.Page | None, name: str, text: str) -> bool:
    return page is not None and ideas.clean_text(text) != page.section(name).strip()


# -- the file ---------------------------------------------------------------------------------------------

def path(state_dir: Path, slug: str) -> Path:
    return ideas.state_folder(state_dir, slug) / FILE


def _list(data: dict, key: str, kind: type) -> list:
    got = data.get(key)
    return [x for x in got if isinstance(x, kind)] if isinstance(got, list) else []


def read(state_dir: Path, slug: str) -> dict | None:
    """The plan change that waits for this goal, its lists whole; None when none waits."""
    data = ideas._json(path(state_dir, slug))
    if data is None:
        return None
    est = data.get("estimate") if isinstance(data.get("estimate"), dict) else {}
    return {**data, "made_at": str(data.get("made_at") or ""), "why": str(data.get("why") or ""),
            "changed": changed_of({"changed": data.get("changed")}), "change": _list(data, "change", dict),
            "drop": _list(data, "drop", str), "add": _list(data, "add", dict),
            "estimate": {"usd_low": est.get("usd_low"), "usd_high": est.get("usd_high")}}


def write(state_dir: Path, slug: str, change: dict) -> dict:
    """A plan change saved, a newer one replacing the one that waited. Its `made_at` is now unless it has one."""
    data = {**change, "made_at": change.get("made_at") or dt.datetime.now().isoformat(timespec="seconds")}
    with ideas.LOCK:
        ideas._write_json(path(state_dir, slug), data)
    return data


def drop(state_dir: Path, slug: str) -> None:
    with ideas.LOCK:
        path(state_dir, slug).unlink(missing_ok=True)


def stale(change: dict, plan: dict | None, goal_state: str = "") -> bool:
    """A plan change that cannot be taken any more (spec 62 §3.3): the goal is done, its plan is not passed (it was made again),
    or every task it would change or drop has started and it adds nothing. A change of nothing (the leader found nothing to
    change) is not stale: its stop says so."""
    if plan is None or not plan.get("passed_at") or goal_state == "done":
        return True
    if change.get("add"):
        return False
    tasks = {str(t.get("id")): t for t in plan.get("tasks") or [] if isinstance(t, dict)}
    named = [str(c.get("id")) for c in change.get("change") or []] + [str(i) for i in change.get("drop") or []]
    return bool(named) and not any(open_task(tasks.get(i)) for i in named)


def live(state_dir: Path, slug: str, plan: dict | None, goal_state: str = "") -> dict | None:
    """The plan change that waits and can still be taken (a read: a stale one is shown nowhere, `settle` drops it)."""
    if not path(state_dir, slug).exists():
        return None
    change = read(state_dir, slug)
    return None if change is None or stale(change, plan, goal_state) else change


def settle(state_dir: Path, slug: str) -> bool:
    """A plan change that cannot be taken any more is dropped by itself (spec 62 §3.3); `changed` stays, for the person to ask again.
    True when one was dropped."""
    if not path(state_dir, slug).exists():
        return False
    with ideas.LOCK:
        change = read(state_dir, slug)
        if change is None or not stale(change, ideas.plan(state_dir, slug), ideas.state(state_dir, slug)["state"]):
            return False
        drop(state_dir, slug)
    return True


# -- what is said of it -----------------------------------------------------------------------------------

def summary(change: dict, plan: dict | None) -> dict:
    """`{made_at, why, added, changed, dropped, usd_low, usd_high, rows}` (spec 62 §2.4): what taking the change now would do. A task
    it names that has started meanwhile (or is gone) is not counted; `rows` are `{op: "add" | "change" | "drop", id, title}`,
    `id` "" for an added task."""
    tasks = {str(t.get("id")): t for t in (plan or {}).get("tasks") or [] if isinstance(t, dict)}
    rows = [{"op": "add", "id": "", "title": str(a.get("title") or "")} for a in change.get("add") or []]
    rows += [{"op": "change", "id": str(c.get("id")), "title": str(c.get("title") or "")}
             for c in change.get("change") or [] if open_task(tasks.get(str(c.get("id"))))]
    rows += [{"op": "drop", "id": str(i), "title": str(tasks[str(i)].get("title") or "")}
             for i in change.get("drop") or [] if open_task(tasks.get(str(i)))]
    count = lambda op: sum(1 for r in rows if r["op"] == op)      # noqa: E731
    est = change.get("estimate") or {}
    return {"made_at": str(change.get("made_at") or ""), "why": str(change.get("why") or ""), "added": count("add"),
            "changed": count("change"), "dropped": count("drop"), "usd_low": est.get("usd_low"), "usd_high": est.get("usd_high"),
            "rows": rows}


def text_of(s: dict) -> str:
    """The stop's text: *The plan changes · +2 · 1 changed · −1* (only the parts that are not zero), else *The plan stays as it is*."""
    parts = [f"+{s['added']}" if s["added"] else "", f"{s['changed']} changed" if s["changed"] else "",
             f"−{s['dropped']}" if s["dropped"] else ""]
    return " · ".join(["The plan changes", *(p for p in parts if p)]) if any(parts) else "The plan stays as it is"


def shown(state_dir: Path, slug: str, plan: dict | None, goal_state: str = "") -> dict | None:
    """The summary of the plan change that waits (the page's `change`), None when none does."""
    change = live(state_dir, slug, plan, goal_state)
    return None if change is None else summary(change, plan)


# -- `after` ------------------------------------------------------------------------------------------------

def in_order(tasks: list[dict]) -> list[dict]:
    """The tasks so that each comes after the ones it waits for, otherwise as they stand: a plan change adds its tasks last, and the
    goal's Stages (core/idea_draft.py `stages`) read a task's `after` among the tasks before it."""
    ids = {str(t.get("id")) for t in tasks}
    out, done, todo = [], set(), list(tasks)
    while todo:
        ready = [t for t in todo if all(str(a) in done or str(a) not in ids for a in t.get("after") or [])]
        first = (ready or todo)[0]                      # none ready: a cycle, which a plan never has
        out.append(first)
        done.add(str(first.get("id")))
        todo.remove(first)
    return out


def reaches(graph: dict[str, list[str]], start: str, target: str) -> bool:
    """Whether `start` waits for `target`, however far (`graph`: task → what it waits for)."""
    seen, todo = set(), [start]
    while todo:
        node = todo.pop()
        if node == target:
            return True
        if node not in seen:
            seen.add(node)
            todo += graph.get(node, [])
    return False


def safe_after(graph: dict[str, list[str]], node: str, wanted: list[str]) -> list[str]:
    """Of the tasks `node` would wait for, those that exist in `graph` and close no cycle (`node` itself, or a task that waits
    for it, however far, is left out; the rest is kept). The graph takes `node` with what is kept."""
    kept: list[str] = []
    for dep in dict.fromkeys(wanted):
        if dep != node and dep in graph and not reaches(graph, dep, node):
            kept.append(dep)
    graph[node] = list(kept)
    return kept
