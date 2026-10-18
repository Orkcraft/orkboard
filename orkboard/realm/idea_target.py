"""The Board's Target (docs/specs/35-goals-window.md §1): thrift · balance · quality picks the tier and the reasoning
(effort) of every step of the Board, the keeper's and the orks'; and the clock the Board's night and reserve read.

    pick("draft", "balance")                       # ("elder", "medium")
    pick("refresh", "thrift")                      # None: thrift reads no goal again at night
    keeper_pick("talk", "quality", "haiku")        # ("haiku", "high"): the Taskmaster's own model wins
    task_pick("warrior", "thrift", "")             # ("laborer", "low"): Grunt runs on the shifted tier
    in_night("01:00-07:00", now)                   # inside the night window (the machine's local time)
    reserve_held(limits, settings, now)            # the reserve left for the person: None, or until when

One Target per Board, for the whole route board → pool → gate (decisions §44.3, §47.6). A role with a model set
(spec 34 §3) runs on it; the Target still gives the effort. No face, no model.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from orkcraft.realm import plans

TARGETS = ("thrift", "balance", "quality")
DEFAULT = "balance"
EFFORTS = ("low", "medium", "high", "xhigh", "max")      # the Claude CLI's `--effort` levels
STEPS = ("goal", "draft", "talk", "plan", "refresh", "propose", "task")
PROPOSALS = {"thrift": 0, "balance": 2, "quality": 3}  # the night's proposals by the Target (§8)
MAX_WAITING = 3                                          # never more proposals than this waiting in all
TIER_ROLE = "elder"                                      # the Taskmaster's default: its model is not the person's pick

# step → target → (tier, effort); a task's tier is relative: -1 one lighter, 0 its own, +1 one heavier.
MATRIX: dict[str, dict[str, tuple[Any, str] | None]] = {
    "goal": {"thrift": ("elder", "medium"), "balance": ("elder", "high"), "quality": ("elder", "xhigh")},
    "draft": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "talk": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "plan": {"thrift": ("elder", "low"), "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "refresh": {"thrift": None, "balance": ("elder", "medium"), "quality": ("elder", "high")},
    "propose": {"thrift": None, "balance": ("elder", "low"), "quality": ("elder", "medium")},
    "task": {"thrift": (-1, "low"), "balance": (0, "medium"), "quality": (1, "high")},
}


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
    from orkcraft.realm import harnesses
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


def reserve_held(limits, settings: dict | None, now: float, provider: str = "claude") -> float | None:
    """What starts by itself waits while the tool's `left` is at or below the reserve (by day, or inside the night
    window): until when (epoch seconds), else None. With no limits read for the tool, no reserve applies."""
    from orkcraft.realm import status
    left = left_of(limits, provider)
    if left is None:
        return None
    night = in_night(str((settings or {}).get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now))
    share = reserve(settings, night)
    if left > share:
        return None
    return status.reset_of(limits, provider, now, share) or now + status.UNKNOWN_RESET_S


def gate(plan: dict, limits, board: dict, now: float) -> str | float | None:
    """What holds a passed plan's tasks besides the spent window: "night" (it starts at night and the window is not
    open: its tasks wait, unheld), the reserve's reset (it started by itself), else None (spec 35 §5, §6)."""
    if plan.get("start_at") == "night" and not in_night(str(board.get("night") or "01:00-07:00"), dt.datetime.fromtimestamp(now)):
        return "night"
    if plan.get("passed_by") == "auto" or plan.get("start_at") == "night":
        return reserve_held(limits, board, now)
    return None
