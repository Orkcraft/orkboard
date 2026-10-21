// The goal's window as data (docs/specs/49-one-window.md §4–§6, §10): from what the Board read (the Map's goals and ideas, the agents, Needs you,
// Review, the gate) the party's members and the tasks in their columns, Planning's items, the stage switch's counts, the ideas at work, the
// stops and the numbers on a member. Pure: no node is made here, so what the window says can be checked without a page.
import { memberWords, stageOf, STAGE_WORDS } from "./shell-map-idea.js";
import { rowState } from "./shell-ideas.js";
import { progressOf, waitsWords } from "./shell-map.js";
import { heldWords } from "./shell-words.js";
import { headWords, TIER_WORDS } from "./shell-who.js";
import { minutes } from "./util.js";

export const BANDS = [["lead", "Planning"], ["build", "Implementation"], ["check", "Checking"]];
export const SEATS = { build: 3, check: 2 };                         // the seats a party leaves (decisions §56), the host's `seats` when it says them
const RANK = ["running", "testing", "failed", "review", "ready", "waiting", "held"];      // nearest the member first (spec 49 §5.4)
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

// -- the goals ---------------------------------------------------------------------------------------------------------------

export const nodesOf = (st, slug) => (st.map?.nodes || []).filter((n) => n.goal === slug);

/** What of the goal's Needs you rows is a stop on the bottom row, in the host's order: a task that failed is the Map's (`failedOf`), its
 *  row here would be the same stop twice. */
export const needsOf = (st, slug) => (st.board?.needs_you || []).filter((n) => n.goal === slug
  && (["asks", "plan", "proposal", "todo", "goal", "party"].includes(n.kind) || (n.kind === "failed" && !n.blocks)));

/** The goal's tasks that failed, with their idea. */
export const failedOf = (st, slug) => nodesOf(st, slug).filter((n) => n.state !== "done")
  .flatMap((n) => (n.tasks || []).filter((t) => t.state === "failed").map((t) => ({ node: n, task: t })));

/** The results waiting at Review that are the goal's. */
export function looksOf(st, slug) {
  const mine = new Set(nodesOf(st, slug).map((n) => n.slug));
  return (st.review?.results || []).filter((r) => mine.has(r.idea));
}

export const stopCount = (st, slug) => needsOf(st, slug).length + failedOf(st, slug).length;

/** The goal of the first stop (a Needs you row of a goal in the host's order, else a goal with a task that failed, else one with a result to look at): "" with none. */
export function firstStopGoal(st) {
  const goals = (st.map?.goals || []).map((g) => g.slug);
  const row = (st.board?.needs_you || []).find((n) => goals.includes(n.goal) && needsOf(st, n.goal).includes(n));
  return row?.goal || goals.find((s) => failedOf(st, s).length) || goals.find((s) => looksOf(st, s).length) || "";
}

/** A chip per goal: its short title, how far it is, its stops, whether its party is at work. */
export function chipsOf(st) {
  return (st.map?.goals || []).map((g) => {
    const mine = nodesOf(st, g.slug);
    const working = g.state === "reading" || mine.some((n) => ["reading", "planning"].includes(n.state) || (n.tasks || []).some(live));
    return { slug: g.slug, title: g.title, short: short(g), pct: progressOf(mine), stops: stopCount(st, g.slug), working };
  });
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

/** The sign on a member's head (spec 49 §5.2): ✗ on the danger ground for a failure, ! on the alert ground for any other stop, ↻ at work, the moon tonight; none when next or free. */
export function signOf(m) {
  if (m.state === "needs") return m.why === "failed" ? { text: "✗", cls: "danger" } : { text: "!", cls: "alert" };
  if (m.state === "work") return { text: "↻", cls: "" };
  if (m.state === "tonight") return { text: "moon", cls: "" };
  return null;
}

/** What a member does, for its line in the solo (spec 49 §5.3): *Takes: code, tests*, *Checks: …*, *Leads: …*, and the words of its first number. */
export function ruleOf(st, m) {
  const lib = (st.roles?.library || []).find((a) => a.id === m.slug);
  const labels = Object.fromEntries((st.roles?.kinds || []).map((k) => [k.kind, k.label.toLowerCase()]));
  if (m.band === "lead") return { kw: "Leads:", rule: (lib?.line || "").replace(/^Leads any goal:\s*/i, "") || "reads the goal, drafts its ideas, asks and plans", runsWord: "plans/made again" };
  if (m.band === "check") return { kw: "Checks:", rule: lib?.check?.applies || lib?.line || "the work of every idea", runsWord: "checks/caught" };
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

/** A task's state in words (spec 48 §4): *working 4 min*, *in Review*, *after k1*, the hold's own words, *failed*. */
export function taskWords(t, now = Date.now()) {
  if (live(t)) {
    const s = t.started ? (now - Date.parse(t.started)) / 1000 : NaN;
    return Number.isFinite(s) && s >= 0 ? `${t.state === "testing" ? "testing" : "working"} ${minutes(s)}` : t.state === "testing" ? "testing" : "working";
  }
  if (t.state === "review") return "in Review";
  if (t.state === "ready") return /stop/i.test(t.note || "") ? "stopped by you" : "next";
  if (t.state === "waiting") return (t.after || []).length ? `after ${t.after.join(", ")}` : t.band === "check" ? "after the build" : "waiting";
  if (t.state === "held") return heldWords(t.note, t.waits_title);
  if (t.state === "failed") return "failed";
  return t.state;
}

/** A task as the column draws it. */
export function taskItem(n, t, now = Date.now()) {
  const words = taskWords(t, now);
  const mark = live(t) ? "↻" : t.state === "failed" ? "✗" : t.state === "held" ? "clock" : "";
  const after = (t.after || []).length ? ` · after ${t.after.join(", ")}` : "";
  return {
    key: `${n.slug}/${t.id}`, idea: n.slug, id: t.id, ideaTitle: short(n), title: short(t), wave: t.wave || 1, state: t.state, mark, words,
    tip: t.state === "failed" ? `${t.title} · ${t.error || "failed"}` : t.state === "held" ? `${t.title} · ${words}` : `${t.title} · wave ${t.wave || 1}${after}`,
    label: `${t.title} (${n.title}): ${words}, wave ${t.wave || 1}`,
    open: { kind: t.state === "review" ? "result" : "task", slug: n.slug, task: t.id },
  };
}

/** The open tasks of one member in its column's order: the one at work nearest it, then failed, in Review, ready, waiting, held. */
export function tasksOf(work, slug, now) {
  const rank = (t) => { const i = RANK.indexOf(t.state); return i < 0 ? RANK.length : i; };
  return work.flatMap((n) => (n.tasks || []).filter((t) => t.by?.slug === slug && isOpen(t)).map((t) => ({ n, t })))
    .sort((a, b) => rank(a.t) - rank(b.t) || (a.t.wave || 1) - (b.t.wave || 1)).map(({ n, t }) => taskItem(n, t, now));
}

/** Planning's items: the ideas in Planning that are not new, the stops first, then the ones the leader is on, then the rest; then the new ones. */
export function planningItems(nodes, lead, titleOf = (slug) => slug) {
  const who = lead?.name || "Taskmaster";
  const rows = nodes.filter((n) => stageOf(n) === "planning" && n.state !== "done");
  const item = (n) => {
    const stop = STOPS.includes(n.needs_you), busy = n.state === "reading" || n.state === "planning", raw = n.state === "raw";
    let words;
    if (n.needs_you === "plan") words = ["plan ready", planPrice(n.plan_estimate || n.estimate)].filter(Boolean).join(" · ");
    else if (n.needs_you === "asks") words = ["asks you", n.asked?.[0]?.by && n.asked[0].by.slug !== lead?.slug ? n.asked[0].by.name : ""].filter(Boolean).join(" · ");
    else if (n.needs_you === "proposal") words = "proposed";
    else if (busy) words = `${who} is ${n.state === "reading" ? "reading" : "planning"} ↻`;
    else if (raw) words = n.queue === "night" || n.waits?.kind === "night" ? "new · tonight" : `new · ${who} reads it later`;
    else { const s = rowState(n, titleOf).text, w = waitsWords(n); words = w && !s.includes(w) ? `${s} · ${w}` : s; }
    return { key: n.slug, idea: n.slug, title: short(n), badge: stop ? "!" : busy ? "↻" : "·", kind: stop ? "stop" : busy ? "busy" : "quiet", words,
      tip: `${n.title} · ${words}`, label: `${n.title}: ${words}`, open: { kind: n.needs_you === "plan" ? "plan" : "idea", slug: n.slug } };
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
export const freeSeats = (st, band, taken) => Math.max(0, ((st.roles?.seats || SEATS)[band] ?? SEATS[band]) - taken);

// -- the ideas at work, Done, the Now line ------------------------------------------------------------------------------------------

/** An idea at work as a row of the ideas bar: its pips, its stage track, its note. */
export function ideaRow(n, party) {
  const tasks = (n.tasks || []).filter((t) => t.state !== "dropped");
  const stage = stageOf(n), at = BANDS.findIndex(([, w]) => w === STAGE_WORDS[stage]);
  const who = (t) => t.by?.name || party.find((m) => m.slug === t.by?.slug)?.name || "Grunt";
  const failed = tasks.filter((t) => t.state === "failed"), running = tasks.filter(live), held = tasks.filter((t) => t.state === "held");
  const looks = (n.results || []).length;
  const next = tasks.find((t) => t.state === "ready" || t.state === "waiting");
  let note = "", bad = false;
  if (failed.length) { note = `✗ ${short(failed[0])} failed`; bad = true; }
  else if (running.length) note = running.map((t) => `${who(t)} ↻ ${short(t)}`).join(" · ");
  else if (held.length) note = `tonight: ${short(held[0])}`;
  else if (looks) note = `${plural(looks, "result waits", "results wait")} for your look`;
  else note = `Nothing waits for your look. Next: ${STAGE_WORDS[stage]}${next ? ` by ${who(next)}` : ""}`;
  const track = BANDS.map(([, name], i) => ({ name: `${i < at ? "✓ " : ""}${name}`, state: i < at ? "past" : i === at ? "now" : "" }));
  return { slug: n.slug, title: n.title, stage, round: n.round || 1, track, bad, note,
    pips: tasks.map((t) => (t.state === "merged" ? "d" : live(t) ? "w" : t.state === "failed" ? "f" : "")),
    label: `${n.title}: ${STAGE_WORDS[stage]}${n.round > 1 ? `, round ${n.round}` : ""}, ${note}` };
}

/** *in dev · waits for main*, or *in main* once the gate no longer lists the idea (no gate: the results merge into main itself). */
export function doneWords(gate, slug) {
  if (gate?.same) return "in main";
  return gate && !(gate.ideas || []).some((i) => i.slug === slug) ? "in main" : "in dev · waits for main";
}

/** *Now:* who ↻ which task (which idea) for every running task, the leader reading; *nothing at work right now*. */
export function nowLine(work, nodes, lead) {
  const bits = [];
  for (const n of work) for (const t of (n.tasks || []).filter(live)) bits.push(`${t.by?.name || "Grunt"} ↻ ${short(t)} (${short(n)})`);
  const reading = nodes.find((n) => n.state === "reading" || n.state === "planning");
  if (reading) bits.push(`${lead?.name || "Taskmaster"} ↻ ${reading.state === "reading" ? "reading" : "planning"} “${short(reading)}”`);
  return bits.length ? bits.join(" · ") : "nothing at work right now";
}

// -- the whole window ---------------------------------------------------------------------------------------------------------------

/** Everything the goal's window draws for one goal (null while the Map is not read, or the goal is gone). */
export function modelOf(st, slug, now = Date.now()) {
  const g = (st.map?.goals || []).find((x) => x.slug === slug);
  if (!g) return null;
  const nodes = nodesOf(st, slug);
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
  const left = Math.max(0, (g.ideas ?? nodes.length) - (g.done ?? done.length));
  return {
    goal: g, nodes, work, members, lead, build, check, planning, counts, warn,
    first: counts.build ? "build" : counts.check ? "check" : "lead",
    freeBuild: freeSeats(st, "build", build.length), freeCheck: freeSeats(st, "check", check.length),
    pct: progressOf(nodes), left, ideas: work.map((n) => ideaRow(n, members)), done,
    process: { next, n: raw.filter((n) => n.queue !== "now" && !n.held_until).length, lead },
    now: nowLine(work, nodes, lead),
  };
}

/** The goal to show: the one this phone shows (`st.track`) when the Map has it, else the first. */
export function shownGoal(st, kept = "") {
  const goals = st.map?.goals || [];
  return (goals.find((g) => g.slug === st.track) || goals.find((g) => g.slug === kept) || goals[0])?.slug || "";
}
