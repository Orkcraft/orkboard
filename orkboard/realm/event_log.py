"""📒 The local event log (docs/design/dogfood-logs.md §3): every product event, exact, on this machine only.

    event_log.record(root, event_log.ASKED, building="pool", ork="Grunt", task="t1", text="Which port?")
    event_log.read(root, since="2026-10-14")       # the lines, oldest first
    event_log.counts(root, since="2026-10-14")     # {event: how many}
    event_log.summary(root, since=…)               # the counts the owner reads after a week (`orkcraft usage local`)

It sits beside the anonymous usage stats (core/usage.py) and is not them: whatever the person said to sharing,
these lines are written to `.orkcraft/usage/events.jsonl` in the town's folder and never leave the machine — no
proxy, no batch, no network. They may hold the town's own words (a question an ork asked, its options), because
only the person who owns the town reads them, by hand or in the analytics zip (realm/analytics.py).

A closed list of events (`EVENTS`); an unknown one is not written. A field is kept as it is when it is plain data
(a string, a number, a bool, a list of strings); a string is cut at `TEXT_MAX`. Writing never troubles the town:
a disk that refuses is ignored. Nothing is written in the demo (the caller passes no root).

No face here: a service records, a face reads (decisions §8: these counts size the way to ask after a week).
"""
from __future__ import annotations

import datetime as dt
import json
import threading
from collections import Counter
from pathlib import Path
from typing import Any

PATH = Path(".orkcraft") / "usage" / "events.jsonl"
TEXT_MAX = 2_000

# The way to ask (ork-console.md §4, §20): what an ork asked, marked, was answered, and where a run stopped.
ASKED = "question_asked"          # building, ork, task, harness, text, options, via ("block" | "line"), at_work
ASSUMED = "assumption_marked"     # building, ork, task, harness, text, at_work (the person's working hours held)
ANSWERED = "question_answered"    # building, ork, task, who ("person" | "steward" | "timer"), waited_s, text
STOPPED = "run_stopped_on_question"   # building, ork, task, harness: the run ended to wait for the person
# A wait the person skipped (ork-console.md §19): which wait, and how long it had lasted.
WAIT_SKIPPED = "wait_skipped"     # building, task, wait, waited_s
# Quiet working hours (audience.md §2a): a question's toast or push held for "since your last look".
HELD_AT_WORK = "question_held_at_work"   # how ("toast" | "push"), title
# Leaving the camp (audience.md §2a): "I'm off", and back (by the person, at evening, or the work done).
CAMP_LEFT = "camp_left"           # carts, first, cap_pct, until, on_power
CAMP_BACK = "camp_back"           # why ("person" | "evening"), minutes, window_pct, capped, carts_left
# Mission 1 (first-mission.md): a quest started, done or skipped.
QUEST_STARTED = "quest_started"   # quest
QUEST_DONE = "quest_done"         # quest, seconds
QUEST_SKIPPED = "quest_skipped"   # quest
# "Since your last look" (audience.md §2a): what the town made while the person was away, and their looks.
BUILT = "result_built"            # building, kind ("passed" | "launched" | "done"), title, ref, tokens, cost (None: unrecorded)
CART_MOVED = "cart_moved"         # source, target, title: a cart delivered along a road
LOOKED = "look"                   # started, seconds: the GUI in front of the person (looks a day, their length)

# The board (docs/specs/33-v1-shell.md §9): every action of the v1 shell, for the day's analysis. `device` is "desktop" or "phone".
IDEA_ADDED = "idea_added"         # idea, track, chars, now (the keeper reads it at once), priority, queue, photos (how many came with it), lens (the kinds pointed at), device,
#                                    type (its goal type's id, else ""), asks (how many answered), refs (how many pictures were Refs'), joined (the agent, else ""), out (the member, else "") (spec 52 §2.7),
#                                    offered (how many types the party offered), near (how many of them with someone missing) (spec 59 §5)
IDEA_SAID = "idea_said"           # idea, section, chars, text, device (the person's turn to the Taskmaster)
KEEPER_STATE = "keeper_state"     # idea, state, was, seconds in the previous state
PLAN_MADE = "plan_made"           # idea, tasks, todos, usd_low, usd_high
PLAN_PASSED = "plan_passed"       # idea, tasks, device, seconds from plan_made, by ("person" · "auto"), risk, priority, via (where the press was: gui/ideas_args.py VIA, else "idea"), pace (by auto: it goes on by day, the week having room),
#                                    joined (the agent who joined at the press, else ""), missing (how many kinds the plan missed when it passed) (spec 52 §2.7)
PLAN_STARTED_NOW = "plan_started_now"   # idea, device, via (gui/ideas_args.py VIA, else "idea"): a plan held for the night started now (spec 41 §4)
IDEA_QUEUED = "idea_queued"       # idea, queue ("now" · "night"), device, via (gui/ideas_args.py VIA, else "idea") (spec 41 §4)
TODO_DONE = "todo_done"           # idea, todo, kind, device, seconds since the plan, skipped (gone without it), words (a file described instead) (a secret's value never; spec 54 §1.3)
TASK_STATE = "task_state"         # idea, task, state, was, round, tier, role, seconds in the previous state, tokens, cost, ran_tier, effort,
#                                    check (true: a check task's), clean (true: a check that found nothing, merged with no commit; spec 43 §1.3)
CHECK_DONE = "check_done"         # idea, task, by (the checker's slug), found, fixed, left, round, cost: a round of a check task ended with findings read
RESULT_READY = "result_ready"     # idea, task, round, passed, failed, files, added, removed, cost, role
RESULT_DECIDED = "result_decided"  # idea, task, round, decision, why, into, pushed, conflict, device, seconds from result_ready,
#                                    dear (on a merge: the person said it cost too much for this, spec 36 §4)
TASK_STOPPED = "task_stopped"     # idea, task, device
TASK_SKIPPED = "task_skipped"     # idea, task, device: a task taken out of its plan before it ran (a check skipped)
CHECK_SKIPPED = "check_skipped"   # idea, by (the checker), skipped (false: taken again), task ("" before a plan), usd (what it spares), device
STOP_ALL = "stop_all"             # count, device
INTO_CHANGED = "into_changed"     # branch, push, device
GATE_MERGED = "gate_merged"       # commits, ideas, files (what dev held that main lacked), how ("fast-forward" · "merge"), pushed, into, main, device (spec 49 §2.1: dev merged into main)
PICK_ASKED = "pick_asked"         # idea, task, n, media (image · audio · video · text), round (spec 51 §2.4: a task left variants for the person to pick from)
PICK_ANSWERED = "pick_answered"   # idea, task, key (the variant's letter; null: none of them, new ones asked), note_chars, via (hand · drawer · screen; else idea), seconds from pick_asked, device, round (the round that was answered)
IDEA_FLAGGED = "idea_flagged"   # idea, goal (its party), by ("gate" · "done"), tasks, first_time, usd, days (spec 50 §2.2: a goal raised its flag in main)
OPENED = "opened"                 # what (idea · plan · todo · task · result · tab · map · recap · flag · week · push · party · gate · today · pick), ref, via (map · board · needs · agents · review · recap · week · flags · push · hand · party · today · gate; old lines ""), device
LIMITS_READ = "limits_read"       # provider, left, window
# Round 2 (docs/specs/34-v1-round-2.md §4): goals by dialog, agents by task type.
GOAL_SAVED = "goal_saved"         # goal, new, metrics (their names), links, priority, device, party (the id of the saved party it was picked from, else ""),
#                                    joined, out (the agent who joined, the member who left, else ""), via ("type": New goal by its type · "plan": a plan's stop · "": Edit the party) (spec 52 §2.7),
#                                    preset (the library's party the seats started from, else ""), stages ("<builders>/<checkers>": the leader's seats) (spec 59 §5)
GOAL_ACCEPTED = "goal_accepted"   # goal, met, by (its leader's name), and the call's measure
GOAL_READ = "goal_read"           # goal, state (asks · ready · raw: not read), seconds the keeper took, tier, effort
ROLE_SAVED = "role_saved"         # role, model, max_parallel, new, device, kinds (the types it takes), instruction_chars
ROLE_DROPPED = "role_dropped"     # role, kinds (the task types sent back to Grunt), device
KIND_SET = "kind_set"             # kind, role, device
# Spec 35 §12: the Board writes, starts what is safe, and works at night.
BOARD_SET = "board_set"           # target, autostart, night, device
IDEA_DRAFTED = "idea_drafted"     # idea, risk, triggers, questions, tier, effort, seconds
IDEA_ANSWERED = "idea_answered"   # idea, answers (how many), picked, recommended, typed, decided (spec 41 §10)
GOAL_ANSWERED = "goal_answered"   # goal, answers, picked, recommended, typed, decided, device (spec 41 §10)
# … and every keeper event (goal_read, idea_drafted, idea_answered, idea_said, plan_made, night_run) carries §0's
# step, prompt_chars, tokens ({"in", "out", "cache_read"}) and cost (null when unpriced, never 0)
KEEPER_STOPPED = "keeper_stopped"  # idea (the person stopped the keeper's run on it)
NIGHT_RUN = "night_run"           # drafted, started, refreshed, proposed, held, paced (the Board's Low ideas the week's pace left for later), seconds
PROPOSAL_MADE = "proposal_made"   # idea, goal
PROPOSAL_ANSWERED = "proposal_answered"   # idea, take, has_reason
BOARD_COMMITTED = "board_committed"   # commit, pages, what, seconds (spec 35 §13: the Board's pages on the work branch)
BOARD_HELD = "board_held"         # why (the work branch could not move to the Board's commit)
# Spec 37 §8: the project, as in an IDE (in the project's own log).
PROJECT_OPENED = "project_opened"   # new (never opened on this machine), git, device
PROJECT_CLOSED = "project_closed"   # stopped (its running tasks were stopped)
FILE_SAVED = "file_saved"         # kind (markdown · text), bytes: never the path or the text
GIT_COMMITTED = "git_committed"   # files (how many), device
GIT_PUSHED = "git_pushed"         # branch, device
# Spec 38 §11: Operations, the person's (in `~/.config/orkcraft/ops/events.jsonl`, never a project's): names,
# counts and states, never a field's, a draft's, a mail's or an issue's words.
OP_ADDED = "op_added"             # op, template, version, device
OP_PREPARED = "op_prepared"       # op, doubts (how many), step, tier, effort, prompt_chars, tokens, cost, seconds
OP_CHECKED = "op_checked"         # op, edited (the names corrected), again (prepared again), device
OP_DONE = "op_done"               # op, alone, step, tokens, cost, seconds
OP_FAILED = "op_failed"           # op, step, acted (true · false · null)
OP_DROPPED = "op_dropped"         # op, from (check · failed)
OP_NOT_RIGHT = "op_not_right"     # op, has_reason
OP_LEARNED = "op_learned"         # template, lines (how many), step, tokens, cost
OP_RULES_ANSWERED = "op_rules_answered"   # template, take, has_reason
OP_TRUST = "op_trust"             # template, alone, why (clean · edit · rules · not_right · version · reset)
# Spec 66 §1–§3: briefs, the person's alone. A template about people's events carry no field's value: never who, never a
# channel's name.
OP_KEPT = "op_kept"               # op, alone, edited (how many parts corrected), device (desktop · phone · alone)
OP_FORGOT = "op_forgot"           # template, runs (how many removed), standing (how many stopped): never the value
OP_STANDING = "op_standing"       # standing (its id), template, what (set · changed · stopped · added · skipped), device

# Spec 43 §4: the night's proposal to take a checker out of a goal's party, and the person's answer.
PARTY_PROPOSED = "party_proposed"   # goal, by (the checker's slug), runs
PARTY_ANSWERED = "party_answered"   # goal, by, take, has_reason, device

# Spec 44 §4: the Claude week came back; what was left of it unused.
WEEK_RESET = "week_reset"         # left (the share left, read just before it came back), provider

# Spec 43 §6: the person's own parties, saved from a goal and picked again in any project.
PARTY_SAVED = "party_saved"       # party (its id), members, own (agents of the person's own it carries), replaced, device
PARTY_DROPPED = "party_dropped"   # party, device

# Spec 62 §4.4: the spec after the start: a section written by hand, the plan change the leader proposes, and the answer.
IDEA_EDITED = "idea_edited"       # idea, section, chars, passed (its plan was passed), device: a section written by hand
PLAN_REVISED = "plan_revised"     # idea, changed (the sections it was made for), added, changed_n, dropped, usd_low, usd_high (what it adds; negative when it saves),
#                                    and the call's measure (step, prompt_chars, tokens, cost): the leader's plan change was saved
PLAN_CHANGE_ANSWERED = "plan_change_answered"   # idea, take, added, changed_n, dropped (taken: what was applied; kept: what was proposed), left (how many of its tasks had started meanwhile), via (gui/ideas_args.py VIA, else "idea"), device

# Spec 65 §6: Ideation's pitches judged, sent, passed and judged again (never a pitch's words).
PITCH_JUDGED = "pitch_judged"     # goal (the pitch), answer (invest · reshape · pass), kills (their ids), tokens, cost, seconds
PITCH_SENT = "pitch_sent"         # goal, to (the party), type (its goal type, else ""), as_decided (the party the Investor named), device
PITCH_PASSED = "pitch_passed"     # goal, as_decided (the Investor said pass), has_reason, device
PITCH_AGAIN = "pitch_again"       # goal, changed (its words were changed), device

# Spec 67 §4: a goal's route across parties, a release (A release) made and out, a party switch (never a goal's words).
IDEA_MOVED = "idea_moved"         # goal, from, to (parties), device
RELEASE_MADE = "release_made"     # goal, party, goals (n), parties (n), device
RELEASE_OUT = "release_out"       # goal, goals (n), days (from its first goal's flag to out; None when no flag is dated), device
PARTY_SHOWN = "party_shown"       # from, to (parties), face (desktop, phone), device

# Spec 42 §3: notifications to a paired phone (counts and tags, never a word of the push).
PUSH_SET = "push_set"             # on, device
PUSH_SENT = "push_sent"           # tag, devices, gone

EVENTS = (ASKED, ASSUMED, ANSWERED, STOPPED, WAIT_SKIPPED, HELD_AT_WORK, CAMP_LEFT, CAMP_BACK, QUEST_STARTED,
          QUEST_DONE, QUEST_SKIPPED, BUILT, CART_MOVED, LOOKED, IDEA_ADDED, IDEA_SAID, KEEPER_STATE, PLAN_MADE, PLAN_PASSED,
          TODO_DONE, TASK_STATE, CHECK_DONE, RESULT_READY, RESULT_DECIDED, TASK_STOPPED, TASK_SKIPPED, CHECK_SKIPPED, STOP_ALL, INTO_CHANGED, GATE_MERGED, IDEA_FLAGGED, PICK_ASKED, PICK_ANSWERED, OPENED, LIMITS_READ, GOAL_SAVED, GOAL_READ, GOAL_ACCEPTED, ROLE_SAVED,
          ROLE_DROPPED, KIND_SET, BOARD_SET, IDEA_DRAFTED, KEEPER_STOPPED, NIGHT_RUN, PROPOSAL_MADE, PROPOSAL_ANSWERED,
          IDEA_ANSWERED, GOAL_ANSWERED, PLAN_STARTED_NOW, IDEA_QUEUED, BOARD_COMMITTED, BOARD_HELD, PROJECT_OPENED, PROJECT_CLOSED, FILE_SAVED, GIT_COMMITTED,
          GIT_PUSHED, OP_ADDED, OP_PREPARED, OP_CHECKED, OP_DONE, OP_FAILED, OP_DROPPED, OP_NOT_RIGHT, OP_LEARNED,
          OP_RULES_ANSWERED, OP_TRUST, OP_KEPT, OP_FORGOT, OP_STANDING, PUSH_SET, PUSH_SENT, PARTY_PROPOSED, PARTY_ANSWERED, PARTY_SAVED, PARTY_DROPPED, WEEK_RESET, IDEA_EDITED, PLAN_REVISED, PLAN_CHANGE_ANSWERED,
          PITCH_JUDGED, PITCH_SENT, PITCH_PASSED, PITCH_AGAIN, IDEA_MOVED, RELEASE_MADE, RELEASE_OUT, PARTY_SHOWN)

_LOCK = threading.Lock()


def path(root: Path) -> Path:
    return Path(root) / PATH


def _plain(value: Any) -> Any:
    """A field as it is kept: plain data only, strings cut; None for anything else (it is dropped)."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return round(value, 3) if isinstance(value, float) else value
    if isinstance(value, str):
        return value[:TEXT_MAX]
    if isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value):
        return [v[:TEXT_MAX] for v in value][:50]
    if isinstance(value, dict) and len(value) <= 8 and all(isinstance(k, str) and (v is None or (
            isinstance(v, (int, float)) and not isinstance(v, bool))) for k, v in value.items()):
        return dict(value)                     # a small count of numbers: a call's tokens (spec 35 §0)
    return None


def line(event: str, at: dt.datetime | None = None, **fields: Any) -> dict | None:
    """The line `record` writes; None for an event not in `EVENTS`."""
    if event not in EVENTS:
        return None
    at = at or dt.datetime.now().astimezone()
    row: dict[str, Any] = {"at": at.isoformat(timespec="seconds"), "event": event}
    for k, v in fields.items():
        kept = _plain(v)
        if kept is not None or v is None:
            row[k] = kept
    return row


def record(root: Path | None, event: str, **fields: Any) -> bool:
    """One event, appended to the town's local log. False when nothing was written (no root, an unknown event,
    a disk that refused)."""
    row = line(event, **fields)
    if root is None or row is None:
        return False
    target = path(root)
    try:
        with _LOCK:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        return False
    return True


def read(root: Path, since: str = "", until: str = "") -> list[dict]:
    """The lines, oldest first; `since` / `until`: ISO days or times (the line's `at` compared as text), inclusive
    of `since`'s day, exclusive of `until`'s."""
    try:
        text = path(root).read_text(encoding="utf-8")
    except OSError:
        return []
    rows = []
    for raw in text.splitlines():
        try:
            row = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(row, dict) or row.get("event") not in EVENTS:
            continue
        at = str(row.get("at") or "")
        if (since and at < since) or (until and at >= until):
            continue
        if row["event"] == OPENED:
            row.setdefault("via", "")           # a line from before spec 39
        rows.append(row)
    return rows


def counts(root: Path, since: str = "", until: str = "") -> dict[str, int]:
    """How many of each event, every event named (0 when none)."""
    found = Counter(r["event"] for r in read(root, since, until))
    return {e: found.get(e, 0) for e in EVENTS}


def summary(root: Path, since: str = "", until: str = "") -> dict[str, Any]:
    """What the owner reads after a week (decisions §8): the counts, and how long the person's answers took."""
    rows = read(root, since, until)
    c = Counter(r["event"] for r in rows)
    waits = sorted(float(r["waited_s"]) for r in rows if r["event"] == ANSWERED and r.get("who") == "person"
                   and isinstance(r.get("waited_s"), (int, float)))
    median = waits[len(waits) // 2] if waits else None
    runs = {(r.get("building"), r.get("task")) for r in rows if r["event"] in (ASKED, ASSUMED)}
    return {"counts": {e: c.get(e, 0) for e in EVENTS}, "answer_wait_median_s": median,
            "tasks_with_questions_or_assumptions": len(runs), "first": rows[0]["at"] if rows else "",
            "last": rows[-1]["at"] if rows else ""}
