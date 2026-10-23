// The one window's words and lists (docs/specs/49-one-window.md): pure functions over `ideas.map`, `ideas.board`, `ideas.agents`,
// `ideas.gate`, `ideas.today` and the snapshot. No signal and no template here; the parts of the window (arena.js and its
// neighbours) draw what these say. The backend writes no words: the member's state, a task's foot and a stop's text are said here.
import { leftToDo, TASK_STATE } from "../board/maplayout.js";
import { memberWords, soFarWords, todayWords } from "../board/mapstage.js";
import { holdWords, hhmm, OPS } from "../board/store.js";
import { TIER_WORDS, RACE_WORDS } from "../orkui.js";
import { kindCount } from "./pickwords.js";
import { pctOf, pctRange, pctDelta, rated, SHARE_TIP } from "../spend.js";

export const RUN = ["running", "testing"];
export const RANK = { running: 0, testing: 0, failed: 1, picking: 1.5, review: 2, ready: 3, waiting: 4, held: 5 };      // a column, from the member up (§5.4); a pick waits for the person, after a failure (spec 51)
const LEVEL = { laborer: 1, warrior: 2, elder: 3 };      // the level's chevrons (marks/rank-1 … 3)

export const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** *Mon 09:00* from a local `YYYY-MM-DDTHH:MM`; "" when it does not read. */
export function dayAt(iso) {
  const d = new Date(iso);
  return !iso || Number.isNaN(d.getTime()) ? "" : `${d.toLocaleDateString("en-US", { weekday: "short" })} ${hhmm(iso)}`;
}

const after = (until) => (until ? ` · after ${hhmm(until)}` : "");

/** Why a goal that is not done does not move, in words; "" for what its mark says (spec 39 §4.3, spec 42 G). */
export function waitsWords(w) {
  if (!w) return "";
  const who = w.title || w.ref || "another goal";
  return { idea: `waits for ${who}`, files: `same files as ${who}`, limits: `waits for limits${after(w.until)}`, reserve: `keeps your reserve${after(w.until)}`,
    night: "tonight", stopped: "stopped", week: `waits: the week is behind${w.until ? ` · until ${dayAt(w.until)}` : ""}` }[w.kind] || "";
}

/** *tonight*, or the Board's own night work: *tonight, or sooner if the week has room* (spec 44 §2); `starts` for a plan that starts tonight. */
export const tonightWords = (n, starts = false) => `${starts ? "starts " : ""}tonight${n.night_by === "board" ? ", or sooner if the week has room" : ""}`;
export const money = (n) => pctOf(n) || `$${n < 10 ? Number(n).toFixed(2) : Math.round(n)}`;
const round2 = (n) => Math.round(n * 100) / 100;
/** *$1–2*: a plan's price, from `plan_estimate`; "" with none. */
export const rangeWords = (e) => (e ? pctRange(e.usd_low, e.usd_high) || `$${round2(e.usd_low)}–${round2(e.usd_high)}` : "");

/** Minutes since a local ISO time, as *4 min*; "" when it is not read or is in the future. */
export function sinceWords(iso, now = Date.now()) {
  const t = iso ? new Date(iso).getTime() : NaN;
  if (Number.isNaN(t) || t > now) return "";
  const m = Math.floor((now - t) / 60000);
  return m < 1 ? "just now" : m < 120 ? `${m} min` : `${Math.floor(m / 60)} h`;
}

// -- the goals ---------------------------------------------------------------------------------------------------------------

/** The map's goals in the Board's order (`order`: the Board's goal slugs, by priority); a goal the Board does not list goes last. */
export function goalsOf(map, order = []) {
  const goals = map?.goals || [], at = (g) => (order.includes(g.slug) ? order.indexOf(g.slug) : order.length);
  return [...goals].sort((a, b) => at(a) - at(b));
}

export const nodesOf = (map, slug) => (map?.nodes || []).filter((n) => n.goal === slug);
/** A goal at work: past its plan, not done (spec 50 §3.3). */
export const atWork = (n) => n.stage === "implementation" || n.stage === "checking";
export const openTasks = (n) => (n.tasks || []).filter(leftToDo);

/** *k/n*: a party's done goals of all its goals (decisions §63.2); its tooltip says it (*k of n goals done*). */
export const countOf = (g, nodes = []) => ({ done: g.done ?? nodes.filter((n) => n.state === "done").length, all: g.ideas ?? nodes.length });
export const countWords = (g, nodes) => { const c = countOf(g, nodes); return `${c.done}/${c.all}`; };
export const countTip = (g, nodes) => { const c = countOf(g, nodes); return `${c.done} of ${c.all} goals done`; };
export const costWords = (g) => [soFarWords(g.usd), todayWords(g.today)].filter(Boolean).join(" · ");

// -- the stops: what waits for the person ----------------------------------------------------------------------------------------

const STOP_KINDS = ["asks", "plan", "proposal"];                 // the stops of Planning (§4.3)
/** The party's Planning: the goals in stage planning that are not raw, the stops first; the raw ones apart (*New (n)*). Its `mark` is a sign's name. */
export function planningOf(g, nodes, leader) {
  const lead = leader || g.leader?.name || "Taskmaster";
  const asks = (n) => n.asked?.[0]?.by?.name;
  const words = (n) => {
    if (n.needs_you === "plan") return "plan ready";
    if (n.needs_you === "asks") return `asks you · ${asks(n) || lead}`;
    if (n.needs_you === "proposal") return "proposed";
    if (n.state === "reading") return `${lead} is reading`;
    if (n.state === "planning") return `${lead} is planning`;
    if (n.waits?.kind === "week") return waitsWords(n.waits);
    if (n.state === "plan" && n.start_at === "night") return tonightWords(n, true);
    if (n.state === "ready") return `ready · ${lead} plans it next`;
    return n.state;
  };
  const row = (n) => {
    const stop = STOP_KINDS.includes(n.needs_you), busy = n.state === "reading" || n.state === "planning";
    return { slug: n.slug, title: n.short || n.title, full: n.title, stop, busy, mark: stop ? "alert" : busy ? "work" : "", words: words(n),
      cost: n.needs_you === "plan" ? rangeWords(n.plan_estimate || n.estimate) : "", kind: n.needs_you === "plan" ? "plan" : "idea", node: n };
  };
  const mine = nodes.filter((n) => n.stage === "planning");
  const rows = mine.filter((n) => n.state !== "raw").map(row);
  const raw = mine.filter((n) => n.state === "raw").map((n) => ({ slug: n.slug, title: n.short || n.title, full: n.title, node: n, kind: "idea", stop: false, busy: false,
    mark: "", cost: "", words: n.waits?.kind === "week" ? waitsWords(n.waits) : n.queue === "hold" ? "stopped" : n.queue === "night" ? tonightWords(n) : `new · ${lead} reads it later` }));
  return { rows: [...rows.filter((r) => r.stop), ...rows.filter((r) => !r.stop)], raw };
}

/** *Process now · 2 new goals* / *no new goal*, the goal it reads and its tooltip (spec 49 §4.4). */
export function powerOf(raw, lead) {
  const first = raw[0];
  return { slug: first?.slug || "", off: !first, words: first ? plural(raw.length, "new goal", "new goals") : "no new goal",
    tip: first ? `${lead} reads “${first.full}” now` : "No new goal to read" };
}

// -- the party -----------------------------------------------------------------------------------------------------------------------

/** The party row (§5.1): the goal's builders, then its checkers (agents outside the party that hold a task among them); the leader apart.
 *  The seats a party leaves are not drawn: the party is changed from Edit the party in the ideas bar. [{slug, name, head, band, state, why}]. */
export function partyOf(g, nodes) {
  const party = g.party || [];
  const lead = party.find((m) => m.band === "lead") || (g.leader ? { ...g.leader, band: "lead", state: "free", why: "" } : null);
  const team = party.filter((m) => m.band !== "lead").map((m) => ({ ...m }));
  const known = new Set([lead?.slug, ...team.map((m) => m.slug)]);
  for (const n of nodes.filter(atWork)) {
    for (const t of openTasks(n)) {
      if (known.has(t.by.slug)) continue;
      known.add(t.by.slug);
      const mine = nodes.filter(atWork).flatMap((x) => openTasks(x).filter((y) => y.by.slug === t.by.slug));
      const failed = mine.some((y) => y.state === "failed"), pick = mine.some((y) => y.state === "picking"), run = mine.some((y) => RUN.includes(y.state));
      team.push({ slug: t.by.slug, name: t.by.name, head: t.head, band: t.band === "check" ? "check" : "build",
        state: failed || pick ? "needs" : run ? "work" : "next", why: failed ? "failed" : pick ? "pick" : "" });
    }
  }
  return { lead, members: [...team.filter((m) => m.band === "build"), ...team.filter((m) => m.band === "check")] };
}

export const BAND_WORDS = { lead: "Leads", build: "Builds", check: "Checks" };
export const BAND_KEYWORD = { lead: "Leads:", build: "Takes:", check: "Checks:" };
/** A party's stage in a band (`g.stages`, spec 59 §3): its word (*Concept*, *Build*, *Playtest* with a Game designer) and its seats. A party with no `stages`
 *  (an older host) says today's words and no seats. */
const STAGE_TODAY = { lead: "Planning", build: "Implementation", check: "Checking" };
export const stageOf = (g, band) => ({ word: g?.stages?.[band]?.word || STAGE_TODAY[band], seats: g?.stages?.[band]?.seats || 0, own: !!g?.stages?.[band]?.word });

/** A task's phase: its wave less the lowest wave among the open tasks of its goal (spec 50 §3.4): 0 now, 1 next, 2 and over later. */
export function phaseOf(n, t) {
  const open = openTasks(n);
  return Math.max(0, t.wave - Math.min(t.wave, ...open.map((x) => x.wave)));
}
export const ROWS = ["now", "next", "later"];
export const rowName = (phase) => ROWS[Math.min(phase, ROWS.length - 1)];

/** A member's open tasks of the goals at work, in its column's order: the one at work nearest it, then failed, in Review, ready, waiting, held (the
 *  front of a stack first); each with its phase and the row it lies in (*now*, *next*, *later*). `order`: the Board's order of the goals is `nodes`'. */
export function columnOf(m, nodes) {
  const items = [];
  nodes.filter(atWork).forEach((n, i) => openTasks(n).forEach((t, j) => {
    if (t.by.slug === m.slug) { const phase = phaseOf(n, t); items.push({ n, t, at: i * 1000 + j, phase, row: rowName(phase) }); }
  }));
  return items.sort((a, b) => (RANK[a.t.state] ?? 9) - (RANK[b.t.state] ?? 9) || a.t.wave - b.t.wave || a.at - b.at);
}
/** The merged tasks of a member, over all the party's goals (*✓ k in dev*). */
export const mergedBy = (m, nodes) => nodes.reduce((k, n) => k + (n.tasks || []).filter((t) => t.state === "merged" && t.by.slug === m.slug).length, 0);

/** A column's items as its rows by phase, each row its stacks: one per goal (in the Board's order, `nodes`'), the front card first.
 *  `list`: items as the column shows them ([{it: {n, t, row}, …}]); [{row, stacks: [{goal, items: [...]}]}], a row with nothing not there. */
export function rowsOf(list, nodes) {
  const place = (slug) => { const i = nodes.findIndex((n) => n.slug === slug); return i < 0 ? nodes.length : i; };
  return ROWS.map((row) => {
    const here = list.filter((x) => x.it.row === row), goals = [...new Set(here.map((x) => x.it.n.slug))].sort((a, b) => place(a) - place(b));
    return { row, stacks: goals.map((goal) => ({ goal, items: here.filter((x) => x.it.n.slug === goal) })) };
  }).filter((r) => r.stacks.length);
}

/** The role of ideas.agents behind a party member. */
export const roleOf = (agents, slug) => (agents?.roles || []).find((r) => r.role === slug) || null;

const modelOf = (roles, role) => {
  const id = role?.model || "", label = (roles?.models || []).find((x) => x.id === id)?.label || "";
  const named = /\(([^)]+)\)/.exec(label);
  return named ? named[1] : TIER_WORDS[id] ? "" : id;
};

/** A member's two numbers, its price, its marks and the words that say them (§5.2). `lead`: the leader (plans, not runs). */
export function statsOf(m, role, lead = false) {
  const w = role?.week || null, cw = role?.check_week || null;
  const finished = w?.finished || 0, again = Math.max(0, finished - (w?.first_time || 0));
  let n, redo, word, tip, avg, price, priceTip;
  const API = rated() ? SHARE_TIP.replace(/^An/, "an") : "at API prices, not your bill";
  if (lead) {
    n = w?.plans ?? finished; redo = again; word = "plans/made again";
    tip = `${plural(n, "plan", "plans")} this week, ${redo} made again`;
    const plans = w?.plans || 0;
    avg = plans >= 3;
    price = plans > 0 && w?.spent != null ? `${avg ? "" : "≈"}${money(w.spent / plans)}` : "—";
    priceTip = plans > 0 && w?.spent != null ? `${avg ? `The average of its ${plans} plans this week` : "About: too few plans yet"}, ${API}` : "No plan priced yet this week";
  } else {
    if (m.band === "check" && cw) { n = cw.checks; redo = cw.caught; word = "checks/caught"; tip = `${plural(n, "check", "checks")} this week, ${redo} caught something`; }
    else { n = finished; redo = again; word = "runs/sent back"; tip = `${plural(n, "run", "runs")} this week, ${redo} sent back to redo`; }
    avg = finished >= 3;
    price = role?.usd_task == null ? "—" : `${avg ? "" : "≈"}${money(role.usd_task)}`;
    priceTip = role?.usd_task == null ? "No price yet" : `${avg ? `The average of its ${finished} runs this week` : "About: too few runs yet, the price of its level"}, ${API}`;
  }
  const tier = m.head?.tier || role?.head?.tier || "laborer", harness = role?.harness || { id: "claude", name: "Claude" };
  return { runs: `${n || 0}/${redo || 0}`, runsWord: word, runsTip: tip, price, priceTip, avg, harness, tier, rank: LEVEL[tier] || 1,
    rankTip: `${TIER_WORDS[tier] || ""}: its level`, harnessTip: `Runs on ${harness.name}`, level: TIER_WORDS[tier] || "" };
}

/** What a member does now, and after (spec 49 §5.2): *<work> Challenge store · 4 min*, *<cross> <task>*, *next: <task>*, *n in Review*. Each line is
 *  {sign, text}: the sign's name (work, cross) or "", and the words beside it. */
export function nowOf(m, col, planning, isLead) {
  const line = (text, sign = "") => ({ sign, text });
  if (isLead) {
    const stops = planning.rows.filter((r) => r.stop), busy = planning.rows.find((r) => r.busy);
    const ready = [...planning.rows, ...planning.raw].find((r) => r.node.state === "ready" || r.node.state === "raw");
    const now = busy ? line(`reading “${busy.title}”`, "work") : ready ? line(`next: plans “${ready.title}”`) : stops.length ? line(`${stops[0].words}: “${stops[0].title}”`) : line("");
    const next = stops.length > 1 ? line(`${stops.length} wait for you`) : stops.length === 1 && busy ? line(`${stops[0].words}: “${stops[0].title}”`) : line("");
    return { now, next };
  }
  const run = col.filter((x) => RUN.includes(x.t.state)), failed = col.find((x) => x.t.state === "failed"), held = col.find((x) => x.t.state === "held");
  const picking = col.find((x) => x.t.state === "picking");
  const nx = col.find((x) => x.t.state === "ready" || x.t.state === "waiting"), rv = col.filter((x) => x.t.state === "review").length;
  const name = (x) => x.t.short || x.t.title, min = (x) => sinceWords(x.t.started);
  const now = run.length ? line(`${name(run[0])}${min(run[0]) ? ` · ${min(run[0])}` : ""}`, "work") : failed ? line(name(failed), "cross") : picking ? line(`asks you to pick: ${name(picking)}`, "alert")
    : nx ? line(`next: ${name(nx)}`) : rv ? line(`${rv} in Review`) : line("");
  const next = failed && run.length ? line(name(failed), "cross") : picking && run.length ? line(`asks you to pick: ${name(picking)}`, "alert") : held ? line(`tonight: ${name(held)}`) : rv && run.length ? line(`${rv} in Review`)
    : nx && run.length ? line(`next: ${name(nx)}`) : line("");
  return { now, next };
}

/** A member's state in words, its colour class and what a screen reader hears. */
export function memberView(m, stats, line, race) {
  const words = memberWords(m) || "free";
  const tone = m.state === "needs" ? "is-needs" : m.state === "work" ? "" : "is-quiet";
  const label = [m.name, `${race ? `${race}, ` : ""}${stats.harness.name}, ${stats.level}`, words, stats.runsTip,
    `${stats.price === "—" ? "no price yet" : `${stats.price} a run`}`, line.now.text].filter(Boolean).join(", ");
  return { words, tone, label: `${label}. A click shows its work.` };
}

/** The sign on a member's head (spec 49 §5.2, orkUI's signs): cross on the danger ground for a failure, alert on the alert ground for another stop, work while at
 *  work, night (the clock) tonight; null when next or free. `mark` is the sign's name. */
export function signOf(m) {
  if (m.state === "needs") return m.why === "failed" ? { mark: "cross", tone: "danger" } : { mark: "alert", tone: "alert" };
  if (m.state === "work") return { mark: "work", tone: "" };
  if (m.state === "tonight") return { mark: "night", tone: "" };
  return null;
}

export const raceOf = (head) => (head ? RACE_WORDS[head.race] || "" : "");

// -- the columns -------------------------------------------------------------------------------------------------------------------

/** A check that waits for the whole build says so: *after the build* (every build task of its goal is among those it follows). */
function followsBuild(t, n) {
  const builds = (n?.tasks || []).filter((x) => x.band !== "check");
  return t.band === "check" && builds.length > 0 && builds.every((b) => (t.after || []).includes(b.id));
}
/** What a task follows, in a few words: *after k1, k2*, or *after the build* for a check that waits for all of it. */
export const afterWords = (t, n) => (followsBuild(t, n) ? "after the build" : `after ${t.after.join(", ")}`);

/** A task's foot: its state in words (*working 4 min*, *in Review*, *after k1*, *tonight · after 01:00*, *failed*). */
export function taskFoot(t, n) {
  if (t.state === "running") return `working${sinceWords(t.started) ? ` ${sinceWords(t.started)}` : ""}`;
  if (t.state === "testing") return "testing";
  if (t.state === "review") return "in Review";
  if (t.state === "picking") return "asks you to pick";
  if (t.state === "failed") return "failed";
  if (t.state === "held") {
    if (n?.waits?.kind === "night") return `tonight${n.waits.until ? ` · after ${hhmm(n.waits.until)}` : ""}`;
    if (n?.waits?.kind === "week") return waitsWords(n.waits);
    return holdWords(t.note, n?.waits?.title) || "held";
  }
  if (t.state === "waiting") return t.after?.length ? afterWords(t, n) : "waiting";
  if (t.state === "ready") return t.note || "next";
  return TASK_STATE[t.state] || t.state;
}
/** The sign at a card's top right: work, cross, night (a hold for tonight); "" for the rest. */
export const taskMark = (t, n) => (RUN.includes(t.state) ? "work" : t.state === "failed" ? "cross" : t.state === "held" && n?.waits?.kind === "night" ? "night" : "");

/** The tasks that wait for `src` (they list it in `after`), in the same goal, not done. */
export function waitersOf(n, src) {
  return openTasks(n).filter((a) => a.id !== src.id && (a.after || []).includes(src.id));
}
/** The tasks `t` waits for: the ones it lists in `after` that are not done yet. */
export function waitsForOf(n, t) {
  return openTasks(n).filter((a) => a.id !== t.id && (t.after || []).includes(a.id));
}
/** A card's dependency lines (the spread's, spec 50 §3.6): *<before> waits for <short>* (*waits for the build*), *<after> n wait for it*. [{sign, text}] */
export function depLines(n, t) {
  const on = waitsForOf(n, t), by = waitersOf(n, t), out = [];
  if (on.length) out.push({ sign: "before", text: `waits for ${followsBuild(t, n) ? "the build" : on.map((x) => x.short || x.title).join(", ")}` });
  if (by.length) out.push({ sign: "after", text: `${by.length} ${by.length === 1 ? "waits" : "wait"} for it` });
  return out;
}

// -- the results --------------------------------------------------------------------------------------------------------------------

/** The goal's results that wait for a look, oldest first. */
export function resultsOf(nodes) {
  const all = nodes.flatMap((n) => (n.results || []).map((r) => ({ ...r, ideaTitle: n.title, ideaSlug: n.slug })));
  return all.map((r, i) => [r, i]).sort(([a, i], [b, j]) => String(a.finished || "").localeCompare(String(b.finished || "")) || i - j).map(([r]) => r);
}

// -- the party line ---------------------------------------------------------------------------------------------------------------------

/** What is at work now, for the party line: [{who, task, goal}] for every running task of the goals at work, and the leader reading ([{who, reading}]). */
export function nowParts(nodes, lead, readingTitle) {
  const bits = [];
  for (const n of nodes.filter(atWork)) for (const t of n.tasks.filter((x) => RUN.includes(x.state))) bits.push({ who: t.by.name, task: t.short || t.title, goal: n.short || n.title });
  if (readingTitle) bits.push({ who: lead, reading: readingTitle });
  return bits;
}
/** The same in plain words (a tooltip): *Backend at work on Credential table (WebAuthn register) · …*, else *nothing at work right now*. */
export const nowWords = (parts) => (parts.length ? parts.map((b) => (b.reading ? `${b.who} at work reading “${b.reading}”` : `${b.who} at work on ${b.task} (${b.goal})`)).join(" · ") : "nothing at work right now");

// -- the gate -------------------------------------------------------------------------------------------------------------------------

/** The gate's button, its words and whether it is off (§5.6); null with no gate to show. */
export function gateOf(gate) {
  if (!gate || gate.same) return null;
  const n = (gate.ideas || []).length, waits = gate.commits > 0;
  return { off: !waits, label: `Merge ${gate.into} into ${gate.main}`,
    words: !waits ? `${gate.main} is up to date` : n ? `${n === 1 ? "1 goal" : `${n} goals`} in ${gate.into} ${n === 1 ? "waits" : "wait"} for ${gate.main}` : `${plural(gate.commits, "commit", "commits")} in ${gate.into} ${gate.commits === 1 ? "waits" : "wait"} for ${gate.main}` };
}

// -- today ---------------------------------------------------------------------------------------------------------------------------------

/** Today's rows of the goal shown, and the gate's (it has no goal): newest first. */
export const todayOf = (today, goal) => (today?.events || []).filter((e) => !e.goal || e.goal === goal);
export const TODAY_TONE = { ok: "is-ok", danger: "is-no", muted: "is-muted", alert: "is-alert", ink: "" };
export const todayTip = (e) => `${e.at} · ${e.title} · ${e.words}`;

// -- the limits ---------------------------------------------------------------------------------------------------------------------------

const pct = (left) => `${Math.round(left * 100)} %`;
/** A tool's line (§8): ten diamonds for what is left, the last ones hatched for the reserve (Claude only); null cells for a tool not read. */
export function limitLine(l, reserve, resetOf) {
  if (typeof l.left !== "number") return { provider: l.provider, name: l.name, read: false, cells: [], pct: "not read", tip: `${l.name}: limits not read${l.error ? ` · ${l.error}` : ""}` };
  const on = Math.round(l.left * 10), share = l.provider === "claude" && reserve ? reserve.share || 0 : 0;
  const kept = share > 0 ? Math.min(on, Math.max(1, Math.round(share * 10))) : 0;
  const tight = [...(l.rows || [])].sort((a, b) => a.left - b.left)[0];
  const reset = tight ? resetOf(tight.reset) : "";
  const cells = Array.from({ length: 10 }, (_, i) => (i < on - kept ? "on" : i < on ? "kept" : ""));
  return { provider: l.provider, name: l.name, read: true, cells, kept, pct: pct(l.left), reset: reset ? `${l.name} ${reset}` : "",
    tip: `${l.name}: ${pct(l.left)} left${kept ? `, ${Math.round(share * 100)} % of it kept for ${reserve.night ? "the morning" : "tonight"}` : ""}${reset ? ` · ${reset}` : ""}` };
}

// -- the stops: the bottom row (§6) -------------------------------------------------------------------------------------------------

export const KIND_WORD = { plan: "Plan ready", change: "Plan change", asks: "Asks you", goal: "Asks you", proposal: "Proposed", party: "Proposed", todo: "A to-do", failed: "Failed",
  pick: "Pick one", op: "At your check", op_failed: "Failed", op_rules: "Rules to take" };
export const isOp = (n) => n.kind === "op" || n.kind === "op_failed" || n.kind === "op_rules";
const GEM = { plan: "", change: "", asks: "?", goal: "?", proposal: "—", party: "—", todo: "·", failed: { sign: "cross" }, pick: "", op: "·", op_failed: { sign: "cross" }, op_rules: "—" };

/** What a plan change adds to the price, for the stop's gem (spec 62 §6.2): *+$0.40–1.20*, *−$0.13–0.38* when it saves (the real minus sign), said as a goal's price is (cents under $1,
 *  else whole dollars); "" for a change of nothing. One that may add or save says both ends: *−$0.10 to +$0.30*. */
export function changeGem(c) {
  const low = Number(c?.usd_low), high = Number(c?.usd_high);
  if (!Number.isFinite(low) || !Number.isFinite(high) || (!low && !high)) return "";
  if (pctDelta(low, high)) return pctDelta(low, high);
  const num = (n, cents) => (cents ? n.toFixed(2) : String(Math.round(n)));
  if (low < 0 && high > 0) return `−$${num(-low, -low < 1)} to +$${num(high, high < 1)}`;
  const [a, b] = [Math.abs(low), Math.abs(high)].sort((x, y) => x - y), cents = a < 1, from = num(a, cents), to = num(b, cents);
  return `${low < 0 || high < 0 ? "−" : "+"}$${from === to ? from : `${from}–${to}`}`;
}

/** A plan change answered, as a toast says it (spec 62 §6.2): *The plan changed: 2 added, 1 dropped.* (only the parts that are not zero), then *1 left as it was: it started.* for the
 *  tasks that started meanwhile; *The plan stays as it was.* when nothing changed (kept, or a change of nothing taken). `got`: `ideas.revise_answer`'s answer. */
export function changeToast(got) {
  const parts = [[got?.added, "added"], [got?.changed, "changed"], [got?.dropped, "dropped"]].filter(([n]) => n > 0).map(([n, w]) => `${n} ${w}`);
  const k = (got?.left || []).length;
  return [parts.length ? `The plan changed: ${parts.join(", ")}.` : "The plan stays as it was.", k ? `${k} left as ${k === 1 ? "it was: it started" : "they were: they started"}.` : ""].filter(Boolean).join(" ");
}

/** The question a row asks first: its `asked` (with the choices and the pick), else its plain text. */
export const firstAsk = (row, node) => (row.asked?.[0] || node?.asked?.[0] || { ask: row.text, choices: [], pick: null, why: "" });
/** A row's questions as `asked` says them (at most three), a plain row's lines with no choices. */
export const askedOf = (row, node) => (row.asked?.length ? row.asked : node?.asked?.length ? node.asked
  : (row.questions?.length ? row.questions : [row.text]).filter(Boolean).map((ask) => ({ ask, choices: [], pick: null, why: "" }))).slice(0, 3);

/** The stops of a goal: its Needs you rows in the host's order, its failed tasks in place of the host's *failed* row of the same idea. */
export function stopsOf(needs, g, nodes) {
  const byIdea = Object.fromEntries(nodes.map((n) => [n.slug, n]));
  const lead = g?.leader?.head || null;
  const failedTasks = (n) => openTasks(n).filter((t) => t.state === "failed");
  const done = new Set();
  const out = [];
  const taskItem = (n, t) => ({ key: `failed/${n.slug}/${t.id}`, kind: "failed", row: null, node: n, task: t, label: KIND_WORD.failed, gem: { sign: "cross" }, tone: "danger",
    gemTip: "It failed", head: t.head || null, small: true, whoTip: `${t.by.name}’s task`, title: t.short || t.title, full: t.title, text: t.error || "It failed" });
  for (const row of needs.filter((x) => !isOp(x) && x.goal === g?.slug)) {
    const n = byIdea[row.idea] || null;
    if (row.kind === "failed" && n && failedTasks(n).length) {
      for (const t of failedTasks(n)) if (!done.has(`${n.slug}/${t.id}`)) { done.add(`${n.slug}/${t.id}`); out.push(taskItem(n, t)); }
      continue;
    }
    const base = { key: `${row.kind}/${row.idea || row.goal}/${row.todo?.id || row.task || ""}`, kind: row.kind, row, node: n, task: null, label: KIND_WORD[row.kind] || row.kind,
      gem: GEM[row.kind] ?? "·", tone: row.kind === "failed" ? "danger" : "alert", gemTip: "", title: row.title, full: row.title, text: row.text, head: lead, small: false, whoTip: "" };
    if (row.kind === "plan") {
      const tasks = n?.tasks || [], checks = tasks.filter((t) => t.band === "check").length, builds = tasks.length - checks;
      base.gem = rangeWords(n?.plan_estimate || n?.estimate) || "—";
      base.gemTip = "What the plan should cost, at API prices";
      if (tasks.length) base.text = `${plural(builds, "task", "tasks")}${checks ? `, ${plural(checks, "check", "checks")}` : ""}`;
    } else if (row.kind === "change") {             // the leader's plan change (spec 62): its price is the gem, its why a muted line under the text
      base.gem = changeGem(row);
      base.gemTip = base.gem ? `What the change should ${row.usd_high < 0 ? "save" : row.usd_low < 0 ? "cost or save" : "cost"}, at API prices` : "";
      base.why = row.why || "";
      base.small = true; base.whoTip = `proposed by ${g?.leader?.name || "Taskmaster"}`;        // the leader's small head on the top row: the card has no room for its art
    } else if (row.kind === "asks" || row.kind === "goal") {
      const q = firstAsk(row, n);
      base.text = `“${q.ask}”`; base.gemTip = "A question costs nothing";
      if (row.kind === "asks") { base.head = q.by?.head || n?.asked?.[0]?.by?.head || lead; base.small = true; base.whoTip = q.by?.name ? `asked by ${q.by.name}` : ""; }
      else base.small = false;
    } else if (row.kind === "failed") { base.small = true; base.head = lead; base.gemTip = "It failed"; }
    else if (row.kind === "pick") {                 // the gem is the count; the member's head; the ask is its line (spec 51 §6)
      base.gem = String(row.n); base.gemTip = kindCount(row); base.small = true; base.head = row.by?.head || lead; base.whoTip = row.by?.name ? `made by ${row.by.name}` : "";
      base.title = row.short || row.title; base.text = `“${row.ask}”`;
    }
    else if (row.kind === "proposal" || row.kind === "party") base.gemTip = "Not planned yet";
    out.push(base);
  }
  for (const n of nodes) for (const t of failedTasks(n)) if (!done.has(`${n.slug}/${t.id}`)) { done.add(`${n.slug}/${t.id}`); out.push(taskItem(n, t)); }
  return out;
}

/** Operations' stops: its rows (op, op_failed, op_rules) in the host's order. */
export function opStopsOf(needs) {
  return needs.filter(isOp).map((row) => ({ key: `${row.kind}/${row.op || row.template}`, kind: row.kind, row, node: null, task: null, label: KIND_WORD[row.kind],
    gem: GEM[row.kind], tone: row.kind === "op_failed" ? "danger" : "alert", gemTip: "", head: null, small: false, whoTip: "", title: row.title,
    full: row.title, text: row.kind === "op_rules" ? (row.lines || [row.text]).join(" · ") : row.text }));
}

// -- one hand (spec 54 §2) ---------------------------------------------------------------------------------------------------------

/** How urgent a kind of stop is (§2.3): 0 red (a failure), 1 what holds work back, 2 what does not, 3 the results to look at. */
const URGENCY = { failed: 0, op_failed: 0, plan: 1, change: 1, asks: 1, goal: 1, todo: 1, pick: 1, op: 1, proposal: 2, party: 2, op_rules: 2, result: 3 };
export const urgencyOf = (s) => URGENCY[s.kind] ?? 1;
const ageOf = (s) => String(s.row?.at || s.task?.finished || s.task?.started || s.result?.finished || "9999");

/** The hand's stops by urgency, the oldest first in a group (a stable sort: the host's order breaks a tie). */
export function byUrgency(stops) {
  return stops.map((s, i) => [s, i]).sort(([a, i], [b, j]) => urgencyOf(a) - urgencyOf(b) || ageOf(a).localeCompare(ageOf(b)) || i - j).map(([s]) => s);
}

/** Each stop of a party (`g`; null for Operations) with the party it belongs to — its name, leader (head and name) — and whether it is another party's than the one shown. */
function inParty(stops, g, shown) {
  const party = g ? { slug: g.slug, name: g.short || g.title, head: g.leader?.head || null, lead: g.leader?.name || "Taskmaster", ops: false }
    : { slug: OPS, name: "Operations", head: null, lead: "Taskmaster", ops: true };
  return stops.map((s) => ({ ...s, g: g || null, party, other: party.slug !== shown }));
}

/** Every stop of the project (§2.1): each party's Needs you rows, failed tasks and Pick one, then Operations'; `keep(partySlug, stop)` is the filter (only the picked goals'),
 *  and the party shown's results join them when `withResults` (below 1 024 px). In urgency's order (§2.3). */
export function handOf({ map, needs, order, shown, keep, withResults = false, ops = true }) {
  const out = [];
  for (const g of goalsOf(map, order)) {
    const nodes = nodesOf(map, g.slug), mine = stopsOf(needs, g, nodes);
    if (withResults && g.slug === shown) mine.push(...resultsOf(nodes).map((r) => resultStop(r, nodes)));
    out.push(...inParty(mine.filter((s) => keep(g.slug, s)), g, shown));
  }
  if (ops) out.push(...inParty(opStopsOf(needs), null, shown));
  return byUrgency(out);
}

/** Where the k-th most urgent of `n` stops lies in the row (§2.3): the most urgent in the middle, the next to its right, the next to its left, and so outward. */
export function laidOut(n) {
  const row = [];
  for (let k = 0; k < n; k += 1) { if (k % 2) row.push(k); else row.unshift(k); }
  const at = new Array(n);
  row.forEach((k, place) => { at[k] = place; });
  return at;
}

/** A fan's turn, rise and order for the item at place `i` of `n` (the middle ones higher): the values of `--rot`, `--dy` and `--z`. A long hand turns less. */
export function fanOf(i, n, fanned = true) {
  const off = i - (n - 1) / 2, ease = n > 6 ? 6 / n : 1;
  return { rot: fanned ? Math.round(off * 5 * ease * 10) / 10 : 0, dy: fanned ? Math.round(off * off * 4 * ease * ease) : 0, z: 10 + i };
}

/** A result among the stops, below 1 024 px (§3): *To look at*, with a result's own answers. */
export function resultStop(r, nodes) {
  const node = nodes.find((n) => n.slug === r.idea) || null, task = node?.tasks.find((t) => t.id === r.task) || null;
  const t = r.tests && !r.check ? r.tests : null;
  return { key: `result/${r.idea}/${r.task}`, kind: "result", row: null, node, task, result: r, label: "To look at", gem: { sign: r.check || !(t && (t.failed > 0 || t.green === false)) ? "check" : "cross" },
    tone: "", gemTip: "A result waits for your look", head: task?.head || null, small: true, whoTip: task ? `${task.by.name}’s task` : "", title: r.title, full: r.title,
    text: [r.diff ? `${plural(r.diff.files, "file", "files")}` : "", r.cost != null ? money(r.cost) : ""].filter(Boolean).join(" · ") };
}
