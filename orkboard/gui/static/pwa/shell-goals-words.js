// The goals of a party as data (docs/specs/50-parties-and-goals.md §3.5, §3.8, §6.3, §6.4, §6.8): what the goals bar and the Goals sheet list (At work, Planning, Waits for main, Flags), the
// goals picked to show only their tasks (the filter: kept per party for the session, in `st.picks`), the party bar's words and the flag line's. Pure: no node is made here.
import { STAGE_WORDS, stageOf } from "./shell-map-idea.js";

const STOPS = ["asks", "plan", "proposal", "todo"];                  // what a goal that asks you waits for (a failure is its own mark)
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const FLAGS_SHOWN = 10;                                       // the newest of a party's flags, then *All n*
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** A flag's date, *14 Oct*, "" when it does not read. */
export function flagDate(at) {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? "" : `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

/** A flag's tally, *14 Oct · ≈$2.10 · 4 of 4 first time*: a part that is not known is left out. */
export function flagTally(f) {
  return [flagDate(f.at), f.usd != null && `≈$${Number(f.usd).toFixed(2)}`, f.tasks ? `${f.first_time ?? 0} of ${f.tasks} first time` : ""].filter(Boolean).join(" · ");
}

const when = (at) => { const t = Date.parse(at); return Number.isNaN(t) ? 0 : t; };

/** The flags of the goals among `nodes`, newest first: [{slug, title, short, element, at, tasks, first_time, usd, days}]. */
export function flagsOf(nodes) {
  return (nodes || []).filter((n) => n.flag).map((n) => ({ slug: n.slug, title: n.title, short: n.short || n.title, element: n.element || "", ...n.flag }))
    .sort((a, b) => when(b.at) - when(a.at));
}

/** Whether a goal is in main: the gate says so (it lists the goals still in dev), or there is no gate. */
export const inMain = (gate, slug) => Boolean(gate && (gate.same || !(gate.ideas || []).some((i) => i.slug === slug)));

/** What the goals bar and the Goals sheet list for one party: its goals at work, in Planning (the ones the leader has read and the new ones), the done ones that wait for main and its flags. A row:
 *  {slug, title, short, element, raw, line, care, mark, markTip, edges, open}; `model`: shell-arena-words.js `modelOf`. */
export function goalsOf(st, model) {
  const nodes = model.nodes;
  const done = (n) => n.state === "done";
  const edges = (n) => Math.min(3, (n.tasks || []).filter((t) => t.state !== "merged" && t.state !== "dropped").length);
  const row = (n, rest) => ({ slug: n.slug, title: n.title, short: n.short || n.title, element: n.element || "", raw: n.state === "raw", edges: edges(n), open: { kind: "idea", slug: n.slug },
    care: false, mark: "", markTip: "", ...rest });
  const atWork = nodes.filter((n) => !done(n) && ["implementation", "checking"].includes(stageOf(n))).map((n) => {
    const tasks = (n.tasks || []).filter((t) => t.state !== "dropped");
    const failed = tasks.some((t) => t.state === "failed"), live = tasks.some((t) => t.state === "running" || t.state === "testing");
    const merged = tasks.filter((t) => t.state === "merged").length;
    return row(n, { line: `${merged}/${tasks.length} in dev · ${STAGE_WORDS[stageOf(n)].toLowerCase()}`, mark: failed ? "cross" : live ? "work" : "", markTip: failed ? "failed" : live ? "at work" : "" });
  });
  const bySlug = new Map(nodes.map((n) => [n.slug, n]));
  const planning = model.planning.map((it) => row(bySlug.get(it.idea) || { slug: it.idea, title: it.title }, { line: it.words, care: it.kind === "stop",
    mark: it.kind === "stop" ? "alert" : it.kind === "busy" ? "work" : "", markTip: it.kind === "stop" ? "asks you" : it.kind === "busy" ? "at work" : "" }));
  const waits = nodes.filter((n) => done(n) && !n.flag && !inMain(st.gate, n.slug)).map((n) => row(n, { line: "in dev", mark: "check" }));
  const flags = flagsOf(nodes);
  const asking = nodes.filter((n) => !done(n) && STOPS.includes(n.needs_you)).length;
  const all = [...atWork, ...planning];
  return { atWork, planning, waits, flags, all, asking, n: all.length };
}

/** The goals bar's count, *3 of 12 done*: the party's done goals of all its goals (the stage switch's counts say what is at work and what asks you). */
export const barWords = (g) => `${g.done ?? 0} of ${g.ideas ?? 0} done`;

/** *k of n goals* (the filter on): the picked goals that are still among the party's, of all its goals that are not done. */
export const filterWords = (picked, list) => `${picked.length} of ${plural(list.n, "goal")}`;

/** The party's count, *3/12 done* (its done goals of all its goals, the map's `done` and `ideas`). */
export const doneWords = (g) => `${g.done ?? 0}/${g.ideas ?? 0} done`;

/** The party's price a goal as a range, *$2–4* (below $1 in cents; "" without a price), from `ideas.party_price`'s `{low, high}`. */
export function priceRange(price) {
  if (!price || price.low == null || price.high == null) return "";
  const { low, high } = price, a = Math.round(low), b = Math.round(high);
  return low < 1 ? `$${low.toFixed(2)}–${high.toFixed(2)}` : a === b ? `$${a}` : `$${a}–${b}`;
}

/** The party's price a goal, *≈$2–4 a goal* ("" without one). */
export const priceWords = (price) => (priceRange(price) ? `≈${priceRange(price)} a goal` : "");

/** The flag line's words: *1 flag raised · <a> is in main*, *2 flags raised · <a> and <b> are in main*, *4 flags raised · <a>, <b> and 2 more are in main*. */
export function flagLine(flags) {
  const n = flags.length, names = flags.map((f) => f.short);
  const who = n === 1 ? `${names[0]} is in main` : n === 2 ? `${names[0]} and ${names[1]} are in main` : `${names[0]}, ${names[1]} and ${n - 2} more are in main`;
  return { head: `${plural(n, "flag")} raised`, tail: who };
}

/** The flags newer than what this device saw (`seen`: the newest `at`, in ms), and the newest `at` among all of them. */
export function freshFlags(nodes, seen) {
  const all = flagsOf(nodes);
  return { fresh: all.filter((f) => when(f.at) > seen), newest: all.reduce((m, f) => Math.max(m, when(f.at)), 0) };
}
