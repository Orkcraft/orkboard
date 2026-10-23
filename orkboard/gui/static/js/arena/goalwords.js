// The party's goals, their flags and their filter in words (docs/specs/50-parties-and-goals.md §3.3, §3.5, §3.8): pure functions over `ideas.map`'s
// nodes (a goal is the code's idea) and `ideas.flags`. No signal and no template here; goals.js and its neighbours draw what these say.
import { planningOf, atWork, openTasks, money, plural, countOf } from "./arenawords.js";

/** The party's goals by where they lie in the left column (§3.3): at work (in the Board's order), Planning (the stops first, those that have been read),
 *  New (raw), those done that wait for main, and the flags (the newest first). `lead`: the leader's name. */
export function listsOf(g, nodes, lead) {
  const planning = planningOf(g, nodes, lead);
  const done = nodes.filter((n) => n.state === "done" || n.stage === "done");
  return { planning, work: nodes.filter(atWork), planRows: planning.rows, raw: planning.raw,
    waiting: done.filter((n) => !n.flag), flagged: done.filter((n) => n.flag).sort((a, b) => String(b.flag.at).localeCompare(String(a.flag.at))) };
}

/** How many goals wait for main: the map's count for the party (`waits_main`), else its done goals with no flag. */
export const waitsMain = (g, nodes) => g.waits_main ?? nodes.filter((n) => (n.state === "done" || n.stage === "done") && !n.flag).length;
/** *Goals n*: the goals that are not done and have been read, as the list shows them. */
export const goalsCount = (lists) => lists.work.length + lists.planRows.length;

/** A goal's element and whether it is drawn dim (a raw goal, not yet read: until its draft). */
export const elementOf = (n) => ({ name: n?.element || "", dim: n?.state === "raw" || n?.state === "reading" });

/** The elements, in orkUI's order (orkboard/realm/idea_element.py `ELEMENTS`). */
export const ELEMENTS = ["meadow", "ice", "dust", "void", "lava"];
/** The element a new goal of a party will get: the one used least among the party's open goals (not done), ties by the order above — the host's rule
 *  (`idea_element.pick`), so the dialog shows what `ideas.add` will answer. `nodes`: the party's goals in the map. */
export function nextElement(nodes) {
  const used = (nodes || []).filter((n) => n.state !== "done" && n.stage !== "done").map((n) => n.element).filter(Boolean);
  const count = (e) => used.filter((x) => x === e).length;
  return ELEMENTS.reduce((best, e) => (count(e) < count(best) ? e : best), ELEMENTS[0]);
}

/** The edges of a goal's pile: one to three, for its open tasks; none for a goal with none. */
export const edgesOf = (n) => Math.min(3, openTasks(n).length);

/** The mark at the right of a goal's row (§3.3): the sign's name, its tone and what it says. A stop is `alert`, a failure `cross`, work `work`, tonight `night`. */
export function goalMark(n) {
  const tasks = n.tasks || [];
  if (tasks.some((t) => t.state === "failed") && atWork(n)) return { sign: "cross", tone: "danger", label: "a task failed" };
  if (n.needs_you === "asks" || n.needs_you === "plan" || n.needs_you === "change" || n.needs_you === "proposal" || n.waits?.kind === "you" || tasks.some((t) => t.state === "picking")) return { sign: "alert", tone: "alert", label: "waits for you" };
  if (n.state === "reading" || n.state === "planning" || tasks.some((t) => t.state === "running" || t.state === "testing")) return { sign: "work", tone: "", label: "at work" };
  if (n.waits?.kind === "night" || tasks.some((t) => t.state === "held") && n.waits?.kind === "night") return { sign: "night", tone: "", label: "tonight" };
  return { sign: "", tone: "", label: "" };
}

/** A goal at work, in a line: *k/n in dev · implementation* (*checking*). */
export const workLine = (n) => `${n.progress?.done ?? 0}/${n.progress?.total ?? 0} in dev · ${n.stage === "checking" ? "checking" : "implementation"}`;

/** What a press on a goal's row does to the filter, said for its tooltip. */
export const pickTip = (picked) => (picked ? "Taken out of the filter: a press shows it with the others again" : "A press shows only this goal’s tasks; press more to add them");

// -- the filter --------------------------------------------------------------------------------------------------------------------------

/** *k of n goals*: how many of the party's goals the filter shows. */
export const filterWords = (shown, all) => `${shown.length} of ${all} goals`;
/** The goals of `nodes` the filter shows (`shown`: their slugs; [] shows all). */
export const throughFilter = (nodes, shown) => (shown.length ? nodes.filter((n) => shown.includes(n.slug)) : nodes);
export const inFilter = (shown, slug) => !shown.length || shown.includes(slug);
/** The sign a card or a result that is gone from a list leaves with (motion.js): *check* when its task merged, *cross* when it was dropped, *fade* when only
 *  the filter took it away (no sign, spec 50 §4.4), "" when it only went elsewhere. `nodes`: the party's goals as they are now. */
export function leaveOf(nodes, shown, goal, task) {
  const t = nodes.find((n) => n.slug === goal)?.tasks.find((y) => y.id === task);
  if (!t) return "";
  if (t.state === "merged") return "check";
  if (t.state === "dropped") return "cross";
  return inFilter(shown, goal) ? "" : "fade";
}

// -- flags -------------------------------------------------------------------------------------------------------------------------------

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "14 Oct" from a flag's time; "" when it does not read. */
export function flagDay(at) {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? "" : `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}
/** *14 Oct · ≈$2.10 · 4 of 4 first time*: a flag's day, its price (left out when unpriced) and how many of its tasks merged in their first round. */
export function flagWords(f) {
  return [flagDay(f.at), f.usd != null ? `≈${money(f.usd)}` : "", f.tasks ? `${f.first_time ?? 0} of ${f.tasks} first time` : ""].filter(Boolean).join(" · ");
}
/** The flagged goals as a row says them: the goal's short name, then its flag's words. */
export const flagRow = (n) => ({ slug: n.slug, short: n.short || n.title, title: n.title, words: flagWords(n.flag), at: n.flag.at });

/** *3 flags raised* (*1 flag raised*). */
export const raisedWords = (n) => `${n} ${n === 1 ? "flag" : "flags"} raised`;
/** *<a> is in main*, *<a> and <b> are in main*, *<a>, <b> and k more are in main*. */
export function inMainWords(shorts) {
  const n = shorts.length;
  if (n === 1) return `${shorts[0]} is in main`;
  if (n === 2) return `${shorts[0]} and ${shorts[1]} are in main`;
  return `${shorts[0]}, ${shorts[1]} and ${n - 2} more are in main`;
}

// -- the party line ---------------------------------------------------------------------------------------------------------------------------

/** *≈$2–4 a goal*: the party's price a goal (`ideas.party_price`'s low and high; Ideation's, `pitch`: *a pitch*, spec 65 §3); below $1 in cents; "" before it is read. */
export function priceWords(price) {
  if (!price || typeof price.low !== "number") return "";
  const { low, high } = price, each = price.pitch ? "a pitch" : "a goal";
  if (low < 1) return `≈$${low.toFixed(2)}–${high.toFixed(2)} ${each}`;
  const a = Math.round(low), b = Math.round(high);
  return a === b ? `≈$${a} ${each}` : `≈$${a}–${b} ${each}`;
}

/** *3 goals at work*, *1 goal at work*: for a tooltip. */
export const workingWords = (n) => plural(n, "goal", "goals") + " at work";

/** A party tab's words: its short name, *k/n*, and what a screen reader hears. */
export function tabWords(g, nodes, stops, working) {
  const c = countOf(g, nodes);
  return [g.short || g.title, `${c.done} of ${c.all} goals done`, stops ? (stops === 1 ? "1 stop waits for you" : `${stops} stops wait for you`) : "", working ? "at work" : ""].filter(Boolean).join(", ");
}
