// The goals of a party as data (docs/specs/50-parties-and-goals.md §3.5, §3.8, §6.3, §6.4, §6.8): what the goals bar and the Goals sheet list (At work, Planning, Waits for main, Flags), the
// goals picked to show only their tasks (the filter: kept per party for the session, in `st.picks`), the party bar's words and the flag line's. Ideation's goals are pitches (spec 65 §8): a pitch's
// line in words (`pitchLine`), the stage it is drawn under (`pitchStage`) and the bar's *4 pitches · 1 passed*. Pure: no node is made here.
import { STAGE_WORDS, stageOf } from "./shell-map-idea.js";
import { hhmm } from "./shell-words.js";
import { pctOf, pctRange } from "./shell-spend.js";

const STOPS = ["asks", "plan", "change", "proposal", "todo"];        // what a goal that asks you waits for (a failure is its own mark; `change`: a plan change, spec 62)
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const FLAGS_SHOWN = 10;                                       // the newest of a party's flags, then *All n*
export const FLAG_ROW = 6;                                           // the flag line's row holds the elements of this many of its goals (spec 64 §1.2)
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** A flag's date, *14 Oct*, "" when it does not read. */
export function flagDate(at) {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? "" : `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

/** A flag's tally, *14 Oct · ≈$2.10 · 4 of 4 first time*: a part that is not known is left out. */
export function flagTally(f) {
  return [flagDate(f.at), f.usd != null && `≈${pctOf(f.usd) || `$${Number(f.usd).toFixed(2)}`}`, f.tasks ? `${f.first_time ?? 0} of ${f.tasks} first time` : ""].filter(Boolean).join(" · ");
}

const when = (at) => { const t = Date.parse(at); return Number.isNaN(t) ? 0 : t; };

/** The flags of the goals among `nodes`, newest first: [{slug, title, short, element, at, tasks, first_time, usd, days, release, own}]. `release`: the last release that holds the goal (spec 68: `{goal, party, version, out}`)
 *  or none; `own`: the goal is itself a release (`{version, goals, out}`), else null. */
export function flagsOf(nodes) {
  return (nodes || []).filter((n) => n.flag).map((n) => ({ slug: n.slug, title: n.title, short: n.short || n.title, element: n.element || "", ...n.flag, own: n.release || null }))
    .sort((a, b) => when(b.at) - when(a.at));
}

// -- a goal's route and its release (docs/specs/68-release-and-route.md §0, §7) ---------------------------------------------------------------------------

/** A party's short name by its slug, from the Map (the slug itself when the Map does not have it). */
export const partyNameOf = (st, slug) => { const g = (st.map?.goals || []).find((x) => x.slug === slug); return g ? g.short || g.title || slug : slug || ""; };

/** Whether the project has a Release party (its leader is the Release manager): a flag then waits for a release or is in one. */
export const hasReleaseParty = (st) => (st.map?.goals || []).some((g) => g.leader?.slug === "release-manager");

const join = (...parts) => parts.filter(Boolean).join(" ");
const kOfN = (done, total) => (total ? ` · ${done || 0} of ${total}` : "");

/** What a pitch's goal is now as the pitch's node says it (`goal_state`): *At work in Mobile app · 3 of 7* · *In main* · *In Release 1.4* · *Out in 1.4* · *Dropped*; `name`: a party's name by its slug. */
export function goalStateWords(gs, name = (s) => s) {
  if (!gs) return "";
  if (gs.state === "dropped") return "Dropped";
  const r = gs.release;
  if (r) return r.out ? join("Out in", r.version) : join("In", name(r.party), r.version);
  if (gs.flag) return "In main";
  return `At work in ${name(gs.party)}${kOfN(gs.done, gs.total)}`;
}

/** What a step of a goal's route says (`node.route`, spec 68 §2.1): *From Ideation: Invest, 22 Oct* · *Moved from Mobile app* · *At work in Mobile app · 3 of 7* · *In main* · *In Release 1.4* · *Out in 1.4*. */
export function routeWords(step, name = (s) => s) {
  switch (step.step) {
    case "pitch": return `From ${name(step.party)}: ${[step.word || step.answer, flagDate(step.at)].filter(Boolean).join(", ")}`;
    case "moved": return `Moved from ${name(step.from || step.party)}`;
    case "party": return `At work in ${name(step.party)}${kOfN(step.done, step.total)}`;
    case "main": return "In main";
    case "release": return step.out ? join("Out in", step.version) : join("In", name(step.party), step.version);
    default: return "";
  }
}

/** A flag's release in a party's Flags group: *In Release 1.4* · *Out in 1.4* · *Waits for a release* (only in a project with a Release party); "" otherwise. A release's own row says its version and goals (`releaseLine`). */
export function flagRelease(f, withRelease, name = (s) => s) {
  if (f.own) return "";
  if (f.release) return f.release.out ? join("Out in", f.release.version) : join("In", name(f.release.party), f.release.version);
  return withRelease ? "Waits for a release" : "";
}

/** *1.4 · 3 goals* (a release's row in the Release party's Flags), *Out in 1.4* once it is out. */
export const releaseLine = (own) => (own.out ? join("Out in", own.version) : [own.version, plural((own.goals || []).length, "goal")].filter(Boolean).join(" · "));

/** *3 flags wait for a release* (*1 flag waits for a release*). */
export const waitWords = (n) => `${plural(n, "flag")} ${n === 1 ? "waits" : "wait"} for a release`;

/** Whether a goal is in main: the gate says so (it lists the goals still in dev), or there is no gate. */
export const inMain = (gate, slug) => Boolean(gate && (gate.same || !(gate.ideas || []).some((i) => i.slug === slug)));

/** What the goals bar and the Goals sheet list for one party: its goals at work, in Planning (the ones the leader has read and the new ones), the done ones that wait for main and its flags. A row:
 *  {slug, title, short, element, raw, type, line, care, mark, markTip, edges, open} (`type`: the goal's type, {id, name, sign}, or null); `model`: shell-arena-words.js `modelOf`. */
export function goalsOf(st, model) {
  if (model.goal?.ideation) return pitchesOf(model, (slug) => partyNameOf(st, slug));
  const nodes = model.nodes;
  const done = (n) => n.state === "done";
  const edges = (n) => Math.min(3, (n.tasks || []).filter((t) => t.state !== "merged" && t.state !== "dropped").length);
  const row = (n, rest) => ({ slug: n.slug, title: n.title, short: n.short || n.title, element: n.element || "", raw: n.state === "raw", edges: edges(n), open: { kind: "idea", slug: n.slug },
    type: n.type?.sign ? n.type : null, care: false, mark: "", markTip: "", ...rest });
  const atWork = nodes.filter((n) => !done(n) && ["implementation", "checking"].includes(stageOf(n))).map((n) => {
    const tasks = (n.tasks || []).filter((t) => t.state !== "dropped");
    const failed = tasks.some((t) => t.state === "failed"), live = tasks.some((t) => t.state === "running" || t.state === "testing"), picking = tasks.some((t) => t.state === "picking");
    const merged = tasks.filter((t) => t.state === "merged").length;
    return row(n, { line: `${merged}/${tasks.length} in dev · ${STAGE_WORDS[stageOf(n)].toLowerCase()}${picking && !failed ? " · asks you to pick" : ""}`, care: picking && !failed,
      mark: failed ? "cross" : picking ? "alert" : live ? "work" : "", markTip: failed ? "failed" : picking ? "asks you to pick" : live ? "at work" : "" });
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

/** The goals bar's count, *3 of 12 goals done*: the party's done goals of all its goals (spec 52 §5.2); Ideation's *4 pitches · 1 passed* (a pitch is never done). */
export const barWords = (g) => (g.ideation ? pitchCount(g) : `${g.done ?? 0} of ${plural(g.ideas ?? 0, "goal")} done`);

const NAME_CUT = 14;                                                 // the goals bar's party name: cut here, with an ellipsis

/** The party's short name as the goals bar says it, cut at 14 characters with an ellipsis. */
export const barName = (g) => { const s = g.short || g.title || ""; return s.length > NAME_CUT ? `${s.slice(0, NAME_CUT - 1)}…` : s; };

/** *k of n goals* (the filter on): the picked goals that are still among the party's, of all its goals that are not done. */
export const filterWords = (picked, list) => `${picked.length} of ${plural(list.n, "goal")}`;

/** The party's count, *3/12 done* (its done goals of all its goals, the map's `done` and `ideas`); Ideation's *4 pitches · 1 passed*. */
export const doneWords = (g) => (g.ideation ? pitchCount(g) : `${g.done ?? 0}/${g.ideas ?? 0} done`);

/** The party's price a goal as a range, *$2–4* (below $1 in cents; "" without a price), from `ideas.party_price`'s `{low, high}`. */
export function priceRange(price) {
  if (!price || price.low == null || price.high == null) return "";
  const { low, high } = price, a = Math.round(low), b = Math.round(high);
  if (pctRange(low, high)) return pctRange(low, high);
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

// -- Ideation's pitches (docs/specs/65-ideation.md §8) ------------------------------------------------------------------------------------------------------

/** *4 pitches · 1 passed* (no passed part when none is). */
export const pitchCount = (g) => [plural(g.ideas ?? 0, "pitch", "pitches"), g.passed ? `${g.passed} passed` : ""].filter(Boolean).join(" · ");

/** How many of a pitch's four views have answered. */
export const answeredOf = (p) => (p?.views || []).filter((v) => v.answered).length;

/** The stage a pitch is drawn under: the Map's `stage` (*Pitch* while new or failed, *Views* while they answer, *Decision* from the case against on); for a host without one, by its state. */
export function pitchStage(n) {
  if (["planning", "implementation", "checking"].includes(n.stage)) return n.stage;
  return n.state === "raw" || n.state === "failed" ? "planning" : n.state === "judging" && answeredOf(n.pitch) < 4 ? "implementation" : "checking";
}

/** Where a decision would send it, *Ship, as Fix a bug* (*Website (a new party)* for a party of the library the project lacks); "" when it names none. */
export function whereWords(d) {
  const w = d?.where;
  if (!w?.party) return "";
  return `${w.name || w.party}${w.preset ? " (a new party)" : ""}${w.type_name ? `, as ${w.type_name}` : ""}`;
}

/** A pitch's line in words: *held: Judge now to have it read*, *2 of 4 views*, *Invest: Ship, as Fix a bug*, *sent to Ship: Dark mode*, *passed: …*. `error`: a failed one's `state_error`. */
export function pitchLine(n, error = "", name = null) {
  const p = n.pitch || {}, d = p.decision, views = (p.views || []).length || 4;
  if (n.state === "raw") {
    if (n.held_until) return `waits for limits · after ${hhmm(n.held_until)}`;
    return n.queue === "hold" ? "held: Judge now to have it read" : n.queue === "night" ? "tonight: the views read it then" : "queued: the views read it soon";
  }
  if (n.state === "failed") return `failed: ${error || "try again"}`;
  if (n.state === "judging") {
    const k = answeredOf(p);
    if (k < views) return `${k} of ${views} views`;
    return p.case ? `${p.investor?.name || "Investor"} decides` : `${p.skeptic?.name || "Skeptic"} makes the case against`;
  }
  if (n.state === "judged") return d ? [d.word, whereWords(d)].filter(Boolean).join(": ") : "judged";
  if (n.state === "sent" && n.goal_state && name) return goalStateWords(n.goal_state, name);                 // spec 68 §2.4: its goal, as it is now
  if (n.state === "sent") return p.sent ? `sent to ${p.sent.name || p.sent.party}${p.sent.title ? `: ${p.sent.title}` : ""}` : "sent";
  if (n.state === "passed") return p.passed?.why ? `passed: ${p.passed.why}` : "passed";
  return n.state;
}

const PITCH_RANK = { judged: 0, judging: 1, failed: 2, raw: 3, sent: 4 };

/** What the goals bar's sheet lists for Ideation: its pitches but the passed ones, the judged first, all under Planning (a pitch has no task: nothing of it is at work, waits for main or raises a flag). */
function pitchesOf(model, name) {
  const rows = model.nodes.filter((n) => n.state !== "passed").sort((a, b) => (PITCH_RANK[a.state] ?? 5) - (PITCH_RANK[b.state] ?? 5)).map((n) => ({
    slug: n.slug, title: n.title, short: n.short || n.title, element: n.element || "", raw: n.state === "raw", edges: 0, open: { kind: "idea", slug: n.slug }, type: null,
    line: pitchLine(n, "", name), care: n.state === "judged", mark: n.state === "failed" ? "cross" : n.state === "judged" ? "alert" : n.state === "judging" ? "work" : "",
    markTip: n.state === "failed" ? "failed" : n.state === "judged" ? "waits for you" : n.state === "judging" ? "being judged" : "" }));
  return { atWork: [], planning: rows, waits: [], flags: [], all: rows, asking: rows.filter((r) => r.care).length, n: rows.length };
}
