"""The Board's Target (docs/specs/35-goals-window.md §1): thrift · balance · quality picks the tier and the reasoning
(effort) of every step of the Board, the keeper's and the orks'; and the clock the Board's night and reserve read.

    pick("draft", "balance")                       # ("elder", "medium")
    pick("refresh", "thrift")                      # None: thrift reads no goal again at night
    pick("op_act", "balance")                      # ("laborer", ""): an operation's action (spec 38 §4)
    keeper_pick("talk", "quality", "haiku")        # ("haiku", "high"): the Taskmaster's own model wins
    task_pick("warrior", "thrift", "")             # ("laborer", "low"): Grunt runs on the shifted tier
    in_night("01:00-07:00", now)                   # inside the night window (the machine's local time)
    reserve_held(limits, settings, now)            # the reserve left for the person: None, or until when
    pace(limits, now)                              # the Claude week's pace: "ahead" · "even" · "behind" · None (spec 44)

One Target per Board, for the whole route board → pool → gate (decisions §44.3, §47.6). A role with a model set
(spec 34 §3) runs on it; the Target still gives the effort. No face, no model.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from orkboard.realm import plans

TARGETS = ("thrift", "balance", "quality")
DEFAULT = "balance"
EFFORTS = ("low", "medium", "high", "xhigh", "max")      # the Claude CLI's `--effort` levels
STEPS = ("goal", "ask", "draft", "answer", "talk", "plan", "refresh", "propose", "task")
PROPOSALS = {"thrift": 0, "balance": 2, "quality": 3}  # the night's proposals by the Target (§8)
MAX_WAITING = 3                                          # never more proposals than this waiting in all
TIER_ROLE = "elder"                                      # the Taskmaster's default: its model is not the person's pick

# step → target → (tier, effort); a task's tier is relative: -1 one lighter, 0 its own, +1 one heavier.
MATRIX: dict[str, dict[str, tuple[Any, str] | None]] = {
    "goal": {"thrift": ("elder", "medium"), "balance": ("elder", "high"), "quality": ("elder", "xhigh")},
    # a member of a goal's party asks before its leader reads the goal (quality only: docs/specs/46-goal-trail.md §2)
    "ask": {"thrift": None, "balance": None, "quality": ("warrior", "low")},
    "draft": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    # the answer to a spec's questions (§0) is not in the spec's table: it finishes the draft, so it runs as the draft
    "answer": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "talk": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "plan": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "refresh": {"thrift": None, "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "propose": {"thrift": None, "balance": ("elder", "low"), "quality": ("elder", "medium")},
    # a goal's leader accepts the goal against its metrics once its ideas are done (core/idea_lead.py)
    "accept": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "task": {"thrift": (-1, "low"), "balance": (0, "medium"), "quality": (1, "high")},
    # Operations' calls (docs/specs/38-operations.md §4), under Operations' own Target: no effort on the laborer tier
    "op_prepare": {"thrift": ("warrior", "low"), "balance": ("warrior", "medium"), "quality": ("elder", "medium")},
    "op_act": {"thrift": ("laborer", ""), "balance": ("laborer", ""), "quality": ("warrior", "low")},
    "op_learn": {"thrift": ("laborer", ""), "balance": ("warrior", "low"), "quality": ("warrior", "medium")},
}
OP_STEPS = ("op_prepare", "op_act", "op_learn")


# §0: one call, one job. What a keeper call is given is built by code and cut to a cap (characters of the prompt, the
# call's own instructions not counted); how many files it may read; its budget in USD (`--max-budget-usd`) in balance,
# half in thrift, double in quality.
CONTEXT = {"goal": 12_000, "draft": 8_000, "answer": 8_000, "talk": 6_000, "plan": 10_000, "refresh": 12_000, "accept": 10_000,
           "propose": 10_000, "ask": 4_000, "op_prepare": 12_000, "op_act": 6_000, "op_learn": 6_000}
READS = {"goal": 8, "draft": 6, "plan": 6, "refresh": 6, "talk": 2, "answer": 2, "propose": 0, "ask": 0, "accept": 4}
CAPS = {"goal": 1.00, "draft": 0.60, "answer": 0.40, "talk": 0.20, "plan": 0.60, "refresh": 0.50, "propose": 0.30, "ask": 0.10, "accept": 0.60,
        "op_prepare": 0.30, "op_act": 0.10, "op_learn": 0.10}
GOAL_QUESTIONS = {"thrift": 3, "balance": 3, "quality": 5}   # a goal's read keeps at most this many questions, its party's too (spec 46 §1)
BUDGET_SHARE = {"thrift": 0.5, "balance": 1.0, "quality": 2.0}


def budget(step: str, target: str) -> float | None:
    """A keeper call's budget in USD under the Target; None for a step with no cap."""
    if step not in CAPS:
        return None
    return round(CAPS[step] * BUDGET_SHARE.get(target if target in TARGETS else DEFAULT, 1.0), 2)


def cut(parts: list[tuple[str, str]], cap: int) -> str:
    """A call's context from its parts ((heading, text), in the order they matter), cut so the whole stays within
    `cap` characters: a part that does not fit is cut, the ones after it are left out."""
    out, left = [], cap
    for head, text in parts:
        block = f"{head}:\n{(text or '').strip() or '(none)'}\n\n"
        if len(block) <= left:
            out.append(block)
            left -= len(block)
            continue
        if left > len(head) + 40:
            out.append(block[:left - 2].rstrip() + "…\n")
        break
    return "".join(out)


def target_of(settings: dict | None) -> str:
    value = (settings or {}).get("target")
    return value if value in TARGETS else DEFAULT


def pick(step: str, target: str, tier: str = "warrior") -> tuple[str, str] | None:
    """(tier, effort) of a step under a target; None when the target skips the step. `tier`: a task's planned tier."""
    row = MATRIX[step].get(target if target in TARGETS else DEFAULT)
    if row is None:
        return None
    what, effort = row
    return (plans.shift(tier, what) if step == "task" else what), effort


def keeper_pick(step: str, target: str, taskmaster: str = TIER_ROLE) -> tuple[str, str] | None:
    """A keeper step's (model or tier, effort): the Taskmaster's model, when it is not its default elder, replaces
    the tier; the Target still gives the effort."""
    got = pick(step, target)
    if got is None:
        return None
    tier, effort = got
    return (taskmaster if taskmaster and taskmaster != TIER_ROLE else tier), effort


def task_pick(tier: str, target: str, role_model: str = "") -> tuple[str, str]:
    """A task's (model or tier it runs on, effort): a role with a model keeps it; Grunt ("") the shifted tier."""
    shifted, effort = pick("task", target, tier or "warrior")
    return (role_model or shifted), effort


def tier_of(model: str) -> str:
    """The tier a model or tier counts as in an estimate (a model the tables do not know: warrior)."""
    if model in plans.tiers.TIERS:
        return model
    from orkboard.realm import harnesses
    return harnesses.tier_of_model(model) or "warrior"


# -- the night and the reserve (§6, §7) -------------------------------------------------------------------------

def _minutes(text: str) -> int:
    hh, mm = text.split(":")
    return int(hh) * 60 + int(mm)


def night_start(spec: str, now: dt.datetime) -> dt.datetime | None:
    """When the night window `now` is in began ("01:00-07:00", local time; it may cross midnight); None outside it."""
    try:
        a, b = (_minutes(x) for x in str(spec).split("-"))
    except ValueError:
        return None
    m = now.hour * 60 + now.minute
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if a < b:
        return day + dt.timedelta(minutes=a) if a <= m < b else None
    if m >= a:
        return day + dt.timedelta(minutes=a)
    if m < b:
        return day - dt.timedelta(days=1) + dt.timedelta(minutes=a)
    return None


def in_night(spec: str, now: dt.datetime | None = None) -> bool:
    return night_start(spec, now or dt.datetime.now()) is not None


def left_of(limits, provider: str = "claude") -> float | None:
    """The smallest share left among the tool's windows, None when none was read."""
    left = [lim.remaining for lim in limits or () if getattr(lim, "provider", "") == provider
            and getattr(lim, "remaining", None) is not None]
    return min(left) if left else None


def reserve(settings: dict | None, night: bool) -> float:
    s = settings or {}
    key, default = ("reserve_night", 0.1) if night else ("reserve_day", 0.3)
    value = s.get(key, default)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default


# -- the week's pace (docs/specs/44-week-pace.md §1) --------------------------------------------------------------

MARGIN = 0.10                     # the week is `ahead` when its share left is this far above the share still to come
SOON_S = 3600                     # by day, within this of the five-hour window's reset its reserve is the night's
WEEK_S = 7 * 24 * 3600
_EDGE = 1e-9                      # a percent read is a float: the edges are compared with this much room


def week(limits, now: float, provider: str = "claude") -> dict | None:
    """The tool's weekly window as read: `{"left", "rest", "reset"}` (its share left, the share of the week still to
    come, 0..1, and when it comes back, epoch seconds); None with no such window (not read, an error, another tool)."""
    from orkboard.realm import status
    for lim in limits or ():
        if getattr(lim, "provider", "") != provider or getattr(lim, "window", "") != "weekly" or getattr(lim, "error", None):
            continue
        left, reset = getattr(lim, "remaining", None), status.reset_at(lim)
        if left is None or reset is None:
            continue
        return {"left": float(left), "rest": min(max((reset - now) / WEEK_S, 0.0), 1.0), "reset": reset}
    return None


def pace(limits, now: float, provider: str = "claude") -> str | None:
    """The week's pace: "ahead" (its share left at least MARGIN above the share to come), "behind" (below it), else
    "even"; None with no `week`."""
    w = week(limits, now, provider)
    if w is None:
        return None
    if w["left"] - w["rest"] >= MARGIN - _EDGE:
        return "ahead"
    return "behind" if w["left"] < w["rest"] else "even"


def reserve_held(limits, settings: dict | None, now: float, provider: str = "claude") -> float | None:
    """What starts by itself waits while any of the tool's windows has its share or less left: the day's reserve by day,
    the night's inside the night window (the five-hour window's, by day within SOON_S of its reset and while the week's
    pace is not behind, is the night's: spec 44 §1). Until when (epoch seconds), else None. With no limits read for the
    tool, no reserve applies."""
    from orkboard.realm import status
    rows = [lim for lim in limits or () if getattr(lim, "provider", "") == provider
            and getattr(lim, "remaining", None) is not None]
    if not rows:
        return None
    night = in_night(str((settings or {}).get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now))
    easing = False if night else pace(limits, now, provider) != "behind"
    held, resets = False, []
    for lim in rows:
        reset = status.reset_at(lim)
        soon = easing and getattr(lim, "window", "") == "session" and reset is not None and 0 < reset - now <= SOON_S
        if lim.remaining <= reserve(settings, night or soon):
            held = True
            if reset is not None and reset > now:
                resets.append(reset)
    if not held:
        return None
    return max(resets) if resets else now + status.UNKNOWN_RESET_S


def board_low(plan: dict, board: dict | None = None) -> bool:
    """A plan the Board itself put off to the night (a Low plan its autostart passed), while `autostart` is on: the
    only work the week's pace moves (spec 44 §2, §3). A plan of before reads as the person's."""
    return plan.get("start_at") == "night" and plan.get("start_at_by") == "board" \
        and bool((board or {}).get("autostart", True))


def week_hold(plan: dict, limits, board: dict, now: float) -> float | None:
    """The week's reset when the Board's Low plan is held for the week: at night, with the week `behind`."""
    if not board_low(plan, board) or not in_night(str(board.get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now)) \
            or pace(limits, now) != "behind":
        return None
    return (week(limits, now) or {}).get("reset")


def gate(plan: dict, limits, board: dict, now: float, day_free: bool = True) -> str | float | None:
    """What holds a passed plan's tasks besides the spent window: "night" (it starts at night and the window is not
    open: its tasks wait, unheld), the week's reset (the Board's Low plan, at night, the week behind: spec 44 §3), the
    reserve's reset (it started by itself), else None (spec 35 §5, §6). The Board's Low plan starts by day while the
    week is `ahead`, one at a time (`day_free`: no other starts by day in this project)."""
    if plan.get("start_at") == "night" and not in_night(str(board.get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now)):
        if not (board_low(plan, board) and day_free and pace(limits, now) == "ahead"):
            return "night"
    elif (until := week_hold(plan, limits, board, now)) is not None:
        return until
    if plan.get("passed_by") == "auto" or plan.get("start_at") == "night":
        return reserve_held(limits, board, now)
    return None
