// The Map's words and shape (docs/specs/39-map.md §3–§4), apart from its components: what a node says besides its Board row's
// words (those are `rowOf`'s), the tiers and the waves, the edges' lines. The backend writes no words; these are the Map's own
// only for `waits`, the same as the Agents chips'.
import { say } from "../link.js";
import { hhmm, dayAt } from "./store.js";
import { rowOf } from "./tracks.js";

/** The Needs you kinds on a node, in words (§4.3). */
export const NEEDS_WORDS = { asks: "asks you", plan: "plan ready", todo: "a to-do waits", failed: "failed", proposal: "proposed" };
/** A task's state in words: the preview's task view and the node's unfolded rows say it the same. */
export const TASK_STATE = { waiting: "waiting", ready: "queued", running: "working", testing: "testing", review: "at Review", merged: "merged",
  failed: "needs you", held: "held", dropped: "dropped" };
const GOAL_WORDS = { reading: "reading", asks: "asks you", ready: "ready" };

const after = (until) => (until ? ` · after ${hhmm(until)}` : "");

/** Why a node that is not done does not move (§4.3), in words; "" for what the Needs you words say. */
export function waitsWords(w) {
  if (!w) return "";
  const who = w.title || w.ref || "another idea";
  return { idea: `waits for ${who}`, files: `same files as ${who}`, limits: `waits for limits${after(w.until)}`,
    reserve: `keeps your reserve${after(w.until)}`, night: "tonight", stopped: "stopped",
    week: `waits: the week is behind${w.until ? ` · until ${dayAt(w.until)}` : ""}` }[w.kind] || "";
}

/** `≈$0.40–1.20` while a plan has not started. */
export const estimateWords = (e) => (e ? `≈$${e.usd_low.toFixed(2)}–${e.usd_high.toFixed(2)}` : "");

/** `≈$12 so far`, or — when nothing is priced. */
export const spentWords = (usd) => (usd == null ? "—" : `≈$${usd < 10 ? usd.toFixed(2) : Math.round(usd)} so far`);

export const goalState = (state) => say(GOAL_WORDS[state] || state || "");

/** What a node shows: the Board's row words, then what only the Map adds. */
export function nodeView(n, titles) {
  const [rowWords, spin] = rowOf(n, titles);
  const needs = NEEDS_WORDS[n.needs_you] || "";
  const wait = n.state === "done" || n.waits?.kind === "you" ? "" : waitsWords(n.waits);
  return { words: rowWords, needs, wait: wait && !rowWords.includes(wait) ? wait : "",
    // a node moves by itself unless it waits for something; a spinner shows only for what runs now
    spin: spin || (["working", "reading", "planning"].includes(n.state) && !wait),
    cost: estimateWords(n.estimate) };
}

/** The nodes of a goal that show in the tree, by tier (top to bottom), each tier in the Board's order. */
export function tiersOf(nodes) {
  const by = new Map();
  for (const n of nodes) if (!n.folded) by.set(n.tier, [...(by.get(n.tier) || []), n]);
  return [...by.keys()].sort((a, b) => a - b).map((t) => by.get(t));
}

/** A node's tasks in waves: a task is in the wave after the deepest it follows (the spec's Stages). */
export function wavesOf(tasks) {
  const wave = {};
  const of = (t, seen = new Set()) => {
    if (wave[t.id]) return wave[t.id];
    if (seen.has(t.id)) return 1;                                // `after` closes no cycle; a broken one does not hang the page
    seen.add(t.id);
    const deps = (t.after || []).map((id) => tasks.find((x) => x.id === id)).filter(Boolean);
    return (wave[t.id] = 1 + Math.max(0, ...deps.map((d) => of(d, seen))));
  };
  tasks.forEach((t) => of(t));
  const out = [];
  for (const t of tasks) (out[wave[t.id] - 1] ||= []).push(t);
  return out.filter(Boolean);
}

/** The line from the bottom of the idea depended on to the top of the one that depends (no arrowheads: the lower waits). */
export function curve(a, b) {
  const k = Math.max(12, (b.y - a.y) / 2);
  return `M${a.x.toFixed(1)} ${a.y.toFixed(1)} C${a.x.toFixed(1)} ${(a.y + k).toFixed(1)} ${b.x.toFixed(1)} ${(b.y - k).toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`;
}

// -- the trail (the Map as a goal's path, decisions §53): from how far it is, through its ideas, to its flag ------------------

/** How far a goal is, in %: its ideas done, and the share of the tasks done of each idea at work (a plan made adds no drop). */
export function progressOf(nodes) {
  if (!nodes.length) return 0;
  const done = nodes.filter((n) => n.state === "done").length;
  const part = nodes.filter((n) => n.state !== "done" && n.progress?.total > 0).reduce((s, n) => s + n.progress.done / n.progress.total, 0);
  return Math.round(((done + part) / nodes.length) * 100);
}

/** A task left to do: not merged, not dropped. */
export const leftToDo = (t) => t.state !== "merged" && t.state !== "dropped";

/** The line from the right of one stop on the trail to the left of the next (no arrowheads: the right one waits). */
export function trailCurve(a, b) {
  const k = Math.max(16, (b.x - a.x) / 2);
  return `M${a.x.toFixed(1)} ${a.y.toFixed(1)} C${(a.x + k).toFixed(1)} ${a.y.toFixed(1)} ${(b.x - k).toFixed(1)} ${b.y.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`;
}

/** The trail's lines: from the start to each stop that waits for no stop shown, between the stops, from each stop no stop
 *  shown waits for to the flag. `shown`: the slugs on the trail; `edges`: the goal's ({from, to}). */
export function trailEdges(shown, edges) {
  const on = new Set(shown);
  const inner = edges.filter((e) => on.has(e.from) && on.has(e.to));
  const into = new Set(inner.map((e) => e.to)), out = new Set(inner.map((e) => e.from));
  return [...shown.filter((s) => !into.has(s)).map((s) => ({ from: "@start", to: s })), ...inner,
    ...shown.filter((s) => !out.has(s)).map((s) => ({ from: s, to: "@end" }))];
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** *7 ideas · 23 results · 19 the first time · ≈$38 · 9 days* (spec 42 §2.3): under a met goal's flag; a part that is null is left out. */
export function tallyWords(t) {
  if (!t) return "";
  return [count(t.ideas, "idea", "ideas"), count(t.results, "result", "results"), `${t.first_time} the first time`,
    t.usd != null && `≈$${Math.round(t.usd)}`, t.days != null && count(t.days, "day", "days")].filter(Boolean).join(" · ");
}

/** "18 October" from a verdict's time. */
export function flagDate(at) {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? "" : `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

/** *met, says Product manager · 18 October* (spec 42 §2.4). */
export const flagWords = (f) => [`met, says ${f.by}`, flagDate(f.at)].filter(Boolean).join(" · ");
