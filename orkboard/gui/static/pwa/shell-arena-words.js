// The goal's window as data (docs/specs/49-one-window.md §4–§6, §10): from what the Board read (the Map's goals and ideas, the agents, Needs you,
// Review, the gate) the party's members and the tasks in their columns, Planning's items, the stage switch's counts, the ideas at work, the
// stops and the numbers on a member. Pure: no node is made here, so what the window says can be checked without a page.
import { memberWords, stageOf, stageWords, STAGE_WORDS } from "./shell-map-idea.js";
import { rowState } from "./shell-ideas.js";
import { waitsWords } from "./shell-map.js";
import { heldWords, say } from "./shell-words.js";
import { headWords, TIER_WORDS } from "./shell-who.js";
import { minutes } from "./util.js";
import { PHASES, depWords, lowWave, phaseOf } from "./shell-phases.js";
import { doneWords as partyDone } from "./shell-goals-words.js";
import { OPS_VIEW } from "./shell-ops.js";

export const BANDS = [["lead", "Planning"], ["build", "Implementation"], ["check", "Checking"]];
/** A party's bands with its leader's words for the stages (`stages` of the Map's goal; today's words without it). */
export const bandsOf = (stages) => { const w = stageWords(stages); return [["lead", w.planning], ["build", w.implementation], ["check", w.checking]]; };
export const SEATS = { build: 3, check: 2 };                         // the seats a party leaves (decisions §56), the host's `seats` when it says them
const RANK = ["running", "testing", "failed", "picking", "review", "ready", "waiting", "held"];      // nearest the member first (spec 49 §5.4); a task that waits for a pick is a stop like a failure
const RANK_OF = { laborer: 1, warrior: 2, elder: 3 };                // a head's tier → the level's chevrons (marks/rank-N.png)
const HARNESSES = new Set(["claude", "codex", "agy", "cursor", "hermes", "pi", "pipeline"]);   // the marks orkUI draws
const FEW = 3;                                                       // finished before a price is the week's average (idea_spend.TOO_FEW)
const STOPS = ["asks", "plan", "proposal"];                          // the kinds of idea that stop the leader's work
const HINT = "at API prices, not your bill";

export const isOpen = (t) => t.state !== "merged" && t.state !== "dropped";
const live = (t) => t.state === "running" || t.state === "testing";
const usd = (n) => (n < 10 ? n.toFixed(2) : String(Math.round(n)));
const short = (x) => x.short || x.title;
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** *$1–2* from a plan's estimate ("" without one). */
export function planPrice(e) {
  if (!e || e.usd_low == null || e.usd_high == null) return "";
  const f = (x) => (Number(x) < 10 ? String(Math.round(Number(x) * 10) / 10) : String(Math.round(Number(x))));
  return `$${f(e.usd_low)}–${f(e.usd_high)}`;
}

/** What a plan change adds or saves (spec 62 §6.2): *+$0.40–1.20*, *−$0.13–0.38* (a real minus sign; the host sends a saving negative); "" for a change that costs and saves nothing. */
export function changePrice(c) {
  const lo = Number(c?.usd_low), hi = Number(c?.usd_high);
  if (c?.usd_low == null || c?.usd_high == null || !Number.isFinite(lo) || !Number.isFinite(hi) || (lo === 0 && hi === 0)) return "";
  const sign = (x) => (x < 0 ? "−" : "+"), f = (x) => (Math.abs(x) < 10 ? Math.abs(x).toFixed(2) : String(Math.round(Math.abs(x))));
  return sign(lo) === sign(hi) || lo === 0 || hi === 0 ? `${sign(lo || hi)}$${f(lo)}–${f(hi)}` : `${sign(lo)}$${f(lo)}–${sign(hi)}$${f(hi)}`;
}

/** What an answered plan change says, from the host's `{added, changed, dropped, left}` (spec 62 §6.2): *The plan changed: 2 added, 1 dropped.* (the parts that are not zero), *The plan stays as it was.*
 *  when nothing was applied; with tasks it named that had started meanwhile, *1 left as it was: it started.* after it. */
export function changeWords(r) {
  const parts = [[r?.added, "added"], [r?.changed, "changed"], [r?.dropped, "dropped"]].filter(([k]) => k > 0).map(([k, w]) => `${k} ${w}`);
  const left = Array.isArray(r?.left) ? r.left.length : Number(r?.left) || 0;
  return `${parts.length ? `The plan changed: ${parts.join(", ")}.` : "The plan stays as it was."}${left ? ` ${left} left as ${left === 1 ? "it was: it" : "they were: they"} started.` : ""}`;
}

// -- the goals ---------------------------------------------------------------------------------------------------------------

export const nodesOf = (st, slug) => (st.map?.nodes || []).filter((n) => n.goal === slug);

/** What of the goal's Needs you rows is a stop on the bottom row, in the host's order: a task that failed is the Map's (`failedOf`), its
 *  row here would be the same stop twice; a task that left variants to pick from is a stop of kind `pick` (spec 51 §2.4). */
export const needsOf = (st, slug) => (st.board?.needs_you || []).filter((n) => n.goal === slug
  && (["asks", "plan", "change", "proposal", "todo", "goal", "party", "pick"].includes(n.kind) || (n.kind === "failed" && !n.blocks)));

/** The goal's tasks that failed, with their idea. */
export const failedOf = (st, slug) => nodesOf(st, slug).filter((n) => n.state !== "done")
  .flatMap((n) => (n.tasks || []).filter((t) => t.state === "failed").map((t) => ({ node: n, task: t })));

/** The results waiting at Review that are the goal's. */
export function looksOf(st, slug) {
  const mine = new Set(nodesOf(st, slug).map((n) => n.slug));
  return (st.review?.results || []).filter((r) => mine.has(r.idea));
}

export const stopCount = (st, slug) => needsOf(st, slug).length + failedOf(st, slug).length;

/** Whether one of the party's stops is a failure (a task that failed, or a goal that did): the dot in the parties' list is then danger, else alert (spec 54 §2.4). */
export const stopFailed = (st, slug) => failedOf(st, slug).length > 0 || needsOf(st, slug).some((n) => n.kind === "failed");

// -- the hand: every stop of the project, by urgency (spec 54 §2.3) ----------------------------------------------------------
const URGENCY = { failed: 0, op_failed: 0, plan: 1, change: 1, asks: 1, goal: 1, todo: 1, pick: 1, op: 1, proposal: 2, party: 2, op_rules: 2, look: 3 };   // red, what holds work back, what does not, results

/** The stops in the order of their urgency: a failure first, then what holds work back (a plan, a plan change, a question, a to-do, a Pick one, an operation at your check), then what does not
 *  (a proposal, a party's proposal, a template's rules), then the results to look at; in a group the oldest first (`at`, an ISO time; one without comes last). */
export function byUrgency(items) {
  const rank = (it) => URGENCY[it.kind] ?? 1;
  const older = (a, b) => (a && b ? (a < b ? -1 : a > b ? 1 : 0) : a ? -1 : b ? 1 : 0);
  return items.map((it, i) => ({ it, i })).sort((a, b) => rank(a.it) - rank(b.it) || older(a.it.at, b.it.at) || a.i - b.i).map(({ it }) => it);
}

/** Where in the fan the stop of urgency `r` (0 the most urgent) of `n` lies: `fanPlaces(n)[r]`. The most urgent lies in the middle, the next to its right, the next to its left, and so outward. */
export function fanPlaces(n) {
  const mid = Math.floor((n - 1) / 2), out = [];
  for (let k = 0; out.length < n; k++) for (const p of k ? [mid + k, mid - k] : [mid]) if (p >= 0 && p < n) out.push(p);
  return out;
}

/** The goal of the first stop (a Needs you row of a goal in the host's order, else a goal with a task that failed, else one with a result to look at): "" with none. */
export function firstStopGoal(st) {
  const goals = (st.map?.goals || []).map((g) => g.slug);
  const row = (st.board?.needs_you || []).find((n) => goals.includes(n.goal) && needsOf(st, n.goal).includes(n));
  return row?.goal || goals.find((s) => failedOf(st, s).length) || goals.find((s) => looksOf(st, s).length) || "";
}

/** A party as the *where* button's sheet lists it: its leader's head, its names, *k/n done*, its stops, whether it is at work (no %: a party has no end, spec 50 §0). */
export function chipsOf(st) {
  return (st.map?.goals || []).map((g) => {
    const mine = nodesOf(st, g.slug);
    const working = g.state === "reading" || mine.some((n) => ["reading", "planning"].includes(n.state) || (n.tasks || []).some(live));
    return { slug: g.slug, title: g.title, short: short(g), head: g.leader?.head || null, stops: stopCount(st, g.slug), failed: stopFailed(st, g.slug), working, done: partyDone(g) };
  });
}

/** What the top bar's *where* button and its sheet say (spec 50 §6.1): the parties, Operations (when the project has any: what waits there is seen from every party), the one shown
 *  (`shown`: a party's slug, or OPS_VIEW), the stops that wait in it (`here`) and in all the others (`other`: never hidden). */
export function partiesOf(st, kept = "") {
  const list = chipsOf(st);
  const hasOps = st.snap?.ops_rev !== undefined && (!st.ops || (st.ops.templates || []).length || (st.ops.runs || []).length);
  const opsStops = (st.board?.needs_you || []).filter((n) => n.kind.startsWith("op"));
  const ops = hasOps ? { stops: opsStops.length, failed: opsStops.some((n) => n.kind === "op_failed") } : null;
  const inOps = st.view === OPS_VIEW;
  const shown = inOps ? OPS_VIEW : shownGoal(st, kept);
  const here = inOps ? ops?.stops || 0 : list.find((c) => c.slug === shown)?.stops || 0;
  const all = list.reduce((n, c) => n + c.stops, 0) + (ops?.stops || 0);
  return { list, ops, shown, here, other: all - here };
}

// -- a member's two numbers and its marks ---------------------------------------------------------------------------------------

const roleOf = (st, slug) => (st.agents?.roles || []).find((r) => r.role === slug) || null;

/** Its runs and redos, its price for a run, each with the words that say which (spec 49 §5.2): the average once 3 have finished, else
 *  *≈* and its level's price. The leader's are its plans, the checker's its checks. */
export function numbersOf(st, m) {
  const role = m.role;
  const price = (n, avg, of, unit) => ({
    price: n == null ? "—" : `${avg ? "" : "≈"}$${n.toFixed(2)}`,
    priceTip: n == null ? `No ${unit} yet this week` : `${avg ? `The average of its ${plural(of, unit)} this week` : "About: too few runs yet, the price of its level"}, ${HINT}`,
  });
  if (m.band === "lead") {
    const tm = roleOf(st, "taskmaster");
    const w = (role?.week?.plans != null ? role.week : tm?.week) || null;
    const plans = w ? w.plans ?? w.finished ?? 0 : 0, again = w ? Math.max(0, Math.min(plans, (w.finished || 0) - (w.first_time || 0))) : 0;
    const each = w && plans > 0 && w.spent != null ? w.spent / plans : null;
    return { runs: `${plans}/${again}`, runsTip: plans ? `${plural(plans, "plan")} this week, ${again} made again` : "No plan yet this week", ...price(each, plans >= FEW, plans, "plan") };
  }
  if (m.band === "check") {
    const c = role?.check_week, checks = c?.checks || 0, caught = c?.caught || 0, done = role?.week?.finished || 0;
    return { runs: `${checks}/${caught}`, runsTip: checks ? `${plural(checks, "check")} this week, ${caught} caught something` : "No check yet this week",
      ...price(role?.usd_task ?? null, done >= FEW, done, "run") };
  }
  const w = role?.week, done = w?.finished || 0, again = Math.max(0, done - (w?.first_time || 0));
  return { runs: `${done}/${again}`, runsTip: done ? `${plural(done, "run")} this week, ${again} sent back to redo` : "No run yet this week",
    ...price(role?.usd_task ?? null, done >= FEW, done, "run") };
}

/** The sign on a member's head (spec 49 §5.2, orkUI's signs): the cross on the danger ground for a failure, the alert sign on the alert ground for any other stop, the work sign at work, the clock tonight;
 *  none when next or free. */
export function signOf(m) {
  if (m.state === "needs") return m.why === "failed" ? { name: "cross", cls: "danger" } : { name: "alert", cls: "alert" };
  if (m.state === "work") return { name: "work", cls: "" };
  if (m.state === "tonight") return { name: "night", cls: "" };
  return null;
}

/** What a member does, for its line in the solo (spec 49 §5.3): *Takes: code, tests*, *Checks: …*, *Leads: …*, and the words of its first number. */
export function ruleOf(st, m) {
  const lib = (st.roles?.library || []).find((a) => a.id === m.slug);
  const labels = Object.fromEntries((st.roles?.kinds || []).map((k) => [k.kind, k.label.toLowerCase()]));
  if (m.band === "lead") return { kw: "Leads:", rule: (lib?.line || "").replace(/^Leads any (?:party|goal):\s*/i, "") || "reads each goal, drafts it, asks and plans", runsWord: "plans/made again" };
  if (m.band === "check") return { kw: "Checks:", rule: say(lib?.check?.applies) || say(lib?.line) || "the work of every goal", runsWord: "checks/caught" };
  const kinds = (m.role?.kinds || lib?.takes || []).map((k) => labels[k] || k);
  return { kw: "Takes:", rule: kinds.length ? kinds.join(", ") : "any task", runsWord: "runs/sent back" };
}

/** A member's tool and level as marks: {id|n, tip} each (null when not known). */
export function marksOf(m) {
  const id = m.role?.harness?.id;
  const rank = RANK_OF[m.head?.tier];
  return {
    harness: HARNESSES.has(id) ? { id, tip: `Runs on ${m.role.harness.name || id}` } : null,
    rank: rank ? { n: rank, tip: `${TIER_WORDS[m.head.tier]}: its level` } : null,
  };
}

// -- tasks and Planning's items ---------------------------------------------------------------------------------------------------

/** A goal's type as its sign and name (spec 53 §3): {id, name, sign}, or null for a goal with no type. */
export const typeOf = (n) => (n?.type?.sign ? n.type : null);

/** A task's state in words (spec 48 §4): *working 4 min*, *in Review*, *asks you to pick*, *after k1*, the hold's own words, *failed*. */
export function taskWords(t, now = Date.now()) {
  if (live(t)) {
    const s = t.started ? (now - Date.parse(t.started)) / 1000 : NaN;
    return Number.isFinite(s) && s >= 0 ? `${t.state === "testing" ? "testing" : "working"} ${minutes(s)}` : t.state === "testing" ? "testing" : "working";
  }
  if (t.state === "review") return "in Review";
  if (t.state === "picking") return "asks you to pick";
  if (t.state === "ready") return /stop/i.test(t.note || "") ? "stopped by you" : "next";
  if (t.state === "waiting") return (t.after || []).length ? `after ${t.after.join(", ")}` : t.band === "check" ? "after the build" : "waiting";
  if (t.state === "held") return heldWords(t.note, t.waits_title);
  if (t.state === "failed") return "failed";
  return t.state;
}

/** A task as the field draws it: its phase (0 now, 1 next, 2 later: how many waves after its goal's current one), and what it waits for. */
export function taskItem(n, t, now = Date.now(), low = lowWave(n)) {
  const words = taskWords(t, now);
  const phase = phaseOf(t, low), when = PHASES[phase];
  const after = (t.after || []).length ? ` · after ${t.after.join(", ")}` : "";
  return {
    key: `${n.slug}/${t.id}`, idea: n.slug, id: t.id, ideaTitle: short(n), type: typeOf(n), title: short(t), wave: t.wave || 1, phase, phaseWord: when, element: n.element || "", state: t.state,
    words, dep: depWords(n, t),
    tip: t.state === "failed" ? `${t.title} · ${t.error || "failed"}` : t.state === "held" ? `${t.title} · ${words}` : `${t.title} · ${when}${after}`,
    label: `${t.title} (${n.title}${typeOf(n) ? `, ${typeOf(n).name}` : ""}): ${words}${phase ? `, ${when}` : ""}`,
    open: { kind: t.state === "review" ? "result" : t.state === "picking" ? "pick" : "task", slug: n.slug, task: t.id },
  };
}

/** The open tasks of one member in its column's order: the one at work nearest it, then failed, in Review, ready, waiting, held (the same wave: the Board's order). */
export function tasksOf(work, slug, now) {
  const rank = (t) => { const i = RANK.indexOf(t.state); return i < 0 ? RANK.length : i; };
  return work.flatMap((n) => { const low = lowWave(n); return (n.tasks || []).filter((t) => t.by?.slug === slug && isOpen(t)).map((t) => ({ n, t, low })); })
    .sort((a, b) => rank(a.t) - rank(b.t) || (a.t.wave || 1) - (b.t.wave || 1)).map(({ n, t, low }) => taskItem(n, t, now, low));
}

/** Planning's items: the goals in Planning that are not new, the stops first, then the ones the leader is on, then the rest; then the new ones. */
export function planningItems(nodes, lead, titleOf = (slug) => slug) {
  const who = lead?.name || "Taskmaster";
  const rows = nodes.filter((n) => stageOf(n) === "planning" && n.state !== "done");
  const item = (n) => {
    const stop = STOPS.includes(n.needs_you), busy = n.state === "reading" || n.state === "planning", raw = n.state === "raw";
    let words;
    if (n.needs_you === "plan") words = ["plan ready", planPrice(n.plan_estimate || n.estimate)].filter(Boolean).join(" · ");
    else if (n.needs_you === "asks") words = ["asks you", n.asked?.[0]?.by && n.asked[0].by.slug !== lead?.slug ? n.asked[0].by.name : ""].filter(Boolean).join(" · ");
    else if (n.needs_you === "proposal") words = "proposed";
    else if (busy) words = `${who} is ${n.state === "reading" ? "reading" : "planning"}`;
    else if (raw) words = n.queue === "night" || n.waits?.kind === "night" ? "new · tonight" : `new · ${who} reads it later`;
    else { const s = rowState(n, titleOf).text, w = waitsWords(n); words = w && !s.includes(w) ? `${s} · ${w}` : s; }
    const type = typeOf(n), said = type ? `${n.title}, ${type.name}` : n.title;
    return { key: n.slug, idea: n.slug, title: short(n), type, element: n.element || "", raw,
      kind: stop ? "stop" : busy ? "busy" : "quiet", words, tip: `${said} · ${words}`, label: `${said}: ${words}`, open: { kind: n.needs_you === "plan" ? "plan" : "idea", slug: n.slug } };
  };
  const rank = (i) => (i.kind === "stop" ? 0 : i.kind === "busy" ? 1 : 2);
  const made = rows.filter((n) => n.state !== "raw").map(item).sort((a, b) => rank(a) - rank(b));
  return [...made, ...rows.filter((n) => n.state === "raw").map(item)];
}

// -- the party ---------------------------------------------------------------------------------------------------------------------

/** The goal's members: the leader, the builders and the checkers (the party the Map read, joined with the agents), then whoever has tasks
 *  here that is not in the party (a goal with no team runs its tasks as Grunt). */
export function membersOf(st, g, work, now = Date.now()) {
  const base = g.party?.length ? g.party : [...(g.leader ? [{ ...g.leader, band: "lead", state: "free", why: "" }] : []),
    ...(g.team || []).map((m) => ({ slug: m.slug, name: m.name, head: m.head, band: m.checks ? "check" : "build", state: "free", why: "" }))];
  const slugs = new Set(base.map((m) => m.slug));
  const extra = [];
  for (const n of work) {
    for (const t of n.tasks || []) {
      const s = t.by?.slug;
      if (!s || slugs.has(s) || !isOpen(t)) continue;
      slugs.add(s);
      extra.push({ slug: s, name: t.by.name || s, head: t.head, band: t.band === "check" ? "check" : "build", state: "free", why: "", orphan: true });
    }
  }
  const members = [...base, ...extra].map((m) => {
    const tasks = m.band === "lead" ? [] : tasksOf(work, m.slug, now);
    let { state, why } = m;
    if (m.orphan) {
      state = tasks.some((t) => t.state === "failed") ? "needs" : tasks.some((t) => t.state === "running" || t.state === "testing") ? "work"
        : tasks.some((t) => t.state === "held") ? "tonight" : tasks.length ? "next" : "free";
      why = state === "needs" ? "failed" : "";
    }
    const role = roleOf(st, m.slug);
    const full = { ...m, state, why, role, tasks, words: memberWords(state, why) };
    const nums = numbersOf(st, full);
    return { ...full, ...nums, ...ruleOf(st, full), marks: marksOf(full), sign: signOf(full), kit: headWords(m.head) };
  });
  return members;
}

/** The seats a party leaves free in a band (3 builders, 2 checkers). */
export const freeSeats = (st, band, taken, stages = null) => Math.max(0, (stages?.[band]?.seats ?? (st.roles?.seats || SEATS)[band] ?? SEATS[band]) - taken);

// -- the ideas at work, Done, the Now line ------------------------------------------------------------------------------------------

/** *in dev · waits for main*, or *in main* once the gate no longer lists the idea (no gate: the results merge into main itself). */
export function doneWords(gate, slug) {
  if (gate?.same) return "in main";
  return gate && !(gate.ideas || []).some((i) => i.slug === slug) ? "in main" : "in dev · waits for main";
}

// -- the whole window ---------------------------------------------------------------------------------------------------------------

/** The goals picked in a party (the filter, kept per party for the session in `st.picks`): the ones that are still among its open goals. */
export function pickedOf(st, slug) {
  const open = new Set(nodesOf(st, slug).filter((n) => n.state !== "done").map((n) => n.slug));
  return ((st.picks || {})[slug] || []).filter((s) => open.has(s));
}

/** Everything the party's window draws for one party (null while the Map is not read, or the party is gone). */
export function modelOf(st, slug, now = Date.now()) {
  const g = (st.map?.goals || []).find((x) => x.slug === slug);
  if (!g) return null;
  const nodes = nodesOf(st, slug);
  const picks = pickedOf(st, slug);
  const work = nodes.filter((n) => ["implementation", "checking"].includes(stageOf(n)));
  const members = membersOf(st, g, work, now);
  const lead = members.find((m) => m.band === "lead") || null;
  const build = members.filter((m) => m.band === "build"), check = members.filter((m) => m.band === "check");
  const titles = new Map((st.map?.nodes || []).map((n) => [n.slug, n.title]));
  const planning = planningItems(nodes, lead, (slug) => titles.get(slug) || slug);
  if (lead) lead.tasks = planning;
  const raw = nodes.filter((n) => n.state === "raw" && stageOf(n) === "planning");
  const next = raw.find((n) => n.queue !== "now" && !n.held_until) || null;
  const sum = (ms) => ms.reduce((k, m) => k + m.tasks.length, 0);
  const failed = (ms) => ms.reduce((k, m) => k + m.tasks.filter((t) => t.state === "failed").length, 0);
  const counts = { lead: planning.length, build: sum(build), check: sum(check) };
  const warn = { lead: planning.filter((i) => i.kind === "stop").length, build: failed(build), check: failed(check) };
  const done = nodes.filter((n) => n.state === "done");
  // A stop's band (spec 52 §5.3): a member's question is its band's, a pick its maker's, a plan, a proposal and the leader's questions Planning's.
  const bandOf = new Map(members.map((x) => [x.slug, x.band]));
  const waits = { lead: 0, build: 0, check: 0 }, waiting = new Map();   // the stops of a band, and of each member (spec 53 §1.2: the sign stands on the face it comes from)
  for (const it of planning.filter((i) => i.kind === "stop")) {
    const n = nodes.find((x) => x.slug === it.idea), by = n?.needs_you === "asks" ? n.asked?.[0]?.by?.slug : "", band = bandOf.get(by);
    const who = band === "build" || band === "check" ? by : lead?.slug;
    waits[band === "build" || band === "check" ? band : "lead"] += 1;
    waiting.set(who, (waiting.get(who) || 0) + 1);
  }
  for (const x of [...build, ...check]) { const k = x.tasks.filter((t) => t.state === "picking").length; waits[x.band] += k; if (k) waiting.set(x.slug, (waiting.get(x.slug) || 0) + k); }
  const signs = new Map([...build, ...check].map((x) => [x.slug, x.tasks.some((t) => t.state === "failed") ? "cross" : waiting.get(x.slug) ? "alert" : ""]));
  if (lead) signs.set(lead.slug, waiting.get(lead.slug) ? "alert" : "");
  const bands = bandsOf(g.stages);
  const faces = { lead: facesOf("lead", lead ? [lead] : [], 0, waits.lead, signs, bands), build: facesOf("build", build, warn.build, waits.build, signs, bands),
    check: facesOf("check", check, warn.check, waits.check, signs, bands) };
  return {
    goal: g, bands, nodes, work, members, lead, build, check, planning, counts, warn, faces,
    first: counts.build ? "build" : counts.check ? "check" : "lead",
    freeBuild: freeSeats(st, "build", build.length, g.stages), freeCheck: freeSeats(st, "check", check.length, g.stages),
    picks, done,
    process: { next, n: raw.filter((n) => n.queue !== "now" && !n.held_until).length, lead },
  };
}

const FACES = { lead: 1, build: 4, check: 3 };                    // the heads a stage's tab shows at most (a Game's four builders, spec 59 §7.3)
const NO_ONE = { lead: "no leader", build: "no builder", check: "no checker" };

/** A stage's tab (spec 52 §5.3, spec 53 §1.2): its band's faces (at most FACES), each {head, slug, name, sign} — the sign (`cross` when a task of the member failed, else `alert`
 *  when a stop waits on it, else none) stands on the face it comes from (`signs`: slug → sign) — the band's own `sign` (for the tab's data), and its label, *Implementation: Grunt, Tester. 1 failed*, *Planning: the Taskmaster. 2 wait for you*, *Checking: no checker*. No number is drawn. */
export function facesOf(key, members, failed, waits, signs = new Map(), bands = BANDS) {
  const word = bands.find(([k]) => k === key)[1];
  const names = members.map((x) => (x.slug === "taskmaster" ? "the Taskmaster" : x.name));
  const said = [failed ? `${failed} failed` : "", waits ? `${waits} ${waits === 1 ? "waits" : "wait"} for you` : ""].filter(Boolean).join(", ");
  return { heads: members.slice(0, FACES[key]).map((x) => ({ head: x.head || null, slug: x.slug, name: x.name, lead: x.band === "lead", sign: signs.get(x.slug) || "" })), sign: failed ? "cross" : waits ? "alert" : "", failed, waits,
    label: `${word}: ${names.length ? names.join(", ") : NO_ONE[key]}.${said ? ` ${said}` : ""}`.replace(/\.$/, "") };
}

/** The goal to show: the one this phone shows (`st.track`) when the Map has it, else the first. */
export function shownGoal(st, kept = "") {
  const goals = st.map?.goals || [];
  return (goals.find((g) => g.slug === st.track) || goals.find((g) => g.slug === kept) || goals[0])?.slug || "";
}
