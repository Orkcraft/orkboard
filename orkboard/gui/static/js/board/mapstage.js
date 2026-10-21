// One goal by stage (docs/specs/48-map-ideas.md): the stage track, the lanes, the columns, the stacks, and the words they say. Pure
// functions over `ideas.map`; the backend writes no words (realm/map_stage.py works the stage out).
import { NEEDS_WORDS, TASK_STATE, leftToDo } from "./maplayout.js";

export const STAGES = ["planning", "implementation", "checking"];
export const STAGE_WORDS = { planning: "Planning", implementation: "Implementation", checking: "Checking", done: "Done" };

/** *Implementation · round 2*: the stage in words, with its round above 1. */
export const stageWords = (n) => `${STAGE_WORDS[n.stage] || ""}${n.round > 1 && n.stage !== "planning" ? ` · round ${n.round}` : ""}`;

/** An idea at work or waiting for the person is shown expanded (§3.3). */
export const isExpanded = (n) => (n.stage !== "done" && (n.stage !== "planning" || !!n.needs_you || n.state === "plan")) || (n.results || []).length > 0;

/** A member's state in words (§3.2): *at work*, *next*, *tonight*, *free*, or the Needs you words. */
export function memberWords(m) {
  if (m.state === "needs") return NEEDS_WORDS[m.why] || "needs you";
  return { work: "at work", next: "next", tonight: "tonight", free: "free" }[m.state] || "";
}

/** A task's words on its card (§4.4): a result waiting is *in Review*; the rest as the preview says it. */
export const taskWords = (t) => (t.state === "review" ? "in Review" : TASK_STATE[t.state] || t.state);

/** The tasks the stage's lanes hold: in Implementation the build tasks, in Checking the checks, not merged and not dropped. */
export const stageTasks = (n) => (n.stage === "planning" ? [] : n.tasks.filter((t) => leftToDo(t) && (n.stage === "checking") === (t.band === "check")));

/** The lanes of an expanded idea: [{slug, name, head, state, why, tasks}]. Planning: the leader. Else the party's members with a
 *  task in the stage, in the party's order, then agents outside the party in the order their tasks come. */
export function lanesOf(n, goal) {
  const party = goal?.party || [];
  if (n.stage === "planning") {
    const lead = party.find((m) => m.band === "lead") || (goal?.leader && { ...goal.leader, state: "free", why: "" });
    return lead ? [{ ...lead, tasks: [] }] : [];
  }
  const tasks = stageTasks(n), out = [];
  for (const m of party) {
    const mine = tasks.filter((t) => t.by.slug === m.slug);
    if (mine.length) out.push({ slug: m.slug, name: m.name, head: m.head, state: m.state, why: m.why, tasks: mine });
  }
  for (const t of tasks) {
    if (out.some((l) => l.slug === t.by.slug)) continue;
    out.push({ slug: t.by.slug, name: t.by.name, head: t.head, state: "free", why: "", tasks: tasks.filter((x) => x.by.slug === t.by.slug) });
  }
  return out;
}

/** The waves of a stage's tasks, ascending: the columns. */
export const columnsOf = (tasks) => [...new Set(tasks.map((t) => t.wave))].sort((a, b) => a - b);

/** The tasks of one lane in one wave: a stack when there are several. */
export const stackOf = (lane, wave) => lane.tasks.filter((t) => t.wave === wave);

/** *k of n tasks in dev*: the merged tasks of all. */
export const inDevWords = (n) => `${n.progress.done} of ${n.progress.total} task${n.progress.total === 1 ? "" : "s"} in dev`;

/** *plan ≈$1–2*. */
export const planWords = (e) => (e ? `plan ≈$${Math.round(e.usd_low * 100) / 100}–${Math.round(e.usd_high * 100) / 100}` : "");

/** *≈$0.84 so far*, "" when unpriced. */
export const soFarWords = (usd) => (usd == null ? "" : `≈$${usd < 10 ? usd.toFixed(2) : Math.round(usd)} so far`);

/** *today 2 merged · ≈$1.15*. */
export const todayWords = (t) => (t ? `today ${t.merged} merged · ≈$${t.usd.toFixed(2)}` : "");

/** The tasks of an idea as pips: a filled one for each merged, a ringed one for each at work, an empty one for the rest. */
export const pipsOf = (n) => n.tasks.map((t) => (t.state === "merged" ? "done" : t.state === "running" || t.state === "testing" ? "working" : "todo"));
